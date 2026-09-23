"""
Watchlist Router for Starred Content Opportunities.
Allows editors to bookmark high-priority or critical pages to track.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Page, Opportunity, WatchlistItem
from backend.schemas import WatchlistItemResponse, WatchlistToggleResponse
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


def resolve_user_id(db: Session, current_user: Optional[User]) -> int:
    if current_user:
        return current_user.id
    demo = db.query(User).filter(User.email == "demo@contentintelligence.ai").first()
    if demo:
        return demo.id
    first_user = db.query(User).first()
    if first_user:
        return first_user.id
    # Create default demo user if not existing
    demo = User(
        email="demo@contentintelligence.ai",
        hashed_password="not_a_real_password_demo",
        full_name="Editorial Lead",
        is_active=True,
        is_verified=True,
        onboarded=True,
    )
    db.add(demo)
    db.commit()
    db.refresh(demo)
    return demo.id


@router.get("", response_model=List[WatchlistItemResponse])
def get_watchlist(
    dataset_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.dataset_id == target_ds)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )

    result = []
    for item in items:
        page = (
            db.query(Page)
            .filter(Page.page_id == item.page_id, Page.dataset_id == target_ds)
            .first()
        )
        opp = (
            db.query(Opportunity)
            .filter(Opportunity.page_id == item.page_id, Opportunity.dataset_id == target_ds)
            .first()
        )

        result.append(
            WatchlistItemResponse(
                id=item.id,
                page_id=item.page_id,
                dataset_id=item.dataset_id,
                notes=item.notes,
                created_at=item.created_at,
                page_title=page.page_title if page else None,
                url=page.url if page else None,
                priority=opp.priority if opp else None,
                action=opp.action if opp else None,
                opportunity_score=opp.opportunity_score if opp else None,
            )
        )
    return result


@router.get("/ids", response_model=List[str])
def get_watchlist_ids(
    dataset_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    ids = [
        r[0]
        for r in db.query(WatchlistItem.page_id)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.dataset_id == target_ds)
        .all()
    ]
    return ids


@router.post("/{page_id}", response_model=WatchlistToggleResponse)
def toggle_watchlist(
    page_id: str,
    dataset_id: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_id == user_id,
            WatchlistItem.page_id == page_id,
            WatchlistItem.dataset_id == target_ds,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return WatchlistToggleResponse(
            page_id=page_id,
            dataset_id=target_ds,
            is_starred=False,
            message=f"Removed page {page_id} from watchlist.",
        )
    else:
        new_item = WatchlistItem(
            user_id=user_id,
            page_id=page_id,
            dataset_id=target_ds,
            notes=notes,
        )
        db.add(new_item)
        db.commit()
        return WatchlistToggleResponse(
            page_id=page_id,
            dataset_id=target_ds,
            is_starred=True,
            message=f"Added page {page_id} to watchlist.",
        )


@router.delete("/{page_id}")
def delete_from_watchlist(
    page_id: str,
    dataset_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_user_id(db, current_user)
    target_ds = dataset_id or "starter-flyrank"

    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.user_id == user_id,
            WatchlistItem.page_id == page_id,
            WatchlistItem.dataset_id == target_ds,
        )
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Page not found in watchlist")

    db.delete(existing)
    db.commit()
    return {"message": "Page removed from watchlist", "page_id": page_id}
