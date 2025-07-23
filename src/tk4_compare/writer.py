from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Set


def print_errors(
    errors,
    path_templates: Path,
    mets_diff_ids,
    templates_diff_ids,
    output_dir: Path,
    batch_paths: list[Path]
):
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_id = batch_paths[0].name.replace(' ', '_')
    dt = datetime.now()
    output_name = f"compare_report-{batch_id}-{dt.strftime('%Y%m%d_%H%M%S')}.md"
    output_path = output_dir / output_name

    with output_path.open('w', encoding='utf-8') as f:
        f.write(f"# Compare METS with Templates - {batch_id}\n\n")
        f.write(f"_log generated {dt.strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
        f.write('## Data discrepancies\n')
        if errors:
            for object_id, diffs in errors.items():
                f.write(f"\n### {object_id}\n")
                for err in diffs:
                    f.write(f"\n#### {err[0]}\n\n")
                    for detail in err[1:]:
                        f.write(f"- {detail}\n")
        else:
            f.write('\nNo data discrepancies found.\n')
        f.write('\n---\n\n## ID discrepancies\n\n')
        if mets_diff_ids:
            f.write(f"There are {len(mets_diff_ids)} unique object id's in METS:\n\n")
            for oid in sorted(mets_diff_ids):
                f.write(f"- {oid}\n")
        if templates_diff_ids:
            f.write(f"\nThere are {len(templates_diff_ids)} unique object id's in templates:\n\n")
            for oid in sorted(templates_diff_ids):
                f.write(f"- {oid}\n")
        if not mets_diff_ids and not templates_diff_ids:
            f.write("Same object ID's found in METS and templates.\n")

    logging.info("Saved output to %s", output_path)
