"use client";

import React from "react";
import { Loader2, AlertCircle, Inbox, RefreshCw } from "lucide-react";

export function LoadingState({ message = "Loading editorial intelligence..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <Loader2 className="w-10 h-10 animate-spin text-emerald-500 mb-4" />
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{message}</p>
    </div>
  );
}

export function EmptyState({
  title = "No opportunities found",
  message = "Try clearing filters or adjusting your search criteria.",
  onReset,
}: {
  title?: string;
  message?: string;
  onReset?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center glass-card rounded-2xl">
      <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4 text-slate-400">
        <Inbox className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-4">{message}</p>
      {onReset && (
        <button
          onClick={onReset}
          className="px-4 py-2 text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
        >
          Reset Filters
        </button>
      )}
    </div>
  );
}

export function ErrorState({
  title = "Failed to load data",
  message = "An error occurred while communicating with the backend API.",
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center glass-card rounded-2xl border-rose-200 dark:border-rose-900/50">
      <div className="w-12 h-12 rounded-full bg-rose-50 dark:bg-rose-950/50 flex items-center justify-center mb-4 text-rose-500">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 rounded-lg transition-colors shadow-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Request
        </button>
      )}
    </div>
  );
}
