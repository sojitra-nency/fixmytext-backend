"""Pass & credit endpoints: catalog, active, order, verify, spin, referral."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.pass_catalog import (
    CREDIT_PACKS,
    DEFAULT_REGION,
    PASSES,
    REGIONS,
    get_credit_pack,
    get_currency,
    get_pass,
    get_price,
    get_symbol,
)
from app.db.models import BillingUserCredit, User
from app.db.session import get_db
from app.schemas.passes import (
    ActiveCredit,
    ActivePass,
    ActiveResponse,
    CatalogResponse,
    ClaimReferralRequest,
    CreditOrderRequest,
    CreditPackItem,
    PassCatalogItem,
    PassOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerifyRequest,
    ReferralCodeResponse,
    SpinResult,
)
from app.services.pass_service import (
    claim_referral,
    ensure_referral_code,
    get_active_credits,
    get_active_passes,
    get_credit_balance,
    grant_credits,
    grant_pass,
    spin_wheel,
)
from app.services.razorpay_service import create_order, fetch_order, verify_payment_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passes", tags=["Passes"])


# ── Catalog ─────────────────────────────────────────────────────────────


@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog(request: Request, region: str = ""):
    """Return all available passes and credit packs with regional pricing.
    Auto-detects region from IP if not provided."""
    if not region or region not in REGIONS:
        from app.services.region_service import detect_region

        ip = request.client.host if request.client else ""
        region = await detect_region(ip)
    if region not in REGIONS:
        region = DEFAULT_REGION

    currency = get_currency(region)
    symbol = get_symbol(region)

    passes = [
        PassCatalogItem(
            id=p["id"],
            name=p["name"],
            subtitle=p["subtitle"],
            tools=p["tools"],
            uses_per_day=p["uses_per_day"],
            duration_days=p["duration_days"],
            price=get_price(p["id"], region),
            currency=currency,
            symbol=symbol,
        )
        for p in PASSES
    ]

    credit_packs = [
        CreditPackItem(
            id=c["id"],
            name=c["name"],
            credits=c["credits"],
            price=get_price(c["id"], region),
            currency=currency,
            symbol=symbol,
        )
        for c in CREDIT_PACKS
    ]

    return CatalogResponse(passes=passes, credit_packs=credit_packs, region=region)


# ── Active Passes & Credits ────────────────────────────────────────────────


@router.get("/active", response_model=ActiveResponse)
async def get_active(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return user's active passes and credit balance."""
    passes = await get_active_passes(user, db)
    credits = await get_active_credits(user, db)
    total = await get_credit_balance(user, db)

    return ActiveResponse(
        passes=[
            ActivePass(
                id=str(p.id),
                pass_id=p.pass_id,
                name=(get_pass(p.pass_id) or {}).get("name", p.pass_id),
                tool_ids=[t.tool_id for t in p.tools] if hasattr(p, "tools") else (p.tool_ids or []),
                tools_count=p.tools_count,
                uses_per_day=p.uses_per_day,
                uses_today=p.uses_today,
                expires_at=p.expires_at,
                source=p.source,
            )
            for p in passes
        ],
        credits=[
            ActiveCredit(
                id=str(c.id),
                credits_remaining=c.credits_remaining,
                credits_total=c.credits_total,
                source=c.source,
            )
            for c in credits
        ],
        total_credits=total,
    )


# ── Razorpay: Create Order (pass) ──────────────────────────────────────────


@router.post("/order", response_model=RazorpayOrderResponse)
async def create_pass_order(
    req: PassOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for purchasing a pass."""
    if not settings.RAZORPAY_KEY_ID:
        raise HTTPException(503, "Payments not configured")

    pass_def = get_pass(req.pass_id)
    if not pass_def:
        raise HTTPException(400, f"Unknown pass: {req.pass_id}")

    from app.services.region_service import resolve_user_region

    region = await resolve_user_region(user, None, db, explicit_region=req.region)
    if user in db.dirty:
        await db.commit()
    amount = get_price(req.pass_id, region)
    currency = get_currency(region)

    order = create_order(
        amount=amount,
        currency=currency,
        receipt=f"pass_{req.pass_id}_{str(user.id)[:8]}",
        notes={
            "user_id": str(user.id),
            "item_id": req.pass_id,
            "item_type": "pass",
            "tool_ids": ",".join(req.tool_ids),
        },
    )
    return RazorpayOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
        user_email=user.email,
        user_name=user.display_name,
    )


# ── Razorpay: Create Order (credits) ───────────────────────────────────────


@router.post("/credit-order", response_model=RazorpayOrderResponse)
async def create_credit_order(
    req: CreditOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay order for purchasing credits."""
    if not settings.RAZORPAY_KEY_ID:
        raise HTTPException(503, "Payments not configured")

    pack = get_credit_pack(req.pack_id)
    if not pack:
        raise HTTPException(400, f"Unknown credit pack: {req.pack_id}")

    from app.services.region_service import resolve_user_region

    region = await resolve_user_region(user, None, db, explicit_region=req.region)
    if user in db.dirty:
        await db.commit()
    amount = get_price(req.pack_id, region)
    currency = get_currency(region)

    order = create_order(
        amount=amount,
        currency=currency,
        receipt=f"credit_{req.pack_id}_{str(user.id)[:8]}",
        notes={"user_id": str(user.id), "item_id": req.pack_id, "item_type": "credit"},
    )
    return RazorpayOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
        user_email=user.email,
        user_name=user.display_name,
    )


