import axios from "axios";

const defaultBaseURL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "/api");

const api = axios.create({
  baseURL: defaultBaseURL,
  withCredentials: true,
});

export function getApiAssetUrl(path: string): string {
  if (path.startsWith("http") || path.startsWith("data:")) return path;
  return `${defaultBaseURL}${path}`;
}

// --- Analysis Models ---

export interface SkinTone {
  fitzpatrick: string;
  undertone: string;
  label: string;
  hex_color: string;
}

export interface BodyType {
  shape: string;
  build: string;
  height_category: string;
}

export interface Proportions {
  shoulder_hip_ratio?: string;
  torso_leg_ratio?: string;
}

export interface ColorRecommendation {
  name: string;
  hex: string;
  category?: string;
  reason?: string;
}

export interface StyleProfile {
  job_id: string;
  gender: string;
  skin_tone: SkinTone;
  body_type: BodyType;
  proportions?: Proportions;
  face_shape?: string;
  color_season?: string;
  eye_color?: string;
  style_vibes: string[];
  color_palette: ColorRecommendation[];
  wardrobe_tips: string[];
  confidence_score?: number;
}

export interface FitProfile {
  height_cm?: number;
  weight_kg?: number;
  shirt_size?: string;
  bottom_size?: string;
  shoe_size?: string;
  preferred_fit?: string;
  pincode?: string;
}

// --- Outfit Models ---

export interface OutfitItem {
  name: string;
  price_usd: number;
  buy_url: string;
  image_url: string;
  brand: string;
  category: string;
}

export interface OutfitRecommendation {
  id: string;
  name: string;
  description: string;
  why_it_works: string;
  items: OutfitItem[];
  total_price_usd: number;
  style_tags: string[];
  image_url: string;
  recommendation_category?: string;
  sub_category?: string;
  source?: string;
  confidence?: number;
}

export interface AnalysisResultPayload {
  job_id: string;
  status?: string;
  profile?: StyleProfile;
  recommendations?: Record<string, OutfitRecommendation[]>;
  fit_profile?: FitProfile;
  user?: UserIdentity | null;
  profile_name?: string | null;
}

export interface JobStatusPayload {
  job_id: string;
  status: string;
  result_url?: string | null;
  error_message?: string | null;
  attempts?: number;
  max_attempts?: number;
  created_at?: string | null;
  updated_at?: string | null;
  locked_at?: string | null;
  started_at?: string | null;
  last_error_at?: string | null;
  completed_at?: string | null;
}

export interface UserIdentity {
  id: string;
  username: string;
  display_name: string;
  email?: string | null;
  created_at?: string | null;
}

export interface UserSessionSummary {
  job_id: string;
  status: string;
  profile_name?: string | null;
  created_at?: string | null;
  gender: string;
  skin_label?: string | null;
  color_season?: string | null;
  style_vibes: string[];
}

export interface AuthPayload {
  status: string;
  user: UserIdentity;
  session_token?: string | null;
  expires_at?: string | null;
}

export interface OtpRequestResponse {
  status: string;
  email: string;
  expires_in_seconds: number;
  delivery: string;
  dev_otp?: string | null;
}

export type VisualAnalysisKind = "color_palette" | "hairstyles" | "look_audit";

export interface VisualAnalysisResult {
  job_id: string;
  status: string;
  kind: VisualAnalysisKind;
  image_url: string;
  prompt_version: string;
  process: string[];
}

export interface ProductColor {
  name: string;
  hex?: string;
  undertone_tags: string[];
  season_tags: string[];
}

export interface CatalogProduct {
  id: string;
  title: string;
  brand: string;
  marketplace: string;
  category: string;
  sub_category: string;
  gender: string;
  image_url: string;
  product_url: string;
  affiliate_url?: string;
  price_inr: number;
  original_price_inr?: number;
  currency: string;
  colors: ProductColor[];
  sizes: string[];
  available_sizes: string[];
  fit?: string;
  fabric?: string;
  pattern?: string;
  tags: string[];
  rating?: number;
  returnable: boolean;
}

