# DESIGN_SYSTEM v2 — «Acid Instrument» (D31)

Approved 2026-07-23 from the UI/UX review session. **Supersedes the D28 v1 palette/typography** (violet `#6E56CF` + Unbounded). Everything else in `docs/UI_GUIDELINES.md` (Russian-only, mobile-first 375px, cards below 768px, bottom tab bar, lucide-only icons, light-only) still applies.

**Visual reference:** `docs/design/redesign-mockup-v2.html` — open it in a browser; it shows all five redesigned screens (Проекты, Детали, Новый анализ, Публикации, Токены) built with these exact tokens. When rebuilding a screen, match the mockup.

---

## 1. Direction

Graphite + acid lime on cold porcelain — the current language of fintech/data instruments (2026 dashboard tier). Principles:

1. **Neutral base, one high-vibrancy accent.** The UI is graphite-on-porcelain; lime appears only where value/action lives.
2. **The accent is a currency — spend it sparingly.** Lime = primary CTA, token balance, high virality, active-state highlights. If lime appears more than ~3 times on a screen, something is wrong.
3. **Color is functional, never decorative.** Green/red exist only for run status. Virality is a heat scale, not a traffic light.
4. **Numbers are the brand.** Every numeral, @handle, timestamp, ID renders in JetBrains Mono with tabular figures.
5. **Data is quiet, actions are loud.** Static metrics are plain text (never chips/pills); interactive controls are pills.

## 2. Tokens — `globals.css` replacement

```css
@theme {
  --color-bg: #F4F5F2;          /* cold porcelain page background */
  --color-card: #FFFFFF;
  --color-ink: #16181D;          /* graphite — text AND inverse surfaces */
  --color-secondary: #5C6470;
  --color-border: #E4E6E1;

  --color-lime: #D6F344;         /* THE accent. Fill only, always with ink text */
  --color-lime-soft: #EFF6D8;    /* soft accent backgrounds */
  --color-olive: #3F6212;        /* accent as TEXT (on white/lime-soft) */

  --color-success: #166534;      /* run status only */
  --color-success-soft: #E4F3E9;
  --color-danger: #B91C1C;       /* run failures + truly destructive actions only */
  --color-danger-soft: #FBEAEA;

  /* virality heat scale */
  --color-heat-med-bg: #EFF6D8;  --color-heat-med-tx: #3F6212;
  --color-heat-low-bg: #EDEEEA;  --color-heat-low-tx: #5C6470;
  /* heat-high = inverse chip: bg ink, text lime (no dedicated tokens) */

  --font-sans: var(--font-golos), system-ui, sans-serif;
  --font-mono: var(--font-jetbrains-mono), ui-monospace, monospace;

  --radius-card: 1.125rem;       /* 18px */
  --radius-control: 0.75rem;     /* 12px — inputs, non-pill controls */
  --radius-chip: 9999px;         /* pills: buttons, segments, chips, badges */
}
```

Contrast: all pairs verified ≥4.5:1 (ink/lime 14.2, olive/white 7.1, secondary/card 6.0, danger/soft 5.6). Do not lighten `olive`, `success`, `danger` — they sit near the floor on their soft backgrounds.

### Hard color rules

- **Lime is never text on a light background** (2.4:1 — always fails). Lime = fill with ink text, or text only on ink. For accent-colored text on light surfaces use `olive`.
- **`danger` is not for reversible actions.** «Архивировать» is a normal ink menu item (v1 got this wrong).
- **Progress ≠ warning.** In-progress runs use `lime-soft`/`olive` pill («Идёт анализ»), never yellow/warning. There is no warning color in v2; if a true warning state appears later, add one via a DECISIONS entry.
- **Low virality is neutral gray, not red.** Red implies error; low performance is information.

## 3. Typography

Fonts via `next/font/google` in `app/layout.tsx`:
- **Golos Text** (`--font-golos`) — all UI text. Keep (already installed).
- **JetBrains Mono** (`--font-jetbrains-mono`, weights 400/500/600/700, `subsets: ["latin", "cyrillic"]`) — replaces Unbounded, which is **removed** (it was loaded for one header line).

