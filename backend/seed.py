"""
Database Seeding Script.
Loads the real processed opportunities catalog (30,000 pages) into the SQLAlchemy database,
initializes indexes, records the champion model run metrics, and creates the default demo user.
"""
import json
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from backend.database import engine, Base, SessionLocal
from backend.models import User, Page, PageMetric, Opportunity, Recommendation, ModelRun
from backend.auth import hash_password
from content_engine.config import OPPORTUNITIES_PATH, REPORTS_DIR, BASE_DIR


def backfill_time_window_metrics(db: Session):
    """
    Checks if page_metrics has unpopulated impressions_last_30d.
    If so, loads opportunities.csv and performs high-speed bulk update.
    """
    sample = db.query(PageMetric).filter(PageMetric.impressions_last_30d > 0).first()
    if sample:
        print("Time-window metrics already populated in database.")
        return

    print("Backfilling 30-day comparative window metrics and content status from opportunities.csv...")
    if not OPPORTUNITIES_PATH.exists():
        print(f"File not found: {OPPORTUNITIES_PATH}")
        return

    import sqlite3
    db_path = BASE_DIR / "content_intelligence.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    df = pd.read_csv(OPPORTUNITIES_PATH)
    pm_updates = []
    opp_updates = []

    for _, row in df.iterrows():
        p_id = str(row["content_id"])
        i_last = float(row.get("impressions_last_30d", 0) or 0)
        c_last = float(row.get("clicks_last_30d", 0) or 0)
        s_last = float(row.get("sessions_last_30d", 0) or 0)
        i_prev = float(row.get("impressions_prev_30d", 0) or 0)
        c_prev = float(row.get("clicks_prev_30d", 0) or 0)
        s_prev = float(row.get("sessions_prev_30d", 0) or 0)
        t_pct = float(row.get("trend_pct", 0) or 0)

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

        pm_updates.append((i_last, c_last, s_last, i_prev, c_prev, s_prev, t_pct or c_change, trend_cls, p_id))

        score = float(row.get("opportunity_score", 0) or 0)
        vis = float(row.get("impressions_90d", 0) or 0)
        sessions = float(row.get("sessions_90d", 0) or 0)
        ctr_val = float(row.get("ctr", 0) or 0)
        pos_val = float(row.get("avg_position", 0) or 0)

        conf_tier = "HIGH" if (vis >= 500 and sessions >= 30) else ("MEDIUM" if (vis >= 100 and sessions >= 10) else "LOW")
        if vis < 50 and sessions < 5:
            status_val = "INSUFFICIENT DATA"
        elif score >= 70.0 and conf_tier in ("HIGH", "MEDIUM") and trend_cls in ("accelerating_decline", "persistent_decline"):
            status_val = "REFRESH NOW"
        elif score >= 55.0 or (0 < pos_val <= 20 and ctr_val < 0.8 and vis >= 300):
            status_val = "REVIEW"
        elif score >= 30.0 or trend_cls in ("persistent_decline", "temporary_drop"):
            status_val = "MONITOR"
        else:
            status_val = "STABLE"

        opp_updates.append((status_val, conf_tier, p_id))

    cursor.executemany(
        """
        UPDATE page_metrics 
        SET impressions_last_30d=?, clicks_last_30d=?, sessions_last_30d=?,
            impressions_prev_30d=?, clicks_prev_30d=?, sessions_prev_30d=?,
            trend_pct=?, trend_classification=?
        WHERE page_id=?
        """,
        pm_updates
    )
    cursor.executemany(
        """
        UPDATE opportunities
        SET content_status=?, confidence_tier=?
        WHERE page_id=?
        """,
        opp_updates
    )
    conn.commit()
    conn.close()
    print(f"Successfully backfilled {len(pm_updates):,} page metrics and opportunity records!")


