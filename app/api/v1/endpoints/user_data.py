"""User data endpoints: preferences, gamification, templates, ui-settings, favorites, tool-stats, pipelines."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import (
    User, UserPreferences, UserGamification, UserTemplate,
    UserUiSettings, UserFavoriteTool, UserToolStats,
    UserPipeline, UserPipelineStep,
)
from app.schemas.user_data import (
    PreferencesResponse, PreferencesUpdate,
    GamificationResponse, GamificationUpdate,
    TemplateResponse, TemplateCreate, TemplateUpdate,
    UiSettingsResponse, UiSettingsUpdate,
    FavoriteToolItem, FavoritesResponse,
    ToolStatItem, ToolStatsResponse,
    PipelineStepResponse, PipelineResponse, PipelineCreate, PipelineUpdate,
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


# ── UI Settings ───────────────────────────────────────────────────────────────

@router.get("/ui-settings", response_model=UiSettingsResponse)
async def get_ui_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(UserUiSettings, user.id)
    if not row:
        return UiSettingsResponse()
    return UiSettingsResponse(
        tool_view=row.tool_view,
        keybindings=row.keybindings or {},
        panel_sizes=row.panel_sizes or {},
    )


@router.put("/ui-settings", response_model=UiSettingsResponse)
async def update_ui_settings(
    body: UiSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(UserUiSettings, user.id)
    if not row:
        row = UserUiSettings(user_id=user.id)
        db.add(row)

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return UiSettingsResponse(
        tool_view=row.tool_view,
        keybindings=row.keybindings or {},
        panel_sizes=row.panel_sizes or {},
    )


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.get("/favorites", response_model=FavoritesResponse)
async def get_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserFavoriteTool)
        .where(UserFavoriteTool.user_id == user.id)
        .order_by(UserFavoriteTool.sort_order)
    )
    rows = result.scalars().all()
    return FavoritesResponse(
        favorites=[FavoriteToolItem(tool_id=r.tool_id, sort_order=r.sort_order) for r in rows]
    )


@router.post("/favorites/{tool_id}", status_code=201)
async def add_favorite(
    tool_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.get(UserFavoriteTool, (user.id, tool_id))
    if existing:
        return {"tool_id": tool_id, "sort_order": existing.sort_order}

    max_result = await db.execute(
        select(func.max(UserFavoriteTool.sort_order))
        .where(UserFavoriteTool.user_id == user.id)
    )
    max_order = max_result.scalar() or -1

    fav = UserFavoriteTool(user_id=user.id, tool_id=tool_id, sort_order=max_order + 1)
    db.add(fav)
    await db.commit()
    return {"tool_id": tool_id, "sort_order": max_order + 1}


@router.delete("/favorites/{tool_id}", status_code=204)
async def remove_favorite(
    tool_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = await db.get(UserFavoriteTool, (user.id, tool_id))
    if fav:
        await db.delete(fav)
        await db.commit()


# ── Tool Stats ────────────────────────────────────────────────────────────────

@router.get("/tool-stats", response_model=ToolStatsResponse)
async def get_tool_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserToolStats)
        .where(UserToolStats.user_id == user.id)
        .order_by(UserToolStats.total_uses.desc())
    )
    rows = result.scalars().all()
    return ToolStatsResponse(
        stats=[
            ToolStatItem(
                tool_id=r.tool_id,
                total_uses=r.total_uses,
                last_used_at=r.last_used_at.isoformat(),
            )
            for r in rows
        ]
    )


# ── Pipelines ─────────────────────────────────────────────────────────────────

def _pipeline_to_response(p: UserPipeline) -> PipelineResponse:
    return PipelineResponse(
        id=str(p.id),
        name=p.name,
        description=p.description,
        steps=[
            PipelineStepResponse(
                id=str(s.id),
                step_order=s.step_order,
                tool_id=s.tool_id,
                tool_label=s.tool_label,
                config=s.config,
            )
            for s in sorted(p.steps, key=lambda s: s.step_order)
        ],
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


@router.get("/pipelines", response_model=list[PipelineResponse])
async def list_pipelines(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPipeline)
        .where(UserPipeline.user_id == user.id, UserPipeline.is_active == True)
        .options(selectinload(UserPipeline.steps))
        .order_by(UserPipeline.created_at)
    )
    return [_pipeline_to_response(p) for p in result.scalars().all()]


@router.post("/pipelines", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    body: PipelineCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = UserPipeline(user_id=user.id, name=body.name, description=body.description)
    db.add(pipeline)
    await db.flush()

    for step_in in body.steps:
        db.add(UserPipelineStep(
            pipeline_id=pipeline.id,
            step_order=step_in.step_order,
            tool_id=step_in.tool_id,
            tool_label=step_in.tool_label,
            config=step_in.config,
        ))

    await db.commit()
    result = await db.execute(
        select(UserPipeline)
        .where(UserPipeline.id == pipeline.id)
        .options(selectinload(UserPipeline.steps))
    )
    return _pipeline_to_response(result.scalar_one())


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: uuid.UUID,
    body: PipelineUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPipeline)
        .where(UserPipeline.id == pipeline_id, UserPipeline.user_id == user.id)
        .options(selectinload(UserPipeline.steps))
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if body.name is not None:
        pipeline.name = body.name
    if body.description is not None:
        pipeline.description = body.description

    if body.steps is not None:
        for step in list(pipeline.steps):
            await db.delete(step)
        await db.flush()
        for step_in in body.steps:
            db.add(UserPipelineStep(
                pipeline_id=pipeline.id,
                step_order=step_in.step_order,
                tool_id=step_in.tool_id,
                tool_label=step_in.tool_label,
                config=step_in.config,
            ))

    await db.commit()
    result = await db.execute(
        select(UserPipeline)
        .where(UserPipeline.id == pipeline_id)
        .options(selectinload(UserPipeline.steps))
    )
    return _pipeline_to_response(result.scalar_one())


@router.delete("/pipelines/{pipeline_id}", status_code=204)
async def delete_pipeline(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await db.get(UserPipeline, pipeline_id)
    if not pipeline or pipeline.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    pipeline.is_active = False
    await db.commit()
