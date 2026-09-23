/**
 * Typed API Client for Content Intelligence Engine FastAPI Backend.
 */

let rawBase = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8001";
if (!rawBase.endsWith("/api")) {
  rawBase = `${rawBase.replace(/\/+$/, "")}/api`;
}
const API_BASE = rawBase;

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ci_token");
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("ci_token", token);
  }
}

export function removeToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("ci_token");
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export interface OverviewKPIs {
  total_pages_analyzed: number;
  high_priority_opportunities: number;
  critical_pages: number;
  pages_to_refresh: number;
  ctr_opportunities: number;
  declining_pages: number;
  pages_to_protect: number;
  action_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  content_type_distribution: Record<string, number>;
  // V2 standard metrics
  total_content?: number;
  refresh_candidates?: number;
  under_review?: number;
  stable_content?: number;
  data_quality_score?: number;
  status_distribution?: Record<string, number>;
}

export interface OpportunityItem {
  queue_rank: number;
  page_id: string;
  client_id: string;
  opportunity_score: number;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  action: "REFRESH" | "OPTIMIZE" | "PROTECT" | "INVESTIGATE" | "MONITOR" | "REWRITE" | "MERGE";
  primary_reason: string;
  confidence: number;
  impressions_90d: number;
  clicks_90d: number;
  ctr: number;
  avg_position: number;
  days_since_last_update: number;
  content_type: string;
  main_intent: string;
  domain?: string | null;
  url?: string | null;
  page_title?: string | null;
  page_type?: string | null;
  page_type_source?: string | null;
  // V2 additions
  content_status?: "REFRESH NOW" | "REVIEW" | "MONITOR" | "STABLE" | "INSUFFICIENT DATA";
  confidence_tier?: "HIGH" | "MEDIUM" | "LOW";
  trend_pct?: number;
  trend_classification?: string;
  recommended_action?: string;
  action_state?: "TO_REVIEW" | "IN_PROGRESS" | "COMPLETED" | "DISMISSED";
}

export interface PaginatedOpportunities {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: OpportunityItem[];
  has_domain_data?: boolean;
  available_domains?: string[];
  available_page_types?: string[];
}

export interface Comparison30d {
  recent_clicks?: number;
  prev_clicks?: number;
  clicks_delta_pct?: number;
  recent_impressions?: number;
  prev_impressions?: number;
  impressions_delta_pct?: number;
  recent_ctr?: number;
  prev_ctr?: number;
  ctr_delta_pct?: number;
  recent_sessions?: number;
  prev_sessions?: number;
  sessions_delta_pct?: number;
  trend_classification?: string;
  has_comparison_data?: boolean;
  data_sufficiency?: {
    meets_threshold?: boolean;
    total_sessions?: number;
    total_clicks?: number;
    days_tracked?: number;
    confidence_tier?: string;
  };
}

export interface PageIntelligence {
  page_id: string;
  dataset_id?: string;
  client_id: string;
  domain?: string | null;
  url?: string | null;
  page_title?: string | null;
  page_type?: string | null;
  page_type_source?: string | null;
  opportunity_score: number;
  priority: string;
  action: string;
  confidence: number;
  ml_opportunity_probability: number;
  primary_reason: string;
  // V2 additions
  content_status?: string;
  confidence_tier?: string;
  comparison_30d?: Comparison30d;
  action_state?: string;
  metrics: Record<string, any>;
  reasons: Array<{
    code?: string;
    title?: string;
    explanation?: string;
    reason_code?: string;
    message?: string;
    metric?: string;
    change_percent?: number;
    severity?: string;
    confidence?: number;
    supporting_metric?: Record<string, any>;
  }>;
  recommendation: {
    action: string;
    directive: string;
    rationale: string;
  };
  model_signals: {
    model_probability: number;
    causal_disclaimer: string;
    top_contributions: Array<{
      feature: string;
      value: number;
      importance: number;
      impact_score: number;
      direction: string;
      explanation: string;
    }>;
  };
}

export interface AnalysisRunItem {
  id: number;
  run_id: string;
  dataset_id: string;
  dataset_name: string;
  started_at: string;
  completed_at?: string | null;
  status: string;
  rows_processed: number;
  scoring_version: string;
  model_version: string;
  data_quality_score: number;
  refresh_candidates_count: number;
}

