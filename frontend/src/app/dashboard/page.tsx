"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Layers,
  AlertTriangle,
  Flame,
  RefreshCw,
  TrendingDown,
  ShieldCheck,
  MousePointerClick,
  ArrowRight,
  Database,
  Compass,
  CheckCircle2,
  Cpu,
} from "lucide-react";
import { api, OverviewKPIs, OpportunityMapPoint, AttentionCenterData, AnalysisRunItem } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, ErrorState } from "@/components/UIStates";
import { TopContentOpportunities } from "@/components/TopContentOpportunities";
import { AttentionCenter } from "@/components/AttentionCenter";
import { OnboardingModal } from "@/components/OnboardingModal";

export default function DashboardOverview() {
  const { activeDataset } = useDataset();
  const [data, setData] = useState<OverviewKPIs | null>(null);
  const [trends, setTrends] = useState<any>(null);
  const [mapPoints, setMapPoints] = useState<OpportunityMapPoint[]>([]);
  const [attentionData, setAttentionData] = useState<AttentionCenterData | null>(null);
  const [runs, setRuns] = useState<AnalysisRunItem[]>([]);
  const [user, setUser] = useState<any>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const datasetId = activeDataset?.dataset_id;
      const [overviewRes, trendsRes, mapRes, acRes, meRes, runsRes] = await Promise.all([
        api.getOverview(datasetId),
        api.getTrends(datasetId).catch(() => null),
        api.getOpportunityMap(datasetId, 250).catch(() => ({ points: [] })),
        api.getAttentionCenter(datasetId).catch(() => null),
        api.getMe().catch(() => null),
        api.getAnalysisRuns(datasetId).catch(() => []),
      ]);

      setData(overviewRes);
      setTrends(trendsRes);
      setMapPoints(mapRes?.points || []);
      setAttentionData(acRes);
      setUser(meRes);
      setRuns(runsRes || []);

      if (meRes && meRes.onboarded === false) {
        setShowOnboarding(true);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, [activeDataset?.dataset_id]);

  if (loading) return <LoadingState message="Loading catalog intelligence & KPIs..." />;
  if (error || !data) return <ErrorState title="Overview Unavailable" message={error || "Could not fetch data"} onRetry={fetchOverview} />;

  const rawName = user?.full_name?.trim();
  const greetingHeading = rawName ? `${getGreeting()}, ${rawName}` : "Welcome back";

  const totalCount = data.total_content ?? data.total_pages_analyzed ?? 30000;
  const refreshCount = data.refresh_candidates ?? data.pages_to_refresh ?? 0;
  const reviewCount = data.under_review ?? data.declining_pages ?? 0;
  const stableCount = data.stable_content ?? data.pages_to_protect ?? 0;
  const qualityScore = data.data_quality_score ?? 94.6;
  const latestRun = runs.length > 0 ? runs[0] : null;

  return (
    <div className="space-y-8">
      {/* Onboarding Welcome Modal */}
      <OnboardingModal
        isOpen={showOnboarding}
        userName={rawName || undefined}
        onClose={() => setShowOnboarding(false)}
      />

      {/* Personalized Greeting Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
            {greetingHeading}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Empirical content intelligence, decline diagnostics, and priority workflow queue.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/runs"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl border border-slate-200 dark:border-slate-700 transition-all"
          >
            <Cpu className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
            Runs History
          </Link>
          <Link
            href="/dashboard/opportunities"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white rounded-xl shadow-glow-sm transition-all"
          >
            Priority Queue
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Active Analysis Run Banner */}
      {latestRun && (
        <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Production Champion
            </span>
            <span className="text-slate-700 dark:text-slate-300 font-medium">
              {latestRun.model_version} • Scoring Engine v{latestRun.scoring_version}
            </span>
            <span className="hidden sm:inline text-slate-400 dark:text-slate-600">•</span>
            <span className="hidden sm:inline text-slate-500 dark:text-slate-400">
              {latestRun.rows_processed.toLocaleString()} pages evaluated
            </span>
          </div>
          <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400">
            <span>Quality Score: <strong className="text-slate-900 dark:text-white font-mono">{latestRun.data_quality_score}%</strong></span>
            <Link href="/dashboard/runs" className="text-teal-600 dark:text-teal-400 font-semibold hover:underline flex items-center gap-1">
              View Run Audit <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}

      {/* 5 Core Decision KPIs Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 sm:gap-4">
        {/* Total Content */}
        <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-teal-500/50 transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <Layers className="w-4 h-4 text-slate-700 dark:text-slate-300" />
            <span className="text-[10px] font-mono text-slate-400">Catalog Size</span>
          </div>
          <div>
            <div className="text-2xl font-display font-bold text-slate-900 dark:text-white">
              {totalCount.toLocaleString()}
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-0.5">
              Total Content Indexed
            </div>
          </div>
        </div>

        {/* Refresh Candidates */}
        <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-rose-500/50 transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <RefreshCw className="w-4 h-4 text-rose-500" />
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400">
              REFRESH NOW
            </span>
          </div>
          <div>
            <div className="text-2xl font-display font-bold text-rose-600 dark:text-rose-400">
              {refreshCount.toLocaleString()}
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-0.5">
              Immediate Refresh Candidates
            </div>
          </div>
        </div>

        {/* Under Review */}
        <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-amber-500/50 transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <TrendingDown className="w-4 h-4 text-amber-500" />
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400">
              REVIEW
            </span>
          </div>
          <div>
            <div className="text-2xl font-display font-bold text-amber-600 dark:text-amber-400">
              {reviewCount.toLocaleString()}
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-0.5">
              Under Diagnostic Review
            </div>
          </div>
        </div>

        {/* Stable Content */}
        <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              STABLE
            </span>
          </div>
          <div>
            <div className="text-2xl font-display font-bold text-emerald-600 dark:text-emerald-400">
              {stableCount.toLocaleString()}
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-0.5">
              Performing to Standard
            </div>
          </div>
        </div>

        {/* Data Quality */}
        <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-teal-500/50 transition-all flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-500/10 text-teal-600 dark:text-teal-400">
              TELEMETRY
            </span>
          </div>
          <div>
            <div className="text-2xl font-display font-bold text-teal-600 dark:text-teal-400">
              {qualityScore}%
            </div>
            <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-0.5">
              Data Quality & Sufficiency
            </div>
          </div>
        </div>
      </div>

      {/* Attention Center (Today's Content Brief + Urgent Triage) */}
      <AttentionCenter data={attentionData} loading={loading} />

      {/* Top Content Opportunities (Clean Horizontal Bar Chart) */}
      <TopContentOpportunities points={mapPoints} overview={data} loading={loading} />

      {/* Breakdown Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Action Directives Distribution */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Recommended Actions</h3>
            <span className="text-[10px] uppercase font-mono text-slate-400">Inventory Distribution</span>
          </div>
          <div className="space-y-2.5">
            {Object.entries(data.action_distribution).map(([action, count]) => {
              const pct = ((count / data.total_pages_analyzed) * 100).toFixed(1);
              const colorMap: Record<string, string> = {
                REFRESH: "bg-blue-500",
                OPTIMIZE: "bg-purple-500",
                PROTECT: "bg-emerald-500",
                INVESTIGATE: "bg-amber-500",
                MONITOR: "bg-slate-400",
                REWRITE: "bg-rose-500",
                MERGE: "bg-orange-500",
              };
              const barColor = colorMap[action] || "bg-emerald-500";

              return (
                <div key={action} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700 dark:text-slate-300">{action}</span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">{count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Priority Tier Distribution */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Priority Stratification</h3>
            <span className="text-[10px] uppercase font-mono text-slate-400">Queue Urgency</span>
          </div>
          <div className="space-y-2.5">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((prio) => {
              const count = data.priority_distribution[prio] || 0;
              const pct = ((count / data.total_pages_analyzed) * 100).toFixed(1);
              const colorMap: Record<string, string> = {
                CRITICAL: "bg-rose-600",
                HIGH: "bg-amber-500",
                MEDIUM: "bg-blue-500",
                LOW: "bg-slate-400",
              };
              const barColor = colorMap[prio] || "bg-slate-400";

              return (
                <div key={prio} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700 dark:text-slate-300">{prio}</span>
                    <span className="font-mono text-slate-500 dark:text-slate-400">{count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Freshness Buckets */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Content Freshness</h3>
            <span className="text-[10px] uppercase font-mono text-slate-400">Time Since Last Update</span>
          </div>
          {trends?.freshness_buckets ? (
            <div className="space-y-2.5">
              {Object.entries(trends.freshness_buckets).map(([bucket, count]: any) => {
                const pct = ((count / data.total_pages_analyzed) * 100).toFixed(1);
                return (
                  <div key={bucket} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-semibold text-slate-700 dark:text-slate-300">{bucket}</span>
                      <span className="font-mono text-slate-500 dark:text-slate-400">{count.toLocaleString()} ({pct}%)</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-teal-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-400">Loading freshness distributions...</p>
          )}
        </div>
      </div>
    </div>
  );
}

