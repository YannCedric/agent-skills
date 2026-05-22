"""Connector edge label placement helpers."""

import math

try:
    from .contracts import LabelBox
    from .metrics import (
        EDGE_CHAR_W,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        text_width,
        wrap_edge_label,
    )
    from .route_paths import segment_length, segment_orientation, segment_point
except ImportError:  # pragma: no cover - script execution fallback
    from contracts import LabelBox  # type: ignore
    from metrics import (  # type: ignore
        EDGE_CHAR_W,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        text_width,
        wrap_edge_label,
    )
    from route_paths import segment_length, segment_orientation, segment_point  # type: ignore


LABEL_SEGMENT_CLEARANCE = 34
DIRECT_LABEL_CLEARANCE = 78
LABEL_OBSTACLE_CLEARANCE = 8


def inline_label_metrics(label, segment):
    orientation = segment_orientation(segment)
    segment_len = segment_length(segment)
    if orientation == "horizontal":
        text_budget = max(
            24,
            min(
                EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
                segment_len - EDGE_LABEL_SEGMENT_PAD * 2 - EDGE_LABEL_INLINE_PAD_X * 2,
            ),
        )
        pad_x = EDGE_LABEL_INLINE_PAD_X
    else:
        text_budget = EDGE_VERTICAL_LABEL_MAX_WIDTH
        pad_x = EDGE_LABEL_PAD_X
    lines = wrap_edge_label(label, text_budget)
    allowed_text_width = text_budget
    if len(lines) == 2:
        allowed_text_width = max(text_budget, EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH)
    width = max(EDGE_LABEL_MIN_W, max(text_width(line, EDGE_CHAR_W) for line in lines) + pad_x * 2)
    height = EDGE_LABEL_PAD_Y * 2 + EDGE_LABEL_LINE_H * len(lines)
    inline_extent = width if orientation == "horizontal" else height
    visible_run = (segment_len - inline_extent) / 2
    if visible_run < EDGE_INLINE_MIN_VISIBLE_RUN and len(lines) == 2:
        lines = wrap_edge_label(label, text_budget, allow_soft_two_line=False)
        allowed_text_width = text_budget
        width = max(EDGE_LABEL_MIN_W, max(text_width(line, EDGE_CHAR_W) for line in lines) + pad_x * 2)
        height = EDGE_LABEL_PAD_Y * 2 + EDGE_LABEL_LINE_H * len(lines)
        inline_extent = width if orientation == "horizontal" else height
        visible_run = (segment_len - inline_extent) / 2
    return {
        "lines": lines,
        "width": width,
        "height": height,
        "inlineExtent": inline_extent,
        "textBudget": text_budget,
        "visibleRun": visible_run,
        "fits": segment_len >= EDGE_INLINE_MIN_READABLE
        and max(text_width(line, EDGE_CHAR_W) for line in lines) <= allowed_text_width
        and visible_run >= EDGE_INLINE_MIN_VISIBLE_RUN,
    }


def distance_point_to_segment(point, segment):
    px, py = point
    x1, y1, x2, y2 = segment["x1"], segment["y1"], segment["x2"], segment["y2"]
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) < 0.1 and abs(dy) < 0.1:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def box_center(box):
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def preferred_label_segment(edge):
    segments = edge.get("segments", [])
    label_segments = [segment for segment in segments if segment.get("role") == "label"]
    horizontal = [segment for segment in label_segments if segment_orientation(segment) == "horizontal"]
    candidates = horizontal or label_segments or segments
    if not candidates:
        return None, None
    best = max(candidates, key=segment_length)
    metrics = inline_label_metrics(edge.get("label", ""), best)
    if not metrics["fits"]:
        fallback_candidates = [
            segment
            for segment in segments
            if segment.get("role") in {"label", "branch"}
            and inline_label_metrics(edge.get("label", ""), segment)["fits"]
        ]
        if fallback_candidates:
            best = max(fallback_candidates, key=segment_length)
    if edge.get("route") == "direct" and segment_length(best) < EDGE_INLINE_MIN_SEGMENT / 2:
        horizontal_segments = [segment for segment in segments if segment_orientation(segment) == "horizontal"]
        best = horizontal_segments[0] if horizontal_segments else max(segments, key=segment_length)
    return segments.index(best), best


