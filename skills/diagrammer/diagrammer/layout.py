#!/usr/bin/env python3
"""Pure layout, sizing, and geometry helpers for diagram compiler."""

import math

try:
    from . import shapes
    from .contracts import AnnotationBox, NodeBox
    from .metrics import (
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_CHAR_W,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MAX_LINES,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        HEIGHT,
        PAD_X,
        WIDTH,
        candidate_line_groups,
        shape_text_width,
        text_width,
        wrap_edge_label,
        wrap_label,
        wrap_text_to_width,
    )
    from .routing import layout_edges, max_segment_length
except ImportError:  # pragma: no cover - script execution fallback
    import shapes
    from contracts import AnnotationBox, NodeBox  # type: ignore
    from metrics import (  # type: ignore
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_CHAR_W,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MAX_LINES,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        HEIGHT,
        PAD_X,
        WIDTH,
        candidate_line_groups,
        shape_text_width,
        text_width,
        wrap_edge_label,
        wrap_label,
        wrap_text_to_width,
    )
    from routing import layout_edges, max_segment_length  # type: ignore


MARGIN_X = 120
MARGIN_Y = 190
LANE_GAP = 82
RANK_GAP = 210
NODE_MIN_W = 160
NODE_MAX_W = 300
NODE_BASE_H = 58
LINE_H = 22
PORT_SPACING = 24
ROUTE_LANE_SPACING = 34
ARROW_TIP_OVERHANG = 5
CONNECTOR_GAP = 10
CONNECTOR_GAP_TOLERANCE = 3

KNOWN_KINDS = shapes.known_kinds()
KNOWN_EDGE_KINDS = {"sync", "async", "retry", "failure"}
KNOWN_ROUTES = {"direct", "top", "bottom"}
KNOWN_PORTS = {"left", "right", "top", "bottom"}
LABEL_CLEARANCE = 12
LABEL_SEGMENT_CLEARANCE = 34
DIRECT_LABEL_CLEARANCE = 78
CANVAS_PAD_X = 90
CANVAS_PAD_TOP = 70
CANVAS_PAD_BOTTOM = 72
LOCAL_TARGET_GAP = 72
EXCESS_CONNECTOR_SEGMENT = 300


def node_size(node):
    raw_label = node.get("label", node.get("id", ""))
    shape = node.get("shape") or shapes.resolve_node_shape(node)
    label_max_width = NODE_MAX_W - PAD_X * 2
    label_lines = wrap_text_to_width(raw_label, label_max_width, CHAR_W, max_lines=3)
    detail = [str(line) for line in node.get("detail", [])]
    detail_lines = []
    for line in detail:
        detail_lines.extend(wrap_text_to_width(line, label_max_width, DETAIL_CHAR_W, max_lines=2))
    longest = max(label_lines + detail_lines + [node.get("kind", "service")], key=len)
    width = min(NODE_MAX_W, max(NODE_MIN_W, int(text_width(longest) + PAD_X * 2 + 20)))
    content_width = width - PAD_X * 2
    label_lines = wrap_text_to_width(raw_label, content_width, CHAR_W, max_lines=3)
    detail_lines = []
    for line in detail:
        detail_lines.extend(wrap_text_to_width(line, content_width, DETAIL_CHAR_W, max_lines=2))
    label_block_h = len(label_lines) * LINE_H
    detail_block_h = len(detail_lines) * LINE_H
    detail_gap = 8 if detail_lines else 0
    height = max(NODE_BASE_H, 26 + label_block_h + detail_gap + detail_block_h + 16)
    if shape == "database-cylinder":
        height = max(height + 78, 220 if detail_lines else 170)
        width = max(width, 190)
    if shape == "horizontal-cylinder":
        height = max(68, min(height + (18 if detail_lines else 0), 150))
        width = max(width, 240)
    if shape == "cloud":
        width = max(width, 250)
        height = max(height + 54, 136)
    if shape == "shield":
        width = max(width, 180)
        height = max(height + 48, 118)
    if shape == "diamond":
        width = max(width, 180)
        height = max(height + 34, 112)
    if shape == "user":
        return max(width, 190), max(height + 18, 92)
    if shape == "document":
        width = max(width, 180)
        height = max(height + 12, 86)
    return width, height


