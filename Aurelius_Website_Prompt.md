# AURELIUS — Study Tracker Website
## Master Build Prompt

---

## ROLE & IDENTITY

You are an expert UI/UX Designer and Frontend Architect specializing in **"Civic Luxury"** and **"High-Trust"** digital experiences. You build production-grade, premium interfaces that feel authoritative, calm, and intelligent — closer to Bloomberg Terminal or Apple Health than a student productivity app.

The product you are building is called **Aurelius** — a premium study tracking tool. The name evokes Marcus Aurelius: discipline, clarity, and the examined life. Every design decision must honor that brand identity.

---

## OBJECTIVE

Build a **fully functional, multi-page React application** for Aurelius using **Tailwind CSS** and **Recharts**. The website must include exactly two pages with full navigation between them:

1. **Landing Page (`/`)** — Brand hero, feature highlights, a live stats preview panel, and a primary CTA.
2. **Statistics Dashboard (`/stats`)** — A rich, data-visualization-forward dashboard displaying the user's full study session history, distraction log, and performance trends.

The entire site must adhere **strictly and without exception** to the design specifications in the sections below. There are no optional rules — every token, spacing value, easing curve, and chart constraint is mandatory.

---

## BRAND & TONE

- **Name:** Aurelius
- **Tagline:** *"Master your attention. Command your time."*
- **Brand Voice:** Calm authority. Never playful, never corporate-sterile. Think: a stoic philosopher who also happens to own a Patek Philippe.
- **Logo Treatment:** The wordmark "AURELIUS" in a micro-label style — `font-sans`, uppercase, `tracking-widest`, `font-semibold`, 13px. Optionally precede it with a minimal geometric mark (e.g., a thin circle or single vertical line in the Rose Gold accent).

---

## DESIGN SYSTEM — NON-NEGOTIABLE RULES

### Color Palette ("Quiet Luxury")
```
--color-canvas:      #F9F8F5   /* Warm Pearl — NEVER use #FFFFFF for page backgrounds */
--color-surface:     rgba(255, 255, 255, 0.60)  /* Liquid Glass card surface */
--color-text-primary:   #1A1A1A   /* Off-Black Charcoal — NEVER use #000000 */
--color-text-secondary: #666666   /* Slate */
--color-accent-trust:   #2C3E50   /* Midnight Blue — primary buttons, key accents */
--color-accent-metal:   #D7C3B3   /* Soft Rose Gold — decorative, borders, micro-labels */
--color-accent-platinum: #A8A9AD  /* Brushed Platinum — secondary accents */
--color-positive:    #2E7D32 on #E8F5E9  /* Muted Green — positive trend pills */
--color-negative:    #C62828 on #FFEBEE  /* Muted Red — negative trend pills */
--color-neutral-pill: #1A1A1A on rgba(0,0,0,0.06)  /* Neutral delta */
```

### Typography
Load **Instrument Serif** and **Inter** from Google Fonts. No other font families are permitted.

| Role | Font | Size | Weight | Letter-Spacing | Line-Height |
|---|---|---|---|---|---|
| Display / Hero Headline | Instrument Serif | 64px–96px | 400 | -0.03em | 1.05 |
| Section Headline | Instrument Serif | 40px–56px | 400 | -0.02em | 1.1 |
| Card Headline | Instrument Serif | 24px–32px | 400 | -0.02em | 1.2 |
| Body Copy | Inter | 15px–17px | 400–500 | 0 | 1.6 |
| Micro-Label / Tag | Inter | 10px–12px | 600 | 0.08em–0.1em | — |
| KPI Number (Stats) | Instrument Serif | 48px–72px | 400 | -0.03em | 1.0 |
| KPI Sub-label | Inter | 12px | 600 | 0.1em | — |

> 🚫 **BANNED:** Arial, Roboto, Times New Roman, any system font stack, font-weight 300.

### Spacing Grid
- Base unit: **8px**. Every margin, padding, gap, and layout value must be a multiple of 8.
- Permitted values: `8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 128px`.
- **Zero arbitrary values.** `margin: 13px` is a hard failure.
- Max page container: **1440px**. Prose/text columns: constrained to **640–800px**.