# ── Razorpay: Verify Payment ───────────────────────────────────────────────


@router.post("/verify")
async def verify_pass_payment(
    req: RazorpayVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment signature and grant pass/credits."""
    if not verify_payment_signature(req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature):
        raise HTTPException(400, "Payment verification failed — invalid signature")

    # Validate order details match what was originally requested (prevents item swap fraud)
    try:
        order = fetch_order(req.razorpay_order_id)
    except Exception as e:
        logger.exception("Failed to fetch Razorpay order %s", req.razorpay_order_id)
        raise HTTPException(502, "Could not verify order details with payment provider") from e
    notes = order.get("notes", {})
    if notes.get("item_id") != req.item_id or notes.get("item_type") != req.item_type:
        raise HTTPException(400, "Order details do not match — item_id or item_type mismatch")
    if notes.get("user_id") != str(user.id):
        raise HTTPException(400, "Order does not belong to this user")

    # Lock user row first to ensure atomicity for grant + welcome gift
    await db.execute(select(User).where(User.id == user.id).with_for_update())

    if req.item_type == "pass":
        pass_def = get_pass(req.item_id)
        if not pass_def:
            raise HTTPException(400, f"Unknown pass: {req.item_id}")
        tool_ids = req.tool_ids if req.tool_ids else ["*"]
        await grant_pass(
            user, req.item_id, tool_ids, "razorpay", db, razorpay_payment_id=req.razorpay_payment_id, auto_commit=False
        )
        safe_item_id = str(req.item_id).replace("\r", "").replace("\n", "")
        safe_payment_id = str(req.razorpay_payment_id).replace("\r", "").replace("\n", "")
        logger.info("Pass granted: user=%s pass=%s payment=%s", user.id, safe_item_id, safe_payment_id)

    elif req.item_type == "credit":
        pack = get_credit_pack(req.item_id)
        if not pack:
            raise HTTPException(400, f"Unknown credit pack: {req.item_id}")
        await grant_credits(
            user, pack["credits"], "purchase", db, razorpay_payment_id=req.razorpay_payment_id, auto_commit=False
        )
        safe_item_id = str(req.item_id).replace("\r", "").replace("\n", "")
        safe_payment_id = str(req.razorpay_payment_id).replace("\r", "").replace("\n", "")
        logger.info(
            "Credits granted: user=%s pack=%s credits=%d payment=%s",
            user.id,
            safe_item_id,
            pack["credits"],
            safe_payment_id,
        )

    # First purchase welcome gift (idempotent — user row already locked above)
    already_welcomed = await db.execute(
        select(func.count()).where(BillingUserCredit.user_id == user.id, BillingUserCredit.source == "welcome")
    )
    if already_welcomed.scalar() == 0:
        await grant_credits(user, 10, "welcome", db, auto_commit=False)
        logger.info("Welcome gift granted: user=%s", user.id)

    await db.commit()
    return {"status": "success"}


# ── Spin the Wheel ─────────────────────────────────────────────────────────


@router.post("/spin", response_model=SpinResult)
async def do_spin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Spin the weekly wheel for a random reward."""
    result = await spin_wheel(user, db)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return SpinResult(**result)


# ── Referral ───────────────────────────────────────────────────────────────


@router.get("/referral-code", response_model=ReferralCodeResponse)
async def get_referral_code(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get or generate the user's referral code."""
    code = await ensure_referral_code(user, db)
    return ReferralCodeResponse(
        referral_code=code,
        referral_url=f"{settings.FRONTEND_URL}/signup?ref={code}",
    )


@router.post("/claim-referral")
async def do_claim_referral(
    req: ClaimReferralRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim a referral code for rewards."""
    result = await claim_referral(user, req.code, db)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result
