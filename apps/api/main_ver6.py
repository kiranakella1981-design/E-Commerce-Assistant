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

    # ---------- FAQ / POLICY FIRST ----------
    faq_phrases = [
        "policy",
        "policies",
        "refund policy",
        "refund policies",
        "return policy",
        "return policies",
        "how do refunds work",
        "how do returns work",
        "explain refund",
        "explain return",
        "what happens if"
    ]

    if any(p in q for p in faq_phrases):
        return {"intent": "faq", "needs_order_id": False}

    # ---------- TRANSACTIONAL (ONLY IF ORDER ID EXISTS) ----------
    if has_order_id:
        if "refund" in q:
            return {"intent": "refund_status", "needs_order_id": False}

        if "return" in q:
            return {"intent": "return_request", "needs_order_id": False}

        if "order" in q or "track" in q or "where is" in q:
            return {"intent": "order_status", "needs_order_id": False}

    # ---------- AMBIGUOUS ORDER QUESTIONS ----------
    if "order" in q or "refund" in q or "return" in q:
        return {"intent": "faq", "needs_order_id": False}

    # ---------- SAFE FALLBACK ----------
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

    logger.info(f"[CHAT] Incoming message: '{user_query}'")

    classification = classify_intent(user_query)
    intent = classification["intent"]
    needs_order_id = classification["needs_order_id"]
    order_id = extract_order_id(user_query)

    logger.info(
        "[CLASSIFY] intent=%s | needs_order_id=%s | extracted_order_id=%s",
        intent,
        needs_order_id,
        order_id
    )

    # ---------- GUARD ----------
    if needs_order_id and not order_id:
        logger.warning(
            "[GUARD BLOCKED] intent=%s | message='%s'",
            intent,
            user_query
        )
        return {"message": "❗ Please provide a valid order number (e.g., 12345)."}

    # ---------- FAQ / RAG ----------
    if intent == "faq":
        logger.info("[FAQ] Running RAG retrieval")

        retrieved = retrieve_docs(user_query)

        logger.info("[FAQ] Retrieved %d documents", len(retrieved))

        if not retrieved:
            logger.warning("[FAQ] No documents retrieved")
            return {"message": "I don't have enough information to answer that."}

        context = "\n".join(retrieved)

        logger.info("[FAQ] Generating answer")

        result = generator(prompt := f"""Answer ONLY using the information below.
If the answer is not present, say "I don't have that information."

Context:
{context}

Question:
{user_query}

Answer:""", max_new_tokens=80)

        answer = result[0]["generated_text"].strip()

        logger.info("[FAQ] Answer generated successfully")

        return {"message": answer}

    # ---------- STRUCTURED TOOLS ----------
    logger.info("[STRUCTURED] Routing to tool: %s", intent)

    if intent == "order_status":
        ...
    elif intent == "refund_status":
        ...
    elif intent == "return_request":
        ...
    else:
        logger.warning("[FALLBACK] Unknown intent: %s", intent)
        reply = "ℹ️ This assistant supports order status, refund status, and returns."

    return {"message": reply}
