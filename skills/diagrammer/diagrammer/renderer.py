"""SVG/HTML rendering helpers for diagrammer layouts."""

import html

try:
    from . import shapes
    from .metrics import (
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_PAD_Y,
        HEIGHT,
        PAD_X,
        WIDTH,
        wrap_label,
        wrap_text_to_width,
    )
except ImportError:  # pragma: no cover - script execution fallback
    import shapes
    from metrics import (  # type: ignore
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_PAD_Y,
        HEIGHT,
        PAD_X,
        WIDTH,
        wrap_label,
        wrap_text_to_width,
    )


def shape_text_area(box):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    shape = box.get("shape") or shapes.resolve_node_shape(box)
    if shape == "cloud":
        return {"x": x + w * 0.16, "y": y + h * 0.26, "width": w * 0.68, "height": h * 0.58}
    if shape == "shield":
        return {"x": x + w * 0.21, "y": y + h * 0.22, "width": w * 0.58, "height": h * 0.62}
    if shape == "diamond":
        return {"x": x + w * 0.23, "y": y + h * 0.25, "width": w * 0.54, "height": h * 0.46}
    if shape == "user":
        return {"x": x + 76, "y": y + 14, "width": max(80, w - 92), "height": max(40, h - 18)}
    if shape == "document":
        return {"x": x + 24, "y": y + 22, "width": max(86, w - 54), "height": max(42, h - 38)}
    if shape == "horizontal-cylinder":
        layout = queue_text_layout(box)
        return {"x": layout["textX"] - layout["textWidth"] / 2, "y": y + 18, "width": layout["textWidth"], "height": max(40, h - 22)}
    if shape == "database-cylinder":
        return {"x": x + PAD_X, "y": y + 84, "width": max(86, w - PAD_X * 2), "height": max(56, h - 106)}
    return {"x": x + PAD_X, "y": y + 22, "width": max(80, w - PAD_X * 2), "height": max(40, h - 32)}


def text_stack_layout(box):
    area = shape_text_area(box)
    label_lines = box.get("labelLines") or wrap_label(box.get("label", ""))
    detail_lines = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    label_line_h = 22
    detail_line_h = 22
    gap = 8 if detail_lines else 0
    ascent = 16
    descent = 5
    block_h = len(label_lines) * label_line_h + gap + len(detail_lines) * detail_line_h
    start_y = area["y"] + max(0, (area["height"] - block_h) / 2)
    first_label_y = start_y + ascent
    label_baselines = [first_label_y + index * label_line_h for index, _line in enumerate(label_lines)]
    first_detail_y = first_label_y + len(label_lines) * label_line_h + gap
    detail_baselines = [first_detail_y + index * detail_line_h for index, _line in enumerate(detail_lines)]
    baselines = label_baselines + detail_baselines
    text_top = first_label_y - ascent if baselines else start_y
    text_bottom = (baselines[-1] + descent) if baselines else area["y"]
    return {
        "area": area,
        "labelLines": label_lines,
        "detailLines": detail_lines,
        "labelBaselines": label_baselines,
        "detailBaselines": detail_baselines,
        "textBounds": {"x": area["x"], "y": text_top, "width": area["width"], "height": text_bottom - text_top},
        "blockHeight": block_h,
    }


def esc(value):
    return html.escape(str(value), quote=True)


def text_lines(lines, x, y, class_name, anchor="middle", line_height=22):
    out = []
    for i, line in enumerate(lines):
        out.append(f'<text class="{class_name}" x="{x:.1f}" y="{y + i * line_height:.1f}" text-anchor="{anchor}">{esc(line)}</text>')
    return "\n".join(out)


