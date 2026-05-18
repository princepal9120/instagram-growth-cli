from pathlib import Path

import ig_cli.config as config
from ig_cli.config import IgConfig, clear_config, load_config, save_config


def test_config_roundtrip(monkeypatch, tmp_path: Path):
    session_path = tmp_path / "session"
    session_path.write_text("session")
    monkeypatch.setattr(config, "SESSION_PATH", session_path)

    path = tmp_path / "config.json"
    save_config(IgConfig(username="founder", region="IN"), path)
    loaded = load_config(path)
    assert loaded.username == "founder"
    assert loaded.region == "IN"
    assert loaded.is_authenticated


def test_clear_config(monkeypatch, tmp_path: Path):
    session_path = tmp_path / "session"
    session_path.write_text("session")
    monkeypatch.setattr(config, "SESSION_PATH", session_path)

    path = tmp_path / "config.json"
    save_config(IgConfig(username="founder"), path)
    clear_config(path)
    assert not path.exists()
    assert not session_path.exists()
