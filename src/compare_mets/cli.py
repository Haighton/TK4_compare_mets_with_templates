import logging
import argparse
import sys
import multiprocessing
from pathlib import Path
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

from tqdm.contrib.logging import logging_redirect_tqdm

from .parser import get_mets, get_templates
from .compare import compare_files, different_ids
from .writer import print_errors
from . import __version__


log_queue = multiprocessing.Queue()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare METS files with KB METS templates."
    )

    # Positional arguments (optioneel gemaakt)
    parser.add_argument("templates", type=Path, nargs="?",
                        help="Path to the METS templates directory (positional).")
    parser.add_argument("batches", type=Path, nargs="*",
                        help="One or more batch directories (positional).")

    # Flags (alternatief)
    parser.add_argument("--templates", dest="templates_flag",
                        type=Path, help="Alternative to positional.")
    parser.add_argument("--batches", dest="batches_flag",
                        type=Path, nargs="+", help="Alternative to positional.")

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./output"),
        help="Directory to save output reports (default: ./output)"
    )

    # Logging flags
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress info messages, only show errors (ERROR level)")

    # Diff options
    parser.add_argument("--diff-threshold", type=float, default=0.5,
                        help="Similarity threshold for xmldiff (default: 0.5).")
    parser.add_argument(
        "--diff-ratio-mode", choices=["fast", "accurate"], default="fast", help="Ratio mode for xmldiff.")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="Show program version and exit.")
    return parser.parse_args()


def setup_logging(verbose: bool = False, quiet: bool = False) -> QueueListener:
    """Configure logging with a queue for multiprocessing safety."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "compare_mets.log"

    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Queue setup
    queue_handler = QueueHandler(log_queue)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [queue_handler]

    listener = QueueListener(log_queue, console_handler, file_handler)
    listener.start()
    return listener


def validate_paths(templates: Path, batches: list[Path]) -> None:
    """Ensure provided paths exist and are directories."""
    if not templates.exists() or not templates.is_dir():
        logging.error(f"Template path does not exist or is not a directory: {templates}")
        sys.exit(1)

    for batch in batches:
        if not batch.exists() or not batch.is_dir():
            logging.error(f"Batch path does not exist or is not a directory: {batch}")
            sys.exit(1)


def main() -> None:
    """Run the comparison process."""
    args = parse_args()
    listener = setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        templates = args.templates_flag or args.templates
        batches = args.batches_flag or args.batches

        if not templates or not batches:
            logging.error(
                "You must provide templates and batches (via positionals or flags).")
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
            logging.error(
                "No template files found in the given template path.")
            sys.exit(1)

        common_ids = set(mets.keys()) & set(templates_dict.keys())
        logging.info(f"Total METS: {len(mets)} | Total templates: {len(templates_dict)} | Common IDs: {len(common_ids)}")
        logging.debug(f"CLI options: diff_threshold={args.diff_threshold}, diff_ratio_mode={args.diff_ratio_mode}")

        logging.info("Comparing METS files against templates...")
        errors = compare_files(
            mets,
            templates_dict,
            diff_threshold=args.diff_threshold,
            diff_ratio_mode=args.diff_ratio_mode,
        )

        logging.info("Checking for ID mismatches...")
        mets_diff_ids, templates_diff_ids = different_ids(mets, templates_dict)

        logging.info(f"Writing output to {args.output}")
        print_errors(errors, templates, mets_diff_ids,
                     templates_diff_ids, args.output, batches)

        total_diffs = sum(len(section) - 1 for diffs in errors.values()
                          for section in diffs)
        logging.info(f"Summary: {len(errors)} files with discrepancies | {total_diffs} total difference blocks")

        if mets_diff_ids or templates_diff_ids:
            logging.info(f"Object ID mismatches detected (METS-only: {len(mets_diff_ids)}, Templates-only: {len(templates_diff_ids)})")
        else:
            logging.info("All object IDs matched between METS and templates.")

        logging.info("Done.")
    finally:
        listener.stop()


if __name__ == "__main__":
    with logging_redirect_tqdm():
        main()
