from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.models.schemas import (
    CatalogProduct,
    FitProfile,
    ProductMatch,
    StyleProfile,
)
from app.services.marketplace_adapters import catalog_cache_path, read_cached_provider_products


CATALOG_PATH = Path(__file__).parent.parent / "catalog" / "seed_products.yaml"


BODY_TAGS: dict[str, set[str]] = {
    "inverted-triangle": {"straight-leg", "relaxed-lower-body", "v-neck", "regular-fit", "layering"},
    "triangle": {"structured", "upper-body-detail", "dark-bottom", "straight-cut"},
    "pear": {"structured", "upper-body-detail", "dark-bottom", "straight-cut"},
    "rectangle": {"layering", "waist-definition", "textured", "structured"},
    "hourglass": {"wrap", "waist-definition", "tailored"},
    "oval": {"vertical", "straight-cut", "tailored", "regular-fit"},
}

HEIGHT_TAGS: dict[str, set[str]] = {
    "petite": {"vertical", "high-rise", "cropped", "minimal", "straight-cut"},
    "average": {"balanced", "regular-fit", "everyday"},
    "tall": {"full-length", "oversized", "wide-leg", "substantial"},
}

FIT_TAGS: dict[str, set[str]] = {
    "slim": {"slim-fit", "tailored"},
    "regular": {"regular-fit", "balanced", "straight-cut"},
    "relaxed": {"regular-fit", "relaxed-lower-body", "layering"},
    "oversized": {"layering", "oversized", "textured"},
}


@lru_cache
def load_seed_catalog() -> list[CatalogProduct]:
    if not CATALOG_PATH.exists():
        return []

    data = yaml.safe_load(CATALOG_PATH.read_text()) or {}
    return [CatalogProduct(**item) for item in data.get("products", [])]


@lru_cache
def load_cached_catalog() -> list[CatalogProduct]:
    return read_cached_provider_products()


def clear_catalog_cache() -> None:
    load_seed_catalog.cache_clear()
    load_cached_catalog.cache_clear()


def load_catalog_products() -> list[CatalogProduct]:
    products = load_seed_catalog() + load_cached_catalog()
    seen: set[str] = set()
    deduped: list[CatalogProduct] = []
    for product in products:
        if product.id in seen:
            continue
        seen.add(product.id)
        deduped.append(product)
    return deduped


def catalog_counts() -> tuple[int, int, str]:
    return len(load_seed_catalog()), len(load_cached_catalog()), str(catalog_cache_path())


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("_", "-")


def _profile_color_names(profile: StyleProfile) -> set[str]:
    return {_normalize(color.name) for color in profile.color_palette}


def _season_family(profile: StyleProfile) -> str:
    if not profile.color_season:
        return ""
    return profile.color_season.value.split("_", 1)[0]


def _size_available(product: CatalogProduct, fit_profile: FitProfile) -> tuple[bool, str | None]:
    preferred_sizes = [
        fit_profile.shirt_size,
        fit_profile.bottom_size,
        fit_profile.shoe_size,
    ]
    available = {_normalize(size) for size in product.available_sizes}
    for size in preferred_sizes:
        if size and _normalize(size) in available:
            return True, size
    return False, next((size for size in preferred_sizes if size), None)


def _score_product(
    product: CatalogProduct,
    profile: StyleProfile,
    fit_profile: FitProfile,
    budget_max_inr: float | None,
) -> ProductMatch:
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    profile_colors = _profile_color_names(profile)
    undertone = _normalize(profile.skin_tone.undertone)
    season = profile.color_season.value if profile.color_season else ""
    season_family = _season_family(profile)
    product_tags = {_normalize(tag) for tag in product.tags}

    for color in product.colors:
        color_name = _normalize(color.name)
        color_undertones = {_normalize(tag) for tag in color.undertone_tags}
        color_seasons = {_normalize(tag) for tag in color.season_tags}

        if color_name in profile_colors:
            score += 30
            reasons.append(f"{color.name} is in your recommended palette")
            break

        if undertone and undertone in color_undertones:
            score += 18
            reasons.append(f"{color.name} supports your {profile.skin_tone.undertone} undertone")
            break

        if season and _normalize(season) in color_seasons:
            score += 24
            reasons.append(f"{color.name} aligns with {season.replace('_', ' ')}")
            break

        if season_family and any(tag.startswith(season_family) for tag in color_seasons):
            score += 12
            reasons.append(f"{color.name} stays close to your seasonal family")
            break

    body_shape = _normalize(profile.body_type.shape)
    body_matches = BODY_TAGS.get(body_shape, set()) & product_tags
    if body_matches:
        score += 18
        reasons.append("Silhouette works with your body architecture")

    height_category = _normalize(profile.body_type.height_category)
    height_matches = HEIGHT_TAGS.get(height_category, set()) & product_tags
    if height_matches:
        score += 10
        reasons.append(f"Proportions suit {profile.body_type.height_category} height")

    preferred_fit = _normalize(fit_profile.preferred_fit)
    fit_matches = FIT_TAGS.get(preferred_fit, set()) & product_tags
    if preferred_fit and fit_matches:
        score += 10
        reasons.append(f"Matches your {fit_profile.preferred_fit} fit preference")
    elif fit_profile.preferred_fit and product.fit:
        warnings.append(f"Fit is listed as {product.fit}")

    size_ok, requested_size = _size_available(product, fit_profile)
    if requested_size and size_ok:
        score += 15
        reasons.append(f"Your size {requested_size} appears available")
    elif requested_size:
        score -= 15
        warnings.append(f"Your size {requested_size} may not be in stock")

    if budget_max_inr:
        if product.price_inr <= budget_max_inr:
            score += 8
            reasons.append("Within your selected budget")
        else:
            score -= 10
            warnings.append("Above your selected budget")

    if product.rating and product.rating >= 4:
        score += min(5, (product.rating - 4) * 5 + 2)

    if product.returnable:
        score += 2
    else:
        warnings.append("Check return policy before buying")

    if not reasons:
        reasons.append("Useful wardrobe option, but not a top trait match")

    return ProductMatch(
        product=product,
        score=round(max(score, 0), 1),
        reasons=reasons[:4],
        warnings=warnings[:3],
    )


def recommend_products(
    profile: StyleProfile,
    fit_profile: FitProfile,
    budget_max_inr: float | None = None,
    limit: int = 8,
) -> list[ProductMatch]:
    products = load_catalog_products()
    gender = _normalize(profile.gender.value)

    matches = []
    for product in products:
        product_gender = _normalize(product.gender)
        if product_gender not in {gender, "unisex"}:
            continue
        matches.append(_score_product(product, profile, fit_profile, budget_max_inr))

    return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]
