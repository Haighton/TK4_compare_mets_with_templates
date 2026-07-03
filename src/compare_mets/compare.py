import collections
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from lxml import etree
from xmldiff import main
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing


def compare_one(common_id: str, mets_path: Path, template_path: Path, diff_options: dict, ns: dict):
    """Compare a single METS/template pair and return errors."""
    parser = etree.XMLParser(encoding="utf-8", remove_blank_text=True)
    error_data = []

    try:
        mets_tree = etree.parse(str(mets_path), parser)
    except (etree.XMLSyntaxError, OSError) as e:
        logging.error(f"Failed to parse METS file {mets_path}: {e}")
        return None

    try:
        template_tree = etree.parse(str(template_path), parser)
    except (etree.XMLSyntaxError, OSError) as e:
        logging.error(f"Failed to parse template file {template_path}: {e}")
        return None

    def diff_xpath(xpath: str) -> list:
        template_nodes = template_tree.xpath(xpath, namespaces=ns)
        mets_nodes = mets_tree.xpath(xpath, namespaces=ns)
        if not template_nodes and not mets_nodes:
            logging.warning(f"XPath {xpath} not found for ID {common_id}")
            return []

        diffs = []
        template_by_id = collections.OrderedDict((n.get("ID"), n) for n in template_nodes)
        mets_by_id = collections.OrderedDict((n.get("ID"), n) for n in mets_nodes)

        if (None not in template_by_id and None not in mets_by_id
                and len(template_by_id) == len(template_nodes)
                and len(mets_by_id) == len(mets_nodes)):
            # Alle nodes hebben een uniek ID-attribuut: match secties op ID,
            # zodat volgordeverschillen geen valse diffs geven.
            for sec_id in template_by_id:
                if sec_id not in mets_by_id:
                    diffs.append(f"Section {sec_id} missing in METS (present in template)")
            for sec_id in mets_by_id:
                if sec_id not in template_by_id:
                    diffs.append(f"Section {sec_id} not in template (present in METS)")
            pairs = [(template_by_id[i], mets_by_id[i]) for i in template_by_id if i in mets_by_id]
        else:
            if len(template_nodes) != len(mets_nodes):
                diffs.append(
                    f"Section count mismatch: template={len(template_nodes)}, METS={len(mets_nodes)}")
            pairs = list(zip(template_nodes, mets_nodes))

        for template_node, mets_node in pairs:
            diffs.extend(main.diff_texts(
                etree.tostring(template_node),
                etree.tostring(mets_node),
                diff_options=diff_options,
            ))
        return diffs

    for label, xpath in [
        ("mets:dmdSec errors:", '//mets:dmdSec[@ID="DMD1"]'),
        ("mets:techMD errors:", '//mets:techMD[@ID="TMD00001"]'),
        ("mets:rightsMD errors:", '//mets:rightsMD[@ADMID="TMD00001"]'),
        ("kbmd:catalogRecord errors:", "//kbmd:catalogRecord"),
        ("mets:sourceMD[2] errors:", '//mets:sourceMD[@ID="SMD2"]'),
        ("mets:digiprovMD errors:", "//mets:digiprovMD"),
    ]:
        diffs = diff_xpath(xpath)
        # Toegestane afwijking: lege elementen mogen als self-closing tag
        # geleverd worden (komt vooral voor in sourceMD/kbmd:catalogRecord).
        diffs = [d for d in diffs if not (str(d).startswith(
            "UpdateTextIn") and str(d).endswith("text=None)"))]
        # Toegestane afwijking: premis:eventDateTime mag door de leverancier
        # aangepast worden.
        if label.startswith("mets:digiprovMD"):
            diffs = [d for d in diffs if not str(d).startswith(
                "UpdateTextIn(node='/mets:digiprovMD/mets:mdWrap/mets:xmlData/premis:event/premis:eventDateTime"
            )]
        if diffs:
            error_data.append([label] + diffs)

    if error_data:
        batch_name = mets_path.parents[2].name
        err_key = f"{common_id} - {batch_name}"
        return err_key, error_data
    return None


def compare_files(
    mets: Dict[str, Path],
    templates: Dict[str, Path],
    diff_threshold: float = 0.5,
    diff_ratio_mode: str = "fast",
    max_workers: int = None,
) -> Dict[str, List[List[str]]]:
    """Compare METS files with templates in parallel using a process pool."""
    errors = collections.OrderedDict()
    common_ids = sorted(set(mets.keys()).intersection(templates.keys()))
    diff_options = {"F": diff_threshold, "ratio_mode": diff_ratio_mode}

    ns = {
        "mets": "http://www.loc.gov/METS/",
        "mods": "http://www.loc.gov/mods/v3",
        "premis": "info:lc/xmlns/premis-v2",
        "kbmd": "http://schemas.kb.nl/kbmd/v1",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xlink": "http://www.w3.org/1999/xlink",
        "mix": "http://www.loc.gov/mix/v20",
        "pica": "info:srw/schema/5/picaXML-v1.0",
        "marc": "http://www.loc.gov/MARC21/slim",
    }

    logging.info(f"Starting parallel comparison with {len(common_ids)} files...")

    with ProcessPoolExecutor(max_workers=max_workers or (multiprocessing.cpu_count() - 1)) as executor:
        futures = {
            executor.submit(compare_one, cid, mets[cid], templates[cid], diff_options, ns): cid
            for cid in common_ids
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Comparing METS files", unit="file"):
            result = future.result()
            if result:
                err_key, error_data = result
                errors[err_key] = error_data

    logging.info(f"Completed comparison for {len(common_ids)} common object IDs")
    return errors


def different_ids(mets: Dict[str, Path], templates: Dict[str, Path]) -> Tuple[Set[str], Set[str]]:
    """Find differences in object IDs between METS and templates.

    Args:
        mets: Object IDs mapped to METS file paths.
        templates: Object IDs mapped to METS template file paths.

    Returns:
        Tuple of:
            - IDs found in METS but not in templates.
            - IDs found in templates but not in METS.
    """
    mets_diff_ids = set(mets.keys()) - set(templates.keys())
    if mets_diff_ids:
        logging.info(f"There are {len(mets_diff_ids)} unique object IDs in METS:")
        for oid in sorted(mets_diff_ids):
            logging.debug(f"  METS-only: {oid}")

    templates_diff_ids = set(templates.keys()) - set(mets.keys())
    if templates_diff_ids:
        logging.info(f"There are {len(templates_diff_ids)} unique object IDs in templates:")
        for oid in sorted(templates_diff_ids):
            logging.debug(f"  Template-only: {oid}")

    return mets_diff_ids, templates_diff_ids