### Corner Radii (Proportional Scaling)
- Page-level cards / hero panels: `24px`
- Standard content cards: `16px`
- Buttons: `9999px` (pill) or `8px` (soft rect)
- Inner chart bars: `4px` top corners only (bottom corners square at baseline)
- Tags / pills: `9999px`

### Motion & Easing
- **ALL** transitions and animations must use: `cubic-bezier(0.25, 1, 0.5, 1)` — Exponential Out.
- > 🚫 **BANNED:** `ease-in-out`, `linear`, `ease`.
- Page load: Staggered fade-up reveals using `animation-delay` increments of `80ms`.
- Hover states: `translateY(-2px)` + subtle shadow deepening over `200ms`.
- Button press: `scale(0.97)` + `opacity: 0.9` — no color flash.
- Navigation transitions: Crossfade at `300ms`.

---

## COMPONENT SPECIFICATIONS

### A. The "Liquid Glass" Card (Use for ALL cards)
```css
background: rgba(255, 255, 255, 0.60);
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.20);
box-shadow:
  inset 0 1px 0 0 rgba(255, 255, 255, 0.40),  /* top-edge light catch */
  0 20px 40px -15px rgba(44, 62, 80, 0.10);    /* colored depth shadow */
border-radius: 16px;
```
Always include a `<div>` with `position: absolute; inset-x: 0; top: 0; height: 1px; background: rgba(255,255,255,0.50)` as the first child — this is the light-edge highlight.

### B. The "Expensive" Button
- **Primary (CTA):** Background `#2C3E50`, text `#F9F8F5`, pill shape, height `48px` (medium) or `56px` (large).
- **Secondary / Ghost:** `border: 1px solid rgba(44,62,80,0.20)`, transparent background, text `#2C3E50`, pill shape.
- Text: UPPERCASE, `letter-spacing: 0.08em`, `font-size: 12px–13px`, `font-weight: 600`.
- Hover: `translateY(-1px)` + shadow deepening.
- Click: `scale(0.97)`.

### C. KPI Stat Card
Three-layer hierarchy inside a Liquid Glass Card:
1. **Number** — `Instrument Serif`, `56px–72px`, `#1A1A1A`, `letter-spacing: -0.03em`.
2. **Label** — `Inter`, `11px`, `font-weight: 600`, `letter-spacing: 0.1em`, UPPERCASE, `#666666`.
3. **Trend Pill** — Rounded pill, `font-size: 11px`, `font-weight: 600`. Use color tokens above (green/red/neutral).

---

## PAGE 1: LANDING PAGE (`/`)

### Navigation Bar
- Full-width, `position: sticky`, `top: 0`, `z-index: 50`.
- Background: `rgba(249, 248, 245, 0.85)` + `backdrop-filter: blur(16px)`.
- Border-bottom: `1px solid rgba(0,0,0,0.06)`.
- Height: `64px`. Content: Logo left, nav links center (`Overview`, `Features`, `Stats`), CTA button right (`Start Tracking`).
- Nav links: `Inter`, `13px`, `font-weight: 500`, `#666666`, hover → `#1A1A1A`.

### Section 1: Hero
- Full viewport height (`100vh`).
- Background: `#F9F8F5` with a subtle radial gradient centered top: `radial-gradient(ellipse 80% 50% at 50% -10%, rgba(215, 195, 179, 0.25) 0%, transparent 70%)`.
- **Micro-label** above headline: `"FOCUS INTELLIGENCE PLATFORM"` — Rose Gold color.
- **Headline:** Two lines, large Instrument Serif. Example: *"The discipline to study.* / *The data to improve."*
- **Sub-headline:** `Inter`, `17px`, max-width `560px`, `#666666`, left-aligned (NOT centered).
- **CTA Group:** Primary button (`Start a Session`) + Ghost button (`View Demo Stats`), aligned left, `gap: 16px`.
- **Hero Visual:** Below or beside the copy — a floating Liquid Glass card showing a mock "Live Session" panel with a running timer (`02:47:13`), a focus score indicator, and a small spark-line. Subtle float animation: `translateY(-6px)` oscillating on a `4s ease-in-out infinite` cycle (exception: this single decorative animation may use ease-in-out).

### Section 2: Feature Highlights
- 3-column grid (collapse to 1-col on mobile), `gap: 32px`.
- Each card: Liquid Glass Card, `padding: 40px 32px`.
- Each card has: an icon (thin-stroke SVG, Rose Gold tint), a card headline (Instrument Serif, 22px), and 2–3 sentences of body copy (Inter, 15px, Slate).

