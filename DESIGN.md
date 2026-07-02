# CS2 Market Analyzer — Design System

## Philosophy

**Modern Analytical Boutique.** The precision of a high-end trading tool with the visual richness of a premium game showcase. Every data point is grounded by visual context. We prioritize breathing room and clarity over raw data density to ensure a "relaxed" analytical experience.

## Color Strategy

**Monochromatic Carbon:** A pure minimalist grayscale palette designed for ultimate data focus and clarity. By removing hue-based distraction, we allow the item assets and numbers to carry the full weight of the interface.

### Palette (OKLCH)

**Backgrounds:**
- **Primary:** `oklch(12% 0 0)` — Deep carbon, main canvas.
- **Secondary:** `oklch(15% 0 0)` — Subtle panel elevation.
- **Tertiary:** `oklch(10% 0 0)` — Deepest layer, table headers, asset frames.

**Surfaces:**
- **Surface:** `oklch(18% 0 0)` — Interactive surfaces (cards, inputs).
- **Surface-hover:** `oklch(22% 0 0)` — Hovered interactive surfaces.
- **Surface-active:** `oklch(25% 0 0)` — Active/focused surfaces.

**Text:**
- **Primary:** `oklch(95% 0 0)` — Stark white for body and headings.
- **Secondary:** `oklch(70% 0 0)` — Muted gray for meta info and descriptions.
- **Tertiary:** `oklch(50% 0 0)` — Lower-priority metadata.
- **Muted:** `oklch(35% 0 0)` — Placeholder, disabled, decorative labels.
- **Accent:** `oklch(95% 0 0)` — Links, emphasis, data highlights.

**Structural:**
- **Border:** `oklch(22% 0 0)` — Default dividers and borders.
- **Border-light:** `oklch(18% 0 0)` — Subtle dividers, inner borders.
- **Border-accent:** `oklch(40% 0 0)` — Hover/focus border emphasis.
- **Grid:** `oklch(14% 0 0)` — Chart grid lines and minor dividers.
- **Divider:** `oklch(18% 0 0)` — Row separators.

**Data Indicators:**
- **Up:** `oklch(85% 0.1 150)` — Price increase, positive delta (emerald tint).
- **Down:** `oklch(75% 0.1 25)` — Price decrease, negative delta (rose tint).

**Radii & Shadows:**
- **Radius-xs:** `2px` — Tags, small indicators.
- **Radius-sm:** `4px` — Cards, inputs, buttons, tables, widgets.
- **Radius-md:** `6px` — Larger containers.
- **Shadow-sm:** `0 1px 3px rgba(0,0,0,0.4)`
- **Shadow-md:** `0 4px 12px rgba(0,0,0,0.5)`

**Theme:** Dark (Default). Carbon base reduces eye strain during extended analysis sessions.

## Typography

The tool uses a single sans family for UI with a monospace sibling for data. This is intentional: product UIs don't need display/body pairing (per register guidance), and a single family keeps the interface calm and consistent.

- **UI stack:** Inter (variable font via next/font) — modern, clean, neutral.
- **Data stack:** JetBrains Mono (variable font via next/font) — tabular-nums for price alignment, tight tracking for density.
- **Body:** 15px, 1.6 line-height, 400 weight, `-0.01em` letter-spacing. Cap line length at 65-75ch.
- **Scale (fixed rem, not fluid — product register):**
  - Display H1: 60px (6xl) / 80px (8xl) on hero — 600 weight, `-0.03em` tracking, `leading-[0.85]`.
  - Section H2: 30px (3xl) — 600 weight, `tracking-tighter`.
  - Section H3: 18px (lg) — 600 weight, `tracking-tight`.
  - Body: 15px — 400 weight, 1.6 line-height.
  - Small: 12px — 500 weight, uppercase labels, tracking-wide.
  - Data: 14px monospace (tabular-nums, `-0.02em`).
  - Micro: 10-11px — uppercase labels, annotations, tag-tech elements, `0.15-0.2em` tracking.
- Headings use `text-wrap: balance` for even line lengths.

## Spacing & Layout

- **Base unit:** 4px (scales to 8, 16, 24, 32, 48, 64).
- **Container max-width:** 1280px (7xl). Side padding: 24px (px-6).
- **Breathing room:** Minimum 24px padding on main containers. No compact modes.
- **Tables:** Generous row height (48px+). Th cells: `px-6 py-5`. Td cells: `px-6 py-4`. No vertical borders.
- **Alignment:** Data right-aligned in tables; text left-aligned. Monospace for all numeric columns.
- **Product layout patterns:**
  - **Landing/marketing (home):** Full-width sections, centered content, asymmetric hero.
  - **Market (data table):** Search bar on top, trending grid, sortable table below.
  - **Item detail (analytical report):** Two-column — chart (3/4) + sidebar (1/4) with metrics.
  - **Portfolio (auth dashboard):** Summary stat cards row, full-width table below.

## Motion & State

Product register guidance: 150-250ms transitions. Motion conveys state, not decoration. No orchestrated page-load sequences.

- **Hover:** 200ms ease-out (css). Background and border transitions on widgets.
- **Page reveals:** Framer Motion — 800ms on hero (marketing), 300-400ms on product pages. Use cubic bezier `[0.16, 1, 0.3, 1]`.
- **Table rows:** Staggered entrance at 10-50ms delay per row.
- **Data animations:** CountUpNumber for value changes. Duration proportional to delta.
- **Preload scan line:** `.progress-line` in header — 2.5s infinite sweep.
- **Reduced motion:** All animations degrade gracefully. `prefers-reduced-motion: reduce` → instant transitions, no scroll-triggered reveals.
- **No decorative motion on product pages.** No orchestrated page-load sequences. No bounce or elastic easing.