def assign_positions(defn, warnings):
    nodes = []
    for index, raw in enumerate(defn.get("nodes", [])):
        node = dict(raw)
        node.setdefault("id", f"node-{index + 1}")
        node.setdefault("label", node["id"])
        node.setdefault("kind", "service")
        if node["kind"] not in KNOWN_KINDS:
            warnings.append({"code": "unknown-kind", "message": f"unknown node kind {node['kind']!r}; rendered as service", "node": node["id"]})
            node["kind"] = "service"
        node["shape"] = shapes.resolve_node_shape(node)
        node.setdefault("lane", index % 3)
        node.setdefault("rank", index)
        w, h = node_size(node)
        node["_width"] = w
        node["_height"] = h
        nodes.append(node)

    ranks = sorted({int(n.get("rank", 0)) for n in nodes}) or [0]
    lanes = sorted({int(n.get("lane", 0)) for n in nodes}) or [0]
    rank_widths = {rank: max([n["_width"] for n in nodes if int(n.get("rank", 0)) == rank] or [NODE_MIN_W]) for rank in ranks}
    lane_heights = {lane: max([n["_height"] for n in nodes if int(n.get("lane", 0)) == lane] or [NODE_BASE_H]) for lane in lanes}

    x_cursor = MARGIN_X
    rank_x = {}
    for rank in ranks:
        rank_x[rank] = x_cursor
        x_cursor += rank_widths[rank] + RANK_GAP

    y_cursor = MARGIN_Y
    lane_y = {}
    for lane in lanes:
        lane_y[lane] = y_cursor
        y_cursor += lane_heights[lane] + LANE_GAP

    total_w = x_cursor - RANK_GAP + MARGIN_X
    total_h = y_cursor - LANE_GAP + MARGIN_Y
    dense_inventory = len(nodes) >= 12
    scale_x = 1.0 if dense_inventory else min(1.0, (WIDTH - MARGIN_X * 2) / max(1, total_w - MARGIN_X * 2))
    scale_y = 1.0 if dense_inventory else min(1.0, (HEIGHT - MARGIN_Y - 120) / max(1, total_h - MARGIN_Y - 120))

    boxes = {}
    for node in nodes:
        rank = int(node.get("rank", 0))
        lane = int(node.get("lane", 0))
        w = node["_width"]
        h = node["_height"]
        x = MARGIN_X + (rank_x[rank] - MARGIN_X) * scale_x
        y = MARGIN_Y + (lane_y[lane] - MARGIN_Y) * scale_y
        x += (rank_widths[rank] - w) * scale_x / 2
        y += (lane_heights[lane] - h) * scale_y / 2
        text_width_budget = shape_text_width(node["shape"], w, h)
        boxes[node["id"]] = NodeBox(
            id=node["id"],
            kind=node["kind"],
            shape=node["shape"],
            shapeFamily=shapes.shape_spec(node["shape"]).family,
            label=node["label"],
            detail=node.get("detail", []),
            labelLines=wrap_text_to_width(node["label"], text_width_budget, CHAR_W, max_lines=3),
            detailLines=[
                wrapped
                for detail_line in node.get("detail", [])
                for wrapped in wrap_text_to_width(detail_line, text_width_budget, DETAIL_CHAR_W, max_lines=2)
            ],
            lane=lane,
            rank=rank,
            x=round(x, 1),
            y=round(y, 1),
            width=round(w, 1),
            height=round(h, 1),
        )
    return nodes, boxes


def center(box):
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def clamp(value, low, high):
    return max(low, min(high, value))



def compactible_sink_target(node_id, boxes, edge_defs):
    node = boxes.get(node_id)
    if not node:
        return False
    for edge in edge_defs:
        if edge.get("to") != node_id or edge.get("kind", "sync") == "retry":
            continue
        source = boxes.get(edge.get("from"))
        if source and source.get("rank", 0) > node.get("rank", 0):
            return False
    outgoing_non_retry = [
        edge for edge in edge_defs
        if edge.get("from") == node_id and edge.get("kind", "sync") != "retry"
    ]
    return node.get("kind") == "db" or not outgoing_non_retry


