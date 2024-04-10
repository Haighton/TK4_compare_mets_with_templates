#!usr/bin/env python3

r"""Compare delivered METS XML files with our (KB) generated METS-templates.

# TK4_compare_mets_with_templates

This script checks if the data we send to the digitisation company - which has
the form of a partly created METS XML file (METS-template) - has been
altered where it shouldn't have been e.g. dmdSec[1] and sourceMD should not be
changed. It will also check if all the object ID's between the supplied METS
and the templates are equal.

## Usage

Script expects atleast 2 arguments which should be the location of the
METS-templates and the location of 1 or more batches:

``
python TK4_compare_mets_with_templates_2_0_0.py "/dir/templates" "/dir/batch_1" ... "/dir/batch_N"

e.g.

python TK4_compare_mets_with_templates_2_0_0.py
       "M:\BKT-traject\Digitalisering\BKT2_kranten7\Metadatadump\Zending_09\
       MMRHCE02_000000001_v2\METS-templates_MMRHCE02_000000001_v2"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_1_01"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_2_01"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_3_01"
``

## Output

A text (markdown) file with all found discrepancies in `OUTPUT_LOC` :
`[OUTPUT_LOC]/compare_mets_with_templates-[batch_id]-[date].txt`

## Modifications

Version| Mod.Date   | Mod.by | Modifications
---    | ---        | ---    | ---
v1.0.0 | 2017-01-01 | THA010 | - Initial prototype script. 
v1.0.2 | 2020-07-20 | THA010 | - Update stable version.
v2.0.0 | 2024-04-10 | THA010 | - Went over everything, cleaned-up and tested
                                 code from v1, autopep8, tbv upcoming TK4 tender.

_Originally created by THA010 for KB BKT2 metadata checks._
"""

import sys
import os
from datetime import datetime
import collections

from lxml import etree
from xmldiff import main
from tqdm import tqdm

# Location of output text file.
OUTPUT_LOC = 'C:/Users/DDD020/OneDrive - KB nationale bibliotheek/Desktop'
# OUTPUT_LOC = '/Users/haighton/Development/KB/TK4_mets_templates_controle/Output'


def get_mets(paths):
    """Get paths to all METS files.

    In contrary to METS-templates, METS files can be found in multiple
    locations. This because of the size limit (500 Gb) of a batch. So this
    function expects 1 or more paths to batch.

    Arguments:
        paths (list): Paths to batch(es).

    Returns:
        mets (ordered dict): {object_id (str): path to METS (str)}
    """
    mets = collections.OrderedDict()
    count = 0
    for path_batch in paths:
        count += 1
        print(f'\nLooking for METS in {os.path.basename(path_batch)} ({count}/{len(paths)}):')
        for dirpath, dirnames, filenames in os.walk(path_batch):
            for filename in filenames:
                if filename.endswith('_mets.xml'):
                    object_id = os.path.basename(
                        filename).replace('_mets.xml', '')
                    mets[object_id] = os.path.join(dirpath, filename)
                    print(filename, end='\r', flush=True)
    print(f'\nFound {len(mets)} METS files.')
    return mets


def get_templates(path_templates):
    """Get METS-template files.

    Arguments:
        path_templates (str): Path to METS-templates.

    Returns:
        templates (ordered dict): {object_id (str): path to METS-template (str)}
    """
    print(f'\nLooking for templates in {os.path.basename(path_templates)}.')
    templates = collections.OrderedDict()
    for dirpath, dirnames, filenames in os.walk(path_templates):
        for filename in filenames:
            if filename.endswith('_mets_template.xml'):
                object_id = os.path.basename(
                    filename).replace('_mets_template.xml', '')
                templates[object_id] = os.path.join(dirpath, filename)
                print(filename, end='\r', flush=True)
    print(f'\nFound {len(templates)} template files.\n')
    return templates


