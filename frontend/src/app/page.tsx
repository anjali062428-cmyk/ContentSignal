"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Search,
  Database,
  Brain,
  Sliders,
  CheckCircle2,
  Users,
  Activity,
  Layers,
  ChevronRight,
  RefreshCw,
  TrendingDown,
  Zap,
} from "lucide-react";

export default function LandingPage() {
  const [activeNode, setActiveNode] = useState<string>("intelligence_engine");
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (typeof window === "undefined") return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const x = (e.clientX / window.innerWidth - 0.5) * 2;
      const y = (e.clientY / window.innerHeight - 0.5) * 2;
      setMousePos({ x, y });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const networkNodes = [
    { id: "search_data", label: "SEARCH DATA", icon: Search, desc: "90d visibility, clicks, click rate, and keyword intent vectors." },
    { id: "content_engine", label: "CONTENT ENGINE", icon: Database, desc: "Metadata, article age, update timestamps, and token length." },
    { id: "analytics", label: "ANALYTICS", icon: Activity, desc: "GA4 sessions, engagement rates, scroll depth, and AI referrals." },
    { id: "intelligence_engine", label: "INTELLIGENCE ENGINE", icon: Brain, desc: "Central ML inference engine synthesizing evidence vectors." },
    { id: "ml_models", label: "ML MODELS", icon: Sliders, desc: "Gradient boosting & tree ensembles trained with client holdout." },
    { id: "scoring", label: "SCORING", icon: Layers, desc: "Deterministic 0–100 opportunity score & priority classification." },
    { id: "recommendations", label: "RECOMMENDATIONS", icon: CheckCircle2, desc: "Evidence-based action directives (REFRESH, OPTIMIZE, PROTECT)." },
    { id: "content_teams", label: "CONTENT TEAMS", icon: Users, desc: "Editorial review queues prioritized by business opportunity." },
  ];

  const realMetrics = [
    { label: "Pages", value: "30,000", tag: "FLYRANK DATASET" },
    { label: "High Priority", value: "9,589", tag: "OPPORTUNITY" },
    { label: "Declining", value: "18,023", tag: "MEASURED SIGNAL" },
    { label: "Click Opportunities", value: "11,382", tag: "SEARCH SIGNAL" },
  ];

  return (
    <div className="space-y-20 py-4 sm:py-6">
      {/* Two-Column Hero Section */}
      <section className="relative pt-4 pb-12 overflow-visible">
        {/* Soft Ambient Radial Background Atmosphere */}
        <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[480px] h-[480px] bg-gradient-to-tr from-teal-500/15 via-cyan-500/10 to-transparent blur-[110px] -z-10 pointer-events-none rounded-full" />
        <div className="absolute top-1/4 left-1/3 w-[320px] h-[320px] bg-emerald-500/10 blur-[90px] -z-10 pointer-events-none rounded-full" />

        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-8 items-center">
            {/* LEFT COLUMN: Product Message & CTAs (50%) */}
            <div className="lg:col-span-6 text-left space-y-6">
              {/* Badge */}
              <div className="animate-hero-fade-up inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-50/80 dark:bg-teal-950/40 text-emerald-700 dark:text-teal-300 border border-emerald-200/80 dark:border-teal-800/80 shadow-sm backdrop-blur-sm">
                <Sparkles className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                <span>CONTENT INTELLIGENCE &bull; DECISION SUPPORT</span>
              </div>

              {/* Headline */}
              <h1 className="animate-hero-fade-up animation-delay-150 text-4xl sm:text-5xl lg:text-6xl font-display font-extrabold text-slate-900 dark:text-white tracking-tight leading-[1.15]">
                Turn Content Data Into<br />
                <span className="bg-gradient-to-r from-teal-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                  Smarter Decisions
                </span>
              </h1>

              {/* Description */}
              <p className="animate-hero-fade-up animation-delay-300 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-xl font-normal leading-relaxed">
                Discover what&apos;s working, uncover new opportunities, and get clear, actionable recommendations &mdash; so your content team can focus on what moves the needle.
              </p>

              {/* CTA Buttons */}
              <div className="animate-hero-fade-up animation-delay-450 flex flex-wrap items-center gap-4 pt-1">
                <Link
                  href="/auth"
                  className="group inline-flex items-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white shadow-glow hover:shadow-glow-cyan transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
                >
                  Get Started
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-200" />
                </Link>
                <Link
                  href="/dashboard"
                  className="group inline-flex items-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold glass-card text-slate-800 dark:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-all duration-200 hover:-translate-y-0.5 border border-slate-200/90 dark:border-slate-800/90 hover:border-teal-500/40"
                >
                  Explore Platform
                  <ChevronRight className="w-4 h-4 text-teal-600 dark:text-teal-400 group-hover:translate-x-0.5 transition-transform duration-200" />
                </Link>
              </div>

              {/* Four Compact Capability Items (Functional Navigation Links) */}
              <div className="animate-hero-fade-up animation-delay-450 pt-5 border-t border-slate-200/80 dark:border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-xl">
                <Link
                  href="/dashboard/analytics"
                  title="View Performance Analytics"
                  className="group flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-50/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 hover:border-teal-500/40 hover:bg-teal-50/30 dark:hover:bg-teal-950/20 transition-all cursor-pointer"
                >
                  <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-teal-500/20 transition-colors">
                    <Search className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-xs leading-snug">
                    <div className="font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">Analyze</div>
                    <div className="text-slate-500 dark:text-slate-400 text-[11px]">Performance</div>
                  </div>
                </Link>

                <Link
                  href="/dashboard/opportunities"
                  title="Find Content Opportunities"
                  className="group flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-50/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 hover:border-cyan-500/40 hover:bg-cyan-50/30 dark:hover:bg-cyan-950/20 transition-all cursor-pointer"
                >
                  <div className="w-7 h-7 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-cyan-500/20 transition-colors">
                    <Activity className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-xs leading-snug">
                    <div className="font-bold text-slate-900 dark:text-white group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors">Find</div>
                    <div className="text-slate-500 dark:text-slate-400 text-[11px]">Opportunities</div>
                  </div>
                </Link>

                <Link
                  href="/dashboard/evidence"
                  title="Prioritize with Grounded Evidence"
                  className="group flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-50/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 hover:border-emerald-500/40 hover:bg-emerald-50/30 dark:hover:bg-emerald-950/20 transition-all cursor-pointer"
                >
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-emerald-500/20 transition-colors">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-xs leading-snug">
                    <div className="font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">Prioritize</div>
                    <div className="text-slate-500 dark:text-slate-400 text-[11px]">With Evidence</div>
                  </div>
                </Link>

                <Link
                  href="/dashboard/opportunities"
                  title="Take Action with Confidence"
                  className="group flex items-start gap-2.5 p-2.5 rounded-xl bg-slate-50/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 hover:border-teal-500/40 hover:bg-teal-50/30 dark:hover:bg-teal-950/20 transition-all cursor-pointer"
                >
                  <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-teal-500/20 transition-colors">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </div>
                  <div className="text-xs leading-snug">
                    <div className="font-bold text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">Take Action</div>
                    <div className="text-slate-500 dark:text-slate-400 text-[11px]">With Confidence</div>
                  </div>
                </Link>
              </div>
            </div>

            {/* RIGHT COLUMN: Compact Abstract Content Intelligence Signal Visualization (50%) */}
            <div className="lg:col-span-6 relative w-full flex items-center justify-center py-6 lg:py-0">
              {/* Subtle Ambient Glow */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none -z-10">
                <div className="w-[320px] h-[320px] bg-gradient-to-tr from-teal-500/15 via-cyan-500/10 to-transparent rounded-full blur-[90px]" />
              </div>

              {/* Light 3D Perspective Container (subtle rotateX/rotateY, pure floating SaaS interface) */}
              <div
                className="perspective-container preserve-3d w-full max-w-[390px] relative"
                style={{
                  transform: `perspective(1000px) rotateX(${2.5 - mousePos.y * 1.5}deg) rotateY(${-3.5 + mousePos.x * 1.5}deg)`,
                  transition: "transform 0.25s cubic-bezier(0.2, 0, 0, 1)",
                }}
              >
                {/* Floating Card 1: [Opportunity] (Positioned directly above the central stack) */}
                <div className="absolute -top-6 right-3 sm:right-6 animate-hero-float-slow z-20 pointer-events-none select-none">
                  <div className="glass-card px-3 py-1.5 rounded-xl border border-teal-500/40 shadow-xl backdrop-blur-md text-left">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[9px] font-mono uppercase font-bold text-teal-600 dark:text-teal-400 tracking-wider">
                        OPPORTUNITY
                      </span>
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
                    </div>
                    <div className="text-xs font-display font-bold text-slate-900 dark:text-white">
                      High Priority
                    </div>
                  </div>
                </div>

                {/* Floating Card 2: SEARCH SIGNAL (Positioned bottom-left) */}
                <div className="absolute -bottom-5 -left-2 sm:-left-4 animate-hero-float-reverse z-20 pointer-events-none select-none">
                  <div className="glass-card px-3 py-1.5 rounded-xl border border-amber-500/40 shadow-xl backdrop-blur-md text-left">
                    <div className="text-[9px] font-mono uppercase font-bold text-amber-600 dark:text-amber-400 tracking-wider mb-0.5">
                      SEARCH SIGNAL
                    </div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-white">
                      <TrendingDown className="w-3.5 h-3.5 text-amber-500" />
                      <span>Visibility</span>
                    </div>
                  </div>
                </div>

                {/* Floating Card 3: ACTION OPTIMIZE (Positioned mid-right) */}
                <div className="absolute top-1/2 -right-3 sm:-right-5 -translate-y-1/2 animate-hero-float-slow z-20 pointer-events-none select-none hidden sm:block">
                  <div className="glass-card px-3 py-1.5 rounded-xl border border-purple-500/35 shadow-xl backdrop-blur-md text-left">
                    <div className="text-[8px] font-mono uppercase font-bold text-slate-400 tracking-wider">
                      ACTION
                    </div>
                    <div className="text-[11px] font-bold text-purple-600 dark:text-purple-400 font-mono flex items-center gap-1 mt-0.5">
                      <Zap className="w-3 h-3 text-purple-500" />
                      <span>OPTIMIZE</span>
                    </div>
                  </div>
                </div>

                {/* Subtle SVG Signal Flow Line */}
                <div className="absolute inset-0 pointer-events-none -z-5 overflow-visible">
                  <svg className="w-full h-full opacity-40 dark:opacity-60" viewBox="0 0 420 320" fill="none">
                    <path
                      d="M 50,270 C 130,230 170,160 230,130 C 290,100 320,40 340,15"
                      stroke="url(#signalFlowGradCompact)"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                      className="animate-signal-flow"
                    />
                    <circle cx="230" cy="130" r="3" fill="#2dd4bf" className="animate-ping opacity-75" />
                    <circle cx="230" cy="130" r="2.5" fill="#2dd4bf" />
                    <defs>
                      <linearGradient id="signalFlowGradCompact" x1="0" y1="1" x2="1" y2="0">
                        <stop offset="0%" stopColor="#0d9488" stopOpacity="0.2" />
                        <stop offset="60%" stopColor="#2dd4bf" stopOpacity="0.9" />
                        <stop offset="100%" stopColor="#34d399" stopOpacity="0.4" />
                      </linearGradient>
                    </defs>
                  </svg>
                </div>

                {/* Central Stack: Content Intelligence Matrix (4 Clean Layered Panels) */}
                <div className="glass-card rounded-2xl p-3 sm:p-4 border border-slate-200/80 dark:border-slate-800/80 shadow-2xl backdrop-blur-xl space-y-2">
                  {/* Matrix Header */}
                  <div className="flex items-center justify-between px-1 pb-1.5 border-b border-slate-200/60 dark:border-slate-800/60">
                    <span className="text-[10px] font-mono font-bold tracking-wider text-slate-600 dark:text-slate-300 uppercase">
                      CONTENT INTELLIGENCE MATRIX
                    </span>
                    <span className="flex items-center gap-1 text-[9px] font-mono font-semibold text-teal-600 dark:text-teal-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
                      ACTIVE
                    </span>
                  </div>

                  {/* Panel 1: Content Performance */}
                  <div className="p-2.5 rounded-xl bg-slate-50/90 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-800/70 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-left">
                      <div className="w-7 h-7 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
                        <Database className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white">
                          Content Performance
                        </div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                          Catalog ingestion &bull; Multi-source metrics
                        </div>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold">
                      INGESTED
                    </span>
                  </div>

                  {/* Panel 2: Search Visibility */}
                  <div className="p-2.5 rounded-xl bg-slate-50/90 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-800/70 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-left">
                      <div className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0">
                        <TrendingDown className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white">
                          Search Visibility
                        </div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                          Rank trajectory &bull; Risk signals
                        </div>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold">
                      SIGNALS
                    </span>
                  </div>

                  {/* Panel 3: Engagement Signals */}
                  <div className="p-2.5 rounded-xl bg-slate-50/90 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-800/70 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 text-left">
                      <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                        <Activity className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white">
                          Engagement Signals
                        </div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                          CTR variance &bull; Audience behavior
                        </div>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold">
                      MEASURED
                    </span>
                  </div>

                  {/* Panel 4: Opportunity Detected */}
                  <div className="p-2.5 rounded-xl bg-teal-50/70 dark:bg-teal-950/30 border border-teal-500/30 flex items-center justify-between shadow-glow-sm">
                    <div className="flex items-center gap-2.5 text-left">
                      <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0">
                        <Sparkles className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-teal-950 dark:text-teal-200">
                          Opportunity Detected
                        </div>
                        <div className="text-[10px] text-teal-700/80 dark:text-teal-400/80 font-mono">
                          Action prioritized &bull; 0–100 score
                        </div>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-700 dark:text-teal-300 font-bold">
                      SCORED
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Central Interactive Network Diagram */}
      <section id="architecture" className="glass-card rounded-3xl p-8 sm:p-12 border border-slate-200/80 dark:border-slate-800/80 relative overflow-hidden scroll-mt-24">
        <div className="text-center max-w-xl mx-auto mb-10 space-y-2">
          <div className="text-xs uppercase font-bold tracking-widest text-teal-600 dark:text-teal-400">
            System Architecture
          </div>
          <h2 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white">
            DATA &rarr; INTELLIGENCE &rarr; DECISION
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Click any subsystem node to inspect its operational role in the ContentSignal pipeline.
          </p>
        </div>

        {/* Network Nodes Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-4xl mx-auto">
          {networkNodes.map((node) => {
            const Icon = node.icon;
            const isSelected = activeNode === node.id;
            const isCenter = node.id === "intelligence_engine";

            return (
              <button
                key={node.id}
                onClick={() => setActiveNode(node.id)}
                className={`flex flex-col items-center text-center p-4 rounded-2xl transition-all duration-200 border text-left ${
                  isSelected
                    ? "bg-teal-50/80 dark:bg-teal-950/40 border-teal-500 shadow-glow-sm scale-[1.03]"
                    : "bg-white/60 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 hover:border-teal-300 dark:hover:border-teal-700"
                } ${isCenter ? "ring-2 ring-teal-500/50" : ""}`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 transition-colors ${
                    isSelected
                      ? "bg-teal-600 text-white shadow-sm"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                  } ${isCenter ? "network-pulse bg-gradient-to-br from-teal-500 to-cyan-500 text-white" : ""}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-1">
                  {node.label}
                </span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                  {node.desc}
                </span>
              </button>
            );
          })}
        </div>

        {/* Active Node Detail Card */}
        {activeNode && (
          <div className="mt-8 max-w-lg mx-auto p-4 rounded-xl bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-center">
            <span className="text-[10px] font-mono uppercase tracking-wider text-teal-600 dark:text-teal-400 font-bold">
              Subsystem Active
            </span>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200 mt-1">
              {networkNodes.find((n) => n.id === activeNode)?.desc}
            </p>
          </div>
        )}
      </section>

      {/* Real Dataset-Backed Metrics */}
      <section className="space-y-6">
        <div className="text-center space-y-1">
          <div className="inline-block px-2.5 py-0.5 rounded text-[10px] font-bold bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-400 border border-teal-200 dark:border-teal-800">
            MEASURED PORTFOLIO SIGNALS
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">
            Starter Dataset Signals
          </h3>
          <p className="text-xs text-slate-500">
            Strictly measured from the 30,000-page FlyRank starter repository &mdash; zero fabricated numbers.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {realMetrics.map((item) => (
            <div
              key={item.label}
              className="glass-card p-5 rounded-2xl border border-slate-200 dark:border-slate-800 relative group hover:border-teal-500/50 transition-all"
            >
              <span className="absolute top-3 right-3 text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                {item.tag}
              </span>
              <div className="text-3xl font-display font-extrabold text-slate-900 dark:text-white mt-3 mb-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                {item.value}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Core Question Callout */}
      <section className="glass-card rounded-3xl p-8 sm:p-12 border border-emerald-200/80 dark:border-emerald-900/40 bg-gradient-to-b from-emerald-50/30 to-transparent text-center space-y-4">
        <span className="text-xs font-bold uppercase tracking-widest text-teal-600 dark:text-teal-400">
          Core Editorial Question
        </span>
        <blockquote className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white max-w-2xl mx-auto">
          &ldquo;Which pages should a content team REVIEW FIRST, and WHY?&rdquo;
        </blockquote>
        <p className="text-sm text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
          Don&apos;t manually inspect thousands of pages. Know which ones deserve attention first &mdash; and understand the exact search signals driving the recommendation.
        </p>
        <div className="pt-2">
          <Link
            href="/dashboard/opportunities"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-slate-900 text-white dark:bg-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100 transition-all"
          >
            Inspect Ranked Queue
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
