"""Semantic FigJam-inspired shape registry for diagrammer nodes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShapeSpec:
    id: str
    family: str
    label: str
    figjam_shape: str
    description: str


SHAPES = {
    "rounded-rectangle": ShapeSpec(
        id="rounded-rectangle",
        family="card",
        label="Rounded rectangle",
        figjam_shape="Rounded rectangle",
        description="Default FigJam node for services, APIs, workers, and generic components.",
    ),
    "database-cylinder": ShapeSpec(
        id="database-cylinder",
        family="system-symbol",
        label="Database cylinder",
        figjam_shape="Cylinder / Database",
        description="Persistent databases, stores, ledgers, and sources of truth.",
    ),
    "horizontal-cylinder": ShapeSpec(
        id="horizontal-cylinder",
        family="system-symbol",
        label="Horizontal cylinder",
        figjam_shape="Horizontal cylinder",
        description="Queues, streams, buffers, topics, and event pipes.",
    ),
    "cloud": ShapeSpec(
        id="cloud",
        family="system-symbol",
        label="Cloud",
        figjam_shape="Cloud",
        description="External SaaS providers, cloud platforms, and third-party network systems.",
    ),
    "user": ShapeSpec(
        id="user",
        family="system-symbol",
        label="User",
        figjam_shape="User",
        description="Humans, customers, operators, and user personas.",
    ),
    "document": ShapeSpec(
        id="document",
        family="flowchart",
        label="Document",
        figjam_shape="Document",
        description="Files, PDFs, reports, messages, and document-like artifacts.",
    ),
    "diamond": ShapeSpec(
        id="diamond",
        family="flowchart",
        label="Decision diamond",
        figjam_shape="Diamond",
        description="Decisions, gates, branch conditions, and manual approvals.",
    ),
    "shield": ShapeSpec(
        id="shield",
        family="flowchart",
        label="Shield",
        figjam_shape="Shield",
        description="Security, auth, risk, policy, and guardrail components.",
    ),
}

KIND_TO_SHAPE = {
    "api": "rounded-rectangle",
    "service": "rounded-rectangle",
    "worker": "rounded-rectangle",
    "client": "user",
    "user": "user",
    "operator": "user",
    "db": "database-cylinder",
    "database": "database-cylinder",
    "datastore": "database-cylinder",
    "storage": "database-cylinder",
    "ledger": "database-cylinder",
    "queue": "horizontal-cylinder",
    "stream": "horizontal-cylinder",
    "topic": "horizontal-cylinder",
    "buffer": "horizontal-cylinder",
    "external": "cloud",
    "provider": "cloud",
    "cloud": "cloud",
    "document": "document",
    "file": "document",
    "pdf": "document",
    "decision": "diamond",
    "gateway": "diamond",
    "approval": "diamond",
    "auth": "shield",
    "security": "shield",
    "risk": "shield",
}

LABEL_KEYWORDS = (
    ("queue", "horizontal-cylinder"),
    ("stream", "horizontal-cylinder"),
    ("topic", "horizontal-cylinder"),
    ("buffer", "horizontal-cylinder"),
    ("db", "database-cylinder"),
    ("database", "database-cylinder"),
    ("store", "database-cylinder"),
    ("ledger", "database-cylinder"),
    ("provider", "cloud"),
    ("cloud", "cloud"),
    ("external", "cloud"),
    ("customer", "user"),
    ("operator", "user"),
    ("user", "user"),
    ("pdf", "document"),
    ("document", "document"),
    ("file", "document"),
    ("risk", "shield"),
    ("auth", "shield"),
    ("security", "shield"),
    ("approval", "diamond"),
    ("decision", "diamond"),
)

GENERIC_KIND_LABEL_KEYWORDS = (
    ("risk", "shield"),
    ("auth", "shield"),
    ("security", "shield"),
    ("approval", "diamond"),
    ("decision", "diamond"),
)


def known_kinds():
    return set(KIND_TO_SHAPE)


def resolve_node_shape(node):
    """Resolve a semantic node definition to a visual shape id."""
    explicit = node.get("shape")
    if explicit:
        return explicit if explicit in SHAPES else "rounded-rectangle"

    kind = str(node.get("kind", "service")).lower()
    label = str(node.get("label", node.get("id", ""))).lower()
    if kind in {"service", "worker", "api"}:
        for keyword, shape_id in GENERIC_KIND_LABEL_KEYWORDS:
            if keyword in label:
                return shape_id
    if kind in KIND_TO_SHAPE:
        return KIND_TO_SHAPE[kind]
    for keyword, shape_id in LABEL_KEYWORDS:
        if keyword in label:
            return shape_id
    return "rounded-rectangle"


def shape_spec(shape_id):
    return SHAPES.get(shape_id, SHAPES["rounded-rectangle"])