def seed_database(limit_rows: int = None):
    print("Creating database tables and indexes...")
    Base.metadata.create_all(bind=engine)


    # Migrate SQLite columns if not present
    with engine.connect() as conn:
        res = conn.exec_driver_sql("PRAGMA table_info(pages)").fetchall()
        col_names = [r[1] for r in res]
        if "dataset_id" not in col_names:
            print("Adding dataset_id column to pages table...")
            conn.exec_driver_sql("ALTER TABLE pages ADD COLUMN dataset_id VARCHAR(64) DEFAULT 'starter-flyrank'")
            conn.exec_driver_sql("UPDATE pages SET dataset_id = 'starter-flyrank' WHERE dataset_id IS NULL")
            conn.commit()

        res_opp = conn.exec_driver_sql("PRAGMA table_info(opportunities)").fetchall()
        opp_cols = [r[1] for r in res_opp]
        if "dataset_id" not in opp_cols:
            print("Adding dataset_id column to opportunities table...")
            conn.exec_driver_sql("ALTER TABLE opportunities ADD COLUMN dataset_id VARCHAR(64) DEFAULT 'starter-flyrank'")
            conn.exec_driver_sql("UPDATE opportunities SET dataset_id = 'starter-flyrank' WHERE dataset_id IS NULL")
            conn.commit()

    db: Session = SessionLocal()
    try:
        # Register Starter FlyRank Dataset
        from backend.models import Dataset
        starter_ds = db.query(Dataset).filter(Dataset.dataset_id == "starter-flyrank").first()
        if not starter_ds:
            starter_ds = Dataset(
                dataset_id="starter-flyrank",
                name="FlyRank Starter/Demo Dataset",
                is_starter=True,
                row_count=30000,
                column_count=44,
                validation_status="analyzed",
                model_name="Gradient Boosting (Production Champion)",
            )
            db.add(starter_ds)
            db.commit()
            print("Registered starter-flyrank dataset record.")

        # 1. Create Default Demo User
        demo_email = "demo@contentintelligence.ai"
        existing_user = db.query(User).filter(User.email == demo_email).first()
        if not existing_user:
            demo_user = User(
                email=demo_email,
                hashed_password=hash_password("DemoPass123!"),
                full_name="Editorial Director",
                is_active=True,
            )
            db.add(demo_user)
            db.commit()
            print(f"Created demo user: {demo_email}")

        # 2. Record Model Run
        model_rep_path = REPORTS_DIR / "model_report.json"
        if model_rep_path.exists():
            with open(model_rep_path, "r", encoding="utf-8") as f:
                m_rep = json.load(f)
            
            existing_run = db.query(ModelRun).first()
            if not existing_run:
                gb_metrics = m_rep["metrics"]["gradient_boosting"]
                run = ModelRun(
                    model_name="gradient_boosting",
                    validation_strategy=m_rep["split"]["validation_strategy"],
                    roc_auc=gb_metrics["roc_auc"],
                    pr_auc=gb_metrics["pr_auc"],
                    precision_at_20=gb_metrics["precision_at_20"],
                    precision_at_50=gb_metrics["precision_at_50"],
                    precision_at_100=gb_metrics["precision_at_100"],
                )
                db.add(run)
                db.commit()
                print("Seeded model run evaluation records.")

        # 3. Check if Pages are already seeded
        page_count = db.query(Page).count()
        if page_count > 0:
            print(f"Database already contains {page_count:,} pages. Checking time-window backfill...")
            backfill_time_window_metrics(db)
            return


        print(f"Reading opportunities catalog from {OPPORTUNITIES_PATH}...")
        df = pd.read_csv(OPPORTUNITIES_PATH)
        if limit_rows:
            df = df.head(limit_rows)

        print(f"Seeding {len(df):,} pages into database...")
        
        # Batch insert for high performance
        batch_size = 2500
        total_rows = len(df)
        
        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch = df.iloc[start_idx:end_idx]

            page_objects = []
            metric_objects = []
            opp_objects = []
            rec_objects = []

            for _, row in batch.iterrows():
                p_id = str(row["content_id"])
                
                # Page
                page_objects.append(Page(
                    page_id=p_id,
                    client_id=str(row["client_id"]),
                    content_type=str(row.get("content_type", "unknown")),
                    main_intent=str(row.get("main_intent", "unknown")),
                    content_age_days=float(row.get("content_age_days", 0) or 0),
                    days_since_last_update=float(row.get("days_since_last_update", 0) or 0),
                    word_count=float(row.get("word_count", 0) or 0),
                    char_count=float(row.get("char_count", 0) or 0),
                ))

                # PageMetric
                c_last = float(row.get("clicks_last_30d", 0) or 0)
                c_prev = float(row.get("clicks_prev_30d", 0) or 0)
                i_last = float(row.get("impressions_last_30d", 0) or 0)
                i_prev = float(row.get("impressions_prev_30d", 0) or 0)
                s_last = float(row.get("sessions_last_30d", 0) or 0)
                s_prev = float(row.get("sessions_prev_30d", 0) or 0)
                t_pct = float(row.get("trend_pct", 0) or 0)

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

                metric_objects.append(PageMetric(
                    page_id=p_id,
                    impressions_90d=float(row.get("impressions_90d", 0) or 0),
                    clicks_90d=float(row.get("clicks_90d", 0) or 0),
                    sessions_90d=float(row.get("sessions_90d", 0) or 0),
                    pageviews_90d=float(row.get("pageviews_90d", 0) or 0),
                    engaged_sessions_90d=float(row.get("engaged_sessions_90d", 0) or 0),
                    ai_sessions_90d=float(row.get("ai_sessions_90d", 0) or 0),
                    scroll_events_90d=float(row.get("scroll_events_90d", 0) or 0),
                    ctr=float(row.get("ctr", 0) or 0),
                    avg_position=float(row.get("avg_position", 0) or 0),
                    engagement_rate=float(row.get("engagement_rate", 0) or 0),
                    scroll_rate=float(row.get("scroll_rate", 0) or 0),
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

                score_val = float(row.get("opportunity_score", 0) or 0)
                imp_val = float(row.get("impressions_90d", 0) or 0)
                ses_val = float(row.get("sessions_90d", 0) or 0)
                ctr_val = float(row.get("ctr", 0) or 0)
                pos_val = float(row.get("avg_position", 0) or 0)

                conf_tier = "HIGH" if (imp_val >= 500 and ses_val >= 30) else ("MEDIUM" if (imp_val >= 100 and ses_val >= 10) else "LOW")
                if imp_val < 50 and ses_val < 5:
                    status_val = "INSUFFICIENT DATA"
                elif score_val >= 70.0 and conf_tier in ("HIGH", "MEDIUM") and trend_cls in ("accelerating_decline", "persistent_decline"):
                    status_val = "REFRESH NOW"
                elif score_val >= 55.0 or (0 < pos_val <= 20 and ctr_val < 0.8 and imp_val >= 300):
                    status_val = "REVIEW"
                elif score_val >= 30.0 or trend_cls in ("persistent_decline", "temporary_drop"):
                    status_val = "MONITOR"
                else:
                    status_val = "STABLE"

                # Opportunity
                opp_objects.append(Opportunity(
                    page_id=p_id,
                    opportunity_score=score_val,
                    priority=str(row.get("priority", "LOW")),
                    action=str(row.get("action", "MONITOR")),
                    primary_reason=str(row.get("primary_reason", "Routine Monitoring")),
                    confidence=float(row.get("confidence", 0.7) or 0.7),
                    ml_probability=float(row.get("ml_opportunity_probability", 0.5) or 0.5),
                    queue_rank=int(row.get("queue_rank", 0) or 0),
                    content_status=status_val,
                    confidence_tier=conf_tier,
                ))

                # Recommendation
                rec_objects.append(Recommendation(
                    page_id=p_id,
                    action=str(row.get("action", "MONITOR")),
                    title=f"Directive: {row.get('action', 'MONITOR')}",
                    directive=f"Assigned action: {row.get('action', 'MONITOR')} for {p_id}",
                    rationale=str(row.get("primary_reason", "Observed performance indicators")),
                ))


            db.bulk_save_objects(page_objects)
            db.bulk_save_objects(metric_objects)
            db.bulk_save_objects(opp_objects)
            db.bulk_save_objects(rec_objects)
            db.commit()
            print(f"Seeded batch {end_idx:,} / {total_rows:,} pages.")

        print("Database seed successfully completed!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
