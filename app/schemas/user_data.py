"""Pydantic schemas for user preferences, gamification, and templates."""

from typing import Optional
from pydantic import BaseModel, Field


# ── Preferences ──────────────────────────────────────────────────────────────

class PreferencesResponse(BaseModel):
    theme: str = "dark"
    persona: Optional[str] = None
    theme_skin: Optional[str] = None


class PreferencesUpdate(BaseModel):
    theme: Optional[str] = Field(None, max_length=10)
    persona: Optional[str] = Field(None, max_length=50)
    theme_skin: Optional[str] = Field(None, max_length=50)


# ── Gamification ─────────────────────────────────────────────────────────────

class GamificationResponse(BaseModel):
    xp: int = 0
    streak_current: int = 0
    streak_last_date: Optional[str] = None
    total_ops: int = 0
    total_chars: int = 0
    tools_used: dict = {}
    discovered_tools: list[str] = []
    achievements: list[str] = []
    favorites: list[str] = []
    saved_pipelines: list = []
    completed_quests: list[str] = []
    daily_quest_id: Optional[str] = None
    daily_quest_date: Optional[str] = None
    daily_quest_completed: bool = False


class GamificationUpdate(BaseModel):
    xp: Optional[int] = None
    streak_current: Optional[int] = None
    streak_last_date: Optional[str] = None
    total_ops: Optional[int] = None
    total_chars: Optional[int] = None
    tools_used: Optional[dict] = None
    discovered_tools: Optional[list[str]] = None
    achievements: Optional[list[str]] = None
    favorites: Optional[list[str]] = None
    saved_pipelines: Optional[list] = None
    completed_quests: Optional[list[str]] = None
    daily_quest_id: Optional[str] = None
    daily_quest_date: Optional[str] = None
    daily_quest_completed: Optional[bool] = None


# ── Templates ────────────────────────────────────────────────────────────────

class TemplateResponse(BaseModel):
    id: str
    name: str
    text: str
    created_at: str
    updated_at: str


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    text: Optional[str] = Field(None, min_length=1)
