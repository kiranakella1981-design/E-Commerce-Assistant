from fastapi import FastAPI, HTTPException
import json
import os

app = FastAPI(title="E-Commerce Support Mock Tools")

# Load mock data once at startup

DATA_PATH = "/app/data/mock_tools/mock_responses.json"
with open(DATA_PATH, "r") as f:
    mock_data = json.load(f)

@app.get("/tools/order/{order_id}/status")
def get_order_status(order_id: str):
    """Return mock order status by order_id"""
    if mock_data.get("order_status", {}).get("order_id") == order_id:
        return mock_data["order_status"]
    raise HTTPException(status_code=404, detail="Order not found")


@app.post("/tools/return")
def create_return_request(order_id: str, item_id: str, reason: str):
    """Create a mock return request"""
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
    """Return mock refund status by order_id"""
    if mock_data.get("refund_status", {}).get("order_id") == order_id:
        return mock_data["refund_status"]
    raise HTTPException(status_code=404, detail="Refund not found")