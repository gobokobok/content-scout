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

## Script generation (post-MVP, placeholder)

To be designed when the epic is scheduled. Known inputs: shortlisted item (summary, caption, metrics), target duration (seconds), user's niche/voice settings. Model: stronger Claude model (Sonnet/Opus tier); token usage recorded as usage_events with a distinct kind.
