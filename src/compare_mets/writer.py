import json
import logging
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .findings import Finding


def _group_by_section(findings: List[Finding]) -> "OrderedDict[str, List[Finding]]":
    grouped: "OrderedDict[str, List[Finding]]" = OrderedDict()
    for finding in findings:
        grouped.setdefault(finding.section, []).append(finding)
    return grouped


def write_reports(
    errors: Dict[str, List[Finding]],
    mets_diff_ids: Set[str],
    templates_diff_ids: Set[str],
    output: Path,
    batch_paths: List[Path],
) -> Tuple[Path, Path]:
    """Write a Markdown report and a machine-readable JSON file."""
    output.mkdir(parents=True, exist_ok=True)
    batch_id = batch_paths[0].name.replace(" ", "_")
    dt = datetime.now()
    stem = f"compare_report-{batch_id}-{dt.strftime('%Y%m%d_%H%M%S')}"
    md_path = output / f"{stem}.md"
    json_path = output / f"{stem}.json"

    total_findings = sum(len(findings) for findings in errors.values())

    logging.info(
        f"Generating report for batch {batch_id} "
        f"(objects with findings: {len(errors)}, total findings: {total_findings})"
    )

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Compare METS with Templates - {batch_id}\n\n")
        f.write(f"_report generated {dt.strftime('%Y-%m-%d %H:%M:%S')}_\n\n")

        f.write("## Summary\n")
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

    report_data = {
        "generated": dt.isoformat(timespec="seconds"),
        "batch_id": batch_id,
        "batches": [str(p) for p in batch_paths],
        "summary": {
            "objects_with_findings": len(errors),
            "total_findings": total_findings,
            "mets_without_template": len(mets_diff_ids),
            "templates_not_returned": len(templates_diff_ids),
        },
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

    logging.info(f"Saved reports for batch {batch_id} to {md_path} and {json_path}")
    return md_path, json_path
