"""
Impact Tracking Router.
Tracks editorial actions taken on pages and benchmarks before/after performance.
"""
import json
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Page, Opportunity, ImpactAction
from backend.schemas import ImpactActionRequest, ImpactActionResponse, ImpactSummaryResponse, UpdateActionStatusRequest, SetPageStateRequest
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api/impact", tags=["Impact Tracking"])


def resolve_user_id(db: Session, current_user: Optional[User]) -> int:
    if current_user:
        return current_user.id
    demo = db.query(User).filter(User.email == "demo@contentintelligence.ai").first()
    if demo:
        return demo.id
    first_user = db.query(User).first()
    return first_user.id if first_user else 1


def resolve_page_and_dataset(db: Session, page_id: str, dataset_id: Optional[str] = None):
    """
    Intelligently resolves a Page record and its canonical dataset_id across
    both standard FlyRank datasets and prefixed custom datasets (e.g. ds_57c9285d26_P174 vs P174).
    """
    target_ds = dataset_id if (dataset_id and dataset_id != "default") else None

    # 1. Exact match with dataset if provided
    if target_ds:
        page = db.query(Page).filter(Page.page_id == page_id, Page.dataset_id == target_ds).first()
        if page:
            return page, page.dataset_id

        # Try prefixing with target_ds
        prefixed = f"{target_ds}_{page_id}"
        page = db.query(Page).filter(Page.page_id == prefixed, Page.dataset_id == target_ds).first()
        if page:
            return page, page.dataset_id

    # 2. Exact match on page_id across datasets
    page = db.query(Page).filter(Page.page_id == page_id).first()
    if page:
        return page, page.dataset_id

    # 3. Match by suffix (e.g. ds_xxx_P174 matching P174)
    page = db.query(Page).filter(Page.page_id.like(f"%_{page_id}")).first()
    if page:
        return page, page.dataset_id

    # 4. If page_id was passed with prefix, strip prefix and search
    if "_" in page_id:
        raw_part = page_id.split("_")[-1]
        page = db.query(Page).filter(Page.page_id == raw_part).first()
        if page:
            return page, page.dataset_id

    return None, target_ds or "starter-flyrank"


