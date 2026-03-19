"""Pass service — unified tool access checking, pass/credit granting and consuming."""

import random
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.pass_catalog import (
    ALWAYS_FREE_TOOL_IDS, PASSES, CREDIT_PACKS, STREAK_REWARDS,
    QUEST_REWARDS, SPIN_REWARDS, REFERRAL_REWARDS, get_pass, get_credit_pack,
)
from app.db.models.user import User
from app.db.models.user_pass import UserPass
from app.db.models.user_credit import UserCredit
from app.db.models.visitor_usage import VisitorUsage


# ── Tool access check (authenticated users) ─────────────────────────────────

async def check_tool_access(
    user: User,
    tool_id: str,
    tool_type: str,
    db: AsyncSession,
) -> dict:
    """
    Check if a user can use a tool. Returns dict with access info.
    Raises nothing — caller decides whether to block.
    """
    today_str = date.today().isoformat()

    # Always-free tools
    if tool_id in ALWAYS_FREE_TOOL_IDS or tool_type == "drawer":
        return {"allowed": True, "reason": "free"}

    # Pro subscriber
    if user.subscription_tier == "pro":
        return {"allowed": True, "reason": "pro"}

    # Reset daily counters if needed
    if user.tool_uses_reset_date != today_str:
        user.tool_uses_today = {}
        user.tool_uses_reset_date = today_str

    # Check active passes
    pass_result = await _check_passes(user, tool_id, today_str, db)
    if pass_result:
        return pass_result

    # Check credit balance
    credit_result = await _check_credits(user, db)
    if credit_result:
        return credit_result

    # Check daily free limit
    uses = user.tool_uses_today.get(tool_id, 0)
    max_free = settings.FREE_USES_PER_TOOL_PER_DAY
    if user.daily_login_date == today_str:
        max_free += settings.DAILY_LOGIN_BONUS

    if uses < max_free:
        # Increment — must create new dict for SQLAlchemy JSONB mutation detection
        new_uses = dict(user.tool_uses_today)
        new_uses[tool_id] = uses + 1
        user.tool_uses_today = new_uses
        await db.commit()
        return {"allowed": True, "reason": "free", "uses_today": uses + 1, "max_free": max_free}

    # Blocked
    return {
        "allowed": False,
        "reason": "blocked",
        "uses_today": uses,
        "max_free": max_free,
        "message": f"Daily limit reached for this tool ({max_free} uses).",
    }


