"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  apiErrorMessage,
  AuthPayload,
  claimSession,
  createSessionVisualAnalysis,
  FitProfile,
  getApiAssetUrl,
  getJobUsage,
  getProductRecommendations,
  getProfile,
  getStoredAuth,
  OutfitRecommendation,
  ProductMatch,
  requestOtp,
  storeAuth,
  StyleProfile,
  UserIdentity,
  UsageLedgerPayload,
  verifyOtp,
  VisualAnalysisKind,
  VisualAnalysisResult,
} from "@/lib/api";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const categoryLabels: Record<string, string> = {
  western: "Western Wear",
  indian: "Indian Wear",
  fusion: "Fusion Wear",
  accessories: "Accessories",
  footwear: "Footwear",
  grooming: "Grooming",
  general: "General",
};

export default function ResultsPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = React.use(params);
  const [profile, setProfile] = useState<StyleProfile | null>(null);
  const [fitProfile, setFitProfile] = useState<FitProfile | null>(null);
  const [recommendations, setRecommendations] = useState<Record<string, OutfitRecommendation[]>>({});
  const [productMatches, setProductMatches] = useState<ProductMatch[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [visualAnalysis, setVisualAnalysis] = useState<VisualAnalysisResult | null>(null);
  const [visualKind, setVisualKind] = useState<VisualAnalysisKind>("color_palette");
  const [visualLoading, setVisualLoading] = useState(false);
  const [usage, setUsage] = useState<UsageLedgerPayload | null>(null);
  const [owner, setOwner] = useState<UserIdentity | null>(null);
  const [authSession, setAuthSession] = useState<AuthPayload | null>(null);
  const [profileName, setProfileName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [claiming, setClaiming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    let hydratedFromStorage = false;

    try {
      const stored = sessionStorage.getItem(`aurafit:${jobId}`);
      if (stored) {
        const parsed = JSON.parse(stored) as {
          profile?: StyleProfile;
          fitProfile?: FitProfile | null;
          recommendations?: Record<string, OutfitRecommendation[]>;
          visualAnalysis?: VisualAnalysisResult | null;
          preferredVisualAnalysisKind?: VisualAnalysisKind | null;
          user?: UserIdentity | null;
          profileName?: string | null;
        };

        if (parsed.profile) {
          setProfile(parsed.profile);
          setFitProfile(parsed.fitProfile || null);
          setRecommendations(parsed.recommendations || {});
          setVisualAnalysis(parsed.visualAnalysis || null);
          if (parsed.preferredVisualAnalysisKind) {
            setVisualKind(parsed.preferredVisualAnalysisKind);
          }
          setOwner(parsed.user || null);
          setProfileName(parsed.profileName || parsed.user?.display_name || "");
          if (parsed.user) {
            localStorage.setItem("aurafit:user", JSON.stringify(parsed.user));
          }
          setLoading(false);
          hydratedFromStorage = true;
        }
      }
    } catch {
      // Ignore bad or unavailable session storage and fall back to the API.
    }

    async function poll() {
      try {
        const data = await getProfile(jobId);
        if (cancelled) return;

        if (data.status === "complete" && data.profile) {
          setProfile(data.profile);
          setFitProfile(data.fit_profile || null);
          setRecommendations(data.recommendations || {});
          setOwner(data.user || null);
          setProfileName((current) => data.profile_name || data.user?.display_name || current);
          if (data.user) {
            localStorage.setItem("aurafit:user", JSON.stringify(data.user));
          }
          setLoading(false);

          try {
            const stored = sessionStorage.getItem(`aurafit:${jobId}`);
            const parsed = stored ? JSON.parse(stored) : {};
            sessionStorage.setItem(
              `aurafit:${jobId}`,
              JSON.stringify({
                ...parsed,
                profile: data.profile,
                fitProfile: data.fit_profile || null,
                recommendations: data.recommendations || {},
                user: data.user || null,
                profileName: data.profile_name || data.user?.display_name || null,
              })
            );
          } catch {
            // Session storage is an optimization only; the backend remains source of truth.
          }
        } else if (data.status === "processing") {
          attempts++;
          if (attempts < 60) {
            setTimeout(poll, 2000);
          } else if (!hydratedFromStorage) {
            setError("Analysis is taking longer than expected. Please try again.");
            setLoading(false);
          }
        }
      } catch {
        if (!cancelled && !hydratedFromStorage) {
          setError("Failed to load results. Please try again.");
          setLoading(false);
        }
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [jobId]);

  useEffect(() => {
    try {
      const auth = getStoredAuth();
      if (auth?.user) {
        setAuthSession(auth);
        setAuthEmail(auth.user.email || "");
        if (!profileName) setProfileName(auth.user.display_name || "");
        return;
      }

      if (owner || profileName) return;
      const stored = localStorage.getItem("aurafit:user");
      if (!stored) return;
      const user = JSON.parse(stored) as UserIdentity;
      setProfileName(user.display_name || "");
    } catch {
      // Ignore bad local identity data.
    }
  }, [owner, profileName]);

  useEffect(() => {
    if (!profile) return;

    let cancelled = false;
    setProductsLoading(true);

    getProductRecommendations(jobId)
      .then((data) => {
        if (cancelled) return;
        setProductMatches(data.products);
        setFitProfile(data.fit_profile);
      })
      .catch(() => {
        if (!cancelled) setProductMatches([]);
      })
      .finally(() => {
        if (!cancelled) setProductsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [jobId, profile]);

  useEffect(() => {
    if (!authSession?.session_token) return;
    getJobUsage(jobId, authSession.session_token)
      .then(setUsage)
      .catch(() => setUsage(null));
  }, [authSession, jobId, visualAnalysis]);

  const tabs = [
    { key: "overview", label: "Overview" },
    ...Object.keys(recommendations).map((key) => ({
      key,
      label: categoryLabels[key] || key,
    })),
  ];

  async function claimWithAuth(auth: AuthPayload) {
    const name = profileName.trim() || auth.user.display_name;
    setClaiming(true);
    setAuthMessage("");
    try {
      const claimed = await claimSession(jobId, auth.user.id, name, auth.session_token);
      setOwner(claimed.user);
      setProfileName(claimed.profile_name);
      setAuthSession(auth);
      storeAuth(auth);
      setAuthMessage("Saved to your AuraFit ID.");
    } catch (error) {
      setAuthMessage(apiErrorMessage(error, "Could not save this profile. Please try again."));
    } finally {
      setClaiming(false);
    }
  }

  async function requestSaveOtp() {
    if (!authEmail.trim()) return;
    setClaiming(true);
    setAuthMessage("");
    try {
      const response = await requestOtp(authEmail.trim(), profileName.trim());
      setOtpRequested(true);
      setAuthMessage(
        response.dev_otp
          ? `Dev OTP: ${response.dev_otp}`
          : "OTP sent. Check your email."
      );
    } catch (error) {
      setAuthMessage(apiErrorMessage(error, "Could not send OTP. Please check your email and try again."));
    } finally {
      setClaiming(false);
    }
  }

  async function verifyOtpAndSave() {
    if (!authEmail.trim() || !otpCode.trim()) return;
    setClaiming(true);
    setAuthMessage("");
    try {
      const auth = await verifyOtp(authEmail.trim(), otpCode.trim(), profileName.trim());
      storeAuth(auth);
      await claimWithAuth(auth);
    } catch (error) {
      setAuthMessage(apiErrorMessage(error, "OTP verification failed. Please try again."));
      setClaiming(false);
    }
  }

  async function generateVisualBoard() {
    if (!authSession?.session_token) {
      setAuthMessage("Save with OTP before generating the premium visual board.");
      return;
    }
    setVisualLoading(true);
    setAuthMessage("");
    try {
      const result = await createSessionVisualAnalysis(jobId, visualKind, authSession.session_token);
      setVisualAnalysis(result);
      try {
        const stored = sessionStorage.getItem(`aurafit:${jobId}`);
        const parsed = stored ? JSON.parse(stored) : {};
        sessionStorage.setItem(
          `aurafit:${jobId}`,
          JSON.stringify({
            ...parsed,
            visualAnalysis: result,
            preferredVisualAnalysisKind: visualKind,
          })
        );
      } catch {
        // Ignore storage issues; the generated image is still available via API.
      }
    } catch (error) {
      setAuthMessage(apiErrorMessage(error, "Could not generate the visual board. Please try again."));
    } finally {
      setVisualLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#0D0D0D]">
        <div className="aura-pulse bg-primary/20 p-6 rounded-full inline-block mb-8">
          <h1 className="text-4xl font-headline italic tracking-tighter text-primary-fixed-dim">AuraFit</h1>
        </div>
        <div className="relative w-48 h-48 mb-12 flex items-center justify-center">
          <div className="absolute inset-0 scanner-ring animate-[spin_3s_linear_infinite]"></div>
          <div className="absolute inset-4 scanner-ring animate-[spin_5s_linear_infinite_reverse] opacity-50"></div>
          <span className="material-symbols-outlined text-primary text-4xl">auto_awesome</span>
        </div>
        <h2 className="text-3xl font-headline text-surface-container-lowest mb-4">Reading your aura...</h2>
        <p className="font-label text-[10px] tracking-widest text-tertiary uppercase">This takes about 20 seconds</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <span className="material-symbols-outlined text-6xl text-error mb-4">error</span>
        <h2 className="font-headline text-2xl mb-4">{error || "Something went wrong"}</h2>
        <Link href="/upload" className="bg-primary text-on-primary px-8 py-3 rounded-lg font-label uppercase tracking-widest text-xs">
          Try Again
        </Link>
      </div>
    );
  }

  return (
    <>
      <Navbar />

      <main className="pt-32 pb-24 px-6 md:px-12 max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-20 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="font-headline text-5xl md:text-7xl mb-4 tracking-tight">Your Style <span className="italic">Manifesto</span></h1>
            <p className="font-body text-on-surface-variant max-w-2xl leading-relaxed">A curated collection of recommendations tailored to your unique silhouette, seasonal palette, and aesthetic leanings.</p>
            <div className="mt-6 max-w-3xl">
              {owner ? (
                <div className="bg-primary-fixed/30 border border-primary/20 px-4 py-3 rounded-xl inline-block">
                  <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-1">Saved Profile</span>
                  <span className="font-body text-sm text-on-surface">
                    {profileName || owner.display_name} · @{owner.username}
                  </span>
                </div>
              ) : authSession?.session_token ? (
                <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 bg-surface-container-low rounded-xl p-4 border border-outline-variant/30">
                  <input
                    value={profileName}
                    onChange={(event) => setProfileName(event.target.value)}
                    placeholder={authSession.user.display_name || "Profile name"}
                    className="bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                  />
                  <button
                    onClick={() => claimWithAuth(authSession)}
                    disabled={claiming}
                    className="bg-primary text-on-primary px-5 py-3 rounded-lg font-label uppercase tracking-widest text-[10px] disabled:opacity-40"
                  >
                    {claiming ? "Saving..." : "Save to My ID"}
                  </button>
                </div>
              ) : (
                <div className="bg-surface-container-low rounded-xl p-4 border border-outline-variant/30 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      value={profileName}
                      onChange={(event) => setProfileName(event.target.value)}
                      placeholder="Profile name"
                      className="bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    />
                    <input
                      value={authEmail}
                      onChange={(event) => setAuthEmail(event.target.value)}
                      placeholder="Email for OTP"
                      inputMode="email"
                      className="bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    />
                  </div>
                  {otpRequested && (
                    <input
                      value={otpCode}
                      onChange={(event) => setOtpCode(event.target.value)}
                      placeholder="6-digit OTP"
                      inputMode="numeric"
                      maxLength={6}
                      className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    />
                  )}
                  <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                    <button
                      onClick={otpRequested ? verifyOtpAndSave : requestSaveOtp}
                      disabled={claiming || !authEmail.trim() || (otpRequested && !otpCode.trim())}
                      className="bg-primary text-on-primary px-5 py-3 rounded-lg font-label uppercase tracking-widest text-[10px] disabled:opacity-40"
                    >
                      {claiming ? "Working..." : otpRequested ? "Verify & Save" : "Send OTP"}
                    </button>
                    <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">
                      Guest result first. OTP only when saving.
                    </span>
                  </div>
                </div>
              )}
              {authMessage && (
                <p className="mt-3 font-label text-[10px] uppercase tracking-widest text-primary">
                  {authMessage}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={async () => {
              try {
                const response = await api.get(`/report/${jobId}`, { responseType: "blob" });
                const url = URL.createObjectURL(response.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = `aurafit-style-report.pdf`;
                a.click();
                URL.revokeObjectURL(url);
              } catch {
                alert("Failed to generate report. Please try again.");
              }
            }}
            className="flex items-center gap-3 bg-primary text-on-primary px-8 py-4 rounded-lg font-label uppercase tracking-widest text-xs hover:opacity-90 transition-opacity active:scale-95 shrink-0"
          >
            <span className="material-symbols-outlined text-lg">download</span>
            Download Style Guide
          </button>
        </header>

        {/* Tab Navigation */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-12 border-b border-outline-variant/30">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-6 py-3 font-label text-xs uppercase tracking-widest whitespace-nowrap transition-colors rounded-t-lg ${
                activeTab === tab.key
                  ? "border-b-2 border-primary text-primary bg-primary-fixed/20"
                  : "text-outline hover:text-primary"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <>
            {visualAnalysis && (
              <section className="mb-20 bg-surface-container-low rounded-xl overflow-hidden editorial-shadow">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 md:p-8 border-b border-outline-variant/30">
                  <div>
                    <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">
                      Generated Visual Analysis
                    </span>
                    <h2 className="font-headline text-3xl capitalize">
                      {visualAnalysis.kind.replace(/_/g, " ")}
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {visualAnalysis.process.map((step) => (
                      <span key={step} className="px-3 py-1 bg-surface-container-highest rounded-full font-label text-[9px] uppercase tracking-wider text-on-surface-variant">
                        {step}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="bg-[#f4f0ea] p-3 md:p-6">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    className="w-full rounded-lg border border-outline-variant/30"
                    alt={`${visualAnalysis.kind.replace(/_/g, " ")} visual analysis`}
                    src={getApiAssetUrl(visualAnalysis.image_url)}
                  />
                </div>
              </section>
            )}
            {!visualAnalysis && (
              <section className="mb-20 bg-surface-container-low rounded-xl p-6 md:p-8 border border-outline-variant/30 editorial-shadow">
                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
                  <div>
                    <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">
                      Premium Visual Board
                    </span>
                    <h2 className="font-headline text-3xl mb-3">Generate after save</h2>
                    <p className="font-body text-sm text-on-surface-variant max-w-2xl leading-relaxed">
                      To keep credits under control for Instagram traffic, we only run image generation after this result is saved to a verified email ID.
                    </p>
                    {usage && (
                      <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant mt-3">
                        Usage: {usage.total_tokens.toLocaleString()} tokens · $
                        {Number(usage.total_actual_cost_usd ?? usage.total_estimated_cost_usd ?? 0).toFixed(4)}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <select
                      value={visualKind}
                      onChange={(event) => setVisualKind(event.target.value as VisualAnalysisKind)}
                      className="bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    >
                      <option value="color_palette">Color Palette</option>
                      <option value="hairstyles">Hairstyles</option>
                      <option value="look_audit">Look Audit</option>
                    </select>
                    <button
                      onClick={generateVisualBoard}
                      disabled={visualLoading || !owner || !authSession?.session_token}
                      className="bg-primary text-on-primary px-5 py-3 rounded-lg font-label uppercase tracking-widest text-[10px] disabled:opacity-40"
                    >
                      {visualLoading ? "Generating..." : owner ? "Generate Board" : "Save First"}
                    </button>
                  </div>
                </div>
              </section>
            )}

            {/* Style Profile Card */}
            <section className="grid grid-cols-1 md:grid-cols-12 mb-20 bg-surface-container-low rounded-xl overflow-hidden editorial-shadow">
              <div className="md:col-span-5 relative h-64 md:h-auto overflow-hidden bg-gradient-to-br from-primary/10 to-tertiary/10">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="bg-surface-container-lowest/40 backdrop-blur-xl p-8 rounded-full border border-white/20">
                    <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface">Curated Identity</span>
                  </div>
                </div>
              </div>

              <div className="md:col-span-7 p-8 md:p-16 flex flex-col justify-center">
                <div className="flex justify-between items-start mb-10">
                  <div>
                    <span className="font-label text-xs uppercase tracking-widest text-primary mb-2 block">Personal Analysis</span>
                    <h2 className="font-headline text-4xl">Your Style Profile</h2>
                  </div>
                  <div className="bg-surface-container-highest px-3 py-1.5 rounded-full flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px] text-primary">auto_awesome</span>
                    <span className="font-label text-[10px] font-bold uppercase tracking-tighter">
                      {Math.round((profile.confidence_score || 0.85) * 100)}% Confidence
                    </span>
                  </div>
                </div>

                <div className="space-y-10">
                  {/* Skin Tone & Body & Face */}
                  <div className="flex flex-wrap gap-12">
                    <div>
                      <span className="font-label text-[10px] uppercase tracking-widest text-outline mb-3 block">Skin Tone</span>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full ring-2 ring-offset-2 ring-outline-variant" style={{ backgroundColor: profile.skin_tone.hex_color }}></div>
                        <span className="font-body text-sm font-medium">{profile.skin_tone.label} · Fitzpatrick {profile.skin_tone.fitzpatrick}</span>
                      </div>
                    </div>
                    <div>
                      <span className="font-label text-[10px] uppercase tracking-widest text-outline mb-3 block">Body Architecture</span>
                      <span className="font-body text-sm font-medium capitalize">{profile.body_type.shape} · {profile.body_type.build} · {profile.body_type.height_category}</span>
                    </div>
                    {profile.face_shape && (
                      <div>
                        <span className="font-label text-[10px] uppercase tracking-widest text-outline mb-3 block">Face Shape</span>
                        <span className="font-body text-sm font-medium capitalize">{profile.face_shape}</span>
                      </div>
                    )}
                    {profile.color_season && (
                      <div>
                        <span className="font-label text-[10px] uppercase tracking-widest text-outline mb-3 block">Color Season</span>
                        <span className="font-body text-sm font-medium capitalize">{profile.color_season.replace(/_/g, " ")}</span>
                      </div>
                    )}
                  </div>

                  {/* Palette */}
                  <div>
                    <span className="font-label text-[10px] uppercase tracking-widest text-outline mb-4 block">Recommended Color Palette</span>
                    <div className="flex flex-wrap gap-4">
                      {profile.color_palette.map((c) => (
                        <div key={c.name} className="flex flex-col items-center gap-2">
                          <div className="w-12 h-12 rounded-full editorial-shadow" style={{ backgroundColor: c.hex }} title={c.name}></div>
                          <span className="font-label text-[9px] uppercase tracking-wider text-on-surface-variant">{c.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Vibe Pills */}
                  <div className="flex flex-wrap gap-3">
                    {profile.style_vibes.map((vibe) => (
                      <span key={vibe} className="px-5 py-2 bg-surface-container-highest rounded-full font-label text-xs uppercase tracking-widest">{vibe}</span>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            <section className="mb-20">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
                <div>
                  <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">
                    Marketplace Matches
                  </span>
                  <h2 className="font-headline text-4xl">Buyable Product Picks</h2>
                </div>
                {fitProfile && (
                  <div className="flex flex-wrap gap-2">
                    {[
                      fitProfile.shirt_size && `Top ${fitProfile.shirt_size}`,
                      fitProfile.bottom_size && `Bottom ${fitProfile.bottom_size}`,
                      fitProfile.shoe_size && `Shoe ${fitProfile.shoe_size}`,
                      fitProfile.preferred_fit && `${fitProfile.preferred_fit} fit`,
                    ].filter(Boolean).map((label) => (
                      <span key={label} className="px-3 py-1 bg-surface-container-low rounded-full font-label text-[9px] uppercase tracking-wider text-on-surface-variant">
                        {label}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {productsLoading && (
                <div className="bg-surface-container-low rounded-xl p-8 font-label text-xs uppercase tracking-widest text-on-surface-variant">
                  Finding size-aware product matches...
                </div>
              )}

              {!productsLoading && productMatches.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {productMatches.map((match) => (
                    <article key={match.product.id} className="bg-surface-container-lowest rounded-xl overflow-hidden editorial-shadow flex flex-col">
                      <div className="relative aspect-[4/5] bg-surface-container-high overflow-hidden">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          className="w-full h-full object-cover"
                          alt={match.product.title}
                          src={match.product.image_url}
                        />
                        <div className="absolute top-3 left-3 bg-surface-container-lowest/90 backdrop-blur px-3 py-1 rounded-full">
                          <span className="font-label text-[9px] uppercase tracking-widest text-primary">
                            {match.score}% match
                          </span>
                        </div>
                      </div>
                      <div className="p-5 flex flex-col flex-1">
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div>
                            <p className="font-label text-[9px] uppercase tracking-widest text-outline mb-1">
                              {match.product.marketplace} · {match.product.brand}
                            </p>
                            <h3 className="font-headline text-xl leading-tight">{match.product.title}</h3>
                          </div>
                          <span className="font-headline text-lg italic text-primary shrink-0">
                            ₹{Math.round(match.product.price_inr).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div className="space-y-2 mb-4 flex-1">
                          {match.reasons.slice(0, 3).map((reason) => (
                            <p key={reason} className="font-body text-xs text-on-surface-variant leading-relaxed">
                              {reason}
                            </p>
                          ))}
                          {match.warnings.slice(0, 1).map((warning) => (
                            <p key={warning} className="font-label text-[9px] uppercase tracking-wider text-error">
                              {warning}
                            </p>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-1.5 mb-4">
                          {match.product.available_sizes.slice(0, 5).map((size) => (
                            <span key={size} className="px-2 py-1 rounded bg-surface-container-high font-label text-[9px] uppercase text-on-surface-variant">
                              {size}
                            </span>
                          ))}
                        </div>
                        <a
                          href={match.product.affiliate_url || match.product.product_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-primary text-on-primary text-center px-4 py-3 rounded-lg font-label text-[10px] uppercase tracking-widest hover:opacity-90 transition-opacity"
                        >
                          View Product
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              {!productsLoading && productMatches.length === 0 && (
                <div className="bg-surface-container-low rounded-xl p-8 font-body text-sm text-on-surface-variant">
                  Product matches will appear here once the catalog service has matches for this profile.
                </div>
              )}
            </section>

            {/* Wardrobe Tips */}
            <section className="mb-12">
              <h2 className="font-headline text-4xl mb-12 text-center">Wardrobe Intelligence</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {profile.wardrobe_tips.map((tip, i) => {
                  const icons = ["anchor", "architecture", "layers", "palette"];
                  const bgClasses = [
                    "bg-secondary-container text-on-secondary-container",
                    "bg-primary-container text-on-primary-container",
                    "bg-tertiary-container text-on-tertiary-container",
                    "bg-secondary-container text-on-secondary-container",
                  ];
                  return (
                    <div key={i} className="bg-surface-container-lowest p-10 rounded-xl editorial-shadow group hover:-translate-y-2 transition-transform duration-300">
                      <div className={`w-14 h-14 ${bgClasses[i % 4]} rounded-full flex items-center justify-center mb-6`}>
                        <span className="material-symbols-outlined text-3xl">{icons[i % 4]}</span>
                      </div>
                      <p className="font-body text-sm text-on-surface-variant leading-relaxed">{tip}</p>
                    </div>
                  );
                })}
              </div>
            </section>
          </>
        )}

        {/* Category Tabs */}
        {activeTab !== "overview" && recommendations[activeTab] && (
          <section>
            <div className="flex items-end justify-between gap-6 mb-12">
              <div>
                <h2 className="font-headline text-4xl mb-2">{categoryLabels[activeTab] || activeTab}</h2>
                <p className="font-body text-on-surface-variant">{recommendations[activeTab].length} curated recommendations for your profile.</p>
              </div>
            </div>

            <div className="masonry-grid gap-12">
              {recommendations[activeTab].map((rec) => (
                <div key={rec.id} className="masonry-item flex flex-col group">
                  {/* Image */}
                  {rec.image_url && (
                    <div className="relative mb-6 overflow-hidden rounded-lg aspect-[3/4]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                        alt={rec.name}
                        src={rec.image_url}
                      />
                      {/* Source badge */}
                      <div className="absolute top-4 left-4">
                        <div className="bg-primary/90 text-on-primary px-3 py-1.5 rounded-full flex items-center gap-2 backdrop-blur-sm">
                          <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>
                            {rec.source === "rule" ? "verified" : rec.source === "hybrid" ? "auto_fix_high" : "auto_awesome"}
                          </span>
                          <span className="font-label text-[10px] font-bold uppercase tracking-widest">
                            {rec.source === "rule" ? "Expert Rule" : rec.source === "hybrid" ? "Hybrid" : "AI Styled"}
                          </span>
                        </div>
                      </div>
                      <button className="absolute bottom-4 right-4 bg-surface-container-lowest/80 backdrop-blur-md p-3 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <span className="material-symbols-outlined text-primary">favorite</span>
                      </button>
                    </div>
                  )}

                  {/* Content */}
                  <div>
                    <h3 className="font-headline text-2xl mb-2 italic">{rec.name}</h3>
                    <p className="font-body text-sm text-on-surface-variant mb-4">{rec.description}</p>

                    {/* Why it works */}
                    <div className="bg-primary-fixed/20 border border-primary/10 rounded-lg p-4 mb-6">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="material-symbols-outlined text-primary text-sm">lightbulb</span>
                        <span className="font-label text-[10px] uppercase tracking-widest text-primary font-bold">Why this works</span>
                      </div>
                      <p className="font-body text-xs text-on-surface-variant leading-relaxed">{rec.why_it_works}</p>
                    </div>

                    {/* Items */}
                    {rec.items.length > 0 && (
                      <ul className="space-y-3 mb-6">
                        {rec.items.map((item, idx) => (
                          <li key={idx} className="flex justify-between items-center text-sm border-b border-outline-variant/30 pb-2">
                            <div>
                              <p className="font-medium">{item.name}</p>
                              <p className="text-[10px] font-label uppercase text-outline">{item.brand}</p>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="font-body">${item.price_usd.toFixed(0)}</span>
                              <a
                                href={item.buy_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="bg-surface-container-high px-3 py-1 rounded-sm text-[10px] font-label uppercase hover:bg-primary hover:text-on-primary transition-colors"
                              >
                                Buy &rarr;
                              </a>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {rec.style_tags.map((tag) => (
                        <span key={tag} className="px-3 py-1 bg-surface-container-highest rounded-full font-label text-[10px] uppercase tracking-wider">{tag}</span>
                      ))}
                    </div>

                    {/* Total + Actions */}
                    {rec.total_price_usd > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="font-headline text-lg italic text-primary">${rec.total_price_usd.toFixed(0)} total</span>
                        <div className="flex items-center gap-2">
                          <button className="w-10 h-10 flex items-center justify-center border border-outline-variant rounded-sm hover:bg-surface-container-low transition-colors">
                            <span className="material-symbols-outlined text-on-surface-variant text-lg">share</span>
                          </button>
                          <button className="w-10 h-10 flex items-center justify-center border border-outline-variant rounded-sm hover:bg-surface-container-low transition-colors">
                            <span className="material-symbols-outlined text-on-surface-variant text-lg">bookmark</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <Footer />
    </>
  );
}
