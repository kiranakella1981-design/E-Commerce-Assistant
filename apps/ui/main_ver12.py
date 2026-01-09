import streamlit as st
import requests
import re
from datetime import datetime
import pytz

API_BASE = "http://api:8000"

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="E-Commerce Assistant", layout="centered")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("🛒 E-Commerce Customer Support Assistant")
    st.header("📖 How to use")
    st.markdown("""
    Ask things like:
    - **Where is my order 12345**
    - **Refund status for 98765**
    - **Return order 55555**
    - **Escalate issue for 44444**
    """)
    st.divider()
    st.subheader("⚙️ Admin")
    if st.button("Reload FAQ"):
        try:
            r = requests.post(f"{API_BASE}/reload_faq", timeout=10)
            st.success(r.json()["message"])
        except Exception as e:
            st.error(f"⚠️ Backend error: {e}")

# ---------------- STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- CHAT DISPLAY ----------------
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(
                f"{msg['content']}\n\n"
                f"<span style='font-size:0.75em;opacity:0.6'>{msg['time']}</span>",
                unsafe_allow_html=True
            )

# ---------------- INPUT ----------------
user_input = st.chat_input("💬 Type your message")

if user_input:
    # --- USER MESSAGE ---
    ist = pytz.timezone("Asia/Kolkata")
    timestamp = datetime.now(ist).strftime("%H:%M")

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": timestamp,
    })

    # --- GUARDS ---
    order_id = re.search(r"\b\d{4,}\b", user_input.lower())
    transaction_triggers = [
        "where is my order",
        "order status",
        "track my order",
        "refund status",
        "return status",
        "return for order",
        "escalate issue",
    ]

    if any(t in user_input.lower() for t in transaction_triggers) and not order_id:
        bot_reply = "❗ Please provide a valid order number (e.g. 12345)."
    else:
        try:
            r = requests.post(f"{API_BASE}/chat", json={"message": user_input}, timeout=10)
            r.raise_for_status()
            bot_reply = r.json()["message"]
        except Exception as e:
            bot_reply = f"⚠️ Backend error: {e}"

    # --- BOT MESSAGE ---
    st.session_state.messages.append({
        "role": "assistant",
        "content": bot_reply,
        "time": datetime.now(ist).strftime("%H:%M"),
    })

    st.rerun()

# ---------------- TESTING MOCK ENDPOINTS ----------------
st.divider()
st.subheader("🔍 Direct Endpoint Testing")

order_id_input = st.text_input("Enter Order ID for testing", key="order_id_input")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("Check Order"):
        try:
            r = requests.get(f"{API_BASE}/order/{order_id_input}", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"⚠️ Backend error: {e}")

with col2:
    if st.button("Refund Order"):
        try:
            r = requests.post(f"{API_BASE}/refund/{order_id_input}", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"⚠️ Backend error: {e}")

with col3:
    if st.button("Return Order"):
        try:
            r = requests.post(f"{API_BASE}/return/{order_id_input}", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"⚠️ Backend error: {e}")

with col4:
    if st.button("Escalate Issue"):
        try:
            r = requests.post(f"{API_BASE}/escalate/{order_id_input}", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"⚠️ Backend error: {e}")
