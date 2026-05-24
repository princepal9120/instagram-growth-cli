from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_DIR = Path(os.environ.get("IG_CLI_HOME", Path.home() / ".ig-cli")).expanduser()
CONFIG_PATH = APP_DIR / "config.json"
PROXIES_PATH = APP_DIR / "proxies.txt"
SESSION_PATH = APP_DIR / "session"
ARCHIVE_PATH = APP_DIR / "archive.db"


@dataclass(slots=True)
class IgConfig:
    username: str | None = None
    region: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.username and SESSION_PATH.exists())


def ensure_app_dir() -> Path:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DIR


def load_config(path: Path = CONFIG_PATH) -> IgConfig:
    if not path.exists():
        return IgConfig()
    try:
        raw: dict[str, Any] = json.loads(path.read_text())
    except json.JSONDecodeError:
        return IgConfig()
    return IgConfig(username=raw.get("username"), region=raw.get("region"))


def save_config(config: IgConfig, path: Path = CONFIG_PATH) -> None:
    ensure_app_dir()
    data = {"username": config.username, "region": config.region}
    path.write_text(json.dumps(data, indent=2) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def clear_config(path: Path = CONFIG_PATH) -> None:
    if path.exists():
        path.unlink()
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()


def load_proxies(path: Path = PROXIES_PATH) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
