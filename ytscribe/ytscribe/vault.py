import json
import shutil
from pathlib import Path

from .models import ClaudeAnalysis, VideoMetadata


DEFAULT_VAULT = Path.home() / "ObsidianVault"
INBOX_SUBDIR = "_inbox/ytscribe"


def video_dir(vault: Path, video_id: str) -> Path:
    return vault / INBOX_SUBDIR / video_id


def init_video_dir(vault: Path, video_id: str, force: bool = False) -> Path:
    """Create the per-video folder. Errors if it already exists unless force."""
    target = video_dir(vault, video_id)
    if target.exists() and not force:
        raise FileExistsError(
            f"{target} already exists. Use --force to overwrite."
        )
    if target.exists() and force:
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_transcript(target: Path, video_id: str, transcript_md: str) -> Path:
    """Write the raw transcript file. Returns its path."""
    path = target / f"{video_id}.transcript.md"
    path.write_text(transcript_md, encoding="utf-8")
    return path


def write_note(
    target: Path,
    video_id: str,
    note_md: str,
    images_src_dir: Path,
    metadata: VideoMetadata,
    analysis: ClaudeAnalysis,
) -> Path:
    """Write the curated note + images + meta into the existing target dir."""
    images_dst = target / "images"
    if images_src_dir.exists():
        if images_dst.exists():
            shutil.rmtree(images_dst)
        shutil.copytree(images_src_dir, images_dst)
    else:
        images_dst.mkdir(exist_ok=True)

    note_path = target / f"{video_id}.md"
    note_path.write_text(note_md, encoding="utf-8")

    meta_path = target / ".meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "metadata": metadata.model_dump(),
                "analysis": analysis.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return note_path
