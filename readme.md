# compare_mets

`compare_mets` is a command-line tool developed by the KB (National Library of the Netherlands) to validate delivered METS XML files against METS-templates previously sent to digitisation partners. It verifies that the source metadata in the templates is returned unchanged in the delivered METS, and that every template sent actually came back in the delivery.

Originally created for the BKT2 newspaper digitisation project, it is suitable for BKT2, BKT3, and TK4 projects.

---

## What It Does

- Compares key METS sections between template and delivered METS:
  - `dmdSec[@ID="DMD1"]`
  - `techMD[@ID="TMD00001"]`
  - `rightsMD[@ADMID="TMD00001"]`
  - `kbmd:catalogRecord`
  - `sourceMD[@ID="SMD2"]`
  - all `digiprovMD` sections (matched on their `ID` attribute; extra or missing sections are reported)
- Uses a strict tree comparison: every difference in element structure, attributes, or text is reported with a readable path and both values. Allowed deviations:
  - `premis:eventDateTime` may be changed by the supplier
  - empty elements may be delivered as self-closing tags (handled implicitly by comparing parsed trees; a field that had content in the template and comes back empty **is** reported)
  - attribute order and namespace prefixes are irrelevant
- Checks delivery completeness: object IDs present in the templates but missing from the delivery (and vice versa)
- Reports files that could not be parsed as findings (they show up in the report, not only in the log)
- Outputs a Markdown report and a machine-readable JSON file per run
- Logs activity to both the console and a rotating log file (`logs/compare_mets.log`), including messages from worker processes

---

## Installation

Clone the repository and install with pip (requires Python 3.11+):

```bash
pip install .
```

---

## Usage

```bash
tk4-compare /path/to/templates /path/to/batch_1 /path/to/batch_2 --output ./results
```

(`compare-mets` is available as an alias for `tk4-compare`.)

### Example:

```bash
tk4-compare \
  "M:/BKT2/Zending_09/METS-templates_MMRHCE02_000000001_v2" \
  "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_1_01" \
  "//gwo-srv-p500/GWO-P500-16/MMRHCE02_000000001_2_01" \
  --output "./results"
```

---

## CLI Arguments

| Argument              | Type      | Required | Description                                                                 |
|-----------------------|-----------|----------|-----------------------------------------------------------------------------|
| `templates`           | Path      | Yes      | Path to the METS templates directory.                                       |
| `batches`             | Path(s)   | Yes      | One or more batch directories with delivered METS files.                    |
| `-o`, `--output`      | Path      | No       | Directory to save output reports (default: `./output`).                     |
| `-c`, `--config`      | Path      | No       | TOML file overriding the compared sections / allowed deviations.            |
| `-v`, `--verbose`     | flag      | No       | Enable verbose logging (DEBUG level).                                       |
| `--quiet`             | flag      | No       | Suppress info messages, only show errors (ERROR level).                     |
| `--version`           | flag      | No       | Print program version and exit.                                             |

### Exit codes

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| 0    | No discrepancies found                                         |
| 1    | Findings and/or delivery completeness issues (see the report)  |
| 2    | Usage error (invalid paths, no METS/templates found)           |

This makes the tool usable in batch scripts and pipelines without parsing the report.

The number of worker processes is chosen automatically: half the CPU cores (capped at the Windows process-pool limit and the number of files), so another parallel tool can run alongside without starving the machine.

---

## Project configuration

The compared sections and allowed deviations default to the KB newspaper projects. For a project with different sections, pass a TOML file via `--config`:

```toml
ignore_text = ["premis:eventDateTime"]

[[sections]]
label = "mets:dmdSec"
xpath = '//mets:dmdSec[@ID="DMD1"]'

[[sections]]
label = "mets:digiprovMD"
xpath = "//mets:digiprovMD"
```

Omitted keys keep their default values. See `config.example.toml` for a fully annotated example. Project configs can be kept in the (git-ignored) `configs/` directory.

---

## Output

The tool generates three files in the `--output` directory per run:

```
compare_report-[batch_id]-[YYYYMMDD_hhmmss].html
compare_report-[batch_id]-[YYYYMMDD_hhmmss].md
compare_report-[batch_id]-[YYYYMMDD_hhmmss].json
```

The **HTML report** is the most convenient to review: identical changes are bundled into one collapsible row with a count of affected objects (`3412 / 3412 objects` is highlighted, so a systematic supplier-wide change is visible at a glance), each row expands to the template/METS values and the affected object IDs, and a per-object view is included. It is fully self-contained (no JavaScript, no external resources), so it can be opened straight from a network share or attached to an e-mail.

The **Markdown report** contains a summary and findings per object ID (readable, e.g. ``mets:digiprovMD[DPMD2]/…/premis:agentName — text changed: template 'X' → METS 'Y'``). The **JSON file** contains the same data plus the bundled view in machine-readable form, for aggregating results across deliveries.

---

## Development

Run the test suite with:

```bash
pip install -e ".[dev]"
pytest
```

---

## Author

Created by Thomas Haighton for the Koninklijke Bibliotheek (KB).
