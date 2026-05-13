"""
Catalog loader and product ranker.
Loads seed data from JSON, ranks products against a StyleProfile.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.schemas import StyleProfile


_CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "seed_catalog.json"
_catalog: list[dict] = []


def load_catalog() -> list[dict]:
    """Load product catalog from seed JSON (cached in-process)."""
    global _catalog
    if not _catalog:
        try:
            with open(_CATALOG_PATH) as f:
                _catalog = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load seed catalog: {e}")
            _catalog = []
    return _catalog


def _score_product(product: dict, profile: StyleProfile, gender: str) -> tuple[float, list[str]]:
    """
    Score a product 0.0–1.0 based on how well it matches the profile.
    Returns (score, reasons).
    """
    score = 0.0
    reasons: list[str] = []

    # Gender match
    prod_gender = product.get("gender", "all")
    if prod_gender != "all" and prod_gender != gender:
        return -1.0, []  # Hard exclude

    # Undertone match
    user_undertone = profile.skin_tone.undertone.lower()
    best_undertones: list[str] = product.get("best_for_undertone", [])
    if user_undertone in best_undertones:
        score += 0.35
        reasons.append(f"Complements your {user_undertone} undertone")

    # Color season match
    if profile.color_season:
        season = profile.color_season.value
        best_seasons: list[str] = product.get("best_for_season", [])
        if season in best_seasons:
            score += 0.30
            reasons.append("Suits your color season palette")

    # Body type match
    best_body: list[str] = product.get("best_for_body", [])
    if profile.body_type.shape in best_body:
        score += 0.25
        reasons.append(f"Flatters your {profile.body_type.shape} silhouette")

    # Mild base score so all gender-matched products appear
    score += 0.10

    return round(score, 2), reasons


def get_ranked_products(
    profile: StyleProfile,
    gender: str = "men",
    wear_type: str = "all",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """
    Return ranked products with match scores and reasons.
    """
    catalog = load_catalog()
    scored: list[tuple[float, dict]] = []

    for product in catalog:
        # Filter by wear type
        prod_sub = product.get("sub_category", "western")
        if wear_type not in ("all", prod_sub):
            continue

        score, reasons = _score_product(product, profile, gender)
        if score < 0:
            continue  # Gender mismatch

        result = dict(product)
        result["match_score"] = score
        result["why_it_suits_you"] = " · ".join(reasons) if reasons else "A versatile choice for your wardrobe."
        scored.append((score, result))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]
