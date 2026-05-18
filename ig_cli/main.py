from __future__ import annotations

import asyncio
import csv
import getpass
import json
from enum import Enum
from pathlib import Path
from typing import Callable

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import IgConfig, SESSION_PATH, clear_config, ensure_app_dir, load_config, load_proxies, save_config
from .core.client import InstagramBlockedError, InstagramPostResult, InstagramTrendClient, VideoResult
from .market import MarketInsight, analyze_market

app = typer.Typer(help="Instagram trend and growth intelligence from your terminal.", no_args_is_help=True)
console = Console()


class OutputFormat(str, Enum):
    table = "table"
    json = "json"


class ExportKind(str, Enum):
    hashtag = "hashtag"
    profile = "profile"
    reels = "reels"
    search = "search"


class ExportFormat(str, Enum):
    json = "json"
    csv = "csv"


class MarketSource(str, Enum):
    search = "search"
    hashtag = "hashtag"
    profile = "profile"
    reels = "reels"


def version_callback(value: bool) -> None:
    if value:
        console.print(f"ig-cli {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True, help="Show version."),
) -> None:
    return None


@app.command()
def login(
    username: str = typer.Option(..., "--username", "-u", help="Instagram username."),
    password: str | None = typer.Option(None, "--password", "-p", help="Instagram password. If omitted, you will be prompted."),
    region: str | None = typer.Option(None, "--region", help="Default region hint, for example IN or US."),
) -> None:
    """Store an Instaloader login session in ~/.ig-cli/session."""
    if InstagramTrendClient is None:  # pragma: no cover
        raise typer.Exit(1)
    ensure_app_dir()
    secret = password or getpass.getpass("Instagram password: ").strip()
    if not secret:
        raise typer.BadParameter("password cannot be empty")
    try:
        import instaloader

        loader = instaloader.Instaloader()
        loader.login(username, secret)
        loader.save_session_to_file(filename=str(SESSION_PATH))
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Instagram login failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    save_config(IgConfig(username=username, region=region))
    console.print("[green]Saved Instagram session to ~/.ig-cli/session[/green]")


@app.command()
def status() -> None:
    """Show whether ig is authenticated."""
    config = load_config()
    if config.is_authenticated:
        console.print(f"[green]Authenticated[/green] user={config.username}")
        if config.region:
            console.print(f"Default region: {config.region}")
    else:
        console.print("[yellow]Anonymous mode[/yellow]. Public Instagram requests will be attempted without login.")
        console.print("Run `ig login --username YOUR_USERNAME` if hashtags or profiles require a session.")


@app.command()
def logout() -> None:
    """Remove stored Instagram auth config and session."""
    clear_config()
    console.print("[green]Logged out. Removed ~/.ig-cli config and session files.[/green]")


@app.command()
def hashtag(
    tag: str = typer.Argument(..., help="Hashtag without or with #."),
    count: int = typer.Option(20, "--count", "-n", min=1, max=200),
    output: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
    proxy: str | None = typer.Option(None, "--proxy", help="Reserved for future proxy support."),
) -> None:
    """Fetch recent/top Instagram posts for a hashtag."""
    _run_and_render(lambda client, px: client.get_hashtag(tag, count=count, proxy=px), output, proxy)


@app.command("profile")
def profile_cmd(
    username: str = typer.Argument(..., help="Instagram username without or with @."),
    count: int = typer.Option(20, "--count", "-n", min=1, max=200),
    output: OutputFormat = typer.Option(OutputFormat.table, "--format"),
    proxy: str | None = typer.Option(None, "--proxy"),
) -> None:
    """Fetch posts for an Instagram profile."""
    _run_and_render(lambda client, px: client.get_user(username, count=count, proxy=px), output, proxy)


@app.command()
def reels(
    username: str = typer.Argument(..., help="Instagram username without or with @."),
    count: int = typer.Option(20, "--count", "-n", min=1, max=200),
    output: OutputFormat = typer.Option(OutputFormat.table, "--format"),
    proxy: str | None = typer.Option(None, "--proxy"),
) -> None:
    """Fetch video/reel-like posts for an Instagram profile."""
    _run_and_render(lambda client, px: client.get_reels(username, count=count, proxy=px), output, proxy)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query. Uses the strongest hashtag candidate because Instagram search is private."),
    count: int = typer.Option(20, "--count", "-n", min=1, max=200),
    output: OutputFormat = typer.Option(OutputFormat.table, "--format"),
    proxy: str | None = typer.Option(None, "--proxy"),
) -> None:
    """Search Instagram through a hashtag fallback."""
    _run_and_render(lambda client, px: client.search(query, count=count, proxy=px), output, proxy)


@app.command()
def export(
    kind: ExportKind = typer.Argument(..., help="One of: hashtag, profile, reels, search."),
    value: str = typer.Argument(..., help="Tag, username, or query."),
    out: Path = typer.Option(..., "--out", "-o", help="Output file path."),
    count: int = typer.Option(50, "--count", "-n", min=1, max=500),
    export_format: ExportFormat = typer.Option(ExportFormat.json, "--format"),
    proxy: str | None = typer.Option(None, "--proxy"),
) -> None:
    """Export Instagram trend data to JSON or CSV."""
    async def fetch(client: InstagramTrendClient, px: str | None) -> list[VideoResult]:
        if kind == ExportKind.hashtag:
            return await client.get_hashtag(value, count=count, proxy=px)
        if kind == ExportKind.profile:
            return await client.get_user(value, count=count, proxy=px)
        if kind == ExportKind.reels:
            return await client.get_reels(value, count=count, proxy=px)
        return await client.search(value, count=count, proxy=px)

    results = _run(fetch, proxy)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [item.to_dict() for item in results]
    if export_format == ExportFormat.json:
        out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    else:
        fieldnames = ["id", "desc", "author", "create_time", "play_count", "like_count", "comment_count", "share_count", "url"]
        with out.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key) for key in fieldnames})
    console.print(f"[green]Exported {len(rows)} rows to {out}[/green]")


