"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import {
  apiErrorMessage,
  AuthPayload,
  CatalogStatus,
  CostPolicy,
  getCatalogStatus,
  getCostPolicy,
  getStoredAuth,
  getUserSessions,
  getUserUsage,
  requestOtp,
  storeAuth,
  UsageLedgerPayload,
  UserIdentity,
  UserSessionSummary,
  verifyOtp,
} from "@/lib/api";

const statusStyles: Record<string, string> = {
  queued: "bg-tertiary/15 text-tertiary border-tertiary/30",
  processing: "bg-primary/15 text-primary border-primary/30",
  complete: "bg-secondary/15 text-secondary border-secondary/30",
  completed: "bg-secondary/15 text-secondary border-secondary/30",
  failed: "bg-error/15 text-error border-error/30",
};

function normalizeStatus(status: string) {
  return status.trim().toLowerCase();
}

function statusLabel(status: string) {
  const normalized = normalizeStatus(status);
  if (normalized === "completed") return "Complete";
  return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : "Unknown";
}

function statusHref(session: UserSessionSummary) {
  const normalized = normalizeStatus(session.status);
  if (normalized === "queued" || normalized === "processing") {
    return `/analyzing?jobId=${encodeURIComponent(session.job_id)}`;
  }
  return `/results/${session.job_id}`;
}

function formatUsd(value?: number | null) {
  if (value === null || value === undefined) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value > 0 && value < 0.01 ? 4 : 2,
    maximumFractionDigits: value > 0 && value < 0.01 ? 4 : 2,
  }).format(value);
}

