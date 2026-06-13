#!/usr/bin/env bash
# Install all agent-tools as editable packages. Requires Python >= 3.11.
set -euo pipefail
cd "$(dirname "$0")"

TOOLS=(eml_to_html notion-mirror ytscribe)

for tool in "${TOOLS[@]}"; do
  echo "==> Installing $tool"
  python3 -m pip install -e "./$tool"
done

# notion-mirror uses httpx at runtime but doesn't declare it; notion-client
# pulls it transitively. Install explicitly to be safe.
python3 -m pip install "httpx>=0.27.0"

echo
echo "Done. Installed CLIs: eml-to-html, notion-mirror, ytscribe"
echo "External requirements: ytscribe needs ffmpeg + the 'claude' CLI; notion-mirror needs ~/.notion_env (DATARIZE_NOTION_API_TOKEN)."
