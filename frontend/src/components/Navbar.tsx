"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Sun,
  Moon,
  LogOut,
  LogIn,
  Menu,
  X,
  Settings as SettingsIcon,
} from "lucide-react";
import { getToken, removeToken } from "@/lib/api";
import { Logo } from "@/components/Logo";
import { DatasetSelector } from "@/components/DatasetSelector";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isDark, setIsDark] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Default is dark mode unless explicitly set to light
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

  // Close menus on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

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

  const isDashboard = pathname.startsWith("/dashboard");

  const dashboardNavItems = [
    { label: "Overview", href: "/dashboard" },
    { label: "Priority Queue", href: "/dashboard/opportunities" },
    { label: "Analysis Runs", href: "/dashboard/runs" },
    { label: "Groups", href: "/dashboard/archetypes" },
    { label: "Analytics", href: "/dashboard/analytics" },
    { label: "Evidence", href: "/dashboard/evidence" },
    { label: "ML Insights", href: "/dashboard/models" },
    { label: "AI Assistant", href: "/dashboard/ai" },
    { label: "Datasets", href: "/dashboard/datasets" },
  ];

  // Public marketing landing navigation
  const publicNavItems = [
    { label: "Platform", href: "/dashboard" },
    { label: "Architecture", href: "/#architecture" },
    { label: "Opportunities", href: "/dashboard/opportunities" },
    { label: "Model Benchmarks", href: "/dashboard/models" },
  ];

  const currentNavItems = isDashboard ? dashboardNavItems : publicNavItems;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Lockup: Logo + Wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <Link href="/" className="flex items-center gap-2.5 group select-none">
            <Logo size={26} className="group-hover:scale-105 transition-transform" />
            <span className="font-display font-semibold text-slate-900 dark:text-white tracking-tight text-[17px] whitespace-nowrap">
              Content<span className="text-teal-600 dark:text-teal-400">Signal</span>
            </span>
          </Link>
        </div>

        {/* Primary Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-3.5 xl:gap-5.5 2xl:gap-7 mx-auto">
          {currentNavItems.map((item) => {
            const active =
              pathname === item.href ||
              (item.href === "/dashboard/ai" && pathname === "/dashboard/ai-assistant") ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={(e) => {
                  if (item.href === "/#architecture" && pathname === "/") {
                    e.preventDefault();
                    document.getElementById("architecture")?.scrollIntoView({ behavior: "smooth" });
                  }
                }}
                className={`relative py-1 text-[13px] font-medium whitespace-nowrap transition-colors ${
                  active
                    ? "text-teal-700 dark:text-teal-400 font-semibold"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                {item.label}
                {active && (
                  <span className="absolute -bottom-[21px] left-0 right-0 h-[2px] bg-teal-600 dark:bg-teal-400 rounded-full" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Utility Group: Dataset Selector + Theme + Settings + Sign In / Out */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 ml-auto lg:ml-0">
          {/* Dataset Selector (Visible on Dashboard views) */}
          {isDashboard && (
            <div className="hidden sm:block">
              <DatasetSelector />
            </div>
          )}

          {isDashboard && (
            <div className="hidden sm:block h-4 w-[1px] bg-slate-200 dark:bg-slate-800" />
          )}

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle color theme"
            title="Toggle theme"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800/80 transition-colors"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-600" />
            )}
          </button>

          {/* Settings Direct Route Link */}
          <Link
            href="/dashboard/settings"
            aria-label="Settings"
            title="Settings"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800/80 transition-colors"
          >
            <SettingsIcon className="w-4 h-4" />
          </Link>

          {/* Auth Action: Sign Out when authenticated, Sign In when unauthenticated */}
          {hasToken ? (
            <button
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
              className="p-2 rounded-lg text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:text-rose-300 dark:hover:bg-rose-950/30 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          ) : (
            <Link
              href="/auth"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 transition-colors shadow-xs"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800/80 transition-colors"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile / Tablet Collapsible Menu Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 px-4 pt-3 pb-5 space-y-3">
          {/* Mobile Dataset Selector if on Dashboard */}
          {isDashboard && (
            <div className="pb-2 border-b border-slate-100 dark:border-slate-900">
              <DatasetSelector />
            </div>
          )}

          <div className="flex flex-col space-y-1">
            {currentNavItems.map((item) => {
              const active =
                pathname === item.href ||
                (item.href === "/dashboard/ai" && pathname === "/dashboard/ai-assistant") ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={(e) => {
                    setMobileMenuOpen(false);
                    if (item.href === "/#architecture" && pathname === "/") {
                      e.preventDefault();
                      document.getElementById("architecture")?.scrollIntoView({ behavior: "smooth" });
                    }
                  }}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    active
                      ? "bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 font-semibold"
                      : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}

            {/* Mobile Settings Link */}
            <Link
              href="/dashboard/settings"
              className="px-3 py-2 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900 flex items-center gap-2"
            >
              <SettingsIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>Settings</span>
            </Link>

            {hasToken ? (
              <button
                onClick={handleLogout}
                className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex items-center gap-2"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign out</span>
              </button>
            ) : (
              <Link
                href="/auth"
                className="px-3 py-2 rounded-lg text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 flex items-center gap-2"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