export default function AccountPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [user, setUser] = useState<UserIdentity | null>(null);
  const [authSession, setAuthSession] = useState<AuthPayload | null>(null);
  const [sessions, setSessions] = useState<UserSessionSummary[]>([]);
  const [usage, setUsage] = useState<UsageLedgerPayload | null>(null);
  const [costPolicy, setCostPolicy] = useState<CostPolicy | null>(null);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus | null>(null);
  const [usageError, setUsageError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    try {
      const auth = getStoredAuth();
      if (auth?.user) {
        setAuthSession(auth);
        setUser(auth.user);
        setName(auth.user.display_name);
        setEmail(auth.user.email || "");
        loadSessions(auth.user.id, auth.session_token);
        return;
      }

      const stored = localStorage.getItem("aurafit:user");
      if (!stored) return;
      const storedUser = JSON.parse(stored) as UserIdentity;
      setUser(storedUser);
      setName(storedUser.display_name);
      setEmail(storedUser.email || "");
      loadSessions(storedUser.id);
    } catch {
      // Ignore bad local identity data.
    }
  }, []);

  useEffect(() => {
    Promise.allSettled([getCostPolicy(), getCatalogStatus()]).then(([policy, catalog]) => {
      if (policy.status === "fulfilled") setCostPolicy(policy.value);
      if (catalog.status === "fulfilled") setCatalogStatus(catalog.value);
    });
  }, []);

  async function loadSessions(userId: string, sessionToken?: string | null) {
    setLoading(true);
    setError("");
    setUsageError("");
    try {
      const data = await getUserSessions(userId);
      setUser(data.user);
      setSessions(data.sessions);
      if (sessionToken) {
        try {
          const userUsage = await getUserUsage(userId, sessionToken);
          setUsage(userUsage);
        } catch {
          setUsage(null);
          setUsageError("Usage summary is unavailable for this account right now.");
        }
      } else {
        setUsage(null);
      }
    } catch {
      setError("Could not load saved profiles.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestOtp() {
    if (!email.trim()) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response = await requestOtp(email.trim(), name.trim());
      setOtpRequested(true);
      setMessage(response.dev_otp ? `Dev OTP: ${response.dev_otp}` : "OTP sent. Check your email.");
    } catch (error) {
      setError(apiErrorMessage(error, "Could not send OTP. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp() {
    if (!email.trim() || !otpCode.trim()) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const auth = await verifyOtp(email.trim(), otpCode.trim(), name.trim());
      storeAuth(auth);
      setAuthSession(auth);
      setUser(auth.user);
      setName(auth.user.display_name);
      setEmail(auth.user.email || "");
      setMessage("Signed in with verified email.");
      await loadSessions(auth.user.id, auth.session_token);
    } catch (error) {
      setError(apiErrorMessage(error, "OTP verification failed. Please try again."));
      setLoading(false);
    }
  }

  const completeCount = sessions.filter((session) => {
    const normalized = normalizeStatus(session.status);
    return normalized === "complete" || normalized === "completed";
  }).length;
  const activeCount = sessions.filter((session) => {
    const normalized = normalizeStatus(session.status);
    return normalized === "queued" || normalized === "processing";
  }).length;
  const failedCount = sessions.filter((session) => normalizeStatus(session.status) === "failed").length;
  const displayedCost = usage?.total_actual_cost_usd ?? usage?.total_estimated_cost_usd ?? 0;

  return (
    <>
      <Navbar />
      <main className="min-h-screen pt-32 pb-24 px-6 md:px-12 max-w-5xl mx-auto">
        <header className="mb-12">
          <span className="font-label text-xs uppercase tracking-widest text-primary mb-3 block">Personal ID</span>
          <h1 className="font-headline text-5xl md:text-6xl mb-4">Your Saved Profiles</h1>
          <p className="font-body text-on-surface-variant max-w-2xl">
            Sign in with a 6-digit email OTP to recover saved analyses from Instagram, mobile, or desktop.
          </p>
        </header>

        <section className="bg-surface-container-low rounded-xl p-6 md:p-8 editorial-shadow mb-10">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-4 items-end">
            <label className="space-y-2">
              <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">Name Optional</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Aviral"
                className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
              />
            </label>
            <label className="space-y-2">
              <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">Email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                inputMode="email"
                className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
              />
            </label>
            <button
              onClick={handleRequestOtp}
              disabled={loading || !email.trim()}
              className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs disabled:opacity-40"
            >
              {loading && !otpRequested ? "Sending..." : "Send OTP"}
            </button>
          </div>
          {otpRequested && (
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 items-end mt-4">
              <label className="space-y-2">
                <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">6-Digit OTP</span>
                <input
                  value={otpCode}
                  onChange={(event) => setOtpCode(event.target.value)}
                  placeholder="123456"
                  inputMode="numeric"
                  maxLength={6}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                />
              </label>
              <button
                onClick={handleVerifyOtp}
                disabled={loading || !otpCode.trim()}
                className="bg-surface-container-highest text-on-surface px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs disabled:opacity-40"
              >
                {loading ? "Verifying..." : "Verify"}
              </button>
            </div>
          )}
          {user && (
            <p className="font-label text-[10px] uppercase tracking-widest text-primary mt-5">
              Active ID: {user.display_name} · @{user.username} · {authSession?.session_token ? "Verified" : "Legacy"}
            </p>
          )}
          {message && <p className="font-label text-[10px] uppercase tracking-widest text-primary mt-5">{message}</p>}
          {error && <p className="text-error font-label text-xs uppercase tracking-widest mt-5">{error}</p>}
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-10">
          <div className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/30">
            <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-3">Production Guards</span>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Email OTP</p>
                <p className="font-headline text-xl mt-2">
                  {costPolicy?.email_delivery_configured ? "Ready" : "Setup Needed"}
                </p>
              </div>
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Dev OTP</p>
                <p className="font-headline text-xl mt-2">
                  {costPolicy?.dev_otp_enabled ? "On" : "Off"}
                </p>
              </div>
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Analysis Cap</p>
                <p className="font-headline text-xl mt-2">{costPolicy?.analysis_limit_per_user_per_day ?? 0}/day</p>
              </div>
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">AI Credit Cap</p>
                <p className="font-headline text-xl mt-2">${Number(costPolicy?.max_daily_ai_cost_per_user_usd || 0).toFixed(2)}</p>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/30">
            <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-3">Marketplace Catalog</span>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Seed Products</p>
                <p className="font-headline text-xl mt-2">{catalogStatus?.seed_products ?? 0}</p>
              </div>
              <div className="bg-surface-container-lowest rounded-lg p-4">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Imported</p>
                <p className="font-headline text-xl mt-2">{catalogStatus?.cached_products ?? 0}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(catalogStatus?.providers || {}).map(([provider, configured]) => (
                <span
                  key={provider}
                  className={`px-3 py-1 rounded-full font-label text-[9px] uppercase tracking-widest ${
                    configured ? "bg-primary-fixed/40 text-primary" : "bg-surface-container-lowest text-on-surface-variant"
                  }`}
                >
                  {provider} {configured ? "ready" : "manual feed"}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          {loading && <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant">Loading saved profiles...</p>}
          {!loading && user && sessions.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="bg-surface-container-low rounded-xl p-5">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Profiles</p>
                <p className="font-headline text-3xl mt-2">{sessions.length}</p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-5">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Complete</p>
                <p className="font-headline text-3xl mt-2">{completeCount}</p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-5">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">In Flight</p>
                <p className="font-headline text-3xl mt-2">{activeCount}</p>
              </div>
              <div className="bg-surface-container-low rounded-xl p-5">
                <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant">Usage</p>
                <p className="font-headline text-3xl mt-2">{authSession?.session_token ? formatUsd(displayedCost) : "Sign in"}</p>
                {authSession?.session_token && (
                  <p className="font-body text-xs text-on-surface-variant mt-1">
                    {usage?.total_tokens?.toLocaleString() || 0} tokens · {usage?.entries.length || 0} events
                  </p>
                )}
              </div>
            </div>
          )}
          {usageError && (
            <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">{usageError}</p>
          )}
          {!loading && failedCount > 0 && (
            <p className="font-label text-[10px] uppercase tracking-widest text-error">
              {failedCount} profile{failedCount === 1 ? "" : "s"} need attention.
            </p>
          )}
          {!loading && user && sessions.length === 0 && (
            <div className="bg-surface-container-low rounded-xl p-8">
              <p className="font-body text-on-surface-variant mb-5">No saved profiles yet.</p>
              <Link href="/upload" className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs">
                Create Analysis
              </Link>
            </div>
          )}
          {sessions.map((session) => (
            <Link
              key={session.job_id}
              href={statusHref(session)}
              className="block bg-surface-container-low rounded-xl p-6 hover:bg-surface-container-high transition-colors"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="font-headline text-2xl">{session.profile_name || "Untitled Profile"}</h2>
                    <span
                      className={`border px-3 py-1 rounded-full font-label text-[9px] uppercase tracking-widest ${
                        statusStyles[normalizeStatus(session.status)] || "bg-surface-container-lowest text-on-surface-variant border-outline-variant"
                      }`}
                    >
                      {statusLabel(session.status)}
                    </span>
                  </div>
                  <p className="font-body text-sm text-on-surface-variant mt-1">
                    {session.skin_label || "Style profile"} · {session.color_season?.replace(/_/g, " ") || "season pending"}
                  </p>
                  {session.created_at && (
                    <p className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant mt-2">
                      Created {new Date(session.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {session.style_vibes.slice(0, 3).map((vibe) => (
                    <span key={vibe} className="px-3 py-1 rounded-full bg-surface-container-lowest font-label text-[9px] uppercase tracking-widest">
                      {vibe}
                    </span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </section>
      </main>
      <Footer />
    </>
  );
}
