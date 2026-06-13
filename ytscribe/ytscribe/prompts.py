ANALYSIS_PROMPT = """You are analyzing a YouTube video transcript to produce an Obsidian knowledge note.

VIDEO METADATA:
- Title: {title}
- Channel: {channel}
- Duration: {duration_human}
- URL: {url}

TRANSCRIPT (timestamped):
{transcript}

YOUR TASK:
Return ONLY a single JSON object matching this exact schema. No prose before or after.

{{
  "title": "Concise Korean title for the note (may differ from video title for clarity)",
  "summary": "3-5 sentence Korean summary of the video's core argument",
  "themes": ["lowercase-kebab-tag-1", "lowercase-kebab-tag-2"],
  "moments": [
    {{
      "t": 47,
      "reason": "Why this moment matters (Korean, 1 sentence)",
      "caption": "Short Korean caption shown under the screenshot"
    }}
  ],
  "key_quotes": [
    {{ "t": 312, "text": "Verbatim quote from the transcript (in original language)" }}
  ],
  "note_body_md": "Reflective Korean markdown. ONLY contain a brief '### 분석' (3-5 sentences of your own interpretation, what's surprising or non-obvious) followed by '### 생각해볼 점' with 3-5 bullet questions for further thinking. Do NOT repeat the summary, moments, or quotes — they are already rendered above by the template. Use H3 (###) headings only. Use [[wikilinks]] for sub-concepts. Keep total under 1500 Korean characters."
}}

CONSTRAINTS:
- moments: pick 5 to 10. Must be in transcript timestamp range. Spaced at least 30 seconds apart. Choose moments where the *content* shifts or peaks (a new claim, a key example, a turning point) — not arbitrary intervals.
- themes: 3 to 6 lowercase-kebab tags suitable for Obsidian.
- key_quotes: 2 to 5 verbatim quotes (do not paraphrase).
- note_body_md: structured Korean note. Sections like ## 핵심 요약, ## 주요 순간, ## 핵심 인용, ## 생각해볼 점. Each "주요 순간" entry should have the timestamp link `[HH:MM:SS]({url}&t=Ns)`, the Korean reason, and the frame placeholder.
- All Korean. Quotes stay in original language.
- Output: ONLY the JSON object. No markdown fences. No commentary.
"""
