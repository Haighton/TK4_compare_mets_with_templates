"""Tests for report grouping and output files."""
from pathlib import Path

from compare_mets.findings import Finding
from compare_mets.writer import group_findings, write_reports


def make_errors():
    shared = Finding("mets:digiprovMD", "text",
                     "mets:digiprovMD[DPMD2]/premis:agentName",
                     "Karmac & Co", "Karmac en Co")
    unique = Finding("mets:dmdSec", "text", "mets:dmdSec[DMD1]/mods:title",
                     "Oude titel", "Nieuwe titel")
    return {
        "OBJ1 - batch": [shared, unique],
        "OBJ2 - batch": [shared],
        "OBJ3 - batch": [shared],
    }


def test_group_findings_bundles_identical_changes():
    groups = group_findings(make_errors())
    key = ("mets:digiprovMD", "text", "mets:digiprovMD[DPMD2]/premis:agentName")
    assert key in groups
    assert groups[key][("Karmac & Co", "Karmac en Co")] == ["OBJ1", "OBJ2", "OBJ3"]
    dmd_key = ("mets:dmdSec", "text", "mets:dmdSec[DMD1]/mods:title")
    assert groups[dmd_key][("Oude titel", "Nieuwe titel")] == ["OBJ1"]


def test_write_reports_produces_three_files(tmp_path):
    md, js, htm = write_reports(
        make_errors(), set(), {"OBJ9"}, tmp_path, [Path("batchdir")], n_compared=4)
    assert md.exists() and js.exists() and htm.exists()

    content = htm.read_text(encoding="utf-8")
    assert "3 / 4 objects" in content          # bundled change with count
    assert "OBJ1, OBJ2, OBJ3" in content       # affected IDs listed together
    assert "Karmac &amp; Co" in content        # values escaped
    assert "templates NOT returned" in content
    assert "<details>" in content


def test_html_marks_change_in_all_objects(tmp_path):
    errors = {k: v for k, v in make_errors().items()}
    _, _, htm = write_reports(errors, set(), set(), tmp_path,
                              [Path("batchdir")], n_compared=3)
    content = htm.read_text(encoding="utf-8")
    assert "count all" in content
    assert "3 / 3 objects" in content
