import streamlit as st
import requests

st.set_page_config(page_title="E-Commerce Support Assistant", layout="wide")

st.title("🛒 E-Commerce Customer Support Assistant")

# Chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat history
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["text"])
    else:
        st.chat_message("assistant").write(msg["text"])

# User input
if prompt := st.chat_input("Ask me about your order, returns, refunds..."):
    st.session_state["messages"].append({"role": "user", "text": prompt})
    st.chat_message("user").write(prompt)

    # Very simple routing demo
    if "order" in prompt.lower():
        resp = requests.get("http://api:8000/tools/order/12345/status").json()
        answer = f"Order #{resp['order_id']} is {resp['status']} and will arrive by {resp['expected_delivery']}."
    elif "refund" in prompt.lower():
        resp = requests.get("http://api:8000/tools/refund/98765/status").json()
        answer = f"Refund for order #{resp['order_id']} is {resp['stage']} and expected {resp['timeline']}."
    elif "return" in prompt.lower():
        answer = "To return an item, please provide your order ID and reason."
    else:
        answer = "I can help with orders, returns, and refunds. Could you clarify your request?"

    st.session_state["messages"].append({"role": "assistant", "text": answer})
    st.chat_message("assistant").write(answer)