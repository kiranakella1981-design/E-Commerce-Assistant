import streamlit as st
import json
import time
from datetime import datetime

DATA_PATH = "/app/data/mock_tools/mock_responses.json"

# ---------------- DATA ----------------
def load_json(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return {}

mock_data = load_json(DATA_PATH)

# ---------------- INTENT ----------------
def classify_intent(user_query: str) -> str:
    q = user_query.lower()
    if "order" in q:
        return "order_status"
    elif "refund" in q:
        return "refund_status"
    elif "return" in q:
        return "return_policy"
    else:
        return "faq"

def handle_order_status(order_id: str):
    data = mock_data.get("order_status", {})
    if data.get("order_id") == order_id:
        return (
            f"👜 Order #{order_id} is {data['status']} and will arrive by {data['expected_delivery']}.\n"
            f"Carrier: {data['carrier']}\n"
            f"[Track your order]({data['tracking_url']})"
        )
    return f"❌ No data found for order #{order_id}."

def handle_refund(order_id: str):
    data = mock_data.get("refund_status", {})
    if data.get("order_id") == order_id:
        return (
            f"💸 Refund for Order #{order_id} is in **{data['stage']}**.\n"
            f"Amount: {data['amount']}\n"
            f"Timeline: {data['timeline']}"
        )
    return f"❌ No refund record found for order #{order_id}."

def handle_return_policy(order_id: str):
    data = mock_data.get("return_request", {})
    if data.get("order_id") == order_id:
        return (
            f"🔄 Return request for Order #{order_id}:\n"
            f"- Item: {data['item_id']}\n"
            f"- Reason: {data['reason']}\n"
            f"- Method: {data['method']}\n"
            f"[Download return label]({data['label_url']})"
        )
    return f"❌ No return request found for order #{order_id}."

def handle_faq(query: str):
    return "ℹ️ This is a mock assistant. Supported queries: order status, refund status, return policy."

# ---------------- STREAMING ----------------
def stream_text(text, delay=0.03):
    placeholder = st.empty()
    rendered = ""
    for token in text.split():
        rendered += token + " "
        placeholder.markdown(rendered)
        time.sleep(delay)

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
    - All responses are mock data baked into the container.
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

.user-msg {
    background: #2e8b57;
    padding: 10px;
    border-radius: 10px;
    color: #fff;
    margin-bottom: 8px;
}

.bot-msg {
    background: #4682b4;
    padding: 10px;
    border-radius: 10px;
    color: #fff;
    margin-bottom: 14px;
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

# ---------------- CHAT WINDOW ----------------
st.markdown('<div id="chat-box" class="chat-box">', unsafe_allow_html=True)

for msg in st.session_state.chat_history:
    st.markdown(
        f"<div class='user-msg'><strong>👤 You</strong> "
        f"<span style='opacity:.6;font-size:.8em'>({msg['time']})</span><br>{msg['query']}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='bot-msg'><strong>🤖 Assistant</strong> "
        f"<span style='opacity:.6;font-size:.8em'>({msg['time']})</span></div>",
        unsafe_allow_html=True,
    )
    stream_text(msg["response"])

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- AUTO SCROLL + INDICATOR ----------------
st.markdown("""
<div id="new-msg" style="
    display:none;
    position:fixed;
    bottom:90px;
    right:20px;
    background:#ff4b4b;
    color:white;
    padding:6px 10px;
    border-radius:20px;
    font-size:14px;
">
New messages ↓
</div>

<script>
const chat = window.parent.document.getElementById("chat-box");
const indicator = window.parent.document.getElementById("new-msg");

if (chat) {
  const atBottom =
    chat.scrollHeight - chat.scrollTop - chat.clientHeight < 20;

  if (!atBottom) {
    indicator.style.display = "block";
  } else {
    indicator.style.display = "none";
  }

  chat.scrollTop = chat.scrollHeight;
}
</script>
""", unsafe_allow_html=True)

# ---------------- INPUT ----------------
user_query = st.chat_input("💬 Type your query here...")

if user_query:
    intent = classify_intent(user_query)
    order_id = "".join([c for c in user_query if c.isdigit()])

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
    st.rerun()

# ---------------- DEBUG ----------------
if st.checkbox("Show raw mock data"):
    st.json(mock_data)