export interface DatasetSummary {
  id: number;
  dataset_id: string;
  name: string;
  user_id?: number | null;
  is_starter: boolean;
  row_count: number;
  column_count: number;
  validation_status: string;
  model_name?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ReadinessItem {
  name: string;
  passed: boolean;
  severity: "blocker" | "warning" | "info";
  message: string;
}

export interface ReadinessReport {
  overall_status: "READY" | "READY_WITH_LIMITATIONS" | "NOT_READY" | "TIME_SERIES" | "LARGE_DATASET";
  summary: string;
  checklist: ReadinessItem[];
  blockers: string[];
  warnings: string[];
  suggested_adapter: string;
  checks_passed?: number;
  total_checks?: number;
  readiness_pct?: number;
}

export interface CanonicalMappingItem {
  canonical_slot: string;
  source_column: string;
  confidence: number;
  data_type: string;
}

export interface ValidationSummary {
  dataset_id?: string;
  is_valid: boolean;
  row_count: number;
  column_count: number;
  valid_status: string;
  missing_required_fields: string[];
  quarantined_fields: string[];
  unexpected_fields: string[];
  has_domain_data?: boolean;
  distinct_domains_count?: number;
  distinct_domains?: string[];
  distinct_page_types?: string[];
  duplicate_ids_count: number;
  warnings: string[];
  errors: string[];
  readiness?: ReadinessReport | null;
  capabilities?: Record<string, any> | null;
  mapping?: CanonicalMappingItem[] | null;
  adapter_type?: string | null;
}

export interface DatasetDetail extends DatasetSummary {
  validation_details?: ValidationSummary | null;
  profile_details?: Record<string, any> | null;
  capabilities_details?: Record<string, any> | null;
  readiness_details?: ReadinessReport | null;
  mapping_details?: CanonicalMappingItem[] | null;
  model_report_details?: Record<string, any> | null;
}

export interface AnalyzeDatasetResponse {
  dataset_id: string;
  status: string;
  pages_analyzed: number;
  high_priority_count: number;
  critical_count: number;
}

export interface WatchlistItem {
  id: number;
  page_id: string;
  dataset_id: string;
  notes?: string | null;
  created_at?: string | null;
  page_title?: string | null;
  url?: string | null;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null;
  action?: string | null;
  opportunity_score?: number | null;
}

export interface WatchlistToggleResponse {
  page_id: string;
  dataset_id: string;
  is_starred: boolean;
  message: string;
}

export interface ImpactAction {
  id: number;
  page_id: string;
  dataset_id: string;
  action_type: string;
  status: string;
  notes?: string | null;
  marked_at?: string | null;
  before_metrics?: Record<string, any> | null;
  after_metrics?: Record<string, any> | null;
  page_title?: string | null;
  url?: string | null;
}

export interface ImpactSummary {
  total_actions: number;
  completed_actions: number;
  actions_by_type: Record<string, number>;
  items: ImpactAction[];
  has_subsequent_snapshot: boolean;
  notice: string;
}

export interface AnalysisJob {
  job_id: string;
  dataset_id: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress_pct: number;
  stage_label: string;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface OpportunityMapPoint {
  page_id: string;
  title: string;
  url: string;
  visibility: number;
  opportunity_score: number;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  action: string;
  position: number;
  ctr: number;
  freshness_days: number;
}

export interface OpportunityMapData {
  dataset_id: string;
  total_points: number;
  points: OpportunityMapPoint[];
}

export interface AttentionCenterItem {
  page_id: string;
  title: string;
  url?: string | null;
  opportunity_score: number;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  action: string;
  primary_reason: string;
  visibility?: number | null;
  ctr?: number | null;
  position?: number | null;
  freshness_days?: number | null;
}

export interface AttentionCenterData {
  dataset_id: string;
  critical_items: AttentionCenterItem[];
  at_risk_items: AttentionCenterItem[];
  stable_items: AttentionCenterItem[];
  content_brief: {
    headline: string;
    key_takeaways: string[];
    suggested_action: string;
  };
}

export const api = {
  getDatasets: () => request<DatasetSummary[]>("/datasets"),
  getDataset: (id: string) => request<DatasetDetail>(`/datasets/${id}`),
  uploadDataset: async (formData: FormData): Promise<ValidationSummary> => {
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/datasets/upload`, {
      method: "POST",
      body: formData,
      headers,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },
  analyzeDataset: (id: string) => request<AnalyzeDatasetResponse>(`/datasets/${id}/analyze`, { method: "POST" }),
  deleteDataset: (id: string) => request<{ status: string; message: string }>(`/datasets/${id}`, { method: "DELETE" }),
  getDatasetReadiness: (id: string) => request<ReadinessReport>(`/datasets/${id}/readiness`),
  getDatasetCapabilities: (id: string) => request<Record<string, any>>(`/datasets/${id}/capabilities`),
  getDatasetMapping: (id: string) => request<{ dataset_id: string; mapping: CanonicalMappingItem[] }>(`/datasets/${id}/mapping`),
  getDatasetProfile: (id: string) => request<Record<string, any>>(`/datasets/${id}/profile`),
  getDatasetModel: (id: string) => request<Record<string, any>>(`/datasets/${id}/model`),

  // Analysis Jobs
  createAnalysisJob: (datasetId: string) => request<AnalysisJob>(`/datasets/${datasetId}/jobs`, { method: "POST" }),
  getAnalysisJob: (datasetId: string, jobId: string) => request<AnalysisJob>(`/datasets/${datasetId}/jobs/${jobId}`),
  listAnalysisJobs: (datasetId: string) => request<AnalysisJob[]>(`/datasets/${datasetId}/jobs`),

  getOverview: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<OverviewKPIs>(`/overview${qs}`);
  },
  getOpportunities: (params: Record<string, any> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "" && v !== "ALL") {
        qs.append(k, String(v));
      }
    });
    return request<PaginatedOpportunities>(`/opportunities?${qs.toString()}`);
  },
  getPageIntelligence: (pageId: string) => request<PageIntelligence>(`/opportunities/${pageId}`),
  getModelMetrics: () => request<any>("/model/metrics"),
  getModelFeatures: () => request<any>("/model/features"),
  getArchetypes: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<any>(`/archetypes${qs}`);
  },
  getTrends: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<any>(`/trends${qs}`);
  },

  // Opportunity Map & Attention Center
  getOpportunityMap: (datasetId?: string, limit: number = 250) => {
    const qs = new URLSearchParams();
    qs.append("limit", String(limit));
    if (datasetId) qs.append("dataset_id", datasetId);
    return request<OpportunityMapData>(`/opportunity-map?${qs.toString()}`);
  },
  getAttentionCenter: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<AttentionCenterData>(`/attention-center${qs}`);
  },

  // Watchlist
  getWatchlist: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<WatchlistItem[]>(`/watchlist${qs}`);
  },
  getWatchlistIds: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<string[]>(`/watchlist/ids${qs}`);
  },
  toggleWatchlist: (pageId: string, datasetId?: string, notes?: string) => {
    const qs = new URLSearchParams();
    if (datasetId) qs.append("dataset_id", datasetId);
    if (notes) qs.append("notes", notes);
    const qStr = qs.toString() ? `?${qs.toString()}` : "";
    return request<WatchlistToggleResponse>(`/watchlist/${pageId}${qStr}`, { method: "POST" });
  },

  // Impact Tracking & Workflow
  getImpactSummary: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<ImpactSummary>(`/impact${qs}`);
  },
  markImpactAction: (data: { page_id: string; action_type: string; notes?: string; dataset_id?: string }) =>
    request<ImpactAction>("/impact/mark", { method: "POST", body: JSON.stringify(data) }),
  updateActionStatus: (actionId: number, status: string, notes?: string) =>
    request<ImpactAction>(`/impact/actions/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, notes }),
    }),
  setPageActionState: (data: { page_id: string; state: string; dataset_id?: string; note?: string }) =>
    request<{ status: string; page_id: string; action_state: string }>("/impact/set-state", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getPageImpact: (pageId: string, datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<ImpactAction[]>(`/impact/${pageId}${qs}`);
  },

  // Analysis Runs
  getAnalysisRuns: (datasetId?: string) => {
    const qs = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : "";
    return request<AnalysisRunItem[]>(`/runs${qs}`);
  },

  // Exports
  exportCsvUrl: (priority?: string, action?: string, datasetId?: string) => {
    const qs = new URLSearchParams();
    if (priority && priority !== "ALL") qs.append("priority", priority);
    if (action && action !== "ALL") qs.append("action", action);
    if (datasetId) qs.append("dataset_id", datasetId);
    return `${API_BASE}/export/csv?${qs.toString()}`;
  },
  getEvidencePdfUrl: (datasetId?: string, limit: number = 35) => {
    const qs = new URLSearchParams();
    qs.append("limit", String(limit));
    if (datasetId) qs.append("dataset_id", datasetId);
    return `${API_BASE}/export/evidence/pdf?${qs.toString()}`;
  },
  getEvidenceDocxUrl: (datasetId?: string, limit: number = 50) => {
    const qs = new URLSearchParams();
    qs.append("limit", String(limit));
    if (datasetId) qs.append("dataset_id", datasetId);
    return `${API_BASE}/export/evidence/docx?${qs.toString()}`;
  },
  getEvidenceXlsxUrl: (datasetId?: string, limit: number = 250) => {
    const qs = new URLSearchParams();
    qs.append("limit", String(limit));
    if (datasetId) qs.append("dataset_id", datasetId);
    return `${API_BASE}/export/evidence/xlsx?${qs.toString()}`;
  },

  // Auth & Onboarding
  login: (data: any) => request<any>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (data: any) => request<any>("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  sendOtp: (data: { email: string; full_name?: string }) =>
    request<any>("/auth/send-otp", { method: "POST", body: JSON.stringify(data) }),
  verifyOtp: (data: { email: string; otp: string }) =>
    request<any>("/auth/verify-otp", { method: "POST", body: JSON.stringify(data) }),
  verifyEmail: (data: { email: string; token: string }) =>
    request<any>("/auth/verify-email", { method: "POST", body: JSON.stringify(data) }),
  resendVerification: (data: { email: string }) =>
    request<any>("/auth/resend-verification", { method: "POST", body: JSON.stringify(data) }),
  cancelVerification: (email: string) =>
    request<any>("/auth/cancel-verification", { method: "POST", body: JSON.stringify({ email }) }),
  completeOnboarding: (data: { onboarded: boolean; primary_goal?: string }) =>
    request<any>("/auth/onboarding", { method: "POST", body: JSON.stringify(data) }),
  getMe: () => request<any>("/auth/me"),

  chatAI: (data: { message: string; page_id?: string; dataset_id?: string }) =>
    request<any>("/ai/chat", { method: "POST", body: JSON.stringify(data) }),
  analyzePage: (data: any) =>
    request<any>("/analyze", { method: "POST", body: JSON.stringify(data) }),
};

