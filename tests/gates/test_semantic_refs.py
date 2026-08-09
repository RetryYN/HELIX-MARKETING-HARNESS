"""semantic_refs ゲートの単体テストと mutation test。"""

import copy

from tools.gates import semantic_refs
from tools.gates.common import CTX


def _canon() -> dict:
    return semantic_refs.load_canon(CTX)


def test_all_structured_refs_resolve() -> None:
    items = CTX.frc + CTX.src + CTX.nfc + CTX.acc + CTX.tcc + CTX.cmpc + CTX.duc
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


def test_transition_refs_are_canonical_and_nfr_ac_tcc_sets_match() -> None:
    faults = semantic_refs.detect_transition_ref_faults(
        CTX.nfc, CTX.acc, CTX.tcc, CTX.allc, CTX.transitions)
    assert faults == []


def test_mutation_task_fatal_failure_transition_is_detected() -> None:
    nfrs = copy.deepcopy(CTX.nfc)
    victim = next(item for item in nfrs if item["id"] == "NFR-4")
    victim["transition_refs"][0]["event"] = "fatal_failure"
    faults = semantic_refs.detect_transition_ref_faults(
        nfrs, CTX.acc, CTX.tcc, CTX.allc, CTX.transitions)
    assert any("NFR-4:非正準transition tasks.in_progress:fatal_failure->escalated" in f
               for f in faults)


def test_mutation_nfr_to_ac_transition_coverage_loss_is_detected() -> None:
    acs = copy.deepcopy(CTX.acc)
    victim = next(item for item in acs if item["id"] == "AC-901")
    victim["transition_refs"] = [
        ref for ref in victim["transition_refs"] if ref["entity"] != "loop_runs"
    ]
    faults = semantic_refs.detect_transition_ref_faults(
        CTX.nfc, acs, CTX.tcc, CTX.allc, CTX.transitions)
    assert any("NFR-1:NFR→AC transition被覆不一致" in f for f in faults)


def test_mutation_ac_to_tcc_transition_coverage_loss_is_detected() -> None:
    tcs = copy.deepcopy(CTX.tcc)
    victim = next(item for item in tcs if item["id"] == "TCC-NFR-06")
    victim["transition_refs"] = [
        ref for ref in victim["transition_refs"] if ref["event"] != "claim"
    ]
    faults = semantic_refs.detect_transition_ref_faults(
        CTX.nfc, CTX.acc, tcs, CTX.allc, CTX.transitions)
    assert any("AC-906:AC→TCC transition被覆不一致" in f for f in faults)


def test_mutation_fr_to_ac_transition_coverage_loss_is_detected() -> None:
    acs = copy.deepcopy(CTX.acc)
    victim = next(item for item in acs if item["id"] == "AC-47-3")
    victim["transition_refs"] = [
        ref for ref in victim["transition_refs"] if ref["event"] != "claim"
    ]
    faults = semantic_refs.detect_transition_ref_faults(
        CTX.nfc, acs, CTX.tcc, CTX.allc, CTX.transitions)
    assert any("FR-47:FR/SR→AC transition被覆不一致" in f for f in faults)


def test_mutation_terminal_escalated_resume_is_detected() -> None:
    acs = copy.deepcopy(CTX.acc)
    victim = next(item for item in acs if item["id"] == "AC-47-3")
    claim = next(ref for ref in victim["transition_refs"] if ref["event"] == "claim")
    claim["from"] = "escalated"
    faults = semantic_refs.detect_transition_ref_faults(
        CTX.nfc, acs, CTX.tcc, CTX.allc, CTX.transitions)
    assert any("AC-47-3:非正準transition tasks.escalated:claim->in_progress" in f
               for f in faults)


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


def _actual_operation_contract(item_id: str = "FR-X") -> dict:
    return {
        "id": item_id,
        "normal_behavior": (
            "execution_mode='actual' の実外部 write を effect='write', "
            "policy_category='content_publish', rate_scope='wp' で sent にし、"
            "external_operation_row_id・correlation_key・request_hash・request_sequenceが"
            "一致するoperation_logを1行生成する"
        ),
        "semantic_refs": {
            "table_refs": ["evidence", "external_operations"],
            "column_refs": sorted(semantic_refs.OPERATION_LOG_REQUIRED_COLUMNS),
            "state_refs": [],
            "event_refs": [],
            "evidence_kind_refs": ["operation_log"],
            "error_type_refs": [],
            "api_refs": [],
        },
    }


def test_actual_external_operation_log_binding_is_accepted() -> None:
    assert semantic_refs.detect_state_evidence_faults(
        [], [], [_actual_operation_contract()]) == []


def test_mutation_external_table_reference_alone_cannot_bless_internal_log() -> None:
    victim = _actual_operation_contract()
    victim["normal_behavior"] = "PairNotEstablishedをoperation_logへ記録する"
    victim["notes"] = (
        "別仕様の語彙: execution_mode='actual', status=sent, effect=read/write, "
        "policy_category, rate_scope, external_operation_row_id, correlation_key, "
        "request_hash, request_sequence"
    )
    faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
    assert any("内部/pre-call operation_log正生成" in fault for fault in faults)


