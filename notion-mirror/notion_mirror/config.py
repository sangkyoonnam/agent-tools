import os
from pathlib import Path
import json

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("NOTION_MIRROR_OUTPUT_DIR", Path.home() / "datarize-vault" / "notion")
).expanduser()
STATE_FILE = Path.home() / ".notion_mirror_state.json"
ENV_FILE = Path.home() / ".notion_env"


def load_token() -> str:
    env_file = ENV_FILE
    if not env_file.exists():
        raise FileNotFoundError(f"{env_file} not found. Create it with: echo 'DATARIZE_NOTION_API_TOKEN=your_token' > {env_file}")

    for line in env_file.read_text().strip().splitlines():
        if line.startswith("DATARIZE_NOTION_API_TOKEN="):
            return line.split("=", 1)[1].strip()

    raise ValueError("DATARIZE_NOTION_API_TOKEN not found in ~/.notion_env")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
