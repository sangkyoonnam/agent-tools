from .models import Segment


class TranscriptUnavailable(Exception):
    pass


def fetch_transcript(video_id: str, langs: list[str]) -> list[Segment]:
    """
    Fetch a YouTube transcript via youtube-transcript-api.

    Tries languages in order; prefers manual captions over auto-generated.
    Raises TranscriptUnavailable if nothing usable found.
    """
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
    except ImportError as e:
        raise TranscriptUnavailable(f"youtube-transcript-api not installed: {e}")

    api = YouTubeTranscriptApi()

    try:
        tlist = api.list(video_id)
    except (TranscriptsDisabled, VideoUnavailable) as e:
        raise TranscriptUnavailable(f"{type(e).__name__}: {e}")
    except Exception as e:
        raise TranscriptUnavailable(f"Failed to list transcripts: {e}")

    chosen = None
    # 1. manual in preferred languages
    try:
        chosen = tlist.find_manually_created_transcript(langs)
    except NoTranscriptFound:
        pass
    # 2. auto-generated in preferred languages
    if chosen is None:
        try:
            chosen = tlist.find_generated_transcript(langs)
        except NoTranscriptFound:
            pass
    # 3. anything translatable to first lang
    if chosen is None:
        for t in tlist:
            if getattr(t, "is_translatable", False):
                try:
                    chosen = t.translate(langs[0])
                    break
                except Exception:
                    continue
    # 4. anything at all
    if chosen is None:
        try:
            chosen = next(iter(tlist))
        except StopIteration:
            raise TranscriptUnavailable(
                f"No transcripts available for video {video_id}"
            )

    try:
        fetched = chosen.fetch()
    except Exception as e:
        raise TranscriptUnavailable(f"Failed to fetch transcript: {e}")

    segments: list[Segment] = []
    for snippet in fetched:
        text = " ".join(snippet.text.strip().split())
        if not text:
            continue
        segments.append(
            Segment(
                start=float(snippet.start),
                end=float(snippet.start) + float(snippet.duration),
                text=text,
            )
        )

    if not segments:
        raise TranscriptUnavailable(f"Empty transcript for video {video_id}")

    return segments


def format_for_prompt(segments: list[Segment]) -> str:
    """Format segments as '[HH:MM:SS] text' lines for the Claude prompt."""
    return "\n".join(
        f"[{_seconds_to_hms(int(s.start))}] {s.text}" for s in segments
    )


def _seconds_to_hms(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"
