"""requirement_discovery の実台帳と append-only mutation を検査する。"""

from __future__ import annotations

import copy
import json

from tools.gates import requirement_discovery
from tools.gates import requirement_discovery as discovery
from tools.gates.common import Ctx


def ledger() -> dict:
    return json.loads(discovery.LEDGER.read_text(encoding="utf-8"))


def test_real_discovery_ledger_is_valid() -> None:
    data = ledger()
    assert discovery.schema_and_event_faults(data) == []
    assert discovery.coverage_faults(data) == []
    assert discovery.prefix_faults(None, data) == []
    assert discovery.contract_coverage_faults(data, Ctx()) == []


def test_mutation_duplicate_event_id_is_rejected() -> None:
    data = ledger()
    duplicate = copy.deepcopy(data["events"][0])
    duplicate["sequence"] = 2
    data["events"].append(duplicate)
    assert any("event_id が重複" in fault for fault in discovery.schema_and_event_faults(data))


def test_mutation_empty_adapted_ledger_is_rejected() -> None:
    data = ledger()
    data["events"] = []
    assert any("event を少なくとも 1 件" in fault for fault in discovery.schema_and_event_faults(data))


def test_mutation_sequence_change_is_rejected() -> None:
    data = ledger()
    data["events"][0]["sequence"] = 9
    assert any("sequence は 1 から単調増加" in fault for fault in discovery.schema_and_event_faults(data))


def test_mutation_malformed_payload_is_a_fault_not_a_type_error() -> None:
    data = ledger()
    data["events"][0].update({
        "event_type": "candidate_recorded",
        "payload": {
            "title": "candidate", "problem_statement": "problem", "value_hypothesis": "value",
            "unresolved_questions": 1,
        },
    })
    assert any("unresolved_questions は string 配列" in fault for fault in discovery.schema_and_event_faults(data))
    assert discovery.detect_discovery_faults(data)


def test_mutation_existing_event_edit_delete_or_reorder_is_rejected() -> None:
    previous = ledger()
    edited = copy.deepcopy(previous)
    edited["events"][0]["payload"]["proposal_summary"] = "改変"
    assert discovery.prefix_faults(previous, edited)
    assert discovery.prefix_faults(previous, {**previous, "events": []})
    two = copy.deepcopy(previous)
    next_event = copy.deepcopy(two["events"][0])
    next_event["event_id"] = "RDE-000002"
    next_event["sequence"] = 2
    two["events"].append(next_event)
    two["events"] = list(reversed(two["events"]))
    assert discovery.prefix_faults(previous, two)


def test_mutation_future_reference_is_rejected() -> None:
    data = ledger()
    data["events"][0]["references"] = [{"kind": "event", "id": "RDE-000001"}]
    assert any(
        "future event reference" in fault for fault in discovery.reference_and_lifecycle_faults(data, Ctx())
    )


def test_mutation_lifecycle_order_reversal_is_rejected() -> None:
    data = ledger()
    base = {
        "occurred_at": "2026-08-13T05:00:00Z",
        "recorded_at": "2026-08-13T05:00:00Z",
        "actor_principal": "codex-luna",
        "references": [],
    }
    data["events"] = [
        {
            **base,
            "event_id": "RDE-000001",
            "sequence": 1,
            "subject_id": "REQ-001",
            "event_type": "candidate_recorded",
            "payload": {},
        },
        {
            **base,
            "event_id": "RDE-000002",
            "sequence": 2,
            "subject_id": "REQ-001",
            "event_type": "question_answered",
            "payload": {},
        },
        {
            **base,
            "event_id": "RDE-000003",
            "sequence": 3,
            "subject_id": "REQ-001",
            "event_type": "question_raised",
            "payload": {},
        },
    ]
    assert any(
        "question_answered に先行 question_raised がない" in fault
        for fault in discovery.reference_and_lifecycle_faults(data, Ctx())
    )


def test_mutation_payload_reference_integrity_is_rejected() -> None:
    data = ledger()
    data["events"].append(
        {
            "event_id": "RDE-000002",
            "sequence": 2,
            "subject_id": "DISCOVERY-LEDGER",
            "event_type": "approval_requested",
            "occurred_at": "2026-08-13T05:01:00Z",
            "recorded_at": "2026-08-13T05:01:00Z",
            "actor_principal": "codex-luna",
            "references": [],
            "payload": {"proposal_event_id": "RDE-404040", "requested_by": "codex-luna"},
        }
    )
    assert any(
        "payload.proposal_event_id が orphan" in fault
        for fault in discovery.reference_and_lifecycle_faults(data, Ctx())
    )


