from __future__ import annotations

import csv
import json
import re
from io import StringIO
from typing import Any

from app.models.schemas import CatalogProduct, Marketplace, ProductColor
from app.services.marketplace_adapters import build_affiliate_url


FIELD_ALIASES: dict[str, list[str]] = {
    "id": ["id", "product_id", "sku", "item_id", "asin", "style_id"],
    "title": ["title", "name", "product_name", "product_title"],
    "brand": ["brand", "brand_name"],
    "category": ["category", "department", "vertical"],
    "sub_category": ["sub_category", "subcategory", "product_type", "article_type"],
    "gender": ["gender", "target_gender", "audience"],
    "image_url": ["image_url", "image", "image_link", "imageurl", "product_image"],
    "product_url": ["product_url", "url", "link", "product_link", "landing_url"],
    "affiliate_url": ["affiliate_url", "deeplink", "deep_link", "tracking_url"],
    "price_inr": ["price_inr", "price", "selling_price", "sale_price", "discounted_price"],
    "original_price_inr": ["original_price_inr", "mrp", "original_price", "list_price"],
    "color": ["color", "colour", "color_name", "base_colour"],
    "color_hex": ["color_hex", "hex", "hex_color"],
    "sizes": ["sizes", "size", "all_sizes"],
    "available_sizes": ["available_sizes", "in_stock_sizes", "available_size"],
    "fit": ["fit", "fit_type"],
    "fabric": ["fabric", "material"],
    "pattern": ["pattern", "print"],
    "tags": ["tags", "keywords", "style_tags"],
    "rating": ["rating", "average_rating"],
    "returnable": ["returnable", "is_returnable"],
}


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def _value(row: dict[str, Any], field: str) -> Any:
    normalized = {_normalize_key(key): value for key, value in row.items()}
    for alias in FIELD_ALIASES[field]:
        value = normalized.get(_normalize_key(alias))
        if value not in (None, "", [], {}):
            return value
    return None


def _split_list(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[,|;/]", str(value)) if item.strip()]


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _bool(value: Any, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "returnable"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def _infer_gender(*parts: str) -> str:
    haystack = " ".join(parts).lower()
    if re.search(r"\b(women|woman|female|girls?|ladies)\b", haystack):
        return "women"
    if re.search(r"\b(men|man|male|boys?)\b", haystack):
        return "men"
    return "unisex"


def _rows_from_csv(raw: str) -> list[dict[str, Any]]:
    return list(csv.DictReader(StringIO(raw)))


def _rows_from_json(raw: str) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("products", "items", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def parse_feed_rows(content: bytes, filename: str) -> list[dict[str, Any]]:
    raw = content.decode("utf-8-sig")
    if filename.lower().endswith(".csv"):
        return _rows_from_csv(raw)
    return _rows_from_json(raw)


def normalize_feed_products(
    rows: list[dict[str, Any]],
    marketplace: Marketplace,
    sub_id: str = "",
) -> list[CatalogProduct]:
    products: list[CatalogProduct] = []
    seen: set[str] = set()

    for row in rows:
        title = str(_value(row, "title") or "").strip()
        product_url = str(_value(row, "product_url") or "").strip()
        price = _float(_value(row, "price_inr"))
        if not title or not product_url or price is None:
            continue

        raw_id = str(_value(row, "id") or "").strip()
        product_id = f"{marketplace.value}-{_slug(raw_id or product_url or title)}"
        if product_id in seen:
            continue
        seen.add(product_id)

        brand = str(_value(row, "brand") or marketplace.value.title()).strip()
        category = str(_value(row, "category") or "clothing").strip().lower().replace(" ", "_")
        sub_category = str(_value(row, "sub_category") or "general").strip().lower().replace(" ", "_")
        gender = str(_value(row, "gender") or "").strip().lower() or _infer_gender(title, category, sub_category)
        color_name = str(_value(row, "color") or "Assorted").strip()
        sizes = _split_list(_value(row, "sizes"))
        available_sizes = _split_list(_value(row, "available_sizes")) or sizes
        tags = _split_list(_value(row, "tags"))

        affiliate_url = str(_value(row, "affiliate_url") or "").strip()
        if not affiliate_url:
            affiliate_url = build_affiliate_url(marketplace, product_url, sub_id=sub_id)

        products.append(CatalogProduct(
            id=product_id,
            title=title,
            brand=brand,
            marketplace=marketplace,
            category=category,
            sub_category=sub_category,
            gender=gender,
            image_url=str(_value(row, "image_url") or "").strip(),
            product_url=product_url,
            affiliate_url=affiliate_url,
            price_inr=price,
            original_price_inr=_float(_value(row, "original_price_inr")),
            colors=[ProductColor(
                name=color_name,
                hex=str(_value(row, "color_hex") or "").strip() or None,
                undertone_tags=[],
                season_tags=[],
            )],
            sizes=sizes,
            available_sizes=available_sizes,
            fit=str(_value(row, "fit") or "").strip() or None,
            fabric=str(_value(row, "fabric") or "").strip() or None,
            pattern=str(_value(row, "pattern") or "").strip() or None,
            tags=tags,
            rating=_float(_value(row, "rating")),
            returnable=_bool(_value(row, "returnable")),
        ))

    return products