@router.post("/mark", response_model=ImpactActionResponse)
def mark_action_taken(
    req: ImpactActionRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    page, target_ds = resolve_page_and_dataset(db, req.page_id, req.dataset_id)

    if not page:
        raise HTTPException(
            status_code=404,
            detail=f"Page '{req.page_id}' was not found in dataset '{req.dataset_id or target_ds}'."
        )

    canonical_page_id = page.page_id
    target_ds = page.dataset_id

    # Fetch opportunity and metrics
    opp = page.opportunity
    m = page.metrics

    before_metrics = {
        "impressions_90d": float(m.impressions_90d or 0) if m else 0.0,
        "clicks_90d": float(m.clicks_90d or 0) if m else 0.0,
        "ctr": round(float(m.ctr or 0), 4) if m else 0.0,
        "avg_position": round(float(m.avg_position or 0), 2) if m else 0.0,
        "days_since_last_update": float(page.days_since_last_update or 0),
        "engagement_rate": round(float(m.engagement_rate or 0), 2) if m else 0.0,
    }
    if opp:
        before_metrics["opportunity_score"] = round(float(opp.opportunity_score or 0), 1)
        before_metrics["priority"] = opp.priority
        before_metrics["recommended_action"] = opp.action

    action_record = ImpactAction(
        user_id=user_id,
        page_id=canonical_page_id,
        dataset_id=target_ds,
        action_type=req.action_type.upper(),
        status="COMPLETED",
        notes=req.notes,
        marked_at=req.marked_at or datetime.utcnow(),
        before_metrics=json.dumps(before_metrics),
        after_metrics=None,  # Populated when a new snapshot dataset is analyzed
    )
    db.add(action_record)
    db.commit()
    db.refresh(action_record)

    return ImpactActionResponse(
        id=action_record.id,
        page_id=action_record.page_id,
        dataset_id=action_record.dataset_id,
        action_type=action_record.action_type,
        status=action_record.status,
        notes=action_record.notes,
        marked_at=action_record.marked_at,
        before_metrics=before_metrics,
        after_metrics=None,
        page_title=page.page_title if page else None,
        url=page.url if page else None,
    )


@router.get("", response_model=ImpactSummaryResponse)
def get_impact_summary(
    dataset_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    # Query actions for this dataset and user
    records = (
        db.query(ImpactAction)
        .filter(ImpactAction.dataset_id == target_ds)
        .order_by(ImpactAction.marked_at.desc())
        .all()
    )

    by_type: Dict[str, int] = {}
    items: List[ImpactActionResponse] = []

    for rec in records:
        by_type[rec.action_type] = by_type.get(rec.action_type, 0) + 1
        page, _ = resolve_page_and_dataset(db, rec.page_id, rec.dataset_id)

        before_data = json.loads(rec.before_metrics) if rec.before_metrics else None
        after_data = json.loads(rec.after_metrics) if rec.after_metrics else None

        items.append(
            ImpactActionResponse(
                id=rec.id,
                page_id=rec.page_id,
                dataset_id=rec.dataset_id,
                action_type=rec.action_type,
                status=rec.status,
                notes=rec.notes,
                marked_at=rec.marked_at,
                before_metrics=before_data,
                after_metrics=after_data,
                page_title=page.page_title if page else None,
                url=page.url if page else None,
            )
        )

    return ImpactSummaryResponse(
        total_actions=len(items),
        completed_actions=sum(1 for it in items if it.status == "COMPLETED"),
        actions_by_type=by_type,
        items=items,
        has_subsequent_snapshot=False,
        notice="Showing marked actions against current baseline snapshot. Subsequent snapshot uploads will measure before/after delta.",
    )


@router.get("/{page_id}", response_model=List[ImpactActionResponse])
def get_page_impact_actions(
    page_id: str,
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    page, canonical_ds = resolve_page_and_dataset(db, page_id, dataset_id)
    canonical_id = page.page_id if page else page_id
    raw_id = page_id.split("_")[-1] if "_" in page_id else page_id

    target_ids = list({page_id, canonical_id, raw_id})
    records = (
        db.query(ImpactAction)
        .filter(ImpactAction.page_id.in_(target_ids))
        .order_by(ImpactAction.marked_at.desc())
        .all()
    )

    result = []
    for rec in records:
        rec_page = page or resolve_page_and_dataset(db, rec.page_id, rec.dataset_id)[0]
        before_data = json.loads(rec.before_metrics) if rec.before_metrics else None
        after_data = json.loads(rec.after_metrics) if rec.after_metrics else None
        result.append(
            ImpactActionResponse(
                id=rec.id,
                page_id=rec.page_id,
                dataset_id=rec.dataset_id,
                action_type=rec.action_type,
                status=rec.status,
                notes=rec.notes,
                marked_at=rec.marked_at,
                before_metrics=before_data,
                after_metrics=after_data,
                page_title=rec_page.page_title if rec_page else None,
                url=rec_page.url if rec_page else None,
            )
        )
    return result


@router.patch("/actions/{action_id}", response_model=ImpactActionResponse)
def update_action_status(
    action_id: int,
    status_str: str = Query(..., alias="status"),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    action = db.query(ImpactAction).filter(ImpactAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action record not found")

    action.status = status_str.upper()
    if notes is not None:
        action.notes = notes
    db.commit()
    db.refresh(action)

    page = db.query(Page).filter(Page.page_id == action.page_id, Page.dataset_id == action.dataset_id).first()
    before_data = json.loads(action.before_metrics) if action.before_metrics else None
    after_data = json.loads(action.after_metrics) if action.after_metrics else None
    return ImpactActionResponse(
        id=action.id,
        page_id=action.page_id,
        dataset_id=action.dataset_id,
        action_type=action.action_type,
        status=action.status,
        notes=action.notes,
        marked_at=action.marked_at,
        before_metrics=before_data,
        after_metrics=after_data,
        page_title=page.page_title if page else None,
        url=page.url if page else None,
    )


@router.post("/set-state", response_model=ImpactActionResponse)
def set_page_action_state(
    req: SetPageStateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    page_id = req.page_id
    status_val = (req.state or req.status or "TO_REVIEW").upper()
    action_type = None
    dataset_id = req.dataset_id
    notes = req.note or req.notes
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    # Find existing action or create new
    action = (
        db.query(ImpactAction)
        .filter(ImpactAction.page_id == page_id, ImpactAction.dataset_id == target_ds)
        .order_by(ImpactAction.marked_at.desc())
        .first()
    )

    page = db.query(Page).filter(Page.page_id == page_id, Page.dataset_id == target_ds).first()
    opp = db.query(Opportunity).filter(Opportunity.page_id == page_id, Opportunity.dataset_id == target_ds).first()
    m = page.metrics if page else None

    if action:
        action.status = status_val.upper()
        if notes:
            action.notes = notes
        if action_type:
            action.action_type = action_type.upper()
        db.commit()
        db.refresh(action)
    else:
        before_metrics = {}
        if m:
            before_metrics = {
                "impressions_90d": float(m.impressions_90d or 0),
                "clicks_90d": float(m.clicks_90d or 0),
                "ctr": round(float(m.ctr or 0), 4),
                "avg_position": round(float(m.avg_position or 0), 2),
                "days_since_last_update": float(page.days_since_last_update or 0),
                "engagement_rate": round(float(m.engagement_rate or 0), 2),
            }
        if opp:
            before_metrics["opportunity_score"] = round(float(opp.opportunity_score or 0), 1)
            before_metrics["priority"] = opp.priority
            before_metrics["recommended_action"] = opp.action

        chosen_action_type = action_type.upper() if action_type else (opp.action if opp else "REFRESH")
        action = ImpactAction(
            user_id=user_id,
            page_id=page_id,
            dataset_id=target_ds,
            action_type=chosen_action_type,
            status=status_val.upper(),
            notes=notes,
            marked_at=datetime.utcnow(),
            before_metrics=json.dumps(before_metrics),
            after_metrics=None,
        )
        db.add(action)
        db.commit()
        db.refresh(action)

    before_data = json.loads(action.before_metrics) if action.before_metrics else None
    after_data = json.loads(action.after_metrics) if action.after_metrics else None
    return ImpactActionResponse(
        id=action.id,
        page_id=action.page_id,
        dataset_id=action.dataset_id,
        action_type=action.action_type,
        status=action.status,
        notes=action.notes,
        marked_at=action.marked_at,
        before_metrics=before_data,
        after_metrics=after_data,
        page_title=page.page_title if page else None,
        url=page.url if page else None,
    )

