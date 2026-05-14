#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://aurafit.fun"
DEFAULT_TIMEOUT_SECONDS = 45


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


class SmokeFailure(Exception):
    pass


def _api_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    return normalized if normalized.endswith("/api") else f"{normalized}/api"


def _json_request(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    ops_token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, dict[str, Any]]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if ops_token:
        headers["X-Ops-Token"] = ops_token

    req = request.Request(url, data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"detail": raw}
        return exc.code, data
    except (TimeoutError, socket.timeout) as exc:
        raise SmokeFailure(f"Timed out after {timeout}s while calling {url}") from exc
    except error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise SmokeFailure(f"Could not reach {url}: {reason}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _check_health(api_base: str, timeout: int) -> CheckResult:
    status, data = _json_request("GET", f"{api_base}/health", timeout=timeout)
    _require(status == 200, f"/health returned HTTP {status}: {data.get('detail') or data}")
    _require(data.get("status") == "ok", f"/health status is not ok: {data.get('status')}")
    _require(data.get("mock_mode") is False, "MOCK_MODE must be false in production")
    _require(data.get("database_auto_migrate") is False, "DATABASE_AUTO_MIGRATE must be false in production")
    _require(data.get("database_available") is True, f"Database unavailable: {data.get('database_error')}")
    _require(data.get("analysis_worker_enabled") is True, "ANALYSIS_WORKER_ENABLED must be true until an external worker is configured")

    storage = data.get("storage") or {}
    email = data.get("email") or {}
    providers = data.get("ai_providers") or {}
    guardrails = data.get("credit_guardrails") or {}

    _require(storage.get("supabase_configured") is True, "Supabase Storage is not configured")
    _require(email.get("configured") is True, "Email delivery is not configured")
    _require(email.get("dev_otp_enabled") is False, "Dev OTP responses must be disabled in production")
    _require(providers.get("openrouter") is True, "OpenRouter text/vision provider is not configured")
    _require(providers.get("openrouter_images") is True, "OpenRouter image provider is not configured")
    _require((guardrails.get("analysis_limit_per_user_per_day") or 0) > 0, "Analysis daily limit is disabled")
    _require((guardrails.get("max_daily_ai_cost_per_user_usd") or 0) > 0, "Daily AI cost guardrail is disabled")

    return CheckResult("health", True, "production health/config is green")


def _check_auth_without_token(api_base: str, timeout: int) -> CheckResult:
    status, data = _json_request("GET", f"{api_base}/auth/sessions", timeout=timeout)
    _require(status == 401, f"Unauthenticated /auth/sessions should be 401, got {status}: {data}")
    return CheckResult("auth_guard", True, "saved profiles require auth")


def _request_otp(api_base: str, email: str, timeout: int) -> CheckResult:
    status, data = _json_request(
        "POST",
        f"{api_base}/auth/otp/request",
        body={"email": email, "display_name": "AuraFit Smoke Test"},
        timeout=timeout,
    )
    _require(status == 200, f"OTP request returned HTTP {status}: {data.get('detail') or data}")
    _require(data.get("status") == "sent", f"OTP request did not return sent: {data}")
    _require(not data.get("dev_otp"), "Production OTP response leaked dev_otp")
    return CheckResult("otp_request", True, f"OTP email accepted for {email}")


def _check_ops_status(api_base: str, ops_token: str, timeout: int) -> CheckResult:
    status, data = _json_request("GET", f"{api_base}/ops/status", ops_token=ops_token, timeout=timeout)
    _require(status == 200, f"/ops/status returned HTTP {status}: {data.get('detail') or data}")
    _require(data.get("status") == "ok", f"/ops/status did not return ok: {data}")
    health = data.get("health") or {}
    counts = data.get("counts") or {}
    _require(health.get("database_available") is True, "ops status reports unavailable database")
    _require((counts.get("users") or 0) >= 0, "ops status did not include user count")
    _require("jobs_by_status" in data, "ops status did not include jobs_by_status")
    return CheckResult("ops_status", True, "protected ops status is reachable")


def _check_authenticated_profile_access(
    api_base: str,
    token: str,
    expected_profile_name: str | None,
    profile_id: str | None,
    timeout: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []

    status, me = _json_request("GET", f"{api_base}/auth/me", token=token, timeout=timeout)
    _require(status == 200, f"/auth/me returned HTTP {status}: {me.get('detail') or me}")
    user = me.get("user") or {}
    _require(bool(user.get("id")), "/auth/me did not return a user id")
    results.append(CheckResult("auth_me", True, f"signed in as {user.get('email') or user.get('display_name')}"))

    status, data = _json_request("GET", f"{api_base}/auth/sessions", token=token, timeout=timeout)
    _require(status == 200, f"/auth/sessions returned HTTP {status}: {data.get('detail') or data}")
    sessions = data.get("sessions") or []
    _require(isinstance(sessions, list), "/auth/sessions did not return a sessions list")
    _require(len(sessions) > 0, "signed-in user has no saved profiles")
    results.append(CheckResult("saved_profiles", True, f"{len(sessions)} saved profile(s) visible"))

    if expected_profile_name:
        expected = expected_profile_name.strip().lower()
        names = [(session.get("profile_name") or "").strip().lower() for session in sessions]
        _require(expected in names, f"Expected profile '{expected_profile_name}' not found. Current: {names}")
        results.append(CheckResult("expected_profile", True, f"found '{expected_profile_name}'"))

    target = None
    if profile_id:
        target = next((session for session in sessions if session.get("job_id") == profile_id), None)
        _require(target is not None, f"Profile id {profile_id} is not in /auth/sessions")
    else:
        target = next((session for session in sessions if session.get("status") == "complete"), sessions[0])

    job_id = target.get("job_id")
    _require(bool(job_id), "Saved profile summary did not include job_id")

    status, profile = _json_request("GET", f"{api_base}/profile/{job_id}", token=token, timeout=timeout)
    _require(status == 200, f"/profile/{job_id} returned HTTP {status}: {profile.get('detail') or profile}")
    _require(profile.get("status") == "complete", f"Profile {job_id} is not complete: {profile.get('status')}")
    _require(bool(profile.get("profile")), f"Profile {job_id} did not include analysis payload")
    results.append(CheckResult("profile_fetch", True, f"profile {job_id} loads with analysis data"))

    return results


def _print_result(result: CheckResult) -> None:
    marker = "PASS" if result.ok else "FAIL"
    print(f"[{marker}] {result.name}: {result.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run production smoke checks against AuraFit without spending AI/image credits.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("AURAFIT_BASE_URL", DEFAULT_BASE_URL),
        help=f"Site base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--session-token",
        default=os.getenv("AURAFIT_SESSION_TOKEN"),
        help="Optional AuraFit bearer session token from a real logged-in browser session.",
    )
    parser.add_argument(
        "--expect-profile-name",
        default=os.getenv("AURAFIT_EXPECT_PROFILE_NAME"),
        help="Optional saved profile name that must be visible for the signed-in user.",
    )
    parser.add_argument(
        "--profile-id",
        default=os.getenv("AURAFIT_PROFILE_ID"),
        help="Optional specific saved profile/job id to fetch.",
    )
    parser.add_argument(
        "--request-otp-email",
        default=os.getenv("AURAFIT_SMOKE_EMAIL"),
        help="Optional email address for a real OTP delivery check. This sends one email.",
    )
    parser.add_argument(
        "--ops-token",
        default=os.getenv("AURAFIT_OPS_TOKEN"),
        help="Optional OPS_ADMIN_TOKEN for protected production ops status checks.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("AURAFIT_SMOKE_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))),
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_base = _api_base_url(args.base_url)
    started = time.time()
    results: list[CheckResult] = []

    try:
        results.append(_check_health(api_base, args.timeout))
        results.append(_check_auth_without_token(api_base, args.timeout))

        if args.request_otp_email:
            results.append(_request_otp(api_base, args.request_otp_email, args.timeout))

        if args.ops_token:
            results.append(_check_ops_status(api_base, args.ops_token, args.timeout))

        if args.session_token:
            results.extend(
                _check_authenticated_profile_access(
                    api_base,
                    args.session_token,
                    args.expect_profile_name,
                    args.profile_id,
                    args.timeout,
                )
            )
        else:
            results.append(CheckResult("authenticated_profile", True, "skipped; set AURAFIT_SESSION_TOKEN to verify profile visibility"))

        for result in results:
            _print_result(result)
        print(f"Smoke checks completed in {time.time() - started:.1f}s against {api_base}")
        return 0
    except SmokeFailure as exc:
        for result in results:
            _print_result(result)
        print(f"[FAIL] smoke: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
