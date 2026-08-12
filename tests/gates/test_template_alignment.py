"""HELIX-HARNESS 適応ゲートの単体・mutation test。"""

from copy import deepcopy

from tools.gates import template_alignment
from tools.gates.common import load


def test_alignment_contract_passes() -> None:
    data = load(template_alignment.ALIGNMENT)
    assert template_alignment.detect_alignment_faults(data) == []


def test_mutation_template_source_commit_is_rejected() -> None:
    data = deepcopy(load(template_alignment.ALIGNMENT))
    data["source"]["commit"] = "0" * 40
    faults = template_alignment.detect_alignment_faults(data)
    assert any("source" in fault or "固定" in fault for fault in faults)
