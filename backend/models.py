"""
SQLAlchemy ORM Database Models.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)  # Existing users default to verified
    verification_token = Column(String(255), nullable=True)
    verification_token_expires_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=True)
    onboarded = Column(Boolean, default=True)    # Existing users default to onboarded
    created_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_starter = Column(Boolean, default=False, index=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    validation_status = Column(String(64), default="pending")
    validation_details = Column(Text, nullable=True)
    profile_details = Column(Text, nullable=True)
    capabilities_details = Column(Text, nullable=True)
    readiness_details = Column(Text, nullable=True)
    mapping_details = Column(Text, nullable=True)
    model_report_details = Column(Text, nullable=True)
    model_name = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pages = relationship("Page", back_populates="dataset", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(64), unique=True, index=True, nullable=False)
    dataset_id = Column(String(64), ForeignKey("datasets.dataset_id"), index=True, nullable=False, default="starter-flyrank")
    client_id = Column(String(64), index=True, nullable=True, default="default")
    content_type = Column(String(64), index=True, default="unknown")
    main_intent = Column(String(64), index=True, default="unknown")
    content_age_days = Column(Float, default=0.0)
    days_since_last_update = Column(Float, default=0.0)
    word_count = Column(Float, default=0.0)
    char_count = Column(Float, default=0.0)
    domain = Column(String(255), index=True, nullable=True)
    url = Column(Text, nullable=True)
    page_title = Column(String(512), nullable=True)
    page_type = Column(String(64), index=True, nullable=True)
    page_type_source = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="pages")
    metrics = relationship("PageMetric", back_populates="page", uselist=False, cascade="all, delete-orphan")
    opportunity = relationship("Opportunity", back_populates="page", uselist=False, cascade="all, delete-orphan")
    recommendation = relationship("Recommendation", back_populates="page", uselist=False, cascade="all, delete-orphan")


class PageMetric(Base):
    __tablename__ = "page_metrics"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(64), ForeignKey("pages.page_id"), index=True, nullable=False)
    impressions_90d = Column(Float, default=0.0)
    clicks_90d = Column(Float, default=0.0)
    sessions_90d = Column(Float, default=0.0)
    pageviews_90d = Column(Float, default=0.0)
    engaged_sessions_90d = Column(Float, default=0.0)
    ai_sessions_90d = Column(Float, default=0.0)
    scroll_events_90d = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    avg_position = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    scroll_rate = Column(Float, default=0.0)
    ai_traffic_pct = Column(Float, default=0.0)
    search_volume = Column(Float, default=0.0)
    competition = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)

    # 30-day comparative time-window fields
    impressions_last_30d = Column(Float, default=0.0)
    clicks_last_30d = Column(Float, default=0.0)
    sessions_last_30d = Column(Float, default=0.0)
    impressions_prev_30d = Column(Float, default=0.0)
    clicks_prev_30d = Column(Float, default=0.0)
    sessions_prev_30d = Column(Float, default=0.0)
    trend_pct = Column(Float, default=0.0)
    trend_classification = Column(String(64), default="stable")

    page = relationship("Page", back_populates="metrics")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(64), ForeignKey("pages.page_id"), index=True, nullable=False)
    dataset_id = Column(String(64), index=True, nullable=False, default="starter-flyrank")
    opportunity_score = Column(Float, index=True, nullable=False)
    priority = Column(String(32), index=True, nullable=False)
    action = Column(String(32), index=True, nullable=False)
    primary_reason = Column(String(255), nullable=False)
    confidence = Column(Float, default=0.7)
    ml_probability = Column(Float, default=0.5)
    queue_rank = Column(Integer, index=True, default=0)
    content_status = Column(String(32), index=True, default="MONITOR")
    confidence_tier = Column(String(32), index=True, default="MEDIUM")
    reasons_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="opportunity")



class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(64), ForeignKey("pages.page_id"), index=True, nullable=False)
    action = Column(String(32), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    directive = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="recommendation")


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(64), nullable=False)
    validation_strategy = Column(String(64), nullable=False)
    roc_auc = Column(Float, default=0.0)
    pr_auc = Column(Float, default=0.0)
    precision_at_20 = Column(Float, default=0.0)
    precision_at_50 = Column(Float, default=0.0)
    precision_at_100 = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    page_id = Column(String(64), nullable=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    is_fallback = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Indexes for high performance
Index("idx_opp_dataset_priority", Opportunity.dataset_id, Opportunity.priority)
Index("idx_opp_dataset_action", Opportunity.dataset_id, Opportunity.action)
Index("idx_opp_dataset_score", Opportunity.dataset_id, Opportunity.opportunity_score)
Index("idx_page_dataset_client", Page.dataset_id, Page.client_id)
Index("idx_page_client_type", Page.client_id, Page.content_type)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    page_id = Column(String(64), index=True, nullable=False)
    dataset_id = Column(String(64), index=True, nullable=False, default="starter-flyrank")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "page_id", "dataset_id", name="uq_user_page_dataset_watchlist"),
    )


class ImpactAction(Base):
    __tablename__ = "impact_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    page_id = Column(String(64), index=True, nullable=False)
    dataset_id = Column(String(64), index=True, nullable=False, default="starter-flyrank")
    action_type = Column(String(32), index=True, nullable=False)
    status = Column(String(32), default="COMPLETED")
    notes = Column(Text, nullable=True)
    marked_at = Column(DateTime, default=datetime.utcnow)
    before_metrics = Column(Text, nullable=True)
    after_metrics = Column(Text, nullable=True)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    dataset_id = Column(String(64), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(32), default="QUEUED", index=True)
    progress_pct = Column(Integer, default=0)
    stage_label = Column(String(128), default="Queued")
    error_message = Column(Text, nullable=True)
    rows_processed = Column(Integer, default=0)
    model_version = Column(String(64), default="Gradient Boosting (Production Champion)")
    scoring_version = Column(String(32), default="2.0")
    data_quality_score = Column(Float, default=95.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

