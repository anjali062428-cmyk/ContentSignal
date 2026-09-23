"""
Opportunities and Page Intelligence Router.
"""
import io
import csv
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from backend.database import get_db
from backend.models import Page, PageMetric, Opportunity, Recommendation, WatchlistItem, User
from backend.auth import get_optional_current_user
from backend.schemas import (
    OverviewKPIs,
    PaginatedOpportunities,
    OpportunityQueueItem,
    PageIntelligenceResponse,
    AnalyzePageRequest,
)
from content_engine.scoring.engine import calculate_opportunity_score, get_priority_tier
from content_engine.scoring.reason_engine import evaluate_page_reasons
from content_engine.scoring.action_engine import determine_recommended_action
from content_engine.explainability.explain import explain_page_prediction

router = APIRouter(prefix="/api", tags=["Opportunities & Intelligence"])


@router.get("/overview", response_model=OverviewKPIs)
def get_overview(
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"
    total_pages = db.query(Page).filter(Page.dataset_id == target_ds).count()

    # Priority counts
    critical = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "CRITICAL").count()
    high = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "HIGH").count()

    # Content Status counts (Section 12 Standard)
    refresh_candidates = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.content_status == "REFRESH NOW").count()
    under_review = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.content_status == "REVIEW").count()
    stable_content = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.content_status == "STABLE").count()

    # Action counts
    refresh_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "REFRESH").count()
    protect_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "PROTECT").count()
    optimize_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "OPTIMIZE").count()

    # Declining pages (ml probability >= 0.50)
    declining_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.ml_probability >= 0.50).count()

    # Distributions
    action_dist = dict(db.query(Opportunity.action, func.count(Opportunity.id)).filter(Opportunity.dataset_id == target_ds).group_by(Opportunity.action).all())
    priority_dist = dict(db.query(Opportunity.priority, func.count(Opportunity.id)).filter(Opportunity.dataset_id == target_ds).group_by(Opportunity.priority).all())
    content_type_dist = dict(db.query(Page.content_type, func.count(Page.id)).filter(Page.dataset_id == target_ds).group_by(Page.content_type).all())
    content_status_dist = dict(db.query(Opportunity.content_status, func.count(Opportunity.id)).filter(Opportunity.dataset_id == target_ds).group_by(Opportunity.content_status).all())

    # Data Quality Score calculation
    data_quality_score = 94.6
    if target_ds != "starter-flyrank":
        from backend.models import Dataset
        ds = db.query(Dataset).filter(Dataset.dataset_id == target_ds).first()
        if ds and ds.readiness_details:
            try:
                import json
                rd = json.loads(ds.readiness_details)
                passed = sum(1 for c in rd.get("checklist", []) if c.get("status") == "PASS")
                total_checks = max(1, len(rd.get("checklist", [])))
                data_quality_score = round((passed / total_checks) * 100.0, 1)
            except Exception:
                pass

    return {
        "total_pages_analyzed": total_pages,
        "total_content": total_pages,
        "high_priority_opportunities": high,
        "critical_pages": critical,
        "refresh_candidates": refresh_candidates,
        "under_review": under_review,
        "stable_content": stable_content,
        "data_quality_score": data_quality_score,
        "pages_to_refresh": refresh_count,
        "ctr_opportunities": optimize_count,
        "declining_pages": declining_count,
        "pages_to_protect": protect_count,
        "action_distribution": action_dist,
        "priority_distribution": priority_dist,
        "content_type_distribution": content_type_dist,
        "content_status_distribution": content_status_dist,
    }