Feature cards to include:
1. **Session Tracking** — Log study sessions with start/end times, subject tags, and goals. Understand how long you actually focus vs. how long you sit down.
2. **Distraction Intelligence** — Aurelius logs every interruption: notification source, app name, time elapsed, and how long it took you to re-engage. See exactly what's breaking your flow.
3. **Progress Analytics** — Weekly and monthly trend lines, streak tracking, and focus quality scores. Turn raw session data into actionable insight.

### Section 3: Stats Preview Teaser
- Full-width section, `padding: 128px 0`.
- Left side (50%): Section headline + body + CTA to `/stats` page.
- Right side (50%): A mocked-out, partially visible statistics dashboard card (blurred at the bottom edge with a fade-out gradient), hinting at the full stats page. Use real Recharts components with sample data.
- Headline: *"Your attention, quantified."*

### Section 4: Footer
- Minimal. `border-top: 1px solid rgba(0,0,0,0.06)`.
- `padding: 48px 0`. Copyright line + nav links.
- `Inter`, `12px`, `#666666`.

---

## PAGE 2: STATISTICS DASHBOARD (`/stats`)

This is the core product page. It must feel like a premium analytics console.

### Page Layout
- Left sidebar (`240px` wide, fixed): Navigation links for filter periods (Today, This Week, This Month, All Time) + subject/tag filters. Liquid Glass background.
- Main content area: scrollable, `padding: 48px 64px`.
- Top: Page title (`"Your Focus Report"`, Instrument Serif, 40px) + date range label (micro-label style).

### Row 1: KPI Cards (4 across)
Use the KPI Stat Card component. Display:
1. **Total Study Time** — e.g., `"142h 30m"` — Trend: `"+12% vs last month"`
2. **Sessions Completed** — e.g., `"47"` — Trend: `"+8 this month"`
3. **Avg. Focus Score** — e.g., `"84"` (out of 100) — Trend: `"+3 pts"`
4. **Total Interruptions** — e.g., `"213"` — Trend: `"-18% vs last month"` (this is good → green)

### Row 2: Primary Charts (2 columns)

**Left (60% width): Daily Study Duration — Line Chart**
- Chart type: Recharts `<LineChart>`.
- X-axis: dates (last 30 days), Y-axis: hours studied.
- One primary line: `stroke: #2C3E50`, `strokeWidth: 2.5`.
- Optional secondary line for "interruptions per session" on dual Y-axis if warranted; otherwise keep single.
- Gridlines: `stroke: rgba(0,0,0,0.04)`, horizontal only.
- No chart border. Axes labels in `Inter`, `11px`, `#A8A9AD`.
- Area fill beneath line: `fill: rgba(44, 62, 80, 0.05)`.

**Right (40% width): Study Time by Subject — Horizontal Bar Chart**
- Chart type: Recharts `<BarChart layout="vertical">`.
- Bars sorted descending by value.
- Y-axis: subject names (`Inter`, `12px`), X-axis: hours.
- Bar color: Use the Quiet Luxury palette — assign each subject a distinct but harmonious color (e.g., `#2C3E50`, `#D7C3B3`, `#A8A9AD`, `#4A6741`, `#8B7355`). NO random colors.
- Bar radius: `[0, 4, 4, 0]` (right-side radius only for horizontal bars).
- Zero baseline strictly enforced.

### Row 3: Distraction Intelligence Panel (Full Width)

This is Aurelius's signature feature section. It must be visually compelling.

**Left (50%): Interruption Source Breakdown — Donut Chart**
- Chart type: Recharts `<PieChart>` with `innerRadius`.
- Maximum 5 slices. Categories: `Messages`, `Social Media`, `Email`, `System Alerts`, `Other`.
- Colors from Quiet Luxury palette — NO default Recharts rainbow.
- Center of donut: Display total interruption count in KPI style (large number + "TOTAL INTERRUPTIONS" micro-label).
- Custom legend below chart: colored dot + label + count + percentage. Horizontally arranged, `gap: 24px`.

