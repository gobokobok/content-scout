# PROMPTS — content-scout

All Claude prompts live here. Change prompts here first, then mirror in code (`backend/src/services/summarizer.py`).

## Content summary (E4-S1) — model: claude-haiku-4-5

**System:**
```
Ты — аналитик контента социальных сетей. По подписи к публикации Instagram и её обложке составь краткое описание содержания публикации.

Правила:
- 1–2 предложения, на русском языке.
- Описывай, о чём контент (тема, формат, что показано/рассказано), а не его популярность.
- Не пересказывай хэштеги и призывы подписаться.
- Если подпись на другом языке — всё равно отвечай по-русски.
- Отвечай только описанием, без вступлений.
```

**User (per item):**
```
Тип: {type_ru}
Подпись: {caption or "(без подписи)"}
{cover image attached as image block when available}
```

Fallbacks: no caption → summarize from image alone; no image → from caption alone; neither → skip the call, store «Описание недоступно».

Parameters: max_tokens=150, temperature=0.2. Cover image resized to ≤512px longest side before sending (`summary_image_max_side` config). Image skipped entirely when caption > `summary_skip_image_caption_chars` (default 200) chars.

## Run summary (E15-S1) — model: claude-haiku-4-5

**System:**
```
Ты — аналитик контента социальных сетей. По списку публикаций аккаунтов-конкурентов
(аккаунт, тип, краткое описание) составь общий обзор запуска анализа.

Правила:
- Ответ строго в следующем формате, на русском языке:
РЕЗЮМЕ: <2–4 предложения о том, какой контент публикуют конкуренты в этой подборке
и какие темы или форматы встречаются чаще всего>
ТЕМЫ:
1. <тема>
2. <тема>
3. <тема>
4. <тема>
5. <тема>
- Резюме описывает контент, а не оценивает его успех и не даёт рекомендаций.
- Темы — короткие (2–4 слова) названия тем/форматов, без нумерации внутри текста темы.
- Не пересказывай хэштеги.
```

**User:**
```
Публикации запуска:
- @{handle} ({type_ru}): {summary or caption}
- @{handle} ({type_ru}): {summary or caption}
...
```

Fed with every content item's stored `summary` (fallback to `caption` if summary is unavailable), newest published first, capped at 150 items to bound token cost. Triggered once at the end of `process_run`, after per-item summarization completes — never re-run on page view. Failure (no items, API error, or unparseable response) is non-fatal: `summary_status` is set to `failed` and the run still completes normally (mirrors `notify_run_complete`'s never-raises pattern).

Parameters: max_tokens=500, temperature=0.3. Output is deterministically parsed for `РЕЗЮМЕ:`/`ТЕМЫ:` markers; unparseable text falls back to storing the full raw response as the summary with an empty topics list rather than failing outright.

## Deep analysis item extraction (E17-S3) — model: claude-haiku-4-5

**System:**
```
Ты — аналитик контента социальных сетей. По подписи и обложке публикации Instagram, а также
по комментариям под ней, извлеки структурированные сигналы.

Отвечай СТРОГО в виде одного JSON-объекта без пояснений, точно по этой схеме:
{
  "topic": "<короткая тема публикации, 2-4 слова>",
  "format": "<формат публикации, например: обучающий, юмор, закулисье, обзор>",
  "hook_type": "<тип зацепки в начале, например: вопрос, шок-факт, интрига, личная история>",
  "has_cta": <true или false — есть ли призыв к действию (подписаться, купить, перейти по ссылке)>,
  "sentiment": "<positive, neutral, negative или mixed — тональность комментариев>",
  "complaints": ["<жалоба 1>", "..."],
  "praises": ["<похвала 1>", "..."],
  "questions": ["<вопрос без ответа 1>", "..."],
  "notable_phrases": ["<заметная цитата 1>", "..."]
}

Правила:
- Если комментариев нет, sentiment оставь "neutral", а списки — пустыми массивами.
- Каждый список — максимум 5 коротких элементов на русском.
- Не добавляй никакого текста вне JSON.
```

