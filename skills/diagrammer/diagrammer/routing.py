"""Connector routing and edge layout helpers for diagrammer."""

try:
    from .contracts import RoutedEdge
    from .edge_labels import (
        DIRECT_LABEL_CLEARANCE,
        LABEL_OBSTACLE_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        box_center,
        candidate_label_anchors,
        distance_point_to_segment,
        inline_label_metrics,
        label_anchor_for_edge,
        label_box,
        label_overlap_penalty,
        place_label_box,
        preferred_label_segment,
        score_label_candidate,
    )
    from .port_geometry import (
        CONNECTOR_GAP,
        anchor,
        arrow_endpoint,
        center,
        clamp,
        diamond_port_point,
        ellipse_side_point,
        port_point,
        rectangular_port_point,
        shape_perimeter_point,
        shape_port_point,
        side_axis,
        side_direction,
    )
    from .route_paths import (
        connector_path,
        make_segment,
        max_segment_length,
        port_route_path,
        route_length,
        segment_length,
        segment_orientation,
        segment_point,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from contracts import RoutedEdge  # type: ignore
    from edge_labels import (  # type: ignore
        DIRECT_LABEL_CLEARANCE,
        LABEL_OBSTACLE_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        box_center,
        candidate_label_anchors,
        distance_point_to_segment,
        inline_label_metrics,
        label_anchor_for_edge,
        label_box,
        label_overlap_penalty,
        place_label_box,
        preferred_label_segment,
        score_label_candidate,
    )
    from port_geometry import (  # type: ignore
        CONNECTOR_GAP,
        anchor,
        arrow_endpoint,
        center,
        clamp,
        diamond_port_point,
        ellipse_side_point,
        port_point,
        rectangular_port_point,
        shape_perimeter_point,
        shape_port_point,
        side_axis,
        side_direction,
    )
    from route_paths import (  # type: ignore
        connector_path,
        make_segment,
        max_segment_length,
        port_route_path,
        route_length,
        segment_length,
        segment_orientation,
        segment_point,
    )


PORT_SPACING = 24
ROUTE_LANE_SPACING = 34

KNOWN_EDGE_KINDS = {"sync", "async", "retry", "failure"}
KNOWN_ROUTES = {"direct", "top", "bottom"}
KNOWN_PORTS = {"left", "right", "top", "bottom"}


def spaced_port_offsets(keys):
    groups = {}
    offsets = {}
    for index, key in enumerate(keys):
        if key is None:
            continue
        groups.setdefault(key, []).append(index)
    for indices in groups.values():
        count = len(indices)
        for order, index in enumerate(indices):
            offsets[index] = (order - (count - 1) / 2) * PORT_SPACING
    return offsets


def edge_sort_coordinate(edge, boxes, endpoint_kind, side):
    other_id = edge.get("to") if endpoint_kind == "source" else edge.get("from")
    other = boxes.get(other_id)
    if not other:
        return 0
    cx, cy = center(other)
    return cy if side_axis(side) == "y" else cx


def shared_endpoint_port_offsets(edges, boxes, source_keys, target_keys):
    groups = {}
    source_offsets = {}
    target_offsets = {}
    for index, key in enumerate(source_keys):
        if key is not None:
            groups.setdefault(key, []).append(("source", index, key[1]))
    for index, key in enumerate(target_keys):
        if key is not None:
            groups.setdefault(key, []).append(("target", index, key[1]))
    for entries in groups.values():
        side = entries[0][2]
        mixed_direction = len({entry[0] for entry in entries}) > 1
        spacing = 56 if mixed_direction and side in {"top", "bottom"} else PORT_SPACING
        entries = sorted(
            entries,
            key=lambda entry: (
                0 if mixed_direction and side in {"top", "bottom"} and entry[0] == "target" else 1,
                edge_sort_coordinate(edges[entry[1]], boxes, entry[0], entry[2]),
                entry[1],
            ),
        )
        count = len(entries)
        for order, (kind, index, _side) in enumerate(entries):
            offset = (order - (count - 1) / 2) * spacing
            if kind == "source":
                source_offsets[index] = offset
            else:
                target_offsets[index] = offset
    return source_offsets, target_offsets


def dominant_horizontal_approach(source, target):
    if not source or not target:
        return False
    source_cx, source_cy = center(source)
    target_cx, target_cy = center(target)
    return abs(target_cx - source_cx) >= max(80, abs(target_cy - source_cy) * 0.75)


def default_ports_for_edge(route, source, target, prefer_directional_source=False):
    if not source or not target:
        return None, None, False, False
    is_forward = target.get("rank", 0) > source.get("rank", 0)
    if route == "direct" and is_forward:
        return "right", "left", False, True
    if route in {"top", "bottom"} and is_forward and target.get("kind") != "db":
        target_side = "left" if target["x"] + target["width"] / 2 >= source["x"] + source["width"] / 2 else "right"
        if not prefer_directional_source:
            return "right" if target_side == "left" else "left", target_side, True, False
        if dominant_horizontal_approach(source, target):
            source_cy = source["y"] + source["height"] / 2
            target_cy = target["y"] + target["height"] / 2
            source_port = "top" if target_cy < source_cy else "bottom"
            return source_port, target_side, True, False
        if target_side == "left":
            return "right", "left", True, False
        return "left", "right", True, False
    if route in {"top", "bottom"} and is_forward and target.get("kind") == "db":
        return None, None, False, False
    return None, None, False, False


def facing_side(source, target):
    source_cx, source_cy = center(source)
    target_cx, target_cy = center(target)
    dx = source_cx - target_cx
    dy = source_cy - target_cy
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "bottom" if dy > 0 else "top"


def normalize_ports_for_geometry(raw, source, target, source_port, target_port):
    if not source or not target or raw.get("lockPorts") or raw.get("preservePorts"):
        return source_port, target_port
    if not (raw.get("sourcePort") and raw.get("targetPort")):
        return source_port, target_port
    if source_port not in KNOWN_PORTS or target_port not in KNOWN_PORTS:
        return source_port, target_port

    source_cx, source_cy = center(source)
    target_cx, target_cy = center(target)
    side_by_side = (
        abs(source_cx - target_cx) > max(80, abs(source_cy - target_cy) * 1.25)
        and abs(source_cy - target_cy) < max(80, abs(source_cx - target_cx) * 0.75)
    )

    if side_by_side and source_port in {"left", "right"} and target_port in {"top", "bottom"}:
        return source_port, facing_side(source, target)
    if side_by_side and source_port in {"top", "bottom"} and target_port in {"left", "right"}:
        return "right" if target_cx > source_cx else "left", target_port
    return source_port, target_port


def resolved_ports_for_edge(raw, source, target, route, prefer_directional_source=False):
    default_source_port, default_target_port, auto_side_dogleg, auto_direct_side = default_ports_for_edge(route, source, target, prefer_directional_source)
    source_port = raw.get("sourcePort") or default_source_port
    target_port = raw.get("targetPort") or default_target_port
    if (
        raw.get("kind") in {"retry", "failure"}
        and route in {"top", "bottom"}
        and not raw.get("sourcePort")
        and not raw.get("targetPort")
        and source
        and target
        and source.get("shape") in {"database-cylinder", "horizontal-cylinder"}
        and source.get("lane") == target.get("lane")
    ):
        source_cx, source_cy = center(source)
        target_cx, target_cy = center(target)
        if abs(source_cx - target_cx) > max(80, abs(source_cy - target_cy) * 1.25):
            if target_cx < source_cx:
                source_port, target_port = "left", "right"
            else:
                source_port, target_port = "right", "left"
    source_port, target_port = normalize_ports_for_geometry(raw, source, target, source_port, target_port)
    return source_port, target_port, auto_side_dogleg and not raw.get("sourcePort") and not raw.get("targetPort"), auto_direct_side and not raw.get("sourcePort") and not raw.get("targetPort")


def route_lane_offsets(edges, source_port_keys, target_port_keys):
    groups = {}
    offsets = {}
    for index, edge in enumerate(edges):
        source_key = source_port_keys[index]
        target_key = target_port_keys[index]
        if not source_key or not target_key:
            continue
        source_id, source_port = source_key
        _target_id, target_port = target_key
        if source_port not in {"left", "right"} or target_port not in {"left", "right"}:
            continue
        groups.setdefault((source_id, source_port, target_port), []).append(index)
    for indices in groups.values():
        count = len(indices)
        for order, index in enumerate(indices):
            offsets[index] = (order - (count - 1) / 2) * ROUTE_LANE_SPACING
    return offsets


def reciprocal_route_lane_offsets(edges, source_port_keys, target_port_keys):
    groups = {}
    offsets = {}
    for index, edge in enumerate(edges):
        source_key = source_port_keys[index]
        target_key = target_port_keys[index]
        if not source_key or not target_key:
            continue
        source_id, source_port = source_key
        target_id, target_port = target_key
        if source_id == target_id:
            continue
        if source_port not in {"left", "right"} or target_port not in {"left", "right"}:
            continue
        pair_key = tuple(sorted((source_id, target_id)))
        groups.setdefault(pair_key, []).append(index)
    for indices in groups.values():
        directions = {(edges[index].get("from"), edges[index].get("to")) for index in indices}
        if len(directions) < 2:
            continue
        ordered = sorted(indices, key=lambda index: (edges[index].get("from", ""), edges[index].get("to", ""), index))
        count = len(ordered)
        for order, index in enumerate(ordered):
            offsets[index] = (order - (count - 1) / 2) * ROUTE_LANE_SPACING
    return offsets


def layout_edges(defn, boxes, warnings):
    edges = []
    incoming_counts = {}
    outgoing_counts = {}
    raw_edges = list(defn.get("edges", []))
    source_port_keys = []
    target_port_keys = []
    for raw in raw_edges:
        incoming_counts[raw.get("to")] = incoming_counts.get(raw.get("to"), 0) + 1
        outgoing_counts[raw.get("from")] = outgoing_counts.get(raw.get("from"), 0) + 1
    for raw in raw_edges:
        source = boxes.get(raw.get("from"))
        target = boxes.get(raw.get("to"))
        route = raw.get("route", "direct")
        source_port = raw.get("sourcePort")
        target_port = raw.get("targetPort")
        prefer_directional_source = outgoing_counts.get(raw.get("from"), 0) > 1 and incoming_counts.get(raw.get("from"), 0) > 0
        source_port, target_port, _auto_side_dogleg, _auto_direct_side = resolved_ports_for_edge(raw, source, target, route, prefer_directional_source)
        source_port_keys.append((raw.get("from"), source_port) if source_port in KNOWN_PORTS else None)
        target_port_keys.append((raw.get("to"), target_port) if target_port in KNOWN_PORTS else None)
    source_offsets, target_offsets = shared_endpoint_port_offsets(raw_edges, boxes, source_port_keys, target_port_keys)
    route_offsets = route_lane_offsets(raw_edges, source_port_keys, target_port_keys)
    for index, offset in reciprocal_route_lane_offsets(raw_edges, source_port_keys, target_port_keys).items():
        route_offsets[index] = route_offsets.get(index, 0) + offset
    for index, raw in enumerate(raw_edges):
        edge = dict(raw)
        edge.setdefault("id", f"edge-{index + 1}")
        edge.setdefault("kind", "sync")
        edge.setdefault("label", "")
        if edge["kind"] not in KNOWN_EDGE_KINDS:
            warnings.append({"code": "unknown-edge-kind", "message": f"unknown edge kind {edge['kind']!r}; rendered as sync", "edge": edge["id"]})
            edge["kind"] = "sync"
        if not edge["label"]:
            warnings.append({"code": "missing-edge-label", "message": "edge has no label", "edge": edge["id"]})
        source = boxes.get(edge.get("from"))
        target = boxes.get(edge.get("to"))
        if not source or not target:
            warnings.append({"code": "missing-edge-node", "message": "edge references a missing node", "edge": edge["id"]})
            continue
        route = edge.get("route", "direct")
        if route not in KNOWN_ROUTES:
            warnings.append({"code": "ambiguous-route", "message": f"unknown route {route!r}; using direct", "edge": edge["id"]})
            route = "direct"
        prefer_directional_source = outgoing_counts.get(edge.get("from"), 0) > 1 and incoming_counts.get(edge.get("from"), 0) > 0
        source_port, target_port, auto_side_dogleg, auto_direct_side = resolved_ports_for_edge(edge, source, target, route, prefer_directional_source)
        if source_port and source_port not in KNOWN_PORTS:
            warnings.append({"code": "ambiguous-port", "message": f"unknown sourcePort {source_port!r}; using route default", "edge": edge["id"]})
            source_port = None
        if target_port and target_port not in KNOWN_PORTS:
            warnings.append({"code": "ambiguous-port", "message": f"unknown targetPort {target_port!r}; using route default", "edge": edge["id"]})
            target_port = None
        if source_port and target_port:
            if (
                edge.get("kind") in {"retry", "failure"}
                and not raw.get("sourcePort")
                and not raw.get("targetPort")
                and source.get("shape") in {"database-cylinder", "horizontal-cylinder"}
                and source_port in {"left", "right"}
                and target_port in {"left", "right"}
            ):
                edge.setdefault("labelPosition", "below")
            path, label_point, segments = port_route_path(
                source,
                target,
                source_port,
                target_port,
                source_offset=source_offsets.get(index, 0),
                target_offset=target_offsets.get(index, 0),
                route_lane_offset=route_offsets.get(index, 0),
            )
        elif route in {"top", "bottom"} and target.get("rank", 0) > source.get("rank", 0) and target.get("kind") != "db":
            path, label_point, segments = port_route_path(
                source,
                target,
                "right",
                "left",
                source_offset=source_offsets.get(index, 0),
                target_offset=target_offsets.get(index, 0),
                route_lane_offset=route_offsets.get(index, 0),
            )
        elif route == "direct" and target.get("rank", 0) > source.get("rank", 0):
            path, label_point, segments = port_route_path(
                source,
                target,
                "right",
                "left",
                source_offset=source_offsets.get(index, 0),
                target_offset=target_offsets.get(index, 0),
                route_lane_offset=route_offsets.get(index, 0),
            )
        else:
            path, label_point, segments = connector_path(source, target, route)
        if auto_side_dogleg and incoming_counts.get(edge.get("to"), 0) > 1 and segments:
            for segment in segments:
                if segment.get("role") == "label":
                    segment["role"] = "branch"
            segments[0]["role"] = "label"
        edge.update({
            "route": route,
            "path": path,
            "segments": segments,
            "sourcePort": source_port,
            "targetPort": target_port,
            "sourceOffset": source_offsets.get(index, 0),
            "targetOffset": target_offsets.get(index, 0),
            "routeLaneOffset": route_offsets.get(index, 0),
            "sourceRank": source.get("rank", 0),
            "targetRank": target.get("rank", 0),
            "sourceLane": source.get("lane", 0),
            "targetLane": target.get("lane", 0),
            "routeLength": round(route_length(segments), 1),
        })
        box = place_label_box(edge, obstacles=boxes.values(), labels=[placed["labelBox"] for placed in edges if placed.get("labelBox")])
        edge["labelBox"] = box
        edges.append(RoutedEdge.from_mapping(edge))
    return edges
