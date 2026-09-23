"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AttentionCenterData, AttentionCenterItem } from "@/lib/api";
import { Flame, AlertTriangle, ShieldCheck, ArrowRight, FileText, CheckCircle2, ChevronRight, Clock, MousePointerClick } from "lucide-react";

interface Props {
  data: AttentionCenterData | null;
  loading?: boolean;
}

export function AttentionCenter({ data, loading = false }: Props) {
  const [activeTab, setActiveTab] = useState<"critical" | "at_risk" | "stable">("critical");

  if (loading || !data) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded animate-pulse" />
        <div className="h-24 w-full bg-slate-100 dark:bg-slate-800/50 rounded animate-pulse" />
      </div>
    );
  }

  const currentItems: AttentionCenterItem[] =
    activeTab === "critical"
      ? data.critical_items
      : activeTab === "at_risk"
      ? data.at_risk_items
      : data.stable_items;

  return (
    <div className="space-y-6">
      {/* Today's Content Brief */}
      <div className="glass-card p-6 rounded-3xl border border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 via-transparent to-teal-500/5 space-y-4 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <FileText className="w-4 h-4" />
          </span>
          <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 font-mono">
            Today&apos;s Content Brief
          </h3>
        </div>

        <div className="space-y-3">
          <p className="text-lg font-display font-bold text-slate-900 dark:text-white leading-snug">
            {data.content_brief.headline}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
            {data.content_brief.key_takeaways.map((takeaway, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60 flex items-start gap-2.5"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                  {takeaway}
                </p>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400">
              <b>Recommended Next Step:</b> {data.content_brief.suggested_action}
            </span>
            <Link
              href="/dashboard/opportunities"
              className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
            >
              Open Full Queue <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Attention Center Triage */}
      <div className="glass-card p-6 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-display font-bold text-slate-900 dark:text-white">
              Attention Center
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Real-time triage prioritized by decay signal urgency, opportunity score, and content stability.
            </p>
          </div>

          {/* Triage Tabs */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <button
              onClick={() => setActiveTab("critical")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "critical"
                  ? "bg-rose-500 text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              Critical ({data.critical_items.length})
            </button>
            <button
              onClick={() => setActiveTab("at_risk")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "at_risk"
                  ? "bg-amber-500 text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              At Risk ({data.at_risk_items.length})
            </button>
            <button
              onClick={() => setActiveTab("stable")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "stable"
                  ? "bg-emerald-500 text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Stable ({data.stable_items.length})
            </button>
          </div>
        </div>

        {/* Items List */}
        <div className="space-y-3">
          {currentItems.map((item) => (
            <div
              key={item.page_id}
              className="p-4 rounded-2xl bg-white/60 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-emerald-500/50 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded tracking-wide ${
                      item.priority === "CRITICAL"
                        ? "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border border-rose-200 dark:border-rose-900"
                        : item.priority === "HIGH"
                        ? "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border border-amber-200 dark:border-amber-900"
                        : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900"
                    }`}
                  >
                    {item.priority}
                  </span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {item.action}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Score: <b>{item.opportunity_score}</b>
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                  {item.title}
                </h4>

                <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
                  {item.url && <span className="truncate max-w-[280px]">{item.url}</span>}
                  {item.freshness_days !== undefined && item.freshness_days !== null && item.freshness_days > 0 && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {item.freshness_days}d ago
                    </span>
                  )}
                  {((item.ctr !== undefined && item.ctr !== null && item.ctr > 0) || (item.position !== undefined && item.position !== null && item.position > 0)) && (
                    <span className="flex items-center gap-1">
                      <MousePointerClick className="w-3 h-3 text-slate-400" />
                      {item.ctr !== null && item.ctr !== undefined && item.ctr > 0 ? `${item.ctr}% Click Rate` : ""}
                      {item.ctr && item.position ? " • " : ""}
                      {item.position !== null && item.position !== undefined && item.position > 0 ? `Pos ${item.position}` : ""}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {item.visibility !== undefined && item.visibility !== null && item.visibility > 0 && (
                  <div className="text-right hidden sm:block">
                    <span className="text-xs font-bold text-slate-900 dark:text-white block font-mono">
                      {item.visibility.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-400">Visibility</span>
                  </div>
                )}
                <Link
                  href={`/dashboard/page/${item.page_id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:hover:bg-slate-100 dark:text-slate-900 transition-colors"
                >
                  Review
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