**User (per item):**
```
Тип: {type_ru}
Подпись: {caption or "(без подписи)"}
Комментарии:
- {author}: {text}
...
{или "Комментарии: отсутствуют" when E17-S2 fetched none}
{cover image attached as image block when available}
```

One call per content item in the run's deep analysis. Comments come from `services/comment_scraper.py:fetch_comments` (E17-S2, capped at `deep_analysis_comments_per_post`, itself capped further to 25 in the prompt). Output is `json.loads`-parsed, not regex-parsed like the run summary — an unparseable or failed response stores a `failed` `DeepAnalysisItem` row (metrics-only degrade for that item, never fails the whole analysis).

Parameters: max_tokens=500, temperature=0.2. Reuses `summarizer.py`'s cover-image policy (≤512px, skipped when caption > `summary_skip_image_caption_chars`) and batching (Message Batches API when the item count reaches `summary_batch_threshold`, same D29 cost policy as content summaries).

## Deep analysis synthesis (E17-S4) — model: claude-sonnet-5

**System:**
```
Ты — маркетинговый аналитик социальных сетей. По списку публикаций конкурентов (метрики,
теги контента, сигналы из комментариев) составь два раздела отчёта: Статистика и Рекомендации.

Правила:
- Всё на русском языке.
- Статистика описывает то, что уже происходит: частота тем и их виральность, разбивка по
форматам/типам зацепок/наличию призыва к действию, частота публикаций, тональность комментариев
с показательными цитатами.
- Рекомендации — практические выводы: конкретные идеи для контента, что стоит делать больше/меньше,
шаблоны зацепок, пакет частых вопросов из комментариев без ответа, предложение по расписанию публикаций,
подборка «украсть эту идею» со ссылкой на content_item_id лучших постов.
- Используй только переданные данные, не выдумывай публикации или цифры.
- Ответь вызовом инструмента submit_deep_analysis_report — не отвечай обычным текстом.
```

**User:**
```
Публикации для анализа:
- id={item_id} @{handle} ({type_ru}, {date}): тема=..., формат=..., зацепка=..., cta=...,
  виральность=..., лайки=N, комментарии=N; тональность=...; жалобы: ...; похвалы: ...;
  вопросы без ответа: ...; заметные цитаты: ...
...
```

One call per deep analysis, fed every `done`-status `DeepAnalysisItem` (E17-S3) joined with its `ContentItem`'s metrics and the same self-relative virality bucket the results table uses (`services/metrics.py`). Output is **structured tool-use**, not free text — the model must call the `submit_deep_analysis_report` tool, whose JSON schema is the contract the frontend (E17-S7/S8) renders directly. An API error, a response with no `tool_use` block, or a run with zero `done` extraction items all set `status=failed` with a Russian message rather than leaving the row stuck (mirrors `generate_run_summary`'s never-raises pattern).

**E17-S9 post-processing (not a prompt change):** when fewer than `deep_analysis_comment_coverage_threshold` (default 50%) of synthesized items had any fetched comments, the comment-derived fields (`stats.sentiment_summary`, `stats.representative_quotes`, `recommendations.faq_pack`) are stripped from the response **after** it comes back, regardless of what the model actually produced — this guarantees no fabricated sentiment/quotes/FAQ on a thin-data run rather than relying on prompt instructions to keep the model honest. A `comment_coverage_degraded: true` flag is added to both `stats` and `recommendations` for the frontend to key its degraded-state note off of. The up-front token charge (E17-S1) is also reduced to `deep_analysis_thin_coverage_multiplier` (default 50%) of the original, refunding the difference — see `services/deep_analysis_synthesis.py:_apply_thin_coverage_pricing`.

Parameters: max_tokens=4096, temperature=0.3, forced `tool_choice`. The only non-Haiku call in the E17 pipeline (D33).

## Script generation (post-MVP, placeholder)

To be designed when the epic is scheduled. Known inputs: shortlisted item (summary, caption, metrics), target duration (seconds), user's niche/voice settings. Model: stronger Claude model (Sonnet/Opus tier); token usage recorded as usage_events with a distinct kind.
