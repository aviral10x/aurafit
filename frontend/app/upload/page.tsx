"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  analyzePhotos,
  apiErrorMessage,
  AuthPayload,
  CostPolicy,
  getCostPolicy,
  getStoredAuth,
  requestOtp,
  storeAuth,
  UserIdentity,
  verifyOtp,
  VisualAnalysisKind,
} from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const styleArchetypes = [
  "Casual", "Streetwear", "Minimal", "Classic", "Formal",
  "Bohemian", "Sporty", "Bold", "Y2K", "Old Money",
  "Dark Academia", "Business Casual",
];

const occasions = [
  "Casual", "Office", "Wedding", "Party", "Date Night", "Travel", "Athleisure",
];

const goalOptions = [
  "Look Taller", "Look Slimmer", "Look Broader", "Look Professional", "Age Appropriate",
];

const ageRanges = ["18-25", "26-35", "36-45", "46-55", "55+"];
const apparelSizes = ["XS", "S", "M", "L", "XL", "XXL"];
const waistSizes = ["28", "30", "32", "34", "36", "38", "40"];
const shoeSizes = ["6", "7", "8", "9", "10", "11", "12"];
const fitOptions = ["slim", "regular", "relaxed", "oversized"];
const minPhotosRequired = 1;
const recommendedPhotos = 3;

const visualAnalysisOptions: { value: VisualAnalysisKind; label: string; description: string }[] = [
  {
    value: "color_palette",
    label: "Color Palette",
    description: "Seasonal palette, drapes, metals, hair, makeup",
  },
  {
    value: "hairstyles",
    label: "Hairstyles",
    description: "Face-framing cuts, parts, volume, grooming",
  },
  {
    value: "look_audit",
    label: "Look Audit",
    description: "Grooming, styling, consult-only cosmetic notes",
  },
];

