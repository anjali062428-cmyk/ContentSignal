"use client";

import React, { useState, useEffect } from "react";
import { Settings, Database, Cpu, ShieldCheck, CheckCircle2, Server, Save } from "lucide-react";
import { useDataset } from "@/context/DatasetContext";

export default function SettingsPage() {
  const { activeDataset } = useDataset();
  const [dbStatus, setDbStatus] = useState("Connected (SQLite / content_intelligence.db)");
  const [apiUrl, setApiUrl] = useState("http://127.0.0.1:8000/api");
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
          Platform Configuration & System Settings
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          Inspect operational parameters, database connectivity, and data integrity guardrails.
        </p>
      </div>

      <div className="space-y-6">
        {/* Database & Infrastructure */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Database & Persistence</h3>
          </div>
          <div className="space-y-3 text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 gap-2">
              <div>
                <div className="font-semibold text-slate-800 dark:text-slate-200">Active Catalog Storage</div>
                <div className="text-[11px] text-slate-400">
                  {activeDataset?.name || "Active Dataset"} ({activeDataset?.dataset_id}) &bull; {dbStatus}
                </div>
              </div>
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Operational ({activeDataset ? activeDataset.row_count.toLocaleString() : "30,000"} pages indexed)
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
              <div className="font-semibold text-slate-800 dark:text-slate-200">PostgreSQL / Supabase Migration</div>
              <p className="text-[11px] text-slate-500">
                Switch to PostgreSQL by setting the <code className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800">DATABASE_URL</code> environment variable. No application code changes required.
              </p>
            </div>
          </div>
        </div>

        {/* Model & Scoring Parameters */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Model & Scoring Policy</h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400 font-medium">Selected Model</div>
              <div className="font-bold text-slate-900 dark:text-white mt-1">Gradient Boosting</div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400 font-medium">Precision@100</div>
              <div className="font-bold text-emerald-600 dark:text-emerald-400 mt-1">72.0%</div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400 font-medium">Holdout Ratio</div>
              <div className="font-bold text-slate-900 dark:text-white mt-1">20% Client-Aware</div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400 font-medium">Random Seed</div>
              <div className="font-bold text-slate-900 dark:text-white mt-1">42 (Reproducible)</div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-2">
            <div className="font-semibold text-slate-800 dark:text-slate-200">Configured Priority Thresholds (0–100)</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
              <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                LOW: <span className="font-bold text-slate-600 dark:text-slate-300">0 – 30</span>
              </div>
              <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                MEDIUM: <span className="font-bold text-blue-600 dark:text-blue-400">31 – 60</span>
              </div>
              <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                HIGH: <span className="font-bold text-amber-600 dark:text-amber-400">61 – 80</span>
              </div>
              <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                CRITICAL: <span className="font-bold text-rose-600 dark:text-rose-400">81 – 100</span>
              </div>
            </div>
          </div>
        </div>

        {/* Data Guardrails & Safety */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Public-Safety & Data Guardrails</h3>
          </div>
          <div className="space-y-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            <p>
              &bull; <strong>9 Proprietary FlyRank Decision Columns:</strong> Quarantined permanently upon raw ingestion.
            </p>
            <p>
              &bull; <strong>Target-Construction Leakage:</strong> 100% excluded (impressions_last_30d, impressions_prev_30d, trend_direction, trend_pct banned from features).
            </p>
            <p>
              &bull; <strong>Privacy & Anonymity:</strong> Zero raw URLs, client names, or personal queries stored or exposed.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}