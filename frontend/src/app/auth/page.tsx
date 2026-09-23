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
  RefreshCw,
  KeyRound,
  AlertCircle,
  Info,
} from "lucide-react";
import { api, setToken } from "@/lib/api";
import { Logo } from "@/components/Logo";

export default function AuthPage() {
  const router = useRouter();

  // Auth method: "otp" (email passwordless OTP - primary) or "password"
  const [authMethod, setAuthMethod] = useState<"otp" | "password">("otp");
  const [isRegister, setIsRegister] = useState(false);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Verification state
  const [isVerifying, setIsVerifying] = useState(false);
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [maskedEmail, setMaskedEmail] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  // 6 interactive input refs for auto-advance, backspace, and paste
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Focus first input box whenever verification screen opens
  useEffect(() => {
    if (isVerifying) {
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
    }
  }, [isVerifying]);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Password strength checks
  const passLengthOk = password.length >= 8;
  const passLetterOk = /[a-zA-Z]/.test(password);
  const passNumberOk = /[0-9]/.test(password);
  const passMatch = password === confirmPassword && confirmPassword.length > 0;
  const isPasswordStrong = passLengthOk && passLetterOk && passNumberOk;

  // Handle Send OTP (Passwordless Email Flow)
  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    setError("");
    setSuccessMessage("");
    setLoading(true);

    try {
      const res = await api.sendOtp({
        email: email.trim(),
        full_name: fullName.trim() || undefined,
      });

      if (res.is_verified && !res.verification_token && res.access_token) {
        setToken(res.access_token);
        router.push("/dashboard");
        return;
      }

      setMaskedEmail(res.masked_email || email);
      setDigits(["", "", "", "", "", ""]);
      setIsVerifying(true);
      setResendCooldown(30);
      setSuccessMessage("Verification code sent to your email.");
    } catch (err: any) {
      setError(err.message || "Unable to send verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

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
  const handleDigitKeyDown = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
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

  // Handle paste support
  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
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

  // Handle Verify OTP
  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = digits.join("").trim();
    if (cleanCode.length !== 6) {
      setError("Please enter the complete 6-digit verification code.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await api.verifyOtp({ email: email.trim(), otp: cleanCode });
      setToken(res.access_token);
      setSuccessMessage("Email verified successfully! Redirecting to dashboard...");
      setTimeout(() => {
        router.push("/dashboard");
      }, 600);
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("expired")) {
        setError("Verification code expired. Please request a new code.");
      } else if (msg.toLowerCase().includes("too many") || msg.toLowerCase().includes("attempts")) {
        setError(msg || "Too many attempts. Please request a new code.");
      } else if (msg.toLowerCase().includes("incorrect") || msg.toLowerCase().includes("invalid")) {
        setError(msg || "Incorrect verification code.");
      } else {
        setError(msg || "Verification failed. Please check your code.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle Resend OTP
  const handleResendCode = async () => {
    if (resendCooldown > 0) return;
    setError("");
    setDigits(["", "", "", "", "", ""]);
    setLoading(true);
    try {
      const res = await api.sendOtp({
        email: email.trim(),
        full_name: fullName.trim() || undefined,
      });
      setResendCooldown(30);
      setSuccessMessage("Verification code sent to your email.");
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 50);
    } catch (err: any) {
      setError(err.message || "Could not send the verification code.");
    } finally {
      setLoading(false);
    }
  };

  // Handle switching emails (cancels previous active token)
  const handleUseDifferentEmail = async () => {
    try {
      if (email.trim()) {
        await api.cancelVerification(email.trim());
      }
    } catch {
      // Ignore
    }
    setIsVerifying(false);
    setDigits(["", "", "", "", "", ""]);
    setError("");
    setSuccessMessage("");
  };

  // Handle Password Auth (Login / Register)
  const handlePasswordAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");
    setLoading(true);

    try {
      if (!isRegister) {
        const res = await api.login({ email: email.trim(), password });
        setToken(res.access_token);
        router.push("/dashboard");
      } else {
        if (!isPasswordStrong) {
          throw new Error("Password must be at least 8 characters and include both letters and numbers.");
        }
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match.");
        }

        const res = await api.register({
          email: email.trim(),
          password,
          confirm_password: confirmPassword,
          full_name: fullName.trim() || undefined,
        });

        if (res.is_verified) {
          setToken(res.access_token);
          router.push("/dashboard");
        } else {
          setMaskedEmail(res.masked_email || email);
          setIsVerifying(true);
          setDigits(["", "", "", "", "", ""]);
          setResendCooldown(30);
          setSuccessMessage("Verification code sent to your email.");
        }
      }
    } catch (err: any) {
      if (err.message && err.message.toLowerCase().includes("not verified")) {
        try {
          const otpRes = await api.sendOtp({ email: email.trim() });
          setMaskedEmail(otpRes.masked_email || email);
        } catch (_) {}
        setMaskedEmail(email);
        setIsVerifying(true);
        setDigits(["", "", "", "", "", ""]);
        setResendCooldown(30);
        setError("Your account is not verified yet. Please enter the verification code.");
      } else {
        setError(err.message || "Authentication failed. Please check your credentials.");
      }
    } finally {
      setLoading(false);
    }
  };

  const fillDemoCredentials = async () => {
    setError("");
    setSuccessMessage("");
    setEmail("demo@contentintelligence.ai");
    setPassword("DemoPass123!");
    setAuthMethod("password");
    setIsRegister(false);
    setIsVerifying(false);

    setLoading(true);
    try {
      const res = await api.login({
        email: "demo@contentintelligence.ai",
        password: "DemoPass123!",
      });
      setToken(res.access_token);
      setSuccessMessage("Demo credentials verified! Entering dashboard...");
      setTimeout(() => {
        router.push("/dashboard");
      }, 500);
    } catch (err: any) {
      setError(err.message || "Failed to auto-login to demo account.");
      setLoading(false);
    }
  };

  const isCodeComplete = digits.join("").length === 6;

  return (
    <div className="max-w-md mx-auto py-12 px-4">
      <div className="glass-card rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-3">
            <Logo size={36} />
          </div>
          <h2 className="text-2xl font-display font-bold text-slate-900 dark:text-white">
            {isVerifying
              ? "Verify Your Code"
              : authMethod === "otp"
              ? "Sign In with Email OTP"
              : isRegister
              ? "Create ContentSignal Account"
              : "Sign in to ContentSignal"}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {isVerifying
              ? `Verification code sent to ${maskedEmail || email || "your email"}`
              : authMethod === "otp"
              ? "Enter your email to receive a secure 6-digit one-time code"
              : isRegister
              ? "Start making explainable content refresh decisions"
              : "Access the ML-powered editorial review queue"}
          </p>
        </div>

        {/* Demo Fast Fill Button (only on normal login/signup) */}
        {!isVerifying && (
          <button
            type="button"
            onClick={fillDemoCredentials}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 transition-colors disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            <span>Auto-fill Demo Credentials (1-Click)</span>
          </button>
        )}

        {/* Method Toggle (Email OTP vs Password) when not verifying */}
        {!isVerifying && (
          <div className="flex rounded-xl bg-slate-100 dark:bg-slate-900/80 p-1 border border-slate-200 dark:border-slate-800 text-xs font-medium">
            <button
              type="button"
              onClick={() => {
                setAuthMethod("otp");
                setError("");
                setSuccessMessage("");
              }}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                authMethod === "otp"
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold"
                  : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Email OTP
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMethod("password");
                setError("");
                setSuccessMessage("");
              }}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                authMethod === "password"
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold"
                  : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              Password
            </button>
          </div>
        )}

        {/* Success Alert */}
        {successMessage && (
          <div className="p-3 rounded-xl text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-500" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-3 rounded-xl text-xs font-medium bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-900 flex items-start justify-between gap-2">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
              <span>{error}</span>
            </div>
            {error.toLowerCase().includes("expired") && (
              <button
                type="button"
                onClick={handleResendCode}
                className="shrink-0 text-xs font-bold text-rose-700 dark:text-rose-300 hover:underline"
              >
                Send New Code
              </button>
            )}
          </div>
        )}

        {/* Verification Screen */}
        {isVerifying ? (
          <form onSubmit={handleVerifySubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-3 text-center">
                6-digit code
              </label>

              {/* Single Interactive 6-Digit Segmented Box Input */}
              <div className="flex justify-center items-center gap-2 mb-2" onPaste={handlePaste}>
                {[0, 1, 2, 3, 4, 5].map((idx) => {
                  const digit = digits[idx];
                  return (
                    <input
                      key={idx}
                      ref={(el) => {
                        inputRefs.current[idx] = el;
                      }}
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={1}
                      disabled={loading}
                      value={digit}
                      onChange={(e) => handleDigitChange(idx, e.target.value)}
                      onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                      className={`w-11 h-12 rounded-xl border text-center font-mono text-xl font-bold transition-all focus:outline-none ${
                        digit
                          ? "border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-sm"
                          : "border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30"
                      } ${error ? "border-rose-400 dark:border-rose-700 bg-rose-50/20" : ""}`}
                    />
                  );
                })}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !isCodeComplete}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying...</span>
                </>
              ) : (
                <>
                  <span>Verify</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="flex items-center justify-between text-xs pt-1">
              <button
                type="button"
                onClick={handleResendCode}
                disabled={resendCooldown > 0 || loading}
                className="text-emerald-600 dark:text-emerald-400 font-medium hover:underline disabled:opacity-50 disabled:no-underline flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${resendCooldown > 0 ? "animate-spin" : ""}`} />
                {resendCooldown > 0 ? `Resend Code in ${resendCooldown}s` : "Resend Code"}
              </button>

              <button
                type="button"
                onClick={handleUseDifferentEmail}
                disabled={loading}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                Use different email
              </button>
            </div>
          </form>
        ) : authMethod === "otp" ? (
          /* Primary Email OTP Form */
          <form onSubmit={handleSendOtp} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Your Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  required
                  autoFocus
                  placeholder="editor@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Full Name <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="e.g. Alex Morgan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Continue / Send Verification Code
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
              <span>
                No password required. We will generate and send a secure 6-digit confirmation code to your email.
              </span>
            </div>
          </form>
        ) : (
          /* Password Form (Login / Register) */
          <form onSubmit={handlePasswordAuthSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    required
                    placeholder="Alex Morgan"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Work Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  required
                  placeholder="editor@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Password
                </label>
                {!isRegister && (
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMethod("otp");
                      setError("");
                      setSuccessMessage("");
                    }}
                    className="text-[11px] text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    Forgot password? Sign in with OTP
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  type="password"
                  required
                  placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              {/* Password strength checklist on registration */}
              {isRegister && (
                <div className="mt-2 space-y-1 text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2
                      className={`w-3.5 h-3.5 ${
                        passLengthOk ? "text-emerald-500" : "text-slate-400"
                      }`}
                    />
                    <span
                      className={
                        passLengthOk
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-slate-500"
                      }
                    >
                      At least 8 characters
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2
                      className={`w-3.5 h-3.5 ${
                        passLetterOk ? "text-emerald-500" : "text-slate-400"
                      }`}
                    />
                    <span
                      className={
                        passLetterOk
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-slate-500"
                      }
                    >
                      At least one letter
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2
                      className={`w-3.5 h-3.5 ${
                        passNumberOk ? "text-emerald-500" : "text-slate-400"
                      }`}
                    />
                    <span
                      className={
                        passNumberOk
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-slate-500"
                      }
                    >
                      At least one number
                    </span>
                  </div>
                </div>
              )}
            </div>

            {isRegister && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                  <input
                    type="password"
                    required
                    placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                {confirmPassword && !passMatch && (
                  <p className="text-[11px] text-rose-500 mt-1">Passwords do not match</p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || (isRegister && (!isPasswordStrong || !passMatch))}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-glow-sm transition-all disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>{isRegister ? "Create Account" : "Sign In with Password"}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* Footer switch between Login & Register (only when in password mode) */}
        {!isVerifying && authMethod === "password" && (
          <div className="text-center pt-2 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError("");
                setSuccessMessage("");
              }}
              className="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
            >
              {isRegister ? (
                <span>
                  Already have an account?{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400 font-semibold">Sign In</strong>
                </span>
              ) : (
                <span>
                  Don&apos;t have an account?{" "}
                  <strong className="text-emerald-600 dark:text-emerald-400 font-semibold">Create one</strong>
                </span>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
