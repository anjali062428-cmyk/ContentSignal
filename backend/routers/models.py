"""
Model Metrics, Features, and Archetypes Router.
"""
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models import Dataset, Page
from content_engine.config import REPORTS_DIR, BASE_DIR

router = APIRouter(prefix="/api", tags=["Model Insights & Archetypes"])


@router.get("/model/metrics")
def get_model_metrics():
    rep_path = REPORTS_DIR / "model_report.json"
    if not rep_path.exists():
        raise HTTPException(status_code=404, detail="Model report not found")
    with open(rep_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/model/features")
def get_model_features():
    rep_path = REPORTS_DIR / "model_report.json"
    if not rep_path.exists():
        raise HTTPException(status_code=404, detail="Model report not found")
    with open(rep_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    return rep.get("feature_importance", {})


@router.get("/archetypes")
def get_content_archetypes(
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"

    # FlyRank starter dataset retains existing K-Means profiles
    if target_ds in ("starter-flyrank", "default", "starter"):
        rep_path = REPORTS_DIR / "content_archetypes.json"
        if not rep_path.exists():
            raise HTTPException(status_code=404, detail="Archetypes report not found")
        with open(rep_path, "r", encoding="utf-8") as f:
            fly_data = json.load(f)
            fly_data["available"] = True
            fly_data["row_count"] = 30000
            fly_data["min_required"] = 50
            fly_data["additional_needed"] = 0
            fly_data["status_badge"] = "Sufficient data"
            fly_data["has_sufficient_variance"] = True
            return fly_data

    # Resolve custom dataset record by ID or by name
    ds_record = db.query(Dataset).filter(
        or_(Dataset.dataset_id == target_ds, Dataset.name == target_ds)
    ).first()

    resolved_id = ds_record.dataset_id if ds_record else target_ds
    dataset_name = ds_record.name if ds_record else target_ds
    total_rows = ds_record.row_count if ds_record else db.query(Page).filter(Page.dataset_id == resolved_id).count()

    # If dataset has fewer than 50 rows or insufficient data, do NOT fabricate groups
    if total_rows < 50:
        needed = max(0, 50 - total_rows)
        return {
            "available": False,
            "dataset_id": resolved_id,
            "dataset_name": dataset_name,
            "row_count": total_rows,
            "min_required": 50,
            "additional_needed": needed,
            "status_badge": "Insufficient data",
            "reason": "Groups unavailable for this dataset: Not enough behavioral variation or evidence is available to form reliable performance groups.",
            "explanation": "Groups require enough records and behavioral variation to form reliable performance profiles.",
            "details": f"Behavioral clustering requires sufficient record volume and multi-dimensional engagement history (minimum 50 records required; {total_rows} detected, {needed} more needed).",
            "profiles": {},
            "has_sufficient_variance": False,
            "interpretability_notice": "Behavioral clustering requires a minimum sample size of 50 records with non-zero variance across multi-dimensional search and engagement signals."
        }

    # Dataset has >= 50 records. Query metrics to evaluate actual behavioral variance
    from backend.models import PageMetric, Opportunity
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    # Check for precomputed archetypes on disk first
    custom_path = BASE_DIR / "data" / "archetypes" / f"{resolved_id}.json"
    if custom_path.exists():
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
                if "profiles" in custom_data and custom_data["profiles"] and len(custom_data["profiles"]) >= 2:
                    custom_data["available"] = True
                    custom_data["row_count"] = total_rows
                    custom_data["min_required"] = 50
                    custom_data["additional_needed"] = 0
                    custom_data["status_badge"] = "Sufficient data"
                    custom_data["has_sufficient_variance"] = True
                    return custom_data
        except Exception:
            pass

    page_records = (
        db.query(PageMetric, Page, Opportunity)
        .join(Page, PageMetric.page_id == Page.page_id)
        .outerjoin(Opportunity, Page.page_id == Opportunity.page_id)
        .filter(Page.dataset_id == resolved_id)
        .all()
    )

    if len(page_records) < 50:
        needed = max(0, 50 - len(page_records))
        return {
            "available": False,
            "dataset_id": resolved_id,
            "dataset_name": dataset_name,
            "row_count": len(page_records),
            "min_required": 50,
            "additional_needed": needed,
            "status_badge": "Insufficient data",
            "reason": "Groups unavailable for this dataset: Not enough behavioral variation or evidence is available to form reliable performance groups.",
            "explanation": "Groups require enough records and behavioral variation to form reliable performance profiles.",
            "details": f"Behavioral clustering requires sufficient record volume and multi-dimensional engagement history (minimum 50 records required; {len(page_records)} detected, {needed} more needed).",
            "profiles": {},
            "has_sufficient_variance": False,
            "interpretability_notice": "Behavioral clustering requires a minimum sample size of 50 records with non-zero variance across multi-dimensional search and engagement signals."
        }

    # Extract feature matrix for variance verification
    feature_matrix = []
    for pm, p, opp in page_records:
        feature_matrix.append([
            np.log1p(max(0.0, float(pm.impressions_90d or 0))),
            np.log1p(max(0.0, float(pm.clicks_90d or 0))),
            np.log1p(max(0.0, float(pm.sessions_90d or 0))),
            float(pm.ctr or 0),
            float(pm.avg_position or 0),
            float(p.days_since_last_update or 0),
            float(pm.engagement_rate or 0),
            float(pm.scroll_rate or 0),
        ])

    X = np.array(feature_matrix)
    col_stds = np.std(X, axis=0)

    # Check for zero or uniform variance
    if np.all(col_stds < 1e-6) or np.sum(col_stds > 1e-4) < 2:
        return {
            "available": False,
            "dataset_id": resolved_id,
            "dataset_name": dataset_name,
            "row_count": len(page_records),
            "min_required": 50,
            "additional_needed": 0,
            "status_badge": "Insufficient variance",
            "reason": "Groups unavailable for this dataset: Not enough behavioral variation or evidence is available to form reliable performance profiles.",
            "explanation": "Groups require enough records and behavioral variation to form reliable performance profiles.",
            "details": f"The dataset contains {len(page_records)} records, but search and engagement metrics exhibit zero or uniform variance across items. Multi-dimensional behavioral variation is required to distinguish performance cohorts.",
            "missing_evidence": [
                "Search impression variance (all values uniform across catalog)",
                "Click and CTR variance across content assets",
                "User engagement and session behavior differentiation",
            ],
            "profiles": {},
            "has_sufficient_variance": False,
            "interpretability_notice": "Behavioral clustering requires multi-dimensional variance across content assets."
        }

    # Execute actual K-Means behavioral clustering on real records
    n_clusters = min(5, max(2, len(page_records) // 25))
    X_scaled = StandardScaler().fit_transform(X)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=5)
    cluster_labels = kmeans.fit_predict(X_scaled)

    profiles = {}
    tot = len(page_records)
    median_all_imp = float(np.median([float(pm.impressions_90d or 0) for pm, _, _ in page_records]))

    CLUSTER_DEFAULTS = [
        ("High Performers", "PROTECT"),
        ("Declining Winners", "REFRESH"),
        ("High Visibility / Low CTR", "OPTIMIZE"),
        ("Growing Content", "MONITOR"),
        ("Low Visibility / Tail", "INVESTIGATE"),
    ]

    for cid in range(n_clusters):
        indices = [i for i, lbl in enumerate(cluster_labels) if lbl == cid]
        size = len(indices)
        if size == 0:
            continue
        c_items = [page_records[i] for i in indices]

        imp_med = float(np.median([float(pm.impressions_90d or 0) for pm, _, _ in c_items]))
        ctr_med = float(np.median([float(pm.ctr or 0) for pm, _, _ in c_items]))
        pos_med = float(np.median([float(pm.avg_position or 0) for pm, _, _ in c_items]))
        days_med = float(np.median([float(p.days_since_last_update or 0) for _, p, _ in c_items]))
        eng_med = float(np.median([float(pm.engagement_rate or 0) for pm, _, _ in c_items]))

        # Select archetype name and action based on empirical profile
        def_name, def_act = CLUSTER_DEFAULTS[cid % len(CLUSTER_DEFAULTS)]
        if imp_med > median_all_imp and ctr_med < 0.8:
            def_name, def_act = "High Visibility / Low CTR", "OPTIMIZE"
        elif days_med > 90 and imp_med > 500:
            def_name, def_act = "Declining Winners", "REFRESH"
        elif ctr_med > 1.2 and eng_med > 2.5:
            def_name, def_act = "High Performers", "PROTECT"

        profiles[str(cid)] = {
            "cluster_id": cid,
            "archetype_name": def_name,
            "recommended_action": def_act,
            "size": size,
            "share_pct": round(size / tot * 100.0, 1),
            "median_impressions": round(imp_med, 1),
            "median_ctr": round(ctr_med, 2),
            "median_position": round(pos_med, 1),
            "median_days_since_update": round(days_med, 1),
            "median_engagement_rate": round(eng_med, 1),
        }

    result = {
        "available": True,
        "dataset_id": resolved_id,
        "dataset_name": dataset_name,
        "row_count": tot,
        "min_required": 50,
        "additional_needed": 0,
        "status_badge": "Sufficient data",
        "method": "K-Means (Standardized Behavioral Features)",
        "features_used": [
            "impressions_90d", "clicks_90d", "sessions_90d", "ctr",
            "avg_position", "days_since_last_update", "engagement_rate", "scroll_rate"
        ],
        "n_clusters": len(profiles),
        "profiles": profiles,
        "has_sufficient_variance": True,
        "interpretability_notice": "Clusters are grouped purely by observable quantitative search and engagement patterns."
    }

    # Cache to disk
    try:
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result



@router.get("/recommendations")
def get_recommendation_types():
    return {
        "REFRESH": {
            "title": "Editorial Refresh",
            "description": "Update outdated facts, refresh statistics, add recent case studies, and expand search coverage.",
            "target_criteria": "High-value declining pages and stale content assets."
        },
        "OPTIMIZE": {
            "title": "SERP / CTR Optimization",
            "description": "Rewrite title tags, meta description, and schema markup to improve SERP click-through rate.",
            "target_criteria": "High impressions on page 1 or 2 with weak CTR (< 0.6%)."
        },
        "PROTECT": {
            "title": "Protect & Defend Asset",
            "description": "Core high-performing asset. Maintain existing URL structure, preserve internal links, and monitor closely.",
            "target_criteria": "High volume pages with healthy engagement and low decline risk."
        },
        "INVESTIGATE": {
            "title": "Engagement & UX Investigation",
            "description": "Review reader bounce, page load performance, layout readability, and mobile user experience.",
            "target_criteria": "Traffic arrives but engagement rate or scroll depth is substandard."
        },
        "MONITOR": {
            "title": "Passive Monitoring",
            "description": "Insufficient activity or steady baseline. Observe over subsequent 30-day reporting windows.",
            "target_criteria": "Low volume or newly indexed pages with insufficient trend history."
        },
        "REWRITE": {
            "title": "Comprehensive Content Overhaul",
            "description": "Fundamental mismatch with search intent or outdated structure requiring major re-authoring.",
            "target_criteria": "Severe drop across all engagement and visibility dimensions."
        },
        "MERGE": {
            "title": "Content Consolidation / Merge",
            "description": "Consolidate duplicate or cannibalizing content into a stronger authoritative pillar page.",
            "target_criteria": "Long-form content with very low search volume and cannibalization risk."
        },
    }
