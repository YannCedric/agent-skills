#!/usr/bin/env python3
"""Compatibility wrapper for the diagrammer example visual gate."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagrammer.example_gate import main


if __name__ == "__main__":
    raise SystemExit(main())
