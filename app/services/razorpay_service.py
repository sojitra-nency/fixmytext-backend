"""Razorpay integration service for payments and subscriptions."""

import hmac
import hashlib
import logging

import razorpay
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: razorpay.Client | None = None
_pro_plan_id: str | None = None

# Pro subscription pricing per region
PRO_PLAN_PRICES = {
    "IN": {"amount": 39900, "currency": "INR"},   # ₹399/mo
    "US": {"amount": 500,   "currency": "USD"},    # $5/mo
    "GB": {"amount": 400,   "currency": "GBP"},    # £4/mo
    "EU": {"amount": 450,   "currency": "EUR"},    # €4.50/mo
}


def init_razorpay():
    """Initialize Razorpay client. Pro plan creation is deferred to first use."""
    global _client
    if not settings.RAZORPAY_KEY_ID:
        return
    _client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def get_client() -> razorpay.Client:
    """Return the Razorpay client instance."""
    if not _client:
        raise RuntimeError("Razorpay not initialized — set RAZORPAY_KEY_ID in .env")
    return _client


def _ensure_pro_plan() -> str:
    """Find or create the Pro monthly subscription plan in Razorpay."""
    # Search existing plans — only catch expected API errors
    try:
        plans = _client.plan.all({"count": 50})
        for plan in plans.get("items", []):
            item = plan.get("item", {})
            if item.get("name") == "FixMyText Pro" and plan.get("period") == "monthly":
                return plan["id"]
    except razorpay.errors.BadRequestError:
        logger.warning("Failed to fetch Razorpay plans, will attempt to create one")

    # Create new plan — let errors propagate so callers know about failures
    plan = _client.plan.create({
        "period": "monthly",
        "interval": 1,
        "item": {
            "name": "FixMyText Pro",
            "amount": PRO_PLAN_PRICES["IN"]["amount"],
            "currency": PRO_PLAN_PRICES["IN"]["currency"],
            "description": "Unlimited access to all 70+ tools. No daily limits.",
        },
    })
    return plan["id"]


def get_pro_plan_id() -> str:
    """Return the Pro plan ID, creating it lazily on first call.
    Raises RuntimeError if plan cannot be found or created."""
    global _pro_plan_id
    if not _pro_plan_id and _client:
        _pro_plan_id = _ensure_pro_plan()
    if not _pro_plan_id:
        raise RuntimeError("Razorpay Pro plan not available — check API credentials and connectivity")
    return _pro_plan_id


# ── One-time payments (passes + credits) ─────────────────────────────────

def create_order(amount: int, currency: str, receipt: str, notes: dict) -> dict:
    """Create a Razorpay order for a one-time payment.
    amount: in smallest currency unit (paise for INR, cents for USD).
    Returns order dict with 'id', 'amount', 'currency'.
    """
    return get_client().order.create({
        "amount": amount,
        "currency": currency.upper(),
        "receipt": receipt,
        "notes": notes,
    })


def fetch_order(order_id: str) -> dict:
    """Fetch order details from Razorpay to validate notes."""
    return get_client().order.fetch(order_id)


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay payment signature. Returns True if valid."""
    try:
        get_client().utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


# ── Subscriptions (Pro) ──────────────────────────────────────────────────

def create_subscription(plan_id: str, customer_email: str, total_count: int = 120) -> dict:
    """Create a Razorpay subscription for Pro.
    total_count: max billing cycles (120 = 10 years).
    Returns subscription dict with 'id', 'short_url'.
    """
    return get_client().subscription.create({
        "plan_id": plan_id,
        "total_count": total_count,
        "notes": {"email": customer_email},
    })


def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a Razorpay subscription."""
    return get_client().subscription.cancel(subscription_id)


def verify_subscription_signature(subscription_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay subscription payment signature."""
    try:
        get_client().utility.verify_subscription_payment_signature({
            "razorpay_subscription_id": subscription_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


# ── Webhook ──────────────────────────────────────────────────────────────

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
