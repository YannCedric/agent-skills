#!/usr/bin/env python3
"""CLI and file orchestration for the diagrammer compiler."""

import argparse
import json
import sys
from pathlib import Path

try:
    from .compiler import compile_diagram
except ImportError:  # pragma: no cover - script execution fallback
    from compiler import compile_diagram  # type: ignore


def read_definition(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON at {exc.lineno}:{exc.colno}: {exc.msg}", file=sys.stderr)
        sys.exit(2)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile diagram.def.json to layout/review/html")
    parser.add_argument("definition", help="Input diagram.def.json")
    parser.add_argument("--out-dir", default=None, help="Output directory")
    args = parser.parse_args(argv)

    source = Path(args.definition)
    out_dir = Path(args.out_dir) if args.out_dir else source.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    defn = read_definition(source)
    layout, review, html_source = compile_diagram(defn)

    (out_dir / "diagram.layout.json").write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    (out_dir / "diagram.review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    (out_dir / "diagram.html").write_text(html_source, encoding="utf-8")

    print(f"Wrote {out_dir / 'diagram.layout.json'}")
    print(f"Wrote {out_dir / 'diagram.review.json'}")
    print(f"Wrote {out_dir / 'diagram.html'}")
    if review["warnings"]:
        print(f"Review warnings: {review['warningCount']}", file=sys.stderr)


if __name__ == "__main__":
    main()