**Right (50%): Top Interrupting Apps — Ranked List**
- NOT a chart. A clean ranked list inside a Liquid Glass card.
- Each row: App icon placeholder (16px colored square using brand colors) + App name (`Inter`, `14px`, `#1A1A1A`) + interruption count on the right (`Inter`, `14px`, `font-weight: 600`, `#2C3E50`) + a thin background bar showing relative proportion behind each row (subtle, `rgba(44,62,80,0.06)`, full-width, behind text).
- Micro-label header: `"TOP DISTRACTION SOURCES — THIS MONTH"`.
- Rows: Instagram, iMessage, Slack, Gmail, Twitter/X, YouTube (in ranked order by count).

### Row 4: Session History Log (Full Width)

A clean, data-dense table of individual sessions.

- Column headers: `SESSION DATE`, `SUBJECT`, `DURATION`, `INTERRUPTIONS`, `FOCUS SCORE`, `NOTES`
- Header style: `Inter`, `11px`, `font-weight: 600`, `letter-spacing: 0.1em`, `#A8A9AD`. UPPERCASE.
- Row dividers: `1px solid rgba(0,0,0,0.05)`. No outer border on the table.
- `FOCUS SCORE` column: Render as a small colored pill (green 80+, amber 60–79, red <60).
- Rows: `padding: 16px 0`. Hover state: `background: rgba(44,62,80,0.03)`.
- Show 8–10 sample rows of plausible data.
- Below table: Ghost pill button — `"View All Sessions"`.

---

## SAMPLE DATA

Use this mock data throughout the application. All charts and stats must be populated — **no empty states on initial render.**

```js
const studySessions = [
  { date: "2024-01-15", subject: "Physics", duration: 120, interruptions: 4, focusScore: 88, notes: "Thermodynamics chapter" },
  { date: "2024-01-16", subject: "Mathematics", duration: 95, interruptions: 7, focusScore: 71, notes: "Integration practice" },
  { date: "2024-01-17", subject: "History", duration: 60, interruptions: 2, focusScore: 93, notes: "WW2 essay prep" },
  { date: "2024-01-18", subject: "Physics", duration: 145, interruptions: 9, focusScore: 65, notes: "Quantum mechanics intro" },
  { date: "2024-01-19", subject: "Literature", duration: 80, interruptions: 1, focusScore: 97, notes: "Hamlet analysis" },
  { date: "2024-01-20", subject: "Mathematics", duration: 110, interruptions: 5, focusScore: 82, notes: "Differential equations" },
  { date: "2024-01-21", subject: "Chemistry", duration: 75, interruptions: 3, focusScore: 90, notes: "Organic compounds" },
  { date: "2024-01-22", subject: "Physics", duration: 130, interruptions: 11, focusScore: 58, notes: "Electromagnetism" },
];

const distractionSources = [
  { name: "Messages",     value: 78, color: "#2C3E50" },
  { name: "Social Media", value: 54, color: "#D7C3B3" },
  { name: "Email",        value: 39, color: "#A8A9AD" },
  { name: "System Alerts",value: 28, color: "#4A6741" },
  { name: "Other",        value: 14, color: "#8B7355" },
];

const topApps = [
  { name: "Instagram",  count: 47 },
  { name: "iMessage",   count: 38 },
  { name: "Slack",      count: 29 },
  { name: "Gmail",      count: 22 },
  { name: "Twitter / X",count: 17 },
  { name: "YouTube",    count: 11 },
];

const dailyHours = [
  // 30 entries of { date: "Jan 1", hours: 2.5 } etc.
  // Generate plausible values ranging from 0.5 to 4.5 hours
];
```

---

## STRICT "AMATEUR" BAN LIST — VIOLATIONS ARE FAILURES

| Rule | Banned |
|---|---|
| Backgrounds | `#FFFFFF`, `#000000`, or any pure-value color for page bg |
| Shadows | Pure black `rgba(0,0,0,X)` — must be tinted with `#2C3E50` |
| Spacing | Any non-multiple-of-8 value (e.g., `margin: 13px`, `padding: 5px`) |
| Typography | Arial, Roboto, system-ui, font-weight 300 |
| Text alignment | Center-aligning body copy or long text blocks |
| Easing | `ease-in-out` or `linear` on UI transitions |
| Charts | 3D effects, default Recharts color palette, overlapping labels |
| Charts | Heavy dark gridlines — use `rgba(0,0,0,0.04)` only |
| Charts | More than 5 slices on any pie/donut chart |
| Charts | Y-axis not starting at zero on bar charts |
| Links | Default browser blue `#0000FF` |
| Code | Inline styles for values that break the grid |

