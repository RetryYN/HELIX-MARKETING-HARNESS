"""semantic_refs ゲートの単体テストと mutation test。"""

from tools.gates import semantic_refs
from tools.gates.common import CTX


def _canon() -> dict:
    return semantic_refs.load_canon(CTX)


def test_all_structured_refs_resolve() -> None:
    items = CTX.frc + CTX.src + CTX.acc + CTX.tcc + CTX.cmpc + CTX.duc
    assert semantic_refs.detect_semantic_ref_faults(items, _canon()) == []


def test_mutation_unknown_table_ref_is_detected() -> None:
    victim = {**CTX.frc[0]}
    victim["semantic_refs"] = {**victim["semantic_refs"],
                               "table_refs": [*victim["semantic_refs"]["table_refs"], "ghost_table"]}
    faults = semantic_refs.detect_semantic_ref_faults([victim], _canon())
    assert any("table ghost_table" in f for f in faults)


def test_mutation_unknown_column_ref_is_detected() -> None:
    victim = {**CTX.frc[0]}
    victim["semantic_refs"] = {**victim["semantic_refs"],
                               "column_refs": ["loop_runs.ghost_column"]}
    faults = semantic_refs.detect_semantic_ref_faults([victim], _canon())
    assert any("column loop_runs.ghost_column" in f for f in faults)


def test_mutation_missing_semantic_refs_block_is_detected() -> None:
    victim = {k: v for k, v in CTX.frc[0].items() if k != "semantic_refs"}
    faults = semantic_refs.detect_semantic_ref_faults([victim], _canon())
    assert any("semantic_refs なし" in f for f in faults)


def test_state_evidence_consistency_holds() -> None:
    assert semantic_refs.detect_state_evidence_faults(CTX.acc, CTX.tcc, CTX.allc) == []


def test_mutation_operation_log_for_internal_transition_is_detected() -> None:
    victim = {**CTX.acc[0], "target": "FR-01",
              "expected_evidence": "operation_log に遷移拒否を記録",
              "semantic_refs": {**CTX.acc[0]["semantic_refs"], "table_refs": ["loop_runs"]}}
    assert semantic_refs.detect_state_evidence_faults([victim], [])


def test_mutation_contract_evidence_channel_and_db_contradiction_are_detected() -> None:
    contract = {
        "id": "FR-11",
        "rejection_behavior": "DB を変更せず state_transitions に rejected 行を記録する",
        "side_effects": [],
        "evidence": ["operation_log 行"],
        "tables": ["w: state_transitions"],
        "semantic_refs": {"table_refs": ["state_transitions"]},
    }
    faults = semantic_refs.detect_state_evidence_faults([], [], [contract])
    assert any("operation_log" in f for f in faults)
    assert any("DB変更なし" in f for f in faults)