def resolve_compacted_x(target, candidate_x, boxes, annotations=None):
    x = candidate_x
    candidate = dict(target)
    for other in boxes.values():
        if other["id"] == target["id"] or other.get("lane") != target.get("lane"):
            continue
        candidate["x"] = x
        same_band = overlaps(candidate, other, padding=42)
        if same_band and x < other["x"] + other["width"] + 42:
            x = other["x"] + other["width"] + LOCAL_TARGET_GAP
    for other in annotations or []:
        candidate["x"] = x
        if overlaps(candidate, other, padding=42) and x < other["x"] + other["width"] + 42:
            x = other["x"] + other["width"] + LOCAL_TARGET_GAP
    return x


def compact_leaf_sink_targets(defn, boxes, initial_edges, annotations=None):
    edge_defs = list(defn.get("edges", []))
    moved = []
    for edge in initial_edges:
        if max_segment_length(edge.get("segments", [])) <= EXCESS_CONNECTOR_SEGMENT:
            continue
        source = boxes.get(edge.get("from"))
        target = boxes.get(edge.get("to"))
        if not source or not target:
            continue
        if target.get("rank", 0) <= source.get("rank", 0) or target["x"] <= source["x"]:
            continue
        if not compactible_sink_target(target["id"], boxes, edge_defs):
            continue
        candidate_x = source["x"] + source["width"] + LOCAL_TARGET_GAP
        candidate_x = resolve_compacted_x(target, candidate_x, boxes, annotations)
        if candidate_x >= target["x"] - 1:
            continue
        old_x = target["x"]
        target["x"] = round(candidate_x, 1)
        moved.append({
            "node": target["id"],
            "fromX": round(old_x, 1),
            "toX": target["x"],
            "triggerEdge": edge["id"],
        })
    if not moved:
        return []
    return [{
        "code": "compact-local-sinks",
        "message": "moved leaf/source-of-truth targets closer to their local parent to shorten excessive connector spans",
        "count": len(moved),
        "nodes": moved,
    }]


def annotation_layout(defn):
    items = []
    annotations = defn.get("annotations", [])
    for index, ann in enumerate(annotations):
        lane = int(ann.get("lane", 0))
        rank = int(ann.get("rank", len(defn.get("nodes", [])) + index))
        width = 280
        height = 34 + len(ann.get("lines", [])) * 22
        x = min(WIDTH - width - 90, MARGIN_X + rank * (NODE_MIN_W + RANK_GAP))
        y = min(HEIGHT - height - 70, 82 + lane * 165)
        items.append(AnnotationBox(
            id=ann.get("id", f"annotation-{index + 1}"),
            title=ann.get("title", "Note"),
            lines=ann.get("lines", []),
            lane=lane,
            rank=rank,
            x=round(x, 1),
            y=round(y, 1),
            width=width,
            height=height,
        ))
    return items


def overlaps(a, b, padding=0):
    return (
        min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"]) > -padding
        and min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"]) > -padding
    )


def move_box(box, dx, dy):
    box["x"] = round(box["x"] + dx, 1)
    box["y"] = round(box["y"] + dy, 1)
    if "anchor" in box:
        box["anchor"]["dx"] = round(box["anchor"].get("dx", 0) + dx, 1)
        box["anchor"]["dy"] = round(box["anchor"].get("dy", 0) + dy, 1)


def content_bounds(layout, include_footer=False):
    items = list(layout["boxes"].values()) + layout["annotations"]
    items += [edge["labelBox"] for edge in layout["edges"] if edge.get("labelBox")]
    if include_footer:
        items.append({"x": 90, "y": HEIGHT - 86, "width": 1450, "height": 78})
    if not items:
        return {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT}
    min_x = min(item["x"] for item in items)
    min_y = min(item["y"] for item in items)
    max_x = max(item["x"] + item["width"] for item in items)
    max_y = max(item["y"] + item["height"] for item in items)
    return {"x": round(min_x, 1), "y": round(min_y, 1), "width": round(max_x - min_x, 1), "height": round(max_y - min_y, 1)}


def trimmed_canvas(bounds):
    x = max(0, math.floor(bounds["x"] - CANVAS_PAD_X))
    y = max(0, math.floor(bounds["y"] - CANVAS_PAD_TOP))
    right = max(WIDTH, math.ceil(bounds["x"] + bounds["width"] + CANVAS_PAD_X))
    bottom = max(HEIGHT, math.ceil(bounds["y"] + bounds["height"] + CANVAS_PAD_BOTTOM))
    return {"x": x, "y": y, "width": right - x, "height": bottom - y}
