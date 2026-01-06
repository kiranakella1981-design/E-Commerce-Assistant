"""
E-Commerce Customer Support Assistant (Streamlit UI)

Usage:
- Ask about your order status, refunds, or return policies.
- The assistant will route your query to the appropriate mock tool or FAQ.
- All data is synthetic and baked into the container for portability.

Deployment:
- Run via Docker Compose from project root.
- Access UI at http://localhost:8501
"""

import streamlit as st
import json
import os

# -------------------------------------------------------------------
# Load mock data baked into the container
# -------------------------------------------------------------------
DATA_PATH = "/app/data/mock_tools/mock_responses.json"
FAQ_PATH = "/app/data/policies/faqs.json"

def load_json(path: str):
    """Utility to safely load JSON files."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load {path}: {e}")
        return {}

mock_data = load_json(DATA_PATH)
faq_data = load_json(FAQ_PATH)

# -------------------------------------------------------------------
# Intent classification (basic rule-based for now)
# -------------------------------------------------------------------
def classify_intent(user_query: str) -> str:
    """Classify query into order_status, refund_status, return_policy, or faq."""
    q = user_query.lower()
    if "order" in q:
        return "order_status"
    elif "refund" in q:
        return "refund_status"
    elif "return" in q:
        return "return_policy"
    else:
        return "faq"

# -------------------------------------------------------------------
# Handlers for each intent
# -------------------------------------------------------------------
def handle_order_status(order_id: str):
    """Retrieve order status from mock data."""
    for entry in mock_data.get("orders", []):
        if entry["order_id"] == order_id:
            return f"👜 Order #{order_id} is {entry['status']} and will arrive by {entry['expected_delivery']}."
    return f"❌ No data found for order #{order_id}."

def handle_refund(order_id: str):
    """Retrieve refund status from mock data."""
    for entry in mock_data.get("refunds", []):
        if entry["order_id"] == order_id:
            return f"💸 Refund for Order #{order_id} is {entry['stage']} (timeline: {entry['timeline']})."
    return f"❌ No refund record found for order #{order_id}."

def handle_return_policy():
    """Return policy from FAQ data."""
    return faq_data.get("return_policy", "Sorry, return policy not available.")

def handle_faq(query: str):
    """Fallback FAQ lookup (naive)."""
    return faq_data.get("general", "Sorry, I couldn't find an answer.")

# -------------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------------
st.title("🛒 E-Commerce Customer Support Assistant")

# Sidebar instructions
with st.sidebar:
    st.header("📖 How to Use")
    st.markdown("""
    - Enter your query in the text box below.
    - Supported queries:
        * Order status (e.g., "Where is my order 12345?")
        * Refund status (e.g., "Help me with refund for 98765")
        * Return policy (e.g., "What is the return policy?")
        * General FAQs
    - All responses are mock data baked into the container.
    """)

# Input box
user_query = st.text_input("💬 Enter your query:")

if user_query:
    intent = classify_intent(user_query)
    st.write(f"🔎 Detected intent: **{intent}**")

    if intent == "order_status":
        # Extract order ID (naive: last number in query)
        order_id = "".join([c for c in user_query if c.isdigit()])
        response = handle_order_status(order_id)
    elif intent == "refund_status":
        order_id = "".join([c for c in user_query if c.isdigit()])
        response = handle_refund(order_id)
    elif intent == "return_policy":
        response = handle_return_policy()
    else:
        response = handle_faq(user_query)

    st.success(response)

# Debug toggle
if st.checkbox("Show raw mock data"):
    st.json(mock_data)
    st.json(faq_data)