import html
import json
import logging
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .findings import Finding


def _object_id(report_key: str) -> str:
    return report_key.split(" - ")[0]


def _group_by_section(findings: List[Finding]) -> "OrderedDict[str, List[Finding]]":
    grouped: "OrderedDict[str, List[Finding]]" = OrderedDict()
    for finding in findings:
        grouped.setdefault(finding.section, []).append(finding)
    return grouped


def group_findings(errors: Dict[str, List[Finding]]):
    """Bundle identical findings across objects.

    Returns an OrderedDict keyed on (section, kind, path); each value is an
    OrderedDict keyed on (template_value, mets_value) mapping to the list of
    object IDs in which that exact change occurs.
    """
    groups: "OrderedDict[Tuple[str, str, str], OrderedDict]" = OrderedDict()
    for report_key, findings in errors.items():
        oid = _object_id(report_key)
        for f in findings:
            occurrences = groups.setdefault((f.section, f.kind, f.path), OrderedDict())
            ids = occurrences.setdefault((f.template_value, f.mets_value), [])
            if oid not in ids:
                ids.append(oid)
    return groups


def _group_object_count(occurrences) -> int:
    return len({oid for ids in occurrences.values() for oid in ids})


def write_reports(
    errors: Dict[str, List[Finding]],
    mets_diff_ids: Set[str],
    templates_diff_ids: Set[str],
    output: Path,
    batch_paths: List[Path],
    n_compared: Optional[int] = None,
) -> Tuple[Path, Path, Path]:
    """Write a Markdown report, a JSON file and an interactive HTML report."""
    output.mkdir(parents=True, exist_ok=True)
    batch_id = batch_paths[0].name.replace(" ", "_")
    dt = datetime.now()
    stem = f"compare_report-{batch_id}-{dt.strftime('%Y%m%d_%H%M%S')}"
    md_path = output / f"{stem}.md"
    json_path = output / f"{stem}.json"
    html_path = output / f"{stem}.html"

    total_findings = sum(len(findings) for findings in errors.values())
    groups = group_findings(errors)

    logging.info(
        f"Generating report for batch {batch_id} "
        f"(objects with findings: {len(errors)}, total findings: {total_findings})"
    )

    _write_markdown(md_path, errors, mets_diff_ids, templates_diff_ids,
                    batch_id, dt, total_findings, n_compared)
    _write_json(json_path, errors, groups, mets_diff_ids, templates_diff_ids,
                batch_paths, batch_id, dt, total_findings, n_compared)
    _write_html(html_path, errors, groups, mets_diff_ids, templates_diff_ids,
                batch_id, dt, total_findings, n_compared)

    logging.info(f"Saved reports for batch {batch_id} to {md_path}, {json_path} and {html_path}")
    return md_path, json_path, html_path


def _write_markdown(md_path, errors, mets_diff_ids, templates_diff_ids,
                    batch_id, dt, total_findings, n_compared) -> None:
    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Compare METS with Templates - {batch_id}\n\n")
        f.write(f"_report generated {dt.strftime('%Y-%m-%d %H:%M:%S')}_\n\n")

        f.write("## Summary\n")
        if n_compared is not None:
            f.write(f"- Objects compared: {n_compared}\n")
        f.write(f"- Objects with findings: {len(errors)}\n")
        f.write(f"- Total findings: {total_findings}\n")
        f.write(f"- Delivered METS without template: {len(mets_diff_ids)}\n")
        f.write(f"- Templates not returned in delivery: {len(templates_diff_ids)}\n\n")

        f.write("## Findings\n")
        if errors:
            for object_id, findings in errors.items():
                f.write(f"\n### {object_id}\n")
                for section, section_findings in _group_by_section(findings).items():
                    f.write(f"\n#### {section}\n\n")
                    for finding in section_findings:
                        f.write(f"- {finding.describe()}\n")
        else:
            f.write("\nNo findings: all compared sections are identical to the templates.\n")

        f.write("\n---\n\n## Delivery completeness\n\n")
        if templates_diff_ids:
            f.write(f"{len(templates_diff_ids)} templates were NOT returned in the delivery:\n\n")
            for oid in sorted(templates_diff_ids):
                f.write(f"- {oid}\n")
            f.write("\n")
        if mets_diff_ids:
            f.write(f"{len(mets_diff_ids)} delivered METS files have no matching template:\n\n")
            for oid in sorted(mets_diff_ids):
                f.write(f"- {oid}\n")
            f.write("\n")
        if not mets_diff_ids and not templates_diff_ids:
            f.write("All object IDs match between templates and delivered METS.\n")


