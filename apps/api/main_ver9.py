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

    # ---------- FAQ ----------
    if intent in ["faq", "unknown"] or is_policy_query(user_query):
        retrieved = retrieve_docs(user_query)
        if not retrieved:
            return {"message": "I don't have enough information to answer that."}

        context = "\n".join(retrieved)
        prompt = f"""
        You are a customer support assistant.

        When answering:
        - Provide a complete and clear response.
        - Include all relevant conditions, steps, timelines, and exceptions.
        - If multiple sentences in the context relate to the question, combine them into one coherent answer.
        - Do not truncate the answer.

        If the context does not contain the answer, reply exactly:
        "I don't have that information."

        Context:
        {context}

        Customer Question:
        {user_query}

        Answer:
        """
        result = generator(prompt, max_new_tokens=1000)
        return {"message": result[0]["generated_text"].strip()}

    # ---------- Structured Tools ----------
    if intent == "order_status":
        data = find_record(mock_data.get("order_status", []), order_id)
        if data:
            logger.info("Returning from return_request with data=%s", data)
            items_str = "\n".join(
                [f"- {i['name']} (SKU: {i['sku']}, Qty: {i['qty']})" for i in data.get("items", [])]
            )
            return {
                "message": (
                    f"👜 Order #{order_id} is {data['status']} and will arrive by {data['estimated_delivery']}.\n"
                    f"Items:\n{items_str}"
                )
            }
        return {"message": f"❌ No data found for order #{order_id}."}

    if intent == "refund_status":
        data = find_record(mock_data.get("refund_status", []), order_id)
        if data:
            logger.info("Refund intent triggered for order_id=%s, data=%s", order_id, data)
            return {
                "message": (
                    f"🧾 Refund for Order #{order_id} is in **{data['status']}**.\n"
                    f"Amount: {data['amount']} INR\n"
                    f"Timeline: {data['timeline']}"
                )
            }
        return {"message": f"❌ No refund record found for order #{order_id}."}

    if intent == "return_request":
        data = find_record(mock_data.get("return_request", []), order_id)
        if data:
            logger.info("Returning from return_request with data=%s", data)
            return {
                "message": (
                    f"📦 Return request for Order #{order_id}:\n"
                    f"- Item: {data['item_id']}\n"
                    f"- Reason: {data['reason']}\n"
                    f"- Method: {data['method']}\n"
                    f"[Download return label]({data['label_url']})"
                )
            }
        return {"message": f"❌ No return request found for order #{order_id}."}

    if intent == "escalation":
        data = find_record(mock_data.get("escalation", []), order_id)
        if data:
            logger.info("Returning from return_request with data=%s", data)
            return {
                "message": (
                    f"⚠️ Escalation created for Order #{order_id}:\n"
                    f"- Ticket ID: {data['ticket_id']}\n"
                    f"- Status: {data['status']}\n"
                    f"- Assigned To: {data['assigned_to']}"
                )
            }
        return {"message": f"❌ No escalation record found for order #{order_id}."}

    return {"message": "ℹ️ This assistant supports order status, refund status, returns, and escalations."}


# --- Order Status ---
@app.get("/order/{order_id}", response_model=OrderStatusResponse)
def get_order(order_id: str):
    if order_id == "error500":
        raise HTTPException(status_code=500, detail="Internal server error")
    elif order_id == "notfound":
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "status": "shipped",
        "estimated_delivery": "2026-01-10",
        "items": [{"sku": "ABC123", "name": "Shoes", "qty": 1}],
    }


# --- Refund ---
@app.post("/refund/{order_id}", response_model=RefundResponse)
def refund_order(order_id: str):
    if order_id in processed_refunds:
        return {"order_id": order_id, "status": "already_refunded"}
    processed_refunds.add(order_id)
    return {"order_id": order_id, "status": "refund_processed", "amount": 1200.0}


# --- Return ---
@app.post("/return/{order_id}", response_model=ReturnResponse)
def return_order(order_id: str):
    if order_id in processed_returns:
        return {
            "order_id": order_id,
            "item_id": "XYZ789",
            "reason": "duplicate_request",
            "method": "pickup",
        }
    processed_returns.add(order_id)
    return {
        "order_id": order_id,
        "item_id": "XYZ789",
        "reason": "size_issue",
        "method": "dropoff",
    }


# --- Escalation ---
@app.post("/escalate/{order_id}", response_model=EscalationResponse)
def escalate_issue(order_id: str):
    return {
        "ticket_id": f"TKT-{order_id}",
        "status": "open",
        "assigned_to": "support_agent_1",
    }


# --- Logging Middleware ---
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response