Scale (mobile base):

| Role | Spec |
|---|---|
| Micro-label | 11px / 600 / uppercase / `tracking-[0.08em]` / secondary — section labels, KPI captions |
| Secondary | 13px / 400 / secondary |
| Body | 15px / 400 / ink |
| Card title | 16px / 600 / ink / `tracking-tight` |
| App-bar title | 17px / 600 / ink (the ONLY page title — no in-body `<h1>` duplicates) |
| Hero number | 34–40px / mono 600 / `tracking-[-0.03em]` — bento hero, token balance |
| KPI number | 24px / mono 600 |
| Metric/mono text | 11.5–13px / mono 500 / `tabular-nums` |

**Mono applies to:** all numerals, @handles, timestamps, run IDs, token amounts, day/time picker chips. Never to Russian sentences.

## 4. Component recipes

All interactive elements: min 40px tap target (44px preferred), `active:scale-[0.98]` pressed state (this is a touch app — hover is a desktop bonus, never the only feedback), `focus-visible:ring-2 ring-ink/20`. Add Telegram haptic (`impactOccurred('light')`) on star-toggle, run-start, and segment switches.

**Primary button** — lime pill: `h-[50px] w-full rounded-chip bg-lime text-ink font-semibold text-[15px]` + soft lime shadow (`shadow-[0_8px_20px_rgba(140,170,20,0.30)]`). Reserved for the screen's ONE main action.

**Dark button** (secondary emphasis, e.g. inside ink surfaces): `bg-ink text-lime rounded-chip h-12`.

**Ghost button:** `h-12 rounded-chip border border-border bg-card text-ink text-sm`.

**Segmented control** — pill track `bg-[#E9EBE6] rounded-chip p-[3px]`; active thumb `bg-ink text-white rounded-chip font-semibold`; optional count badge: inactive `bg-[#DDDFD9] text-secondary`, active `bg-lime text-ink`, mono 11px.

**Selection chips** (day-of-week, day-count, month): `h-[42px] rounded-[10px] border border-border bg-card font-mono text-[13px]`; selected: `bg-ink border-ink text-lime font-semibold`. Grid layout (`grid-cols-7` for days) — never wrapping flex.

**Heat badge (виральность)** — one component, three variants, always icon `Flame` + label (never color alone):
- high: `bg-ink text-lime` (the inverse chip — the signature scan-anchor of the feed)
- medium: `bg-heat-med-bg text-heat-med-tx`
- low: `bg-heat-low-bg text-heat-low-tx`, no flame icon

**Status pill (runs):** dot + label, 11.5px: done `bg-success-soft text-success`; in-progress `bg-lime-soft text-olive`; failed `bg-danger-soft text-danger`.

**Static metrics** — NOT chips. Plain inline `text-secondary`: lucide icon 13px + mono value, gap-1.5, items separated by `gap-x-3`. Values non-breaking (`whitespace-nowrap`). «—» for missing IG view counts (never 0).

**Bento KPI grid:** `grid grid-cols-2 gap-2`; hero cell `col-span-2 bg-ink text-white rounded-card` with lime mono number; satellite cells `bg-card border border-border` with 24px ink numbers under micro-labels.

**App bar:** translucent glass — `bg-bg/80 backdrop-blur-lg`; round icon buttons (`rounded-chip border border-border bg-card`); token balance pill `bg-lime-soft border-[#DCE9B8] text-olive font-mono`.

**Bottom sheet — ONE component** (today there are four implementations: `ui/bottom-sheet.tsx`, `run-dialog.tsx`, usage `RunDetailSheet`, `ShortlistSortBottomSheet`). Spec: `rounded-t-[24px]`, grab handle, header row with title + X, scrollable body, optional sticky footer, `env(safe-area-inset-bottom)`, slide-up 240ms ease-out, body scroll lock. Migrate all four to it.

