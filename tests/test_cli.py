from pathlib import Path

from typer.testing import CliRunner

from ig_cli.core.client import InstagramPostResult
from ig_cli.main import app, render_table

runner = CliRunner()


def test_help_works():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Instagram trend and growth intelligence" in result.output


def test_status_without_config(monkeypatch, tmp_path):
    import ig_cli.config as config
    import ig_cli.main as main

    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    monkeypatch.setattr(main, "load_config", lambda: config.load_config(path))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Anonymous mode" in result.output


def test_render_table_smoke():
    render_table([
        InstagramPostResult(
            id="1",
            desc="hello world",
            author="creator",
            create_time=None,
            play_count=1000,
            like_count=100,
            comment_count=10,
            share_count=None,
            url="https://example.com",
            raw={},
        )
    ])


def _sample_post(desc: str = "How to automate content marketing for indie founders #saas") -> InstagramPostResult:
    return InstagramPostResult(
        id="1",
        desc=desc,
        author="creator",
        create_time=None,
        play_count=1000,
        like_count=120,
        comment_count=15,
        share_count=5,
        url="https://example.com",
        raw={},
    )


def test_market_command_json(monkeypatch):
    import ig_cli.main as main

    monkeypatch.setattr(main, "_run", lambda fetcher, proxy: [_sample_post()])

    result = runner.invoke(app, ["market", "ai marketing", "--format", "json"])

    assert result.exit_code == 0
    assert '"query": "ai marketing"' in result.output
    assert '"opportunity_score"' in result.output
    assert '"reel_ideas"' in result.output
    assert '"lead_magnet"' in result.output


def test_compare_command(monkeypatch):
    import ig_cli.main as main

    sample = [_sample_post()]
    monkeypatch.setattr(main, "_client", lambda: _FakeClient(sample))

    result = runner.invoke(app, ["compare", "hashtag", "aitools", "buildinpublic"])

    assert result.exit_code == 0
    assert "aitools" in result.output
    assert "buildinpublic" in result.output


class _FakeClient:
    def __init__(self, results: list[InstagramPostResult]) -> None:
        self._results = results

    async def get_hashtag(self, tag: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        return self._results

    async def get_user(self, username: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        return self._results

    async def get_reels(self, username: str, count: int = 20, proxy: str | None = None) -> list[InstagramPostResult]:
        return self._results


def test_sync_command(monkeypatch, tmp_path: Path):
    import ig_cli.main as main

    sample = [_sample_post()]
    monkeypatch.setattr(main, "_client", lambda: _FakeClient(sample))
    monkeypatch.setattr(main, "ARCHIVE_PATH", tmp_path / "archive.db")

    result = runner.invoke(app, ["sync", "hashtag", "aitools", "--count", "5"])

    assert result.exit_code == 0
    assert "Synced" in result.output
    assert (tmp_path / "archive.db").exists()


def test_search_local_command(monkeypatch, tmp_path: Path):
    import ig_cli.main as main
    from ig_cli.db import init_db, upsert_posts

    db_path = tmp_path / "archive.db"
    conn = init_db(db_path)
    upsert_posts(conn, [_sample_post("How to automate founder marketing for SaaS")], source="hashtag", tag_or_user="aitools")
    conn.close()

    monkeypatch.setattr(main, "ARCHIVE_PATH", db_path)

    result = runner.invoke(app, ["search", "automate", "--local"])

    assert result.exit_code == 0


def test_archive_command(monkeypatch, tmp_path: Path):
    import ig_cli.main as main
    from ig_cli.db import init_db, upsert_posts

    db_path = tmp_path / "archive.db"
    conn = init_db(db_path)
    upsert_posts(conn, [_sample_post()], source="hashtag", tag_or_user="aitools")
    conn.close()

    monkeypatch.setattr(main, "ARCHIVE_PATH", db_path)

    result = runner.invoke(app, ["archive"])

    assert result.exit_code == 0
    assert "Total posts" in result.output


def test_market_local_no_cache(monkeypatch, tmp_path: Path):
    import ig_cli.main as main

    db_path = tmp_path / "archive.db"
    monkeypatch.setattr(main, "ARCHIVE_PATH", db_path)

    result = runner.invoke(app, ["market", "aitools", "--local"])

    assert result.exit_code == 1
    assert "ig sync" in result.output
