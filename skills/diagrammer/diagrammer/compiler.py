#!/usr/bin/env python3
"""Compile a small diagram definition into layout, review, and HTML/SVG artifacts."""

try:
    from . import shapes
    from .contracts import AnnotationBox, DiagramLayout, LabelBox, NodeBox, RoutedEdge
    from .edge_labels import (
        box_center,
        distance_point_to_segment,
        inline_label_metrics,
        label_anchor_for_edge,
        label_box,
        preferred_label_segment,
    )
    from .port_geometry import (
        anchor,
        arrow_endpoint,
        port_point,
        rectangular_port_point,
        shape_perimeter_point,
        shape_port_point,
        side_axis,
        side_direction,
    )
    from .routing import (
        connector_path,
        default_ports_for_edge,
        dominant_horizontal_approach,
        edge_sort_coordinate,
        facing_side,
        layout_edges,
        max_segment_length,
        normalize_ports_for_geometry,
        port_route_path,
        resolved_ports_for_edge,
        route_lane_offsets,
        route_length,
        segment_length,
        segment_orientation,
        segment_point,
        shared_endpoint_port_offsets,
        spaced_port_offsets,
    )
    from .layout import (
        WIDTH,
        HEIGHT,
        MARGIN_X,
        MARGIN_Y,
        LANE_GAP,
        RANK_GAP,
        NODE_MIN_W,
        NODE_MAX_W,
        NODE_BASE_H,
        LINE_H,
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_CHAR_W,
        PAD_X,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_MAX_LINES,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        PORT_SPACING,
        ROUTE_LANE_SPACING,
        ARROW_TIP_OVERHANG,
        CONNECTOR_GAP,
        CONNECTOR_GAP_TOLERANCE,
        KNOWN_KINDS,
        KNOWN_EDGE_KINDS,
        KNOWN_ROUTES,
        KNOWN_PORTS,
        LABEL_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        DIRECT_LABEL_CLEARANCE,
        CANVAS_PAD_X,
        CANVAS_PAD_TOP,
        CANVAS_PAD_BOTTOM,
        LOCAL_TARGET_GAP,
        EXCESS_CONNECTOR_SEGMENT,
        text_width,
        wrap_label,
        wrap_text_to_width,
        candidate_line_groups,
        wrap_edge_label,
        shape_text_width,
        node_size,
        assign_positions,
        center,
        clamp,
        compactible_sink_target,
        resolve_compacted_x,
        compact_leaf_sink_targets,
        annotation_layout,
        overlaps,
        move_box,
        content_bounds,
        trimmed_canvas,
    )
    from .review import (
        inflated,
        segment_intersects_box,
        edge_label_distance,
        edge_label_visible_run,
        label_distance_limit,
        point_distance,
        segment_span_overlap,
        segment_crossing_point,
        point_near_segment_endpoint,
        internal_branch_segments,
        edge_endpoint_gaps,
        excess_span_review_applies,
        node_text_fit,
        analyze_layout,
        relabel_edges_to_anchors,
        nudge_label_from_obstacle,
        autofix_layout,
    )
    from .renderer import (
        esc,
        legend_item_summary,
        queue_text_layout,
        render_annotation,
        render_client,
        render_cloud,
        render_db,
        render_diamond,
        render_document,
        render_edge,
        render_edge_label_mask,
        render_edge_label_text,
        render_html,
        render_legend_symbol,
        render_queue,
        render_service,
        render_shape_legend,
        render_shield,
        render_user,
        shape_legend_items,
        shape_legend_size,
        shape_text_area,
        text_lines,
        text_stack_layout,
    )
