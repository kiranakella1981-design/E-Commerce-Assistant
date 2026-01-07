from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import re

from sentence_transformers import SentenceTransformer
import faiss
from transformers import pipeline

# ---------------- APP ----------------
app = FastAPI(title="E-Commerce Support Mock Tools")

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

    # ---------- STRUCTURED ACTIONS ----------
    if has_order_id:
        if "refund" in q:
            return {"intent": "refund_status", "needs_order_id": False}
        if "return" in q:
            return {"intent": "return_request", "needs_order_id": False}
        if "order" in q or "where is" in q or "track" in q:
            return {"intent": "order_status", "needs_order_id": False}

    # ---------- POLICY / FAQ ----------
    if any(phrase in q for phrase in [
        "return policy",
        "refund policy",
        "how do returns work",
        "how do refunds work",
        "explain return",
        "explain refund",
        "policy"
    ]):
        return {"intent": "faq", "needs_order_id": False}

    # ---------- AMBIGUOUS TRACKING ----------
    if "where is my order" in q or "track my order" in q:
        return {"intent": "order_status", "needs_order_id": True}

    # ---------- FALLBACK ----------
    return {"intent": "faq", "needs_order_id": False}

# ---------------- RAG SETUP ----------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")
generator = pipeline("text2text-generation", model="google/flan-t5-small", return_full_text=False)

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
    classification = classify_intent(user_query)
    intent = classification["intent"]
    needs_order_id = classification["needs_order_id"]
    order_id = extract_order_id(user_query)

    # ---------- GUARD ----------
    if needs_order_id and not order_id:
        return {"message": "❗ Please provide a valid order number (e.g., 12345)."}

    # ---------- FAQ / RAG ----------
    if intent == "faq":
        retrieved = retrieve_docs(user_query)

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
