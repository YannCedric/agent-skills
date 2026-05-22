---
name: diagrammer
description: Create polished, deterministic technical diagrams as SVG/HTML with rendered PNG exports. Use for architecture diagrams, system diagrams, C4 context/container/component views, sequence diagrams, data-flow diagrams, state machines, integration boundaries, failure/retry paths, flow charts, and shareable technical visual artifacts. Prefer this skill whenever accurate labels, arrows, boundaries, layout, and readable exports matter.
---

# Diagrammer

Create useful technical diagrams as deterministic artifacts: source HTML with inline SVG, rendered PNG, and concise notes about assumptions and what the diagram does not imply.

Use this skill for static diagram artifacts first. Do not make video, animation, Excalidraw, Mermaid, or Structurizr the primary output unless the user asks or the situation clearly benefits from it.

## Workflow

1. Build a tiny brief before drawing:
   - audience
   - system boundary
   - diagram type
   - decision or question the diagram should clarify
   - what the diagram must not imply
2. If one answer is obvious, proceed with stated assumptions. Ask only when missing input would make the diagram misleading.
3. Choose a preset:
   - presentation-16x9: 1600x900, broad share/presentation default
   - doc-wide: 1600x1000, documentation default
   - square-share: 1200x1200, social/chat sharing
   - mobile-share: 900x1200, narrow/mobile viewing
   - custom specs when the user provides dimensions, theme, or format constraints
4. Read references/diagram-principles.md when selecting diagram type, visual conventions, or the QA checklist. Read references/figjam-theme.md when using the default visual theme or when the user asks for a FigJam/whiteboard look.
5. For system/component diagrams, prefer the compiler prototype:
   - write diagram.def.json from the brief
   - run diagrammer-compile diagram.def.json --out-dir out when the package is installed
   - fallback: python3 skills/diagrammer/scripts/compile_diagram.py diagram.def.json --out-dir out
   - inspect diagram.review.json and revise the definition or layout hints when warnings matter
6. For other diagram types, create one HTML file with inline SVG. Keep labels real text, not images.
7. Run the structural readability check: diagrammer-validate path/to/diagram.html, or fallback to python3 skills/diagrammer/scripts/validate_svg.py path/to/diagram.html
8. Render it with: diagrammer-render path/to/diagram.html path/to/diagram.png --preset presentation-16x9, or fallback to python3 skills/diagrammer/scripts/render.py path/to/diagram.html path/to/diagram.png --preset presentation-16x9
9. Review diagram.review.json before final delivery. If publishable is false, recommendation is revise-or-split-before-sharing, score is below 80, or blocking warnings include overlap, connector intrusion, connector crossing, long return routes, or shape text overflow, revise the definition/layout or split the view before sharing.
10. Review the PNG before final delivery. Revise if the artifact has overlap, label overflow, tiny text, crossed lines that confuse reading order, weak boundaries, unclear arrow semantics, or visual clutter.
11. Deliver diagram.html, diagram.png, a short explanation, assumptions, not-implied notes, and optional export/source variants only when useful.

For bundled compiler fixtures, run the visual regression gate after renderer/routing/shape changes:

```bash
python3 skills/diagrammer/scripts/check_examples.py --json --quiet
```

Use `--out-dir tmp/diagrammer-example-gate` when you want to keep fresh temporary renders for inspection.

## Artifact Rules

- Read references/compiler-pipeline.md before using the compiler prototype or writing a diagram.def.json definition.
- The compiler implementation lives in the Python package under diagrammer/. scripts/ contains compatibility wrappers so older skill instructions keep working.
- For development, run tests from the skill root with: python3 -m unittest discover -s tests
- Runtime assumption for the source package: Python 3.10+ is available. For hosts without Python, publish a platform-specific standalone binary or zipapp as an optional release artifact; keep source + tests as the canonical distribution.
- Prefer SVG/HTML as the canonical source because it gives precise layout, text, arrows, and reproducible exports.
- Use light mode for the shareable PNG unless the user asks otherwise. The HTML may support dark mode with prefers-color-scheme.
- Default font stack: Liberation Sans, Arial, Helvetica, sans-serif. Use a different bundled or locally installed font only when it improves the artifact and renders reliably on the host.
- Default connector style: FigJam-inspired rounded elbow connectors. Prefer horizontal/vertical paths with quadratic 90-degree turns, round caps/joins, and compact open chevron arrow tips.
- Connector labels should be inline text gaps by default: connector stroke, a small canvas-colored mask behind centered text, then connector stroke resumes. Use bordered label chips only for annotation-like callouts, not ordinary arrow labels.
- For common infrastructure, use simple canonical symbols consistently: standalone database cylinders, standalone queue/buffer cylinders, and plain rounded nodes for services/workers/APIs. Avoid surrounding container boxes unless boundary ownership is the main message.
- Keep drawing code and visible shapes aligned: implement reusable primitives such as service_node, db_cylinder, queue_cylinder, annotation_block, connector, and connector_label rather than hand-drawing one-off variants.
- Database cylinders may include 3-5 schema/status rows inside the cylinder when those details matter. Queue/stream/buffer symbols should be horizontal standalone cylinders, not rounded service cards.
- Treat note groups as first-class annotation blocks on the open canvas. Do not put annotations in cards unless the box is communicating ownership, trust, or another real boundary.
- Prefer neutral gray connectors for ordinary relationships. Reserve red/amber connectors for failure, retry, guard, or exception paths.
- Split crowded systems into a multi-frame bundle rather than forcing everything into one diagram.
- Keep diagrams focused on the question. Architecture diagrams are communication tools, not inventories.
- Avoid hidden state or durable decision logging. This skill draws artifacts; other skills may handle state.

## Multi-Frame Bundles

Use 2-4 diagrams when one diagram would be crowded:

- context: who/what touches the system
- container/component: major building blocks and responsibilities
- sequence/data flow: important path through the system
- failure/retry/state: edge behavior that would otherwise be hidden

Keep naming explicit, for example:

- 01-context.html / 01-context.png
- 02-order-review-sequence.html / 02-order-review-sequence.png
- 03-failure-retry-path.html / 03-failure-retry-path.png

## Output Notes

When replying, keep the explanation short and grounded:

- what the diagram shows
- the main reading path
- assumptions made
- what it intentionally does not imply
- files created

## Optional Exports

- Mermaid: useful for README-native simple flows, but not canonical for polished complex diagrams.
- Structurizr/C4 DSL: useful when the user wants model-as-code maintainability.
- Excalidraw: useful when the user needs hand-editable workshop artifacts.
- Video walkthrough: out of scope for v1 unless the user specifically needs motion or narration.
