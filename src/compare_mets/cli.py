import logging
import argparse
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

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

    # Positional arguments (optioneel gemaakt)
    parser.add_argument(
        "templates",
        type=Path,
        nargs="?",
        help="Path to the METS templates directory (positional)."
    )
    parser.add_argument(
        "batches",
        type=Path,
        nargs="*",
        help="One or more batch directories (positional)."
    )

    # Flags (alternatief)
    parser.add_argument(
        "--templates",
        dest="templates_flag",
        type=Path,
        help="Path to the METS templates directory (alternative to positional)."
    )
    parser.add_argument(
        "--batches",
        dest="batches_flag",
        type=Path,
        nargs="+",
        help="One or more batch directories (alternative to positional)."
    )

    parser.add_argument(
        "-o", "--output",
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
    """Configure logging format and level, with rotating file handler."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)  # zorg dat logs/ bestaat
    log_file = log_dir / "compare_mets.log"

    # formatter voor zowel console als file
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    # File handler met rotatie (bijv. max 5 MB per file, max 5 oude bestanden)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,             # bewaar max 5 oude versies
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
        force=True  # overschrijf eerdere logging-config
    )


def validate_paths(templates: Path, batches: list[Path]) -> None:
    """Ensure provided paths exist and are directories."""
    if not templates.exists() or not templates.is_dir():
        logging.error(
            f"Template path does not exist or is not a directory: {templates}")
        sys.exit(1)

    for batch in batches:
        if not batch.exists() or not batch.is_dir():
            logging.error(
                f"Batch path does not exist or is not a directory: {batch}")
            sys.exit(1)


def main() -> None:
    """Run the comparison process."""
    setup_logging()
    args = parse_args()

    # Kies: gebruik flags als ze zijn meegegeven, anders positionals
    templates = args.templates_flag or args.templates
    batches = args.batches_flag or args.batches

    if not templates or not batches:
        logging.error("You must provide templates and batches (via positionals or flags).")
        sys.exit(1)

    validate_paths(templates, batches)

    logging.info("Loading METS files from batches...")
    mets = get_mets(batches)
    logging.info(f"Loading template files from {templates}")
    templates_dict = get_templates(templates)

    if not mets:
        logging.error("No METS files found in the given batch paths.")
        sys.exit(1)
    if not templates_dict:
        logging.error("No template files found in the given template path.")
        sys.exit(1)

    common_ids = set(mets.keys()) & set(templates_dict.keys())
    logging.info("Total METS: %d | Total templates: %d | Common object IDs: %d",
                 len(mets), len(templates_dict), len(common_ids))

    logging.info("Comparing METS files against templates...")
    errors = compare_files(mets, templates_dict)
    logging.info("Checking for ID mismatches...")
    mets_diff_ids, templates_diff_ids = different_ids(mets, templates_dict)

    logging.info(f"Writing output to {args.output}")
    print_errors(errors, templates, mets_diff_ids,
                 templates_diff_ids, args.output, batches)

    # Final summary
    total_diffs = sum(len(section) - 1 for diffs in errors.values()
                      for section in diffs)
    logging.info(f"Summary: {len(errors)} files with discrepancies | {total_diffs} total difference blocks")

    if mets_diff_ids or templates_diff_ids:
        logging.info("Object ID mismatches detected (METS-only: %d, Templates-only: %d)",
                     len(mets_diff_ids), len(templates_diff_ids))
    else:
        logging.info("All object IDs matched between METS and templates.")

    logging.info("Done.")


if __name__ == '__main__':
    with logging_redirect_tqdm():
        main()