def label_anchor_for_edge(edge):
    existing_box = edge.get("labelBox")
    existing_anchor = existing_box.get("anchor") if existing_box else None
    if existing_anchor and existing_anchor.get("placementMode") == "obstacle-aware":
        return dict(existing_anchor)
    index, segment = preferred_label_segment(edge)
    if segment is None:
        return None
    route = edge.get("route", "direct")
    source_rank = edge.get("sourceRank", 0)
    target_rank = edge.get("targetRank", 0)
    t = 0.5
    x, y = segment_point(segment, t)
    orientation = segment_orientation(segment)
    side = "above"
    if orientation == "horizontal":
        side = "inline"
        segment_len = segment_length(segment)
        label_fits_inline = inline_label_metrics(edge.get("label", ""), segment)["fits"]
        if not label_fits_inline:
            side = "above"
    else:
        side = "right" if target_rank >= source_rank else "left"
        if segment_length(segment) >= 72:
            side = "inline"
    return {
        "segmentIndex": index,
        "t": round(t, 2),
        "x": round(x, 1),
        "y": round(y, 1),
        "side": side,
        "orientation": orientation,
        "route": route,
        "segmentLength": round(segment_length(segment), 1),
    }


def candidate_label_anchors(edge):
    segments = edge.get("segments", [])
    preferred_index, preferred_segment = preferred_label_segment(edge)
    ordered = []
    for index, segment in enumerate(segments):
        if segment.get("role") in {"label", "branch"}:
            ordered.append((index, segment))
    for index, segment in enumerate(segments):
        if (index, segment) not in ordered:
            ordered.append((index, segment))
    if preferred_segment is not None:
        ordered = [(preferred_index, preferred_segment)] + [
            item for item in ordered if item[0] != preferred_index
        ]

    route = edge.get("route", "direct")
    source_rank = edge.get("sourceRank", 0)
    target_rank = edge.get("targetRank", 0)
    anchors = []
    for index, segment in ordered:
        orientation = segment_orientation(segment)
        length = segment_length(segment)
        inline_fits = inline_label_metrics(edge.get("label", ""), segment)["fits"]
        if orientation == "horizontal":
            sides = ["inline"] if inline_fits else []
            sides += ["above", "below"]
        else:
            lateral = "right" if target_rank >= source_rank else "left"
            opposite = "left" if lateral == "right" else "right"
            sides = ["inline"] if length >= 72 else []
            sides += [lateral, opposite]
        seen_sides = []
        for side in sides:
            if side not in seen_sides:
                seen_sides.append(side)
        t_values = [0.5]
        if length >= 120:
            t_values += [0.35, 0.65]
        if length >= 220:
            t_values += [0.22, 0.78]
        if length >= 300:
            t_values += [0.12, 0.88]
        for side in seen_sides:
            for t in t_values:
                x, y = segment_point(segment, t)
                anchors.append({
                    "segmentIndex": index,
                    "t": round(t, 2),
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "side": side,
                    "orientation": orientation,
                    "route": route,
                    "segmentLength": round(length, 1),
                    "placementMode": "obstacle-aware",
                })
    return anchors


