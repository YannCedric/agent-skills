#!/usr/bin/env python3
"""Lightweight SVG/HTML diagram checks for common readability problems."""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


DEFAULT_FONT_SIZES = {
    "title": 38,
    "subtitle": 19,
    "boundary-title": 16,
    "step-title": 23,
    "step-note": 16,
    "arrow-label": 15,
    "status-title": 22,
    "footer": 15,
    "small": 14,
    "micro": 12,
    "label": 19,
}


class DiagramParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.groups = []
        self.current_text = None
        self.texts = []
        self.shapes = []
        self.styles = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = {"tag": tag, "attrs": attrs, "children": []}
        if self.stack:
            self.stack[-1]["children"].append(node)
        if tag == "g":
            self.groups.append(node)
        if tag in {"rect", "circle", "ellipse", "polygon", "path"}:
            self.shapes.append(node)
        if tag == "text":
            self.current_text = {"attrs": attrs, "content": ""}
        if tag == "style":
            self.current_text = {"attrs": {"data-style": "true"}, "content": ""}
        self.stack.append(node)

    def handle_endtag(self, tag):
        if tag == "text" and self.current_text and "data-style" not in self.current_text["attrs"]:
            self.texts.append(self.current_text)
            self.current_text = None
        if tag == "style" and self.current_text and "data-style" in self.current_text["attrs"]:
            self.styles += self.current_text["content"]
            self.current_text = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.current_text is not None:
            self.current_text["content"] += data


def as_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def class_font_sizes(styles):
    sizes = dict(DEFAULT_FONT_SIZES)
    for selector, size in re.findall(r"\.([a-zA-Z0-9_-]+)\s*\{[^}]*font-size:\s*(\d+(?:\.\d+)?)px", styles):
        sizes[selector] = float(size)
    return sizes


def text_size(text, attrs, sizes):
    classes = attrs.get("class", "").split()
    font_size = max([sizes.get(name, 16) for name in classes] or [16])
    # Conservative approximation for sans-serif uppercase/lowercase mix.
    width = len(text.strip()) * font_size * 0.58
    height = font_size * 1.25
    return width, height, font_size


def first_rect(group):
    for child in group["children"]:
        if child["tag"] == "rect":
            return child["attrs"]
    return None


def group_texts(group):
    return [child for child in group["children"] if child["tag"] == "text"]


def group_rect(group):
    rect = first_rect(group)
    if not rect:
        return None
    return {
        "x": as_float(rect.get("x")),
        "y": as_float(rect.get("y")),
        "width": as_float(rect.get("width")),
        "height": as_float(rect.get("height")),
        "rx": as_float(rect.get("rx")),
    }


def check_label_fit(groups, sizes, padding):
    warnings = []
    for group in groups:
        if "connector-label" in group["attrs"].get("class", "").split():
            continue
        rect = first_rect(group)
        if not rect:
            continue
        rx = as_float(rect.get("x"))
        rw = as_float(rect.get("width"))
        if rw <= 0:
            continue
        usable = max(rw - padding * 2, 1)
        for text_node in group_texts(group):
            label = "".join(
                child.get("attrs", {}).get("data", "") for child in text_node.get("children", [])
            )
            # Parser stores text content globally, so recover by matching attrs later.
            label = text_node["attrs"].get("_content", label)
            if not label:
                continue
            tw, _, font_size = text_size(label, text_node["attrs"], sizes)
            if tw > usable:
                warnings.append(
                    f"label may overflow {rw:.0f}px box: {label!r} needs ~{tw:.0f}px at {font_size:.0f}px"
                )
    return warnings


def attach_text_content(parser):
    by_key = {}
    for item in parser.texts:
        key = tuple(sorted(item["attrs"].items()))
        by_key.setdefault(key, []).append(item["content"].strip())

    def walk(node):
        if node["tag"] == "text":
            key = tuple(sorted(node["attrs"].items()))
            values = by_key.get(key)
            if values:
                node["attrs"]["_content"] = values.pop(0)
        for child in node["children"]:
            walk(child)

    for group in parser.groups:
        walk(group)


