"use client";

import React, { useState } from "react";
import { Sparkles, Compass, CheckCircle2, ArrowRight, ShieldCheck, BarChart3, FileSpreadsheet } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  isOpen: boolean;
  userName?: string;
  onClose: () => void;
}

export function OnboardingModal({ isOpen, userName, onClose }: Props) {
  const [selectedGoal, setSelectedGoal] = useState<string>("recover_traffic");
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleComplete = async () => {
    setSubmitting(true);
    try {
      await api.completeOnboarding({ onboarded: true, primary_goal: selectedGoal });
    } catch {
      // Gracefully continue even if local/offline
    } finally {
      setSubmitting(false);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6 overflow-hidden">
        {/* Background decorative tint */}
        <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Header */}
        <div className="space-y-2 relative">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Welcome to ContentSignal</span>
          </div>
          <h2 className="text-2xl font-display font-bold text-slate-900 dark:text-white">
            Welcome{userName ? `, ${userName}` : ""}. Let&apos;s set up your workflow.
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            ContentSignal turns organic search snapshots into high-conviction editorial decisions. Here is how your team creates impact:
          </p>
        </div>

        {/* 3 Core Pillars */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 relative">
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 space-y-2">
            <div className="p-2 w-fit rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <BarChart3 className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">1. ML Opportunity Queue</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Prioritizes 30,000+ pages using Champion Gradient Boosting decay probability and 90-day search visibility.
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 space-y-2">
            <div className="p-2 w-fit rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Compass className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">2. Action Directives</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Every flagged page receives an explicit editorial recommendation: Refresh, Optimize CTR, or Protect.
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 space-y-2">
            <div className="p-2 w-fit rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <h4 className="text-xs font-bold text-slate-900 dark:text-white">3. Evidence & Tracking</h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Star items to Watchlist, record editorial actions, and export executive PDF, DOCX, and XLSX reports.
            </p>
          </div>
        </div>

        {/* Primary Goal Selection */}
        <div className="space-y-2 pt-1 relative">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            What is your primary editorial objective this quarter?
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {[
              { id: "recover_traffic", label: "Recover Decaying Pages", desc: "Target aging URLs losing visibility" },
              { id: "boost_ctr", label: "Boost Click Rates", desc: "Optimize high-ranking search snippets" },
              { id: "executive_audit", label: "Executive Portfolio Audit", desc: "Export board-level reports" },
            ].map((goal) => (
              <button
                key={goal.id}
                type="button"
                onClick={() => setSelectedGoal(goal.id)}
                className={`p-3 rounded-xl text-left border transition-all ${
                  selectedGoal === goal.id
                    ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-500"
                    : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                <span className="text-xs font-bold text-slate-900 dark:text-white block">
                  {goal.label}
                </span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 block mt-0.5">
                  {goal.desc}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleComplete}
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all"
        >
          <span>Explore Dashboard</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
