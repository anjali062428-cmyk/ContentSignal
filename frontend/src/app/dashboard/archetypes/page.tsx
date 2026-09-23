"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Compass, Info, ArrowRight, UploadCloud, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, ErrorState } from "@/components/UIStates";

export default function ArchetypesPage() {
  const { activeDataset } = useDataset();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchArchetypes = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getArchetypes(activeDataset?.dataset_id);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load content archetypes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArchetypes();
  }, [activeDataset?.dataset_id]);

  if (loading) return <LoadingState message="Calculating content performance groups..." />;
  if (error || !data) return <ErrorState title="Failed to Load Groups" message={error || "Error"} onRetry={fetchArchetypes} />;

  const profiles = Object.values(data.profiles || {});
  const currentRecords = data.row_count ?? activeDataset?.row_count ?? 0;
  const minRequired = data.min_required ?? 50;
  const additionalNeeded = data.additional_needed ?? Math.max(0, minRequired - currentRecords);

  const getActionColor = (action: string) => {
    switch (action) {
      case "PROTECT": return "bg-emerald-600 text-white";
      case "REFRESH": return "bg-blue-600 text-white";
      case "OPTIMIZE": return "bg-purple-600 text-white";
      case "INVESTIGATE": return "bg-amber-600 text-white";
      default: return "bg-slate-600 text-white";
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
          Content Performance Groups
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          Behavioral performance groups identifying structural profiles across the {currentRecords > 0 ? currentRecords.toLocaleString() : (activeDataset ? activeDataset.row_count.toLocaleString() : "30,000")}-page catalog ({activeDataset?.name || "Active Dataset"}).
        </p>
      </div>

      {/* Semantic Caution Banner */}
      <div className="p-4 rounded-2xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/50 dark:bg-blue-950/30 flex items-start gap-3 text-xs">
        <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
        <div className="space-y-1 text-slate-700 dark:text-slate-300">
          <span className="font-bold text-blue-900 dark:text-blue-300">Behavioral vs. Semantic Clustering</span>
          <p>{data.interpretability_notice || "Clusters are grouped purely by observable quantitative search and engagement patterns."}</p>
        </div>
      </div>

      {/* Archetype Cards Grid or Polished Intentional Unavailable State */}
      {profiles.length === 0 || data.available === false ? (
        <div className="glass-card p-6 sm:p-10 rounded-2xl border border-slate-200 dark:border-slate-800 text-center space-y-6 max-w-2xl mx-auto my-6 shadow-sm">
          {/* Status Badge & Icon */}
          <div className="flex flex-col items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <AlertCircle className="w-3.5 h-3.5" />
              {data.status_badge || (currentRecords < 50 ? "Insufficient data" : "Insufficient variance")}
            </span>
            <div className="w-14 h-14 rounded-2xl bg-amber-500/10 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center mt-1">
              <Compass className="w-7 h-7" />
            </div>
          </div>

          {/* Heading & Explanation */}
          <div className="space-y-2 max-w-lg mx-auto">
            <h3 className="text-xl font-display font-bold text-slate-900 dark:text-white">
              Groups unavailable for this dataset
            </h3>
            <p className="text-sm text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
              Groups require enough records and behavioral variation to form reliable performance profiles.
            </p>
            {data.details && (
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-normal pt-1">
                {data.details}
              </p>
            )}
          </div>

          {/* 3-Stat Record Requirement Box */}
          <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-center">
            <div className="space-y-1">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                Current Records
              </span>
              <span className="text-xl sm:text-2xl font-display font-bold text-slate-900 dark:text-white font-mono block">
                {currentRecords}
              </span>
            </div>
            <div className="border-x border-slate-200 dark:border-slate-800 space-y-1">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                Minimum Required
              </span>
              <span className="text-xl sm:text-2xl font-display font-bold text-slate-900 dark:text-white font-mono block">
                {minRequired}
              </span>
            </div>
            <div className="space-y-1">
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                Additional Needed
              </span>
              <span className="text-xl sm:text-2xl font-display font-bold text-amber-600 dark:text-amber-400 font-mono block">
                {additionalNeeded}
              </span>
            </div>
          </div>

          {/* Missing Evidence Breakdown (for >=50 rows with insufficient variance) */}
          {data.missing_evidence && data.missing_evidence.length > 0 && (
            <div className="text-left bg-amber-500/5 dark:bg-slate-900/80 p-4 rounded-xl border border-amber-500/20 dark:border-slate-800 text-xs space-y-2">
              <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-amber-500" />
                Missing Behavioral Evidence:
              </span>
              <ul className="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1 font-mono text-[11px]">
                {data.missing_evidence.map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Helpful Action CTA */}
          <div className="pt-2">
            <Link
              href="/dashboard/datasets"
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all hover:shadow"
            >
              <UploadCloud className="w-4 h-4" />
              Upload a larger dataset
              <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {profiles.map((p: any) => (
            <div
              key={p.cluster_id}
              className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 transition-all shadow-sm"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-400">
                    GROUP #{p.cluster_id}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${getActionColor(p.recommended_action)}`}>
                    {p.recommended_action}
                  </span>
                </div>

                <h3 className="text-lg font-display font-bold text-slate-900 dark:text-white">
                  {p.archetype_name}
                </h3>

                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-display font-extrabold text-slate-900 dark:text-white">
                    {p.size.toLocaleString()}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    pages ({p.share_pct}%)
                  </span>
                </div>
              </div>

              {/* Profile Metrics */}
              <div className="space-y-2 pt-2 border-t border-slate-200/80 dark:border-slate-800/80 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Median Visibility:</span>
                  <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                    {p.median_impressions !== undefined ? p.median_impressions.toLocaleString() : "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Median Click Rate:</span>
                  <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                    {p.median_ctr !== undefined ? `${p.median_ctr.toFixed(2)}%` : "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Median Position:</span>
                  <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                    {p.median_position === 0 || p.median_position === undefined ? "—" : p.median_position.toFixed(1)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Median Freshness:</span>
                  <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                    {p.median_days_since_update !== undefined ? `${p.median_days_since_update.toFixed(0)}d` : "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Median Engagement:</span>
                  <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                    {p.median_engagement_rate !== undefined ? `${p.median_engagement_rate.toFixed(1)}%` : "—"}
                  </span>
                </div>
              </div>

              <Link
                href={`/dashboard/opportunities?action=${p.recommended_action}`}
                className="inline-flex items-center justify-center gap-1.5 w-full py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-900 dark:text-white transition-colors"
              >
                Filter Queue by Action ({p.recommended_action})
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}