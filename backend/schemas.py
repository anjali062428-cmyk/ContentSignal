"""
Pydantic v2 Request & Response Schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: Optional[str] = None
    full_name: Optional[str] = None


class SendOTPRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class CancelVerificationRequest(BaseModel):
    email: EmailStr


class OnboardingRequest(BaseModel):
    onboarded: bool = True
    primary_goal: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class RegisterResponse(BaseModel):
    message: str
    email: str
    masked_email: str
    is_verified: bool
    verification_token: Optional[str] = None


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool = True
    onboarded: bool = True


# Overview KPI Schemas
class OverviewKPIs(BaseModel):
    total_pages_analyzed: int
    total_content: int = 0
    high_priority_opportunities: int
    critical_pages: int
    refresh_candidates: int = 0
    under_review: int = 0
    stable_content: int = 0
    data_quality_score: float = 94.0
    pages_to_refresh: int
    ctr_opportunities: int
    declining_pages: int
    pages_to_protect: int
    action_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    content_type_distribution: Dict[str, int]
    content_status_distribution: Dict[str, int] = {}


# Opportunity Item in Queue
class OpportunityQueueItem(BaseModel):
    queue_rank: int
    page_id: str
    client_id: str
    opportunity_score: float
    priority: str
    action: str
    primary_reason: str
    confidence: float
    content_status: str = "MONITOR"
    confidence_tier: str = "MEDIUM"
    trend_pct: float = 0.0
    trend_classification: str = "stable"
    impressions_last_30d: float = 0.0
    clicks_last_30d: float = 0.0
    impressions_prev_30d: float = 0.0
    clicks_prev_30d: float = 0.0
    action_state: Optional[str] = None
    impressions_90d: float
    clicks_90d: float
    ctr: float
    avg_position: float
    days_since_last_update: float
    content_type: str
    main_intent: str
    domain: Optional[str] = None
    url: Optional[str] = None
    page_title: Optional[str] = None
    page_type: Optional[str] = None
    page_type_source: Optional[str] = None
    reasons: List[Dict[str, Any]] = []


class PaginatedOpportunities(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[OpportunityQueueItem]
    has_domain_data: bool = False
    available_domains: List[str] = []
    available_page_types: List[str] = []


# Detailed Page Intelligence
class PageIntelligenceResponse(BaseModel):
    page_id: str
    dataset_id: Optional[str] = None
    client_id: str
    opportunity_score: float
    priority: str
    action: str
    confidence: float
    content_status: str = "MONITOR"
    confidence_tier: str = "MEDIUM"
    trend_classification: str = "stable"
    ml_opportunity_probability: float
    primary_reason: str
    domain: Optional[str] = None
    url: Optional[str] = None
    page_title: Optional[str] = None
    page_type: Optional[str] = None
    page_type_source: Optional[str] = None
    metrics: Dict[str, Any]
    comparison_30d: Optional[Dict[str, Any]] = None
    reasons: List[Dict[str, Any]]
    recommendation: Dict[str, Any]
    model_signals: Dict[str, Any]
    ai_summary: Optional[str] = None



# On-demand Scoring Request
class AnalyzePageRequest(BaseModel):
    impressions_90d: float = 0.0
    clicks_90d: float = 0.0
    sessions_90d: float = 0.0
    ctr: float = 0.0
    avg_position: float = 0.0
    days_since_last_update: float = 0.0
    content_age_days: float = 0.0
    word_count: float = 0.0
    engagement_rate: float = 0.0
    scroll_rate: float = 0.0
    search_volume: float = 0.0
    cpc: float = 0.0
    content_type: str = "keyword article"
    main_intent: str = "informational"


# AI Chat Request
class AIChatRequest(BaseModel):
    message: str
    page_id: Optional[str] = None
    dataset_id: Optional[str] = None


class AIChatResponse(BaseModel):
    query: str
    response: str
    is_grounded: bool
    is_fallback: bool
    supporting_evidence: Optional[Union[Dict[str, Any], List[Any]]] = None


# Dataset Management Schemas
class DatasetSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    dataset_id: str
    name: str
    user_id: Optional[int] = None
    is_starter: bool = False
    row_count: int = 0
    column_count: int = 0
    validation_status: str = "pending"
    model_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ValidationSummaryResponse(BaseModel):
    dataset_id: Optional[str] = None
    is_valid: bool
    row_count: int
    column_count: int
    valid_status: str
    missing_required_fields: List[str] = []
    quarantined_fields: List[str] = []
    unexpected_fields: List[str] = []
    has_domain_data: bool = False
    distinct_domains_count: int = 0
    distinct_domains: List[str] = []
    distinct_page_types: List[str] = []
    duplicate_ids_count: int = 0
    warnings: List[str] = []
    errors: List[str] = []
    readiness: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    mapping: Optional[List[Dict[str, Any]]] = None
    adapter_type: Optional[str] = None


class DatasetDetailResponse(DatasetSummary):
    validation_details: Optional[Dict[str, Any]] = None
    profile_details: Optional[Dict[str, Any]] = None
    capabilities_details: Optional[Dict[str, Any]] = None
    readiness_details: Optional[Dict[str, Any]] = None
    mapping_details: Optional[List[Dict[str, Any]]] = None
    model_report_details: Optional[Dict[str, Any]] = None


class AnalyzeDatasetResponse(BaseModel):
    dataset_id: str
    status: str
    pages_analyzed: int
    high_priority_count: int
    critical_count: int


# Watchlist Schemas
class WatchlistItemResponse(BaseModel):
    id: int
    page_id: str
    dataset_id: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    page_title: Optional[str] = None
    url: Optional[str] = None
    priority: Optional[str] = None
    action: Optional[str] = None
    opportunity_score: Optional[float] = None


class WatchlistToggleResponse(BaseModel):
    page_id: str
    dataset_id: str
    is_starred: bool
    message: str


# Impact Tracking Schemas
class ImpactActionRequest(BaseModel):
    page_id: str
    dataset_id: str = "starter-flyrank"
    action_type: str  # REFRESH, OPTIMIZE, MERGE, CANONICALIZE, PRUNE, REWRITE
    notes: Optional[str] = None
    marked_at: Optional[datetime] = None


class ImpactActionResponse(BaseModel):
    id: int
    page_id: str
    dataset_id: str
    action_type: str
    status: str
    notes: Optional[str] = None
    marked_at: Optional[datetime] = None
    before_metrics: Optional[Dict[str, Any]] = None
    after_metrics: Optional[Dict[str, Any]] = None
    page_title: Optional[str] = None
    url: Optional[str] = None


class ImpactSummaryResponse(BaseModel):
    total_actions: int
    completed_actions: int
    actions_by_type: Dict[str, int]
    items: List[ImpactActionResponse]
    has_subsequent_snapshot: bool = False
    notice: str = "Showing marked actions against current baseline snapshot. Subsequent snapshot uploads will measure before/after delta."


class UpdateActionStatusRequest(BaseModel):
    status: str  # 'TO_REVIEW', 'IN_PROGRESS', 'COMPLETED', 'DISMISSED'
    notes: Optional[str] = None


class SetPageStateRequest(BaseModel):
    page_id: str
    state: Optional[str] = None
    status: Optional[str] = None
    dataset_id: Optional[str] = None
    note: Optional[str] = None
    notes: Optional[str] = None


# Analysis Job Schemas
class CreateJobRequest(BaseModel):
    dataset_id: str


class AnalysisJobResponse(BaseModel):
    job_id: str
    dataset_id: str
    status: str
    progress_pct: int
    stage_label: str
    rows_processed: int = 0
    model_version: str = "Gradient Boosting (Production Champion)"
    scoring_version: str = "2.0"
    data_quality_score: float = 95.0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnalysisRunItem(BaseModel):
    run_id: str
    dataset_id: str
    dataset_name: Optional[str] = None
    status: str
    progress_pct: int
    stage_label: str
    rows_processed: int = 0
    model_version: str = "Gradient Boosting (Production Champion)"
    scoring_version: str = "2.0"
    data_quality_score: float = 95.0
    created_at: Optional[datetime] = None



# Evidence Center Export Schemas
class EvidenceExportRequest(BaseModel):
    dataset_id: str = "starter-flyrank"
    format: str = "pdf"  # pdf, docx, xlsx
    include_summary: bool = True
    include_top_opportunities: bool = True
    include_watchlist: bool = True
    include_impact: bool = True
    max_items: int = 50


# Project Schemas (SRS Section 24)
class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None


class ProjectSummaryResponse(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    is_starter: bool = False
    row_count: int = 0
    column_count: int = 0
    validation_status: str = "pending"
    active_run_summary: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectDetailResponse(ProjectSummaryResponse):
    validation_details: Optional[Dict[str, Any]] = None
    capabilities_details: Optional[Dict[str, Any]] = None
    readiness_details: Optional[Dict[str, Any]] = None
    mapping_details: Optional[List[Dict[str, Any]]] = None
    model_name: Optional[str] = None


class ProjectRunDetailResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    progress_pct: int
    stage_label: str
    rows_processed: int = 0
    model_version: str = "Gradient Boosting (Production Champion)"
    scoring_version: str = "2.0"
    data_quality_score: float = 95.0
    error_message: Optional[str] = None
    execution_logs: List[str] = []
    stage_timings: Dict[str, float] = {}
    champion_model_metrics: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectRecommendationsResponse(BaseModel):
    project_id: str
    total_recommendations: int
    grouped_by_action: Dict[str, List[Dict[str, Any]]]


