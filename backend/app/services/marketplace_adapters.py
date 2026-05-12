from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.schemas import CatalogProduct, Marketplace, ProductColor


FLIPKART_DIRECTORY_URL = "https://affiliate-api.flipkart.net/affiliate/download/feeds/{tracking_id}.json"


def catalog_cache_path() -> Path:
    if settings.catalog_cache_file:
        return Path(settings.catalog_cache_file)
    return Path(settings.upload_dir) / "catalog" / "provider_products.json"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _amount(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("amount")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_affid(url: str, affiliate_id: str) -> str:
    if not url or not affiliate_id:
        return url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "affid" not in query:
        query["affid"] = [affiliate_id]
    new_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def _append_query_param(url: str, key: str, value: str) -> str:
    if not url or not key or not value:
        return url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if key not in query:
        query[key] = [value]
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))


def build_affiliate_url(marketplace: Marketplace, product_url: str, sub_id: str = "") -> str:
    if not product_url:
        return product_url

    template = {
        Marketplace.myntra: settings.myntra_affiliate_url_template,
        Marketplace.snitch: settings.snitch_affiliate_url_template,
        Marketplace.ajio: settings.ajio_affiliate_url_template,
    }.get(marketplace, "")

    if template:
        encoded_url = urllib.parse.quote(product_url, safe="")
        return template.format(
            url=encoded_url,
            raw_url=product_url,
            sub_id=urllib.parse.quote(sub_id, safe=""),
            marketplace=marketplace.value,
        )

    if marketplace == Marketplace.amazon and settings.amazon_associate_tag:
        return _append_query_param(product_url, "tag", settings.amazon_associate_tag)

    return product_url


def _image_url(image_urls: Any) -> str:
    if isinstance(image_urls, dict):
        preferred_keys = ["800x800", "unknown", "400x400", "200x200"]
        for key in preferred_keys:
            if image_urls.get(key):
                return image_urls[key]
        for value in image_urls.values():
            if value:
                return str(value)
    if isinstance(image_urls, list) and image_urls:
        return str(image_urls[0])
    return ""


def _infer_gender(*parts: str) -> str:
    haystack = " ".join(parts).lower()
    if re.search(r"\b(women|woman|female|girls?|ladies)\b", haystack):
        return "women"
    if re.search(r"\b(men|man|male|boys?)\b", haystack):
        return "men"
    return "unisex"


def _category_parts(category_path: Any) -> list[str]:
    if isinstance(category_path, list):
        parts = []
        for item in category_path:
            if isinstance(item, dict):
                parts.append(_normalize_text(item.get("title") or item.get("name")))
            else:
                parts.append(_normalize_text(item))
        return [part for part in parts if part]
    if isinstance(category_path, str):
        return [part.strip() for part in re.split(r"[>/|]", category_path) if part.strip()]
    return []


def _tags(*parts: str) -> list[str]:
    raw = " ".join(parts).lower()
    tokens = re.findall(r"[a-z0-9]+", raw)
    ignored = {"and", "for", "with", "the", "new", "pack", "set"}
    return sorted({token for token in tokens if len(token) > 2 and token not in ignored})[:20]


def _parse_product_entry(entry: dict[str, Any], affiliate_id: str) -> CatalogProduct | None:
    base = entry.get("productBaseInfoV1") or entry.get("productBaseInfo") or entry
    if "productAttributes" in base:
        base = base["productAttributes"]

    product_id = _normalize_text(_first_present(
        base.get("productId"),
        base.get("id"),
        entry.get("productId"),
    ))
    title = _normalize_text(_first_present(
        base.get("title"),
        base.get("name"),
        entry.get("title"),
    ))
    product_url = _normalize_text(_first_present(
        base.get("productUrl"),
        base.get("url"),
        entry.get("productUrl"),
    ))
    if not product_id and product_url:
        product_id = urllib.parse.urlparse(product_url).path.strip("/").split("/")[-1]
    if not product_id or not title or not product_url:
        return None

    brand = _normalize_text(_first_present(base.get("productBrand"), base.get("brand"))) or "Flipkart"
    color_name = _normalize_text(_first_present(base.get("color"), base.get("colorGroup"))) or "Assorted"
    category_parts = _category_parts(base.get("categoryPath") or entry.get("categoryPath"))
    category = category_parts[0].lower().replace(" ", "_") if category_parts else "clothing"
    sub_category = category_parts[-1].lower().replace(" ", "_") if category_parts else "general"
    gender = _infer_gender(title, sub_category, " ".join(category_parts))

    selling_price = _amount(_first_present(
        base.get("sellingPrice"),
        base.get("flipkartSellingPrice"),
        base.get("specialPrice"),
    ))
    mrp = _amount(_first_present(base.get("maximumRetailPrice"), base.get("mrp")))
    price = selling_price or mrp
    if price is None:
        return None

    raw_size = _normalize_text(_first_present(base.get("size"), base.get("sizeUnit")))
    sizes = [raw_size] if raw_size else []
    in_stock = bool(_first_present(base.get("inStock"), base.get("isAvailable"), True))
    available_sizes = sizes if in_stock else []

    return CatalogProduct(
        id=f"flipkart-{product_id}",
        title=title,
        brand=brand,
        marketplace=Marketplace.flipkart,
        category=category,
        sub_category=sub_category,
        gender=gender,
        image_url=_image_url(base.get("imageUrls")),
        product_url=product_url,
        affiliate_url=_append_affid(product_url, affiliate_id),
        price_inr=price,
        original_price_inr=mrp,
        colors=[ProductColor(name=color_name, undertone_tags=[], season_tags=[])],
        sizes=sizes,
        available_sizes=available_sizes,
        fit=None,
        fabric=None,
        pattern=None,
        tags=_tags(title, brand, color_name, " ".join(category_parts)),
        rating=_amount(_first_present(base.get("averageRating"), base.get("rating"))),
        returnable=True,
    )


