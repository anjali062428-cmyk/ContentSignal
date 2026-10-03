"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Lock,
  Mail,
  User,
  Phone,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  CheckCircle2,
  KeyRound,
  AlertCircle,
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Clock,
  Edit3,
  X,
  Check,
} from "lucide-react";
import { api, setToken } from "@/lib/api";
import { Logo } from "@/components/Logo";

type AuthMode = "login" | "signup" | "forgot_password";
type SignupStep = "form" | "verify";
type LoginMethod = "password" | "otp";
type LoginOtpStep = "request" | "verify";
type ResetStep = "request" | "verify";

const COUNTRY_CODES = [
  { code: "+91", label: "India (+91)", flag: "🇮🇳" },
  { code: "+1", label: "US / Canada (+1)", flag: "🇺🇸" },
  { code: "+44", label: "UK (+44)", flag: "🇬🇧" },
  { code: "+61", label: "Australia (+61)", flag: "🇦🇺" },
  { code: "+971", label: "UAE (+971)", flag: "🇦🇪" },
  { code: "+65", label: "Singapore (+65)", flag: "🇸🇬" },
  { code: "+49", label: "Germany (+49)", flag: "🇩🇪" },
  { code: "+33", label: "France (+33)", flag: "🇫🇷" },
];

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function AuthPage() {
  const router = useRouter();

  // Mode: "login" | "signup" | "forgot_password"
  const [mode, setMode] = useState<AuthMode>("login");

  // ==========================================
  // SIGNUP STATE
  // ==========================================
  const [signupStep, setSignupStep] = useState<SignupStep>("form");
  const [fullName, setFullName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [countryCode, setCountryCode] = useState("+91");
  const [mobileNumber, setMobileNumber] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(true);

  // Show/Hide password toggles
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Verification state (Phase 10 & 11)
  const [maskedEmail, setMaskedEmail] = useState("");
  const [maskedMobile, setMaskedMobile] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [mobileVerified, setMobileVerified] = useState(false);
  const [smsConfigured, setSmsConfigured] = useState(true);
  const [smsMessage, setSmsMessage] = useState("");

  // Email OTP state
  const [emailDigits, setEmailDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [emailCountdown, setEmailCountdown] = useState(600); // 10 minutes
  const [emailResendCooldown, setEmailResendCooldown] = useState(60);

  // Mobile OTP state
  const [mobileDigits, setMobileDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [mobileCountdown, setMobileCountdown] = useState(300); // 5 minutes
  const [mobileResendCooldown, setMobileResendCooldown] = useState(60);

  // Inline editing during verification (Phase 12)
  const [isEditingEmail, setIsEditingEmail] = useState(false);
  const [editEmailVal, setEditEmailVal] = useState("");
  const [isEditingMobile, setIsEditingMobile] = useState(false);
  const [editMobileVal, setEditMobileVal] = useState("");
  const [editCountryCodeVal, setEditCountryCodeVal] = useState("+91");

  // Input refs for 6-digit OTP boxes
  const emailInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const mobileInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const loginOtpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const resetInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // ==========================================
  // LOGIN STATE (Phase 13)
  // ==========================================
  const [loginMethod, setLoginMethod] = useState<LoginMethod>("password");
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Login via OTP
  const [loginOtpStep, setLoginOtpStep] = useState<LoginOtpStep>("request");
  const [loginOtpDigits, setLoginOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [loginMaskedIdentifier, setLoginMaskedIdentifier] = useState("");
  const [loginOtpCooldown, setLoginOtpCooldown] = useState(0);
  const [loginOtpCountdown, setLoginOtpCountdown] = useState(300);

  // ==========================================
  // FORGOT PASSWORD STATE (Phase 14)
  // ==========================================
  const [resetStep, setResetStep] = useState<ResetStep>("request");
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [maskedResetIdentifier, setMaskedResetIdentifier] = useState("");
  const [resetDigits, setResetDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false);
  const [resetCooldown, setResetCooldown] = useState(0);
  const [resetCountdown, setResetCountdown] = useState(600);

  // ==========================================
  // FEEDBACK STATE
  // ==========================================
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const clearFeedback = () => {
    setError("");
    setSuccessMessage("");
  };

  // Restore pending verification state on page refresh if user was in verification step
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem("cs_pending_auth");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.email && parsed.step === "verify") {
          setSignupEmail(parsed.email);
          setMaskedEmail(parsed.maskedEmail || parsed.email);
          setFullName(parsed.fullName || "");
          setMobileNumber(parsed.mobileNumber || "");
          setCountryCode(parsed.countryCode || "+91");
          setMaskedMobile(parsed.maskedMobile || "");
          setSmsConfigured(parsed.smsConfigured ?? true);
          setEmailVerified(parsed.emailVerified || false);
          setMobileVerified(parsed.mobileVerified || false);
          setMode("signup");
          setSignupStep("verify");
        }
      }
    } catch {
      // Ignore sessionStorage read errors
    }
  }, []);

  // Sync to sessionStorage
  const savePendingState = (overrides?: any) => {
    try {
      sessionStorage.setItem(
        "cs_pending_auth",
        JSON.stringify({
          email: signupEmail.trim(),
          maskedEmail,
          fullName: fullName.trim(),
          mobileNumber: mobileNumber.trim(),
          countryCode,
          maskedMobile,
          smsConfigured,
          emailVerified,
          mobileVerified,
          step: "verify",
          ...overrides,
        })
      );
    } catch {
      // Ignore sessionStorage write errors
    }
  };

  // Global second timer for all cooldowns and expiration countdowns
  useEffect(() => {
    const timer = setInterval(() => {
      // Email OTP countdown & cooldown
      setEmailCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      setEmailResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));

      // Mobile OTP countdown & cooldown
      setMobileCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      setMobileResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));

      // Login OTP countdown & cooldown
      setLoginOtpCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      setLoginOtpCooldown((prev) => (prev > 0 ? prev - 1 : 0));

      // Reset countdown & cooldown
      setResetCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      setResetCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Focus input automatically on step changes
  useEffect(() => {
    if (mode === "signup" && signupStep === "verify") {
      setTimeout(() => {
        if (!emailVerified) {
          emailInputRefs.current[0]?.focus();
        } else if (!mobileVerified && smsConfigured) {
          mobileInputRefs.current[0]?.focus();
        }
      }, 100);
    } else if (mode === "login" && loginMethod === "otp" && loginOtpStep === "verify") {
      setTimeout(() => {
        loginOtpInputRefs.current[0]?.focus();
      }, 100);
    } else if (mode === "forgot_password" && resetStep === "verify") {
      setTimeout(() => {
        resetInputRefs.current[0]?.focus();
      }, 100);
    }
  }, [mode, signupStep, loginMethod, loginOtpStep, resetStep, emailVerified, mobileVerified, smsConfigured]);

  // ==========================================
  // PASSWORD STRENGTH EVALUATION (Phase 3)
  // ==========================================
  const evalPassword = (pwd: string) => {
    const hasMinLen = pwd.length >= 8;
    const hasUpper = /[A-Z]/.test(pwd);
    const hasLower = /[a-z]/.test(pwd);
    const hasNumber = /[0-9]/.test(pwd);
    const hasSpecial = /[^A-Za-z0-9]/.test(pwd);
    const noSpaces = !/\s/.test(pwd);

    let score = 0;
    if (hasMinLen) score++;
    if (hasUpper && hasLower) score++;
    if (hasNumber) score++;
    if (hasSpecial) score++;

    let label = "Weak";
    let colorClass = "bg-rose-500";
    let textClass = "text-rose-400";
    if (score === 2) {
      label = "Fair";
      colorClass = "bg-amber-500";
      textClass = "text-amber-400";
    } else if (score === 3) {
      label = "Good";
      colorClass = "bg-sky-500";
      textClass = "text-sky-400";
    } else if (score === 4) {
      label = "Strong";
      colorClass = "bg-emerald-500";
      textClass = "text-emerald-400";
    }

    const isValid = hasMinLen && hasUpper && hasLower && hasNumber && hasSpecial && noSpaces;
    return {
      hasMinLen,
      hasUpper,
      hasLower,
      hasNumber,
      hasSpecial,
      noSpaces,
      score,
      label,
      colorClass,
      textClass,
      isValid,
    };
  };

  const signupStrength = evalPassword(signupPassword);
  const signupPassMatch = signupPassword === confirmPassword && confirmPassword.length > 0;

  const resetStrength = evalPassword(newPassword);
  const resetPassMatch = newPassword === confirmNewPassword && confirmNewPassword.length > 0;

  // ==========================================
  // DIGIT BOX HELPERS
  // ==========================================
  const handleDigitChangeGeneric = (
    idx: number,
    val: string,
    digitsArr: string[],
    setDigitsArr: (d: string[]) => void,
    refs: React.MutableRefObject<(HTMLInputElement | null)[]>
  ) => {
    const numericChar = val.replace(/\D/g, "").slice(-1);
    const next = [...digitsArr];
    next[idx] = numericChar;
    setDigitsArr(next);
    clearFeedback();

    if (numericChar && idx < 5) {
      refs.current[idx + 1]?.focus();
    }
  };

  const handleDigitKeyDownGeneric = (
    idx: number,
    e: React.KeyboardEvent<HTMLInputElement>,
    digitsArr: string[],
    setDigitsArr: (d: string[]) => void,
    refs: React.MutableRefObject<(HTMLInputElement | null)[]>
  ) => {
    if (e.key === "Backspace") {
      if (!digitsArr[idx] && idx > 0) {
        const next = [...digitsArr];
        next[idx - 1] = "";
        setDigitsArr(next);
        refs.current[idx - 1]?.focus();
      } else {
        const next = [...digitsArr];
        next[idx] = "";
        setDigitsArr(next);
      }
    } else if (e.key === "ArrowLeft" && idx > 0) {
      e.preventDefault();
      refs.current[idx - 1]?.focus();
    } else if (e.key === "ArrowRight" && idx < 5) {
      e.preventDefault();
      refs.current[idx + 1]?.focus();
    }
  };

  const handlePasteGeneric = (
    e: React.ClipboardEvent,
    setDigitsArr: (d: string[]) => void,
    refs: React.MutableRefObject<(HTMLInputElement | null)[]>
  ) => {
    e.preventDefault();
    const pasteData = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!pasteData) return;
    const next = ["", "", "", "", "", ""];
    for (let i = 0; i < 6; i++) {
      next[i] = pasteData[i] || "";
    }
    setDigitsArr(next);
    clearFeedback();
    const nextFocus = Math.min(pasteData.length, 5);
    refs.current[nextFocus]?.focus();
  };

  // ==========================================
  // SIGNUP FLOW (Phase 1, 2, 7, 10, 11)
  // ==========================================
  const handleSignupInitiate = async (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();

    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }
    if (!signupEmail.trim() || !signupEmail.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    if (mobileNumber.trim()) {
      const cleanMob = mobileNumber.replace(/[\s-]/g, "");
      if (!/^\d{7,15}$/.test(cleanMob)) {
        setError("Please enter a valid mobile number (7 to 15 digits).");
        return;
      }
    }
    if (!signupStrength.isValid) {
      setError(
        "Password must be at least 8 characters and include uppercase, lowercase, number, and special character."
      );
      return;
    }
    if (!signupPassMatch) {
      setError("Passwords do not match.");
      return;
    }
    if (!agreeTerms) {
      setError("Please accept the Terms of Service and Privacy Policy to continue.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.signupInitiate({
        full_name: fullName.trim(),
        email: signupEmail.trim(),
        mobile_number: mobileNumber.trim() ? mobileNumber.replace(/[\s-]/g, "") : undefined,
        country_code: countryCode,
        password: signupPassword,
        confirm_password: confirmPassword,
        terms_accepted: agreeTerms,
      });

      if (res.is_verified && res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        router.push("/dashboard");
        return;
      }

      const maskedEm = res.masked_email || signupEmail.trim();
      const maskedMob = res.masked_mobile || (mobileNumber.trim() ? `${countryCode} ${mobileNumber.trim()}` : "");
      const isSmsOk = res.sms_status !== "SMS_NOT_CONFIGURED";

      setMaskedEmail(maskedEm);
      setMaskedMobile(maskedMob);
      setSmsConfigured(isSmsOk);
      setSmsMessage(res.sms_message || "");
      setEmailVerified(false);
      setMobileVerified(false);
      setEmailDigits(["", "", "", "", "", ""]);
      setMobileDigits(["", "", "", "", "", ""]);
      setEmailCountdown(600);
      setMobileCountdown(300);
      setEmailResendCooldown(60);
      setMobileResendCooldown(60);
      setSignupStep("verify");
      setSuccessMessage(res.message || "Verification code sent to your email.");

      savePendingState({
        maskedEmail: maskedEm,
        maskedMobile: maskedMob,
        smsConfigured: isSmsOk,
        emailVerified: false,
        mobileVerified: false,
      });
    } catch (err: any) {
      setError(err.message || "Unable to send verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Verify Email OTP
  const handleVerifyEmail = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const code = emailDigits.join("").trim();
    if (code.length !== 6) {
      setError("Please enter the complete 6-digit email verification code.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.signupVerifyEmail({
        email: signupEmail.trim(),
        otp: code,
      });

      setEmailVerified(true);
      savePendingState({ emailVerified: true });

      // If user is now fully verified or mobile is optional/not configured
      if (res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        setSuccessMessage("Account successfully activated! Redirecting to dashboard...");
        setTimeout(() => router.push("/dashboard"), 500);
        return;
      }

      setSuccessMessage("Email address verified successfully!");
    } catch (err: any) {
      setEmailDigits(["", "", "", "", "", ""]);
      setError(err.message || "Invalid or expired verification code. Please try again.");
      emailInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // Verify Mobile OTP
  const handleVerifyMobile = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const code = mobileDigits.join("").trim();
    if (code.length !== 6) {
      setError("Please enter the complete 6-digit mobile verification code.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.signupVerifyMobile({
        email: signupEmail.trim(),
        otp: code,
      });

      setMobileVerified(true);
      savePendingState({ mobileVerified: true });

      if (res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        setSuccessMessage("Account verified and activated! Redirecting to dashboard...");
        setTimeout(() => router.push("/dashboard"), 500);
        return;
      }

      setSuccessMessage("Mobile number verified successfully!");
    } catch (err: any) {
      setMobileDigits(["", "", "", "", "", ""]);
      setError(err.message || "Invalid or expired verification code. Please try again.");
      mobileInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // Resend Email OTP
  const handleResendEmailOtp = async () => {
    if (emailResendCooldown > 0 || loading) return;
    clearFeedback();
    setLoading(true);
    try {
      const res = await api.resendEmailOtp({ email: signupEmail.trim() });
      setEmailResendCooldown(60);
      setEmailCountdown(600);
      setEmailDigits(["", "", "", "", "", ""]);
      setSuccessMessage(res.message || "New email verification code sent.");
      emailInputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.message || "Unable to send verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Resend Mobile OTP
  const handleResendMobileOtp = async () => {
    if (mobileResendCooldown > 0 || loading) return;
    clearFeedback();
    setLoading(true);
    try {
      const res = await api.resendMobileOtp({ email: signupEmail.trim() });
      setMobileResendCooldown(60);
      setMobileCountdown(300);
      setMobileDigits(["", "", "", "", "", ""]);
      setSuccessMessage(res.message || "New mobile verification code sent via SMS.");
      mobileInputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.message || "Unable to send mobile verification code.");
    } finally {
      setLoading(false);
    }
  };

  // Skip Mobile Verification (Phase 11)
  const handleSkipMobileVerification = async () => {
    if (!emailVerified) {
      setError("Please verify your email address before continuing.");
      return;
    }
    clearFeedback();
    setLoading(true);
    try {
      // Re-call verify-email or login to get token now that email is verified
      const res = await api.login({
        email: signupEmail.trim(),
        password: signupPassword,
      });
      if (res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to finalize account activation.");
    } finally {
      setLoading(false);
    }
  };

  // Inline Change Email (Phase 12)
  const handleSaveChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    const newEm = editEmailVal.trim();
    if (!newEm || !newEm.includes("@")) {
      setError("Please enter a valid new email address.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.changeContact({
        email: signupEmail.trim(),
        new_email: newEm,
      });

      setSignupEmail(newEm);
      setMaskedEmail(res.masked_email || newEm);
      setEmailVerified(false);
      setEmailDigits(["", "", "", "", "", ""]);
      setEmailCountdown(600);
      setEmailResendCooldown(60);
      setIsEditingEmail(false);
      setSuccessMessage(res.message || `Verification code sent to ${newEm}`);

      savePendingState({
        email: newEm,
        maskedEmail: res.masked_email || newEm,
        emailVerified: false,
      });
    } catch (err: any) {
      setError(err.message || "Failed to update email address.");
    } finally {
      setLoading(false);
    }
  };

  // Inline Change Mobile (Phase 12)
  const handleSaveChangeMobile = async (e: React.FormEvent) => {
    e.preventDefault();
    const newMob = editMobileVal.trim().replace(/[\s-]/g, "");
    if (!/^\d{7,15}$/.test(newMob)) {
      setError("Please enter a valid mobile number (7 to 15 digits).");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.changeContact({
        email: signupEmail.trim(),
        new_mobile: newMob,
        country_code: editCountryCodeVal,
      });

      setMobileNumber(newMob);
      setCountryCode(editCountryCodeVal);
      setMaskedMobile(res.masked_mobile || `${editCountryCodeVal} ${newMob}`);
      setMobileVerified(false);
      setMobileDigits(["", "", "", "", "", ""]);
      setMobileCountdown(300);
      setMobileResendCooldown(60);
      setIsEditingMobile(false);
      setSuccessMessage(res.message || "Verification code sent to your new mobile number.");

      savePendingState({
        mobileNumber: newMob,
        countryCode: editCountryCodeVal,
        maskedMobile: res.masked_mobile || `${editCountryCodeVal} ${newMob}`,
        mobileVerified: false,
      });
    } catch (err: any) {
      setError(err.message || "Failed to update mobile number.");
    } finally {
      setLoading(false);
    }
  };

  // Cancel Verification and Return to Form
  const handleCancelVerification = () => {
    clearFeedback();
    sessionStorage.removeItem("cs_pending_auth");
    setSignupStep("form");
  };

  // ==========================================
  // LOGIN FLOW (Phase 13)
  // ==========================================
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();

    const ident = loginIdentifier.trim();
    if (!ident) {
      setError("Please enter your email address or mobile number.");
      return;
    }
    if (!loginPassword) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.login({
        identifier: ident,
        password: loginPassword,
        remember_me: rememberMe,
      });

      if (res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        router.push("/dashboard");
      }
    } catch (err: any) {
      if (err.status === 401 || err.status === 404) {
        setError("Invalid email/mobile or password.");
      } else {
        setError(err.message || "Invalid email/mobile or password.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Login via OTP: Request OTP
  const handleRequestLoginOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();

    const ident = loginIdentifier.trim();
    if (!ident) {
      setError("Please enter your registered email address or mobile number.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.loginOtpInitiate({ identifier: ident });
      setLoginMaskedIdentifier(res.masked_target || ident);
      setLoginOtpStep("verify");
      setLoginOtpCooldown(60);
      setLoginOtpCountdown(300);
      setLoginOtpDigits(["", "", "", "", "", ""]);
      setSuccessMessage(res.message || "Login verification code sent.");
    } catch (err: any) {
      setError(err.message || "Unable to send login verification code.");
    } finally {
      setLoading(false);
    }
  };

  // Login via OTP: Verify & Sign In
  const handleVerifyLoginOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = loginOtpDigits.join("").trim();
    if (code.length !== 6) {
      setError("Please enter the complete 6-digit verification code.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.loginOtpVerify({
        identifier: loginIdentifier.trim(),
        otp: code,
      });

      if (res.access_token) {
        setToken(res.access_token);
        sessionStorage.removeItem("cs_pending_auth");
        router.push("/dashboard");
      }
    } catch (err: any) {
      setLoginOtpDigits(["", "", "", "", "", ""]);
      setError(err.message || "Invalid or expired login code. Please try again.");
      loginOtpInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // FORGOT PASSWORD FLOW (Phase 14)
  // ==========================================
  const handleForgotPasswordRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    const ident = resetIdentifier.trim();
    if (!ident) {
      setError("Please enter your registered email address or mobile number.");
      return;
    }

    clearFeedback();
    setLoading(true);
    try {
      const res = await api.forgotPassword({ identifier: ident });
      setMaskedResetIdentifier(res.masked_target || ident);
      setResetDigits(["", "", "", "", "", ""]);
      setResetStep("verify");
      setResetCooldown(60);
      setResetCountdown(600);
      setSuccessMessage(res.message || "Verification code sent.");
    } catch (err: any) {
      setError(err.message || "Unable to send verification code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = resetDigits.join("").trim();
    if (code.length !== 6) {
      setError("Please enter the complete 6-digit verification code.");
      return;
    }
    if (!resetStrength.isValid) {
      setError(
        "New password must be at least 8 characters and include uppercase, lowercase, number, and special character."
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
        identifier: resetIdentifier.trim(),
        otp: code,
        new_password: newPassword,
        confirm_password: confirmNewPassword,
      });

      setSuccessMessage(res.message || "Password updated successfully. Please log in with your new password.");
      setLoginIdentifier(resetIdentifier.trim());
      setNewPassword("");
      setConfirmNewPassword("");
      setResetDigits(["", "", "", "", "", ""]);
      setResetStep("request");
      setMode("login");
      setLoginMethod("password");
    } catch (err: any) {
      setResetDigits(["", "", "", "", "", ""]);
      setError(err.message || "Invalid or expired reset code. Please try again.");
      resetInputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResendResetOtp = async () => {
    if (resetCooldown > 0 || loading) return;
    clearFeedback();
    setLoading(true);
    try {
      const res = await api.forgotPassword({ identifier: resetIdentifier.trim() });
      setResetCooldown(60);
      setResetCountdown(600);
      setResetDigits(["", "", "", "", "", ""]);
      setSuccessMessage(res.message || "New reset verification code sent.");
      resetInputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.message || "Unable to send reset verification code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#0B1120] text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 -right-40 w-96 h-96 bg-teal-500/10 rounded-full blur-[120px]" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-slate-800/20 rounded-full blur-[120px]" />
      </div>

      <div className="w-full max-w-[520px] relative z-10 py-8">
        {/* Logo and Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex justify-center mb-3">
            <Logo size={32} />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white">ContentSignal</h1>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mt-1">
            Enterprise Decision Support Platform
          </p>
        </div>

        {/* Main Glass Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 rounded-2xl shadow-2xl p-6 sm:p-8">
          {/* Navigation Tabs (Only shown when not in verification step) */}
          {signupStep === "form" && resetStep === "request" && (
            <div className="grid grid-cols-2 p-1 mb-6 bg-slate-950/60 border border-slate-800/80 rounded-xl">
              <button
                type="button"
                onClick={() => {
                  clearFeedback();
                  setMode("login");
                }}
                className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                  mode === "login"
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  clearFeedback();
                  setMode("signup");
                }}
                className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                  mode === "signup"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Create Account
              </button>
            </div>
          )}

          {/* Feedback Alerts */}
          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{error}</div>
            </div>
          )}

          {successMessage && (
            <div className="mb-5 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{successMessage}</div>
            </div>
          )}

          {/* ================================================================= */}
          {/* SCREEN 3: LOGIN                                                   */}
          {/* ================================================================= */}
          {mode === "login" && (
            <div>
              {/* Method Switcher: Password vs OTP */}
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800/60 text-xs">
                <span className="font-semibold text-slate-300">
                  {loginMethod === "password" ? "Sign In with Password" : "Sign In with Verification Code"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    clearFeedback();
                    setLoginMethod(loginMethod === "password" ? "otp" : "password");
                    setLoginOtpStep("request");
                  }}
                  className="text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  {loginMethod === "password" ? "Use OTP instead" : "Use Password instead"}
                </button>
              </div>

              {loginMethod === "password" ? (
                <form onSubmit={handlePasswordLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Email or Mobile Number
                    </label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        {loginIdentifier.includes("@") ? (
                          <Mail className="w-4 h-4" />
                        ) : (
                          <Smartphone className="w-4 h-4" />
                        )}
                      </span>
                      <input
                        type="text"
                        required
                        value={loginIdentifier}
                        onChange={(e) => {
                          setLoginIdentifier(e.target.value);
                          clearFeedback();
                        }}
                        placeholder="name@company.com or 9876543210"
                        className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold text-slate-300">Password</label>
                      <button
                        type="button"
                        onClick={() => {
                          clearFeedback();
                          setResetIdentifier(loginIdentifier);
                          setMode("forgot_password");
                          setResetStep("request");
                        }}
                        className="text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
                      >
                        Forgot password?
                      </button>
                    </div>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <Lock className="w-4 h-4" />
                      </span>
                      <input
                        type={showLoginPassword ? "text" : "password"}
                        required
                        value={loginPassword}
                        onChange={(e) => {
                          setLoginPassword(e.target.value);
                          clearFeedback();
                        }}
                        placeholder="••••••••"
                        className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowLoginPassword(!showLoginPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                        tabIndex={-1}
                      >
                        {showLoginPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center pt-1">
                    <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-400 hover:text-slate-300">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded border-slate-700 bg-slate-950/80 text-emerald-600 focus:ring-emerald-500 focus:ring-offset-0"
                      />
                      <span>Remember me for 30 days</span>
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !loginIdentifier || !loginPassword}
                    className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
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
                </form>
              ) : (
                /* Login with OTP */
                <div>
                  {loginOtpStep === "request" ? (
                    <form onSubmit={handleRequestLoginOtp} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                          Registered Email or Mobile Number
                        </label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            {loginIdentifier.includes("@") ? (
                              <Mail className="w-4 h-4" />
                            ) : (
                              <Smartphone className="w-4 h-4" />
                            )}
                          </span>
                          <input
                            type="text"
                            required
                            value={loginIdentifier}
                            onChange={(e) => {
                              setLoginIdentifier(e.target.value);
                              clearFeedback();
                            }}
                            placeholder="name@company.com or 9876543210"
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={loading || !loginIdentifier.trim()}
                        className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <span>Send Login Code</span>
                            <ArrowRight className="w-4 h-4" />
                          </>
                        )}
                      </button>
                    </form>
                  ) : (
                    <form onSubmit={handleVerifyLoginOtp} className="space-y-5">
                      <div className="text-center space-y-1">
                        <p className="text-xs text-slate-400">
                          Enter 6-digit code sent to{" "}
                          <span className="font-semibold text-slate-200">{loginMaskedIdentifier}</span>
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Expires in <span className="font-mono text-emerald-400">{formatTime(loginOtpCountdown)}</span>
                        </p>
                      </div>

                      <div className="flex justify-center items-center gap-2.5">
                        {loginOtpDigits.map((digit, idx) => (
                          <input
                            key={idx}
                            ref={(el) => {
                              loginOtpInputRefs.current[idx] = el;
                            }}
                            type="text"
                            inputMode="numeric"
                            maxLength={1}
                            value={digit}
                            onChange={(e) =>
                              handleDigitChangeGeneric(
                                idx,
                                e.target.value,
                                loginOtpDigits,
                                setLoginOtpDigits,
                                loginOtpInputRefs
                              )
                            }
                            onKeyDown={(e) =>
                              handleDigitKeyDownGeneric(
                                idx,
                                e,
                                loginOtpDigits,
                                setLoginOtpDigits,
                                loginOtpInputRefs
                              )
                            }
                            onPaste={(e) =>
                              handlePasteGeneric(e, setLoginOtpDigits, loginOtpInputRefs)
                            }
                            className="w-11 h-12 text-center text-lg font-bold font-mono rounded-xl border border-slate-700 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                          />
                        ))}
                      </div>

                      <button
                        type="submit"
                        disabled={loading || loginOtpDigits.join("").length !== 6}
                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <span>Verify &amp; Sign In</span>
                            <ArrowRight className="w-4 h-4" />
                          </>
                        )}
                      </button>

                      <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
                        <button
                          type="button"
                          onClick={() => setLoginOtpStep("request")}
                          className="text-slate-400 hover:text-slate-200"
                        >
                          Change recipient
                        </button>
                        <button
                          type="button"
                          disabled={loginOtpCooldown > 0 || loading}
                          onClick={handleRequestLoginOtp}
                          className="text-emerald-400 hover:text-emerald-300 disabled:text-slate-500 disabled:cursor-not-allowed"
                        >
                          {loginOtpCooldown > 0 ? `Resend in ${loginOtpCooldown}s` : "Resend code"}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}

              <div className="text-center pt-4 mt-4 border-t border-slate-800/80">
                <span className="text-xs text-slate-400">Don&apos;t have an account? </span>
                <button
                  type="button"
                  onClick={() => {
                    clearFeedback();
                    setSignupEmail(loginIdentifier.includes("@") ? loginIdentifier : "");
                    setMode("signup");
                    setSignupStep("form");
                  }}
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  Create Account
                </button>
              </div>
            </div>
          )}

          {/* ================================================================= */}
          {/* SCREEN 1: SIGNUP FORM                                             */}
          {/* ================================================================= */}
          {mode === "signup" && signupStep === "form" && (
            <form onSubmit={handleSignupInitiate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Full Name</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </span>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      clearFeedback();
                    }}
                    placeholder="Anjali Sharma"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Work Email</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </span>
                  <input
                    type="email"
                    required
                    value={signupEmail}
                    onChange={(e) => {
                      setSignupEmail(e.target.value);
                      clearFeedback();
                    }}
                    placeholder="anjali@company.com"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Mobile Number <span className="text-slate-500 font-normal">(Optional)</span>
                </label>
                <div className="flex gap-2">
                  <select
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    className="w-[110px] shrink-0 px-2 py-2.5 text-xs font-medium rounded-xl border border-slate-800 bg-slate-950/70 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all cursor-pointer"
                  >
                    {COUNTRY_CODES.map((c) => (
                      <option key={c.code} value={c.code} className="bg-slate-900 text-white">
                        {c.flag} {c.code}
                      </option>
                    ))}
                  </select>
                  <div className="relative flex-1">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Phone className="w-4 h-4" />
                    </span>
                    <input
                      type="tel"
                      value={mobileNumber}
                      onChange={(e) => {
                        setMobileNumber(e.target.value.replace(/[^\d\s-]/g, ""));
                        clearFeedback();
                      }}
                      placeholder="98765 43210"
                      className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type={showSignupPassword ? "text" : "password"}
                    required
                    value={signupPassword}
                    onChange={(e) => {
                      setSignupPassword(e.target.value);
                      clearFeedback();
                    }}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSignupPassword(!showSignupPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                    tabIndex={-1}
                  >
                    {showSignupPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {signupPassword && (
                  <div className="mt-2 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Strength:</span>
                      <span className={`font-semibold ${signupStrength.textClass}`}>
                        {signupStrength.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5 h-1">
                      {[1, 2, 3, 4].map((step) => (
                        <div
                          key={step}
                          className={`h-full rounded-full transition-all duration-300 ${
                            signupStrength.score >= step
                              ? signupStrength.colorClass
                              : "bg-slate-800"
                          }`}
                        />
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1 text-[10px] text-slate-400">
                      <span className={signupStrength.hasMinLen ? "text-emerald-400" : ""}>
                        {signupStrength.hasMinLen ? "✓" : "•"} 8+ characters
                      </span>
                      <span className={signupStrength.hasUpper ? "text-emerald-400" : ""}>
                        {signupStrength.hasUpper ? "✓" : "•"} 1 uppercase
                      </span>
                      <span className={signupStrength.hasLower ? "text-emerald-400" : ""}>
                        {signupStrength.hasLower ? "✓" : "•"} 1 lowercase
                      </span>
                      <span className={signupStrength.hasNumber && signupStrength.hasSpecial ? "text-emerald-400" : ""}>
                        {signupStrength.hasNumber && signupStrength.hasSpecial ? "✓" : "•"} 1 number &amp; 1 symbol
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Confirm Password</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </span>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    required
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      clearFeedback();
                    }}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {confirmPassword && !signupPassMatch && (
                  <p className="text-[11px] text-rose-400 mt-1">Passwords do not match</p>
                )}
              </div>

              <div className="pt-1">
                <label className="flex items-start gap-2 cursor-pointer select-none text-xs text-slate-400 leading-snug">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-950/80 text-emerald-600 focus:ring-emerald-500 focus:ring-offset-0 mt-0.5"
                  />
                  <span>
                    I agree to the{" "}
                    <span className="text-emerald-400 hover:underline">Terms of Service</span> and{" "}
                    <span className="text-emerald-400 hover:underline">Privacy Policy</span>.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={
                  loading ||
                  !fullName.trim() ||
                  !signupEmail ||
                  !signupStrength.isValid ||
                  !signupPassMatch ||
                  !agreeTerms
                }
                className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <span>Create Account &amp; Verify</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              <div className="text-center pt-4 border-t border-slate-800/80">
                <span className="text-xs text-slate-400">Already have an account? </span>
                <button
                  type="button"
                  onClick={() => {
                    clearFeedback();
                    setLoginIdentifier(signupEmail);
                    setMode("login");
                  }}
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  Sign In
                </button>
              </div>
            </form>
          )}

          {/* ================================================================= */}
          {/* SCREEN 2: DUAL VERIFICATION SCREEN (Phases 10, 11, 12, 15)        */}
          {/* ================================================================= */}
          {mode === "signup" && signupStep === "verify" && (
            <div className="space-y-6">
              {/* Header */}
              <div className="text-center space-y-1.5 pb-2">
                <div className="w-12 h-12 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-2">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h2 className="text-lg font-bold text-white">Verify Your Account</h2>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  We need to verify your contact details before activating your ContentSignal account.
                </p>
              </div>

              {/* ------------------------------------------------------------- */}
              {/* SECTION 1: EMAIL VERIFICATION                                 */}
              {/* ------------------------------------------------------------- */}
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/50 space-y-3.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {emailVerified ? (
                      <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center">
                        <Clock className="w-3.5 h-3.5" />
                      </div>
                    )}
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Email Verification
                    </span>
                  </div>
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      emailVerified
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}
                  >
                    {emailVerified ? "Verified" : "Pending"}
                  </span>
                </div>

                {/* Email address display & change button */}
                <div className="flex items-center justify-between text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                  <div className="flex items-center gap-2 truncate">
                    <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="font-mono text-slate-200 truncate">{maskedEmail}</span>
                  </div>
                  {!emailVerified && !isEditingEmail && (
                    <button
                      type="button"
                      onClick={() => {
                        setEditEmailVal(signupEmail);
                        setIsEditingEmail(true);
                      }}
                      className="text-emerald-400 hover:text-emerald-300 text-xs font-medium flex items-center gap-1 shrink-0 ml-2"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Change</span>
                    </button>
                  )}
                </div>

                {/* Inline Change Email Form (Phase 12) */}
                {isEditingEmail && !emailVerified && (
                  <form onSubmit={handleSaveChangeEmail} className="space-y-2 pt-1">
                    <div className="flex gap-2">
                      <input
                        type="email"
                        required
                        value={editEmailVal}
                        onChange={(e) => setEditEmailVal(e.target.value)}
                        placeholder="new.email@company.com"
                        className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                      <button
                        type="submit"
                        disabled={loading || !editEmailVal.includes("@")}
                        className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg disabled:opacity-50"
                      >
                        {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Update & Resend"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsEditingEmail(false)}
                        className="px-2 py-1.5 text-xs text-slate-400 hover:text-white"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </form>
                )}

                {/* OTP Input Boxes (only if not yet verified) */}
                {!emailVerified && !isEditingEmail && (
                  <div className="space-y-3 pt-1">
                    <div className="flex justify-center items-center gap-2">
                      {emailDigits.map((digit, idx) => (
                        <input
                          key={idx}
                          ref={(el) => {
                            emailInputRefs.current[idx] = el;
                          }}
                          type="text"
                          inputMode="numeric"
                          maxLength={1}
                          value={digit}
                          onChange={(e) =>
                            handleDigitChangeGeneric(
                              idx,
                              e.target.value,
                              emailDigits,
                              setEmailDigits,
                              emailInputRefs
                            )
                          }
                          onKeyDown={(e) =>
                            handleDigitKeyDownGeneric(
                              idx,
                              e,
                              emailDigits,
                              setEmailDigits,
                              emailInputRefs
                            )
                          }
                          onPaste={(e) => handlePasteGeneric(e, setEmailDigits, emailInputRefs)}
                          className="w-10 h-12 text-center text-lg font-bold font-mono rounded-xl border border-slate-700 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                        />
                      ))}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                      <span>
                        Code expires in{" "}
                        <span className="font-mono text-emerald-400 font-semibold">
                          {formatTime(emailCountdown)}
                        </span>
                      </span>
                      <button
                        type="button"
                        disabled={emailResendCooldown > 0 || loading}
                        onClick={handleResendEmailOtp}
                        className="font-medium text-emerald-400 hover:text-emerald-300 disabled:text-slate-500 disabled:cursor-not-allowed flex items-center gap-1"
                      >
                        <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                        <span>
                          {emailResendCooldown > 0 ? `Resend in ${emailResendCooldown}s` : "Resend code"}
                        </span>
                      </button>
                    </div>

                    <button
                      type="button"
                      disabled={loading || emailDigits.join("").length !== 6}
                      onClick={() => handleVerifyEmail()}
                      className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : "Verify Email"}
                    </button>

                    <p className="text-[10px] text-slate-500 text-center">
                      Check your spam or junk folder if you don&apos;t see it in your inbox.
                    </p>
                  </div>
                )}
              </div>

              {/* ------------------------------------------------------------- */}
              {/* SECTION 2: MOBILE VERIFICATION (Optional/Configured)          */}
              {/* ------------------------------------------------------------- */}
              {mobileNumber.trim() ? (
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/50 space-y-3.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {mobileVerified ? (
                        <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                          <Check className="w-3.5 h-3.5" />
                        </div>
                      ) : !smsConfigured ? (
                        <div className="w-6 h-6 rounded-full bg-slate-700/50 text-slate-400 flex items-center justify-center">
                          <AlertCircle className="w-3.5 h-3.5" />
                        </div>
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center">
                          <Clock className="w-3.5 h-3.5" />
                        </div>
                      )}
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                        Mobile Verification
                      </span>
                    </div>
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                        mobileVerified
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : !smsConfigured
                          ? "bg-slate-800 text-slate-400 border border-slate-700"
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}
                    >
                      {mobileVerified
                        ? "Verified"
                        : !smsConfigured
                        ? "Unavailable"
                        : "Pending"}
                    </span>
                  </div>

                  {/* Mobile number display & change button */}
                  <div className="flex items-center justify-between text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                    <div className="flex items-center gap-2 truncate">
                      <Smartphone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="font-mono text-slate-200 truncate">{maskedMobile}</span>
                    </div>
                    {!mobileVerified && !isEditingMobile && (
                      <button
                        type="button"
                        onClick={() => {
                          setEditMobileVal(mobileNumber);
                          setEditCountryCodeVal(countryCode);
                          setIsEditingMobile(true);
                        }}
                        className="text-emerald-400 hover:text-emerald-300 text-xs font-medium flex items-center gap-1 shrink-0 ml-2"
                      >
                        <Edit3 className="w-3 h-3" />
                        <span>Change</span>
                      </button>
                    )}
                  </div>

                  {/* Inline Change Mobile Form (Phase 12) */}
                  {isEditingMobile && !mobileVerified && (
                    <form onSubmit={handleSaveChangeMobile} className="space-y-2 pt-1">
                      <div className="flex gap-2">
                        <select
                          value={editCountryCodeVal}
                          onChange={(e) => setEditCountryCodeVal(e.target.value)}
                          className="w-[85px] px-1 py-1.5 text-xs rounded-lg border border-slate-700 bg-slate-950 text-white"
                        >
                          {COUNTRY_CODES.map((c) => (
                            <option key={c.code} value={c.code}>
                              {c.code}
                            </option>
                          ))}
                        </select>
                        <input
                          type="tel"
                          required
                          value={editMobileVal}
                          onChange={(e) => setEditMobileVal(e.target.value)}
                          placeholder="98765 43210"
                          className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                        <button
                          type="submit"
                          disabled={loading || !editMobileVal.trim()}
                          className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg disabled:opacity-50"
                        >
                          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Update"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setIsEditingMobile(false)}
                          className="px-2 py-1.5 text-xs text-slate-400 hover:text-white"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </form>
                  )}

                  {/* If SMS provider is NOT configured (Phase 10 & 11) */}
                  {!smsConfigured ? (
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-2">
                      <p>
                        Mobile verification is temporarily unavailable. We&apos;ll verify your mobile number later.
                      </p>
                      {emailVerified && (
                        <button
                          type="button"
                          onClick={handleSkipMobileVerification}
                          className="text-xs font-semibold text-emerald-400 hover:underline flex items-center gap-1"
                        >
                          <span>Proceed to Dashboard</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ) : (
                    /* If SMS provider IS configured */
                    !mobileVerified && !isEditingMobile && (
                      <div className="space-y-3 pt-1">
                        <div className="flex justify-center items-center gap-2">
                          {mobileDigits.map((digit, idx) => (
                            <input
                              key={idx}
                              ref={(el) => {
                                mobileInputRefs.current[idx] = el;
                              }}
                              type="text"
                              inputMode="numeric"
                              maxLength={1}
                              value={digit}
                              onChange={(e) =>
                                handleDigitChangeGeneric(
                                  idx,
                                  e.target.value,
                                  mobileDigits,
                                  setMobileDigits,
                                  mobileInputRefs
                                )
                              }
                              onKeyDown={(e) =>
                                handleDigitKeyDownGeneric(
                                  idx,
                                  e,
                                  mobileDigits,
                                  setMobileDigits,
                                  mobileInputRefs
                                )
                              }
                              onPaste={(e) => handlePasteGeneric(e, setMobileDigits, mobileInputRefs)}
                              className="w-10 h-12 text-center text-lg font-bold font-mono rounded-xl border border-slate-700 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                            />
                          ))}
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
                          <span>
                            Expires in{" "}
                            <span className="font-mono text-emerald-400 font-semibold">
                              {formatTime(mobileCountdown)}
                            </span>
                          </span>
                          <button
                            type="button"
                            disabled={mobileResendCooldown > 0 || loading}
                            onClick={handleResendMobileOtp}
                            className="font-medium text-emerald-400 hover:text-emerald-300 disabled:text-slate-500 disabled:cursor-not-allowed flex items-center gap-1"
                          >
                            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
                            <span>
                              {mobileResendCooldown > 0
                                ? `Resend in ${mobileResendCooldown}s`
                                : "Resend SMS"}
                            </span>
                          </button>
                        </div>

                        <button
                          type="button"
                          disabled={loading || mobileDigits.join("").length !== 6}
                          onClick={() => handleVerifyMobile()}
                          className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin mx-auto" /> : "Verify Mobile"}
                        </button>

                        {emailVerified && (
                          <div className="text-center pt-1">
                            <button
                              type="button"
                              onClick={handleSkipMobileVerification}
                              className="text-[11px] text-slate-400 hover:text-slate-200 underline"
                            >
                              Skip mobile verification for now
                            </button>
                          </div>
                        )}
                      </div>
                    )
                  )}
                </div>
              ) : null}

              {/* Bottom Complete Activation or Back link */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handleCancelVerification}
                  className="text-slate-400 hover:text-slate-200 flex items-center gap-1"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to signup</span>
                </button>

                {emailVerified && (!mobileNumber.trim() || mobileVerified || !smsConfigured) && (
                  <button
                    type="button"
                    onClick={() => router.push("/dashboard")}
                    className="py-1.5 px-3 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-md"
                  >
                    <span>Enter Dashboard</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ================================================================= */}
          {/* SCREEN 4: FORGOT PASSWORD (Phase 14)                              */}
          {/* ================================================================= */}
          {mode === "forgot_password" && (
            <div>
              {resetStep === "request" ? (
                <form onSubmit={handleForgotPasswordRequest} className="space-y-4">
                  <div className="text-center space-y-1 mb-2">
                    <div className="w-10 h-10 mx-auto rounded-xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-300 mb-2">
                      <KeyRound className="w-5 h-5 text-emerald-400" />
                    </div>
                    <h2 className="text-base font-bold text-white">Reset Password</h2>
                    <p className="text-xs text-slate-400">
                      Enter your registered email or mobile number. We&apos;ll send you a verification code.
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Email or Mobile Number
                    </label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        {resetIdentifier.includes("@") ? (
                          <Mail className="w-4 h-4" />
                        ) : (
                          <Smartphone className="w-4 h-4" />
                        )}
                      </span>
                      <input
                        type="text"
                        required
                        value={resetIdentifier}
                        onChange={(e) => {
                          setResetIdentifier(e.target.value);
                          clearFeedback();
                        }}
                        placeholder="name@company.com or 9876543210"
                        className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !resetIdentifier.trim()}
                    className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <span>Send Verification Code</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  <div className="text-center pt-4 border-t border-slate-800/80">
                    <button
                      type="button"
                      onClick={() => {
                        clearFeedback();
                        setMode("login");
                      }}
                      className="text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                    >
                      &larr; Back to Sign In
                    </button>
                  </div>
                </form>
              ) : (
                /* Step 2: Verify & Enter New Password */
                <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                  <div className="text-center space-y-1 mb-2">
                    <h2 className="text-base font-bold text-white">Enter Code &amp; New Password</h2>
                    <p className="text-xs text-slate-400">
                      Code sent to <span className="font-semibold text-slate-200">{maskedResetIdentifier}</span>
                    </p>
                  </div>

                  <div className="flex justify-center items-center gap-2.5 my-3">
                    {resetDigits.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={(el) => {
                          resetInputRefs.current[idx] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) =>
                          handleDigitChangeGeneric(
                            idx,
                            e.target.value,
                            resetDigits,
                            setResetDigits,
                            resetInputRefs
                          )
                        }
                        onKeyDown={(e) =>
                          handleDigitKeyDownGeneric(
                            idx,
                            e,
                            resetDigits,
                            setResetDigits,
                            resetInputRefs
                          )
                        }
                        onPaste={(e) => handlePasteGeneric(e, setResetDigits, resetInputRefs)}
                        className="w-10 h-12 text-center text-lg font-bold font-mono rounded-xl border border-slate-700 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                    ))}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">New Password</label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <Lock className="w-4 h-4" />
                      </span>
                      <input
                        type={showResetPassword ? "text" : "password"}
                        required
                        value={newPassword}
                        onChange={(e) => {
                          setNewPassword(e.target.value);
                          clearFeedback();
                        }}
                        placeholder="••••••••"
                        className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowResetPassword(!showResetPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                        tabIndex={-1}
                      >
                        {showResetPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>

                    {newPassword && (
                      <div className="mt-2 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-400">Strength:</span>
                          <span className={`font-semibold ${resetStrength.textClass}`}>
                            {resetStrength.label}
                          </span>
                        </div>
                        <div className="grid grid-cols-4 gap-1.5 h-1">
                          {[1, 2, 3, 4].map((step) => (
                            <div
                              key={step}
                              className={`h-full rounded-full transition-all duration-300 ${
                                resetStrength.score >= step
                                  ? resetStrength.colorClass
                                  : "bg-slate-800"
                              }`}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Confirm New Password
                    </label>
                    <div className="relative">
                      <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                        <Lock className="w-4 h-4" />
                      </span>
                      <input
                        type={showResetConfirmPassword ? "text" : "password"}
                        required
                        value={confirmNewPassword}
                        onChange={(e) => {
                          setConfirmNewPassword(e.target.value);
                          clearFeedback();
                        }}
                        placeholder="••••••••"
                        className="w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border border-slate-800 bg-slate-950/70 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowResetConfirmPassword(!showResetConfirmPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
                        tabIndex={-1}
                      >
                        {showResetConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {confirmNewPassword && !resetPassMatch && (
                      <p className="text-[11px] text-rose-400 mt-1">Passwords do not match</p>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={
                      loading ||
                      resetDigits.join("").length !== 6 ||
                      !resetStrength.isValid ||
                      !resetPassMatch
                    }
                    className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-950/40"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <span>Update Password</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                    <button
                      type="button"
                      onClick={() => setResetStep("request")}
                      className="text-slate-400 hover:text-slate-200 flex items-center gap-1"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      <span>Back</span>
                    </button>

                    <button
                      type="button"
                      disabled={resetCooldown > 0 || loading}
                      onClick={handleResendResetOtp}
                      className="font-medium text-emerald-400 hover:text-emerald-300 disabled:text-slate-500 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                      <span>{resetCooldown > 0 ? `Resend in ${resetCooldown}s` : "Resend code"}</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>

        {/* Footer info */}
        <p className="text-center text-[11px] text-slate-500 mt-6">
          &copy; {new Date().getFullYear()} ContentSignal &bull; Enterprise Decision Support
        </p>
      </div>
    </div>
  );
}