def test_mutation_positive_claim_in_input_field_is_not_blanket_skipped() -> None:
    for claim in (
        "PairNotEstablishedでoperation_logを1行生成する",
        "PairNotEstablishedで1行生成する証跡はoperation_logとする",
    ):
        victim = _actual_operation_contract()
        victim.pop("normal_behavior")
        victim["input"] = claim
        faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
        assert any("内部/pre-call operation_log正生成" in fault for fault in faults), claim


def test_observation_only_fields_and_negative_kind_ref_are_accepted() -> None:
    victim = _actual_operation_contract()
    victim.pop("normal_behavior")
    victim.update({
        "fixture": "既存operation_log 1行を入力として混入済み",
        "given": "operation_log orphan 行",
        "observation_point": "operation_logの件数をSELECTで観測",
        "expected_evidence": "PairNotEstablished時はoperation_log 0行",
    })
    assert semantic_refs.detect_state_evidence_faults([], [], [victim]) == []


def test_mutation_negative_or_neutral_wording_cannot_hide_positive_claim() -> None:
    claims = (
        "operation_log 0行ではなく内部拒否を1行生成する",
        "operation_log 0行は禁止し内部拒否を1行生成する",
        "外部操作差分なしという旧仕様を廃止し operation_log 1行を生成する",
        "operation_logの検査対象として内部拒否を1行生成する",
    )
    for index, claim in enumerate(claims):
        victim = _actual_operation_contract(f"FR-MUT-{index}")
        victim["normal_behavior"] = claim
        positive, _ = semantic_refs._operation_log_fragments(claim)
        assert positive, claim
        faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
        assert faults, claim


def test_mutation_actual_operation_log_without_sent_boundary_is_detected() -> None:
    victim = _actual_operation_contract()
    victim["normal_behavior"] = victim["normal_behavior"].replace(" sent にし、", " 実行し、")
    faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
    assert any("'sent'" in fault for fault in faults)


def test_mutation_operation_log_only_in_ac_db_delta_is_detected() -> None:
    victim = _actual_operation_contract("AC-X")
    victim.pop("normal_behavior")
    victim["expected_db_delta"] = "内部ゲート拒否でoperation_log +1行"
    faults = semantic_refs.detect_state_evidence_faults([victim], [], [])
    assert faults


def test_mutation_operation_log_only_in_tcc_then_is_detected() -> None:
    victim = _actual_operation_contract("TCC-X")
    victim.pop("normal_behavior")
    victim["then"] = "内部状態遷移をoperation_logへ記録する"
    faults = semantic_refs.detect_state_evidence_faults([], [victim], [])
    assert faults


def test_mutation_mixed_negative_and_positive_claim_does_not_skip_positive() -> None:
    victim = _actual_operation_contract()
    victim["normal_behavior"] = (
        "mockではoperation_log 0行、実行時の内部ゲート拒否はoperation_log +1行"
    )
    faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
    assert faults


def test_mutation_web_fetch_without_structured_external_binding_is_detected() -> None:
    victim = _actual_operation_contract()
    victim["normal_behavior"] = "Web 取得の結果をoperation_logへ記録する"
    victim["semantic_refs"]["table_refs"] = ["evidence"]
    faults = semantic_refs.detect_state_evidence_faults([], [], [victim])
    assert any("table_ref欠落" in fault for fault in faults)


def test_mutation_markdown_internal_rejection_log_is_detected() -> None:
    text = "| PairNotEstablished | 送信前拒否 | operation_log 1行 |"
    faults = semantic_refs.detect_markdown_operation_log_faults([("fixture.md", text)])
    assert faults == ["fixture.md:1:内部/pre-call拒否をoperation_logで表現"]


def test_markdown_actual_sent_and_zero_row_rejections_are_accepted() -> None:
    text = "\n".join([
        "| PairNotEstablished | 外部2表・operation_log 0行 |",
        "| RateLimitExceeded | sent後のprovider 429はexternal_operation_row_id束縛operation_log 1行 |",
    ])
    assert semantic_refs.detect_markdown_operation_log_faults([("fixture.md", text)]) == []


def test_mutation_markdown_parent_child_wrapping_is_detected() -> None:
    for parent in (
        "- PairNotEstablished（送信前拒否）",
        "- PairNotEstablished（送信前拒否）。",
    ):
        text = "\n".join([parent, "  - operation_log 1行を生成する"])
        faults = semantic_refs.detect_markdown_operation_log_faults([("wrapped.md", text)])
        assert faults == ["wrapped.md:1:内部/pre-call拒否をoperation_logで表現"]


def test_mutation_fullwidth_slash_cannot_separate_rejection_from_log() -> None:
    text = "- PairNotEstablished（送信前拒否）／operation_log 1行を生成する"
    faults = semantic_refs.detect_markdown_operation_log_faults([("slash.md", text)])
    assert faults == ["slash.md:1:内部/pre-call拒否をoperation_logで表現"]


def test_markdown_three_line_wrapped_negative_claim_is_accepted() -> None:
    text = "\n".join([
        "- PairNotEstablished（送信前拒否）では operation_log は",
        "  外部操作とともに",
        "  0行とする",
    ])
    assert semantic_refs.detect_markdown_operation_log_faults([("wrapped.md", text)]) == []
