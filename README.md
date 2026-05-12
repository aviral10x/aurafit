# AuraFit — AI-Powered Personal Styling Platform

A premium styling intelligence platform that delivers personalized recommendations for Indian, Western, and Fusion dressing based on body shape, proportions, coloring, facial features, age, and transformation goals.

## Architecture

**Rule Engine First, AI Assist Second** — Expert styling knowledge lives in 19 YAML rule files (116 rules). Claude vision handles structured photo analysis. OpenAI image generation creates visual-first editorial boards.

```
backend/app/
  main.py              # FastAPI app with lifespan
  config.py            # Settings (pydantic-settings)
  database.py          # PostgreSQL async connection
  models/
    schemas.py         # Pydantic request/response models
    db.py              # SQLAlchemy ORM (5 tables)
  services/
    analyzer.py        # Claude vision photo analysis
    rule_engine.py     # YAML rule loader + matcher
    recommender.py     # Combines rules + AI
    product_recommender.py # Ranks marketplace-ready products against the profile
    report_generator.py # PDF report generation
    visual_prompts.py   # Versioned infographic prompt templates
    openai_image.py     # OpenAI image edit/generation workflow
    storage.py          # Local + Supabase Storage abstraction
  catalog/
    seed_products.yaml  # Local marketplace-shaped seed catalog for development
  api/
    routes.py          # All API endpoints
  rules/               # 19 YAML rule files
    body/              # Body shape rules (men + women + proportions)
    color/             # Undertone palettes, color seasons, makeup
    face/              # Face shape accessories, neckline-jewellery
    indian/            # Saree, lehenga, kurta, sherwani rules
    western/           # Western wear by body shape
    fusion/            # Indo-western combinations
    accessories/       # Footwear, bags, belts, watches
    occasions/         # Casual to bridal occasion modifiers
    goals/             # Look taller, slimmer, broader, etc.
    age/               # Age-based style adjustments

frontend/
  app/
    page.tsx           # Landing page
    upload/page.tsx    # Photo upload + preferences
    results/[jobId]/   # Tabbed results with PDF download
  components/
    Navbar.tsx         # Shared navigation
    Footer.tsx         # Shared footer
  lib/api.ts           # API client + TypeScript interfaces
```

## Quick Start

### Docker (Recommended)

```bash
cp backend/.env.example backend/.env
docker-compose up
```

