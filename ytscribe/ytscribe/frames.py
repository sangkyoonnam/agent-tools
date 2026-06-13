import subprocess
from pathlib import Path
from .models import Moment


def extract_frame(video_path: Path, t_seconds: int, out_path: Path) -> None:
    """Extract a single JPEG frame at the given timestamp using ffmpeg.

    Uses fast seek (-ss before -i) for speed; sufficient for screenshot use.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(t_seconds),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def extract_all(
    video_path: Path, moments: list[Moment], images_dir: Path
) -> dict[int, Path]:
    """Extract one frame per moment. Returns {seconds: relative_path}."""
    result: dict[int, Path] = {}
    for m in moments:
        fname = f"frame-{_hms_filename(m.t)}.jpg"
        out = images_dir / fname
        extract_frame(video_path, m.t, out)
        result[m.t] = Path("images") / fname
    return result


def _hms_filename(s: int) -> str:
    h, rem = divmod(s, 3600)
    mm, ss = divmod(rem, 60)
    return f"{h:02d}-{mm:02d}-{ss:02d}"