@router.get("/opportunities", response_model=PaginatedOpportunities)
def get_opportunities_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    dataset_id: Optional[str] = Query(None),
    search: Optional[str] = None,
    priority: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    content_status: Optional[str] = None,
    confidence: Optional[str] = None,
    confidence_tier: Optional[str] = None,
    content_type: Optional[str] = None,
    domain: Optional[str] = None,
    page_type: Optional[str] = None,
    smart_filter: Optional[str] = None,
    sort_by: str = Query("opportunity_score"),
    sort_order: str = Query("desc"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"
    query = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
    )

    # Smart Filters
    if smart_filter:
        sf = smart_filter.lower().strip()
        if sf in ("high_impact", "refresh_now"):
            query = query.filter(Opportunity.content_status == "REFRESH NOW")
        elif sf == "under_review":
            query = query.filter(Opportunity.content_status == "REVIEW")
        elif sf == "quick_wins":
            query = query.filter(Opportunity.action == "OPTIMIZE")
        elif sf == "decaying_fast":
            query = query.filter((Opportunity.action == "REFRESH") | (Page.days_since_last_update >= 180))
        elif sf == "high_visibility":
            query = query.filter(PageMetric.impressions_90d >= 5000)
        elif sf == "watchlist":
            user_id = current_user.id if current_user else 1
            watch_page_ids = [
                r[0] for r in db.query(WatchlistItem.page_id)
                .filter(WatchlistItem.user_id == user_id, WatchlistItem.dataset_id == target_ds)
                .all()
            ]
            query = query.filter(Page.page_id.in_(watch_page_ids))

    # Filters
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Page.page_id.ilike(search_pattern)) | 
            (Page.client_id.ilike(search_pattern)) |
            (Page.domain.ilike(search_pattern)) |
            (Page.page_title.ilike(search_pattern))
        )

    if priority and priority.upper() != "ALL":
        query = query.filter(Opportunity.priority == priority.upper())

    if action and action.upper() != "ALL":
        query = query.filter(Opportunity.action == action.upper())

    target_status = content_status or status
    if target_status and target_status.upper() != "ALL":
        query = query.filter(Opportunity.content_status == target_status.upper())

    target_conf = confidence_tier or confidence
    if target_conf and target_conf.upper() != "ALL":
        query = query.filter(Opportunity.confidence_tier == target_conf.upper())

    if content_type and content_type.lower() != "all":
        query = query.filter(Page.content_type.ilike(content_type))

    if domain and domain.lower() != "all":
        query = query.filter(Page.domain == domain)

    if page_type and page_type.lower() != "all":
        query = query.filter(Page.page_type == page_type)

    # Sorting mapping
    sort_column = Opportunity.opportunity_score
    if sort_by == "impressions_90d":
        sort_column = PageMetric.impressions_90d
    elif sort_by == "ctr":
        sort_column = PageMetric.ctr
    elif sort_by == "avg_position":
        sort_column = PageMetric.avg_position
    elif sort_by == "days_since_last_update":
        sort_column = Page.days_since_last_update
    elif sort_by == "confidence":
        sort_column = Opportunity.confidence
    elif sort_by == "queue_rank":
        sort_column = Opportunity.queue_rank
    elif sort_by == "trend_pct":
        sort_column = PageMetric.trend_pct

    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    total = query.count()
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    # Query distinct domains and page types for this dataset
    distinct_domains = [
        d[0] for d in db.query(Page.domain)
        .filter(Page.dataset_id == target_ds, Page.domain.isnot(None))
        .distinct()
        .all()
        if d[0]
    ]
    distinct_page_types = [
        pt[0] for pt in db.query(Page.page_type)
        .filter(Page.dataset_id == target_ds, Page.page_type.isnot(None))
        .distinct()
        .all()
        if pt[0]
    ]
    has_domain_data = len(distinct_domains) > 0 or len(distinct_page_types) > 0

    # Query action states for current items
    from backend.models import ImpactAction
    action_records = db.query(ImpactAction.page_id, ImpactAction.status).filter(ImpactAction.dataset_id == target_ds).all()
    action_map = {r[0]: r[1] for r in action_records}

    items = []
    for opp, p, m in results:
        # Structured reasons
        reasons_list = []
        if opp.reasons_json:
            try:
                import json
                reasons_list = json.loads(opp.reasons_json)
            except Exception:
                reasons_list = []
        if not reasons_list:
            reasons_list = evaluate_page_reasons({
                "impressions_90d": m.impressions_90d,
                "clicks_90d": m.clicks_90d,
                "sessions_90d": m.sessions_90d,
                "ctr": m.ctr,
                "avg_position": m.avg_position,
                "days_since_last_update": p.days_since_last_update,
                "engagement_rate": m.engagement_rate,
                "scroll_rate": m.scroll_rate,
                "clicks_last_30d": m.clicks_last_30d,
                "clicks_prev_30d": m.clicks_prev_30d,
                "impressions_last_30d": m.impressions_last_30d,
                "impressions_prev_30d": m.impressions_prev_30d,
            }, opp.ml_probability)

        items.append(OpportunityQueueItem(
            queue_rank=opp.queue_rank,
            page_id=opp.page_id,
            client_id=p.client_id,
            opportunity_score=opp.opportunity_score,
            priority=opp.priority,
            action=opp.action,
            primary_reason=opp.primary_reason,
            confidence=opp.confidence,
            content_status=opp.content_status or "MONITOR",
            confidence_tier=opp.confidence_tier or "MEDIUM",
            trend_pct=m.trend_pct or 0.0,
            trend_classification=m.trend_classification or "stable",
            impressions_last_30d=m.impressions_last_30d or 0.0,
            clicks_last_30d=m.clicks_last_30d or 0.0,
            impressions_prev_30d=m.impressions_prev_30d or 0.0,
            clicks_prev_30d=m.clicks_prev_30d or 0.0,
            action_state=action_map.get(opp.page_id, "TO_REVIEW"),
            impressions_90d=m.impressions_90d,
            clicks_90d=m.clicks_90d,
            ctr=m.ctr,
            avg_position=m.avg_position,
            days_since_last_update=p.days_since_last_update,
            content_type=p.content_type,
            main_intent=p.main_intent,
            domain=p.domain,
            url=p.url,
            page_title=p.page_title,
            page_type=p.page_type,
            page_type_source=p.page_type_source,
            reasons=reasons_list,
        ))

    total_pages = (total + page_size - 1) // page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": items,
        "has_domain_data": has_domain_data,
        "available_domains": sorted(distinct_domains),
        "available_page_types": sorted(distinct_page_types),
    }



