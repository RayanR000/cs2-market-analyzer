---
target: homepage
total_score: 27
p0_count: 1
p1_count: 2
timestamp: 2026-07-08T02-41-21Z
slug: frontend-app-page-tsx
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | No loading state; fallback data silently replaces live data (page.tsx:116-148) |
| 2 | Match Between System and Real World | 4 | Language matches analyst mental model throughout |
| 3 | User Control and Freedom | 3 | Theme toggle present; no undo/back or item customization |
| 4 | Consistency and Standards | 4 | Tokens consistent; hero stats bypass StatCard component |
| 5 | Error Prevention | 2 | Error swallowing at page.tsx:143; no API response validation |
| 6 | Recognition Rather Than Recall | 3 | Navigation visible; capability section doesn't link to features |
| 7 | Flexibility and Efficiency of Use | 2 | No shortcuts, no search on homepage, read-only surface |
| 8 | Aesthetic and Minimalist Design | 4 | Strongest score — calm, restrained, data-forward |
| 9 | Error Recovery | 1 | Zero error states; failures silently replaced with fallback |
| 10 | Help and Documentation | 2 | No tooltips or onboarding; assumes domain expertise |
| **Total** | | **27/40** | **Acceptable** |

## Anti-Patterns Verdict

**LLM assessment**: The page does not trigger the "AI made this" reflex. No gradient text, no glassmorphism, no hero-metric template, no numbered section markers, no identical card grids. The capability section renders distinct inline widgets per card. The carbon dark palette with warm amber is executed with discipline. A faint category-echo exists — the "DATA TERMINAL" branding + uppercase monospace + carbon dark could be guessed from the "financial terminal" aesthetic alone — but the design's originality lives in restraint rather than novel visual language.

**Deterministic scan**: CLI detector returned zero findings. Manual review caught 5 issues: hardcoded rarity colors in ItemCard (Medium), missing focus states globally (Medium), muted text contrast fails WCAG AA in both themes (Medium), inline conditional styles (Low), unused StatCard prop (Low). No false positives.

## Overall Impression

This is a disciplined, well-scoped product homepage. The strongest quality is what it *doesn't* do — no decoration, no gaming clichés, no information overload. The data typography hierarchy (JetBrains Mono for numbers, Inter for UI) creates instant visual distinction. The section spacing is confident. The biggest opportunity: the homepage currently has zero interactivity — it's a read-only billboard for a tool that's described but never demonstrated.

## What's Working

1. **Restraint as brand identity** — The anti-pattern discipline is well-enforced. The widget-block pattern (border + background shift on hover, no shadow) is elegant and consistent. Every element earns its space.

2. **Data typography hierarchy** — font-data with tabular-nums for all numeric content creates immediate signal distinction. The 10px uppercase tracking labels vs. 3xl data values creates excellent hierarchy.

3. **Section spacing and breathing room** — pb-32 lg:pb-44 between sections provides generous, confident spacing. The design trusts whitespace to guide the eye.

## Priority Issues

### [P0] Silent data fallback — Critical trust issue
API errors are caught and swallowed (page.tsx:143). Fallback data at lines 18-51 and 117 silently replaces live data. The user sees "24H Volume: $2,481,290" with no indication this is fabricated. An analytical instrument showing fake data without warning violates the core contract — users make financial decisions on this data.
**Fix**: Add a visible error state — a subtle banner or muted toast: "Live data unavailable — showing cached values." When fallback is active, add a small indicator on stats.
**Suggested command**: $impeccable harden

### [P1] Hero stats bypass StatCard component
The hero section (page.tsx:173-215) hand-builds stat displays with inline markup instead of using the existing StatCard component. Different markup, same data pattern. Creates maintenance drift and means hero stats lack CountUpNumber animation.
**Fix**: Refactor hero stats to use StatCard with a variant prop, or extract a shared HeroStat component.
**Suggested command**: $impeccable polish

### [P1] Muted text fails WCAG AA contrast
--text-muted (38% L in dark, 72% L in light) on respective backgrounds yields ~2.7:1 and ~3.2:1 ratios — both below the 4.5:1 minimum for small text. Affects ItemCard type labels, footer copyright, Header subtitle, StatCard annotations across both themes.
**Fix**: Bump --text-muted in dark mode to ~45% L (oklch(45% 0.003 30)) and in light mode to ~60% L. Verify contrast after change.
**Suggested command**: $impeccable colorize

### [P2] No loading or empty states on homepage
Zero loading indicators. No skeleton for trending items, no shimmer for stats, no empty state if API returns no trending items. Creates uncanny valley — data appears instantly from fallback, then may or may not update.
**Fix**: Add skeleton states for trending cards and a loading indicator for stats. Show fallback immediately but with "Loading live data..." that resolves.
**Suggested command**: $impeccable polish

### [P2] Missing keyboard focus indicators
globals.css:208-210 removes outline on all form inputs with no visible replacement. Violates WCAG 2.4.7. Interactive elements need visible focus indicators.
**Fix**: Add focus ring styles (2px solid accent with 2px offset per design system spec).
**Suggested command**: $impeccable harden

## Minor Observations

- ItemCard glow effect (blur-[80px] bg-white opacity-[0.03]) is nearly invisible — contributes nothing visually
- Header progress-line animation runs infinitely as decoration, contradicting "motion conveys state" principle
- Stats volume24h calculation uses magic number avgPrice * 2800
- ItemCard transition-all duration-300 is 50ms longer than design system's 250ms standard
- CapabilityCard description max-w-xs may orphan words at some viewports

## Questions to Consider

1. If a first-time user sees "$2,481,290" as 24H Volume, do they know what unit this is? USD? Skin-value-adjusted? Should there be a unit label?
2. The capabilities section ("What this does") is brochure filler in an instrument. Could it be replaced by inline feature hints on the market page?
3. The hero section is literally 3 metrics — does this violate the design system's "No hero-metric template" rule, or is the distinction that these serve the narrative rather than being the hero itself?
4. The fallback items (Vulcan, Asiimov, Printstream, Butterfly Fade) are hardcoded. What happens if a user clicks into an item that doesn't exist in the real database?
