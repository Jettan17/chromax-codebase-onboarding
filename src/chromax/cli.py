"""Chromax CLI — codebase onboarding agent."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(
    name="chromax",
    help="Index a GitHub repo and ask questions about its codebase.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _main() -> None:
    """Chromax — codebase onboarding agent."""


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Natural language question about the codebase."),
    repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo in 'owner/name' format."),
) -> None:
    """Ask a question about a GitHub repository."""
    from chromax.agents.basic import ask as agent_ask

    console.print(f"[bold cyan]Chromax[/bold cyan] — asking about [green]{repo}[/green]...")
    answer = agent_ask(question, repo)
    console.print()
    console.print(Markdown(answer))
