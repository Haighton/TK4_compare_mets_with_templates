# compare_mets

`compare_mets` is a command-line tool developed by the KB (National Library of the Netherlands) to validate delivered METS XML files against METS-templates previously sent to digitisation partners. It helps ensure that critical metadata sections remain unaltered and that object IDs are consistent between batches and templates.

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
- Logs activity to both the console and a rotating log file (`logs/compare_mets.log`)

---

## Installation

Clone the repository and install with pip:

```bash
pip install .
```

---

## Usage

You can provide **positional arguments** (templates path first, then batches) **or flags** (`--templates` and `--batches`). Both styles are supported.

```bash
compare_mets /path/to/templates /path/to/batch_1 /path/to/batch_2 ... --output /path/to/output
```

or equivalently:

```bash
compare_mets --templates /path/to/templates --batches /path/to/batch_1 /path/to/batch_2 --output /path/to/output
```

### Example:

```bash
compare_mets   "M:/BKT2/Zending_09/MMRHCE02_000000001_v2/METS-templates_MMRHCE02_000000001_v2"   "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_1_01"   "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_2_01"   --output "./results"   --diff-threshold 0.3   --diff-ratio-mode accurate
```

---

## CLI Arguments

| Argument              | Type      | Required | Description                                                                 |
|-----------------------|-----------|----------|-----------------------------------------------------------------------------|
| `templates`           | Path      | Yes\*   | Positional: path to the METS templates directory.                           |
| `batches`             | Path(s)   | Yes\*   | Positional: one or more batch directories.                                  |
| `--templates`         | Path      | Yes\*   | Flag alternative to the `templates` positional argument.                    |
| `--batches`           | Path(s)   | Yes\*   | Flag alternative to the `batches` positional argument.                      |
| `-o`, `--output`      | Path      | No       | Directory to save output reports. Defaults to current working directory `./output`.    |
| `-v`, `--verbose`     | flag      | No       | Enable verbose logging (DEBUG level).                                       |
| `--quiet`             | flag      | No       | Suppress info messages, only show errors (ERROR level).                     |
| `--diff-threshold`    | float     | No       | Similarity threshold for xmldiff (default: 0.5). Lower = more sensitive.    |
| `--diff-ratio-mode`   | fast/accurate | No   | Ratio mode for xmldiff (default: fast). 'fast' = quick, 'accurate' = precise|
| `--version`           | flag      | No       | Print program version and exit.                                             |

\* You must provide either the positional arguments (`templates batches...`) **or** the flags (`--templates ... --batches ...`).  

---

## Output

The tool generates a Markdown report in the specified `--output` directory, named:

```
compare_report-[batch_id]-[YYYYMMDD_hhmmss].md
```

Each report includes:

- **Summary section**: number of files with discrepancies, total difference blocks, and ID mismatches.
- **Detailed discrepancies** per METS file/object ID.
- **ID discrepancies**: listing object IDs missing in templates or METS.

Logs are written to both the console and to `logs/compare_mets.log` (rotating file, max ~5MB, keeping 5 backups).

---

## Author

Created by Thomas Haighton for the Koninklijke Bibliotheek (KB).
