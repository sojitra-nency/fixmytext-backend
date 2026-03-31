"""Pydantic schemas for subscription/billing."""

from pydantic import BaseModel
from typing import Optional


class SubscriptionStatus(BaseModel):
    tier: str
    tool_uses_today: dict = {}
    free_uses_per_tool: int = 3
    daily_login_bonus: bool = False
    credit_balance: int = 0
    active_passes_count: int = 0
    region: Optional[str] = None


class RazorpayProOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    user_email: str
    user_name: str


class RazorpayProVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
