"""Subscription endpoints: status, checkout (Pro), verify, cancel, webhook."""

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User
from app.schemas.subscription import (
    SubscriptionStatus, RazorpaySubscriptionResponse, RazorpaySubVerifyRequest,
)
from app.services.razorpay_service import (
    create_subscription, get_pro_plan_id, verify_subscription_signature,
    cancel_subscription, verify_webhook_signature,
)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


# ── Status ──────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SubscriptionStatus)
async def subscription_status(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's subscription status, usage, and pass/credit info."""
    from app.services.pass_service import get_credit_balance, get_active_passes, record_daily_login
    from app.services.region_service import resolve_user_region

    if not user.region:
        await resolve_user_region(user, request, db)
        await db.commit()

    today = date.today().isoformat()
    tool_uses = user.tool_uses_today if user.tool_uses_reset_date == today else {}

    daily_bonus = user.daily_login_date == today
    if not daily_bonus:
        await record_daily_login(user, db)
        daily_bonus = True

    credit_balance = await get_credit_balance(user, db)
    active_passes = await get_active_passes(user, db)

    return SubscriptionStatus(
        tier=user.subscription_tier or "free",
        tool_uses_today=tool_uses,
        free_uses_per_tool=settings.FREE_USES_PER_TOOL_PER_DAY,
        daily_login_bonus=daily_bonus,
        credit_balance=credit_balance,
        active_passes_count=len(active_passes),
        region=user.region,
        razorpay_subscription_id=str(user.razorpay_subscription_id) if user.razorpay_subscription_id else None,
    )


# ── Pro Checkout (create Razorpay subscription) ─────────────────────────────

@router.post("/checkout", response_model=RazorpaySubscriptionResponse)
async def create_pro_checkout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay subscription for upgrading to Pro."""
    if not settings.RAZORPAY_KEY_ID:
        raise HTTPException(503, "Payments not configured")

    if user.subscription_tier == "pro":
        raise HTTPException(400, "Already subscribed to Pro")

    plan_id = get_pro_plan_id()
    if not plan_id:
        raise HTTPException(503, "Pro plan not available")

    sub = create_subscription(plan_id, user.email)
    return RazorpaySubscriptionResponse(
        subscription_id=sub["id"],
        key_id=settings.RAZORPAY_KEY_ID,
        user_email=user.email,
        user_name=user.display_name,
    )


# ── Verify Pro Subscription Payment ─────────────────────────────────────────

@router.post("/verify")
async def verify_pro_payment(
    req: RazorpaySubVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay subscription payment and activate Pro."""
    if not verify_subscription_signature(req.razorpay_subscription_id, req.razorpay_payment_id, req.razorpay_signature):
        raise HTTPException(400, "Subscription verification failed")

    user.subscription_tier = "pro"
    user.razorpay_subscription_id = req.razorpay_subscription_id
    await db.commit()
    logger.info("Pro activated: user=%s sub=%s payment=%s", user.id, req.razorpay_subscription_id, req.razorpay_payment_id)
    return {"status": "success", "tier": "pro"}


# ── Cancel Pro ───────────────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_pro(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel Pro subscription."""
    if not user.razorpay_subscription_id:
        raise HTTPException(400, "No active subscription")

    try:
        cancel_subscription(str(user.razorpay_subscription_id))
    except Exception:
        logger.warning("Razorpay cancel failed for sub %s, user %s", user.razorpay_subscription_id, user.id, exc_info=True)

    user.subscription_tier = "free"
    user.razorpay_subscription_id = None
    await db.commit()
    return {"status": "cancelled"}


# ── Webhook ──────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhook events for subscriptions and payments."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(503, "Webhook secret not configured")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(400, "Invalid webhook signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid payload")

    event_type = event.get("event", "")
    payload = event.get("payload", {})

    if event_type == "subscription.charged":
        # Renewal — keep Pro active
        sub_entity = payload.get("subscription", {}).get("entity", {})
        await _handle_subscription_active(db, sub_entity)

    elif event_type in ("subscription.cancelled", "subscription.halted"):
        sub_entity = payload.get("subscription", {}).get("entity", {})
        await _handle_subscription_ended(db, sub_entity)

    elif event_type == "payment.captured":
        # One-time payments are verified via /passes/verify — log for audit trail only
        payment_id = payload.get("payment", {}).get("entity", {}).get("id", "unknown")
        logger.info("payment.captured webhook received: payment=%s (no action needed)", payment_id)

    return {"status": "ok"}


async def _handle_subscription_active(db: AsyncSession, sub: dict):
    """Keep Pro tier active on subscription renewal."""
    sub_id = sub.get("id")
    if not sub_id:
        logger.warning("subscription.charged webhook missing subscription ID in payload")
        return

    result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
    user = result.scalars().first()
    if user:
        user.subscription_tier = "pro"
        await db.commit()


async def _handle_subscription_ended(db: AsyncSession, sub: dict):
    """Downgrade user when subscription ends."""
    sub_id = sub.get("id")
    if not sub_id:
        logger.warning("subscription.cancelled/halted webhook missing subscription ID in payload")
        return

    result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
    user = result.scalars().first()
    if user:
        user.subscription_tier = "free"
        user.razorpay_subscription_id = None
        await db.commit()
