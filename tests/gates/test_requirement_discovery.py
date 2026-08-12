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
    assert any("自動 mutation" in fault for fault in discovery.safety_faults(ledger(), tmp_path))


def test_mutation_contract_change_requires_proposal_and_decision(monkeypatch) -> None:
    data = ledger()
    monkeypatch.setattr(
        discovery,
        "changed_contract_paths",
        lambda _start: {"docs/L3-system-requirements/canonical/functional/fr-contracts.json"},
    )
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
