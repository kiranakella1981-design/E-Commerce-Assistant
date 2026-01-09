import re

def extract_order_id(text: str) -> str | None:
    """
    Extracts an order ID (4+ digit number) from user text.
    """
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None


def find_record(records, order_id: str):
    """
    Finds a record in a list of dicts by order_id or ticket_id.
    """
    for rec in records:
        if str(rec.get("order_id")) == str(order_id) or str(rec.get("ticket_id")) == f"TKT-{order_id}":
            return rec
    return None