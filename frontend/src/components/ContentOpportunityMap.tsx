"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { OpportunityMapPoint } from "@/lib/api";
import { ExternalLink, Filter, X } from "lucide-react";

interface Props {
  points: OpportunityMapPoint[];
  loading?: boolean;
}

export function ContentOpportunityMap({ points, loading = false }: Props) {
  const [selectedPoint, setSelectedPoint] = useState<OpportunityMapPoint | null>(null);
  const [filterTier, setFilterTier] = useState<string>("ALL");

  const filteredPoints = useMemo(() => {
    if (filterTier === "ALL") return points;
    if (filterTier === "CRITICAL") return points.filter((p) => p.priority === "CRITICAL");
    if (filterTier === "HIGH") return points.filter((p) => p.priority === "HIGH" || p.priority === "CRITICAL");
    if (filterTier === "REFRESH") return points.filter((p) => p.action === "REFRESH");
    if (filterTier === "OPTIMIZE") return points.filter((p) => p.action === "OPTIMIZE");
    return points;
  }, [points, filterTier]);

  // Compute scale boundaries
  const { minVis, maxVis } = useMemo(() => {
    if (!points.length) return { minVis: 100, maxVis: 100000 };
    const visValues = points.map((p) => Math.max(p.visibility, 10));
    return {
      minVis: Math.min(...visValues),
      maxVis: Math.max(...visValues),
    };
  }, [points]);

  // Log scale for X axis to handle heavy skew in organic search impressions
  const logMin = Math.log10(Math.max(minVis, 10));
  const logMax = Math.log10(Math.max(maxVis, 1000));
  const logSpan = Math.max(logMax - logMin, 1);

  const width = 800;
  const height = 360;
  const padLeft = 60;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 45;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const getX = (vis: number) => {
    const val = Math.log10(Math.max(vis, 10));
    const ratio = Math.min(Math.max((val - logMin) / logSpan, 0), 1);
    return padLeft + ratio * chartW;
  };

  const getY = (score: number) => {
    const ratio = Math.min(Math.max(score / 100, 0), 1);
    return padTop + (1 - ratio) * chartH;
  };

  const colorForPriority = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "#EF4444"; // rose-500
      case "HIGH":
        return "#F59E0B"; // amber-500
      case "MEDIUM":
        return "#3B82F6"; // blue-500
      default:
        return "#94A3B8"; // slate-400
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 h-[400px] flex items-center justify-center">
        <p className="text-xs text-slate-400 animate-pulse">Rendering Content Opportunity Map...</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
      {/* Map Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-display font-bold text-slate-900 dark:text-white">
              Content Opportunity Map
            </h3>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/50 text-teal-600 dark:text-teal-400 border border-teal-200 dark:border-teal-800 font-semibold">
              {filteredPoints.length} Sampled Pages
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            X = Visibility (90d Impressions, Log Scale) &nbsp;|&nbsp; Y = Opportunity (0–100)
          </p>
        </div>

        {/* Filter Pills with distinct active state */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: "ALL", label: "All Points" },
            { id: "CRITICAL", label: "Critical" },
            { id: "HIGH", label: "High Priority" },
            { id: "REFRESH", label: "Refresh" },
            { id: "OPTIMIZE", label: "Optimize" },
          ].map((f) => {
            const isActive = filterTier === f.id;
            return (
              <button
                key={f.id}
                onClick={() => setFilterTier(f.id)}
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
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden rounded-xl bg-slate-50/50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
          style={{ minHeight: "280px" }}
        >
          {/* Quadrant Background Tints */}
          {/* Top Right: Act Now (High Visibility & High Opportunity) */}
          <rect
            x={padLeft + chartW / 2}
            y={padTop}
            width={chartW / 2}
            height={chartH / 2}
            fill="rgba(239, 68, 68, 0.035)"
          />
          {/* Top Left: Improve & Grow (Low Visibility & High Opportunity) */}
          <rect
            x={padLeft}
            y={padTop}
            width={chartW / 2}
            height={chartH / 2}
            fill="rgba(245, 158, 11, 0.025)"
          />
          {/* Bottom Right: Protect (High Visibility & Low Opportunity) */}
          <rect
            x={padLeft + chartW / 2}
            y={padTop + chartH / 2}
            width={chartW / 2}
            height={chartH / 2}
            fill="rgba(16, 185, 129, 0.035)"
          />
          {/* Bottom Left: Monitor (Low Visibility & Low Opportunity) */}
          <rect
            x={padLeft}
            y={padTop + chartH / 2}
            width={chartW / 2}
            height={chartH / 2}
            fill="rgba(148, 163, 184, 0.02)"
          />

          {/* Quadrant Labels (Simplified Terminology) */}
          <text
            x={padLeft + chartW - 10}
            y={padTop + 15}
            textAnchor="end"
            fontSize="10"
            fill="currentColor"
            className="text-rose-600 dark:text-rose-400 font-bold opacity-80 uppercase tracking-wide"
          >
            Act Now (High Visibility • Urgent)
          </text>
          <text
            x={padLeft + 10}
            y={padTop + 15}
            textAnchor="start"
            fontSize="10"
            fill="currentColor"
            className="text-amber-600 dark:text-amber-400 font-bold opacity-80 uppercase tracking-wide"
          >
            Improve &amp; Grow (Low Visibility • High Potential)
          </text>
          <text
            x={padLeft + chartW - 10}
            y={padTop + chartH - 10}
            textAnchor="end"
            fontSize="10"
            fill="currentColor"
            className="text-emerald-600 dark:text-emerald-400 font-bold opacity-80 uppercase tracking-wide"
          >
            Protect (Top Visibility • Defend)
          </text>
          <text
            x={padLeft + 10}
            y={padTop + chartH - 10}
            textAnchor="start"
            fontSize="10"
            fill="currentColor"
            className="text-slate-400 dark:text-slate-500 font-bold opacity-80 uppercase tracking-wide"
          >
            Monitor (Low Visibility • Routine)
          </text>

          {/* Grid lines: Y-axis (Score) */}
          {[0, 25, 50, 75, 100].map((score) => {
            const y = getY(score);
            return (
              <g key={`grid-y-${score}`}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="currentColor"
                  className="text-slate-200 dark:text-slate-800"
                  strokeDasharray={score === 50 ? "4 2" : "2 2"}
                  strokeWidth={score === 50 ? 1 : 0.5}
                />
                <text
                  x={padLeft - 10}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="10"
                  fill="currentColor"
                  className="text-slate-400 font-mono"
                >
                  {score}
                </text>
              </g>
            );
          })}

          {/* Vertical midline dividing visibility */}
          <line
            x1={padLeft + chartW / 2}
            y1={padTop}
            x2={padLeft + chartW / 2}
            y2={padTop + chartH}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-800"
            strokeDasharray="4 2"
            strokeWidth={1}
          />

          {/* Horizontal midline dividing score (50) */}
          <line
            x1={padLeft}
            y1={padTop + chartH / 2}
            x2={width - padRight}
            y2={padTop + chartH / 2}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-800"
            strokeDasharray="4 2"
            strokeWidth={1}
          />

          {/* X-axis Labels */}
          <text
            x={padLeft}
            y={height - 14}
            textAnchor="start"
            fontSize="10"
            fill="currentColor"
            className="text-slate-400 font-mono"
          >
            10
          </text>
          <text
            x={padLeft + chartW / 2}
            y={height - 14}
            textAnchor="middle"
            fontSize="10"
            fill="currentColor"
            className="text-slate-400 font-mono"
          >
            {Math.round(Math.pow(10, (logMin + logMax) / 2)).toLocaleString()}
          </text>
          <text
            x={width - padRight}
            y={height - 14}
            textAnchor="end"
            fontSize="10"
            fill="currentColor"
            className="text-slate-400 font-mono"
          >
            {Math.round(maxVis).toLocaleString()} Visibility
          </text>

          {/* Render Points */}
          {filteredPoints.map((pt) => {
            const cx = getX(pt.visibility);
            const cy = getY(pt.opportunity_score);
            const isSelected = selectedPoint?.page_id === pt.page_id;
            const color = colorForPriority(pt.priority);

            return (
              <circle
                key={pt.page_id}
                cx={cx}
                cy={cy}
                r={isSelected ? 6 : pt.priority === "CRITICAL" ? 4.5 : 3.5}
                fill={color}
                fillOpacity={isSelected ? 1 : 0.75}
                stroke={isSelected ? "#FFFFFF" : color}
                strokeWidth={isSelected ? 2 : 0.5}
                className="cursor-pointer transition-transform hover:scale-150"
                onMouseEnter={() => setSelectedPoint(pt)}
                onClick={() => setSelectedPoint(pt)}
              />
            );
          })}
        </svg>

        {/* Empty State when filter yields 0 results */}
        {filteredPoints.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/10 dark:bg-slate-950/40 backdrop-blur-[1px] p-4 text-center">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              No pages match the &ldquo;{filterTier}&rdquo; filter.
            </p>
            <button
              onClick={() => setFilterTier("ALL")}
              className="mt-2 text-xs px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-medium transition-colors"
            >
              Reset to All Points
            </button>
          </div>
        )}

        {/* Hover / Selected Point Tooltip Inspector */}
        {selectedPoint && (
          <div className="absolute top-3 right-3 max-w-[290px] w-full p-3.5 rounded-xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200 dark:border-slate-800 shadow-xl text-xs space-y-2.5 pointer-events-auto z-20 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between gap-2">
              <span
                className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase"
                style={{
                  backgroundColor: `${colorForPriority(selectedPoint.priority)}20`,
                  color: colorForPriority(selectedPoint.priority),
                }}
              >
                {selectedPoint.priority}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-teal-600 dark:text-teal-400 font-bold">
                  Score: {selectedPoint.opportunity_score}
                </span>
                <button
                  onClick={() => setSelectedPoint(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5"
                  title="Close Inspector"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div>
              <p className="font-bold text-slate-900 dark:text-white line-clamp-2 leading-snug">
                {selectedPoint.title || "Untitled Page"}
              </p>
              {selectedPoint.url && (
                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5 font-mono">
                  {selectedPoint.url}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-1.5 py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-[11px]">
              <div>
                <span className="text-[10px] text-slate-400 block">Visibility</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                  {selectedPoint.visibility.toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block">Click Rate</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                  {selectedPoint.ctr}%
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block">Action</span>
                <span className="font-semibold text-teal-600 dark:text-teal-400">
                  {selectedPoint.action}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block">Priority</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {selectedPoint.priority}
                </span>
              </div>
            </div>

            <Link
              href={`/dashboard/page/${selectedPoint.page_id}`}
              className="flex items-center justify-center gap-1.5 w-full py-1.5 px-3 rounded-lg text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white transition-colors"
            >
              View Details
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        )}
      </div>

      {/* Explanatory 4-Quadrant Legend */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pt-1 text-xs">
        <div className="p-3 rounded-xl bg-rose-500/5 border border-rose-500/20 dark:bg-rose-950/20 dark:border-rose-900/40">
          <div className="flex items-center gap-1.5 font-semibold text-rose-600 dark:text-rose-400">
            <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
            <span>Act Now</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            High visibility &amp; urgent decay. Immediate refresh yields maximum organic traffic recovery.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 dark:bg-amber-950/20 dark:border-amber-900/40">
          <div className="flex items-center gap-1.5 font-semibold text-amber-600 dark:text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span>Improve &amp; Grow</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Lower traffic with strong optimization signals. Rewriting or expanding can unlock top tier rankings.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 dark:bg-emerald-950/20 dark:border-emerald-900/40">
          <div className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
            <span>Protect</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Top organic performers with strong current rankings. Defend content depth against competitors.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-slate-500/5 border border-slate-500/20 dark:bg-slate-800/40 dark:border-slate-800">
          <div className="flex items-center gap-1.5 font-semibold text-slate-600 dark:text-slate-400">
            <span className="w-2 h-2 rounded-full bg-slate-400 shrink-0" />
            <span>Monitor</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
            Lower visibility &amp; low decay rate. Maintain in observation queue with routine periodic check-ins.
          </p>
        </div>
      </div>
    </div>
  );
}
