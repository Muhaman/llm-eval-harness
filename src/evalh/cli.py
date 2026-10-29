"""`evalh` command line."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import structlog
import typer

from evalh.compare import Comparison, compare
from evalh.config import ConfigError, Suite, load_suite
from evalh.llm import Judge
from evalh.report import read_jsonl, render_markdown, write_jsonl
from evalh.runner import run_suite

app = typer.Typer(add_completion=False, no_args_is_help=True, help="LLM regression eval harness.")

EXIT_REGRESSED = 1
EXIT_CONFIG_ERROR = 2


@app.callback()
def main() -> None:
    """LLM regression eval harness."""


def _needs_judge(suite: Suite) -> bool:
    return any(spec.type == "judge" for case in suite.cases for spec in case.graders)


def _fail(message: str) -> typer.Exit:
    typer.echo(f"error: {message}", err=True)
    return typer.Exit(EXIT_CONFIG_ERROR)


@app.command()
def run(
    suite_path: Annotated[Path, typer.Argument(metavar="SUITE", help="Path to a suite YAML file.")],
    out: Annotated[Path, typer.Option(help="Where to write per-case JSONL results.")] = Path(
        "results.jsonl"
    ),
    report: Annotated[Path, typer.Option(help="Where to write the Markdown report.")] = Path(
        "report.md"
    ),
    baseline: Annotated[
        Path | None, typer.Option(help="Baseline results JSONL to compare against.")
    ] = None,
    threshold: Annotated[float, typer.Option(help="Allowed pass-rate drop.")] = 0.02,
    concurrency: Annotated[int, typer.Option(min=1, help="Max in-flight cases.")] = 8,
    timeout: Annotated[float, typer.Option(min=0.001, help="Per-case timeout, seconds.")] = 60.0,
) -> None:
    """Run a suite. Exit 1 on regression vs baseline, 2 on config error."""
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))
    try:
        suite = load_suite(suite_path)
        judge = Judge() if _needs_judge(suite) else None
        baseline_result = read_jsonl(baseline) if baseline is not None else None
        result = asyncio.run(
            run_suite(
                suite,
                concurrency=concurrency,
                timeout_s=timeout,
                judge=judge,
                base_dir=suite_path.resolve().parent,
            )
        )
    except ConfigError as exc:
        raise _fail(str(exc)) from exc

    comparison: Comparison | None = None
    if baseline_result is not None:
        comparison = compare(result, baseline_result, threshold)
    write_jsonl(result, out)
    report.write_text(render_markdown(result, comparison), encoding="utf-8")

    typer.echo(f"{result.passed}/{len(result.cases)} cases passed ({result.pass_rate:.1%})")
    if comparison is not None and comparison.regressed:
        failing = ", ".join(comparison.newly_failing) or "none"
        typer.echo(
            f"REGRESSION: pass rate {comparison.pass_rate_delta:+.1%}, newly failing: {failing}"
        )
        raise typer.Exit(EXIT_REGRESSED)
