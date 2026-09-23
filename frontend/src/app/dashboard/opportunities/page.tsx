"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Download,
  ArrowUpDown,
  ExternalLink,
  Globe,
  FileText,
  Star,
  CheckCircle2,
  FileSpreadsheet,
  TrendingDown,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import { api, PaginatedOpportunities, OpportunityItem } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";
import { LoadingState, EmptyState, ErrorState } from "@/components/UIStates";
import { MarkActionModal } from "@/components/MarkActionModal";

export default function OpportunityQueuePage() {
  const { activeDataset } = useDataset();
  const [data, setData] = useState<PaginatedOpportunities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter and Sorting State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState("");
  const [smartFilter, setSmartFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [confidenceFilter, setConfidenceFilter] = useState("ALL");
  const [priority, setPriority] = useState("ALL");
  const [action, setAction] = useState("ALL");
  const [contentType, setContentType] = useState("ALL");
  const [domainFilter, setDomainFilter] = useState("ALL");
  const [pageTypeFilter, setPageTypeFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("opportunity_score");
  const [sortOrder, setSortOrder] = useState("desc");

  // Watchlist & Action Modal State
  const [watchlistIds, setWatchlistIds] = useState<Set<string>>(new Set());
  const [actionModalTarget, setActionModalTarget] = useState<{
    pageId: string;
    pageTitle?: string;
    initialAction?: string;
  } | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Load Watchlist IDs for this dataset
  const fetchWatchlistIds = async () => {
    try {
      const ids = await api.getWatchlistIds(activeDataset?.dataset_id);
      setWatchlistIds(new Set(ids));
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    fetchWatchlistIds();
  }, [activeDataset?.dataset_id]);

  // Reset domain filters when dataset switches
  useEffect(() => {
    setDomainFilter("ALL");
    setPageTypeFilter("ALL");
    setSmartFilter("ALL");
    setStatusFilter("ALL");
    setConfidenceFilter("ALL");
    setPage(1);
  }, [activeDataset?.dataset_id]);

  const fetchOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getOpportunities({
        page,
        page_size: pageSize,
        search,
        smart_filter: smartFilter !== "ALL" ? smartFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        content_status: statusFilter !== "ALL" ? statusFilter : undefined,
        confidence: confidenceFilter !== "ALL" ? confidenceFilter : undefined,
        confidence_tier: confidenceFilter !== "ALL" ? confidenceFilter : undefined,
        priority,
        action,
        content_type: contentType,
        domain: domainFilter,
        page_type: pageTypeFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        dataset_id: activeDataset?.dataset_id,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load opportunities queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOpportunities();
  }, [
    page,
    pageSize,
    smartFilter,
    statusFilter,
    confidenceFilter,
    priority,
    action,
    contentType,
    domainFilter,
    pageTypeFilter,
    sortBy,
    sortOrder,
    activeDataset?.dataset_id,
  ]);

  const handleToggleStar = async (pageId: string) => {
    try {
      const res = await api.toggleWatchlist(pageId, activeDataset?.dataset_id);
      setWatchlistIds((prev) => {
        const next = new Set(prev);
        if (res.is_starred) next.add(pageId);
        else next.delete(pageId);
        return next;
      });
      setToastMessage(res.is_starred ? `Starred ${pageId} to Watchlist` : `Removed ${pageId} from Watchlist`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch {
      // Ignore
    }
  };

  const handleWorkflowChange = async (pageId: string, newState: string) => {
    try {
      await api.setPageActionState({
        page_id: pageId,
        state: newState,
        dataset_id: activeDataset?.dataset_id,
      });
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) =>
            item.page_id === pageId ? { ...item, action_state: newState as any } : item
          ),
        };
      });
      const formatted = newState.replace("_", " ");
      setToastMessage(`Updated workflow status for ${pageId} to ${formatted}`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err: any) {
      setToastMessage(`Failed to update workflow state: ${err.message}`);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchOpportunities();
  };

  const handleExport = () => {
    const url = api.exportCsvUrl(priority, action, activeDataset?.dataset_id);
    window.open(url, "_blank");
  };

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case "CRITICAL":
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 border-rose-200 dark:border-rose-900";
      case "HIGH":
        return "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 border-amber-200 dark:border-amber-900";
      case "MEDIUM":
        return "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border-blue-200 dark:border-blue-900";
      default:
        return "bg-slate-50 text-slate-700 dark:bg-slate-900 dark:text-slate-300 border-slate-200 dark:border-slate-800";
    }
  };

  const getActionBadge = (act: string) => {
    switch (act) {
      case "REFRESH":
        return "bg-rose-600 text-white";
      case "OPTIMIZE":
        return "bg-purple-600 text-white";
      case "PROTECT":
        return "bg-emerald-600 text-white";
      case "INVESTIGATE":
        return "bg-amber-600 text-white";
      case "MERGE":
        return "bg-orange-600 text-white";
      case "REWRITE":
        return "bg-rose-700 text-white";
      default:
        return "bg-slate-600 text-white";
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "REFRESH NOW":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30";
      case "REVIEW":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30";
      case "MONITOR":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30";
      case "STABLE":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
      case "INSUFFICIENT DATA":
        return "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/30";
    }
  };

  const getConfidenceBadge = (tier?: string) => {
    switch (tier) {
      case "HIGH":
        return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30";
      case "MEDIUM":
        return "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30";
      case "LOW":
        return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30";
    }
  };

  const hasDomainData = Boolean(data?.has_domain_data);

  const isAnyFilterActive =
    search !== "" ||
    smartFilter !== "ALL" ||
    statusFilter !== "ALL" ||
    confidenceFilter !== "ALL" ||
    priority !== "ALL" ||
    action !== "ALL" ||
    contentType !== "ALL" ||
    domainFilter !== "ALL" ||
    pageTypeFilter !== "ALL";

  const handleResetFilters = () => {
    setSearch("");
    setSmartFilter("ALL");
    setStatusFilter("ALL");
    setConfidenceFilter("ALL");
    setPriority("ALL");
    setAction("ALL");
    setContentType("ALL");
    setDomainFilter("ALL");
    setPageTypeFilter("ALL");
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Mark Action Modal */}
      <MarkActionModal
        isOpen={!!actionModalTarget}
        pageId={actionModalTarget?.pageId || ""}
        pageTitle={actionModalTarget?.pageTitle}
        initialAction={actionModalTarget?.initialAction}
        datasetId={activeDataset?.dataset_id}
        onClose={() => setActionModalTarget(null)}
        onSuccess={() => {
          setToastMessage(`Action logged successfully for ${actionModalTarget?.pageId}`);
          setTimeout(() => setToastMessage(null), 3500);
          fetchOpportunities();
        }}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-3 rounded-2xl bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>{toastMessage}</span>
          </div>
          <button onClick={() => setToastMessage(null)} className="text-xs hover:underline text-emerald-600 dark:text-emerald-400">
            Dismiss
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
            Opportunity Review Queue
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Ranked candidate pages for{" "}
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
              {activeDataset?.name || "Active Catalog"}
            </span>
            . Ordered by opportunity score.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/evidence"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-xl transition-all shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            Evidence Exports
          </Link>
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:hover:bg-slate-100 dark:text-slate-900 rounded-xl transition-all shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV ({data?.total.toLocaleString() || "..."})
          </button>
        </div>
      </div>

      {/* Smart Filters Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-[11px] font-bold text-slate-400 uppercase font-mono mr-1">
          Smart Filter:
        </span>
        {[
          { id: "ALL", label: "All Inventory" },
          { id: "watchlist", label: `⭐ Watchlist (${watchlistIds.size})` },
          { id: "high_impact", label: "🔥 High Impact (Score ≥ 70)" },
          { id: "quick_wins", label: "⚡ Quick Wins (CTR Optimize)" },
          { id: "decaying_fast", label: "📉 Decaying Fast (Refresh)" },
          { id: "high_visibility", label: "👁️ High Visibility (5k+)" },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => {
              setSmartFilter(f.id);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-xl font-semibold whitespace-nowrap transition-all ${
              smartFilter === f.id
                ? "bg-emerald-600 text-white shadow-glow-sm"
                : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:border-emerald-500/50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-card p-4 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={
                hasDomainData
                  ? "Search by page ID, client ID, domain, or title..."
                  : "Search by page ID or client ID..."
              }
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white rounded-xl transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
          {/* Status Filter (V2 Master Standard) */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="REFRESH NOW">REFRESH NOW</option>
              <option value="REVIEW">REVIEW</option>
              <option value="MONITOR">MONITOR</option>
              <option value="STABLE">STABLE</option>
              <option value="INSUFFICIENT DATA">INSUFFICIENT DATA</option>
            </select>
          </div>

          {/* Confidence Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Confidence:</span>
            <select
              value={confidenceFilter}
              onChange={(e) => {
                setConfidenceFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Confidence</option>
              <option value="HIGH">High Confidence</option>
              <option value="MEDIUM">Medium Confidence</option>
              <option value="LOW">Low Confidence</option>
            </select>
          </div>

          {/* Priority Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Priority:</span>
            <select
              value={priority}
              onChange={(e) => {
                setPriority(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {/* Action Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Action:</span>
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Actions</option>
              <option value="REFRESH">REFRESH</option>
              <option value="OPTIMIZE">OPTIMIZE</option>
              <option value="PROTECT">PROTECT</option>
              <option value="INVESTIGATE">INVESTIGATE</option>
              <option value="MONITOR">MONITOR</option>
              <option value="MERGE">MERGE</option>
              <option value="REWRITE">REWRITE</option>
            </select>
          </div>

          {/* Optional Domain Filter (only rendered if dataset has domain data) */}
          {hasDomainData && (
            <div className="flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
              <span className="text-slate-500 dark:text-slate-400 font-medium">Domain:</span>
              <select
                value={domainFilter}
                onChange={(e) => {
                  setDomainFilter(e.target.value);
                  setPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none max-w-[150px] truncate"
              >
                <option value="ALL">All Domains</option>
                {data?.available_domains?.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Optional Page Type Filter (only rendered if dataset has domain data) */}
          {hasDomainData && (
            <div className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
              <span className="text-slate-500 dark:text-slate-400 font-medium">Page Type:</span>
              <select
                value={pageTypeFilter}
                onChange={(e) => {
                  setPageTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none max-w-[150px] truncate"
              >
                <option value="ALL">All Page Types</option>
                {data?.available_page_types?.map((pt) => (
                  <option key={pt} value={pt}>
                    {pt}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sort By */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Sort By:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="opportunity_score">Opportunity</option>
              <option value="impressions_90d">Visibility (90d)</option>
              <option value="ctr">Click Rate</option>
              <option value="avg_position">Position</option>
              <option value="days_since_last_update">Freshness</option>
              <option value="confidence">Confidence</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300"
              title={`Sort order: ${sortOrder.toUpperCase()}`}
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
            </button>
            {isAnyFilterActive && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-2.5 py-1 rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 text-xs font-semibold hover:bg-rose-100 dark:hover:bg-rose-900/60 transition-colors"
                title="Reset all search queries and active filters"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Table Content */}
      {loading ? (
        <LoadingState message="Querying paginated opportunities catalog..." />
      ) : error ? (
        <ErrorState title="Failed to Load Queue" message={error} onRetry={fetchOpportunities} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No Matching Pages Found"
          message="No pages match the active combination of search and filter settings."
          onReset={handleResetFilters}
        />
      ) : (
        <div className="space-y-4">
          <div className="glass-card rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100/60 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 font-bold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-3 px-2 w-8 text-center">⭐</th>
                    <th className="py-3 px-2 w-10 text-center">Rank</th>
                    <th className="py-3 px-3">Content Asset</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3 text-center">Score</th>
                    <th className="py-3 px-3 text-center">Confidence</th>
                    <th className="py-3 px-3 text-right">30d Trend</th>
                    <th className="py-3 px-4">Primary Reason</th>
                    <th className="py-3 px-3">Action</th>
                    <th className="py-3 px-3">Workflow</th>
                    <th className="py-3 px-3 text-center">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/60 dark:divide-slate-800/60">
                  {data.items.map((item) => {
                    const trend = item.trend_pct;
                    const confidenceLabel = item.confidence_tier || (item.confidence >= 0.8 ? "HIGH" : item.confidence >= 0.6 ? "MEDIUM" : "LOW");
                    const currentWorkflow = item.action_state || "TO_REVIEW";

                    return (
                      <tr
                        key={item.page_id}
                        className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors"
                      >
                        {/* 0. Star */}
                        <td className="py-3 px-2 text-center">
                          <button
                            onClick={() => handleToggleStar(item.page_id)}
                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            title={watchlistIds.has(item.page_id) ? "Remove from Watchlist" : "Star to Watchlist"}
                          >
                            <Star
                              className={`w-3.5 h-3.5 transition-colors ${
                                watchlistIds.has(item.page_id)
                                  ? "fill-amber-400 text-amber-400"
                                  : "text-slate-300 dark:text-slate-600 hover:text-amber-400"
                              }`}
                            />
                          </button>
                        </td>

                        {/* 0. Rank */}
                        <td className="py-3 px-2 text-center font-mono font-semibold text-slate-400 text-[11px]">
                          #{item.queue_rank}
                        </td>

                        {/* 1. Content Title / URL / ID */}
                        <td className="py-3 px-3 max-w-[210px]">
                          <div
                            className="font-semibold text-slate-900 dark:text-slate-100 truncate"
                            title={item.page_title || item.url || item.page_id}
                          >
                            {item.page_title || item.url || item.page_id}
                          </div>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono mt-0.5">
                            {item.domain ? (
                              <span className="truncate max-w-[90px]">{item.domain}</span>
                            ) : (
                              <span>{item.content_type || "asset"}</span>
                            )}
                            <span>•</span>
                            <span className="truncate max-w-[100px]">{item.page_id}</span>
                          </div>
                        </td>

                        {/* 2. Status */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-bold border ${getStatusBadge(
                              item.content_status
                            )}`}
                          >
                            {item.content_status || "MONITOR"}
                          </span>
                        </td>

                        {/* 3. Opportunity Score */}
                        <td className="py-3 px-3 text-center">
                          <span className="font-display font-extrabold text-sm text-teal-600 dark:text-teal-400">
                            {item.opportunity_score.toFixed(0)}
                          </span>
                        </td>

                        {/* 4. Confidence Tier */}
                        <td className="py-3 px-3 text-center whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold border ${getConfidenceBadge(
                              confidenceLabel
                            )}`}
                          >
                            {confidenceLabel}
                          </span>
                        </td>

                        {/* 5. 30d Trend */}
                        <td className="py-3 px-3 text-right font-mono font-medium whitespace-nowrap">
                          {trend !== undefined && trend !== null ? (
                            <span
                              className={`inline-flex items-center gap-0.5 ${
                                trend < -5
                                  ? "text-rose-600 dark:text-rose-400"
                                  : trend > 5
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-slate-500"
                              }`}
                            >
                              {trend < 0 ? (
                                <TrendingDown className="w-3 h-3 shrink-0" />
                              ) : trend > 0 ? (
                                <TrendingUp className="w-3 h-3 shrink-0" />
                              ) : null}
                              {trend > 0 ? `+${trend.toFixed(1)}%` : `${trend.toFixed(1)}%`}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* 6. Primary Reason */}
                        <td className="py-3 px-4 max-w-[220px]">
                          <div className="font-medium text-slate-800 dark:text-slate-200 truncate" title={item.primary_reason}>
                            {item.primary_reason}
                          </div>
                          {item.trend_classification && (
                            <div className="text-[10px] text-slate-400 capitalize truncate">
                              {item.trend_classification.replace("_", " ")}
                            </div>
                          )}
                        </td>

                        {/* 7. Recommended Action */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-bold ${getActionBadge(
                              item.action
                            )}`}
                          >
                            {item.action}
                          </span>
                        </td>

                        {/* 8. Action State / Workflow */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <select
                            value={currentWorkflow}
                            onChange={(e) => handleWorkflowChange(item.page_id, e.target.value)}
                            className={`px-2 py-1 text-[11px] font-semibold rounded-lg border transition-colors cursor-pointer focus:outline-none ${
                              currentWorkflow === "COMPLETED"
                                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                                : currentWorkflow === "IN_PROGRESS"
                                ? "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30"
                                : currentWorkflow === "DISMISSED"
                                ? "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/30"
                                : "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30"
                            }`}
                          >
                            <option value="TO_REVIEW">To Review</option>
                            <option value="IN_PROGRESS">In Progress</option>
                            <option value="COMPLETED">Completed</option>
                            <option value="DISMISSED">Dismissed</option>
                          </select>
                        </td>

                        {/* Inspect link */}
                        <td className="py-3 px-3 text-center whitespace-nowrap">
                          <div className="flex items-center justify-center gap-1.5">
                            <button
                              onClick={() =>
                                setActionModalTarget({
                                  pageId: item.page_id,
                                  pageTitle: item.page_title || item.page_id,
                                  initialAction: item.action,
                                })
                              }
                              className="px-2 py-1 text-[10px] font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                              title="Log Manual Note/Intervention"
                            >
                              Log
                            </button>
                            <Link
                              href={`/dashboard/page/${item.page_id}`}
                              className="inline-flex items-center gap-0.5 px-2 py-1 text-[11px] font-semibold text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-950/40 rounded-lg border border-teal-500/20 transition-colors"
                            >
                              Inspect
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 px-1">
            <div>
              Showing {((page - 1) * pageSize + 1).toLocaleString()} to{" "}
              {Math.min(page * pageSize, data.total).toLocaleString()} of{" "}
              {data.total.toLocaleString()} pages
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium transition-colors"
              >
                Previous
              </button>
              <span className="font-mono text-slate-700 dark:text-slate-300 px-2">
                Page {page} of {data.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, data.total_pages))}
                disabled={page >= data.total_pages}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
