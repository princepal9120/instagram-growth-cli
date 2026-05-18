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


def test_market_command_json(monkeypatch):
    import ig_cli.main as main

    monkeypatch.setattr(
        main,
        "_run",
        lambda fetcher, proxy: [
            InstagramPostResult(
                id="1",
                desc="How to automate content marketing for indie founders #saas",
                author="creator",
                create_time=None,
                play_count=1000,
                like_count=120,
                comment_count=15,
                share_count=5,
                url="https://example.com",
                raw={},
            )
        ],
    )

    result = runner.invoke(app, ["market", "ai marketing", "--format", "json"])

    assert result.exit_code == 0
    assert '"query": "ai marketing"' in result.output
    assert '"opportunity_score"' in result.output
