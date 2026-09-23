"use client";

import React, { useState, useEffect } from "react";
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

export function MarketingNavbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isDark, setIsDark] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  const navItems = [
    { label: "Platform", href: "/dashboard" },
    { label: "Architecture", href: "/#architecture" },
    { label: "Opportunities", href: "/dashboard/opportunities" },
    { label: "Model Benchmarks", href: "/dashboard/models" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Lockup */}
        <div className="flex items-center gap-3 shrink-0">
          <Link href="/" className="flex items-center gap-2.5 group select-none">
            <Logo size={26} className="group-hover:scale-105 transition-transform" />
            <span className="font-display font-semibold text-slate-900 dark:text-white tracking-tight text-[17px] whitespace-nowrap">
              Content<span className="text-teal-600 dark:text-teal-400">Signal</span>
            </span>
          </Link>
        </div>

        {/* Desktop Links */}
        <nav className="hidden md:flex items-center gap-6 mx-auto">
          {navItems.map((item) => {
            const active = pathname === item.href;
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
                className={`text-[13px] font-medium transition-colors ${
                  active
                    ? "text-teal-600 dark:text-teal-400 font-semibold"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Utilities */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
          <button
            onClick={toggleTheme}
            aria-label="Toggle color theme"
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-600" />
            )}
          </button>

          <Link
            href="/dashboard/settings"
            aria-label="Settings"
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
          >
            <SettingsIcon className="w-4 h-4" />
          </Link>

          {hasToken ? (
            <button
              onClick={handleLogout}
              aria-label="Sign out"
              className="p-2 rounded-xl text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:text-rose-300 dark:hover:bg-rose-950/30 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          ) : (
            <Link
              href="/auth"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 transition-colors shadow-xs"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
            className="md:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 px-4 pt-3 pb-5 space-y-2">
          {navItems.map((item) => (
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
              className="block px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
