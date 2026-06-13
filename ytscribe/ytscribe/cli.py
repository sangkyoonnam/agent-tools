import shutil
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import claude_runner, frames, metadata as metadata_mod, template, transcript, vault, video
from .vault import DEFAULT_VAULT, video_dir

app = typer.Typer(
    add_completion=False,
    help="YouTube → Obsidian note with AI-picked frames.",
)
console = Console()


@app.command()
def main(
    url: str = typer.Argument(..., help="YouTube video URL"),
    vault_path: Path = typer.Option(
        DEFAULT_VAULT, "--vault", help="Obsidian vault root"
    ),
    lang: str = typer.Option(
        "ko", "--lang", help="Preferred caption language (fallback to en)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing note for this video_id"
    ),
    keep_workdir: bool = typer.Option(
        False, "--keep-workdir", help="Do not delete temporary work directory"
    ),
    workdir: Optional[Path] = typer.Option(
        None, "--workdir", help="Use this work directory instead of a temp one"
    ),
):
    """Process a YouTube video and write an Obsidian note."""
    # 1. metadata
    console.print("[bold cyan]1/7[/] Fetching metadata...")
    meta = metadata_mod.fetch_metadata(url)
    console.print(f"   [dim]{meta.title} · {meta.channel}[/]")

    # init vault target dir up front (errors if exists & not force)
    try:
        target_dir = vault.init_video_dir(vault_path, meta.video_id, force=force)
    except FileExistsError as e:
        console.print(f"[yellow]![/] {e}")
        raise typer.Exit(1)

    # set up work dir
    if workdir is None:
        work_root = Path(tempfile.mkdtemp(prefix=f"ytscribe-{meta.video_id}-"))
    else:
        work_root = workdir
        work_root.mkdir(parents=True, exist_ok=True)
    console.print(f"   [dim]workdir: {work_root}[/]")

    try:
        # 2. transcript
        console.print("[bold cyan]2/7[/] Fetching transcript...")
        langs = [lang, "en"] if lang != "en" else ["en"]
        try:
            segments = transcript.fetch_transcript(meta.video_id, langs)
        except transcript.TranscriptUnavailable as e:
            console.print(f"[red]✗[/] {e}")
            console.print(
                "[yellow]Hint:[/] whisper fallback not yet implemented. "
                "Skipping this video."
            )
            raise typer.Exit(2)
        console.print(f"   [dim]{len(segments)} segments[/]")

        # 3. write transcript file FIRST (source-of-truth, survives later failures)
        console.print("[bold cyan]3/7[/] Saving transcript to vault...")
        transcript_md = template.render_transcript(meta, segments)
        transcript_path = vault.write_transcript(
            target_dir, meta.video_id, transcript_md
        )
        console.print(f"   [dim]{transcript_path}[/]")

        # 4. claude analysis
        console.print("[bold cyan]4/7[/] Analyzing with Claude Code...")
        analysis = claude_runner.analyze(meta, segments, work_root)
        console.print(
            f"   [dim]{len(analysis.moments)} moments · {len(analysis.themes)} themes[/]"
        )

        # 5. download video
        console.print("[bold cyan]5/7[/] Downloading video (≤720p)...")
        video_path = video.download_video(url, work_root / "video")

        # 6. extract frames
        console.print("[bold cyan]6/7[/] Extracting frames...")
        images_dir = work_root / "images"
        frames.extract_all(video_path, analysis.moments, images_dir)

        # 7. render and write curated note
        console.print("[bold cyan]7/7[/] Writing curated note to vault...")
        note_md = template.render_note(meta, analysis, segments)
        note_path = vault.write_note(
            target_dir,
            meta.video_id,
            note_md,
            images_dir,
            meta,
            analysis,
        )
        console.print(f"[bold green]✓[/] {note_path}")

    finally:
        if not keep_workdir and workdir is None:
            shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    app()
