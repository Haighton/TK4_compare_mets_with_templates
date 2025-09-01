from pathlib import Path
import collections
import logging
from typing import Dict


def get_mets(paths: list[Path]) -> Dict[str, Path]:
    """Return dictionary of object_id to METS XML file path from batch folders."""
    mets = collections.OrderedDict()
    for path_batch in paths:
        logging.info(f"Searching METS files in {path_batch}")
        for path in path_batch.rglob("*_mets.xml"):
            object_id = path.stem.replace("_mets", "")
            mets[object_id] = path
            logging.debug(f"Found METS file for object_id={object_id}: {path}")
    logging.info(f"Found {len(mets)} METS files")
    return mets


def get_templates(path_templates: Path) -> Dict[str, Path]:
    """Return dictionary of object_id to METS template file path."""
    templates = collections.OrderedDict()
    logging.info(f"Searching templates in {path_templates}")
    for path in path_templates.rglob("*_mets_template.xml"):
        object_id = path.stem.replace("_mets_template", "")
        templates[object_id] = path
        logging.debug(f"Found template file for object_id={object_id}: {path}")
    logging.info(f"Found {len(templates)} template files")
    return templates
