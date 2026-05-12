# AuraFit Roadmap

Last updated: May 3, 2026

## Phase 0: Local MVP Foundation

Status: Complete

- Frontend and backend run locally without Docker.
- PostgreSQL-backed analysis persistence is working.
- Upload accepts 1+ photo and collects style, fit, and marketplace preferences.
- Current Aviral profile is saved and visible in My Profiles.

## Phase 1: AI Styling Core

Status: Complete

- OpenRouter-backed structured image/style analysis is wired.
- Rule engine combines body, color, face, occasion, goal, and category rules.
- Recommendations are generated and persisted.
- PDF report download exists.

## Phase 2: Marketplace Matching Foundation

Status: Complete for MVP

- Normalized product catalog schema exists.
- Local seed catalog powers buyable recommendations.
- Product ranking considers color season, fit, size, budget, gender, and style tags.
- Generic CSV/JSON import endpoint exists.
- Flipkart feed adapter foundation exists.
- Marketplace feed CSV template exists for Snitch, Myntra, Amazon, Ajio, and partner exports.
- Account page surfaces provider/catalog readiness.

Remaining:

- Production feeds for Amazon, Myntra, Snitch, Ajio.
- Affiliate-link QA and click tracking.
- Sync failure logging and admin import UI.

## Phase 3: Instagram-Friendly Auth And Cost Gate

Status: Complete for MVP, pending provider credentials

- Upload/preferences happen before login.
- Analyze click opens email OTP gate.
- Backend blocks anonymous `/analyze` calls.
- Verified sessions are issued after OTP.
- Result links are sent through SMTP or logged in explicit dev mode.
- Visual board generation requires saved/verified profile.
- Daily per-user analysis quota is now enforced before upload persistence or AI calls.
- Dev OTP can be disabled and now fails closed if SMTP/Resend is missing.
- Daily recorded AI spend cap and daily visual-board cap are enforced.
- Standalone image generation is disabled by default.
- Upload/account/results pages surface guardrail and usage state.

Remaining:

- Production email provider setup: Resend API key, verified sender domain, SMTP password.
- Per-IP/device rate limiting using Redis or managed KV.
- Abuse dashboard for OTP attempts, analysis usage, and failed payments/credits.
- Better session-cookie hardening for deployed HTTPS.

## Phase 4: Async Jobs And Reliability

Status: Complete for MVP

- `/analyze` creates DB-backed jobs and returns quickly.
- Job statuses exist: queued, processing, complete, failed.
- Worker retries transient failures and records attempts/errors.
- Frontend polls result status and resumes by job ID.
- Completion email is sent after worker success when SMTP is configured.

Remaining:

- Move from DB-backed queue to Redis/Vercel Queues when traffic requires fan-out.
- Add worker metrics, dead-letter queue, and admin replay tools.

## Phase 5: Storage And Privacy

Status: Partially complete

- Uploaded photos and generated boards mirror to Supabase Storage.
- Worker can restore missing local files from Supabase Storage.

Remaining:

- Serve sensitive images through signed URLs only.
- Add user deletion/export flows.
- Add explicit consent language for face/photo analysis.
- Add retention policy for source photos and generated results.

## Phase 6: Production Commerce

Status: Not started

- Integrate real marketplace feeds and affiliate programs.
- Add product freshness, stock, size availability, and price refresh jobs.
- Add marketplace-specific ranking boosts and exclusions.
- Add click/conversion attribution.
- Add "save item", "not my style", and feedback loops.

## Phase 7: Launch Hardening

Status: Not started

- Deployment environments: dev, staging, production.
- Observability: logs, metrics, traces, alerts.
- Automated tests for auth, upload, analysis quota, catalog import, and profile recovery.
- Mobile and Instagram in-app browser QA.
- Security review for auth, uploads, CORS, rate limits, and file serving.

## Current Sprint

Goal: make paid/social traffic safer before scaling.

- Enforce analysis only after OTP verification.
- Enforce daily per-user analysis quota.
- Keep visual generation behind saved verified profile.
- Document SMTP and cost controls.
- Next: add async job processing and durable result status.
