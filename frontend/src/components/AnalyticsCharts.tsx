"use client";

import React, { useState } from "react";

export interface ChartDataPoint {
  key: string;
  label: string;
  count: number;
  percentage: number;
  color?: string;
  secondaryInfo?: string;
}

interface VerticalBarChartProps {
  data: ChartDataPoint[];
  total: number;
  heightClass?: string;
  accentGradient?: string;
}

/**
 * Clean, restrained SVG + CSS vertical bar chart matching ContentSignal design system.
 * Shows subtle grid lines, Y-axis ticks, hover tooltips, and readable X-axis labels.
 */
export function VerticalBarChart({
  data,
  total,
  heightClass = "h-52",
  accentGradient = "from-teal-600 to-teal-400 dark:from-teal-500 dark:to-teal-300",
}: VerticalBarChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="w-full h-40 flex items-center justify-center text-xs text-slate-400 font-mono">
        No distribution data available
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  // Determine clean Y-axis grid ticks (4 intervals)
  const getNiceCeiling = (max: number): number => {
    if (max <= 50) return 50;
    if (max <= 100) return 100;
    if (max <= 1000) return 1000;
    if (max <= 5000) return 5000;
    if (max <= 10000) return 10000;
    if (max <= 15000) return 15000;
    if (max <= 20000) return 20000;
    if (max <= 25000) return 25000;
    return Math.ceil(max / 5000) * 5000;
  };

  const ceiling = getNiceCeiling(maxCount);
  const gridTicks = [ceiling, Math.round(ceiling * 0.66), Math.round(ceiling * 0.33), 0];

  const formatTick = (val: number) => {
    if (val >= 1000) return `${(val / 1000).toFixed(val % 1000 === 0 ? 0 : 1)}k`;
    return `${val}`;
  };

  return (
    <div className="w-full select-none pt-2">
      <div className={`relative w-full ${heightClass} flex`}>
        {/* Y-Axis scale labels */}
        <div className="w-9 sm:w-11 shrink-0 flex flex-col justify-between text-[10px] font-mono text-slate-400 pb-6 pr-1 text-right">
          {gridTicks.map((tick, i) => (
            <span key={i} className="leading-none">
              {formatTick(tick)}
            </span>
          ))}
        </div>

        {/* Chart Area with Gridlines & Bars */}
        <div className="relative flex-1 flex flex-col justify-between pb-6 pl-1">
          {/* Subtle horizontal grid lines */}
          <div className="absolute inset-0 pb-6 flex flex-col justify-between pointer-events-none">
            {gridTicks.map((_, i) => (
              <div
                key={i}
                className="w-full border-b border-slate-100 dark:border-slate-800/80"
              />
            ))}
          </div>

          {/* Bar Columns */}
          <div className="relative z-10 w-full h-full flex items-end justify-around gap-2 sm:gap-4 px-1">
            {data.map((item, idx) => {
              const heightPct = ceiling > 0 ? (item.count / ceiling) * 100 : 0;
              // Ensure small non-zero values have minimum visibility
              const barHeightPct = item.count > 0 ? Math.max(heightPct, 2.5) : 0;
              const isHovered = hoveredIndex === idx;

              return (
                <div
                  key={item.key}
                  className="relative flex-1 flex flex-col items-center h-full justify-end group cursor-pointer"
                  onMouseEnter={() => setHoveredIndex(idx)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {/* Tooltip */}
                  {isHovered && (
                    <div className="absolute -top-12 z-30 pointer-events-none px-2.5 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-950 text-white border border-slate-700/80 shadow-xl text-[11px] whitespace-nowrap text-center animate-in fade-in duration-150">
                      <div className="font-semibold text-slate-200">{item.label}</div>
                      <div className="text-[10px] text-teal-400 font-mono">
                        {item.count.toLocaleString()} pages ({item.percentage.toFixed(1)}%)
                      </div>
                      {/* Arrow */}
                      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-900 dark:bg-slate-950 border-b border-r border-slate-700/80 rotate-45" />
                    </div>
                  )}

                  {/* Value callout on top of bar if space permits */}
                  {barHeightPct > 15 && (
                    <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {formatTick(item.count)}
                    </span>
                  )}

                  {/* Vertical Bar */}
                  <div
                    className={`w-full max-w-[36px] sm:max-w-[48px] rounded-t-md transition-all duration-200 ${
                      item.color || `bg-gradient-to-t ${accentGradient}`
                    } ${isHovered ? "brightness-110 scale-y-[1.02] shadow-sm" : "opacity-90"}`}
                    style={{ height: `${barHeightPct}%` }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* X-Axis Labels Row */}
      <div className="flex w-full pl-9 sm:pl-11">
        <div className="flex-1 flex justify-around gap-2 sm:gap-4 px-1">
          {data.map((item, idx) => (
            <div
              key={item.key}
              className={`flex-1 text-center truncate text-[11px] sm:text-xs transition-colors ${
                hoveredIndex === idx
                  ? "font-semibold text-teal-600 dark:text-teal-400"
                  : "text-slate-600 dark:text-slate-400"
              }`}
              title={`${item.label}: ${item.count.toLocaleString()} (${item.percentage.toFixed(1)}%)`}
            >
              {item.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface HorizontalBarProps {
  data: ChartDataPoint[];
  total: number;
}

/**
 * Clean horizontal distribution chart for content type mix.
 */
export function HorizontalDistributionChart({ data, total }: HorizontalBarProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="w-full py-6 flex items-center justify-center text-xs text-slate-400 font-mono">
        No distribution data available
      </div>
    );
  }

  return (
    <div className="w-full space-y-4 pt-1">
      {data.map((item) => {
        const isHovered = hoveredKey === item.key;
        return (
          <div
            key={item.key}
            className="space-y-1.5 group cursor-pointer"
            onMouseEnter={() => setHoveredKey(item.key)}
            onMouseLeave={() => setHoveredKey(null)}
          >
            <div className="flex items-center justify-between text-xs">
              <span
                className={`font-medium transition-colors ${
                  isHovered
                    ? "text-teal-700 dark:text-teal-300 font-semibold"
                    : "text-slate-700 dark:text-slate-300"
                }`}
              >
                {item.label}
              </span>
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="text-slate-900 dark:text-white font-semibold">
                  {item.count.toLocaleString()}
                </span>
                <span className="text-slate-400 text-[11px]">({item.percentage.toFixed(1)}%)</span>
              </div>
            </div>

            {/* Horizontal Bar Track */}
            <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  item.color || "bg-gradient-to-r from-teal-600 to-cyan-500"
                } ${isHovered ? "brightness-110" : "opacity-95"}`}
                style={{ width: `${Math.max(item.percentage, 1)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
