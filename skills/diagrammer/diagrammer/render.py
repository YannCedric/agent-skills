#!/usr/bin/env python3
"""Render a diagram HTML file to PNG with Playwright."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


PRESETS = {
    "presentation-16x9": (1600, 900),
    "doc-wide": (1600, 1000),
    "square-share": (1200, 1200),
    "mobile-share": (900, 1200),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Render diagram HTML to PNG")
    parser.add_argument("html", help="Input HTML path or URL")
    parser.add_argument("output", nargs="?", help="Output PNG path")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="presentation-16x9")
    parser.add_argument("--width", type=int, help="Override viewport width")
    parser.add_argument("--height", type=int, help="Override viewport height")
    parser.add_argument("--scale", type=int, default=2, help="Device scale factor")
    parser.add_argument("--wait", type=int, default=500, help="Wait time after load in ms")
    parser.add_argument("--quiet", action="store_true", help="Suppress helper progress output")
    return parser.parse_args()


def to_url(value):
    if value.startswith(("http://", "https://", "file://")):
        return value
    path = Path(value).expanduser().resolve()
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.as_uri()


def svg_viewbox_size(value):
    if value.startswith(("http://", "https://", "file://")):
        return None
    path = Path(value).expanduser().resolve()
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r"<svg[^>]*\bviewBox=['\"]\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)", source, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def main():
    args = parse_args()
    preset_width, preset_height = PRESETS[args.preset]
    width = args.width or preset_width
    height = args.height or preset_height
    viewbox = svg_viewbox_size(args.html)
    if viewbox and not args.height:
        view_w, view_h = viewbox
        height = min(height, max(1, round(width * view_h / view_w)))
    output = args.output or str(Path(args.html).with_suffix(".png"))

    url = to_url(args.html)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if not shutil.which("agent-browser"):
            print("Error: neither python playwright nor agent-browser is installed.", file=sys.stderr)
            sys.exit(1)
        output_stream = subprocess.DEVNULL if args.quiet else None
        subprocess.run(["agent-browser", "set", "viewport", str(width), str(height)], check=True, stdout=output_stream)
        subprocess.run(["agent-browser", "open", url], check=True, stdout=output_stream)
        if args.wait:
            subprocess.run(["agent-browser", "wait", str(args.wait)], check=True, stdout=output_stream)
        subprocess.run(["agent-browser", "screenshot", output], check=True, stdout=output_stream)
        subprocess.run(["agent-browser", "close"], check=False, stdout=output_stream)
        size = os.path.getsize(output)
        label = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f}MB"
        if not args.quiet:
            print(f"Rendered {output} ({width}x{height}, {label})")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=args.scale,
        )
        page.goto(url, wait_until="networkidle")
        if args.wait:
            page.wait_for_timeout(args.wait)
        svg = page.locator("svg").first
        if svg.count():
            svg.screenshot(path=output)
        else:
            page.screenshot(path=output, full_page=True)
        browser.close()

    size = os.path.getsize(output)
    label = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f}MB"
    if not args.quiet:
        print(f"Rendered {output} ({width}x{height} @ {args.scale}x, {label})")


if __name__ == "__main__":
    main()