async def _check_passes(user: User, tool_id: str, today_str: str, db: AsyncSession) -> Optional[dict]:
    """Check if any active pass covers this tool with remaining uses."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserPass).where(
            and_(
                UserPass.user_id == user.id,
                UserPass.is_active == True,  # noqa: E712
                UserPass.expires_at > now,
            )
        )
    )
    passes = result.scalars().all()

    for p in passes:
        # Reset pass daily uses if needed
        if p.uses_reset_date != today_str:
            p.uses_today = 0
            p.uses_reset_date = today_str

        # Check if this pass covers the tool
        covers = p.tools_count == -1 or "*" in (p.tool_ids or []) or tool_id in (p.tool_ids or [])
        if covers and p.uses_today < p.uses_per_day:
            p.uses_today += 1
            await db.commit()
            return {
                "allowed": True,
                "reason": "pass",
                "pass_name": get_pass(p.pass_id)["name"] if get_pass(p.pass_id) else p.pass_id,
            }

    return None


async def _check_credits(user: User, db: AsyncSession) -> Optional[dict]:
    """Check if user has any remaining credits. Consume 1 if so."""
    result = await db.execute(
        select(UserCredit).where(
            and_(
                UserCredit.user_id == user.id,
                UserCredit.credits_remaining > 0,
            )
        ).order_by(UserCredit.created_at.asc())  # FIFO
    )
    credit = result.scalars().first()
    if credit:
        credit.credits_remaining -= 1
        await db.commit()
        total_remaining = await get_credit_balance(user, db)
        return {"allowed": True, "reason": "credit", "credits_remaining": total_remaining}
    return None


# ── Visitor access check (unauthenticated) ───────────────────────────────────

async def check_visitor_access(
    fingerprint: str,
    ip_address: str,
    tool_id: str,
    tool_type: str,
    db: AsyncSession,
) -> dict:
    """Check tool access for unauthenticated visitor using fingerprint + IP."""
    if tool_id in ALWAYS_FREE_TOOL_IDS or tool_type == "drawer":
        return {"allowed": True, "reason": "free"}

    today_str = date.today().isoformat()

    # Find by fingerprint or IP in a single locked query to prevent race conditions
    visitor = None
    conditions = []
    if fingerprint:
        conditions.append(VisitorUsage.fingerprint == fingerprint)
    if ip_address:
        conditions.append(VisitorUsage.ip_address == ip_address)

    if conditions:
        result = await db.execute(
            select(VisitorUsage).where(or_(*conditions)).with_for_update().limit(1)
        )
        visitor = result.scalars().first()

    if visitor:
        # Reset if new day
        if visitor.reset_date != today_str:
            visitor.tool_uses_today = {}
            visitor.reset_date = today_str

        uses = visitor.tool_uses_today.get(tool_id, 0)
        if uses >= settings.FREE_USES_PER_TOOL_PER_DAY:
            return {
                "allowed": False,
                "reason": "blocked",
                "uses_today": uses,
                "max_free": settings.FREE_USES_PER_TOOL_PER_DAY,
                "message": "Sign in to get more free uses, or buy a pass!",
            }

        new_uses = dict(visitor.tool_uses_today)
        new_uses[tool_id] = uses + 1
        visitor.tool_uses_today = new_uses
        # Update fingerprint/IP if we found by the other
        if fingerprint and visitor.fingerprint != fingerprint:
            visitor.fingerprint = fingerprint
        if ip_address and visitor.ip_address != ip_address:
            visitor.ip_address = ip_address
        await db.commit()
        return {"allowed": True, "reason": "free", "uses_today": uses + 1}

    # New visitor
    new_visitor = VisitorUsage(
        fingerprint=fingerprint or "unknown",
        ip_address=ip_address or "unknown",
        tool_uses_today={tool_id: 1},
        reset_date=today_str,
    )
    db.add(new_visitor)
    await db.commit()
    return {"allowed": True, "reason": "free", "uses_today": 1}


# ── Grant pass ───────────────────────────────────────────────────────────────

async def grant_pass(
    user: User,
    pass_id: str,
    tool_ids: list[str],
    source: str,
    db: AsyncSession,
    razorpay_payment_id: str | None = None,
    auto_commit: bool = True,
) -> UserPass:
    """Create a UserPass for the user."""
    pass_def = get_pass(pass_id)
    if not pass_def:
        raise ValueError(f"Unknown pass: {pass_id}")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=pass_def["duration_days"])

    # For "all tools" passes, store ["*"]
    if pass_def["tools"] == -1:
        tool_ids = ["*"]

    user_pass = UserPass(
        user_id=user.id,
        pass_id=pass_id,
        tool_ids=tool_ids,
        tools_count=pass_def["tools"],
        uses_per_day=pass_def["uses_per_day"],
        source=source,
        expires_at=expires,
        razorpay_payment_id=razorpay_payment_id,
    )
    db.add(user_pass)
    if auto_commit:
        await db.commit()
    return user_pass


# ── Grant credits ────────────────────────────────────────────────────────────

async def grant_credits(
    user: User,
    amount: int,
    source: str,
    db: AsyncSession,
    razorpay_payment_id: str | None = None,
    auto_commit: bool = True,
) -> UserCredit:
    """Add credits to user's balance."""
    credit = UserCredit(
        user_id=user.id,
        credits_total=amount,
        credits_remaining=amount,
        source=source,
        razorpay_payment_id=razorpay_payment_id,
    )
    db.add(credit)
    if auto_commit:
        await db.commit()
    return credit


# ── Credit balance ───────────────────────────────────────────────────────────

async def get_credit_balance(user: User, db: AsyncSession) -> int:
    """Return total remaining credits across all packs."""
    from sqlalchemy import func
    result = await db.execute(
        select(func.coalesce(func.sum(UserCredit.credits_remaining), 0)).where(
            and_(UserCredit.user_id == user.id, UserCredit.credits_remaining > 0)
        )
    )
    return result.scalar()


# ── Active passes ────────────────────────────────────────────────────────────

