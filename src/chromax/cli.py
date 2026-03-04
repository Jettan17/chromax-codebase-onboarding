"""Chromax CLI - codebase onboarding agent."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="chromax",
    help="Index a GitHub repo and ask questions about its codebase.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _main() -> None:
    """Chromax - codebase onboarding agent."""


@app.command("index")
def index(
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo in 'owner/name' format."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logs."),
) -> None:
    """Index a GitHub repository into the local vector store."""
    from chromax.indexer.indexer import Indexer

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    console.print(f"[bold cyan]Chromax[/bold cyan] - indexing [green]{repo}[/green]...")

    with Progress(SpinnerColumn("line"), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Fetching and chunking files...", total=None)
        indexer = Indexer(repo)
        stats = indexer.index()
        progress.update(task, description="Done!", completed=True)

    console.print(f"\n[bold green]Indexed[/bold green] [green]{repo}[/green]")
    console.print(f"  Files processed : {stats['files_fetched']}")
    console.print(f"  Files skipped   : {stats['files_skipped']}")
    console.print(f"  Chunks added    : {stats['chunks_added']}")
    console.print(f"  Chunks skipped  : {stats['chunks_skipped']} (already indexed)")
    console.print(f"  Total in store  : {stats['chunks_added'] + stats['chunks_skipped']}")


@app.command("status")
def status(
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo in 'owner/name' format."),
) -> None:
    """Show index stats for a repository."""
    from chromax.indexer.indexer import Indexer

    indexer = Indexer(repo)
    count = indexer.chunk_count()
    if count == 0:
        console.print(f"[yellow]{repo}[/yellow] is not indexed yet. Run [bold]chromax index --repo {repo}[/bold].")
    else:
        console.print(f"[green]{repo}[/green] - [bold]{count}[/bold] chunks in vector store.")


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Natural language question about the codebase."),
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo in 'owner/name' format."),
) -> None:
    """Ask a question about a GitHub repository."""
    from chromax.agents.basic import ask as agent_ask

    console.print(f"[bold cyan]Chromax[/bold cyan] - asking about [green]{repo}[/green]...")
    answer = agent_ask(question, repo)
    console.print()
    console.print(Markdown(answer))