@app.command()
def market(
    query: str = typer.Argument(..., help="Niche, product category, hashtag, profile, or customer pain to analyze."),
    source: MarketSource = typer.Option(MarketSource.hashtag, "--source", help="Research source: search, hashtag, profile, or reels."),
    count: int = typer.Option(30, "--count", "-n", min=5, max=200),
    output: OutputFormat = typer.Option(OutputFormat.table, "--format"),
    proxy: str | None = typer.Option(None, "--proxy"),
) -> None:
    """Analyze Instagram posts and turn them into indie-hacker marketing actions."""
    async def fetch(client: InstagramTrendClient, px: str | None) -> list[VideoResult]:
        if source == MarketSource.profile:
            return await client.get_user(query, count=count, proxy=px)
        if source == MarketSource.reels:
            return await client.get_reels(query, count=count, proxy=px)
        if source == MarketSource.search:
            return await client.search(query, count=count, proxy=px)
        return await client.get_hashtag(query, count=count, proxy=px)

    results = _run(fetch, proxy)
    insight = analyze_market(results, query=query, source=source.value)
    if output == OutputFormat.json:
        console.print_json(json.dumps(insight.to_dict(), ensure_ascii=False))
    else:
        render_market(insight)


def _resolve_proxy(proxy: str | None) -> str | None:
    if proxy:
        return proxy
    proxies = load_proxies()
    if proxies:
        console.print("[yellow]Proxy file found, but Instaloader proxy support is not wired yet.[/yellow]")
    return None


def _client() -> InstagramTrendClient:
    config = load_config()
    return InstagramTrendClient(username=config.username, session_file=str(SESSION_PATH))


def _run(fetcher: Callable[[InstagramTrendClient, str | None], object], proxy: str | None) -> list[VideoResult]:
    async def run_fetch() -> list[VideoResult]:
        return await fetcher(_client(), _resolve_proxy(proxy))  # type: ignore[return-value]

    try:
        return asyncio.run(run_fetch())
    except InstagramBlockedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


def _run_and_render(fetcher: Callable[[InstagramTrendClient, str | None], object], output: OutputFormat, proxy: str | None) -> None:
    results = _run(fetcher, proxy)
    if output == OutputFormat.json:
        console.print_json(json.dumps([item.to_dict() for item in results], ensure_ascii=False))
    else:
        render_table(results)


def render_table(results: list[InstagramPostResult]) -> None:
    table = Table(title="Instagram trends")
    table.add_column("#", justify="right")
    table.add_column("Author")
    table.add_column("Views/Likes", justify="right")
    table.add_column("Likes", justify="right")
    table.add_column("Comments", justify="right")
    table.add_column("Caption")
    table.add_column("URL")
    for idx, item in enumerate(results, start=1):
        table.add_row(
            str(idx),
            item.author or "",
            _fmt(item.play_count),
            _fmt(item.like_count),
            _fmt(item.comment_count),
            _clip(item.desc or "", 80),
            item.url or "",
        )
    console.print(table)


def render_market(insight: MarketInsight) -> None:
    summary = Table(title=f"Instagram market intelligence: {insight.query}", show_header=False)
    summary.add_column("Metric", style="bold")
    summary.add_column("Value")
    summary.add_row("Source", insight.source)
    summary.add_row("Posts analyzed", str(insight.videos_analyzed))
    summary.add_row("Total views/likes", _fmt(insight.total_views))
    summary.add_row("Median views/likes", _fmt(insight.median_views))
    summary.add_row("Median engagement", f"{insight.median_engagement_rate:.2%}")
    summary.add_row("Opportunity score", f"{insight.opportunity_score}/100")
    summary.add_row("Decision", insight.decision)
    console.print(summary)

    signals = Table(title="Signals")
    signals.add_column("Keywords")
    signals.add_column("Hashtags")
    signals.add_column("Hooks")
    for idx in range(max(len(insight.top_keywords), len(insight.top_hashtags), len(insight.hook_formats), 1)):
        signals.add_row(_pair(insight.top_keywords, idx), _pair(insight.top_hashtags, idx, prefix="#"), _pair(insight.hook_formats, idx))
    console.print(signals)

    _render_list("Content angles", insight.content_angles)
    _render_list("Product opportunities", insight.product_opportunities)
    _render_list("Validation plan", insight.validation_plan)


def _render_list(title: str, rows: list[str]) -> None:
    table = Table(title=title, show_header=False)
    table.add_column("#", justify="right")
    table.add_column("Action")
    for idx, row in enumerate(rows, start=1):
        table.add_row(str(idx), row)
    console.print(table)


def _pair(rows: list[tuple[str, int]], idx: int, prefix: str = "") -> str:
    if idx >= len(rows):
        return ""
    label, count = rows[idx]
    return f"{prefix}{label} ({count})"


def _fmt(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value:,}"


def _clip(value: str, length: int) -> str:
    return value if len(value) <= length else value[: length - 1] + "…"


if __name__ == "__main__":
    app()