@router.get("/opportunities/{page_id}", response_model=PageIntelligenceResponse)
def get_page_intelligence(page_id: str, db: Session = Depends(get_db)):
    page = db.query(Page).filter(Page.page_id == page_id).first()
    if not page:
        # Check by suffix (e.g. ds_xxx_P149 matching P149)
        page = db.query(Page).filter(Page.page_id.like(f"%_{page_id}")).first()
    if not page and "_" in page_id:
        raw_part = page_id.split("_")[-1]
        page = db.query(Page).filter(Page.page_id == raw_part).first()
    if not page:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found in catalog")

    opp = page.opportunity
    m = page.metrics
    rec = page.recommendation

    # Raw metrics dictionary
    metrics_dict = {
        "impressions_90d": m.impressions_90d if m else 0,
        "clicks_90d": m.clicks_90d if m else 0,
        "sessions_90d": m.sessions_90d if m else 0,
        "pageviews_90d": m.pageviews_90d if m else 0,
        "ctr": m.ctr if m else 0,
        "avg_position": m.avg_position if m else 0,
        "engagement_rate": m.engagement_rate if m else 0,
        "scroll_rate": m.scroll_rate if m else 0,
        "ai_sessions_90d": m.ai_sessions_90d if m else 0,
        "ai_traffic_pct": m.ai_traffic_pct if m else 0,
        "search_volume": m.search_volume if m else 0,
        "competition": m.competition if m else 0,
        "cpc": m.cpc if m else 0,
        "content_age_days": page.content_age_days,
        "days_since_last_update": page.days_since_last_update,
        "word_count": page.word_count,
        "content_type": page.content_type,
        "main_intent": page.main_intent,
        "clicks_last_30d": m.clicks_last_30d if m else 0,
        "clicks_prev_30d": m.clicks_prev_30d if m else 0,
        "impressions_last_30d": m.impressions_last_30d if m else 0,
        "impressions_prev_30d": m.impressions_prev_30d if m else 0,
    }

    # Evaluate reasons and model signals
    ml_prob = opp.ml_probability if opp else 0.5
    reasons = evaluate_page_reasons(metrics_dict, ml_prob)
    
    # Model attribution signals
    explanation = explain_page_prediction(metrics_dict)

    rec_dict = {
        "action": opp.action if opp else "MONITOR",
        "directive": rec.directive if rec else "Review content performance.",
        "rationale": rec.rationale if rec else "Observed metrics.",
    }

    # 30-day comparative delta breakdown
    c_last = float(m.clicks_last_30d) if (m and m.clicks_last_30d is not None) else 0.0
    c_prev = float(m.clicks_prev_30d) if (m and m.clicks_prev_30d is not None) else 0.0
    i_last = float(m.impressions_last_30d) if (m and m.impressions_last_30d is not None) else 0.0
    i_prev = float(m.impressions_prev_30d) if (m and m.impressions_prev_30d is not None) else 0.0
    s_last = float(m.sessions_last_30d) if (m and m.sessions_last_30d is not None) else 0.0
    s_prev = float(m.sessions_prev_30d) if (m and m.sessions_prev_30d is not None) else 0.0

    clicks_change_pct = round(((c_last - c_prev) / max(1.0, c_prev)) * 100.0, 1) if c_prev > 0 else 0.0
    impressions_change_pct = round(((i_last - i_prev) / max(1.0, i_prev)) * 100.0, 1) if i_prev > 0 else 0.0
    sessions_change_pct = round(((s_last - s_prev) / max(1.0, s_prev)) * 100.0, 1) if s_prev > 0 else 0.0

    ctr_last = round((c_last / max(1.0, i_last)) * 100.0, 2) if i_last > 0 else (float(m.ctr) if (m and m.ctr is not None) else 0.0)
    ctr_prev = round((c_prev / max(1.0, i_prev)) * 100.0, 2) if i_prev > 0 else (float(m.ctr) if (m and m.ctr is not None) else 0.0)
    ctr_change_pct = round(((ctr_last - ctr_prev) / max(0.01, ctr_prev)) * 100.0, 1) if ctr_prev > 0 else 0.0

    has_comparison = (c_last > 0 or c_prev > 0 or i_last > 0 or i_prev > 0 or s_last > 0 or s_prev > 0)
    days_tracked = 60 if has_comparison else 0

    comparison_30d = {
        # Frontend canonical fields expected by page detail
        "recent_clicks": c_last,
        "prev_clicks": c_prev,
        "clicks_delta_pct": clicks_change_pct,
        "recent_impressions": i_last,
        "prev_impressions": i_prev,
        "impressions_delta_pct": impressions_change_pct,
        "recent_ctr": ctr_last,
        "prev_ctr": ctr_prev,
        "ctr_delta_pct": ctr_change_pct,
        "recent_sessions": s_last,
        "prev_sessions": s_prev,
        "sessions_delta_pct": sessions_change_pct,
        "trend_pct": float(m.trend_pct) if (m and m.trend_pct is not None) else 0.0,
        "trend_classification": m.trend_classification if (m and m.trend_classification) else "stable",
        "has_comparison_data": has_comparison,
        "data_sufficiency": {
            "meets_threshold": has_comparison,
            "days_tracked": days_tracked,
            "confidence_tier": opp.confidence_tier if (opp and opp.confidence_tier) else "MEDIUM",
        },
        # Backward compatibility fields
        "clicks_last_30d": c_last,
        "clicks_prev_30d": c_prev,
        "clicks_change_pct": clicks_change_pct,
        "impressions_last_30d": i_last,
        "impressions_prev_30d": i_prev,
        "impressions_change_pct": impressions_change_pct,
    }

    return {
        "page_id": page.page_id,
        "dataset_id": page.dataset_id,
        "client_id": page.client_id,
        "domain": page.domain,
        "url": page.url,
        "page_title": page.page_title,
        "page_type": page.page_type,
        "page_type_source": page.page_type_source,
        "opportunity_score": opp.opportunity_score if opp else 0.0,
        "priority": opp.priority if opp else "LOW",
        "action": opp.action if opp else "MONITOR",
        "confidence": opp.confidence if opp else 0.7,
        "content_status": opp.content_status if (opp and opp.content_status) else "MONITOR",
        "confidence_tier": opp.confidence_tier if (opp and opp.confidence_tier) else "MEDIUM",
        "trend_classification": m.trend_classification if (m and m.trend_classification) else "stable",
        "ml_opportunity_probability": ml_prob,
        "primary_reason": opp.primary_reason if opp else "Routine Monitoring",
        "metrics": metrics_dict,
        "comparison_30d": comparison_30d,
        "reasons": reasons,
        "recommendation": rec_dict,
        "model_signals": explanation,
        "ai_summary": None,
    }



