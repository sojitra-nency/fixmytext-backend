"""Subscription endpoints: status, checkout (Pro), verify, cancel, webhook."""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models import User
from app.db.models.billing_subscription import Subscription
from app.db.session import get_db
from app.schemas.subscription import (
    RazorpayProOrderResponse,
    RazorpayProVerifyRequest,
    SubscriptionStatus,
)
from app.services.pass_service import (
    get_active_passes,
    get_all_tool_uses_today,
    get_credit_balance,
    get_subscription_tier,
    has_logged_in_today,
    record_daily_login,
)
from app.services.razorpay_service import (
    PRO_PLAN_PRICES,
    create_order,
    fetch_order,
    verify_payment_signature,
    verify_webhook_signature,
)
from app.services.region_service import resolve_user_region

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


# ── Status ────────────────────────────────────────────────────────────


@router.get("/status", response_model=SubscriptionStatus)
async def subscription_status(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's subscription status, usage, and pass/credit info."""

    if not user.region:
        await resolve_user_region(user, request, db)
        await db.commit()

    tool_uses = await get_all_tool_uses_today(user.id, db)

    daily_bonus = await has_logged_in_today(user.id, db)
    if not daily_bonus:
        await record_daily_login(user, db)
        daily_bonus = True

    credit_balance = await get_credit_balance(user, db)
    active_passes = await get_active_passes(user, db)

    return SubscriptionStatus(
        tier=await get_subscription_tier(user.id, db),
        tool_uses_today=tool_uses,
        free_uses_per_tool=settings.FREE_USES_PER_TOOL_PER_DAY,
        daily_login_bonus=daily_bonus,
        credit_balance=credit_balance,
        active_passes_count=len(active_passes),
        region=user.region,
    )


# ── Pro Checkout (create Razorpay order — one-time payment) ─────────────────


@router.post("/checkout", response_model=RazorpayProOrderResponse)
async def create_pro_checkout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for upgrading to Pro (one-time monthly payment)."""
    if not settings.RAZORPAY_KEY_ID:
        raise HTTPException(503, "Payments not configured")

    if await get_subscription_tier(user.id, db) == "pro":
        raise HTTPException(400, "Already subscribed to Pro")

    region = user.region or "IN"
    pricing = PRO_PLAN_PRICES.get(region, PRO_PLAN_PRICES["IN"])

    try:
        order = create_order(
            amount=pricing["amount"],
            currency=pricing["currency"],
            receipt=f"pro_{str(user.id)[:8]}",
            notes={"user_id": str(user.id), "item_type": "pro_subscription"},
        )
    except Exception as e:
        logger.exception("Failed to create Razorpay order for Pro checkout, user %s", user.id)
        raise HTTPException(502, "Failed to start checkout — please try again later") from e

    return RazorpayProOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
        user_email=user.email,
        user_name=user.display_name,
    )


# ── Verify Pro Payment ────────────────────────────────────────────────


@router.post("/verify")
async def verify_pro_payment(
    req: RazorpayProVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment and activate Pro."""
    if not verify_payment_signature(req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature):
        raise HTTPException(400, "Payment verification failed — invalid signature")

    # Validate order belongs to this user
    try:
        order = fetch_order(req.razorpay_order_id)
    except Exception as e:
        logger.exception("Failed to fetch order %s", req.razorpay_order_id)
        raise HTTPException(502, "Could not verify order details") from e

    notes = order.get("notes", {})
    if notes.get("user_id") != str(user.id):
        raise HTTPException(400, "Order does not belong to this user")
    if notes.get("item_type") != "pro_subscription":
        raise HTTPException(400, "Order is not for Pro subscription")

    # Create/update Subscription row in billing schema
    sub = Subscription(
        user_id=user.id,
        tier="pro",
        status="active",
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        amount_paid_subunits=order.get("amount"),
        currency=order.get("currency"),
        region=user.region,
    )
    db.add(sub)

    await db.commit()
    logger.info("Pro activated: user=%s order=%s payment=%s", user.id, req.razorpay_order_id, req.razorpay_payment_id)
    return {"status": "success", "tier": "pro"}


# ── Cancel Pro ────────────────────────────────────────────────────────


@router.post("/cancel")
async def cancel_pro(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel Pro subscription (immediate downgrade)."""
    tier = await get_subscription_tier(user.id, db)
    if tier != "pro":
        raise HTTPException(400, "No active Pro subscription")

    # Update Subscription row
    sub_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == user.id,
                Subscription.status == "active",
                Subscription.tier == "pro",
            )
        )
    )
    active_sub = sub_result.scalars().first()
    if active_sub:
        active_sub.status = "cancelled"
        active_sub.cancelled_at = datetime.now(UTC)

    await db.commit()
    return {"status": "cancelled"}


# ── Webhook ───────────────────────────────────────────────────────────


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhook events for payments."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(503, "Webhook secret not configured")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(400, "Invalid webhook signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "Invalid payload") from e

    event_type = event.get("event", "")
    payload = event.get("payload", {})

    if event_type == "payment.captured":
        payment_id = payload.get("payment", {}).get("entity", {}).get("id", "unknown")
        logger.info("payment.captured webhook received: payment=%s", payment_id)

    return {"status": "ok"}
