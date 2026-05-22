"""Typed internal contracts shared across diagram layout, routing, and rendering."""

from dataclasses import dataclass, field, fields
from typing import Any


class ContractMapping:
    """Small mapping adapter for internal dataclasses.

    The compiler still exposes dictionaries publicly. Internally these contracts
    make cross-module fields explicit while preserving existing dict-style helper
    access during the refactor.
    """

    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _field_keys(cls) -> dict[str, str]:
        return {item.metadata.get("key", item.name): item.name for item in fields(cls) if item.name != "_extra"}

    @classmethod
    def from_mapping(cls, value):
        if isinstance(value, ContractMapping):
            value = value.to_dict()
        keys = cls._field_keys()
        kwargs = {}
        extra = {}
        for key, item in dict(value).items():
            if key in keys:
                kwargs[keys[key]] = item
            else:
                extra[key] = item
        instance = cls(**kwargs)
        instance._extra.update(extra)
        return instance

    def __getitem__(self, key):
        field_name = self._field_keys().get(key)
        if field_name:
            return getattr(self, field_name)
        return self._extra[key]

    def __setitem__(self, key, value):
        field_name = self._field_keys().get(key)
        if field_name:
            setattr(self, field_name, value)
        else:
            self._extra[key] = value

    def __contains__(self, key):
        return key in self._field_keys() or key in self._extra

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())

    def get(self, key, default=None):
        return self[key] if key in self else default

    def pop(self, key, default=None):
        field_name = self._field_keys().get(key)
        if field_name:
            value = getattr(self, field_name)
            setattr(self, field_name, default)
            return value
        return self._extra.pop(key, default)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def update(self, values):
        for key, value in values.items():
            self[key] = value

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

    def keys(self):
        return self.to_dict().keys()

    def to_dict(self):
        result = {}
        for item in fields(self):
            if item.name == "_extra":
                continue
            key = item.metadata.get("key", item.name)
            value = getattr(self, item.name)
            if value is None:
                continue
            result[key] = _to_dict(value)
        result.update({key: _to_dict(value) for key, value in self._extra.items()})
        return result


def _to_dict(value):
    if isinstance(value, ContractMapping):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _to_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dict(item) for item in value]
    return value


@dataclass
class NodeBox(ContractMapping):
    id: str
    type: str = "node"
    kind: str = "service"
    shape: str = "rounded-rectangle"
    shapeFamily: str = "rectangle"
    label: str = ""
    detail: list[str] = field(default_factory=list)
    labelLines: list[str] = field(default_factory=list)
    detailLines: list[str] = field(default_factory=list)
    lane: int = 0
    rank: int = 0
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class AnnotationBox(ContractMapping):
    id: str
    type: str = "annotation"
    title: str = "Note"
    lines: list[str] = field(default_factory=list)
    lane: int = 0
    rank: int = 0
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class LabelBox(ContractMapping):
    type: str = "edge-label"
    label: str = ""
    lines: list[str] = field(default_factory=list)
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    anchor: dict[str, Any] | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class RoutedEdge(ContractMapping):
    id: str
    from_: str = field(default="", metadata={"key": "from"})
    to: str = ""
    kind: str = "sync"
    label: str = ""
    route: str = "direct"
    path: str = ""
    segments: list[dict[str, Any]] = field(default_factory=list)
    sourcePort: str | None = None
    targetPort: str | None = None
    sourceOffset: float = 0
    targetOffset: float = 0
    routeLaneOffset: float = 0
    sourceRank: int = 0
    targetRank: int = 0
    sourceLane: int = 0
    targetLane: int = 0
    routeLength: float = 0
    labelBox: LabelBox | None = None
    labelPosition: str | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class DiagramLayout(ContractMapping):
    title: str
    subtitle: str = ""
    template: str = "system-left-to-right"
    canvas: dict[str, Any] = field(default_factory=dict)
    boxes: dict[str, NodeBox] = field(default_factory=dict)
    edges: list[RoutedEdge] = field(default_factory=list)
    annotations: list[AnnotationBox] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    notImplied: list[str] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)