export interface ProductMatch {
  product: CatalogProduct;
  score: number;
  reasons: string[];
  warnings: string[];
}

export interface ProductRecommendationResponse {
  job_id: string;
  status: string;
  fit_profile: FitProfile;
  products: ProductMatch[];
}

export interface CostPolicy {
  analysis_limit_per_user_per_day: number;
  guest_analysis_limit_per_day: number;
  visual_generation_requires_auth: boolean;
  visual_generation_trigger: string;
  standalone_visual_generation_enabled?: boolean;
  max_visual_generations_per_user_per_day?: number;
  max_daily_ai_cost_per_user_usd?: number;
  cost_tracking_enabled?: boolean;
  dev_otp_enabled?: boolean;
  email_delivery_configured?: boolean;
  pricing?: Record<string, number>;
  guardrails: string[];
}

export interface CatalogStatus {
  seed_products: number;
  cached_products: number;
  cache_path: string;
  providers: Record<string, boolean>;
}

export interface UsageLedgerEntry {
  id: string;
  job_id?: string | null;
  session_id?: string | null;
  user_id?: string | null;
  operation: string;
  provider: string;
  model: string;
  status: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  image_count: number;
  estimated_cost_usd: number;
  actual_cost_usd?: number | null;
  currency: string;
  details: Record<string, unknown>;
  created_at?: string | null;
}

export interface UsageLedgerPayload {
  job_id?: string | null;
  user_id?: string | null;
  total_estimated_cost_usd: number;
  total_actual_cost_usd?: number | null;
  total_tokens: number;
  entries: UsageLedgerEntry[];
}

// --- API Functions ---

export const AUTH_STORAGE_KEY = "aurafit:auth";

export function getStoredAuth(): AuthPayload | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as AuthPayload;
  } catch {
    return null;
  }
}

export function storeAuth(auth: AuthPayload) {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
  localStorage.setItem("aurafit:user", JSON.stringify(auth.user));
}

export function clearStoredAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_STORAGE_KEY);
  localStorage.removeItem("aurafit:user");
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return fallback;
}

function authHeaders(sessionToken?: string | null) {
  return sessionToken ? { Authorization: `Bearer ${sessionToken}` } : undefined;
}

export async function analyzePhotos(
  photos: File[],
  gender: string,
  budgetMin: number,
  budgetMax: number,
  stylePreferences: string[],
  wearType: string = "all",
  occasion: string[] = [],
  goals: string[] = [],
  ageRange: string = "",
  fitProfile: FitProfile = {},
  owner?: { user_id?: string; profile_name?: string; session_token?: string | null }
): Promise<AnalysisResultPayload> {
  const formData = new FormData();
  photos.forEach((photo) => formData.append("photos", photo));
  formData.append("gender", gender);
  formData.append("budget_min", budgetMin.toString());
  formData.append("budget_max", budgetMax.toString());
  formData.append("style_preferences", stylePreferences.join(","));
  formData.append("wear_type", wearType);
  formData.append("occasion", occasion.join(","));
  formData.append("goals", goals.join(","));
  formData.append("age_range", ageRange);
  if (fitProfile.height_cm) formData.append("height_cm", fitProfile.height_cm.toString());
  if (fitProfile.weight_kg) formData.append("weight_kg", fitProfile.weight_kg.toString());
  if (fitProfile.shirt_size) formData.append("shirt_size", fitProfile.shirt_size);
  if (fitProfile.bottom_size) formData.append("bottom_size", fitProfile.bottom_size);
  if (fitProfile.shoe_size) formData.append("shoe_size", fitProfile.shoe_size);
  if (fitProfile.preferred_fit) formData.append("preferred_fit", fitProfile.preferred_fit);
  if (fitProfile.pincode) formData.append("pincode", fitProfile.pincode);
  if (owner?.user_id) formData.append("user_id", owner.user_id);
  if (owner?.profile_name) formData.append("profile_name", owner.profile_name);

  const { data } = await api.post("/analyze", formData, {
    headers: authHeaders(owner?.session_token),
  });
  return data;
}

