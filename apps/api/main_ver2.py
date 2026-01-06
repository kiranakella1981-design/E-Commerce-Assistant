from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import re

app = FastAPI(title="E-Commerce Support Mock Tools")

# Load mock data once at startup
DATA_PATH = "/app/data/mock_tools/mock_responses.json"
with open(DATA_PATH, "r") as f:
    mock_data = json.load(f)

# ---------------- MODELS ----------------
class ChatRequest(BaseModel):
    message: str

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

# ---------------- EXISTING TOOL ENDPOINTS ----------------
@app.get("/tools/order/{order_id}/status")
def get_order_status(order_id: str):
    if mock_data.get("order_status", {}).get("order_id") == order_id:
        return mock_data["order_status"]
    raise HTTPException(status_code=404, detail="Order not found")

@app.post("/tools/return")
def create_return_request(order_id: str, item_id: str, reason: str):
    return {
        "order_id": order_id,
        "item_id": item_id,
        "reason": reason,
        "return_request_id": "RR-20260105-001",
        "method": "pickup",
        "label_url": "http://mockreturns.com/label/RR-20260105-001"
    }

@app.get("/tools/refund/{order_id}/status")
def get_refund_status(order_id: str):
    if mock_data.get("refund_status", {}).get("order_id") == order_id:
        return mock_data["refund_status"]
    raise HTTPException(status_code=404, detail="Refund not found")

# ---------------- NEW CHAT ENDPOINT ----------------
@app.post("/chat")
def chat(req: ChatRequest):
    user_query = req.message
    order_id = extract_order_id(user_query)
    intent = classify_intent(user_query)

    # Guardrail: missing order ID
    if intent in {"order_status", "refund_status", "return_policy"} and not order_id:
        return {"message": "❗ Please provide a valid order number (e.g. 12345)."}

    # Route to tools
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
        reply = "ℹ️ This is a mock assistant. Supported queries: order status, refund status, return policy."

    return {"message": reply}