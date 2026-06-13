import subprocess
import sys
from pathlib import Path

YTDLP = [sys.executable, "-m", "yt_dlp"]


def download_video(url: str, work_dir: Path, max_height: int = 720) -> Path:
    """Download video at <= max_height resolution. Returns local file path."""
    work_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(work_dir / "video.%(ext)s")
    cmd = YTDLP + [
        "-f",
        f"bv*[height<={max_height}]+ba/b[height<={max_height}]",
        "--merge-output-format",
        "mp4",
        "-o",
        out_template,
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    candidates = list(work_dir.glob("video.*"))
    if not candidates:
        raise RuntimeError(f"yt-dlp did not produce a video file in {work_dir}")
    return candidates[0]
