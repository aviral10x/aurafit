import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// Lazy singleton — created on first use to avoid build-time crash when env vars are absent
let _supabase: SupabaseClient | null = null;

function getSupabaseClient(): SupabaseClient {
  if (!_supabase) {
    if (!supabaseUrl || !supabaseAnonKey) {
      // Return a dummy client in build/preview environments without Supabase configured
      return createClient("https://placeholder.supabase.co", "placeholder");
    }
    _supabase = createClient(supabaseUrl, supabaseAnonKey);
  }
  return _supabase;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    return (getSupabaseClient() as unknown as Record<string, unknown>)[prop as string];
  },
});


/** Request an OTP to the given email address. */
export async function requestOTP(email: string) {
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: true },
  });
  if (error) throw new Error(error.message);
}

/** Verify the OTP and return the session. */
export async function verifyOTP(email: string, token: string) {
  const { data, error } = await supabase.auth.verifyOtp({
    email,
    token,
    type: "email",
  });
  if (error) throw new Error(error.message);
  return data.session;
}

/** Sign out the current user. */
export async function signOut() {
  await supabase.auth.signOut();
}

/** Get the current session (null if not authenticated). */
export async function getSession() {
  const { data } = await supabase.auth.getSession();
  return data.session;
}

/** Get the current user (null if not authenticated). */
export async function getUser() {
  const { data } = await supabase.auth.getUser();
  return data.user;
}
