"""OSSTriage CLI — AI-driven PR review and Issue triage from the command line."""

from __future__ import annotations

import sys
from pathlib import Path

import dspy
import typer
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

from osstriage import __version__
from osstriage.core.config import Settings
from osstriage.core.exceptions import ConfigError, GitHubAPIError, AIModuleError, OSSTriageError
from osstriage.core.logging import setup_logging, get_logger
from osstriage.dspy_modules.review_pr import ReviewPRModule
from osstriage.dspy_modules.triage_issue import TriageIssueModule
from osstriage.github_client import GitHubClient, parse_github_url

# ---------------------------------------------------------------------------
# App & console setup
# ---------------------------------------------------------------------------

custom_theme = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "header": "bold magenta",
    }
)
console = Console(theme=custom_theme)
logger = get_logger("cli")

app = typer.Typer(
    name="osstriage",
    help="🤖 AI-driven PR review & Issue triage for OSS maintainers.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_settings() -> Settings:
    """Load and validate settings, printing a friendly error on failure."""
    try:
        return Settings.load()
    except ConfigError as exc:
        console.print(f"[error]Configuration error:[/error] {exc}")
        raise typer.Exit(code=1) from exc


def _configure_dspy(settings: Settings, model: str | None = None) -> None:
    """Initialise DSPy with the chosen LLM backend."""
    model_name = model or settings.model
    lm = dspy.LM(
        model=f"openai/{model_name}",
        api_key=settings.openai_api_key,
    )
    dspy.configure(lm=lm)
    logger.info("DSPy configured with model: %s", model_name)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def review_pr(
    pr_url: str = typer.Argument(
        ...,
        help="Full GitHub PR URL (e.g. https://github.com/owner/repo/pull/42)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the LLM model (default: from env or gpt-4o).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only display the review locally — do not post a comment on GitHub.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging.",
    ),
) -> None:
    """Review a Pull Request using AI and post structured feedback."""
    settings = _load_settings()
    setup_logging("DEBUG" if verbose else settings.log_level)

    console.print(
        Panel(
            f"[header]OSSTriage v{__version__}[/header] — Reviewing PR",
            subtitle=pr_url,
        )
    )

    # Parse URL
    try:
        parsed = parse_github_url(pr_url)
    except GitHubAPIError as exc:
        console.print(f"[error]{exc}[/error]")
        raise typer.Exit(code=1) from exc

    # Fetch PR data
    with console.status("[info]Fetching PR data from GitHub…[/info]"):
        try:
            client = GitHubClient(settings.github_token)
            pr_data = client.get_pr(parsed.owner, parsed.repo, parsed.number)
        except OSSTriageError as exc:
            console.print(f"[error]Failed to fetch PR:[/error] {exc}")
            raise typer.Exit(code=1) from exc

    console.print(
        f"[success]✓[/success] Fetched PR #{pr_data.number}: "
        f"[bold]{pr_data.title}[/bold]  "
        f"(+{pr_data.additions} / -{pr_data.deletions} across {pr_data.changed_files} files)"
    )

    # Run AI review
    with console.status("[info]Running AI-powered code review…[/info]"):
        _configure_dspy(settings, model)
        reviewer = ReviewPRModule()
        try:
            result = reviewer(
                diff=pr_data.diff,
                pr_title=pr_data.title,
                pr_body=pr_data.body,
            )
        except AIModuleError as exc:
            console.print(f"[error]AI review failed:[/error] {exc}")
            raise typer.Exit(code=1) from exc

    # Display result
    console.print()
    console.print(Panel(result.to_markdown(), title="Review Result", border_style="green"))

    # Post comment (unless dry-run)
    if not dry_run:
        with console.status("[info]Posting review comment on GitHub…[/info]"):
            try:
                client.post_review_comment(
                    parsed.owner,
                    parsed.repo,
                    parsed.number,
                    result.to_markdown(),
                )
                console.print("[success]✓ Review comment posted on GitHub![/success]")
            except OSSTriageError as exc:
                console.print(f"[warning]Could not post comment:[/warning] {exc}")
    else:
        console.print("[warning]Dry-run mode — comment was NOT posted.[/warning]")


@app.command()
def triage_issue(
    issue_url: str = typer.Argument(
        ...,
        help="Full GitHub Issue URL (e.g. https://github.com/owner/repo/issues/7)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the LLM model (default: from env or gpt-4o).",
    ),
    apply_labels: bool = typer.Option(
        False,
        "--apply-labels",
        help="Automatically apply suggested labels to the issue.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only display the triage result — do not modify the issue.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging.",
    ),
) -> None:
    """Triage a GitHub Issue — suggest labels, priority, and a summary."""
    settings = _load_settings()
    setup_logging("DEBUG" if verbose else settings.log_level)

    console.print(
        Panel(
            f"[header]OSSTriage v{__version__}[/header] — Triaging Issue",
            subtitle=issue_url,
        )
    )

    # Parse URL
    try:
        parsed = parse_github_url(issue_url)
    except GitHubAPIError as exc:
        console.print(f"[error]{exc}[/error]")
        raise typer.Exit(code=1) from exc

    # Fetch issue
    with console.status("[info]Fetching issue from GitHub…[/info]"):
        try:
            client = GitHubClient(settings.github_token)
            issue_data = client.get_issue(parsed.owner, parsed.repo, parsed.number)
        except OSSTriageError as exc:
            console.print(f"[error]Failed to fetch issue:[/error] {exc}")
            raise typer.Exit(code=1) from exc

    console.print(
        f"[success]✓[/success] Fetched Issue #{issue_data.number}: "
        f"[bold]{issue_data.title}[/bold]"
    )

    # Run AI triage
    with console.status("[info]Running AI-powered issue triage…[/info]"):
        _configure_dspy(settings, model)
        triager = TriageIssueModule()
        try:
            result = triager(
                issue_title=issue_data.title,
                issue_body=issue_data.body,
                existing_labels=", ".join(issue_data.labels),
            )
        except AIModuleError as exc:
            console.print(f"[error]AI triage failed:[/error] {exc}")
            raise typer.Exit(code=1) from exc

    # Display result
    console.print()
    console.print(Panel(result.to_markdown(), title="Triage Result", border_style="cyan"))

    # Apply labels (unless dry-run)
    if apply_labels and not dry_run:
        with console.status("[info]Applying labels on GitHub…[/info]"):
            try:
                client.add_labels(
                    parsed.owner,
                    parsed.repo,
                    parsed.number,
                    result.suggested_labels,
                )
                console.print("[success]✓ Labels applied on GitHub![/success]")
            except OSSTriageError as exc:
                console.print(f"[warning]Could not apply labels:[/warning] {exc}")
    elif dry_run:
        console.print("[warning]Dry-run mode — no changes made on GitHub.[/warning]")


@app.command()
def setup_action() -> None:
    """Scaffold a GitHub Action workflow for OSSTriage into the current repository."""
    workflow_dir = Path(".github/workflows")
    workflow_file = workflow_dir / "osstriage.yml"

    if workflow_file.exists():
        overwrite = typer.confirm(
            f"{workflow_file} already exists. Overwrite?", default=False
        )
        if not overwrite:
            console.print("[warning]Aborted.[/warning]")
            raise typer.Exit()

    workflow_content = """\
# OSSTriage — Automated PR Review
# https://github.com/your-org/osstriage
name: OSSTriage PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        run: uv python install 3.13

      - name: Install OSSTriage
        run: uv tool install osstriage

      - name: Review Pull Request
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          osstriage review-pr \\
            "https://github.com/${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
"""

    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_file.write_text(workflow_content)

    console.print(
        f"[success]✓ GitHub Action workflow created at {workflow_file}[/success]\n\n"
        "Next steps:\n"
        "  1. Add [bold]OPENAI_API_KEY[/bold] to your repository secrets.\n"
        "  2. Commit and push the workflow file.\n"
        "  3. Open a PR to see OSSTriage in action!"
    )


@app.command()
def version() -> None:
    """Show the OSSTriage version."""
    console.print(f"osstriage [header]v{__version__}[/header]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
