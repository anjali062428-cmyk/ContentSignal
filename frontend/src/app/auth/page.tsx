"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Lock,
  Mail,
  User,
  ArrowRight,
  Loader2,
  CheckCircle2,
  KeyRound,
  AlertCircle,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import { api, setToken } from "@/lib/api";
import { Logo } from "@/components/Logo";

type AuthMode = "login" | "signup" | "forgot_password";
type SignupStep = "form" | "otp";
type ResetStep = "email" | "verify";

export default function AuthPage() {
  const router = useRouter();

  // Mode: "login" | "signup" | "forgot_password"
  const [mode, setMode] = useState<AuthMode>("login");

  // Sign up state
  const [signupStep, setSignupStep] = useState<SignupStep>("form");
  const [fullName, setFullName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Login state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Forgot password state
  const [resetStep, setResetStep] = useState<ResetStep>("email");
  const [resetEmail, setResetEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");

  // 6-digit OTP state
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [maskedEmail, setMaskedEmail] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  // Status feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Input refs for 6-digit OTP
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Focus first input box whenever OTP screen opens
  useEffect(() => {
    if (
      (mode === "signup" && signupStep === "otp") ||
      (mode === "forgot_password" && resetStep === "verify")
    ) {
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
    }
  }, [mode, signupStep, resetStep]);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const clearFeedback = () => {
    setError("");
    setSuccessMessage("");
  };

  // Password strength checks for sign up
  const signupPassLengthOk = signupPassword.length >= 8;
  const signupPassLetterOk = /[a-zA-Z]/.test(signupPassword);
  const signupPassNumberOk = /[0-9]/.test(signupPassword);
  const signupPassMatch =
    signupPassword === confirmPassword && confirmPassword.length > 0;
  const isSignupPasswordStrong =
    signupPassLengthOk && signupPassLetterOk && signupPassNumberOk;

  // Password strength checks for reset
  const resetPassLengthOk = newPassword.length >= 8;
  const resetPassLetterOk = /[a-zA-Z]/.test(newPassword);
  const resetPassNumberOk = /[0-9]/.test(newPassword);
  const resetPassMatch =
    newPassword === confirmNewPassword && confirmNewPassword.length > 0;
  const isResetPasswordStrong =
    resetPassLengthOk && resetPassLetterOk && resetPassNumberOk;

  // Handle digit change with auto-advance
  const handleDigitChange = (idx: number, val: string) => {
    const numericChar = val.replace(/\D/g, "").slice(-1);
    const nextDigits = [...digits];
    nextDigits[idx] = numericChar;
    setDigits(nextDigits);
    setError("");

    if (numericChar && idx < 5) {
      inputRefs.current[idx + 1]?.focus();
    }
  };

  // Handle backspace and arrow navigation
  const handleDigitKeyDown = (
    idx: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace") {
      if (!digits[idx] && idx > 0) {
        const nextDigits = [...digits];
        nextDigits[idx - 1] = "";
        setDigits(nextDigits);
        inputRefs.current[idx - 1]?.focus();
      } else {
        const nextDigits = [...digits];
        nextDigits[idx] = "";
        setDigits(nextDigits);
      }
    } else if (e.key === "ArrowLeft" && idx > 0) {
      inputRefs.current[idx - 1]?.focus();
    } else if (e.key === "ArrowRight" && idx < 5) {
      inputRefs.current[idx + 1]?.focus();
    }
  };

  // Handle paste support for OTP
  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasteData = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!pasteData) return;
    const nextDigits = [...digits];
    for (let i = 0; i < 6; i++) {
      nextDigits[i] = pasteData[i] || "";
    }
    setDigits(nextDigits);
    setError("");
    const nextFocus = Math.min(pasteData.length, 5);
    inputRefs.current[nextFocus]?.focus();
  };

  // 1. Normal Login (No OTP required)
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    clearFeedback();
    setLoading(true);

    try {
      const res = await api.login({
        email: loginEmail.trim(),
        password: loginPassword,
      });

      if (res.access_token) {
        setToken(res.access_token);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(
        err.message ||
          "Incorrect email or password. Please verify your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  // 2. Sign Up: Step 1 (Validate & Dispatch OTP)
  const handleSignupInitiate = async (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();

    if (!signupEmail.trim() || !signupEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    if (!isSignupPasswordStrong) {
      setError(
        "Password must be at least 8 characters and include at least one letter and one number."
      );
      return;
    }
    if (!signupPassMatch) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.signupInitiate({
        full_name: fullName.trim() || "User",
        email: signupEmail.trim(),
        password: signupPassword,
        confirm_password: confirmPassword,
      });

      if (res.is_verified && res.access_token) {
        setToken(res.access_token);
        router.push("/dashboard");
        return;
      }

      setMaskedEmail(res.masked_email || signupEmail.trim());
      setDigits(["", "", "", "", "", ""]);
      setSignupStep("otp");
      setResendCooldown(30);
      setSuccessMessage(
        res.message || "A 6-digit verification code has been sent to your email."
      );
    } catch (err: any) {
      setError(err.message || "Unable to send verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // 2. Sign Up: Step 2 (Verify OTP & Complete Account Creation)
  const handleSignupVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = digits.join("").trim();
    if (cleanCode.length !== 6) {
      setError("Please enter the complete 6-digit verification code.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.signupVerify({
        email: signupEmail.trim(),
        otp: cleanCode,
      });

      if (res.access_token) {
        setToken(res.access_token);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(
        err.message || "Invalid or expired verification code. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // 3. Forgot Password: Step 1 (Send Reset Code)
  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetEmail.trim() || !resetEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.forgotPassword({ email: resetEmail.trim() });
      setMaskedEmail(res.masked_email || resetEmail.trim());
      setDigits(["", "", "", "", "", ""]);
      setResetStep("verify");
      setResendCooldown(30);
      setSuccessMessage(
        res.message || "If an account exists, a reset code was sent."
      );
    } catch (err: any) {
      setError(err.message || "Unable to send reset code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // 3. Forgot Password: Step 2 (Verify Code & Update Password)
  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = digits.join("").trim();
    if (cleanCode.length !== 6) {
      setError("Please enter the complete 6-digit verification code.");
      return;
    }
    if (!isResetPasswordStrong) {
      setError(
        "New password must be at least 8 characters and include at least one letter and one number."
      );
      return;
    }
    if (!resetPassMatch) {
      setError("Passwords do not match.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.resetPassword({
        email: resetEmail.trim(),
        otp: cleanCode,
        new_password: newPassword,
        confirm_password: confirmNewPassword,
      });

      // Switch back to login with success message
      setLoginEmail(resetEmail.trim());
      setLoginPassword("");
      setMode("login");
      setResetStep("email");
      setNewPassword("");
      setConfirmNewPassword("");
      setDigits(["", "", "", "", "", ""]);
      setSuccessMessage(
        res.message || "Password updated successfully. Please log in."
      );
    } catch (err: any) {
      setError(err.message || "Password reset failed. Please check the code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden transition-colors">
      {/* Dynamic Background Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/10 dark:bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[450px] h-[450px] bg-blue-500/10 dark:bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Main Container Card */}
      <div className="w-full max-w-md bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <Logo />
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1">
            {mode === "login" && "Sign In to ContentSignal"}
            {mode === "signup" &&
              (signupStep === "form"
                ? "Create Your Account"
                : "Verify Your Email")}
            {mode === "forgot_password" &&
              (resetStep === "email"
                ? "Reset Your Password"
                : "Enter Code & New Password")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            {mode === "login" &&
              "Enter your email and password to access your dashboard"}
            {mode === "signup" &&
              (signupStep === "form"
                ? "Get real-time catalog intelligence and AI-driven growth signals"
                : `We sent a 6-digit code to ${maskedEmail || signupEmail}`)}
            {mode === "forgot_password" &&
              (resetStep === "email"
                ? "Enter your registered email to receive a password reset code"
                : `Enter the 6-digit code sent to ${maskedEmail || resetEmail}`)}
          </p>
        </div>

        {/* Global Feedback Messages */}
        {error && (
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-400 text-xs">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="flex-1 font-medium leading-relaxed">{error}</div>
          </div>
        )}

        {successMessage && (
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="flex-1 font-medium leading-relaxed">
              {successMessage}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* 1. LOGIN MODE                                                             */}
        {/* ========================================================================= */}
        {mode === "login" && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    clearFeedback();
                    setResetEmail(loginEmail);
                    setResetStep("email");
                    setMode("forgot_password");
                  }}
                  className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !loginEmail || !loginPassword}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="text-center pt-3 border-t border-slate-100 dark:border-slate-800">
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Don&apos;t have an account?{" "}
              </span>
              <button
                type="button"
                onClick={() => {
                  clearFeedback();
                  setSignupEmail(loginEmail);
                  setSignupStep("form");
                  setMode("signup");
                }}
                className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
              >
                Create Account
              </button>
            </div>
          </form>
        )}

        {/* ========================================================================= */}
        {/* 2. SIGN UP MODE                                                           */}
        {/* ========================================================================= */}
        {mode === "signup" && (
          <div>
            {signupStep === "form" ? (
              <form onSubmit={handleSignupInitiate} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      required
                      placeholder="Jane Doe"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="email"
                      required
                      placeholder="name@company.com"
                      value={signupEmail}
                      onChange={(e) => setSignupEmail(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Password (min 8 characters)
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      placeholder="••••••••"
                      value={signupPassword}
                      onChange={(e) => setSignupPassword(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  {signupPassword && (
                    <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            signupPassLengthOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            signupPassLengthOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          8+ characters
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            signupPassLetterOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            signupPassLetterOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          At least 1 letter
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            signupPassNumberOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            signupPassNumberOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          At least 1 number
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  {confirmPassword && !signupPassMatch && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      Passwords do not match
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={
                    loading ||
                    !isSignupPasswordStrong ||
                    !signupPassMatch ||
                    !signupEmail
                  }
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Continue & Verify Email</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="text-center pt-3 border-t border-slate-100 dark:border-slate-800">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Already have an account?{" "}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      clearFeedback();
                      setLoginEmail(signupEmail);
                      setMode("login");
                    }}
                    className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    Sign In
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleSignupVerify} className="space-y-6">
                <div className="space-y-3">
                  <label className="block text-xs font-semibold text-center text-slate-700 dark:text-slate-300">
                    Enter the 6-digit code
                  </label>
                  <div
                    className="flex justify-center gap-2 sm:gap-2.5"
                    onPaste={handlePaste}
                  >
                    {digits.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={(el) => {
                          inputRefs.current[idx] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleDigitChange(idx, e.target.value)}
                        onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                        className="w-10 h-12 sm:w-11 sm:h-12 text-center text-xl font-bold font-mono rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all shadow-sm"
                      />
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || digits.join("").trim().length !== 6}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Verify & Open Dashboard</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="flex items-center justify-between text-xs pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      clearFeedback();
                      setSignupStep("form");
                    }}
                    className="flex items-center gap-1 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Back</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleSignupInitiate}
                    disabled={resendCooldown > 0 || loading}
                    className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400 disabled:opacity-50 hover:underline"
                  >
                    <RefreshCw
                      className={`w-3.5 h-3.5 ${
                        loading ? "animate-spin" : ""
                      }`}
                    />
                    <span>
                      {resendCooldown > 0
                        ? `Resend in ${resendCooldown}s`
                        : "Resend Code"}
                    </span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* 3. FORGOT PASSWORD MODE                                                   */}
        {/* ========================================================================= */}
        {mode === "forgot_password" && (
          <div>
            {resetStep === "email" ? (
              <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="email"
                      required
                      placeholder="name@company.com"
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || !resetEmail}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Send Reset Code</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="text-center pt-3 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => {
                      clearFeedback();
                      setMode("login");
                    }}
                    className="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  >
                    ← Back to Sign In
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                <div className="space-y-3">
                  <label className="block text-xs font-semibold text-center text-slate-700 dark:text-slate-300">
                    Enter the 6-digit code
                  </label>
                  <div
                    className="flex justify-center gap-2 sm:gap-2.5"
                    onPaste={handlePaste}
                  >
                    {digits.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={(el) => {
                          inputRefs.current[idx] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleDigitChange(idx, e.target.value)}
                        onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                        className="w-10 h-12 sm:w-11 sm:h-12 text-center text-xl font-bold font-mono rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all shadow-sm"
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    New Password (min 8 characters)
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      placeholder="••••••••"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  {newPassword && (
                    <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            resetPassLengthOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            resetPassLengthOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          8+ characters
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            resetPassLetterOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            resetPassLetterOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          At least 1 letter
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2
                          className={`w-3.5 h-3.5 ${
                            resetPassNumberOk
                              ? "text-emerald-500"
                              : "text-slate-400"
                          }`}
                        />
                        <span
                          className={
                            resetPassNumberOk
                              ? "text-emerald-600 dark:text-emerald-400 font-medium"
                              : "text-slate-500"
                          }
                        >
                          At least 1 number
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      required
                      placeholder="••••••••"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  {confirmNewPassword && !resetPassMatch && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      Passwords do not match
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={
                    loading ||
                    digits.join("").trim().length !== 6 ||
                    !isResetPasswordStrong ||
                    !resetPassMatch
                  }
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Reset Password & Sign In</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <div className="flex items-center justify-between text-xs pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      clearFeedback();
                      setResetStep("email");
                    }}
                    className="flex items-center gap-1 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Back</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleForgotPasswordSubmit}
                    disabled={resendCooldown > 0 || loading}
                    className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400 disabled:opacity-50 hover:underline"
                  >
                    <RefreshCw
                      className={`w-3.5 h-3.5 ${
                        loading ? "animate-spin" : ""
                      }`}
                    />
                    <span>
                      {resendCooldown > 0
                        ? `Resend in ${resendCooldown}s`
                        : "Resend Code"}
                    </span>
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
