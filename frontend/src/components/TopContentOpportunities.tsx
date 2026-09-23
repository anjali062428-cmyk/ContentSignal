"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { OpportunityMapPoint, OverviewKPIs } from "@/lib/api";

interface Props {
  points: OpportunityMapPoint[];
  overview?: OverviewKPIs | null;
  loading?: boolean;
}

export function TopContentOpportunities({ points, overview, loading = false }: Props) {
  const [filter, setFilter] = useState<string>("ALL");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const filteredPoints = useMemo(() => {
    if (!points || points.length === 0) return [];
    let result = points;
    if (filter === "CRITICAL") {
      result = points.filter((p) => p.priority === "CRITICAL");
    } else if (filter === "HIGH") {
      result = points.filter((p) => p.priority === "HIGH" || p.priority === "CRITICAL");
    } else if (filter === "REFRESH") {
      result = points.filter((p) => p.action === "REFRESH");
    } else if (filter === "OPTIMIZE") {
      result = points.filter((p) => p.action === "OPTIMIZE");
    }
    return [...result].sort((a, b) => b.opportunity_score - a.opportunity_score);
  }, [points, filter]);

  // Show top 8 highest-opportunity items
  const topItems = filteredPoints.slice(0, 8);

  const priorityBadgeClass = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50";
      case "HIGH":
        return "bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50";
      case "MEDIUM":
        return "bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-900/50";
      default:
        return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700";
    }
  };

  const barColorClass = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-gradient-to-r from-rose-500 to-amber-500";
      case "HIGH":
        return "bg-gradient-to-r from-amber-500 to-teal-400";
      default:
        return "bg-gradient-to-r from-teal-600 to-emerald-400";
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 h-[380px] flex items-center justify-center">
        <p className="text-xs text-slate-400 animate-pulse">Loading top content opportunities...</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-5">
      {/* Header with Title and 'View All Opportunities' Link */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-display font-bold text-slate-900 dark:text-white uppercase tracking-wide">
              Top Content Opportunities
            </h3>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/50 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-800 font-semibold">
              Highest Score First
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Pages with the highest opportunity scores and recommended actions.
          </p>
        </div>

        <Link
          href="/dashboard/opportunities"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-600 hover:text-teal-500 dark:text-teal-400 dark:hover:text-teal-300 shrink-0 transition-colors"
        >
          View All Opportunities &rarr;
        </Link>
      </div>

      {/* Optional Real Summary Strip from Dataset KPIs */}
      {overview && (
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 p-2.5 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />
            <span className="text-[11px] font-sans text-slate-500 dark:text-slate-400">Critical:</span>
            <span className="font-bold">{overview.critical_pages.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
            <span className="text-[11px] font-sans text-slate-500 dark:text-slate-400">High Priority:</span>
            <span className="font-bold">{overview.high_priority_opportunities.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
            <span className="text-[11px] font-sans text-slate-500 dark:text-slate-400">Refresh:</span>
            <span className="font-bold">{overview.pages_to_refresh.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20 font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0" />
            <span className="text-[11px] font-sans text-slate-500 dark:text-slate-400">Optimize:</span>
            <span className="font-bold">{(overview.action_distribution?.OPTIMIZE ?? overview.ctr_opportunities).toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Filter Buttons */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
        {[
          { id: "ALL", label: "All" },
          { id: "CRITICAL", label: "Critical" },
          { id: "HIGH", label: "High Priority" },
          { id: "REFRESH", label: "Refresh" },
          { id: "OPTIMIZE", label: "Optimize" },
        ].map((f) => {
          const isActive = filter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
                isActive
                  ? "bg-teal-600 text-white dark:bg-teal-500 dark:text-slate-950 font-semibold shadow-sm ring-1 ring-teal-500"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-700/70"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Horizontal Bar Chart Rows */}
      {topItems.length > 0 ? (
        <div className="space-y-2 pt-1">
          {topItems.map((item) => {
            const isHovered = hoveredId === item.page_id;
            return (
              <div key={item.page_id} className="relative">
                <Link
                  href={`/dashboard/page/${item.page_id}`}
                  className="group block p-3 rounded-xl bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800 hover:border-teal-500/50 dark:hover:border-teal-500/50 transition-all duration-150"
                  onMouseEnter={() => setHoveredId(item.page_id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    {/* Left: Content title and priority badge */}
                    <div className="sm:w-2/5 min-w-0 flex items-center gap-2">
                      <span
                        className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white truncate group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors"
                        title={item.title || item.page_id}
                      >
                        {item.title || item.page_id}
                      </span>
                      <span className={`text-[10px] font-mono uppercase font-bold px-1.5 py-0.5 rounded shrink-0 ${priorityBadgeClass(item.priority)}`}>
                        {item.priority}
                      </span>
                    </div>

                    {/* Center & Right: Progress bar and numerical score */}
                    <div className="sm:w-3/5 flex items-center gap-3 min-w-0">
                      <div className="flex-1 h-3 bg-slate-200/70 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${barColorClass(item.priority)} ${isHovered ? "brightness-110" : "opacity-95"}`}
                          style={{ width: `${Math.min(Math.max(item.opportunity_score, 4), 100)}%` }}
                        />
                      </div>

                      {/* Numerical Opportunity Score */}
                      <span className="font-mono font-bold text-xs sm:text-sm text-slate-900 dark:text-white w-8 sm:w-10 text-right shrink-0">
                        {Math.round(item.opportunity_score)}
                      </span>
                    </div>
                  </div>
                </Link>

                {/* Hover Tooltip */}
                {isHovered && (
                  <div className="absolute right-4 sm:right-16 bottom-full mb-2 z-30 pointer-events-none p-3 rounded-xl bg-slate-900 dark:bg-slate-950 text-white border border-slate-700/90 shadow-2xl text-xs space-y-1.5 w-64 animate-in fade-in zoom-in-95 duration-100">
                    <div className="font-bold text-slate-100 line-clamp-1">
                      {item.title || item.page_id}
                    </div>
                    <div className="pt-1 border-t border-slate-800 space-y-1 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Opportunity Score:</span>
                        <span className="font-mono font-bold text-teal-400">{item.opportunity_score}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Priority:</span>
                        <span className="font-semibold text-slate-200">{item.priority}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">CTR:</span>
                        <span className="font-mono text-slate-200">{item.ctr}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Impressions:</span>
                        <span className="font-mono text-slate-200">{item.visibility.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Recommended Action:</span>
                        <span className="font-semibold text-emerald-400">{item.action}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Empty State */
        <div className="py-10 px-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 text-center space-y-3">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            No opportunities found for this filter.
          </p>
          <button
            onClick={() => setFilter("ALL")}
            className="text-xs px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold transition-colors shadow-sm"
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Footer Info */}
      <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/80 text-xs">
        <span className="text-slate-400 text-[11px]">
          Showing top {topItems.length} of {filteredPoints.length} matching pages
        </span>
        <Link
          href="/dashboard/opportunities"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-600 hover:text-teal-500 dark:text-teal-400 dark:hover:text-teal-300 transition-colors"
        >
          View All Opportunities &rarr;
        </Link>
      </div>
    </div>
  );
}
