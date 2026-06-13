"""Core mirroring logic."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .assets import start_downloader
from .client import NotionMirrorClient
from .config import load_state, save_state
from .converter import block_to_md, database_to_md
from .log import SyncLog

console = Console()


def clean_id(notion_id: str) -> str:
    return notion_id


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name or "Untitled"


def make_name(title: str, notion_id: str) -> str:
    """Create 'title [id]' for files and directories."""
    return f"{sanitize_filename(title)} [{clean_id(notion_id)}]"


def get_page_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


def build_frontmatter(page: dict, sync_status: str = "complete") -> str:
    created = page.get("created_time", "")
    edited = page.get("last_edited_time", "")
    notion_id = page.get("id", "")
    url = page.get("url", "")

    lines = [
        "---",
        f"notion_id: {notion_id}",
        f"notion_url: {url}",
        f"created: {created}",
        f"last_edited: {edited}",
        f"sync_status: {sync_status}",
        "source: notion-datarize",
        "---",
    ]
    return "\n".join(lines)


def _split_frontmatter(content: str) -> tuple[list[str], str]:
    """Return frontmatter lines and body for a Markdown document.

    If the document has no YAML frontmatter, start with an empty frontmatter
    and keep the full content as body.
    """
    if not content.startswith("---\n"):
        return [], content
    end = content.find("\n---", 4)
    if end == -1:
        return [], content
    fm = content[4:end].splitlines()
    body = content[end + len("\n---") :]
    if body.startswith("\n"):
        body = body[1:]
    return fm, body


def _set_frontmatter_field(lines: list[str], key: str, value: str) -> list[str]:
    replacement = f"{key}: {value}"
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[idx] = replacement
            return lines
    lines.append(replacement)
    return lines


def set_frontmatter_status(filepath: Path, status: str) -> None:
    """Set sync_status in a Markdown file without deleting its body."""
    content = filepath.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(content)
    fm = _set_frontmatter_field(fm, "sync_status", status)
    filepath.write_text("---\n" + "\n".join(fm) + "\n---\n\n" + body, encoding="utf-8")


def mark_markdown_deleted(filepath: Path, reason: str = "notion_deleted") -> None:
    """Mark a mirrored Markdown file as deleted instead of removing it."""
    content = filepath.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(content)
    fm = _set_frontmatter_field(fm, "sync_status", "deleted")
    fm = _set_frontmatter_field(fm, "delete_reason", reason)
    fm = _set_frontmatter_field(fm, "deleted_at", datetime.now(timezone.utc).isoformat())
    filepath.write_text("---\n" + "\n".join(fm) + "\n---\n\n" + body, encoding="utf-8")


def _frontmatter_value(filepath: Path, key: str) -> str | None:
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return None
    fm, _body = _split_frontmatter(content)
    for line in fm:
        if line.startswith(f"{key}:"):
            value = line.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
                return value[1:-1]
            return value
    return None


def _is_not_found_error(exc: Exception) -> bool:
    text = repr(exc).lower()
    return "object_not_found" in text or "not_found" in text or "404" in text


def mark_deleted_remote_pages(client: NotionMirrorClient, mirror_dir: Path) -> list[Path]:
    """Mark local mirror notes as deleted when Notion says they are gone.

    This never removes local Markdown files. It scans existing `.md` files for a
    `notion_id` frontmatter field, retrieves the remote page, and marks the
    local note `sync_status: deleted` when the page is archived, in_trash, or no
    longer accessible by ID.
    """
    marked: list[Path] = []
    for path in mirror_dir.rglob("*.md"):
        if _frontmatter_value(path, "sync_status") == "deleted":
            continue
        notion_id = _frontmatter_value(path, "notion_id")
        if not notion_id:
            continue
        try:
            page = client.get_page(notion_id)
        except Exception as exc:
            if _is_not_found_error(exc):
                mark_markdown_deleted(path, reason="notion_not_found")
                marked.append(path)
            continue
        if page.get("archived") or page.get("in_trash"):
            mark_markdown_deleted(path, reason="notion_archived")
            marked.append(path)
    return marked


def _finalize_frontmatter(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    filepath.write_text(
        content.replace("sync_status: in_progress", "sync_status: complete"),
        encoding="utf-8",
    )


def _needs_resync(output_dir: Path, title: str, notion_id: str) -> bool:
    """Check if existing file has sync_status: in_progress (incomplete previous sync)."""
    name = make_name(title, notion_id)
    filepath = output_dir / name / f"{name}.md"
    if not filepath.exists():
        return False
    try:
        # Only read first 500 bytes for frontmatter check
        head = filepath.read_text(encoding="utf-8")[:500]
        return "sync_status: in_progress" in head
    except Exception:
        return False


def mirror_page(
    client: NotionMirrorClient,
    page: dict,
    output_dir: Path,
    log: SyncLog | None = None,
) -> Path:
    title = get_page_title(page)
    name = make_name(title, page["id"])
    page_dir = output_dir / name
    page_dir.mkdir(parents=True, exist_ok=True)
    filepath = page_dir / f"{name}.md"

    frontmatter = build_frontmatter(page, sync_status="in_progress")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + "\n\n" + f"# {title}\n\n")
        _stream_blocks(client, page["id"], f, page_dir)

    _finalize_frontmatter(filepath)
    if log:
        log.log("page", title)
    return filepath


def _stream_blocks(
    client: NotionMirrorClient,
    block_id: str,
    f,
    page_dir: Path,
    indent: int = 0,
):
    blocks = client.get_blocks(block_id)

    for block in blocks:
        btype = block.get("type", "")
        line = block_to_md(block, indent=indent, children_map={}, page_dir=page_dir)
        f.write(line + "\n")
        f.flush()

        if block.get("has_children") and btype not in ("child_page", "child_database"):
            if btype == "table":
                _stream_table(client, block, f, indent)
            else:
                _stream_blocks(client, block["id"], f, page_dir, indent + 1)


def _stream_table(client: NotionMirrorClient, table_block: dict, f, indent: int):
    from .converter import _table_to_md
    rows = client.get_blocks(table_block["id"])
    prefix = "  " * indent
    table_md = _table_to_md(rows, prefix)
    f.write(table_md + "\n")
    f.flush()


def mirror_database(
    client: NotionMirrorClient,
    db: dict,
    output_dir: Path,
    log: SyncLog | None = None,
) -> Path:
    title_parts = db.get("title", [])
    title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled Database"
    name = make_name(title, db["id"])
    db_dir = output_dir / name
    db_dir.mkdir(parents=True, exist_ok=True)
    filepath = db_dir / f"{name}.md"

    items = client.query_database(db["id"])
    # In API 2025-09-03, properties are on data_source, not database
    data_sources = db.get("data_sources", [])
    properties_schema = {}
    if data_sources:
        try:
            ds = client.client.data_sources.retrieve(data_sources[0]["id"])
            properties_schema = ds.get("properties", {})
        except Exception:
            pass

    frontmatter_lines = [
        "---",
        f"notion_id: {db['id']}",
        f"notion_url: {db.get('url', '')}",
        f"type: database",
        f"last_edited: {db.get('last_edited_time', '')}",
        "source: notion-datarize",
        "---",
    ]
    frontmatter = "\n".join(frontmatter_lines)
    table_md = database_to_md(title, properties_schema, items)

    content = frontmatter + "\n\n" + table_md + "\n"
    filepath.write_text(content, encoding="utf-8")

    if log:
        log.log("database", title)

    for item in items:
        item_title = get_page_title(item)
        if item_title and item_title != "Untitled":
            try:
                blocks, children_map = client.get_blocks_recursive(item["id"])
                if blocks:
                    mirror_page(client, item, db_dir, log=log)
            except Exception:
                pass

    return filepath


def sync_single(
    client: NotionMirrorClient,
    target_id: str,
    output_dir: Path,
    recursive: bool = False,
    since_last: bool = False,
):
    target_id = target_id.replace("-", "")
    state = load_state()
    last_sync = state.get("last_sync") if since_last else None
    log = SyncLog()
    downloader = start_downloader()

    if since_last and last_sync:
        console.print(f"[blue]Incremental sync since {last_sync}[/blue]")
    else:
        console.print(f"[blue]Syncing {target_id}...[/blue]")

    # Try as page first
    try:
        page = client.get_page(target_id)
        if page.get("object") == "page":
            title = get_page_title(page)
            edited = page.get("last_edited_time", "")
            resync = _needs_resync(output_dir, title, page["id"])
            if last_sync and edited < last_sync and not resync:
                console.print(f"[dim]Skipped (not modified): {title}[/dim]")
                log.log("page", title, status="skipped")
            else:
                path = mirror_page(client, page, output_dir, log=log)
                console.print(f"[green]Page saved: {path}[/green]")
            if recursive:
                title = get_page_title(page)
                page_dir = output_dir / make_name(title, page["id"])
                _sync_children_recursive(client, target_id, page_dir, last_sync, log=log)

            _stop_downloader(downloader, log)
            _finish(state, log)
            return
    except Exception:
        pass

    # Try as database
    try:
        db = client.get_database(target_id)
        if db.get("object") == "database":
            edited = db.get("last_edited_time", "")
            if last_sync and edited < last_sync:
                console.print(f"[dim]Skipped (not modified): DB[/dim]")
                log.log("database", "DB", status="skipped")
            else:
                path = mirror_database(client, db, output_dir, log=log)
                console.print(f"[green]Database saved: {path}[/green]")

            _stop_downloader(downloader, log)
            _finish(state, log)
            return
    except Exception:
        pass

    console.print(f"[red]Could not find page or database: {target_id}[/red]")
    log.log("sync", target_id, status="error", detail="not found")
    _stop_downloader(downloader, log)
    _finish(state, log)


def _stop_downloader(downloader, log: SyncLog):
    console.print(f"\n[blue]Waiting for asset downloads to finish...[/blue]")
    downloader.stop_and_wait()
    log.log("assets", f"{downloader.success} downloaded, {downloader.errors} failed")
    if downloader.errors:
        console.print(f"[yellow]{downloader.errors} asset downloads failed.[/yellow]")
    else:
        console.print(f"[green]{downloader.success} assets downloaded.[/green]")


def _finish(state: dict, log: SyncLog):
    now = datetime.now(timezone.utc).isoformat()
    state["last_sync"] = now
    save_state(state)

    summary = log.summary()
    console.print(f"\n[green]Done![/green] {summary['ok']} synced, {summary['skipped']} skipped, {summary['errors']} errors in {summary['elapsed_seconds']}s")
    console.print(f"[dim]Log: {summary['log_file']}[/dim]")


def _sync_children_recursive(
    client: NotionMirrorClient,
    block_id: str,
    output_dir: Path,
    last_sync: str | None = None,
    log: SyncLog | None = None,
):
    blocks = client.get_blocks(block_id)

    for block in blocks:
        block_type = block.get("type", "")

        if block_type == "child_page":
            child_id = block["id"]
            title = block.get("child_page", {}).get("title", "Untitled")
            try:
                child_page = client.get_page(child_id)
                edited = child_page.get("last_edited_time", "")
                resync = _needs_resync(output_dir, title, child_id)
                if last_sync and edited < last_sync and not resync:
                    console.print(f"[dim]  Skipped: {title}[/dim]")
                    if log:
                        log.log("page", title, status="skipped")
                else:
                    if resync:
                        console.print(f"[dim]  → page (retry): {title}[/dim]")
                    else:
                        console.print(f"[dim]  → page: {title}[/dim]")
                    mirror_page(client, child_page, output_dir, log=log)
                child_dir = output_dir / make_name(title, child_id)
                _sync_children_recursive(client, child_id, child_dir, last_sync, log=log)
            except Exception as e:
                console.print(f"[red]  Error syncing child '{title}': {e}[/red]")
                if log:
                    log.log("page", title, status="error", detail=str(e))

        elif block_type == "child_database":
            child_id = block["id"]
            title = block.get("child_database", {}).get("title", "Untitled DB")
            try:
                db = client.get_database(child_id)
                edited = db.get("last_edited_time", "")
                if last_sync and edited < last_sync:
                    console.print(f"[dim]  Skipped: {title}[/dim]")
                    if log:
                        log.log("database", title, status="skipped")
                else:
                    console.print(f"[dim]  → database: {title}[/dim]")
                    mirror_database(client, db, output_dir, log=log)
            except Exception as e:
                console.print(f"[red]  Error syncing child DB '{title}': {e}[/red]")
                if log:
                    log.log("database", title, status="error", detail=str(e))

        elif block.get("has_children"):
            _sync_children_recursive(client, block["id"], output_dir, last_sync, log=log)


def sync_all(
    client: NotionMirrorClient,
    output_dir: Path,
    since_last: bool = False,
    limit: int | None = None,
    pages_only: bool = False,
    databases_only: bool = False,
):
    state = load_state()
    last_sync = state.get("last_sync") if since_last else None
    log = SyncLog()
    downloader = start_downloader()

    if since_last and last_sync:
        console.print(f"[blue]Incremental sync since {last_sync}[/blue]")
    else:
        console.print("[blue]Full workspace sync[/blue]")

    pages = []
    databases = []

    if not databases_only:
        console.print("[dim]Searching pages...[/dim]")
        pages = client.search_all(filter_type="page", last_edited_after=last_sync, limit=limit)
        console.print(f"[dim]Found {len(pages)} pages[/dim]")

    if not pages_only:
        console.print("[dim]Searching databases...[/dim]")
        databases = client.search_all(filter_type="database", last_edited_after=last_sync, limit=limit)
        console.print(f"[dim]Found {len(databases)} databases[/dim]")

    total = len(pages) + len(databases)
    if total == 0:
        console.print("[yellow]No items to sync.[/yellow]")
        return

    page_names: dict[str, str] = {}
    for p in pages:
        page_names[p["id"]] = make_name(get_page_title(p), p["id"])
    for d in databases:
        title_parts = d.get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled Database"
        page_names[d["id"]] = make_name(title, d["id"])

    def resolve_output_dir(item: dict) -> Path:
        parent = item.get("parent", {})
        parent_type = parent.get("type", "")
        if parent_type == "page_id":
            parent_id = parent["page_id"]
            parent_name = page_names.get(parent_id, "")
            if parent_name:
                return output_dir / parent_name
        elif parent_type == "database_id":
            parent_id = parent["database_id"]
            parent_name = page_names.get(parent_id, "")
            if parent_name:
                return output_dir / parent_name
        return output_dir

    # Phase 1: sync pages and databases
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Syncing pages...", total=total)

        for db in databases:
            title_parts = db.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled DB"
            progress.update(task, description=f"DB: {title}")
            try:
                target_dir = resolve_output_dir(db)
                mirror_database(client, db, target_dir, log=log)
            except Exception as e:
                console.print(f"[red]Error syncing DB '{title}': {e}[/red]")
                log.log("database", title, status="error", detail=str(e))
            progress.advance(task)

        for page in pages:
            title = get_page_title(page)
            progress.update(task, description=f"Page: {title}")
            try:
                target_dir = resolve_output_dir(page)
                mirror_page(client, page, target_dir, log=log)
            except Exception as e:
                console.print(f"[red]Error syncing '{title}': {e}[/red]")
                log.log("page", title, status="error", detail=str(e))
            progress.advance(task)

    # Wait for asset downloads to finish
    _stop_downloader(downloader, log)

    now = datetime.now(timezone.utc).isoformat()
    state["last_sync"] = now
    state["last_synced_count"] = log.summary()["ok"]
    save_state(state)

    summary = log.summary()
    console.print(f"\n[green]Done![/green] {summary['ok']} synced, {summary['skipped']} skipped, {summary['errors']} errors in {summary['elapsed_seconds']}s")
    console.print(f"[dim]Log: {summary['log_file']}[/dim]")
