from __future__ import annotations

from app.models.schemas import VisualAnalysisKind


PROMPT_VERSION = "visual-analysis-v1"


BASE_EDITORIAL_STYLE = """
Create one premium editorial infographic from the provided portrait.
Use a clean light neutral background, structured grid, rounded cards, soft shadows,
thin sans-serif typography, subtle tracking, and a high-end Pinterest/editorial look.
Keep text minimal: short labels only, no paragraphs, no long explanations.
Preserve the subject's identity and face accurately. Do not change facial structure,
skin texture, age, body size, or expression unless the section explicitly compares hair
or grooming styling. Avoid caricature, fantasy styling, and exaggerated retouching.
""".strip()


COLOR_ANALYSIS_PROMPT = f"""
{BASE_EDITORIAL_STYLE}

Task: diagram-first personal color analysis.

Required reasoning to show visually:
- Analyze skin undertone: cool, warm, or neutral.
- Analyze value: light, medium, or deep.
- Analyze chroma: soft/muted or clear/bright.
- Analyze contrast level between features: low, medium, or high.
- Assign the best matching 16-season palette:
  Soft Summer, Light Summer, Cool Summer, Bright Summer,
  Soft Autumn, Warm Autumn, Deep Autumn, Light Autumn,
  Light Spring, Warm Spring, Bright Spring, Clear Spring,
  Deep Winter, Cool Winter, Bright Winter, Clear Winter.

Strict palette rule:
- All colors, metals, hair tones, and makeup must derive from the detected season.
- No cross-season contamination.
- Palette must feel cohesive and realistic: fabric-based and season-accurate.

Top section:
- Portrait top-left.
- Title: YOUR COLOR PALETTE.
- Subtitle: detected season name.
- Descriptor line: 3-5 short traits only.

Swatch sections:
- Neutrals.
- Best Colors.
- Supporting Colors.
- Each swatch needs color name plus a specific 2-3 word descriptor.
- Descriptors must reflect real palette qualities, not generic filler.

Critical fabric draping rule for every portrait tile:
- Use an asymmetrical wrap drape.
- Start from one shoulder and fall diagonally across the chest.
- Natural folds, soft tension.
- One shoulder more covered, one more open.
- Avoid symmetrical draping, even shoulder coverage, poncho shapes,
  flat horizontal necklines, and identical fabric blocks.

See the Colors in Action:
- 10-14 tiles using the same portrait.
- Each tile uses a different detected-palette clothing color.
- Face unchanged.
- Clean grid.

Bottom modules:
- Metals: choose 2-3 season-appropriate metals with short descriptors.
- Hair Tones: range aligned with the palette undertone, value, and chroma.
- Makeup: blush, lip, shadow, liner, all season-aligned.
- Eyes: identify visible eye color and tonal quality.

Final quality check:
- Maintain strict consistency between detected season and every visual element.
- No colors, metals, hair tones, or makeup tones outside the inferred palette.
""".strip()


HAIRSTYLE_PROMPT = f"""
{BASE_EDITORIAL_STYLE}

Task: hairstyle analysis graphic.

Create a visual-first hairstyle comparison board using the portrait.
Show side-by-side headshots with different hairstyle ideas and short labels only.

Layout:
- Title: HAIR DIRECTION.
- Subtitle: FACE-FRAMING OPTIONS.
- Portrait reference card top-left.
- 8-12 small headshot tiles in a clean grid.
- Add a compact "Best Bets" row with 3 strongest options.
- Add a compact "Use Caution" row with 2 softer alternatives.

Analysis cues:
- Infer face shape, hair density impression, forehead proportion, jaw softness/sharpness,
  and overall style direction from the portrait.
- Keep recommendations wearable and realistic.
- Do not change face, skin, age, or facial structure.
- Hairstyles may vary cut, length, parting, volume, texture, fringe, and facial hair only
  if the subject presents masculine grooming cues.

Tile labels:
- Use 2-4 word labels such as "soft side part", "textured crop", "curtain fringe",
  "jawline bob", "loose layers", "clean stubble".
- Include tiny fit scores as "8.5/10" style fit scores, not attractiveness ratings.

Visual comparison:
- Keep lighting and face consistent across tiles.
- Use clear before/reference vs option comparison.
- Use tasteful annotation lines for hairline, cheekbone, jaw, and face-frame balance.
""".strip()


LOOK_AUDIT_PROMPT = f"""
{BASE_EDITORIAL_STYLE}

Task: cosmetic styling potential audit focused on good looks and model-like presentation.

Safety and scope:
- This is non-medical visual styling guidance only.
- Do not diagnose flaws, disorders, asymmetry problems, or medical issues.
- Do not claim plastic surgery is needed.
- Do not label features as defective or "fixed".
- If aesthetic procedures are shown, label them as "consult-only options" and keep them
  conservative, reversible-looking, and non-graphic.
- Rate proposals as "style fit" from 1-10, not "hotness" or human attractiveness.

Layout:
- Title: LOOK POTENTIAL AUDIT.
- Big before/reference portrait on the left.
- Big polished styling direction on the right.
- At least 8 small headshot tiles with different ideas:
  hair, beard/no beard if relevant, brows, eyewear, grooming, color direction, neckline,
  and editorial styling.
- Add short feature annotation callouts around the reference:
  "jaw framing", "brow shape", "hair volume", "skin finish", "facial hair line".
- Add pros/cons cards for the top 3 styling proposals.
- Include a small "Consult-only" card for any surgical/aesthetic procedure ideas.

Visual rules:
- Optimize for polished, aspirational model styling while preserving identity.
- Use realistic grooming and wardrobe changes.
- Keep all text short labels only.
- No paragraphs.
- No extreme body or face transformation.
""".strip()


PROMPTS_BY_KIND = {
    VisualAnalysisKind.color_palette: COLOR_ANALYSIS_PROMPT,
    VisualAnalysisKind.hairstyles: HAIRSTYLE_PROMPT,
    VisualAnalysisKind.look_audit: LOOK_AUDIT_PROMPT,
}


PROCESS_BY_KIND = {
    VisualAnalysisKind.color_palette: [
        "Detect undertone, value, chroma, contrast",
        "Map to 16-season palette",
        "Generate palette-locked editorial board",
    ],
    VisualAnalysisKind.hairstyles: [
        "Read face-framing cues",
        "Compare realistic hair directions",
        "Score style fit, not attractiveness",
    ],
    VisualAnalysisKind.look_audit: [
        "Compare grooming and styling directions",
        "Annotate non-medical visual balance cues",
        "Keep procedure notes consult-only",
    ],
}


def build_visual_prompt(kind: VisualAnalysisKind) -> str:
    return PROMPTS_BY_KIND[kind]
