from __future__ import annotations

import os
import json
from typing import Optional

from app.config import settings
from app.models.schemas import (
    StyleProfile,
    OutfitRecommendation,
    OutfitItem,
    RecommendationCategory,
    RecommendationSubCategory,
    RecommendationSource,
)
from app.services.llm_client import (
    openrouter_chat_text,
    openrouter_configured,
    parse_json_response,
)
from app.services.cost_ledger import capture_response_usage
from app.services.rule_engine import rule_engine


def _coerce_outfit_payload(payload) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("outfits", "recommendations", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _build_conditions(profile: StyleProfile) -> dict[str, str]:
    """Build a conditions dict from a StyleProfile for rule matching."""
    conditions = {
        "gender": profile.gender.value,
        "body_shape": profile.body_type.shape,
        "body_build": profile.body_type.build,
        "height_category": profile.body_type.height_category,
        "undertone": profile.skin_tone.undertone,
        "fitzpatrick": profile.skin_tone.fitzpatrick,
    }
    if profile.face_shape:
        conditions["face_shape"] = profile.face_shape.value
    if profile.color_season:
        conditions["color_season"] = profile.color_season.value
    if profile.proportions:
        if profile.proportions.shoulder_hip_ratio:
            conditions["shoulder_hip_ratio"] = profile.proportions.shoulder_hip_ratio
        if profile.proportions.torso_leg_ratio:
            conditions["torso_leg_ratio"] = profile.proportions.torso_leg_ratio
    if profile.eye_color:
        conditions["eye_color"] = profile.eye_color
    return conditions


def get_rule_recommendations(
    profile: StyleProfile,
    category_prefix: Optional[str] = None,
) -> list[dict]:
    """Get all matching rule-based recommendations for a profile."""
    conditions = _build_conditions(profile)
    if category_prefix:
        return rule_engine.match_by_category(conditions, category_prefix)
    return rule_engine.match(conditions)


def get_mock_recommendations(profile: StyleProfile) -> dict[str, list[OutfitRecommendation]]:
    """Return mock recommendations organized by category."""
    western = [
        OutfitRecommendation(
            id="outfit-1",
            name="Weekend Wanderer",
            description="A relaxed earthy outfit perfect for daytime errands or brunch.",
            why_it_works="The rust and olive tones complement your warm olive skin, while the relaxed fits balance your athletic upper body.",
            items=[
                OutfitItem(name="Relaxed Linen Shirt in Natural", price_usd=45.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=300&h=400&fit=crop", brand="Zara", category="Tops"),
                OutfitItem(name="Wide Leg Chinos in Olive", price_usd=35.99, buy_url="https://www.hm.com/", image_url="https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=300&h=400&fit=crop", brand="H&M", category="Bottoms"),
                OutfitItem(name="Suede Low-Top Sneakers in Sand", price_usd=59.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=300&h=400&fit=crop", brand="Zara", category="Shoes"),
            ],
            total_price_usd=141.79,
            style_tags=["Casual", "Earthy", "Weekend"],
            image_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.clothing,
            sub_category=RecommendationSubCategory.western,
            source=RecommendationSource.ai,
        ),
        OutfitRecommendation(
            id="outfit-2",
            name="Urban Minimalist",
            description="Clean lines and neutral tones for an effortlessly cool city look.",
            why_it_works="Monochrome neutrals with camel accents create a refined look that lets your natural coloring take center stage.",
            items=[
                OutfitItem(name="Oversized Cotton Tee in Ecru", price_usd=19.99, buy_url="https://www.hm.com/", image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=300&h=400&fit=crop", brand="H&M", category="Tops"),
                OutfitItem(name="Straight Leg Jeans in Washed Black", price_usd=49.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1542272604-787c3835535d?w=300&h=400&fit=crop", brand="Zara", category="Bottoms"),
                OutfitItem(name="Minimal Leather Belt in Brown", price_usd=25.99, buy_url="https://www.asos.com/", image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=400&fit=crop", brand="ASOS", category="Accessories"),
            ],
            total_price_usd=95.88,
            style_tags=["Minimal", "Urban", "Everyday"],
            image_url="https://images.unsplash.com/photo-1490578474895-699cd4e2cf59?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.clothing,
            sub_category=RecommendationSubCategory.western,
            source=RecommendationSource.ai,
        ),
        OutfitRecommendation(
            id="outfit-3",
            name="Smart Casual Friday",
            description="Elevated basics that transition from office to after-work drinks.",
            why_it_works="Structured pieces like the blazer draw attention upward while earth tones keep the palette warm and flattering.",
            items=[
                OutfitItem(name="Unstructured Knit Blazer in Camel", price_usd=89.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=300&h=400&fit=crop", brand="Zara", category="Outerwear"),
                OutfitItem(name="Slim Fit Oxford Shirt in White", price_usd=34.90, buy_url="https://www.uniqlo.com/", image_url="https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=300&h=400&fit=crop", brand="Uniqlo", category="Tops"),
                OutfitItem(name="Tapered Chinos in Dark Olive", price_usd=39.99, buy_url="https://www.hm.com/", image_url="https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=300&h=400&fit=crop", brand="H&M", category="Bottoms"),
                OutfitItem(name="Leather Derby Shoes in Cognac", price_usd=79.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=300&h=400&fit=crop", brand="Zara", category="Shoes"),
            ],
            total_price_usd=244.69,
            style_tags=["Smart Casual", "Office", "Elevated"],
            image_url="https://images.unsplash.com/photo-1617137968427-85924c800a22?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.clothing,
            sub_category=RecommendationSubCategory.western,
            source=RecommendationSource.ai,
        ),
    ]

    indian = [
        OutfitRecommendation(
            id="outfit-indian-1",
            name="Festival Classic",
            description="A refined kurta set perfect for festive gatherings and celebrations.",
            why_it_works="The deep rust tone complements your warm undertone beautifully, while the straight-cut kurta balances broader shoulders.",
            items=[
                OutfitItem(name="Silk Blend Kurta in Rust", price_usd=65.00, buy_url="https://www.fabindia.com/", image_url="https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=300&h=400&fit=crop", brand="FabIndia", category="Kurta"),
                OutfitItem(name="Churidar in Off-White", price_usd=25.00, buy_url="https://www.fabindia.com/", image_url="https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop", brand="FabIndia", category="Bottoms"),
                OutfitItem(name="Kolhapuri Chappals in Tan", price_usd=35.00, buy_url="https://www.fabindia.com/", image_url="https://images.unsplash.com/photo-1603487742131-4160ec999306?w=300&h=400&fit=crop", brand="FabIndia", category="Footwear"),
            ],
            total_price_usd=125.00,
            style_tags=["Festive", "Traditional", "Ethnic"],
            image_url="https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.clothing,
            sub_category=RecommendationSubCategory.indian,
            source=RecommendationSource.rule,
        ),
    ]

    accessories = [
        OutfitRecommendation(
            id="acc-1",
            name="Essential Accessories Kit",
            description="Foundational accessories that elevate every outfit in your wardrobe.",
            why_it_works="Warm-toned metals and cognac leather create a cohesive accessory palette that complements your skin tone.",
            items=[
                OutfitItem(name="Minimal Watch in Rose Gold", price_usd=59.90, buy_url="https://www.cosstores.com/", image_url="https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=300&h=400&fit=crop", brand="COS", category="Watch"),
                OutfitItem(name="Leather Belt in Cognac", price_usd=29.99, buy_url="https://www.asos.com/", image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=400&fit=crop", brand="ASOS", category="Belt"),
            ],
            total_price_usd=89.89,
            style_tags=["Accessories", "Essential", "Everyday"],
            image_url="https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.accessories,
            sub_category=RecommendationSubCategory.general,
            source=RecommendationSource.rule,
        ),
    ]

    footwear = [
        OutfitRecommendation(
            id="foot-1",
            name="Versatile Footwear Collection",
            description="Three essential shoe styles that cover casual, smart, and active occasions.",
            why_it_works="Earth-toned footwear in varied styles ensures you have the right shoe for every outfit and occasion.",
            items=[
                OutfitItem(name="Suede Low-Top Sneakers in Sand", price_usd=59.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=300&h=400&fit=crop", brand="Zara", category="Sneakers"),
                OutfitItem(name="Leather Chelsea Boots in Dark Brown", price_usd=89.99, buy_url="https://www.asos.com/", image_url="https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=300&h=400&fit=crop", brand="ASOS", category="Boots"),
                OutfitItem(name="Woven Leather Sandals in Tan", price_usd=49.90, buy_url="https://www.zara.com/", image_url="https://images.unsplash.com/photo-1603487742131-4160ec999306?w=300&h=400&fit=crop", brand="Zara", category="Sandals"),
            ],
            total_price_usd=199.79,
            style_tags=["Footwear", "Versatile", "Essential"],
            image_url="https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.footwear,
            sub_category=RecommendationSubCategory.general,
            source=RecommendationSource.rule,
        ),
    ]

    grooming = [
        OutfitRecommendation(
            id="groom-1",
            name="Grooming Essentials",
            description="Foundational grooming recommendations based on your face shape and coloring.",
            why_it_works="An oval face shape is versatile — most beard styles and haircuts work well, so focus on enhancing your strong features.",
            items=[],
            total_price_usd=0,
            style_tags=["Grooming", "Face Shape", "Hair"],
            image_url="https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=600&h=800&fit=crop",
            recommendation_category=RecommendationCategory.grooming,
            sub_category=RecommendationSubCategory.general,
            source=RecommendationSource.rule,
        ),
    ]

    return {
        "western": western,
        "indian": indian,
        "accessories": accessories,
        "footwear": footwear,
        "grooming": grooming,
    }


async def get_recommendations(
    profile: StyleProfile,
    budget_min: float = 50,
    budget_max: float = 300,
    style_preferences: list[str] | None = None,
    wear_type: str = "all",
    occasion: list[str] | None = None,
    goals: list[str] | None = None,
) -> dict[str, list[OutfitRecommendation]]:
    """Generate recommendations combining rule engine + AI."""

    if settings.mock_mode:
        return get_mock_recommendations(profile)

    # Step 1: Get rule-based recommendations
    conditions = _build_conditions(profile)
    if occasion:
        conditions["occasion"] = occasion[0]  # Primary occasion

    rule_results = rule_engine.match(conditions)

    # Step 2: Get AI-generated outfit recommendations
    wear_instruction = ""
    if wear_type == "indian":
        wear_instruction = "Focus on Indian wear: kurta, sherwani, bandhgala, pathani for men; saree, lehenga, salwar kameez, kurti for women."
    elif wear_type == "fusion":
        wear_instruction = "Focus on Indo-western fusion outfits that blend Indian and Western elements."
    elif wear_type == "western":
        wear_instruction = "Focus on Western wear only."
    else:
        wear_instruction = "Include a mix of Western, Indian, and Fusion outfits."

    occasion_text = f"Occasions: {', '.join(occasion)}" if occasion else ""
    goals_text = f"Style goals: {', '.join(goals)}" if goals else ""

    prompt = f"""Based on this style profile, generate 10 complete outfit recommendations as a JSON array.

Profile:
- Gender: {profile.gender.value}
- Skin tone: {profile.skin_tone.label} (Fitzpatrick {profile.skin_tone.fitzpatrick}, {profile.skin_tone.undertone} undertone)
- Body type: {profile.body_type.shape}, {profile.body_type.build} build, {profile.body_type.height_category} height
- Face shape: {profile.face_shape.value if profile.face_shape else 'unknown'}
- Color season: {profile.color_season.value if profile.color_season else 'unknown'}
- Style vibes: {', '.join(profile.style_vibes)}
- Best colors: {', '.join(c.name for c in profile.color_palette)}
- Budget range: ${budget_min}-${budget_max} per outfit
- Style preferences: {', '.join(style_preferences or [])}
{occasion_text}
{goals_text}

{wear_instruction}

Each outfit must have this exact JSON structure:
{{
  "id": "outfit-N",
  "name": "Outfit Name",
  "description": "One sentence description",
  "why_it_works": "Why this works for this specific person",
  "items": [
    {{
      "name": "Brand Product Name in Color",
      "price_usd": 49.90,
      "buy_url": "https://www.brand.com/",
      "image_url": "https://images.unsplash.com/photo-ID?w=300&h=400&fit=crop",
      "brand": "Brand Name",
      "category": "Tops|Bottoms|Shoes|Outerwear|Accessories|Kurta|Lehenga|Saree|Dupatta"
    }}
  ],
  "total_price_usd": 149.90,
  "style_tags": ["tag1", "tag2"],
  "image_url": "https://images.unsplash.com/photo-ID?w=600&h=800&fit=crop",
  "recommendation_category": "clothing",
  "sub_category": "western|indian|fusion",
  "source": "ai",
  "confidence": 0.85
}}

Use real brands with realistic product names and prices.
Use positive, empowering language in why_it_works. Focus on what flatters.
Return ONLY the JSON array."""

    if openrouter_configured():
        response_text = openrouter_chat_text(
            [{"role": "user", "content": prompt}],
            model=settings.openrouter_text_model,
            max_tokens=3600,
            operation="recommendations.text",
        )
        results = parse_json_response(response_text)
    else:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        fallback_model = "claude-sonnet-4-6-20250514"
        message = client.messages.create(
            model=fallback_model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        capture_response_usage(
            message,
            operation="recommendations.text",
            provider="anthropic",
            model=fallback_model,
            details={"max_tokens": 4000},
        )
        results = json.loads(message.content[0].text)

    outfit_payloads = _coerce_outfit_payload(results)
    if not outfit_payloads:
        return {
            "western": [],
            "indian": [],
            "fusion": [],
            "accessories": [],
            "footwear": [],
            "grooming": [],
        }

    ai_recs: list[OutfitRecommendation] = []
    for payload in outfit_payloads:
        try:
            ai_recs.append(OutfitRecommendation(**payload))
        except Exception:
            continue
    if not ai_recs:
        return {
            "western": [],
            "indian": [],
            "fusion": [],
            "accessories": [],
            "footwear": [],
            "grooming": [],
        }

    # Step 3: Organize by sub-category
    categorized: dict[str, list[OutfitRecommendation]] = {}
    for rec in ai_recs:
        key = rec.sub_category.value if hasattr(rec.sub_category, 'value') else rec.sub_category
        if key not in categorized:
            categorized[key] = []
        categorized[key].append(rec)

    return categorized
