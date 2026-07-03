"""Typed comparison results."""
from dataclasses import dataclass
from typing import Optional


def _fmt(value: Optional[str], limit: int = 120) -> str:
    if value is None:
        return "(empty)"
    if len(value) > limit:
        value = value[:limit] + "…"
    return f"'{value}'"


@dataclass(frozen=True)
class Finding:
    """A single difference between a METS template and a delivered METS file.

    kind is one of: text, attribute, element, missing-element, extra-element,
    missing-section, extra-section, section-count, parse-error.
    """
    section: str
    kind: str
    path: str
    template_value: Optional[str] = None
    mets_value: Optional[str] = None

    def describe(self) -> str:
        t, m = _fmt(self.template_value), _fmt(self.mets_value)
        if self.kind == "text":
            return f"`{self.path}` — text changed: template {t} → METS {m}"
        if self.kind == "attribute":
            return f"`{self.path}` — attribute changed: template {t} → METS {m}"
        if self.kind == "element":
            return f"`{self.path}` — element replaced: template has {t}, METS has {m}"
        if self.kind == "missing-element":
            return f"`{self.path}` — element missing in METS (present in template)"
        if self.kind == "extra-element":
            return f"`{self.path}` — extra element in METS (not in template)"
        if self.kind == "missing-section":
            return f"`{self.path}` — section missing in METS (present in template)"
        if self.kind == "extra-section":
            return f"`{self.path}` — extra section in METS (not in template)"
        if self.kind == "section-count":
            return f"`{self.path}` — number of sections differs: template {t}, METS {m}"
        if self.kind == "parse-error":
            return f"`{self.path}` — file could not be parsed: {self.mets_value}"
        return f"`{self.path}` — {self.kind}: template {t} → METS {m}"
