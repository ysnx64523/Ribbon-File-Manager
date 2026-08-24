"""Persistent user settings (JSON file under XDG config)."""

from __future__ import annotations

import json
from typing import Any

from .. import config

_DEFAULTS: dict[str, Any] = {
    "lang": "",          # e.g. "zh_CN"; empty = system default
    "theme": "system",   # system | light | dark
}


def settings_path():
    return config.SETTINGS_DIR / "settings.json"


def load() -> dict[str, Any]:
    data = dict(_DEFAULTS)
    try:
        raw = json.loads(settings_path().read_text("utf-8"))
        for key in _DEFAULTS:
            if key in raw:
                data[key] = raw[key]
    except (OSError, ValueError):
        pass
    return data


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def save(updates: dict[str, Any]) -> None:
    data = load()
    data.update(updates)
    try:
        config.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        settings_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass
