# agent-tools

에이전트(Hermes·Codex·Claude 등)와 사람이 함께 쓰는 개인 CLI 도구 모음. 각 도구는 독립 Python 패키지(`pyproject.toml`)라 따로 `pip install -e` 할 수 있고, 나중에 개별 repo로 분할하기도 쉽다.

> private 저장소. 도구 코드에 시크릿은 없으며(토큰은 환경변수·`~/.notion_env`에서 읽음), 외부 통신은 각 도구가 호출하는 공식 API(Notion·YouTube)와 에셋 다운로드뿐이다.

## 요구사항

- Python ≥ 3.11
- 추가: `ffmpeg`(ytscribe 프레임 추출), `claude` CLI(ytscribe 요약), `~/.notion_env`(notion-mirror 토큰)

## 설치

```bash
./install.sh          # 3개 전부 editable 설치
# 또는 개별
python3 -m pip install -e ./notion-mirror
```

## 도구 카탈로그

| 도구 | CLI | 한 줄 설명 |
|---|---|---|
| [`eml_to_html`](./eml_to_html) | `eml-to-html` | EML 이메일 파일 → HTML 변환 |
| [`notion-mirror`](./notion-mirror) | `notion-mirror` | Notion 워크스페이스 → Obsidian 마크다운 미러 |
| [`ytscribe`](./ytscribe) | `ytscribe` | YouTube URL → 자막·요약·핵심 프레임이 담긴 Obsidian 노트 |

### eml_to_html
`.eml` 메일을 사람이 읽기 좋은 HTML로 변환. 의존성: `typer`, `rich`.

### notion-mirror
Notion 페이지·데이터베이스를 Obsidian 볼트로 미러링(블록→마크다운, 에셋 다운로드, 증분 동기화).
- 토큰: 환경변수, `~/.notion_env`, 또는 `~/.hermes/.env`의 `DATARIZE_NOTION_API_TOKEN` / `NOTION_API_KEY` / `NOTION_API_TOKEN`
- 출력 경로: `--output` 또는 `NOTION_MIRROR_OUTPUT_DIR`
- Mac Mini 기본 출력 경로: `~/ObsidianVault-Datarize/03_Resources/Notion Mirror`
- 주요 명령: `notion-mirror sync <id> [--recursive/--no-recursive]`, `notion-mirror sync-all [--since-last] [--dry-run] [--limit N] [--pages-only|--databases-only]`, `notion-mirror status`
- 의존성: `typer`, `notion-client`, `rich`, `httpx`

### ytscribe
YouTube URL을 받아 메타데이터·자막을 모으고, `claude` CLI로 핵심 순간(5–10개)·한국어 요약을 뽑은 뒤, `ffmpeg`로 해당 타임스탬프 프레임을 떠서 Obsidian `_inbox`에 노트 한 장으로 저장.
- 의존성: `typer`, `rich`, `yt-dlp` (+ `ffmpeg`, `claude` CLI)
- 참고: PyPI에 단독 배포할 경우 기존 `ytscribe` 서비스와 충돌을 피해 `nsb-ytscribe`로 개명할 것(모노레포 폴더명으로는 무관).

## 향후

도구가 커지거나 외부 배포가 필요해지면 해당 폴더를 독립 repo로 분리한다(각자 `pyproject.toml`을 유지하므로 비용이 작다).
