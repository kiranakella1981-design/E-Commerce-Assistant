# =========================
# Imports
# =========================
import json
import logging

from fastapi import FastAPI, HTTPException
from models import (
    ChatRequest,
    OrderStatusResponse,
    RefundResponse,
    ReturnResponse,
    EscalationResponse,
)
from intents import classify_intent, is_policy_query
from rag import retrieve_docs, generator, load_faq_docs
from utils import extract_order_id, find_record

# =========================
# App Initialization
# =========================
app = FastAPI(title="E-Commerce Support Mock Tools")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ecom-chat")

# --- Idempotency stores ---
processed_refunds: set[str] = set()
processed_returns: set[str] = set()

# =========================
# Data Paths
# =========================
MOCK_PATH = "/app/data/mock_tools/mock_responses.json"

with open(MOCK_PATH, "r") as f:
    mock_data = json.load(f)

# =========================
# API Endpoints
# =========================
@app.post("/reload_faq")
def reload_faq():
    load_faq_docs()
    return {"message": "FAQ reloaded successfully."}


@app.post("/chat")
def chat(req: ChatRequest):
    user_query = req.message
    logger.info("[ENTRY] /chat message='%s'", user_query)

    classification = classify_intent(user_query)
    intent = classification["intent"]
    needs_order_id = classification["needs_order_id"]
    order_id = extract_order_id(user_query)

    logger.info(
        "[CLASSIFY] intent=%s needs_order_id=%s extracted_order_id=%s",
        intent,
        needs_order_id,
        order_id,
    )

    # ---------- Guard ----------
    if needs_order_id and not order_id:
        logger.info("[GUARD] Missing order ID")
        return {"message": "❗ Please provide a valid order number (e.g., 12345)."}

    if intent in ["faq", "unknown"] or is_policy_query(user_query):
        logger.info("[FAQ] Handling FAQ intent")

        with open("data/faq_docs.json") as f:
            faq_docs = json.load(f)  # list of strings

        relevant_answers = []
        q = user_query.lower()

        if "refund" in q:
            relevant_answers = [entry for entry in faq_docs if "refund" in entry.lower()]
        elif "return" in q:
            relevant_answers = [entry for entry in faq_docs if "return" in entry.lower()]
        elif "exchange" in q:
            relevant_answers = [entry for entry in faq_docs if "exchange" in entry.lower()]
        elif "exception" in q:
            relevant_answers = [entry for entry in faq_docs if "exception" in entry.lower()]
        elif "international" in q:
            relevant_answers = [entry for entry in faq_docs if "international" in entry.lower()]
        elif "support" in q:
            relevant_answers = [entry for entry in faq_docs if "support" in entry.lower()]
        elif "rule" in q:
            relevant_answers = [entry for entry in faq_docs if "rule" in entry.lower()]

        if not relevant_answers:
            logger.info("[FAQ] No relevant FAQ entries found for query='%s'", user_query)
            return {"message": "I don't have that information."}

        faq_context = "\n".join(relevant_answers[:3])
        logger.info("[FAQ] Context injected:\n%s", faq_context)

        prompt = f"""
        You are a customer support assistant.

        The customer is asking about a policy (e.g., refund, return, exchange). Your job is to:
        - Interpret the question as a request for structured policy information.
        - Extract and merge relevant sentences from the context below.
        - Organize the answer clearly: start with eligibility, then process, then exceptions.
        - Include timelines, conditions, and edge cases.
        - Do not repeat the question or echo the input.
        - Do not truncate or summarize vaguely.
        - If the context does not contain the answer, reply exactly:
        "I don't have that information."

        Context:
        {faq_context}

        Customer Question:
        {user_query}

        Answer:
        """

        result = generator(prompt, max_new_tokens=1000)
        logger.info("[FAQ] Returning generated answer")
        return {"message": result[0]["generated_text"].strip()}


    # ---------- Structured Tools ----------
    if intent == "order_status":
        data = find_record(mock_data.get("order_status", []), order_id)
        if data:
            logger.info("[ORDER_STATUS] Found record for order_id=%s data=%s", order_id, data)
            items_str = "\n".join(
                [f"- {i['name']} (SKU: {i['sku']}, Qty: {i['qty']})" for i in data.get("items", [])]
            )
            return {
                "message": (
                    f"👜 Order #{order_id} is {data['status']} and will arrive by {data['estimated_delivery']}.\n"
                    f"Items:\n{items_str}"
                )
            }
        logger.info("[ORDER_STATUS] No record found for order_id=%s", order_id)
        return {"message": f"❌ No data found for order #{order_id}."}

    if intent == "refund_status":
        data = find_record(mock_data.get("refund_status", []), order_id)
        if data:
            logger.info("[REFUND_STATUS] Found record for order_id=%s data=%s", order_id, data)
            return {
                "message": (
                    f"🧾 Refund for Order #{order_id} is in **{data['status']}**.\n"
                    f"Amount: {data['amount']} INR\n"
                    f"Timeline: {data['timeline']}"
                )
            }
        logger.info("[REFUND_STATUS] No record found for order_id=%s", order_id)
        return {"message": f"❌ No refund record found for order #{order_id}."}

    if intent == "return_request":
        data = find_record(mock_data.get("return_request", []), order_id)
        if data:
            logger.info("[RETURN_REQUEST] Found record for order_id=%s data=%s", order_id, data)
            return {
                "message": (
                    f"📦 Return request for Order #{order_id}:\n"
                    f"- Item: {data['item_id']}\n"
                    f"- Reason: {data['reason']}\n"
                    f"- Method: {data['method']}\n"
                    f"[Download return label]({data['label_url']})"
                )
            }
        logger.info("[RETURN_REQUEST] No record found for order_id=%s", order_id)
        return {"message": f"❌ No return request found for order #{order_id}."}

    if intent == "escalation":
        data = find_record(mock_data.get("escalation", []), order_id)
        if data:
            logger.info("[ESCALATION] Found record for order_id=%s data=%s", order_id, data)
            return {
                "message": (
                    f"⚠️ Escalation created for Order #{order_id}:\n"
                    f"- Ticket ID: {data['ticket_id']}\n"
                    f"- Status: {data['status']}\n"
                    f"- Assigned To: {data['assigned_to']}"
                )
            }
        logger.info("[ESCALATION] No record found for order_id=%s", order_id)
        return {"message": f"❌ No escalation record found for order #{order_id}."}

    logger.info("[FALLBACK] General fallback triggered")
    return {"message": "ℹ️ This assistant supports order status, refund status, returns, and escalations."}