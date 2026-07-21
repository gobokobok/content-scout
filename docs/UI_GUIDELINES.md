# UI_GUIDELINES — content-scout

## Language
- Russian only (D8). Every string from `frontend/messages/ru.json` — hardcoded UI text fails review.
- Tone: neutral professional («Запустить анализ», not «Погнали!»). Numbers formatted ru-RU (space thousands separator: 12 500).
- Dates: `dd.MM.yyyy HH:mm`, user's local timezone (data stored UTC).

## Navigation structure

```
/login, /register          — auth screens
/projects                  — workspace home: project list + «Создать проект»
/projects/[id]             — project shell with tabs:
   Конкуренты   — competitor list manager (counter «N / 50», platform tabs; only Instagram enabled)
   Результаты   — run selector + results table + «Запустить анализ» + «Экспорт в Excel»
   Шорт-лист    — shortlisted items (+ disabled «Создать сценарий» → tooltip «Скоро»)
   История      — past runs and shortlist activity
/usage                     — «Использование»: current month consumption
/admin                     — admin-only usage across users
```

## Results table
- Columns: Аккаунт (+ подписчики) · Дата публикации · Тип · Заголовок · Ссылка · Описание · Лайки · Комментарии · Виральность · Вовлечённость · Дней с публикации · Просмотров/день · Лайков/день · ★ (shortlist)
- Every sortable column is server-side sorted; active sort indicated; default sort «Просмотров/день» desc. Виральность is a badge, not sorted directly — sort by Вовлечённость for a cross-account ranking instead.
- Просмотры has no dedicated column: Instagram doesn't expose view counts for most post types, so a raw views column was judged misleading and removed (views still feed Просмотров/день for reels).
- **Виральность** (E5-S5) is scored **relative to that account's own median engagement within the current run** — never an absolute/industry threshold. A meme account and a niche B2B account have wildly different normal engagement, so comparing either to a fixed number would be meaningless. Accounts with fewer than 3 items in the run show «недостаточно данных» instead of a badge. **Вовлечённость** (`engagement_rate = (лайки + комментарии) / подписчики`) is the separate cross-account question — use it, not the badge, to compare raw performance between different competitors.
- Тип as label + icon: Reels / Пост / Карусель.
- Заголовок = caption first line, truncated ~60 chars with tooltip; Ссылка opens IG in new tab.
- Pagination 50 rows/page.

## Run flow UX
1. «Запустить анализ» → dialog: duration select (1–7 дней) → «Рассчитать стоимость»
2. Estimate shown («≈ $0.35 · 12 аккаунтов · до ~120 публикаций») → «Подтвердить и запустить»
3. Progress state on Результаты tab: status in Russian (В очереди / Сбор данных 4/12 / Создание описаний 80/120) with progress bar, polling every 2s
4. Failure → red banner with error_message and «Повторить»

## Responsive / mobile (D16, updated by D28)

- Mobile-first Tailwind: base styles target 375px, `md:`/`lg:` add desktop layout. No fixed pixel widths on layout containers.
- Every screen must be **usable** (not just rendered) at 375px: tap targets ≥44px, forms full-width, dialogs become bottom sheets on mobile.
- **Navigation on mobile:** bottom tab bar (Результаты / Конкуренты / Шортлист / История inside a project), `env(safe-area-inset-bottom)` respected — this is the Telegram-Mini-App-native pattern (D17). Desktop keeps top tabs.
- **Tables (results, shortlist, history):** below `md` (768px) rows render as **cards** (cover placeholder, @handle, one-line summary, metric chips with «просм./день» highlighted); the dense table is the ≥`md` experience with sticky header + sticky first column. Sorting on mobile via a sort chip + bottom sheet. (E12-S2; supersedes the old horizontal-scroll-only rule.)
- No hover-only affordances anywhere — everything must work by tap.
- Definition of done for any UI story includes a check at 375px viewport (browser preview `resize_window` mobile preset).

## Design system v1 (D28) — light only

Dark mode is **removed** (no `dark:` classes). Tokens live in `globals.css` (`@theme`); components never hardcode hex.

**Palette**
| Token | Value | Use |
|---|---|---|
| bg | `#F6F7F9` | page background (never pure white pages) |
| card | `#FFFFFF` | cards, sheets, table surface |
| ink | `#1A1523` | primary text |
| secondary | `#6F6E77` | secondary text, labels |
| border | `#E4E2E9` | hairlines |
| accent | `#6E56CF` (hover ~`#5D48B8`) | primary buttons, active tab/pill, links |
| accent-soft | `#EDE9FE` | accent backgrounds (avatars, active chips) |
| success | `#30A46C` / soft `#E9F9F1` | hero metric chip (просм./день), positive states |
| warning/star | `#FFB224` | shortlist star, warnings |
| danger | `#E5484D` | errors, destructive actions |

**Type:** Golos Text (UI/body/data — Cyrillic-first, tabular figures on metric columns) + Unbounded (logo «scout.» and rare display accents), both via `next/font/google`.

**Shape:** cards 14px radius, controls/buttons 12px, chips/pills 999px; hairline borders, soft elevation only where needed (bottom sheets).

**Icons:** `lucide-react` only — never emoji/unicode glyphs as UI.

**States:** skeleton loaders (never «Загрузка…» text), toasts for transient errors, designed empty states with a next-action hint («Добавьте аккаунты конкурентов, чтобы запустить первый анализ»).

Follow the frontend-design skill when building screens; avoid generic AI-slop aesthetics. The approved visual direction (mockup from the 2026-07-18 review): white cards on `#F6F7F9`, violet pill tabs, metric chips, bottom nav.
