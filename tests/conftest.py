"""Test wiring: make the scripts package importable, hand out fresh stores."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "vigia-watch" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from vigia.store import VigiaStore  # noqa: E402


@pytest.fixture()
def store(tmp_path):
    return VigiaStore(str(tmp_path / "vigia"))
