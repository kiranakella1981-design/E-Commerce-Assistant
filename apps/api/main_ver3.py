from fastapi import FastAPI
from pydantic import BaseModel
import json
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
DATA_PATH = "/app/data/mock_tools/mock_responses.json"
with open(DATA_PATH, "r") as f:
    mock_data = json.load(f)

# ---------------- UTIL ----------------
def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None

def classify_intent(user_query: str) -> str:
    q = user_query.lower()
    if "refund" in q:
        return "refund_status"
    elif "return" in q:
        return "return_policy"
    elif "order" in q:
        return "order_status"
    else:
        return "faq"

# ---------------- RAG SETUP ----------------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

docs = [
    "Refunds are processed within 5 business days.",
    "Returns must be initiated within 30 days of delivery.",
    "Orders are shipped via BlueDart and typically arrive in 3 to 5 days.",
    "Return pickup is available for most metro cities."
]

doc_embeddings = embedder.encode(docs)
index = faiss.IndexFlatL2(doc_embeddings.shape[1])
index.add(doc_embeddings)

# Instruction-tuned model, cleaner output
generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    return_full_text=False
)

def retrieve_docs(query: str, k: int = 2, threshold: float = 1.0) -> list[str]:
    q_emb = embedder.encode([query])
    D, I = index.search(q_emb, k)
    # Only return docs if similarity is strong enough
    if D[0][0] > threshold:
        return []
    return [docs[i] for i in I[0]]

# ---------------- CHAT ENDPOINT ----------------
@app.post("/chat")
def chat(req: ChatRequest):
    user_query = req.message
    intent = classify_intent(user_query)
    order_id = extract_order_id(user_query)

    # ---------- GUARDS ----------
    if intent in {"order_status", "refund_status", "return_policy"} and not order_id:
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

    elif intent == "return_policy":
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