def compare_files(mets, templates):
    """Compare data between METS and templates.

    diff_options:

    - `F`: A value between 0 and 1 that determines how similar two XML nodes
           must be to match as the same in both trees.   (Default: 0.5)
    - `ratio_mode`: ['accurate', 'fast', 'faster']. (Default: fast)

    Arguments:
        mets (ordered dict):      Object id's with paths to METS files.
        templates (ordered dict): Object id's with paths to template file.

    Returns:
        Ordered dict: Errors {object_id (str): [xmldiff output (list of lists)]}
    """
    errors = collections.OrderedDict()
    common_ids = list(set(mets.keys()).intersection(templates.keys()))
    common_ids = sorted(common_ids)

    parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True)
    diff_options = {'F': 0.5, 'ratio_mode': 'fast'}
    ns = {"mets": "http://www.loc.gov/METS/",
          "mods": "http://www.loc.gov/mods/v3",
          "premis": "info:lc/xmlns/premis-v2",
          "kbmd": "http://schemas.kb.nl/kbmd/v1",
          "xsi": "http://www.w3.org/2001/XMLSchema-instance",
          "xlink": "http://www.w3.org/1999/xlink",
          "mix": "http://www.loc.gov/mix/v20",
          "pica": "info:srw/schema/5/picaXML-v1.0",
          "marc": "http://www.loc.gov/MARC21/slim"}

    for common_id in tqdm(common_ids):
        error_data = []

        # Parse METS and template XML files.
        mets_tree = etree.parse(mets[common_id], parser)
        template_tree = etree.parse(templates[common_id], parser)

        dmdsec_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//mets:dmdSec[@ID="DMD1"]', namespaces=ns)[0]),
                                      right=etree.tostring(mets_tree.xpath(
                                          '//mets:dmdSec[@ID="DMD1"]', namespaces=ns)[0]),
                                      diff_options=diff_options)
        if dmdsec_diff:
            error_data.append(['mets:dmdSec errors:'] + dmdsec_diff)

        techmd_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//mets:techMD[@ID="TMD00001"]', namespaces=ns)[0]),
                                      right=etree.tostring(mets_tree.xpath(
                                          '//mets:techMD[@ID="TMD00001"]', namespaces=ns)[0]),
                                      diff_options=diff_options)
        if techmd_diff:
            error_data.append(['mets:techMD errors'] + techmd_diff)

        rightsmd_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//mets:rightsMD[@ADMID="TMD00001"]', namespaces=ns)[0]),
                                        right=etree.tostring(mets_tree.xpath(
                                            '//mets:rightsMD[@ADMID="TMD00001"]', namespaces=ns)[0]),
                                        diff_options=diff_options)
        if rightsmd_diff:
            error_data.append(['mets:rightsMD errors:'] + rightsmd_diff)

        # Using the .xpath function automatically adds all the namespaces from
        # the loaded XML to the root of the output. We also need pica and marc
        # namespaces, we get these by using kbdm:catalogRecord as our root,
        # rather than mets:sourceMD[@ID="SMD1"].
        #
        # testns = mets_tree.xpath('//kbmd:catalogRecord', namespaces=ns)[0]
        # testns = mets_tree.xpath('//mets:sourceMD[@ID="SMD1"]', namespaces=ns)[0]
        # print(testns.nsmap)

        sourcemd_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//kbmd:catalogRecord', namespaces=ns)[0]),
                                        right=etree.tostring(mets_tree.xpath(
                                            '//kbmd:catalogRecord', namespaces=ns)[0]),
                                        diff_options=diff_options)
        if sourcemd_diff:
            error_data.append(['kbmd:catalogRecord errors:'] + sourcemd_diff)

        # Comapare //mets:amdSec/mets:sourceMD/[@ID="SMD2"]
        sourcemd2_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//mets:sourceMD[@ID="SMD2"]', namespaces=ns)[0]),
                                         right=etree.tostring(mets_tree.xpath(
                                             '//mets:sourceMD[@ID="SMD2"]', namespaces=ns)[0]),
                                         diff_options=diff_options)
        if sourcemd2_diff:
            error_data.append(['mets:sourceMD[2] errors:'] + sourcemd2_diff)

        # Compare //mets:amdSec/mets:digiprovMD
        digiprovmd_diff = main.diff_texts(left=etree.tostring(template_tree.xpath('//mets:digiprovMD', namespaces=ns)[0]),
                                          right=etree.tostring(mets_tree.xpath(
                                              '//mets:digiprovMD', namespaces=ns)[0]),
                                          diff_options=diff_options)

        if digiprovmd_diff:
            # Ignore premis:eventDateTime difference.
            rm_entry = 0
            for i in range(len(digiprovmd_diff)):
                if str(digiprovmd_diff[i]).startswith("UpdateTextIn(node='/mets:digiprovMD/mets:mdWrap/mets:xmlData/premis:event/premis:eventDateTime[1]'"):
                    rm_entry = i
            del digiprovmd_diff[rm_entry]

            if digiprovmd_diff:
                error_data.append(
                    ['mets:digiprovMD errors:'] + digiprovmd_diff)

        # Batch ID
        batch_name = os.path.basename(os.path.dirname(os.path.dirname(
                                      os.path.dirname(mets[common_id]))))
        err_key = common_id + ' - ' + batch_name

        if error_data:
            errors[err_key] = error_data

    return errors


