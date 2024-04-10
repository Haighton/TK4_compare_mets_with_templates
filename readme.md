# TK4_compare_mets_with_templates

This script checks if the data we send to the digitisation company - which has
the form of a partly created METS XML file (METS-template) - has been
altered where it shouldn't have been e.g. dmdSec[1] and sourceMD should not be
changed. It will also check if all the object ID's between the supplied METS
and the templates are equal.

## Usage

Script expects atleast 2 arguments which should be the location of the
METS-templates and the location of 1 or more batches:

```
python TK4_compare_mets_with_templates_2_0_0.py "/dir/templates" "/dir/batch_1" ... "/dir/batch_N"

e.g.

python TK4_compare_mets_with_templates_2_0_0.py
       "M:\BKT-traject\Digitalisering\BKT2_kranten7\Metadatadump\Zending_09\
       MMRHCE02_000000001_v2\METS-templates_MMRHCE02_000000001_v2"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_1_01"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_2_01"
       "\\gwo-srv-p500\GWO-P500-16\MMRHCE02_000000001_3_01"
```

## Output

A text (markdown) file with all found discrepancies in `OUTPUT_LOC` :
`[OUTPUT_LOC]/compare_mets_with_templates-[batch_id]-[date].txt`


_Originally created by THA010 for KB BKT2 metadata checks._