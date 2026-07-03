import collections
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from logging.handlers import QueueHandler
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from lxml import etree
from tqdm import tqdm

from .config import CompareConfig, default_config
from .findings import Finding
from .tree_compare import compare_trees, prefix_map, qname


def _parse(path: Path):
    parser = etree.XMLParser(remove_comments=True, remove_pis=True)
    return etree.parse(str(path), parser)


def _compare_section(label: str, xpath: str, template_tree, mets_tree,
                     config: CompareConfig, common_id: str) -> List[Finding]:
    ns = config.namespaces
    prefixes = prefix_map(config)
    template_nodes = template_tree.xpath(xpath, namespaces=ns)
    mets_nodes = mets_tree.xpath(xpath, namespaces=ns)
    if not template_nodes and not mets_nodes:
        logging.warning(f"XPath {xpath} not found for ID {common_id}")
        return []

    findings: List[Finding] = []
    pairs = []
    template_by_id = collections.OrderedDict((n.get("ID"), n) for n in template_nodes)
    mets_by_id = collections.OrderedDict((n.get("ID"), n) for n in mets_nodes)

    if (None not in template_by_id and None not in mets_by_id
            and len(template_by_id) == len(template_nodes)
            and len(mets_by_id) == len(mets_nodes)):
        # All nodes carry a unique ID attribute: match sections on ID, so
        # extra, missing or reordered sections are handled explicitly.
        for sec_id, node in template_by_id.items():
            if sec_id in mets_by_id:
                pairs.append((node, mets_by_id[sec_id]))
            else:
                findings.append(Finding(label, "missing-section",
                                        f"{qname(node.tag, prefixes)}[{sec_id}]"))
        for sec_id, node in mets_by_id.items():
            if sec_id not in template_by_id:
                findings.append(Finding(label, "extra-section",
                                        f"{qname(node.tag, prefixes)}[{sec_id}]"))
    else:
        if len(template_nodes) != len(mets_nodes):
            findings.append(Finding(label, "section-count", label,
                                    str(len(template_nodes)), str(len(mets_nodes))))
        pairs = list(zip(template_nodes, mets_nodes))

    for template_node, mets_node in pairs:
        root_path = qname(template_node.tag, prefixes)
        if template_node.get("ID"):
            root_path += f"[{template_node.get('ID')}]"
        findings.extend(compare_trees(template_node, mets_node, label, config, root_path))
    return findings


def compare_one(common_id: str, mets_path: Path, template_path: Path,
                config: CompareConfig) -> Optional[Tuple[str, List[Finding]]]:
    """Compare a single METS/template pair and return (report key, findings)."""
    findings: List[Finding] = []

    mets_tree = template_tree = None
    try:
        mets_tree = _parse(mets_path)
    except (etree.XMLSyntaxError, OSError) as e:
        logging.error(f"Failed to parse METS file {mets_path}: {e}")
        findings.append(Finding("(file)", "parse-error", mets_path.name, None, str(e)))
    try:
        template_tree = _parse(template_path)
    except (etree.XMLSyntaxError, OSError) as e:
        logging.error(f"Failed to parse template file {template_path}: {e}")
        findings.append(Finding("(file)", "parse-error", template_path.name, None, str(e)))

    if mets_tree is not None and template_tree is not None:
        for label, xpath in config.sections:
            findings.extend(_compare_section(
                label, xpath, template_tree, mets_tree, config, common_id))

    if findings:
        parents = mets_path.parents
        batch_name = parents[2].name if len(parents) > 2 else parents[0].name
        return f"{common_id} - {batch_name}", findings
    return None


def _init_worker(log_queue, level: int) -> None:
    """Route worker-process logging into the main process via the queue."""
    root = logging.getLogger()
    root.handlers = [QueueHandler(log_queue)]
    root.setLevel(level)


def _auto_workers(n_tasks: int) -> int:
    """Pick a worker count that leaves room for other processes.

    Uses half the cores, so a second tool with auto workers can run
    alongside without starving the machine. Capped at 61 (the Windows
    wait-handle limit for ProcessPoolExecutor) and at the number of tasks.
    """
    cores = multiprocessing.cpu_count() or 2
    return max(1, min(cores // 2, 61, n_tasks))


def compare_files(
    mets: Dict[str, Path],
    templates: Dict[str, Path],
    config: Optional[CompareConfig] = None,
    max_workers: Optional[int] = None,
    log_queue=None,
) -> Dict[str, List[Finding]]:
    """Compare METS files with templates in parallel using a process pool."""
    config = config or default_config()
    errors: Dict[str, List[Finding]] = collections.OrderedDict()
    common_ids = sorted(set(mets.keys()).intersection(templates.keys()))

    initializer, initargs = None, ()
    if log_queue is not None:
        initializer = _init_worker
        initargs = (log_queue, logging.getLogger().getEffectiveLevel())

    workers = max_workers or _auto_workers(len(common_ids))
    logging.info(f"Starting parallel comparison with {len(common_ids)} files "
                 f"using {workers} workers...")

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=initializer,
        initargs=initargs,
    ) as executor:
        futures = {
            executor.submit(compare_one, cid, mets[cid], templates[cid], config): cid
            for cid in common_ids
        }
        for future in tqdm(as_completed(futures), total=len(futures),
                           desc="Comparing METS files", unit="file"):
            result = future.result()
            if result:
                err_key, findings = result
                errors[err_key] = findings

    logging.info(f"Completed comparison for {len(common_ids)} common object IDs")
    return errors


def different_ids(mets: Dict[str, Path], templates: Dict[str, Path]) -> Tuple[Set[str], Set[str]]:
    """Check delivery completeness on object IDs.

    Args:
        mets: Object IDs mapped to delivered METS file paths.
        templates: Object IDs mapped to METS template file paths.

    Returns:
        Tuple of:
            - IDs delivered in METS without a matching template.
            - IDs sent as template but not returned in the delivered METS.
    """
    mets_diff_ids = set(mets.keys()) - set(templates.keys())
    if mets_diff_ids:
        logging.info(f"There are {len(mets_diff_ids)} delivered METS without a template:")
        for oid in sorted(mets_diff_ids):
            logging.debug(f"  METS-only: {oid}")

    templates_diff_ids = set(templates.keys()) - set(mets.keys())
    if templates_diff_ids:
        logging.info(f"There are {len(templates_diff_ids)} templates not returned in the delivery:")
        for oid in sorted(templates_diff_ids):
            logging.debug(f"  Template-only: {oid}")

    return mets_diff_ids, templates_diff_ids