def check_style(parser, source, sizes, min_label_size):
    warnings = []
    colors = set()
    for shape in parser.shapes:
        for attr in ("fill", "stroke"):
            value = shape["attrs"].get(attr)
            if value and not value.startswith("var(") and value not in {"none", "transparent"}:
                colors.add(value.lower())
    if len(colors) > 6:
        warnings.append(f"many direct colors used ({len(colors)}); prefer tokens and restrained semantics")

    shape_tags = {shape["tag"] for shape in parser.shapes}
    shape_tags.discard("path")
    max_shape_families = 4 if "system-symbol" in source else 2
    if len(shape_tags) > max_shape_families:
        warnings.append(f"many shape families used ({', '.join(sorted(shape_tags))}); default should be rectangles plus simple system symbols")

    if re.search(r"\bfilter\s*=", source):
        warnings.append("filters/shadows detected; avoid decorative shadows by default")

    for text in parser.texts:
        classes = text["attrs"].get("class", "").split()
        if any(name in {"step-title", "label", "status-title"} for name in classes):
            _, _, font_size = text_size(text["content"], text["attrs"], sizes)
            if font_size < min_label_size:
                warnings.append(f"primary label below {min_label_size}px: {text['content']!r} is {font_size:.0f}px")
    return warnings


def check_connectors(source):
    warnings = []
    path_tags = re.findall(r"<path\b[^>]*>", source)
    connector_tags = []
    for tag in path_tags:
        attrs = dict(re.findall(r'([a-zA-Z:-]+)="([^"]+)"', tag))
        classes = attrs.get("class", "").split()
        if "marker-end=" in tag or "connector" in classes or any("flow" in name for name in classes):
            connector_tags.append(tag)
    class_strokes = {}
    for class_name, body in re.findall(r"\.([a-zA-Z0-9_-]+)\s*\{([^}]*)\}", source):
        stroke_match = re.search(r"stroke-width:\s*(\d+(?:\.\d+)?)(?:px)?", body)
        if stroke_match:
            class_strokes[class_name] = as_float(stroke_match.group(1))

    for tag in connector_tags:
        attrs = dict(re.findall(r'([a-zA-Z:-]+)="([^"]+)"', tag))
        classes = attrs.get("class", "").split()
        is_connector_class = "connector" in classes
        d_match = re.search(r'\bd="([^"]+)"', tag)
        path_data = d_match.group(1) if d_match else ""
        if re.search(r"\b[CS]\b", path_data):
            warnings.append("connector uses freeform cubic/smooth curves; prefer H/V/L with Q rounded 90-degree elbows")
        if "stroke-linecap=" not in tag and not is_connector_class:
            warnings.append("connector should use round line caps")
        if "stroke-linejoin=" not in tag and not is_connector_class:
            warnings.append("connector should use round joins")
        command_count = len(re.findall(r"[MLHVQCSATZ]", path_data))
        if command_count > 9:
            warnings.append("connector route has many path commands; simplify or split the flow instead of forcing a long route")
        if looks_like_return_route(path_data):
            warnings.append("connector appears to use a long visual return route; split/linearize the flow or add a separate frame")

        stroke_width = as_float(attrs.get("stroke-width"), 0)
        if not stroke_width:
            stroke_width = max([class_strokes.get(name, 0) for name in classes] or [0])
        is_exception = any(re.search(r"(exception|warn|error|fail|reopen|retry)", name) for name in classes)
        if stroke_width > 3.5:
            if is_exception:
                warnings.append("exception/warning connector stroke is heavy; keep exception paths around 2.5-3px")
            else:
                warnings.append("connector stroke is heavy for an ordinary diagram; keep paths around 2.5-3px")

    marker_defs = re.findall(r"<marker\b[^>]*id=\"([^\"]*arrow[^\"]*)\"[^>]*>(.*?)</marker>", source, re.S)
    for marker_id, body in marker_defs:
        marker_tag = re.search(rf"<marker\b[^>]*id=\"{re.escape(marker_id)}\"[^>]*>", source)
        tag = marker_tag.group(0) if marker_tag else ""
        width_match = re.search(r'markerWidth="([^"]+)"', tag)
        height_match = re.search(r'markerHeight="([^"]+)"', tag)
        width = as_float(width_match.group(1), 0) if width_match else 0
        height = as_float(height_match.group(1), 0) if height_match else 0
        if width >= 12 or height >= 12:
            warnings.append(f"arrow marker {marker_id!r} is large; use compact FigJam-like arrow tips")
        if "<path" not in body:
            warnings.append(f"arrow marker {marker_id!r} should use a simple path tip")
        elif "Z" not in body and 'fill="none"' not in body:
            warnings.append(f"arrow marker {marker_id!r} should be a filled triangle or open chevron tip")

    return warnings


