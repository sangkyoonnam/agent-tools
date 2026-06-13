import os
from pathlib import Path
import json

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get(
        "NOTION_MIRROR_OUTPUT_DIR",
        Path.home() / "ObsidianVault-Datarize" / "03_Resources" / "Notion Mirror",
    )
).expanduser()
STATE_FILE = Path.home() / ".notion_mirror_state.json"
ENV_FILE = Path.home() / ".notion_env"
HERMES_ENV_FILE = Path.home() / ".hermes" / ".env"
TOKEN_KEYS = ("DATARIZE_NOTION_API_TOKEN", "NOTION_API_KEY", "NOTION_API_TOKEN")


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_token() -> str:
    """Load a Notion integration token.

    Preferred lookup order:
    1. Process env: DATARIZE_NOTION_API_TOKEN, NOTION_API_KEY, NOTION_API_TOKEN
    2. ~/.notion_env with the same keys
    3. ~/.hermes/.env with the same keys

    This keeps the old laptop notion-mirror setup working while also allowing
    Hermes-managed Notion credentials on the Mac Mini.
    """
    for key in TOKEN_KEYS:
        value = os.environ.get(key)
        if value:
            return value.strip()

    for env_file in (ENV_FILE, HERMES_ENV_FILE):
        values = _parse_env_file(env_file)
        for key in TOKEN_KEYS:
            value = values.get(key)
            if value:
                return value.strip()

    keys = ", ".join(TOKEN_KEYS)
    raise FileNotFoundError(
        f"No Notion token found. Set one of {keys} in environment, {ENV_FILE}, or {HERMES_ENV_FILE}."
    )


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
