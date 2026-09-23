"""
Dataset Analyzer Pipeline.
Analyzes a validated dataset using the appropriate adapter (FlyRankAdapter or GenericTabularAdapter),
executes model training/inference, computes Opportunity Scores, Priorities, Reasons, and Action Directives,
persists records to SQLite associated with dataset_id, and computes behavioral archetypes.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from backend.models import Dataset, Page, PageMetric, Opportunity, Recommendation
from content_engine.config import BASE_DIR, REPORTS_DIR, RANDOM_SEED
from content_engine.validation.dataset_validator import is_flyrank_schema_candidate
from content_engine.adapters.flyrank import FlyRankAdapter
from content_engine.adapters.generic_tabular import GenericTabularAdapter
from content_engine.archetypes.clustering import ARCHETYPE_NAMES, ARCHETYPE_ACTIONS
from content_engine.classification.page_classifier import extract_and_normalize_domain, classify_page_type


def analyze_and_persist_dataset(
    dataset_id: str,
    df_clean: pd.DataFrame,
    db: Session,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes full ML scoring, prioritization, and archetype clustering
    on a validated DataFrame and stores results in SQLite.
    Dynamically routes between FlyRankAdapter and GenericTabularAdapter.
    """
    total_rows = len(df_clean)
    if total_rows == 0:
        raise ValueError("Cannot analyze an empty dataset.")

    # 1. Select appropriate adapter
    cols = [str(c).strip() for c in df_clean.columns]
    is_flyrank = is_flyrank_schema_candidate(cols)

    if is_flyrank or dataset_id == "starter-flyrank":
        adapter = FlyRankAdapter(dataset_id=dataset_id)
    else:
        adapter = GenericTabularAdapter(dataset_id=dataset_id)

    # 2. Profile, Capabilities, Readiness, and Canonical Mapping
    profile = adapter.profile(df_clean)
    capabilities = adapter.detect_capabilities(profile)
    readiness = adapter.check_readiness(profile, capabilities)
    mappings, df_canonical = adapter.map_canonical(df_clean, target=target)

    # 3. Model Training / Inference & Opportunity Scoring
    model_output = adapter.train_or_evaluate(df_clean, df_canonical, target=target)
    df_scored = adapter.score(df_clean, df_canonical, model_output)

    # 4. Clean out existing records for this dataset if re-analyzing
    existing_pids = [p[0] for p in db.query(Page.page_id).filter(Page.dataset_id == dataset_id).all()]
    if existing_pids:
        db.query(PageMetric).filter(PageMetric.page_id.in_(existing_pids)).delete(synchronize_session=False)
        db.query(Recommendation).filter(Recommendation.page_id.in_(existing_pids)).delete(synchronize_session=False)
    db.query(Opportunity).filter(Opportunity.dataset_id == dataset_id).delete(synchronize_session=False)
    db.query(Page).filter(Page.dataset_id == dataset_id).delete(synchronize_session=False)
    db.commit()

    # 5. Persist to Database in batches
    batch_size = 2000
    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        batch = df_scored.iloc[start_idx:end_idx]
        can_batch = df_canonical.iloc[start_idx:end_idx]

        page_objs = []
        metric_objs = []
        opp_objs = []
        rec_objs = []

        for offset, (_, row) in enumerate(batch.iterrows()):
            can_row = can_batch.iloc[offset]

            # Determine primary identifier
            raw_cid = str(
                row.get("content_id") or
                row.get("id") or
                row.get("page_id") or
                row.get("seller_id") or
                can_row.get("canonical_record_id") or
                f"rec_{start_idx + offset + 1}"
            )
            p_id = raw_cid if dataset_id == "starter-flyrank" else f"{dataset_id}_{raw_cid}"

            dom = str(row.get("domain")).strip() if "domain" in row and not pd.isna(row.get("domain")) and str(row.get("domain")).strip() else None
            u = str(row.get("url")).strip() if "url" in row and not pd.isna(row.get("url")) and str(row.get("url")).strip() else None
            if not dom and u:
                dom = extract_and_normalize_domain(u)
            if dom and dom.startswith("www."):
                dom = dom[4:]

            title = (
                row.get("page_title") or
                row.get("title") or
                can_row.get("canonical_title") or
                raw_cid
            )
            pt = row.get("page_type")
            pt_src = row.get("page_type_source")
            if not pt or str(pt).strip().lower() in ["unknown", "none", "nan"]:
                pt, pt_src = classify_page_type(
                    explicit_page_type=None,
                    content_type=row.get("content_type") or can_row.get("canonical_content_type"),
                    url=u,
                    page_title=title,
                )

            # Extract metrics (fallback to canonical if specific FlyRank column is absent)
            vis = float(row.get("impressions_90d") or row.get("impressions") or row.get("views") or can_row.get("canonical_visibility") or 0.0)
            clicks = float(row.get("clicks_90d") or row.get("clicks") or can_row.get("canonical_search_visibility") or 0.0)
            sessions = float(row.get("sessions_90d") or row.get("sessions") or vis or 0.0)
            pviews = float(row.get("pageviews_90d") or row.get("pageviews") or vis or 0.0)
            eng_sessions = float(row.get("engaged_sessions_90d") or row.get("likes") or row.get("comments") or can_row.get("canonical_engagement") or 0.0)
            ctr_val = float(row.get("ctr") or can_row.get("canonical_ctr") or 0.0)
            if ctr_val == 0.0 and vis > 0 and clicks > 0:
                ctr_val = round((clicks / vis) * 100.0, 2)
            pos_val = float(row.get("avg_position") or row.get("rank") or row.get("position") or can_row.get("canonical_position") or 0.0)
            eng_rate = float(row.get("engagement_rate") or (eng_sessions / max(1.0, sessions) * 100.0) or 0.0)
            scroll_rate = float(row.get("scroll_rate") or 0.0)
            wc = float(row.get("word_count") or can_row.get("canonical_text_length") or 0.0)
            days_up = float(
                row.get("days_since_last_update") or
                row.get("days_since_update") or
                row.get("content_age_days") or
                row.get("age") or
                can_row.get("canonical_freshness") or
                can_row.get("canonical_date") or
                0.0
            )
            age_days = float(
                row.get("content_age_days") or
                row.get("age") or
                row.get("days_since_last_update") or
                row.get("days_since_update") or
                can_row.get("canonical_freshness") or
                can_row.get("canonical_date") or
                0.0
            )

            page_objs.append(Page(
                page_id=p_id,
                dataset_id=dataset_id,
                client_id=str(row.get("client_id", "default")),
                content_type=str(pt or row.get("content_type", "article")),
                main_intent=str(row.get("main_intent", "informational")),
                content_age_days=age_days,
                days_since_last_update=days_up,
                word_count=wc,
                char_count=float(row.get("char_count", 0) or 0),
                domain=str(dom) if dom else None,
                url=str(u) if u else None,
                page_title=str(title) if title else None,
                page_type=str(pt) if pt else None,
                page_type_source=str(pt_src) if pt_src else None,
            ))

            # Extract 30-day comparative window metrics
            c_last = float(row.get("clicks_last_30d") or 0.0)
            c_prev = float(row.get("clicks_prev_30d") or 0.0)
            i_last = float(row.get("impressions_last_30d") or 0.0)
            i_prev = float(row.get("impressions_prev_30d") or 0.0)
            s_last = float(row.get("sessions_last_30d") or 0.0)
            s_prev = float(row.get("sessions_prev_30d") or 0.0)
            t_pct = float(row.get("trend_pct") or 0.0)

            # Fallback estimation if explicit 30d columns missing
            if c_last == 0 and c_prev == 0 and clicks > 0:
                c_last = round(clicks / 3.0, 1)
                c_prev = round(clicks / 3.0, 1)
            if i_last == 0 and i_prev == 0 and vis > 0:
                i_last = round(vis / 3.0, 1)
                i_prev = round(vis / 3.0, 1)
            if s_last == 0 and s_prev == 0 and sessions > 0:
                s_last = round(sessions / 3.0, 1)
                s_prev = round(sessions / 3.0, 1)

            c_change = round(((c_last - c_prev) / max(1.0, c_prev)) * 100.0, 1) if c_prev > 0 else 0.0
            i_change = round(((i_last - i_prev) / max(1.0, i_prev)) * 100.0, 1) if i_prev > 0 else 0.0

            if c_change <= -35.0 and i_change <= -25.0:
                trend_cls = "accelerating_decline"
            elif c_change <= -15.0 or i_change <= -20.0:
                trend_cls = "persistent_decline"
            elif c_change >= 25.0 or i_change >= 30.0:
                trend_cls = "growing"
            elif c_change >= 10.0:
                trend_cls = "recovering"
            else:
                trend_cls = "stable"

            metric_objs.append(PageMetric(
                page_id=p_id,
                impressions_90d=vis,
                clicks_90d=clicks,
                sessions_90d=sessions,
                pageviews_90d=pviews,
                engaged_sessions_90d=eng_sessions,
                ai_sessions_90d=float(row.get("ai_sessions_90d", 0) or 0),
                scroll_events_90d=float(row.get("scroll_events_90d", 0) or 0),
                ctr=ctr_val,
                avg_position=pos_val,
                engagement_rate=eng_rate,
                scroll_rate=scroll_rate,
                ai_traffic_pct=float(row.get("ai_traffic_pct", 0) or 0),
                search_volume=float(row.get("search_volume", 0) or 0),
                competition=float(row.get("competition", 0) or 0),
                cpc=float(row.get("cpc", 0) or 0),
                impressions_last_30d=i_last,
                clicks_last_30d=c_last,
                sessions_last_30d=s_last,
                impressions_prev_30d=i_prev,
                clicks_prev_30d=c_prev,
                sessions_prev_30d=s_prev,
                trend_pct=t_pct or c_change,
                trend_classification=trend_cls,
            ))

            score_val = float(row["opportunity_score"])
            prob_val = float(row.get("ml_probability", row.get("ml_opportunity_probability", 0.50)))
            priority_val = str(row["priority"])
            action_val = str(row["action"])
            reason_val = str(row["primary_reason"])
            rank_val = int(row.get("queue_rank", start_idx + offset + 1))

            conf_tier = "HIGH" if (vis >= 500 and sessions >= 30) else ("MEDIUM" if (vis >= 100 and sessions >= 10) else "LOW")
            status_val = str(row.get("content_status") or "")
            if not status_val or status_val in ("None", "nan"):
                if vis < 50 and sessions < 5:
                    status_val = "INSUFFICIENT DATA"
                elif score_val >= 70.0 and conf_tier in ("HIGH", "MEDIUM") and trend_cls in ("accelerating_decline", "persistent_decline"):
                    status_val = "REFRESH NOW"
                elif score_val >= 55.0 or (0 < pos_val <= 20 and ctr_val < 0.8 and vis >= 300):
                    status_val = "REVIEW"
                elif score_val >= 30.0 or trend_cls in ("persistent_decline", "temporary_drop"):
                    status_val = "MONITOR"
                else:
                    status_val = "STABLE"

            opp_objs.append(Opportunity(
                page_id=p_id,
                dataset_id=dataset_id,
                opportunity_score=score_val,
                priority=priority_val,
                action=action_val,
                primary_reason=reason_val,
                confidence=0.85 if conf_tier == "HIGH" else (0.70 if conf_tier == "MEDIUM" else 0.45),
                ml_probability=prob_val,
                queue_rank=rank_val,
                content_status=status_val,
                confidence_tier=conf_tier,
                reasons_json=str(row.get("reasons_json") or ""),
            ))


            rec_objs.append(Recommendation(
                page_id=p_id,
                action=action_val,
                title=reason_val,
                directive=str(row.get("directive", "Review asset performance.")),
                rationale=str(row.get("rationale", "Standard opportunity prioritization.")),
            ))

        db.bulk_save_objects(page_objs)
        db.bulk_save_objects(metric_objs)
        db.bulk_save_objects(opp_objs)
        db.bulk_save_objects(rec_objs)
        db.commit()

    # 6. Update Dataset record metadata
    ds_record = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if ds_record:
        ds_record.row_count = total_rows
        ds_record.column_count = len(cols)
        ds_record.validation_status = "valid"
        ds_record.model_name = model_output.get("model_report", {}).get("model_type", "Standard Model")
        ds_record.profile_details = json.dumps(profile)
        ds_record.capabilities_details = json.dumps(capabilities)
        ds_record.readiness_details = json.dumps(readiness)
        ds_record.mapping_details = json.dumps(mappings)
        ds_record.model_report_details = json.dumps(model_output.get("model_report", {}))
        db.commit()

    # 7. Dynamic Archetype Generation
    archetype_summary = {}
    try:
        archetype_dir = BASE_DIR / "data" / "archetypes"
        archetype_dir.mkdir(parents=True, exist_ok=True)
        arch_file = archetype_dir / f"{dataset_id}.json"

        # Group by priority / action
        action_dist = df_scored["action"].value_counts().to_dict()
        prio_dist = df_scored["priority"].value_counts().to_dict()

        archetypes = [
            {
                "id": 0,
                "name": "High-Yield Optimization Candidates",
                "action": "OPTIMIZE",
                "page_count": int(action_dist.get("OPTIMIZE", 0)),
                "pct_of_catalog": round(float(action_dist.get("OPTIMIZE", 0) / total_rows * 100.0), 1),
                "strategic_directive": "Focus on metadata and search snippet refinement to capture available search volume."
            },
            {
                "id": 1,
                "name": "Decay Vulnerable Assets",
                "action": "REFRESH",
                "page_count": int(action_dist.get("REFRESH", 0)),
                "pct_of_catalog": round(float(action_dist.get("REFRESH", 0) / total_rows * 100.0), 1),
                "strategic_directive": "Prioritize factual refreshes, new examples, and updated headers."
            },
            {
                "id": 2,
                "name": "Core Stable Anchors",
                "action": "PROTECT",
                "page_count": int(action_dist.get("PROTECT", 0)),
                "pct_of_catalog": round(float(action_dist.get("PROTECT", 0) / total_rows * 100.0), 1),
                "strategic_directive": "Protect against URL changes and retain internal cross-links."
            },
            {
                "id": 3,
                "name": "Low-Activity Monitoring Set",
                "action": "MONITOR",
                "page_count": int(action_dist.get("MONITOR", 0)),
                "pct_of_catalog": round(float(action_dist.get("MONITOR", 0) / total_rows * 100.0), 1),
                "strategic_directive": "Track over subsequent reporting cycles."
            }
        ]
        with open(arch_file, "w", encoding="utf-8") as f:
            json.dump({"archetypes": archetypes}, f, indent=2)
    except Exception:
        pass

    # Count high/critical priority
    high_count = int((df_scored["priority"] == "HIGH").sum())
    critical_count = int((df_scored["priority"] == "CRITICAL").sum())

    return {
        "dataset_id": dataset_id,
        "status": "analyzed",
        "pages_analyzed": total_rows,
        "high_priority_count": high_count,
        "critical_count": critical_count,
        "model_name": ds_record.model_name if ds_record else "Standard Model",
    }
