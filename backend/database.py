"""
Database Connection and Session Management.
Supports SQLite out of the box and swaps seamlessly to PostgreSQL/Supabase via DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import DATABASE_URL

# Connect arguments for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_columns():
    """Ensure newly added columns and tables exist in the SQLite database."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        with engine.connect() as conn:
            # 1. Pages table migrations
            if "pages" in tables:
                columns = [c["name"] for c in inspector.get_columns("pages")]
                if "domain" not in columns:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN domain VARCHAR(255)"))
                if "url" not in columns:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN url TEXT"))
                if "page_title" not in columns:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN page_title VARCHAR(512)"))
                if "page_type" not in columns:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN page_type VARCHAR(64)"))
                if "page_type_source" not in columns:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN page_type_source VARCHAR(64)"))

            # 2. Users table migrations
            if "users" in tables:
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "is_verified" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1"))
                    conn.execute(text("UPDATE users SET is_verified = 1 WHERE is_verified IS NULL"))
                if "verification_token" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(255)"))
                if "verification_token_expires_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN verification_token_expires_at DATETIME"))
                if "otp_attempts" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN otp_attempts INTEGER DEFAULT 0"))
                if "onboarded" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN onboarded BOOLEAN DEFAULT 1"))
                    conn.execute(text("UPDATE users SET onboarded = 1 WHERE onboarded IS NULL"))

            # 3. Datasets table migrations
            if "datasets" in tables:
                ds_cols = [c["name"] for c in inspector.get_columns("datasets")]
                if "profile_details" not in ds_cols:
                    conn.execute(text("ALTER TABLE datasets ADD COLUMN profile_details TEXT"))
                if "capabilities_details" not in ds_cols:
                    conn.execute(text("ALTER TABLE datasets ADD COLUMN capabilities_details TEXT"))
                if "readiness_details" not in ds_cols:
                    conn.execute(text("ALTER TABLE datasets ADD COLUMN readiness_details TEXT"))
                if "mapping_details" not in ds_cols:
                    conn.execute(text("ALTER TABLE datasets ADD COLUMN mapping_details TEXT"))
                if "model_report_details" not in ds_cols:
                    conn.execute(text("ALTER TABLE datasets ADD COLUMN model_report_details TEXT"))

            # 4. Page Metrics table migrations (30-day comparative windows)
            if "page_metrics" in tables:
                pm_cols = [c["name"] for c in inspector.get_columns("page_metrics")]
                if "impressions_last_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN impressions_last_30d FLOAT DEFAULT 0.0"))
                if "clicks_last_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN clicks_last_30d FLOAT DEFAULT 0.0"))
                if "sessions_last_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN sessions_last_30d FLOAT DEFAULT 0.0"))
                if "impressions_prev_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN impressions_prev_30d FLOAT DEFAULT 0.0"))
                if "clicks_prev_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN clicks_prev_30d FLOAT DEFAULT 0.0"))
                if "sessions_prev_30d" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN sessions_prev_30d FLOAT DEFAULT 0.0"))
                if "trend_pct" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN trend_pct FLOAT DEFAULT 0.0"))
                if "trend_classification" not in pm_cols:
                    conn.execute(text("ALTER TABLE page_metrics ADD COLUMN trend_classification VARCHAR(64) DEFAULT 'stable'"))

            # 5. Opportunities table migrations (Content Status & Confidence)
            if "opportunities" in tables:
                opp_cols = [c["name"] for c in inspector.get_columns("opportunities")]
                if "content_status" not in opp_cols:
                    conn.execute(text("ALTER TABLE opportunities ADD COLUMN content_status VARCHAR(32) DEFAULT 'MONITOR'"))
                if "confidence_tier" not in opp_cols:
                    conn.execute(text("ALTER TABLE opportunities ADD COLUMN confidence_tier VARCHAR(32) DEFAULT 'MEDIUM'"))
                if "reasons_json" not in opp_cols:
                    conn.execute(text("ALTER TABLE opportunities ADD COLUMN reasons_json TEXT"))

            # 6. Analysis Jobs table migrations
            if "analysis_jobs" in tables:
                job_cols = [c["name"] for c in inspector.get_columns("analysis_jobs")]
                if "rows_processed" not in job_cols:
                    conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN rows_processed INTEGER DEFAULT 0"))
                if "model_version" not in job_cols:
                    conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN model_version VARCHAR(64) DEFAULT 'Gradient Boosting (Production Champion)'"))
                if "scoring_version" not in job_cols:
                    conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN scoring_version VARCHAR(32) DEFAULT '2.0'"))
                if "data_quality_score" not in job_cols:
                    conn.execute(text("ALTER TABLE analysis_jobs ADD COLUMN data_quality_score FLOAT DEFAULT 95.0"))

            conn.commit()


        # 3. Create any newly declared models (e.g. watchlist_items, impact_actions, analysis_jobs)
        from backend import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Ignore if tables are not yet created
        pass


ensure_columns()


def get_db():
    """Dependency that yields a database session and closes it cleanly."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

