#!/usr/bin/env python3
"""Render and check bundled diagrammer fixtures."""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_PNG_BYTES = 12_000
MIN_NON_BACKGROUND_RATIO = 0.002
MIN_DARK_PIXEL_RATIO = 0.001


def read_png(path):
    data = Path(path).read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = None
    idat = []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, _interlace = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat.append(chunk_data)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or color_type not in {2, 6}:
        raise ValueError("unsupported PNG encoding")
    channels = 4 if color_type == 6 else 3
    row_bytes = width * channels
    raw = zlib.decompress(b"".join(idat))
    rows = []
    cursor = 0
    previous = bytearray(row_bytes)
    for _row in range(height):
        filter_type = raw[cursor]
        cursor += 1
        current = bytearray(raw[cursor:cursor + row_bytes])
        cursor += row_bytes
        unfilter_scanline(current, previous, channels, filter_type)
        rows.append(bytes(current))
        previous = current
    return {"width": width, "height": height, "channels": channels, "rows": rows, "byteSize": len(data)}


def paeth(left, above, upper_left):
    estimate = left + above - upper_left
    pa = abs(estimate - left)
    pb = abs(estimate - above)
    pc = abs(estimate - upper_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return above
    return upper_left


def unfilter_scanline(current, previous, bpp, filter_type):
    for index in range(len(current)):
        left = current[index - bpp] if index >= bpp else 0
        above = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 0:
            value = current[index]
        elif filter_type == 1:
            value = current[index] + left
        elif filter_type == 2:
            value = current[index] + above
        elif filter_type == 3:
            value = current[index] + ((left + above) // 2)
        elif filter_type == 4:
            value = current[index] + paeth(left, above, upper_left)
        else:
            raise ValueError(f"unsupported PNG filter {filter_type}")
        current[index] = value & 0xFF


def png_visual_stats(path):
    image = read_png(path)
    channels = image["channels"]
    rows = image["rows"]
    first = rows[0][0:channels]
    background = first[:3]
    total = image["width"] * image["height"]
    non_background = 0
    dark = 0
    sampled = 0
    sample_step = max(1, total // 120_000)
    pixel_index = 0
    stride = channels
    for row in rows:
        for offset in range(0, len(row), stride):
            if pixel_index % sample_step:
                pixel_index += 1
                continue
            rgb = row[offset:offset + 3]
            if sum(abs(rgb[index] - background[index]) for index in range(3)) > 24:
                non_background += 1
            if sum(rgb) / 3 < 220:
                dark += 1
            sampled += 1
            pixel_index += 1
    return {
        "width": image["width"],
        "height": image["height"],
        "byteSize": image["byteSize"],
        "nonBackgroundRatio": round(non_background / sampled, 5),
        "darkPixelRatio": round(dark / sampled, 5),
    }


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_rendered_example(name, out_dir):
    html_path = out_dir / "diagram.html"
    png_path = out_dir / f"{name}.png"
    review_path = out_dir / "diagram.review.json"
    review = load_json(review_path)
    html = html_path.read_text(encoding="utf-8")
    stats = png_visual_stats(png_path)
    failures = []
    if not review.get("ok") or review.get("warningCount") != 0:
        failures.append("review is not clean")
    if stats["byteSize"] < MIN_PNG_BYTES:
        failures.append("PNG is unexpectedly small")
    if stats["width"] < 900 or stats["height"] < 450:
        failures.append("PNG dimensions are too small")
    if stats["nonBackgroundRatio"] < MIN_NON_BACKGROUND_RATIO:
        failures.append("PNG appears blank")
    if stats["darkPixelRatio"] < MIN_DARK_PIXEL_RATIO:
        failures.append("PNG has too little visible ink")
    if "shape-legend" in html and "legend-symbol-" not in html:
        failures.append("shape legend is missing symbol previews")
    return {
        "name": name,
        "ok": not failures,
        "failures": failures,
        "review": {
            "ok": review.get("ok"),
            "score": review.get("score"),
            "warningCount": review.get("warningCount"),
        },
        "png": stats,
        "hasShapeLegend": "shape-legend" in html,
    }


def check_example_artifacts(name, examples_dir):
    html_path = examples_dir / f"{name}.html"
    png_path = examples_dir / f"{name}.png"
    review_path = examples_dir / f"{name}.review.json"
    failures = []
    for path in [html_path, png_path, review_path]:
        if not path.exists():
            failures.append(f"missing {path.name}")
    if failures:
        return {"name": name, "ok": False, "failures": failures, "review": {}, "png": {}, "hasShapeLegend": False}

    review = load_json(review_path)
    html = html_path.read_text(encoding="utf-8")
    stats = png_visual_stats(png_path)
    if not review.get("ok") or review.get("warningCount") != 0:
        failures.append("review is not clean")
    if stats["byteSize"] < MIN_PNG_BYTES:
        failures.append("PNG is unexpectedly small")
    if stats["width"] < 900 or stats["height"] < 450:
        failures.append("PNG dimensions are too small")
    if stats["nonBackgroundRatio"] < MIN_NON_BACKGROUND_RATIO:
        failures.append("PNG appears blank")
    if stats["darkPixelRatio"] < MIN_DARK_PIXEL_RATIO:
        failures.append("PNG has too little visible ink")
    if "shape-legend" in html and "legend-symbol-" not in html:
        failures.append("shape legend is missing symbol previews")
    return {
        "name": name,
        "ok": not failures,
        "failures": failures,
        "review": {
            "ok": review.get("ok"),
            "score": review.get("score"),
            "warningCount": review.get("warningCount"),
        },
        "png": stats,
        "hasShapeLegend": "shape-legend" in html,
    }


def run_command(command, cwd, quiet=False):
    stdout = subprocess.DEVNULL if quiet else None
    subprocess.run(command, cwd=cwd, check=True, stdout=stdout)


def render_fixture(fixture, out_dir, skill_root, quiet=False):
    name = fixture.name.removesuffix(".def.json")
    target = out_dir / name
    target.mkdir(parents=True, exist_ok=True)
    compile_script = skill_root / "scripts" / "compile_diagram.py"
    render_script = skill_root / "scripts" / "render.py"
    run_command([sys.executable, str(compile_script), str(fixture), "--out-dir", str(target)], skill_root.parent.parent, quiet=quiet)
    run_command([sys.executable, str(render_script), str(target / "diagram.html"), str(target / f"{name}.png"), "--preset", "doc-wide", "--scale", "1", "--quiet"], skill_root.parent.parent, quiet=quiet)
    return target


def copy_example_artifacts(name, rendered_dir, examples_dir):
    examples_dir.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in [
        (f"{name}.png", f"{name}.png"),
        ("diagram.html", f"{name}.html"),
        ("diagram.review.json", f"{name}.review.json"),
    ]:
        shutil.copy2(rendered_dir / source_name, examples_dir / target_name)


def run_gate(skill_root, out_dir=None, update_examples=False, render=False, quiet=False):
    fixture_dir = skill_root / "fixtures" / "simple"
    examples_dir = skill_root / "examples" / "simple"
    fixtures = sorted(fixture_dir.glob("*.def.json"))
    owned_temp = None
    render = True
    if out_dir is None:
        owned_temp = tempfile.TemporaryDirectory(prefix="diagrammer-example-gate-")
        out_dir = Path(owned_temp.name)
    else:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    try:
        for fixture in fixtures:
            name = fixture.name.removesuffix(".def.json")
            rendered_dir = render_fixture(fixture, out_dir, skill_root, quiet=quiet)
            result = check_rendered_example(name, rendered_dir)
            results.append(result)
            if update_examples and result["ok"]:
                copy_example_artifacts(name, rendered_dir, examples_dir)
    finally:
        if owned_temp is not None:
            owned_temp.cleanup()

    return {
        "ok": all(result["ok"] for result in results),
        "count": len(results),
        "results": results,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render and visually gate bundled diagrammer fixtures")
    parser.add_argument("--out-dir", help="Directory for rendered temporary artifacts")
    parser.add_argument("--render", action="store_true", help="Deprecated; fixtures are always rendered before checking")
    parser.add_argument("--update-examples", action="store_true", help="Copy passing artifacts to examples/simple")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--quiet", action="store_true", help="Suppress compile/render progress output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    skill_root = Path(__file__).resolve().parents[1]
    report = run_gate(skill_root, Path(args.out_dir) if args.out_dir else None, update_examples=args.update_examples, render=args.render, quiet=args.quiet)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for result in report["results"]:
            status = "ok" if result["ok"] else "fail"
            print(f"{result['name']}: {status} review={result['review']['score']}/{result['review']['warningCount']} png={result['png']['width']}x{result['png']['height']} nonbg={result['png']['nonBackgroundRatio']}")
            for failure in result["failures"]:
                print(f"  - {failure}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