**One formatter each** in `lib/format.ts`: `formatNumber` (ru-RU, space thousands), `formatDate`/`formatDateTime` (one implementation — delete the three ad-hoc copies in usage page / results page / run detail page).

## 5. Per-screen specs (match the mockup)

**Проекты** — app-bar title only; segmented Активные/Архив with counts; cards carry name + status pill + meta row (`N конкурентов · анализ <когда>` in mono values); never-run state gets an olive nudge in the meta row; «Новый проект» = full-width lime pill pinned bottom (gradient fade over content), NOT a small top-right button. Empty state includes the CTA button.

**Детали** — bento grid: hero cell «Публикаций проанализировано» (ink bg, lime 38px number), satellites Конкуренты / Аудитория. ⚠️ v1 shows `lifetime_items_analyzed` for both публикации and токены — drop the tokens KPI until the real `usage_events` sum is wired. Below: «Последний анализ» card (micro-label + status pill, date + item count, lime «Запустить анализ» — the app's primary CTA lives HERE, on the project landing screen). Nav rows to Конкуренты/Расписание with round lime-soft icon, bold label + informative sub-line («12 аккаунтов · @glossy.daily добавлен вчера», «Каждый вторник в 09:00 · включено»).

**Новый анализ (sheet)** — three micro-labeled sections: ОБЪЁМ АНАЛИЗА (segmented За период / Последние N + 7-col mono chips + plain-text summary line «Публикации за последние 3 дня · 12 аккаунтов»); ЗАПУСК (segmented Сейчас / По расписанию; schedule fields in a `bg-bg rounded-[14px]` inset: 7-col weekday chips + styled time row with clock icon and «Москва»); СТОИМОСТЬ (lime-soft row: «Оценка стоимости ≈ N ток./запуск» — computed, not the vague v1 note). Sticky footer: one lime pill whose label states the outcome — «Запустить анализ» or «Запланировать: вт, 09:00».

**Публикации (внутри анализа)** — controls row of pill icon-buttons (sort shows active label «Виральность», active = ink fill); cards: 58px rounded cover thumbnail (type icon on neutral gradient as fallback until R2 thumbnails exist, D25), mono `@handle · 890K`, heat badge right, 2-line expandable summary, quiet metric row (heart/comment/eye + mono values + `ER 6,4%`), 40px star top-right (filled = olive). Pagination → «Показать ещё · N» ghost button.

**Токены (usage)** — kill the `<table>` (violates D16 card rule). Hero balance card: ink bg, БАЛАНС micro-label, lime 40px mono number, divider, «Потрачено в июле» + mono value (this replaces the duplicate balance row — the header pill and page hero are the same number, shown once each). Month picker = horizontal chips (active ink/lime), not tiny chevrons. Runs list: one card, rows grouped under day micro-labels: mono time · project name · signed mono delta («−860») · chevron → detail bottom sheet (unified Sheet component).

## 6. Migration checklist (ordered, for the rebuild session)

1. `globals.css`: swap `@theme` to §2; `layout.tsx`: replace Unbounded with JetBrains Mono; delete the `font-display` usage in app-bar.
2. `components/ui/index.tsx`: rebuild Button (3 variants, pill), TabChip→Segmented, Badge→StatusPill + HeatBadge; add pressed/focus states everywhere.
3. Unify Sheet (4 implementations → 1) and formatters (3 date + 2 number → 1 each).
4. Rebuild the five screens per §5 against the mockup (mobile-first; desktop `md:` keeps current structure where it exists).
5. Sweep for stragglers: `text-[10px]` (→ 11px min), `hover:`-only feedback, `text-danger` on archive actions, warning-yellow statuses, `<table>` at mobile widths, duplicate in-body `<h1>`.
6. Verify each screen at 375px (`resize_window` mobile preset) + re-run the contrast pairs if any hex changes.

All UI strings still go through `next-intl` (`messages/ru.json`); new strings needed: cost-estimate line, «Показать ещё», day-group labels, nav-row sub-lines.
