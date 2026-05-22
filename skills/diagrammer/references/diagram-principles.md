# Diagram Principles

## Diagram Type Selection

- C4 context: audience needs system scope, users, and external systems.
- C4 container: audience needs major deployable/runtime parts and their responsibilities.
- C4 component: audience needs internals of one container, not the whole estate.
- Sequence: audience needs ordering, handoffs, human approval, or sync/async semantics.
- Data flow: audience needs sources, transformations, stores, and outputs.
- State machine: audience needs lifecycle/status transitions and terminal states.
- Integration boundary: audience needs ownership, trust boundaries, vendor edges, or protocols.
- Failure/retry path: audience needs degraded behavior, retry semantics, queues, dead letters, or operator intervention.
- Tradeoff matrix: audience needs options compared, not system topology.

Use the lowest-detail view that answers the question. Do not model everything.

## Brief Contract

Before drawing, establish:

- audience: executive, product, engineering, security, operations, customer, or mixed
- boundary: what is inside the system and what is external
- diagram type: selected from the taxonomy or custom
- decision/question: what this artifact should clarify
- must-not-imply: ownership, durability, sync behavior, trust, approval, scale, or retries that are unknown

## Visual Conventions

- Canvas: use a fixed viewport and SVG viewBox. Prefer 1600x900 or 1600x1000.
- Typography: default to Liberation Sans, Arial, Helvetica, sans-serif. Keep primary labels at 20px or larger for shareable exports and avoid tiny annotation-heavy diagrams.
- Label fit: size boxes from labels, not the other way around. Keep at least 18px horizontal padding on both sides; if the label is long, widen the box, split the label into two lines, or shorten the text.
- Palette: default to neutral canvas, neutral nodes, one primary flow color, and one reserved exception color. Add more colors only when they clarify a real semantic distinction.
- Shapes: default to one shape family: simple rounded rectangles with 6-8px radius. Use diamonds, icons, and pictograms only when the shape itself communicates important meaning.
- System symbols: use simple, consistent canonical symbols for common infrastructure when they improve scanning. Databases should use standalone cylinder symbols; queues/streams/buffers should use standalone queue/cylinder-like buffer symbols. Services, APIs, workers, and clients stay simple rounded rectangles/circles.
- Code primitives: keep generator helper names aligned to the visual grammar, for example service_node, db_cylinder, queue_cylinder, annotation_block, connector, and connector_label. Avoid one-off SVG fragments that make the artifact drift away from the skill rules.
- Database detail: if schema/status detail is shown, place 3-5 rows inside the database cylinder. Do not move database rows into a separate card unless the card is a different artifact.
- Queue detail: queues, streams, buffers, and topics should read as horizontal cylinders/buffers. If extra detail is needed, put short rows inside the cylinder or in a nearby annotation block, not inside a service-style card.
- Annotation blocks: requirements, entities, tradeoffs, and not-implied notes can be first-class open-canvas elements. They should be grouped in code with an annotation-block class and usually should not have a surrounding box.
- Effects: avoid decorative shadows by default. Use spacing, strokes, and subtle fills to create hierarchy.
- Groups: prefer open-canvas grouping with labels and spacing. Use titled containers only when ownership, trust boundaries, or deployment boundaries are the main point.
- Arrows:
  - solid arrow: primary request/data flow
  - dashed arrow: async, callback, retry, or optional path
  - red/amber arrow: failure, guard, or exception path
  - double-headed arrows only when bidirectional behavior is genuinely intended
  - default connector geometry should feel FigJam-like: straight segments, smooth rounded 90-degree elbows, round caps/joins, and compact open chevron tips
  - avoid freeform cubic curves for normal flow diagrams; they are harder to align consistently and tend to look less systematic
- Connector color: keep ordinary connectors gray/neutral unless color is carrying a real semantic distinction. Red should be reserved for failure, retry, guard, or exception paths.
- Labels: favor fewer, larger labels. Label arrows only when protocol, payload, or state transition matters. Connector labels should read as inline text gaps on the connector: a small canvas-colored mask behind centered text, with the connector resuming close to both sides. Remove redundant connector labels when branches get tight.
- Legend: include only when visual semantics are not obvious; avoid legends that explain decorative color.

## False-Implication Checklist

Call out or fix ambiguity around:

- sync vs async
- system ownership
- trust/security boundary
- human approval vs automated action
- durable persistence vs transient cache
- queue/retry/dead-letter behavior
- source of truth
- external vendor responsibility
- batch vs real-time timing
- read path vs write path

If the source material does not prove a behavior, either omit it or mark it as an assumption.

## Render Review Checklist

Open the rendered PNG and revise until:

- no labels overlap shapes, arrows, or other labels
- no labels overflow their containing boxes or sit tight against box edges
- text is readable at the intended sharing size
- arrows have visible shafts and heads
- the primary reading path is obvious
- related items are grouped visually
- boundaries are named and not misleading
- no diagram area is dense while another is empty without reason
- color semantics are consistent
- every major external system is clearly outside the boundary
- assumptions/not-implied notes cover important uncertainty

Also inspect diagram.review.json before sharing. Treat publishable: false, a score below 80, or recommendation: revise-or-split-before-sharing as a stop sign, even if the PNG is superficially readable. Blocking warnings mean the artifact should be revised or split:

- box-overlap, label-overlap, or shape-text-overflow
- connector-node-intrusion or connector-crossing
- detached-connector-label or label-too-close-to-arrow-tip
- long-bottom-return-route
- merged-route-lane, opposing-route-corridor, or collapsed connector ports

When a bundle has multiple low-score frames, prefer fewer arrows per frame and split runtime, indexing, eval, and failure/retry concerns into separate diagrams.

## Preset Matrix

| Preset | Size | Use |
| --- | ---: | --- |
| presentation-16x9 | 1600x900 | Default for slides, chat previews, wide sharing |
| doc-wide | 1600x1000 | Default for docs and architecture pages |
| square-share | 1200x1200 | Compact social/chat artifact |
| mobile-share | 900x1200 | Phone-friendly vertical artifact |

For custom specs, keep dimensions explicit and make sure the SVG viewBox matches the viewport.

## Baseline Eval Prompts

Use these for private validation before publishing:

1. Create an architecture diagram for a generic order-to-POS workflow: upload order, review details, operator approval, POS send, sent/failed state. Show human approval and avoid implying fully automated approval.
2. Create a system diagram for a SaaS app with browser client, API, auth provider, payment provider, relational DB, webhook worker, and analytics destination. Show trust boundaries and source of truth.
3. Create a failure/retry path diagram for an async integration that receives webhooks, validates payloads, queues jobs, retries failed sends, dead-letters exhausted jobs, and alerts an operator.

Compare with-skill output against baseline output for artifact completeness, readability, false implications, and whether a rendered PNG exists.
