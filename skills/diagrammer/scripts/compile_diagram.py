#!/usr/bin/env python3
"""Compatibility wrapper for the packaged diagrammer compiler."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagrammer.cli import main


if __name__ == "__main__":
    main()
