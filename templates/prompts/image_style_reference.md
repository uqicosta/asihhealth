# AsihHealth Image Generation Style Reference

**Purpose**: This document provides a consistent visual style guide for all AI-generated images (primarily using DALL·E / OpenAI) used in AsihHealth content.

Use this reference when generating:
- Thumbnail background images
- Video asset / stock images (for Ken Burns effect)
- Any other supporting visuals

The goal is to maintain a cohesive, professional brand identity across all videos.

---

## Core Brand Style

- **Channel Identity**: AsihHealth — Indonesian health education YouTube channel
- **Tone**: Professional yet warm, trustworthy, approachable, and educational
- **Audience**: Indonesian general public (orang awam) — keep visuals clear, relatable, and non-intimidating
- **Overall Aesthetic**: Cinematic health photography mixed with modern stock-photo quality. High production value suitable for YouTube.

### Visual Keywords (always include or reference these)
- Cinematic
- High detail / photorealistic or clean artistic illustration
- Natural yet dramatic lighting
- Professional stock photo aesthetic
- Clean composition with breathing room
- Warm, human, and hopeful (even when covering serious health topics)
- Indonesian cultural context (people, environments, clothing, food, settings)

### Color Direction
- Primary accent: Strong health red (#DC2626 or similar)
- Use red accents subtly (clothing, objects, highlights) rather than dominant color
- Natural skin tones, greens, warm neutrals, soft blues
- High contrast with dark moody backgrounds + bright, clean highlights (especially for thumbnails)
- Avoid oversaturated "stock photo" colors or cartoonish looks

### Mood & Emotion
- Calm authority mixed with care
- Informative and serious when needed, but never scary or sensationalist
- Positive, solution-oriented feeling where appropriate

---

## Thumbnail Background Style (for DALL·E)

Thumbnails are 1280x720 (16:9). The AI-generated image will have **bold text overlaid** later using Pillow, so follow these rules strictly:

- **Composition**: Leave clear negative space, preferably on the right third or bottom area for title text
- **Subject focus**: Strong central or left-side subject (person, symbolic object, or scene)
- **Style modifiers**:
  - Cinematic, high-contrast YouTube thumbnail style
  - Dramatic lighting with strong shadows and highlights
  - Professional photography / cinematic still
  - Emotional and attention-grabbing
  - Dark moody background with bright, clean subject lighting
  - Rich colors with red accent elements for urgency/health theme
  - Highly detailed, sharp focus
  - 16:9 composition
- **Avoid**:
  - Busy backgrounds that compete with text
  - Text, logos, or watermarks in the generated image
  - Cartoonish or overly artistic styles (unless specified)
  - Faces looking directly at camera in a stock-photo cheesy way (prefer natural or thoughtful expressions)

**Recommended base style block for thumbnails**:
```
cinematic high-contrast YouTube thumbnail background for Indonesian health education video, dramatic lighting, professional photography style, emotional and attention-grabbing, dark moody background with bright clean highlights, rich colors with subtle red health accents, highly detailed, sharp focus, 16:9 composition, clean negative space on the right side suitable for bold text overlay, no text, no logos, no watermarks, photorealistic
```

---

## Video Asset / Ken Burns Image Style

These images are used as full-screen visuals with slow zoom + pan (Ken Burns effect). They need to look good when cropped and animated.

- **Aspect ratio**: Prefer 16:9 landscape (1792x1024 or similar)
- **Composition**: Layered depth — foreground interest + midground + background. Good for slow camera movement.
- **Style modifiers**:
  - High-quality cinematic still
  - Photorealistic or clean detailed illustration
  - Natural lighting (can be soft and beautiful or slightly dramatic)
  - Rich but clean composition
  - Suitable for slow zoom and pan effects (avoid flat or overly busy images)
  - Subtle medical/wellness elements
  - Indonesian cultural context where natural
  - Professional stock photo / high-end documentary aesthetic
- **Avoid**:
  - Text or graphics
  - Very flat images (no depth)
  - Extremely busy foregrounds that become distracting when zoomed
  - Low-resolution or painterly styles that pixelate on zoom

**Recommended base style block for video assets**:
```
high-quality detailed cinematic still for Indonesian health education video, photorealistic or clean artistic illustration, natural lighting, rich but clean composition, suitable for slow Ken Burns zoom and pan effect, subtle medical and wellness elements, Indonesian cultural context, professional stock photo aesthetic, high resolution, 16:9 landscape, no text, no watermarks, no logos
```

---

## Full Reusable Style Reference (Copy-Paste Ready)

You can append or prepend this block to most image prompts:

```
AsihHealth brand style: cinematic, professional health education photography for Indonesian YouTube channel, warm and trustworthy tone, high detail, natural yet dramatic lighting, clean modern aesthetic with subtle red health accent color, Indonesian subjects and environments, photorealistic or high-quality illustration, suitable for YouTube thumbnails and video backgrounds, no text, no watermarks, no logos
```

### Thumbnail-specific addition:
```
... cinematic high-contrast YouTube thumbnail style, strong subject focus with negative space for text overlay on the right, dark moody background with bright highlights, emotional and attention-grabbing
```

### Video asset-specific addition:
```
... high-quality cinematic still suitable for Ken Burns slow zoom and pan, layered depth with foreground/midground/background interest, professional documentary stock photo quality
```

---

## Prompt Engineering Tips

1. **Always start with the subject**, then append style reference:
   ```
   [Main subject description], [AsihHealth style reference]
   ```

2. **Be specific about Indonesian context** when relevant (e.g., "Indonesian doctor in white coat", "traditional Indonesian market", "young Indonesian woman drinking water").

3. **For thumbnails**: Explicitly request negative space / composition for text.

4. **For video assets**: Mention "cinematic still suitable for slow camera movement" or "layered depth".

5. **Quality boosters** (use sparingly):
   - "highly detailed, sharp focus, 8k"
   - "professional photography, cinematic lighting"

6. **What to avoid in prompts**:
   - "text", "logo", "watermark", "writing"
   - Overly cartoonish or "in the style of" specific artists unless intentional
   - Extreme close-ups for Ken Burns assets (need room to zoom)

---

## Example Prompts

**Thumbnail background (kopi topic):**
```
Cinematic high-contrast portrait of a concerned middle-aged Indonesian man holding a cup of coffee, dramatic side lighting, professional health education YouTube thumbnail style, dark moody background with red accent elements, negative space on the right for text overlay, highly detailed, photorealistic, AsihHealth brand style
```

**Video asset (jantung / heart health):**
```
High-quality cinematic still of an Indonesian doctor explaining to a patient using a heart model, natural window lighting in a clean modern clinic, layered depth, suitable for slow Ken Burns zoom, professional stock photo aesthetic, subtle medical elements, Indonesian cultural context, clean composition, AsihHealth visual style
```

---

## Current Code Usage

The code automatically loads the style blocks for consistency:

- **Thumbnail backgrounds**: `templates/prompts/image_style_block_thumbnail.txt` (preferred) or `image_style_block.txt`
  - Used in `core/thumbnail.py` → `_build_dalle_prompt()`

- **Video asset images** (Ken Burns): `templates/prompts/image_style_block_assets.txt` (preferred) or `image_style_block.txt`
  - Used in `core/assets.py` → `_generate_openai_stock_for_topic()`

When you want to evolve the visual style across the entire project, edit the block `.txt` files (and this reference document).

**Tip**: Keep the `.txt` blocks relatively concise (under ~400-500 characters) because they will be appended to subject-specific prompts sent to DALL·E. The detailed explanations live in this `.md` file for humans.

---

**Last updated**: 2026 (update this date when you revise the style)

This reference should be the single source of truth for visual consistency across all AsihHealth AI-generated images.