def _write_json(json_path, errors, groups, mets_diff_ids, templates_diff_ids,
                batch_paths, batch_id, dt, total_findings, n_compared) -> None:
    report_data = {
        "generated": dt.isoformat(timespec="seconds"),
        "batch_id": batch_id,
        "batches": [str(p) for p in batch_paths],
        "summary": {
            "objects_compared": n_compared,
            "objects_with_findings": len(errors),
            "total_findings": total_findings,
            "mets_without_template": len(mets_diff_ids),
            "templates_not_returned": len(templates_diff_ids),
        },
        "grouped": [
            {
                "section": section,
                "kind": kind,
                "path": path,
                "object_count": _group_object_count(occurrences),
                "occurrences": [
                    {
                        "template_value": template_value,
                        "mets_value": mets_value,
                        "object_ids": ids,
                    }
                    for (template_value, mets_value), ids in occurrences.items()
                ],
            }
            for (section, kind, path), occurrences in groups.items()
        ],
        "objects": {
            key: [asdict(finding) | {"description": finding.describe()}
                  for finding in findings]
            for key, findings in errors.items()
        },
        "ids": {
            "mets_without_template": sorted(mets_diff_ids),
            "templates_not_returned": sorted(templates_diff_ids),
        },
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)


_HTML_STYLE = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     margin:2rem auto;max-width:1100px;padding:0 1rem;color:#1a1a1a;background:#fafafa}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}
.meta{color:#666;font-size:.85rem}
.cards{display:flex;gap:.8rem;flex-wrap:wrap;margin:1rem 0}
.card{border:1px solid #ddd;border-radius:8px;padding:.6rem 1rem;background:#fff;min-width:8rem}
.card .num{font-size:1.5rem;font-weight:700;display:block}
.card.warn .num{color:#c0392b}
.card .lbl{font-size:.8rem;color:#666}
details{border:1px solid #ddd;border-radius:8px;margin:.4rem 0;background:#fff}
details summary{cursor:pointer;padding:.55rem .9rem;display:flex;gap:.6rem;
                align-items:center;flex-wrap:wrap;list-style-position:outside}
details[open] summary{border-bottom:1px solid #eee}
.count{background:#1a6b9a;color:#fff;border-radius:999px;padding:.05rem .6rem;
       font-weight:600;font-size:.8rem;white-space:nowrap}
.count.all{background:#c0392b}
.kind{background:#eee;border-radius:4px;padding:.05rem .45rem;font-size:.8rem;color:#444}
.section-name{font-weight:600;font-size:.9rem}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
     font-size:.82rem;word-break:break-all}
.path{color:#555}
table{border-collapse:collapse;width:100%}
th,td{border-top:1px solid #eee;padding:.45rem .9rem;text-align:left;
      vertical-align:top;font-size:.85rem}
th{color:#666;font-weight:600}
td code{white-space:pre-wrap}
.ids{color:#555;max-height:8rem;overflow:auto}
.empty{color:#999;font-style:italic}
ul{margin:.4rem 0;padding:.2rem .9rem 0.6rem 2rem}
li{font-size:.85rem;margin:.2rem 0}
.ok{color:#1e7d32}
"""


def _esc(value: Optional[str]) -> str:
    if value is None:
        return "<span class='empty'>(empty)</span>"
    return f"<code>{html.escape(value)}</code>"


def _finding_html(f: Finding) -> str:
    if f.kind in ("missing-section", "extra-section", "missing-element",
                  "extra-element", "parse-error"):
        return (f"<code class='path'>{html.escape(f.path)}</code> "
                f"<span class='kind'>{f.kind}</span> "
                f"{_esc(f.mets_value) if f.kind == 'parse-error' else ''}")
    return (f"<code class='path'>{html.escape(f.path)}</code> "
            f"<span class='kind'>{f.kind}</span> "
            f"template {_esc(f.template_value)} → METS {_esc(f.mets_value)}")


def _write_html(html_path, errors, groups, mets_diff_ids, templates_diff_ids,
                batch_id, dt, total_findings, n_compared) -> None:
    out = []
    w = out.append
    w("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    w(f"<title>compare_mets - {html.escape(batch_id)}</title>")
    w(f"<style>{_HTML_STYLE}</style></head><body>")
    w(f"<h1>Compare METS with Templates — {html.escape(batch_id)}</h1>")
    w(f"<p class='meta'>report generated {dt.strftime('%Y-%m-%d %H:%M:%S')}</p>")

    w("<div class='cards'>")
    if n_compared is not None:
        w(f"<div class='card'><span class='num'>{n_compared}</span>"
          f"<span class='lbl'>objects compared</span></div>")
    warn = " warn" if errors else ""
    w(f"<div class='card{warn}'><span class='num'>{len(errors)}</span>"
      f"<span class='lbl'>objects with findings</span></div>")
    w(f"<div class='card{warn}'><span class='num'>{total_findings}</span>"
      f"<span class='lbl'>total findings</span></div>")
    w(f"<div class='card'><span class='num'>{len(groups)}</span>"
      f"<span class='lbl'>distinct changes</span></div>")
    warn_ids = " warn" if (mets_diff_ids or templates_diff_ids) else ""
    w(f"<div class='card{warn_ids}'><span class='num'>{len(templates_diff_ids)}</span>"
      f"<span class='lbl'>templates not returned</span></div>")
    w("</div>")

    w("<h2>Findings, bundled per change</h2>")
    if not groups:
        w("<p class='ok'>No findings: all compared sections are identical to the templates.</p>")
    ordered = sorted(groups.items(),
                     key=lambda item: _group_object_count(item[1]), reverse=True)
    for (section, kind, path), occurrences in ordered:
        object_count = _group_object_count(occurrences)
        is_all = n_compared is not None and object_count == n_compared
        count_label = f"{object_count} / {n_compared}" if n_compared is not None else str(object_count)
        count_cls = "count all" if is_all else "count"
        title = " title='occurs in ALL compared objects'" if is_all else ""
        w("<details>")
        w(f"<summary><span class='{count_cls}'{title}>{count_label} objects</span>"
          f"<span class='kind'>{html.escape(kind)}</span>"
          f"<span class='section-name'>{html.escape(section)}</span>"
          f"<code class='path'>{html.escape(path)}</code></summary>")
        w("<table><tr><th>Template</th><th>Delivered METS</th><th>Object IDs</th></tr>")
        for (template_value, mets_value), ids in occurrences.items():
            ids_html = html.escape(", ".join(ids))
            w(f"<tr><td>{_esc(template_value)}</td><td>{_esc(mets_value)}</td>"
              f"<td><div class='ids'>{ids_html} <b>({len(ids)})</b></div></td></tr>")
        w("</table></details>")

    w("<h2>Delivery completeness</h2>")
    if templates_diff_ids:
        w(f"<details><summary><span class='count all'>{len(templates_diff_ids)}</span> "
          f"templates NOT returned in the delivery</summary><ul>")
        for oid in sorted(templates_diff_ids):
            w(f"<li>{html.escape(oid)}</li>")
        w("</ul></details>")
    if mets_diff_ids:
        w(f"<details><summary><span class='count'>{len(mets_diff_ids)}</span> "
          f"delivered METS files without matching template</summary><ul>")
        for oid in sorted(mets_diff_ids):
            w(f"<li>{html.escape(oid)}</li>")
        w("</ul></details>")
    if not mets_diff_ids and not templates_diff_ids:
        w("<p class='ok'>All object IDs match between templates and delivered METS.</p>")

    if errors:
        w("<h2>Per object</h2>")
        for report_key, findings in errors.items():
            w(f"<details><summary><span class='count'>{len(findings)}</span> "
              f"{html.escape(report_key)}</summary><ul>")
            for f in findings:
                w(f"<li>{_finding_html(f)}</li>")
            w("</ul></details>")

    w("</body></html>")
    html_path.write_text("\n".join(out), encoding="utf-8")
