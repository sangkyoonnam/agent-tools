# ytscribe

YouTube → Obsidian note with AI-picked frames.

> **Local-only tool.** If ever published to PyPI/GitHub, rename to `nsb-ytscribe` to avoid collision with the existing `ytscribe` service.

## What it does

Given a YouTube URL, ytscribe:

1. Fetches metadata (title, channel, duration)
2. Downloads captions (auto or manual) via `yt-dlp`
3. Hands the transcript to **Claude Code** (`claude` CLI subprocess — not the API) to:
   - Pick 5–10 meaningful moments by content
   - Generate a Korean summary, themes, key quotes, and a structured note body
4. Downloads the video at ≤720p
5. Extracts a single JPEG frame at each picked timestamp via `ffmpeg`
6. Writes everything as a single markdown note + `images/` folder into your Obsidian vault inbox

Output:
```
~/ObsidianVault/_inbox/ytscribe/<video_id>/
├── <video_id>.md
├── images/
│   ├── frame-00-00-15.jpg
│   └── ...
└── .meta.json
```

## Why Claude Code, not the API

The user already pays for Claude Code Max. Using `claude -p "<prompt>" --output-format json` as a subprocess avoids API costs entirely. The trade-off: slower than direct API and constrained to one round-trip per video.

## Install

System dependencies:
- `ffmpeg` (`brew install ffmpeg`)
- `yt-dlp` (bundled as a Python dep, but the binary form also works)
- `claude` CLI (https://docs.claude.com/claude-code)

Tool:
```bash
pipx install -e ~/Workspace/tools/ytscribe
```

Optional whisper fallback (for videos without captions):
```bash
pipx install -e '~/Workspace/tools/ytscribe[whisper]'
```

## Usage

```bash
ytscribe https://www.youtube.com/watch?v=SZStlIhyTCY

ytscribe https://www.youtube.com/watch?v=... --vault ~/ObsidianVault --lang ko
ytscribe https://... --force                # overwrite existing
ytscribe https://... --keep-workdir         # debug: keep temp dir
ytscribe https://... --workdir ./debug      # use a fixed workdir
```

## Pipeline stages

| # | Stage          | Tool                   |
|---|----------------|------------------------|
| 1 | Metadata       | `yt-dlp --dump-json`   |
| 2 | Transcript     | `yt-dlp --write-subs`  |
| 3 | Analysis       | `claude -p ... --output-format json` |
| 4 | Video download | `yt-dlp -f ≤720p`      |
| 5 | Frame extract  | `ffmpeg -ss <t> -frames:v 1` |
| 6 | Note write     | Jinja2 → vault         |

## Project layout

```
ytscribe/
├── pyproject.toml
├── README.md
└── ytscribe/
    ├── cli.py            # typer entry, pipeline orchestration
    ├── metadata.py       # yt-dlp metadata fetch
    ├── transcript.py     # caption fetch + VTT parse
    ├── video.py          # yt-dlp video download
    ├── frames.py         # ffmpeg frame extraction
    ├── claude_runner.py  # claude CLI subprocess + JSON parsing
    ├── prompts.py        # prompt template
    ├── template.py       # jinja2 markdown rendering
    ├── vault.py          # write to Obsidian inbox
    ├── models.py         # pydantic data models
    └── templates/note.md.j2
```

## Limitations / TODO

- Whisper fallback not yet implemented (transcript-less videos fail)
- Single Claude round-trip — long videos may overflow context
- No scene-detection layer (Claude picks moments purely from transcript)
- Korean output hardcoded (configurable language is TODO)
