# Diagrammer Compiler Pipeline

The compiler prototype keeps the user workflow conversational while using explicit internal artifacts:

1. diagram.def.json - semantic definition written from the conversation.
2. diagram.layout.json - measured boxes, stable connector segments, inline text-gap labels, segment anchors, and canvas metadata.
3. diagram.review.json - scoring metrics, autofix summary, and inspectable warnings for overlap, missing labels, ambiguous routes, or unknown kinds.
4. diagram.html - self-contained HTML/SVG source, rendered to PNG with scripts/render.py.

Warnings should guide revision, but only hard JSON parse errors stop generation. The compiler runs a deterministic autofix pass before writing final layout/review/render artifacts so common label and canvas issues are repaired without requiring template-specific hand edits.

## Definition Contract

~~~json
{
  "title": "Job scheduler",
  "subtitle": "System-left-to-right component view",
  "template": "system-left-to-right",
  "nodes": [
    {
      "id": "api",
      "label": "Scheduler API",
      "kind": "api",
      "detail": ["validates jobs"],
      "lane": 0,
      "rank": 1
    }
  ],
  "edges": [
    {
      "from": "api",
      "to": "queue",
      "label": "enqueue job",
      "kind": "async",
      "route": "direct",
      "labelPosition": "above"
    }
  ],
  "annotations": [
    {
      "title": "Not implied",
      "lines": ["No exactly-once delivery claim"],
      "lane": 1,
      "rank": 4
    }
  ],
  "assumptions": ["Workers are horizontally scalable"],
  "notImplied": ["No global ordering guarantee"]
}
~~~

## Fields

- title, subtitle: visible diagram heading.
- template: currently system-left-to-right.
- nodes[]: id, label, kind, optional shape override, optional detail, optional lane, optional rank.
- kind: semantic element type. Current common kinds include service, api, worker, client/user, external/provider/cloud, db/database/datastore/storage, queue/stream/topic/buffer, document/file/pdf, decision/approval, auth/security/risk.
- shape: optional visual primitive override. Prefer semantic kind first; use shape only when the compiler's semantic mapping is wrong for the diagram.
- edges[]: from, to, label, kind, optional route, optional labelPosition.
- edge.kind: sync, async, retry, or failure.
- route: direct, top, or bottom.
- labelPosition: above or below.
- annotations[]: open-canvas note groups with title, lines, optional lane, optional rank.
- assumptions, notImplied: surfaced in the artifact footer and review context.

## Layout Rules

- The first template is rank-based left-to-right layout.
- rank controls horizontal position; lane controls vertical position.
- Omitted lanes/ranks receive stable defaults based on node order.
- Node boxes are estimated from label and detail text before rendering.
- Connector routes are stored as stable axis-aligned segments even when rendered with rounded SVG elbows.
- Connector labels are measured text-gap boxes, not bordered chips by default.
- Connector labels should carry an explicit anchor containing segmentIndex, t, side, orientation, and route so the renderer can mask the connector under the text before drawing nodes.
- Connector endpoints use shape-aware visual perimeter ports with a consistent minimum gap on both source and target sides. Target measurements account for the rendered arrowhead tip, not just the SVG path endpoint.
- Route corridors and shape attachment sides are separate choices. A top/bottom route hint may move the connector through an outer corridor, but the final target port should still match the approach direction; for example, an upper branch from a left-side source to Payment Events should enter the target's left edge instead of defaulting to the bottom edge.
- Shared source and target ports are allocated symmetrically around each shape side's midpoint. Multiple incoming or outgoing connectors are sorted by the opposite endpoint position, with definition order as a tie-breaker, then assigned equal offsets such as -24/0/+24.
- Mixed source/target use of the same side gets wider reciprocal lanes, with incoming target slots ordered before outgoing source slots on top/bottom sides. This prevents bidirectional near-parallel routes from crossing or hiding labels while keeping their endpoints visibly distinct.
- Reciprocal facing-side pairs are treated as a label-placement bundle: the primary edge keeps the direct inline slot when it fits, while retry/failure labels move outside the primary lane to avoid hiding the opposing arrowhead.
- The compiler runs a local sink-compaction pass before final edge layout. When a leaf/source-of-truth target is only far away because the rank grid spread it out, the target can move closer to its local parent before routes are recomputed.
- Ordinary connectors are neutral. failure and retry connectors use the reserved exception color.
- The compiler resolves each node to a FigJam-inspired shape via diagrammer/shapes.py, then stores both kind and shape in diagram.layout.json.
- DBs render as standalone cylinders. Queues/streams/topics render as horizontal buffer/cylinders. External providers render as cloud symbols. Clients/users render with a simple user symbol. Risk/auth/security may render as shields, while approvals/decisions may render as diamonds. Generic services, APIs, and workers stay rounded rectangles.
- Node text fitting is validated against each shape's usable text area and the rendered SVG text baselines, not only its outer bounding box. Narrow shapes such as clouds, shields, diamonds, and horizontal cylinders expose smaller text budgets so overflow is caught before export.
- A shape legend is rendered only when the diagram uses semantic shapes that need explanation, or when several non-default shapes appear together. The legend is a visible panel anchored away from the main flow so it explains the visual decision without adding noise to ordinary box-only diagrams.
- Annotation blocks stay open-canvas by default and do not use surrounding boxes.

