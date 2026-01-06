import streamlit as st
import json
import re
import time
from datetime import datetime
import markdown  # <-- added for Markdown to HTML conversion

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

# ---------------- UTIL / GUARDS ----------------
def extract_order_id(text: str) -> str | None:
    """Extract the first numeric order id (4+ digits)"""
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None

def validate_order_id(order_id: str) -> bool:
    """Ensure order ID is numeric and non-empty"""
    return bool(order_id) and order_id.isdigit()

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

# ---------------- MOCK HANDLERS ----------------
def handle_order_status(order_id: str):
    data = mock_data.get("order_status", {})
    if str(data.get("order_id")) == str(order_id):
        return (
            f"👜 Order #{order_id} is {data['status']} and will arrive by {data['expected_delivery']}.\n\n"
            f"Carrier: {data['carrier']}\n"
            f"[Track your order]({data['tracking_url']})"
        )
    return f"❌ No data found for order #{order_id}."

def handle_refund(order_id: str):
    data = mock_data.get("refund_status", {})
    if str(data.get("order_id")) == str(order_id):
        return (
            f"💸 Refund for Order #{order_id} is in **{data['stage']}**.\n\n"
            f"Amount: {data['amount']}\n"
            f"Timeline: {data['timeline']}"
        )
    return f"❌ No refund record found for order #{order_id}."

def handle_return_policy(order_id: str):
    data = mock_data.get("return_request", {})
    if str(data.get("order_id")) == str(order_id):
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
def stream_text(text: str, delay: float = 0.015):
    """Stream text token by token in Streamlit."""
    placeholder = st.empty()
    rendered = ""
    for token in text.split():
        rendered += token + " "
        placeholder.markdown(rendered, unsafe_allow_html=True)
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
    """)

# ---------------- STATE ----------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "llm_stream" not in st.session_state:
    st.session_state.llm_stream = False  # placeholder flag for streaming LLM

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
    margin-bottom: 6px;
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
        # User message
        html += f"""
        <div class="user-msg">
            <strong>👤 You</strong>
            <span style="opacity:.6;font-size:.8em">({msg['time']})</span><br>
            {msg['query']}
        </div>
        """
        # Bot message
        response_html = markdown.markdown(msg['response'], extensions=["extra"])
        html += f"""
        <div class="bot-msg">
            <strong>🤖 Assistant</strong>
            <span style="opacity:.6;font-size:.8em">({msg['time']})</span><br>
            {response_html}
        </div>
        """
    html += "</div>"

    # Auto-scroll
    html += """
    <script>
        const chat = document.getElementById("chat-box");
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---------------- LLM / MOCK INTERFACE ----------------
def get_assistant_response(user_query: str) -> str:
    """Return mock assistant response"""
    intent = classify_intent(user_query)
    order_id = extract_order_id(user_query)

    if intent in {"order_status", "refund_status", "return_policy"} and not order_id:
        return "❗ Please provide a valid order number (e.g., 98765)."

    if intent == "order_status":
        return handle_order_status(order_id)
    elif intent == "refund_status":
        return handle_refund(order_id)
    elif intent == "return_policy":
        return handle_return_policy(order_id)
    else:
        return handle_faq(user_query)

# ---------------- INPUT ----------------
user_query = st.chat_input("💬 Type your query here...")

if user_query:
    response = get_assistant_response(user_query)
    st.session_state.chat_history.append({
        "query": user_query,
        "response": response,
        "time": datetime.now().strftime("%H:%M"),
    })

# Render chat
render_chat(st.session_state.chat_history)

# ---------------- DEBUG ----------------
if st.checkbox("Show raw mock data"):
    st.json(mock_data)
