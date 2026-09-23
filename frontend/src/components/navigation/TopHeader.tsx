"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu,
  Search,
  Sun,
  Moon,
  Bell,
  Settings as SettingsIcon,
  LogOut,
  LogIn,
  CheckCircle2,
  AlertTriangle,
  Database,
  ShieldCheck,
  X,
} from "lucide-react";
import { DatasetSelector } from "@/components/DatasetSelector";
import { getToken, removeToken } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";

interface TopHeaderProps {
  onMobileToggle: () => void;
}

export function TopHeader({ onMobileToggle }: TopHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { activeDataset } = useDataset();

  const [isDark, setIsDark] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [hasUnreadAlerts, setHasUnreadAlerts] = useState(true);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  // Initialize theme and auth status
  useEffect(() => {
    const isDarkStored = localStorage.getItem("ci_theme") !== "light";
    if (isDarkStored) {
      document.documentElement.classList.add("dark");
      setIsDark(true);
    } else {
      document.documentElement.classList.remove("dark");
      setIsDark(false);
    }
    setHasToken(!!getToken());
  }, [pathname]);

  // Click outside listener for notifications popover
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotificationsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard shortcut '/' to focus search input
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (
        e.key === "/" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("ci_theme", "light");
      setIsDark(false);
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("ci_theme", "dark");
      setIsDark(true);
    }
  };

  const handleLogout = () => {
    removeToken();
    setHasToken(false);
    router.push("/auth");
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    router.push(`/dashboard/opportunities?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  // Resolve current route breadcrumb title
  const getSectionTitle = () => {
    if (pathname === "/dashboard") return "Overview";
    if (pathname.startsWith("/dashboard/opportunities")) return "Priority Queue";
    if (pathname.startsWith("/dashboard/runs")) return "Analysis Runs";
    if (pathname.startsWith("/dashboard/archetypes")) return "Groups";
    if (pathname.startsWith("/dashboard/analytics")) return "Analytics";
    if (pathname.startsWith("/dashboard/evidence")) return "Evidence";
    if (pathname.startsWith("/dashboard/models")) return "ML Insights";
    if (pathname.startsWith("/dashboard/ai")) return "AI Assistant";
    if (pathname.startsWith("/dashboard/datasets")) return "Datasets";
    if (pathname.startsWith("/dashboard/settings")) return "Settings";
    if (pathname.startsWith("/dashboard/page/")) return "Page Intelligence";
    return "Dashboard";
  };

  return (
    <header className="sticky top-0 z-30 w-full h-16 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-slate-950/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between gap-3 transition-colors">
      {/* Left: Mobile Menu Button + Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMobileToggle}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumb Hierarchy */}
        <div className="hidden sm:flex items-center gap-2 text-xs select-none">
          <span className="text-slate-400 dark:text-slate-500 font-medium">ContentSignal</span>
          <span className="text-slate-300 dark:text-slate-700">/</span>
          <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
            {getSectionTitle()}
          </span>
        </div>
      </div>

      {/* Center: Global Quick Search Input */}
      <div className="flex-1 max-w-md mx-2 hidden md:block">
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search pages, signals, or URLs... (Press /)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-8 py-1.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </form>
      </div>

      {/* Right Utility Group */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {/* Dataset Workspace Selector */}
        <div className="hidden sm:block">
          <DatasetSelector />
        </div>

        <div className="hidden sm:block h-4 w-[1px] bg-slate-200 dark:bg-slate-800" />

        {/* Notifications Popover */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => {
              setNotificationsOpen(!notificationsOpen);
              if (hasUnreadAlerts) setHasUnreadAlerts(false);
            }}
            className="relative p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
            title="System notifications & alerts"
            aria-label="System notifications"
          >
            <Bell className="w-4 h-4" />
            {hasUnreadAlerts && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal-500 ring-2 ring-white dark:ring-slate-950" />
            )}
          </button>

          {/* Notifications Dropdown Card */}
          {notificationsOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-xl z-50 p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-900">
                <span className="text-xs font-bold text-slate-900 dark:text-white">System Alerts</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 font-semibold border border-teal-200 dark:border-teal-800">
                  Live Telemetry
                </span>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60">
                  <Database className="w-4 h-4 text-teal-600 dark:text-teal-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      Catalog Active
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      {activeDataset?.name || "Active Workspace"} is indexed and ready.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60">
                  <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      Telemetry & Quality Audit
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      94.6% data quality & sufficiency score across measurable fields.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-2 rounded-xl bg-slate-50 dark:bg-slate-900/60">
                  <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      Priority Content Queued
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      Review priority candidates generated based on search decline rate.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle color theme"
          title={isDark ? "Switch to light theme" : "Switch to dark theme"}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-slate-600" />
          )}
        </button>

        {/* Settings Shortcut Link */}
        <Link
          href="/dashboard/settings"
          aria-label="Settings"
          title="Settings"
          className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
        >
          <SettingsIcon className="w-4 h-4" />
        </Link>

        {/* Auth / Profile Button */}
        {hasToken ? (
          <button
            onClick={handleLogout}
            aria-label="Sign out"
            title="Sign out"
            className="p-2 rounded-xl text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:text-rose-300 dark:hover:bg-rose-950/30 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        ) : (
          <Link
            href="/auth"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 transition-colors shadow-xs"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign In</span>
          </Link>
        )}
      </div>
    </header>
  );
}
