import streamlit as st
import json

DATA_PATH = "/app/data/mock_tools/mock_responses.json"

def load_json(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return {}

mock_data = load_json(DATA_PATH)

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

st.set_page_config(page_title="E-Commerce Assistant", layout="centered")
st.title("🛒 E-Commerce Customer Support Assistant")

# Sidebar instructions
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

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Scrollable dark chat window
with st.container():
    st.markdown(
        """
        <div style='height:400px; overflow-y:auto; border:1px solid #444; padding:10px; background:#1e1e1e; color:#ddd;'>
        """,
        unsafe_allow_html=True,
    )
    for query, resp in reversed(st.session_state.chat_history):
        st.markdown(f"<div style='background:#2e8b57; padding:6px; border-radius:6px; color:#fff;'><strong>👤 You:</strong> {query}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#4682b4; padding:6px; border-radius:6px; color:#fff;'><strong>🤖 Assistant:</strong> {resp}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#555;'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Prompt box at bottom
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

    st.session_state.chat_history.append((user_query, response))

if st.checkbox("Show raw mock data"):
    st.json(mock_data)