"""Pydantic schemas for passes, credits, and tool access."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Catalog ──────────────────────────────────────────────────────────────────

class PassCatalogItem(BaseModel):
    id: str
    name: str
    subtitle: str
    tools: int
    uses_per_day: int
    duration_days: int
    price: int
    currency: str
    symbol: str


class CreditPackItem(BaseModel):
    id: str
    name: str
    credits: int
    price: int
    currency: str
    symbol: str


class CatalogResponse(BaseModel):
    passes: list[PassCatalogItem]
    credit_packs: list[CreditPackItem]
    region: str


# ── Active Passes & Credits ──────────────────────────────────────────────────

class ActivePass(BaseModel):
    id: str
    pass_id: str
    name: str
    tool_ids: list[str]
    tools_count: int
    uses_per_day: int
    uses_today: int
    expires_at: datetime
    source: str


class ActiveCredit(BaseModel):
    id: str
    credits_remaining: int
    credits_total: int
    source: str


class ActiveResponse(BaseModel):
    passes: list[ActivePass]
    credits: list[ActiveCredit]
    total_credits: int


# ── Razorpay Order / Verify ──────────────────────────────────────────────────

class PassOrderRequest(BaseModel):
    pass_id: str = Field(..., description="Catalog pass ID e.g. 'day_triple'")
    tool_ids: list[str] = Field(default=[], description="Selected tool IDs")
    region: str = Field(default="", description="Browser-detected region (IN, US, GB, EU)")


class CreditOrderRequest(BaseModel):
    pack_id: str = Field(..., description="Credit pack ID e.g. 'credits_15'")
    region: str = Field(default="", description="Browser-detected region")


class RazorpayOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    user_email: str
    user_name: str


class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    item_id: str
    item_type: str = Field(..., pattern="^(pass|credit)$")
    tool_ids: list[str] = []


# ── Spin ─────────────────────────────────────────────────────────────────────

class SpinResult(BaseModel):
    reward_type: str
    amount: Optional[int] = None
    pass_id: Optional[str] = None
    pass_name: Optional[str] = None
    message: str


# ── Referral ─────────────────────────────────────────────────────────────────

class ClaimReferralRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Referral code to claim")


class ReferralCodeResponse(BaseModel):
    referral_code: str
    referral_url: str
