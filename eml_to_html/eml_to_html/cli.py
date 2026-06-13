"""CLI interface for eml_to_html."""

from pathlib import Path

import typer
from rich.console import Console

from eml_to_html.converter import convert

app = typer.Typer(help="Convert EML email files to HTML.")
console = Console()


@app.command()
def main(
    src: Path = typer.Argument(..., help="EML file or directory containing EML files"),
    dst: Path = typer.Option(None, "--out", "-o", help="Output file or directory (default: same location, .html extension)"),
    headers: bool = typer.Option(False, "--headers", "-H", help="Include email headers (Subject, From, To, Date)"),
) -> None:
    """Convert EML files to HTML."""
    if src.is_file():
        _convert_one(src, dst, headers=headers)
    elif src.is_dir():
        eml_files = sorted(src.glob("*.eml"))
        if not eml_files:
            console.print(f"[yellow]No .eml files found in {src}[/yellow]")
            raise typer.Exit(1)
        out_dir = dst or src
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in eml_files:
            _convert_one(f, out_dir / f"{f.stem}.html", headers=headers)
        console.print(f"[green]Converted {len(eml_files)} files → {out_dir}[/green]")
    else:
        console.print(f"[red]Not found: {src}[/red]")
        raise typer.Exit(1)


def _convert_one(src: Path, dst: Path | None, *, headers: bool = False) -> None:
    if dst is None:
        dst = src.with_suffix(".html")
    elif dst.is_dir():
        dst = dst / f"{src.stem}.html"
    convert(src, dst, headers=headers)
    console.print(f"[green]{src.name}[/green] → [blue]{dst}[/blue]")
