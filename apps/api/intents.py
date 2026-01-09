import re
import logging

logger = logging.getLogger("ecom-chat")

# =========================
# Order Intent Detection
# =========================
STRONG_ORDER_ACTIONS = [
    "track", "tracking",
    "where is", "where's",
    "cancel", "cancelled",
    "refund my", "refund order", "refund status",
    "return my", "return order", "return status", "return request",
    "replace my",
    "order status",
    "shipment status",
]

WEAK_ORDER_ACTIONS = [
    "shipment",
    "delivered",
    "delivery",
    "package",
]


def has_order_id(query: str) -> bool:
    return bool(re.search(r"\b\d{4,}\b", query))

def has_order_action(query: str) -> bool:
    q = query.lower()
    for phrase in STRONG_ORDER_ACTIONS:
        if phrase in q:
            logger.info("[ACTION_MATCH] Strong action detected: %s", phrase)
            return True
    for phrase in WEAK_ORDER_ACTIONS:
        if phrase in q and "my" in q:
            logger.info("[ACTION_MATCH] Weak action detected: %s", phrase)
            return True
    return False

# =========================
# FAQ Detection
# =========================
FAQ_KEYWORDS = {
    "refund": [
        "refund", "refunds", "money back",
        "refund time", "refund status",
        "refund processing time",
    ],

    "return": [
        "return", "returns", "return item",
        "return window", "return period",
        "return eligibility", "return rules",
    ],

    "exchange": [
        "exchange", "replacement", "replace item",
    ],

    "defective": [
        "defective", "damaged", "broken",
        "wrong item", "incorrect item",
    ],

    "exceptions": [
        "exception", "exceptions",
        "excluded", "exclusion",
        "non refundable", "non returnable",
        "final sale", "clearance",
        "special case", "special conditions",
    ],

    "international": [
        "international", "overseas",
        "outside india", "global",
        "remote area", "remote location",
        "cross border",
    ],

    "contact": [
        "contact", "support",
        "customer care", "customer support",
        "helpdesk", "email",
        "phone", "call",
        "live chat",
    ],
    "shipping":[
        "shipping", "delivery",
        "ship", "deliver",
        "shipping time", "delivery time",   
    ],
    "policy": [
        "policy", "terms", "conditions",
        "rules", "guidelines",
    ],
}


def is_faq_intent(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kws in FAQ_KEYWORDS.values() for kw in kws)

def is_policy_query(query: str) -> bool:
    q = query.lower()
    policy_phrases = [
        "return policy",
        "refund policy",
        "exchange policy",
        "exceptions policy",
        "international returns policy",
        "support policy",
        "rules policy",
    ]
    return any(p in q for p in policy_phrases)

# =========================
# Escalation Detection
# =========================
ESCALATION_KEYWORDS = [
    "complaint", "issue not resolved", "escalate", "escalation",
    "agent", "human support", "talk to agent", "customer care",
    "manager", "supervisor", "not happy", "problem persists"
]

def is_escalation_intent(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in ESCALATION_KEYWORDS)

# =========================
# Final Intent Classifier
# =========================
def classify_intent(user_query: str) -> dict:
    q = user_query.lower()

    order_id_present = has_order_id(q)
    order_action_present = has_order_action(q)
    is_order_query = order_id_present and order_action_present

    logger.info(
        "[INTENT_START] query='%s' order_id=%s order_action=%s",
        user_query,
        order_id_present,
        order_action_present,
    )

    # 1️⃣ Order intents
    if is_order_query:
        logger.info("[INTENT] ORDER detected")
        if "refund" in q or "refund status" in q or "refund order" in q:
            logger.info("[INTENT_MATCH] Refund keywords detected")
            return {"intent": "refund_status", "needs_order_id": True}
        if "return" in q or "return status" in q or "return request" in q or "return order" in q:
            logger.info("[INTENT_MATCH] Return keywords detected")
            return {"intent": "return_request", "needs_order_id": True}
        if "track" in q or "where is my order" in q or "order status" in q:
            logger.info("[INTENT_MATCH] Order status keywords detected")
            return {"intent": "order_status", "needs_order_id": True}
        # default order intent
        return {"intent": "order_status", "needs_order_id": True}

    # 2️⃣ Escalation intents
    if is_escalation_intent(q):
        logger.info("[INTENT] ESCALATION detected")
        return {"intent": "escalation", "needs_order_id": True}
    
    # 3️⃣ Shipping intents (FAQ-level, no order ID)
    if any(kw in q for kw in FAQ_KEYWORDS["shipping"]):
        logger.info("[INTENT] SHIPPING detected")
        return {"intent": "shipping", "needs_order_id": False}

    # 4️⃣ FAQ intents
    if is_faq_intent(q):
        logger.info("[INTENT] FAQ detected")
        return {"intent": "faq", "needs_order_id": False}

    # 5️⃣ Fallback
    logger.info("[INTENT] GENERAL fallback")
    return {"intent": "general", "needs_order_id": False}
