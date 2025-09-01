from pathlib import Path
import collections
import logging
from typing import OrderedDict


def get_mets(paths: list[Path]) -> dict[str, Path]:
    """Return dictionary of object_id to METS XML file path from batch folders."""
    mets = collections.OrderedDict()
    for path_batch in paths:
        logging.info("Searching METS files in %s", path_batch)
        for path in path_batch.rglob("*_mets.xml"):
            object_id = path.stem.replace('_mets', '')
            mets[object_id] = path
    logging.info("Found %d METS files", len(mets))
    return mets


def get_templates(path_templates: Path) -> dict[str, Path]:
    """Return dictionary of object_id to METS template file path."""
    templates = collections.OrderedDict()
    logging.info("Searching templates in %s", path_templates)
    for path in path_templates.rglob("*_mets_template.xml"):
        object_id = path.stem.replace('_mets_template', '')
        templates[object_id] = path
    logging.info("Found %d template files", len(templates))
    return templates