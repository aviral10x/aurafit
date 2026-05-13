-- ============================================================
-- AuraFit Supabase Schema
-- Run this in the Supabase SQL editor (Settings > SQL Editor)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- BACKEND USERS
-- AuraFit uses its own backend OTP/session model. Do not point
-- analysis ownership at auth.users unless the API is rewritten for
-- native Supabase Auth end-to-end.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.users (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username          TEXT NOT NULL UNIQUE,
  display_name      TEXT NOT NULL,
  email             TEXT UNIQUE,
  email_verified_at TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.auth_otps (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email       TEXT NOT NULL,
  display_name TEXT,
  code_hash   TEXT NOT NULL,
  purpose     TEXT NOT NULL DEFAULT 'login',
  attempts    INT NOT NULL DEFAULT 0,
  expires_at  TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.auth_sessions (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash   TEXT NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at   TIMESTAMPTZ NOT NULL,
  revoked_at   TIMESTAMPTZ
);

-- ============================================================
-- SESSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sessions (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID REFERENCES public.users(id) ON DELETE SET NULL,
  profile_name TEXT,
  gender       TEXT NOT NULL DEFAULT 'men',
  age_range    TEXT,
  occasion     TEXT[],
  goals        TEXT[],
  budget_min   FLOAT NOT NULL DEFAULT 50,
  budget_max   FLOAT NOT NULL DEFAULT 300,
  style_preferences TEXT[],
  wear_type    TEXT NOT NULL DEFAULT 'all',
  height_cm    FLOAT,
  weight_kg    FLOAT,
  shirt_size   TEXT,
  bottom_size  TEXT,
  shoe_size    TEXT,
  preferred_fit TEXT,
  pincode      TEXT,
  status       TEXT NOT NULL DEFAULT 'pending',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- PHOTOS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.photos (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id   UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- ANALYSIS RESULTS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.analysis_results (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id        UUID NOT NULL UNIQUE REFERENCES public.sessions(id) ON DELETE CASCADE,
  body_shape        TEXT NOT NULL,
  body_build        TEXT NOT NULL,
  height_category   TEXT NOT NULL,
  shoulder_hip_ratio TEXT,
  torso_leg_ratio    TEXT,
  skin_fitzpatrick  TEXT NOT NULL,
  skin_undertone    TEXT NOT NULL,
  skin_label        TEXT NOT NULL,
  skin_hex          TEXT NOT NULL,
  face_shape        TEXT,
  eye_color         TEXT,
  color_season      TEXT,
  style_vibes       TEXT[],
  wardrobe_tips     TEXT[],
  raw_ai_response   JSONB,
  confidence_score  FLOAT NOT NULL DEFAULT 0.85,
  analyzed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- COLOR PALETTES
-- ============================================================
CREATE TABLE IF NOT EXISTS public.color_palettes (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id  UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  color_name  TEXT NOT NULL,
  hex_value   TEXT NOT NULL,
  category    TEXT NOT NULL DEFAULT 'best',
  reason      TEXT
);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.recommendations (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id   UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  category     TEXT NOT NULL DEFAULT 'clothing',
  sub_category TEXT NOT NULL DEFAULT 'western',
  title        TEXT NOT NULL,
  description  TEXT NOT NULL,
  why_it_works TEXT NOT NULL,
  items        JSONB,
  style_tags   TEXT[],
  image_url    TEXT,
  total_price_usd FLOAT,
  source       TEXT NOT NULL DEFAULT 'ai',
  confidence   FLOAT NOT NULL DEFAULT 0.85,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- COST LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.cost_logs (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id   UUID REFERENCES public.sessions(id) ON DELETE SET NULL,
  user_id      UUID REFERENCES public.users(id) ON DELETE SET NULL,
  ip_address   TEXT,
  model_name   TEXT NOT NULL,
  input_tokens  INT NOT NULL DEFAULT 0,
  output_tokens INT NOT NULL DEFAULT 0,
  cost_usd     FLOAT NOT NULL DEFAULT 0,
  job_type     TEXT NOT NULL DEFAULT 'analysis',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- PRODUCTS (Marketplace seed)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.products (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  brand        TEXT NOT NULL,
  title        TEXT NOT NULL,
  price_usd    FLOAT NOT NULL,
  image_url    TEXT NOT NULL,
  buy_url      TEXT NOT NULL,
  category     TEXT NOT NULL,
  sub_category TEXT NOT NULL DEFAULT 'western',
  occasion     TEXT[],
  gender       TEXT NOT NULL DEFAULT 'all',
  colors       TEXT[],
  best_for_undertone TEXT[],
  best_for_season    TEXT[],
  best_for_body      TEXT[],
  active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- VISUAL BOARDS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.visual_boards (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id   UUID NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  board_type   TEXT NOT NULL,
  image_url    TEXT NOT NULL,
  storage_path TEXT,
  prompt_used  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- STORAGE BUCKETS
-- (Run via Supabase Dashboard > Storage, or via API)
-- Buckets to create:
--   photos         (private, max 50MB per file)
--   visual-boards  (private, max 10MB per file)
-- ============================================================

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE public.sessions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.photos            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_results  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.color_palettes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recommendations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cost_logs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visual_boards     ENABLE ROW LEVEL SECURITY;

-- Service role has full access (backend uses service key, bypasses RLS)
-- No anon/authenticated direct access — all DB access goes through backend API

-- Public read for products
CREATE POLICY "products_public_read" ON public.products
  FOR SELECT USING (active = true);
