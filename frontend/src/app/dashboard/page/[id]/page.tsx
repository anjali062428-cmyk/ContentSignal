"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  BrainCircuit,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Clock,
  Eye,
  MousePointerClick,
  Activity,
  Layers,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Info,
  Loader2,
  Globe,
  ExternalLink,
  Star,
  History,
  Calendar,
  Compass,
} from "lucide-react";
import { api, PageIntelligence, ImpactAction } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, ErrorState } from "@/components/UIStates";
import { MarkActionModal } from "@/components/MarkActionModal";

// Safe formatting helpers handling number, null, undefined, NaN
const formatNumber = (val: any): string => {
  if (val === undefined || val === null || val === "" || isNaN(Number(val))) return "—";
  return Number(val).toLocaleString();
};

const formatPercent = (val: any, decimals = 1): string => {
  if (val === undefined || val === null || val === "" || isNaN(Number(val))) return "—";
  return `${Number(val).toFixed(decimals)}%`;
};

const formatMetric = (val: any, decimals = 1, suffix = ""): string => {
  if (val === undefined || val === null || val === "" || isNaN(Number(val))) return "—";
  return `${Number(val).toFixed(decimals)}${suffix}`;
};

const formatScore = (val: any, decimals = 0): string => {
  if (val === undefined || val === null || val === "" || isNaN(Number(val))) return "0";
  return Number(val).toFixed(decimals);
};

