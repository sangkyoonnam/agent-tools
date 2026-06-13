# notion-mirror

Notion workspace를 Obsidian Markdown tree로 mirror하는 CLI입니다.

## Runtime

- Python >= 3.11
- Installed on Mac Mini via dedicated venv:
  `/Users/sangkyoonnam/Workspace/namsang/.venvs/agent-tools`
- CLI shim:
  `/Users/sangkyoonnam/.local/bin/notion-mirror`

## Token lookup

`notion-mirror`는 아래 순서로 Notion integration token을 찾습니다.

1. Process env
2. `~/.notion_env`
3. `~/.hermes/.env`

지원하는 key 이름:

```text
DATARIZE_NOTION_API_TOKEN
NOTION_API_KEY
NOTION_API_TOKEN
```

Mac Mini Hermes에서는 현재 `~/.hermes/.env`의 `NOTION_API_KEY`를 사용합니다.

## Datarize Obsidian integration

Datarize 전용 vault:

```text
~/ObsidianVault-Datarize/
```

Notion mirror 영역:

```text
~/ObsidianVault-Datarize/03_Resources/Notion Mirror/
```

현재 Syncthing-safe mirror는 기존 raw Notion mirror의 핵심 상위 page 2개를 기준으로 재구성합니다.

```text
03_Resources/Notion Mirror/
  챕터팀 페이지 [7a04625b-b11e-4828-9a2b-ce2f1a774d9f]/
    pages/<notion_id>.md
    assets/<page_id>/<asset_hash>.<ext>
    index.md
  프로젝트 [68eea3d4-4cca-4e6d-b297-2bc9c758f27d]/
    pages/<notion_id>.md
    assets/<page_id>/<asset_hash>.<ext>
    index.md
  90_Metadata/
```

원본 raw mirror archive:

```text
~/Workspace/namsang/local-archives/datarize-notion-legacy-20260613T081244Z/notion
```

중요:

- Google Workspace/ZIP을 거친 raw mirror는 Unicode normalization/path length 문제로 Syncthing conflict가 날 수 있습니다.
- raw nested mirror를 그대로 vault에 넣지 말고, 상위 page 2개를 유지한 sync-safe layout으로 변환해서 사용합니다.
- 각 generated note의 frontmatter에는 원래 제목, notion id, original_rel_path가 보존됩니다.

## Commands

```bash
notion-mirror --help
notion-mirror sync-all --dry-run --limit 5 --pages-only
notion-mirror sync-all --dry-run --limit 5
notion-mirror sync-all --since-last
notion-mirror daily-context --since-hours 24
notion-mirror sync <notion_page_or_database_id> --no-recursive
notion-mirror sync <notion_page_or_database_id> --recursive
notion-mirror status
```

## Install

From the monorepo root:

```bash
python3.11 -m venv ~/Workspace/namsang/.venvs/agent-tools
~/Workspace/namsang/.venvs/agent-tools/bin/python -m pip install -e ./notion-mirror
```

Create shim:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/notion-mirror <<'EOF'
#!/usr/bin/env bash
exec "$HOME/Workspace/namsang/.venvs/agent-tools/bin/python" -m notion_mirror.cli "$@"
EOF
chmod +x ~/.local/bin/notion-mirror
```
