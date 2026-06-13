import json
import subprocess
import sys
from .models import VideoMetadata

YTDLP = [sys.executable, "-m", "yt_dlp"]


def fetch_metadata(url: str) -> VideoMetadata:
    """Use yt-dlp to fetch video metadata without downloading the video."""
    result = subprocess.run(
        YTDLP + ["--dump-json", "--skip-download", "--no-warnings", url],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return VideoMetadata(
        video_id=data["id"],
        title=data["title"],
        channel=data.get("channel") or data.get("uploader", "Unknown"),
        channel_url=data.get("channel_url") or data.get("uploader_url"),
        duration=int(data.get("duration") or 0),
        upload_date=data.get("upload_date"),
        description=data.get("description"),
        thumbnail=data.get("thumbnail"),
        webpage_url=data.get("webpage_url", url),
    )
