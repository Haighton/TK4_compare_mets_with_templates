# tk4-compare

`tk4-compare` is a command-line tool developed by the KB (National Library of the Netherlands) to validate delivered METS XML files against METS templates previously sent to digitisation partners. It helps ensure that critical metadata sections remain unaltered and that object IDs are consistent between batches and templates.

Originally created for the BKT2 newspaper digitisation project, it is suitable for BKT2, BKT3, and TK4 projects.

---

## What It Does

- Compares key METS sections:
  - `dmdSec[1]`
  - `techMD`
  - `rightsMD`
  - `sourceMD`
  - `digiprovMD`
- Filters known, irrelevant diffs (e.g. self-closing tags in `kbmd:catalogRecord`)
- Checks for mismatched object IDs between templates and actual METS files
- Outputs a Markdown report listing discrepancies per batch/object ID

---

## Installation

Clone the repository and install with pip:

```bash
pip install .
```

---

## Usage

```bash
tk4-compare /path/to/templates /path/to/batch_1 /path/to/batch_2 ... --output-dir /path/to/output
```

### Example:

```bash
tk4-compare \
  "M:/BKT2/Zending_09/MMRHCE02_000000001_v2/METS-templates_MMRHCE02_000000001_v2" \
  "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_1_01" \
  "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_2_01" \
  --output-dir "./results"
```

---

## Output

The tool generates a `.md` file in the specified `--output-dir`, named:

```
compare_report-[batch_id]-[YYYYMMDD_hhmmss].md
```

The report includes:

- Differences in key METS sections
- A section listing IDs that are missing in either templates or METS

---

## Author

Created by Thomas Haighton for the Koninklijke Bibliotheek (KB).
