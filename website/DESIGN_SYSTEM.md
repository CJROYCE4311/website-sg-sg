# SG@SG Design System — "Clubhouse Modern"

Premium golf-club aesthetic: deep pine greens, warm ivory neutrals, one gold accent, serif display type. The entire system lives in the `<style>` block of `index.html` — copy it verbatim onto every page (or extract to `sgsg.css` and link it).

## Tokens (CSS custom properties)
- **Greens:** `--pine-950 #0B1F17` · `--pine-900 #10281F` · `--pine-800 #173626` · `--pine-700 #1E4634` · `--pine-600 #2A5A44`
- **Gold accent (sparingly):** `--gold-500 #A98644` · `--gold-400 #C2A15C` · `--gold-300 #D8BE85`
- **Neutrals:** page bg `--ivory-50 #F5F2EA` · card `--paper #FCFBF7` · inset `--ivory-100 #EDE8DA` · border `--line #E3DECE`
- **Text:** `--ink-900 #1C2420` · `--ink-600 #4C564F` · `--ink-400 #79837B`
- **Type:** Playfair Display (h1/h2/display, weights 500–700) + Archivo (everything else, 400–700)
- **Shape:** radius 18/12/8px; shadows `--shadow-card` / `--shadow-lift`; 8-pt spacing (`--space-1…6`)

## Component classes (reusable as-is)
- `.app-container` + `.sidebar` + `.main-content` — shell. Sidebar: pine gradient, gold icons, `.nav-btn.active` gets gold inset bar. Mark the current page's nav item `active`.
- `.top-header` + `.header-content` — slim page-title strip. Per page: swap `.eyebrow` + `<h2>` (e.g. "Money List" / "2026 Season Payouts").
- `.eyebrow` — gold uppercase label with leading rule. Use above every section title.
- `.brand-band` — dark hero panel. Subpages: reuse shorter, drop `.brand-logo-panel`.
- `.glass-panel` / `.card` — standard elevated card (name kept for legacy markup).
- `.stat-card` (+ one `.accent-card` max per grid) — KPI tiles. Great for Money List totals.
- `.link-card` (+ one `.primary-link`) — navigation tiles.
- `.primary-action` (gold pill, ONE per page) / `.secondary-action` (+`.on-light` on light bg) / `.small-link`.
- `.result-row` — archive rows: `<a class="result-row"><span style="display:flex;align-items:center"><span class="dot"></span><span class="row-date">…</span></span><span class="row-format">…</span></a>`. Legacy purple Tailwind rows are auto-overridden, but update the generator to emit `.result-row`.
- `.date-grid` + `.date-next` — calendar chips.
- `.contact-band` — dark footer band.

## Data tables (Money List, Player Stats, Hole Index)
No table on the homepage, so use this recipe: wrap in `.card.glass-panel`; `border-collapse: collapse`; header row — 12px uppercase, letter-spacing 0.12em, color `--ink-400`, bottom border 1px `--line`; body rows — 15px, `font-variant-numeric: tabular-nums` for numbers, row hover `background: var(--ivory-100)`; leader/top row may use gold text `--gold-500` or a `.accent-card`-style highlight. Money values right-aligned.

## Rules of thumb
- Max two background colors per page: ivory field + pine dark bands. Gold is an accent only — never a background for large areas.
- One `.primary-action` and one `.accent-card`/`.primary-link` per page.
- Lucide icons: 1.5 stroke-width; on dark chips `background: var(--pine-900); color: var(--gold-400)`.
- Keep Tailwind CDN on pages whose content is script-generated; the `.prose` and `.results-log` overrides in the stylesheet re-skin generated blocks.
- Charts (AverageScore): use pine-600 as series color, gold-400 for highlights, `--line` gridlines on `--paper`.

## Assets
`assets/sgsg-tournament-logo.png` and `assets/IMG_Sign-Ups.png` here are generated placeholders — replace with the real files on deploy (paths unchanged).
