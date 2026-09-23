"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Database, ChevronDown, Check, Plus, CheckCircle2, AlertCircle, SlidersHorizontal } from "lucide-react";
import { useDataset } from "@/context/DatasetContext";

export function DatasetSelector() {
  const { datasets, activeDataset, setActiveDataset, isLoading } = useDataset();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const formatTriggerLabel = (d: any) => {
    if (!d) return "Select Dataset";
    let baseName = d.name || "Dataset";
    if (d.is_starter || baseName.toLowerCase().includes("flyrank")) {
      baseName = "FlyRank Starter";
    }
    const count = d.row_count >= 1000 ? `${Math.round(d.row_count / 1000)}k` : `${d.row_count || 0}`;
    return `${baseName} · ${count}`;
  };

  const formatDropdownName = (d: any) => {
    if (d.is_starter || d.name?.toLowerCase().includes("flyrank")) {
      return "FlyRank Starter Dataset";
    }
    return d.name;
  };

  if (isLoading && !activeDataset) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100/50 dark:bg-slate-900/50 text-xs text-slate-400">
        <Database className="w-3.5 h-3.5 animate-pulse text-teal-500" />
        <span>Loading datasets...</span>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/80 hover:bg-slate-100 dark:hover:bg-slate-800/90 hover:border-slate-300 dark:hover:border-slate-700 text-xs text-slate-800 dark:text-slate-200 transition-all"
        title="Switch active dataset workspace"
      >
        <Database className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
        <span className="font-medium text-[12px] whitespace-nowrap">
          {formatTriggerLabel(activeDataset)}
        </span>
        <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform shrink-0 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-xl z-50 overflow-hidden py-1 divide-y divide-slate-100 dark:divide-slate-900">
          <div className="px-3.5 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>Available Datasets ({datasets.length})</span>
            <span>Switch Catalog</span>
          </div>

          <div className="max-h-60 overflow-y-auto py-1">
            {datasets.map((d) => {
              const isSelected = activeDataset?.dataset_id === d.dataset_id;
              const isValid = !d.validation_status || d.validation_status.toLowerCase().includes("valid");

              return (
                <button
                  key={d.dataset_id}
                  onClick={() => {
                    setActiveDataset(d);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3.5 py-2.5 flex items-center justify-between gap-2.5 hover:bg-slate-50 dark:hover:bg-slate-900/60 transition-colors ${
                    isSelected ? "bg-teal-50/70 dark:bg-teal-950/30" : ""
                  }`}
                >
                  <div className="flex items-start gap-2.5 min-w-0">
                    <Database className={`w-4 h-4 shrink-0 mt-0.5 ${
                      isSelected ? "text-teal-600 dark:text-teal-400" : "text-slate-400"
                    }`} />
                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-xs font-semibold truncate ${
                            isSelected
                              ? "text-teal-700 dark:text-teal-300"
                              : "text-slate-800 dark:text-slate-200"
                          }`}
                        >
                          {formatDropdownName(d)}
                        </span>
                        {d.is_starter ? (
                          <span className="text-[9px] font-bold px-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 shrink-0">
                            Demo
                          </span>
                        ) : (
                          <span className="text-[9px] font-bold px-1 rounded bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 shrink-0">
                            Custom
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                        <span>{d.row_count.toLocaleString()} pages · {d.is_starter ? "Demo" : "Custom"}</span>
                        {isValid ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-500 inline ml-1" />
                        ) : (
                          <AlertCircle className="w-3 h-3 text-amber-500 inline ml-1" />
                        )}
                      </div>
                    </div>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0" />}
                </button>
              );
            })}
          </div>

          {/* Footer actions: Manage datasets + Upload dataset */}
          <div className="p-2.5 bg-slate-50/70 dark:bg-slate-900/60 flex items-center justify-between gap-2">
            <Link
              href="/dashboard/datasets"
              onClick={() => setIsOpen(false)}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700/80 border border-slate-200 dark:border-slate-700 transition-colors shadow-xs text-center"
            >
              <SlidersHorizontal className="w-3 h-3 text-slate-500" />
              Manage datasets
            </Link>
            <Link
              href="/dashboard/datasets"
              onClick={() => setIsOpen(false)}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white transition-colors shadow-xs text-center"
            >
              <Plus className="w-3.5 h-3.5" />
              + Upload dataset
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
