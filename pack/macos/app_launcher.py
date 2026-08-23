#!/usr/bin/env python3
"""Launcher stub used by macOS ``.app`` bundles.

py2app wraps a script; this thin wrapper just delegates to the installed
``ribbonfm`` console entry point so the bundle can locate translations and the
bundled resources (which are installed as package data).
"""

import sys

from ribbonfm.app import main

if __name__ == "__main__":
    sys.exit(main())
