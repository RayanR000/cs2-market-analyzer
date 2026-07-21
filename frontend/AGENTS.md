<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- BEGIN:design-context -->
# Design Context

## Product Register
Design SERVES the tool. The interface should disappear into the analysis task.

## Brand Personality
Analytical, precise, calm. Every element clarifies signal from noise.

## Principles
- **Clarity over Density** — whitespace and hierarchy guide the eye
- **Asset-Grounded Data** — high-res skin images anchor every analysis
- **Comfortable Analysis** — tinted carbon dark mode, warm amber accents
- **Precision Tools** — every component behaves exactly once, predictably
- **Rich but Not Loud** — color only where it signals data or state

## Palette (OKLCH)
- Bg: `oklch(18% 0.004 30)` / `oklch(22% 0.005 30)` / `oklch(15% 0.003 30)`
- Text: `oklch(93% 0 0)` / `oklch(70% 0.004 30)` / `oklch(52% 0.004 30)` / `oklch(38% 0.003 30)`
- Accent: `oklch(62% 0.14 55)` — warm amber
- Data: `oklch(62% 0.14 155)` (up) / `oklch(62% 0.12 25)` (down)
- Radii: 2px (xs), 4px (sm), 6px (md)

## Typography
- Inter for UI, JetBrains Mono for data. No display fonts.
- Rem scale: Display 48px, H1 32px, H2 22px, H3 16px, Body 15px, Small 13px, Caption 11px, Micro 10px.
- Tabular-nums on all numeric content.

## Styling
- Use CSS custom properties from `app/globals.css` — never inline hex values.
- Widget: `bg-background-secondary border border-border radius-sm`, hover → `border-accent bg-surface`.
- Primary button: `bg-accent text-background-primary`. No border + shadow on same element.
- No neon, no tactical gaming cliches, no decorative motion on product pages.
<!-- END:design-context -->

<!-- BEGIN:api-server -->
# API Server

FastAPI on port 8000. Start from `backend/`:
```
source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints: `GET /health`, `/items/*`, `/items/{id}/price-history`, `/trends`, `/prediction`, `/events`, `/prices`, `/variants`, `/event-impacts`, `/feature-importance`, `/social-sentiment`, `/market/summary`, `/opportunities/*`, `/events/*`, `/accuracy/*`, `/ab-test/*`, `/auth/*`, `/portfolio/inventory`.

Frontend fetches from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

When adding migrations or columns, ensure SQLAlchemy models match production schema.
<!-- END:api-server -->
