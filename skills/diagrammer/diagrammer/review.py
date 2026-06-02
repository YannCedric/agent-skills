#!/usr/bin/env python3
"""Layout review, scoring, and review-time autofix helpers."""

import math

BLOCKING_WARNING_CODES = {
    "box-overlap",
    "label-overlap",
    "shape-text-overflow",
    "connector-node-intrusion",
    "connector-crossing",
    "detached-connector-label",
    "label-too-close-to-arrow-tip",
    "long-bottom-return-route",
    "merged-route-lane",
    "opposing-route-corridor",
    "collapsed-source-port",
    "collapsed-target-port",
}
PUBLISHABLE_SCORE = 80

try:
    from .layout import (
        CONNECTOR_GAP,
        CONNECTOR_GAP_TOLERANCE,
        DIRECT_LABEL_CLEARANCE,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        EXCESS_CONNECTOR_SEGMENT,
        HEIGHT,
        KNOWN_PORTS,
        LABEL_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        PORT_SPACING,
        ROUTE_LANE_SPACING,
        WIDTH,
        content_bounds,
        move_box,
        overlaps,
        trimmed_canvas,
    )
    from .metrics import CHAR_W, DETAIL_CHAR_W, text_width, wrap_label
    from .port_geometry import shape_perimeter_point
    from .renderer import text_stack_layout
    from .routing import (
        box_center,
        distance_point_to_segment,
        label_anchor_for_edge,
        label_box,
        max_segment_length,
        segment_length,
        segment_orientation,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from layout import (  # type: ignore
        CONNECTOR_GAP,
        CONNECTOR_GAP_TOLERANCE,
        DIRECT_LABEL_CLEARANCE,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        EXCESS_CONNECTOR_SEGMENT,
        HEIGHT,
        KNOWN_PORTS,
        LABEL_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        PORT_SPACING,
        ROUTE_LANE_SPACING,
        WIDTH,
        content_bounds,
        move_box,
        overlaps,
        trimmed_canvas,
    )
    from metrics import CHAR_W, DETAIL_CHAR_W, text_width, wrap_label  # type: ignore
    from port_geometry import shape_perimeter_point  # type: ignore
    from renderer import text_stack_layout  # type: ignore
    from routing import (  # type: ignore
        box_center,
        distance_point_to_segment,
        label_anchor_for_edge,
        label_box,
        max_segment_length,
        segment_length,
        segment_orientation,
    )


def inflated(box, padding):
    return {
        "x": box["x"] - padding,
        "y": box["y"] - padding,
        "width": box["width"] + padding * 2,
        "height": box["height"] + padding * 2,
    }


def segment_intersects_box(segment, box, padding=0):
    target = inflated(box, padding)
    x1, y1, x2, y2 = segment["x1"], segment["y1"], segment["x2"], segment["y2"]
    left = target["x"]
    right = target["x"] + target["width"]
    top = target["y"]
    bottom = target["y"] + target["height"]
    if segment_orientation(segment) == "horizontal":
        y = y1
        if y < top or y > bottom:
            return False
        return max(min(x1, x2), left) < min(max(x1, x2), right)
    x = x1
    if x < left or x > right:
        return False
    return max(min(y1, y2), top) < min(max(y1, y2), bottom)


def edge_label_distance(edge):
    box = edge.get("labelBox")
    if not box:
        return None
    point = box_center(box)
    segments = edge.get("segments", [])
    if not segments:
        return None
    return min(distance_point_to_segment(point, segment) for segment in segments)


def edge_label_visible_run(edge):
    box = edge.get("labelBox")
    if not box:
        return None
    anchor_data = box.get("anchor") or {}
    index = anchor_data.get("segmentIndex")
    segments = edge.get("segments", [])
    if index is None or index >= len(segments):
        return None
    segment = segments[index]
    extent = box["width"] if segment_orientation(segment) == "horizontal" else box["height"]
    return (segment_length(segment) - extent) / 2


def label_distance_limit(edge):
    box = edge.get("labelBox") or {}
    anchor_data = box.get("anchor") or {}
    if anchor_data.get("route") == "direct" and anchor_data.get("orientation") == "horizontal":
        return DIRECT_LABEL_CLEARANCE + 24
    if anchor_data.get("orientation") == "vertical":
        return EDGE_VERTICAL_LABEL_MAX_WIDTH
    return LABEL_SEGMENT_CLEARANCE + 28


def detached_external_label(edge):
    box = edge.get("labelBox")
    if not box:
        return None
    anchor_data = box.get("anchor") or {}
    side = anchor_data.get("side")
    if side not in {"above", "below", "left", "right"}:
        return None
    index = anchor_data.get("segmentIndex")
    segments = edge.get("segments", [])
    if index is None or index < 0 or index >= len(segments):
        return None
    segment = segments[index]
    distance = distance_point_to_segment(box_center(box), segment)
    orientation = anchor_data.get("orientation") or segment_orientation(segment)
    offset = LABEL_SEGMENT_CLEARANCE
    if anchor_data.get("route") == "direct" and orientation == "horizontal" and side in {"above", "below"}:
        offset = 42
    if side in {"left", "right"}:
        threshold = box.get("width", 0) / 2 + offset + 24
    else:
        threshold = offset + 24
    if distance <= threshold:
        return None
    return {
        "edge": edge["id"],
        "label": edge.get("label", box.get("label")),
        "distance": round(distance, 1),
        "threshold": round(threshold, 1),
        "anchorSide": side,
        "anchorOrientation": orientation,
        "segmentIndex": index,
    }


def point_distance(left, right):
    return math.hypot(left[0] - right[0], left[1] - right[1])


def segment_span_overlap(left, right):
    if segment_orientation(left) != segment_orientation(right):
        return 0
    if segment_orientation(left) == "horizontal":
        return max(0, min(max(left["x1"], left["x2"]), max(right["x1"], right["x2"])) - max(min(left["x1"], left["x2"]), min(right["x1"], right["x2"])))
    return max(0, min(max(left["y1"], left["y2"]), max(right["y1"], right["y2"])) - max(min(left["y1"], left["y2"]), min(right["y1"], right["y2"])))


def segment_crossing_point(left, right):
    left_orientation = segment_orientation(left)
    right_orientation = segment_orientation(right)
    if left_orientation == right_orientation:
        return None
    horizontal = left if left_orientation == "horizontal" else right
    vertical = right if left_orientation == "horizontal" else left
    hx1, hx2 = sorted((horizontal["x1"], horizontal["x2"]))
    vy1, vy2 = sorted((vertical["y1"], vertical["y2"]))
    x = vertical["x1"]
    y = horizontal["y1"]
    if hx1 < x < hx2 and vy1 < y < vy2:
        return x, y
    return None


def point_near_segment_endpoint(point, segment, threshold=8):
    endpoints = ((segment["x1"], segment["y1"]), (segment["x2"], segment["y2"]))
    return any(point_distance(point, endpoint) <= threshold for endpoint in endpoints)


def opposing_route_corridor_overlap(left, right):
    if left.get("from") != right.get("to") or left.get("to") != right.get("from"):
        return 0
    max_overlap = 0
    for left_segment in internal_branch_segments(left):
        for right_segment in internal_branch_segments(right):
            orientation = segment_orientation(left_segment)
            if orientation != segment_orientation(right_segment):
                continue
            same_lane = (
                abs(left_segment["x1"] - right_segment["x1"]) < ROUTE_LANE_SPACING * 0.5
                if orientation == "vertical"
                else abs(left_segment["y1"] - right_segment["y1"]) < ROUTE_LANE_SPACING * 0.5
            )
            if same_lane:
                max_overlap = max(max_overlap, segment_span_overlap(left_segment, right_segment))
    return max_overlap


def internal_branch_segments(edge):
    segments = edge.get("segments", [])
    return [segment for segment in segments[1:-1] if segment.get("role") == "branch"]


def edge_endpoint_gaps(edge, boxes):
    gaps = []
    segments = edge.get("segments", [])
    source = boxes.get(edge.get("from"))
    target = boxes.get(edge.get("to"))
    if source and edge.get("sourcePort") in KNOWN_PORTS and "sourceOffset" in edge and segments:
        side = edge["sourcePort"]
        perimeter = shape_perimeter_point(source, side, edge.get("sourceOffset", 0))
        start = (segments[0]["x1"], segments[0]["y1"])
        gaps.append(("source", point_distance(start, perimeter)))
    if target and edge.get("targetPort") in KNOWN_PORTS and "targetOffset" in edge and segments:
        side = edge["targetPort"]
        endpoint = (segments[-1]["x2"], segments[-1]["y2"])
        perimeter = shape_perimeter_point(target, side, edge.get("targetOffset", 0))
        gaps.append(("target", point_distance(endpoint, perimeter)))
    return gaps


def excess_span_review_applies(layout, edge):
    target = layout["boxes"].get(edge.get("to"))
    if not target:
        return False
    outgoing_non_retry = [
        candidate for candidate in layout.get("edges", [])
        if candidate.get("from") == edge.get("to") and candidate.get("kind", "sync") != "retry"
    ]
    if target.get("kind") != "db" and outgoing_non_retry:
        return False
    for candidate in layout.get("edges", []):
        if candidate.get("to") != edge.get("to") or candidate.get("kind", "sync") == "retry":
            continue
        if candidate.get("sourceRank", 0) > candidate.get("targetRank", 0):
            return False
    return True


def node_text_fit(box):
    stack = text_stack_layout(box)
    area = stack["area"]
    label_lines = box.get("labelLines") or wrap_label(box.get("label", ""))
    detail_lines = box.get("detailLines") or [str(line) for line in box.get("detail", [])]
    max_label_width = max([text_width(line, CHAR_W) for line in label_lines] or [0])
    max_detail_width = max([text_width(line, DETAIL_CHAR_W) for line in detail_lines] or [0])
    text_height = stack["textBounds"]["height"]
    return {
        "area": area,
        "textBounds": stack["textBounds"],
        "maxTextWidth": max(max_label_width, max_detail_width),
        "textHeight": text_height,
        "fitsWidth": max(max_label_width, max_detail_width) <= area["width"] + 1,
        "fitsHeight": text_height <= area["height"] + 1,
    }


def analyze_layout(layout, base_warnings=None):
    warnings = list(base_warnings or [])
    metrics = {
        "score": 100,
        "warningCount": 0,
        "boxOverlapCount": 0,
        "labelOverlapCount": 0,
        "labelNodeIntrusionCount": 0,
        "labelFarFromConnectorCount": 0,
        "detachedConnectorLabelCount": 0,
        "unanchoredLabelCount": 0,
        "nodeIntrusionCount": 0,
        "longRouteCount": 0,
        "excessConnectorSpanCount": 0,
        "connectorEndpointGapCount": 0,
        "mergedRouteLaneCount": 0,
        "opposingRouteCorridorCount": 0,
        "collapsedPortEndpointCount": 0,
        "connectorCrossingCount": 0,
        "shapeTextOverflowCount": 0,
        "ambiguousLabelPlacementCount": 0,
        "blockingWarningCount": 0,
        "publishable": True,
        "excessWhitespaceRatio": 0,
        "routeCount": len(layout["edges"]),
        "labelCount": sum(1 for edge in layout["edges"] if edge.get("labelBox")),
    }

    label_boxes = [edge["labelBox"] for edge in layout["edges"] if edge.get("labelBox")]
    obstacles = list(layout["boxes"].values()) + layout["annotations"]
    all_boxes = obstacles + label_boxes
    for i, left in enumerate(all_boxes):
        for right in all_boxes[i + 1 :]:
            code = "label-overlap" if "edge-label" in {left["type"], right["type"]} else "box-overlap"
            padding = -4 if code == "label-overlap" else 2
            if overlaps(left, right, padding=padding):
                if code == "label-overlap":
                    metrics["labelOverlapCount"] += 1
                    if "edge-label" in {left["type"], right["type"]} and {left["type"], right["type"]} != {"edge-label"}:
                        metrics["labelNodeIntrusionCount"] += 1
                else:
                    metrics["boxOverlapCount"] += 1
                warnings.append({
                    "code": code,
                    "message": f"{left.get('id', left.get('label', left['type']))} overlaps or sits too close to {right.get('id', right.get('label', right['type']))}",
                })

    node_boxes = list(layout["boxes"].values())
    for node in node_boxes:
        fit = node_text_fit(node)
        if not fit["fitsWidth"] or not fit["fitsHeight"]:
            metrics["shapeTextOverflowCount"] += 1
            warnings.append({
                "code": "shape-text-overflow",
                "message": f"node text does not fit the usable {node.get('shape', node.get('kind'))} text area",
                "node": node["id"],
                "shape": node.get("shape"),
                "maxTextWidth": round(fit["maxTextWidth"], 1),
                "textAreaWidth": round(fit["area"]["width"], 1),
                "textHeight": round(fit["textHeight"], 1),
                "textAreaHeight": round(fit["area"]["height"], 1),
            })
    for i, left in enumerate(layout["edges"]):
        for right in layout["edges"][i + 1 :]:
            if left.get("from") == right.get("from") and left.get("sourcePort") and left.get("sourcePort") == right.get("sourcePort"):
                left_start = (left["segments"][0]["x1"], left["segments"][0]["y1"]) if left.get("segments") else None
                right_start = (right["segments"][0]["x1"], right["segments"][0]["y1"]) if right.get("segments") else None
                if left_start and right_start and point_distance(left_start, right_start) < PORT_SPACING * 0.55:
                    metrics["collapsedPortEndpointCount"] += 1
                    warnings.append({"code": "collapsed-source-port", "message": "sibling connectors start from the same visual source point", "edges": [left["id"], right["id"]]})
            if left.get("to") == right.get("to") and left.get("targetPort") and left.get("targetPort") == right.get("targetPort"):
                left_end = (left["segments"][-1]["x2"], left["segments"][-1]["y2"]) if left.get("segments") else None
                right_end = (right["segments"][-1]["x2"], right["segments"][-1]["y2"]) if right.get("segments") else None
                if left_end and right_end and point_distance(left_end, right_end) < PORT_SPACING * 0.55:
                    metrics["collapsedPortEndpointCount"] += 1
                    warnings.append({"code": "collapsed-target-port", "message": "sibling connectors end at the same visual target point", "edges": [left["id"], right["id"]]})
            if left.get("from") == right.get("from") and left.get("sourcePort") == right.get("sourcePort"):
                for left_segment in internal_branch_segments(left):
                    for right_segment in internal_branch_segments(right):
                        if segment_orientation(left_segment) != segment_orientation(right_segment):
                            continue
                        same_lane = (
                            abs(left_segment["x1"] - right_segment["x1"]) < ROUTE_LANE_SPACING * 0.5
                            if segment_orientation(left_segment) == "vertical"
                            else abs(left_segment["y1"] - right_segment["y1"]) < ROUTE_LANE_SPACING * 0.5
                        )
                        if same_lane and segment_span_overlap(left_segment, right_segment) > 24:
                            metrics["mergedRouteLaneCount"] += 1
                            warnings.append({"code": "merged-route-lane", "message": "sibling connector trunks visually merge before splitting", "edges": [left["id"], right["id"]]})
            corridor_overlap = opposing_route_corridor_overlap(left, right)
            if corridor_overlap > ROUTE_LANE_SPACING * 1.5:
                metrics["opposingRouteCorridorCount"] += 1
                warnings.append({
                    "code": "opposing-route-corridor",
                    "message": "opposing connectors between the same nodes visually merge in a shared corridor",
                    "edges": [left["id"], right["id"]],
                    "overlap": round(corridor_overlap, 1),
                })
            for left_segment in left.get("segments", []):
                for right_segment in right.get("segments", []):
                    if {left.get("from"), left.get("to")} == {right.get("from"), right.get("to")} and "retry" in {left.get("kind"), right.get("kind")}:
                        continue
                    point = segment_crossing_point(left_segment, right_segment)
                    if point and not point_near_segment_endpoint(point, left_segment) and not point_near_segment_endpoint(point, right_segment):
                        metrics["connectorCrossingCount"] += 1
                        warnings.append({"code": "connector-crossing", "message": "connector routes cross away from a shared endpoint", "edges": [left["id"], right["id"]]})
    for edge in layout["edges"]:
        label = edge.get("labelBox")
        if edge.get("label") and not label:
            metrics["ambiguousLabelPlacementCount"] += 1
            warnings.append({"code": "missing-label-box", "message": "edge label has no measured text-gap box", "edge": edge["id"]})
        if label and not label.get("anchor"):
            metrics["unanchoredLabelCount"] += 1
            warnings.append({"code": "unanchored-label", "message": "connector label is not attached to a segment anchor", "edge": edge["id"]})
        if label:
            distance = edge_label_distance(edge)
            if distance is None:
                metrics["ambiguousLabelPlacementCount"] += 1
                warnings.append({"code": "ambiguous-label-placement", "message": "connector label cannot be measured against route geometry", "edge": edge["id"]})
            elif distance > label_distance_limit(edge):
                metrics["labelFarFromConnectorCount"] += 1
                warnings.append({"code": "label-far-from-connector", "message": f"connector label is {distance:.1f}px from its route", "edge": edge["id"]})
            detached_label = detached_external_label(edge)
            if detached_label:
                metrics["detachedConnectorLabelCount"] += 1
                warnings.append({
                    "code": "detached-connector-label",
                    "message": f"external connector label is {detached_label['distance']:.1f}px from its anchored segment",
                    **detached_label,
                })
            visible_run = edge_label_visible_run(edge)
            if label.get("anchor", {}).get("side") == "inline" and visible_run is not None and visible_run < EDGE_INLINE_MIN_VISIBLE_RUN:
                metrics["ambiguousLabelPlacementCount"] += 1
                warnings.append({"code": "label-too-close-to-arrow-tip", "message": f"inline label leaves only {visible_run:.1f}px of visible connector run", "edge": edge["id"]})
        for endpoint_kind, gap in edge_endpoint_gaps(edge, layout["boxes"]):
            if abs(gap - CONNECTOR_GAP) > CONNECTOR_GAP_TOLERANCE:
                metrics["connectorEndpointGapCount"] += 1
                warnings.append({
                    "code": "connector-endpoint-gap",
                    "message": "connector endpoint gap is inconsistent with the shape perimeter",
                    "edge": edge["id"],
                    "endpoint": endpoint_kind,
                    "gap": round(gap, 1),
                    "expected": CONNECTOR_GAP,
                })
        has_explicit_ports = bool(edge.get("sourcePort") and edge.get("targetPort"))
        if not has_explicit_ports and edge.get("route") == "bottom" and edge.get("sourceRank", 0) > edge.get("targetRank", 0) and edge.get("routeLength", 0) > 880:
            metrics["longRouteCount"] += 1
            warnings.append({"code": "long-bottom-return-route", "message": "bottom return route is very long", "edge": edge["id"], "routeLength": edge.get("routeLength")})
        excessive_segment = max_segment_length(edge.get("segments", []))
        if excessive_segment > EXCESS_CONNECTOR_SEGMENT:
            forward_local = 0 < edge.get("targetRank", 0) - edge.get("sourceRank", 0) <= 1
            target_compacted = edge.get("to") in set(layout.get("_compactedNodes", []))
            if forward_local and edge.get("kind") not in {"retry", "failure"} and not target_compacted and excess_span_review_applies(layout, edge):
                metrics["excessConnectorSpanCount"] += 1
                warnings.append({
                    "code": "excess-connector-span",
                    "message": "connector has a long uninterrupted segment; compact local targets or mark the long boundary crossing explicitly",
                    "edge": edge["id"],
                    "maxSegmentLength": round(excessive_segment, 1),
                })
        for segment in edge.get("segments", []):
            for node in node_boxes:
                if node["id"] in {edge.get("from"), edge.get("to")}:
                    continue
                if segment_intersects_box(segment, node, padding=6):
                    metrics["nodeIntrusionCount"] += 1
                    warnings.append({"code": "connector-node-intrusion", "message": f"connector crosses or runs too close to unrelated node {node['id']}", "edge": edge["id"], "node": node["id"]})

    bounds = content_bounds(layout)
    whitespace_ratio = 1 - ((bounds["width"] * bounds["height"]) / max(1, WIDTH * HEIGHT))
    metrics["excessWhitespaceRatio"] = round(max(0, whitespace_ratio), 3)
    # Croppable whitespace is exported as metadata for renderers; it is not a
    # diagram-quality warning now that render.py can auto-size to the SVG viewBox.

    penalty = (
        metrics["boxOverlapCount"] * 12
        + metrics["labelOverlapCount"] * 12
        + metrics["labelFarFromConnectorCount"] * 8
        + metrics["detachedConnectorLabelCount"] * 8
        + metrics["unanchoredLabelCount"] * 10
        + metrics["nodeIntrusionCount"] * 14
        + metrics["longRouteCount"] * 6
        + metrics["excessConnectorSpanCount"] * 6
        + metrics["connectorEndpointGapCount"] * 8
        + metrics["mergedRouteLaneCount"] * 10
        + metrics["opposingRouteCorridorCount"] * 10
        + metrics["collapsedPortEndpointCount"] * 10
        + metrics["connectorCrossingCount"] * 10
        + metrics["shapeTextOverflowCount"] * 10
        + metrics["ambiguousLabelPlacementCount"] * 10
        + (8 if metrics["excessWhitespaceRatio"] > 0.72 else 0)
        + len([w for w in warnings if w.get("code", "").startswith("unknown") or w.get("code", "").startswith("missing")]) * 8
    )
    metrics["score"] = max(0, 100 - penalty)
    metrics["warningCount"] = len(warnings)
    blocking_warnings = [warning for warning in warnings if warning.get("code") in BLOCKING_WARNING_CODES]
    metrics["blockingWarningCount"] = len(blocking_warnings)
    metrics["publishable"] = metrics["score"] >= PUBLISHABLE_SCORE and not blocking_warnings
    recommendation = (
        "shareable"
        if metrics["publishable"]
        else "revise-or-split-before-sharing"
    )
    return {
        "ok": not warnings,
        "score": metrics["score"],
        "metrics": metrics,
        "warningCount": len(warnings),
        "blockingWarningCount": len(blocking_warnings),
        "publishable": metrics["publishable"],
        "recommendation": recommendation,
        "blockingWarnings": blocking_warnings,
        "warnings": warnings,
    }


def relabel_edges_to_anchors(layout):
    count = 0
    for edge in layout["edges"]:
        if not edge.get("label"):
            continue
        anchor_data = label_anchor_for_edge(edge)
        if not anchor_data:
            continue
        edge["labelBox"] = label_box(edge["label"], (anchor_data["x"], anchor_data["y"]), edge.get("labelPosition"), anchor_data)
        count += 1
    return count


def nudge_label_from_obstacle(label, obstacle):
    lx, ly = box_center(label)
    ox, oy = box_center(obstacle)
    overlap_x = min(label["x"] + label["width"], obstacle["x"] + obstacle["width"]) - max(label["x"], obstacle["x"])
    overlap_y = min(label["y"] + label["height"], obstacle["y"] + obstacle["height"]) - max(label["y"], obstacle["y"])
    if overlap_x <= 0 or overlap_y <= 0:
        return False
    if overlap_x < overlap_y:
        direction = -1 if lx < ox else 1
        move_box(label, direction * (overlap_x + LABEL_CLEARANCE), 0)
    else:
        direction = -1 if ly < oy else 1
        move_box(label, 0, direction * (overlap_y + LABEL_CLEARANCE))
    return True


def autofix_layout(layout):
    fixes = []
    fixes.extend(layout.pop("_layoutFixes", []))
    anchored = relabel_edges_to_anchors(layout)
    if anchored:
        fixes.append({"code": "label-segment-anchors", "message": "moved connector labels to explicit segment anchors", "count": anchored})

    # Keep labels attached to their segment slots. Free nudging made the sample
    # score better in some cases, but visually detached labels from their lines.
    bounds = content_bounds(layout)
    view = trimmed_canvas(bounds)
    layout["canvas"].update({"contentBounds": bounds, "trimmedViewBox": view})
    if view["width"] < WIDTH or view["height"] < HEIGHT:
        fixes.append({"code": "canvas-trim-metadata", "message": "recorded compact viewBox metadata for crop-aware exports", "trimmedViewBox": view})

    compacted_routes = sum(1 for edge in layout["edges"] if edge.get("route") == "bottom" and edge.get("sourceRank", 0) > edge.get("targetRank", 0))
    if compacted_routes:
        fixes.append({"code": "compact-bottom-return", "message": "used tighter offset for bottom return routes", "count": compacted_routes})
    return {"fixCount": sum(item.get("count", 1) for item in fixes), "fixes": fixes}
