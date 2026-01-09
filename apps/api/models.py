from pydantic import BaseModel
from typing import List

# =========================
# Request Models
# =========================
class ChatRequest(BaseModel):
    message: str

# --- Pydantic Models ---
class Item(BaseModel):
    sku: str
    name: str
    qty: int

class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    estimated_delivery: str
    items: List[Item]

class RefundResponse(BaseModel):
    order_id: str
    status: str
    amount: float | None = None

class ReturnResponse(BaseModel):
    order_id: str
    item_id: str
    reason: str
    method: str

class EscalationResponse(BaseModel):
    ticket_id: str
    status: str
    assigned_to: str
