# =========================
# Imports
# =========================
import json
import logging
import os
import re

from fastapi import FastAPI
from pydantic import BaseModel

from sentence_transformers import SentenceTransformer
import faiss
from transformers import pipeline


# =========================
# App Initialization
# =========================
app = FastAPI(title="E-Commerce Support Mock Tools")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("ecom-chat")


# =========================
# Request Models
# =========================
class ChatRequest(BaseModel):
    message: str


# =========================
# Data Paths
# =========================
MOCK_PATH = "/app/data/mock_tools/mock_responses.json"
FAQ_PATH = "/app/data/faq_docs.json"

with open(MOCK_PATH, "r") as f:
    mock_data = json.load(f)


# =========================
# Utility Functions
# =========================
def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None


def has_order_id(query: str) -> bool:
    return bool(re.search(r"\b\d{4,}\b", query))


def contains_phrase(query: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", query) is not None


# =========================
# Order Intent Detection
# =========================
STRONG_ORDER_ACTIONS = [
    "track", "tracking",
    "where is", "where's",
    "cancel", "cancelled",
    "refund my", "return my", "replace my",
    "order status",
    "shipment status",
]

WEAK_ORDER_ACTIONS = [
    "shipment",
    "delivered",
    "delivery",
    "package",
]


def has_order_action(query: str) -> bool:
    q = query.lower()

    for phrase in STRONG_ORDER_ACTIONS:
        if contains_phrase(q, phrase):
            return True

    for phrase in WEAK_ORDER_ACTIONS:
        if contains_phrase(q, phrase) and "my" in q:
            return True

    return False


# =========================
# FAQ Detection
# =========================
FAQ_KEYWORDS = {
    "refund": [
        "refund", "refunds", "money back",
        "refund time", "refund status",
        "refund processing time",
    ],

    "return": [
        "return", "returns", "return item",
        "return window", "return period",
        "return eligibility", "return rules",
    ],

    "exchange": [
        "exchange", "replacement", "replace item",
    ],

    "defective": [
        "defective", "damaged", "broken",
        "wrong item", "incorrect item",
    ],

    "exceptions": [
        "exception", "exceptions",
        "excluded", "exclusion",
        "non refundable", "non returnable",
        "final sale", "clearance",
        "special case", "special conditions",
    ],

    "international": [
        "international", "overseas",
        "outside india", "global",
        "remote area", "remote location",
        "cross border",
    ],

    "contact": [
        "contact", "support",
        "customer care", "customer support",
        "helpdesk", "email",
        "phone", "call",
        "live chat",
    ],

    "policy": [
        "policy", "terms", "conditions",
        "rules", "guidelines",
    ],
}


def is_faq_intent(query: str) -> bool:
    q = query.lower()
    matches = sum(
        1
        for keywords in FAQ_KEYWORDS.values()
        for kw in keywords
        if kw in q
    )
    return matches >= 1


# =========================
# Final Intent Classifier
# =========================
def classify_intent(user_query: str) -> dict:
    q = user_query.lower()

    order_id_present = has_order_id(q)
    order_action_present = has_order_action(q)
    is_order_query = order_id_present and order_action_present

    logger.info(
        "[INTENT_START] query='%s' order_id=%s order_action=%s",
        user_query,
        order_id_present,
        order_action_present,
    )

    # 1️⃣ Order intents (highest priority)
    if is_order_query:
        logger.info("[INTENT] ORDER detected")

        if "refund" in q:
            return {"intent": "refund_status", "needs_order_id": True}

        if "return" in q:
            return {"intent": "return_request", "needs_order_id": True}

        return {"intent": "order_status", "needs_order_id": True}

    # 2️⃣ FAQ intents
    if is_faq_intent(q):
        logger.info("[INTENT] FAQ detected")
        return {"intent": "faq", "needs_order_id": False}

    # 3️⃣ Fallback
    logger.info("[INTENT] GENERAL fallback")
    return {"intent": "general", "needs_order_id": False}


# =========================
# RAG Setup
# =========================
embedder = SentenceTransformer("all-MiniLM-L6-v2")
generator = pipeline("text2text-generation", model="google/flan-t5-small")

docs: list[str] = []
index = None


def load_faq_docs() -> None:
    global docs, index

    with open(FAQ_PATH, "r") as f:
        docs = json.load(f)

    embeddings = embedder.encode(docs)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)


# def retrieve_docs(query: str, k: int = 2, threshold: float = 1.0) -> list[str]:
#     q_emb = embedder.encode([query])
#     distances, indices = index.search(q_emb, k)

#     if distances[0][0] > threshold:
#         return []

#     return [docs[i] for i in indices[0]]

def retrieve_docs(query: str, k: int = 4, threshold: float = 2.5) -> list[str]:
    q_emb = embedder.encode([query])
    distances, indices = index.search(q_emb, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if dist <= threshold:
            results.append(docs[idx])

    return results

def is_policy_query(query: str) -> bool:
    policy_words = [
        "return", "refund", "exchange",
        "policy", "exception", "contact",
        "international", "eligible",
        "support", "rules"
    ]
    return any(w in query.lower() for w in policy_words)


# Load FAQ docs on startup
load_faq_docs()


# =========================
# API Endpoints
# =========================
@app.post("/reload_faq")
def reload_faq():
    load_faq_docs()
    return {
        "message": f"FAQ reloaded successfully. {len(docs)} entries indexed."
    }


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

        # Use ONLY the information provided in the context below.
        # Do NOT add new information or assumptions.

    # ---------- FAQ ----------
    # if intent == "faq":
    #     retrieved = retrieve_docs(user_query)
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
        data = mock_data.get("order_status", {})
        if str(data.get("order_id")) == str(order_id):
            return {
                "message": (
                    f"👜 Order #{order_id} is {data['status']} and will arrive by "
                    f"{data['expected_delivery']}.\n"
                    f"Carrier: {data['carrier']}\n"
                    f"[Track your order]({data['tracking_url']})"
                )
            }
        return {"message": f"❌ No data found for order #{order_id}."}

    if intent == "refund_status":
        data = mock_data.get("refund_status", {})
        if str(data.get("order_id")) == str(order_id):
            return {
                "message": (
                    f"🧾 Refund for Order #{order_id} is in **{data['stage']}**.\n"
                    f"Amount: {data['amount']} INR\n"
                    f"Timeline: {data['timeline']}"
                )
            }
        return {"message": f"❌ No refund record found for order #{order_id}."}

    if intent == "return_request":
        data = mock_data.get("return_request", {})
        if str(data.get("order_id")) == str(order_id):
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

    return {
        "message": "ℹ️ This assistant supports order status, refund status, and returns."
    }
