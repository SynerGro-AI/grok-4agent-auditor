"""Command-line interface for the Grok XAI 4-Agent Code Auditor."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rprint

from grok_auditor.core.config import AuditorConfig
from grok_auditor.core.orchestrator import AuditOrchestrator, AuditReport

app = typer.Typer(
    name="grok-auditor",
    help="Grok XAI 4-Agent Code Project Auditor — transforms basic code into enterprise-grade software.",
    add_completion=False,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )


def _print_report(report: AuditReport) -> None:
    """Render a rich summary of the AuditReport to stdout."""
    console.rule(f"[bold cyan]Grok XAI 4-Agent Audit: {report.source_file}")

    # ── Agent 1: Analysis ─────────────────────────────────────────────
    analysis = report.analysis
    console.print(
        Panel(
            f"[bold]Language:[/bold] {analysis.language}\n"
            f"[bold]Quality Score:[/bold] {analysis.quality_score}/100\n"
            f"[bold]Complexity:[/bold] {analysis.complexity}\n"
            f"[bold]Lines of Code:[/bold] {analysis.lines_of_code}\n\n"
            f"{analysis.summary}",
            title="[green]Agent 1 — Code Analysis",
            border_style="green",
        )
    )
    if analysis.issues:
        t = Table(title="Issues", show_header=True)
        t.add_column("Severity", style="bold")
        t.add_column("Category")
        t.add_column("Description")
        t.add_column("Line")
        for issue in analysis.issues:
            t.add_row(issue.severity, issue.category, issue.description, str(issue.line_hint or ""))
        console.print(t)

    # ── Agent 2: Security ─────────────────────────────────────────────
    security = report.security
    risk_colour = {
        "none": "green", "low": "yellow", "medium": "orange3",
        "high": "red", "critical": "bold red",
    }.get(security.risk_level.lower(), "white")
    console.print(
        Panel(
            f"[bold]Risk Level:[/bold] [{risk_colour}]{security.risk_level}[/{risk_colour}]\n\n"
            f"{security.summary}",
            title="[red]Agent 2 — Security Audit",
            border_style="red",
        )
    )
    if security.vulnerabilities:
        t = Table(title="Vulnerabilities", show_header=True)
        t.add_column("ID")
        t.add_column("Severity", style="bold")
        t.add_column("Title")
        t.add_column("OWASP")
        for v in security.vulnerabilities:
            t.add_row(v.id, v.severity, v.title, v.owasp_category or "")
        console.print(t)

    # ── Agent 3: Architecture ─────────────────────────────────────────
    arch = report.architecture
    console.print(
        Panel(
            f"[bold]Current Pattern:[/bold] {arch.current_pattern}\n"
            f"[bold]Maturity Level:[/bold] {arch.maturity_level}\n\n"
            f"{arch.summary}",
            title="[blue]Agent 3 — Architecture",
            border_style="blue",
        )
    )
    if arch.recommended_patterns:
        t = Table(title="Recommended Patterns", show_header=True)
        t.add_column("Pattern")
        t.add_column("Rationale")
        t.add_column("First Step")
        for p in arch.recommended_patterns:
            t.add_row(p.pattern, p.rationale, p.implementation_hint)
        console.print(t)

    # ── Agent 4: Refactor ─────────────────────────────────────────────
    refactor = report.refactor
    console.print(
        Panel(
            f"[bold]Estimated Enterprise Quality Score:[/bold] {refactor.estimated_quality_score}/100\n\n"
            f"[bold]Migration Notes:[/bold]\n{refactor.migration_notes}",
            title="[magenta]Agent 4 — Enterprise Refactor",
            border_style="magenta",
        )
    )
    if refactor.changelog:
        t = Table(title="Refactoring Changes", show_header=True)
        t.add_column("#")
        t.add_column("Change")
        for i, entry in enumerate(refactor.changelog, 1):
            t.add_row(str(i), entry.change)
        console.print(t)

    console.rule(f"[bold]Device used:[/bold] {report.device_used}")


@app.command()
def audit(
    source: Optional[Path] = typer.Argument(
        None,
        help="Path to the source file to audit. Reads from stdin if omitted.",
        exists=False,
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l", help="Override language hint (e.g. python, javascript)."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write full JSON report to this file."
    ),
    save_refactor: Optional[Path] = typer.Option(
        None, "--save-refactor", help="Write the refactored source code to this file."
    ),
    save_tests: Optional[Path] = typer.Option(
        None, "--save-tests", help="Write the generated test scaffold to this file."
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override Grok model."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Audit a source file (or stdin) with all four Grok XAI agents."""
    _setup_logging(verbose)

    # Read code
    if source is not None:
        if not source.exists():
            console.print(f"[red]Error:[/red] File not found: {source}")
            raise typer.Exit(1)
        code = source.read_text(encoding="utf-8")
        label = str(source)
    else:
        console.print("[dim]Reading source from stdin… (Ctrl-D to finish)[/dim]")
        code = sys.stdin.read()
        label = "<stdin>"

    if not code.strip():
        console.print("[red]Error:[/red] No source code provided.")
        raise typer.Exit(1)

    # Build config
    config_kwargs: dict = {}
    if model:
        config_kwargs["model"] = model

    try:
        config = AuditorConfig(**config_kwargs)
    except Exception as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1)

    # Run audit
    orchestrator = AuditOrchestrator(config)
    try:
        with console.status("[bold green]Running 4-agent audit…"):
            report = asyncio.run(
                orchestrator.audit_async(code, source_label=label, language=language)
            )
    except Exception as exc:
        console.print(f"[red]Audit failed:[/red] {exc}")
        raise typer.Exit(1)
    finally:
        asyncio.run(orchestrator.close())

    _print_report(report)

    # Optional outputs
    if output:
        report.save(output)
        console.print(f"[dim]Full JSON report written to {output}[/dim]")

    if save_refactor and report.refactor.refactored_code:
        save_refactor.parent.mkdir(parents=True, exist_ok=True)
        save_refactor.write_text(report.refactor.refactored_code, encoding="utf-8")
        console.print(f"[dim]Refactored code written to {save_refactor}[/dim]")

    if save_tests and report.refactor.test_scaffold:
        save_tests.parent.mkdir(parents=True, exist_ok=True)
        save_tests.write_text(report.refactor.test_scaffold, encoding="utf-8")
        console.print(f"[dim]Test scaffold written to {save_tests}[/dim]")


@app.command()
def version() -> None:
    """Print the version and exit."""
    from grok_auditor import __version__

    rprint(f"grok-auditor [bold]{__version__}[/bold]")


if __name__ == "__main__":
    app()
