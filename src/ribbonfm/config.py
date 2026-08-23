"""Global application configuration and constants.

Kept free of any UI imports so it can be used by the core layer and tests.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_ID = "org.ribbonfm.RibbonFM"
APP_NAME = "Ribbon File Manager"
APP_GETTEXT_DOMAIN = "ribbonfm"
LOG_DOMAIN = "ribbonfm"

# Where the package ships its data (UI description, CSS, icons). When installed
# as a regular dependency this resolves to the package directory; when running
# from a source checkout (src/ layout) it falls back to the git tree so we can
# edit the UI without reinstalling.
_RESOURCE_BASE = Path(__file__).resolve().parent

# Preferred source layout: resources/{ui,css,icons}. A checkout can also place
# them next to the package (e.g. data/ directory) -- fallbacks are listed in
# order.
def resources_dir() -> Path:
    """Return the directory that contains the bundled resources."""
    for candidate in (
        _RESOURCE_BASE / "resources",
        _RESOURCE_BASE.parent / "resources",
        Path(__file__).resolve().parent.parent.parent / "data",
        _RESOURCE_BASE,
    ):
        if candidate.is_dir():
            return candidate
    return _RESOURCE_BASE


SETTINGS_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ribbonfm"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ribbonfm"

# Directory listing limits used to keep huge directories responsive.
MAX_RECENT_FILES = 12
DEFAULT_SORT = ("name", True)  # (column key, ascending)
