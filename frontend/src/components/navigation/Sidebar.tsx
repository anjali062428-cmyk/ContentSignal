"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Layers,
  ListOrdered,
  BarChart3,
  TrendingUp,
  History,
  ShieldCheck,
  Bot,
  FolderKanban,
  Database,
  Settings,
  User,
  ChevronLeft,
  ChevronRight,
  X,
  LogOut,
} from "lucide-react";
import { Logo } from "@/components/Logo";
import { getToken, removeToken } from "@/lib/api";

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const NAV_GROUP_1: NavItem[] = [
  { id: "overview", label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { id: "all_content", label: "All Content", href: "/dashboard/opportunities", icon: Layers },
  { id: "priority_queue", label: "Priority Queue", href: "/dashboard/opportunities", icon: ListOrdered },
  { id: "analytics", label: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
];

export const NAV_GROUP_2: NavItem[] = [
  { id: "trends", label: "Trends", href: "/dashboard/archetypes", icon: TrendingUp },
  { id: "runs", label: "Analysis Runs", href: "/dashboard/runs", icon: History },
  { id: "quality", label: "Data Quality", href: "/dashboard/evidence", icon: ShieldCheck },
  { id: "ai", label: "AI Assistant", href: "/dashboard/ai", icon: Bot },
];

export const NAV_GROUP_3: NavItem[] = [
  { id: "projects", label: "Projects", href: "/dashboard/models", icon: FolderKanban },
  { id: "datasets", label: "Datasets", href: "/dashboard/datasets", icon: Database },
];

interface SidebarProps {
  isExpanded: boolean;
  onToggleExpand: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({
  isExpanded,
  onToggleExpand,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(!!getToken());
  }, [pathname]);

  const handleLogout = () => {
    removeToken();
    setHasToken(false);
    onMobileClose();
    router.push("/auth");
  };

  const isItemActive = (item: NavItem) => {
    if (item.id === "overview") {
      return pathname === "/dashboard";
    }
    if (item.id === "all_content") {
      return false;
    }
    if (item.id === "priority_queue") {
      return pathname === "/dashboard/opportunities";
    }
    if (item.id === "ai") {
      return pathname === "/dashboard/ai" || pathname === "/dashboard/ai-assistant";
    }
    return pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
  };

  const renderNavGroup = (items: NavItem[]) => (
    <div className="space-y-1">
      {items.map((item) => {
        const active = isItemActive(item);
        const Icon = item.icon;

        return (
          <div key={item.id} className="relative group">
            <Link
              href={item.href}
              onClick={onMobileClose}
              className={`flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium transition-all ${
                active
                  ? "bg-teal-500/10 text-teal-600 dark:bg-teal-500/15 dark:text-teal-400 font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900"
              } ${!isExpanded && !mobileOpen ? "justify-center" : ""}`}
            >
              <Icon
                className={`w-5 h-5 shrink-0 transition-colors ${
                  active
                    ? "text-teal-600 dark:text-teal-400"
                    : "text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-slate-200"
                }`}
              />

              {(isExpanded || mobileOpen) && (
                <span className="truncate whitespace-nowrap">{item.label}</span>
              )}

              {/* Active Indicator Bar when collapsed */}
              {active && !isExpanded && !mobileOpen && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-teal-600 dark:bg-teal-400 rounded-r-full" />
              )}
            </Link>

            {/* Hover Tooltip in Collapsed Mode */}
            {!isExpanded && !mobileOpen && (
              <div className="fixed left-16 ml-3 px-2.5 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-800 text-white text-xs font-medium shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap border border-slate-700/80">
                {item.label}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onMobileClose}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-40 lg:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 flex flex-col bg-white dark:bg-[#080d1a] border-r border-slate-200/80 dark:border-slate-800/80 transition-all duration-300 ease-in-out ${
          isExpanded ? "w-64" : "w-16"
        } ${
          mobileOpen
            ? "translate-x-0 w-64 shadow-2xl"
            : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Logo / Brand Lockup Header */}
        <div className="h-16 flex items-center justify-between px-3.5 border-b border-slate-200/80 dark:border-slate-800/80 shrink-0">
          <Link
            href="/dashboard"
            onClick={onMobileClose}
            className={`flex items-center gap-2.5 group select-none min-w-0 ${
              !isExpanded && !mobileOpen ? "mx-auto" : ""
            }`}
            title="ContentSignal Dashboard"
          >
            <Logo size={26} className="group-hover:scale-105 transition-transform shrink-0" />
            {(isExpanded || mobileOpen) && (
              <span className="font-display font-bold text-slate-900 dark:text-white tracking-tight text-[16px] whitespace-nowrap truncate">
                Content<span className="text-teal-600 dark:text-teal-400">Signal</span>
              </span>
            )}
          </Link>

          {/* Mobile Close Button */}
          <button
            onClick={onMobileClose}
            className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Navigation Groups */}
        <div className="flex-1 py-3 px-2 space-y-2 overflow-y-auto overflow-x-hidden">
          {/* Group 1: Overview, All Content, Priority Queue, Analytics */}
          {renderNavGroup(NAV_GROUP_1)}

          {/* Divider 1 */}
          <div className="my-2 mx-2 border-t border-slate-200/80 dark:border-slate-800/80" />

          {/* Group 2: Trends, Analysis Runs, Data Quality, AI Assistant */}
          {renderNavGroup(NAV_GROUP_2)}

          {/* Divider 2 */}
          <div className="my-2 mx-2 border-t border-slate-200/80 dark:border-slate-800/80" />

          {/* Group 3: Projects, Datasets */}
          {renderNavGroup(NAV_GROUP_3)}
        </div>

        {/* Divider 3 before Bottom Section */}
        <div className="mx-4 border-t border-slate-200/80 dark:border-slate-800/80 shrink-0" />

        {/* Bottom Group: Settings, Profile, Expand Toggle */}
        <div className="p-2 space-y-1 shrink-0">
          {/* Settings Item */}
          <div className="relative group">
            <Link
              href="/dashboard/settings"
              onClick={onMobileClose}
              className={`flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium transition-colors ${
                pathname === "/dashboard/settings"
                  ? "bg-teal-500/10 text-teal-600 dark:bg-teal-500/15 dark:text-teal-400 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900"
              } ${!isExpanded && !mobileOpen ? "justify-center" : ""}`}
            >
              <Settings className="w-5 h-5 shrink-0 text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-slate-200" />
              {(isExpanded || mobileOpen) && <span className="truncate">Settings</span>}
            </Link>

            {!isExpanded && !mobileOpen && (
              <div className="fixed left-16 ml-3 px-2.5 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-800 text-white text-xs font-medium shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap border border-slate-700/80">
                Settings
              </div>
            )}
          </div>

          {/* Profile / Auth Item */}
          <div className="relative group">
            {hasToken ? (
              <button
                onClick={handleLogout}
                className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:text-rose-300 dark:hover:bg-rose-950/30 transition-colors ${
                  !isExpanded && !mobileOpen ? "justify-center" : ""
                }`}
              >
                <LogOut className="w-5 h-5 shrink-0" />
                {(isExpanded || mobileOpen) && <span className="truncate">Sign Out</span>}
              </button>
            ) : (
              <Link
                href="/auth"
                onClick={onMobileClose}
                className={`flex items-center gap-3 px-2.5 py-2 rounded-xl text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-900 transition-colors ${
                  !isExpanded && !mobileOpen ? "justify-center" : ""
                }`}
              >
                <User className="w-5 h-5 shrink-0" />
                {(isExpanded || mobileOpen) && <span className="truncate">Sign In / Profile</span>}
              </Link>
            )}

            {!isExpanded && !mobileOpen && (
              <div className="fixed left-16 ml-3 px-2.5 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-800 text-white text-xs font-medium shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap border border-slate-700/80">
                {hasToken ? "Sign Out" : "Sign In / Profile"}
              </div>
            )}
          </div>

          {/* Desktop Expand / Collapse Button */}
          <div className="hidden lg:block pt-1">
            <button
              onClick={onToggleExpand}
              className={`w-full flex items-center gap-3 px-2.5 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-500 dark:hover:text-slate-200 dark:hover:bg-slate-900 transition-colors ${
                !isExpanded ? "justify-center" : ""
              }`}
              title={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
            >
              {isExpanded ? (
                <>
                  <ChevronLeft className="w-4 h-4 shrink-0" />
                  <span className="truncate text-[11px]">Collapse</span>
                </>
              ) : (
                <ChevronRight className="w-4 h-4 shrink-0" />
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
