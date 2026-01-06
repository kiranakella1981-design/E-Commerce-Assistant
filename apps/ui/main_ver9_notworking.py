import streamlit as st
import re
import requests
from datetime import datetime

API_URL = "http://api:8000/tools"

# ---------------- UTIL ----------------
def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None

def md_to_html_basic(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<a href='\2' target='_blank'>\1</a>", text)
    text = text.replace("\n", "<br>")
    return text

# ---------------- INTENT ----------------
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

# ---------------- HANDLERS ----------------
def handle_order_status(order_id: str):
    r = requests.get(f"{API_URL}/order/{order_id}/status")
    if r.status_code == 200:
        data = r.json()
        return (
            f"👜 Order #{order_id} is {data['status']} and will arrive by {data['expected_delivery']}.\n"
            f"Carrier: {data['carrier']}\n"
            f"[Track your order]({data['tracking_url']})"
        )
    return f"❌ No data found for order #{order_id}."

def handle_refund(order_id: str):
    r = requests.get(f"{API_URL}/refund/{order_id}/status")
    if r.status_code == 200:
        data = r.json()
        return (
            f"🧾 Refund for Order #{order_id} is in **{data['stage']}**.\n"
            f"Amount: {data['amount']} INR\n"
            f"Timeline: {data['timeline']}"
        )
    return f"❌ No refund record found for order #{order_id}."

def handle_return_policy(order_id: str):
    payload = {"order_id": order_id, "item_id": "shoes", "reason": "size issue"}
    r = requests.post(f"{API_URL}/return", params=payload)
    if r.status_code == 200:
        data = r.json()
        return (
            f"📦 Return request for Order #{order_id}:\n"
            f"- Item: {data['item_id']}\n"
            f"- Reason: {data['reason']}\n"
            f"- Method: {data['method']}\n"
            f"[Download return label]({data['label_url']})"
        )
    return f"❌ No return request found for order #{order_id}."

def handle_faq(query: str):
    return "ℹ️ This is a mock assistant. Supported queries: order status, refund status, return policy."

# ---------------- PAGE ----------------
st.set_page_config(page_title="E-Commerce Assistant", layout="centered")
st.title("🛒 E-Commerce Customer Support Assistant")

with st.sidebar:
    st.header("📖 How to Use")
    st.markdown("""
    - Enter your query in the text box below.
    - Supported queries:
        * Order status (e.g., "Where is my order 12345?")
        * Refund status (e.g., "Help me with refund for 98765")
        * Return policy (e.g., "I want to return order 98765")
    """)

# ---------------- STATE ----------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------- STYLES ----------------
st.markdown("""
<style>
.chat-box {
    height: 400px;
    overflow-y: auto;
    border: 1px solid #444;
    padding: 10px;
    background: #1e1e1e;
    color: #ddd;
}
.user-msg, .bot-msg {
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 8px;
    word-wrap: break-word;
    overflow-wrap: anywhere;
}
.user-msg {
    background: #2e8b57;
    color: #fff;
}
.bot-msg {
    background: #4682b4;
    color: #fff;
}
.stChatInput {
    position: sticky;
    bottom: 0;
    background: #0e1117;
    padding-top: 6px;
    z-index: 100;
}
</style>
""", unsafe_allow_html=True)

# ---------------- CHAT RENDER ----------------
def render_chat(history):
    html = '<div id="chat-box" class="chat-box">'
    for msg in history:
        html += f"""
        <div class="user-msg">
            <strong>👤 You</strong>
            <span style="opacity:.6;font-size:.8em">({msg['time']})</span><br>
            {md_to_html_basic(msg['query'])}
        </div>
        <div class="bot-msg">
            <strong>🤖 Assistant</strong>
            <span style="opacity:.6;font-size:.8em">({msg['time']})</span><br>
            {md_to_html_basic(msg['response'])}
        </div>
        """
    html += "</div>"
    html += """
    <script>
        const chat = document.getElementById("chat-box");
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---------------- INPUT ----------------
user_query = st.chat_input("💬 Type your query here...")

if user_query:
    intent = classify_intent(user_query)
    order_id = extract_order_id(user_query)

    if intent in {"order_status", "refund_status", "return_policy"} and not order_id:
        response = "❗ Please provide a valid order number (e.g., 98765)."
    else:
        if intent == "order_status":
            response = handle_order_status(order_id)
        elif intent == "refund_status":
            response = handle_refund(order_id)
        elif intent == "return_policy":
            response = handle_return_policy(order_id)
        else:
            response = handle_faq(user_query)

    st.session_state.chat_history.append({
        "query": user_query,
        "response": response,
        "time": datetime.now().strftime("%H:%M"),
    })

# ---------------- RENDER ----------------
render_chat(st.session_state.chat_history)