export default function PageIntelligencePage() {
  const params = useParams();
  const pageId = params.id as string;
  const { activeDataset } = useDataset();

  const [data, setData] = useState<PageIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Starred Watchlist
  const [isStarred, setIsStarred] = useState(false);
  const [isTogglingWatchlist, setIsTogglingWatchlist] = useState(false);

  // Impact Tracking
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [impactActions, setImpactActions] = useState<ImpactAction[]>([]);
  const [impactNotice, setImpactNotice] = useState<string>("");
  const [impactLoading, setImpactLoading] = useState(false);

  // Grounded AI Assistant
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const fetchDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPageIntelligence(pageId);
      setData(res);

      // Fetch watchlist state
      try {
        const w = await api.getWatchlistIds();
        setIsStarred(w.includes(pageId));
      } catch (e) {
        console.error("Could not fetch watchlist IDs", e);
      }

      // Fetch impact actions
      fetchImpact();
    } catch (err: any) {
      setError(err.message || "Failed to load page intelligence.");
    } finally {
      setLoading(false);
    }
  };

  const fetchImpact = async () => {
    try {
      setImpactLoading(true);
      const res = await api.getPageImpact(pageId);
      setImpactActions(Array.isArray(res) ? res : []);
      setImpactNotice("Interventions lock current 90-day search metrics as a baseline. Subsequent performance deltas will be calculated when the next 90-day dataset ingestion snapshot is uploaded.");
    } catch (err) {
      console.error("Failed to load page impact actions", err);
    } finally {
      setImpactLoading(false);
    }
  };

  const handleToggleWatchlist = async () => {
    if (isTogglingWatchlist) return;
    setIsTogglingWatchlist(true);
    try {
      const res = await api.toggleWatchlist(pageId);
      setIsStarred(res.is_starred);
    } catch (err) {
      console.error("Failed to toggle watchlist", err);
    } finally {
      setIsTogglingWatchlist(false);
    }
  };

  useEffect(() => {
    if (pageId) fetchDetails();
  }, [pageId]);

  const handleAskAI = async () => {
    setAiLoading(true);
    try {
      const res = await api.chatAI({
        message: `Explain why page ${pageId} was flagged and what action should be taken.`,
        page_id: pageId,
      });
      setAiResponse(res.response);
    } catch (err: any) {
      setAiResponse("AI explanation is temporarily unavailable.");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) return <LoadingState message={`Analyzing signals for page ${pageId}...`} />;
  if (error || !data) return <ErrorState title="Page Not Found" message={error || "Could not find page in catalog"} onRetry={fetchDetails} />;

  const m = data.metrics;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/opportunities"
            className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-mono font-bold text-slate-900 dark:text-white">
                {data.page_id}
              </h1>
              <span className="text-xs px-2 py-0.5 rounded-md font-mono bg-slate-100 dark:bg-slate-800 text-slate-500">
                Client: {data.client_id}
              </span>
              {data.domain && (
                <span className="text-xs px-2 py-0.5 rounded-md font-mono bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200/50 dark:border-indigo-800/50">
                  {data.domain}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Content Type: <span className="font-semibold text-slate-700 dark:text-slate-300">{m?.content_type || "Standard"}</span> &bull; Intent: <span className="font-semibold text-slate-700 dark:text-slate-300">{m?.main_intent || "Informational"}</span>
            </p>
          </div>
        </div>

        {/* Header Actions & Score */}
        <div className="flex items-center gap-3">
          {/* Star Watchlist Toggle */}
          <button
            onClick={handleToggleWatchlist}
            disabled={isTogglingWatchlist}
            className={`p-2.5 rounded-xl border transition-all ${
              isStarred
                ? "bg-amber-500/10 border-amber-400/60 text-amber-500 shadow-sm"
                : "border-slate-200 dark:border-slate-800 text-slate-400 hover:text-amber-500 hover:border-amber-300"
            }`}
            title={isStarred ? "Starred in Watchlist (Click to unstar)" : "Add to Starred Watchlist"}
          >
            <Star className={`w-4 h-4 ${isStarred ? "fill-amber-400 text-amber-400" : ""}`} />
          </button>

          {/* Mark Action Button */}
          <button
            onClick={() => setIsActionModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Mark Action</span>
          </button>

          {/* Content Status Badge */}
          {data.content_status && (
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-[10px] uppercase font-mono text-slate-400 font-bold mb-1">Status</span>
              <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${
                data.content_status === "REFRESH NOW"
                  ? "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30"
                  : data.content_status === "REVIEW"
                  ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30"
                  : data.content_status === "STABLE"
                  ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                  : "bg-slate-500/15 text-slate-500 dark:text-slate-400 border-slate-500/30"
              }`}>
                {data.content_status}
              </span>
            </div>
          )}

          {/* Opportunity Score Pill */}
          <div className="glass-card px-4 py-2 rounded-2xl border border-teal-500/30 flex items-center gap-3 shadow-glow-sm">
            <div>
              <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Opportunity</div>
              <div className="text-2xl font-display font-extrabold text-teal-600 dark:text-teal-400">
                {formatScore(data.opportunity_score, 0)} <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
            </div>
            <div className="text-right">
              <span className="inline-block px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-teal-600 text-white">
                {data.confidence_tier ? `${data.confidence_tier} CONF` : data.priority}
              </span>
              <div className="text-[10px] text-slate-400 mt-0.5 font-mono">{formatScore((data.confidence ?? 0.7) * 100, 0)}% Certainty</div>
            </div>
          </div>
        </div>
      </div>

      {/* Domain & Page Intelligence */}
      {(data.domain || data.url || data.page_type) && (
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-indigo-500" />
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Domain &amp; Page Intelligence
              </h2>
            </div>
            {data.page_type && (
              <span className="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200/50 dark:border-indigo-800/50">
                {data.page_type}
              </span>
            )}
          </div>

          {data.page_title && (
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {data.page_title}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Domain</div>
              <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1 truncate font-mono">
                {data.domain || "—"}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">URL</div>
              <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1 truncate font-mono">
                {data.url ? (
                  <a
                    href={data.url.startsWith("http") ? data.url : `https://${data.url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-600 dark:text-emerald-400 hover:underline inline-flex items-center gap-1 max-w-full"
                  >
                    <span className="truncate">{data.url}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Page Type</div>
              <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1">
                {data.page_type || "Other"}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Classified From</div>
              <div className="text-xs font-mono text-slate-600 dark:text-slate-400 mt-1.5">
                {data.page_type_source || "url_pattern"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recommended Action Directive */}
      <div className="p-6 rounded-2xl border border-emerald-300 dark:border-emerald-800/80 bg-gradient-to-r from-emerald-50 via-teal-50/40 to-cyan-50/30 dark:from-emerald-950/40 dark:via-teal-950/20 dark:to-cyan-950/20 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
            Recommended Action:
          </span>
          <span className="px-3 py-0.5 rounded-lg text-xs font-bold bg-emerald-600 text-white">
            {data.action}
          </span>
        </div>
        <p className="text-sm font-semibold text-slate-900 dark:text-white">
          {data.recommendation?.directive || "Review content performance."}
        </p>
        <p className="text-xs text-slate-600 dark:text-slate-400">
          <strong>Decision Rationale:</strong> {data.recommendation?.rationale || "Observed metrics."}
        </p>
      </div>

      {/* 30-Day Comparative Performance Diagnostics (V2 Standard) */}
      {data.comparison_30d?.has_comparison_data ? (
        <div className="glass-card p-6 rounded-2xl border border-teal-500/30 bg-gradient-to-br from-teal-500/5 via-transparent to-emerald-500/5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  30-Day Comparative Performance Analysis
                </h2>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Empirical delta comparison of recent 30 days vs previous 30-day baseline window.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase font-mono bg-teal-500/10 text-teal-700 dark:text-teal-300 border border-teal-500/30">
                {(data.comparison_30d.trend_classification || "stable").replace(/_/g, " ")}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Clicks Delta */}
            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Search Clicks</div>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                  {formatNumber(data.comparison_30d.recent_clicks)}
                  <span className="text-xs font-normal text-slate-400 ml-1">vs {formatNumber(data.comparison_30d.prev_clicks)}</span>
                </span>
              </div>
              <div className={`text-xs font-mono font-semibold flex items-center gap-1 ${
                (data.comparison_30d.clicks_delta_pct ?? 0) < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"
              }`}>
                {(data.comparison_30d.clicks_delta_pct ?? 0) < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <TrendingUp className="w-3.5 h-3.5" />}
                {(data.comparison_30d.clicks_delta_pct ?? 0) > 0 ? `+${data.comparison_30d.clicks_delta_pct}%` : `${data.comparison_30d.clicks_delta_pct ?? 0}%`}
              </div>
            </div>

            {/* Impressions Delta */}
            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Impressions</div>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                  {formatNumber(data.comparison_30d.recent_impressions)}
                  <span className="text-xs font-normal text-slate-400 ml-1">vs {formatNumber(data.comparison_30d.prev_impressions)}</span>
                </span>
              </div>
              <div className={`text-xs font-mono font-semibold flex items-center gap-1 ${
                (data.comparison_30d.impressions_delta_pct ?? 0) < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"
              }`}>
                {(data.comparison_30d.impressions_delta_pct ?? 0) < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <TrendingUp className="w-3.5 h-3.5" />}
                {(data.comparison_30d.impressions_delta_pct ?? 0) > 0 ? `+${data.comparison_30d.impressions_delta_pct}%` : `${data.comparison_30d.impressions_delta_pct ?? 0}%`}
              </div>
            </div>

            {/* CTR Delta */}
            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Click Rate (CTR)</div>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                  {formatPercent(data.comparison_30d.recent_ctr, 2)}
                  <span className="text-xs font-normal text-slate-400 ml-1">vs {formatPercent(data.comparison_30d.prev_ctr, 2)}</span>
                </span>
              </div>
              <div className={`text-xs font-mono font-semibold flex items-center gap-1 ${
                (data.comparison_30d.ctr_delta_pct ?? 0) < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"
              }`}>
                {(data.comparison_30d.ctr_delta_pct ?? 0) < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <TrendingUp className="w-3.5 h-3.5" />}
                {(data.comparison_30d.ctr_delta_pct ?? 0) > 0 ? `+${data.comparison_30d.ctr_delta_pct}%` : `${data.comparison_30d.ctr_delta_pct ?? 0}%`}
              </div>
            </div>

            {/* Data Sufficiency */}
            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Data Sufficiency</div>
              <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1">
                {data.comparison_30d.data_sufficiency?.meets_threshold ? (
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Statistically Sound
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-4 h-4" /> Sparse Telemetry
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                {data.comparison_30d.data_sufficiency?.days_tracked ?? 60} days tracked
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-card p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 flex items-start gap-3">
          <Info className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Comparison data unavailable for this dataset
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              30-day baseline delta comparisons require temporal comparative windows (recent 30 days vs previous 30 days). Aggregated snapshot metrics are available below.
            </p>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Visibility (90d)</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {formatNumber(m?.impressions_90d)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Clicks (90d)</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {formatNumber(m?.clicks_90d)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Click Rate</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {formatPercent(m?.ctr, 2)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Position</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {(m?.avg_position === 0 || m?.avg_position === undefined || m?.avg_position === null) ? "No Rank" : formatMetric(m?.avg_position, 1)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Visits (90d)</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {formatNumber(m?.sessions_90d)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Engagement</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {formatPercent(m?.engagement_rate, 1)}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Freshness</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {m?.days_since_last_update !== undefined && m?.days_since_last_update !== null ? `${formatScore(m?.days_since_last_update, 0)}d` : "—"}
          </div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] font-medium text-slate-500">Word Count</div>
          <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {(m?.word_count && m.word_count > 0) ? formatNumber(m.word_count) : "Unrecorded"}
          </div>
        </div>
      </div>

      {/* Flagged Reasons */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Why This Content Needs Attention (Explainable Diagnostics)
          </h2>
        </div>
        <div className="space-y-3">
          {data.reasons.map((r, idx) => {
            const title = r.title || r.code || r.reason_code;
            const explanation = r.message || r.explanation;
            const changePct = r.change_percent;

            return (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-2"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">{title}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold ${
                      r.severity === "critical"
                        ? "bg-rose-500/15 text-rose-600 dark:text-rose-400"
                        : r.severity === "high"
                        ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                        : "bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                    }`}>
                      {r.severity || "medium"}
                    </span>
                    {changePct !== null && changePct !== undefined && (
                      <span className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded ${
                        changePct < 0 ? "bg-rose-500/10 text-rose-600 dark:text-rose-400" : "bg-emerald-500/10 text-emerald-600"
                      }`}>
                        {changePct > 0 ? `+${changePct}%` : `${changePct}%`}
                      </span>
                    )}
                  </div>
                  <div className="text-right text-xs font-mono text-slate-500">
                    Confidence: {formatScore(((r.confidence ?? data.confidence ?? 0.7) * 100), 0)}%
                  </div>
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-400">{explanation}</p>

                {r.supporting_metric && Object.keys(r.supporting_metric).length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-200/60 dark:border-slate-800/60">
                    {Object.entries(r.supporting_metric).map(([k, v]) => (
                      <span key={k} className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400">
                        {k.replace(/_/g, " ")}: <strong className="text-slate-900 dark:text-slate-200 font-semibold">{typeof v === "number" ? formatNumber(v) : String(v)}</strong>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Model Signals */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-500" />
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Key Signals
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            ML Probability: {formatMetric((data.model_signals?.model_probability ?? 0.5) * 100, 1, "%")}
          </span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {data.model_signals?.causal_disclaimer || "Model signals provide observational attribution and do not imply causal guarantees."}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(data.model_signals?.top_contributions || []).map((c) => (
            <div
              key={c.feature}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-xs space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800 dark:text-slate-200">{c.feature}</span>
                <span
                  className={`font-mono text-[11px] font-bold ${
                    c.direction === "increased" ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500"
                  }`}
                >
                  {c.direction === "increased" ? "+ increased priority" : "- decreased priority"}
                </span>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-[11px]">{c.explanation}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Before & After Impact Tracking History */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-500" />
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Intervention History &amp; Impact Baseline Tracker
              </h2>
              <p className="text-xs text-slate-500">
                Logged editorial interventions with baseline performance snapshots for post-update comparison.
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsActionModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Log Another Action</span>
          </button>
        </div>

        {/* Aggregate Notice Banner */}
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 flex items-center gap-2">
          <Info className="w-4 h-4 text-slate-400 shrink-0" />
          <span>
            {impactNotice || "Interventions lock current 90-day search metrics as a baseline. Subsequent performance deltas will be calculated when the next 90-day dataset ingestion snapshot is uploaded."}
          </span>
        </div>

        {impactActions.length > 0 ? (
          <div className="space-y-3">
            {impactActions.map((act) => (
              <div
                key={act.id}
                className="p-4 rounded-xl bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-md text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      {act.action_type}
                    </span>
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      Intervention #{act.id}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
                      {act.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>
                      {act.marked_at ? new Date(act.marked_at).toLocaleDateString() : "Recorded"}
                    </span>
                  </div>
                </div>

                {act.notes && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 italic bg-slate-50 dark:bg-slate-800/40 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800/60">
                    &ldquo;{act.notes}&rdquo;
                  </p>
                )}

                {/* Baseline Snapshot Chips */}
                {act.before_metrics && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Pre-Intervention Baseline Snapshot
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                        <span className="text-slate-400 text-[10px]">Score:</span>
                        <div className="font-bold text-slate-800 dark:text-slate-200">
                          {act.before_metrics.opportunity_score ?? act.before_metrics.score ?? "—"}
                        </div>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                        <span className="text-slate-400 text-[10px]">Visibility:</span>
                        <div className="font-bold text-slate-800 dark:text-slate-200">
                          {formatNumber(act.before_metrics.impressions_90d)}
                        </div>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                        <span className="text-slate-400 text-[10px]">CTR:</span>
                        <div className="font-bold text-slate-800 dark:text-slate-200">
                          {act.before_metrics.ctr !== undefined && act.before_metrics.ctr !== null ? formatPercent(act.before_metrics.ctr, 2) : "—"}
                        </div>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                        <span className="text-slate-400 text-[10px]">Avg Position:</span>
                        <div className="font-bold text-slate-800 dark:text-slate-200">
                          {act.before_metrics.avg_position !== undefined && act.before_metrics.avg_position !== null ? formatMetric(act.before_metrics.avg_position, 1) : "—"}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 text-center space-y-2">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No editorial actions logged for this page yet.
            </p>
            <button
              onClick={() => setIsActionModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Record First Action</span>
            </button>
          </div>
        )}
      </div>

      {/* Editorial Diagnostic Assistant */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Editorial Diagnostic Assistant
              </h2>
              <p className="text-xs text-slate-500">
                Synthesize an editorial action plan based strictly on observable 30-day comparative measurements.
              </p>
            </div>
          </div>
          <button
            onClick={handleAskAI}
            disabled={aiLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white rounded-xl transition-all shadow-glow-sm disabled:opacity-50"
          >
            {aiLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Compass className="w-4 h-4" />
            )}
            Generate Editorial Diagnostic
          </button>
        </div>

        {aiResponse && (
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {aiResponse}
          </div>
        )}
      </div>

      {/* Mark Action Modal */}
      <MarkActionModal
        isOpen={isActionModalOpen}
        pageId={data.page_id}
        pageTitle={data.page_title || data.page_id}
        initialAction={data.action || "REFRESH"}
        datasetId={data.dataset_id || activeDataset?.dataset_id || "starter-flyrank"}
        onClose={() => setIsActionModalOpen(false)}
        onSuccess={() => {
          fetchImpact();
        }}
      />
    </div>
  );
}