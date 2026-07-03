"""Comparison configuration: which sections to check and which deviations are allowed.

The defaults match the KB newspaper projects (BKT2/BKT3/TK4). A project can
override them with a small TOML file passed via --config, e.g.:

    ignore_text = ["premis:eventDateTime"]

    [[sections]]
    label = "mets:dmdSec"
    xpath = '//mets:dmdSec[@ID="DMD1"]'
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

DEFAULT_NAMESPACES = {
    "mets": "http://www.loc.gov/METS/",
    "mods": "http://www.loc.gov/mods/v3",
    "premis": "info:lc/xmlns/premis-v2",
    "kbmd": "http://schemas.kb.nl/kbmd/v1",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xlink": "http://www.w3.org/1999/xlink",
    "mix": "http://www.loc.gov/mix/v20",
    "pica": "info:srw/schema/5/picaXML-v1.0",
    "marc": "http://www.loc.gov/MARC21/slim",
}

DEFAULT_SECTIONS = (
    ("mets:dmdSec", '//mets:dmdSec[@ID="DMD1"]'),
    ("mets:techMD", '//mets:techMD[@ID="TMD00001"]'),
    ("mets:rightsMD", '//mets:rightsMD[@ADMID="TMD00001"]'),
    ("kbmd:catalogRecord", "//kbmd:catalogRecord"),
    ("mets:sourceMD[SMD2]", '//mets:sourceMD[@ID="SMD2"]'),
    ("mets:digiprovMD", "//mets:digiprovMD"),
)

# Elements whose text the supplier is allowed to change.
DEFAULT_IGNORE_TEXT = ("premis:eventDateTime",)


@dataclass(frozen=True)
class CompareConfig:
    namespaces: Dict[str, str]
    sections: Tuple[Tuple[str, str], ...]
    ignore_text: FrozenSet[str]  # element tags in Clark notation ({uri}local)


def _clark(name: str, namespaces: Dict[str, str]) -> str:
    """Convert a prefixed name like 'premis:eventDateTime' to Clark notation."""
    prefix, _, local = name.rpartition(":")
    if not prefix:
        return local
    return f"{{{namespaces[prefix]}}}{local}"


def make_config(namespaces, sections, ignore_text) -> CompareConfig:
    return CompareConfig(
        namespaces=dict(namespaces),
        sections=tuple((label, xpath) for label, xpath in sections),
        ignore_text=frozenset(_clark(name, namespaces) for name in ignore_text),
    )


def default_config() -> CompareConfig:
    return make_config(DEFAULT_NAMESPACES, DEFAULT_SECTIONS, DEFAULT_IGNORE_TEXT)


def load_config(path: Path) -> CompareConfig:
    """Load a project config from TOML; unspecified keys keep their defaults."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    namespaces = {**DEFAULT_NAMESPACES, **data.get("namespaces", {})}
    if "sections" in data:
        sections = tuple((s["label"], s["xpath"]) for s in data["sections"])
    else:
        sections = DEFAULT_SECTIONS
    ignore_text = tuple(data.get("ignore_text", DEFAULT_IGNORE_TEXT))
    return make_config(namespaces, sections, ignore_text)
