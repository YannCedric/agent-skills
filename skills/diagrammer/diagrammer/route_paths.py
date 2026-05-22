"""Pure connector route segment and path construction helpers."""

import math

try:
    from .port_geometry import (
        CONNECTOR_GAP,
        arrow_endpoint,
        center,
        clamp,
        port_point,
        shape_port_point,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from port_geometry import (  # type: ignore
        CONNECTOR_GAP,
        arrow_endpoint,
        center,
        clamp,
        port_point,
        shape_port_point,
    )


PORT_SPACING = 24
ROUTE_LANE_SPACING = 34
LABEL_SEGMENT_CLEARANCE = 34


def make_segment(x1, y1, x2, y2, role):
    return {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1), "role": role}


def segment_length(segment):
    return abs(segment["x2"] - segment["x1"]) + abs(segment["y2"] - segment["y1"])


def route_length(segments):
    return sum(segment_length(segment) for segment in segments)


def max_segment_length(segments):
    return max([segment_length(segment) for segment in segments] or [0])


def segment_point(segment, t=0.5):
    return (
        segment["x1"] + (segment["x2"] - segment["x1"]) * t,
        segment["y1"] + (segment["y2"] - segment["y1"]) * t,
    )


def segment_orientation(segment):
    return "horizontal" if abs(segment["x2"] - segment["x1"]) >= abs(segment["y2"] - segment["y1"]) else "vertical"


def port_route_path(source, target, source_port, target_port, source_offset=0, target_offset=0, route_lane_offset=0):
    sx, sy = port_point(source, source_port, offset=source_offset)
    ex, ey = port_point(target, target_port, is_target=True, offset=target_offset)
    segments = []

    if source_port in {"left", "right"} and target_port in {"left", "right"}:
        if abs(sy - ey) <= PORT_SPACING:
            segments = [make_segment(sx, sy, ex, ey, "label")]
            return f"M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}", ((sx + ex) / 2, min(sy, ey) - LABEL_SEGMENT_CLEARANCE), segments
        mid_x = (sx + ex) / 2
        if route_lane_offset:
            low = min(sx, ex) + 32
            high = max(sx, ex) - 32
            if low < high:
                mid_x = clamp(mid_x + route_lane_offset, low, high)
        bend1 = 14 if mid_x >= sx else -14
        bend2 = 14 if ex >= mid_x else -14
        vertical_bend = math.copysign(14, ey - sy)
        segments = [
            make_segment(sx, sy, mid_x, sy, "branch"),
            make_segment(mid_x, sy, mid_x, ey, "branch"),
            make_segment(mid_x, ey, ex, ey, "label"),
        ]
        path = (
            f"M {sx:.1f} {sy:.1f} H {mid_x - bend1:.1f} "
            f"Q {mid_x:.1f} {sy:.1f} {mid_x:.1f} {sy + vertical_bend:.1f} "
            f"V {ey - vertical_bend:.1f} "
            f"Q {mid_x:.1f} {ey:.1f} {mid_x + bend2:.1f} {ey:.1f} H {ex:.1f}"
        )
        return path, ((mid_x + ex) / 2, ey - LABEL_SEGMENT_CLEARANCE), segments

    if source_port in {"top", "bottom"} and target_port in {"top", "bottom"}:
        direction = -1 if source_port == "top" else 1
        target_direction = -1 if target_port == "top" else 1
        mid_y = sy + direction * max(58, abs(sy - ey) / 2)
        if source_port != target_port:
            mid_y = (sy + ey) / 2
        bend1 = 14 * direction
        bend2 = 14 * target_direction
        horizontal_bend = 14 if ex >= sx else -14
        segments = [
            make_segment(sx, sy, sx, mid_y, "label"),
            make_segment(sx, mid_y, ex, mid_y, "branch"),
            make_segment(ex, mid_y, ex, ey, "entry"),
        ]
        path = (
            f"M {sx:.1f} {sy:.1f} V {mid_y - bend1:.1f} "
            f"Q {sx:.1f} {mid_y:.1f} {sx + horizontal_bend:.1f} {mid_y:.1f} "
            f"H {ex - horizontal_bend:.1f} "
            f"Q {ex:.1f} {mid_y:.1f} {ex:.1f} {mid_y - bend2:.1f} V {ey:.1f}"
        )
        return path, (sx, (sy + mid_y) / 2), segments

    if source_port in {"left", "right"}:
        if target_port in {"top", "bottom"} and abs(sx - ex) > 40:
            direction = 1 if sx > ex else -1
            mid_x = ex + direction * ROUTE_LANE_SPACING
            target_direction = -1 if target_port == "top" else 1
            approach_y = ey + target_direction * ROUTE_LANE_SPACING
            horizontal_bend = 14 if mid_x >= sx else -14
            vertical_bend = 14 if approach_y >= sy else -14
            exit_bend = 14 if ex >= mid_x else -14
            target_bend = 14 * target_direction
            segments = [
                make_segment(sx, sy, mid_x, sy, "label"),
                make_segment(mid_x, sy, mid_x, approach_y, "branch"),
                make_segment(mid_x, approach_y, ex, approach_y, "branch"),
                make_segment(ex, approach_y, ex, ey, "entry"),
            ]
            path = (
                f"M {sx:.1f} {sy:.1f} H {mid_x - horizontal_bend:.1f} "
                f"Q {mid_x:.1f} {sy:.1f} {mid_x:.1f} {sy + vertical_bend:.1f} "
                f"V {approach_y - vertical_bend:.1f} "
                f"Q {mid_x:.1f} {approach_y:.1f} {mid_x + exit_bend:.1f} {approach_y:.1f} "
                f"H {ex - exit_bend:.1f} "
                f"Q {ex:.1f} {approach_y:.1f} {ex:.1f} {approach_y - target_bend:.1f} V {ey:.1f}"
            )
            return path, ((sx + mid_x) / 2, sy - LABEL_SEGMENT_CLEARANCE), segments
        mid_x = ex
        horizontal_bend = 14 if mid_x >= sx else -14
        vertical_bend = 14 if ey >= sy else -14
        segments = [
            make_segment(sx, sy, mid_x, sy, "label"),
            make_segment(mid_x, sy, ex, ey, "entry"),
        ]
        path = (
            f"M {sx:.1f} {sy:.1f} H {mid_x - horizontal_bend:.1f} "
            f"Q {mid_x:.1f} {sy:.1f} {mid_x:.1f} {sy + vertical_bend:.1f} V {ey:.1f}"
        )
        return path, ((sx + mid_x) / 2, sy - LABEL_SEGMENT_CLEARANCE), segments

    mid_y = ey + route_lane_offset
    vertical_bend = 14 if mid_y >= sy else -14
    horizontal_bend = 14 if ex >= sx else -14
    if route_lane_offset:
        target_bend = 14 if ey >= mid_y else -14
        segments = [
            make_segment(sx, sy, sx, mid_y, "label"),
            make_segment(sx, mid_y, ex, mid_y, "branch"),
            make_segment(ex, mid_y, ex, ey, "entry"),
        ]
        path = (
            f"M {sx:.1f} {sy:.1f} V {mid_y - vertical_bend:.1f} "
            f"Q {sx:.1f} {mid_y:.1f} {sx + horizontal_bend:.1f} {mid_y:.1f} "
            f"H {ex - horizontal_bend:.1f} "
            f"Q {ex:.1f} {mid_y:.1f} {ex:.1f} {mid_y + target_bend:.1f} V {ey:.1f}"
        )
    else:
        segments = [
            make_segment(sx, sy, sx, mid_y, "label"),
            make_segment(sx, mid_y, ex, ey, "entry"),
        ]
        path = (
            f"M {sx:.1f} {sy:.1f} V {mid_y - vertical_bend:.1f} "
            f"Q {sx:.1f} {mid_y:.1f} {sx + horizontal_bend:.1f} {mid_y:.1f} H {ex:.1f}"
        )
    return path, (sx, (sy + mid_y) / 2), segments


