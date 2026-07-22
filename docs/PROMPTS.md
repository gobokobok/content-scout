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

## Script generation (post-MVP, placeholder)

To be designed when the epic is scheduled. Known inputs: shortlisted item (summary, caption, metrics), target duration (seconds), user's niche/voice settings. Model: stronger Claude model (Sonnet/Opus tier); token usage recorded as usage_events with a distinct kind.
