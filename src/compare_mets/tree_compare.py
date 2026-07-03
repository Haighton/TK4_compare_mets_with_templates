"""Strict element-tree comparison between a template and a delivered METS.

Unlike a generic XML diff, this answers one question: is the delivered tree
identical to the template tree, apart from explicitly allowed deviations?
Every mismatch is reported as a Finding with a readable path and both values.

Normalisation that happens implicitly:
- empty elements and self-closing tags are identical after parsing;
- leading/trailing whitespace around text is ignored;
- attribute order is irrelevant (attributes are compared as a mapping);
- namespace *prefixes* are irrelevant (tags are compared by namespace URI).
"""
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from .config import CompareConfig
from .findings import Finding


def prefix_map(config: CompareConfig) -> Dict[str, str]:
    """Map namespace URIs back to prefixes, for readable paths."""
    return {uri: prefix for prefix, uri in config.namespaces.items()}


def qname(tag: str, prefixes: Dict[str, str]) -> str:
    """Convert a Clark-notation tag to a prefixed name where possible."""
    if not isinstance(tag, str) or not tag.startswith("{"):
        return str(tag)
    uri, _, local = tag[1:].partition("}")
    prefix = prefixes.get(uri)
    return f"{prefix}:{local}" if prefix else tag


def compare_trees(template_el, mets_el, section: str, config: CompareConfig,
                  path: Optional[str] = None) -> List[Finding]:
    """Compare two elements recursively and return all differences."""
    prefixes = prefix_map(config)
    if path is None:
        path = qname(template_el.tag, prefixes)
    findings: List[Finding] = []
    _compare(template_el, mets_el, section, config, prefixes, path, findings,
             compare_tail=False)
    return findings


def _norm(text: Optional[str]) -> Optional[str]:
    return (text or "").strip() or None


def _child_paths(children, parent_path: str, prefixes: Dict[str, str]) -> List[str]:
    """Build a path per child, with [n] only when the tag occurs more than once."""
    counts = Counter(child.tag for child in children)
    seen: Counter = Counter()
    paths = []
    for child in children:
        seen[child.tag] += 1
        name = qname(child.tag, prefixes)
        if counts[child.tag] > 1:
            name = f"{name}[{seen[child.tag]}]"
        paths.append(f"{parent_path}/{name}")
    return paths


def _compare(template_el, mets_el, section, config, prefixes, path, findings,
             compare_tail: bool) -> None:
    if template_el.tag != mets_el.tag:
        findings.append(Finding(section, "element", path,
                                qname(template_el.tag, prefixes),
                                qname(mets_el.tag, prefixes)))
        return

    template_attrs = dict(template_el.attrib)
    mets_attrs = dict(mets_el.attrib)
    for name in sorted(set(template_attrs) | set(mets_attrs)):
        if template_attrs.get(name) != mets_attrs.get(name):
            findings.append(Finding(section, "attribute",
                                    f"{path}/@{qname(name, prefixes)}",
                                    template_attrs.get(name),
                                    mets_attrs.get(name)))

    if template_el.tag not in config.ignore_text:
        template_text, mets_text = _norm(template_el.text), _norm(mets_el.text)
        if template_text != mets_text:
            findings.append(Finding(section, "text", path, template_text, mets_text))

    if compare_tail:
        template_tail, mets_tail = _norm(template_el.tail), _norm(mets_el.tail)
        if template_tail != mets_tail:
            findings.append(Finding(section, "text", f"{path} (tail)",
                                    template_tail, mets_tail))

    template_children = list(template_el)
    mets_children = list(mets_el)
    template_paths = _child_paths(template_children, path, prefixes)
    mets_paths = _child_paths(mets_children, path, prefixes)

    # Align children on their tag sequence, so that a single inserted or
    # removed element does not misalign everything after it.
    matcher = SequenceMatcher(
        None,
        [child.tag for child in template_children],
        [child.tag for child in mets_children],
        autojunk=False,
    )
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal" or (op == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1):
                _compare(template_children[i1 + k], mets_children[j1 + k],
                         section, config, prefixes, template_paths[i1 + k],
                         findings, compare_tail=True)
        else:
            for k in range(i1, i2):
                findings.append(Finding(section, "missing-element",
                                        template_paths[k],
                                        qname(template_children[k].tag, prefixes),
                                        None))
            for k in range(j1, j2):
                findings.append(Finding(section, "extra-element",
                                        mets_paths[k],
                                        None,
                                        qname(mets_children[k].tag, prefixes)))
