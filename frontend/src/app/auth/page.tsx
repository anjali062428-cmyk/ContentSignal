"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignIn, SignUp, useUser } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { Mail, Phone, ShieldCheck, Sparkles, CheckCircle2, Lock } from "lucide-react";
import { Logo } from "@/components/Logo";

type AuthMode = "signin" | "signup";
type IdentifierPreference = "email" | "phone";

export default function AuthPage() {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useUser();

  const [mode, setMode] = useState<AuthMode>("signin");
  const [identifierPref, setIdentifierPref] = useState<IdentifierPreference>("email");

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace("/dashboard");
    }
  }, [isLoaded, isSignedIn, router]);

  const clerkAppearance = {
    baseTheme: dark,
    variables: {
      colorPrimary: "#0d9488", // Teal 600
      colorBackground: "#0b1220", // ContentSignal dark navy
      colorInputBackground: "#070b14",
      colorInputText: "#f8fafc",
      colorText: "#f8fafc",
      colorTextSecondary: "#94a3b8",
      colorDanger: "#f43f5e",
      borderRadius: "0.75rem",
    },
    elements: {
      rootBox: "w-full",
      card: "w-full bg-[#0b1220] border border-slate-800 shadow-2xl rounded-2xl p-6 sm:p-8",
      headerTitle: "text-xl font-bold text-white tracking-tight",
      headerSubtitle: "text-xs text-slate-400 font-normal",
      socialButtonsBlockButton:
        "bg-slate-900/90 border border-slate-800 hover:bg-slate-850 hover:border-slate-700 text-slate-200 transition-all text-xs font-medium py-2.5",
      socialButtonsBlockButtonText: "text-slate-200 font-medium",
      dividerLine: "bg-slate-800",
      dividerText: "text-slate-500 text-[11px] uppercase tracking-wider",
      formButtonPrimary:
        "w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold text-sm py-2.5 rounded-xl transition-all shadow-md shadow-teal-950/50 hover:shadow-teal-900/50 active:scale-[0.99]",
      formFieldLabel: "text-xs font-medium text-slate-300 mb-1.5",
      formFieldInput:
        "bg-[#070b14] border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all",
      footer: "hidden", // We provide custom styled footer tabs
      identityPreviewText: "text-slate-200 text-xs",
      identityPreviewEditButton: "text-teal-400 hover:text-teal-300 text-xs font-medium",
      formResendCodeLink: "text-teal-400 hover:text-teal-300 text-xs font-medium",
      otpCodeFieldInput:
        "bg-[#070b14] border border-slate-800 text-teal-400 text-lg font-mono focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30",
    },
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 bg-[#070b14] text-slate-100 relative overflow-hidden">
      {/* Background Ambient Glows */}
      <div className="absolute top-1/4 -left-48 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl shadow-teal-950/20 backdrop-blur-md mb-1">
            <Logo className="w-10 h-10" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center justify-center gap-2">
              ContentSignal
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 font-medium max-w-xs mx-auto">
              Turn Search Data into Smarter Content Decisions
            </p>
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-950/40 border border-teal-800/40 text-[11px] font-medium text-teal-300">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-400 shrink-0" />
            <span>Enterprise Multi-User Authentication</span>
          </div>
        </div>

        {/* Card Container */}
        <div className="bg-[#0b1220]/90 backdrop-blur-xl border border-slate-800/90 rounded-2xl shadow-2xl p-6 sm:p-7 space-y-5">
          {/* Mode Switcher: Sign In vs Sign Up */}
          <div className="grid grid-cols-2 p-1 rounded-xl bg-slate-900/90 border border-slate-800">
            <button
              type="button"
              onClick={() => setMode("signin")}
              className={`py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all ${
                mode === "signin"
                  ? "bg-teal-600 text-white shadow-md shadow-teal-950/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all ${
                mode === "signup"
                  ? "bg-teal-600 text-white shadow-md shadow-teal-950/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Identifier Selector: [ Email ] [ Phone ] */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Preferred Identifier
              </span>
              <span className="text-[10px] text-teal-400/90">Single identifier supported</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setIdentifierPref("email")}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-medium border transition-all ${
                  identifierPref === "email"
                    ? "bg-slate-850 border-teal-500/60 text-teal-300 ring-1 ring-teal-500/20 shadow-xs"
                    : "bg-slate-900/60 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                <Mail className="w-3.5 h-3.5 shrink-0" />
                <span>Email Address</span>
              </button>
              <button
                type="button"
                onClick={() => setIdentifierPref("phone")}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-medium border transition-all ${
                  identifierPref === "phone"
                    ? "bg-slate-850 border-teal-500/60 text-teal-300 ring-1 ring-teal-500/20 shadow-xs"
                    : "bg-slate-900/60 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                <Phone className="w-3.5 h-3.5 shrink-0" />
                <span>Phone Number</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed px-0.5">
              {identifierPref === "email"
                ? "Sign in or register with your email. Phone number is not required."
                : "Sign in or register with your phone number and SMS OTP. Email is not required."}
            </p>
          </div>

          {/* Clerk Component Mounting Point */}
          <div className="w-full pt-1">
            {mode === "signin" ? (
              <SignIn
                routing="hash"
                forceRedirectUrl="/dashboard"
                appearance={clerkAppearance}
              />
            ) : (
              <SignUp
                routing="hash"
                forceRedirectUrl="/dashboard"
                appearance={clerkAppearance}
              />
            )}
          </div>
        </div>

        {/* Feature Badges Footer */}
        <div className="grid grid-cols-3 gap-2 text-center text-[11px] text-slate-500">
          <div className="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <Lock className="w-3.5 h-3.5 text-teal-400 shrink-0" />
            <span>Encrypted Session</span>
          </div>
          <div className="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 shrink-0" />
            <span>Tenant Isolation</span>
          </div>
          <div className="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
            <Sparkles className="w-3.5 h-3.5 text-teal-400 shrink-0" />
            <span>Zero Password Leaks</span>
          </div>
        </div>
      </div>
    </div>
  );
}
