"""Agent preferences. Missing keys mean onboarding is unfinished."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kit.jsonio import load_json, save_json_atomic

REQUIRED_KEYS = ("timezone", "digest_time", "language")

# Defaults a fresh agent runs on until onboarding writes the file.
DEFAULTS: dict[str, Any] = {
    "timezone": "UTC",
    "digest_time": "08:30",
    "digest_enabled": True,
    "language": "",                 # "" = mirror the user each turn
    "threshold_pct": 5.0,           # default drop that fires an alert
    "sweep_times": ["09:00", "15:00", "21:00"],
}


def config_path(home: str) -> str:
    return f"{home}/config.json"


def load(home: str) -> dict[str, Any]:
    stored = load_json(config_path(home), {}) or {}
    return {**DEFAULTS, **stored}


def save(home: str, config: dict[str, Any]) -> None:
    save_json_atomic(config_path(home), config)


def missing_keys(home: str) -> list[str]:
    """Keys onboarding has not asked about yet -- judged on the FILE, never on
    the defaults: a default is what the agent runs on, not what the user chose."""
    stored = load_json(config_path(home), {}) or {}
    return [key for key in REQUIRED_KEYS if key not in stored]