Opens at [http://localhost:3000](http://localhost:3000). PostgreSQL, backend, and frontend start automatically.

### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Update DATABASE_URL to point to local Postgres
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## With Real AI Analysis

1. Get an OpenRouter API key for structured text/vision analysis, or use Anthropic directly.
2. Get an OpenAI API key from [platform.openai.com](https://platform.openai.com) for generated visual boards.
3. Edit `backend/.env`:
   ```
   MOCK_MODE=false
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENROUTER_TEXT_MODEL=google/gemini-2.5-flash
   OPENROUTER_VISION_MODEL=anthropic/claude-opus-4.6-fast
   OPENROUTER_IMAGE_MODEL=openai/gpt-5.4-image-2
   OPENROUTER_IMAGE_SIZE=2K
   LLM_MAX_IMAGES=3
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   OPENAI_IMAGE_MODEL=gpt-image-2
   ```
4. Restart the backend

OpenRouter is used first when `OPENROUTER_API_KEY` is present. Anthropic is the fallback for structured analysis and outfit generation. `/visual-analysis` uses OpenRouter image generation first via `OPENROUTER_IMAGE_MODEL`, then falls back to the OpenAI Images API if `OPENAI_API_KEY` is configured.

## Supabase Phase 1

AuraFit can use Supabase for the production database and file storage while keeping the current DB-backed worker.

1. Create a Supabase project.
2. Copy the pooled Postgres connection string and set it as `DATABASE_URL` using the async SQLAlchemy driver:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
   ```
3. Create a private Storage bucket, for example `aurafit`.
4. Add Storage settings:
   ```
   SUPABASE_URL=https://PROJECT_REF.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   SUPABASE_STORAGE_ENABLED=true
   SUPABASE_STORAGE_BUCKET=aurafit
   SUPABASE_STORAGE_UPLOADS_PREFIX=uploads
   ```
5. Restart the backend and confirm:
   ```
   curl http://localhost:8000/health
   ```

When Supabase Storage is enabled, uploads are written locally for immediate processing and mirrored to Supabase. If a worker later runs on ephemeral disk, it can restore missing photos from Supabase before analysis. Generated visual boards are also mirrored, while local file serving remains the development fallback.

## Visual Analysis Flow

When a user uploads photos, AuraFit allows low-friction input collection before any AI credits are used:

1. Upload/preferences: the user completes inputs without a login wall.
2. OTP gate: clicking Analyze asks for email and verifies a 6-digit OTP.
3. Structured analysis: `/analyze` reads up to `LLM_MAX_IMAGES` photos only after OTP, downscales them for efficient vision calls, detects body/color/style attributes, and returns recommendations.
4. Result delivery: AuraFit saves the profile to the verified ID and emails the result link.
5. Visual board generation: `/sessions/{job_id}/visual-analysis` sends the saved lead portrait plus a versioned prompt to image generation and returns a generated infographic image.

Supported visual modes:

| Mode | Purpose |
|------|---------|
| `color_palette` | 16-season color analysis, asymmetrical drape comparisons, metals, hair, makeup, eyes |
| `hairstyles` | Side-by-side hairstyle and grooming comparisons with style-fit labels |
| `look_audit` | Non-medical cosmetics/style audit with grooming, styling, and consult-only aesthetic notes |

The look audit intentionally rates proposal fit, not human attractiveness, and avoids medical claims or “fix this flaw” language.

## Instagram-Friendly Auth Flow

AuraFit is set up for Reel-link traffic where every extra step hurts conversion, but AI work should not start for anonymous visitors:

1. Land on `/upload`.
2. Upload photos and fill preferences without a login wall.
3. Click Analyze.
4. Verify email with a 6-digit OTP.
5. Run analysis only after verification.
6. Save the result to the AuraFit ID and email the result link.
7. Generate the premium visual board after the saved result exists.

OTP endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/auth/otp/request` | Send a 6-digit email OTP |
| `POST` | `/auth/otp/verify` | Verify OTP, create/find user, return session token |
| `GET` | `/auth/me` | Validate a bearer session token |
| `POST` | `/auth/logout` | Revoke the current session token |
| `POST` | `/sessions/{job_id}/claim` | Attach a guest result to a verified user |

Local development returns the OTP in the API response only when SMTP is not configured and `AUTH_DEV_RETURN_OTP=true`. For production, configure SMTP and set `AUTH_DEV_RETURN_OTP=false`. If dev OTP is off and SMTP is missing, OTP requests fail closed instead of pretending an email was sent.

```
AUTH_TOKEN_SECRET=change-this-long-random-secret
AUTH_DEV_RETURN_OTP=false
AUTH_REQUIRE_EMAIL_DELIVERY=true
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USERNAME=resend
SMTP_PASSWORD=re_xxxxxxxxx
SMTP_FROM_EMAIL=AuraFit <login@yourdomain.com>
VISUAL_GENERATION_REQUIRES_AUTH=true
STANDALONE_VISUAL_GENERATION_ENABLED=false
ANALYSIS_REQUIRES_AUTH=true
ANALYSIS_LIMIT_PER_USER_PER_DAY=3
MAX_VISUAL_GENERATIONS_PER_USER_PER_DAY=1
MAX_DAILY_AI_COST_PER_USER_USD=1.00
```

For Resend SMTP, use host `smtp.resend.com`, username `resend`, and the Resend API key as the SMTP password. Verify the sender domain before using a branded `SMTP_FROM_EMAIL`.

## Cost Controls

The MVP avoids accidental credit burn from Instagram traffic:

- Upload/preferences are allowed before login; `/analyze` requires verified email OTP.
- Verified users are limited by `ANALYSIS_LIMIT_PER_USER_PER_DAY` before any AI work starts.
- Verified users are blocked after `MAX_DAILY_AI_COST_PER_USER_USD` of recorded daily usage.
- `LLM_MAX_IMAGES` limits how many uploaded photos are sent to the vision model.
- Visual generation is gated behind verified email OTP and `MAX_VISUAL_GENERATIONS_PER_USER_PER_DAY`.
- Standalone `/visual-analysis` generation is disabled unless `STANDALONE_VISUAL_GENERATION_ENABLED=true`.
- Completed result links are emailed to verified users for recovery.
- Product matching is deterministic/catalog-based and does not spend LLM credits.
- Completed results are loaded by `job_id` instead of re-running analysis on refresh.

Use `/cost-policy` to inspect the active guardrails from the backend.

## Marketplace Product Matching

AuraFit now separates style guidance from buyable product matching:

1. Upload captures optional fit data: height, weight, top size, bottom size, shoe size, fit preference, and pincode.
2. `/products/recommendations/{job_id}` ranks catalog products against the user profile and fit data.
3. The current catalog is a local seed file shaped like future marketplace feeds. It includes marketplace, brand, product URL, affiliate URL, price in INR, colors, sizes, available sizes, fit, fabric, tags, rating, and returnability.
4. This layer is designed so Flipkart/Amazon/Myntra/Snitch adapters can later sync real feeds into the same normalized schema.

### Flipkart Feed Sync

The first marketplace adapter is in place for Flipkart Affiliate feeds. It follows Flipkart's official feed listing/download flow:

1. Set credentials in `backend/.env`:
   ```
   FLIPKART_AFFILIATE_ID=your_tracking_id
   FLIPKART_AFFILIATE_TOKEN=your_api_token
   ```
2. Start the backend.
3. Check provider status:
   ```
   curl http://localhost:8000/catalog/status
   ```
4. Sync all available Flipkart feeds into the normalized provider cache:
   ```
   curl -X POST "http://localhost:8000/catalog/sync/flipkart?max_products_per_category=100"
   ```
5. Sync selected categories only:
   ```
   curl -X POST "http://localhost:8000/catalog/sync/flipkart?categories=mens_clothing,womens_clothing&max_products_per_category=50"
   ```

The adapter downloads Flipkart feed URLs, normalizes products into AuraFit's catalog schema, appends `affid` to product URLs, and merges cached provider products into `/products/recommendations/{job_id}`.

### Generic Marketplace Feed Import

For marketplaces without immediate API/feed credentials, import partner CSV/JSON exports directly:

```
curl -X POST "http://localhost:8000/catalog/import-feed" \
  -F "marketplace=myntra" \
  -F "replace_marketplace=true" \
  -F "sub_id=aurafit-dev" \
  -F "file=@/path/to/products.csv"
```

Supported marketplaces: `amazon`, `flipkart`, `myntra`, `snitch`, `ajio`, `other`.

A starter CSV is available at `backend/app/catalog/feed_template.csv`.

Recommended CSV columns:

| Column | Notes |
|--------|-------|
| `id` / `sku` / `asin` | Stable product identifier |
| `title` / `name` | Product title |
| `brand` | Brand name |
| `category`, `sub_category` | Normalized product grouping |
| `gender` | `men`, `women`, or `unisex` |
| `image_url` | Product image |
| `product_url` | Marketplace product page |
| `affiliate_url` | Optional direct tracking URL |
| `price_inr`, `original_price_inr` | INR pricing |
| `color`, `color_hex` | Product color |
| `sizes`, `available_sizes` | Comma or pipe separated |
| `fit`, `fabric`, `pattern`, `tags` | Ranking metadata |
| `rating`, `returnable` | Trust/commerce metadata |

If `affiliate_url` is absent, AuraFit can generate one using:

```
AMAZON_ASSOCIATE_TAG=yourtag-21
MYNTRA_AFFILIATE_URL_TEMPLATE=https://tracking.example.com/?url={url}&subid={sub_id}
SNITCH_AFFILIATE_URL_TEMPLATE=https://tracking.example.com/?url={url}&subid={sub_id}
AJIO_AFFILIATE_URL_TEMPLATE=https://tracking.example.com/?url={url}&subid={sub_id}
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check + loaded rule categories |
| `POST` | `/analyze` | Upload photos + preferences, get analysis |
| `POST` | `/visual-analysis` | Standalone visual generation, disabled by default in production |
| `POST` | `/sessions/{job_id}/visual-analysis` | Generate a saved result's premium visual board after OTP save |
| `GET` | `/visual-analysis/{job_id}/image` | Fetch generated visual analysis image |
| `GET` | `/sessions/{job_id}/visual-analysis/{kind}/image` | Fetch a saved result's generated visual board |
| `GET` | `/cost-policy` | Inspect credit-control guardrails |
| `POST` | `/auth/otp/request` | Request email OTP |
| `POST` | `/auth/otp/verify` | Verify OTP and create a session token |
| `GET` | `/auth/me` | Validate signed-in user |
| `POST` | `/auth/logout` | Revoke session token |
| `GET` | `/catalog/status` | Inspect seed/provider catalog counts and configured providers |
| `POST` | `/catalog/sync/flipkart` | Sync Flipkart Affiliate feeds into normalized catalog cache |
| `GET` | `/products/recommendations/{job_id}` | Fetch size-aware marketplace product matches |
| `GET` | `/profile/{job_id}` | Fetch analysis results + recommendations |
| `GET` | `/report/{job_id}` | Download PDF style report |
| `GET` | `/rules/categories` | List loaded rule categories |

## Tech Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, Anthropic SDK
- **Database:** PostgreSQL 16 (async via SQLAlchemy + asyncpg)
- **Rule Engine:** YAML-based with indexed matching
- **AI:** OpenRouter for Claude/GPT image workflows, OpenAI Images fallback
- **Reports:** ReportLab PDF generation
- **Infrastructure:** Docker Compose
