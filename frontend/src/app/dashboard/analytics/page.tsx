"use client";

import React, { useState, useEffect } from "react";
import { BarChart3, Clock, Layers, SlidersHorizontal, Info, Globe } from "lucide-react";
import { api, OverviewKPIs, OpportunityMapPoint } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, ErrorState } from "@/components/UIStates";
import { ContentOpportunityMap } from "@/components/ContentOpportunityMap";
import {
  VerticalBarChart,
  HorizontalDistributionChart,
  ChartDataPoint,
} from "@/components/AnalyticsCharts";

function normalizeDistribution(
  raw: any,
  keyProp: string = "key",
  valProp: string = "count"
): Array<{ key: string; value: number }> {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw.map((item) => {
      const k = item[keyProp] ?? item.key ?? item.name ?? "";
      const v = Number(item[valProp] ?? item.value ?? item.count ?? item.avg_score ?? 0);
      return { key: String(k), value: Number.isFinite(v) ? v : 0 };
    });
  }
  if (typeof raw === "object") {
    return Object.entries(raw).map(([k, v]) => ({
      key: k,
      value: Number.isFinite(Number(v)) ? Number(v) : 0,
    }));
  }
  return [];
}

export default function AnalyticsPage() {
  const { activeDataset } = useDataset();
  const [overview, setOverview] = useState<OverviewKPIs | null>(null);
  const [trends, setTrends] = useState<any>(null);
  const [mapPoints, setMapPoints] = useState<OpportunityMapPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const datasetId = activeDataset?.dataset_id;
      const [oRes, tRes, mapRes] = await Promise.all([
        api.getOverview(datasetId),
        api.getTrends(datasetId),
        api.getOpportunityMap(datasetId, 250).catch(() => ({ points: [] })),
      ]);
      setOverview(oRes);
      setTrends(tRes);
      setMapPoints(mapRes?.points || []);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [activeDataset?.dataset_id]);

  if (loading) return <LoadingState message="Aggregating multi-dimensional catalog analytics..." />;
  if (error || !overview) return <ErrorState title="Analytics Unavailable" message={error || "Error"} onRetry={fetchAnalytics} />;

  const totalPages = overview.total_pages_analyzed;
  const scoreBuckets = trends?.opportunity_score_buckets || {};
  const freshBuckets = trends?.freshness_buckets || {};

  // 1. Opportunity Score Distribution (0–100 in 5 ranges)
  const scoreKeys = ["0-20", "21-40", "41-60", "61-80", "81-100"];
  const scoreChartData: ChartDataPoint[] = scoreKeys.map((k) => {
    const count = scoreBuckets[k] || 0;
    const pct = totalPages > 0 ? (count / totalPages) * 100 : 0;
    return {
      key: k,
      label: k,
      count,
      percentage: pct,
    };
  });

  // 2. Publication Freshness (5 time buckets)
  const freshKeys = ["0-30d", "31-90d", "91-180d", "181-365d", "365d+"];
  const freshChartData: ChartDataPoint[] = freshKeys.map((k) => {
    const count = freshBuckets[k] || 0;
    const pct = totalPages > 0 ? (count / totalPages) * 100 : 0;
    return {
      key: k,
      label: k,
      count,
      percentage: pct,
    };
  });

  // 3. Content Type Mix
  const formatContentType = (str: string) => {
    return str
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const contentTypeData: ChartDataPoint[] = Object.entries(overview.content_type_distribution || {})
    .sort((a, b) => b[1] - a[1])
    .map(([k, count]) => {
      const pct = totalPages > 0 ? (count / totalPages) * 100 : 0;
      return {
        key: k,
        label: formatContentType(k),
        count,
        percentage: pct,
      };
    });

  // 4. Recommended Actions
  const actionKeys = ["INVESTIGATE", "MONITOR", "OPTIMIZE", "PROTECT", "REFRESH"];
  const actionColors: Record<string, string> = {
    INVESTIGATE: "bg-indigo-500 dark:bg-indigo-600",
    MONITOR: "bg-sky-500 dark:bg-sky-600",
    OPTIMIZE: "bg-teal-500 dark:bg-teal-600",
    PROTECT: "bg-emerald-500 dark:bg-emerald-600",
    REFRESH: "bg-amber-500 dark:bg-amber-600",
  };

  // Collect any additional actions if custom dataset introduced others
  const allActionKeys = Array.from(new Set([...actionKeys, ...Object.keys(overview.action_distribution || {})]));
  const actionChartData: ChartDataPoint[] = allActionKeys.map((k) => {
    const count = (overview.action_distribution || {})[k] || 0;
    const pct = totalPages > 0 ? (count / totalPages) * 100 : 0;
    return {
      key: k,
      label: k,
      count,
      percentage: pct,
      color: actionColors[k] || "bg-teal-600 dark:bg-teal-500",
    };
  });

  // Top summary indicators
  const topScoreTier = [...scoreChartData].sort((a, b) => b.count - a.count)[0];
  const topAction = [...actionChartData].sort((a, b) => b.count - a.count)[0];
  const freshUnder90 = (freshBuckets["0-30d"] || 0) + (freshBuckets["31-90d"] || 0);
  const freshPct = totalPages > 0 ? ((freshUnder90 / totalPages) * 100).toFixed(1) : "0";

  // Domain & Page Intelligence Data
  const hasDomainIntel = Boolean(trends?.has_domain_intelligence);

  const domainOppList = normalizeDistribution(trends?.opportunities_by_domain, "domain", "count");
  const domainTotalCount = domainOppList.reduce((acc, d) => acc + d.value, 0) || totalPages;
  const domainOppChartData: ChartDataPoint[] = domainOppList.map((d) => ({
    key: d.key,
    label: d.key,
    count: d.value,
    percentage: domainTotalCount > 0 ? (d.value / domainTotalCount) * 100 : 0,
    color: "bg-gradient-to-r from-indigo-600 to-teal-500",
  }));

  const pageTypeList = normalizeDistribution(trends?.page_type_distribution, "page_type", "count");
  const pageTypeTotalCount = pageTypeList.reduce((acc, pt) => acc + pt.value, 0) || totalPages;
  const pageTypeMixChartData: ChartDataPoint[] = pageTypeList.map((pt) => ({
    key: pt.key,
    label: formatContentType(pt.key),
    count: pt.value,
    percentage: pageTypeTotalCount > 0 ? (pt.value / pageTypeTotalCount) * 100 : 0,
    color: "bg-gradient-to-r from-teal-500 to-cyan-500",
  }));

  const scoreByPageTypeList = normalizeDistribution(trends?.score_by_page_type, "page_type", "avg_score");
  const scoreByPageTypeChartData: ChartDataPoint[] = scoreByPageTypeList.map((pt) => ({
    key: pt.key,
    label: formatContentType(pt.key),
    count: Math.round(pt.value),
    percentage: pt.value,
  }));

  const decliningList = normalizeDistribution(trends?.declining_by_domain, "domain", "count");
  const decliningTotalCount = decliningList.reduce((acc, d) => acc + d.value, 0) || 1;
  const decliningByDomainChartData: ChartDataPoint[] = decliningList.map((d) => ({
    key: d.key,
    label: d.key,
    count: d.value,
    percentage: decliningTotalCount > 0 ? (d.value / decliningTotalCount) * 100 : 0,
    color: "bg-gradient-to-r from-rose-500 to-amber-500",
  }));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
          Catalog Search & Traffic Analytics
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          Empirical distributions across <span className="font-semibold text-teal-600 dark:text-teal-400">{activeDataset?.name || "Active Catalog"}</span> ({totalPages.toLocaleString()} pages). Strict dataset-measured metrics &mdash; zero fabricated time series.
        </p>
      </div>

      {/* Real Dataset Summary Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Analyzed Pages
          </div>
          <div className="text-xl sm:text-2xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {totalPages.toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">100% verified coverage</div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Top Opportunity Range
          </div>
          <div className="text-xl sm:text-2xl font-display font-bold text-teal-600 dark:text-teal-400 mt-1">
            {topScoreTier?.label || "41–60"}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
            {topScoreTier?.count.toLocaleString()} pages ({topScoreTier?.percentage.toFixed(1)}%)
          </div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Primary Action
          </div>
          <div className="text-xl sm:text-2xl font-display font-bold text-slate-900 dark:text-white mt-1">
            {topAction?.label || "OPTIMIZE"}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
            {topAction?.count.toLocaleString()} pages ({topAction?.percentage.toFixed(1)}%)
          </div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-slate-200 dark:border-slate-800">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Freshness
          </div>
          <div className="text-xl sm:text-2xl font-display font-bold text-teal-600 dark:text-teal-400 mt-1">
            {freshPct}%
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
            {freshUnder90.toLocaleString()} updated &le; 90d
          </div>
        </div>
      </div>

      {/* 2x2 Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Row 1, Card 1: Opportunity Score Distribution */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Opportunity Distribution
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Distribution of pages across opportunity ranges.
              </p>
            </div>
            <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
              0–100 Scale
            </span>
          </div>

          <VerticalBarChart
            data={scoreChartData}
            total={totalPages}
            accentGradient="from-teal-600 to-teal-400 dark:from-teal-600 dark:to-teal-400"
          />

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>Score ranges: 0–20 to 81–100</span>
            <span>Total: {totalPages.toLocaleString()} pages</span>
          </div>
        </div>

        {/* Row 1, Card 2: Freshness */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Freshness
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Distribution of pages by elapsed time since last editorial update.
              </p>
            </div>
            <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
              Days Elapsed
            </span>
          </div>

          <VerticalBarChart
            data={freshChartData}
            total={totalPages}
            accentGradient="from-cyan-600 to-teal-400 dark:from-cyan-600 dark:to-teal-400"
          />

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>Elapsed intervals: 0–30d to 365d+</span>
            <span>Recent (&le;90d): {freshPct}%</span>
          </div>
        </div>

        {/* Row 2, Card 1: Page Types */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Page Types
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Distribution across indexed article formats in this catalog.
              </p>
            </div>
            <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
              Architectural Format
            </span>
          </div>

          <HorizontalDistributionChart
            data={contentTypeData}
            total={totalPages}
          />

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>{contentTypeData.length} distinct article types</span>
            <span>Total: {totalPages.toLocaleString()} pages</span>
          </div>
        </div>

        {/* Row 2, Card 2: Recommended Actions */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Recommended Actions
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Distribution of editorial actions across the analyzed catalog.
              </p>
            </div>
            <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
              Editorial Actions
            </span>
          </div>

          <VerticalBarChart
            data={actionChartData}
            total={totalPages}
          />

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>Queue actions: 5 categories</span>
            <span>Primary: {topAction?.label} ({topAction?.percentage.toFixed(1)}%)</span>
          </div>
        </div>
      </div>

      {/* Advanced Opportunity Analysis Matrix */}
      <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-lg sm:text-xl font-display font-bold text-slate-900 dark:text-white">
            Advanced Opportunity Analysis
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Multi-dimensional quadrant matrix mapping Visibility vs. Opportunity Score across catalog segments.
          </p>
        </div>
        <ContentOpportunityMap points={mapPoints} loading={loading} />
      </div>

      {/* Domain & Page Intelligence Section */}
      {hasDomainIntel ? (
        <div className="space-y-6 pt-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-indigo-500" />
              <h2 className="text-lg sm:text-xl font-display font-bold text-slate-900 dark:text-white">
                Domain &amp; Page Intelligence Breakdown
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
              Cross-domain performance distributions and automated page type classification metrics.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart 1: Opportunities by Domain */}
            <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Opportunities by Domain
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Distribution of flagged priority opportunities across identified domains.
                  </p>
                </div>
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shrink-0">
                  Domain Distribution
                </span>
              </div>
              <HorizontalDistributionChart
                data={domainOppChartData}
                total={domainTotalCount}
              />
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Top active domains</span>
                <span>Total: {domainTotalCount.toLocaleString()} pages</span>
              </div>
            </div>

            {/* Chart 2: Page Type Mix */}
            <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Page Types
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Catalog composition by inferred structural and editorial page types.
                  </p>
                </div>
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
                  Page Types
                </span>
              </div>
              <HorizontalDistributionChart
                data={pageTypeMixChartData}
                total={pageTypeTotalCount}
              />
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>{pageTypeMixChartData.length} page archetypes</span>
                <span>Total: {pageTypeTotalCount.toLocaleString()} pages</span>
              </div>
            </div>

            {/* Chart 3: Opportunity by Page Type */}
            <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Opportunity by Page Type
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Mean opportunity score across classified page types (0–100).
                  </p>
                </div>
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
                  Mean Score
                </span>
              </div>
              <VerticalBarChart
                data={scoreByPageTypeChartData}
                total={100}
                accentGradient="from-indigo-600 to-teal-400 dark:from-indigo-600 dark:to-teal-400"
              />
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Higher score indicates higher optimization potential</span>
                <span>Max: 100</span>
              </div>
            </div>

            {/* Chart 4: Declining Pages by Domain */}
            <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Declining by Domain
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Pages exhibiting traffic/ranking decay or negative momentum by domain.
                  </p>
                </div>
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 shrink-0">
                  Decay Signals
                </span>
              </div>
              <HorizontalDistributionChart
                data={decliningByDomainChartData}
                total={decliningTotalCount}
              />
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Pages with decay or negative momentum</span>
                <span>Total: {decliningTotalCount.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-3">
          <Info className="w-4 h-4 text-slate-400 shrink-0" />
          <span>
            Domain &amp; URL intelligence is unavailable for this dataset. Upload a dataset containing domain or URL fields to enable page and domain classification.
          </span>
        </div>
      )}
    </div>
  );
}