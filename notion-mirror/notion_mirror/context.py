"""Daily context extraction from a local Notion mirror."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re


@dataclass
class ChangedNote:
    path: Path
    rel_path: Path
    mtime: datetime
    title: str
    top_group: str
    sub_group: str


def _frontmatter_title(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    for line in text[4:end].splitlines():
        if line.startswith("title:"):
            value = line.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                try:
                    import json
                    return json.loads(value)
                except Exception:
                    return value.strip('"')
            return value
    return None


def _clean_title_from_filename(path: Path) -> str:
    fm_title = _frontmatter_title(path)
    if fm_title:
        return fm_title
    name = path.stem
    # mirror filenames usually end with " [uuid]". Keep the human part.
    return re.sub(r"\s+\[[0-9a-fA-F-]{8,}\]$", "", name).strip() or path.stem


def _group_for(rel_path: Path) -> tuple[str, str]:
    parts = rel_path.parts
    top = parts[0] if len(parts) >= 1 else "_root"
    sub = parts[1] if len(parts) >= 2 else "_root"

    # Datarize legacy mirror has two especially important top-level axes:
    # - 프로젝트 [...]       => product/project axis
    # - 챕터팀 페이지 [...]   => team/chapter axis
    if "프로젝트" in top:
        top_label = "제품/프로젝트"
    elif "챕터" in top or "팀" in top:
        top_label = "팀/챕터"
    elif top == "temp":
        top_label = "임시/미분류"
    else:
        top_label = top
    return top_label, sub


def collect_changed_notes(
    mirror_dir: Path,
    since: datetime | None = None,
    since_hours: int = 24,
    max_items: int = 200,
) -> list[ChangedNote]:
    """Collect changed Markdown notes from mirror_dir.

    Uses filesystem mtime. This works well when `notion-mirror sync-all --since-last`
    runs before this command because only changed Notion pages are rewritten.
    """
    mirror_dir = mirror_dir.expanduser().resolve()
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)

    notes: list[ChangedNote] = []
    for path in mirror_dir.rglob("*.md"):
        try:
            st = path.stat()
        except OSError:
            continue
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        if mtime < since:
            continue
        try:
            rel = path.relative_to(mirror_dir)
        except ValueError:
            rel = path
        top, sub = _group_for(rel)
        notes.append(
            ChangedNote(
                path=path,
                rel_path=rel,
                mtime=mtime,
                title=_clean_title_from_filename(path),
                top_group=top,
                sub_group=sub,
            )
        )

    notes.sort(key=lambda n: n.mtime, reverse=True)
    return notes[:max_items]


def render_daily_context_markdown(
    notes: list[ChangedNote],
    mirror_dir: Path,
    since: datetime,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    mirror_dir = mirror_dir.expanduser().resolve()

    lines: list[str] = []
    lines.append("# Datarize Notion Daily Context")
    lines.append("")
    lines.append(f"- Generated at: {generated_at.isoformat()}")
    lines.append(f"- Since: {since.isoformat()}")
    lines.append(f"- Mirror source: `{mirror_dir}`")
    lines.append(f"- Changed markdown notes: {len(notes)}")
    lines.append("")

    if not notes:
        lines.append("변경된 Notion mirror markdown note가 없습니다.")
        lines.append("")
        return "\n".join(lines)

    by_top: dict[str, list[ChangedNote]] = defaultdict(list)
    for note in notes:
        by_top[note.top_group].append(note)

    lines.append("## 요약")
    lines.append("")
    for top, items in sorted(by_top.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"- {top}: {len(items)} changed notes")
    lines.append("")

    for top, items in sorted(by_top.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"## {top}")
        lines.append("")
        by_sub: dict[str, list[ChangedNote]] = defaultdict(list)
        for note in items:
            by_sub[note.sub_group].append(note)
        for sub, sub_items in sorted(by_sub.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            lines.append(f"### {sub} ({len(sub_items)})")
            for note in sub_items[:20]:
                local_time = note.mtime.astimezone().strftime("%Y-%m-%d %H:%M")
                lines.append(f"- {local_time} — {note.title}")
                lines.append(f"  - path: `{note.rel_path.as_posix()}`")
            if len(sub_items) > 20:
                lines.append(f"- ... and {len(sub_items) - 20} more")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