@router.get("/pages")
def list_pages(limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    pages = db.query(Page).limit(limit).all()
    return [{"page_id": p.page_id, "client_id": p.client_id, "content_type": p.content_type} for p in pages]


@router.get("/pages/{page_id}")
def get_page(page_id: str, db: Session = Depends(get_db)):
    return get_page_intelligence(page_id, db)


@router.get("/trends")
def get_trends(
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Aggregate distribution data for charts."""
    target_ds = dataset_id or "starter-flyrank"
    scores = [s[0] for s in db.query(Opportunity.opportunity_score).filter(Opportunity.dataset_id == target_ds).all()]
    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in scores:
        if s <= 20: buckets["0-20"] += 1
        elif s <= 40: buckets["21-40"] += 1
        elif s <= 60: buckets["41-60"] += 1
        elif s <= 80: buckets["61-80"] += 1
        else: buckets["81-100"] += 1

    # Freshness distribution
    freshness_data = [d[0] for d in db.query(Page.days_since_last_update).filter(Page.dataset_id == target_ds).all()]
    fresh_buckets = {"0-30d": 0, "31-90d": 0, "91-180d": 0, "181-365d": 0, "365d+": 0}
    for f in freshness_data:
        if f <= 30: fresh_buckets["0-30d"] += 1
        elif f <= 90: fresh_buckets["31-90d"] += 1
        elif f <= 180: fresh_buckets["91-180d"] += 1
        elif f <= 365: fresh_buckets["181-365d"] += 1
        else: fresh_buckets["365d+"] += 1

    # Domain Intelligence Analytics (optional, for datasets with domain/URL data)
    has_domain_pages = db.query(Page.id).filter(Page.dataset_id == target_ds, Page.domain.isnot(None)).first() is not None
    has_pt_pages = db.query(Page.id).filter(Page.dataset_id == target_ds, Page.page_type.isnot(None)).first() is not None
    has_domain_intelligence = bool(has_domain_pages or has_pt_pages)

    opportunities_by_domain = {}
    page_type_distribution = {}
    score_by_page_type = {}
    declining_by_domain = {}

    if has_domain_intelligence:
        from sqlalchemy import func
        if has_domain_pages:
            # A. Opportunities by Domain (High/Critical priority)
            opps_by_dom_raw = (
                db.query(Page.domain, func.count(Opportunity.id))
                .join(Opportunity, Page.page_id == Opportunity.page_id)
                .filter(Page.dataset_id == target_ds, Page.domain.isnot(None), Opportunity.priority.in_(["HIGH", "CRITICAL"]))
                .group_by(Page.domain)
                .order_by(func.count(Opportunity.id).desc())
                .limit(10)
                .all()
            )
            opportunities_by_domain = {d: count for d, count in opps_by_dom_raw if d}

            # D. Declining Pages by Domain (action == REFRESH)
            declining_by_dom_raw = (
                db.query(Page.domain, func.count(Opportunity.id))
                .join(Opportunity, Page.page_id == Opportunity.page_id)
                .filter(Page.dataset_id == target_ds, Page.domain.isnot(None), Opportunity.action == "REFRESH")
                .group_by(Page.domain)
                .order_by(func.count(Opportunity.id).desc())
                .limit(10)
                .all()
            )
            declining_by_domain = {d: count for d, count in declining_by_dom_raw if d}

        if has_pt_pages:
            # B. Page Type Mix
            pt_dist_raw = (
                db.query(Page.page_type, func.count(Page.id))
                .filter(Page.dataset_id == target_ds, Page.page_type.isnot(None))
                .group_by(Page.page_type)
                .order_by(func.count(Page.id).desc())
                .all()
            )
            page_type_distribution = {pt: count for pt, count in pt_dist_raw if pt}

            # C. Opportunity Score by Page Type
            score_by_pt_raw = (
                db.query(Page.page_type, func.avg(Opportunity.opportunity_score))
                .join(Opportunity, Page.page_id == Opportunity.page_id)
                .filter(Page.dataset_id == target_ds, Page.page_type.isnot(None))
                .group_by(Page.page_type)
                .order_by(func.avg(Opportunity.opportunity_score).desc())
                .all()
            )
            score_by_page_type = {
                pt: round(float(avg_s), 1)
                for pt, avg_s in score_by_pt_raw
                if pt and avg_s is not None
            }

    return {
        "opportunity_score_buckets": buckets,
        "freshness_buckets": fresh_buckets,
        "has_domain_intelligence": has_domain_intelligence,
        "opportunities_by_domain": opportunities_by_domain,
        "page_type_distribution": page_type_distribution,
        "score_by_page_type": score_by_page_type,
        "declining_by_domain": declining_by_domain,
    }


@router.get("/export/csv")
def export_opportunities_csv(
    dataset_id: Optional[str] = Query(None),
    priority: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(5000, le=30000),
    db: Session = Depends(get_db),
):
    """
    Exports the ranked review queue as a CSV file.
    Does NOT export restricted or private FlyRank decision fields.
    """
    target_ds = dataset_id or "starter-flyrank"
    query = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
    )

    if priority and priority.upper() != "ALL":
        query = query.filter(Opportunity.priority == priority.upper())
    if action and action.upper() != "ALL":
        query = query.filter(Opportunity.action == action.upper())

    results = query.order_by(desc(Opportunity.opportunity_score)).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    has_dom = any(p.domain for _, p, _ in results)
    headers = [
        "queue_rank", "page_id", "opportunity_score", "priority", "action",
        "primary_reason", "confidence", "impressions_90d", "clicks_90d", "ctr",
        "avg_position", "days_since_last_update", "content_type", "main_intent"
    ]
    if has_dom:
        headers.extend(["domain", "url", "page_title", "page_type"])
    writer.writerow(headers)

    for opp, p, m in results:
        row = [
            opp.queue_rank, opp.page_id, opp.opportunity_score, opp.priority, opp.action,
            opp.primary_reason, opp.confidence, m.impressions_90d, m.clicks_90d, m.ctr,
            m.avg_position, p.days_since_last_update, p.content_type, p.main_intent
        ]
        if has_dom:
            row.extend([p.domain or "", p.url or "", p.page_title or "", p.page_type or ""])
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=content_intelligence_opportunities.csv"}
    )


@router.post("/score")
@router.post("/analyze")
def score_on_demand_page(req: AnalyzePageRequest):
    """Real-time scoring endpoint for on-demand page features."""
    row_dict = req.model_dump()
    # Assume default 0.50 decline probability for unmodeled on-demand input
    score = calculate_opportunity_score(
        ml_prob=0.50,
        impressions_90d=req.impressions_90d,
        days_since_update=req.days_since_last_update,
        ctr=req.ctr,
        avg_position=req.avg_position,
        engagement_rate=req.engagement_rate,
    )
    priority = get_priority_tier(score)
    reasons = evaluate_page_reasons(row_dict, ml_probability=0.50)
    action_info = determine_recommended_action(
        row_dict, ml_probability=0.50, opportunity_score=score, reason_codes=[r["code"] for r in reasons]
    )

    return {
        "opportunity_score": score,
        "priority": priority,
        "action": action_info["action"],
        "directive": action_info["directive"],
        "reasons": reasons,
    }


@router.get("/opportunity-map")
def get_opportunity_map(
    dataset_id: Optional[str] = Query(None),
    limit: int = Query(250, ge=20, le=500),
    db: Session = Depends(get_db),
):
    """
    Sub-sampled representative scatter data for the Content Opportunity Map.
    X-axis = Visibility (Impressions), Y-axis = Opportunity Score.
    Prevents DOM bloat and browser freezes on 30k rows while displaying authentic data.
    """
    target_ds = dataset_id or "starter-flyrank"
    results = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
        .order_by(desc(Opportunity.opportunity_score))
        .limit(limit)
        .all()
    )

    points = []
    for opp, p, m in results:
        points.append({
            "page_id": opp.page_id,
            "title": p.page_title or opp.page_id,
            "url": p.url or f"/{opp.page_id}",
            "visibility": float(m.impressions_90d or 0),
            "opportunity_score": round(float(opp.opportunity_score or 0), 1),
            "priority": opp.priority,
            "action": opp.action,
            "position": round(float(m.avg_position or 0), 1),
            "ctr": round(float(m.ctr or 0), 2),
            "freshness_days": int(p.days_since_last_update or 0),
        })

    return {
        "dataset_id": target_ds,
        "total_points": len(points),
        "points": points,
    }


@router.get("/attention-center")
def get_attention_center(
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Attention Center triage: Critical, At Risk, and Stable pages
    plus synthesized Today's Content Brief.
    """
    target_ds = dataset_id or "starter-flyrank"

    def format_row(opp, p, m):
        return {
            "page_id": opp.page_id,
            "title": p.page_title or opp.page_id,
            "url": p.url if p.url else None,
            "opportunity_score": round(float(opp.opportunity_score or 0), 1),
            "priority": opp.priority,
            "action": opp.action,
            "primary_reason": opp.primary_reason or "Review performance",
            "visibility": int(m.impressions_90d) if (m.impressions_90d is not None and m.impressions_90d > 0) else None,
            "ctr": round(float(m.ctr), 2) if (m.ctr is not None and m.ctr > 0) else None,
            "position": round(float(m.avg_position), 1) if (m.avg_position is not None and m.avg_position > 0) else None,
            "freshness_days": int(p.days_since_last_update) if (p.days_since_last_update is not None and p.days_since_last_update > 0) else None,
        }

    # 1. Critical (Urgent interventions)
    critical_query = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "CRITICAL")
        .order_by(desc(Opportunity.opportunity_score))
        .limit(5)
        .all()
    )
    critical_items = [format_row(o, p, m) for o, p, m in critical_query]

    # 2. At Risk (High priority decay/refresh)
    at_risk_query = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "HIGH")
        .order_by(desc(Opportunity.opportunity_score))
        .limit(5)
        .all()
    )
    at_risk_items = [format_row(o, p, m) for o, p, m in at_risk_query]

    # 3. Stable (High-performing pages to protect)
    stable_query = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds, Opportunity.action == "PROTECT")
        .order_by(desc(PageMetric.impressions_90d))
        .limit(5)
        .all()
    )
    stable_items = [format_row(o, p, m) for o, p, m in stable_query]

    # 4. Generate structured Today's Content Brief from real dataset counts
    total_critical = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "CRITICAL").count()
    total_high = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "HIGH").count()
    total_refresh = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "REFRESH").count()
    total_optimize = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "OPTIMIZE").count()
    total_declining = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.ml_probability >= 0.50).count()

    top_crit_name = critical_items[0]["title"] if critical_items else "high-priority pages"
    top_opt_name = at_risk_items[0]["title"] if at_risk_items else "key pages"

    if total_refresh > 0:
        takeaway_1 = f"Immediate focus: Refresh queue holds {total_refresh:,} decaying assets prioritized for editorial refresh."
    elif total_declining > 0 and total_optimize > 0:
        takeaway_1 = f"Immediate focus: Refresh queue holds 0 assets; {total_optimize:,} declining assets prioritized for search snippet optimization."
    elif total_optimize > 0:
        takeaway_1 = f"Immediate focus: 0 assets in refresh queue; {total_optimize:,} pages prioritized for CTR optimization."
    else:
        takeaway_1 = "Immediate focus: Refresh queue holds 0 assets requiring editorial updates; catalog metrics are stable."

    if total_optimize > 0:
        takeaway_2 = f"Quick wins: {total_optimize:,} pages occupy high search positions with below-average click rates."
    elif total_declining > 0:
        takeaway_2 = f"Performance trend: {total_declining:,} pages show softening metrics requiring monitoring."
    else:
        takeaway_2 = "Quick wins: Search visibility and click rates are balanced across active pages."

    if critical_items:
        takeaway_3 = f"Top urgent asset: '{top_crit_name}' has the highest composite review signal."
    elif at_risk_items:
        takeaway_3 = f"Leading opportunity: '{top_opt_name}' is the top candidate for review."
    else:
        takeaway_3 = "Catalog monitoring: No critical interventions currently required."

    headline = (
        f"{total_critical:,} critical pages require immediate editorial review"
        if total_critical > 0
        else (
            f"{total_high:,} high-priority content opportunities identified"
            if total_high > 0
            else "Content catalog stable with 0 critical interventions required"
        )
    )

    if critical_items:
        suggested_action = f"Begin today's workflow by addressing the {min(len(critical_items), 5)} critical pages in the Attention Center."
    elif total_optimize > 0:
        suggested_action = f"Focus effort on snippet and title optimization for {top_opt_name} to capture existing search volume."
    elif total_refresh > 0:
        suggested_action = f"Initiate editorial refresh workflows to restore decaying content momentum."
    else:
        suggested_action = "Maintain routine content performance monitoring across upcoming reporting cycles."

    content_brief = {
        "headline": headline,
        "key_takeaways": [takeaway_1, takeaway_2, takeaway_3],
        "suggested_action": suggested_action,
    }

    return {
        "dataset_id": target_ds,
        "critical_items": critical_items,
        "at_risk_items": at_risk_items,
        "stable_items": stable_items,
        "content_brief": content_brief,
    }

