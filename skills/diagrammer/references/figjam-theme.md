# FigJam-Inspired Default Theme

Use this for the default diagrammer look unless the user asks for a stricter brand or documentation style.

## Visual Tokens

- Canvas: warm whiteboard off-white, optionally with an extremely subtle dot grid.
- Nodes: rounded rectangles, 10-12px radius, white or very pale sticky-note fills.
- Common system elements should use simple canonical symbols on the open canvas:
  - Database: standalone cylinder symbol, optionally with 3-5 schema/status bullets inside.
  - Queue / stream / buffer: flatter horizontal cylinder/buffer: long body, rounded left cap, visible right end ellipse.
  - Worker / service / API / UI: rounded rectangle node without extra pictograms unless the symbol clarifies the system.
- Strokes: dark neutral for nodes, light neutral for boundaries, one primary connector color, one exception color.
- Typography: Liberation Sans, Arial, Helvetica, sans-serif on this host; use large labels over dense annotations.
- Connectors: straight segments with rounded 90-degree elbows, round caps/joins, compact open chevron arrow tips by default.
- Connector labels: inline text gaps by default: connector stroke, canvas-colored gap, label text, then connector stroke resumes. Avoid bordered pill chips unless the label is an annotation rather than part of the arrow.
- Label only the connectors that need clarification. If two labels collide or stack tightly, remove the redundant one before shrinking text.
- Ordinary connector strokes should stay gray/neutral. Use red only for failure, retry, guard, or exception paths.
- Effects: no shadows by default. Create depth with spacing, stroke weight, and grouping.

## Layout Rules

- Place branch outcomes close to the branching system; do not route outcome lines across unrelated boundaries.
- Leave clear vertical air between sibling branch connectors and labels; outcome branches should not share a cramped elbow cluster.
- Prefer a larger board over cramped routing. For system diagrams with queues, databases, and branches, use a wider/taller custom canvas when the default 16:9 share preset forces labels between arrows.
- Prefer short return loops to the nearest previous step over long loops across the whole diagram.
- Use symmetric branch geometry where outcomes are peers.
- Mark repeated node rows with classes such as \`flow-step\` and \`flow-outcome\` so validation can enforce row alignment, consistent heights, and rounded corners.
- Avoid surrounding container boxes by default. Use small text labels, spacing, and connector direction for grouping unless an ownership/trust boundary is the point of the diagram.
- Annotation blocks are valid first-class elements on the board for requirements, entities, tradeoffs, and not-implied notes. Keep them open-canvas by default rather than putting them in cards.
- Keep the code primitive and the shape meaning aligned: database cylinders should be created by a db_cylinder-style helper, queues by a horizontal queue_cylinder-style helper, notes by annotation_block, and flows by connector helpers.
- If a diagram needs many labels or crossings, split it into multiple frames.