def connector_path(a, b, route):
    acx, acy = center(a)
    bcx, bcy = center(b)
    if route == "top":
        sx, sy = shape_port_point(a, "top", gap=CONNECTOR_GAP)
        ex, ey = arrow_endpoint(b, "top")
        mid_y = min(sy, ey) - 58
        direction = 1 if ex >= sx else -1
        segments = [
            make_segment(sx, sy, sx, mid_y, "exit"),
            make_segment(sx, mid_y, ex, mid_y, "label"),
            make_segment(ex, mid_y, ex, ey, "entry"),
        ]
        label = ((sx + ex) / 2, mid_y - LABEL_SEGMENT_CLEARANCE)
        path = f"M {sx:.1f} {sy:.1f} V {mid_y + 12:.1f} Q {sx:.1f} {mid_y:.1f} {sx + direction * 12:.1f} {mid_y:.1f} H {ex - direction * 12:.1f} Q {ex:.1f} {mid_y:.1f} {ex:.1f} {mid_y + 12:.1f} V {ey:.1f}"
        return path, label, segments
    if route == "bottom":
        backtrack = acx > bcx + 12
        sx, sy = shape_port_point(a, "bottom", gap=CONNECTOR_GAP)
        if backtrack:
            ex, ey = arrow_endpoint(b, "right")
            if bcy > acy:
                sx, sy = shape_port_point(a, "bottom", gap=CONNECTOR_GAP)
                sx = a["x"] + a["width"] * 0.25
                segments = [
                    make_segment(sx, sy, sx, ey, "exit"),
                    make_segment(sx, ey, ex, ey, "label"),
                ]
                label = ((sx + ex) / 2, ey - LABEL_SEGMENT_CLEARANCE)
                path = (
                    f"M {sx:.1f} {sy:.1f} V {ey - 12:.1f} "
                    f"Q {sx:.1f} {ey:.1f} {sx - 12:.1f} {ey:.1f} H {ex:.1f}"
                )
                return path, label, segments
            mid_y = max(sy, b["y"] + b["height"]) + 34
            approach_x = ex + 32
            segments = [
                make_segment(sx, sy, sx, mid_y, "exit"),
                make_segment(sx, mid_y, approach_x, mid_y, "label"),
                make_segment(approach_x, mid_y, approach_x, ey, "entry"),
                make_segment(approach_x, ey, ex, ey, "entry"),
            ]
            label = ((sx + approach_x) / 2, mid_y + LABEL_SEGMENT_CLEARANCE)
            path = f"M {sx:.1f} {sy:.1f} V {mid_y - 12:.1f} Q {sx:.1f} {mid_y:.1f} {sx - 12:.1f} {mid_y:.1f} H {approach_x + 12:.1f} Q {approach_x:.1f} {mid_y:.1f} {approach_x:.1f} {mid_y - 12:.1f} V {ey + 12:.1f} Q {approach_x:.1f} {ey:.1f} {approach_x - 12:.1f} {ey:.1f} H {ex:.1f}"
            return path, label, segments
        if bcy > acy and a.get("rank") is not None and a.get("rank") == b.get("rank"):
            ex, ey = arrow_endpoint(b, "top")
            segments = [make_segment(sx, sy, sx, ey, "label")]
            path = f"M {sx:.1f} {sy:.1f} V {ey:.1f}"
            if abs(sx - ex) >= 24:
                segments.append(make_segment(sx, ey, ex, ey, "entry"))
                path += f" H {ex:.1f}"
            return path, (sx, (sy + ey) / 2), segments
        ex, ey = arrow_endpoint(b, "bottom")
        if bcy > acy and abs(sx - ex) < 24:
            segments = [make_segment(sx, sy, sx, ey, "label")]
            path = f"M {sx:.1f} {sy:.1f} V {ey:.1f}"
            if abs(sx - ex) >= 24:
                segments.append(make_segment(sx, ey, ex, ey, "entry"))
                path += f" H {ex:.1f}"
            return path, (sx, (sy + ey) / 2), segments
        mid_y = max(sy, b["y"] + b["height"] if bcy > acy else ey) + 34
        segments = [
            make_segment(sx, sy, sx, mid_y, "exit"),
            make_segment(sx, mid_y, ex, mid_y, "label"),
            make_segment(ex, mid_y, ex, ey, "entry"),
        ]
        label = ((sx + ex) / 2, mid_y + LABEL_SEGMENT_CLEARANCE)
        path = f"M {sx:.1f} {sy:.1f} V {mid_y - 12:.1f} Q {sx:.1f} {mid_y:.1f} {sx + 12:.1f} {mid_y:.1f} H {ex - 12:.1f} Q {ex:.1f} {mid_y:.1f} {ex:.1f} {mid_y - 12:.1f} V {ey:.1f}"
        return path, label, segments

    if acx <= bcx:
        sx, sy = shape_port_point(a, "right", gap=CONNECTOR_GAP)
        ex, ey = arrow_endpoint(b, "left")
    else:
        sx, sy = shape_port_point(a, "left", gap=CONNECTOR_GAP)
        ex, ey = arrow_endpoint(b, "right")
    dx = ex - sx
    mid_x = sx + dx / 2
    if abs(sy - ey) < 10:
        segments = [make_segment(sx, sy, ex, ey, "label")]
        return f"M {sx:.1f} {sy:.1f} H {ex:.1f}", ((sx + ex) / 2, sy - LABEL_SEGMENT_CLEARANCE), segments
    bend = 14 if dx >= 0 else -14
    segments = [
        make_segment(sx, sy, mid_x, sy, "exit"),
        make_segment(mid_x, sy, mid_x, ey, "label"),
        make_segment(mid_x, ey, ex, ey, "entry"),
    ]
    return (
        f"M {sx:.1f} {sy:.1f} H {mid_x - bend:.1f} "
        f"Q {mid_x:.1f} {sy:.1f} {mid_x:.1f} {sy + math.copysign(14, ey - sy):.1f} "
        f"V {ey - math.copysign(14, ey - sy):.1f} "
        f"Q {mid_x:.1f} {ey:.1f} {mid_x + bend:.1f} {ey:.1f} H {ex:.1f}"
    ), (mid_x, min(sy, ey) - LABEL_SEGMENT_CLEARANCE), segments