## Scoring And Autofix

The review file includes:

- score: 0-100 final layout score after autofix.
- metrics: counts for label overlaps, labels far from routes, unanchored labels, connector-node intrusions, long return routes, excess connector spans, connector endpoint gap mismatches, shape text overflow, ambiguous label placement, whitespace ratio, routes, and labels.
- warnings: concrete issues still visible after autofix.
- preAutofix: score, metrics, and warning count from the raw layout.
- autofix: fix count plus named fixes applied before final render.

Current deterministic fixes:

- Move connector labels to explicit segment anchors and render inline text gaps where possible.
- Compact local leaf/source-of-truth targets when a connector has an excessive uninterrupted span and the move does not collide with existing nodes or annotations.
- Prefer clearer top/retry labels outside loop corners and direct labels above the route with enough node clearance.
- Nudge connector labels away from nodes, annotations, and neighboring labels when an inline text gap is not possible.
- Use a tighter offset for long bottom return routes.
- Record content bounds and compact trimmedViewBox metadata in diagram.layout.json for crop-aware export tooling.

Current scoring warnings cover:

- label overlaps with nodes, annotations, or other labels.
- connector labels too far from their route segment.
- connector labels without explicit anchor data.
- connector paths crossing or running through unrelated node boxes.
- very long bottom return routes.
- excess canvas whitespace.
- missing or ambiguous label placement data.

## Commands

~~~bash
diagrammer-compile diagram.def.json --out-dir out
diagrammer-validate out/diagram.html
diagrammer-render out/diagram.html out/diagram.png --width 2000 --height 1200 --quiet
~~~

When the package is not installed, the compatibility wrappers remain available:

~~~bash
python3 skills/diagrammer/scripts/compile_diagram.py diagram.def.json --out-dir out
python3 skills/diagrammer/scripts/validate_svg.py out/diagram.html
python3 skills/diagrammer/scripts/render.py out/diagram.html out/diagram.png --width 2000 --height 1200 --quiet
~~~

For development:

~~~bash
cd skills/diagrammer
python3 -m unittest discover -s tests
~~~

## Distribution Model

Canonical distribution is source code plus a Python package:

- SKILL.md is the agent-facing workflow and routing layer.
- diagrammer/ is the tested compiler package.
- pyproject.toml defines console entry points.
- scripts/ keeps backwards-compatible wrappers for copied skill folders.
- fixtures/ and tests/ are part of the package quality gate.

Python 3.10+ is the default runtime dependency. For hosts where Python is not available, provide optional built artifacts after the source package stabilizes:

- zipapp when Python exists but a single-file runner is preferred.
- PyInstaller/Nuitka-style standalone binaries only for specific platforms that cannot rely on Python.

Do not make Bash the compiler implementation. Bash wrappers are acceptable for convenience, but diagram layout logic should stay in testable source code.
