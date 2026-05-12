from __future__ import annotations

import base64
import json
from io import BytesIO

from app.config import settings
from app.models.schemas import (
    StyleProfile,
    SkinTone,
    BodyType,
    Proportions,
    ColorRecommendation,
    Gender,
    FaceShape,
    ColorSeason,
)
from app.services.llm_client import (
    openrouter_chat_text,
    openrouter_configured,
    parse_json_response,
)
from app.services.cost_ledger import capture_response_usage


def _media_type(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


def _encode_image_for_llm(path: str) -> tuple[str, str]:
    """Resize images before LLM vision calls to keep latency and token cost sane."""
    from PIL import Image

    media_type = _media_type(path)
    with Image.open(path) as image:
        image.thumbnail(
            (settings.llm_image_max_dimension, settings.llm_image_max_dimension),
            Image.Resampling.LANCZOS,
        )
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=settings.llm_image_quality, optimize=True)
    return "image/jpeg", base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def _analysis_prompt(gender: Gender) -> str:
    return f"""Analyze these photos of a person ({gender.value}) and return a JSON object with exactly this structure:
{{
  "skin_tone": {{
    "fitzpatrick": "I-VI",
    "undertone": "warm|cool|neutral|olive",
    "label": "descriptive label like 'Warm Olive, Medium'",
    "hex_color": "#hex approximation of their skin tone"
  }},
  "body_type": {{
    "shape": "rectangle|inverted-triangle|triangle|hourglass|oval|pear",
    "build": "slim|athletic|average|broad",
    "height_category": "petite|average|tall"
  }},
  "proportions": {{
    "shoulder_hip_ratio": "balanced|broad-shoulder|wide-hip",
    "torso_leg_ratio": "long-torso|balanced|long-legs"
  }},
  "face_shape": "oval|round|square|heart|oblong|diamond",
  "color_season": "spring_light|spring_warm|spring_clear|summer_light|summer_cool|summer_soft|autumn_soft|autumn_warm|autumn_deep|winter_deep|winter_cool|winter_clear",
  "eye_color": "brown|blue|green|hazel|gray|amber",
  "style_vibes": ["list", "of", "style", "tags"],
  "color_palette": [
    {{"name": "Color Name", "hex": "#hexcode", "category": "best|good", "reason": "Why this color suits them"}}
  ],
  "wardrobe_tips": ["tip1", "tip2", "tip3", "tip4"],
  "confidence_score": 0.85
}}

For color_palette, recommend 6 colors that would look best on this person given their skin tone and undertone.
For wardrobe_tips, give 4 specific, actionable tips based on their body type and coloring.
Use positive, empowering language. Focus on what flatters, not what to avoid.
Return ONLY the JSON, no other text."""


def get_mock_profile(job_id: str, gender: Gender) -> StyleProfile:
    """Return a mock profile for development without API key."""
    return StyleProfile(
        job_id=job_id,
        gender=gender,
        skin_tone=SkinTone(
            fitzpatrick="IV",
            undertone="warm",
            label="Warm Olive, Medium",
            hex_color="#C68642",
        ),
        body_type=BodyType(
            shape="inverted-triangle",
            build="athletic",
            height_category="average",
        ),
        proportions=Proportions(
            shoulder_hip_ratio="broad-shoulder",
            torso_leg_ratio="balanced",
        ),
        face_shape=FaceShape.oval,
        color_season=ColorSeason.autumn_warm,
        eye_color="brown",
        style_vibes=["Streetwear", "Casual", "Minimalist", "Urban"],
        color_palette=[
            ColorRecommendation(name="Rust", hex="#B7410E", category="best", reason="Rich warm tone that echoes your undertone"),
            ColorRecommendation(name="Olive", hex="#708238", category="best", reason="Earth green that complements warm olive skin"),
            ColorRecommendation(name="Camel", hex="#C19A6B", category="best", reason="Warm neutral that enhances your natural coloring"),
            ColorRecommendation(name="Off-White", hex="#FAF0E6", category="best", reason="Soft white that harmonizes better than pure white"),
            ColorRecommendation(name="Terracotta", hex="#E2725B", category="good", reason="Warm accent that adds vibrancy"),
            ColorRecommendation(name="Forest Green", hex="#228B22", category="good", reason="Deep green for visual depth"),
        ],
        wardrobe_tips=[
            "Earth tones like rust, olive, and camel complement your warm olive skin beautifully — make them the backbone of your wardrobe.",
            "With an athletic, inverted-triangle build, opt for straight-leg or relaxed-fit trousers to balance broader shoulders.",
            "Layering with open overshirts and lightweight jackets adds visual interest without overwhelming your frame.",
            "Opt for cream, ecru, or off-white instead of bright white for a more harmonious look near your face.",
        ],
        confidence_score=1.0,
    )


async def analyze_photos(image_paths: list[str], job_id: str, gender: Gender) -> StyleProfile:
    """Analyze uploaded photos using OpenRouter/Claude vision or return mock data."""
    if settings.mock_mode:
        return get_mock_profile(job_id, gender)

    prompt = _analysis_prompt(gender)
    selected_paths = image_paths[: max(1, settings.llm_max_images)]

    if openrouter_configured():
        content = []
        for path in selected_paths:
            media_type, data = _encode_image_for_llm(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{data}"},
            })
        content.append({"type": "text", "text": prompt})

        response_text = openrouter_chat_text(
            [{"role": "user", "content": content}],
            model=settings.openrouter_vision_model,
            max_tokens=2200,
            operation="analysis.vision",
        )
        result = parse_json_response(response_text)
        return _profile_from_result(result, job_id, gender)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    image_content = []
    for path in selected_paths:
        media_type, data = _encode_image_for_llm(path)
        image_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })

    image_content.append({
        "type": "text",
        "text": prompt,
    })

    fallback_model = "claude-sonnet-4-6-20250514"
    message = client.messages.create(
        model=fallback_model,
        max_tokens=2000,
        messages=[{"role": "user", "content": image_content}],
    )
    capture_response_usage(
        message,
        operation="analysis.vision",
        provider="anthropic",
        model=fallback_model,
        details={"max_tokens": 2000},
    )

    result = json.loads(message.content[0].text)
    return _profile_from_result(result, job_id, gender)


def _profile_from_result(result: dict, job_id: str, gender: Gender) -> StyleProfile:
    face_shape = None
    if result.get("face_shape"):
        try:
            face_shape = FaceShape(result["face_shape"])
        except ValueError:
            pass

    color_season = None
    if result.get("color_season"):
        try:
            color_season = ColorSeason(result["color_season"])
        except ValueError:
            pass

    return StyleProfile(
        job_id=job_id,
        gender=gender,
        skin_tone=SkinTone(**result["skin_tone"]),
        body_type=BodyType(**result["body_type"]),
        proportions=Proportions(**result.get("proportions", {})),
        face_shape=face_shape,
        color_season=color_season,
        eye_color=result.get("eye_color"),
        style_vibes=result["style_vibes"],
        color_palette=[ColorRecommendation(**c) for c in result["color_palette"]],
        wardrobe_tips=result["wardrobe_tips"],
        confidence_score=result.get("confidence_score", 0.85),
    )