export async function loginUser(displayName: string, email: string = ""): Promise<UserIdentity> {
  const { data } = await api.post("/auth/login", {
    display_name: displayName,
    email: email || undefined,
  });
  return data.user;
}

export async function requestOtp(email: string, displayName: string = ""): Promise<OtpRequestResponse> {
  const { data } = await api.post("/auth/otp/request", {
    email,
    display_name: displayName || undefined,
  });
  return data;
}

export async function verifyOtp(
  email: string,
  otpCode: string,
  displayName: string = ""
): Promise<AuthPayload> {
  const { data } = await api.post("/auth/otp/verify", {
    email,
    otp_code: otpCode,
    display_name: displayName || undefined,
  });
  return data;
}

export async function getMe(sessionToken?: string | null): Promise<AuthPayload> {
  const { data } = await api.get("/auth/me", {
    headers: authHeaders(sessionToken),
  });
  return data;
}

export async function logoutUser(sessionToken?: string | null): Promise<void> {
  await api.post("/auth/logout", null, {
    headers: authHeaders(sessionToken),
  });
  clearStoredAuth();
}

export async function claimSession(
  jobId: string,
  userId?: string,
  profileName?: string,
  sessionToken?: string | null
): Promise<{ status: string; job_id: string; profile_name: string; user: UserIdentity }> {
  const { data } = await api.post(`/sessions/${jobId}/claim`, {
    user_id: userId,
    profile_name: profileName,
    session_token: sessionToken || undefined,
  }, {
    headers: authHeaders(sessionToken),
  });
  return data;
}

export async function getUserSessions(userId: string): Promise<{
  user: UserIdentity;
  sessions: UserSessionSummary[];
}> {
  const { data } = await api.get(`/users/${userId}/sessions`);
  return data;
}

export async function getProfile(jobId: string): Promise<{
  status: string;
  profile?: StyleProfile;
  recommendations?: Record<string, OutfitRecommendation[]>;
  fit_profile?: FitProfile;
  user?: UserIdentity | null;
  profile_name?: string | null;
}> {
  const { data } = await api.get(`/profile/${jobId}`);
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobStatusPayload> {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data;
}

export async function getJobUsage(
  jobId: string,
  sessionToken?: string | null
): Promise<UsageLedgerPayload> {
  const { data } = await api.get(`/jobs/${jobId}/usage`, {
    headers: authHeaders(sessionToken),
  });
  return data;
}

export async function getUserUsage(
  userId: string,
  sessionToken?: string | null
): Promise<UsageLedgerPayload> {
  const { data } = await api.get(`/users/${userId}/usage`, {
    headers: authHeaders(sessionToken),
  });
  return data;
}

export async function getProductRecommendations(
  jobId: string,
  budgetMaxInr: number = 5000
): Promise<ProductRecommendationResponse> {
  const { data } = await api.get(`/products/recommendations/${jobId}`, {
    params: { budget_max_inr: budgetMaxInr },
  });
  return data;
}

export async function createVisualAnalysis(
  photo: File,
  kind: VisualAnalysisKind = "color_palette"
): Promise<VisualAnalysisResult> {
  const formData = new FormData();
  formData.append("photo", photo);
  formData.append("kind", kind);

  const { data } = await api.post("/visual-analysis", formData);
  return data;
}

export async function createSessionVisualAnalysis(
  jobId: string,
  kind: VisualAnalysisKind = "color_palette",
  sessionToken?: string | null
): Promise<VisualAnalysisResult> {
  const formData = new FormData();
  formData.append("kind", kind);
  const { data } = await api.post(`/sessions/${jobId}/visual-analysis`, formData, {
    headers: authHeaders(sessionToken),
  });
  return data;
}

export async function getCostPolicy(): Promise<CostPolicy> {
  const { data } = await api.get("/cost-policy");
  return data;
}

export async function getCatalogStatus(): Promise<CatalogStatus> {
  const { data } = await api.get("/catalog/status");
  return data;
}

export default api;
