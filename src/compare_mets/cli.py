import argparse
import logging
import multiprocessing
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path

from tqdm.contrib.logging import logging_redirect_tqdm

from . import __version__
from .compare import compare_files, different_ids
from .config import default_config, load_config
from .parser import get_mets, get_templates
from .writer import write_reports

log_queue = multiprocessing.Queue()

# Exit codes: 0 = no discrepancies, 1 = discrepancies found, 2 = usage error.
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare delivered METS files with KB METS templates."
    )
    parser.add_argument("templates", type=Path,
                        help="Path to the METS templates directory.")
    parser.add_argument("batches", type=Path, nargs="+",
                        help="One or more batch directories with delivered METS files.")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./output"),
        help="Directory to save output reports (default: ./output)"
    )
    parser.add_argument("-c", "--config", type=Path, default=None,
                        help="Optional TOML file overriding sections/allowed deviations.")
    parser.add_argument("--max-workers", type=int, default=None,
                        help="Number of worker processes (default: CPU count - 1).")

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress info messages, only show errors (ERROR level)")

    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}",
                        help="Show program version and exit.")
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

    queue_handler = QueueHandler(log_queue)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [queue_handler]

    listener = QueueListener(log_queue, console_handler, file_handler)
    listener.start()
    return listener


def validate_paths(templates: Path, batches: list) -> None:
    """Ensure provided paths exist and are directories."""
    if not templates.exists() or not templates.is_dir():
        logging.error(f"Template path does not exist or is not a directory: {templates}")
        sys.exit(EXIT_USAGE)

    for batch in batches:
        if not batch.exists() or not batch.is_dir():
            logging.error(f"Batch path does not exist or is not a directory: {batch}")
            sys.exit(EXIT_USAGE)


def main() -> None:
    """Run the comparison process."""
    args = parse_args()
    listener = setup_logging(verbose=args.verbose, quiet=args.quiet)
    exit_code = EXIT_OK

    try:
        validate_paths(args.templates, args.batches)
        config = load_config(args.config) if args.config else default_config()

        logging.info("Loading METS files from batches...")
        mets = get_mets(args.batches)
        logging.info(f"Loading template files from {args.templates}")
        templates_dict = get_templates(args.templates)

        if not mets:
            logging.error("No METS files found in the given batch paths.")
            sys.exit(EXIT_USAGE)
        if not templates_dict:
            logging.error("No template files found in the given template path.")
            sys.exit(EXIT_USAGE)

        common_ids = set(mets.keys()) & set(templates_dict.keys())
        logging.info(
            f"Total METS: {len(mets)} | Total templates: {len(templates_dict)} "
            f"| Common IDs: {len(common_ids)}")

        logging.info("Comparing METS files against templates...")
        errors = compare_files(
            mets,
            templates_dict,
            config=config,
            max_workers=args.max_workers,
            log_queue=log_queue,
        )

        logging.info("Checking delivery completeness (IDs sent vs returned)...")
        mets_diff_ids, templates_diff_ids = different_ids(mets, templates_dict)

        logging.info(f"Writing output to {args.output}")
        write_reports(errors, mets_diff_ids, templates_diff_ids,
                      args.output, args.batches, n_compared=len(common_ids))

        total_findings = sum(len(findings) for findings in errors.values())
        logging.info(
            f"Summary: {len(errors)} objects with findings | {total_findings} total findings")

        if mets_diff_ids or templates_diff_ids:
            logging.info(
                f"Delivery incomplete (METS without template: {len(mets_diff_ids)}, "
                f"templates not returned: {len(templates_diff_ids)})")
        else:
            logging.info("All object IDs matched between METS and templates.")

        if errors or mets_diff_ids or templates_diff_ids:
            exit_code = EXIT_FINDINGS
        logging.info("Done.")
    finally:
        listener.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    with logging_redirect_tqdm():
        main()
