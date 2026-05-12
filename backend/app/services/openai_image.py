from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import is_secret_configured, settings
from app.models.schemas import VisualAnalysisKind
from app.services.cost_ledger import capture_image_usage, capture_response_usage
from app.services.llm_client import get_openrouter_client, openrouter_configured
from app.services.visual_prompts import build_visual_prompt


def _write_mock_visual(output_path: Path, kind: VisualAnalysisKind) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1536, 1024), "#f4f0ea")
    draw = ImageDraw.Draw(image)
    title = {
        VisualAnalysisKind.color_palette: "YOUR COLOR PALETTE",
        VisualAnalysisKind.hairstyles: "HAIR DIRECTION",
        VisualAnalysisKind.look_audit: "LOOK POTENTIAL AUDIT",
    }[kind]

    try:
        title_font = ImageFont.truetype("Helvetica.ttc", 56)
        label_font = ImageFont.truetype("Helvetica.ttc", 24)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    draw.rounded_rectangle((64, 64, 1472, 960), radius=36, fill="#fffaf3", outline="#ddd4c8", width=2)
    draw.text((112, 110), title, fill="#2d2925", font=title_font)
    draw.text((112, 184), "MOCK VISUAL · SET MOCK_MODE=false AND CONFIGURE IMAGE PROVIDER", fill="#81766a", font=label_font)

    colors = ["#6e7f5f", "#a66a4b", "#c9b08a", "#3e4b59", "#b9847d", "#d7c7ac"]
    for index, color in enumerate(colors):
        x = 112 + index * 220
        draw.rounded_rectangle((x, 300, x + 160, 520), radius=24, fill=color)
        draw.text((x, 548), f"Option {index + 1}", fill="#2d2925", font=label_font)

    for row in range(2):
        for col in range(4):
            x = 112 + col * 330
            y = 650 + row * 130
            draw.rounded_rectangle((x, y, x + 270, y + 84), radius=18, fill="#eee5da", outline="#ddd4c8")
            draw.text((x + 22, y + 26), "short label", fill="#4d463f", font=label_font)

    image.save(output_path, format="PNG")


def _image_to_data_url(image_path: Path) -> str:
    with Image.open(image_path) as image:
        image.thumbnail(
            (
                settings.openrouter_image_input_max_dimension,
                settings.openrouter_image_input_max_dimension,
            ),
            Image.Resampling.LANCZOS,
        )
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92, optimize=True)
    encoded = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def _write_openrouter_visual(image_path: Path, output_path: Path, kind: VisualAnalysisKind) -> bool:
    if not openrouter_configured():
        return False

    prompt = build_visual_prompt(kind)
    response = get_openrouter_client().chat.completions.create(
        model=settings.openrouter_image_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(image_path)}},
                ],
            }
        ],
        extra_body={
            "modalities": ["image", "text"],
            "image_config": {
                "aspect_ratio": settings.openrouter_image_aspect_ratio,
                "image_size": settings.openrouter_image_size,
            },
        },
    )

    message = response.model_dump()["choices"][0]["message"]
    images = message.get("images") or []
    if not images:
        return False

    capture_response_usage(
        response,
        operation=f"visual.{kind.value}",
        provider="openrouter",
        model=settings.openrouter_image_model,
        image_count=len(images),
        details={
            "kind": kind.value,
            "aspect_ratio": settings.openrouter_image_aspect_ratio,
            "image_size": settings.openrouter_image_size,
        },
    )

    data_url = images[0]["image_url"]["url"]
    _, encoded = data_url.split(",", 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(encoded))
    return True


def _write_openai_visual(image_path: Path, output_path: Path, kind: VisualAnalysisKind) -> bool:
    if not is_secret_configured(settings.openai_api_key):
        return False
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_visual_prompt(kind)

    with image_path.open("rb") as image_file:
        response = client.images.edit(
            model=settings.openai_image_model,
            image=image_file,
            prompt=prompt,
            size=settings.openai_image_size,
            quality=settings.openai_image_quality,
        )

    image_base64 = response.data[0].b64_json
    capture_image_usage(
        operation=f"visual.{kind.value}",
        provider="openai",
        model=settings.openai_image_model,
        image_count=1,
        details={
            "kind": kind.value,
            "size": settings.openai_image_size,
            "quality": settings.openai_image_quality,
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(image_base64))
    return True


def _generate_visual_sync(image_path: Path, output_path: Path, kind: VisualAnalysisKind) -> None:
    if settings.mock_mode:
        _write_mock_visual(output_path, kind)
        return

    if _write_openrouter_visual(image_path, output_path, kind):
        return
    if _write_openai_visual(image_path, output_path, kind):
        return

    _write_mock_visual(output_path, kind)


async def generate_visual_analysis(
    image_path: Path,
    output_path: Path,
    kind: VisualAnalysisKind,
) -> None:
    await asyncio.to_thread(_generate_visual_sync, image_path, output_path, kind)
