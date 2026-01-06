import streamlit as st
import requests
import re
from datetime import datetime
import pytz

API_URL = "http://api:8000/chat"

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
    """)

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
    order_id = re.search(r"\b\d{4,}\b", user_input)
    if any(k in user_input.lower() for k in ["order", "refund", "return"]) and not order_id:
        bot_reply = "❗ Please provide a valid order number (e.g. 12345)."
    else:
        try:
            r = requests.post(API_URL, json={"message": user_input}, timeout=10)
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

    