const genderMap: Record<string, string> = {
  Masculine: "men",
  Feminine: "women",
  Neutral: "nonbinary",
};

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photos, setPhotos] = useState<{ file: File; url: string }[]>([]);
  const [gender, setGender] = useState("Masculine");
  const [selectedStyles, setSelectedStyles] = useState<string[]>(["Streetwear", "Classic", "Old Money"]);
  const [wearType, setWearType] = useState("all");
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([]);
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const [ageRange, setAgeRange] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [shirtSize, setShirtSize] = useState("");
  const [bottomSize, setBottomSize] = useState("");
  const [shoeSize, setShoeSize] = useState("");
  const [preferredFit, setPreferredFit] = useState("regular");
  const [pincode, setPincode] = useState("");
  const [visualAnalysisKind, setVisualAnalysisKind] = useState<VisualAnalysisKind>("color_palette");
  const [currentUser, setCurrentUser] = useState<UserIdentity | null>(null);
  const [authSession, setAuthSession] = useState<AuthPayload | null>(null);
  const [showAuthGate, setShowAuthGate] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [budgetMin] = useState(50);
  const [budgetMax] = useState(300);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);
  const [isAuthWorking, setIsAuthWorking] = useState(false);
  const [costPolicy, setCostPolicy] = useState<CostPolicy | null>(null);

  useEffect(() => {
    try {
      const auth = getStoredAuth();
      if (auth?.user) {
        setAuthSession(auth);
        setCurrentUser(auth.user);
        setProfileName(auth.user.display_name || "");
        setAuthEmail(auth.user.email || "");
        return;
      }
      const stored = localStorage.getItem("aurafit:user");
      if (stored) {
        const user = JSON.parse(stored) as UserIdentity;
        setCurrentUser(user);
        setProfileName(user.display_name || "");
        setAuthEmail(user.email || "");
      }
    } catch {
      // Ignore bad local identity data.
    }
  }, []);

  useEffect(() => {
    getCostPolicy()
      .then(setCostPolicy)
      .catch(() => setCostPolicy(null));
  }, []);

  function handleFiles(files: FileList | null) {
    if (!files) return;
    const newPhotos = Array.from(files).map((file) => ({
      file,
      url: URL.createObjectURL(file),
    }));
    setPhotos((prev) => [...prev, ...newPhotos].slice(0, 10));
  }

  function removePhoto(index: number) {
    setPhotos((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].url);
      updated.splice(index, 1);
      return updated;
    });
  }

  function toggleStyle(style: string) {
    setSelectedStyles((prev) =>
      prev.includes(style) ? prev.filter((s) => s !== style) : [...prev, style]
    );
  }

  function toggleOccasion(occ: string) {
    setSelectedOccasions((prev) =>
      prev.includes(occ) ? prev.filter((o) => o !== occ) : [...prev, occ]
    );
  }

  function toggleGoal(goal: string) {
    setSelectedGoals((prev) =>
      prev.includes(goal) ? prev.filter((g) => g !== goal) : [...prev, goal]
    );
  }

  const canSubmit = photos.length >= minPhotosRequired && !isSubmitting && !isAuthWorking;

  function optionalNumber(value: string) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
  }

  async function runAnalysis(auth: AuthPayload) {
    setIsSubmitting(true);
    setAuthMessage("");

    try {
      const result = await analyzePhotos(
        photos.map((p) => p.file),
        genderMap[gender] || "men",
        budgetMin,
        budgetMax,
        selectedStyles,
        wearType,
        selectedOccasions.map((o) => o.toLowerCase().replace(/\s+/g, "-")),
        selectedGoals.map((g) => g.toLowerCase().replace(/ /g, "-")),
        ageRange,
        {
          height_cm: optionalNumber(heightCm),
          weight_kg: optionalNumber(weightKg),
          shirt_size: shirtSize || undefined,
          bottom_size: bottomSize || undefined,
          shoe_size: shoeSize || undefined,
          preferred_fit: preferredFit || undefined,
          pincode: pincode || undefined,
        },
        {
          user_id: auth.user.id,
          profile_name: profileName.trim() || auth.user.display_name,
          session_token: auth.session_token,
        }
      );

      try {
        sessionStorage.setItem(
          `aurafit:${result.job_id}`,
          JSON.stringify({
            status: result.status || "queued",
            profile: result.profile,
            recommendations: result.recommendations,
            fitProfile: result.fit_profile,
            user: result.user || auth.user,
            profileName: result.profile_name || profileName.trim() || auth.user.display_name,
            preferredVisualAnalysisKind: visualAnalysisKind,
            visualAnalysis: null,
          })
        );
      } catch {
        // Ignore storage issues and fall back to API-based loading.
      }

      router.push(`/analyzing?jobId=${encodeURIComponent(result.job_id)}`);
    } catch (error) {
      setIsSubmitting(false);
      setIsAuthWorking(false);
      setAuthMessage(apiErrorMessage(error, "Something went wrong during analysis. Please try again."));
    }
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    if (authSession?.session_token) {
      await runAnalysis(authSession);
      return;
    }

    setShowAuthGate(true);
    setAuthMessage("Verify your email to start analysis and save your results.");
  }

  async function requestAnalyzeOtp() {
    if (!authEmail.trim()) return;
    setIsAuthWorking(true);
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
      setIsAuthWorking(false);
    }
  }

  async function verifyOtpAndAnalyze() {
    if (!authEmail.trim() || !otpCode.trim()) return;
    setIsAuthWorking(true);
    setAuthMessage("");
    try {
      const auth = await verifyOtp(authEmail.trim(), otpCode.trim(), profileName.trim());
      storeAuth(auth);
      setAuthSession(auth);
      setCurrentUser(auth.user);
      setProfileName(auth.user.display_name || profileName);
      setAuthEmail(auth.user.email || authEmail);
      setShowAuthGate(false);
      await runAnalysis(auth);
    } catch (error) {
      setAuthMessage(apiErrorMessage(error, "OTP verification failed. Please try again."));
      setIsAuthWorking(false);
    }
  }

  return (
    <>
      <Navbar />

      {/* Main Content */}
      <main className="flex-grow pt-32 pb-24 px-6 md:px-12 max-w-4xl mx-auto w-full">
        {/* Step Indicator */}
        <div className="flex justify-between items-center mb-16 px-4">
          <div className="flex flex-col items-center gap-2">
            <span className="font-label text-[10px] tracking-[0.2em] uppercase text-primary font-bold">Step 01</span>
            <span className="font-headline text-lg italic text-on-surface step-active">Upload Photos</span>
          </div>
          <div className="h-[1px] flex-grow mx-8 bg-outline-variant opacity-30"></div>
          <div className="flex flex-col items-center gap-2 opacity-40">
            <span className="font-label text-[10px] tracking-[0.2em] uppercase text-on-surface-variant">Step 02</span>
            <span className="font-headline text-lg italic text-on-surface-variant">Your Preferences</span>
          </div>
          <div className="h-[1px] flex-grow mx-8 bg-outline-variant opacity-30"></div>
          <div className="flex flex-col items-center gap-2 opacity-40">
            <span className="font-label text-[10px] tracking-[0.2em] uppercase text-on-surface-variant">Step 03</span>
            <span className="font-headline text-lg italic text-on-surface-variant">Get Results</span>
          </div>
        </div>

        {/* Headline */}
        <header className="text-center mb-12">
          <h1 className="font-headline text-5xl md:text-6xl mb-4 tracking-tight">Curate Your <span className="text-primary italic">Aura.</span></h1>
          <p className="font-body text-on-surface-variant max-w-xl mx-auto leading-relaxed">
            Our AI stylist analyzes your physical profile and personal taste to curate a bespoke wardrobe that feels uniquely yours.
          </p>
        </header>

        <section className="space-y-12">
          <div className="space-y-6">
            <div className="flex justify-between items-end">
              <div>
                <h2 className="font-label text-xs tracking-widest uppercase font-bold text-primary">00. Prep First</h2>
                <p className="font-body text-sm text-on-surface-variant mt-2">
                  Upload and customize first. We ask for email OTP only when you click Analyze.
                </p>
              </div>
              {currentUser && (
                <span className="font-label text-[10px] uppercase tracking-widest text-primary">
                  Active ID: {currentUser.display_name}
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-surface-container-low rounded-xl p-5 border border-outline-variant/30">
              <div>
                <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">Low Friction</span>
                <p className="font-body text-xs text-on-surface-variant leading-relaxed">No login wall before photo upload.</p>
              </div>
              <div>
                <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">Credit Safe</span>
                <p className="font-body text-xs text-on-surface-variant leading-relaxed">
                  AI starts after OTP · {costPolicy?.analysis_limit_per_user_per_day ?? 3}/day analysis cap
                </p>
              </div>
              <div>
                <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">Recoverable</span>
                <p className="font-body text-xs text-on-surface-variant leading-relaxed">We email your result link and attach it to your personal ID.</p>
              </div>
            </div>
            {costPolicy && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/30">
                <div>
                  <span className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant block mb-1">Email OTP</span>
                  <p className="font-body text-xs text-on-surface-variant">
                    {costPolicy.email_delivery_configured ? "Production email ready" : "Needs SMTP/Resend key"}
                  </p>
                </div>
                <div>
                  <span className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant block mb-1">Daily Credit Guard</span>
                  <p className="font-body text-xs text-on-surface-variant">
                    ${Number(costPolicy.max_daily_ai_cost_per_user_usd || 0).toFixed(2)} per verified user
                  </p>
                </div>
                <div>
                  <span className="font-label text-[9px] uppercase tracking-widest text-on-surface-variant block mb-1">Visual Boards</span>
                  <p className="font-body text-xs text-on-surface-variant">
                    {costPolicy.max_visual_generations_per_user_per_day || 0}/day after save
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Upload Section */}
          <div className="space-y-6">
            <div className="flex justify-between items-end">
              <h2 className="font-label text-xs tracking-widest uppercase font-bold text-primary">01. Visual Data</h2>
              <span className="font-label text-[10px] text-on-surface-variant">1 REQUIRED / 3+ RECOMMENDED</span>
            </div>

            {/* Drag & Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center group transition-all cursor-pointer ${
                isDragging
                  ? "border-primary bg-primary-fixed/20 scale-[1.01]"
                  : "border-primary/40 bg-surface-container-low hover:border-primary hover:bg-surface-container"
              }`}
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={(e) => { e.preventDefault(); dragCounter.current++; setIsDragging(true); }}
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={(e) => { e.preventDefault(); dragCounter.current--; if (dragCounter.current === 0) setIsDragging(false); }}
              onDrop={(e) => { e.preventDefault(); dragCounter.current = 0; setIsDragging(false); handleFiles(e.dataTransfer.files); }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
              />
              <div className="mb-4">
                <span className="material-symbols-outlined text-4xl text-primary opacity-60 group-hover:opacity-100 transition-opacity">add_a_photo</span>
              </div>
              <p className="font-headline text-xl mb-2 italic">Drop your photos here or <span className="underline decoration-primary/40 underline-offset-4">click to browse</span></p>
              <p className="text-xs text-on-surface-variant font-label tracking-wider max-w-xs mx-auto leading-relaxed">
                START WITH ONE CLEAR PORTRAIT. ADD SIDE AND FULL-BODY PHOTOS FOR BETTER FIT ANALYSIS.
              </p>
            </div>

            {/* Photo Grid Preview */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {photos.map((photo, i) => (
                <div key={i} className="aspect-square relative group overflow-hidden bg-surface-container-highest">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" alt={`Upload ${i + 1}`} src={photo.url} />
                  <button
                    onClick={() => removePhoto(i)}
                    className="absolute top-2 right-2 bg-on-surface text-surface w-6 h-6 flex items-center justify-center rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <span className="material-symbols-outlined text-xs">close</span>
                  </button>
                </div>
              ))}
              {Array.from({ length: Math.max(0, 5 - photos.length) }).map((_, i) => (
                <div
                  key={`empty-${i}`}
                  className="aspect-square border border-outline-variant border-dashed flex items-center justify-center bg-surface-container-lowest cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <span className="material-symbols-outlined text-outline-variant">add</span>
                </div>
              ))}
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between font-label text-[10px] tracking-widest text-on-surface-variant">
                <span>UPLOAD PROGRESS</span>
                <span className="text-primary">{photos.length} / {minPhotosRequired} REQUIRED</span>
              </div>
              <div className="w-full h-1 bg-surface-container-highest overflow-hidden">
                <div className="h-full bg-primary transition-all duration-700" style={{ width: `${Math.min(100, (photos.length / recommendedPhotos) * 100)}%` }}></div>
              </div>
            </div>

            {/* Trust Strip */}
            <div className="flex flex-wrap gap-x-6 gap-y-3 pt-2">
              {[
                { icon: "lock", text: "Encrypted in transit & at rest" },
                { icon: "no_photography", text: "Never used to train AI" },
                { icon: "auto_delete", text: "Auto-deleted after 30 days" },
              ].map(({ icon, text }) => (
                <div key={icon} className="flex items-center gap-2 text-on-surface-variant">
                  <span className="material-symbols-outlined text-[16px] text-outline">{icon}</span>
                  <span className="font-label text-[10px] tracking-wider uppercase">{text}</span>
                </div>
              ))}
              <a href="/privacy" className="flex items-center gap-1 text-primary hover:underline underline-offset-4 transition-colors" target="_blank" rel="noopener noreferrer">
                <span className="font-label text-[10px] tracking-wider uppercase">Privacy Policy</span>
                <span className="material-symbols-outlined text-[12px]">open_in_new</span>
              </a>
            </div>

          </div>

          {/* Preferences Section */}
          <div className="space-y-8 pt-8">
            <h2 className="font-label text-xs tracking-widest uppercase font-bold text-primary">02. Stylistic Intent</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
              <div className="space-y-8">
                {/* Gender */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Gender Identity</label>
                  <div className="flex p-1 bg-surface-container-low rounded-lg w-fit">
                    {["Masculine", "Feminine", "Neutral"].map((g) => (
                      <button
                        key={g}
                        onClick={() => setGender(g)}
                        className={`px-6 py-2 text-xs font-label uppercase tracking-widest ${gender === g ? "bg-surface-container-lowest text-on-surface rounded-md shadow-sm" : "text-on-surface-variant hover:text-on-surface"}`}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Wear Type */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Styling Type</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { value: "all", label: "All Styles" },
                      { value: "western", label: "Western" },
                      { value: "indian", label: "Indian" },
                      { value: "fusion", label: "Fusion" },
                    ].map((wt) => (
                      <button
                        key={wt.value}
                        onClick={() => setWearType(wt.value)}
                        className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                          wearType === wt.value
                            ? "border-primary bg-primary-fixed text-on-primary-fixed"
                            : "border-outline-variant hover:border-primary hover:text-primary"
                        }`}
                      >
                        {wt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Age Range */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Age Range</label>
                  <div className="flex flex-wrap gap-2">
                    {ageRanges.map((age) => (
                      <button
                        key={age}
                        onClick={() => setAgeRange(ageRange === age ? "" : age)}
                        className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                          ageRange === age
                            ? "border-primary bg-primary-fixed text-on-primary-fixed"
                            : "border-outline-variant hover:border-primary hover:text-primary"
                        }`}
                      >
                        {age}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-8">
                {/* Style Archetypes */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Style Archetypes</label>
                  <div className="flex flex-wrap gap-2">
                    {styleArchetypes.map((style) => (
                      <button
                        key={style}
                        onClick={() => toggleStyle(style)}
                        className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                          selectedStyles.includes(style)
                            ? "border-primary bg-primary-fixed text-on-primary-fixed"
                            : "border-outline-variant hover:border-primary hover:text-primary"
                        }`}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Occasions */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Occasions</label>
                  <div className="flex flex-wrap gap-2">
                    {occasions.map((occ) => (
                      <button
                        key={occ}
                        onClick={() => toggleOccasion(occ)}
                        className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                          selectedOccasions.includes(occ)
                            ? "border-primary bg-primary-fixed text-on-primary-fixed"
                            : "border-outline-variant hover:border-primary hover:text-primary"
                        }`}
                      >
                        {occ}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Goals */}
                <div>
                  <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Style Goals</label>
                  <div className="flex flex-wrap gap-2">
                    {goalOptions.map((goal) => (
                      <button
                        key={goal}
                        onClick={() => toggleGoal(goal)}
                        className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                          selectedGoals.includes(goal)
                            ? "border-primary bg-primary-fixed text-on-primary-fixed"
                            : "border-outline-variant hover:border-primary hover:text-primary"
                        }`}
                      >
                        {goal}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Fit Details Section */}
          <div className="space-y-8 pt-8">
            <div>
              <h2 className="font-label text-xs tracking-widest uppercase font-bold text-primary mb-2">03. Fit Data</h2>
              <p className="font-body text-sm text-on-surface-variant">
                These details make marketplace matches size-aware instead of just visually stylish.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className="space-y-2">
                <span className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant">Height CM</span>
                <input
                  value={heightCm}
                  onChange={(event) => setHeightCm(event.target.value)}
                  inputMode="numeric"
                  placeholder="175"
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                />
              </label>
              <label className="space-y-2">
                <span className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant">Weight KG</span>
                <input
                  value={weightKg}
                  onChange={(event) => setWeightKg(event.target.value)}
                  inputMode="numeric"
                  placeholder="70"
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                />
              </label>
              <label className="space-y-2">
                <span className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant">Pincode</span>
                <input
                  value={pincode}
                  onChange={(event) => setPincode(event.target.value)}
                  inputMode="numeric"
                  placeholder="110001"
                  className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                />
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Top Size</label>
                <div className="flex flex-wrap gap-2">
                  {apparelSizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setShirtSize(shirtSize === size ? "" : size)}
                      className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                        shirtSize === size
                          ? "border-primary bg-primary-fixed text-on-primary-fixed"
                          : "border-outline-variant hover:border-primary hover:text-primary"
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Bottom / Waist Size</label>
                <div className="flex flex-wrap gap-2">
                  {waistSizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setBottomSize(bottomSize === size ? "" : size)}
                      className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                        bottomSize === size
                          ? "border-primary bg-primary-fixed text-on-primary-fixed"
                          : "border-outline-variant hover:border-primary hover:text-primary"
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Shoe Size</label>
                <div className="flex flex-wrap gap-2">
                  {shoeSizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setShoeSize(shoeSize === size ? "" : size)}
                      className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                        shoeSize === size
                          ? "border-primary bg-primary-fixed text-on-primary-fixed"
                          : "border-outline-variant hover:border-primary hover:text-primary"
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="font-label text-[10px] tracking-widest uppercase text-on-surface-variant block mb-4">Preferred Fit</label>
                <div className="flex flex-wrap gap-2">
                  {fitOptions.map((fit) => (
                    <button
                      key={fit}
                      onClick={() => setPreferredFit(fit)}
                      className={`px-4 py-2 border text-[11px] font-label uppercase tracking-wider rounded-full transition-colors ${
                        preferredFit === fit
                          ? "border-primary bg-primary-fixed text-on-primary-fixed"
                          : "border-outline-variant hover:border-primary hover:text-primary"
                      }`}
                    >
                      {fit}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Visual Analysis Section */}
          <div className="space-y-6 pt-8">
            <div>
              <h2 className="font-label text-xs tracking-widest uppercase font-bold text-primary mb-2">04. Visual Output</h2>
              <p className="font-body text-sm text-on-surface-variant">
                Choose the premium board we can generate after the verified analysis is complete.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {visualAnalysisOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setVisualAnalysisKind(option.value)}
                  className={`text-left p-5 rounded-xl border transition-all ${
                    visualAnalysisKind === option.value
                      ? "border-primary bg-primary-fixed/30 shadow-sm"
                      : "border-outline-variant bg-surface-container-low hover:border-primary/60"
                  }`}
                >
                  <span className="font-label text-[11px] uppercase tracking-widest text-primary block mb-3">
                    {option.label}
                  </span>
                  <span className="font-body text-xs text-on-surface-variant leading-relaxed">
                    {option.description} · after verification
                  </span>
                </button>
              ))}
            </div>
          </div>

          {showAuthGate && !authSession?.session_token && (
            <div className="space-y-5 pt-8">
              <div className="bg-surface-container-low rounded-2xl p-6 md:p-8 border border-primary/25 editorial-shadow">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-6">
                  <div>
                    <span className="font-label text-[10px] uppercase tracking-widest text-primary block mb-2">
                      Final Step
                    </span>
                    <h2 className="font-headline text-3xl mb-3">Verify email to start analysis</h2>
                    <p className="font-body text-sm text-on-surface-variant max-w-2xl leading-relaxed">
                      We will save the result to your AuraFit ID and email you the result link. AI credits are used only after OTP verification.
                    </p>
                  </div>
                  <span className="font-label text-[10px] uppercase tracking-widest text-primary bg-primary-fixed/30 rounded-full px-3 py-1 w-fit">
                    Credit Safe
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="space-y-2">
                    <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">Name Optional</span>
                    <input
                      value={profileName}
                      onChange={(event) => setProfileName(event.target.value)}
                      placeholder="Aviral"
                      className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">Email</span>
                    <input
                      value={authEmail}
                      onChange={(event) => setAuthEmail(event.target.value)}
                      placeholder="you@example.com"
                      inputMode="email"
                      className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg px-4 py-3 font-body text-sm outline-none focus:border-primary"
                    />
                  </label>
                </div>

                {otpRequested && (
                  <label className="space-y-2 block mt-4">
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
                )}

                <div className="flex flex-col sm:flex-row gap-3 sm:items-center mt-5">
                  <button
                    onClick={otpRequested ? verifyOtpAndAnalyze : requestAnalyzeOtp}
                    disabled={isAuthWorking || isSubmitting || !authEmail.trim() || (otpRequested && !otpCode.trim())}
                    className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs disabled:opacity-40"
                  >
                    {isSubmitting
                      ? "Generating..."
                      : isAuthWorking
                        ? "Working..."
                        : otpRequested
                          ? "Verify & Generate"
                          : "Send OTP"}
                  </button>
                  <button
                    onClick={() => {
                      setShowAuthGate(false);
                      setAuthMessage("");
                    }}
                    disabled={isSubmitting || isAuthWorking}
                    className="bg-surface-container-highest text-on-surface px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs disabled:opacity-40"
                  >
                    Edit Inputs
                  </button>
                </div>

                {authMessage && (
                  <p className="font-label text-[10px] uppercase tracking-widest text-primary mt-5">
                    {authMessage}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* CTA Button */}
          <div className="pt-12">
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || (showAuthGate && !authSession?.session_token)}
              className={`w-full py-6 rounded-lg font-label uppercase tracking-[0.3em] flex items-center justify-center gap-3 group relative overflow-hidden ${
                canSubmit && (!showAuthGate || authSession?.session_token)
                  ? "bg-primary text-on-primary cursor-pointer hover:opacity-90 transition-opacity"
                  : "bg-surface-container-highest text-on-surface-variant cursor-not-allowed"
              }`}
            >
              {isSubmitting ? (
                <>
                  <span className="material-symbols-outlined animate-spin z-10">progress_activity</span>
                  <span className="z-10">Analyzing Your Style...</span>
                </>
              ) : (
                <>
                  <span className="z-10">Analyze My Style</span>
                  <span className="material-symbols-outlined z-10">arrow_right_alt</span>
                </>
              )}
            </button>
            {!authSession?.session_token && photos.length >= minPhotosRequired && !isSubmitting && !showAuthGate && (
              <p className="text-center mt-4 font-label text-[10px] text-on-surface-variant uppercase tracking-widest opacity-80">
                Next: email OTP, then we generate and email your result link.
              </p>
            )}
            {!canSubmit && !isSubmitting && (
              <p className="text-center mt-4 font-label text-[10px] text-error uppercase tracking-widest opacity-80">
                Please upload {minPhotosRequired - photos.length} more photo{minPhotosRequired - photos.length !== 1 ? "s" : ""} to unlock analysis
              </p>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
