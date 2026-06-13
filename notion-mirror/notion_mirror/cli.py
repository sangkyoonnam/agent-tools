"""CLI for notion-mirror."""

from pathlib import Path

import typer
from rich.console import Console

from .config import DEFAULT_OUTPUT_DIR, load_token
from .client import NotionMirrorClient
from .mirror import sync_single, sync_all

app = typer.Typer(
    name="notion-mirror",
    help="Notion → Obsidian mirror tool",
    no_args_is_help=True,
)
console = Console()


def _get_client() -> NotionMirrorClient:
    try:
        token = load_token()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    return NotionMirrorClient(token)


@app.command()
def sync(
    target_id: str = typer.Argument(help="Notion page or database ID to sync"),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output", "-o", help="Output directory"),
    recursive: bool = typer.Option(False, "--recursive/--no-recursive", "-r", help="Recursively sync child pages"),
    since_last: bool = typer.Option(False, "--since-last", help="Only sync items changed since last sync"),
):
    """Sync a specific page or database by ID."""
    client = _get_client()
    output_dir.mkdir(parents=True, exist_ok=True)
    sync_single(client, target_id, output_dir, recursive=recursive, since_last=since_last)


@app.command("sync-all")
def sync_all_cmd(
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output", "-o", help="Output directory"),
    since_last: bool = typer.Option(False, "--since-last", help="Only sync items changed since last sync"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without writing"),
    limit: int | None = typer.Option(None, "--limit", "-n", min=1, help="Limit pages/databases searched; useful for smoke tests"),
    pages_only: bool = typer.Option(False, "--pages-only", help="Only search/sync pages"),
    databases_only: bool = typer.Option(False, "--databases-only", help="Only search/sync databases"),
):
    """Sync entire workspace. Use --since-last for incremental sync."""
    client = _get_client()
    output_dir.mkdir(parents=True, exist_ok=True)

    if pages_only and databases_only:
        console.print("[red]Use only one of --pages-only or --databases-only.[/red]")
        raise typer.Exit(2)

    if dry_run:
        console.print("[blue]Dry run — listing items to sync[/blue]")
        from .config import load_state
        state = load_state()
        last_sync = state.get("last_sync") if since_last else None

        pages = [] if databases_only else client.search_all(filter_type="page", last_edited_after=last_sync, limit=limit)
        databases = [] if pages_only else client.search_all(filter_type="database", last_edited_after=last_sync, limit=limit)

        console.print(f"\n[bold]Pages ({len(pages)}):[/bold]")
        for p in pages:
            from .mirror import get_page_title
            console.print(f"  - {get_page_title(p)}")

        console.print(f"\n[bold]Databases ({len(databases)}):[/bold]")
        for d in databases:
            title_parts = d.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts) or "Untitled"
            console.print(f"  - {title}")

        console.print(f"\n[dim]Total: {len(pages) + len(databases)} items[/dim]")
        return

    sync_all(client, output_dir, since_last=since_last, limit=limit, pages_only=pages_only, databases_only=databases_only)


@app.command("daily-context")
def daily_context_cmd(
    mirror_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--mirror-dir", "-m", help="Notion mirror body directory"),
    since_hours: int = typer.Option(24, "--since-hours", min=1, help="Look back this many hours using file mtimes"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional markdown output path"),
    max_items: int = typer.Option(200, "--max-items", min=1, help="Maximum changed notes to include"),
):
    """Render a team/product grouped daily context report from changed mirror notes."""
    from datetime import datetime, timedelta, timezone
    from .context import collect_changed_notes, render_daily_context_markdown

    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    notes = collect_changed_notes(mirror_dir, since=since, max_items=max_items)
    markdown = render_daily_context_markdown(notes, mirror_dir=mirror_dir, since=since)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        console.print(f"[green]Wrote daily context:[/green] {output}")
    else:
        console.print(markdown)


@app.command()
def status():
    """Show last sync status."""
    from .config import load_state
    state = load_state()

    if not state:
        console.print("[yellow]No sync has been performed yet.[/yellow]")
        return

    console.print(f"[bold]Last sync:[/bold] {state.get('last_sync', 'unknown')}")
    console.print(f"[bold]Items synced:[/bold] {state.get('last_synced_count', 'unknown')}")


if __name__ == "__main__":
    app()