## Components

### Header
- Sticky top, `z-50`, `bg-background-primary/95 backdrop-blur-sm`.
- Contains: logo (CS mark + "DATA TERMINAL"), nav links (MARKET, PORTFOLIO), auth button.
- Nav links: uppercase 11px, tracking-[0.2em], underline-on-hover animation via absolute span.
- Auth: "AUTHENTICATE" button — white bg, black text, or Steam button (portfolio context).
- States: loading (pulse avatar skeleton), logged-in (avatar + username + logout), logged-out (auth button).
- Bottom border divider at `oklch(18% 0 0 / 0.6)`.

### Search
- Full-width input, `bg-background-secondary`, border `--border`, rounded-sm.
- Left: search icon (SVG, `text-tertiary` → `text-primary` on focus).
- Right: "Terminal" tag badge.
- Focus: `bg-surface`, border → `--border-accent`, box-shadow inset highlight.
- Placeholder: uppercase, bold, `text-muted` (10px).

### StatCard
- Widget-block container (`bg-background-secondary`, border, radius-sm).
- Top: uppercase label (10px, text-muted). Right: annotation tag (visible on hover).
- Center: large value via CountUpNumber (30px, font-data, font-medium, tracking-tighter).
- Optional: change indicator (+4.2%) in data-up/down color.
- Bottom: subvalue label (10px, uppercase, text-muted).
- Hover: scan line animation (top edge, scale-x from 0 to 1, 500ms).

### ItemCard
- Widget-block container, relative overflow-hidden.
- Top: type label (9px, uppercase, text-muted) + name (14px, font-semibold). Rarity dot (1.5px, colored glow).
- Center: asset image in aspect-square frame (bg-background-tertiary). Image scales 105% on hover (700ms).
- Bottom: EST. VALUE (large price, monospace) + 7D DELTA (data-up/down color).
- Hover: white glow background opacity 0 → 0.03 (500ms), annotation tag fade in.

### Buttons
- Flat, uppercase, bold, 10-11px, tracking-[0.2em].
- **Primary (CTA):** `bg-white text-black`, hover `bg-muted`, active `scale-95`.
- **Nav links:** `text-secondary`, hover `text-primary`, underline animation.
- **Auth (Steam):** Dark blue `#1b2838`, white text, rounded-lg, hover scale-105.

### Tables
- Full-width, bg-surface, rounded-sm overflow-hidden.
- Thead: bg-background-tertiary, uppercase 10px, text-secondary.
- Rows: stripe-row (bottom border divider). Hover → bg-background-tertiary.
- Sortable column headers: click buttons, show sort direction arrow.
- Data-up/down badges: inline-block, rounded, bg tint + colored text.
- Loading: full-row "Loading backend market data..." centered.
- Empty: "No items match your search" centered.
- Error: red-tinted banner at top.

### Charts
- Recharts LineChart, `ResponsiveContainer`, 360px height.
- Dark theme: stroke `#2d3748` for grid, `#6b7280` for axis labels.
- Steam line: `#cbd5e1` stroke, 2px. CSFloat line: `#ff6b35` stroke, 2px.
- Tooltip: dark bg `#1a1f2e`, matching border, white text, rounded-sm.
- No animation on chart lines (data accuracy > decoration).
- Time range tabs: 24h / 7d / 30d / all.

### PriceSourceFilter
- Toggle-style filter for multi-source chart data (Steam, CSFloat, etc.).
- Sidebar display: source name + data point count.

### Loading States
- **Full-screen:** centering spinner (`border-4 border-t-transparent`, 48px, animate-spin) + text.
- **Inline (tables):** full-row centered message.
- **Header avatar:** pulse animation skeleton (8x8 rounded, bg-surface).

### Empty States
- **No inventory:** message + "Browse market →" link.
- **No search results:** "No items match your search" centered.
- **No signals:** "No technical factors returned yet."

### Error States
- Red-tinted banner: `border-red-500/35 bg-red-500/8`, text-primary, rounded-lg, px-4 py-3.
- **Item unavailable:** full page with "← MARKET" back link, "Item unavailable" heading, error message.
- **Login required (portfolio):** CTA page with Steam sign-in button.

## Visual Hierarchy

- **Primary:** High-res skin image (The "What").
- **Secondary:** Large price/trend chart (The "Value").
- **Tertiary:** Supporting metadata (Wear, Volume, etc.).
- **Focus:** Use elevation (Background-secondary) and whitespace rather than color to group elements.
- **Emphasis:** Inverse focus (white bg + black text) for primary actions.

## Anti-patterns to avoid

- **Information Overload:** Do not show 20 columns of data at once.
- **Harsh Contrast:** Avoid `#000` background with pure `#fff` text.
- **Generic Slop:** Avoid standard shadcn/tailwind defaults without custom OKLCH adjustments.
- **Gamer Cliche:** No aggressive "tactical" UI or neon glows. Keep it "Boutique."
- **Decorative motion on product pages:** Motion conveys state, not decoration.
- **Orchestrated page-load sequences:** Products load into tasks, users don't watch them load.
- **Inconsistent component vocabulary:** Same button shape, same form control style across all screens.
- **Display fonts in UI labels:** One sans family (Inter), one data family (JetBrains Mono).
