from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import ClaudeAnalysis, VideoMetadata, Segment


def _seconds_to_hms(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _seconds_to_filename(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{sec:02d}"


def _human_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def _format_published(upload_date: str | None) -> str | None:
    if not upload_date or len(upload_date) != 8:
        return None
    return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"


def render_transcript(metadata: VideoMetadata, segments: list[Segment]) -> str:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=("md", "j2")),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    template = env.get_template("transcript.md.j2")
    transcript_lines = [
        f"[{_seconds_to_hms(int(s.start))}] {s.text}" for s in segments
    ]
    return template.render(
        title=metadata.title,
        source_url=metadata.webpage_url,
        channel=metadata.channel,
        duration_human=_human_duration(metadata.duration),
        published=_format_published(metadata.upload_date),
        captured=date.today().isoformat(),
        note_basename=metadata.video_id,
        transcript_lines=transcript_lines,
    )


def render_note(
    metadata: VideoMetadata,
    analysis: ClaudeAnalysis,
    segments: list[Segment],
) -> str:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=("md", "j2")),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    template = env.get_template("note.md.j2")

    moments = [
        {
            "t": m.t,
            "t_hms": _seconds_to_hms(m.t),
            "t_filename": _seconds_to_filename(m.t),
            "reason": m.reason,
            "caption": m.caption,
        }
        for m in analysis.moments
    ]
    quotes = [
        {"t": q.t, "t_hms": _seconds_to_hms(q.t), "text": q.text}
        for q in analysis.key_quotes
    ]

    return template.render(
        title=analysis.title or metadata.title,
        source_url=metadata.webpage_url,
        channel=metadata.channel,
        channel_url=metadata.channel_url,
        duration_human=_human_duration(metadata.duration),
        published=_format_published(metadata.upload_date),
        captured=date.today().isoformat(),
        themes=analysis.themes,
        summary=analysis.summary,
        moments=moments,
        key_quotes=quotes,
        note_body_md=analysis.note_body_md,
        transcript_basename=f"{metadata.video_id}.transcript",
    )
