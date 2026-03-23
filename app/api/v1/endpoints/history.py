"""Operation history endpoints — persistent per-user operation tracking."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, desc

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, OperationHistory
from app.schemas.history import (
    HistoryCreate, HistoryResponse, HistoryListResponse, HistoryStatsResponse,
)

router = APIRouter(prefix="/history", tags=["History"])

PREVIEW_MAX = 500


def _row_to_response(row: OperationHistory) -> HistoryResponse:
    return HistoryResponse(
        id=str(row.id),
        tool_id=row.tool_id,
        tool_label=row.tool_label,
        tool_type=row.tool_type,
        input_preview=row.input_preview,
        output_preview=row.output_preview,
        input_length=row.input_length,
        output_length=row.output_length,
        status=row.status,
        created_at=row.created_at.isoformat(),
    )


# ── List (paginated, newest first) ──────────────────────────────────────────

@router.get("", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    tool_id: str | None = Query(None, max_length=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(OperationHistory).where(OperationHistory.user_id == user.id)
    count_base = select(func.count()).select_from(OperationHistory).where(OperationHistory.user_id == user.id)

    if tool_id:
        base = base.where(OperationHistory.tool_id == tool_id)
        count_base = count_base.where(OperationHistory.tool_id == tool_id)

    total = (await db.execute(count_base)).scalar() or 0

    rows = (await db.execute(
        base.order_by(desc(OperationHistory.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return HistoryListResponse(
        items=[_row_to_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ── Record a new operation ──────────────────────────────────────────────────

@router.post("", response_model=HistoryResponse, status_code=201)
async def record_operation(
    body: HistoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = OperationHistory(
        user_id=user.id,
        tool_id=body.tool_id,
        tool_label=body.tool_label,
        tool_type=body.tool_type,
        input_preview=body.input_preview[:PREVIEW_MAX],
        output_preview=body.output_preview[:PREVIEW_MAX],
        input_length=body.input_length,
        output_length=body.output_length,
        status=body.status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_response(row)


# ── Stats (must come before /{entry_id} to avoid path conflict) ─────────────

@router.get("/stats/summary", response_model=HistoryStatsResponse)
async def get_history_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(
        select(func.count()).select_from(OperationHistory).where(OperationHistory.user_id == user.id)
    )).scalar() or 0

    breakdown_rows = (await db.execute(
        select(OperationHistory.tool_id, func.count())
        .where(OperationHistory.user_id == user.id)
        .group_by(OperationHistory.tool_id)
        .order_by(func.count().desc())
    )).all()
    tools_breakdown = {row[0]: row[1] for row in breakdown_rows}

    recent_rows = (await db.execute(
        select(OperationHistory.tool_id)
        .where(OperationHistory.user_id == user.id)
        .order_by(desc(OperationHistory.created_at))
        .limit(50)
    )).scalars().all()
    seen = []
    for tid in recent_rows:
        if tid not in seen:
            seen.append(tid)
        if len(seen) >= 10:
            break

    return HistoryStatsResponse(
        total_operations=total,
        tools_breakdown=tools_breakdown,
        recent_tools=seen,
    )


# ── Clear all history ────────────────────────────────────────────────────────

@router.delete("", status_code=204)
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(OperationHistory).where(OperationHistory.user_id == user.id)
    )
    await db.commit()


# ── Get single entry ────────────────────────────────────────────────────────

@router.get("/{entry_id}", response_model=HistoryResponse)
async def get_history_entry(
    entry_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(OperationHistory, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="History entry not found")
    return _row_to_response(row)


# ── Delete single entry ─────────────────────────────────────────────────────

@router.delete("/{entry_id}", status_code=204)
async def delete_history_entry(
    entry_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(OperationHistory, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="History entry not found")
    await db.delete(row)
    await db.commit()