def render_service(box, classes="service-node"):
    label = box.get("labelLines") or wrap_label(box["label"])
    detail = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    content = [f'<g class="{classes}" data-node="{esc(box["id"])}">']
    content.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="var(--node)" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(text_lines(label, x + w / 2, y + 34, "label"))
    dy = y + 34 + len(label) * 24 + 8
    for line in detail:
        content.append(f'<text class="small" x="{x + w / 2:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 22
    content.append("</g>")
    return "\n".join(content)


def render_client(box):
    return render_service(box, "service-node client-node")


def render_user(box):
    label = box.get("labelLines") or wrap_label(box["label"])
    detail = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    icon_cx = x + 38
    icon_cy = y + h / 2 - 3
    text_x = x + w / 2 + 16
    content = [f'<g class="user-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="var(--node)" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(f'<circle cx="{icon_cx:.1f}" cy="{icon_cy - 10:.1f}" r="9" fill="none" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(f'<path d="M {icon_cx - 18:.1f} {icon_cy + 22:.1f} C {icon_cx - 12:.1f} {icon_cy + 4:.1f} {icon_cx + 12:.1f} {icon_cy + 4:.1f} {icon_cx + 18:.1f} {icon_cy + 22:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2" stroke-linecap="round"/>')
    content.append(text_lines(label, text_x, y + 34, "label"))
    dy = y + 34 + len(label) * 24 + 8
    for line in detail:
        content.append(f'<text class="small" x="{text_x:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 22
    content.append("</g>")
    return "\n".join(content)


def render_cloud(box):
    stack = text_stack_layout(box)
    label = stack["labelLines"]
    detail = stack["detailLines"]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    left = x + w * 0.08
    right = x + w * 0.92
    top = y + h * 0.18
    bottom = y + h * 0.92
    path = (
        f"M {left:.1f} {bottom:.1f} "
        f"C {x + w * 0.00:.1f} {bottom:.1f} {x + w * 0.00:.1f} {top + h * 0.22:.1f} {x + w * 0.20:.1f} {top + h * 0.20:.1f} "
        f"C {x + w * 0.22:.1f} {y + h * 0.04:.1f} {x + w * 0.46:.1f} {y + h * 0.02:.1f} {x + w * 0.54:.1f} {top:.1f} "
        f"C {x + w * 0.72:.1f} {top - h * 0.10:.1f} {x + w * 0.90:.1f} {top + h * 0.10:.1f} {x + w * 0.84:.1f} {top + h * 0.30:.1f} "
        f"C {x + w * 1.00:.1f} {top + h * 0.30:.1f} {x + w * 1.00:.1f} {bottom:.1f} {right:.1f} {bottom:.1f} Z"
    )
    content = [f'<g class="cloud-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<path d="{path}" fill="var(--node)" stroke="var(--stroke)" stroke-width="2" stroke-linejoin="round"/>')
    for line, baseline in zip(label, stack["labelBaselines"]):
        content.append(f'<text class="label" x="{x + w / 2:.1f}" y="{baseline:.1f}" text-anchor="middle">{esc(line)}</text>')
    for line, baseline in zip(detail, stack["detailBaselines"]):
        content.append(f'<text class="small" x="{x + w / 2:.1f}" y="{baseline:.1f}" text-anchor="middle">{esc(line)}</text>')
    content.append("</g>")
    return "\n".join(content)


def render_document(box):
    label = box.get("labelLines") or wrap_label(box["label"])
    detail = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    fold = min(28, w * 0.18)
    content = [f'<g class="document-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<path d="M {x:.1f} {y:.1f} H {x + w - fold:.1f} L {x + w:.1f} {y + fold:.1f} V {y + h:.1f} H {x:.1f} Z" fill="var(--node)" stroke="var(--stroke)" stroke-width="2" stroke-linejoin="round"/>')
    content.append(f'<path d="M {x + w - fold:.1f} {y:.1f} V {y + fold:.1f} H {x + w:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(text_lines(label, x + w / 2, y + 38, "label"))
    dy = y + 34 + len(label) * 24 + 8
    for line in detail:
        content.append(f'<text class="small" x="{x + w / 2:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 22
    content.append("</g>")
    return "\n".join(content)


def render_diamond(box):
    label = box.get("labelLines") or wrap_label(box["label"])
    detail = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    points = f"{x + w / 2:.1f},{y:.1f} {x + w:.1f},{y + h / 2:.1f} {x + w / 2:.1f},{y + h:.1f} {x:.1f},{y + h / 2:.1f}"
    content = [f'<g class="diamond-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<polygon points="{points}" fill="var(--node)" stroke="var(--stroke)" stroke-width="2" stroke-linejoin="round"/>')
    content.append(text_lines(label, x + w / 2, y + h / 2 - 4, "label", line_height=20))
    dy = y + h / 2 + len(label) * 20 + 10
    for line in detail[:2]:
        content.append(f'<text class="small" x="{x + w / 2:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 20
    content.append("</g>")
    return "\n".join(content)


def render_shield(box):
    label = box.get("labelLines") or wrap_label(box["label"])
    detail = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    path = (
        f"M {x + w / 2:.1f} {y:.1f} L {x + w * 0.88:.1f} {y + h * 0.16:.1f} "
        f"V {y + h * 0.46:.1f} C {x + w * 0.86:.1f} {y + h * 0.70:.1f} {x + w * 0.66:.1f} {y + h * 0.88:.1f} {x + w / 2:.1f} {y + h:.1f} "
        f"C {x + w * 0.34:.1f} {y + h * 0.88:.1f} {x + w * 0.14:.1f} {y + h * 0.70:.1f} {x + w * 0.12:.1f} {y + h * 0.46:.1f} "
        f"V {y + h * 0.16:.1f} Z"
    )
    content = [f'<g class="shield-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<path d="{path}" fill="var(--node)" stroke="var(--stroke)" stroke-width="2" stroke-linejoin="round"/>')
    content.append(text_lines(label, x + w / 2, y + 38, "label", line_height=20))
    dy = y + 36 + len(label) * 22 + 8
    for line in detail[:2]:
        content.append(f'<text class="small" x="{x + w / 2:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 20
    content.append("</g>")
    return "\n".join(content)


def render_db(box):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    ey = min(82, max(58, h * 0.32))
    rx = w / 2
    ry = ey / 2
    cx = x + rx
    k = 0.5522847498
    top_cy = y + ey / 2
    bottom_cy = y + h - ey / 2
    bottom_arc = (
        f"C {x:.1f} {bottom_cy + k * ry:.1f} {cx - k * rx:.1f} {bottom_cy + ry:.1f} {cx:.1f} {bottom_cy + ry:.1f} "
        f"C {cx + k * rx:.1f} {bottom_cy + ry:.1f} {x + w:.1f} {bottom_cy + k * ry:.1f} {x + w:.1f} {bottom_cy:.1f}"
    )
    bottom_arc_reverse = (
        f"C {x + w:.1f} {bottom_cy + k * ry:.1f} {cx + k * rx:.1f} {bottom_cy + ry:.1f} {cx:.1f} {bottom_cy + ry:.1f} "
        f"C {cx - k * rx:.1f} {bottom_cy + ry:.1f} {x:.1f} {bottom_cy + k * ry:.1f} {x:.1f} {bottom_cy:.1f}"
    )
    content = [f'<g class="data-store system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<path d="M {x:.1f} {top_cy:.1f} C {x:.1f} {y:.1f} {x + w:.1f} {y:.1f} {x + w:.1f} {top_cy:.1f} L {x + w:.1f} {bottom_cy:.1f} {bottom_arc_reverse} Z" fill="var(--node)" stroke="none"/>')
    content.append(f'<ellipse cx="{cx:.1f}" cy="{top_cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(f'<path d="M {x:.1f} {top_cy:.1f} V {bottom_cy:.1f} {bottom_arc} V {top_cy:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2" stroke-linejoin="round"/>')
    content.append(text_lines(box.get("labelLines") or wrap_label(box["label"]), x + w / 2, y + 104, "label"))
    dy = y + 142
    details = box.get("detailLines") or box.get("detail", []) or ["source of truth"]
    for line in details[:5]:
        content.append(f'<text class="schema" x="{x + w / 2:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 20
    content.append("</g>")
    return "\n".join(content)


def queue_text_layout(box):
    x, w, h = box["x"], box["width"], box["height"]
    cap_rx = h * 0.24
    cap_cx = x + w - cap_rx
    cap_left = cap_cx - cap_rx
    text_x = x + w / 2 - cap_rx * 0.35
    text_right = cap_left + 4
    text_width_available = max(80, min(cap_cx - x - 36, (text_right - text_x) * 2))
    label_lines = wrap_text_to_width(box["label"], text_width_available, CHAR_W, max_lines=3)
    detail_lines = [
        wrapped
        for detail_line in box.get("detail", [])
        for wrapped in wrap_text_to_width(detail_line, text_width_available, DETAIL_CHAR_W, max_lines=2)
    ]
    return {
        "textX": text_x,
        "textWidth": text_width_available,
        "labelLines": label_lines,
        "detailLines": detail_lines,
        "capLeft": cap_left,
    }


def render_queue(box):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    cap_rx = h * 0.24
    cap_cx = x + w - cap_rx
    left = x + h / 2
    text_layout = queue_text_layout(box)
    text_x = text_layout["textX"]
    label_lines = text_layout["labelLines"]
    detail_lines = text_layout["detailLines"]
    content = [f'<g class="queue-node system-symbol" data-node="{esc(box["id"])}">']
    content.append(f'<path d="M {left:.1f} {y:.1f} H {cap_cx:.1f} V {y + h:.1f} H {left:.1f} C {x:.1f} {y + h:.1f} {x:.1f} {y:.1f} {left:.1f} {y:.1f} Z" fill="var(--node)" stroke="none"/>')
    content.append(f'<path d="M {cap_cx:.1f} {y:.1f} H {left:.1f} C {x:.1f} {y:.1f} {x:.1f} {y + h:.1f} {left:.1f} {y + h:.1f} H {cap_cx:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(f'<ellipse cx="{cap_cx:.1f}" cy="{y + h / 2:.1f}" rx="{cap_rx:.1f}" ry="{h / 2:.1f}" fill="none" stroke="var(--stroke)" stroke-width="2"/>')
    content.append(text_lines(label_lines, text_x, y + 30, "label", line_height=20))
    dy = y + 58 + max(0, len(label_lines) - 1) * 14
    for line in detail_lines[:3]:
        content.append(f'<text class="small" x="{text_x:.1f}" y="{dy:.1f}" text-anchor="middle">{esc(line)}</text>')
        dy += 22
    content.append("</g>")
    return "\n".join(content)


def render_annotation(item):
    out = [f'<g class="annotation-block" data-annotation="{esc(item["id"])}">']
    out.append(f'<text class="annotation-title" x="{item["x"]:.1f}" y="{item["y"]:.1f}">{esc(item["title"])}</text>')
    y = item["y"] + 28
    for line in item.get("lines", []):
        out.append(f'<text class="small" x="{item["x"]:.1f}" y="{y:.1f}">{esc(line)}</text>')
        y += 22
    out.append("</g>")
    return "\n".join(out)


LEGEND_SHAPES = {"cloud", "user", "document", "diamond", "shield"}


def shape_legend_items(layout):
    used = []
    for box in layout["boxes"].values():
        shape = box.get("shape") or shapes.resolve_node_shape(box)
        if shape != "rounded-rectangle" and shape not in used:
            used.append(shape)
    if not used:
        return []
    if not any(shape in LEGEND_SHAPES for shape in used) and len(used) < 3:
        return []
    return [{"shape": shape, "label": shapes.shape_spec(shape).label, "description": shapes.shape_spec(shape).description} for shape in used]


def legend_item_summary(item):
    shape = item["shape"]
    return {
        "cloud": "external provider / cloud system",
        "shield": "risk, auth, or security boundary",
        "diamond": "decision or approval point",
        "document": "file or document artifact",
        "user": "human actor",
        "horizontal-cylinder": "queue, stream, or buffer",
        "database-cylinder": "database or source of truth",
    }.get(shape, item["description"])


def shape_legend_size(items):
    visible = items[:5]
    max_chars = max([len(legend_item_summary(item)) for item in visible] + [6])
    symbol_and_gap = 72
    horizontal_padding = 48
    title_width = len("Legend") * 12
    row_width = symbol_and_gap + max_chars * 7.6
    width = max(220, min(760, horizontal_padding + max(title_width, row_width)))
    height = 84 + max(0, len(visible) - 1) * 28
    return width, height


def render_legend_symbol(shape, cx, cy):
    w = 34
    h = 22
    x = cx - w / 2
    y = cy - h / 2
    if shape == "user":
        return (
            f'<g class="legend-symbol legend-symbol-user"><circle cx="{cx:.1f}" cy="{cy - 6:.1f}" r="4.5"/>'
            f'<path d="M {cx - 9:.1f} {cy + 8:.1f} C {cx - 6:.1f} {cy:.1f} {cx + 6:.1f} {cy:.1f} {cx + 9:.1f} {cy + 8:.1f}"/></g>'
        )
    if shape == "document":
        fold = 7
        return (
            f'<g class="legend-symbol legend-symbol-document"><path d="M {x:.1f} {y:.1f} H {x + w - fold:.1f} L {x + w:.1f} {y + fold:.1f} V {y + h:.1f} H {x:.1f} Z"/>'
            f'<path d="M {x + w - fold:.1f} {y:.1f} V {y + fold:.1f} H {x + w:.1f}"/></g>'
        )
    if shape == "shield":
        return (
            f'<path class="legend-symbol legend-symbol-shield" d="M {cx:.1f} {y:.1f} L {x + w * 0.86:.1f} {y + h * 0.18:.1f} '
            f'V {y + h * 0.46:.1f} C {x + w * 0.82:.1f} {y + h * 0.70:.1f} {x + w * 0.62:.1f} {y + h * 0.88:.1f} {cx:.1f} {y + h:.1f} '
            f'C {x + w * 0.38:.1f} {y + h * 0.88:.1f} {x + w * 0.18:.1f} {y + h * 0.70:.1f} {x + w * 0.14:.1f} {y + h * 0.46:.1f} '
            f'V {y + h * 0.18:.1f} Z"/>'
        )
    if shape == "diamond":
        return f'<polygon class="legend-symbol legend-symbol-diamond" points="{cx:.1f},{y:.1f} {x + w:.1f},{cy:.1f} {cx:.1f},{y + h:.1f} {x:.1f},{cy:.1f}"/>'
    if shape == "cloud":
        return (
            f'<path class="legend-symbol legend-symbol-cloud" d="M {x + 4:.1f} {y + h:.1f} '
            f'C {x - 1:.1f} {y + h:.1f} {x - 1:.1f} {y + 9:.1f} {x + 7:.1f} {y + 9:.1f} '
            f'C {x + 8:.1f} {y + 1:.1f} {x + 19:.1f} {y:.1f} {x + 22:.1f} {y + 6:.1f} '
            f'C {x + 31:.1f} {y + 4:.1f} {x + 36:.1f} {y + 14:.1f} {x + 31:.1f} {y + 16:.1f} '
            f'C {x + 38:.1f} {y + 16:.1f} {x + 38:.1f} {y + h:.1f} {x + w - 3:.1f} {y + h:.1f} Z"/>'
        )
    if shape == "horizontal-cylinder":
        rx = h * 0.24
        cap_cx = x + w - rx
        left = x + h / 2
        outline = (
            f"M {left:.1f} {y:.1f} H {cap_cx:.1f} "
            f"C {x + w:.1f} {y:.1f} {x + w:.1f} {y + h:.1f} {cap_cx:.1f} {y + h:.1f} "
            f"H {left:.1f} C {x:.1f} {y + h:.1f} {x:.1f} {y:.1f} {left:.1f} {y:.1f} Z"
        )
        return (
            f'<g class="legend-symbol legend-symbol-horizontal-cylinder"><path d="{outline}"/>'
            f'<ellipse cx="{cap_cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{h / 2:.1f}"/></g>'
        )
    if shape == "database-cylinder":
        top_cy = y + 6
        bottom_cy = y + h - 6
        return (
            f'<g class="legend-symbol legend-symbol-database-cylinder">'
            f'<path d="M {x:.1f} {top_cy:.1f} V {bottom_cy:.1f} '
            f'C {x:.1f} {y + h + 2:.1f} {x + w:.1f} {y + h + 2:.1f} {x + w:.1f} {bottom_cy:.1f} '
            f'V {top_cy:.1f} C {x + w:.1f} {y:.1f} {x:.1f} {y:.1f} {x:.1f} {top_cy:.1f} Z"/>'
            f'<ellipse cx="{cx:.1f}" cy="{top_cy:.1f}" rx="{w / 2:.1f}" ry="6"/>'
            f'</g>'
        )
    return f'<rect class="legend-symbol legend-symbol-rounded-rectangle" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5"/>'


def render_shape_legend(layout, svg_height=HEIGHT):
    items = shape_legend_items(layout)
    if not items:
        return ""
    legend_w, legend_h = shape_legend_size(items)
    x = 90
    canvas_h = layout.get("canvas", {}).get("height", HEIGHT)
    y = max(canvas_h + 24, svg_height - legend_h - 24)
    line_h = 28
    out = [f'<g class="shape-legend" data-legend="shapes">']
    out.append(f'<rect class="legend-panel" x="{x:.1f}" y="{y:.1f}" width="{legend_w:.1f}" height="{legend_h:.1f}" rx="8"/>')
    out.append(f'<text class="legend-title" x="{x + 24:.1f}" y="{y + 30:.1f}">Legend</text>')
    row_y = y + 62
    for item in items[:5]:
        shape = item["shape"]
        summary = legend_item_summary(item)
        out.append(render_legend_symbol(shape, x + 40, row_y - 8))
        out.append(f'<text class="legend-row" x="{x + 72:.1f}" y="{row_y:.1f}">{esc(summary)}</text>')
        row_y += line_h
    out.append("</g>")
    return "\n".join(out)


def render_edge(edge):
    kind = edge.get("kind", "sync")
    marker = "arrow-red" if kind in {"failure", "retry"} else "arrow"
    classes = ["connector", f"connector-{kind}"]
    dashed = ' stroke-dasharray="8 8"' if kind in {"async", "retry"} else ""
    return f'<path class="{" ".join(classes)}" d="{esc(edge["path"])}" fill="none" marker-end="url(#{marker})"{dashed}/>'


def render_edge_label_mask(edge):
    out = []
    box = edge.get("labelBox")
    if box:
        out.append(f'<rect class="connector-label-mask" data-edge="{esc(edge["id"])}" x="{box["x"]:.1f}" y="{box["y"]:.1f}" width="{box["width"]:.1f}" height="{box["height"]:.1f}" rx="2" fill="var(--canvas)" stroke="none"/>')
    return "\n".join(out)


def render_edge_label_text(edge):
    out = []
    box = edge.get("labelBox")
    if box:
        out.append(f'<g class="connector-label" data-edge="{esc(edge["id"])}">')
        lines = box.get("lines") or [box["label"]]
        text_x = box["x"] + box["width"] / 2
        first_y = box["y"] + EDGE_LABEL_PAD_Y + 11
        out.append(f'<text class="connector-label-text" x="{text_x:.1f}" y="{first_y:.1f}" text-anchor="middle">')
        for index, line in enumerate(lines):
            dy = 0 if index == 0 else EDGE_LABEL_LINE_H
            out.append(f'<tspan x="{text_x:.1f}" dy="{dy}">{esc(line)}</tspan>')
        out.append('</text>')
        out.append("</g>")
    return "\n".join(out)


def render_html(defn, layout, review):
    title = defn.get("title", "System diagram")
    subtitle = defn.get("subtitle", "")
    parts = []
    for edge in layout["edges"]:
        parts.append(render_edge(edge))
    for edge in layout["edges"]:
        parts.append(render_edge_label_mask(edge))
    for box in layout["boxes"].values():
        shape = box.get("shape") or shapes.resolve_node_shape(box)
        if shape == "database-cylinder":
            parts.append(render_db(box))
        elif shape == "horizontal-cylinder":
            parts.append(render_queue(box))
        elif shape == "user":
            parts.append(render_user(box))
        elif shape == "cloud":
            parts.append(render_cloud(box))
        elif shape == "document":
            parts.append(render_document(box))
        elif shape == "diamond":
            parts.append(render_diamond(box))
        elif shape == "shield":
            parts.append(render_shield(box))
        else:
            kind = box.get("kind", "service")
            parts.append(render_service(box, f"service-node {kind}-node"))
    for item in layout["annotations"]:
        parts.append(render_annotation(item))
    legend_items = shape_legend_items(layout)
    canvas = layout.get("canvas", {})
    canvas_w = canvas.get("width", WIDTH)
    canvas_h = canvas.get("height", HEIGHT)
    _, legend_h = shape_legend_size(legend_items) if legend_items else (0, 0)
    svg_height = canvas_h + legend_h + 58 if legend_items else canvas_h
    legend = render_shape_legend(layout, svg_height)
    if legend:
        parts.append(legend)
    for edge in layout["edges"]:
        parts.append(render_edge_label_text(edge))

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(title)}</title>
<style>
:root {{
  --canvas: #fbfaf6;
  --grid: rgba(45, 50, 57, 0.05);
  --ink: #23272f;
  --muted: #646b77;
  --stroke: #343a44;
  --connector: #68717d;
  --danger: #b83b3b;
  --node: #fffefb;
  --chip: #fbfaf6;
  --chip-stroke: #d9d5ca;
}}
html, body {{ margin: 0; background: var(--canvas); }}
body {{ font-family: Liberation Sans, Arial, Helvetica, sans-serif; color: var(--ink); }}
svg {{ display: block; width: 100vw; height: auto; background-color: var(--canvas); background-image: radial-gradient(var(--grid) 1px, transparent 1px); background-size: 28px 28px; }}
.title {{ font-size: 40px; font-weight: 700; fill: var(--ink); }}
.subtitle {{ font-size: 20px; fill: var(--muted); }}
.label {{ font-size: 20px; font-weight: 700; fill: var(--ink); }}
.small {{ font-size: 15px; fill: var(--muted); }}
.schema {{ font-size: 15px; fill: var(--muted); }}
.annotation-title {{ font-size: 21px; font-weight: 700; fill: var(--ink); }}
.legend-panel {{ fill: rgba(255, 254, 251, 0.94); stroke: var(--chip-stroke); stroke-width: 1.5; }}
.legend-title {{ font-size: 22px; font-weight: 700; fill: var(--ink); }}
.legend-row {{ font-size: 16px; fill: var(--muted); }}
.legend-symbol,
.legend-symbol path,
.legend-symbol ellipse,
.legend-symbol circle {{ fill: var(--node); stroke: var(--stroke); stroke-width: 1.7; stroke-linejoin: round; }}
.legend-symbol-user circle,
.legend-symbol-user path {{ fill: none; stroke: var(--stroke); stroke-linecap: round; }}
.legend-symbol-document path + path,
.legend-symbol-horizontal-cylinder ellipse,
.legend-symbol-database-cylinder ellipse {{ fill: none; }}
.connector {{ stroke: var(--connector); stroke-width: 2.8; stroke-linecap: butt; stroke-linejoin: round; }}
.connector-failure, .connector-retry {{ stroke: var(--danger); }}
.connector-label-text {{ font-size: 14px; font-weight: 700; fill: var(--ink); }}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {svg_height}" role="img" aria-label="{esc(title)}">
<defs>
  <marker id="arrow" markerWidth="20" markerHeight="14" refX="12" refY="7" orient="auto" markerUnits="userSpaceOnUse">
    <path d="M 2 2 L 17 7 L 2 12" fill="none" stroke="var(--connector)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
  <marker id="arrow-red" markerWidth="20" markerHeight="14" refX="12" refY="7" orient="auto" markerUnits="userSpaceOnUse">
    <path d="M 2 2 L 17 7 L 2 12" fill="none" stroke="var(--danger)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
</defs>
<text class="title" x="90" y="82">{esc(title)}</text>
<text class="subtitle" x="90" y="116">{esc(subtitle)}</text>
{"\n".join(parts)}
</svg>
</body>
</html>
'''