def test_mutation_bootstrap_subject_cannot_bypass_approval_order() -> None:
    data = ledger()
    decision = copy.deepcopy(data["events"][0])
    decision.update({"event_id": "RDE-000002", "sequence": 2, "event_type": "approval_decided"})
    data["events"].append(decision)
    assert any(
        "approval_decided に先行 approval_requested" in fault
        for fault in discovery.reference_and_lifecycle_faults(data, Ctx())
    )


def approval_event(*, approver: str, digest: str) -> dict:
    return {
        "event_id": "RDE-000002",
        "sequence": 2,
        "subject_id": "DISCOVERY-LEDGER",
        "event_type": "approval_decided",
        "occurred_at": "2026-08-13T05:01:00Z",
        "recorded_at": "2026-08-13T05:01:00Z",
        "actor_principal": approver,
        "references": [{"kind": "event", "id": "RDE-000001"}],
        "payload": {
            "proposal_event_id": "RDE-000001",
            "proposal_author_principal": "codex-luna",
            "approver_principal": approver,
            "decision": "accepted",
            "artifact_id": "L4-BASIC-DESIGN",
            "artifact_digest": digest,
            "artifact_snapshot": None,
        },
    }


def test_mutation_self_approval_is_rejected() -> None:
    data = ledger()
    data["events"].append(approval_event(approver="codex-luna", digest="000000000000"))
    assert any("self approval" in fault for fault in discovery.approval_faults(data, Ctx()))


def test_mutation_approval_digest_mismatch_is_rejected() -> None:
    data = ledger()
    data["events"].append(approval_event(approver="po-reviewer", digest="000000000000"))
    assert any("approval_digest と不一致" in fault for fault in discovery.approval_faults(data, Ctx()))


def test_mutation_approval_actor_must_match_approver() -> None:
    data = ledger()
    event = approval_event(approver="po-reviewer", digest="000000000000")
    event["actor_principal"] = "another-reviewer"
    data["events"].append(event)
    assert any("actor_principal と approver_principal" in fault for fault in discovery.approval_faults(data, Ctx()))


def test_mutation_rejected_decision_does_not_settle_contract_coverage(monkeypatch) -> None:
    data = ledger()
    context = Ctx()
    artifact = next(item["artifact_id"] for item in context.manifest_items
                    if item["canonical_path"].endswith("functional/fr-contracts.json"))
    data["events"][0]["payload"]["target_artifact_ids"] = [artifact]
    data["events"].append({
        "event_id": "RDE-000002", "sequence": 2, "subject_id": "DISCOVERY-LEDGER",
        "event_type": "approval_decided", "occurred_at": "2026-08-13T05:01:00Z",
        "recorded_at": "2026-08-13T05:01:00Z", "actor_principal": "po-reviewer", "references": [],
        "payload": {
            "proposal_event_id": "RDE-000001", "proposal_author_principal": "codex-luna",
            "approver_principal": "po-reviewer", "decision": "rejected", "artifact_id": artifact,
            "artifact_digest": "000000000000", "artifact_snapshot": None,
        },
    })
    monkeypatch.setattr(discovery, "changed_contract_paths", lambda _start: {"docs/L3-system-requirements/canonical/functional/fr-contracts.json"})
    assert any("approval_decided 又は withdrawn" in fault
               for fault in discovery.contract_coverage_faults(data, context))


def test_historical_accepted_snapshot_does_not_require_current_digest(monkeypatch) -> None:
    data = ledger()
    context = Ctx()
    artifact = next(item for item in context.manifest_items if item["artifact_id"] == "L4-BASIC-DESIGN")
    digest = artifact["approval_digest"]
    data["events"][0]["payload"]["target_artifact_ids"] = ["L4-BASIC-DESIGN"]
    data["events"].extend([
        {"event_id": "RDE-000002", "sequence": 2, "subject_id": "DISCOVERY-LEDGER", "event_type": "approval_requested",
         "occurred_at": "2026-08-13T05:01:00Z", "recorded_at": "2026-08-13T05:01:00Z", "actor_principal": "codex-luna", "references": [],
         "payload": {"proposal_event_id": "RDE-000001", "requested_by": "codex-luna"}},
        {"event_id": "RDE-000003", "sequence": 3, "subject_id": "DISCOVERY-LEDGER", "event_type": "approval_decided",
         "occurred_at": "2026-08-13T05:02:00Z", "recorded_at": "2026-08-13T05:02:00Z", "actor_principal": "po-old", "references": [],
         "payload": {"proposal_event_id": "RDE-000001", "proposal_author_principal": "codex-luna", "approver_principal": "po-old", "decision": "accepted", "artifact_id": "L4-BASIC-DESIGN", "artifact_digest": "000000000000", "artifact_snapshot": {}}},
        {"event_id": "RDE-000004", "sequence": 4, "subject_id": "DISCOVERY-LEDGER", "event_type": "approval_decided",
         "occurred_at": "2026-08-13T05:03:00Z", "recorded_at": "2026-08-13T05:03:00Z", "actor_principal": "po-new", "references": [],
         "payload": {"proposal_event_id": "RDE-000001", "proposal_author_principal": "codex-luna", "approver_principal": "po-new", "decision": "accepted", "artifact_id": "L4-BASIC-DESIGN", "artifact_digest": digest, "artifact_snapshot": {}}},
    ])
    monkeypatch.setattr(discovery, "_snapshot_faults", lambda _payload, _event_id: [])
    faults = discovery.approval_faults(data, context)
    assert not any("RDE-000003: latest accepted" in fault for fault in faults)
    assert not any("RDE-000003: latest accepted canonical" in fault for fault in faults)


