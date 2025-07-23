import collections
from pathlib import Path
import logging
from typing import Dict, Set, Tuple
from lxml import etree
from xmldiff import main
from tqdm import tqdm
from typing import Dict, List, Tuple

def compare_files(mets: dict[str, Path], templates: dict[str, Path]) -> Dict[str, List[List[str]]]:
    """Compare key METS sections between each METS and its template."""
    errors = collections.OrderedDict()
    common_ids = sorted(set(mets.keys()).intersection(templates.keys()))
    parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True)
    diff_options = {'F': 0.5, 'ratio_mode': 'fast'}
    ns = {
        "mets": "http://www.loc.gov/METS/",
        "mods": "http://www.loc.gov/mods/v3",
        "premis": "info:lc/xmlns/premis-v2",
        "kbmd": "http://schemas.kb.nl/kbmd/v1",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xlink": "http://www.w3.org/1999/xlink",
        "mix": "http://www.loc.gov/mix/v20",
        "pica": "info:srw/schema/5/picaXML-v1.0",
        "marc": "http://www.loc.gov/MARC21/slim"
    }

    for common_id in tqdm(common_ids):
        error_data = []

        try:
            mets_tree = etree.parse(str(mets[common_id]), parser)
        except (etree.XMLSyntaxError, OSError) as e:
            logging.error("Failed to parse METS file %s: %s", mets[common_id], e)
            continue

        try:
            template_tree = etree.parse(str(templates[common_id]), parser)
        except (etree.XMLSyntaxError, OSError) as e:
            logging.error("Failed to parse template file %s: %s", templates[common_id], e)
            continue

        def diff_xpath(xpath: str) -> list:
            try:
                return main.diff_texts(
                    etree.tostring(template_tree.xpath(xpath, namespaces=ns)[0]),
                    etree.tostring(mets_tree.xpath(xpath, namespaces=ns)[0]),
                    diff_options=diff_options
                )
            except IndexError:
                logging.warning("XPath %s not found in one of the documents for ID %s", xpath, common_id)
                return []

        for label, xpath in [
            ("mets:dmdSec errors:", '//mets:dmdSec[@ID="DMD1"]'),
            ("mets:techMD errors:", '//mets:techMD[@ID="TMD00001"]'),
            ("mets:rightsMD errors:", '//mets:rightsMD[@ADMID="TMD00001"]'),
            ("kbmd:catalogRecord errors:", '//kbmd:catalogRecord'),
            ("mets:sourceMD[2] errors:", '//mets:sourceMD[@ID="SMD2"]'),
            ("mets:digiprovMD errors:", '//mets:digiprovMD')
        ]:
            diffs = diff_xpath(xpath)
            if label.startswith("kbmd"):
                diffs = [d for d in diffs if not (str(d).startswith("UpdateTextIn") and str(d).endswith("text=None)"))]
            if label.startswith("mets:digiprovMD"):
                diffs = [d for d in diffs if not str(d).startswith("UpdateTextIn(node='/mets:digiprovMD/mets:mdWrap/mets:xmlData/premis:event/premis:eventDateTime")]
            if diffs:
                error_data.append([label] + diffs)

        if error_data:
            batch_name = mets[common_id].parents[2].name
            err_key = f"{common_id} - {batch_name}"
            errors[err_key] = error_data

    logging.info("Completed comparison for %d common object IDs", len(common_ids))
    return errors


def different_ids(mets: Dict[str, Path], templates: Dict[str, Path]) -> Tuple[Set[str], Set[str]]:
    """Find differences in object ID's between METS and templates.

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
        print(f"\nThere are {len(mets_diff_ids)} unique object id's in METS:")
        for ids in sorted(mets_diff_ids):
            print(f"- {ids}")

    templates_diff_ids = set(templates.keys()) - set(mets.keys())
    if templates_diff_ids:
        print(f"\nThere are {len(templates_diff_ids)} unique object id's in templates:")
        for ids in sorted(templates_diff_ids):
            print(f"- {ids}")

    return mets_diff_ids, templates_diff_ids

