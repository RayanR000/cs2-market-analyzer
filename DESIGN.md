# CS2 Market Analyzer — Design System

## Philosophy

**Modern Analytical Boutique.** The precision of a high-end trading tool with the visual richness of a premium game showcase. Every data point is grounded by visual context. We prioritize breathing room and clarity over raw data density to ensure a "relaxed" analytical experience.

## Philosophy

**Tactile Analytical Boutique.** The precision of a high-end mechanical instrument. We use physical metaphors—brushed steel, matte carbon, and sharp bevels—to create a sense of "weight" and authority. The interface should feel like a custom-machined terminal.

## Color Strategy

**Monochromatic Carbon (Tactile):** A pure minimalist grayscale palette enhanced by texture and depth. 

### Palette (OKLCH)

**Base:**
- **Background-primary:** `oklch(12% 0 0)` — Deepest carbon floor.
- **Background-secondary:** `oklch(16% 0 0)` — Brushed metal elevation.
- **Surface:** `oklch(20% 0 0)` — Matte interactive surfaces.
- **Text-primary:** `oklch(98% 0 0)` — Stark white for high-precision data.
- **Text-secondary:** `oklch(60% 0 0)` — Muted technical gray.
- **Border:** `oklch(24% 0 0)` — Sharp, mechanical dividers.

### Textures & Depth
- **Grain:** A consistent, subtle noise filter across the entire background to simulate a physical matte finish.
- **Bevels:** 1px "highlight" borders on the top and left of cards to simulate a beveled edge.
- **Gradients:** Subtle top-to-bottom linear gradients on surfaces to mimic lighting on brushed steel.

## Components & Patterns

- **Machined Cards:** `card-boutique` now features a 1px top highlight and a deeper bottom shadow to feel "inset" or "bolted" to the UI.
- **Terminal Inputs:** Search and inputs use a deeper, "carved" inset look.
- **Data Display:** High-contrast stark white on deep black. No glows, just raw, sharp precision.


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
