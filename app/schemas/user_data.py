"""Pydantic schemas for user preferences, gamification, templates, ui-settings, favorites, tool-stats, pipelines."""

from pydantic import BaseModel, Field

# ── Preferences ──────────────────────────────────────────────────────────────


class PreferencesResponse(BaseModel):
    theme: str = "dark"
    persona: str | None = None
    theme_skin: str | None = None


class PreferencesUpdate(BaseModel):
    theme: str | None = Field(None, max_length=10)
    persona: str | None = Field(None, max_length=50)
    theme_skin: str | None = Field(None, max_length=50)


# ── Gamification ─────────────────────────────────────────────────────────────


class GamificationResponse(BaseModel):
    xp: int = 0
    streak_current: int = 0
    streak_last_date: str | None = None
    total_ops: int = 0
    total_chars: int = 0
    achievements: list[str] = []
    completed_quests: list[str] = []
    daily_quest_id: str | None = None
    daily_quest_date: str | None = None
    daily_quest_completed: bool = False


class GamificationUpdate(BaseModel):
    xp: int | None = None
    streak_current: int | None = None
    streak_last_date: str | None = None
    total_ops: int | None = None
    total_chars: int | None = None
    achievements: list[str] | None = None
    completed_quests: list[str] | None = None
    daily_quest_id: str | None = None
    daily_quest_date: str | None = None
    daily_quest_completed: bool | None = None


# ── Templates ────────────────────────────────────────────────────────────────


class TemplateResponse(BaseModel):
    id: str
    name: str
    text: str
    tool_id: str | None = None
    created_at: str
    updated_at: str


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)
    tool_id: str | None = Field(None, max_length=100)


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    text: str | None = Field(None, min_length=1)
    tool_id: str | None = Field(None, max_length=100)


# ── UI Settings ───────────────────────────────────────────────────────────────


class UiSettingsResponse(BaseModel):
    tool_view: str = "grid"
    keybindings: dict = {}
    panel_sizes: dict = {}


class UiSettingsUpdate(BaseModel):
    tool_view: str | None = Field(None, max_length=10)
    keybindings: dict | None = None
    panel_sizes: dict | None = None


# ── Favorites ─────────────────────────────────────────────────────────────────


class FavoriteToolItem(BaseModel):
    tool_id: str
    sort_order: int


class FavoritesResponse(BaseModel):
    favorites: list[FavoriteToolItem]


# ── Tool Stats ────────────────────────────────────────────────────────────────


class ToolStatItem(BaseModel):
    tool_id: str
    total_uses: int
    last_used_at: str


class ToolStatsResponse(BaseModel):
    stats: list[ToolStatItem]


# ── Pipelines ─────────────────────────────────────────────────────────────────


class PipelineStepResponse(BaseModel):
    id: str
    step_order: int
    tool_id: str
    tool_label: str
    config: dict | None = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    steps: list[PipelineStepResponse]
    created_at: str
    updated_at: str


class PipelineStepIn(BaseModel):
    step_order: int
    tool_id: str = Field(..., max_length=100)
    tool_label: str = Field(..., max_length=200)
    config: dict | None = None


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    steps: list[PipelineStepIn] = []


class PipelineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    steps: list[PipelineStepIn] | None = None


# ── Discovered Tools ─────────────────────────────────────────────────────────


class DiscoveredToolItem(BaseModel):
    tool_id: str
    discovered_at: str


class DiscoveredToolsResponse(BaseModel):
    tools: list[DiscoveredToolItem]
    count: int


# ── Spin History ─────────────────────────────────────────────────────────────


class SpinHistoryItem(BaseModel):
    spin_date: str
    reward_type: str
    reward_ref: str | None = None
    iso_week: int


class SpinHistoryResponse(BaseModel):
    spins: list[SpinHistoryItem]
