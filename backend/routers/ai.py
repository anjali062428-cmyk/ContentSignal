"""
Grounded AI Assistant API Router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.models import Page, PageMetric, Opportunity, AIConversation, Dataset
from backend.schemas import AIChatRequest, AIChatResponse
from backend.ai_assistant import generate_grounded_response
from backend.routers.opportunities import get_page_intelligence
import json
from sqlalchemy import func

router = APIRouter(prefix="/api/ai", tags=["Grounded AI Assistant"])


@router.post("/chat", response_model=AIChatResponse)
def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    target_ds = req.dataset_id or "starter-flyrank"

    # 1. Check if a single page was explicitly requested or page_id is given
    page_ctx = None
    if req.page_id:
        try:
            page_ctx = get_page_intelligence(req.page_id, db)
            if hasattr(page_ctx, "dict"):
                page_ctx = page_ctx.dict()
        except HTTPException:
            page_ctx = None

    # 2. Dataset Metadata & Capabilities
    dataset = db.query(Dataset).filter(Dataset.dataset_id == target_ds).first()
    dataset_name = dataset.name if dataset else target_ds
    capabilities = {}
    missing_capabilities = []
    detected_capabilities = []
    if dataset and dataset.capabilities_details:
        try:
            cd = json.loads(dataset.capabilities_details)
            capabilities = cd.get("capabilities", {})
            missing_capabilities = cd.get("missing_capabilities", [])
            detected_capabilities = cd.get("detected_capabilities", [])
        except Exception:
            pass

    # 3. Aggregations & Status Breakdown
    total_pages = db.query(func.count(Page.id)).filter(Page.dataset_id == target_ds).scalar() or 0
    total_opportunities = db.query(func.count(Opportunity.id)).filter(Opportunity.dataset_id == target_ds).scalar() or total_pages

    status_counts = dict(
        db.query(Opportunity.content_status, func.count(Opportunity.id))
        .filter(Opportunity.dataset_id == target_ds)
        .group_by(Opportunity.content_status)
        .all()
    )
    prio_counts = dict(
        db.query(Opportunity.priority, func.count(Opportunity.id))
        .filter(Opportunity.dataset_id == target_ds)
        .group_by(Opportunity.priority)
        .all()
    )
    action_counts = dict(
        db.query(Opportunity.action, func.count(Opportunity.id))
        .filter(Opportunity.dataset_id == target_ds)
        .group_by(Opportunity.action)
        .all()
    )

    # 4. Content Age Telemetry & Older Performing Pages
    age_stats_row = db.query(
        func.coalesce(func.min(Page.content_age_days), 0),
        func.coalesce(func.max(Page.content_age_days), 0),
        func.coalesce(func.avg(Page.content_age_days), 0),
    ).filter(Page.dataset_id == target_ds, Page.content_age_days > 0).first()

    has_age_data = bool(age_stats_row and age_stats_row[1] > 0)
    older_strong_pages = []
    age_stats_dict = {
        "has_age_data": has_age_data,
        "min_age": float(age_stats_row[0]) if has_age_data else 0.0,
        "max_age": float(age_stats_row[1]) if has_age_data else 0.0,
        "avg_age": float(age_stats_row[2]) if has_age_data else 0.0,
    }

    if has_age_data:
        threshold_age = age_stats_dict["avg_age"] * 0.8
        older_rows = (
            db.query(Page, PageMetric, Opportunity)
            .join(PageMetric, Page.page_id == PageMetric.page_id)
            .join(Opportunity, Page.page_id == Opportunity.page_id)
            .filter(
                Page.dataset_id == target_ds,
                func.coalesce(Page.content_age_days, Page.days_since_last_update, 0) >= threshold_age,
            )
            .order_by(desc(PageMetric.clicks_90d), desc(PageMetric.impressions_90d))
            .limit(10)
            .all()
        )
        if len(older_rows) < 5:
            older_rows = (
                db.query(Page, PageMetric, Opportunity)
                .join(PageMetric, Page.page_id == PageMetric.page_id)
                .join(Opportunity, Page.page_id == Opportunity.page_id)
                .filter(Page.dataset_id == target_ds)
                .order_by(
                    desc(func.coalesce(Page.content_age_days, Page.days_since_last_update, 0)),
                    desc(PageMetric.clicks_90d),
                )
                .limit(10)
                .all()
            )
        for p, m, o in older_rows:
            older_strong_pages.append({
                "page_id": p.page_id,
                "age": float(p.content_age_days or p.days_since_last_update or 0.0),
                "score": float(o.opportunity_score),
                "priority": o.priority,
                "action": o.action,
                "clicks": float(m.clicks_90d or 0),
                "impressions": float(m.impressions_90d or 0),
                "ctr": float(m.ctr or 0),
                "pos": float(m.avg_position or 0),
            })

    # 5. Top Overall Pages (Ranked by Opportunity Score)
    top_overall_rows = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .outerjoin(PageMetric, Opportunity.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
        .order_by(desc(Opportunity.opportunity_score))
        .limit(10)
        .all()
    )
    top_overall_pages = [
        {
            "page_id": opp.page_id,
            "score": float(opp.opportunity_score),
            "priority": opp.priority,
            "action": opp.action,
            "content_status": opp.content_status or "REVIEW",
            "confidence_tier": opp.confidence_tier or "MEDIUM",
            "reason": opp.primary_reason or "Operational review candidate.",
            "impressions": float(m.impressions_90d or 0) if m else 0.0,
            "clicks": float(m.clicks_90d or 0) if m else 0.0,
            "ctr": float(m.ctr or 0) if m else 0.0,
            "pos": float(m.avg_position or 0) if m else 0.0,
            "age": float(p.content_age_days or p.days_since_last_update or 0) if p else 0.0,
        }
        for opp, p, m in top_overall_rows
    ]

    # 6. High Exposure / Weak Click Performance (CTR Opportunities)
    top_ctr_rows = (
        db.query(Opportunity, PageMetric)
        .join(PageMetric, Opportunity.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
        .order_by(desc(PageMetric.impressions_90d))
        .limit(30)
        .all()
    )
    ctr_candidates = [
        {
            "page_id": opp.page_id,
            "ctr": float(m.ctr or 0),
            "pos": float(m.avg_position or 0),
            "imp": float(m.impressions_90d or 0),
            "clicks": float(m.clicks_90d or 0),
            "score": float(opp.opportunity_score or 0),
        }
        for opp, m in top_ctr_rows if (m.impressions_90d or 0) > 0 and ((m.ctr or 0) < 3.0 or opp.action == "OPTIMIZE")
    ]
    if len(ctr_candidates) < 5 and top_ctr_rows:
        ctr_candidates = [
            {
                "page_id": opp.page_id,
                "ctr": float(m.ctr or 0),
                "pos": float(m.avg_position or 0),
                "imp": float(m.impressions_90d or 0),
                "clicks": float(m.clicks_90d or 0),
                "score": float(opp.opportunity_score or 0),
            }
            for opp, m in sorted(top_ctr_rows, key=lambda x: (x[1].ctr or 0.0))[:5]
        ]

    # 7. Domain & Page Type Breakdown
    has_domain = db.query(Page.id).filter(Page.dataset_id == target_ds, Page.domain.isnot(None)).first() is not None
    top_domains = []
    top_page_types = []
    if has_domain:
        top_domains = [
            {"domain": d, "high_priority_count": count}
            for d, count in db.query(Page.domain, func.count(Opportunity.id))
            .join(Opportunity, Page.page_id == Opportunity.page_id)
            .filter(Page.dataset_id == target_ds, Page.domain.isnot(None), Opportunity.priority.in_(["HIGH", "CRITICAL"]))
            .group_by(Page.domain)
            .order_by(func.count(Opportunity.id).desc())
            .limit(5)
            .all()
            if d
        ]
        top_page_types = [
            {"page_type": pt, "refresh_count": count}
            for pt, count in db.query(Page.page_type, func.count(Opportunity.id))
            .join(Opportunity, Page.page_id == Opportunity.page_id)
            .filter(Page.dataset_id == target_ds, Page.page_type.isnot(None), Opportunity.action == "REFRESH")
            .group_by(Page.page_type)
            .order_by(func.count(Opportunity.id).desc())
            .limit(5)
            .all()
            if pt
        ]

    catalog_summary = {
        "dataset_id": target_ds,
        "dataset_name": dataset_name,
        "total_pages": total_pages,
        "total_opportunities": total_opportunities,
        "status_distribution": status_counts,
        "priority_distribution": prio_counts,
        "action_distribution": action_counts,
        "capabilities": capabilities,
        "missing_capabilities": missing_capabilities,
        "detected_capabilities": detected_capabilities,
        "has_domain_data": has_domain,
        "top_domains": top_domains,
        "top_page_types": top_page_types,
        "age_stats": age_stats_dict,
        "older_strong_pages": older_strong_pages,
        "top_overall_pages": top_overall_pages,
        "top_ctr_pages": ctr_candidates[:5],
    }

    result = generate_grounded_response(
        query=req.message,
        page_context=page_ctx,
        catalog_summary=catalog_summary,
    )

    # Record interaction
    try:
        conv = AIConversation(
            page_id=req.page_id,
            query=req.message,
            response=result["response"],
            is_fallback=result["is_fallback"],
        )
        db.add(conv)
        db.commit()
    except Exception:
        db.rollback()

    return result


@router.post("/explain", response_model=AIChatResponse)
def explain_page_ai(req: AIChatRequest, db: Session = Depends(get_db)):
    if not req.page_id:
        raise HTTPException(status_code=400, detail="page_id is required for page explanation")
    return ai_chat(req, db)
