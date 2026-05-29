# CS2 Market Analyzer — Design System

## Philosophy

**Modern Analytical Boutique.** The precision of a high-end trading tool with the visual richness of a premium game showcase. Every data point is grounded by visual context. We prioritize breathing room and clarity over raw data density to ensure a "relaxed" analytical experience.

## Philosophy

**Modern Analytical Boutique.** The precision of a high-end trading tool with the visual richness of a premium game showcase. Every data point is grounded by visual context. We prioritize breathing room and clarity over raw data density to ensure a "relaxed" analytical experience.

## Color Strategy

**Monochromatic Carbon:** A pure minimalist grayscale palette designed for ultimate data focus and clarity. By removing hue-based distraction, we allow the item assets and numbers to carry the full weight of the interface.

### Palette (OKLCH)

**Base:**
- **Background-primary:** `oklch(14% 0 0)` — Deep carbon/black.
- **Background-secondary:** `oklch(18% 0 0)` — Subtle panel elevation.
- **Surface:** `oklch(22% 0 0)` — Interactive surfaces.
- **Text-primary:** `oklch(95% 0 0)` — Stark white for maximum readability.
- **Text-secondary:** `oklch(65% 0 0)` — Muted gray for meta info.
- **Border:** `oklch(28% 0 0)` — Sharp, precise dividers.

**Accents:**
- **Gain:** `oklch(95% 0 0)` with positive indicator (or subtle `oklch(80% 0.12 150)` emerald only for data). 
- **Loss:** `oklch(95% 0 0)` with negative indicator (or subtle `oklch(65% 0.15 25)` rose only for data).
- **Action:** `oklch(95% 0 0)` (Inverse focus: black text on white background).
- **Highlight:** `oklch(40% 0 0)` — Medium gray for secondary focus.

*Note: While the UI is monochromatic, data indicators (Gain/Loss) can retain very low-chroma green/red tints to ensure analytical safety, or rely entirely on symbols (↑/↓).*


**Theme:** Dark (Default). Softer than pitch black to reduce eye strain.

## Typography

- **Font Stack:** 'Inter' for UI (modern, clean), 'JetBrains Mono' or 'IBM Plex Mono' for data (tabular, precise).
- **Headline:** Inter, 500-600 weight, tight tracking.
- **Body:** Inter, 15px, 1.6 line-height for comfort.
- **Data:** Monospace, 14px, for prices and trends.
- **Scale:**
  - H1: 32px, 600 weight (Hero headers)
  - H2: 24px, 500 weight (Section headers)
  - Body: 15px, 400 weight
  - Small: 12px, 500 weight (Labels/Secondary)

## Spacing & Layout

- **Base Unit:** 4px (Scaling to 8, 16, 24, 32, 48, 64).
- **Breathing Room:** Minimum 24px padding for main containers. Avoid "compact" modes.
- **Grid:** Fluid 12-column grid. Large gutters (24px) to prevent information crowding.
- **Alignment:** Data is right-aligned in tables; text is left-aligned.

## Components & Patterns

- **Skin Cards:** Large, high-quality asset displays. Use subtle background gradients or glows based on item rarity (e.g., Covert = subtle red tint).
- **Charts:** Clean, minimalist line charts. Use the Gain/Loss colors for the line. No heavy grids; just essential axes.
- **Search:** Prominent, centered, with large hit areas. 
- **Buttons:** Slightly rounded (8px radius). Flat with subtle hover elevation.
- **Tables:** Generous row height (48px+). Soft striping. No vertical borders.

## Visual Hierarchy

- **Primary:** High-res skin image (The "What").
- **Secondary:** Large price/trend chart (The "Value").
- **Tertiary:** Supporting metadata (Wear, Volume, etc.).
- **Focus:** Use elevation (Background-secondary) and whitespace rather than color to group elements.

## Anti-patterns to avoid

- **Information Overload:** Do not show 20 columns of data at once.
- **Harsh Contrast:** Avoid `#000` background with pure `#fff` text.
- **Generic Slop:** Avoid standard shadcn/tailwind defaults without custom OKLCH adjustments.
- **Gamer Cliche:** No aggressive "tactical" UI or neon glows. Keep it "Boutique."
