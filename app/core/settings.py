from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def ensure_settings_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)

    _ENV_LOADED = True


def get_required_setting(name: str) -> str:
    ensure_settings_loaded()
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"{name} environment variable must be set")
    return value