def looks_like_return_route(path_data):
    if len(re.findall(r"[MLHVQCSATZ]", path_data)) < 5:
        return False
    tokens = re.findall(r"([MLHVQCSATZ])\s*([^MLHVQCSATZ]*)", path_data)
    x = y = None
    last_h = None
    horizontal_reversal = False
    vertical_reversal = False
    has_long_horizontal = False
    for command, values in tokens:
        numbers = [as_float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", values)]
        if command == "M" and len(numbers) >= 2:
            x, y = numbers[-2], numbers[-1]
        elif command == "H" and numbers and x is not None:
            new_x = numbers[-1]
            if abs(new_x - x) > 260:
                has_long_horizontal = True
                if last_h and (new_x - x) * last_h < 0:
                    horizontal_reversal = True
                last_h = 1 if new_x > x else -1
            x = new_x
        elif command == "V" and numbers and y is not None:
            new_y = numbers[-1]
            if abs(new_y - y) > 120:
                vertical_reversal = True
            y = new_y
        elif command == "L" and len(numbers) >= 2:
            x, y = numbers[-2], numbers[-1]
        elif command == "Q" and len(numbers) >= 4:
            x, y = numbers[-2], numbers[-1]
    bend_count = sum(1 for command, _values in tokens if command in {"H", "V", "Q"})
    q_count = sum(1 for command, _values in tokens if command == "Q")
    long_horizontal = has_long_horizontal and bend_count >= 4
    multi_bend_return = bool(long_horizontal) and q_count >= 2
    return horizontal_reversal or (vertical_reversal and bool(long_horizontal)) or multi_bend_return


def check_connector_labels(source):
    warnings = []
    raw_label_classes = ("flow-label", "arrow-label")
    for class_name in raw_label_classes:
        if re.search(rf'class="[^"]*\b{class_name}\b', source):
            warnings.append(f"raw {class_name} text detected; use connector-label groups with a measured text gap")
    for class_value in re.findall(r'class="([^"]*)"', source):
        if "label-mask" in class_value.split():
            warnings.append("ad hoc label-mask detected; use connector-label-mask inside a connector-label group")
            break

    label_groups = re.findall(r'<g\b[^>]*class="[^"]*\bconnector-label\b[^"]*"[^>]*>(.*?)</g>', source, re.S)
    for group in label_groups:
        if "<text" not in group:
            warnings.append("connector-label group should include visible label text")
    label_count = len(label_groups)
    mask_count = len(re.findall(r'class="[^"]*\bconnector-label-mask\b', source))
    if label_count and mask_count < label_count:
        warnings.append("connector labels should include a measured canvas mask so the connector breaks around text")

    return warnings


def check_footer_notes(source):
    warnings = []
    if "annotation-block" in source:
        return warnings

    footer_texts = re.findall(r'<text\b[^>]*class="[^"]*\b(?:footer|note|note-title)\b[^"]*"[^>]*>(.*?)</text>', source, re.S)
    cleaned = [re.sub(r"<[^>]+>", "", item).strip() for item in footer_texts]
    long_lines = [item for item in cleaned if len(item) > 92]
    if len(cleaned) >= 3 or long_lines:
        warnings.append("footer notes read as long prose; group short bullets as compact annotation-block elements")
    return warnings


def check_connector_label_spacing(source):
    warnings = []
    groups = re.findall(r'<rect\b[^>]*class="[^"]*\bconnector-label-mask\b[^"]*"[^>]*>', source, re.S)
    boxes = []
    for tag in groups:
        attrs = dict(re.findall(r'([a-zA-Z:-]+)="([^"]+)"', tag))
        boxes.append(
            {
                "x": as_float(attrs.get("x")),
                "y": as_float(attrs.get("y")),
                "width": as_float(attrs.get("width")),
                "height": as_float(attrs.get("height")),
            }
        )

    for i, left in enumerate(boxes):
        for right in boxes[i + 1 :]:
            overlap_x = min(left["x"] + left["width"], right["x"] + right["width"]) - max(left["x"], right["x"])
            overlap_y = min(left["y"] + left["height"], right["y"] + right["height"]) - max(left["y"], right["y"])
            if overlap_x > 4 and overlap_y > 4:
                warnings.append("connector label chips are overlapping or too close; remove redundant labels or reroute")
                return warnings
    return warnings


def check_layout_classes(parser):
    warnings = []

    def class_groups(name):
        return [group for group in parser.groups if name in group["attrs"].get("class", "").split()]

    for class_name in ("flow-step", "flow-outcome"):
        rects = [group_rect(group) for group in class_groups(class_name)]
        rects = [rect for rect in rects if rect]
        if len(rects) < 2:
            continue
        y_values = [rect["y"] for rect in rects]
        h_values = [rect["height"] for rect in rects]
        if max(y_values) - min(y_values) > 4:
            warnings.append(f"{class_name} nodes are not row-aligned")
        if max(h_values) - min(h_values) > 4:
            warnings.append(f"{class_name} nodes do not have consistent heights")
        if any(rect["rx"] < 10 for rect in rects):
            warnings.append(f"{class_name} nodes should use FigJam-like rounded corners")

    return warnings


def check_system_symbols(source):
    warnings = []

    data_store_groups = re.findall(
        r'<g\b[^>]*class="[^"]*\bdata-store\b[^"]*"[^>]*>(.*?)</g>', source, re.S
    )
    for group in data_store_groups:
        has_cylinder_body = "<rect" in group or group.count("<path") >= 2
        has_top_ellipse = group.count("<ellipse") >= 1
        has_bottom_arc = group.count("<ellipse") >= 2 or re.search(r"<path\b[^>]*\bC\b", group)
        if not (has_cylinder_body and has_top_ellipse and has_bottom_arc):
            warnings.append("data-store should render as a standalone cylinder with a top ellipse and visible front bottom arc")
        if 'class="schema"' not in group:
            warnings.append("data-store cylinder should include visible schema/status rows when detail is known")

    queue_groups = re.findall(
        r'<g\b[^>]*class="[^"]*\bqueue-node\b[^"]*"[^>]*>(.*?)</g>', source, re.S
    )
    for group in queue_groups:
        rect_match = re.search(r"<rect\b([^>]*)>", group)
        path_match = re.search(r"<path\b([^>]*)>", group)
        if not rect_match and not path_match:
            warnings.append("queue-node should be a standalone horizontal cylinder, not text-only or card-only")
            continue
        if rect_match:
            attrs = dict(re.findall(r'([a-zA-Z:-]+)="([^"]+)"', rect_match.group(1)))
            width = as_float(attrs.get("width"))
            height = as_float(attrs.get("height"))
            rx = as_float(attrs.get("rx"))
            if width <= height * 1.8:
                warnings.append("queue-node should read as a horizontal cylinder/buffer, wider than tall")
            if rx < height * 0.4:
                warnings.append("queue-node should use pill/cylinder rounding, not a standard service-card corner")
        elif not re.search(r"\bC\b", path_match.group(1)):
            warnings.append("queue-node path should use curved end caps")
        if group.count("<ellipse") < 1:
            warnings.append("queue-node should include an end ellipse to distinguish it from a card")

    annotation_groups = re.findall(
        r'<g\b[^>]*class="[^"]*\bannotation-block\b[^"]*"[^>]*>(.*?)</g>', source, re.S
    )
    for group in annotation_groups:
        if "<rect" in group:
            warnings.append("annotation-block should stay open-canvas by default; avoid card boxes unless boundary ownership matters")
        if group.count("<text") < 2:
            warnings.append("annotation-block should include a title and at least one annotation line")

    if 'class="annotation"' in source and "annotation-block" not in source:
        warnings.append("raw annotation text detected; group notes as first-class annotation-block elements")

    return warnings


def main():
    parser = argparse.ArgumentParser(description="Validate common SVG diagram readability issues")
    parser.add_argument("html", help="HTML/SVG file to inspect")
    parser.add_argument("--padding", type=int, default=18, help="Minimum horizontal label padding inside nodes")
    parser.add_argument("--min-label-size", type=int, default=20, help="Minimum primary label font size")
    args = parser.parse_args()

    source = Path(args.html).read_text(encoding="utf-8")
    parsed = DiagramParser()
    parsed.feed(source)
    attach_text_content(parsed)
    sizes = class_font_sizes(parsed.styles)

    warnings = []
    warnings.extend(check_label_fit(parsed.groups, sizes, args.padding))
    warnings.extend(check_style(parsed, source, sizes, args.min_label_size))
    warnings.extend(check_connectors(source))
    warnings.extend(check_connector_labels(source))
    warnings.extend(check_footer_notes(source))
    warnings.extend(check_connector_label_spacing(source))
    warnings.extend(check_layout_classes(parsed))
    warnings.extend(check_system_symbols(source))

    if warnings:
        for warning in warnings:
            print(f"WARN: {warning}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {args.html}")


if __name__ == "__main__":
    main()
