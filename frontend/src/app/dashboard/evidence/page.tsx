"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileDown,
  FileSpreadsheet,
  FileText,
  FileCode,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Download,
  Layers,
  ArrowRight,
  ExternalLink,
  Info,
  Calendar,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState } from "@/components/UIStates";

export default function EvidenceExportPage() {
  const { datasets, activeDataset, isLoading } = useDataset();
  const [exportLimit, setExportLimit] = useState<number>(50);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  if (isLoading && !activeDataset) {
    return <LoadingState message="Loading Evidence Center..." />;
  }

  const datasetId = activeDataset?.dataset_id;

  const handleDownload = (format: "pdf" | "docx" | "xlsx") => {
    setDownloadingFormat(format);
    let url = "";
    if (format === "pdf") {
      url = api.getEvidencePdfUrl(datasetId, exportLimit);
    } else if (format === "docx") {
      url = api.getEvidenceDocxUrl(datasetId, exportLimit);
    } else if (format === "xlsx") {
      url = api.getEvidenceXlsxUrl(datasetId, exportLimit);
    }

    // Trigger download
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `contentsignal_${format}_${datasetId || "export"}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      setDownloadingFormat(null);
    }, 1500);
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-emerald-600 text-white shadow-sm">
              <FileDown className="w-5 h-5" />
            </span>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
              Evidence Center &amp; Executive Exports
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Generate boardroom-ready PDF briefs, Word strategy memos, and Excel analysis workbooks grounded strictly in verified dataset signals.
          </p>
        </div>

        {/* Scope Selector */}
        <div className="flex items-center gap-3 bg-white dark:bg-slate-900 p-2 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium px-2">
            <Filter className="w-3.5 h-3.5 text-emerald-500" />
            <span>Scope:</span>
          </div>
          <div className="flex items-center gap-1">
            {[35, 50, 100, 250].map((count) => (
              <button
                key={count}
                onClick={() => setExportLimit(count)}
                className={`px-2.5 py-1 text-xs rounded-xl font-medium transition-all ${
                  exportLimit === count
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                Top {count}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active Dataset Snapshot Card */}
      {activeDataset && (
        <div className="p-6 rounded-2xl border border-emerald-300 dark:border-emerald-800/80 bg-gradient-to-r from-emerald-50 via-teal-50/40 to-cyan-50/30 dark:from-emerald-950/40 dark:via-teal-950/20 dark:to-cyan-950/20 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Active Dataset: {activeDataset.name}
                </h2>
                {activeDataset.is_starter ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                    STARTER DEMO
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    CUSTOM DATASET
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white">
                  GROUNDED EVIDENCE
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-mono">
                Dataset ID: {activeDataset.dataset_id} &bull; Model: {activeDataset.model_name || "Gradient Boosting"}
              </p>
            </div>

            <Link
              href="/dashboard/opportunities"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors self-start sm:self-auto"
            >
              <span>Inspect Opportunities</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-emerald-200 dark:border-emerald-800/60 text-xs">
            <div>
              <span className="text-slate-500">Indexed Catalog Pages:</span>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                {activeDataset.row_count.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-slate-500">Contract Validation:</span>
              <div className="font-bold text-base text-emerald-600 dark:text-emerald-400">
                {activeDataset.validation_status}
              </div>
            </div>
            <div>
              <span className="text-slate-500">Export Scope:</span>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                Top {exportLimit} Directives
              </div>
            </div>
            <div>
              <span className="text-slate-500">Audit Protocol:</span>
              <div className="font-semibold text-base text-slate-900 dark:text-white">
                Zero Leakage Enforced
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3 Export Artifact Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* PDF Card */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 transition-all group">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900">
                <FileText className="w-6 h-6" />
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase">
                PDF Document
              </span>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                Executive Briefing
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                High-density, boardroom-ready briefing report created via ReportLab. Includes KPI scorecard, priority breakdowns, action queue, and deterministic reason codes.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px] text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Letter format with corporate header typography</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Executive KPI summary scorecard</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Color-coded priority flags (Critical &amp; High)</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("pdf")}
            disabled={downloadingFormat === "pdf"}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all shadow-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4 text-rose-400" />
            <span>{downloadingFormat === "pdf" ? "Generating PDF..." : `Download PDF (${exportLimit} Pages)`}</span>
          </button>
        </div>

        {/* Word Card */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 transition-all group">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-900">
                <FileCode className="w-6 h-6" />
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase">
                Word Document
              </span>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                Editorial Strategy Memo
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                Editable Microsoft Word memo built via python-docx. Formatted with executive styles, structured tables, and decision rationale ready for circulation.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px] text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Full editorial circulation and markup support</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Primary decision reason &amp; directive breakdown</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Standardized 1-inch editorial margins</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("docx")}
            disabled={downloadingFormat === "docx"}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all shadow-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4 text-blue-400" />
            <span>{downloadingFormat === "docx" ? "Generating Word Doc..." : `Download Word (${exportLimit} Pages)`}</span>
          </button>
        </div>

        {/* Excel Card */}
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 transition-all group">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900">
                <FileSpreadsheet className="w-6 h-6" />
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase">
                Excel Spreadsheet
              </span>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                Deep-Dive Analytics Workbook
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                Multi-sheet workbook created via openpyxl. Features Executive Summary, Opportunity Queue, and Watchlist &amp; Action Log with dark navy headers.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px] text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>3 distinct worksheets with auto-sized columns</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Includes Starred Watchlist and Action Log history</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Formatted raw numerical metrics for pivot tables</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleDownload("xlsx")}
            disabled={downloadingFormat === "xlsx"}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white transition-all shadow-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            <span>{downloadingFormat === "xlsx" ? "Generating Excel..." : `Download Excel (${exportLimit} Pages)`}</span>
          </button>
        </div>
      </div>

      {/* Methodology & Integrity Notice */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-500" />
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Grounding &amp; Data Integrity Standard
          </h2>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          All exported artifacts are assembled dynamically from verified database records. ContentSignal enforces a strict zero-fabrication policy: no synthetic time series, no placeholder text, and no external black-box models. Opportunity priority scores, deterministic reason codes, and behavioral archetype classifications reflect observable 90-day search and traffic signals.
        </p>
        <div className="flex flex-wrap gap-4 pt-2 text-[11px] text-slate-500 dark:text-slate-400">
          <div>&bull; <strong className="text-slate-700 dark:text-slate-300">Model:</strong> Gradient Boosting Classifier</div>
          <div>&bull; <strong className="text-slate-700 dark:text-slate-300">Contract:</strong> 44 Schema Columns</div>
          <div>&bull; <strong className="text-slate-700 dark:text-slate-300">Quarantine:</strong> 9 Decision Columns Isolated</div>
          <div>&bull; <strong className="text-slate-700 dark:text-slate-300">Time Window:</strong> Trailing 90-Day Aggregation</div>
        </div>
      </div>
    </div>
  );
}