def label_box(label, point, position=None, anchor_data=None):
    if not label:
        return None
    x, y = point
    side = position
    if anchor_data and not side:
        side = anchor_data.get("side", side)
    if anchor_data and anchor_data.get("orientation") == "vertical" and side == "above":
        side = "left"
    pad_x = EDGE_LABEL_PAD_X
    if anchor_data and anchor_data.get("orientation") == "horizontal" and side == "inline":
        pad_x = EDGE_LABEL_INLINE_PAD_X
    max_text_width = None
    if anchor_data and anchor_data.get("orientation") == "horizontal" and side == "inline":
        segment_text_budget = anchor_data.get("segmentLength", 0) - EDGE_LABEL_SEGMENT_PAD * 2 - pad_x * 2
        max_text_width = max(24, min(EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH, segment_text_budget))
    elif anchor_data and anchor_data.get("orientation") == "horizontal":
        max_text_width = min(EDGE_FLOATING_LABEL_MAX_WIDTH, max(72, anchor_data.get("segmentLength", 0) + 8))
    elif anchor_data and anchor_data.get("orientation") == "vertical":
        max_text_width = EDGE_VERTICAL_LABEL_MAX_WIDTH
    lines = wrap_edge_label(label, max_text_width)
    width = max(EDGE_LABEL_MIN_W, int(max(text_width(line, EDGE_CHAR_W) for line in lines) + pad_x * 2))
    height = EDGE_LABEL_PAD_Y * 2 + EDGE_LABEL_LINE_H * len(lines)
    if anchor_data and side == "inline" and len(lines) == 2:
        inline_extent = width if anchor_data.get("orientation") == "horizontal" else height
        visible_run = (anchor_data.get("segmentLength", 0) - inline_extent) / 2
        if visible_run < EDGE_INLINE_MIN_VISIBLE_RUN:
            lines = wrap_edge_label(label, max_text_width, allow_soft_two_line=False)
            width = max(EDGE_LABEL_MIN_W, int(max(text_width(line, EDGE_CHAR_W) for line in lines) + pad_x * 2))
            height = EDGE_LABEL_PAD_Y * 2 + EDGE_LABEL_LINE_H * len(lines)
    offset = LABEL_SEGMENT_CLEARANCE
    if anchor_data and anchor_data.get("route") == "direct" and anchor_data.get("orientation") == "horizontal":
        offset = 42 if side in {"above", "below"} else DIRECT_LABEL_CLEARANCE
    if side == "inline":
        pass
    elif side == "above":
        y -= offset
    elif side == "below":
        y += offset
    elif side == "left":
        x -= width / 2 + offset
    elif side == "right":
        x += width / 2 + offset
    box = LabelBox(label=label, lines=lines, x=round(x - width / 2, 1), y=round(y - height / 2, 1), width=width, height=height)
    if anchor_data:
        box.anchor = dict(anchor_data)
    return box


def label_overlap_penalty(label, obstacle, padding):
    overlap_x = min(label["x"] + label["width"], obstacle["x"] + obstacle["width"]) - max(label["x"], obstacle["x"])
    overlap_y = min(label["y"] + label["height"], obstacle["y"] + obstacle["height"]) - max(label["y"], obstacle["y"])
    if overlap_x <= -padding or overlap_y <= -padding:
        return 0
    return max(1, overlap_x + padding) * max(1, overlap_y + padding)


def score_label_candidate(edge, candidate, obstacles, labels):
    anchor_data = candidate.get("anchor") or {}
    segment_index = anchor_data.get("segmentIndex")
    segments = edge.get("segments", [])
    segment = segments[segment_index] if segment_index is not None and segment_index < len(segments) else None
    score = 0
    for obstacle in obstacles:
        score += label_overlap_penalty(candidate, obstacle, LABEL_OBSTACLE_CLEARANCE) * 80
    for label in labels:
        score += label_overlap_penalty(candidate, label, 4) * 55
    if segment is not None:
        distance = distance_point_to_segment(box_center(candidate), segment)
        score += distance * 3
        if candidate["anchor"]["side"] != "inline":
            score += 16
        if segment.get("role") != "label":
            score += 28
        score += abs(candidate["anchor"].get("t", 0.5) - 0.5) * 18
    if candidate["x"] < 0 or candidate["y"] < 0:
        score += 5000
    return score


def place_label_box(edge, obstacles=None, labels=None):
    obstacles = list(obstacles or [])
    labels = list(labels or [])
    candidates = []
    for anchor_data in candidate_label_anchors(edge):
        box = label_box(edge.get("label", ""), (anchor_data["x"], anchor_data["y"]), edge.get("labelPosition"), anchor_data=anchor_data)
        if box:
            candidates.append(box)
    if not candidates:
        anchor_data = label_anchor_for_edge(edge)
        if not anchor_data:
            return None
        return label_box(edge.get("label", ""), (anchor_data["x"], anchor_data["y"]), edge.get("labelPosition"), anchor_data=anchor_data)
    return min(candidates, key=lambda candidate: score_label_candidate(edge, candidate, obstacles, labels))
