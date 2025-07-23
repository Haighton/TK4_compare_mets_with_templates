import logging
import argparse
import sys
from pathlib import Path
from tqdm.contrib.logging import logging_redirect_tqdm
from .parser import get_mets, get_templates
from .compare import compare_files, different_ids
from .writer import print_errors
from . import __version__


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare METS files with KB METS templates."
    )
    parser.add_argument("templates", type=Path, help="Path to the METS templates directory.")
    parser.add_argument("batches", nargs='+', type=Path, help="One or more batch directories.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to save output reports (default: current working directory)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit."
    )
    return parser.parse_args()


def setup_logging() -> None:
    """Configure logging format and level."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )


def validate_paths(templates: Path, batches: list[Path]) -> None:
    """Ensure provided paths exist and are directories."""
    if not templates.exists() or not templates.is_dir():
        logging.error("Template path does not exist or is not a directory: %s", templates)
        sys.exit(1)

    for batch in batches:
        if not batch.exists() or not batch.is_dir():
            logging.error("Batch path does not exist or is not a directory: %s", batch)
            sys.exit(1)


def main() -> None:
    """Run the comparison process."""
    setup_logging()
    args = parse_args()

    validate_paths(args.templates, args.batches)

    logging.info("Loading METS files from batches...")
    mets = get_mets(args.batches)
    logging.info("Loading template files from %s", args.templates)
    templates = get_templates(args.templates)

    if not mets:
        logging.error("No METS files found in the given batch paths.")
        sys.exit(1)
    if not templates:
        logging.error("No template files found in the given template path.")
        sys.exit(1)

    common_ids = set(mets.keys()) & set(templates.keys())
    logging.info("Total METS: %d | Total templates: %d | Common object IDs: %d",
                 len(mets), len(templates), len(common_ids))

    logging.info("Comparing METS files against templates...")
    errors = compare_files(mets, templates)
    logging.info("Checking for ID mismatches...")
    mets_diff_ids, templates_diff_ids = different_ids(mets, templates)

    logging.info("Writing output to %s", args.output_dir)
    print_errors(errors, args.templates, mets_diff_ids, templates_diff_ids, args.output_dir, args.batches)

    # Final summary
    total_diffs = sum(len(section) - 1 for diffs in errors.values() for section in diffs)
    logging.info("Summary: %d files with discrepancies | %d total difference blocks",
                 len(errors), total_diffs)

    if mets_diff_ids or templates_diff_ids:
        logging.info("Object ID mismatches detected (METS-only: %d, Templates-only: %d)",
                     len(mets_diff_ids), len(templates_diff_ids))
    else:
        logging.info("All object IDs matched between METS and templates.")

    logging.info("Done.")


if __name__ == '__main__':
    with logging_redirect_tqdm():
        main()
