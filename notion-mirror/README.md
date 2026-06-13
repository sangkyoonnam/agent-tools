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

## Output directory

기본 출력 위치:

```text
~/ObsidianVault-Datarize/03_Resources/Notion Mirror
```

명시적으로 덮어쓰려면:

```bash
export NOTION_MIRROR_OUTPUT_DIR="$HOME/ObsidianVault-Datarize/03_Resources/Notion Mirror"
```

또는 실행 시:

```bash
notion-mirror sync-all --output "$HOME/ObsidianVault-Datarize/03_Resources/Notion Mirror"
```

## Datarize Obsidian integration

Datarize 전용 vault 구조:

```text
~/ObsidianVault-Datarize/
  03_Resources/
    Notion Mirror/
      00_Inbox/
      01_Pages/
      02_Databases/
      03_Attachments/
      90_Metadata/
```

`Notion Mirror` 아래 파일은 자동/반자동 mirror 결과로 취급합니다. 사람이 정리한 운영 지식으로 승격할 내용만 vault의 일반 PARA 영역으로 복사/정리합니다.

## Commands

```bash
notion-mirror --help
notion-mirror sync-all --dry-run --limit 5 --pages-only
notion-mirror sync-all --dry-run --limit 5
notion-mirror sync-all --since-last
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