---

## TECHNICAL REQUIREMENTS

- **Framework:** Next.js 14+ using the **App Router** (`/app` directory). All pages are React Server Components by default; add `"use client"` only where interactivity or hooks are required (e.g., chart components, sidebar filters).
- **Styling:** Tailwind CSS utility classes. Define custom design tokens (colors, fonts, shadows) in `tailwind.config.ts`.
- **Charts:** Recharts exclusively (`LineChart`, `BarChart`, `PieChart`, `Cell`, `Tooltip`, `Legend`). All Recharts components **must** be wrapped in a `"use client"` component. No Chart.js, no D3 raw, no Victory.
- **Routing:** Next.js App Router file-based routing.
  - `/app/page.tsx` → Landing Page
  - `/app/stats/page.tsx` → Statistics Dashboard
  - `/app/layout.tsx` → Root layout (navbar, fonts, global styles)
- **Fonts:** Use `next/font/google` to load `Instrument_Serif` and `Inter` — never a raw `<link>` tag. Apply via CSS variables in `layout.tsx`:
  ```ts
  import { Instrument_Serif, Inter } from 'next/font/google';
  const instrumentSerif = Instrument_Serif({ weight: '400', subsets: ['latin'], variable: '--font-serif' });
  const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
  ```
- **Navigation:** Use `<Link>` from `next/link` for all internal navigation. The navbar should be in a shared `components/Navbar.tsx` client component and imported into `/app/layout.tsx`.
- **Icons:** Lucide React (`lucide-react`) for all iconography. Thin stroke, consistent sizing at `16px` or `20px`.
- **State:** React `useState` for active filter period and sidebar selection inside `"use client"` components. No external state library needed.
- **No placeholder images.** Use SVG-based abstract shapes, gradient blocks, or Lucide icons as all visual elements. If images are needed, use `next/image`.
- **TypeScript:** Use `.tsx` / `.ts` for all files. Define explicit interfaces for all data shapes (e.g., `StudySession`, `DistractionSource`).

### Recommended File Structure
```
/app
  layout.tsx          ← Root layout: fonts, navbar, global CSS vars
  page.tsx            ← Landing page (Server Component)
  globals.css         ← Tailwind base + CSS custom properties
  /stats
    page.tsx          ← Stats dashboard shell (Server Component)
/components
  Navbar.tsx          ← "use client" — sticky nav with active link state
  LiquidCard.tsx      ← Reusable Liquid Glass card wrapper
  KpiCard.tsx         ← "use client" — KPI stat card with trend pill
  /charts
    DailyHoursChart.tsx    ← "use client" — Recharts LineChart
    SubjectBarChart.tsx    ← "use client" — Recharts BarChart
    DistractionDonut.tsx   ← "use client" — Recharts PieChart
  TopAppsList.tsx          ← Ranked distraction apps list
  SessionTable.tsx         ← Study session history table
/lib
  data.ts             ← All mock data (studySessions, distractionSources, etc.)
  types.ts            ← TypeScript interfaces
tailwind.config.ts
```

---

## FINAL QUALITY CHECKLIST

Before considering the build complete, verify every item:

- [ ] Background is `#F9F8F5`, never white.
- [ ] All cards use the Liquid Glass specification (blur, border, inner shadow, colored drop shadow).
- [ ] All headlines use Instrument Serif with negative tracking.
- [ ] All spacing is on the 8px grid.
- [ ] All transitions use `cubic-bezier(0.25, 1, 0.5, 1)`.
- [ ] All chart Y-axes start at zero.
- [ ] No chart has more than 5 colors / slices without falling back to bar chart.
- [ ] Chart gridlines are `rgba(0,0,0,0.04)` or lighter.
- [ ] KPI cards show number → label → trend pill in correct hierarchy.
- [ ] Buttons are pill or soft-rect shaped, uppercase, tracked out.
- [ ] Donut chart center shows total count KPI.
- [ ] Session log table has colored focus score pills.
- [ ] All sample data is populated — no empty states.
- [ ] Site navigates correctly between Landing and Stats page.