except ImportError:  # pragma: no cover - script execution fallback
    import shapes
    from contracts import AnnotationBox, DiagramLayout, LabelBox, NodeBox, RoutedEdge  # type: ignore
    from port_geometry import (  # type: ignore
        anchor,
        arrow_endpoint,
        port_point,
        rectangular_port_point,
        shape_perimeter_point,
        shape_port_point,
        side_axis,
        side_direction,
    )
    from edge_labels import (  # type: ignore
        box_center,
        distance_point_to_segment,
        inline_label_metrics,
        label_anchor_for_edge,
        label_box,
        preferred_label_segment,
    )
    from routing import (  # type: ignore
        connector_path,
        default_ports_for_edge,
        dominant_horizontal_approach,
        edge_sort_coordinate,
        facing_side,
        layout_edges,
        max_segment_length,
        normalize_ports_for_geometry,
        port_route_path,
        resolved_ports_for_edge,
        route_lane_offsets,
        route_length,
        segment_length,
        segment_orientation,
        segment_point,
        shared_endpoint_port_offsets,
        spaced_port_offsets,
    )
    from layout import (  # type: ignore
        WIDTH,
        HEIGHT,
        MARGIN_X,
        MARGIN_Y,
        LANE_GAP,
        RANK_GAP,
        NODE_MIN_W,
        NODE_MAX_W,
        NODE_BASE_H,
        LINE_H,
        CHAR_W,
        DETAIL_CHAR_W,
        EDGE_CHAR_W,
        PAD_X,
        EDGE_LABEL_PAD_X,
        EDGE_LABEL_INLINE_PAD_X,
        EDGE_LABEL_PAD_Y,
        EDGE_LABEL_LINE_H,
        EDGE_LABEL_MIN_W,
        EDGE_LABEL_SEGMENT_PAD,
        EDGE_LABEL_MAX_LINES,
        EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH,
        EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH,
        EDGE_VERTICAL_LABEL_MAX_WIDTH,
        EDGE_FLOATING_LABEL_MAX_WIDTH,
        EDGE_INLINE_MIN_SEGMENT,
        EDGE_INLINE_MIN_READABLE,
        EDGE_INLINE_MIN_VISIBLE_RUN,
        PORT_SPACING,
        ROUTE_LANE_SPACING,
        ARROW_TIP_OVERHANG,
        CONNECTOR_GAP,
        CONNECTOR_GAP_TOLERANCE,
        KNOWN_KINDS,
        KNOWN_EDGE_KINDS,
        KNOWN_ROUTES,
        KNOWN_PORTS,
        LABEL_CLEARANCE,
        LABEL_SEGMENT_CLEARANCE,
        DIRECT_LABEL_CLEARANCE,
        CANVAS_PAD_X,
        CANVAS_PAD_TOP,
        CANVAS_PAD_BOTTOM,
        LOCAL_TARGET_GAP,
        EXCESS_CONNECTOR_SEGMENT,
        text_width,
        wrap_label,
        wrap_text_to_width,
        candidate_line_groups,
        wrap_edge_label,
        shape_text_width,
        node_size,
        assign_positions,
        center,
        clamp,
        compactible_sink_target,
        resolve_compacted_x,
        compact_leaf_sink_targets,
        annotation_layout,
        overlaps,
        move_box,
        content_bounds,
        trimmed_canvas,
    )
    from review import (  # type: ignore
        inflated,
        segment_intersects_box,
        edge_label_distance,
        edge_label_visible_run,
        label_distance_limit,
        point_distance,
        segment_span_overlap,
        segment_crossing_point,
        point_near_segment_endpoint,
        internal_branch_segments,
        edge_endpoint_gaps,
        excess_span_review_applies,
        node_text_fit,
        analyze_layout,
        relabel_edges_to_anchors,
        nudge_label_from_obstacle,
        autofix_layout,
    )
    from renderer import (  # type: ignore
        esc,
        legend_item_summary,
        queue_text_layout,
        render_annotation,
        render_client,
        render_cloud,
        render_db,
        render_diamond,
        render_document,
        render_edge,
        render_edge_label_mask,
        render_edge_label_text,
        render_html,
        render_legend_symbol,
        render_queue,
        render_service,
        render_shape_legend,
        render_shield,
        render_user,
        shape_legend_items,
        shape_legend_size,
        shape_text_area,
        text_lines,
        text_stack_layout,
    )



KNOWN_TEMPLATES = {"system-left-to-right"}

def read_definition(path):
    try:
        from .cli import read_definition as cli_read_definition
    except ImportError:  # pragma: no cover - script execution fallback
        from cli import read_definition as cli_read_definition  # type: ignore

    return cli_read_definition(path)


def review_layout(layout, warnings):
    return analyze_layout(layout, warnings)


def review_with_autofix(layout, warnings):
    before = analyze_layout(layout, warnings)
    autofix = autofix_layout(layout)
    after = analyze_layout(layout, warnings)
    after["autofix"] = autofix
    after["preAutofix"] = {"score": before["score"], "metrics": before["metrics"], "warningCount": before["warningCount"]}
    return after



def compile_diagram(defn):
    warnings = []
    template = defn.get("template", "system-left-to-right")
    if template not in KNOWN_TEMPLATES:
        warnings.append({"code": "unknown-template", "message": f"unknown template {template!r}; using system-left-to-right"})
        template = "system-left-to-right"
    nodes, boxes = assign_positions(defn, warnings)
    annotations = annotation_layout(defn)
    initial_edges = layout_edges(defn, boxes, warnings)
    layout_fixes = compact_leaf_sink_targets(defn, boxes, initial_edges, annotations)
    edges = layout_edges(defn, boxes, warnings) if layout_fixes else initial_edges
    layout = DiagramLayout(
        title=defn.get("title", "System diagram"),
        subtitle=defn.get("subtitle", ""),
        template=template,
        canvas={"width": WIDTH, "height": HEIGHT},
        boxes=boxes,
        edges=edges,
        annotations=annotations,
        assumptions=defn.get("assumptions", []),
        notImplied=defn.get("notImplied", []),
    )
    if layout_fixes:
        layout["_layoutFixes"] = layout_fixes
        layout["_compactedNodes"] = [node["node"] for fix in layout_fixes for node in fix.get("nodes", [])]
    bounds = content_bounds(layout)
    layout["canvas"].update({
        "width": max(WIDTH, int(bounds["x"] + bounds["width"] + CANVAS_PAD_X)),
        "height": max(HEIGHT, int(bounds["y"] + bounds["height"] + CANVAS_PAD_BOTTOM)),
    })
    review = review_with_autofix(layout, warnings)
    html = render_html(defn, layout, review)
    return layout.to_dict(), review, html


def main(argv=None):
    try:
        from .cli import main as cli_main
    except ImportError:  # pragma: no cover - script execution fallback
        from cli import main as cli_main  # type: ignore

    return cli_main(argv)


if __name__ == "__main__":
    main()
