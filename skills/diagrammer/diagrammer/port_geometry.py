"""Connector port geometry helpers for diagrammer shapes."""

import math

try:
    from . import shapes
except ImportError:  # pragma: no cover - script execution fallback
    import shapes  # type: ignore


CONNECTOR_GAP = 10


def center(box):
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def clamp(value, low, high):
    return max(low, min(high, value))


def anchor(box, side, offset=0):
    return shape_port_point(box, side, offset, gap=0)


def side_axis(side):
    return "y" if side in {"left", "right"} else "x"


def side_direction(side):
    if side == "left":
        return -1, 0
    if side == "right":
        return 1, 0
    if side == "top":
        return 0, -1
    return 0, 1


def rectangular_port_point(box, side, offset=0):
    if side == "left":
        inset = min(24, max(6, box["height"] * 0.2))
        return box["x"], clamp(box["y"] + box["height"] / 2 + offset, box["y"] + inset, box["y"] + box["height"] - inset)
    if side == "right":
        inset = min(24, max(6, box["height"] * 0.2))
        return box["x"] + box["width"], clamp(box["y"] + box["height"] / 2 + offset, box["y"] + inset, box["y"] + box["height"] - inset)
    if side == "top":
        inset = min(24, max(6, box["width"] * 0.2))
        return clamp(box["x"] + box["width"] / 2 + offset, box["x"] + inset, box["x"] + box["width"] - inset), box["y"]
    inset = min(24, max(6, box["width"] * 0.2))
    return clamp(box["x"] + box["width"] / 2 + offset, box["x"] + inset, box["x"] + box["width"] - inset), box["y"] + box["height"]


def ellipse_side_point(cx, cy, rx, ry, side, offset):
    if side in {"left", "right"}:
        dy = clamp(offset, -ry + 2, ry - 2)
        x_radius = rx * math.sqrt(max(0, 1 - (dy * dy) / (ry * ry)))
        x = cx - x_radius if side == "left" else cx + x_radius
        return x, cy + dy
    dx = clamp(offset, -rx + 2, rx - 2)
    y_radius = ry * math.sqrt(max(0, 1 - (dx * dx) / (rx * rx)))
    y = cy - y_radius if side == "top" else cy + y_radius
    return cx + dx, y


def diamond_port_point(box, side, offset):
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    cx, cy = x + w / 2, y + h / 2
    if side in {"left", "right"}:
        dy = clamp(offset, -h / 2 + 8, h / 2 - 8)
        half_width = (w / 2) * (1 - abs(dy) / (h / 2))
        return (cx - half_width if side == "left" else cx + half_width), cy + dy
    dx = clamp(offset, -w / 2 + 8, w / 2 - 8)
    half_height = (h / 2) * (1 - abs(dx) / (w / 2))
    return cx + dx, (cy - half_height if side == "top" else cy + half_height)


def shape_perimeter_point(box, side, offset=0):
    shape = box.get("shape") or shapes.resolve_node_shape(box)
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]
    if shape == "horizontal-cylinder":
        if side == "left":
            return ellipse_side_point(x + h / 2, y + h / 2, h / 2, h / 2, "left", offset)
        if side == "right":
            cap_rx = h * 0.24
            return ellipse_side_point(x + w - cap_rx, y + h / 2, cap_rx, h / 2, "right", offset)
    if shape == "database-cylinder":
        if side in {"top", "bottom"}:
            ey = min(82, max(58, h * 0.32))
            cy = y + ey / 2 if side == "top" else y + h - ey / 2
            return ellipse_side_point(x + w / 2, cy, w / 2, ey / 2, side, offset)
    if shape == "diamond":
        return diamond_port_point(box, side, offset)
    if shape == "cloud":
        # Approximate the visible cloud outline; keep ports away from the lobes'
        # bounding-box extremes where arrows look detached.
        if side == "left":
            return x + w * 0.04, clamp(y + h / 2 + offset, y + h * 0.36, y + h * 0.84)
        if side == "right":
            return x + w * 0.96, clamp(y + h / 2 + offset, y + h * 0.36, y + h * 0.84)
        if side == "top":
            return clamp(x + w / 2 + offset, x + w * 0.24, x + w * 0.82), y + h * 0.08
        return clamp(x + w / 2 + offset, x + w * 0.14, x + w * 0.86), y + h * 0.92
    if shape == "shield":
        if side in {"left", "right"}:
            return (x + w * (0.12 if side == "left" else 0.88), clamp(y + h / 2 + offset, y + h * 0.20, y + h * 0.74))
        if side == "top":
            return clamp(x + w / 2 + offset, x + w * 0.32, x + w * 0.68), y
        return clamp(x + w / 2 + offset, x + w * 0.38, x + w * 0.62), y + h
    return rectangular_port_point(box, side, offset)


def shape_port_point(box, side, offset=0, gap=0):
    px, py = shape_perimeter_point(box, side, offset)
    dx, dy = side_direction(side)
    return px + dx * gap, py + dy * gap


def arrow_endpoint(box, side, offset=0):
    return shape_port_point(box, side, offset=offset, gap=CONNECTOR_GAP)


def port_point(box, side, is_target=False, offset=0):
    if is_target:
        return arrow_endpoint(box, side, offset=offset)
    return shape_port_point(box, side, offset=offset, gap=CONNECTOR_GAP)
