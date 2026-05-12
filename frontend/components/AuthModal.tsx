"use client";

import { useState, useEffect, useRef } from "react";
import { requestOTP, verifyOTP } from "@/lib/supabase";

type Step = "email" | "otp" | "success";

interface AuthModalProps {
  onClose: () => void;
  onSuccess: (email: string) => void;
}

export default function AuthModal({ onClose, onSuccess }: AuthModalProps) {
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await requestOTP(email);
      setStep("otp");
      setCooldown(60);
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (cooldown > 0) return;
    setLoading(true);
    setError("");
    try {
      await requestOTP(email);
      setCooldown(60);
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to resend. Try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleOtpChange(idx: number, value: string) {
    if (!/^\d*$/.test(value)) return;
    const next = [...otp];
    next[idx] = value.slice(-1);
    setOtp(next);
    if (value && idx < 5) otpRefs.current[idx + 1]?.focus();
    // Auto-submit when all 6 filled
    if (next.every((d) => d !== "") && value) {
      handleVerify(next.join(""));
    }
  }

  function handleOtpKeyDown(idx: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      otpRefs.current[idx - 1]?.focus();
    }
  }

  async function handleVerify(code?: string) {
    const token = code || otp.join("");
    if (token.length !== 6) {
      setError("Enter the full 6-digit code.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await verifyOTP(email, token);
      setStep("success");
      setTimeout(() => onSuccess(email), 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid code. Please try again.");
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-on-surface/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-surface-container-lowest rounded-2xl shadow-2xl max-w-sm w-full p-8 z-10">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors"
          aria-label="Close"
        >
          <span className="material-symbols-outlined text-on-surface-variant">close</span>
        </button>

        {/* Success */}
        {step === "success" && (
          <div className="text-center py-8">
            <div className="w-20 h-20 rounded-full bg-primary-fixed/20 flex items-center justify-center mx-auto mb-6">
              <span className="material-symbols-outlined text-primary text-4xl">check_circle</span>
            </div>
            <h2 className="font-headline text-2xl mb-2">You&apos;re in</h2>
            <p className="font-body text-sm text-on-surface-variant">Welcome to AuraFit, {email}</p>
          </div>
        )}

        {/* Email step */}
        {step === "email" && (
          <>
            <div className="mb-8">
              <div className="w-14 h-14 rounded-full bg-primary-fixed flex items-center justify-center mb-6">
                <span className="material-symbols-outlined text-on-primary-fixed text-2xl">auto_awesome</span>
              </div>
              <h2 className="font-headline text-2xl mb-2">Sign in to AuraFit</h2>
              <p className="font-body text-sm text-on-surface-variant">
                We&apos;ll send a 6-digit code to your email — no password needed.
              </p>
            </div>
            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <div>
                <label htmlFor="auth-email" className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant block mb-2">
                  Email address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@email.com"
                  className="w-full bg-surface-container-high border border-outline-variant/30 rounded-lg px-4 py-3 font-body text-sm focus:outline-none focus:border-primary transition-colors"
                  autoFocus
                  required
                />
              </div>
              {error && (
                <p className="font-body text-xs text-error">{error}</p>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-on-primary py-4 rounded-lg font-label uppercase tracking-widest text-xs hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? "Sending…" : "Send Code"}
              </button>
            </form>
          </>
        )}

        {/* OTP step */}
        {step === "otp" && (
          <>
            <div className="mb-8">
              <div className="w-14 h-14 rounded-full bg-primary-fixed flex items-center justify-center mb-6">
                <span className="material-symbols-outlined text-on-primary-fixed text-2xl">mark_email_read</span>
              </div>
              <h2 className="font-headline text-2xl mb-2">Check your inbox</h2>
              <p className="font-body text-sm text-on-surface-variant">
                Sent a 6-digit code to <strong className="text-on-surface">{email}</strong>.
              </p>
              <button
                onClick={() => { setStep("email"); setOtp(["","","","","",""]); setError(""); }}
                className="font-label text-[10px] uppercase tracking-widest text-primary mt-2 hover:underline underline-offset-4"
              >
                Change email
              </button>
            </div>

            {/* OTP Input */}
            <div className="flex gap-2 mb-6 justify-center">
              {otp.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => { otpRefs.current[idx] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  className="w-11 h-14 text-center text-xl font-headline bg-surface-container-high border border-outline-variant/30 rounded-lg focus:outline-none focus:border-primary transition-colors"
                />
              ))}
            </div>

            {error && <p className="font-body text-xs text-error text-center mb-4">{error}</p>}

            <button
              onClick={() => handleVerify()}
              disabled={loading || otp.some((d) => !d)}
              className="w-full bg-primary text-on-primary py-4 rounded-lg font-label uppercase tracking-widest text-xs hover:opacity-90 transition-opacity disabled:opacity-50 mb-4"
            >
              {loading ? "Verifying…" : "Verify Code"}
            </button>

            <div className="text-center">
              <button
                onClick={handleResend}
                disabled={cooldown > 0 || loading}
                className="font-label text-xs text-on-surface-variant hover:text-primary transition-colors disabled:opacity-50"
              >
                {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
