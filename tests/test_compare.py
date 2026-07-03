"""Tests for the strict tree comparison and the pair comparison.

Fixtures are minimal METS documents with the same section IDs the KB
templates use (DMD1, TMD00001, SMD1/SMD2, DPMD1/DPMD2).
"""
from pathlib import Path

import pytest

from compare_mets.compare import compare_one, different_ids
from compare_mets.config import default_config

CONFIG = default_config()

METS_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/"
           xmlns:mods="http://www.loc.gov/mods/v3"
           xmlns:premis="info:lc/xmlns/premis-v2"
           xmlns:kbmd="http://schemas.kb.nl/kbmd/v1">
  <mets:dmdSec ID="DMD1">
    <mets:mdWrap MDTYPE="MODS"><mets:xmlData>
      <mods:mods><mods:titleInfo><mods:title>{title}</mods:title></mods:titleInfo></mods:mods>
    </mets:xmlData></mets:mdWrap>
  </mets:dmdSec>
  <mets:amdSec ID="AMD1">
    <mets:techMD ID="TMD00001">
      <mets:mdWrap MDTYPE="PREMIS:OBJECT"><mets:xmlData>
        <premis:object><premis:objectIdentifier>
          <premis:objectIdentifierType>local</premis:objectIdentifierType>
          <premis:objectIdentifierValue>OBJ1</premis:objectIdentifierValue>
        </premis:objectIdentifier></premis:object>
      </mets:xmlData></mets:mdWrap>
    </mets:techMD>
    <mets:rightsMD {rights_attrs}>
      <mets:mdWrap MDTYPE="PREMIS:RIGHTS"><mets:xmlData>
        <premis:rights><premis:rightsStatement>
          <premis:rightsBasis>{rights_basis}</premis:rightsBasis>
        </premis:rightsStatement></premis:rights>
      </mets:xmlData></mets:mdWrap>
    </mets:rightsMD>
    <mets:sourceMD ID="SMD1">
      <mets:mdWrap MDTYPE="OTHER"><mets:xmlData>
        <kbmd:catalogRecord>
          <kbmd:ppn>{ppn}</kbmd:ppn>
          {empty_field}
        </kbmd:catalogRecord>
      </mets:xmlData></mets:mdWrap>
    </mets:sourceMD>
    <mets:sourceMD ID="SMD2">
      <mets:mdWrap MDTYPE="OTHER"><mets:xmlData>
        <kbmd:metadatadump sourceProvider="KB"><kbmd:dump>x</kbmd:dump></kbmd:metadatadump>
      </mets:xmlData></mets:mdWrap>
    </mets:sourceMD>
    {digiprov1}
    {digiprov2}
  </mets:amdSec>
</mets:mets>
"""

DIGIPROV_EVENT = """<mets:digiprovMD ID="DPMD1" ADMID="TMD00001 DPMD2">
  <mets:mdWrap MDTYPE="PREMIS:EVENT"><mets:xmlData>
    <premis:event>
      <premis:eventType>creation</premis:eventType>
      <premis:eventDateTime>{datetime}</premis:eventDateTime>
      <premis:eventDetail>{detail}</premis:eventDetail>
    </premis:event>
  </mets:xmlData></mets:mdWrap>
</mets:digiprovMD>"""

DIGIPROV_AGENT = """<mets:digiprovMD ADMID="DPMD1" ID="DPMD2">
  <mets:mdWrap MDTYPE="PREMIS:AGENT"><mets:xmlData>
    <premis:agent>
      <premis:agentName>{agent}</premis:agentName>
      <premis:agentType>organization</premis:agentType>
    </premis:agent>
  </mets:xmlData></mets:mdWrap>