def _product_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    possible = [
        payload.get("productInfoList"),
        payload.get("products"),
        payload.get("productInfo"),
    ]
    nested_products = payload.get("products")
    if isinstance(nested_products, dict):
        possible.extend([
            nested_products.get("productInfoList"),
            nested_products.get("productInfo"),
        ])

    for value in possible:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


class FlipkartAffiliateAdapter:
    provider = Marketplace.flipkart

    def __init__(
        self,
        affiliate_id: str | None = None,
        affiliate_token: str | None = None,
    ):
        self.affiliate_id = affiliate_id or settings.flipkart_affiliate_id
        self.affiliate_token = affiliate_token or settings.flipkart_affiliate_token

    @property
    def configured(self) -> bool:
        return bool(self.affiliate_id and self.affiliate_token)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Fk-Affiliate-Id": self.affiliate_id,
            "Fk-Affiliate-Token": self.affiliate_token,
        }

    def fetch_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_feed_directory(self) -> dict[str, Any]:
        url = FLIPKART_DIRECTORY_URL.format(tracking_id=self.affiliate_id)
        return self.fetch_json(url)

    def feed_urls(
        self,
        directory: dict[str, Any],
        categories: list[str] | None = None,
        variant: str = "v1.1.0",
    ) -> list[str]:
        listings = (
            directory.get("apiGroups", {})
            .get("affiliate", {})
            .get("apiListings", {})
        )
        selected = {category.strip().lower() for category in categories or [] if category.strip()}
        urls: list[str] = []
        for key, listing in listings.items():
            if selected and key.lower() not in selected:
                continue
            variants = listing.get("availableVariants", {})
            feed = variants.get(variant) or variants.get("v1.1.0") or variants.get("v0.1.0") or {}
            url = feed.get("get")
            if url:
                urls.append(url)
        return urls

    def download_payloads(self, url: str) -> list[Any]:
        request = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "")

        if "zip" in content_type.lower() or content[:2] == b"PK":
            payloads: list[Any] = []
            with zipfile.ZipFile(BytesIO(content)) as archive:
                for name in archive.namelist():
                    if not name.lower().endswith(".json"):
                        continue
                    raw = archive.read(name).decode("utf-8")
                    payloads.extend(self._loads_json_or_lines(raw))
            return payloads

        return self._loads_json_or_lines(content.decode("utf-8"))

    def _loads_json_or_lines(self, raw: str) -> list[Any]:
        raw = raw.strip()
        if not raw:
            return []
        try:
            return [json.loads(raw)]
        except json.JSONDecodeError:
            payloads = []
            for line in raw.splitlines():
                line = line.strip().rstrip(",")
                if not line:
                    continue
                try:
                    payloads.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return payloads

    def normalize_payloads(self, payloads: list[Any], limit: int | None = None) -> list[CatalogProduct]:
        products: list[CatalogProduct] = []
        seen: set[str] = set()
        for payload in payloads:
            for entry in _product_entries(payload):
                product = _parse_product_entry(entry, self.affiliate_id)
                if not product or product.id in seen:
                    continue
                seen.add(product.id)
                products.append(product)
                if limit and len(products) >= limit:
                    return products
        return products

    def sync(
        self,
        categories: list[str] | None = None,
        max_products_per_category: int = 100,
    ) -> list[CatalogProduct]:
        if not self.configured:
            return []

        directory = self.fetch_feed_directory()
        products: list[CatalogProduct] = []
        for url in self.feed_urls(directory, categories=categories):
            payloads = self.download_payloads(url)
            products.extend(self.normalize_payloads(payloads, limit=max_products_per_category))
        return products


def read_cached_provider_products() -> list[CatalogProduct]:
    path = catalog_cache_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [CatalogProduct(**item) for item in data.get("products", [])]


def write_cached_provider_products(
    products: list[CatalogProduct],
    replace_marketplaces: set[Marketplace] | None = None,
) -> Path:
    path = catalog_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_cached_provider_products()
    if replace_marketplaces:
        existing = [product for product in existing if product.marketplace not in replace_marketplaces]

    merged: dict[str, CatalogProduct] = {product.id: product for product in existing}
    for product in products:
        merged[product.id] = product

    path.write_text(json.dumps({
        "products": [product.model_dump(mode="json") for product in merged.values()],
    }, indent=2))
    return path