def test_mutation_secret_field_is_rejected() -> None:
    data = ledger()
    data["events"][0]["payload"]["proposal_summary"] = "Bearer supersensitive"
    assert any("secret/PII value" in fault for fault in discovery.safety_faults(data))


def test_mutation_canonical_mutation_path_is_rejected(tmp_path) -> None:
    source = tmp_path / "src" / "writer.py"
    source.parent.mkdir()
    source.write_text(
        'path = "requirement-discovery-events.json"\npath.write_text("bad")\n', encoding="utf-8"
    )
    assert any("canonical path alias" in fault for fault in discovery.safety_faults(ledger(), tmp_path))


def test_mutation_imported_ledger_or_contract_alias_write_is_rejected(tmp_path) -> None:
    source = tmp_path / "tools" / "writer.py"
    source.parent.mkdir()
    source.write_text(
        "from tools.gates.requirement_discovery import LEDGER\n"
        "from tools.gates.common import FR_CONTRACTS\n"
        "LEDGER.write_text('bad')\nFR_CONTRACTS.write_text('bad')\n", encoding="utf-8"
    )
    faults = discovery.safety_faults(ledger(), tmp_path)
    assert any("LEDGER" in fault for fault in faults)
    assert any("FR_CONTRACTS" in fault for fault in faults)


def test_mutation_pii_and_token_values_are_rejected() -> None:
    for value in ("alice@example.test", "090-1234-5678", "東京都千代田区1丁目1番地", "ghp_abcdefghijklmnopqrstuvwxyz012345"):
        data = ledger()
        data["events"][0]["payload"]["proposal_summary"] = value
        assert any("secret/PII value" in fault for fault in discovery.safety_faults(data))


def test_mutation_contract_change_requires_proposal_and_decision(monkeypatch) -> None:
    data = ledger()
    monkeypatch.setattr(
        discovery,
        "changed_contract_paths",
        lambda _start: {"docs/L3-system-requirements/canonical/functional/fr-contracts.json"},
    )
    assert any("specification_proposed" in fault for fault in discovery.contract_coverage_faults(data, Ctx()))


def test_mutation_sr_contract_change_requires_discovery_coverage(monkeypatch) -> None:
    data = ledger()
    monkeypatch.setattr(discovery, "changed_contract_paths", lambda _start: {"docs/L3-system-requirements/canonical/strategy/sr-contracts.json"})
    assert any("specification_proposed" in fault for fault in discovery.contract_coverage_faults(data, Ctx()))


def test_mutation_meta_gate_observes_requirement_discovery_module() -> None:
    """meta gate 用: 本番モジュール呼出しの結果を mutation test 自身で観測する。"""
    assert requirement_discovery.prefix_faults({"events": [{}]}, {"events": []})


def test_mutation_withdrawal_without_explicit_deferred_reason_does_not_settle_coverage(monkeypatch) -> None:
    data = ledger()
    data["events"].append(
        {
            "event_id": "RDE-000002",
            "sequence": 2,
            "subject_id": "DISCOVERY-LEDGER",
            "event_type": "withdrawn",
            "occurred_at": "2026-08-13T05:01:00Z",
            "recorded_at": "2026-08-13T05:01:00Z",
            "actor_principal": "po-reviewer",
            "references": [{"kind": "event", "id": "RDE-000001"}],
            "payload": {"reason": "later", "withdrawn_event_id": "RDE-000001"},
        }
    )
    monkeypatch.setattr(
        discovery,
        "changed_contract_paths",
        lambda _start: {"docs/L3-system-requirements/canonical/functional/fr-contracts.json"},
    )
    context = Ctx()
    artifact = next(
        item["artifact_id"]
        for item in context.manifest_items
        if item["canonical_path"].endswith("functional/fr-contracts.json")
    )
    data["events"][0]["payload"]["target_artifact_ids"] = [artifact]
    assert any(
        "approval_decided 又は withdrawn" in fault
        for fault in discovery.contract_coverage_faults(data, context)
    )
