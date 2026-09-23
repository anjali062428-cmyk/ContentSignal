"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Database,
  Upload,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  Cpu,
  Trash2,
  ArrowRight,
  Loader2,
  FileText,
  Layers,
  Sparkles,
  Info,
  Clock,
  HardDrive,
  Check,
  FileSpreadsheet,
} from "lucide-react";
import { api, ValidationSummary, AnalyzeDatasetResponse, DatasetSummary, AnalysisJob } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, ErrorState } from "@/components/UIStates";

export default function DatasetsPage() {
  const router = useRouter();
  const { datasets, activeDataset, setActiveDataset, refreshDatasets, isLoading: isContextLoading } = useDataset();

  // File Upload & Drag-and-Drop State
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationReport, setValidationReport] = useState<ValidationSummary | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Analysis State with Staged Progress Bar
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingStep, setAnalyzingStep] = useState<string>("");
  const [analysisProgress, setAnalysisProgress] = useState<number>(0);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeDatasetResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Deletion State
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSelectFile = (selectedFile: File) => {
    setFile(selectedFile);
    setValidationReport(null);
    setValidationError(null);
    setAnalysisResult(null);
    setAnalysisError(null);
    if (!datasetName) {
      setDatasetName(selectedFile.name.replace(/\.[^/.]+$/, ""));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith(".csv")) {
        handleSelectFile(droppedFile);
      } else {
        setValidationError("Please drop a valid .csv file.");
      }
    }
  };

  const handleValidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setValidationError("Please choose or drop a CSV file to validate.");
      return;
    }

    setIsValidating(true);
    setValidationError(null);
    setValidationReport(null);
    setAnalysisResult(null);
    setAnalysisError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (datasetName.trim()) {
        formData.append("name", datasetName.trim());
      }

      const report = await api.uploadDataset(formData);
      setValidationReport(report);
      await refreshDatasets();
    } catch (err: any) {
      setValidationError(err.message || "Failed to validate dataset.");
    } finally {
      setIsValidating(false);
    }
  };

  const pollJobStatus = async (datasetId: string, jobId: string) => {
    const maxPolls = 60;
    let polls = 0;

    const interval = setInterval(async () => {
      polls++;
      try {
        const job = await api.getAnalysisJob(datasetId, jobId);
        setAnalysisProgress(job.progress_pct);
        if (job.stage_label) {
          setAnalyzingStep(job.stage_label);
        }

        if (job.status === "COMPLETED") {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisProgress(100);
          setAnalyzingStep("Analysis complete!");
          await refreshDatasets(datasetId);
        } else if (job.status === "FAILED") {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisError(job.error_message || "Background analysis job failed.");
        } else if (polls >= maxPolls) {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisError("Job polling timed out. Please check the dataset inventory.");
        }
      } catch (err: any) {
        clearInterval(interval);
        setIsAnalyzing(false);
        setAnalysisError(err.message || "Failed checking analysis job status.");
      }
    }, 800);
  };

  const handleAnalyze = async (datasetId: string) => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisProgress(10);
    setAnalyzingStep("Queueing background analysis job...");

    try {
      // Try background job queue first
      try {
        const job = await api.createAnalysisJob(datasetId);
        setActiveJobId(job.job_id);
        setAnalysisProgress(20);
        setAnalyzingStep(job.stage_label || "Initializing feature pipeline...");
        await pollJobStatus(datasetId, job.job_id);
        return;
      } catch (jobErr) {
        console.warn("Background job creation fallback to synchronous execution", jobErr);
      }

      // Synchronous fallback
      setAnalysisProgress(25);
      setAnalyzingStep("Initializing feature pipeline & data quarantine...");
      setTimeout(() => { setAnalysisProgress(50); setAnalyzingStep("Running Gradient Boosting model inference..."); }, 1200);
      setTimeout(() => { setAnalysisProgress(75); setAnalyzingStep("Evaluating deterministic reason codes & actions..."); }, 2500);
      setTimeout(() => { setAnalysisProgress(90); setAnalyzingStep("Computing K-Means behavioral archetypes..."); }, 3800);

      const res = await api.analyzeDataset(datasetId);
      setAnalysisProgress(100);
      setAnalyzingStep("Completed");
      setAnalysisResult(res);
      await refreshDatasets(datasetId);
      setIsAnalyzing(false);
    } catch (err: any) {
      setAnalysisError(err.message || "Analysis failed.");
      setIsAnalyzing(false);
    }
  };

  const handleDelete = async (dataset: DatasetSummary) => {
    if (dataset.is_starter) {
      alert("The FlyRank Starter Dataset is protected and cannot be deleted.");
      return;
    }

    if (!confirm(`Are you sure you want to permanently delete "${dataset.name}" and all associated pages and opportunities?`)) {
      return;
    }

    setDeletingId(dataset.dataset_id);
    setDeleteError(null);

    try {
      await api.deleteDataset(dataset.dataset_id);
      await refreshDatasets();
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete dataset.");
    } finally {
      setDeletingId(null);
    }
  };

  if (isContextLoading && !activeDataset) {
    return <LoadingState message="Loading dataset management workspace..." />;
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
            <Database className="w-7 h-7 text-emerald-500" />
            Dataset Management &amp; Ingestion
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Import and score custom CSV datasets against the strict 44-column contract. All uploads are validated, quarantined, and scored with zero leakage.
          </p>
        </div>
      </div>

      {/* Active Dataset Hero Banner */}
      {activeDataset && (
        <div className="p-6 rounded-2xl border border-emerald-300 dark:border-emerald-800/80 bg-gradient-to-r from-emerald-50 via-teal-50/40 to-cyan-50/30 dark:from-emerald-950/40 dark:via-teal-950/20 dark:to-cyan-950/20 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-emerald-600 text-white shadow-sm">
                <HardDrive className="w-5 h-5" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">
                    {activeDataset.name}
                  </h2>
                  {activeDataset.is_starter ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                      STARTER DEMO
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      CUSTOM USER DATASET
                    </span>
                  )}
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white">
                    ACTIVE
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  Dataset ID: <span className="font-mono">{activeDataset.dataset_id}</span> &bull; All dashboard KPIs, opportunity queues, and AI assistant queries currently ground to this dataset.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/dashboard/opportunities"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors"
              >
                View Opportunities Queue
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-emerald-200 dark:border-emerald-800/60 text-xs">
            <div>
              <span className="text-slate-500">Indexed Pages:</span>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                {activeDataset.row_count.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-slate-500">Contract Schema:</span>
              <div className="font-mono font-bold text-base text-slate-900 dark:text-white">
                {activeDataset.column_count} columns
              </div>
            </div>
            <div>
              <span className="text-slate-500">Validation Status:</span>
              <div className="font-bold text-base text-emerald-600 dark:text-emerald-400">
                {activeDataset.validation_status}
              </div>
            </div>
            <div>
              <span className="text-slate-500">ML Scoring Model:</span>
              <div className="font-semibold text-base text-slate-900 dark:text-white truncate">
                {activeDataset.model_name || "Gradient Boosting"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Schema Completeness & Data Quality Standards Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Dataset-Agnostic Capability Engine &amp; Data Contract Standards
            </h2>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            Contract v2.0 &bull; Canonical Adapters
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              <span>Primary FlyRank Isolation</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Preserves the full 44-column contract. 9 proprietary decision columns are permanently quarantined to eliminate feature leakage while maintaining full champion model accuracy.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              <span>Semantic Capability Detection</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Auto-detects identity, visibility, search, engagement, time, and conversion signals. Maps headers dynamically to canonical slots without requiring rigid re-naming.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Check className="w-4 h-4 text-emerald-500" />
              <span>10-Point Readiness &amp; Streaming</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Runs an automated 10-point readiness audit, rejecting invalid non-content datasets and streaming large/time-series data without memory crashes.
            </p>
          </div>
        </div>
      </div>

      {/* Upload Section with Drag-and-Drop */}
      <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Upload className="w-5 h-5 text-emerald-500" />
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Upload New Dataset (CSV)
              </h2>
              <p className="text-xs text-slate-500">
                Drag and drop your dataset CSV or browse your local file system.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleValidate} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Dataset Name (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Q3 Organic Search Performance"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all flex flex-col items-center justify-center gap-3 ${
              isDragging
                ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30 shadow-glow-sm"
                : file
                ? "border-emerald-400 bg-emerald-50/20 dark:bg-emerald-950/20"
                : "border-slate-300 dark:border-slate-700 hover:border-emerald-400 hover:bg-slate-50 dark:hover:bg-slate-900/50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />

            {file ? (
              <div className="flex flex-col items-center gap-2">
                <span className="p-3 rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 shadow-sm">
                  <FileSpreadsheet className="w-8 h-8" />
                </span>
                <div className="text-sm font-bold text-slate-900 dark:text-white">
                  {file.name}
                </div>
                <div className="text-xs font-mono text-slate-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB &bull; Click or drop another file to replace
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <span className="p-3 rounded-2xl bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  <Upload className="w-8 h-8 text-emerald-500" />
                </span>
                <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Drag and drop your dataset CSV here
                </div>
                <p className="text-xs text-slate-500 max-w-sm">
                  Accepts CSV format conforming to the 44-column contract. Max file size: 50MB.
                </p>
                <button
                  type="button"
                  className="mt-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                >
                  Browse Files
                </button>
              </div>
            )}
          </div>

          {validationError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 flex items-start gap-2.5 text-xs text-rose-700 dark:text-rose-300">
              <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <strong>Validation Failed:</strong> {validationError}
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="submit"
              disabled={isValidating || !file}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow-sm transition-all disabled:opacity-50"
            >
              {isValidating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running Schema &amp; Contract Validation...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  Validate Dataset
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Staged Progress Bar During Analysis */}
      {isAnalyzing && (
        <div className="glass-card p-6 rounded-2xl border border-emerald-400 bg-emerald-50/40 dark:bg-emerald-950/20 space-y-4 shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-emerald-600 dark:text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Executing ML Scoring &amp; Grouping Pipeline
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 font-mono mt-0.5">
                  {analyzingStep || "Processing..."}
                </p>
              </div>
            </div>
            <span className="text-sm font-display font-extrabold text-emerald-600 dark:text-emerald-400">
              {analysisProgress}%
            </span>
          </div>

          {/* Progress Track */}
          <div className="w-full bg-slate-200 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.max(analysisProgress, 5)}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] text-slate-500 dark:text-slate-400">
            <div className={`flex items-center gap-1.5 ${analysisProgress >= 20 ? "text-emerald-600 dark:text-emerald-400 font-semibold" : ""}`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Feature Pipeline</span>
            </div>
            <div className={`flex items-center gap-1.5 ${analysisProgress >= 45 ? "text-emerald-600 dark:text-emerald-400 font-semibold" : ""}`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Gradient Boosting</span>
            </div>
            <div className={`flex items-center gap-1.5 ${analysisProgress >= 70 ? "text-emerald-600 dark:text-emerald-400 font-semibold" : ""}`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Reason Directives</span>
            </div>
            <div className={`flex items-center gap-1.5 ${analysisProgress >= 90 ? "text-emerald-600 dark:text-emerald-400 font-semibold" : ""}`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>K-Means Clusters</span>
            </div>
          </div>
        </div>
      )}

      {analysisError && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 flex items-start gap-2.5 text-xs text-rose-700 dark:text-rose-300">
          <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <strong>Analysis Job Error:</strong> {analysisError}
          </div>
        </div>
      )}

      {/* Validation Results Card */}
      {validationReport && (
        <div className="glass-card p-6 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              {validationReport.is_valid && validationReport.readiness?.overall_status !== "NOT_READY" ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              ) : validationReport.readiness?.overall_status === "READY_WITH_LIMITATIONS" ? (
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              ) : (
                <XCircle className="w-6 h-6 text-rose-500" />
              )}
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    {validationReport.readiness?.overall_status === "READY"
                      ? "Dataset Ready for Scoring"
                      : validationReport.readiness?.overall_status === "READY_WITH_LIMITATIONS"
                      ? "Dataset Ready (With Limitations)"
                      : validationReport.readiness?.overall_status === "TIME_SERIES"
                      ? "Time Series Dataset Detected"
                      : validationReport.readiness?.overall_status === "LARGE_DATASET"
                      ? "Large Scale Dataset Detected"
                      : validationReport.is_valid
                      ? "Schema Validation Passed"
                      : "Dataset Not Ready — Ingestion Blocked"}
                  </h3>
                  {validationReport.readiness?.overall_status && (
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                        validationReport.readiness.overall_status === "READY"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
                          : validationReport.readiness.overall_status === "READY_WITH_LIMITATIONS"
                          ? "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800"
                          : validationReport.readiness.overall_status === "TIME_SERIES"
                          ? "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800"
                          : validationReport.readiness.overall_status === "LARGE_DATASET"
                          ? "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800"
                          : "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800"
                      }`}
                    >
                      {validationReport.readiness.overall_status}
                    </span>
                  )}
                  {validationReport.adapter_type && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      Adapter: {validationReport.adapter_type}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {validationReport.row_count.toLocaleString()} rows &bull; {validationReport.column_count} columns
                  {validationReport.readiness?.summary ? ` &bull; ${validationReport.readiness.summary}` : ""}
                </p>
              </div>
            </div>

            {validationReport.dataset_id && (
              <div>
                {validationReport.readiness?.overall_status === "NOT_READY" || !validationReport.is_valid ? (
                  <button
                    disabled
                    className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 rounded-xl cursor-not-allowed"
                    title="Resolve blocking checklist issues before scoring this dataset"
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    Analysis Blocked
                  </button>
                ) : (
                  <button
                    onClick={() => handleAnalyze(validationReport.dataset_id!)}
                    disabled={isAnalyzing}
                    className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow-glow-sm transition-all disabled:opacity-50"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Analyzing Dataset ({analysisProgress}%)...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Analyze Dataset &amp; Generate Opportunities
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Validation Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-[11px] text-slate-500">Total Valid Rows</div>
              <div className="text-xl font-display font-bold text-slate-900 dark:text-white mt-0.5">
                {validationReport.row_count.toLocaleString()}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-[11px] text-slate-500">Duplicate Records</div>
              <div className={`text-xl font-display font-bold mt-0.5 ${validationReport.duplicate_ids_count > 0 ? "text-rose-500" : "text-emerald-500"}`}>
                {validationReport.duplicate_ids_count}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-[11px] text-slate-500">Quarantined Columns</div>
              <div className="text-xl font-display font-bold text-amber-500 mt-0.5">
                {validationReport.quarantined_fields.length}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-[11px] text-slate-500">Readiness Score</div>
              <div className="text-xl font-display font-bold text-emerald-500 mt-0.5">
                {validationReport.readiness?.readiness_pct !== undefined
                  ? `${validationReport.readiness.readiness_pct}%`
                  : validationReport.is_valid
                  ? "100%"
                  : "0%"}
              </div>
            </div>
          </div>

          {/* 10-Point Readiness Checklist */}
          {validationReport.readiness?.checklist && validationReport.readiness.checklist.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  Dataset Readiness Checklist (10 Quality Gates)
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  {validationReport.readiness.checklist.filter((c) => c.passed).length} of {validationReport.readiness.checklist.length} Passed
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {validationReport.readiness.checklist.map((item, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
                      item.passed
                        ? "bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200/60 dark:border-emerald-900/40 text-slate-700 dark:text-slate-300"
                        : item.severity === "blocker"
                        ? "bg-rose-50/40 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/50 text-rose-800 dark:text-rose-200"
                        : "bg-amber-50/40 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/50 text-amber-800 dark:text-amber-200"
                    }`}
                  >
                    {item.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    ) : item.severity === "blocker" ? (
                      <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <div className="font-semibold capitalize text-[11px]">
                        {item.name.replace(/_/g, " ")}
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">
                        {item.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detected Capabilities */}
          {validationReport.capabilities && Object.keys(validationReport.capabilities).length > 0 && (
            <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-2.5">
              <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-blue-500" />
                Detected Dataset Capabilities
              </span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(validationReport.capabilities).map(([cap, detail]: [string, any]) => {
                  const cols = detail?.columns || [];
                  const isPresent = detail?.present !== false;
                  return (
                    <div
                      key={cap}
                      className={`px-2.5 py-1.5 rounded-lg border text-[11px] flex items-center gap-1.5 ${
                        isPresent
                          ? "bg-slate-100 dark:bg-slate-800/80 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200"
                          : "bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 text-slate-400 opacity-60"
                      }`}
                    >
                      <span className="font-bold">{cap}</span>
                      {cols.length > 0 && (
                        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                          {cols.length} col{cols.length === 1 ? "" : "s"}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Canonical Mappings */}
          {validationReport.mapping && validationReport.mapping.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-2.5">
              <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-purple-500" />
                Canonical Feature Slot Mappings ({validationReport.mapping.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {validationReport.mapping.map((m, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 font-mono text-[10px] px-2 py-1 rounded bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/60 text-purple-700 dark:text-purple-300"
                  >
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{m.source_column}</span>
                    <span className="text-slate-400">&rarr;</span>
                    <span>{m.canonical_slot}</span>
                    <span className="text-[9px] text-purple-500">({Math.round(m.confidence * 100)}%)</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quarantined Columns Notice */}
          {validationReport.quarantined_fields.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-amber-900 dark:text-amber-300">
                <ShieldCheck className="w-4 h-4 text-amber-500" />
                <span>{validationReport.quarantined_fields.length} Restricted FlyRank Columns Quarantined:</span>
              </div>
              <p className="text-[11px] text-amber-800 dark:text-amber-400">
                These proprietary decision fields are safely stored in raw form but permanently excluded from feature pipelines, ML models, and scoring calculations:
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {validationReport.quarantined_fields.map((col) => (
                  <span
                    key={col}
                    className="font-mono text-[10px] px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Errors List */}
          {validationReport.errors && validationReport.errors.length > 0 && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-rose-900 dark:text-rose-300">
                <XCircle className="w-4 h-4 text-rose-500" />
                <span>Ingestion Blockers &amp; Errors ({validationReport.errors.length}):</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-[11px] text-rose-800 dark:text-rose-300">
                {validationReport.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings List */}
          {validationReport.warnings && validationReport.warnings.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-slate-200">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span>Validation Observations &amp; Limitations ({validationReport.warnings.length}):</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-600 dark:text-slate-400">
                {validationReport.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Analysis Result Banner */}
      {analysisResult && (
        <div className="p-6 rounded-2xl border border-emerald-400 bg-emerald-50/80 dark:bg-emerald-950/40 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-7 h-7 text-emerald-600 dark:text-emerald-400" />
              <div>
                <h3 className="text-base font-bold text-emerald-900 dark:text-emerald-200">
                  Dataset Successfully Analyzed &amp; Scored!
                </h3>
                <p className="text-xs text-emerald-700 dark:text-emerald-400">
                  Scored {analysisResult.pages_analyzed.toLocaleString()} pages &bull; Generated opportunity rankings, multi-factor decision reasons, and behavioral archetypes.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push("/dashboard/opportunities")}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors"
              >
                Open Opportunities Queue
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2 border-t border-emerald-200 dark:border-emerald-800 text-xs">
            <div>
              <span className="text-slate-500">Pages Analyzed:</span>
              <div className="font-bold text-emerald-900 dark:text-emerald-200 text-base">
                {analysisResult.pages_analyzed.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-slate-500">High Priority Pages:</span>
              <div className="font-bold text-amber-600 text-base">
                {analysisResult.high_priority_count.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-slate-500">Critical Pages:</span>
              <div className="font-bold text-rose-600 text-base">
                {analysisResult.critical_count.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dataset Inventory Table */}
      <div className="glass-card rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm space-y-4 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Dataset Inventory &amp; Workspaces
            </h2>
            <p className="text-xs text-slate-500">
              Manage installed catalogs and switch the active decision-support workspace.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {datasets.length} catalog{datasets.length === 1 ? "" : "s"} registered
          </span>
        </div>

        {deleteError && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 text-xs text-rose-700">
            {deleteError}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/60 dark:bg-slate-900/60 text-slate-500 font-bold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="py-3 px-3">Dataset Name</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3 text-right">Rows</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-3">Scoring Model</th>
                <th className="py-3 px-3 text-center">Active</th>
                <th className="py-3 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/60 dark:divide-slate-800/60">
              {datasets.map((d) => {
                const isActive = activeDataset?.dataset_id === d.dataset_id;
                return (
                  <tr
                    key={d.dataset_id}
                    className={`hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors ${
                      isActive ? "bg-emerald-50/30 dark:bg-emerald-950/20" : ""
                    }`}
                  >
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {d.name}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {d.dataset_id}
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      {d.is_starter ? (
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-900">
                          Starter Demo
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-900">
                          Custom
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                      {d.row_count.toLocaleString()}
                    </td>

                    <td className="py-3 px-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          d.validation_status === "VALID" || d.validation_status === "READY"
                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                            : "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                        }`}
                      >
                        {d.validation_status}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                      {d.model_name || "Gradient Boosting"}
                    </td>

                    <td className="py-3 px-3 text-center">
                      {isActive ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Active
                        </span>
                      ) : (
                        <button
                          onClick={() => setActiveDataset(d)}
                          className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors"
                        >
                          Set Active
                        </button>
                      )}
                    </td>

                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Analyze Button */}
                        <button
                          onClick={() => handleAnalyze(d.dataset_id)}
                          disabled={isAnalyzing}
                          className="px-2 py-1 rounded-lg text-[11px] font-semibold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 transition-colors disabled:opacity-40"
                          title="Run scoring and grouping pipeline"
                        >
                          Analyze
                        </button>

                        {/* Delete Button */}
                        {d.is_starter ? (
                          <span
                            className="p-1 text-slate-300 dark:text-slate-700 cursor-not-allowed"
                            title="The starter dataset is protected from deletion"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </span>
                        ) : (
                          <button
                            onClick={() => handleDelete(d)}
                            disabled={deletingId === d.dataset_id}
                            className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded transition-colors"
                            title="Delete custom dataset"
                          >
                            {deletingId === d.dataset_id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-500" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
