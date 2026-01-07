from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import re
import logging

from sentence_transformers import SentenceTransformer
import faiss
from transformers import pipeline

# ---------------- APP ----------------
app = FastAPI(title="E-Commerce Support Mock Tools")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("ecom-chat")


# ---------------- MODELS ----------------
class ChatRequest(BaseModel):
    message: str

# ---------------- MOCK DATA ----------------
# DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mock_responses.json")
# with open(DATA_PATH, "r") as f:
#     mock_data = json.load(f)
# ---------------- MOCK DATA ----------------
MOCK_PATH = "/app/data/mock_tools/mock_responses.json"
with open(MOCK_PATH, "r") as f:
    mock_data = json.load(f)

FAQ_PATH = "/app/data/faq_docs.json"

# ---------------- UTIL ----------------
def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None


def classify_intent(user_query: str) -> dict:
    q = user_query.lower()
    has_order_id = bool(re.search(r"\b\d{4,}\b", q))

    logger.info(
        f"Intent classification started | query='{user_query}' | has_order_id={has_order_id}"
    )

    # ---------- FAQ / POLICY (FIRST) ----------
    # policy_phrases = [
    #     "refund policy",
    #     "return policy",
    #     "refund policies",
    #     "return policies",
    #     "refund rules",
    #     "return rules",
    #     "how do refunds work",
    #     "how do returns work",
    #     "refund policy",
    #     "return policy",
    #     "policies"
    # ]

    policy_phrases = [
        # Core policy terms
        "return policy",
        "refund policy",
        "returns and refunds",
        "returns & refunds",

        # Refund related
        "refund",
        "refunds",
        "get a refund",
        "refund status",
        "refund time",
        "how long for refund",
        "refund processing time",
        "refund method",

        # Return related
        "return",
        "returns",
        "return item",
        "return process",
        "return window",
        "return period",
        "eligible for return",
        "non returnable",
        "return eligibility",

        # Exchange
        "exchange",
        "replacement",
        "replace item",

        # Defective / incorrect items
        "defective item",
        "damaged item",
        "wrong item",
        "incorrect item",

        # Charges & exceptions
        "shipping fee refund",
        "refund shipping charges",
        "final sale",
        "non refundable"
    ]

    if any(p in q for p in policy_phrases):
        logger.info("Detected intent='faq'")
        return {"intent": "faq", "needs_order_id": False}

    # ---------- TRANSACTIONAL ----------
    if "refund" in q and (has_order_id or "status" in q):
        logger.info("Detected intent='refund_status'")
        return {"intent": "refund_status", "needs_order_id": True}

    if "return" in q and (has_order_id or "request" in q):
        logger.info("Detected intent='return_request'")
        return {"intent": "return_request", "needs_order_id": True}

    if any(p in q for p in ["order", "track", "where is"]):
        logger.info("Detected intent='order_status'")
        return {"intent": "order_status", "needs_order_id": True}

    # ---------- FALLBACK ----------
    logger.info("Detected intent='faq'")
    return {"intent": "faq", "needs_order_id": False}


# ---------------- RAG SETUP ----------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")
#generator = pipeline("text2text-generation", model="google/flan-t5-small", return_full_text=False)
generator = pipeline("text2text-generation", model="google/flan-t5-small")

docs = []
index = None

def load_faq_docs():
    global docs, index
    with open(FAQ_PATH, "r") as f:
        docs = json.load(f)
    doc_embeddings = embedder.encode(docs)
    index = faiss.IndexFlatL2(doc_embeddings.shape[1])
    index.add(doc_embeddings)

# Load FAQ docs once at startup
load_faq_docs()

def retrieve_docs(query: str, k: int = 2, threshold: float = 1.0) -> list[str]:
    q_emb = embedder.encode([query])
    D, I = index.search(q_emb, k)
    if D[0][0] > threshold:
        return []
    return [docs[i] for i in I[0]]

# ---------------- ENDPOINTS ----------------
@app.post("/reload_faq")
def reload_faq():
    load_faq_docs()
    return {"message": f"FAQ reloaded successfully. {len(docs)} entries indexed."}

@app.post("/chat")
def chat(req: ChatRequest):
    user_query = req.message
    logger.info(f"[ENTRY] /chat clasify_intent called with message='{user_query}'")
    classification = classify_intent(user_query)

    intent = classification["intent"]
    needs_order_id = classification["needs_order_id"]
    order_id = extract_order_id(user_query)

    logger.info(
        f"[CLASSIFY] intent={intent} | needs_order_id={needs_order_id} | extracted_order_id={order_id}"
    )

    # ---------- GUARD ----------
    if needs_order_id and not order_id:
        logger.info("[GUARD] Missing order ID")
        return {"message": "❗ Please provide a valid order number (e.g., 12345)."}

    reply = "⚠️ Unable to process your request."

    # ---------- FAQ ----------
    if intent == "faq":
        retrieved = retrieve_docs(user_query)
        # if not retrieved:
        #     return {"message": "I don't have enough information to answer that."}

        # context = "\n".join(retrieved)
        # result = generator(context, max_new_tokens=80)
        # return {"message": result[0]["generated_text"].strip()}
    
        if not retrieved:
                return {"message": "I don't have enough information to answer that."}

        context = "\n".join(retrieved)        
        prompt = f"""Answer ONLY using the information below.
            If the answer is not present, say "I don't have that information."

            Context:
            {context}

            Question:
            {user_query}

            Answer:"""

        result = generator(prompt, max_new_tokens=80)
        answer = result[0]["generated_text"].strip()
        return {"message": answer}


    # ---------- STRUCTURED TOOLS ----------
    if intent == "order_status":
        data = mock_data.get("order_status", {})
        if str(data.get("order_id")) == str(order_id):
            reply = (
                f"👜 Order #{order_id} is {data['status']} and will arrive by {data['expected_delivery']}.\n"
                f"Carrier: {data['carrier']}\n"
                f"[Track your order]({data['tracking_url']})"
            )
        else:
            reply = f"❌ No data found for order #{order_id}."

    elif intent == "refund_status":
        data = mock_data.get("refund_status", {})
        if str(data.get("order_id")) == str(order_id):
            reply = (
                f"🧾 Refund for Order #{order_id} is in **{data['stage']}**.\n"
                f"Amount: {data['amount']} INR\n"
                f"Timeline: {data['timeline']}"
            )
        else:
            reply = f"❌ No refund record found for order #{order_id}."

    elif intent == "return_request":
        data = mock_data.get("return_request", {})
        if str(data.get("order_id")) == str(order_id):
            reply = (
                f"📦 Return request for Order #{order_id}:\n"
                f"- Item: {data['item_id']}\n"
                f"- Reason: {data['reason']}\n"
                f"- Method: {data['method']}\n"
                f"[Download return label]({data['label_url']})"
            )
        else:
            reply = f"❌ No return request found for order #{order_id}."

    else:
        reply = "ℹ️ This assistant supports order status, refund status, and returns."

    return {"message": reply}

