import unittest
import contextlib
import io
import sys
import json
import re
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagrammer import cli, compiler, edge_labels, example_gate, routing, shapes, validate_svg


class CLICompatibilityTests(unittest.TestCase):
    def test_cli_owns_definition_io_while_compiler_exports_compatibility_wrappers(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "simple" / "basic-web-app.def.json"

        self.assertEqual(compiler.read_definition(fixture), cli.read_definition(fixture))

        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                compiler.main([str(fixture), "--out-dir", tmp])

            self.assertIn("diagram.layout.json", stdout.getvalue())
            self.assertTrue((Path(tmp) / "diagram.layout.json").exists())
            self.assertTrue((Path(tmp) / "diagram.review.json").exists())
            self.assertTrue((Path(tmp) / "diagram.html").exists())


class ConnectorRoutingTests(unittest.TestCase):
    def test_edge_label_helpers_keep_compatibility_imports(self):
        self.assertIs(routing.place_label_box, edge_labels.place_label_box)
        self.assertIs(routing.label_anchor_for_edge, edge_labels.label_anchor_for_edge)
        self.assertIs(compiler.label_box, edge_labels.label_box)

    def test_stress_fixtures_compile_with_tracked_review_warnings(self):
        expected_warning_codes = {
            "incident-response.def.json": ["connector-node-intrusion", "long-bottom-return-route"],
            "mobile-onboarding.def.json": ["label-overlap", "label-overlap", "connector-node-intrusion"],
            "ticketmaster-system.def.json": ["long-bottom-return-route", "connector-node-intrusion", "connector-node-intrusion", "connector-node-intrusion"],
            "warehouse-ingestion.def.json": ["label-overlap", "shape-text-overflow"],
        }
        stress_dir = Path(__file__).resolve().parents[1] / "fixtures" / "stress"

        for fixture_name, expected_codes in expected_warning_codes.items():
            with self.subTest(fixture=fixture_name):
                definition = json.loads((stress_dir / fixture_name).read_text(encoding="utf-8"))

                layout, review, html = compiler.compile_diagram(definition)

                self.assertGreater(len(layout["boxes"]), 0)
                self.assertGreater(len(layout["edges"]), 0)
                self.assertIn("<svg", html)
                self.assertIn("metrics", review)
                self.assertEqual([warning["code"] for warning in review["warnings"]], expected_codes)
                self.assertNotIn("unknown-kind", expected_codes)
                self.assertNotIn("unknown-shape", expected_codes)

    def test_dense_ticketmaster_layout_expands_before_labels_collide_with_nodes(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "stress" / "ticketmaster-system.def.json"
        definition = json.loads(fixture.read_text(encoding="utf-8"))

        layout, review, _html = compiler.compile_diagram(definition)

        self.assertGreater(layout["canvas"]["width"], compiler.WIDTH)
        self.assertGreater(layout["canvas"]["height"], compiler.HEIGHT)
        self.assertEqual(review["metrics"]["labelOverlapCount"], 0)
        self.assertNotIn("label-overlap", {warning["code"] for warning in review["warnings"]})
        for edge in layout["edges"]:
            label = edge.get("labelBox")
            if not label:
                continue
            for node in layout["boxes"].values():
                self.assertFalse(
                    compiler.overlaps(label, node, padding=0),
                    f"{edge['id']} label overlaps {node['id']}",
                )

    def test_shape_registry_maps_semantic_kinds_to_figjam_primitives(self):
        self.assertEqual(shapes.resolve_node_shape({"kind": "queue", "label": "Payment Events"}), "horizontal-cylinder")
        self.assertEqual(shapes.resolve_node_shape({"kind": "external", "label": "Payment Provider"}), "cloud")
        self.assertEqual(shapes.resolve_node_shape({"kind": "client", "label": "Customer"}), "user")
        self.assertEqual(shapes.resolve_node_shape({"kind": "service", "label": "Risk Review"}), "shield")
        self.assertEqual(shapes.resolve_node_shape({"kind": "service", "label": "Ledger Service"}), "rounded-rectangle")

    def test_internal_layout_contracts_keep_dict_compatibility(self):
        definition = {
            "title": "typed contracts",
            "nodes": [
                {"id": "a", "label": "A", "rank": 0, "lane": 0},
                {"id": "b", "label": "B", "rank": 1, "lane": 0},
            ],
            "edges": [{"from": "a", "to": "b", "label": "request", "route": "direct"}],
        }

        _nodes, boxes = compiler.assign_positions(definition, [])
        edges = compiler.layout_edges(definition, boxes, [])
        layout, review, _html = compiler.compile_diagram(definition)

        self.assertIsInstance(boxes["a"], compiler.NodeBox)
        self.assertIsInstance(edges[0], compiler.RoutedEdge)
        self.assertIsInstance(edges[0]["labelBox"], compiler.LabelBox)
        self.assertEqual(boxes["a"]["id"], boxes["a"].to_dict()["id"])
        self.assertEqual(edges[0].to_dict()["from"], "a")
        self.assertIsInstance(layout["boxes"]["a"], dict)
        self.assertIsInstance(layout["edges"][0]["labelBox"], dict)
        self.assertEqual(review["warningCount"], 0)

    def test_rendered_primary_label_size_satisfies_validator_default(self):
        html = compiler.render_html(
            {"title": "label contract"},
            {"boxes": {}, "edges": [], "annotations": [], "assumptions": [], "notImplied": []},
            {"score": 100, "warnings": [], "metrics": {}},
        )

        self.assertRegex(html, r"\.label \{ font-size: 20px;")

    def test_box_overlap_warning_reduces_review_score(self):
        layout = {
            "boxes": {
                "left": {
                    "id": "left",
                    "type": "node",
                    "kind": "service",
                    "shape": "rounded-rectangle",
                    "label": "Left",
                    "labelLines": ["Left"],
                    "detailLines": [],
                    "x": 100,
                    "y": 100,
                    "width": 220,
                    "height": 120,
                },
                "right": {
                    "id": "right",
                    "type": "node",
                    "kind": "service",
                    "shape": "rounded-rectangle",
                    "label": "Right",
                    "labelLines": ["Right"],
                    "detailLines": [],
                    "x": 180,
                    "y": 140,
                    "width": 220,
                    "height": 120,
                },
            },
            "edges": [],
            "annotations": [],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("box-overlap", {warning["code"] for warning in review["warnings"]})
        self.assertEqual(review["metrics"]["boxOverlapCount"], 1)
        self.assertLess(review["score"], 100)

    def test_validator_allows_renderer_system_symbol_shape_set(self):
        html = compiler.render_html(
            {"title": "semantic"},
            {
                "boxes": {
                    "user": {
                        "id": "user",
                        "type": "node",
                        "kind": "client",
                        "shape": "user",
                        "label": "User",
                        "labelLines": ["User"],
                        "detailLines": [],
                        "x": 100,
                        "y": 100,
                        "width": 180,
                        "height": 120,
                    },
                    "queue": {
                        "id": "queue",
                        "type": "node",
                        "kind": "queue",
                        "shape": "horizontal-cylinder",
                        "label": "Queue",
                        "labelLines": ["Queue"],
                        "detailLines": [],
                        "x": 330,
                        "y": 100,
                        "width": 220,
                        "height": 96,
                    },
                    "decision": {
                        "id": "decision",
                        "type": "node",
                        "kind": "decision",
                        "shape": "diamond",
                        "label": "Decision",
                        "labelLines": ["Decision"],
                        "detailLines": [],
                        "x": 610,
                        "y": 100,
                        "width": 220,
                        "height": 112,
                    },
                },
                "edges": [],
                "annotations": [],
                "assumptions": [],
                "notImplied": [],
            },
            {"score": 100, "warnings": [], "metrics": {}},
        )
        parser = validate_svg.DiagramParser()
        parser.feed(html)

        warnings = validate_svg.check_style(parser, html, validate_svg.class_font_sizes(parser.styles), 20)

        self.assertNotIn("many shape families", "\n".join(warnings))

    def test_validator_label_spacing_matches_review_overlap_tolerance(self):
        source = '''<svg>
<rect class="connector-label-mask" x="10" y="10" width="42" height="24"/>
<rect class="connector-label-mask" x="10" y="34" width="42" height="24"/>
</svg>'''

        self.assertEqual(validate_svg.check_connector_label_spacing(source), [])

    def test_validator_warns_on_raw_connector_labels_and_masks(self):
        source = '''<svg>
<text class="flow-label" x="10" y="20">promote</text>
<text class="arrow-label" x="10" y="40">review</text>
<rect class="label-mask" x="4" y="4" width="80" height="24"/>
</svg>'''

        warnings = validate_svg.check_connector_labels(source)

        self.assertIn("raw flow-label text detected", "\n".join(warnings))
        self.assertIn("raw arrow-label text detected", "\n".join(warnings))
        self.assertIn("ad hoc label-mask detected", "\n".join(warnings))

    def test_validator_warns_on_large_markers_heavy_exception_strokes_and_return_routes(self):
        source = '''<svg><style>
.exception-flow { stroke: #d97706; stroke-width: 4; fill: none; }
</style>
<defs>
  <marker id="arrow-amber" markerWidth="12" markerHeight="12">
    <path d="M2 2 L10 6 L2 10" fill="none"/>
  </marker>
</defs>
<path class="exception-flow" marker-end="url(#arrow-amber)" d="M1250 425 V512 Q1250 532 1230 532 H902 Q882 532 882 560"/>
</svg>'''

        warnings = validate_svg.check_connectors(source)
        joined = "\n".join(warnings)

        self.assertIn("arrow marker 'arrow-amber' is large", joined)
        self.assertIn("exception/warning connector stroke is heavy", joined)
        self.assertIn("long visual return route", joined)

    def test_validator_accepts_compact_connector_label_group(self):
        source = '''<svg><style>
.flow { stroke-width: 2.75px; }
</style>
<defs>
  <marker id="arrow" markerWidth="8" markerHeight="8">
    <path d="M1 1 L7 4 L1 7" fill="none"/>
  </marker>
</defs>
<path class="flow connector" marker-end="url(#arrow)" d="M10 40 H90"/>
<g class="connector-label">
  <rect class="connector-label-mask" x="38" y="26" width="32" height="20"/>
  <text x="42" y="41">ok</text>
</g>
</svg>'''

        self.assertEqual(validate_svg.check_connectors(source), [])
        self.assertEqual(validate_svg.check_connector_labels(source), [])

    def test_validator_warns_on_footer_prose_without_annotation_block(self):
        source = '''<svg>
<text class="note-title" x="20" y="720">Not every anomaly is automatically an exception.</text>
<text class="note" x="20" y="748">Gus treats it as a candidate until it has enough evidence and user-facing explanation.</text>
<text class="note" x="20" y="776">The queue asks for judgment; it does not silently change the vendor system.</text>
</svg>'''

        self.assertIn("footer notes read as long prose", "\n".join(validate_svg.check_footer_notes(source)))

    def test_compiler_stores_resolved_shape_metadata(self):
        definition = {
            "title": "shape metadata",
            "nodes": [
                {"id": "provider", "label": "Payment Provider", "kind": "external", "rank": 0, "lane": 0},
                {"id": "events", "label": "Payment Events", "kind": "queue", "rank": 1, "lane": 0},
            ],
            "edges": [{"from": "provider", "to": "events", "label": "webhook", "kind": "async", "route": "direct"}],
        }

        layout, review, _html = compiler.compile_diagram(definition)

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(layout["boxes"]["provider"]["shape"], "cloud")
        self.assertEqual(layout["boxes"]["events"]["shape"], "horizontal-cylinder")

    def test_shape_text_overflow_is_reviewed_against_usable_area(self):
        layout = {
            "boxes": {
                "provider": {
                    "id": "provider",
                    "type": "node",
                    "kind": "external",
                    "shape": "cloud",
                    "label": "Very Long External Payment Provider Name",
                    "detail": ["long account reconciliation detail"],
                    "labelLines": ["Very Long External Payment Provider Name"],
                    "detailLines": ["long account reconciliation detail"],
                    "x": 100,
                    "y": 100,
                    "width": 160,
                    "height": 80,
                }
            },
            "edges": [],
            "annotations": [],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("shape-text-overflow", {warning["code"] for warning in review["warnings"]})

    def test_cloud_text_fit_uses_rendered_baselines_not_outer_bounds(self):
        box = {
            "id": "payment",
            "type": "node",
            "kind": "external",
            "shape": "cloud",
            "label": "Payment Provider",
            "detail": ["authorize", "webhook"],
            "labelLines": ["Payment", "Provider"],
            "detailLines": ["authorize", "webhook"],
            "x": 100,
            "y": 100,
            "width": 250,
            "height": 170,
        }

        fit = compiler.node_text_fit(box)
        rendered = compiler.render_cloud(box)

        self.assertTrue(fit["fitsHeight"])
        self.assertGreater(fit["textBounds"]["y"], fit["area"]["y"])
        self.assertLessEqual(fit["textBounds"]["y"] + fit["textBounds"]["height"], fit["area"]["y"] + fit["area"]["height"])
        self.assertIn('y="235.5"', rendered)
        self.assertNotIn('y="285.', rendered)

    def test_shape_legend_is_added_only_for_semantic_shapes_that_need_explanation(self):
        semantic = {
            "boxes": {
                "provider": {"id": "provider", "kind": "external", "shape": "cloud", "label": "Provider", "labelLines": ["Provider"], "detail": [], "detailLines": [], "x": 100, "y": 100, "width": 250, "height": 136},
                "risk": {"id": "risk", "kind": "service", "shape": "shield", "label": "Risk", "labelLines": ["Risk"], "detail": [], "detailLines": [], "x": 400, "y": 100, "width": 180, "height": 118},
            },
            "edges": [],
            "annotations": [],
            "assumptions": [],
            "notImplied": [],
        }
        generic = {
            "boxes": {
                "service": {"id": "service", "kind": "service", "shape": "rounded-rectangle", "label": "Service", "labelLines": ["Service"], "detail": [], "detailLines": [], "x": 100, "y": 100, "width": 180, "height": 70}
            },
            "edges": [],
            "annotations": [],
            "assumptions": [],
            "notImplied": [],
        }

        self.assertIn("shape-legend", compiler.render_html({"title": "semantic"}, semantic, {"score": 100, "warnings": [], "metrics": {}}))
        self.assertNotIn("shape-legend", compiler.render_html({"title": "generic"}, generic, {"score": 100, "warnings": [], "metrics": {}}))

    def test_shape_legend_renders_shape_previews_not_generic_dots(self):
        semantic = {
            "boxes": {
                "operator": {"id": "operator", "kind": "operator", "shape": "user", "label": "Operator", "labelLines": ["Operator"], "detail": [], "detailLines": [], "x": 100, "y": 100, "width": 190, "height": 92},
                "provider": {"id": "provider", "kind": "external", "shape": "cloud", "label": "Provider", "labelLines": ["Provider"], "detail": [], "detailLines": [], "x": 360, "y": 100, "width": 250, "height": 136},
                "events": {"id": "events", "kind": "queue", "shape": "horizontal-cylinder", "label": "Events", "labelLines": ["Events"], "detail": [], "detailLines": [], "x": 620, "y": 100, "width": 250, "height": 96},
                "orders": {"id": "orders", "kind": "db", "shape": "database-cylinder", "label": "Orders", "labelLines": ["Orders"], "detail": [], "detailLines": [], "x": 880, "y": 100, "width": 220, "height": 110},
            },
            "edges": [],
            "annotations": [],
            "assumptions": [],
            "notImplied": [],
        }

        html = compiler.render_html({"title": "semantic"}, semantic, {"score": 100, "warnings": [], "metrics": {}})

        self.assertIn("legend-symbol-user", html)
        self.assertIn("legend-symbol-cloud", html)
        self.assertIn("legend-symbol-horizontal-cylinder", html)
        self.assertIn("legend-symbol-database-cylinder", html)
        self.assertIn(">Legend</text>", html)
        self.assertIn(">external provider / cloud system</text>", html)
        self.assertIn(">queue, stream, or buffer</text>", html)
        self.assertIn(">database or source of truth</text>", html)
        self.assertNotIn(">Shape legend</text>", html)
        self.assertNotIn("legend-row-label", html)
        self.assertNotIn(">Cloud</tspan>", html)
        self.assertNotIn(">Horizontal cylinder</tspan>", html)
        self.assertNotIn("legend-dot", html)
        panel_width = float(re.search(r'class="legend-panel"[^>]* width="([0-9.]+)"', html).group(1))
        panel_height = float(re.search(r'class="legend-panel"[^>]* height="([0-9.]+)"', html).group(1))
        self.assertLess(panel_width, 400)
        self.assertLess(panel_height, 180)

    def test_cylinder_legend_symbols_use_clean_arcs(self):
        queue_symbol = compiler.render_legend_symbol("horizontal-cylinder", 40, 40)
        db_symbol = compiler.render_legend_symbol("database-cylinder", 40, 40)

        self.assertNotIn("V 51.0 H", queue_symbol)
        self.assertIn("<ellipse", queue_symbol)
        self.assertLess(db_symbol.find("<path"), db_symbol.find("<ellipse"))
        self.assertIn("<ellipse", db_symbol)

    def test_example_gate_checks_png_ink_and_legend_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = example_gate.run_gate(Path(__file__).resolve().parents[1], out_dir=out_dir, quiet=True)
            result = next(item for item in report["results"] if item["name"] == "approval-flow")

        self.assertTrue(report["ok"], report["results"])
        self.assertTrue(result["hasShapeLegend"])
        self.assertGreater(result["png"]["nonBackgroundRatio"], example_gate.MIN_NON_BACKGROUND_RATIO)

    def test_local_side_by_side_mixed_port_hint_snaps_to_facing_side(self):
        source = {"id": "orders", "x": 1200, "y": 300, "width": 200, "height": 150, "rank": 2, "lane": 0}
        target = {"id": "worker", "x": 920, "y": 310, "width": 180, "height": 100, "rank": 1, "lane": 0}
        raw = {"sourcePort": "left", "targetPort": "bottom", "route": "top"}

        source_port, target_port, _side, _direct = compiler.resolved_ports_for_edge(raw, source, target, "top")

        self.assertEqual(source_port, "left")
        self.assertEqual(target_port, "right")

    def test_leaf_sink_compaction_shortens_excessive_connector_spans(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "payment-webhook-reconciliation.def.json"
        definition = json.loads(fixture.read_text(encoding="utf-8"))

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["id"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertIn("compact-local-sinks", {fix["code"] for fix in review["autofix"]["fixes"]})
        self.assertLess(compiler.max_segment_length(edges["edge-9"]["segments"]), compiler.EXCESS_CONNECTOR_SEGMENT)
        self.assertLess(compiler.max_segment_length(edges["edge-10"]["segments"]), compiler.EXCESS_CONNECTOR_SEGMENT + 16)
        self.assertLess(layout["boxes"]["notify"]["x"], 1800)
        self.assertLess(edges["edge-8"]["routeLength"], 420)

    def test_shared_target_ports_are_centered_and_sorted_by_source_position(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "payment-webhook-reconciliation.def.json"
        definition = json.loads(fixture.read_text(encoding="utf-8"))

        layout, review, _html = compiler.compile_diagram(definition)
        events = layout["boxes"]["events"]
        edges = {edge["id"]: edge for edge in layout["edges"]}
        incoming = [edges["edge-4"], edges["edge-5"], edges["edge-6"]]
        endpoints = [edge["segments"][-1] for edge in incoming]
        center_y = events["y"] + events["height"] / 2

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual([edge["targetOffset"] for edge in incoming], [-compiler.PORT_SPACING, 0, compiler.PORT_SPACING])
        self.assertEqual([round(endpoint["y2"] - center_y, 1) for endpoint in endpoints], [-compiler.PORT_SPACING, 0, compiler.PORT_SPACING])

    def test_horizontal_cylinder_incoming_ports_are_visually_tight(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "payment-webhook-reconciliation.def.json"
        definition = json.loads(fixture.read_text(encoding="utf-8"))

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["id"]: edge for edge in layout["edges"]}
        incoming = [edges["edge-4"], edges["edge-5"], edges["edge-6"]]
        endpoint_xs = [edge["segments"][-1]["x2"] for edge in incoming]

        self.assertEqual(review["warningCount"], 0)
        self.assertLessEqual(max(endpoint_xs) - min(endpoint_xs), 5)

    def test_reciprocal_mixed_port_routes_do_not_cross_or_overlap_labels(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "payment-webhook-reconciliation.def.json"
        definition = json.loads(fixture.read_text(encoding="utf-8"))

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["id"]: edge for edge in layout["edges"]}
        update = edges["edge-8"]
        retry = edges["edge-10"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(update["sourcePort"], "right")
        self.assertEqual(update["targetPort"], "left")
        self.assertEqual(retry["sourcePort"], "left")
        self.assertEqual(retry["targetPort"], "right")
        for update_segment in update["segments"]:
            for retry_segment in retry["segments"]:
                self.assertIsNone(compiler.segment_crossing_point(update_segment, retry_segment))
        update_label = update["labelBox"]
        update_vertical = update["segments"][1]
        retry_vertical = retry["segments"][1]
        self.assertLess(update_label["x"] + update_label["width"], update_vertical["x1"])
        self.assertGreaterEqual(abs(update_vertical["x1"] - retry_vertical["x1"]), compiler.ROUTE_LANE_SPACING)
        self.assertEqual(abs(update["routeLaneOffset"]), compiler.ROUTE_LANE_SPACING / 2)
        self.assertEqual(update["routeLaneOffset"], -retry["routeLaneOffset"])
        self.assertFalse(compiler.overlaps(update["labelBox"], retry["labelBox"], padding=4))

    def test_compiled_connector_endpoint_gaps_match_shape_perimeters(self):
        definition = {
            "title": "gap check",
            "nodes": [
                {"id": "source", "label": "Source API", "kind": "api", "rank": 0, "lane": 0},
                {"id": "queue", "label": "Queue", "kind": "queue", "rank": 1, "lane": 0},
            ],
            "edges": [
                {"from": "source", "to": "queue", "label": "enqueue", "route": "direct"}
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edge = layout["edges"][0]
        gaps = [round(gap, 1) for _kind, gap in compiler.edge_endpoint_gaps(edge, layout["boxes"])]

        self.assertEqual(review["metrics"]["connectorEndpointGapCount"], 0)
        self.assertEqual(gaps, [compiler.CONNECTOR_GAP, compiler.CONNECTOR_GAP])

    def test_excess_connector_span_is_reviewed_when_autofix_cannot_compact(self):
        layout = {
            "boxes": {
                "source": {"id": "source", "type": "node", "kind": "service", "shape": "rounded-rectangle", "label": "Source", "labelLines": ["Source"], "detail": [], "detailLines": [], "x": 100, "y": 100, "width": 180, "height": 70},
                "mid": {"id": "mid", "type": "node", "kind": "service", "shape": "rounded-rectangle", "label": "Intermediate", "labelLines": ["Intermediate"], "detail": [], "detailLines": [], "x": 720, "y": 100, "width": 180, "height": 70},
            },
            "edges": [
                {"id": "edge-1", "from": "source", "to": "mid", "label": "call", "kind": "sync", "route": "direct", "sourceRank": 0, "targetRank": 1, "segments": [{"x1": 280, "y1": 135, "x2": 715, "y2": 135, "role": "label"}], "labelBox": {"type": "edge-label", "x": 480, "y": 112, "width": 40, "height": 24, "anchor": {"segmentIndex": 0, "side": "inline", "orientation": "horizontal", "route": "direct"}}}
            ],
            "annotations": [],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("excess-connector-span", {warning["code"] for warning in review["warnings"]})

    def test_bottom_route_to_lower_target_enters_bottom_edge(self):
        source = {"x": 480, "y": 190, "width": 190, "height": 118}
        target = {"x": 838, "y": 400, "width": 220, "height": 200}

        path, _label, segments = compiler.connector_path(source, target, "bottom")

        self.assertTrue(path.endswith("V 610.0"))
        self.assertEqual(segments[-1]["x2"], 948.0)
        self.assertEqual(segments[-1]["y2"], 610.0)

    def test_backtracking_bottom_route_enters_target_side(self):
        source = {"x": 840, "y": 400, "width": 220, "height": 200}
        target = {"x": 480, "y": 190, "width": 190, "height": 118}

        _path, _label, segments = compiler.connector_path(source, target, "bottom")

        self.assertEqual(segments[-1]["x2"], 680.0)
        self.assertEqual(segments[-1]["y2"], 249.0)

    def test_backtracking_bottom_route_to_lower_target_uses_compact_side_return(self):
        source = {"x": 1226.7, "y": 190, "width": 262, "height": 118}
        target = {"x": 838.5, "y": 402.2, "width": 220, "height": 250}

        _path, _label, segments = compiler.connector_path(source, target, "bottom")

        self.assertLess(compiler.route_length(segments), 560)
        self.assertEqual(segments[-1]["x2"], 1068.5)
        self.assertEqual(segments[-1]["y2"], 527.2)
        self.assertEqual(segments[0]["x1"], source["x"] + source["width"] * 0.25)

    def test_direct_route_uses_side_anchors(self):
        source = {"x": 120, "y": 190, "width": 220, "height": 108}
        target = {"x": 480, "y": 190, "width": 190, "height": 118}

        path, _label, segments = compiler.connector_path(source, target, "direct")

        self.assertTrue(path.startswith("M 350.0 244.0"))
        self.assertTrue(path.endswith("H 470.0"))
        self.assertEqual(segments[-1]["x2"], 470.0)

    def test_direct_route_right_to_left_uses_target_right_side(self):
        source = {"x": 840, "y": 190, "width": 220, "height": 108}
        target = {"x": 480, "y": 190, "width": 190, "height": 118}

        path, _label, segments = compiler.connector_path(source, target, "direct")

        self.assertTrue(path.startswith("M 830.0 244.0"))
        self.assertTrue(path.endswith("H 680.0"))
        self.assertEqual(segments[-1]["x2"], 680.0)

    def test_explicit_right_to_left_ports_keep_fanout_source_side(self):
        source = {"x": 430, "y": 300, "width": 180, "height": 80}
        target = {"x": 780, "y": 120, "width": 180, "height": 80}

        path, _label, segments = compiler.port_route_path(source, target, "right", "left")

        self.assertTrue(path.startswith("M 620.0 340.0"))
        self.assertTrue(path.endswith("H 770.0"))
        self.assertEqual(segments[0], {"x1": 620, "y1": 340.0, "x2": 695.0, "y2": 340.0, "role": "branch"})
        self.assertEqual(segments[-1]["role"], "label")
        self.assertEqual(segments[-1]["x2"], 770.0)
        self.assertEqual(segments[-1]["y2"], 160.0)

    def test_explicit_bottom_to_bottom_ports_keep_loop_into_target_bottom(self):
        source = {"x": 780, "y": 500, "width": 180, "height": 80}
        target = {"x": 430, "y": 300, "width": 180, "height": 80}

        _path, _label, segments = compiler.port_route_path(source, target, "bottom", "bottom")

        self.assertEqual(segments[0]["x1"], 870.0)
        self.assertEqual(segments[0]["y1"], 590)
        self.assertEqual(segments[-1]["x2"], 520.0)
        self.assertEqual(segments[-1]["y2"], 390)

    def test_compile_preserves_explicit_source_and_target_ports(self):
        definition = {
            "title": "ports",
            "nodes": [
                {"id": "browse", "label": "Browse", "kind": "api", "rank": 0, "lane": 1},
                {"id": "share", "label": "Share", "kind": "service", "rank": 1, "lane": 0},
            ],
            "edges": [
                {
                    "from": "browse",
                    "to": "share",
                    "label": "share",
                    "route": "top",
                    "sourcePort": "right",
                    "targetPort": "left",
                }
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edge = layout["edges"][0]
        source = layout["boxes"]["browse"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edge["sourcePort"], "right")
        self.assertEqual(edge["targetPort"], "left")
        self.assertEqual(edge["segments"][0]["x1"], source["x"] + source["width"] + compiler.CONNECTOR_GAP)

    def test_forward_top_route_defaults_to_compact_side_dogleg(self):
        definition = {
            "title": "forward top",
            "nodes": [
                {"id": "gateway", "label": "Gateway", "kind": "api", "rank": 0, "lane": 1},
                {"id": "auth", "label": "Auth", "kind": "service", "rank": 1, "lane": 0},
            ],
            "edges": [
                {"from": "gateway", "to": "auth", "label": "verify session", "route": "top"}
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edge = layout["edges"][0]
        source = layout["boxes"]["gateway"]
        target = layout["boxes"]["auth"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edge["segments"][0]["x1"], source["x"] + source["width"] + compiler.CONNECTOR_GAP)
        self.assertEqual(edge["segments"][-1]["x2"], compiler.arrow_endpoint(target, "left")[0])
        self.assertLess(edge["routeLength"], 420)

    def test_forward_bottom_route_defaults_to_compact_side_dogleg(self):
        definition = {
            "title": "forward bottom",
            "nodes": [
                {"id": "gateway", "label": "Gateway", "kind": "api", "rank": 0, "lane": 1},
                {"id": "catalog", "label": "Catalog", "kind": "service", "rank": 1, "lane": 2},
            ],
            "edges": [
                {"from": "gateway", "to": "catalog", "label": "price items", "route": "bottom"}
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edge = layout["edges"][0]
        source = layout["boxes"]["gateway"]
        target = layout["boxes"]["catalog"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edge["segments"][0]["x1"], source["x"] + source["width"] + compiler.CONNECTOR_GAP)
        self.assertEqual(edge["segments"][-1]["x2"], target["x"] - compiler.CONNECTOR_GAP)
        self.assertLess(edge["routeLength"], 420)

    def test_auto_side_dogleg_fanin_labels_stay_on_source_side(self):
        definition = {
            "title": "fanin labels",
            "nodes": [
                {"id": "top", "label": "Top", "kind": "service", "rank": 0, "lane": 0},
                {"id": "middle", "label": "Middle", "kind": "service", "rank": 0, "lane": 1},
                {"id": "target", "label": "Target", "kind": "worker", "rank": 1, "lane": 1},
            ],
            "edges": [
                {"from": "top", "to": "target", "label": "top result", "route": "top"},
                {"from": "middle", "to": "target", "label": "ok", "route": "bottom"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edges["top result"]["segments"][0]["role"], "label")
        self.assertNotEqual(edges["top result"]["segments"][-1]["role"], "label")
        self.assertEqual(edges["ok"]["segments"][0]["role"], "label")

    def test_same_source_port_edges_are_evenly_spaced_around_center(self):
        definition = {
            "title": "source spacing",
            "nodes": [
                {"id": "source", "label": "Source", "kind": "api", "detail": ["one", "two"], "rank": 0, "lane": 1},
                {"id": "top", "label": "Top", "kind": "service", "rank": 1, "lane": 0},
                {"id": "middle", "label": "Middle", "kind": "service", "rank": 1, "lane": 1},
                {"id": "bottom", "label": "Bottom", "kind": "service", "rank": 1, "lane": 2},
            ],
            "edges": [
                {"from": "source", "to": "top", "label": "top", "route": "top", "sourcePort": "right", "targetPort": "left"},
                {"from": "source", "to": "middle", "label": "middle", "route": "direct", "sourcePort": "right", "targetPort": "left"},
                {"from": "source", "to": "bottom", "label": "bottom", "route": "bottom", "sourcePort": "right", "targetPort": "left"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        starts = [edge["segments"][0]["y1"] for edge in layout["edges"]]
        source_center_y = layout["boxes"]["source"]["y"] + layout["boxes"]["source"]["height"] / 2

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(starts, sorted(starts))
        self.assertAlmostEqual(starts[1], source_center_y, places=1)
        self.assertAlmostEqual(starts[1] - starts[0], compiler.PORT_SPACING, places=1)
        self.assertAlmostEqual(starts[2] - starts[1], compiler.PORT_SPACING, places=1)

    def test_same_source_side_edges_get_separate_route_lanes(self):
        definition = {
            "title": "source route lanes",
            "nodes": [
                {"id": "source", "label": "Source", "kind": "worker", "detail": ["two outgoing effects"], "rank": 0, "lane": 1},
                {"id": "top", "label": "Top", "kind": "service", "rank": 1, "lane": 0},
                {"id": "bottom", "label": "Bottom", "kind": "db", "rank": 1, "lane": 2},
            ],
            "edges": [
                {"from": "source", "to": "top", "label": "send receipt", "route": "top", "sourcePort": "right", "targetPort": "left"},
                {"from": "source", "to": "bottom", "label": "update payment status", "route": "bottom", "sourcePort": "right", "targetPort": "left"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        trunks = [edge["segments"][1]["x1"] for edge in layout["edges"]]

        self.assertEqual(review["warningCount"], 0)
        self.assertGreaterEqual(abs(trunks[1] - trunks[0]), compiler.PORT_SPACING)

    def test_multi_branch_top_bottom_routes_exit_directional_source_sides(self):
        definition = {
            "title": "directional branches",
            "nodes": [
                {"id": "queue", "label": "Queue", "kind": "queue", "rank": 0, "lane": 1},
                {"id": "source", "label": "Source", "kind": "worker", "rank": 1, "lane": 1},
                {"id": "upper", "label": "Upper", "kind": "service", "rank": 2, "lane": 0},
                {"id": "lower", "label": "Lower", "kind": "service", "rank": 2, "lane": 2},
            ],
            "edges": [
                {"from": "queue", "to": "source", "label": "consume", "route": "direct"},
                {"from": "source", "to": "upper", "label": "notify", "route": "top"},
                {"from": "source", "to": "lower", "label": "write status", "route": "bottom"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edges["notify"]["sourcePort"], "top")
        self.assertEqual(edges["write status"]["sourcePort"], "bottom")
        self.assertLess(edges["notify"]["segments"][0]["y2"], edges["notify"]["segments"][0]["y1"])
        self.assertGreater(edges["write status"]["segments"][0]["y2"], edges["write status"]["segments"][0]["y1"])

    def test_review_flags_visually_merged_sibling_route_lanes(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "source",
                    "to": "top",
                    "sourcePort": "right",
                    "targetPort": "left",
                    "label": "send receipt",
                    "segments": [
                        {"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"},
                        {"x1": 200, "y1": 100, "x2": 200, "y2": 220, "role": "branch"},
                        {"x1": 200, "y1": 220, "x2": 300, "y2": 220, "role": "entry"},
                    ],
                    "labelBox": {"type": "edge-label", "label": "send receipt", "x": 130, "y": 80, "width": 80, "height": 24, "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "inline", "orientation": "horizontal", "route": "top"}},
                },
                {
                    "id": "edge-2",
                    "from": "source",
                    "to": "bottom",
                    "sourcePort": "right",
                    "targetPort": "left",
                    "label": "update payment status",
                    "segments": [
                        {"x1": 100, "y1": 124, "x2": 202, "y2": 124, "role": "label"},
                        {"x1": 202, "y1": 124, "x2": 202, "y2": 260, "role": "branch"},
                        {"x1": 202, "y1": 260, "x2": 300, "y2": 260, "role": "entry"},
                    ],
                    "labelBox": {"type": "edge-label", "label": "update payment status", "x": 126, "y": 104, "width": 88, "height": 40, "anchor": {"segmentIndex": 0, "x": 151, "y": 124, "side": "inline", "orientation": "horizontal", "route": "bottom"}},
                },
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("merged-route-lane", {warning["code"] for warning in review["warnings"]})

    def test_review_flags_opposing_edges_that_share_a_corridor(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-8",
                    "from": "reconciler",
                    "to": "orders",
                    "kind": "sync",
                    "label": "update payment status",
                    "segments": [
                        {"x1": 1677.1, "y1": 411.6, "x2": 1768.3, "y2": 411.6, "role": "branch"},
                        {"x1": 1768.3, "y1": 411.6, "x2": 1768.3, "y2": 602.9, "role": "branch"},
                        {"x1": 1768.3, "y1": 602.9, "x2": 1859.6, "y2": 602.9, "role": "label"},
                    ],
                    "labelBox": {"type": "edge-label", "label": "update payment status", "x": 1770, "y": 583, "width": 110, "height": 24, "anchor": {"segmentIndex": 2, "x": 1810, "y": 602.9, "side": "inline", "orientation": "horizontal", "route": "bottom"}},
                },
                {
                    "id": "edge-10",
                    "from": "orders",
                    "to": "reconciler",
                    "kind": "retry",
                    "label": "retry mismatch",
                    "segments": [
                        {"x1": 1859.6, "y1": 626.9, "x2": 1768.3, "y2": 626.9, "role": "branch"},
                        {"x1": 1768.3, "y1": 626.9, "x2": 1768.3, "y2": 435.6, "role": "branch"},
                        {"x1": 1768.3, "y1": 435.6, "x2": 1677.1, "y2": 435.6, "role": "label"},
                    ],
                    "labelBox": {"type": "edge-label", "label": "retry mismatch", "x": 1690, "y": 416, "width": 90, "height": 24, "anchor": {"segmentIndex": 2, "x": 1720, "y": 435.6, "side": "inline", "orientation": "horizontal", "route": "top"}},
                },
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("opposing-route-corridor", {warning["code"] for warning in review["warnings"]})
        self.assertEqual(review["metrics"]["opposingRouteCorridorCount"], 1)
        self.assertLess(review["score"], 100)

    def test_review_flags_collapsed_sibling_source_points(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {"id": "edge-1", "from": "source", "to": "a", "sourcePort": "right", "targetPort": "left", "label": "", "segments": [{"x1": 100, "y1": 100, "x2": 220, "y2": 100, "role": "label"}]},
                {"id": "edge-2", "from": "source", "to": "b", "sourcePort": "right", "targetPort": "left", "label": "", "segments": [{"x1": 100, "y1": 105, "x2": 220, "y2": 180, "role": "label"}]},
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("collapsed-source-port", {warning["code"] for warning in review["warnings"]})

    def test_review_flags_connector_crossings(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {"id": "edge-1", "from": "a", "to": "b", "label": "", "segments": [{"x1": 100, "y1": 160, "x2": 240, "y2": 160, "role": "label"}]},
                {"id": "edge-2", "from": "c", "to": "d", "label": "", "segments": [{"x1": 170, "y1": 100, "x2": 170, "y2": 220, "role": "label"}]},
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("connector-crossing", {warning["code"] for warning in review["warnings"]})

    def test_review_flags_conflicting_labels(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "first",
                    "segments": [{"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"}],
                    "labelBox": {"type": "edge-label", "label": "first", "x": 120, "y": 90, "width": 80, "height": 24, "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "inline", "orientation": "horizontal", "route": "direct"}},
                },
                {
                    "id": "edge-2",
                    "from": "c",
                    "to": "d",
                    "label": "second",
                    "segments": [{"x1": 100, "y1": 130, "x2": 200, "y2": 130, "role": "label"}],
                    "labelBox": {"type": "edge-label", "label": "second", "x": 126, "y": 96, "width": 82, "height": 24, "anchor": {"segmentIndex": 0, "x": 150, "y": 130, "side": "above", "orientation": "horizontal", "route": "direct"}},
                },
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("label-overlap", {warning["code"] for warning in review["warnings"]})

    def test_same_target_port_edges_are_evenly_spaced_around_center(self):
        definition = {
            "title": "target spacing",
            "nodes": [
                {"id": "top", "label": "Top", "kind": "service", "rank": 0, "lane": 0},
                {"id": "middle", "label": "Middle", "kind": "service", "rank": 0, "lane": 1},
                {"id": "bottom", "label": "Bottom", "kind": "service", "rank": 0, "lane": 2},
                {"id": "target", "label": "Target", "kind": "worker", "detail": ["one", "two"], "rank": 1, "lane": 1},
            ],
            "edges": [
                {"from": "top", "to": "target", "label": "top", "route": "top"},
                {"from": "middle", "to": "target", "label": "middle", "route": "direct", "sourcePort": "right", "targetPort": "left"},
                {"from": "bottom", "to": "target", "label": "bottom", "route": "bottom"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        ends = [edge["segments"][-1]["y2"] for edge in layout["edges"]]
        target_center_y = layout["boxes"]["target"]["y"] + layout["boxes"]["target"]["height"] / 2

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(ends, sorted(ends))
        self.assertAlmostEqual(ends[1], target_center_y, places=1)
        self.assertAlmostEqual(ends[1] - ends[0], compiler.PORT_SPACING, places=1)
        self.assertAlmostEqual(ends[2] - ends[1], compiler.PORT_SPACING, places=1)

    def test_label_moves_to_longer_segment_when_tip_run_would_disappear(self):
        edge = {
            "label": "identity claims",
            "route": "top",
            "sourceRank": 2,
            "targetRank": 3,
            "segments": [
                {"x1": 985.5, "y1": 248.0, "x2": 1043.7, "y2": 248.0, "role": "label"},
                {"x1": 1057.7, "y1": 248.0, "x2": 1057.7, "y2": 395.2, "role": "branch"},
                {"x1": 1071.7, "y1": 395.2, "x2": 1129.8, "y2": 395.2, "role": "branch"},
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["segmentIndex"], 1)
        self.assertEqual(anchor["orientation"], "vertical")
        self.assertGreaterEqual(
            (anchor["segmentLength"] - compiler.inline_label_metrics(edge["label"], edge["segments"][1])["inlineExtent"]) / 2,
            compiler.EDGE_INLINE_MIN_VISIBLE_RUN,
        )

    def test_review_flags_inline_label_that_erases_visible_arrow_run(self):
        layout = {
            "boxes": {
                "a": {"id": "a", "type": "node", "x": 100, "y": 100, "width": 120, "height": 60},
                "b": {"id": "b", "type": "node", "x": 300, "y": 100, "width": 120, "height": 60},
            },
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "identity claims",
                    "route": "direct",
                    "sourceRank": 0,
                    "targetRank": 1,
                    "segments": [{"x1": 220, "y1": 130, "x2": 292, "y2": 130, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "identity claims",
                        "x": 219.5,
                        "y": 110,
                        "width": 73,
                        "height": 40,
                        "anchor": {"segmentIndex": 0, "x": 256, "y": 130, "side": "inline", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertIn("label-too-close-to-arrow-tip", {warning["code"] for warning in review["warnings"]})
        self.assertFalse(review["publishable"])
        self.assertEqual(review["recommendation"], "revise-or-split-before-sharing")

    def test_review_marks_clear_layout_publishable(self):
        layout = {
            "boxes": {
                "a": {"id": "a", "type": "node", "x": 100, "y": 100, "width": 120, "height": 60},
                "b": {"id": "b", "type": "node", "x": 360, "y": 100, "width": 120, "height": 60},
            },
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "request",
                    "route": "direct",
                    "sourceRank": 0,
                    "targetRank": 1,
                    "segments": [{"x1": 220, "y1": 130, "x2": 352, "y2": 130, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "request",
                        "x": 260,
                        "y": 118,
                        "width": 52,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 286, "y": 130, "side": "inline", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertTrue(review["publishable"])
        self.assertEqual(review["recommendation"], "shareable")
        self.assertEqual(review["blockingWarningCount"], 0)
        self.assertEqual(review["metrics"]["blockingWarningCount"], 0)
        self.assertTrue(review["metrics"]["publishable"])

    def test_review_blocks_overlap_even_when_score_remains_high(self):
        layout = {
            "boxes": {
                "a": {"id": "a", "type": "node", "x": 100, "y": 100, "width": 120, "height": 60},
                "b": {"id": "b", "type": "node", "x": 214, "y": 100, "width": 120, "height": 60},
            },
            "annotations": [],
            "edges": [],
        }

        review = compiler.analyze_layout(layout)

        self.assertLess(review["score"], 100)
        self.assertFalse(review["publishable"])
        self.assertEqual(review["recommendation"], "revise-or-split-before-sharing")
        self.assertEqual(review["blockingWarningCount"], 1)
        self.assertEqual(review["blockingWarnings"][0]["code"], "box-overlap")

    def test_review_flags_detached_external_connector_label(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "slow path",
                    "route": "direct",
                    "segments": [{"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "slow path",
                        "x": 110,
                        "y": -2,
                        "width": 80,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "above", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)
        warning = next(item for item in review["warnings"] if item["code"] == "detached-connector-label")

        self.assertEqual(review["metrics"]["detachedConnectorLabelCount"], 1)
        self.assertLess(review["score"], 100)
        self.assertEqual(warning["edge"], "edge-1")
        self.assertEqual(warning["label"], "slow path")
        self.assertEqual(warning["anchorSide"], "above")
        self.assertEqual(warning["anchorOrientation"], "horizontal")
        self.assertEqual(warning["segmentIndex"], 0)
        self.assertEqual(warning["distance"], 90)
        self.assertEqual(warning["threshold"], 66)

    def test_review_accepts_close_external_connector_label(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "slow path",
                    "route": "direct",
                    "segments": [{"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "slow path",
                        "x": 110,
                        "y": 46,
                        "width": 80,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "above", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertEqual(review["metrics"]["detachedConnectorLabelCount"], 0)
        self.assertNotIn("detached-connector-label", {warning["code"] for warning in review["warnings"]})
        self.assertEqual(review["warningCount"], 0)

    def test_review_flags_detached_external_connector_label(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "slow path",
                    "route": "direct",
                    "segments": [{"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "slow path",
                        "x": 110,
                        "y": -2,
                        "width": 80,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "above", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)
        warning = next(item for item in review["warnings"] if item["code"] == "detached-connector-label")

        self.assertEqual(review["metrics"]["detachedConnectorLabelCount"], 1)
        self.assertLess(review["score"], 100)
        self.assertEqual(warning["edge"], "edge-1")
        self.assertEqual(warning["label"], "slow path")
        self.assertEqual(warning["anchorSide"], "above")
        self.assertEqual(warning["anchorOrientation"], "horizontal")
        self.assertEqual(warning["segmentIndex"], 0)
        self.assertEqual(warning["distance"], 90)
        self.assertEqual(warning["threshold"], 66)

    def test_review_accepts_close_external_connector_label(self):
        layout = {
            "boxes": {},
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "slow path",
                    "route": "direct",
                    "segments": [{"x1": 100, "y1": 100, "x2": 200, "y2": 100, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "slow path",
                        "x": 110,
                        "y": 46,
                        "width": 80,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 150, "y": 100, "side": "above", "orientation": "horizontal", "route": "direct"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertEqual(review["metrics"]["detachedConnectorLabelCount"], 0)
        self.assertNotIn("detached-connector-label", {warning["code"] for warning in review["warnings"]})
        self.assertEqual(review["warningCount"], 0)

    def test_backward_top_route_keeps_over_the_top_return(self):
        definition = {
            "title": "backward top",
            "nodes": [
                {"id": "payment", "label": "Payment", "kind": "external", "rank": 1, "lane": 0},
                {"id": "checkout", "label": "Checkout", "kind": "api", "rank": 0, "lane": 0},
            ],
            "edges": [
                {"from": "payment", "to": "checkout", "label": "retry timeout", "route": "top", "kind": "retry"}
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edge = layout["edges"][0]
        source = layout["boxes"]["payment"]

        self.assertEqual(review["warningCount"], 0)
        self.assertAlmostEqual(edge["segments"][0]["y1"], compiler.shape_port_point(source, "top", gap=compiler.CONNECTOR_GAP)[1], places=1)

    def test_explicit_port_return_route_is_not_flagged_as_accidental_long_route(self):
        layout = {
            "boxes": {
                "a": {"id": "a", "type": "node", "x": 800, "y": 500, "width": 160, "height": 80},
                "b": {"id": "b", "type": "node", "x": 400, "y": 300, "width": 160, "height": 80},
            },
            "annotations": [],
            "edges": [
                {
                    "id": "edge-1",
                    "from": "a",
                    "to": "b",
                    "label": "back",
                    "route": "bottom",
                    "sourceRank": 2,
                    "targetRank": 1,
                    "sourcePort": "bottom",
                    "targetPort": "bottom",
                    "routeLength": 820,
                    "segments": [{"x1": 880, "y1": 580, "x2": 880, "y2": 680, "role": "label"}],
                    "labelBox": {
                        "type": "edge-label",
                        "label": "back",
                        "x": 859,
                        "y": 618,
                        "width": 42,
                        "height": 24,
                        "anchor": {"segmentIndex": 0, "x": 880, "y": 630, "side": "inline", "orientation": "vertical", "route": "bottom"},
                    },
                }
            ],
        }

        review = compiler.analyze_layout(layout)

        self.assertEqual(review["warningCount"], 0)

    def test_short_horizontal_direct_label_floats_above(self):
        edge = {
            "label": "admit buyer after fraud screening window",
            "route": "direct",
            "sourceRank": 0,
            "targetRank": 1,
            "segments": [
                {"x1": 100, "y1": 200, "x2": 220, "y2": 200, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["side"], "above")
        self.assertEqual(anchor["orientation"], "horizontal")

    def test_short_horizontal_direct_label_stays_inline_when_wrapped_to_two_lines(self):
        edge = {
            "label": "request access",
            "route": "direct",
            "sourceRank": 0,
            "targetRank": 1,
            "segments": [
                {"x1": 100, "y1": 200, "x2": 220, "y2": 200, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)
        box = compiler.label_box(edge["label"], (anchor["x"], anchor["y"]), anchor_data=anchor)

        self.assertEqual(anchor["side"], "inline")
        self.assertEqual(box["lines"], ["request", "access"])

    def test_short_direct_label_floats_when_inline_would_hide_connector_runs(self):
        edge = {
            "label": "request access",
            "route": "direct",
            "sourceRank": 0,
            "targetRank": 1,
            "segments": [
                {"x1": 100, "y1": 200, "x2": 178, "y2": 200, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["side"], "above")

    def test_node_box_exposes_wrapped_label_and_detail_lines(self):
        definition = {
            "title": "node wrapping",
            "nodes": [
                {
                    "id": "waiting",
                    "label": "Edge Admission Waiting Room Queue",
                    "kind": "queue",
                    "detail": ["signed position token with fairness window"],
                    "rank": 0,
                    "lane": 0,
                }
            ],
            "edges": [],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        box = layout["boxes"]["waiting"]

        self.assertLessEqual(max(compiler.text_width(line) for line in box["labelLines"]), box["width"] - compiler.PAD_X * 2 + 1)
        self.assertGreaterEqual(len(box["detailLines"]), 2)
        self.assertEqual(review["warningCount"], 0)

    def test_header_only_service_uses_content_height(self):
        width, height = compiler.node_size({"id": "node", "label": "Header only", "kind": "service"})

        self.assertGreaterEqual(width, compiler.NODE_MIN_W)
        self.assertLessEqual(height, 66)

    def test_service_with_body_text_adds_only_needed_height(self):
        _header_width, header_height = compiler.node_size({"id": "node", "label": "Header only", "kind": "service"})
        _body_width, body_height = compiler.node_size({
            "id": "node",
            "label": "Header only",
            "kind": "service",
            "detail": ["one body line"],
        })

        self.assertGreater(body_height, header_height)
        self.assertLessEqual(body_height - header_height, compiler.LINE_H + 12)

    def test_queue_without_body_does_not_reserve_detail_space(self):
        _width, height = compiler.node_size({"id": "queue", "label": "Queue", "kind": "queue"})

        self.assertEqual(height, 68)

    def test_queue_label_is_biased_left_of_right_cap(self):
        box = {
            "id": "events",
            "kind": "queue",
            "label": "Payment Events",
            "detail": ["authorized", "failed"],
            "x": 976.9,
            "y": 337.2,
            "width": 240,
            "height": 116,
        }

        layout = compiler.queue_text_layout(box)
        label_width = max(compiler.text_width(line) for line in layout["labelLines"])

        self.assertLess(layout["textX"], box["x"] + box["width"] / 2)
        self.assertLessEqual(layout["textX"] + label_width / 2, layout["capLeft"] + 5)
        self.assertEqual(layout["labelLines"], ["Payment Events"])

    def test_rank_and_lane_gaps_are_compact_defaults(self):
        definition = {
            "title": "compact",
            "nodes": [
                {"id": "a", "label": "A", "rank": 0, "lane": 0},
                {"id": "b", "label": "B", "rank": 1, "lane": 0},
                {"id": "c", "label": "C", "rank": 0, "lane": 1},
            ],
            "edges": [],
        }

        _nodes, boxes = compiler.assign_positions(definition, [])

        self.assertLessEqual(boxes["b"]["x"] - (boxes["a"]["x"] + boxes["a"]["width"]), compiler.RANK_GAP + 1)
        self.assertLessEqual(boxes["c"]["y"] - (boxes["a"]["y"] + boxes["a"]["height"]), compiler.LANE_GAP + 1)

    def test_short_horizontal_direct_label_stays_inline_when_it_fits(self):
        edge = {
            "label": "claim message",
            "route": "direct",
            "sourceRank": 0,
            "targetRank": 1,
            "segments": [
                {"x1": 100, "y1": 200, "x2": 230, "y2": 200, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["side"], "inline")

    def test_nearly_vertical_bottom_route_uses_vertical_label_segment(self):
        source = {"x": 766.6, "y": 190.0, "width": 251, "height": 118}
        target = {"x": 778.1, "y": 402.2, "width": 220, "height": 250}

        _path, _label, segments = compiler.connector_path(source, target, "bottom")

        self.assertEqual(compiler.segment_orientation(segments[0]), "vertical")
        self.assertEqual(segments[0]["role"], "label")
        self.assertGreater(compiler.segment_length(segments[0]), 300)

    def test_same_rank_bottom_route_enters_lower_target_top(self):
        source = {"x": 766.6, "y": 190.0, "width": 251, "height": 118, "rank": 2}
        target = {"x": 778.1, "y": 402.2, "width": 220, "height": 250, "rank": 2}

        _path, _label, segments = compiler.connector_path(source, target, "bottom")

        self.assertEqual(segments[0]["y2"], target["y"] - compiler.CONNECTOR_GAP)

    def test_short_direct_dogleg_prefers_source_side_label_segment(self):
        edge = {
            "label": "issue ticket",
            "route": "direct",
            "sourceRank": 4,
            "targetRank": 5,
            "segments": [
                {"x1": 1657.2, "y1": 522.1, "x2": 1686.8, "y2": 522.1, "role": "exit"},
                {"x1": 1686.8, "y1": 522.1, "x2": 1686.8, "y2": 527.2, "role": "label"},
                {"x1": 1686.8, "y1": 527.2, "x2": 1716.5, "y2": 527.2, "role": "entry"},
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["segmentIndex"], 0)

    def test_top_route_enters_target_top_edge(self):
        source = {"x": 480, "y": 400, "width": 190, "height": 118}
        target = {"x": 840, "y": 190, "width": 220, "height": 108}

        _path, _label, segments = compiler.connector_path(source, target, "top")

        self.assertEqual(segments[-1]["x2"], 950.0)
        self.assertEqual(segments[-1]["y2"], 180.0)

    def test_edge_label_wraps_for_short_segment(self):
        lines = compiler.wrap_edge_label("enqueue review message", max_width=80)

        self.assertEqual(lines, ["enqueue", "review message"])

    def test_three_word_edge_label_prefers_two_lines_when_soft_width_fits(self):
        lines = compiler.wrap_edge_label("publish ledger update", max_width=96)

        self.assertEqual(lines, ["publish", "ledger update"])

    def test_edge_label_prefers_two_lines_when_they_fit(self):
        lines = compiler.wrap_edge_label("claim message", max_width=70)

        self.assertEqual(lines, ["claim", "message"])

    def test_edge_label_can_wrap_past_three_lines_when_necessary(self):
        lines = compiler.wrap_edge_label("validate transform enqueue dispatch confirm", max_width=70)

        self.assertEqual(lines, ["validate", "transform", "enqueue", "dispatch", "confirm"])

    def test_vertical_edge_label_wraps_to_bounded_width(self):
        box = compiler.label_box(
            "screen bursty traffic before seat access",
            (320, 240),
            anchor_data={
                "side": "right",
                "orientation": "vertical",
                "route": "direct",
                "segmentLength": 90,
            },
        )

        self.assertLessEqual(box["width"], 140)
        self.assertGreater(len(box["lines"]), 1)

    def test_long_vertical_connector_label_stays_inline(self):
        edge = {
            "label": "paid order",
            "route": "bottom",
            "sourceRank": 4,
            "targetRank": 4,
            "segments": [
                {"x1": 100, "y1": 100, "x2": 100, "y2": 240, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["orientation"], "vertical")
        self.assertEqual(anchor["side"], "inline")

    def test_arrow_marker_is_long_same_stroke_open_chevron(self):
        html = compiler.render_html(
            {"title": "marker test", "nodes": [], "edges": []},
            {"boxes": {}, "edges": [], "annotations": [], "assumptions": [], "notImplied": []},
            {"score": 100, "warnings": [], "metrics": {}},
        )

        self.assertIn('markerWidth="20"', html)
        self.assertIn('refX="12"', html)
        self.assertIn('M 2 2 L 17 7 L 2 12', html)
        self.assertIn('fill="none" stroke="var(--connector)" stroke-width="2.8"', html)
        self.assertNotIn('connector-tip', html)

    def test_inline_label_masks_use_tighter_padding(self):
        box = compiler.label_box(
            "claim message",
            (100, 100),
            anchor_data={"side": "inline", "orientation": "horizontal", "route": "direct", "segmentLength": 130},
        )

        self.assertEqual(box["width"], 65)
        self.assertEqual(box["height"], 40)

    def test_horizontal_inline_labels_wrap_before_consuming_connector(self):
        box = compiler.label_box(
            "enqueue review message",
            (100, 100),
            anchor_data={"side": "inline", "orientation": "horizontal", "route": "direct", "segmentLength": 218},
        )

        self.assertEqual(box["lines"], ["enqueue", "review message"])
        self.assertLessEqual(box["width"], 124)

    def test_three_line_direct_label_stays_inline_when_geometry_has_visible_runs(self):
        edge = {
            "label": "publish response event",
            "route": "direct",
            "sourceRank": 3,
            "targetRank": 4,
            "segments": [
                {"x1": 1415.5, "y1": 392.6, "x2": 1547.1, "y2": 392.6, "role": "label"}
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)
        box = compiler.label_box(edge["label"], (anchor["x"], anchor["y"]), anchor_data=anchor)

        self.assertEqual(anchor["side"], "inline")
        self.assertEqual(box["lines"], ["publish", "response", "event"])
        self.assertGreaterEqual((anchor["segmentLength"] - box["width"]) / 2, compiler.EDGE_INLINE_MIN_VISIBLE_RUN)

    def test_vertical_inline_label_padding_stays_unchanged(self):
        box = compiler.label_box(
            "paid order",
            (100, 100),
            anchor_data={"side": "inline", "orientation": "vertical", "route": "bottom", "segmentLength": 130},
        )

        self.assertEqual(box["width"], 98)

    def test_backedge_retry_label_anchor_is_centered_on_segment(self):
        edge = {
            "label": "Retry later",
            "route": "top",
            "sourceRank": 3,
            "targetRank": 1,
            "segments": [
                {"x1": 600, "y1": 180, "x2": 600, "y2": 100, "role": "exit"},
                {"x1": 600, "y1": 100, "x2": 300, "y2": 100, "role": "label"},
                {"x1": 300, "y1": 100, "x2": 300, "y2": 180, "role": "entry"},
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)
        box = compiler.label_box(edge["label"], (anchor["x"], anchor["y"]), anchor_data=anchor)

        self.assertEqual(anchor["t"], 0.5)
        self.assertEqual(anchor["x"], 450)
        self.assertAlmostEqual(box["x"] + box["width"] / 2, 450)

    def test_backtracking_bottom_label_anchor_is_centered_on_segment(self):
        edge = {
            "label": "Retry later",
            "route": "bottom",
            "sourceRank": 3,
            "targetRank": 1,
            "segments": [
                {"x1": 600, "y1": 240, "x2": 600, "y2": 340, "role": "exit"},
                {"x1": 600, "y1": 340, "x2": 300, "y2": 340, "role": "label"},
                {"x1": 300, "y1": 340, "x2": 300, "y2": 240, "role": "entry"},
            ],
        }

        anchor = compiler.label_anchor_for_edge(edge)

        self.assertEqual(anchor["t"], 0.5)
        self.assertEqual(anchor["x"], 450)

    def test_compiled_edges_all_use_real_path_markers(self):
        definition = {
            "title": "route marker test",
            "template": "system-left-to-right",
            "nodes": [
                {"id": "a", "label": "A", "kind": "api", "rank": 0, "lane": 0},
                {"id": "b", "label": "B", "kind": "queue", "rank": 1, "lane": 0},
                {"id": "c", "label": "C", "kind": "db", "rank": 1, "lane": 1},
            ],
            "edges": [
                {"from": "a", "to": "b", "label": "direct", "kind": "sync", "route": "direct"},
                {"from": "a", "to": "c", "label": "bottom", "kind": "sync", "route": "bottom"},
                {"from": "c", "to": "b", "label": "top retry", "kind": "retry", "route": "top"},
            ],
        }

        _layout, _review, html = compiler.compile_diagram(definition)

        self.assertEqual(html.count('class="connector '), 3)
        self.assertEqual(html.count('marker-end="url(#arrow'), 3)
        self.assertNotIn('connector-tip', html)

    def test_current_state_fixture_keeps_db_arrowheads_on_visible_sides(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "order-intake-reliability.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, html = compiler.compile_diagram(definition)
        edges = {edge["id"]: edge for edge in layout["edges"]}
        orders = layout["boxes"]["orders"]

        self.assertEqual(review["warningCount"], 0)
        self.assertLess(edges["edge-7"]["routeLength"], 560)
        self.assertEqual(edges["edge-2"]["segments"][-1]["y2"], orders["y"] + orders["height"] + compiler.CONNECTOR_GAP)
        self.assertEqual(edges["edge-7"]["segments"][-1]["x2"], orders["x"] + orders["width"] + compiler.CONNECTOR_GAP)
        retry = edges["edge-6"]
        retry_segment = retry["segments"][retry["labelBox"]["anchor"]["segmentIndex"]]
        retry_mid_x, retry_mid_y = compiler.segment_point(retry_segment, 0.5)
        retry_label_x, retry_label_y = compiler.box_center(retry["labelBox"])
        self.assertEqual(retry["labelBox"]["anchor"]["t"], 0.5)
        self.assertAlmostEqual(retry_label_x, retry_mid_x, places=1)
        self.assertAlmostEqual(retry_label_y, retry_mid_y, places=1)
        enqueue = edges["edge-3"]
        self.assertEqual(enqueue["labelBox"]["lines"], ["enqueue", "review message"])
        self.assertNotIn("connector-tip", html)

    def test_ticketing_fixture_compiles_without_review_warnings(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "ticketing-onsale.def.json"
        definition = compiler.read_definition(fixture)

        _layout, review, html = compiler.compile_diagram(definition)

        self.assertEqual(review["warningCount"], 0)
        self.assertIn("Ticketing Onsale Purchase Path", html)

    def test_ticketing_direct_label_segments_have_room_for_arrowheads(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "ticketing-onsale.def.json"
        definition = compiler.read_definition(fixture)

        layout, _review, _html = compiler.compile_diagram(definition)

        for edge in layout["edges"]:
            if edge["route"] == "direct" and edge.get("label"):
                _index, segment = compiler.preferred_label_segment(edge)
                self.assertGreaterEqual(compiler.segment_length(segment), 90, edge["label"])

    def test_ticketing_terminal_arrow_segments_are_visible(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "ticketing-onsale.def.json"
        definition = compiler.read_definition(fixture)

        layout, _review, _html = compiler.compile_diagram(definition)

        for edge in layout["edges"]:
            terminal = edge["segments"][-1]
            self.assertGreaterEqual(compiler.segment_length(terminal), 24, edge["label"])

    def test_ticketing_release_hold_uses_compact_facing_side_route(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "ticketing-onsale.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, _html = compiler.compile_diagram(definition)
        release = {edge["label"]: edge for edge in layout["edges"]}["release hold"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(release["sourcePort"], "left")
        self.assertEqual(release["targetPort"], "right")
        self.assertEqual(len(release["segments"]), 1)
        self.assertLess(release["routeLength"], 500)

    def test_cloud_text_stack_is_visually_centered_lower_in_lobes(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "order-intake-reliability.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, _html = compiler.compile_diagram(definition)
        pos = layout["boxes"]["pos"]
        stack = compiler.text_stack_layout(pos)

        self.assertEqual(review["warningCount"], 0)
        self.assertGreater(stack["labelBaselines"][0], pos["y"] + pos["height"] * 0.47)
        self.assertLess(stack["textBounds"]["y"] + stack["textBounds"]["height"], pos["y"] + pos["height"] * 0.82)

    def test_payment_webhook_fixture_compiles_without_review_warnings(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "payment-webhook-reconciliation.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertIn("Payment Webhook Reconciliation", html)
        self.assertEqual(edges["provider webhook"]["labelBox"]["anchor"]["orientation"], "vertical")
        self.assertGreaterEqual(compiler.edge_label_visible_run(edges["provider webhook"]), compiler.EDGE_INLINE_MIN_VISIBLE_RUN)
        self.assertEqual(edges["create ledger entry"]["labelBox"]["lines"], ["create", "ledger entry"])
        self.assertEqual(edges["publish ledger update"]["labelBox"]["lines"], ["publish", "ledger update"])
        self.assertEqual(edges["update payment status"]["labelBox"]["lines"], ["update", "payment status"])
        self.assertEqual(edges["send receipt"]["sourcePort"], "top")
        self.assertEqual(edges["update payment status"]["sourcePort"], "right")
        self.assertEqual(edges["update payment status"]["targetPort"], "left")
        self.assertGreaterEqual(
            abs(edges["retry mismatch"]["segments"][-1]["y2"] - edges["update payment status"]["segments"][0]["y1"]),
            compiler.PORT_SPACING,
        )

    def test_semantic_shapes_showcase_compiles_without_review_warnings(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "semantic-shapes-showcase.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertIn("Semantic Shapes Showcase", html)
        self.assertIn("shape-legend", html)
        self.assertIn("legend-symbol-cloud", html)
        self.assertEqual(edges["retry"]["targetPort"], "right")
        self.assertLess(edges["retry"]["routeLength"], 180)

    def test_fresh_minimal_hint_payment_reconciliation_example_compiles_cleanly(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "current-state" / "order-payment-reconciliation-auto.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, html = compiler.compile_diagram(definition)
        shapes = {box["id"]: box["shape"] for box in layout["boxes"].values()}
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertIn("Order Payment Reconciliation", html)
        self.assertEqual(shapes["provider"], "cloud")
        self.assertEqual(shapes["webhook"], "document")
        self.assertEqual(shapes["events"], "horizontal-cylinder")
        self.assertEqual(shapes["orders"], "database-cylinder")
        self.assertEqual(edges["retry"]["sourcePort"], "left")
        self.assertEqual(edges["retry"]["targetPort"], "right")
        self.assertLess(edges["retry"]["routeLength"], 180)

    def test_top_route_to_higher_side_target_enters_left_not_bottom(self):
        definition = {
            "title": "Side Selection",
            "template": "system-left-to-right",
            "nodes": [
                {"id": "input", "label": "Input", "kind": "service", "lane": 1, "rank": 0},
                {"id": "worker", "label": "Worker", "kind": "worker", "lane": 1, "rank": 1},
                {"id": "events", "label": "Payment Events", "kind": "queue", "lane": 0, "rank": 2},
                {"id": "receipts", "label": "Receipt Store", "kind": "service", "lane": 1, "rank": 2},
            ],
            "edges": [
                {"from": "input", "to": "worker", "label": "trigger", "route": "direct"},
                {"from": "worker", "to": "events", "label": "send event", "route": "top"},
                {"from": "worker", "to": "receipts", "label": "persist receipt", "route": "direct"},
            ],
        }

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}
        send = edges["send event"]

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(send["sourcePort"], "top")
        self.assertEqual(send["targetPort"], "left")
        self.assertNotEqual(send["targetPort"], "bottom")
        self.assertEqual(send["segments"][-1]["role"], "entry")
        self.assertGreater(abs(send["segments"][-1]["x2"] - send["segments"][-1]["x1"]), 24)

    def test_queue_db_reciprocal_pair_moves_failure_label_outside_primary_lane(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "exploration" / "reciprocal-queue-db.def.json"
        definition = compiler.read_definition(fixture)

        layout, review, _html = compiler.compile_diagram(definition)
        edges = {edge["label"]: edge for edge in layout["edges"]}

        self.assertEqual(review["warningCount"], 0)
        self.assertEqual(edges["reserve hold"]["sourcePort"], "right")
        self.assertEqual(edges["reserve hold"]["targetPort"], "left")
        self.assertEqual(edges["release hold"]["sourcePort"], "left")
        self.assertEqual(edges["release hold"]["targetPort"], "right")
        self.assertGreater(edges["release hold"]["labelBox"]["y"], edges["reserve hold"]["labelBox"]["y"])

    def test_db_cylinder_uses_deep_matching_curvature(self):
        html = compiler.render_html(
            {"title": "db", "nodes": [], "edges": []},
            {
                "boxes": {
                    "db": {
                        "id": "db",
                        "kind": "db",
                        "label": "Orders DB",
                        "labelLines": ["Orders DB"],
                        "detail": [],
                        "detailLines": [],
                        "x": 100,
                        "y": 100,
                        "width": 200,
                        "height": 250,
                    }
                },
                "edges": [],
                "annotations": [],
                "assumptions": [],
                "notImplied": [],
            },
            {"score": 100, "warnings": [], "metrics": {}},
        )

        self.assertIn('ry="40.0"', html)
        self.assertIn('C 100.0 332.1 144.8 350.0 200.0 350.0 C 255.2 350.0 300.0 332.1 300.0 310.0', html)
        self.assertIn('C 300.0 332.1 255.2 350.0 200.0 350.0 C 144.8 350.0 100.0 332.1 100.0 310.0', html)

    def test_cloud_shape_renders_external_provider_as_system_symbol(self):
        html = compiler.render_html(
            {"title": "cloud", "nodes": [], "edges": []},
            {
                "boxes": {
                    "provider": {
                        "id": "provider",
                        "kind": "external",
                        "shape": "cloud",
                        "label": "Payment Provider",
                        "labelLines": ["Payment Provider"],
                        "detail": [],
                        "detailLines": [],
                        "x": 100,
                        "y": 100,
                        "width": 220,
                        "height": 90,
                    }
                },
                "edges": [],
                "annotations": [],
                "assumptions": [],
                "notImplied": [],
            },
            {"score": 100, "warnings": [], "metrics": {}},
        )

        self.assertIn('class="cloud-node system-symbol"', html)
        self.assertIn("<path", html)
        self.assertNotIn('external-node rect', html)


if __name__ == "__main__":
    unittest.main()
