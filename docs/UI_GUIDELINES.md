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
- Columns: Аккаунт · Дата публикации · Тип · Заголовок · Ссылка · Описание · Лайки · Просмотры · Дней с публикации · Просмотров/день · Лайков/день · ★ (shortlist)
- Every column sortable (server-side); active sort indicated; default sort «Просмотров/день» desc.
- Views for посты/карусели render «—» (never 0); «—» sorts after numbers.
- Тип as label + icon: Reels / Пост / Карусель.
- Заголовок = caption first line, truncated ~60 chars with tooltip; Ссылка opens IG in new tab.
- Pagination 50 rows/page.

## Run flow UX
1. «Запустить анализ» → dialog: duration select (1–7 дней) → «Рассчитать стоимость»
2. Estimate shown («≈ $0.35 · 12 аккаунтов · до ~120 публикаций») → «Подтвердить и запустить»
3. Progress state on Результаты tab: status in Russian (В очереди / Сбор данных 4/12 / Создание описаний 80/120) with progress bar, polling every 2s
4. Failure → red banner with error_message and «Повторить»

## Responsive / mobile (D16)

- Mobile-first Tailwind: base styles target 375px, `md:`/`lg:` add desktop layout. No fixed pixel widths on layout containers.
- Every screen must be **usable** (not just rendered) at 375px: tap targets ≥44px, forms full-width, dialogs become full-screen sheets on mobile.
- Project tabs (Конкуренты / Результаты / Шорт-лист / История) collapse to a horizontally scrollable tab bar on mobile.
- **Tables (results, shortlist, history):** MVP behavior on small screens is horizontal scroll *inside the table container* (page never scrolls sideways) with a sticky first column (Аккаунт) and sticky header. Post-MVP polish: card layout per row on mobile (title + summary + key metrics), tracked as its own backlog story.
- Run dialog, progress bar, and «Экспорт в Excel» / «Запустить анализ» actions must all work on mobile.
- Definition of done for any UI story includes a check at 375px viewport (dev tools or browser preview `resize_window` mobile preset).

## Visual style
- Tailwind; clean SaaS dashboard, light theme for MVP. Dense-but-readable data table (the table IS the product).
- Loading: skeleton rows. Empty states with a next-action hint («Добавьте аккаунты конкурентов, чтобы запустить первый анализ»).
- Follow the frontend-design skill when building screens; avoid generic AI-slop aesthetics.