def different_ids(mets, templates):
    """Find differences in object ID's between METS and templates.

    Arguments:
        mets (ordered dict):      Object id's with paths to METS files.
        templates (ordered dict): Object id's with paths to template file.

    Returns:
        mets_diff_ids (list):     ID's found in METS but not in templates.
        templates_diff_ids(list): ID's found in templates but not in METS.
    """
    mets_diff_ids = set(mets.keys()) - set(templates.keys())
    if len(mets_diff_ids) > 0:
        print(f"\nThere are {len(mets_diff_ids)} unique object id's in METS:")
        for ids in mets_diff_ids:
            print(ids)

    templates_diff_ids = set(templates.keys()) - set(mets.keys())
    if len(templates_diff_ids) > 0:
        print(f"\nThere are {len(templates_diff_ids)} unique object id's in templates:")
        for ids in templates_diff_ids:
            print(ids)

    return mets_diff_ids, templates_diff_ids


def print_errors(errors, path_templates, mets_diff_ids, templates_diff_ids):
    """Write errors to a text file.

    Arguments:
        errors (dict):             ID's with differences found by xmldiff.
        path_templates (str):      Path to templates.
        mets_diff_ids (list):      ID's of METS not found in templates.
        templates_diff_ids (list): ID's of templates not found in METS.

    Output:
        Text file with found errors at OUTPUT_LOC.
    """
    batch_name_split = os.path.basename(path_templates).split('_')
    batch_id = batch_name_split[1] + '_' + batch_name_split[2]
    dt = datetime.now()
    output_name = (f"compare_mets_with_templates-{batch_id}-{dt.strftime('%Y%m%d')}.txt")

    with open(os.path.join(OUTPUT_LOC, output_name), 'w+') as output_file:

        output_file.write(f"# Compare METS with Templates - {batch_id}\n\n")
        output_file.write(f"_log generated {dt.strftime('%Y-%m-%d %H:%M')}_\n\n")
        output_file.write('\n## Data discrepancies\n')

        # NB: errors dict values are list of lists, first val is category.
        if errors:
            for object_id, errs in errors.items():
                try:
                    output_file.write(f"\n### {object_id}\n")
                    for err in errs:
                        cnt = 0
                        output_file.write('\n')
                        for serr in err:
                            if cnt > 0:
                                output_file.write(f"- {serr}\n")
                            else:
                                output_file.write(f"#### {serr}\n\n")
                            cnt += 1
                    output_file.write('\n')
                except UnicodeEncodeError:
                    output_file.write(f"\nUnicodeEncodeError in {object_id}")
                    continue
        else:
            output_file.write('\nNo data discrepancies found.\n')

        # Write discrepancies in Object ID's.
        output_file.write('---\n\n## ID discrepancies')
        if len(mets_diff_ids) > 0:
            output_file.write(f"\n\nThere are {len(mets_diff_ids)} unique object id's in METS:\n\n")
            mets_diff_ids = sorted(mets_diff_ids)
            for ids in mets_diff_ids:
                output_file.write(f"- {ids}\n")

        if len(templates_diff_ids) > 0:
            output_file.write(f"\n\nThere are {len(templates_diff_ids)} unique object id's in templates:\n\n")
            templates_diff_ids = sorted(templates_diff_ids)
            for ids in templates_diff_ids:
                output_file.write(f"- {ids}\n")

        if len(templates_diff_ids) == 0 and len(mets_diff_ids) == 0:
            output_file.write(
                "\nSame object ID's found in METS and templates.")


if __name__ == "__main__":
    mets = get_mets(sys.argv[2:])
    templates = get_templates(sys.argv[1])
    errors = compare_files(mets, templates)
    mets_diff_ids, templates_diff_ids = different_ids(mets, templates)
    print_errors(errors, sys.argv[1], mets_diff_ids, templates_diff_ids)
