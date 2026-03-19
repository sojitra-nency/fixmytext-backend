"""User data endpoints: preferences, gamification, templates."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, UserPreferences, UserGamification, UserTemplate
from app.schemas.user_data import (
    PreferencesResponse, PreferencesUpdate,
    GamificationResponse, GamificationUpdate,
    TemplateResponse, TemplateCreate, TemplateUpdate,
)

router = APIRouter(prefix="/user", tags=["User Data"])


# ── Preferences ──────────────────────────────────────────────────────────────

@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.get(UserPreferences, user.id)
    if not prefs:
        return PreferencesResponse()
    return PreferencesResponse(theme=prefs.theme, persona=prefs.persona, theme_skin=prefs.theme_skin)


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.get(UserPreferences, user.id)
    if not prefs:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(prefs, key, value)

    await db.commit()
    await db.refresh(prefs)
    return PreferencesResponse(theme=prefs.theme, persona=prefs.persona, theme_skin=prefs.theme_skin)


# ── Gamification ─────────────────────────────────────────────────────────────

def _gam_to_response(gam: UserGamification) -> GamificationResponse:
    """Convert ORM model to response schema. JSONB columns are native dicts/lists."""
    return GamificationResponse(
        xp=gam.xp,
        streak_current=gam.streak_current,
        streak_last_date=gam.streak_last_date,
        total_ops=gam.total_ops,
        total_chars=gam.total_chars,
        tools_used=gam.tools_used,
        discovered_tools=gam.discovered_tools,
        achievements=gam.achievements,
        favorites=gam.favorites,
        saved_pipelines=gam.saved_pipelines,
        completed_quests=gam.completed_quests,
        daily_quest_id=gam.daily_quest_id,
        daily_quest_date=gam.daily_quest_date,
        daily_quest_completed=gam.daily_quest_completed,
    )


@router.get("/gamification", response_model=GamificationResponse)
async def get_gamification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gam = await db.get(UserGamification, user.id)
    if not gam:
        return GamificationResponse()
    return _gam_to_response(gam)


@router.put("/gamification", response_model=GamificationResponse)
async def update_gamification(
    body: GamificationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gam = await db.get(UserGamification, user.id)
    if not gam:
        gam = UserGamification(user_id=user.id)
        db.add(gam)

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(gam, key, value)

    await db.commit()
    await db.refresh(gam)
    return _gam_to_response(gam)


# ── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserTemplate).where(UserTemplate.user_id == user.id).order_by(UserTemplate.created_at)
    )
    templates = result.scalars().all()
    return [
        TemplateResponse(
            id=str(t.id), name=t.name, text=t.text,
            created_at=t.created_at.isoformat(), updated_at=t.updated_at.isoformat(),
        )
        for t in templates
    ]


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    template = UserTemplate(user_id=user.id, name=body.name, text=body.text)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse(
        id=str(template.id), name=template.name, text=template.text,
        created_at=template.created_at.isoformat(), updated_at=template.updated_at.isoformat(),
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(UserTemplate, template_id)
    if not template or template.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return TemplateResponse(
        id=str(template.id), name=template.name, text=template.text,
        created_at=template.created_at.isoformat(), updated_at=template.updated_at.isoformat(),
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(UserTemplate, template_id)
    if not template or template.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
