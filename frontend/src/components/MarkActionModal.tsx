"use client";

import React, { useState } from "react";
import { CheckCircle2, X, AlertCircle, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  isOpen: boolean;
  pageId: string;
  pageTitle?: string;
  initialAction?: string;
  datasetId?: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function MarkActionModal({
  isOpen,
  pageId,
  pageTitle,
  initialAction = "REFRESH",
  datasetId = "starter-flyrank",
  onClose,
  onSuccess,
}: Props) {
  const [actionType, setActionType] = useState(initialAction);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setActionType(initialAction || "REFRESH");
      setNotes("");
      setError("");
      setSuccess(false);
      setLoading(false);
    }
  }, [isOpen, pageId, initialAction]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await api.markImpactAction({
        page_id: pageId,
        action_type: actionType,
        notes: notes.trim() || undefined,
        dataset_id: datasetId,
      });
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 600);
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        setError("Unable to connect to backend server. Please verify the API server is active on port 8001.");
      } else {
        setError(msg || "Failed to mark action.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <Sparkles className="w-4 h-4" />
            </span>
            <h3 className="text-base font-bold font-display text-slate-900 dark:text-white">
              Mark Action Taken
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
            Target Page:
          </p>
          <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
            {pageTitle || pageId}
          </p>
          <p className="text-[11px] font-mono text-slate-400">{pageId}</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl text-xs font-medium bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-900 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Intervention Type
            </label>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="REFRESH">REFRESH — Content update & factual refresh</option>
              <option value="OPTIMIZE">OPTIMIZE — Search snippet (Title/Meta/CTR)</option>
              <option value="MERGE">MERGE — Consolidate duplicate/overlapping pages</option>
              <option value="CANONICALIZE">CANONICALIZE — Canonical tag correction</option>
              <option value="PRUNE">PRUNE — Deprecate or 410 obsolete content</option>
              <option value="REWRITE">REWRITE — Complete structural overhaul</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Editorial Notes & Context (Optional)
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Updated statistics for 2026, refreshed title tag with primary keyword."
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
            />
          </div>

          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <p className="font-semibold text-slate-700 dark:text-slate-300">
              Impact Tracking Notice:
            </p>
            <p>
              Current baseline search metrics (Visibility, CTR, Position, Score) will be recorded. Subsequent dataset uploads will measure post-intervention performance delta.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || success}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : success ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              <span>{success ? "Action Logged!" : "Record Action Taken"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