</mets:digiprovMD>"""

DEFAULTS = dict(
    title="De Krant",
    rights_attrs='ID="RMD1" ADMID="TMD00001"',
    rights_basis="copyright",
    ppn="123456789",
    empty_field="<kbmd:annotation></kbmd:annotation>",
    datetime="2023-05-24T14:31:19.620+02:00",
    detail="project=BKT3;",
    agent="Karmac Informatie &amp; Innovatie B.V.",
)


def build_doc(**overrides) -> str:
    values = {**DEFAULTS, **overrides}
    digiprov1 = values.pop("digiprov1", DIGIPROV_EVENT.format(
        datetime=values["datetime"], detail=values["detail"]))
    digiprov2 = values.pop("digiprov2", DIGIPROV_AGENT.format(agent=values["agent"]))
    return METS_DOC.format(**values, digiprov1=digiprov1, digiprov2=digiprov2)


def run_compare(tmp_path: Path, template_xml: str, mets_xml: str):
    template_path = tmp_path / "OBJ1_mets_template.xml"
    mets_path = tmp_path / "batch" / "sub" / "OBJ1" / "OBJ1_mets.xml"
    mets_path.parent.mkdir(parents=True)
    template_path.write_text(template_xml, encoding="utf-8")
    mets_path.write_text(mets_xml, encoding="utf-8")
    result = compare_one("OBJ1", mets_path, template_path, CONFIG)
    return result[1] if result else []


def test_identical_documents_yield_no_findings(tmp_path):
    doc = build_doc()
    assert run_compare(tmp_path, doc, doc) == []


def test_change_in_second_digiprov_is_detected(tmp_path):
    # Regression: with xmldiff only the first digiprovMD node was compared.
    findings = run_compare(
        tmp_path, build_doc(),
        build_doc(agent="Andere Leverancier B.V."))
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == "text"
    assert "DPMD2" in f.path and "agentName" in f.path
    assert f.template_value == "Karmac Informatie & Innovatie B.V."
    assert f.mets_value == "Andere Leverancier B.V."


def test_eventdatetime_change_is_allowed(tmp_path):
    findings = run_compare(
        tmp_path, build_doc(),
        build_doc(datetime="2026-01-15T09:00:00.000+01:00"))
    assert findings == []


def test_self_closing_empty_element_is_allowed(tmp_path):
    findings = run_compare(
        tmp_path,
        build_doc(empty_field="<kbmd:annotation>\n  </kbmd:annotation>"),
        build_doc(empty_field="<kbmd:annotation/>"))
    assert findings == []


def test_emptied_field_is_detected(tmp_path):
    # A field with content in the template delivered as self-closing tag is
    # a real change; the old text=None filter masked this.
    findings = run_compare(
        tmp_path,
        build_doc(empty_field="<kbmd:annotation>waarde</kbmd:annotation>"),
        build_doc(empty_field="<kbmd:annotation/>"))
    assert len(findings) == 1
    assert findings[0].kind == "text"
    assert findings[0].template_value == "waarde"
    assert findings[0].mets_value is None


def test_missing_digiprov_section_is_reported(tmp_path):
    findings = run_compare(
        tmp_path, build_doc(),
        build_doc(digiprov2=""))
    assert [f.kind for f in findings] == ["missing-section"]
    assert "DPMD2" in findings[0].path


def test_extra_digiprov_sections_are_compared(tmp_path):
    # Newer material carries four digiprov sections; all must be checked.
    extra_tpl = DIGIPROV_AGENT.format(agent="Extra Agent").replace(
        'ID="DPMD2"', 'ID="DPMD4"').replace('ADMID="DPMD1"', 'ADMID="DPMD3"')
    extra_mets = extra_tpl.replace("Extra Agent", "Gewijzigde Agent")
    tpl = build_doc(digiprov2=DIGIPROV_AGENT.format(agent=DEFAULTS["agent"]) + extra_tpl)
    mets = build_doc(digiprov2=DIGIPROV_AGENT.format(agent=DEFAULTS["agent"]) + extra_mets)
    findings = run_compare(tmp_path, tpl, mets)
    assert len(findings) == 1
    assert "DPMD4" in findings[0].path
    assert findings[0].mets_value == "Gewijzigde Agent"


def test_attribute_order_is_ignored(tmp_path):
    findings = run_compare(
        tmp_path,
        build_doc(rights_attrs='ID="RMD1" ADMID="TMD00001"'),
        build_doc(rights_attrs='ADMID="TMD00001" ID="RMD1"'))
    assert findings == []


def test_attribute_value_change_is_detected(tmp_path):
    tpl = build_doc()
    mets = build_doc().replace('sourceProvider="KB"', 'sourceProvider="Leverancier"')
    findings = run_compare(tmp_path, tpl, mets)
    assert len(findings) == 1
    assert findings[0].kind == "attribute"
    assert findings[0].path.endswith("@sourceProvider")
    assert findings[0].template_value == "KB"
    assert findings[0].mets_value == "Leverancier"


def test_removed_element_is_detected(tmp_path):
    findings = run_compare(
        tmp_path,
        build_doc(empty_field="<kbmd:annotation>x</kbmd:annotation>"),
        build_doc(empty_field=""))
    assert [f.kind for f in findings] == ["missing-element"]
    assert "annotation" in findings[0].path


def test_parse_error_is_reported_as_finding(tmp_path):
    findings = run_compare(tmp_path, build_doc(), "<mets:mets>kapot")
    assert [f.kind for f in findings] == ["parse-error"]
    assert findings[0].path == "OBJ1_mets.xml"


def test_different_ids_reports_both_directions():
    mets = {"A": Path("a"), "B": Path("b")}
    templates = {"B": Path("b"), "C": Path("c")}
    mets_only, templates_only = different_ids(mets, templates)
    assert mets_only == {"A"}
    assert templates_only == {"C"}