async def get_active_passes(user: User, db: AsyncSession) -> list[UserPass]:
    """Return all non-expired active passes."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserPass).where(
            and_(
                UserPass.user_id == user.id,
                UserPass.is_active == True,  # noqa: E712
                UserPass.expires_at > now,
            )
        ).order_by(UserPass.expires_at.asc())
    )
    return result.scalars().all()


# ── Active credits ───────────────────────────────────────────────────────────

async def get_active_credits(user: User, db: AsyncSession) -> list[UserCredit]:
    """Return all credit rows with remaining balance."""
    result = await db.execute(
        select(UserCredit).where(
            and_(UserCredit.user_id == user.id, UserCredit.credits_remaining > 0)
        ).order_by(UserCredit.created_at.asc())
    )
    return result.scalars().all()


# ── Daily login bonus ────────────────────────────────────────────────────────

async def record_daily_login(user: User, db: AsyncSession) -> bool:
    """Record daily login. Returns True if this is first login today (bonus granted)."""
    today_str = date.today().isoformat()
    if user.daily_login_date == today_str:
        return False
    user.daily_login_date = today_str
    await db.commit()
    return True


# ── Spin the wheel ───────────────────────────────────────────────────────────

async def spin_wheel(user: User, db: AsyncSession) -> dict:
    """Spin the weekly wheel. Returns reward info."""
    today_str = date.today().isoformat()

    # Check if already spun this week (Sunday-based)
    if user.last_spin_date:
        last_spin = date.fromisoformat(user.last_spin_date)
        today = date.today()
        # Same ISO week?
        if last_spin.isocalendar()[1] == today.isocalendar()[1] and last_spin.year == today.year:
            return {"error": "Already spun this week. Come back next week!"}

    # Weighted random selection
    total_weight = sum(r["weight"] for r in SPIN_REWARDS)
    roll = random.randint(1, total_weight)
    cumulative = 0
    reward = SPIN_REWARDS[-1]
    for r in SPIN_REWARDS:
        cumulative += r["weight"]
        if roll <= cumulative:
            reward = r
            break

    user.last_spin_date = today_str

    if reward["type"] == "credits":
        await grant_credits(user, reward["amount"], "spin", db, auto_commit=False)
        await db.commit()
        return {"reward_type": "credits", "amount": reward["amount"], "message": f"You won {reward['amount']} credits!"}
    else:
        pass_def = get_pass(reward["pass_id"])
        if not pass_def:
            raise ValueError(f"Invalid spin reward pass_id: {reward['pass_id']}")
        await grant_pass(user, reward["pass_id"], ["*"], "spin", db, auto_commit=False)
        await db.commit()
        return {"reward_type": "pass", "pass_id": reward["pass_id"], "pass_name": pass_def["name"], "message": f"You won a {pass_def['name']} pass!"}


# ── Referral code ────────────────────────────────────────────────────────────

async def ensure_referral_code(user: User, db: AsyncSession) -> str:
    """Generate referral code if user doesn't have one."""
    if user.referral_code:
        return user.referral_code
    code = secrets.token_urlsafe(8)[:10].upper()
    user.referral_code = code
    await db.commit()
    return code


async def claim_referral(user: User, code: str, db: AsyncSession) -> dict:
    """Claim a referral code. Grants rewards to both parties atomically."""
    # Lock user row to prevent concurrent referral claims
    locked = await db.execute(select(User).where(User.id == user.id).with_for_update())
    user = locked.scalars().first()

    if user.referred_by:
        return {"error": "You've already used a referral code."}
    if user.referral_code == code:
        return {"error": "You can't use your own referral code."}

    result = await db.execute(select(User).where(User.referral_code == code))
    referrer = result.scalars().first()
    if not referrer:
        return {"error": "Invalid referral code."}

    try:
        # Reward referrer
        rr = REFERRAL_REWARDS["referrer"]
        await grant_pass(referrer, rr["pass_id"], ["*"], "referral", db, auto_commit=False)
        await grant_credits(referrer, rr["credits"], "referral", db, auto_commit=False)

        # Reward new user
        nr = REFERRAL_REWARDS["new_user"]
        await grant_credits(user, nr["credits"], "referral", db, auto_commit=False)

        # Mark as referred only after all rewards are staged
        user.referred_by = referrer.id
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {"success": True, "message": "Referral claimed! You got 10 credits."}
