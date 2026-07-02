<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- BEGIN:design-context -->
# Design Context

## Product Register
**product** — design SERVES the tool. Familiarity is a feature; the interface should disappear into the analysis task.

## Brand Personality
Analytical, minimalist, relaxed. A professional tool that feels comfortable, not overwhelming or sterile.

## Key Principles
- **Clarity over Density** — whitespace and hierarchy > crammed data
- **Asset-Grounded Data** — high-res skin images provide visual context
- **Comfortable Analysis** — soft carbon dark mode to reduce eye strain
- **Bespoke Authenticity** — custom OKLCH tokens, no shadcn/tailwind defaults

## Palette (OKLCH)
- Bg: `oklch(12% 0 0)` (primary), `oklch(15% 0 0)` (secondary), `oklch(10% 0 0)` (tertiary)
- Text: `oklch(95% 0 0)` (primary), `oklch(70% 0 0)` (secondary), `oklch(50% 0 0)` (tertiary), `oklch(35% 0 0)` (muted)
- Data: Green/red at low chroma (`oklch(85% 0.1 150)` / `oklch(75% 0.1 25)`)
- Radii: 2px (xs), 4px (sm), 6px (md) — no large rounding on cards

## Typography
- Inter for UI, JetBrains Mono for data. No display fonts.
- Fixed rem scale, not fluid. Body 15px, 1.6 line-height. Gaps via 4px base unit.

## Styling
- Use CSS custom properties from `app/globals.css` — never inline hex values.
- Widget pattern: `bg-background-secondary border border-border radius-sm` with hover → `border-accent bg-surface`.
- No neon, no tactical gaming cliches, no decorative motion on product pages.
<!-- END:design-context -->

<!-- BEGIN:api-server -->
# API Server

The FastAPI server runs on port 8000. Start it from `backend/`:
```
source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000
```

It connects to Supabase (production DB) and serves all data endpoints:
- `GET /health` — health check
- `GET /items/`, `/items/search`, `/items/trending`, `/items/{item_id}` — items
- `GET /items/{item_id}/price-history`, `/trends`, `/prediction`, `/events`, `/prices`
- `GET /opportunities/`, `/undervalued`, `/overheated`, `/momentum`
- `GET /events/`, `/events/recent`
- `GET /auth/me`, `/auth/steam/login`, `POST /auth/logout`
- `GET /portfolio/inventory`

The frontend fetches from `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

The `daily_analysis` table in production is missing the `updated_at` column — the model in `database.py` has been patched to match. If migrations or new columns are added, ensure schema alignment.
<!-- END:api-server -->
