"use client";

import React, { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/navigation/Sidebar";
import { TopHeader } from "@/components/navigation/TopHeader";
import { MarketingNavbar } from "@/components/navigation/MarketingNavbar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [isExpanded, setIsExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Restore sidebar preference from localStorage
  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("ci_sidebar_expanded");
    if (stored === "true") {
      setIsExpanded(true);
    }
  }, []);

  // Close mobile drawer on route transition
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const toggleExpand = () => {
    setIsExpanded((prev) => {
      const next = !prev;
      localStorage.setItem("ci_sidebar_expanded", String(next));
      return next;
    });
  };

  const isDashboard = pathname.startsWith("/dashboard");

  if (!isDashboard) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#090d16] text-slate-900 dark:text-slate-100 transition-colors duration-200">
        <MarketingNavbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200/80 dark:border-slate-800/80 py-6 text-center text-xs text-slate-500 dark:text-slate-500">
          <p>ContentSignal &bull; Observational Decision-Support Platform</p>
          <p className="mt-1 text-[11px] text-slate-400">
            Claims are observational, estimated, and directional &bull; Never causal guarantees.
          </p>
        </footer>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#090d16] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Left Icon-First Sidebar */}
      <Sidebar
        isExpanded={isExpanded}
        onToggleExpand={toggleExpand}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main Column (Header + Page Content + Footer) */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          isExpanded ? "lg:pl-64" : "lg:pl-16"
        }`}
      >
        <TopHeader onMobileToggle={() => setMobileOpen((prev) => !prev)} />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-slate-200/80 dark:border-slate-800/80 py-6 text-center text-xs text-slate-500 dark:text-slate-500">
          <p>ContentSignal &bull; Observational Decision-Support Platform</p>
          <p className="mt-1 text-[11px] text-slate-400">
            Claims are observational, estimated, and directional &bull; Never causal guarantees.
          </p>
        </footer>
      </div>
    </div>
  );
}
