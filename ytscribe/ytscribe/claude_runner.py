import json
import shutil
import subprocess
from pathlib import Path

from .models import ClaudeAnalysis, VideoMetadata, Segment
from .prompts import ANALYSIS_PROMPT
from .transcript import format_for_prompt


class ClaudeError(Exception):
    pass


def ensure_claude_available() -> None:
    if shutil.which("claude") is None:
        raise ClaudeError(
            "`claude` CLI not found in PATH. Install Claude Code first: "
            "https://docs.claude.com/claude-code"
        )


def analyze(
    metadata: VideoMetadata,
    segments: list[Segment],
    work_dir: Path,
    timeout: int = 600,
) -> ClaudeAnalysis:
    """Run claude CLI with the analysis prompt and return parsed result."""
    ensure_claude_available()

    transcript_str = format_for_prompt(segments)
    prompt = ANALYSIS_PROMPT.format(
        title=metadata.title,
        channel=metadata.channel,
        duration_human=_human_duration(metadata.duration),
        url=metadata.webpage_url,
        transcript=transcript_str,
    )

    # Persist prompt for debugging / re-runs
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / ".prompt.txt").write_text(prompt, encoding="utf-8")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ClaudeError(f"claude CLI timed out after {timeout}s")

    if result.returncode != 0:
        (work_dir / ".claude_stderr.txt").write_text(result.stderr, encoding="utf-8")
        raise ClaudeError(
            f"claude CLI exited {result.returncode}. stderr saved to {work_dir}/.claude_stderr.txt"
        )

    raw = result.stdout
    (work_dir / ".claude_raw.txt").write_text(raw, encoding="utf-8")

    # claude --output-format json wraps the actual output in an envelope
    try:
        envelope = json.loads(raw)
        inner_text = envelope.get("result") if isinstance(envelope, dict) else None
        if not inner_text:
            inner_text = raw
    except json.JSONDecodeError:
        inner_text = raw

    payload = _extract_json_object(inner_text)
    if payload is None:
        raise ClaudeError(
            f"Could not find JSON object in claude output. Raw saved to {work_dir}/.claude_raw.txt"
        )

    try:
        analysis = ClaudeAnalysis.model_validate(payload)
    except Exception as e:
        raise ClaudeError(f"Claude output failed schema validation: {e}")

    # enforce monotonic + ≥30s spacing on moments
    analysis.moments = _dedupe_moments(analysis.moments, min_gap=30)
    return analysis


def _dedupe_moments(moments, min_gap: int = 30):
    sorted_m = sorted(moments, key=lambda m: m.t)
    out = []
    for m in sorted_m:
        if out and (m.t - out[-1].t) < min_gap:
            continue
        out.append(m)
    return out


def _extract_json_object(text: str) -> dict | None:
    """Find the first balanced top-level JSON object in text."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = text[start : i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    return None
    return None


def _human_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"
