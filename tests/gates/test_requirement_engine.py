"""HELIX 要件確定エンジン adaptation の mutation tests。"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts.render_views import render_requirement_candidates
from tools.gates import requirement_engine
from tools.gates.common import Ctx


def test_projection_is_deterministic_and_non_authoritative() -> None:
    first = requirement_engine.semantic_projection(Ctx())
    second = requirement_engine.semantic_projection(Ctx())
    assert first == second
    assert first["authority"] == "generated_non_authoritative_projection"
    assert first["partition"] == "stable_id_keyed_shards"
    assert [shard["kind"] for shard in first["shards"]] == [
        "requirements",
        "system_contracts",
        "acceptance_cases",
        "system_tests",
        "refinement_contracts",
    ]
    assert any(record["kind"] == "RRF" for record in first["records"])
    assert sum(record["kind"] == "REQ" for record in first["records"]) == 55
    assert first["revalidation_inventory"]["counts"] == {
        "BR": 41,
        "BRM": 70,
        "REQ": 55,
        "FR": 43,
        "SR": 19,
        "NFR": 11,
        "MR": 54,
        "FN": 61,
        "AC": 252,
        "TC": 258,
        "total": 864,
    }
    assert all(item["decision_status"] == "unresolved" for item in first["revalidation_inventory"]["items"])
    inventory = {
        item["stable_id"]: set(item["decision_subject_ids"])
        for item in first["revalidation_inventory"]["items"]
    }
    assert "AUTOMATED-PUBLISHING-ADMISSION" in inventory["FR-46"]
    assert "VPS-UI-INBOX-LIFECYCLE" in inventory["FR-76"]
    assert "VPS-UI-AUTHENTICATION-SESSION" in inventory["FR-77"]
    assert "DISCORD-COMMUNITY-MARKETING-ROUTE" in inventory["MR-DC-1"]
    for stable_id in ("BR-H2", "BR-H3", "FR-16", "FR-43", "FR-46", "FR-75", "FR-76", "FR-77"):
        assert "AUTO-MODE-DECISION-AUTHORITY" not in inventory[stable_id]
        assert "DISCORD-MULTI-PURPOSE-BOUNDARIES" not in inventory[stable_id]
    assert all(
        record["applicability"] == ("proposal_only" if record["kind"] == "RRF" else "revalidation_required")
        for record in first["records"]
    )
    assert first["root_digest"].startswith("sha256:")
    assert requirement_engine.projection_faults(first) == []


def test_mutation_projection_digest_and_order_are_rejected() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    projection["records"][0]["semantic"]["id"] = "MUTATED"
    projection["records"] = list(reversed(projection["records"]))
    faults = requirement_engine.projection_faults(projection)
    assert any("semantic digest" in fault for fault in faults)
    assert any("決定順" in fault for fault in faults)
    assert any("root digest" in fault for fault in faults)


def test_mutation_projection_missing_partition_is_rejected() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    projection["shards"].pop()
    assert any("5 partition" in fault for fault in requirement_engine.projection_faults(projection))


def test_mutation_revalidation_inventory_cannot_drop_or_promote_contract() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    projection["revalidation_inventory"]["items"].pop()
    projection["revalidation_inventory"]["items"][0]["decision_status"] = "current"
    faults = requirement_engine.projection_faults(projection)
    assert any("IR schema" in fault for fault in faults)
    assert any("inventory digest" in fault or "current扱い" in fault for fault in faults)


def test_vps_ui_gate_requires_runtime_reality_disclaimer() -> None:
    faults = requirement_engine.vps_ui_requirement_descent_faults(Ctx())
    assert not any("配置方針と未実装" in fault for fault in faults)
    assert not any("PRC-15" in fault for fault in faults)


def test_mutation_projection_record_partition_schema_is_rejected() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    projection["records"][0]["partition"] = "unknown"
    assert any("IR schema" in fault for fault in requirement_engine.projection_faults(projection))


def test_mutation_projection_cannot_make_legacy_contract_current() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    contract = next(record for record in projection["records"] if record["kind"] == "FR")
    contract["applicability"] = "current"
    faults = requirement_engine.projection_faults(projection)
    assert any("IR schema" in fault for fault in faults)
    assert any("record applicability不正" in fault for fault in faults)


def test_req_projection_is_explicitly_non_authoritative_revalidation_input() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    req_records = [record for record in projection["records"] if record["kind"] == "REQ"]
    assert req_records
    assert {record["source_authority"] for record in req_records} == {"read_only_req_revalidation_ledger"}
    assert {record["applicability"] for record in req_records} == {"revalidation_required"}
    req_records[0]["source_authority"] = "canonical_contract_json"
    assert any(
        "REQ/" in fault and "record source authority不正" in fault
        for fault in requirement_engine.projection_faults(projection)
    )


def test_media_and_function_ledgers_are_projected_as_read_only_revalidation_inputs() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    expected_counts = {"BRM": 70, "MR": 54, "FN": 61}
    for kind, count in expected_counts.items():
        records = [record for record in projection["records"] if record["kind"] == kind]
        assert len(records) == count
        assert {record["source_authority"] for record in records} == {"read_only_legacy_requirement_ledger"}
        assert {record["applicability"] for record in records} == {"revalidation_required"}


def test_authority_policy_keeps_revising_fail_closed() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    assert requirement_engine.authority_faults(policy) == []
    policy["implementation_authorized"] = True
    assert any("revising" in fault for fault in requirement_engine.authority_faults(policy))


def test_generated_requirement_candidate_view_is_complete_and_non_authoritative() -> None:
    path, text = render_requirement_candidates()
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert path == requirement_engine.CANDIDATE_VIEW
    assert "提案専用の生成view" in text
    assert "現行要求の正本・PO承認・設計・実装入力ではない" in text
    assert "本view全体を一括承認として扱わない" in text
    assert "approval receiptあり **0** 件" in text
    for record in refinements["records"]:
        assert text.count(f"## {record['refinement_id']} —") == 1
        if record["approval"] is None:
            section = text.split(f"## {record['refinement_id']} —", 1)[1].split("\n## ", 1)[0]
            assert "未承認（approval receiptなし）" in section


def test_mutation_incomplete_helix_engine_cannot_claim_adapted() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["helix_engine_adoption"]["status"] = "adapted"
    policy["helix_engine_adoption"]["missing_before_adapted"] = []
    assert any("bridge境界" in fault for fault in requirement_engine.authority_faults(policy))


def test_mutation_dual_authority_and_bulk_approval_are_rejected() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["projection"]["dual_authority"] = "allowed"
    policy["refinement"]["bulk_approval"] = "allowed"
    faults = requirement_engine.authority_faults(policy)
    assert any("dual authority" in fault for fault in faults)
    assert any("一括承認" in fault for fault in faults)


def test_mutation_old_source_cannot_be_current_during_revalidation() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    first = policy["canonical_sources"][0]
    policy["source_applicability"][first] = "current"
    assert any("revalidation_required" in fault for fault in requirement_engine.authority_faults(policy))


def test_unresolved_semantic_gates_have_no_waiver_and_typed_disposition() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    assert requirement_engine.authority_faults(policy) == []
    policy["unresolved_semantic_gate_disposition"]["waiver_forbidden"] = False
    del policy["unresolved_semantic_gate_disposition"]["gates"]["G-REQ-VPS-UI-DESCENT"]
    faults = requirement_engine.authority_faults(policy)
    assert any("waiver禁止" in fault for fault in faults)
    assert any("処理分類が不完全" in fault for fault in faults)


def test_mutation_confirmed_legacy_artifact_cannot_be_implementation_input() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["artifact_applicability_policy"]["implementation_input"] = True
    policy["artifact_applicability_policy"]["exception_artifact_ids"] = ["L0-MARKETING-HARNESS-CHARTER"]
    faults = requirement_engine.authority_faults(policy)
    assert any("実装入力" in fault for fault in faults)
    assert any("例外" in fault for fault in faults)


def test_manifest_blocks_all_l0_l6_artifacts_during_revalidation() -> None:
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    applicability = manifest["applicability_policy"]
    assert applicability["revalidation_required_layers"] == ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]
    assert applicability["implementation_input"] is False
    assert applicability["exception_artifact_ids"] == []
    assert applicability["layer_policy_is_default"] is True
    assert applicability["per_artifact_applicability_required"] is True
    items = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))["items"]
    assert all(item["implementation_input"] is False for item in items)
    assert all(item["applicability_status"] != "current" for item in items if item["layer"] != "00-authority")


def test_current_compatibility_view_drift_is_detected() -> None:
    faults = requirement_engine.compatibility_drift_faults(Ctx())
    assert any(fault.startswith("FR-16: compatibility view slice=") for fault in faults)


def test_mutation_compatibility_view_cannot_become_authority() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["compatibility_inputs"]["docs/L3-system-requirements/canonical/functional/requirements.json"] = (
        "canonical"
    )
    assert requirement_engine.compatibility_authority_faults(policy)


def test_mutation_req_trace_ledger_cannot_become_current_authority() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["compatibility_inputs"]["docs/L1-business-requirements/canonical/req/req.json"] = "canonical"
    assert requirement_engine.compatibility_authority_faults(policy)


def test_trace_parent_missing_child_is_detected() -> None:
    ctx = Ctx()
    _ = ctx.brc
    mutated = copy.deepcopy(ctx.__dict__["brc"])
    parent = next(item for item in mutated if item["id"] == "BR-A1")
    parent["trace_down"] = []
    ctx.__dict__["brc"] = mutated
    assert any(
        "parent trace_down missing child" in fault
        for fault in requirement_engine.bidirectional_trace_faults(ctx)
    )


def test_current_req_to_nfr_trace_gaps_are_detected() -> None:
    faults = requirement_engine.layered_trace_faults(Ctx())
    assert any(fault.startswith("REQ-027->NFR-6:") for fault in faults)
    assert any(fault.startswith("REQ-030->NFR-8:") for fault in faults)
    assert any("FR-76: stable REQ root" in fault for fault in faults)
    assert any("FR-77: stable REQ root" in fault for fault in faults)
    assert any("SR-17: stable REQ root" in fault for fault in faults)
    assert any("NFR-10: stable REQ root" in fault for fault in faults)


def test_current_legacy_du_to_tc_references_are_detected() -> None:
    faults = requirement_engine.implementation_trace_faults(Ctx())
    assert any("DU-13: unknown TC reference TC-041" in fault for fault in faults)
    assert any("DU-14: unknown TC reference TC-047" in fault for fault in faults)


def test_current_req_to_fn_413_trace_gap_is_detected() -> None:
    faults = requirement_engine.functional_ledger_trace_faults(Ctx())
    assert any("REQ-045->FN-413: FN upstream missing REQ" in fault for fault in faults)


def test_contract_prose_cannot_use_wildcard_as_executable_fr_reference() -> None:
    faults = requirement_engine.trace_semantic_responsibility_faults(Ctx())
    assert any("FR-21: 実行契約本文が未定義wildcard ID FR-4x" in fault for fault in faults)
    assert any("CMP-10: security boundaryが存在しない要求ID BR-31" in fault for fault in faults)


def test_requirements_defined_without_descent_or_deferred_contract_is_detected() -> None:
    faults = requirement_engine.requirement_descent_admission_faults(Ctx())
    assert any("FR/FR-17: requirements_defined" in fault for fault in faults)
    assert any("FR/FR-76: FN/CMPへ未降下" in fault for fault in faults)
    assert any("SR/SR-17: acceptance contractへ未降下" in fault for fault in faults)
    assert any("SR/SR-19: deferred再開条件がない" in fault for fault in faults)


def test_old_api_only_evidence_contract_conflicts_with_vps_ui_primary_requirement() -> None:
    faults = requirement_engine.vps_ui_requirement_descent_faults(Ctx())
    assert faults == ["FR-77: VPS UI主入口に必要なevidence/KPI閲覧を旧API-only契約が明示禁止"]


def test_upstream_po_judgements_missing_from_acceptance_are_detected() -> None:
    faults = requirement_engine.human_judgement_descent_faults(Ctx())
    assert any("BR-A3->FR-71: brand計画確定・改訂承認" in fault for fault in faults)
    assert any("BR-D2->FR-32: draft採否の人間承認" in fault for fault in faults)
    assert any("BR-D3->FR-33: 危険側config変更承認" in fault for fault in faults)
    assert any("BR-D4->FR-34: 事業profile内容確定" in fault for fault in faults)
    assert any("BR-E1->FR-61: KPI tree初期承認" in fault for fault in faults)
    assert any("BR-F1->FR-41: 有償API例外追加承認" in fault for fault in faults)
    assert any("BR-F3->FR-41: 媒体追加PO判断" in fault for fault in faults)
    assert any("BR-G3->FR-52: Design System改訂承認" in fault for fault in faults)
    assert any("BR-H2->FR-46: オートモード移行の最終承認" in fault for fault in faults)
    assert any("BR-H2->FR-46: auto適格性の機械判定がPOの移行承認を代替" in fault for fault in faults)
    assert any("BR-H2->FR-75: preflight前の公開・auto-mode最終承認" in fault for fault in faults)
    assert any("BR-H2->FR-75: preflight自動判定" in fault for fault in faults)
    assert any("BR-F5->FR-75: 警告停止後の再開判断" in fault for fault in faults)
    assert any("BR-F5->FR-75: preflight自動判定" in fault for fault in faults)
    assert any("BR-I1->FR-34: brand/profile追加廃止判断" in fault for fault in faults)
    assert any("BR-I1->FR-75: preflight対象profile追加廃止判断" in fault for fault in faults)
    assert any("BR-I5->SR-06: campaign brief確定判断" in fault for fault in faults)
    assert any("BR-I5->SR-14: campaign語彙変更承認" in fault for fault in faults)
    assert any("BR-I6->SR-13: 企画確定の人間判断を別agent審査で代替" in fault for fault in faults)


def test_nfrs_without_stable_req_and_business_authority_are_detected() -> None:
    faults = requirement_engine.nfr_requirement_authority_faults(Ctx())
    assert any("NFR-1: stable REQ根拠" in fault for fault in faults)
    assert any("NFR-9: stable BR/actor/value根拠がない" in fault for fault in faults)
    assert any("NFR-10: stable BR/actor/value根拠がない" in fault for fault in faults)
    assert any("NFR-11: stable REQ根拠" in fault for fault in faults)


def test_confirmed_acceptance_cannot_depend_on_draft_strategy_tests() -> None:
    faults = requirement_engine.strategy_test_authority_faults(Ctx())
    assert any("strategy test ledger lifecycle=draft" in fault for fault in faults)
    assert any("PO content receiptがない" in fault for fault in faults)


def test_old_provider_specific_runtime_dependencies_are_detected() -> None:
    faults = requirement_engine.provider_dependency_semantic_faults()
    assert any("Claude Design" in fault for fault in faults)
    assert any("Codex CLI/home" in fault for fault in faults)
    assert any("consumer Web UI" in fault for fault in faults)


def test_current_fr_fn_and_ac_phase_mismatches_are_detected() -> None:
    faults = requirement_engine.phase_alignment_faults(Ctx())
    assert any("FR-16(S0)->FN-110(S1)" in fault for fault in faults)
    assert any("FR-44(S1)->FN-406(S0)" in fault for fault in faults)
    assert any("FR-44(S1)->AC-44-1(S0)" in fault for fault in faults)
    assert any("FR-53: 包含phase S3+" in fault for fault in faults)


def test_current_sparse_contract_semantic_dimensions_are_detected() -> None:
    faults = requirement_engine.semantic_dimension_faults(Ctx())
    assert not any(fault.startswith("BR/") for fault in faults)
    assert any("REQ/REQ-001: semantic dimension actor missing" in fault for fault in faults)
    assert any("FN/FN-101: semantic dimension actor missing" in fault for fault in faults)
    assert any("MR/MR-WP-1: semantic dimension actor missing" in fault for fault in faults)
    assert any("FR/FR-16: semantic dimension actor missing" in fault for fault in faults)
    assert any("NFR/NFR-1: semantic dimension phase missing" in fault for fault in faults)
    assert any("AC/AC-16-1: semantic dimension actor missing" in fault for fault in faults)
    assert any("AC/AC-16-1: semantic dimension scope missing" in fault for fault in faults)
    assert any("AC/AC-16-1: semantic dimension phase missing" in fault for fault in faults)


def test_mutation_req_upstream_must_be_bidirectional() -> None:
    ctx = Ctx()
    _ = ctx.req
    mutated = copy.deepcopy(ctx.__dict__["req"])
    req = next(item for item in mutated if item["id"] == "REQ-001")
    req["trace"]["upstream"] = ["BR-J1"]
    ctx.__dict__["req"] = mutated
    faults = requirement_engine.layered_trace_faults(ctx)
    assert any("BR-J1->REQ-001: BR downstream missing REQ" in fault for fault in faults)


def test_withdrawn_requests_are_not_active() -> None:
    data = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    assert requirement_engine.active_approval_requests(data) == []


def test_current_refinement_records_are_structurally_valid_and_cover_candidates() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.refinement_faults(refinements, discovery) == []


def test_req_authority_normalization_binds_delta_overlay_and_pending_cutover(
    tmp_path: Path, monkeypatch: Any
) -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.req_authority_normalization_policy_faults(Ctx(), refinements) == []

    stale_delta = copy.deepcopy(refinements)
    stale_delta["req_authority_normalization_policy"]["delta_overlay"]["REQ-053/text"][0] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "delta overlay" in fault or "正本digest" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(Ctx(), stale_delta)
    )

    premature_cutover = copy.deepcopy(refinements)
    premature_cutover["req_authority_normalization_policy"]["delta_overlay_dispositions"][
        "cutover_blocked"
    ] = False
    assert any(
        "cutover解除" in fault or "正本digest" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(
            Ctx(), premature_cutover
        )
    )
    incomplete_classified = copy.deepcopy(refinements)
    disposition = incomplete_classified["req_authority_normalization_policy"][
        "delta_overlay_dispositions"
    ]
    disposition["status"] = "classified_pending_cutover"
    assert any(
        "exact被覆" in fault or "PO row-set receipt" in fault or "artifact binding" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(
            Ctx(), incomplete_classified
        )
    )

    classified = copy.deepcopy(refinements)
    policy = classified["req_authority_normalization_policy"]
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    by_id = {item["artifact_id"]: item for item in manifest["items"]}
    source_ids = ["L1-REQ", "L1-REQUIREMENT-LIST"]
    source_revisions = []
    source_content_digests = []
    for artifact_id in source_ids:
        path = requirement_engine.REPO_ROOT / by_id[artifact_id]["canonical_path"]
        revision = requirement_engine.git(
            "log", "-1", "--format=%H", "--", by_id[artifact_id]["canonical_path"]
        )
        source_revisions.append(revision.stdout.strip())
        source_content_digests.append("sha256:" + hashlib.sha256(path.read_bytes()).hexdigest())
    rows = {}
    for key, source_value_digests in policy["delta_overlay"].items():
        selected_value_digest = source_value_digests[0]
        rows[key] = {
            "source_artifact_ids": source_ids,
            "source_revisions": source_revisions,
            "source_content_digests": source_content_digests,
            "source_value_digests": source_value_digests,
            "selection": "ledger",
            "selected_value_digest": selected_value_digest,
            "candidate_row_digest": requirement_engine._digest(
                {
                    "row_key": key,
                    "selection": "ledger",
                    "selected_value_digest": selected_value_digest,
                    "disposition": "retain",
                }
            ),
            "disposition": "retain",
            "rationale": "PO classified fixture",
            "owner_subject_id": "REQ-AUTHORITY-NORMALIZATION",
            "source_refs": [],
            "prohibited_inheritance": [],
            "downstream_trace_impact": "redescent required",
            "resume_conditions": [],
        }
    classified_disposition = policy["delta_overlay_dispositions"]
    classified_disposition.update(
        {
            "status": "classified_pending_cutover",
            "selected_rows": rows,
            "cutover_blocked": True,
            "classification_approval": {
                "authority": "PO",
                "approver_principal": "po",
                "req_subset_meaning_digest": policy["existing_req_subset_meaning_digest"],
                "delta_overlay_digest": requirement_engine._digest(policy["delta_overlay"]),
                "selected_rows_digest": requirement_engine._digest(rows),
                "approved_at": "2026-08-16T00:00:00Z",
            },
        }
    )
    candidate_path = tmp_path / "req-authority-normalization-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "normalization_row_digests": {
                    key: row["candidate_row_digest"]
                    for key, row in rows.items()
                    if row["candidate_row_digest"] is not None
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_id = "AUTH-DEVELOPMENT-REQ-AUTHORITY-NORMALIZATION-CANDIDATE"
    augmented_manifest = copy.deepcopy(manifest)
    augmented_manifest["items"].append(
        {
            "artifact_id": candidate_id,
            "layer": "00-authority",
            "artifact_type": "requirement-normalization-candidate",
            "authority_format": "json",
            "authority_status": "active",
            "implementation_input": False,
            "canonical_path": str(candidate_path),
        }
    )
    original_load = requirement_engine.load

    def load_with_candidate(path: Path) -> dict[str, object]:
        return augmented_manifest if path == requirement_engine.MANIFEST else original_load(path)

    monkeypatch.setattr(requirement_engine, "load", load_with_candidate)
    classified_disposition["candidate_artifact_binding"] = {
        "artifact_id": candidate_id,
        "content_digest": "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    }
    healthy_faults = requirement_engine.req_authority_normalization_policy_faults(Ctx(), classified)
    assert healthy_faults == []

    early_ratified = copy.deepcopy(classified)
    early_ratified["req_authority_normalization_policy"]["status"] = "ratified"
    assert any(
        "stageとpolicy status" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(Ctx(), early_ratified)
    )

    swapped_candidate = copy.deepcopy(classified)
    swapped_candidate["req_authority_normalization_policy"]["delta_overlay_dispositions"][
        "candidate_artifact_binding"
    ]["artifact_id"] = "AUTH-DEVELOPMENT-REQUIREMENT-REFINEMENTS"
    assert any(
        "pending candidate" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(
            Ctx(), swapped_candidate
        )
    )

    complete_candidate_swap = copy.deepcopy(classified)
    complete_policy = complete_candidate_swap["req_authority_normalization_policy"]
    complete_policy["status"] = "ratified"
    complete_disposition = complete_policy["delta_overlay_dispositions"]
    complete_disposition["status"] = "cutover_complete"
    complete_disposition["candidate_artifact_binding"]["artifact_id"] = (
        "AUTH-DEVELOPMENT-REQUIREMENT-REFINEMENTS"
    )
    assert any(
        "cutover complete candidateの専用identity" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(
            Ctx(), complete_candidate_swap
        )
    )

    reversed_selection = copy.deepcopy(classified)
    reversed_selection["req_authority_normalization_policy"]["delta_overlay_dispositions"][
        "selected_rows"
    ]["REQ-001/source_refs"]["disposition"] = "obsolete"
    assert any(
        "selectionとdisposition" in fault
        for fault in requirement_engine.req_authority_normalization_policy_faults(
            Ctx(), reversed_selection
        )
    )
    assert requirement_engine.refinement_coverage_faults(refinements, discovery) == []
    open_faults = requirement_engine.open_refinement_faults(refinements)
    assert any("VPS-UI-PRIMARY-HUMAN-INTERFACE: lifecycle=specified" in fault for fault in open_faults)
    assert any("VPS-UI-QUALITY-ATTRIBUTES: lifecycle=draft" in fault for fault in open_faults)
    assert any("MEDIA-POC-SCRUM-RELEASE: pending_resolution=1" in fault for fault in open_faults)
    assert any("AGENT-NEO-HELIX-REDEFINITION: lifecycle=draft" in fault for fault in open_faults)
    assert any("PO approval receiptがない" in fault for fault in open_faults)
    assert not any("AUTO-MODE-DECISION-AUTHORITY" in fault for fault in open_faults)
    assert not any("DISCORD-MULTI-PURPOSE-BOUNDARIES" in fault for fault in open_faults)


def test_nfr_business_authority_policy_keeps_unclassified_rows_fail_closed() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.nfr_business_authority_policy_faults(Ctx(), refinements) == []

    stale_parent = copy.deepcopy(refinements)
    stale_parent["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "parent_semantic_digest"
    ] = "sha256:" + "0" * 64
    assert any(
        "parent meaning digest" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), stale_parent)
    )

    early_ratified = copy.deepcopy(refinements)
    early_ratified["nfr_business_authority_policy"]["status"] = "ratified"
    assert any(
        "早期ratified" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), early_ratified)
    )

    leaked_phase = copy.deepcopy(refinements)
    leaked_phase["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "lifecycle_phase"
    ] = "S0"
    assert any(
        "未決境界" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), leaked_phase)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["nfr_business_authority_policy"]
    for row in policy["authority_rows"].values():
        row.update(
            {
                "stable_root_subject_id": "REQ-040",
                "actor_or_principal_scope": {
                    "principal_subject_id": "NFR-BUSINESS-AUTHORITY",
                    "scope_ids": ["profile:*"],
                },
                "applicability_scope": {
                    "profile_ids": ["profile:*"],
                    "operation_ids": [],
                    "risk_classes": [],
                },
                "lifecycle_phase": "initial",
                "disposition": "retain",
                "resume_conditions": [],
                "evidence_or_measurement_authority": {
                    "authority_subject_id": "NFR-BUSINESS-AUTHORITY",
                    "registration_required": True,
                    "quality_dimensions": ["availability"],
                },
                "disposition_rationale": "PO classified fixture",
            }
        )
    state = policy["classification_state"]
    state.update(
        {
            "status": "classified_pending_cutover",
            "cutover_blocked": True,
            "classification_approval": {
                "authority": "PO",
                "approver_principal": "po",
                "parent_inventory_digest": classified[
                    "legacy_strategy_quality_meaning_inventory"
                ]["meaning_migrations_digest"],
                "authority_rows_digest": requirement_engine._digest(policy["authority_rows"]),
                "approved_at": "2026-08-16T00:00:00Z",
            },
        }
    )
    assert requirement_engine.nfr_business_authority_policy_faults(Ctx(), classified) == []

    unknown_root = copy.deepcopy(classified)
    unknown_root["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "stable_root_subject_id"
    ] = "UNKNOWN"
    assert any(
        "未知BR/REQ" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), unknown_root)
    )

    classified_s0 = copy.deepcopy(classified)
    classified_s0["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "lifecycle_phase"
    ] = "S0"
    assert any(
        "旧slice" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), classified_s0)
    )

    stale_receipt = copy.deepcopy(classified)
    stale_receipt["nfr_business_authority_policy"]["classification_state"][
        "classification_approval"
    ]["authority_rows_digest"] = "sha256:" + "0" * 64
    assert any(
        "PO row-set receipt" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), stale_receipt)
    )

    unknown_quality = copy.deepcopy(classified)
    unknown_quality["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "evidence_or_measurement_authority"
    ]["quality_dimensions"] = ["UNKNOWN"]
    assert any(
        "measurement authority型" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), unknown_quality)
    )

    object_rationale = copy.deepcopy(classified)
    object_rationale["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "disposition_rationale"
    ] = {"not": "text"}
    assert any(
        "rationaleが非空文字列" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), object_rationale)
    )

    unhashable_scope = copy.deepcopy(classified)
    unhashable_scope["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "actor_or_principal_scope"
    ]["scope_ids"] = [{}]
    assert any(
        "actor/principal scope型" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(Ctx(), unhashable_scope)
    )

    invalid_scope_prefix = copy.deepcopy(classified)
    invalid_scope_prefix["nfr_business_authority_policy"]["authority_rows"]["NFR-9"][
        "actor_or_principal_scope"
    ]["scope_ids"] = ["junk"]
    assert any(
        "actor/principal scope型" in fault
        for fault in requirement_engine.nfr_business_authority_policy_faults(
            Ctx(), invalid_scope_prefix
        )
    )


def test_refinement_routing_rejects_unknown_supersession_and_overlapping_work() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))

    unknown_replacement = copy.deepcopy(refinements)
    discord = next(
        record
        for record in unknown_replacement["records"]
        if record["subject_id"] == "DISCORD-MULTI-PURPOSE-BOUNDARIES"
    )
    discord["superseded_by_subject_ids"] = ["UNKNOWN-SUBJECT"]
    faults = requirement_engine.refinement_faults(unknown_replacement, discovery)
    assert any("superseded置換先が未知" in fault for fault in faults)

    overlapping = copy.deepcopy(refinements)
    route = next(
        record for record in overlapping["records"] if record["subject_id"] == "GENAI-EXECUTION-ROUTE"
    )
    shared = route["registration_bindings"][0]
    route["design_later"].append(shared)
    faults = requirement_engine.refinement_faults(overlapping, discovery)
    assert any("registrationとdesign-laterが重複" in fault for fault in faults)


def test_implementation_obligations_block_admission_until_receipt_and_design_trace_exist() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    faults = requirement_engine.implementation_obligation_faults(refinements, set())
    assert any("implementation obligation未充足" in fault for fault in faults)
    assert requirement_engine.implementation_obligation_faults(refinements, require_complete=False) == []

    mutated = copy.deepcopy(refinements)
    mutated["implementation_obligation_fulfillments"] = [
        {
            "obligation_id": "OBL-0000000000000000",
            "kind": "design",
            "subject_id": "UNKNOWN",
            "status": "fulfilled",
            "target_refs": ["UNKNOWN-ARTIFACT"],
            "receipt_digest": "sha256:" + "0" * 64,
            "evidence_digest": "sha256:" + "1" * 64,
            "review_digest": "sha256:" + "2" * 64,
        }
    ]
    faults = requirement_engine.implementation_obligation_faults(mutated, set())
    assert any("未知又はstale obligation" in fault for fault in faults)


def test_obligation_target_requires_exact_json_pointer_or_clause_marker(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        '{"rows":{"REG-1":{"status":"ready","obligation_ids":["OBL-1111111111111111"]}}}',
        encoding="utf-8",
    )
    assert requirement_engine._obligation_target_digest(registry, "/rows/REG-1") is not None
    assert (
        requirement_engine._obligation_target_digest(registry, "/rows/REG-1", "OBL-1111111111111111")
        is not None
    )
    assert (
        requirement_engine._obligation_target_digest(registry, "/rows/REG-1", "OBL-2222222222222222") is None
    )
    assert requirement_engine._obligation_target_digest(registry, "/status") is None

    design = tmp_path / "design.md"
    design.write_text(
        "<!-- clause-id: CL-SESSION-RECOVERY -->\n"
        "<!-- obligation-ids: OBL-1111111111111111 -->\n"
        "具体的な復旧契約\n",
        encoding="utf-8",
    )
    assert requirement_engine._obligation_target_digest(design, "CL-SESSION-RECOVERY") is not None
    assert (
        requirement_engine._obligation_target_digest(design, "CL-SESSION-RECOVERY", "OBL-1111111111111111")
        is not None
    )
    assert (
        requirement_engine._obligation_target_digest(design, "CL-SESSION-RECOVERY", "OBL-2222222222222222")
        is None
    )
    assert requirement_engine._obligation_target_digest(design, "status") is None


def test_delivery_admission_keeps_full_v_and_release_boundaries() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    records = {record["subject_id"]: record for record in refinements["records"]}
    assert records["WORDPRESS-CONTENT-OPERATIONS-RELEASE"]["delivery_admission"]["sequence"] == 1
    assert records["WORDPRESS-CONTENT-OPERATIONS-RELEASE"]["delivery_admission"]["program_stage"] == 1
    assert records["WORDPRESS-PLATFORM-MAINTENANCE-RELEASE"]["delivery_admission"]["sequence"] == 2
    assert records["WORDPRESS-PLATFORM-MAINTENANCE-RELEASE"]["delivery_admission"]["program_stage"] == 1
    assert records["WORDPRESS-SECURITY-MAINTENANCE-RELEASE"]["delivery_admission"]["sequence"] == 2
    assert records["WORDPRESS-SECURITY-MAINTENANCE-RELEASE"]["delivery_admission"]["program_stage"] == 1
    assert records["AGENT-NEO-SITE-BUILD-RELEASE"]["delivery_admission"]["sequence"] == 3
    assert records["AGENT-NEO-SITE-BUILD-RELEASE"]["delivery_admission"]["program_stage"] == 2
    assert records["AGENT-NEO-PRODUCT-EVOLUTION-RELEASE"]["delivery_admission"]["sequence"] == 4
    assert records["AGENT-NEO-PRODUCT-EVOLUTION-RELEASE"]["delivery_admission"]["program_stage"] == 3

    mutated = copy.deepcopy(refinements)
    security = next(
        record
        for record in mutated["records"]
        if record["subject_id"] == "WORDPRESS-SECURITY-MAINTENANCE-RELEASE"
    )
    security["delivery_admission"]["standard_model"] = "discovery_scrum"
    security["delivery_admission"]["predecessor_subject_ids"] = ["WORDPRESS-PLATFORM-MAINTENANCE-RELEASE"]
    faults = requirement_engine.refinement_faults(mutated, discovery)
    assert any("Full V L1-L12が標準工程でない" in fault for fault in faults)
    assert any("predecessor release不一致" in fault for fault in faults)


def test_mutation_refinement_without_candidate_is_rejected() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    refinements["records"][0]["subject_id"] = "UNKNOWN-SUBJECT"
    faults = requirement_engine.refinement_coverage_faults(refinements, discovery)
    assert any("candidate_recordedのない" in fault for fault in faults)


def test_mutation_refinement_requires_three_polarities_and_digests() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    refinements = {
        "schema_version": "marketing-harness-requirements-refinement.v1",
        "authority": "canonical",
        "records": [
            {
                "refinement_id": "RRF-FR-16-NOTIFICATION-BOUNDARY",
                "subject_id": "FR-16-NOTIFICATION-BOUNDARY",
                "revision": 1,
                "lifecycle_status": "specified",
                "source_event_ids": ["RDE-000002"],
                "source_set_digest": "sha256:" + "0" * 64,
                "semantic_dimensions": {},
                "acceptance_cases": [],
                "pending_resolution": ["unresolved"],
                "semantic_digest": "sha256:" + "0" * 64,
                "approval": None,
            }
        ],
    }
    faults = requirement_engine.refinement_faults(refinements, discovery)
    assert any("source_set_digest" in fault for fault in faults)
    assert any("semantic dimensions" in fault for fault in faults)
    assert any("positive/negative/boundary" in fault for fault in faults)
    assert any("pending_resolution" in fault for fault in faults)


def test_mutation_refinement_non_po_receipt_is_rejected() -> None:
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    source = [next(event for event in discovery["events"] if event["event_id"] == "RDE-000002")]
    record = {
        "refinement_id": "RRF-FR-16-NOTIFICATION-BOUNDARY",
        "subject_id": "FR-16-NOTIFICATION-BOUNDARY",
        "revision": 1,
        "lifecycle_status": "approved",
        "source_event_ids": ["RDE-000002"],
        "source_set_digest": requirement_engine._digest(source),
        "semantic_dimensions": {
            "actors": ["kernel"],
            "beneficiaries": ["PO"],
            "value": "安全停止",
            "tasks": ["停止"],
            "workflow": ["異常→停止"],
            "scope_in": ["停止"],
            "scope_out": ["外部通知"],
            "prohibitions": ["誤承認禁止"],
            "human_judgement": ["再開はPO"],
            "side_effects": ["状態変更"],
            "evidence": ["遷移証跡"],
            "phase": "S0",
        },
        "acceptance_cases": [
            {
                "acceptance_id": f"RAC-FR-16-{suffix}",
                "polarity": polarity,
                "statement": polarity,
                "system_test_id": f"RST-FR-16-{suffix}",
            }
            for suffix, polarity in (("P", "positive"), ("N", "negative"), ("B", "boundary"))
        ],
        "pending_resolution": [],
        "approval": None,
    }
    semantic = {key: value for key, value in record.items() if key not in {"semantic_digest", "approval"}}
    record["semantic_digest"] = requirement_engine._digest(semantic)
    record["approval"] = {
        "authority": "PO",
        "approver_principal": "codex-terra",
        "subject_digest": record["semantic_digest"],
        "source_set_digest": record["source_set_digest"],
        "decision_receipt_digest": "sha256:" + "1" * 64,
        "approved_revision": 1,
        "approved_at": "2026-08-14T00:00:00Z",
    }
    faults = requirement_engine.refinement_faults(
        {
            "schema_version": "marketing-harness-requirements-refinement.v1",
            "authority": "canonical",
            "records": [record],
        },
        discovery,
    )
    assert any("信頼済みPO" in fault for fault in faults)


def test_semantic_faults_block_active_approval_request() -> None:
    data = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    data["events"] = [event for event in data["events"] if event.get("event_id") != "RDE-000065"]
    faults = requirement_engine.approval_admission_faults(Ctx(), data)
    assert faults and "FR-16-NOTIFICATION-BOUNDARY" in faults[0]


def test_confirmed_req_view_and_machine_ledger_semantic_drift_is_detected() -> None:
    faults = requirement_engine.req_compatibility_drift_faults(Ctx())
    assert any("REQ-001: REQ source_refs semantic drift" in fault for fault in faults)
    assert any("REQ-008: REQ related semantic drift" in fault for fault in faults)
    assert any("REQ-053: REQ text semantic drift" in fault for fault in faults)


def test_mutation_cutover_is_rejected_while_semantics_are_open() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    discovery = json.loads(requirement_engine.requirement_discovery.LEDGER.read_text(encoding="utf-8"))
    policy["requirements_baseline_status"] = "approved"
    policy["implementation_authorized"] = True
    faults = requirement_engine.authority_cutover_faults(Ctx(), policy, refinements, discovery)
    assert any("semantic closure" in fault for fault in faults)
    assert any("active refinement" in fault for fault in faults)


def test_current_obsolete_wsl_and_discord_routes_are_detected() -> None:
    faults = requirement_engine.obsolete_runtime_route_faults()
    assert any("ddl.sql" in fault and "discord" in fault for fault in faults)
    assert any("tech-stack_v0.1.md" in fault and "cron（WSL）" in fault for fault in faults)


def test_semantic_closure_includes_obsolete_runtime_routes() -> None:
    faults = requirement_engine.semantic_closure_faults(Ctx())
    assert any("旧runtime route" in fault for fault in faults)


def test_current_wordpress_operation_and_maintenance_are_mixed() -> None:
    faults = requirement_engine.wordpress_responsibility_boundary_faults()
    assert any("MR-WP-1" in fault and "同一actions" in fault for fault in faults)
    assert any("MR-WP-1" in fault and "同一connection" in fault for fault in faults)


def test_semantic_closure_includes_wordpress_boundary() -> None:
    assert any(
        "content operationとmaintenance" in fault
        for fault in requirement_engine.semantic_closure_faults(Ctx())
    )


def test_current_approval_and_operational_notifications_are_mixed() -> None:
    faults = requirement_engine.notification_purpose_boundary_faults(Ctx())
    assert any(fault.startswith("FR-16:") and "FR-46" in fault for fault in faults)
    assert any(fault.startswith("FR-43:") and "FR-46" in fault for fault in faults)
    assert any(fault.startswith("FR-76:") and "承認transport" in fault for fault in faults)


def test_semantic_closure_includes_notification_purpose_boundary() -> None:
    assert any("投稿可否承認FR-46" in fault for fault in requirement_engine.semantic_closure_faults(Ctx()))


def test_current_media_route_semantic_conflicts_are_detected() -> None:
    faults = requirement_engine.media_route_semantic_faults()
    assert any(fault.startswith("LINE:") for fault in faults)
    assert any(fault.startswith("GENAI:") for fault in faults)
    assert any(fault.startswith("X:") for fault in faults)
    assert any(fault.startswith("PLAY:") for fault in faults)


def test_semantic_closure_includes_media_route_conflicts() -> None:
    assert any("consumer Web UI" in fault for fault in requirement_engine.semantic_closure_faults(Ctx()))


def test_current_connector_priority_conflicts_are_detected() -> None:
    faults = requirement_engine.connector_priority_semantic_faults()
    assert any("ADR-006" in fault for fault in faults)
    assert any("FR-41" in fault and "L4/L5" in fault for fault in faults)


def test_current_l2_prototype_semantic_gaps_are_detected() -> None:
    faults = requirement_engine.l2_revalidation_semantic_faults(Ctx())
    assert any("notification class" in fault for fault in faults)
    assert any("return/差戻し" in fault for fault in faults)
    assert any("FR-78" in fault for fault in faults)
    assert any("subscription" in fault for fault in faults)
    assert any("全ブランドBI" in fault for fault in faults)


def test_current_vps_credential_contract_conflicts_are_detected() -> None:
    faults = requirement_engine.vps_credential_boundary_faults()
    assert any("S0暗号化store" in fault for fault in faults)
    assert any("external-if" in fault for fault in faults)


def test_current_media_requirements_lack_admission_boundaries() -> None:
    faults = requirement_engine.media_requirement_admission_faults()
    assert any(fault.startswith("MR-WP-1: capability_status") for fault in faults)
    assert any(fault.startswith("MR-LINE-1: execution_mode") for fault in faults)
    assert any(fault.startswith("MR-GENAI-1: principal") for fault in faults)
    assert any(fault.startswith("MR-X-1: effect") for fault in faults)
    assert any("downstream AC/TC/contract" in fault for fault in faults)


def test_legacy_media_inventory_defaults_all_old_mr_to_deferred() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_media_inventory_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    route = next(
        record for record in mutated["records"] if record["subject_id"] == "LEGACY-MEDIA-ADMISSION-INVENTORY"
    )
    route["legacy_media_admission"]["covered_legacy_mr_ids"].pop()
    route["legacy_media_admission"]["default_status"] = "enabled"
    faults = requirement_engine.legacy_media_inventory_faults(mutated)
    assert any("旧MR全54件" in fault for fault in faults)
    assert any("defaultがdeferredでない" in fault for fault in faults)


def test_normative_consumers_do_not_reference_legacy_requirement_view() -> None:
    assert requirement_engine.legacy_requirement_consumer_faults() == []


def test_l2_through_l6_remain_non_implementation_inputs_until_requirement_freeze() -> None:
    ctx = Ctx()
    assert requirement_engine.design_not_started_faults(ctx) == []
    mutated = copy.deepcopy(ctx.manifest_items)
    l2 = next(item for item in mutated if str(item.get("canonical_path", "")).startswith("docs/L2-"))
    l2["lifecycle_status"] = "confirmed"
    l2["implementation_input"] = True
    mutated_ctx = Ctx()
    mutated_ctx.__dict__["manifest_items"] = mutated
    faults = requirement_engine.design_not_started_faults(mutated_ctx)
    assert any("implementation_input=true" in fault for fault in faults)
    assert any("旧L2がdraftでない" in fault for fault in faults)


def test_all_legacy_requirement_ids_have_typed_redescent_decision_routes() -> None:
    projection = requirement_engine.semantic_projection(Ctx())
    assert requirement_engine.projection_faults(projection) == []
    items = projection["revalidation_inventory"]["items"]
    assert len(items) == 864
    expected_dimensions = {
        "actors",
        "beneficiaries",
        "value",
        "tasks",
        "workflow",
        "scope_in",
        "scope_out",
        "prohibitions",
        "human_judgement",
        "side_effects",
        "evidence",
        "phase",
    }
    assert all(set(item["required_semantic_dimensions"]) == expected_dimensions for item in items)
    assert all(item["decision_subject_ids"] for item in items)
    assert all(set(item["allowed_dispositions"]) == {"redescent", "deferred", "superseded"} for item in items)
    assert all(item["scope_assignment"] == "legacy_revalidation_only" for item in items)
    mutated = copy.deepcopy(projection)
    mutated["revalidation_inventory"]["items"][0]["decision_subject_ids"] = ["UNKNOWN-SUBJECT"]
    mutated["revalidation_inventory"]["digest"] = requirement_engine._digest(
        mutated["revalidation_inventory"]["items"]
    )
    mutated["root_digest"] = requirement_engine._digest(
        {
            "shards": mutated["shards"],
            "records": mutated["records"],
            "revalidation_inventory": mutated["revalidation_inventory"],
        }
    )
    assert any(
        "実在refinement subjectへ未束縛" in fault for fault in requirement_engine.projection_faults(mutated)
    )


def test_refinement_scope_assignments_separate_initial_and_deferred_candidates() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.scope_assignment_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["scope_assignments"]["GENAI-EXECUTION-ROUTE"] = "initial_candidate"
    assert any(
        "生成AI/旧媒体" in fault for fault in requirement_engine.scope_assignment_faults(mutated)
    )
    historical_reversal = copy.deepcopy(refinements)
    historical_reversal["scope_assignments"]["AUTO-MODE-DECISION-AUTHORITY"] = "deferred_candidate"
    assert any(
        "historical-only" in fault
        for fault in requirement_engine.scope_assignment_faults(historical_reversal)
    )
    replacement_reversal = copy.deepcopy(refinements)
    old_auto = next(
        record
        for record in replacement_reversal["records"]
        if record["subject_id"] == "AUTO-MODE-DECISION-AUTHORITY"
    )
    old_auto["superseded_by_subject_ids"] = ["GENAI-EXECUTION-ROUTE"]
    assert any(
        "supersession先" in fault
        for fault in requirement_engine.scope_assignment_faults(replacement_reversal)
    )


def test_decision_packets_cover_each_subject_once_without_bulk_approval() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.decision_packet_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["decision_packets"][0]["subject_ids"].append(mutated["decision_packets"][1]["subject_ids"][0])
    mutated["decision_packets"][0]["bulk_decision_forbidden"] = False
    mutated["decision_response_contract"]["unanswered_default"] = "approve_as_written"
    mutated["records"][0]["lifecycle_status"] = "draft"
    pending_record = next(record for record in mutated["records"] if record["pending_resolution"])
    mutated["records"][1]["pending_resolution"].append(pending_record["pending_resolution"][0])
    mutated["question_classifications"].pop(next(iter(mutated["question_classifications"])))
    mutated["decision_class_contracts"].pop("quality_target")
    mutated["captured_po_decisions"][0]["design_not_started"] = False
    mutated["captured_po_decisions"][0]["required_new_subject_ids"].append("UNMATERIALIZED-SUBJECT")
    browser_record = next(
        record for record in mutated["records"] if record["subject_id"] == "EXTERNAL-BROWSER-AUTOMATION-ROUTE"
    )
    browser_record["semantic_dimensions"] = json.loads(
        json.dumps(browser_record["semantic_dimensions"], ensure_ascii=False).replace("Playwright", "browser")
    )
    faults = requirement_engine.decision_packet_faults(mutated)
    assert any("exactly once" in fault for fault in faults)
    assert any("一括承認禁止" in fault for fault in faults)
    assert any("unanswered_default" in fault for fault in faults)
    assert any("PO質問がない" in fault for fault in faults)
    assert any("複数subject" in fault for fault in faults)
    assert any("decision class" in fault for fault in faults)
    assert any("回答契約" in fault for fault in faults)
    assert any("未承認・未設計境界" in fault for fault in faults)
    assert any("refinementへ未materialize" in fault for fault in faults)
    assert any("意味materialization" in fault for fault in faults)

    scope_default_reversal = copy.deepcopy(refinements)
    content = next(
        record
        for record in scope_default_reversal["records"]
        if record["subject_id"] == "CONTENT-QUALITY-GATE-LEARNING"
    )
    content["semantic_dimensions"]["tasks"].remove(
        "明示scopeがないfeedbackはsource feedbackのmedia_account_idを既定scopeとして導出する"
    )
    assert any(
        "意味materializationが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(scope_default_reversal)
    )

    no_action_reversal = copy.deepcopy(refinements)
    content = next(
        record
        for record in no_action_reversal["records"]
        if record["subject_id"] == "CONTENT-QUALITY-GATE-LEARNING"
    )
    content["acceptance_cases"][2]["statement"] = content["acceptance_cases"][2]["statement"].replace(
        "通知を含め何もしない", "更新不能を通知する"
    )
    assert any(
        "意味materializationが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(no_action_reversal)
    )

    retry_exhaustion_notification_reversal = copy.deepcopy(refinements)
    content = next(
        record
        for record in retry_exhaustion_notification_reversal["records"]
        if record["subject_id"] == "CONTENT-QUALITY-GATE-LEARNING"
    )
    content["semantic_dimensions"]["tasks"].remove(
        "retry budgetを使い切ってblockedになった場合だけVPS UI内inboxへ通知eventを記録する"
    )
    assert any(
        "POD-20260815-009/CONTENT-QUALITY-GATE-LEARNING" in fault
        and "意味materializationが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(retry_exhaustion_notification_reversal)
    )

    inbox_retry_notification_reversal = copy.deepcopy(refinements)
    inbox = next(
        record
        for record in inbox_retry_notification_reversal["records"]
        if record["subject_id"] == "VPS-UI-INBOX-LIFECYCLE"
    )
    inbox["semantic_dimensions"]["prohibitions"].remove("通常のcontent quality retryをinbox itemにする")
    assert any(
        "POD-20260815-009/VPS-UI-INBOX-LIFECYCLE" in fault and "PO回答projectionが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(inbox_retry_notification_reversal)
    )

    inbox_auto_expiry_reversal = copy.deepcopy(refinements)
    inbox = next(
        record
        for record in inbox_auto_expiry_reversal["records"]
        if record["subject_id"] == "VPS-UI-INBOX-LIFECYCLE"
    )
    inbox["semantic_dimensions"]["prohibitions"].remove(
        "未確認、時間経過、stale表示又は記録失敗だけでaction_requiredをexpiredにする"
    )
    assert any(
        "VPS-UI-INBOX-LIFECYCLE: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(inbox_auto_expiry_reversal)
    )

    inbox_resolver_reminder_reversal = copy.deepcopy(refinements)
    inbox = next(
        record
        for record in inbox_resolver_reminder_reversal["records"]
        if record["subject_id"] == "VPS-UI-INBOX-LIFECYCLE"
    )
    inbox["semantic_dimensions"]["prohibitions"].remove("reminder/escalationで別itemを量産する")
    assert any(
        "VPS-UI-INBOX-LIFECYCLE: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(inbox_resolver_reminder_reversal)
    )

    semantic_coverage_na_reversal = copy.deepcopy(refinements)
    semantic_coverage_na_reversal["semantic_coverage_policy"]["not_applicable_contract"] = ["該当なし"]
    assert any(
        "semantic coverage resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(semantic_coverage_na_reversal)
    )

    semantic_coverage_record_reversal = copy.deepcopy(refinements)
    semantic_coverage = next(
        record
        for record in semantic_coverage_record_reversal["records"]
        if record["subject_id"] == "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2"
    )
    semantic_coverage["semantic_dimensions"]["prohibitions"].remove("core意味軸へnot_applicableを使う")
    assert any(
        "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(semantic_coverage_record_reversal)
    )

    semantic_descent_union_reversal = copy.deepcopy(refinements)
    semantic_descent_union_reversal["contract_semantic_descent_policy"]["multi_parent_contract"].remove(
        "implicit_union_prohibited"
    )
    assert any(
        "contract semantic descent resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(semantic_descent_union_reversal)
    )

    semantic_descent_record_reversal = copy.deepcopy(refinements)
    descent = next(
        record
        for record in semantic_descent_record_reversal["records"]
        if record["subject_id"] == "CONTRACT-SEMANTIC-DESCENT-V2"
    )
    descent["semantic_dimensions"]["prohibitions"].remove(
        "safety/prohibition/human judgementを子で削除又は弱化する"
    )
    assert any(
        "CONTRACT-SEMANTIC-DESCENT-V2: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(semantic_descent_record_reversal)
    )

    quota_effect_reversal = copy.deepcopy(refinements)
    quota_effect_reversal["rate_quota_cost_policy"]["blocked_effects_when_unknown"].remove("money")
    assert any(
        "rate/quota/cost resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(quota_effect_reversal)
    )

    money_currency_reversal = copy.deepcopy(refinements)
    money_currency_reversal["rate_quota_cost_policy"]["registration_fields"]["money_cost_ceiling"].remove(
        "currency"
    )
    assert any(
        "rate/quota/cost resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(money_currency_reversal)
    )

    nonmoney_currency_reversal = copy.deepcopy(refinements)
    nonmoney_currency_reversal["rate_quota_cost_policy"]["registration_fields"]["retry_budget"].append(
        "currency"
    )
    assert any(
        "rate/quota/cost resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(nonmoney_currency_reversal)
    )

    quota_record_reversal = copy.deepcopy(refinements)
    quota = next(
        record
        for record in quota_record_reversal["records"]
        if record["subject_id"] == "RATE-QUOTA-COST-AUTHORITY"
    )
    quota["semantic_dimensions"]["prohibitions"].remove(
        "limit失敗を理由に既確定blocked/failed/safety-stopped状態をrollbackする"
    )
    assert any(
        "RATE-QUOTA-COST-AUTHORITY: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(quota_record_reversal)
    )

    state_signal_reversal = copy.deepcopy(refinements)
    state_signal_reversal["product_state_authority_policy"]["non_authoritative_signals"].remove(
        "inbox_acknowledged"
    )
    assert any(
        "product state authority resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(state_signal_reversal)
    )

    state_target_reversal = copy.deepcopy(refinements)
    state_target_reversal["product_state_authority_policy"]["transition_binding"].remove("target_state")
    assert any(
        "product state authority resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(state_target_reversal)
    )

    state_failure_revision_reversal = copy.deepcopy(refinements)
    state_failure_revision_reversal["product_state_authority_policy"]["transition_outcomes"].remove(
        "persistence_failure_preserves_current_state_and_revision"
    )
    assert any(
        "product state authority resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(state_failure_revision_reversal)
    )

    state_record_reversal = copy.deepcopy(refinements)
    state_record = next(
        record
        for record in state_record_reversal["records"]
        if record["subject_id"] == "PRODUCT-STATE-AUTHORITY"
    )
    state_record["semantic_dimensions"]["prohibitions"].remove("通知又はretry失敗で既確定状態をrollbackする")
    assert any(
        "PRODUCT-STATE-AUTHORITY: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(state_record_reversal)
    )

    state_acceptance_reversal = copy.deepcopy(refinements)
    state_record = next(
        record
        for record in state_acceptance_reversal["records"]
        if record["subject_id"] == "PRODUCT-STATE-AUTHORITY"
    )
    state_record["acceptance_cases"][0]["statement"] = state_record["acceptance_cases"][0][
        "statement"
    ].replace("expected priorより大きいresulting revision、", "")
    assert any(
        "PRODUCT-STATE-AUTHORITY: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(state_acceptance_reversal)
    )

    profile_auth_reversal = copy.deepcopy(refinements)
    profile_auth_reversal["business_profile_authorization_policy"]["non_implication_rules"].remove(
        "session_does_not_imply_authorization"
    )
    assert any(
        "business profile authorization resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(profile_auth_reversal)
    )

    state_principal_duplication_reversal = copy.deepcopy(refinements)
    state_principal_duplication_reversal["product_state_authority_policy"]["transition_binding"].append(
        "authorized_principal"
    )
    assert any(
        "product state authority resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(state_principal_duplication_reversal)
    )

    state_recovery_principal_reversal = copy.deepcopy(refinements)
    recovery = state_recovery_principal_reversal["product_state_authority_policy"]["recovery_contract"]
    recovery.remove("recovery_authorization_grant_ref")
    recovery.append("recovery_principal_permission")
    assert any(
        "product state authority resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(state_recovery_principal_reversal)
    )

    state_acceptance_principal_reversal = copy.deepcopy(refinements)
    state_record = next(
        record
        for record in state_acceptance_principal_reversal["records"]
        if record["subject_id"] == "PRODUCT-STATE-AUTHORITY"
    )
    state_record["acceptance_cases"][0]["statement"] = state_record["acceptance_cases"][0][
        "statement"
    ].replace("有効なauthorization grant ID/revision/semantic digest", "許可principal")
    assert any(
        "PRODUCT-STATE-AUTHORITY: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(state_acceptance_principal_reversal)
    )

    profile_auth_record_reversal = copy.deepcopy(refinements)
    profile_auth = next(
        record
        for record in profile_auth_record_reversal["records"]
        if record["subject_id"] == "BUSINESS-PROFILE-AUTHORIZATION"
    )
    profile_auth["semantic_dimensions"]["prohibitions"].remove(
        "authentication又はsession成立をauthorizationとみなす"
    )
    assert any(
        "BUSINESS-PROFILE-AUTHORIZATION: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(profile_auth_record_reversal)
    )

    ui_auth_grant_reversal = copy.deepcopy(refinements)
    ui_auth_grant_reversal["vps_ui_authentication_session_policy"]["authorization_separation"].remove(
        "operation_requires_grant_id_revision_and_semantic_digest"
    )
    assert any(
        "VPS UI authentication/session resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_grant_reversal)
    )

    ui_auth_restart_reversal = copy.deepcopy(refinements)
    ui_auth_restart_reversal["vps_ui_authentication_session_policy"]["restart_boundary"].remove(
        "existing_web_session_does_not_reauthorize_runtime_credential"
    )
    assert any(
        "VPS UI authentication/session resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_restart_reversal)
    )

    ui_auth_record_reversal = copy.deepcopy(refinements)
    ui_auth = next(
        record
        for record in ui_auth_record_reversal["records"]
        if record["subject_id"] == "VPS-UI-AUTHENTICATION-SESSION"
    )
    ui_auth["semantic_dimensions"]["prohibitions"].remove(
        "authentication又はsession成立からauthorizationを推論する"
    )
    assert any(
        "VPS-UI-AUTHENTICATION-SESSION: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_record_reversal)
    )

    ui_auth_all_storage_reversal = copy.deepcopy(refinements)
    ui_auth = next(
        record
        for record in ui_auth_all_storage_reversal["records"]
        if record["subject_id"] == "VPS-UI-AUTHENTICATION-SESSION"
    )
    negative = next(case for case in ui_auth["acceptance_cases"] if case["polarity"] == "negative")
    negative["statement"] = negative["statement"].replace(
        "のrepo・製品DB・log・inboxへの永続化又は露出", "の保存"
    )
    assert any(
        "VPS-UI-AUTHENTICATION-SESSION: resolver候補の意味が反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_all_storage_reversal)
    )

    ui_auth_raw_reversal = copy.deepcopy(refinements)
    ui_auth_raw_reversal["vps_ui_authentication_session_policy"]["secret_boundaries"][0] = "no_secret_in_repo"
    assert any(
        "VPS UI authentication/session resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_raw_reversal)
    )

    ui_auth_product_db_reversal = copy.deepcopy(refinements)
    ui_auth_product_db_reversal["vps_ui_authentication_session_policy"]["secret_boundaries"].remove(
        "no_raw_secret_or_bearer_token_in_product_db"
    )
    assert any(
        "VPS UI authentication/session resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_product_db_reversal)
    )

    ui_auth_event_digest_reversal = copy.deepcopy(refinements)
    ui_auth_event_digest_reversal["vps_ui_authentication_session_policy"][
        "credential_material_handling"
    ].remove("authentication_event_digest_uses_secret_free_canonical_projection")
    assert any(
        "VPS UI authentication/session resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_auth_event_digest_reversal)
    )

    ui_quality_generic_na = copy.deepcopy(refinements)
    ui_quality_generic_na["vps_ui_quality_attributes_policy"]["not_applicable_contract"] = ["not_applicable"]
    assert any(
        "VPS UI quality attributes resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_generic_na)
    )

    ui_quality_partial_pass = copy.deepcopy(refinements)
    ui_quality_partial_pass["vps_ui_quality_attributes_policy"]["non_implication_rules"].remove(
        "partial_pass_does_not_imply_overall_pass"
    )
    assert any(
        "VPS UI quality attributes resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_partial_pass)
    )

    ui_quality_threshold_reversal = copy.deepcopy(refinements)
    ui_quality_threshold_reversal["vps_ui_quality_attributes_policy"]["attribute_binding"].remove(
        "threshold_registration_digest"
    )
    assert any(
        "VPS UI quality attributes resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_threshold_reversal)
    )

    ui_quality_fake_na_threshold = copy.deepcopy(refinements)
    ui_quality_fake_na_threshold["vps_ui_quality_attributes_policy"]["applicability_field_contracts"][
        "not_applicable"
    ]["prohibited"].remove("threshold_registration_digest")
    assert any(
        "VPS UI quality attributes resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_fake_na_threshold)
    )

    ui_quality_deferred_owner = copy.deepcopy(refinements)
    ui_quality_deferred_owner["vps_ui_quality_attributes_policy"]["applicability_field_contracts"][
        "deferred"
    ]["required"].remove("defer_owner_subject_id")
    assert any(
        "VPS UI quality attributes resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_deferred_owner)
    )

    ui_quality_partition_gap = copy.deepcopy(refinements)
    ui_quality_partition_gap["vps_ui_quality_attributes_policy"]["applicability_field_contracts"]["deferred"][
        "prohibited"
    ].remove("metric")
    assert any(
        "VPS UI quality deferred: field partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_partition_gap)
    )

    ui_quality_partition_overlap = copy.deepcopy(refinements)
    ui_quality_partition_overlap["vps_ui_quality_attributes_policy"]["applicability_field_contracts"][
        "direct"
    ]["prohibited"].append("metric")
    assert any(
        "VPS UI quality direct: field partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(ui_quality_partition_overlap)
    )

    wp_browser_authority = copy.deepcopy(refinements)
    wp_browser_authority["wordpress_content_operations_policy"]["route_policy"].remove(
        "browser_confirmation_does_not_imply_write_authority"
    )
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_browser_authority)
    )

    wp_unsupported_substitution = copy.deepcopy(refinements)
    wp_unsupported_substitution["wordpress_content_operations_policy"][
        "unsupported_in_place_contract"
    ].remove("no_adjacent_operation_substitution")
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_unsupported_substitution)
    )

    wp_missing_remote_revision = copy.deepcopy(refinements)
    wp_missing_remote_revision["wordpress_content_operations_policy"]["attempt_binding"].remove(
        "current_remote_revision"
    )
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_missing_remote_revision)
    )

    wp_missing_grant_digest = copy.deepcopy(refinements)
    wp_missing_grant_digest["wordpress_content_operations_policy"]["attempt_binding"].remove(
        "authorization_grant_semantic_digest"
    )
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_missing_grant_digest)
    )

    wp_activation_identity = copy.deepcopy(refinements)
    wp_activation_identity["wordpress_content_operations_policy"]["attempt_binding"].remove(
        "activation_decision_or_scope_id"
    )
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_activation_identity)
    )

    wp_activation_digest = copy.deepcopy(refinements)
    wp_activation_digest["wordpress_content_operations_policy"]["attempt_binding"].remove(
        "activation_scope_semantic_digest"
    )
    assert any(
        "WordPress content operations resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_activation_digest)
    )

    wp_security_content_authority = copy.deepcopy(refinements)
    wp_security_content_authority["wordpress_security_maintenance_policy"]["non_authority_signals"].remove(
        "content_grant"
    )
    assert any(
        "WordPress security maintenance resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_content_authority)
    )

    wp_security_backup = copy.deepcopy(refinements)
    wp_security_backup["wordpress_security_maintenance_policy"]["attempt_binding"].remove(
        "backup_restore_evidence_digest"
    )
    assert any(
        "WordPress security maintenance resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_backup)
    )

    wp_security_emergency = copy.deepcopy(refinements)
    wp_security_emergency["wordpress_security_maintenance_policy"]["emergency_contract"].remove(
        "no_automatic_normal_operation_resume"
    )
    assert any(
        "WordPress security maintenance resolver policyが正本とexactly一致しない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_emergency)
    )

    wp_security_assess_fake_rollback = copy.deepcopy(refinements)
    wp_security_assess_fake_rollback["wordpress_security_maintenance_policy"]["operation_group_contracts"][
        "assess"
    ]["prohibited"].remove("rollback")
    assert any(
        "WordPress security assess: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_assess_fake_rollback)
    )

    wp_security_patch_without_backup = copy.deepcopy(refinements)
    patch_contract = wp_security_patch_without_backup["wordpress_security_maintenance_policy"][
        "operation_group_contracts"
    ]["patch_core"]
    patch_contract["required"].remove("backup_restore")
    assert any(
        "WordPress security patch_core: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_patch_without_backup)
    )

    wp_security_rotation_fake_component = copy.deepcopy(refinements)
    rotation_contract = wp_security_rotation_fake_component["wordpress_security_maintenance_policy"][
        "operation_group_contracts"
    ]["credential_rotation"]
    rotation_contract["prohibited"].remove("component_inventory")
    assert any(
        "WordPress security credential_rotation: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_rotation_fake_component)
    )

    wp_security_rotation_without_risk = copy.deepcopy(refinements)
    rotation_contract = wp_security_rotation_without_risk["wordpress_security_maintenance_policy"][
        "operation_group_contracts"
    ]["credential_rotation"]
    rotation_contract["required"].remove("risk_classification")
    assert any(
        "WordPress security credential_rotation: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_rotation_without_risk)
    )

    wp_security_quarantine_fake_advisory = copy.deepcopy(refinements)
    quarantine_contract = wp_security_quarantine_fake_advisory["wordpress_security_maintenance_policy"][
        "operation_group_contracts"
    ]["quarantine"]
    quarantine_contract["prohibited"].remove("advisory_source")
    assert any(
        "WordPress security quarantine: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_security_quarantine_fake_advisory)
    )

    wp_platform_install_fake_revision = copy.deepcopy(refinements)
    install = wp_platform_install_fake_revision["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["install_plugin"]
    install["required"].remove("observed_presence")
    assert any(
        "WordPress platform install_plugin: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_install_fake_revision)
    )

    wp_platform_install_fake_installed_state = copy.deepcopy(refinements)
    install = wp_platform_install_fake_installed_state["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["install_plugin"]
    install["prohibited"].remove("observed_installed_state")
    assert any(
        "WordPress platform install_plugin: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_install_fake_installed_state)
    )

    wp_platform_update_missing_installed_state = copy.deepcopy(refinements)
    update = wp_platform_update_missing_installed_state["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["update_plugin_nonsecurity"]
    update["required"].remove("observed_installed_state")
    assert any(
        "WordPress platform update_plugin_nonsecurity: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_update_missing_installed_state)
    )

    for key, mutate in {
        "install_present": lambda policy: policy["presence_contract"]["install_plugin"].update(
            required_value="present"
        ),
        "update_absent": lambda policy: policy["presence_contract"]["present_required_operations"].remove(
            "update_plugin_nonsecurity"
        ),
        "inspect_absent_installed": lambda policy: policy["presence_contract"]["inspect_inventory"].update(
            absent="installed_state_required"
        ),
        "unknown_execute": lambda policy: policy["presence_contract"].update(unknown_outcome="execute"),
    }.items():
        mutated = copy.deepcopy(refinements)
        mutate(mutated["wordpress_platform_maintenance_policy"])
        assert any(
            "WordPress platform maintenance resolver policyが正本digestと一致しない" in fault
            for fault in requirement_engine.decision_packet_faults(mutated)
        ), key

    wp_platform_inspect_forced_installed = copy.deepcopy(refinements)
    inspect = wp_platform_inspect_forced_installed["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["inspect_inventory"]
    inspect["conditional"].remove("observed_installed_state")
    inspect["required"].append("observed_installed_state")
    assert any(
        "WordPress platform inspect presence cross contractが不正" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_inspect_forced_installed)
    )

    wp_platform_state_missing = copy.deepcopy(refinements)
    state_change = wp_platform_state_missing["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["change_plugin_state"]
    state_change["required"].remove("desired_state")
    assert any(
        "WordPress platform change_plugin_state: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_state_missing)
    )

    wp_platform_config_missing = copy.deepcopy(refinements)
    config_change = wp_platform_config_missing["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["schema_or_config_change"]
    config_change["required"].remove("config_change")
    assert any(
        "WordPress platform schema_or_config_change: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_config_missing)
    )

    wp_platform_rollback_missing = copy.deepcopy(refinements)
    rollback = wp_platform_rollback_missing["wordpress_platform_maintenance_policy"][
        "operation_group_contracts"
    ]["rollback"]
    rollback["required"].remove("rollback_context")
    assert any(
        "WordPress platform rollback: group partitionがexactでない" in fault
        for fault in requirement_engine.decision_packet_faults(wp_platform_rollback_missing)
    )

    paid_phase_reversal = copy.deepcopy(refinements)
    growth = next(
        record
        for record in paid_phase_reversal["records"]
        if record["subject_id"] == "RESEARCH-LED-CONTENT-GROWTH"
    )
    growth["semantic_dimensions"]["scope_out"].remove("初期/中期の有料集客")
    assert any(
        "意味materializationが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(paid_phase_reversal)
    )

    decision_snapshot_reversal = copy.deepcopy(refinements)
    discord_decision = next(
        decision
        for decision in decision_snapshot_reversal["captured_po_decisions"]
        if decision["decision_id"] == "POD-20260815-002"
    )
    discord_decision["statement"] = "Discordを製品通知経路として使用する"
    assert any(
        "captured PO回答snapshotが反転又は欠落" in fault
        for fault in requirement_engine.decision_packet_faults(decision_snapshot_reversal)
    )

    superseded_packet_reversal = copy.deepcopy(refinements)
    packet = next(
        item
        for item in superseded_packet_reversal["decision_packets"]
        if "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2" in item["subject_ids"]
    )
    packet["subject_ids"].append("REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE")
    assert any(
        "全subjectをexactly once" in fault
        for fault in requirement_engine.decision_packet_faults(superseded_packet_reversal)
    )
    old_auto_packet_reversal = copy.deepcopy(refinements)
    old_auto_packet_reversal["decision_packets"][-1]["subject_ids"].append(
        "AUTO-MODE-DECISION-AUTHORITY"
    )
    assert any(
        "全subjectをexactly once" in fault
        for fault in requirement_engine.decision_packet_faults(old_auto_packet_reversal)
    )


def test_candidate_prc_headings_bind_to_real_refinement_subjects() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.candidate_requirement_binding_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["candidate_requirement_bindings"].pop("PRC-01")
    mutated["candidate_requirement_bindings"]["PRC-02"].append("UNKNOWN-SUBJECT")
    faults = requirement_engine.candidate_requirement_binding_faults(mutated)
    assert any("heading" in fault for fault in faults)
    assert any("未知refinement" in fault for fault in faults)
    historical_reversal = copy.deepcopy(refinements)
    historical_reversal["candidate_requirement_bindings"]["PRC-24"].insert(
        0, "AUTO-MODE-DECISION-AUTHORITY"
    )
    historical_faults = requirement_engine.candidate_requirement_binding_faults(historical_reversal)
    assert any("superseded履歴subject" in fault for fault in historical_faults)

    superseded_mutation = copy.deepcopy(refinements)
    superseded_mutation["candidate_requirement_bindings"]["PRC-19"].append(
        "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE"
    )
    faults = requirement_engine.candidate_requirement_binding_faults(superseded_mutation)
    assert any("superseded履歴subject" in fault for fault in faults)

    notification_mutation = copy.deepcopy(refinements)
    notification_mutation["candidate_requirement_bindings"]["PRC-05"] = ["DISCORD-MULTI-PURPOSE-BOUNDARIES"]
    faults = requirement_engine.candidate_requirement_binding_faults(notification_mutation)
    assert any("通知／Discord community" in fault for fault in faults)

    approval_mutation = copy.deepcopy(refinements)
    ui_record = next(
        record
        for record in approval_mutation["records"]
        if record["subject_id"] == "VPS-UI-PRIMARY-HUMAN-INTERFACE"
    )
    ui_record["semantic_dimensions"]["scope_in"].append("投稿承認")
    faults = requirement_engine.candidate_requirement_binding_faults(approval_mutation)
    assert any("旧個別投稿承認" in fault for fault in faults)

    auto_mode_mutation = copy.deepcopy(refinements)
    auto_mode_mutation["candidate_requirement_bindings"]["PRC-06"] = [
        "AUTO-MODE-DECISION-AUTHORITY",
        "CONTRACT-SEMANTIC-DESCENT-V2",
    ]
    faults = requirement_engine.candidate_requirement_binding_faults(auto_mode_mutation)
    assert any("旧auto-mode" in fault for fault in faults)


def test_legacy_l0_clauses_have_explicit_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.l0_clause_disposition_faults(refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_l0_clause_dispositions"] = missing["legacy_l0_clause_dispositions"][1:]
    assert any("clause被覆" in fault for fault in requirement_engine.l0_clause_disposition_faults(missing))

    regressed = copy.deepcopy(refinements)
    discord = next(
        row
        for row in regressed["legacy_l0_clause_dispositions"]
        if row["clause_id"] == "L0V04-DISCORD-APPROVAL"
    )
    discord["disposition"] = "retain"
    assert any("意味移送" in fault for fault in requirement_engine.l0_clause_disposition_faults(regressed))

    undeferred = copy.deepcopy(refinements)
    pwa = next(
        row for row in undeferred["legacy_l0_clause_dispositions"] if row["clause_id"] == "L0V04-PWA-PLAY"
    )
    pwa["resume_conditions"] = []
    assert any(
        "deferred再開条件" in fault for fault in requirement_engine.l0_clause_disposition_faults(undeferred)
    )


def test_l0_north_star_authority_normalization_is_source_bound_and_fail_closed(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.l0_north_star_authority_normalization_policy_faults(refinements) == []

    stale = copy.deepcopy(refinements)
    stale["l0_north_star_authority_normalization_policy"]["legacy_clause_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "snapshot digest" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(stale)
    )

    source_stale = copy.deepcopy(refinements)
    source_stale["legacy_l0_clause_dispositions"][0]["source_ref"] = "marketing-harness-charter_v0.4 §999"
    assert any(
        "source path/locator/content" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(source_stale)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["l0_north_star_authority_normalization_policy"]
    state = policy["classification_state"]
    state["status"] = "classified_pending_cutover"
    controls_by_clause = {
        "L0V04-PURPOSE": ["POD-20260815-007"],
        "L0V04-DUAL-LOOP": ["POD-20260815-007"],
        "L0V04-MEDIA-PARALLEL": ["POD-20260815-007"],
        "L0V04-PWA-PLAY": ["POD-20260815-007"],
        "L0V04-HUMAN-AI": ["POD-20260815-003", "POD-20260815-004", "POD-20260815-005", "POD-20260815-006", "POD-20260815-009"],
        "L0V04-PILLARS": ["POD-20260815-005", "POD-20260815-006", "POD-20260815-007"],
        "L0V04-CONSUMER-WEB-AUTOMATION": ["POD-20260815-001"],
        "L0V04-CONNECTOR-PRIORITY": ["POD-20260815-001"],
        "L0V04-CLAUDE-DESIGN": [],
        "L0V04-BROWSER-MEASUREMENT": ["POD-20260815-001", "POD-20260815-007"],
        "L0V04-FULL-V": ["POD-20260815-004"],
        "L0V04-RUNTIME": ["POD-20260815-002"],
        "L0V04-DISCORD-APPROVAL": ["POD-20260815-002"],
        "L0V04-DISCORD-COMMUNITY": ["POD-20260815-002"],
        "L0V04-AUTO-MODE": ["POD-20260815-003", "POD-20260815-004", "POD-20260815-005", "POD-20260815-006", "POD-20260815-009"],
    }
    source_digests = requirement_engine._legacy_l0_source_clause_digests(classified)
    clause_semantics = requirement_engine._l0_candidate_clause_semantics(
        classified["legacy_l0_clause_dispositions"]
    )
    selected = {}
    for source in classified["legacy_l0_clause_dispositions"]:
        clause_id = source["clause_id"]
        disposition = source["disposition"]
        selected[clause_id] = {
            "parent_row_digest": requirement_engine._digest(source),
            "source_clause_digest": source_digests[clause_id],
            "disposition": disposition,
            "retained_value_clause_ids": [
                row["clause_id"]
                for row in clause_semantics[clause_id]["retained_value_clauses"]
            ] if disposition != "obsolete" else [],
            "prohibited_legacy_mechanisms": [
                row["clause_id"]
                for row in clause_semantics[clause_id]["prohibited_mechanism_clauses"]
            ],
            "replacement_prc_digests": {
                prc: policy["replacement_prc_digests"][prc]
                for prc in source["replacement_prc_ids"]
            },
            "captured_po_control_ids": controls_by_clause[clause_id],
            "scope_subject_ids": ["L0-NORTH-STAR-AUTHORITY-NORMALIZATION"],
            "owner_subject_id": "L0-NORTH-STAR-AUTHORITY-NORMALIZATION",
            "rationale": "PO fixture classification",
            "resume_conditions": source["resume_conditions"] if disposition == "defer" else [],
        }
    state["selected_rows"] = selected
    pod_ids = [f"POD-20260815-{index:03d}" for index in (1, 2, 3, 4, 5, 6, 7, 9)]
    pod_projection = {
        decision_id: classified["captured_po_decision_controls"][decision_id]
        for decision_id in pod_ids
    }
    state["classification_approval"] = {
        "authority": "PO",
        "subject_id": "L0-NORTH-STAR-AUTHORITY-NORMALIZATION",
        "legacy_snapshot_digest": requirement_engine._digest(classified["legacy_l0_clause_dispositions"]),
        "source_clause_digests_digest": requirement_engine._digest(source_digests),
        "selected_rows_digest": requirement_engine._digest(selected),
        "candidate_clause_semantics_digest": requirement_engine._digest(clause_semantics),
        "captured_po_projection_digest": requirement_engine._digest(pod_projection),
    }
    candidate_path = tmp_path / "l0-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "north_star_clause_row_digests": {
                    clause_id: requirement_engine._digest(row) for clause_id, row in selected.items()
                },
                "north_star_clause_semantics": clause_semantics,
                "captured_po_projection_digest": requirement_engine._digest(pod_projection),
                "captured_po_controls": pod_projection,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "artifact_id": "AUTH-DEVELOPMENT-L0-NORTH-STAR-CANDIDATE",
                        "canonical_path": "l0-candidate.json",
                        "layer": "L0-charter",
                        "artifact_type": "north-star-authority-candidate",
                        "authority_format": "json",
                        "authority_status": "active",
                        "implementation_input": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    state["candidate_artifact_binding"] = {
        "artifact_id": "AUTH-DEVELOPMENT-L0-NORTH-STAR-CANDIDATE",
        "content_digest": candidate_digest,
    }
    state["classification_approval"]["candidate_content_digest"] = candidate_digest
    charter_path = tmp_path / "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md"
    charter_path.parent.mkdir(parents=True)
    original_charter_text = requirement_engine.LEGACY_L0_CHARTER.read_text(encoding="utf-8")
    charter_path.write_text(original_charter_text, encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "MANIFEST", manifest_path)
    monkeypatch.setattr(requirement_engine, "LEGACY_L0_CHARTER", charter_path)
    assert requirement_engine.l0_north_star_authority_normalization_policy_faults(classified) == []

    stale_semantic_receipt = copy.deepcopy(classified)
    stale_semantic_receipt["l0_north_star_authority_normalization_policy"]["classification_state"]["classification_approval"]["candidate_clause_semantics_digest"] = "sha256:" + "0" * 64
    assert any(
        "classification approval" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(stale_semantic_receipt)
    )

    bad_retained = copy.deepcopy(classified)
    bad_retained["l0_north_star_authority_normalization_policy"]["classification_state"]["selected_rows"]["L0V04-PURPOSE"]["retained_value_clause_ids"] = ["L0N-ARBITRARY"]
    assert any(
        "retained value clause" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(bad_retained)
    )

    swapped_segment = charter_path.read_text(encoding="utf-8").replace(
        "媒体ごとに独立して並走（X / note / YouTube / owned media / Discord コミュニティ …）。同期は強制しない",
        "媒体ごとに独立して並走（segment swapped）",
    )
    charter_path.write_text(swapped_segment, encoding="utf-8")
    assert any(
        "source path/locator/content" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(classified)
    )
    charter_path.write_text(original_charter_text, encoding="utf-8")

    discord_reversal = copy.deepcopy(classified)
    discord_reversal["l0_north_star_authority_normalization_policy"]["classification_state"]["selected_rows"]["L0V04-DISCORD-APPROVAL"]["captured_po_control_ids"] = []
    assert any(
        "captured PO control" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(discord_reversal)
    )

    candidate_path.write_text(json.dumps({"north_star_clause_row_digests": {}}), encoding="utf-8")
    assert any(
        "candidate" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(classified)
    )
    candidate_data = {
        "north_star_clause_row_digests": {
            clause_id: requirement_engine._digest(row) for clause_id, row in selected.items()
        },
        "north_star_clause_semantics": clause_semantics,
        "captured_po_projection_digest": requirement_engine._digest(pod_projection),
        "captured_po_controls": pod_projection,
    }
    candidate_path.write_text(json.dumps(candidate_data, ensure_ascii=False), encoding="utf-8")
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()

    complete = copy.deepcopy(classified)
    complete_policy = complete["l0_north_star_authority_normalization_policy"]
    complete_policy["status"] = "ratified"
    complete_state = complete_policy["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    complete_state["candidate_artifact_binding"]["content_digest"] = candidate_digest
    view_path = tmp_path / "l0-view.json"
    view_data = {
        "source_l0_content_digest": candidate_digest,
        "rendered_clause_row_digests": candidate_data["north_star_clause_row_digests"],
        "rendered_clause_semantics": clause_semantics,
    }
    view_path.write_text(json.dumps(view_data, ensure_ascii=False), encoding="utf-8")
    view_digest = "sha256:" + hashlib.sha256(view_path.read_bytes()).hexdigest()
    trace_path = tmp_path / "l1-trace.json"
    trace_data = {
        "source_l0_content_digest": candidate_digest,
        "l0_clause_to_prcs": {
            clause_id: sorted(source["replacement_prc_ids"])
            for clause_id, source in sorted(
                (row["clause_id"], row) for row in complete["legacy_l0_clause_dispositions"]
            )
        },
        "l0_clause_to_scope_subjects": {
            clause_id: sorted(selected[clause_id]["scope_subject_ids"])
            for clause_id in sorted(selected)
        },
    }
    trace_path.write_text(json.dumps(trace_data, ensure_ascii=False), encoding="utf-8")
    trace_digest = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    review_path = tmp_path / "l0-go-review.json"
    review = {
        "separation_status": "ci_attested",
        "verdict": "Go",
        "reviewer_principal": "ci-independent-reviewer",
        "author_principal": "requirements-authority-resolver",
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "reviewed_artifact_digests": {
            "candidate": candidate_digest,
            "view": view_digest,
            "trace": trace_digest,
        },
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
    review_digest = "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["items"][0]["implementation_input"] = True
    manifest["items"].extend(
        [
            {"artifact_id": "L0-NORTH-STAR-GENERATED-VIEW", "canonical_path": "l0-view.json"},
            {"artifact_id": "L1-NORTH-STAR-TRACE", "canonical_path": "l1-trace.json"},
            {"artifact_id": "AUTH-L0-GO-REVIEW", "canonical_path": "l0-go-review.json"},
        ]
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    baseline_path = tmp_path / "docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text(json.dumps({"fixture": True}), encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "l0_json_artifact_id": "AUTH-DEVELOPMENT-L0-NORTH-STAR-CANDIDATE",
        "l0_json_digest": candidate_digest,
        "generated_view_artifact_id": "L0-NORTH-STAR-GENERATED-VIEW",
        "generated_view_digest": view_digest,
        "l1_trace_artifact_id": "L1-NORTH-STAR-TRACE",
        "l1_trace_digest": trace_digest,
        "manifest_digest": "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "baseline_digest": "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "same_commit": True,
        "trace_diff_count": 0,
        "independent_go_artifact_id": "AUTH-L0-GO-REVIEW",
        "independent_go_digest": review_digest,
    }
    original_git = requirement_engine.git

    def fixture_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="fixture-head\n")
        if args[:2] == ("rev-parse", "HEAD^{tree}"):
            return SimpleNamespace(returncode=0, stdout="fixture-tree\n")
        if args and args[0] == "show":
            path = tmp_path / str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(
                returncode=0 if path.is_file() else 1,
                stdout=path.read_text(encoding="utf-8") if path.is_file() else "",
            )
        if args and args[0] == "show":
            path = tmp_path / str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(
                returncode=0 if path.is_file() else 1,
                stdout=path.read_text(encoding="utf-8") if path.is_file() else "",
            )
        return original_git(*args)

    monkeypatch.setattr(requirement_engine, "git", fixture_git)
    assert requirement_engine.l0_north_star_authority_normalization_policy_faults(complete) == []

    reversed_view = copy.deepcopy(complete)
    view_data["rendered_clause_row_digests"]["L0V04-PURPOSE"] = "sha256:" + "0" * 64
    view_path.write_text(json.dumps(view_data, ensure_ascii=False), encoding="utf-8")
    reversed_view["l0_north_star_authority_normalization_policy"]["classification_state"]["cutover_artifact_bindings"]["generated_view_digest"] = "sha256:" + hashlib.sha256(view_path.read_bytes()).hexdigest()
    assert any(
        "generated view" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(reversed_view)
    )
    view_path.write_text(json.dumps({**view_data, "rendered_clause_row_digests": candidate_data["north_star_clause_row_digests"]}, ensure_ascii=False), encoding="utf-8")

    reversed_trace = copy.deepcopy(complete)
    trace_data["l0_clause_to_prcs"]["L0V04-PURPOSE"] = []
    trace_path.write_text(json.dumps(trace_data, ensure_ascii=False), encoding="utf-8")
    reversed_trace["l0_north_star_authority_normalization_policy"]["classification_state"]["cutover_artifact_bindings"]["l1_trace_digest"] = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    assert any(
        "L0→L1 trace" in fault
        for fault in requirement_engine.l0_north_star_authority_normalization_policy_faults(reversed_trace)
    )


def test_agent_neo_redefinition_is_fixed_source_read_only_and_unratified(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.agent_neo_helix_redefinition_policy_faults(refinements) == []
    redundant_question = copy.deepcopy(refinements)
    redundant_record = next(
        record
        for record in redundant_question["records"]
        if record["subject_id"] == "AGENT-NEO-HELIX-REDEFINITION"
    )
    redundant_record["pending_resolution"].append(
        "MARKETING HARNESSとAGENT NEOのrepo/authority/API/evidence境界を閉じる"
    )
    assert any(
        "解決済みrepo境界" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(
            redundant_question
        )
    )

    stale_source = copy.deepcopy(refinements)
    stale_source["agent_neo_helix_redefinition_policy"]["source_ref"] = (
        "source:github:RetryYN/AGENT-NEO@HEAD"
    )
    assert any(
        "captured-observation" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(stale_source)
    )

    external_write = copy.deepcopy(refinements)
    external_write["agent_neo_helix_redefinition_policy"]["repo_authority_contract"][
        "external_repo_write_current_scope"
    ] = "allowed"
    assert any(
        "repo read-only" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(external_write)
    )

    old_success = copy.deepcopy(refinements)
    old_success["agent_neo_helix_redefinition_policy"]["repo_authority_contract"][
        "prohibited_admission_evidence"
    ].remove("legacy_g4_pass")
    assert any(
        "旧成功非流用" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(old_success)
    )

    invalid_effective_row = copy.deepcopy(refinements)
    invalid_effective_row["agent_neo_helix_redefinition_policy"][
        "capability_classification_candidates"
    ]["effective_row_digests"]["license"] = "sha256:" + "0" * 64
    assert any(
        "captured-observation" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(invalid_effective_row)
    )

    early_selection = copy.deepcopy(refinements)
    early_selection["agent_neo_helix_redefinition_policy"]["classification_state"][
        "selected_rows"
    ] = {"license": {"disposition": "candidate"}}
    assert any(
        "PO未分類" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(early_selection)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["agent_neo_helix_redefinition_policy"]
    candidates = requirement_engine._agent_neo_capability_classification_candidates()
    selected = {
        stable_id: {
            "effective_candidate_row_digest": candidates["effective_row_digests"][stable_id],
            "disposition": "defer",
            "release_owner": "none",
            "allowed_effects": [],
            "separate_authorization_dependency_ids": [],
            "defer_resume_conditions": ["PO capability adoption decision"],
            "obsolete_reason": None,
        }
        for stable_id in candidates["rows"]
    }
    selected_digest = requirement_engine._digest(selected)
    policy["classification_state"] = {
        "status": "classified_pending_cutover",
        "selected_rows": selected,
        "classification_approval": {
            "authority": "PO", "approver_principal": "po", "approved_revision": 1,
            "capability_inventory_digest": requirement_engine._digest(
                requirement_engine._agent_neo_capability_source_inventory()
            ),
            "candidate_rows_digest": requirement_engine._digest(candidates),
            "selected_rows_digest": selected_digest,
            "authority_semantic_digest": policy["authority_semantic_digest"],
        },
        "candidate_artifact_binding": {
            "artifact_id": "AUTH-DEVELOPMENT-AGENT-NEO-REDEFINITION-CANDIDATE",
            "implementation_input": False,
            "selected_rows_digest": selected_digest,
            "content_digest": "pending",
        },
        "cutover_artifact_bindings": None,
        "cutover_blocked": True,
    }
    candidate_path = tmp_path / "agent-neo-candidate.json"
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest": policy["authority_semantic_digest"],
        "selected_rows_digest": selected_digest,
        "selected_rows": selected,
    }, ensure_ascii=False), encoding="utf-8")
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    manifest["items"].append({
        "artifact_id": "AUTH-DEVELOPMENT-AGENT-NEO-REDEFINITION-CANDIDATE",
        "layer": "00-authority", "artifact_type": "requirement-authority-candidate",
        "authority_format": "json", "authority_status": "active",
        "implementation_input": False, "canonical_path": candidate_path.name,
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "MANIFEST", manifest_path)
    policy["classification_state"]["candidate_artifact_binding"]["content_digest"] = (
        "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    )
    assert requirement_engine.agent_neo_helix_redefinition_policy_faults(classified) == []

    escaped_manifest = copy.deepcopy(manifest)
    escaped_manifest["items"][-1]["canonical_path"] = str(candidate_path.resolve())
    manifest_path.write_text(json.dumps(escaped_manifest), encoding="utf-8")
    assert any(
        "candidate artifact" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(classified)
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    invalid_active = copy.deepcopy(classified)
    row = invalid_active["agent_neo_helix_redefinition_policy"]["classification_state"]["selected_rows"]["license"]
    row.update(disposition="replace", release_owner="none", allowed_effects=["external_write"], defer_resume_conditions=None)
    assert any(
        "active release owner" in fault or "authorization dependency" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(invalid_active)
    )

    complete = copy.deepcopy(classified)
    complete_policy = complete["agent_neo_helix_redefinition_policy"]
    complete_policy["status"] = "ratified"
    complete_state = complete_policy["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    complete_state["candidate_artifact_binding"]["implementation_input"] = True
    manifest["items"][-1]["implementation_input"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    baseline_path = tmp_path / "docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}", encoding="utf-8")
    baseline_digest = "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    manifest["items"].append({
        "artifact_id": "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO", "layer": "00-authority",
        "artifact_type": "review", "authority_format": "json", "authority_status": "active",
        "implementation_input": False, "canonical_path": review_path.name,
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    review = {
        "review_id": "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO", "verdict": "Go",
        "separation_status": "ci_attested", "reviewer_principal": "ci-reviewer",
        "author_principal": "codex", "target_commit": "fixture-head", "target_tree": "fixture-tree",
        "reviewed_artifact_digests": {"candidate": candidate_digest, "manifest": manifest_digest, "baseline": baseline_digest},
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "target_commit": "fixture-head", "target_tree": "fixture-tree",
        "candidate_content_digest": candidate_digest, "manifest_digest": manifest_digest,
        "baseline_digest": baseline_digest,
        "captured_source_observation_binding": {
            "repository": "RetryYN/AGENT-NEO", "source_commit": "9f5d679c0befce093ba077fcf11d514e4c75f17a",
            "access": "read_only", "capability_inventory_digest": requirement_engine._digest(
                requirement_engine._agent_neo_capability_source_inventory()
            ), "external_write_authorized": False,
        },
        "independent_go_artifact_id": "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO",
        "independent_go_path": review_path.name,
        "independent_go_digest": "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest(),
    }
    original_git = requirement_engine.git
    def fixture_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="fixture-head\n")
        if args[:2] == ("rev-parse", "HEAD^{tree}"):
            return SimpleNamespace(returncode=0, stdout="fixture-tree\n")
        if args and args[0] == "show":
            path = tmp_path / str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(
                returncode=0 if path.is_file() else 1,
                stdout=path.read_text(encoding="utf-8") if path.is_file() else "",
            )
        return original_git(*args)
    monkeypatch.setattr(requirement_engine, "git", fixture_git)
    assert requirement_engine.agent_neo_helix_redefinition_policy_faults(complete) == []

    escaped_review_manifest = copy.deepcopy(manifest)
    escaped_review_manifest["items"][-1]["canonical_path"] = str(review_path.resolve())
    manifest_path.write_text(json.dumps(escaped_review_manifest), encoding="utf-8")
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(complete)
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    review["verdict"] = "No-Go"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    complete_state["cutover_artifact_bindings"]["independent_go_digest"] = (
        "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    )
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.agent_neo_helix_redefinition_policy_faults(complete)
    )


def test_agent_neo_site_build_waits_for_parent_and_separates_site_effects(monkeypatch, tmp_path) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.agent_neo_site_build_release_policy_faults(refinements) == []

    early = copy.deepcopy(refinements)
    early["agent_neo_site_build_release_policy"]["classification_state"]["selected_rows"] = {
        "health_audit": {"release_disposition": "candidate"}
    }
    assert any(
        "site-build選択" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(early)
    )

    parent_ready_early_cutover = copy.deepcopy(refinements)
    parent_ready_early_cutover["agent_neo_helix_redefinition_policy"]["classification_state"][
        "status"
    ] = "classified_pending_cutover"
    site_policy = parent_ready_early_cutover["agent_neo_site_build_release_policy"]
    site_policy["parent_policy_digests"]["agent_neo_helix_redefinition_policy"] = (
        requirement_engine._digest(parent_ready_early_cutover["agent_neo_helix_redefinition_policy"])
    )
    site_policy["status"] = "ratified"
    site_policy["classification_state"]["cutover_blocked"] = False
    assert any(
        "classified rows" in fault or "classification stage" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(
            parent_ready_early_cutover
        )
    )

    missing_content = copy.deepcopy(refinements)
    missing_content["agent_neo_site_build_release_policy"]["parent_policy_digests"].pop(
        "wordpress_content_operations_policy"
    )
    assert any(
        "parent authority" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(missing_content)
    )

    repo_write = copy.deepcopy(refinements)
    repo_write["agent_neo_site_build_release_policy"]["responsibility_contract"][
        "agent_neo_repo_effect"
    ] = "external_write"
    assert any(
        "repo read-only" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(repo_write)
    )

    fake_dimension = copy.deepcopy(refinements)
    fake_dimension["agent_neo_site_build_release_policy"]["capability_overlay_contract"][
        "required_binding_dimensions"
    ].append("authorization_grant_id_revision_digest")
    assert any(
        "binding dimensions" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(fake_dimension)
    )

    classified = copy.deepcopy(refinements)
    parent = classified["agent_neo_helix_redefinition_policy"]
    parent["classification_state"]["status"] = "classified_pending_cutover"
    parent["classification_state"]["selected_rows"] = {
        "site_identity": {
            "effective_candidate_row_digest": "sha256:" + "1" * 64,
            "disposition": "candidate", "release_owner": "site_build",
            "allowed_effects": ["read", "state_write"],
        }
    }
    site = classified["agent_neo_site_build_release_policy"]
    site["parent_policy_digests"]["agent_neo_helix_redefinition_policy"] = requirement_engine._digest(parent)
    projection = {
        "site_identity": {
            "effective_candidate_row_digest": "sha256:" + "1" * 64,
            "disposition": "candidate", "allowed_effects": ["read", "state_write"],
        }
    }
    site["eligible_parent_capability_projection"] = projection
    site["authority_semantic_digest"] = requirement_engine._digest({
        key: site[key] for key in (
            "source_event_digests", "refinement_record_digest", "parent_policy_digests",
            "eligible_parent_capability_projection", "responsibility_contract",
            "capability_overlay_contract", "release_attempt_contract",
            "release_attempt_field_contracts",
        )
    })
    dimensions = site["capability_overlay_contract"]["required_binding_dimensions"]
    selected = {
        "site_identity": {
            "parent_row_digest": requirement_engine._digest(projection["site_identity"]),
            "responsibility_family": "platform", "allowed_site_effects": ["read", "state_write"],
            "required_grant_effects": ["state_write"], "required_binding_dimensions": dimensions,
            "release_disposition": "candidate", "owner_subject_id": "AGENT-NEO-SITE-BUILD-RELEASE",
            "rationale": "site identity is required for scoped site build", "resume_conditions": [],
        }
    }
    selected_digest = requirement_engine._digest(selected)
    candidate_path = tmp_path / "site-build-candidate.json"
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest": site["authority_semantic_digest"],
        "selected_rows_digest": selected_digest, "selected_rows": selected,
        "release_attempt_field_contracts": site["release_attempt_field_contracts"],
    }), encoding="utf-8")
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    manifest["items"].append({
        "artifact_id":"AUTH-DEVELOPMENT-AGENT-NEO-SITE-BUILD-CANDIDATE",
        "layer":"00-authority","artifact_type":"requirement-authority-candidate",
        "authority_format":"json","authority_status":"active","implementation_input":False,
        "canonical_path":candidate_path.name,
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    site["classification_state"] = {
        "status": "classified_pending_cutover", "selected_rows": selected,
        "classification_approval": {
            "authority": "PO", "approver_principal": "po", "approved_revision": 1,
            "parent_projection_digest": requirement_engine._digest(projection),
            "selected_rows_digest": selected_digest, "parent_policy_digest": requirement_engine._digest(parent),
            "authority_semantic_digest": site["authority_semantic_digest"],
        },
        "candidate_artifact_binding": {
            "artifact_id": "AUTH-DEVELOPMENT-AGENT-NEO-SITE-BUILD-CANDIDATE",
            "implementation_input": False, "selected_rows_digest": selected_digest,
            "content_digest":"sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        },
        "cutover_artifact_bindings": None, "cutover_blocked": True,
    }
    monkeypatch.setattr(requirement_engine, "agent_neo_helix_redefinition_policy_faults", lambda _: [])
    monkeypatch.setattr(requirement_engine,"REPO_ROOT",tmp_path)
    monkeypatch.setattr(requirement_engine,"MANIFEST",manifest_path)
    assert requirement_engine.agent_neo_site_build_release_policy_faults(classified) == []

    complete = copy.deepcopy(classified)
    complete_parent = complete["agent_neo_helix_redefinition_policy"]
    complete_parent["status"] = "ratified"
    complete_parent["classification_state"]["status"] = "cutover_complete"
    complete_parent["classification_state"]["cutover_blocked"] = False
    complete_site = complete["agent_neo_site_build_release_policy"]
    complete_site["status"] = "ratified"
    complete_site["parent_policy_digests"]["agent_neo_helix_redefinition_policy"] = (
        requirement_engine._digest(complete_parent)
    )
    complete_site["authority_semantic_digest"] = requirement_engine._digest({
        key: complete_site[key] for key in (
            "source_event_digests", "refinement_record_digest", "parent_policy_digests",
            "eligible_parent_capability_projection", "responsibility_contract",
            "capability_overlay_contract", "release_attempt_contract",
            "release_attempt_field_contracts",
        )
    })
    complete_state = complete_site["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    complete_state["classification_approval"]["parent_policy_digest"] = (
        requirement_engine._digest(complete_parent)
    )
    complete_state["classification_approval"]["authority_semantic_digest"] = (
        complete_site["authority_semantic_digest"]
    )
    complete_state["candidate_artifact_binding"]["implementation_input"] = True
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest": complete_site["authority_semantic_digest"],
        "selected_rows_digest": selected_digest, "selected_rows": selected,
        "release_attempt_field_contracts": complete_site["release_attempt_field_contracts"],
    }), encoding="utf-8")
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    complete_state["candidate_artifact_binding"]["content_digest"] = candidate_digest
    manifest["items"][-1]["implementation_input"] = True
    baseline_path = tmp_path / "docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}", encoding="utf-8")
    baseline_digest = "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    review_path = tmp_path / "site-build-review.json"
    manifest["items"].append({
        "artifact_id":"AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO", "layer":"00-authority",
        "artifact_type":"review", "authority_format":"json", "authority_status":"active",
        "implementation_input":False, "canonical_path":review_path.name,
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    parent_digest = requirement_engine._digest(complete_parent)
    review = {
        "review_id":"AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO", "verdict":"Go",
        "separation_status":"ci_attested", "reviewer_principal":"ci-reviewer",
        "author_principal":"codex", "target_commit":"fixture-head", "target_tree":"fixture-tree",
        "reviewed_artifact_digests":{"candidate":candidate_digest,"manifest":manifest_digest,"baseline":baseline_digest,"parent_policy":parent_digest},
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "target_commit":"fixture-head", "target_tree":"fixture-tree",
        "candidate_content_digest":candidate_digest, "manifest_digest":manifest_digest,
        "baseline_digest":baseline_digest, "parent_policy_digest":parent_digest,
        "parent_cutover_status":"cutover_complete", "agent_neo_external_repo_access":"read_only",
        "independent_go_artifact_id":"AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO",
        "independent_go_path":review_path.name,
        "independent_go_digest":"sha256:"+hashlib.sha256(review_path.read_bytes()).hexdigest(),
    }
    original_git = requirement_engine.git
    def site_fixture_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="fixture-head\n")
        if args[:2] == ("rev-parse", "HEAD^{tree}"):
            return SimpleNamespace(returncode=0, stdout="fixture-tree\n")
        if args and args[0] == "show":
            fixture_path = tmp_path / str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(
                returncode=0 if fixture_path.is_file() else 1,
                stdout=fixture_path.read_text(encoding="utf-8") if fixture_path.is_file() else "",
            )
        return original_git(*args)
    monkeypatch.setattr(requirement_engine,"git",site_fixture_git)
    assert requirement_engine.agent_neo_site_build_release_policy_faults(complete) == []

    parent_not_complete = copy.deepcopy(complete)
    parent_not_complete["agent_neo_helix_redefinition_policy"]["classification_state"]["status"] = "classified_pending_cutover"
    assert any(
        "親AGENT NEO cutover" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(parent_not_complete)
    )

    no_go = copy.deepcopy(complete)
    review["verdict"] = "No-Go"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    no_go["agent_neo_site_build_release_policy"]["classification_state"]["cutover_artifact_bindings"]["independent_go_digest"] = (
        "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    )
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.agent_neo_site_build_release_policy_faults(no_go)
    )


def test_agent_neo_product_evolution_stays_read_only_and_parent_bound(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.agent_neo_product_evolution_release_policy_faults(refinements) == []

    repo_write = copy.deepcopy(refinements)
    policy = repo_write["agent_neo_product_evolution_release_policy"]
    policy["repo_authority_contract"]["requirements_cutover_repo_write_authorized"] = True
    assert any(
        "repo read-only" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(repo_write)
    )

    legacy_success = copy.deepcopy(refinements)
    legacy_success["agent_neo_product_evolution_release_policy"][
        "evidence_non_inheritance_contract"
    ]["prohibited_as_compatibility_or_release_proof"].remove("legacy_g4_pass")
    assert any(
        "旧成功非証拠化" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(legacy_success)
    )

    early = copy.deepcopy(refinements)
    early["agent_neo_product_evolution_release_policy"]["classification_state"][
        "repo_write_authorized"
    ] = True
    assert any(
        "repo write" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(early)
    )

    classified = copy.deepcopy(refinements)
    parent = classified["agent_neo_helix_redefinition_policy"]
    parent["classification_state"]["status"] = "classified_pending_cutover"
    parent["classification_state"]["selected_rows"] = {
        "external_api": {
            "effective_candidate_row_digest": "sha256:" + "2" * 64,
            "disposition":"candidate", "release_owner":"product_evolution",
            "allowed_effects":["read","external_write"],
        }
    }
    product = classified["agent_neo_product_evolution_release_policy"]
    product["parent_policy_digests"]["agent_neo_helix_redefinition_policy"] = (
        requirement_engine._digest(parent)
    )
    projection = {"external_api":{
        "effective_candidate_row_digest":"sha256:"+"2"*64,
        "disposition":"candidate", "allowed_effects":["read","external_write"],
    }}
    product["eligible_parent_capability_projection"] = projection
    product["authority_semantic_digest"] = requirement_engine._digest({
        key:product[key] for key in (
            "source_event_digests","refinement_record_digest","parent_policy_digests",
            "eligible_parent_capability_projection","repo_authority_contract",
            "evidence_non_inheritance_contract","capability_overlay_contract",
            "repo_change_attempt_contract",
        )
    })
    compatibility = {
        "required_dimensions":["affected_site_class","breaking_change","data_schema_api_content_compatibility","migration_evidence","regression_evidence","rollback_evidence","source_target_version_range"],
        "not_applicable_dimensions":{},
    }
    selected = {"external_api":{
        "parent_projection_digest":requirement_engine._digest(projection["external_api"]),
        "component_family":"integration_contract", "change_effects":["repo_read","repo_write"],
        "compatibility_obligations":compatibility, "regression_scope_class":"affected_sites",
        "breaking_change_disposition":"po_risk_acceptance_required", "migration_required":True,
        "rollback_required":True, "release_disposition":"candidate",
        "separate_authorization_dependency_ids":["AGENT-NEO-PRODUCT-EVOLUTION-CHANGE-AUTHORIZATION"],
        "owner_subject_id":"AGENT-NEO-PRODUCT-EVOLUTION-RELEASE",
        "rationale":"external API contract evolution requires compatibility and rollback proof",
        "resume_conditions":[],
    }}
    selected_digest = requirement_engine._digest(selected)
    candidate_path = tmp_path / "product-evolution-candidate.json"
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest":product["authority_semantic_digest"],
        "selected_rows_digest":selected_digest,"selected_rows":selected,
        "repo_authority_contract":product["repo_authority_contract"],
        "repo_change_attempt_contract":product["repo_change_attempt_contract"],
    }),encoding="utf-8")
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    manifest["items"].append({
        "artifact_id":"AUTH-DEVELOPMENT-AGENT-NEO-PRODUCT-EVOLUTION-CANDIDATE",
        "layer":"00-authority","artifact_type":"requirement-authority-candidate",
        "authority_format":"json","authority_status":"active","implementation_input":False,
        "canonical_path":candidate_path.name,
    })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    product["classification_state"] = {
        "status":"classified_pending_cutover","selected_rows":selected,
        "classification_approval":{"authority":"PO","approver_principal":"po","approved_revision":1,"parent_projection_digest":requirement_engine._digest(projection),"selected_rows_digest":selected_digest,"parent_policy_digest":requirement_engine._digest(parent),"authority_semantic_digest":product["authority_semantic_digest"],"repo_write_authorized":False},
        "candidate_artifact_binding":{"artifact_id":"AUTH-DEVELOPMENT-AGENT-NEO-PRODUCT-EVOLUTION-CANDIDATE","implementation_input":False,"selected_rows_digest":selected_digest,"content_digest":"sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest()},
        "cutover_artifact_bindings":None,"cutover_blocked":True,"repo_write_authorized":False,
    }
    monkeypatch.setattr(requirement_engine,"agent_neo_helix_redefinition_policy_faults",lambda _:[])
    monkeypatch.setattr(requirement_engine,"REPO_ROOT",tmp_path)
    monkeypatch.setattr(requirement_engine,"MANIFEST",manifest_path)
    assert requirement_engine.agent_neo_product_evolution_release_policy_faults(classified) == []

    grant_reuse = copy.deepcopy(classified)
    row = grant_reuse["agent_neo_product_evolution_release_policy"]["classification_state"]["selected_rows"]["external_api"]
    row["separate_authorization_dependency_ids"] = ["BUSINESS-PROFILE-AUTHORIZATION"]
    assert any(
        "external repo authorization" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(grant_reuse)
    )

    missing_migration = copy.deepcopy(classified)
    row = missing_migration["agent_neo_product_evolution_release_policy"]["classification_state"]["selected_rows"]["external_api"]
    row["migration_required"] = False
    row["compatibility_obligations"]["required_dimensions"].remove("migration_evidence")
    assert any(
        "compatibility" in fault or "migration/rollback" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(missing_migration)
    )

    complete = copy.deepcopy(classified)
    complete_parent = complete["agent_neo_helix_redefinition_policy"]
    complete_parent["status"] = "ratified"
    complete_parent["classification_state"]["status"] = "cutover_complete"
    complete_parent["classification_state"]["cutover_blocked"] = False
    complete_site = complete["agent_neo_site_build_release_policy"]
    complete_site["status"] = "ratified"
    complete_site["classification_state"]["status"] = "cutover_complete"
    complete_site["classification_state"]["cutover_blocked"] = False
    complete_product = complete["agent_neo_product_evolution_release_policy"]
    complete_product["status"] = "ratified"
    complete_product["parent_policy_digests"]["agent_neo_helix_redefinition_policy"] = requirement_engine._digest(complete_parent)
    complete_product["parent_policy_digests"]["agent_neo_site_build_release_policy"] = requirement_engine._digest(complete_site)
    complete_product["authority_semantic_digest"] = requirement_engine._digest({
        key:complete_product[key] for key in (
            "source_event_digests","refinement_record_digest","parent_policy_digests",
            "eligible_parent_capability_projection","repo_authority_contract",
            "evidence_non_inheritance_contract","capability_overlay_contract",
            "repo_change_attempt_contract",
        )
    })
    complete_state = complete_product["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    complete_state["classification_approval"]["parent_policy_digest"] = requirement_engine._digest(complete_parent)
    complete_state["classification_approval"]["authority_semantic_digest"] = complete_product["authority_semantic_digest"]
    complete_state["candidate_artifact_binding"]["implementation_input"] = True
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest":complete_product["authority_semantic_digest"],
        "selected_rows_digest":selected_digest,"selected_rows":selected,
        "repo_authority_contract":complete_product["repo_authority_contract"],
        "repo_change_attempt_contract":complete_product["repo_change_attempt_contract"],
    }),encoding="utf-8")
    candidate_digest = "sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    complete_state["candidate_artifact_binding"]["content_digest"] = candidate_digest
    manifest["items"][-1]["implementation_input"] = True
    baseline_path = tmp_path/"docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}",encoding="utf-8")
    baseline_digest = "sha256:"+hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    review_path = tmp_path/"product-evolution-review.json"
    manifest["items"].append({
        "artifact_id":"AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO","layer":"00-authority",
        "artifact_type":"review","authority_format":"json","authority_status":"active",
        "implementation_input":False,"canonical_path":review_path.name,
    })
    manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    manifest_digest = "sha256:"+hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    parent_digest = requirement_engine._digest(complete_parent)
    site_digest = requirement_engine._digest(complete_site)
    review = {
        "review_id":"AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO","verdict":"Go",
        "separation_status":"ci_attested","reviewer_principal":"ci-reviewer","author_principal":"codex",
        "target_commit":"fixture-head","target_tree":"fixture-tree",
        "reviewed_artifact_digests":{"candidate":candidate_digest,"manifest":manifest_digest,"baseline":baseline_digest,"parent_policy":parent_digest,"site_build_policy":site_digest},
    }
    review_path.write_text(json.dumps(review),encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "target_commit":"fixture-head","target_tree":"fixture-tree","candidate_content_digest":candidate_digest,
        "manifest_digest":manifest_digest,"baseline_digest":baseline_digest,
        "parent_policy_digest":parent_digest,"parent_cutover_status":"cutover_complete",
        "site_build_policy_digest":site_digest,"site_build_cutover_status":"cutover_complete",
        "requirements_cutover_repo_write_authorized":False,"external_repo_access":"read_only",
        "independent_go_artifact_id":"AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO",
        "independent_go_path":review_path.name,
        "independent_go_digest":"sha256:"+hashlib.sha256(review_path.read_bytes()).hexdigest(),
    }
    original_git = requirement_engine.git
    def product_fixture_git(*args):
        if args[:2] == ("rev-parse","HEAD"):
            return SimpleNamespace(returncode=0,stdout="fixture-head\n")
        if args[:2] == ("rev-parse","HEAD^{tree}"):
            return SimpleNamespace(returncode=0,stdout="fixture-tree\n")
        if args and args[0] == "show":
            fixture_path = tmp_path/str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(returncode=0 if fixture_path.is_file() else 1,stdout=fixture_path.read_text(encoding="utf-8") if fixture_path.is_file() else "")
        return original_git(*args)
    monkeypatch.setattr(requirement_engine,"agent_neo_site_build_release_policy_faults",lambda _:[])
    monkeypatch.setattr(requirement_engine,"git",product_fixture_git)
    assert requirement_engine.agent_neo_product_evolution_release_policy_faults(complete) == []

    write_enabled = copy.deepcopy(complete)
    write_enabled["agent_neo_product_evolution_release_policy"]["classification_state"]["repo_write_authorized"] = True
    assert any(
        "read-only" in fault or "classified rows/state" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(write_enabled)
    )

    site_incomplete = copy.deepcopy(complete)
    site_incomplete["agent_neo_site_build_release_policy"]["classification_state"]["status"] = "classified_pending_cutover"
    assert any(
        "site-build" in fault
        for fault in requirement_engine.agent_neo_product_evolution_release_policy_faults(site_incomplete)
    )


def test_media_release_separates_poc_and_production_write_authority(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.fr16_notification_boundary_policy_faults(refinements) == []
    assert requirement_engine.discord_notification_rejection_policy_faults(refinements) == []
    operational_discord = copy.deepcopy(refinements)
    operational_discord["discord_notification_rejection_policy"]["purpose_partition"]["allowed_discord_purposes"].append("operational_notification")
    assert requirement_engine.discord_notification_rejection_policy_faults(operational_discord)
    community_grant = copy.deepcopy(refinements)
    community_grant["discord_notification_rejection_policy"]["purpose_partition"]["community_execution_authority"] = "granted"
    assert requirement_engine.discord_notification_rejection_policy_faults(community_grant)
    source_mutation = copy.deepcopy(refinements)
    source_mutation["discord_notification_rejection_policy"]["rejection_contract"]["source_state_invariant"] = "source_state_may_change"
    assert requirement_engine.discord_notification_rejection_policy_faults(source_mutation)
    credential_share = copy.deepcopy(refinements)
    credential_share["discord_notification_rejection_policy"]["cross_purpose_prohibitions"].remove("credential_sharing")
    assert requirement_engine.discord_notification_rejection_policy_faults(credential_share)
    legacy_transport = copy.deepcopy(refinements)
    legacy_transport["discord_notification_rejection_policy"]["prohibited_legacy_mechanisms"].remove("approval_transport_tuple")
    assert requirement_engine.discord_notification_rejection_policy_faults(legacy_transport)
    fake_registration = copy.deepcopy(refinements)
    fake_registration["discord_notification_rejection_policy"]["registration_contract"]["disposition"] = "community_registration"
    assert requirement_engine.discord_notification_rejection_policy_faults(fake_registration)
    decision_facts_reversed = copy.deepcopy(refinements)
    decision_facts_reversed["captured_po_decision_controls"]["POD-20260815-002"]["facts"]["discord_role"] = "product_notification"
    assert requirement_engine.discord_notification_rejection_policy_faults(decision_facts_reversed)
    community_wrapper_changed = copy.deepcopy(refinements)
    community_wrapper_changed["captured_po_decision_controls"]["POD-20260815-002"]["subject_semantic_digests"]["DISCORD-COMMUNITY-MARKETING-ROUTE"] = "sha256:" + "0" * 64
    assert requirement_engine.discord_notification_rejection_policy_faults(community_wrapper_changed) == []
    alternate_adapter_fallback = copy.deepcopy(refinements)
    rejection_record = next(
        row
        for row in alternate_adapter_fallback["records"]
        if row["subject_id"] == "DISCORD-NOTIFICATION-REJECTION-BOUNDARY"
    )
    rejection_record["semantic_dimensions"]["workflow"] = [
        "通知要求→purpose判定→Discord route拒否→UI inbox又は別承認済みadapterへ限定"
    ]
    rejection_record["acceptance_cases"][0]["statement"] = (
        "製品通知をUI inbox又は別承認済みadapterへ限定しDiscordへ送信しない"
    )
    rejection_record["semantic_digest"] = requirement_engine._digest(
        {
            key: value
            for key, value in rejection_record.items()
            if key not in {"semantic_digest", "approval"}
        }
    )
    rejection_policy = alternate_adapter_fallback["discord_notification_rejection_policy"]
    rejection_policy["refinement_record_digest"] = requirement_engine._digest(rejection_record)
    rejection_policy["refinement_record_semantic_digest"] = rejection_record["semantic_digest"]
    rejection_policy["refinement_record_content_digest"] = requirement_engine._digest(
        {key: value for key, value in rejection_record.items() if key != "semantic_digest"}
    )
    fr16_policy = alternate_adapter_fallback["fr16_notification_boundary_policy"]
    fr16_policy["parent_semantic_digests"]["discord_notification_rejection"] = requirement_engine._digest(
        rejection_record
    )
    fr16_policy["authority_semantic_digest"] = requirement_engine._digest(
        {key: value for key, value in fr16_policy.items() if key != "authority_semantic_digest"}
    )
    rejection_policy["parent_semantic_digests"]["fr16_notification_policy"] = requirement_engine._digest(
        fr16_policy
    )
    rejection_policy["authority_semantic_digest"] = requirement_engine._digest(
        {key: value for key, value in rejection_policy.items() if key != "authority_semantic_digest"}
    )
    assert requirement_engine.discord_notification_rejection_policy_faults(
        alternate_adapter_fallback
    )
    assert requirement_engine.vps_ui_primary_interface_policy_faults(refinements) == []
    assert refinements["vps_ui_primary_interface_policy"]["primary_route_contract"]["human_product_entry"] == ["vps_web_ui", "vps_ui_inbox"]
    assert "discord_product_notification" in refinements["vps_ui_primary_interface_policy"]["prohibited_legacy_interfaces"]
    assert refinements["vps_ui_primary_interface_policy"]["cutover_blocked_until_parent_ratification"] is True
    for contract in refinements["vps_ui_primary_interface_policy"]["operation_contracts"].values():
        assert set(contract["required"]).isdisjoint(contract["prohibited"])
        assert set(contract["required"]) | set(contract["prohibited"]) == set(refinements["vps_ui_primary_interface_policy"]["operation_binding_field_universe"])
    ack_approves = copy.deepcopy(refinements)
    ack_approves["vps_ui_primary_interface_policy"]["operation_contracts"]["inbox_seen_ack"]["allowed_effects"].append("approve")
    assert requirement_engine.vps_ui_primary_interface_policy_faults(ack_approves)
    authn_only = copy.deepcopy(refinements)
    authn_only["vps_ui_primary_interface_policy"]["operation_contracts"]["explicit_business_decision"]["required"].remove("authorization_grant_semantic_digest")
    assert requirement_engine.vps_ui_primary_interface_policy_faults(authn_only)
    view_write = copy.deepcopy(refinements)
    view_write["vps_ui_primary_interface_policy"]["operation_contracts"]["state_evidence_diagnostic_view"]["allowed_effects"] = ["state_write"]
    assert requirement_engine.vps_ui_primary_interface_policy_faults(view_write)
    inbox_partition_gap = copy.deepcopy(refinements)
    inbox_partition_gap["vps_ui_primary_interface_policy"]["operation_contracts"]["inbox_seen_ack"]["prohibited"].remove("business_decision_id")
    assert requirement_engine.vps_ui_primary_interface_policy_faults(inbox_partition_gap)
    invalid_universe = copy.deepcopy(refinements)
    invalid_universe["vps_ui_primary_interface_policy"]["operation_binding_field_universe"][0] = {}
    assert requirement_engine.vps_ui_primary_interface_policy_faults(invalid_universe)
    semantic_body_reversed = copy.deepcopy(refinements)
    primary_record = next(row for row in semantic_body_reversed["records"] if row.get("subject_id") == "VPS-UI-PRIMARY-HUMAN-INTERFACE")
    primary_record["semantic_dimensions"]["prohibitions"].remove("通知受信だけで意思決定を成立させない")
    semantic_body_reversed["vps_ui_primary_interface_policy"]["refinement_record_digest"] = requirement_engine._digest(primary_record)
    assert requirement_engine.vps_ui_primary_interface_policy_faults(semantic_body_reversed)
    feedback_activates = copy.deepcopy(refinements)
    feedback_activates["vps_ui_primary_interface_policy"]["operation_contracts"]["structured_feedback"]["allowed_effects"] = ["state_write"]
    assert requirement_engine.vps_ui_primary_interface_policy_faults(feedback_activates)
    raw_secret = copy.deepcopy(refinements)
    raw_secret["vps_ui_primary_interface_policy"]["data_minimization"]["allowed"].append("raw_credential")
    assert requirement_engine.vps_ui_primary_interface_policy_faults(raw_secret)
    discord_primary = copy.deepcopy(refinements)
    discord_primary["vps_ui_primary_interface_policy"]["primary_route_contract"]["human_product_entry"] = ["discord"]
    assert requirement_engine.vps_ui_primary_interface_policy_faults(discord_primary)
    playwright_decides = copy.deepcopy(refinements)
    playwright_decides["vps_ui_primary_interface_policy"]["non_implication_invariants"].remove("playwright_or_browser_confirmation_does_not_replace_human_decision")
    assert requirement_engine.vps_ui_primary_interface_policy_faults(playwright_decides)
    early_cutover = copy.deepcopy(refinements)
    early_cutover["vps_ui_primary_interface_policy"]["cutover_blocked_until_parent_ratification"] = False
    assert requirement_engine.vps_ui_primary_interface_policy_faults(early_cutover)
    fixed_registration = copy.deepcopy(refinements)
    fixed_registration["vps_ui_primary_interface_policy"]["registration_values_in_policy"] = "fixed_values"
    assert requirement_engine.vps_ui_primary_interface_policy_faults(fixed_registration)
    activation_reversed = copy.deepcopy(refinements)
    activation_reversed["captured_po_decision_controls"]["POD-20260815-003"]["facts"]["activation_authority"] = "machine_decision"
    assert requirement_engine.vps_ui_primary_interface_policy_faults(activation_reversed)
    unrelated_route_priority = copy.deepcopy(refinements)
    unrelated_route_priority["captured_po_decision_controls"]["POD-20260815-001"]["facts"]["route_priority"] = ["playwright"]
    assert requirement_engine.vps_ui_primary_interface_policy_faults(unrelated_route_priority) == []
    assert requirement_engine.external_browser_automation_route_policy_faults(refinements) == []
    assert requirement_engine.official_api_route_authority_policy_faults(refinements) == []
    assert requirement_engine.genai_execution_route_policy_faults(refinements) == []
    assert requirement_engine.automated_publishing_admission_policy_faults(refinements) == []
    assert requirement_engine.content_quality_gate_learning_policy_faults(refinements) == []
    assert requirement_engine.content_risk_classification_policy_faults(refinements) == []
    assert requirement_engine.research_led_content_growth_policy_faults(refinements) == []
    assert requirement_engine.discord_community_marketing_route_policy_faults(refinements) == []
    assert requirement_engine.vps_credential_security_boundary_policy_faults(refinements) == []
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(refinements) == []
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(refinements) == []
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(refinements) == []
    assert requirement_engine.ratification_dependency_audit_faults(refinements) == []
    missing_parent_edge = copy.deepcopy(refinements)
    row = next(row for row in missing_parent_edge["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "vps_credential_security_boundary_policy")
    row["parent_authority_ids"].remove("vps_ui_authentication_session_policy")
    assert requirement_engine.ratification_dependency_audit_faults(missing_parent_edge)
    partial_scc_ready = copy.deepcopy(refinements)
    row = next(row for row in partial_scc_ready["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "content_quality_gate_learning_policy")
    row["downstream_admission"] = "ready"
    assert requirement_engine.ratification_dependency_audit_faults(partial_scc_ready)
    write_from_ratification = copy.deepcopy(refinements)
    write_from_ratification["ratification_dependency_audit"]["external_write_authorized"] = True
    assert requirement_engine.ratification_dependency_audit_faults(write_from_ratification)
    historical_ratified = copy.deepcopy(refinements)
    historical_ratified["ratification_dependency_audit"]["historical_exclusions"].remove("AUTO-MODE-DECISION-AUTHORITY")
    assert requirement_engine.ratification_dependency_audit_faults(historical_ratified)
    missing_provider_prerequisite = copy.deepcopy(refinements)
    row = next(row for row in missing_provider_prerequisite["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "genai_execution_route_policy")
    row["parent_authority_ids"].remove("provider_neutral_execution_policy")
    assert requirement_engine.ratification_dependency_audit_faults(missing_provider_prerequisite)
    fake_wp_parent = copy.deepcopy(refinements)
    row = next(row for row in fake_wp_parent["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "wordpress_maintenance_boundaries_policy")
    row["parent_authority_ids"].append("discord_community_marketing_route_policy")
    assert requirement_engine.ratification_dependency_audit_faults(fake_wp_parent)
    quality_ready_early = copy.deepcopy(refinements)
    row = next(row for row in quality_ready_early["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "vps_ui_quality_attributes_policy")
    row["ratification_readiness"] = "ready_for_po_consideration"
    assert requirement_engine.ratification_dependency_audit_faults(quality_ready_early)
    strategy_ready_early = copy.deepcopy(refinements)
    row = next(row for row in strategy_ready_early["ratification_dependency_audit"]["authority_rows"] if row["authority_id"] == "strategy_requirement_admission_policy")
    row["ratification_readiness"] = "ready_for_po_consideration"
    assert requirement_engine.ratification_dependency_audit_faults(strategy_ready_early)
    missing_coverage = copy.deepcopy(refinements)
    missing_coverage["resolved_subject_authority_coverage_audit"]["coverage_rows"].pop()
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(missing_coverage)
    duplicate_primary = copy.deepcopy(refinements)
    row = next(row for row in duplicate_primary["resolved_subject_authority_coverage_audit"]["coverage_rows"] if row["subject_id"] == "VPS-UI-INBOX-LIFECYCLE")
    row["authority_refs"].append(copy.deepcopy(row["authority_refs"][0]))
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(duplicate_primary)
    superseded_active = copy.deepcopy(refinements)
    row = next(row for row in superseded_active["resolved_subject_authority_coverage_audit"]["coverage_rows"] if row["subject_id"] == "AUTO-MODE-DECISION-AUTHORITY")
    row["authority_refs"][0]["role"] = "primary_policy"
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(superseded_active)
    lifecycle_reactivated = copy.deepcopy(refinements)
    record = next(row for row in lifecycle_reactivated["records"] if row["subject_id"] == "AUTO-MODE-DECISION-AUTHORITY")
    record["lifecycle_status"] = "specified"
    audit_row = next(row for row in lifecycle_reactivated["resolved_subject_authority_coverage_audit"]["coverage_rows"] if row["subject_id"] == "AUTO-MODE-DECISION-AUTHORITY")
    audit_row["record_lifecycle_status"] = "specified"
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(lifecycle_reactivated)
    authority_self_follow = copy.deepcopy(refinements)
    authority_self_follow["rate_quota_cost_policy"]["unknown_limit_outcome"] = "allow_external_write"
    audit_row = next(row for row in authority_self_follow["resolved_subject_authority_coverage_audit"]["coverage_rows"] if row["subject_id"] == "RATE-QUOTA-COST-AUTHORITY")
    audit_row["authority_refs"][0]["authority_digest"] = requirement_engine._digest(authority_self_follow["rate_quota_cost_policy"])
    assert requirement_engine.resolved_subject_authority_coverage_audit_faults(authority_self_follow)
    content_updates_core = copy.deepcopy(refinements)
    content_updates_core["wordpress_maintenance_boundaries_policy"]["operation_routing_matrix"]["content:create_draft"]["allowed_effect"] = "platform_write"
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(content_updates_core)
    platform_accepts_security = copy.deepcopy(refinements)
    platform_accepts_security["wordpress_maintenance_boundaries_policy"]["security_intersection_contract"]["single_receipt_substitution"] = "allowed"
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(platform_accepts_security)
    security_publishes = copy.deepcopy(refinements)
    security_publishes["wordpress_maintenance_boundaries_policy"]["non_implication"].remove("security_patch_does_not_authorize_content_publish")
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(security_publishes)
    missing_route = copy.deepcopy(refinements)
    missing_route["wordpress_maintenance_boundaries_policy"]["operation_routing_matrix"].pop("platform:install_plugin")
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(missing_route)
    platform_effect_reversed = copy.deepcopy(refinements)
    platform_effect_reversed["wordpress_platform_maintenance_policy"]["operations"].remove("install_plugin")
    platform_effect_reversed["wordpress_maintenance_boundaries_policy"]["parent_policy_digests"]["platform"] = requirement_engine._digest(platform_effect_reversed["wordpress_platform_maintenance_policy"])
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(platform_effect_reversed)
    platform_backup_weakened = copy.deepcopy(refinements)
    platform_backup_weakened["wordpress_platform_maintenance_policy"]["operation_group_contracts"]["update_core_nonsecurity"]["required"].remove("backup")
    platform_backup_weakened["wordpress_platform_maintenance_policy"]["operation_group_contracts"]["update_core_nonsecurity"]["prohibited"].append("backup")
    platform_backup_weakened["wordpress_maintenance_boundaries_policy"]["parent_policy_digests"]["platform"] = requirement_engine._digest(platform_backup_weakened["wordpress_platform_maintenance_policy"])
    assert requirement_engine.wordpress_maintenance_boundaries_policy_faults(platform_backup_weakened)
    ack_decides = copy.deepcopy(refinements)
    ack_decides["vps_ui_inbox_lifecycle_policy"]["operation_contracts"]["acknowledge"]["value_contract"]["approve_reject_resume_authority"] = "granted"
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(ack_decides)
    auto_expiry = copy.deepcopy(refinements)
    auto_expiry["vps_ui_inbox_lifecycle_policy"]["lifecycle_contract"]["inbox_auto_expiry"] = "allowed"
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(auto_expiry)
    active_purge = copy.deepcopy(refinements)
    active_purge["vps_ui_inbox_lifecycle_policy"]["operation_contracts"]["archive_redact_or_purge"]["value_contract"]["active_item"] = "allowed"
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(active_purge)
    rollback = copy.deepcopy(refinements)
    rollback["vps_ui_inbox_lifecycle_policy"]["operation_contracts"]["create_content_quality_retry_exhausted"]["value_contract"]["failure_effect"] = "rollback_source"
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(rollback)
    fallback = copy.deepcopy(refinements)
    fallback["vps_ui_inbox_lifecycle_policy"]["external_fallback_authorized"] = True
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(fallback)
    approval_rule = copy.deepcopy(refinements)
    approval = approval_rule["vps_ui_inbox_lifecycle_policy"]["operation_contracts"]["create_approval_waiting"]
    approval["prohibited"].remove("rule_revision_digest")
    approval["required"].append("rule_revision_digest")
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(approval_rule)
    quality_missing_rule = copy.deepcopy(refinements)
    quality = quality_missing_rule["vps_ui_inbox_lifecycle_policy"]["operation_contracts"]["create_content_quality_retry_exhausted"]
    quality["required"].remove("rule_revision_digest")
    quality["prohibited"].append("rule_revision_digest")
    assert requirement_engine.vps_ui_inbox_lifecycle_policy_faults(quality_missing_rule)
    auto_unlock = copy.deepcopy(refinements)
    auto_unlock["vps_credential_security_boundary_policy"]["restart_contract"]["credential_only_auto_unlock"] = "allowed"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(auto_unlock)
    old_grant = copy.deepcopy(refinements)
    old_grant["vps_credential_security_boundary_policy"]["restart_contract"]["old_session_or_grant_reuse"] = "allowed"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(old_grant)
    raw_secret = copy.deepcopy(refinements)
    raw_secret["vps_credential_security_boundary_policy"]["secret_material_contract"]["raw_secret_or_bearer_or_credential_material"]["product_database"] = "allowed"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(raw_secret)
    expired_continues = copy.deepcopy(refinements)
    expired_continues["vps_credential_security_boundary_policy"]["state_contracts"]["revoked_or_expired"]["value_contract"]["continued_use"] = "allowed"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(expired_continues)
    persistent = copy.deepcopy(refinements)
    persistent["vps_credential_security_boundary_policy"]["persistent_service_authorized"] = True
    assert requirement_engine.vps_credential_security_boundary_policy_faults(persistent)
    agents_continue = copy.deepcopy(refinements)
    agents_continue["captured_po_decision_controls"]["POD-20260815-008"]["facts"]["current_runtime_lifecycle"] = "agents_continue_after_reboot"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(agents_continue)
    implicit_service = copy.deepcopy(refinements)
    implicit_service["captured_po_decision_controls"]["POD-20260815-008"]["facts"]["future_persistent_service"] = "implicit_authorized"
    assert requirement_engine.vps_credential_security_boundary_policy_faults(implicit_service)
    discord_notification = copy.deepcopy(refinements)
    discord_notification["discord_community_marketing_route_policy"]["purpose_contract"]["allowed"].append("operational_notification")
    assert requirement_engine.discord_community_marketing_route_policy_faults(discord_notification)
    discord_self_bot = copy.deepcopy(refinements)
    discord_self_bot["discord_community_marketing_route_policy"]["principal_contract"]["self_bot"] = "allowed"
    assert requirement_engine.discord_community_marketing_route_policy_faults(discord_self_bot)
    discord_shared_credential = copy.deepcopy(refinements)
    discord_shared_credential["discord_community_marketing_route_policy"]["cross_purpose_separation"].remove("credential")
    assert requirement_engine.discord_community_marketing_route_policy_faults(discord_shared_credential)
    discord_post_growth = copy.deepcopy(refinements)
    discord_post_growth["discord_community_marketing_route_policy"]["non_implication"].remove("post_success_does_not_prove_growth")
    assert requirement_engine.discord_community_marketing_route_policy_faults(discord_post_growth)
    post_with_reply_target = copy.deepcopy(refinements)
    post = post_with_reply_target["discord_community_marketing_route_policy"]["operation_contracts"]["community_post"]
    post["prohibited"].remove("reply_to_message_id")
    post["required"].append("reply_to_message_id")
    assert requirement_engine.discord_community_marketing_route_policy_faults(post_with_reply_target)
    reply_without_target = copy.deepcopy(refinements)
    reply = reply_without_target["discord_community_marketing_route_policy"]["operation_contracts"]["community_reply"]
    reply["required"].remove("reply_to_message_id")
    reply["prohibited"].append("reply_to_message_id")
    assert requirement_engine.discord_community_marketing_route_policy_faults(reply_without_target)
    cross_thread_reply = copy.deepcopy(refinements)
    cross_thread_reply["discord_community_marketing_route_policy"]["operation_contracts"]["community_reply"]["reply_target_contract"]["cross_thread_or_channel"] = "allowed"
    assert requirement_engine.discord_community_marketing_route_policy_faults(cross_thread_reply)
    researchless = copy.deepcopy(refinements)
    researchless["research_led_content_growth_policy"]["prohibited_inheritance"].remove("researchless_content_generation")
    assert requirement_engine.research_led_content_growth_policy_faults(researchless)
    publish_proves = copy.deepcopy(refinements)
    publish_proves["research_led_content_growth_policy"]["evidence_non_implication"].remove("publication_success_does_not_prove_hypothesis")
    assert requirement_engine.research_led_content_growth_policy_faults(publish_proves)
    offer_auto_mutates = copy.deepcopy(refinements)
    offer_auto_mutates["research_led_content_growth_policy"]["offer_contract"]["immutable_or_unknown"] = "automatic_mutation"
    assert requirement_engine.research_led_content_growth_policy_faults(offer_auto_mutates)
    paid_early = copy.deepcopy(refinements)
    paid_early["research_led_content_growth_policy"]["paid_acquisition_contract"]["phase"] = "initial"
    assert requirement_engine.research_led_content_growth_policy_faults(paid_early)
    direct_strategy = copy.deepcopy(refinements)
    direct_strategy["research_led_content_growth_policy"]["strategy_feedback_contract"]["direct_upstream_mutation"] = "allowed"
    assert requirement_engine.research_led_content_growth_policy_faults(direct_strategy)
    unknown_low = copy.deepcopy(refinements)
    unknown_low["content_risk_classification_policy"]["classification_contract"]["unknown_or_missing"] = "low_risk_pass"
    assert requirement_engine.content_risk_classification_policy_faults(unknown_low)
    preference_weakens = copy.deepcopy(refinements)
    preference_weakens["content_risk_classification_policy"]["strictness_contract"]["user_preference_can_weaken_mandatory_risk"] = True
    assert requirement_engine.content_risk_classification_policy_faults(preference_weakens)
    ai_replaces_hj = copy.deepcopy(refinements)
    ai_replaces_hj["content_risk_classification_policy"]["classification_contract"]["human_judgement_required"] = "ai_allowed"
    assert requirement_engine.content_risk_classification_policy_faults(ai_replaces_hj)
    risk_pass_publishes = copy.deepcopy(refinements)
    risk_pass_publishes["content_risk_classification_policy"]["non_implication"].remove("risk_pass_does_not_grant_publish")
    assert requirement_engine.content_risk_classification_policy_faults(risk_pass_publishes)
    missing_risk_domain = copy.deepcopy(refinements)
    missing_risk_domain["content_risk_classification_policy"]["risk_domains"].remove("health")
    assert requirement_engine.content_risk_classification_policy_faults(missing_risk_domain)
    failed_to_review = copy.deepcopy(refinements)
    failed_to_review["content_quality_gate_learning_policy"]["verdict_contract"]["fail"] = "human_review"
    assert requirement_engine.content_quality_gate_learning_policy_faults(failed_to_review)
    global_feedback = copy.deepcopy(refinements)
    global_feedback["content_quality_gate_learning_policy"]["feedback_scope_contract"]["missing_scope_default"] = "global"
    assert requirement_engine.content_quality_gate_learning_policy_faults(global_feedback)
    weak_ymyl = copy.deepcopy(refinements)
    weak_ymyl["content_quality_gate_learning_policy"]["strictness_contract"]["brand_or_ymyl_weakening"] = "allowed"
    assert requirement_engine.content_quality_gate_learning_policy_faults(weak_ymyl)
    quality_is_growth = copy.deepcopy(refinements)
    quality_is_growth["content_quality_gate_learning_policy"]["growth_non_implication"]["quality_pass"] = "growth_evidence"  # noqa: S105
    assert requirement_engine.content_quality_gate_learning_policy_faults(quality_is_growth)
    pod_scope_global = copy.deepcopy(refinements)
    pod_scope_global["captured_po_decision_controls"]["POD-20260815-005"]["facts"]["missing_scope_default"] = "global"
    assert requirement_engine.content_quality_gate_learning_policy_faults(pod_scope_global)
    pod_retry_notifies = copy.deepcopy(refinements)
    pod_retry_notifies["captured_po_decision_controls"]["POD-20260815-009"]["facts"]["ordinary_failed_retry_notification"] = "vps_ui_inbox"
    assert requirement_engine.content_quality_gate_learning_policy_faults(pod_retry_notifies)
    missing_quality_dimension = copy.deepcopy(refinements)
    missing_quality_dimension["content_quality_gate_learning_policy"]["quality_dimensions"].remove("format_and_type")
    assert requirement_engine.content_quality_gate_learning_policy_faults(missing_quality_dimension)
    generic_na = copy.deepcopy(refinements)
    generic_na["content_quality_gate_learning_policy"]["dimension_coverage_contract"]["generic_na"] = "allowed"
    assert requirement_engine.content_quality_gate_learning_policy_faults(generic_na)
    direct_without_evidence = copy.deepcopy(refinements)
    direct = direct_without_evidence["content_quality_gate_learning_policy"]["dimension_disposition_contracts"]["direct"]
    direct["required"].remove("evidence_digest")
    direct["prohibited"].append("evidence_digest")
    assert requirement_engine.content_quality_gate_learning_policy_faults(direct_without_evidence)
    machine_activation = copy.deepcopy(refinements)
    machine_activation["automated_publishing_admission_policy"]["activation_contract"]["machine_eligibility"] = "authority"
    assert requirement_engine.automated_publishing_admission_policy_faults(machine_activation)
    failed_artifact_review = copy.deepcopy(refinements)
    failed_artifact_review["automated_publishing_admission_policy"]["outcome_contracts"]["gate_fail_regenerate"]["human_review_before_regeneration"] = "allowed"
    assert requirement_engine.automated_publishing_admission_policy_faults(failed_artifact_review)
    ordinary_retry_notice = copy.deepcopy(refinements)
    ordinary_retry_notice["automated_publishing_admission_policy"]["outcome_contracts"]["gate_fail_regenerate"]["notification"] = "vps_ui_inbox"
    assert requirement_engine.automated_publishing_admission_policy_faults(ordinary_retry_notice)
    exhaustion_rolls_back = copy.deepcopy(refinements)
    exhaustion_rolls_back["automated_publishing_admission_policy"]["outcome_contracts"]["retry_exhausted_blocked"]["notification_failure"] = "rollback"
    assert requirement_engine.automated_publishing_admission_policy_faults(exhaustion_rolls_back)
    unsupported_notifies = copy.deepcopy(refinements)
    unsupported_notifies["automated_publishing_admission_policy"]["outcome_contracts"]["unsupported_update_non_action"]["notification"] = "vps_ui_inbox"
    assert requirement_engine.automated_publishing_admission_policy_faults(unsupported_notifies)
    pass_becomes_fail = copy.deepcopy(refinements)
    pass_becomes_fail["automated_publishing_admission_policy"]["outcome_contracts"]["gate_pass_auto_operation"]["value_contract"]["gate_verdict"] = "fail"
    assert requirement_engine.automated_publishing_admission_policy_faults(pass_becomes_fail)
    regenerate_advances_state = copy.deepcopy(refinements)
    regenerate_advances_state["automated_publishing_admission_policy"]["outcome_contracts"]["gate_fail_regenerate"]["value_contract"]["result_revision_relation"] = "greater_than_prior"
    assert requirement_engine.automated_publishing_admission_policy_faults(regenerate_advances_state)
    unsupported_without_result_revision = copy.deepcopy(refinements)
    unsupported = unsupported_without_result_revision["automated_publishing_admission_policy"]["outcome_contracts"]["unsupported_update_non_action"]
    unsupported["required"].remove("result_state_revision")
    unsupported["prohibited"].append("result_state_revision")
    assert requirement_engine.automated_publishing_admission_policy_faults(unsupported_without_result_revision)
    consumer_genai = copy.deepcopy(refinements)
    consumer_genai["genai_execution_route_policy"]["provider_contract"]["consumer_web_ui_unattended"] = "allowed"
    assert requirement_engine.genai_execution_route_policy_faults(consumer_genai)
    fixed_runtime = copy.deepcopy(refinements)
    fixed_runtime["genai_execution_route_policy"]["provider_contract"]["codex_or_claude_runtime_required"] = "required"
    assert requirement_engine.genai_execution_route_policy_faults(fixed_runtime)
    response_publishes = copy.deepcopy(refinements)
    response_publishes["genai_execution_route_policy"]["non_implication"].remove("generation_response_does_not_grant_publish")
    assert requirement_engine.genai_execution_route_policy_faults(response_publishes)
    unregistered_cli = copy.deepcopy(refinements)
    unregistered_cli["genai_execution_route_policy"]["route_contracts"]["registered_cli"]["adoption"] = "implicit"
    assert requirement_engine.genai_execution_route_policy_faults(unregistered_cli)
    ambiguous_cli_record = copy.deepcopy(refinements)
    genai_record = next(
        row
        for row in ambiguous_cli_record["records"]
        if row["subject_id"] == "GENAI-EXECUTION-ROUTE"
    )
    genai_record["semantic_dimensions"]["scope_in"][1] = "任意CLI adapter"
    genai_record["semantic_digest"] = requirement_engine._digest(
        {
            key: value
            for key, value in genai_record.items()
            if key not in {"semantic_digest", "approval"}
        }
    )
    genai_policy = ambiguous_cli_record["genai_execution_route_policy"]
    genai_policy["refinement_record_digest"] = requirement_engine._digest(genai_record)
    genai_policy["refinement_record_semantic_digest"] = genai_record["semantic_digest"]
    genai_policy["refinement_record_content_digest"] = requirement_engine._digest(
        {key: value for key, value in genai_record.items() if key != "semantic_digest"}
    )
    genai_policy["authority_semantic_digest"] = requirement_engine._digest(
        {key: value for key, value in genai_policy.items() if key != "authority_semantic_digest"}
    )
    assert requirement_engine.genai_execution_route_policy_faults(ambiguous_cli_record)
    genai_browser_fallback = copy.deepcopy(refinements)
    genai_browser_fallback["genai_execution_route_policy"]["fallback_contract"]["consumer_web_ui"] = "allowed"
    assert requirement_engine.genai_execution_route_policy_faults(genai_browser_fallback)
    generate_as_read = copy.deepcopy(refinements)
    generate_as_read["genai_execution_route_policy"]["route_contracts"]["official_api"]["parent_route_effect"] = "read"
    assert requirement_engine.genai_execution_route_policy_faults(generate_as_read)
    generate_without_operation_auth = copy.deepcopy(refinements)
    api_contract = generate_without_operation_auth["genai_execution_route_policy"]["route_contracts"]["official_api"]
    api_contract["required"].remove("operation_authorization_ref")
    api_contract["prohibited"].append("operation_authorization_ref")
    assert requirement_engine.genai_execution_route_policy_faults(generate_without_operation_auth)
    confirmation_with_credential = copy.deepcopy(refinements)
    confirmation = confirmation_with_credential["genai_execution_route_policy"]["route_contracts"]["playwright_confirmation"]
    confirmation["prohibited"].remove("credential_scope_digest")
    confirmation["required"].append("credential_scope_digest")
    assert requirement_engine.genai_execution_route_policy_faults(confirmation_with_credential)
    confirmation_without_evidence = copy.deepcopy(refinements)
    confirmation = confirmation_without_evidence["genai_execution_route_policy"]["route_contracts"]["playwright_confirmation"]
    confirmation["required"].remove("confirmation_evidence_digest")
    confirmation["prohibited"].append("confirmation_evidence_digest")
    assert requirement_engine.genai_execution_route_policy_faults(confirmation_without_evidence)
    confirmation_uses_generation_response = copy.deepcopy(refinements)
    confirmation = confirmation_uses_generation_response["genai_execution_route_policy"]["route_contracts"]["playwright_confirmation"]
    confirmation["required"].remove("confirmation_evidence_digest")
    confirmation["prohibited"].append("confirmation_evidence_digest")
    confirmation["prohibited"].remove("response_digest")
    confirmation["required"].append("response_digest")
    assert requirement_engine.genai_execution_route_policy_faults(confirmation_uses_generation_response)
    attended_with_response = copy.deepcopy(refinements)
    attended = attended_with_response["genai_execution_route_policy"]["route_contracts"]["attended_manual"]
    attended["prohibited"].remove("response_digest")
    attended["required"].append("response_digest")
    assert requirement_engine.genai_execution_route_policy_faults(attended_with_response)
    mcp_first = copy.deepcopy(refinements)
    mcp_first["official_api_route_authority_policy"]["precedence_contract"]["automation_order"] = ["official_mcp", "official_api"]
    assert requirement_engine.official_api_route_authority_policy_faults(mcp_first)
    stale_terms_allowed = copy.deepcopy(refinements)
    stale_terms_allowed["official_api_route_authority_policy"]["fail_close_conditions"].remove("terms_mismatch")
    assert requirement_engine.official_api_route_authority_policy_faults(stale_terms_allowed)
    browser_implicit = copy.deepcopy(refinements)
    browser_implicit["official_api_route_authority_policy"]["browser_boundary"]["implicit_fallback"] = "allowed"
    assert requirement_engine.official_api_route_authority_policy_faults(browser_implicit)
    route_grants_release = copy.deepcopy(refinements)
    route_grants_release["official_api_route_authority_policy"]["non_implication"].remove("route_success_does_not_grant_release")
    assert requirement_engine.official_api_route_authority_policy_faults(route_grants_release)
    invalid_route_universe = copy.deepcopy(refinements)
    invalid_route_universe["official_api_route_authority_policy"]["route_registry_field_universe"][0] = {}
    assert requirement_engine.official_api_route_authority_policy_faults(invalid_route_universe)
    export_write = copy.deepcopy(refinements)
    export_write["official_api_route_authority_policy"]["route_kind_effect_contracts"]["official_export"]["allowed_effects"].append("external_write")
    assert requirement_engine.official_api_route_authority_policy_faults(export_write)
    attended_read = copy.deepcopy(refinements)
    attended_read["official_api_route_authority_policy"]["route_kind_effect_contracts"]["attended_manual"]["allowed_effects"] = ["read"]
    assert requirement_engine.official_api_route_authority_policy_faults(attended_read)
    write_without_authority = copy.deepcopy(refinements)
    write_without_authority["official_api_route_authority_policy"]["route_kind_effect_contracts"]["official_api"]["write_required_fields"] = []
    assert requirement_engine.official_api_route_authority_policy_faults(write_without_authority)
    browser_first = copy.deepcopy(refinements)
    browser_first["external_browser_automation_route_policy"]["precedence_contract"]["order"] = ["playwright_registered_fallback", "official_api"]
    assert requirement_engine.external_browser_automation_route_policy_faults(browser_first)
    quota_bypass = copy.deepcopy(refinements)
    quota_bypass["external_browser_automation_route_policy"]["precedence_contract"]["fallback_forbidden_reasons"].remove("quota_rejection")
    assert requirement_engine.external_browser_automation_route_policy_faults(quota_bypass)
    confirmation_writes = copy.deepcopy(refinements)
    confirmation_writes["external_browser_automation_route_policy"]["route_field_contracts"]["playwright_confirmation"]["allowed_effects"] = ["external_write"]
    assert requirement_engine.external_browser_automation_route_policy_faults(confirmation_writes)
    browser_write = copy.deepcopy(refinements)
    browser_write["external_browser_automation_route_policy"]["browser_write_authorized"] = True
    assert requirement_engine.external_browser_automation_route_policy_faults(browser_write)
    consumer_ui = copy.deepcopy(refinements)
    consumer_ui["external_browser_automation_route_policy"]["engine_contract"]["consumer_web_ui_unattended"] = "allowed"
    assert requirement_engine.external_browser_automation_route_policy_faults(consumer_ui)
    unknown_engine = copy.deepcopy(refinements)
    unknown_engine["external_browser_automation_route_policy"]["engine_contract"]["automatic_engine_substitution"] = "allowed"
    assert requirement_engine.external_browser_automation_route_policy_faults(unknown_engine)
    missing_terms = copy.deepcopy(refinements)
    missing_terms["external_browser_automation_route_policy"]["route_field_contracts"]["playwright_registered_fallback"]["required"].remove("terms_revision_digest")
    assert requirement_engine.external_browser_automation_route_policy_faults(missing_terms)
    invalid_browser_universe = copy.deepcopy(refinements)
    invalid_browser_universe["external_browser_automation_route_policy"]["attempt_binding_field_universe"][0] = {}
    assert requirement_engine.external_browser_automation_route_policy_faults(invalid_browser_universe)

    write_without_risk = copy.deepcopy(refinements)
    write_without_risk["external_browser_automation_route_policy"]["route_field_contracts"]["official_api"]["write_effect_contract"]["required"].remove("risk_gate_receipt")
    assert requirement_engine.external_browser_automation_route_policy_faults(write_without_risk)

    attended_result = copy.deepcopy(refinements)
    attended = attended_result["external_browser_automation_route_policy"]["route_field_contracts"]["attended_manual"]
    attended["prohibited"].remove("result_or_confirmation_receipt")
    attended["required"].append("result_or_confirmation_receipt")
    assert requirement_engine.external_browser_automation_route_policy_faults(attended_result)

    allow_list_reversed = copy.deepcopy(refinements)
    prohibited = allow_list_reversed["external_browser_automation_route_policy"]["prohibited_inheritance"]
    prohibited[prohibited.index("out_of_allow_list_external_read")] = "allow_list_external_read"
    assert requirement_engine.external_browser_automation_route_policy_faults(allow_list_reversed)
    notify_before_stop = copy.deepcopy(refinements)
    notify_before_stop["fr16_notification_boundary_policy"]["ordering_invariant"] = "inbox_attempt_before_stop"
    assert requirement_engine.fr16_notification_boundary_policy_faults(notify_before_stop)
    discord_fallback = copy.deepcopy(refinements)
    discord_fallback["fr16_notification_boundary_policy"]["route_contract"]["allowed"].append("discord")
    assert requirement_engine.fr16_notification_boundary_policy_faults(discord_fallback)
    rollback_on_failure = copy.deepcopy(refinements)
    rollback_on_failure["fr16_notification_boundary_policy"]["failure_invariants"].remove("inbox_failure_or_retry_exhaustion_preserves_source_state_revision_and_history")
    assert requirement_engine.fr16_notification_boundary_policy_faults(rollback_on_failure)
    ack_resumes = copy.deepcopy(refinements)
    ack_resumes["fr16_notification_boundary_policy"]["authority_invariants"].remove("notification_does_not_approve_reject_or_resume")
    assert requirement_engine.fr16_notification_boundary_policy_faults(ack_resumes)
    unknown_class = copy.deepcopy(refinements)
    unknown_class["fr16_notification_boundary_policy"]["source_class_contracts"]["approval_waiting"]["source_state"] = "blocked"
    assert requirement_engine.fr16_notification_boundary_policy_faults(unknown_class)
    wrong_predecessor = copy.deepcopy(refinements)
    wrong_predecessor["fr16_notification_boundary_policy"]["source_class_contracts"]["approval_waiting"]["required_predecessor"] = "authorized_stop_transition_committed"
    assert requirement_engine.fr16_notification_boundary_policy_faults(wrong_predecessor)
    missing_rule_revision = copy.deepcopy(refinements)
    missing_rule_revision["fr16_notification_boundary_policy"]["dedupe_contract"]["class_field_contracts"]["blocked_retry_exhausted"]["required"].remove("rule_revision_digest")
    assert requirement_engine.fr16_notification_boundary_policy_faults(missing_rule_revision)
    mixed_retry_identity = copy.deepcopy(refinements)
    mixed_retry_identity["fr16_notification_boundary_policy"]["dedupe_contract"]["class_field_contracts"]["blocked_retry_exhausted"]["required"].append("source_state_revision")
    assert requirement_engine.fr16_notification_boundary_policy_faults(mixed_retry_identity)
    missing_registration = copy.deepcopy(refinements)
    inbox = next(row for row in missing_registration["records"] if row.get("subject_id") == "VPS-UI-INBOX-LIFECYCLE")
    inbox["registration_bindings"].pop(0)
    assert requirement_engine.fr16_notification_boundary_policy_faults(missing_registration)
    stale_source = copy.deepcopy(refinements)
    stale_source["fr16_notification_boundary_policy"]["source_event_digests"]["RDE-000002"] = "sha256:" + "0" * 64
    assert requirement_engine.fr16_notification_boundary_policy_faults(stale_source)
    legacy_s0 = copy.deepcopy(refinements)
    legacy_record = next(
        row for row in legacy_s0["records"]
        if row.get("subject_id") == "FR-16-NOTIFICATION-BOUNDARY"
    )
    legacy_record["semantic_dimensions"]["phase"] = "S0"
    legacy_record["semantic_digest"] = requirement_engine._digest(legacy_record["semantic_dimensions"])
    legacy_policy = legacy_s0["fr16_notification_boundary_policy"]
    legacy_policy["refinement_record_digest"] = requirement_engine._digest(legacy_record)
    legacy_policy["refinement_record_semantic_digest"] = legacy_record["semantic_digest"]
    legacy_policy["refinement_record_content_digest"] = requirement_engine._digest(
        {key: value for key, value in legacy_record.items() if key != "semantic_digest"}
    )
    legacy_policy.pop("authority_semantic_digest")
    legacy_policy["authority_semantic_digest"] = requirement_engine._digest(legacy_policy)
    assert requirement_engine.fr16_notification_boundary_policy_faults(legacy_s0)
    assert requirement_engine.media_poc_scrum_release_policy_faults(refinements) == []

    whole_media = copy.deepcopy(refinements)
    whole_media["media_poc_scrum_release_policy"]["captured_po_decision_projection"][
        "release_granularity"
    ]["partial_success_media_acceptance"] = "allowed"
    assert any(
        "媒体release単位" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(whole_media)
    )

    poc_permission = copy.deepcopy(refinements)
    poc_permission["media_poc_scrum_release_policy"]["poc_evidence_contract"][
        "production_permission_inference"
    ] = "allowed"
    assert any(
        "PoC evidence" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(poc_permission)
    )

    early_write = copy.deepcopy(refinements)
    early_write["media_poc_scrum_release_policy"]["classification_state"][
        "production_write_authorized"
    ] = True
    assert any(
        "本番write" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(early_write)
    )

    discord_notification = copy.deepcopy(refinements)
    discord_notification["media_poc_scrum_release_policy"]["community_purpose_contract"][
        "allowed_purpose"
    ] = "product_notification"
    assert any(
        "community operation" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(discord_notification)
    )

    stale_credential = copy.deepcopy(refinements)
    stale_credential["media_poc_scrum_release_policy"]["production_write_authority_contract"][
        "required_bindings"
    ].remove("credential_semantic_digest")
    assert any(
        "本番write" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(stale_credential)
    )

    stale_restart_decision = copy.deepcopy(refinements)
    stale_restart_decision["media_poc_scrum_release_policy"][
        "credential_restart_decision_digest"
    ] = "sha256:" + "0" * 64
    assert any(
        "parent authority" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(stale_restart_decision)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["media_poc_scrum_release_policy"]
    discord_record = next(
        row for row in classified["records"]
        if row["subject_id"] == "DISCORD-COMMUNITY-MARKETING-ROUTE"
    )
    rows = {
        "wordpress_content":{
            "release_unit_id":"wordpress_content","media_id":"wordpress","responsibility_family":"content_database_and_publication",
            "operation_classes":["create","read","update","stable_identity","publish","publication_evidence"],
            "capability_ids":["CAP-MEDIA-WP-CREATE","CAP-MEDIA-WP-READ","CAP-MEDIA-WP-UPDATE","CAP-MEDIA-WP-STABLE-IDENTITY","CAP-MEDIA-WP-PUBLISH","CAP-MEDIA-WP-PUBLICATION-EVIDENCE"],
            "parent_semantic_digests":{"wordpress_content_operations_policy":policy["parent_policy_digests"]["wordpress_content_operations_policy"],"business_profile_authorization_policy":policy["parent_policy_digests"]["business_profile_authorization_policy"],"product_state_authority_policy":policy["parent_policy_digests"]["product_state_authority_policy"],"wordpress_capability_map":requirement_engine._digest(policy["release_unit_classification_contract"]["wordpress_capability_map"]),"selection_event":policy["source_event_digests"]["RDE-000082"]},
            "included_responsibilities":["content_database","content_crud","stable_identity","publication","publication_evidence"],
            "excluded_responsibilities":["platform_maintenance","security_maintenance"],
            "disposition":"selected_requirement_candidate","owner_subject_id":"MEDIA-POC-SCRUM-RELEASE",
            "selection_source_event_ids":["RDE-000082"],"selection_source_digest":policy["source_event_digests"]["RDE-000082"],
            "selection_rationale":"PO selected WordPress content database and publication as the first release unit",
            "production_authority":"prohibited_by_selection","admission_policy_ref":"media_poc_scrum_release_policy.production_write_authority_contract","resume_conditions":[],
        },
        "discord_community":{
            "release_unit_id":"discord_community","media_id":"discord","responsibility_family":"community_marketing",
            "operation_classes":[],"capability_ids":[],
            "parent_semantic_digests":{"discord_community_requirement":policy["parent_requirement_record_digests"]["DISCORD-COMMUNITY-MARKETING-ROUTE"],"community_purpose_contract":requirement_engine._digest(policy["community_purpose_contract"])},
            "included_responsibilities":["community_marketing"],
            "excluded_responsibilities":["product_notification","product_approval","development_pr_notification"],
            "disposition":"deferred","owner_subject_id":"MEDIA-POC-SCRUM-RELEASE",
            "selection_source_event_ids":discord_record["source_event_ids"],
            "selection_source_digest":policy["parent_requirement_record_digests"]["DISCORD-COMMUNITY-MARKETING-ROUTE"],
            "selection_rationale":"community route is distinct from the initial WordPress content release",
            "production_authority":"prohibited_by_selection","admission_policy_ref":"media_poc_scrum_release_policy.production_write_authority_contract",
            "resume_conditions":["community release candidate PO classification","guild/account/operation registration","moderation and crisis authority review"],
        },
    }
    rows_digest = requirement_engine._digest(rows)
    candidate_path = tmp_path/"media-release-candidate.json"
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest":policy["authority_semantic_digest"],
        "release_unit_rows_digest":rows_digest,"selected_release_units":rows,
        "production_write_authorized":False,
        "production_write_attempt_contract":policy["production_write_attempt_contract"],
    }),encoding="utf-8")
    manifest = json.loads(requirement_engine.MANIFEST.read_text(encoding="utf-8"))
    manifest["items"].append({
        "artifact_id":"AUTH-DEVELOPMENT-MEDIA-POC-SCRUM-RELEASE-CANDIDATE",
        "layer":"00-authority","artifact_type":"requirement-authority-candidate",
        "authority_format":"json","authority_status":"active","implementation_input":False,
        "canonical_path":candidate_path.name,
    })
    manifest_path = tmp_path/"manifest.json"
    manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    candidate_content_digest = "sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    classification_event = {
        "event_id":"RDE-900000","sequence":900000,"subject_id":"MEDIA-POC-SCRUM-RELEASE",
        "event_type":"authority_classification_decided","occurred_at":"2026-08-16T00:00:00Z","recorded_at":"2026-08-16T00:00:00Z",
        "actor_principal":"po","references":[],
        "payload":{"approver_principal":"po","decision":"accepted","approved_policy_id":"media_poc_scrum_release_policy","approved_revision":1,"approved_policy_semantic_digest":policy["authority_semantic_digest"],"approved_rows_digest":rows_digest,"approved_candidate_content_digest":candidate_content_digest,"production_write_authorized":False},
    }
    classified_ledger = requirement_engine.requirement_discovery.load_discovery_ledger()
    classified_ledger = copy.deepcopy(classified_ledger)
    classified_ledger["events"].append(classification_event)
    monkeypatch.setattr(requirement_engine.requirement_discovery,"load_discovery_ledger",lambda: classified_ledger)
    policy["classification_state"] = {
        "status":"classified_pending_cutover","selected_release_units":rows,
        "classification_approval":{"decision_id":classification_event["event_id"],"authority":"PO","approver_principal":"po","approved_revision":1,"authority_semantic_digest":policy["authority_semantic_digest"],"release_unit_rows_digest":rows_digest,"candidate_content_digest":candidate_content_digest,"source_event_or_artifact_digest":requirement_engine._digest(classification_event),"production_write_authorized":False},
        "candidate_artifact_binding":{"artifact_id":"AUTH-DEVELOPMENT-MEDIA-POC-SCRUM-RELEASE-CANDIDATE","implementation_input":False,"release_unit_rows_digest":rows_digest,"content_digest":candidate_content_digest},
        "cutover_artifact_bindings":None,"cutover_blocked":True,"production_write_authorized":False,
    }
    monkeypatch.setattr(requirement_engine,"REPO_ROOT",tmp_path)
    monkeypatch.setattr(requirement_engine,"MANIFEST",manifest_path)
    assert requirement_engine.media_poc_scrum_release_policy_faults(classified) == []

    invalid_wp_parent = copy.deepcopy(classified)
    invalid_wp_parent["wordpress_content_operations_policy"]["operations"].remove("publish")
    assert any(
        "WordPress parent" in fault or "semantic member" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(invalid_wp_parent)
    )

    invalid_read_parent = copy.deepcopy(classified)
    invalid_read_parent["business_profile_authorization_policy"]["effect_classes"].remove("read")
    assert any(
        "business profile authorization parent" in fault or "semantic member" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(invalid_read_parent)
    )

    capability_swap = copy.deepcopy(classified)
    capability_swap["media_poc_scrum_release_policy"]["release_unit_classification_contract"][
        "wordpress_capability_map"
    ]["CAP-MEDIA-WP-PUBLISH"]["parent_semantic_members"] = ["delete"]
    assert any(
        "release unit分類" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(capability_swap)
    )

    identity_as_read = copy.deepcopy(classified)
    identity_as_read["media_poc_scrum_release_policy"]["release_unit_classification_contract"][
        "wordpress_capability_map"
    ]["CAP-MEDIA-WP-STABLE-IDENTITY"]["effect"] = "read"
    assert any(
        "release unit分類" in fault or "binding責務" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(identity_as_read)
    )

    selected_discord = copy.deepcopy(classified)
    selected_discord["media_poc_scrum_release_policy"]["classification_state"]["selected_release_units"]["discord_community"]["disposition"] = "selected_requirement_candidate"
    assert any(
        "exact partition" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(selected_discord)
    )

    classified_write = copy.deepcopy(classified)
    classified_write["media_poc_scrum_release_policy"]["classification_state"]["production_write_authorized"] = True
    assert any(
        "write禁止" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(classified_write)
    )

    complete = copy.deepcopy(classified)
    dependency_subjects = {
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE","BUSINESS-PROFILE-AUTHORIZATION",
        "PRODUCT-STATE-AUTHORITY","RATE-QUOTA-COST-AUTHORITY",
        "AUTOMATED-PUBLISHING-ADMISSION","CONTENT-QUALITY-GATE-LEARNING",
        "CONTENT-RISK-CLASSIFICATION","OFFICIAL-API-ROUTE-AUTHORITY",
        "VPS-CREDENTIAL-SECURITY-BOUNDARY",
    }
    by_subject = {row["subject_id"]:row for row in complete["records"]}
    approval_events = []
    policy_semantics = {
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE": ("wordpress_content_operations_policy", requirement_engine._digest(complete["wordpress_content_operations_policy"])),
        "BUSINESS-PROFILE-AUTHORIZATION": ("business_profile_authorization_policy", requirement_engine._digest(complete["business_profile_authorization_policy"])),
        "PRODUCT-STATE-AUTHORITY": ("product_state_authority_policy", requirement_engine._digest(complete["product_state_authority_policy"])),
        "RATE-QUOTA-COST-AUTHORITY": ("rate_quota_cost_policy", requirement_engine._digest(complete["rate_quota_cost_policy"])),
    }
    for index, subject in enumerate(sorted(dependency_subjects), start=900001):
        by_subject[subject]["lifecycle_status"] = "frozen"
        policy_id, semantic_digest = policy_semantics.get(
            subject, (subject, by_subject[subject]["semantic_digest"])
        )
        event = {
            "event_id": f"RDE-{index:06d}", "sequence": index,
            "subject_id": subject, "event_type": "policy_ratification_decided",
            "occurred_at": "2026-08-16T00:00:00Z", "recorded_at": "2026-08-16T00:00:00Z",
            "actor_principal": "po", "references": [],
            "payload": {"approver_principal": "po", "decision": "accepted", "approved_policy_id": policy_id, "approved_revision": by_subject[subject]["revision"], "approved_policy_semantic_digest": semantic_digest},
        }
        approval_events.append(event)
        by_subject[subject]["approval"] = {
            "decision_id": event["event_id"], "authority": "PO", "approver_principal": "po",
            "approved_revision": by_subject[subject]["revision"],
            "approved_policy_id": policy_id,
            "approved_policy_semantic_digest": semantic_digest,
            "source_event_or_artifact_digest": requirement_engine._digest(event),
        }
    complete["provider_policy_bindings"]["status"] = "ratified"
    provider_event = {
        "event_id": "RDE-900100", "sequence": 900100,
        "subject_id": "PROVIDER-NEUTRAL-EXECUTION-POLICY", "event_type": "policy_ratification_decided",
        "occurred_at": "2026-08-16T00:00:00Z", "recorded_at": "2026-08-16T00:00:00Z",
        "actor_principal": "po", "references": [],
        "payload": {"approver_principal": "po", "decision": "accepted", "approved_policy_id": "provider_neutral_execution_policy", "approved_revision": complete["provider_policy_bindings"]["policy_revision"], "approved_policy_semantic_digest": complete["provider_policy_bindings"]["policy_digest"]},
    }
    approval_events.append(provider_event)
    complete["provider_policy_bindings"]["approval"] = {
        "decision_id": provider_event["event_id"], "authority": "PO", "approver_principal": "po",
        "approved_revision": complete["provider_policy_bindings"]["policy_revision"],
        "approved_policy_id": "provider_neutral_execution_policy",
        "approved_policy_semantic_digest": complete["provider_policy_bindings"]["policy_digest"],
        "source_event_or_artifact_digest": requirement_engine._digest(provider_event),
    }
    original_ledger = requirement_engine.requirement_discovery.load_discovery_ledger()
    fixture_ledger = copy.deepcopy(original_ledger)
    fixture_ledger["events"].extend(approval_events)
    monkeypatch.setattr(
        requirement_engine.requirement_discovery, "load_discovery_ledger", lambda: fixture_ledger
    )
    complete_policy = complete["media_poc_scrum_release_policy"]
    for subject in (
        "AUTOMATED-PUBLISHING-ADMISSION","CONTENT-QUALITY-GATE-LEARNING",
        "CONTENT-RISK-CLASSIFICATION","OFFICIAL-API-ROUTE-AUTHORITY",
        "VPS-CREDENTIAL-SECURITY-BOUNDARY",
    ):
        complete_policy["parent_requirement_record_digests"][subject] = requirement_engine._digest(by_subject[subject])
    complete_policy["authority_semantic_digest"] = requirement_engine._digest({
        key:complete_policy[key] for key in (
            "source_event_digests","refinement_record_digest","parent_policy_digests",
            "parent_requirement_record_digests","credential_restart_decision_digest",
            "legacy_media_inventory_digests","captured_po_decision_projection",
            "poc_evidence_contract","community_purpose_contract",
            "release_unit_classification_contract","production_write_authority_contract",
            "production_write_attempt_contract",
        )
    })
    complete_rows = copy.deepcopy(rows)
    complete_rows["wordpress_content"]["parent_semantic_digests"] = {
        "wordpress_content_operations_policy":complete_policy["parent_policy_digests"]["wordpress_content_operations_policy"],
        "business_profile_authorization_policy":complete_policy["parent_policy_digests"]["business_profile_authorization_policy"],
        "product_state_authority_policy":complete_policy["parent_policy_digests"]["product_state_authority_policy"],
        "wordpress_capability_map":requirement_engine._digest(complete_policy["release_unit_classification_contract"]["wordpress_capability_map"]),
        "selection_event":complete_policy["source_event_digests"]["RDE-000082"],
    }
    complete_rows["discord_community"]["parent_semantic_digests"]["discord_community_requirement"] = complete_policy["parent_requirement_record_digests"]["DISCORD-COMMUNITY-MARKETING-ROUTE"]
    complete_rows_digest = requirement_engine._digest(complete_rows)
    complete_state = complete_policy["classification_state"]
    complete_policy["status"] = "ratified"
    complete_state["status"] = "cutover_complete"
    complete_state["selected_release_units"] = complete_rows
    complete_state["cutover_blocked"] = False
    complete_classification_event = next(row for row in fixture_ledger["events"] if row["event_id"] == "RDE-900000")
    complete_classification_event["payload"]["approved_policy_semantic_digest"] = complete_policy["authority_semantic_digest"]
    complete_classification_event["payload"]["approved_rows_digest"] = complete_rows_digest
    complete_state["classification_approval"] = {"decision_id":complete_classification_event["event_id"],"authority":"PO","approver_principal":"po","approved_revision":1,"authority_semantic_digest":complete_policy["authority_semantic_digest"],"release_unit_rows_digest":complete_rows_digest,"candidate_content_digest":None,"source_event_or_artifact_digest":None,"production_write_authorized":False}
    complete_state["candidate_artifact_binding"]["implementation_input"] = True
    complete_state["candidate_artifact_binding"]["release_unit_rows_digest"] = complete_rows_digest
    candidate_path.write_text(json.dumps({
        "authority_semantic_digest":complete_policy["authority_semantic_digest"],
        "release_unit_rows_digest":complete_rows_digest,"selected_release_units":complete_rows,
        "production_write_authorized":False,
        "production_write_attempt_contract":complete_policy["production_write_attempt_contract"],
    }),encoding="utf-8")
    candidate_digest="sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    complete_classification_event["payload"]["approved_candidate_content_digest"] = candidate_digest
    complete_state["classification_approval"]["candidate_content_digest"] = candidate_digest
    complete_state["classification_approval"]["source_event_or_artifact_digest"] = requirement_engine._digest(complete_classification_event)
    complete_state["candidate_artifact_binding"]["content_digest"] = candidate_digest
    manifest["items"][-1]["implementation_input"] = True
    baseline_path=tmp_path/"docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}",encoding="utf-8")
    baseline_digest="sha256:"+hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest),encoding="utf-8")
    manifest_digest="sha256:"+hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    dependency_receipts = {
        subject:{"authority_id":subject,"revision":by_subject[subject]["revision"],"semantic_digest":policy_semantics.get(subject,(subject,by_subject[subject]["semantic_digest"]))[1],"approval_or_ratification_receipt":by_subject[subject]["approval"],"approval_or_ratification_receipt_digest":requirement_engine._digest(by_subject[subject]["approval"]),"frozen":True}
        for subject in sorted(dependency_subjects)
    }
    dependency_receipts["PROVIDER-NEUTRAL-EXECUTION-POLICY"] = {"authority_id":"PROVIDER-NEUTRAL-EXECUTION-POLICY","revision":complete["provider_policy_bindings"]["policy_revision"],"semantic_digest":complete["provider_policy_bindings"]["policy_digest"],"approval_or_ratification_receipt":complete["provider_policy_bindings"]["approval"],"approval_or_ratification_receipt_digest":requirement_engine._digest(complete["provider_policy_bindings"]["approval"]),"frozen":True}
    dependency_digest=requirement_engine._digest(dependency_receipts)
    cutover_event={"event_id":"RDE-900101","sequence":900101,"subject_id":"MEDIA-POC-SCRUM-RELEASE","event_type":"authority_cutover_decided","occurred_at":"2026-08-16T00:00:00Z","recorded_at":"2026-08-16T00:00:00Z","actor_principal":"po","references":[],"payload":{"approver_principal":"po","decision":"accepted","approved_policy_id":"media_poc_scrum_release_policy.cutover","approved_revision":1,"approved_policy_semantic_digest":complete_policy["authority_semantic_digest"],"approved_rows_digest":complete_rows_digest,"approved_candidate_content_digest":candidate_digest,"approved_parent_receipts_digest":dependency_digest,"production_write_authorized":False}}
    fixture_ledger["events"].append(cutover_event)
    complete_state["cutover_artifact_bindings"] = {
        "authority_semantic_digest":complete_policy["authority_semantic_digest"],
        "release_unit_rows_digest":complete_rows_digest,"candidate_content_digest":candidate_digest,
        "parent_dependency_receipts":dependency_receipts,"parent_dependency_receipts_digest":dependency_digest,
        "requirements_cutover_receipt":{"decision_id":cutover_event["event_id"],"authority":"PO","approver_principal":"po","authority_semantic_digest":complete_policy["authority_semantic_digest"],"release_unit_rows_digest":complete_rows_digest,"candidate_content_digest":candidate_digest,"parent_dependency_receipts_digest":dependency_digest,"source_event_or_artifact_digest":requirement_engine._digest(cutover_event),"production_write_authorized":False},
        "manifest_digest":manifest_digest,"baseline_digest":baseline_digest,
        "production_write_authorized":False,"requirements_cutover_write_authorized":False,
        "ci_attestation_policy":{"provider":"github_actions","repository":"RetryYN/HELIX-MARKETING-HARNESS","workflow_ref":"RetryYN/HELIX-MARKETING-HARNESS/.github/workflows/requirements.yml@refs/heads/main","reviewer_principal":"github-actions"},
    }
    original_git=requirement_engine.git
    def media_fixture_git(*args):
        if args[:2] == ("rev-parse","HEAD"):
            return SimpleNamespace(returncode=0,stdout="fixture-head\n")
        if args[:2] == ("rev-parse","HEAD^{tree}"):
            return SimpleNamespace(returncode=0,stdout="fixture-tree\n")
        if args and args[0] == "show":
            fixture_path=tmp_path/str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(returncode=0 if fixture_path.is_file() else 1,stdout=fixture_path.read_text(encoding="utf-8") if fixture_path.is_file() else "")
        return original_git(*args)
    monkeypatch.setattr(requirement_engine,"git",media_fixture_git)
    monkeypatch.setenv("GITHUB_ACTIONS","true")
    monkeypatch.setenv("GITHUB_SHA","fixture-head")
    monkeypatch.setenv("GITHUB_RUN_ID","9001")
    monkeypatch.setenv("GITHUB_REPOSITORY","RetryYN/HELIX-MARKETING-HARNESS")
    monkeypatch.setenv("GITHUB_WORKFLOW_REF","RetryYN/HELIX-MARKETING-HARNESS/.github/workflows/requirements.yml@refs/heads/main")
    monkeypatch.setenv("GITHUB_ACTOR","codex")
    monkeypatch.setattr(requirement_engine,"_completed_media_independent_go",lambda _head,_digests: True)
    assert requirement_engine.media_poc_scrum_release_policy_faults(complete) == []

    monkeypatch.delenv("GITHUB_ACTIONS")
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )
    monkeypatch.setenv("GITHUB_ACTIONS","true")

    cutover_write=copy.deepcopy(complete)
    cutover_write["media_poc_scrum_release_policy"]["classification_state"]["production_write_authorized"] = True
    assert any(
        "write禁止" in fault or "exact partition" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(cutover_write)
    )

    parent_unfrozen=copy.deepcopy(complete)
    by_subject_unfrozen={row["subject_id"]:row for row in parent_unfrozen["records"]}
    by_subject_unfrozen["CONTENT-RISK-CLASSIFICATION"]["lifecycle_status"]="specified"
    assert any(
        "approval receipt付きfrozen" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(parent_unfrozen)
    )

    forged_parent_approval = copy.deepcopy(complete)
    forged_by_subject = {row["subject_id"]: row for row in forged_parent_approval["records"]}
    forged_by_subject["CONTENT-RISK-CLASSIFICATION"]["approval"] = {
        "authority": "PO", "approver_principal": "po", "approved_revision": 1
    }
    assert any(
        "approval receipt付きfrozen" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(forged_parent_approval)
    )

    stale_event_target_ledger = copy.deepcopy(fixture_ledger)
    stale_event = next(
        row for row in stale_event_target_ledger["events"]
        if row["subject_id"] == "CONTENT-RISK-CLASSIFICATION"
        and row["event_type"] == "policy_ratification_decided"
    )
    stale_event["payload"]["approved_policy_semantic_digest"] = "sha256:" + "0" * 64
    monkeypatch.setattr(
        requirement_engine.requirement_discovery,
        "load_discovery_ledger",
        lambda: stale_event_target_ledger,
    )
    assert any(
        "approval receipt付きfrozen" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )

    spoofed_actor_ledger = copy.deepcopy(fixture_ledger)
    spoofed_actor_event = next(
        row for row in spoofed_actor_ledger["events"]
        if row["subject_id"] == "CONTENT-RISK-CLASSIFICATION"
        and row["event_type"] == "policy_ratification_decided"
    )
    spoofed_actor_event["actor_principal"] = "not-po"
    spoofed_actor_event["payload"]["approver_principal"] = "not-po"
    monkeypatch.setattr(
        requirement_engine.requirement_discovery,
        "load_discovery_ledger",
        lambda: spoofed_actor_ledger,
    )
    assert any(
        "approval receipt付きfrozen" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )

    mismatched_actor_ledger = copy.deepcopy(fixture_ledger)
    mismatched_event = next(
        row for row in mismatched_actor_ledger["events"]
        if row["subject_id"] == "CONTENT-RISK-CLASSIFICATION"
        and row["event_type"] == "policy_ratification_decided"
    )
    mismatched_event["payload"]["approver_principal"] = "not-po"
    monkeypatch.setattr(
        requirement_engine.requirement_discovery,
        "load_discovery_ledger",
        lambda: mismatched_actor_ledger,
    )
    assert any(
        "approval receipt付きfrozen" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )

    missing_media_cutover_ledger = copy.deepcopy(fixture_ledger)
    missing_media_cutover_ledger["events"] = [
        row for row in missing_media_cutover_ledger["events"]
        if row["event_id"] != cutover_event["event_id"]
    ]
    monkeypatch.setattr(
        requirement_engine.requirement_discovery,
        "load_discovery_ledger",
        lambda: missing_media_cutover_ledger,
    )
    assert any(
        "cutover PO decision" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )
    monkeypatch.setattr(
        requirement_engine.requirement_discovery,
        "load_discovery_ledger",
        lambda: fixture_ledger,
    )

    monkeypatch.setattr(requirement_engine,"_completed_media_independent_go",lambda _head,_digests: False)
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.media_poc_scrum_release_policy_faults(complete)
    )


def test_strategy_requirement_admission_is_parent_bound_and_unratified(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), refinements) == []

    stale_sr = copy.deepcopy(refinements)
    stale_sr["strategy_requirement_admission_policy"]["source_sr_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "source SR snapshot" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), stale_sr)
    )

    stale_l0 = copy.deepcopy(refinements)
    stale_l0["l0_north_star_authority_normalization_policy"]["legacy_clause_count"] = 14
    assert any(
        "L0 north-star parent digest" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), stale_l0)
    )

    missing_offer_axis = copy.deepcopy(refinements)
    del missing_offer_axis["strategy_requirement_admission_policy"]["meaning_axis_bindings"]["product_offer_authority"]
    assert any(
        "商品/offer/funnel" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), missing_offer_axis)
    )

    paid_phase_reversal = copy.deepcopy(refinements)
    paid_phase_reversal["captured_po_decision_controls"]["POD-20260815-007"]["facts"]["paid_acquisition_phase"] = "initial"
    assert any(
        "商品/offer/funnel" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), paid_phase_reversal)
    )

    early_admission = copy.deepcopy(refinements)
    state = early_admission["strategy_requirement_admission_policy"]["classification_state"]
    state["selected_rows"] = {"SR-17": {"disposition": "initial_candidate"}}
    state["cutover_blocked"] = False
    assert any(
        "未分類なのに" in fault or "未批准" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), early_admission)
    )

    classified = copy.deepcopy(refinements)
    classified["legacy_strategy_quality_meaning_inventory"]["status"] = "classified"
    classified["legacy_strategy_quality_meaning_inventory"]["cutover_blocked"] = False
    classified["l0_north_star_authority_normalization_policy"]["classification_state"].update(
        status="cutover_complete", cutover_blocked=False
    )
    classified["test_id_authority_alignment_policy"]["classification_state"].update(
        status="cutover_complete", cutover_blocked=False
    )
    policy = classified["strategy_requirement_admission_policy"]
    policy["l0_north_star_policy_digest"] = requirement_engine._digest(
        classified["l0_north_star_authority_normalization_policy"]
    )
    policy["test_authority_policy_digest"] = requirement_engine._digest(
        classified["test_id_authority_alignment_policy"]
    )
    state = policy["classification_state"]
    state["status"] = "classified_pending_cutover"
    inventory_rows = classified["legacy_strategy_quality_meaning_inventory"]["meaning_migrations"]
    snapshot = {
        stable_id: value
        for stable_id, value in requirement_engine._legacy_strategy_quality_meaning_snapshot(Ctx()).items()
        if stable_id.startswith("SR-")
    }
    selected = {
        sr_id: {
            "parent_meaning_digest": requirement_engine._digest(inventory_rows[sr_id]),
            "source_sr_digest": requirement_engine._digest(snapshot[sr_id]),
            "disposition": "defer",
            "l0_clause_refs": [],
            "l0_clause_semantic_digests": {},
            "meaning_axis_refs": [],
            "meaning_axis_digests": {},
            "human_judgement_authority": {
                "authority_subject_id": "STRATEGY-REQUIREMENT-ADMISSION",
                "receipt_required": True,
            },
            "descent_targets": {"fn_ids": [], "cmp_ids": [], "ac_ids": []},
            "strategy_test_oracle_refs": [],
            "owner_subject_id": "STRATEGY-REQUIREMENT-ADMISSION",
            "rationale": "fixture defer until PO selects strategy scope",
            "resume_conditions": ["PO selects value, scope, descent and oracle"],
        }
        for sr_id in sorted(snapshot)
    }
    l0_semantics = requirement_engine._l0_candidate_clause_semantics(
        classified["legacy_l0_clause_dispositions"]
    )
    selected["SR-06"].update(
        disposition="initial_candidate",
        l0_clause_refs=["L0V04-DUAL-LOOP"],
        l0_clause_semantic_digests={
            "L0V04-DUAL-LOOP": requirement_engine._digest(l0_semantics["L0V04-DUAL-LOOP"])
        },
        meaning_axis_refs=["research_growth"],
        meaning_axis_digests={
            "research_growth": policy["meaning_axis_bindings"]["research_growth"]["semantic_projection_digest"]
        },
        descent_targets={"fn_ids": [], "cmp_ids": [], "ac_ids": ["AC-SR-01"]},
        strategy_test_oracle_refs=["AC-SR-01"],
        resume_conditions=[],
    )
    state["selected_rows"] = selected
    state["classification_approval"] = {
        "authority": "PO",
        "subject_id": "STRATEGY-REQUIREMENT-ADMISSION",
        "selected_rows_digest": requirement_engine._digest(selected),
        "source_sr_snapshot_digest": requirement_engine._digest(snapshot),
        "parent_meaning_inventory_digest": requirement_engine._digest(
            {key: inventory_rows[key] for key in sorted(snapshot)}
        ),
        "meaning_axis_bindings_digest": requirement_engine._digest(policy["meaning_axis_bindings"]),
    }
    candidate_path = tmp_path / "strategy-admission.json"
    candidate_data = {
        "strategy_admission_row_digests": {
            key: requirement_engine._digest(value) for key, value in selected.items()
        },
        "meaning_axis_bindings": policy["meaning_axis_bindings"],
    }
    candidate_path.write_text(json.dumps(candidate_data, ensure_ascii=False), encoding="utf-8")
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    state["candidate_artifact_binding"] = {
        "artifact_id": "AUTH-DEVELOPMENT-STRATEGY-REQUIREMENT-ADMISSION-CANDIDATE",
        "content_digest": candidate_digest,
    }
    state["classification_approval"]["candidate_content_digest"] = candidate_digest
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "artifact_id": "AUTH-DEVELOPMENT-STRATEGY-REQUIREMENT-ADMISSION-CANDIDATE",
                        "canonical_path": "strategy-admission.json",
                        "layer": "L3-system-requirements",
                        "artifact_type": "strategy-requirement-admission-candidate",
                        "authority_format": "json",
                        "authority_status": "active",
                        "implementation_input": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "MANIFEST", manifest_path)
    monkeypatch.setattr(
        requirement_engine, "l0_north_star_authority_normalization_policy_faults", lambda _: []
    )
    monkeypatch.setattr(
        requirement_engine, "test_id_authority_alignment_policy_faults", lambda _ctx, _data: []
    )
    monkeypatch.setattr(
        requirement_engine, "legacy_strategy_quality_meaning_inventory_faults", lambda _ctx, _data: []
    )
    assert requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), classified) == []

    missing_sr = copy.deepcopy(classified)
    del missing_sr["strategy_requirement_admission_policy"]["classification_state"]["selected_rows"]["SR-19"]
    assert any(
        "SR19件" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), missing_sr)
    )

    complete = copy.deepcopy(classified)
    complete_policy = complete["strategy_requirement_admission_policy"]
    complete_policy["status"] = "ratified"
    complete_state = complete_policy["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    trace_path = tmp_path / "strategy-trace.json"
    trace_data = {
        "strategy_descent_projection": {
            sr_id: {
                "descent_targets": selected[sr_id]["descent_targets"],
                "strategy_test_oracle_refs": selected[sr_id]["strategy_test_oracle_refs"],
            }
            for sr_id in sorted(selected)
        }
    }
    trace_path.write_text(json.dumps(trace_data, ensure_ascii=False), encoding="utf-8")
    trace_digest = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    test_authority_path = tmp_path / "strategy-test-authority.json"
    duplicate_ids = complete["legacy_strategy_ac_ledger_disposition"]["aggregate_duplicate_ids"]
    general_ac = {str(row["id"]): row for row in Ctx().acc}
    authority_oracles = {
        ac_id: {"source_disposition": "general_selected", "oracle": general_ac[ac_id]}
        for ac_id in duplicate_ids
    }
    test_authority_path.write_text(
        json.dumps(
            {
                "ac_sr_oracles": authority_oracles,
                "ac_sr_oracle_row_digests": {
                    ac_id: requirement_engine._digest(row) for ac_id, row in authority_oracles.items()
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    test_authority_digest = "sha256:" + hashlib.sha256(test_authority_path.read_bytes()).hexdigest()
    complete["test_id_authority_alignment_policy"]["classification_state"]["strategy_test_owner"] = {
        "current_authority_artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE"
    }
    complete_policy["test_authority_policy_digest"] = requirement_engine._digest(
        complete["test_id_authority_alignment_policy"]
    )
    review_path = tmp_path / "strategy-go-review.json"
    review = {
        "separation_status": "ci_attested",
        "verdict": "Go",
        "reviewer_principal": "ci-independent-reviewer",
        "author_principal": "requirements-authority-resolver",
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "reviewed_artifact_digests": {
            "strategy": candidate_digest,
            "trace": trace_digest,
            "test_authority": test_authority_digest,
        },
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
    review_digest = "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["items"][0]["implementation_input"] = True
    manifest["items"].extend(
        [
            {"artifact_id": "L3-STRATEGY-DESCENT-TRACE", "canonical_path": "strategy-trace.json"},
            {"artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE", "canonical_path": "strategy-test-authority.json"},
            {"artifact_id": "AUTH-STRATEGY-GO-REVIEW", "canonical_path": "strategy-go-review.json"},
        ]
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    baseline_path = tmp_path / "docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text(json.dumps({"fixture": True}), encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "strategy_json_artifact_id": "AUTH-DEVELOPMENT-STRATEGY-REQUIREMENT-ADMISSION-CANDIDATE",
        "strategy_json_digest": candidate_digest,
        "descent_trace_artifact_id": "L3-STRATEGY-DESCENT-TRACE",
        "descent_trace_digest": trace_digest,
        "test_authority_artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE",
        "test_authority_digest": test_authority_digest,
        "manifest_digest": "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "baseline_digest": "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "same_commit": True,
        "trace_diff_count": 0,
        "independent_go_artifact_id": "AUTH-STRATEGY-GO-REVIEW",
        "independent_go_digest": review_digest,
    }
    original_git = requirement_engine.git

    def strategy_fixture_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="fixture-head\n")
        if args[:2] == ("rev-parse", "HEAD^{tree}"):
            return SimpleNamespace(returncode=0, stdout="fixture-tree\n")
        if args and args[0] == "show":
            path = tmp_path / str(args[1]).removeprefix("HEAD:")
            return SimpleNamespace(
                returncode=0 if path.is_file() else 1,
                stdout=path.read_text(encoding="utf-8") if path.is_file() else "",
            )
        return original_git(*args)

    monkeypatch.setattr(requirement_engine, "git", strategy_fixture_git)
    assert requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), complete) == []

    reversed_trace = copy.deepcopy(complete)
    trace_data["strategy_descent_projection"].pop("SR-19")
    trace_path.write_text(json.dumps(trace_data, ensure_ascii=False), encoding="utf-8")
    reversed_trace["strategy_requirement_admission_policy"]["classification_state"]["cutover_artifact_bindings"]["descent_trace_digest"] = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    assert any(
        "descent trace" in fault
        for fault in requirement_engine.strategy_requirement_admission_policy_faults(Ctx(), reversed_trace)
    )


def test_legacy_critical_responsibilities_are_split_into_current_meaning_owners() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.critical_responsibility_disposition_faults(refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_critical_responsibility_dispositions"] = [
        row for row in missing["legacy_critical_responsibility_dispositions"] if row["legacy_id"] != "FR-76"
    ]
    assert any(
        "critical責務被覆" in fault
        for fault in requirement_engine.critical_responsibility_disposition_faults(missing)
    )

    discord_regression = copy.deepcopy(refinements)
    fr46 = next(
        row
        for row in discord_regression["legacy_critical_responsibility_dispositions"]
        if row["legacy_id"] == "FR-46"
    )
    fr46["disposition"] = "retain"
    fr46["prohibited_inheritance"] = ["個別投稿の毎回承認"]
    faults = requirement_engine.critical_responsibility_disposition_faults(discord_regression)
    assert any("FR-46" in fault for fault in faults)

    api_only_regression = copy.deepcopy(refinements)
    fr77 = next(
        row
        for row in api_only_regression["legacy_critical_responsibility_dispositions"]
        if row["legacy_id"] == "FR-77"
    )
    fr77["disposition"] = "retain"
    assert any(
        "FR-77" in fault
        for fault in requirement_engine.critical_responsibility_disposition_faults(api_only_regression)
    )


def test_semantic_descent_policy_requires_direct_high_risk_axes_and_blocks_design() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.semantic_descent_policy_faults(refinements) == []

    implicit_scope = copy.deepcopy(refinements)
    implicit_scope["semantic_descent_policy"]["dimensions"]["scope_in"]["mode"] = (
        "explicit_inheritance_or_direct"
    )
    assert any(
        "scope_in" in fault for fault in requirement_engine.semantic_descent_policy_faults(implicit_scope)
    )

    design_early = copy.deepcopy(refinements)
    fn_cmp = next(
        edge
        for edge in design_early["semantic_descent_policy"]["edge_contracts"]
        if edge["edge_id"] == "SED-FN-CMP"
    )
    fn_cmp["admission"] = "requirements_candidate"
    assert any(
        "要求freeze前" in fault for fault in requirement_engine.semantic_descent_policy_faults(design_early)
    )

    missing_edge = copy.deepcopy(refinements)
    missing_edge["semantic_descent_policy"]["edge_contracts"] = missing_edge["semantic_descent_policy"][
        "edge_contracts"
    ][1:]
    assert any(
        "edge被覆" in fault for fault in requirement_engine.semantic_descent_policy_faults(missing_edge)
    )


def test_legacy_nfrs_have_business_rooted_or_deferred_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_nfr_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_nfr_dispositions"] = missing["legacy_nfr_dispositions"][:-1]
    assert any(
        "旧NFR被覆" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), missing)
    )

    false_root = copy.deepcopy(refinements)
    nfr9 = next(row for row in false_root["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-9")
    nfr9["disposition"] = "redescent"
    assert any(
        "stable BR/REQ root" in fault
        for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), false_root)
    )

    old_rate = copy.deepcopy(refinements)
    nfr7 = next(row for row in old_rate["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-7")
    nfr7["replacement_meaning"] = "全経路を1〜5秒一様乱数にする"
    assert any(
        "NFR-7" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), old_rate)
    )

    early_paid = copy.deepcopy(refinements)
    nfr6 = next(row for row in early_paid["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-6")
    nfr6["disposition"] = "redescent"
    assert any(
        "NFR-6" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), early_paid)
    )


def test_orphan_fr_sr_requirements_have_exact_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.orphan_requirement_group_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_orphan_requirement_groups"] = missing["legacy_orphan_requirement_groups"][1:]
    assert any(
        "orphan FR/SR被覆" in fault
        for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), missing)
    )

    early_paid = copy.deepcopy(refinements)
    paid = next(
        group for group in early_paid["legacy_orphan_requirement_groups"] if "FR-73" in group["stable_ids"]
    )
    paid["disposition"] = "redescent"
    assert any(
        "FR-73" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), early_paid)
    )

    old_ui = copy.deepcopy(refinements)
    inbox = next(
        group for group in old_ui["legacy_orphan_requirement_groups"] if "FR-76" in group["stable_ids"]
    )
    inbox["replacement_meaning"] = "Discord operational notificationとAPI-only閲覧を維持する"
    assert any(
        "FR-76" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), old_ui)
    )

    premature_strategy = copy.deepcopy(refinements)
    advanced = next(
        group
        for group in premature_strategy["legacy_orphan_requirement_groups"]
        if "SR-17" in group["stable_ids"]
    )
    advanced["resume_conditions"] = []
    assert any(
        "deferred再開条件" in fault
        for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), premature_strategy)
    )


def test_all_legacy_req_ids_have_item_level_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_req_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_req_disposition_groups"][0]["stable_ids"].remove("REQ-001")
    missing["legacy_req_disposition_groups"][0]["item_dispositions"].pop("REQ-001")
    assert any(
        "旧REQ被覆" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), missing)
    )

    no_resume = copy.deepcopy(refinements)
    reporting = next(
        group for group in no_resume["legacy_req_disposition_groups"] if "REQ-025" in group["stable_ids"]
    )
    reporting["deferred_resume_by_id"].pop("REQ-025")
    assert any(
        "deferred ID" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), no_resume)
    )

    old_connector = copy.deepcopy(refinements)
    connector = next(
        group for group in old_connector["legacy_req_disposition_groups"] if "REQ-026" in group["stable_ids"]
    )
    connector["replacement_policy"] = "MCP→browser→paid APIを維持する"
    assert any(
        "REQ-026" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), old_connector)
    )

    old_notification = copy.deepcopy(refinements)
    human = next(
        group
        for group in old_notification["legacy_req_disposition_groups"]
        if "REQ-039" in group["stable_ids"]
    )
    human["replacement_policy"] = "Discordへ通知する"
    assert any(
        "REQ-039" in fault
        for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), old_notification)
    )


def test_all_legacy_br_ids_preserve_value_without_old_runtime_routes() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_br_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_br_disposition_groups"][0]["stable_ids"].remove("BR-A1")
    missing["legacy_br_disposition_groups"][0]["item_dispositions"].pop("BR-A1")
    assert any(
        "旧BR被覆" in fault for fault in requirement_engine.legacy_br_disposition_faults(Ctx(), missing)
    )

    old_approval = copy.deepcopy(refinements)
    human = next(
        group for group in old_approval["legacy_br_disposition_groups"] if "BR-H2" in group["stable_ids"]
    )
    human["replacement_policy"] = "Discordで全投稿を毎回承認する"
    assert any(
        "BR-H2" in fault for fault in requirement_engine.legacy_br_disposition_faults(Ctx(), old_approval)
    )


def test_legacy_br_req_fr_meaning_inventory_is_id_exact_and_fail_closed() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    faults = requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), refinements)
    assert faults == ["旧BR/REQ/FR意味分類候補がPO未承認 remaining=0"]

    stale_source = copy.deepcopy(refinements)
    stale_source["legacy_requirement_meaning_inventory"]["source_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "source digest" in fault
        for fault in requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), stale_source)
    )

    lost_money_binding = copy.deepcopy(refinements)
    lost_money_binding["legacy_requirement_meaning_inventory"]["high_risk_meaning_migrations"]["BR-C4"][
        "retain"
    ] = ["金銭処理を行う"]
    assert any(
        "高risk" in fault
        for fault in requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), lost_money_binding)
    )

    false_completion = copy.deepcopy(refinements)
    false_completion["legacy_requirement_meaning_inventory"]["status"] = "classified"
    assert any(
        "全139 ID" in fault
        for fault in requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), false_completion)
    )

    empty_rows = copy.deepcopy(refinements)
    inventory = empty_rows["legacy_requirement_meaning_inventory"]
    inventory["status"] = "classified"
    inventory["cutover_blocked"] = False
    inventory["meaning_migrations"] = {
        stable_id: None for stable_id in requirement_engine._legacy_requirement_meaning_snapshot(Ctx())
    }
    inventory["meaning_migrations_digest"] = requirement_engine._digest(inventory["meaning_migrations"])
    assert any(
        "field閉集合" in fault
        for fault in requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), empty_rows)
    )

    high_risk_split = copy.deepcopy(empty_rows)
    snapshot = requirement_engine._legacy_requirement_meaning_snapshot(Ctx())
    high_risk_split["legacy_requirement_meaning_inventory"]["meaning_migrations"]["BR-C4"] = {
        "source_digest": requirement_engine._digest(snapshot["BR-C4"]),
        "disposition": "replace",
        "retained_value_clauses": ["金銭処理を記録する"],
        "retained_safety_clauses": [],
        "retained_human_judgement_clauses": [],
        "obsolete_or_prohibited_clauses": ["旧手段を継承しない"],
        "owner_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        "no_retained_reason": None,
        "resume_conditions": [],
    }
    assert any(
        "BR-C4: 通常意味rowが高risk" in fault
        for fault in requirement_engine.legacy_requirement_meaning_inventory_faults(Ctx(), high_risk_split)
    )


def test_legacy_strategy_quality_meaning_inventory_is_exact_and_cutover_blocked() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), refinements) == [
        "旧SR/NFR意味分類候補がPO未承認 remaining=0"
    ]

    missing = copy.deepcopy(refinements)
    del missing["legacy_strategy_quality_meaning_inventory"]["meaning_migrations"]["SR-13"]
    assert any(
        "全30 ID" in fault
        for fault in requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), missing)
    )

    stale = copy.deepcopy(refinements)
    stale["legacy_strategy_quality_meaning_inventory"]["source_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "source digest" in fault
        for fault in requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), stale)
    )

    agent_judge = copy.deepcopy(refinements)
    agent_judge["legacy_strategy_quality_meaning_inventory"]["meaning_migrations"]["SR-13"][
        "retained_human_judgement_clauses"
    ] = ["別agentが企画の採否を決める"]
    assert any(
        "重要意味境界retained_human_judgement_clauses" in fault
        for fault in requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), agent_judge)
    )

    old_s0 = copy.deepcopy(refinements)
    old_s0["legacy_strategy_quality_meaning_inventory"]["meaning_migrations"]["SR-15"][
        "obsolete_or_prohibited_clauses"
    ] = ["旧S0の5点をそのまま初期releaseにする"]
    assert any(
        "SR-15: 重要意味境界" in fault
        for fault in requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), old_s0)
    )

    fixed_unlock = copy.deepcopy(refinements)
    fixed_unlock["legacy_strategy_quality_meaning_inventory"]["meaning_migrations"]["NFR-4"][
        "retained_human_judgement_clauses"
    ] = ["暗号化storeを起動時に自動解除する"]
    assert any(
        "NFR-4: 重要意味境界" in fault
        for fault in requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), fixed_unlock)
    )

    classified = copy.deepcopy(refinements)
    inventory = classified["legacy_strategy_quality_meaning_inventory"]
    inventory["status"] = "classified"
    inventory["cutover_blocked"] = False
    inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": inventory["source_snapshot_digest"],
        "meaning_migrations_digest": inventory["meaning_migrations_digest"],
    }
    assert requirement_engine.legacy_strategy_quality_meaning_inventory_faults(Ctx(), classified) == []


def test_legacy_mr_meaning_inventory_is_exact_and_cutover_blocked() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_mr_meaning_inventory_faults(refinements) == [
        "旧MR意味分類候補がPO未承認 remaining=0"
    ]

    missing = copy.deepcopy(refinements)
    del missing["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-DC-1"]
    assert any("全54 ID" in fault for fault in requirement_engine.legacy_mr_meaning_inventory_faults(missing))

    stale = copy.deepcopy(refinements)
    stale["legacy_mr_meaning_inventory"]["source_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "source digest" in fault for fault in requirement_engine.legacy_mr_meaning_inventory_faults(stale)
    )

    discord_notice = copy.deepcopy(refinements)
    discord_notice["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-DC-1"][
        "retained_safety_clauses"
    ] = ["Discordを製品通知と投稿承認にも共用する"]
    assert any(
        "MR-DC-1: 重要MR意味境界" in fault
        for fault in requirement_engine.legacy_mr_meaning_inventory_faults(discord_notice)
    )

    line_browser_write = copy.deepcopy(refinements)
    line_browser_write["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-LINE-3"][
        "retained_safety_clauses"
    ] = ["browser writeを第一経路にする"]
    assert any(
        "MR-LINE-3: 重要MR意味境界" in fault
        for fault in requirement_engine.legacy_mr_meaning_inventory_faults(line_browser_write)
    )

    x_playwright_write = copy.deepcopy(refinements)
    x_playwright_write["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-X-3"][
        "retained_safety_clauses"
    ] = ["Playwrightで無人writeする"]
    assert any(
        "MR-X-3: 重要MR意味境界" in fault
        for fault in requirement_engine.legacy_mr_meaning_inventory_faults(x_playwright_write)
    )

    money_without_owner = copy.deepcopy(refinements)
    money_without_owner["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-STRIPE-1"][
        "retained_human_judgement_clauses"
    ] = ["AIが全money operationを判断する"]
    assert any(
        "MR-STRIPE-1: 重要MR意味境界" in fault
        for fault in requirement_engine.legacy_mr_meaning_inventory_faults(money_without_owner)
    )

    mixed_wp_authority = copy.deepcopy(refinements)
    mixed_wp_authority["legacy_mr_meaning_inventory"]["meaning_migrations"]["MR-WP-1"][
        "owner_subject_ids"
    ].append("WORDPRESS-SECURITY-MAINTENANCE-RELEASE")
    assert any(
        "MR-WP-1: WP operation/effect owner binding" in fault
        for fault in requirement_engine.legacy_mr_meaning_inventory_faults(mixed_wp_authority)
    )

    classified = copy.deepcopy(refinements)
    inventory = classified["legacy_mr_meaning_inventory"]
    inventory["status"] = "classified"
    inventory["cutover_blocked"] = False
    inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": inventory["source_snapshot_digest"],
        "meaning_migrations_digest": inventory["meaning_migrations_digest"],
    }
    assert requirement_engine.legacy_mr_meaning_inventory_faults(classified) == []


def test_legacy_fn_meaning_inventory_is_parent_digest_bound_and_cutover_blocked() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), refinements) == [
        "旧FN意味分類候補がPO未承認 remaining=0"
    ]

    missing = copy.deepcopy(refinements)
    del missing["legacy_fn_meaning_inventory"]["meaning_migrations"]["FN-110"]
    assert any(
        "全61 ID" in fault for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), missing)
    )

    stale_parent = copy.deepcopy(refinements)
    stale_parent["legacy_fn_meaning_inventory"]["meaning_migrations"]["FN-202"]["parent_semantic_digest"] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "FN-202: parent semantic digest" in fault
        for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), stale_parent)
    )

    discord_stop = copy.deepcopy(refinements)
    discord_stop["legacy_fn_meaning_inventory"]["meaning_migrations"]["FN-110"]["direct_semantics"][
        "side_effects"
    ] = ["external_write"]
    assert any(
        "FN-110: 重要FN意味境界" in fault
        for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), discord_stop)
    )

    auto_activation = copy.deepcopy(refinements)
    auto_activation["legacy_fn_meaning_inventory"]["meaning_migrations"]["FN-410"]["direct_semantics"][
        "human_judgement"
    ] = ["機械基準だけでscope activationする"]
    assert any(
        "FN-410: 重要FN意味境界" in fault
        for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), auto_activation)
    )

    orphan_enabled = copy.deepcopy(refinements)
    orphan_enabled["legacy_fn_meaning_inventory"]["meaning_migrations"]["FN-413"]["disposition"] = (
        "inherit_and_redescent"
    )
    assert any(
        "FN-413: stable parentなし" in fault
        for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), orphan_enabled)
    )

    fn_only_classified = copy.deepcopy(refinements)
    fn_inventory = fn_only_classified["legacy_fn_meaning_inventory"]
    fn_inventory["status"] = "classified"
    fn_inventory["cutover_blocked"] = False
    fn_inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": fn_inventory["source_snapshot_digest"],
        "meaning_migrations_digest": fn_inventory["meaning_migrations_digest"],
    }
    assert any(
        "親inventory" in fault and "classifiedでない" in fault
        for fault in requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), fn_only_classified)
    )

    classified = copy.deepcopy(refinements)
    for key in (
        "legacy_requirement_meaning_inventory",
        "legacy_strategy_quality_meaning_inventory",
        "legacy_mr_meaning_inventory",
    ):
        parent = classified[key]
        parent["status"] = "classified"
        parent["cutover_blocked"] = False
        parent["meaning_migrations_digest"] = requirement_engine._digest(parent["meaning_migrations"])
        parent["classification_approval"] = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "approved_at": "2026-08-15T00:00:00+09:00",
            "source_snapshot_digest": parent["source_snapshot_digest"],
            "meaning_migrations_digest": parent["meaning_migrations_digest"],
        }
    inventory = classified["legacy_fn_meaning_inventory"]
    inventory["status"] = "classified"
    inventory["cutover_blocked"] = False
    inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": inventory["source_snapshot_digest"],
        "meaning_migrations_digest": inventory["meaning_migrations_digest"],
    }
    assert requirement_engine.legacy_fn_meaning_inventory_faults(Ctx(), classified) == []


def test_legacy_ac_meaning_inventory_is_oracle_and_parent_digest_bound() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), refinements) == [
        "旧AC意味分類候補がPO未承認 remaining=0"
    ]

    missing = copy.deepcopy(refinements)
    del missing["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-16-1"]
    assert any(
        "全252 ID" in fault for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), missing)
    )

    stale_fn = copy.deepcopy(refinements)
    stale_fn["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-1"]["fn_semantic_digest"] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "AC-46-1: FN semantic digest" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), stale_fn)
    )

    discord_escalation = copy.deepcopy(refinements)
    discord_escalation["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-16-1"]["oracle_delta"][
        "scope_out"
    ] = ["Discord承認transportへ異常通知する"]
    assert any(
        "AC-16-1: 重要AC意味境界" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), discord_escalation)
    )

    machine_activation = copy.deepcopy(refinements)
    machine_activation["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-75-1"]["oracle_delta"][
        "human_judgement"
    ] = ["preflightが自動判断する"]
    assert any(
        "AC-75-1: 重要AC意味境界" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), machine_activation)
    )

    family_gap = copy.deepcopy(refinements)
    family_gap["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-2"]["critical_family_refs"] = []
    assert any(
        "AC-46-2: critical family意味継承" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), family_gap)
    )

    family_reversal = copy.deepcopy(refinements)
    family_reversal["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-2"]["family_compliance"][
        "notification-purpose-separation"
    ]["prohibited_ack"] = ["Discordでdecisionする"]
    assert any(
        "AC-46-2: critical family compliance" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), family_reversal)
    )

    family_delta_reversal = copy.deepcopy(refinements)
    reversed_row = family_delta_reversal["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-2"]
    reversed_row["oracle_delta"]["scope_in"] = ["Discordでdecisionする"]
    reversed_row["no_direct_oracle_reason"] = None
    assert any(
        "AC-46-2: family control再降下前" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), family_delta_reversal)
    )

    representative_reversal = copy.deepcopy(refinements)
    representative_reversal["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-1"]["oracle_delta"][
        "scope_in"
    ].append("Discordでdecisionする")
    assert any(
        "AC-46-1: family代表oracle delta" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), representative_reversal)
    )

    unknown_owner = copy.deepcopy(refinements)
    unknown_owner["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-26-1"]["owner_bindings"][0][
        "owner_subject_id"
    ] = "UNKNOWN-OWNER"
    assert any(
        "AC-26-1: AC owner bindingのeffect又はowner" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), unknown_owner)
    )

    missing_state_owner = copy.deepcopy(refinements)
    missing_state_owner["legacy_ac_meaning_inventory"]["meaning_migrations"]["AC-46-1"]["owner_bindings"] = []
    assert any(
        "AC-46-1: allowed effectがownerへexactly束縛" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), missing_state_owner)
    )

    missing_polarity = copy.deepcopy(refinements)
    missing_polarity["legacy_ac_meaning_inventory"]["polarity_gap_dispositions"] = []
    assert any(
        "3極性gap台帳" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), missing_polarity)
    )

    stale_strategy = copy.deepcopy(refinements)
    stale_strategy["legacy_ac_meaning_inventory"]["strategy_ac_ledger_disposition_digest"] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "strategy二重台帳処遇digest" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), stale_strategy)
    )

    ac_only_classified = copy.deepcopy(refinements)
    ac_inventory = ac_only_classified["legacy_ac_meaning_inventory"]
    ac_inventory["status"] = "classified"
    ac_inventory["cutover_blocked"] = False
    ac_inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": ac_inventory["source_snapshot_digest"],
        "meaning_migrations_digest": ac_inventory["meaning_migrations_digest"],
        "polarity_gap_dispositions_digest": ac_inventory["polarity_gap_dispositions_digest"],
    }
    assert any(
        "親inventory" in fault and "承認済みでない" in fault
        for fault in requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), ac_only_classified)
    )

    classified = copy.deepcopy(refinements)
    for key in (
        "legacy_requirement_meaning_inventory",
        "legacy_strategy_quality_meaning_inventory",
        "legacy_mr_meaning_inventory",
        "legacy_fn_meaning_inventory",
    ):
        parent = classified[key]
        parent["status"] = "classified"
        parent["cutover_blocked"] = False
        parent["meaning_migrations_digest"] = requirement_engine._digest(parent["meaning_migrations"])
        parent["classification_approval"] = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "approved_at": "2026-08-15T00:00:00+09:00",
            "source_snapshot_digest": parent["source_snapshot_digest"],
            "meaning_migrations_digest": parent["meaning_migrations_digest"],
        }
    inventory = classified["legacy_ac_meaning_inventory"]
    inventory["status"] = "classified"
    inventory["cutover_blocked"] = False
    for gap in inventory["polarity_gap_dispositions"]:
        gap["disposition"] = "po_approved_na"
    inventory["polarity_gap_dispositions_digest"] = requirement_engine._digest(
        inventory["polarity_gap_dispositions"]
    )
    inventory["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": inventory["source_snapshot_digest"],
        "meaning_migrations_digest": inventory["meaning_migrations_digest"],
        "polarity_gap_dispositions_digest": inventory["polarity_gap_dispositions_digest"],
    }
    assert requirement_engine.legacy_ac_meaning_inventory_faults(Ctx(), classified) == []


def test_legacy_tc_meaning_inventory_is_parent_ac_and_group_bound() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), refinements) == [
        "旧TC意味分類候補がPO未承認 remaining=0"
    ]
    missing = copy.deepcopy(refinements)
    del missing["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-16-1"]
    assert any(
        "全258 ID" in fault for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), missing)
    )
    stale_ac = copy.deepcopy(refinements)
    stale_ac["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-46-1"]["parent_ac_semantic_digest"] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "TCC-46-1: parent AC semantic digest" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), stale_ac)
    )
    old_oracle = copy.deepcopy(refinements)
    old_oracle["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-46-1"]["test_oracle_delta"][
        "expected_result"
    ] = ["Discord interactionでapproved"]
    assert any(
        "TCC-46-1: 親再降下前にTC固有oracle" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), old_oracle)
    )
    missing_money_group = copy.deepcopy(refinements)
    missing_money_group["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-73-2"][
        "critical_group_refs"
    ].remove("money-authority")
    assert any(
        "TCC-73-2: TC critical group継承" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), missing_money_group)
    )
    missing_credential_group = copy.deepcopy(refinements)
    missing_credential_group["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-77-3"][
        "critical_group_refs"
    ].remove("credential-boundary")
    assert any(
        "TCC-77-3: TC critical group継承" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), missing_credential_group)
    )
    stale_oracle = copy.deepcopy(refinements)
    stale_oracle["legacy_tc_meaning_inventory"]["meaning_migrations"]["TCC-NFR-02"][
        "source_oracle_digest"
    ] = "sha256:" + "0" * 64
    assert any(
        "TCC-NFR-02: source test oracle digest" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), stale_oracle)
    )

    restart_reversal = copy.deepcopy(refinements)
    restart_reversal["legacy_tc_meaning_inventory"]["critical_group_policies"]["credential-boundary"][
        "unlock"
    ] = "pending_po"
    assert any(
        "TC critical group policy" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), restart_reversal)
    )

    stale_restart_binding = copy.deepcopy(refinements)
    stale_restart_binding["legacy_tc_meaning_inventory"]["credential_restart_decision_digest"] = (
        "sha256:" + "0" * 64
    )
    assert any(
        "VPS再起動判断" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), stale_restart_binding)
    )
    changed_source = Ctx()
    changed_tcs = changed_source.tcc
    nfr_tc = next(item for item in changed_tcs if item["id"] == "TCC-NFR-02")
    nfr_tc["aspect_assertions"]["NFR-2:brief-digest"] = "改変されたassertion"
    changed_source_faults = requirement_engine.legacy_tc_meaning_inventory_faults(changed_source, refinements)
    assert any("TCC-NFR-02: source test oracle digest" in fault for fault in changed_source_faults)
    tc_only = copy.deepcopy(refinements)
    tc = tc_only["legacy_tc_meaning_inventory"]
    tc["status"] = "classified"
    tc["cutover_blocked"] = False
    tc["classification_approval"] = {
        "authority": "PO",
        "approver_principal": "po",
        "approved_revision": 1,
        "approved_at": "2026-08-15T00:00:00+09:00",
        "source_snapshot_digest": tc["source_snapshot_digest"],
        "meaning_migrations_digest": tc["meaning_migrations_digest"],
        "parent_ac_inventory_digest": requirement_engine._digest(tc_only["legacy_ac_meaning_inventory"]),
    }
    assert any(
        "親AC inventory" in fault
        for fault in requirement_engine.legacy_tc_meaning_inventory_faults(Ctx(), tc_only)
    )


def test_all_legacy_media_brs_are_capability_candidates_not_permissions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_media_br_disposition_faults(refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_media_br_dispositions"] = missing["legacy_media_br_dispositions"][1:]
    assert any(
        "media BR被覆" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(missing)
    )

    discord_notice = copy.deepcopy(refinements)
    discord = next(row for row in discord_notice["legacy_media_br_dispositions"] if row["media_id"] == "dc")
    discord["route_policy"] = "製品通知と投稿承認に使う"
    assert any(
        "dc" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(discord_notice)
    )

    x_browser = copy.deepcopy(refinements)
    x = next(row for row in x_browser["legacy_media_br_dispositions"] if row["media_id"] == "x")
    x["route_policy"] = "Playwrightで無人投稿する"
    assert any("x" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(x_browser))

    duplicate_media = copy.deepcopy(refinements)
    duplicate_media["legacy_media_br_dispositions"].append(
        copy.deepcopy(duplicate_media["legacy_media_br_dispositions"][0])
    )
    assert any(
        "一媒体一行" in fault
        for fault in requirement_engine.legacy_media_br_disposition_faults(duplicate_media)
    )

    weak_design_source = copy.deepcopy(refinements)
    ds = next(row for row in weak_design_source["legacy_media_br_dispositions"] if row["media_id"] == "ds")
    ds["route_policy"] = "デザインを同期する"
    assert any(
        "ds" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(weak_design_source)
    )

    missing_item = copy.deepcopy(refinements)
    missing_item["legacy_media_br_item_dispositions"].pop("BR-M-DC-1")
    assert any(
        "ID別処置" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(missing_item)
    )

    stale_source = copy.deepcopy(refinements)
    stale_source["legacy_media_br_source_digests"]["line"] = "sha256:" + "0" * 64
    assert any(
        "semantic digest" in fault
        for fault in requirement_engine.legacy_media_br_disposition_faults(stale_source)
    )

    stale_item = copy.deepcopy(refinements)
    stale_item["legacy_media_br_item_digests"]["BR-M-DC-1"] = "sha256:" + "0" * 64
    assert any(
        "70 ID" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(stale_item)
    )

    lost_meaning = copy.deepcopy(refinements)
    lost_meaning["legacy_media_br_meaning_migrations"]["BR-M-DC-1"]["retained_meaning"] = "Botを使う"
    assert any(
        "meaning移送" in fault
        for fault in requirement_engine.legacy_media_br_disposition_faults(lost_meaning)
    )

    lost_retained_clause = copy.deepcopy(refinements)
    lost_retained_clause["legacy_media_br_meaning_migrations"]["BR-M-DC-1"]["retained_safety_clauses"] = []
    assert any(
        "保持価値・安全制約の閉集合" in fault
        for fault in requirement_engine.legacy_media_br_disposition_faults(lost_retained_clause)
    )

    invented_retained_clause = copy.deepcopy(refinements)
    invented_retained_clause["legacy_media_br_meaning_migrations"]["BR-M-GENAI-4"][
        "retained_value_clauses"
    ].append("Codex CLIを製品必須経路にする")
    assert any(
        "保持価値・安全制約の閉集合" in fault
        for fault in requirement_engine.legacy_media_br_disposition_faults(invented_retained_clause)
    )


def test_provider_route_policy_is_typed_and_prohibits_unattended_consumer_ui() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.provider_neutral_execution_policy_faults(refinements) == []

    unsafe = copy.deepcopy(refinements)
    unsafe["provider_neutral_execution_policy"]["prohibited_routes"] = []
    assert requirement_engine.provider_neutral_execution_policy_faults(unsafe)

    unbound = copy.deepcopy(refinements)
    unbound["provider_policy_bindings"]["media_ids"].remove("genai")
    assert any(
        "revision/digest束縛" in fault
        for fault in requirement_engine.provider_neutral_execution_policy_faults(unbound)
    )

    fake_ratified = copy.deepcopy(refinements)
    fake_ratified["provider_policy_bindings"]["status"] = "ratified"
    assert any(
        "PO receipt" in fault
        for fault in requirement_engine.provider_neutral_execution_policy_faults(fake_ratified)
    )


def test_all_legacy_frs_have_exact_current_requirement_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_fr_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_fr_disposition_groups"][0]["stable_ids"].remove("FR-11")
    missing["legacy_fr_disposition_groups"][0]["item_dispositions"].pop("FR-11")
    assert any(
        "旧FR被覆" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), missing)
    )

    missing_resume = copy.deepcopy(refinements)
    connectors = next(
        group for group in missing_resume["legacy_fr_disposition_groups"] if "FR-45" in group["stable_ids"]
    )
    connectors["deferred_resume_by_id"].pop("FR-45")
    assert any(
        "deferred ID" in fault
        for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), missing_resume)
    )

    old_approval = copy.deepcopy(refinements)
    connectors = next(
        group for group in old_approval["legacy_fr_disposition_groups"] if "FR-46" in group["stable_ids"]
    )
    connectors["replacement_policy"] = "Discordで投稿を毎回承認する"
    assert any(
        "FR-46" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), old_approval)
    )

    api_only = copy.deepcopy(refinements)
    ui = next(group for group in api_only["legacy_fr_disposition_groups"] if "FR-77" in group["stable_ids"])
    ui["replacement_policy"] = "read-only APIだけを提供する"
    assert any("FR-77" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), api_only))


def test_legacy_fn_ac_tc_cannot_claim_current_design_or_acceptance() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_derived_contract_faults(Ctx(), refinements) == []

    wrong_digest = copy.deepcopy(refinements)
    fn = next(row for row in wrong_digest["legacy_derived_contract_policy"] if row["kind"] == "FN")
    fn["stable_id_digest"] = "sha256:" + "0" * 64
    assert any(
        "FN" in fault and "digest" in fault
        for fault in requirement_engine.legacy_derived_contract_faults(Ctx(), wrong_digest)
    )

    current_acceptance = copy.deepcopy(refinements)
    ac = next(row for row in current_acceptance["legacy_derived_contract_policy"] if row["kind"] == "AC")
    ac["disposition"] = "current_acceptance_evidence"
    assert any(
        "AC" in fault and "defer" in fault
        for fault in requirement_engine.legacy_derived_contract_faults(Ctx(), current_acceptance)
    )


def test_legacy_test_ids_and_duplicate_strategy_ac_have_explicit_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_test_authority_disposition_faults(Ctx(), refinements) == []

    missing_test = copy.deepcopy(refinements)
    missing_test["legacy_test_id_dispositions"] = missing_test["legacy_test_id_dispositions"][1:]
    assert any(
        "旧TC ID disposition" in fault
        for fault in requirement_engine.legacy_test_authority_disposition_faults(Ctx(), missing_test)
    )

    guessed_mapping = copy.deepcopy(refinements)
    guessed_mapping["legacy_test_id_dispositions"][0]["candidate_target_ids"] = ["TCC-001"]
    assert any(
        "PO未決" in fault
        for fault in requirement_engine.legacy_test_authority_disposition_faults(Ctx(), guessed_mapping)
    )

    unioned_ac = copy.deepcopy(refinements)
    unioned_ac["legacy_strategy_ac_ledger_disposition"]["disposition"] = "union_as_current"
    assert any(
        "legacy限定" in fault
        for fault in requirement_engine.legacy_test_authority_disposition_faults(Ctx(), unioned_ac)
    )

    weakened_claims = copy.deepcopy(refinements)
    weakened_claims["legacy_strategy_ac_ledger_disposition"]["prohibited_claims"] = ["使用しない"]
    assert any(
        "非union・非受入" in fault
        for fault in requirement_engine.legacy_test_authority_disposition_faults(Ctx(), weakened_claims)
    )


def test_test_id_authority_alignment_policy_is_two_track_and_fail_closed(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), refinements) == []

    stale = copy.deepcopy(refinements)
    stale["legacy_test_id_dispositions"] = stale["legacy_test_id_dispositions"][1:]
    assert any(
        "14 ID" in fault or "snapshot digest" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), stale)
    )

    early = copy.deepcopy(refinements)
    early["test_id_authority_alignment_policy"]["status"] = "ratified"
    assert any(
        "未分類" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), early)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["test_id_authority_alignment_policy"]
    state = policy["classification_state"]
    state["status"] = "classified_pending_cutover"
    mapping = {}
    for source in classified["legacy_test_id_dispositions"]:
        mapping[source["legacy_test_id"]] = {
            "parent_row_digest": requirement_engine._digest(source),
            "referenced_by": source["referenced_by"],
            "disposition": "abolish",
            "target_test_ids": [],
            "target_oracle_semantic_digests": {},
            "merge_group_id": None,
            "collision_source_set_digest": None,
            "owner_subject_id": "TEST-ID-AUTHORITY-ALIGNMENT",
            "rationale": "PO fixture abolishes unresolved legacy alias",
            "resume_conditions": [],
            "du_trace_impact": ["remove legacy alias and regenerate DU trace"],
        }
    state["legacy_tc_mapping_rows"] = mapping
    strategy_snapshot = classified["legacy_strategy_ac_ledger_disposition"]
    authority_path = tmp_path / "strategy-test-authority.json"
    authority_oracles = {
        stable_id: {
            "source_disposition": "new_oracle",
            "oracle": {
                "target_requirement_ids": ["SR-06"],
                "polarity": "normal",
                "given": f"{stable_id} approved fixture input",
                "when": "the strategy behavior is exercised",
                "then": "the approved observable result is produced",
                "failure_oracle": "invalid or stale input is rejected without authority mutation",
                "recovery_oracle": "recovery requires a new authorized attempt and evidence",
                "evidence_dimensions": ["subject_digest", "actor", "result", "failure", "recovery"],
                "phase_disposition": "redescent",
                "owner_subject_id": "TEST-ID-AUTHORITY-ALIGNMENT",
                "resume_conditions": [],
            },
        }
        for stable_id in strategy_snapshot["aggregate_duplicate_ids"]
    }
    authority_projection = {
        stable_id: requirement_engine._digest(row)
        for stable_id, row in authority_oracles.items()
    }
    authority_path.write_text(
        json.dumps(
            {
                "ac_sr_oracles": authority_oracles,
                "ac_sr_oracle_row_digests": authority_projection,
            }
        ),
        encoding="utf-8",
    )
    authority_digest = "sha256:" + hashlib.sha256(authority_path.read_bytes()).hexdigest()
    strategy_owner = {
        "parent_strategy_snapshot_digest": requirement_engine._digest(strategy_snapshot),
        "duplicate_ids": strategy_snapshot["aggregate_duplicate_ids"],
        "current_authority_artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE",
        "current_authority_content_digest": authority_digest,
        "duplicate_oracle_projection_digest": requirement_engine._digest(authority_projection),
        "general_legacy_artifact_id": "L3-AC-CONTRACTS",
        "strategy_legacy_artifact_id": "L3-AC-SR",
        "prohibited_union_claims": strategy_snapshot["prohibited_claims"],
        "supersession_scope": ["AC-SR duplicate IDs and their test authority"],
    }
    state["strategy_test_owner"] = strategy_owner
    state["classification_approval"] = {
        "authority": "PO",
        "subject_id": "TEST-ID-AUTHORITY-ALIGNMENT",
        "legacy_snapshot_digest": requirement_engine._digest(classified["legacy_test_id_dispositions"]),
        "strategy_snapshot_digest": requirement_engine._digest(strategy_snapshot),
        "mapping_rows_digest": requirement_engine._digest(mapping),
        "strategy_owner_digest": requirement_engine._digest(strategy_owner),
    }
    candidate_path = tmp_path / "test-id-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "legacy_tc_mapping_row_digests": {
                    key: requirement_engine._digest(value) for key, value in mapping.items()
                },
                "strategy_test_owner_digest": requirement_engine._digest(strategy_owner),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "artifact_id": "AUTH-DEVELOPMENT-TEST-ID-AUTHORITY-CANDIDATE",
                        "canonical_path": "test-id-candidate.json",
                        "layer": "00-authority",
                        "artifact_type": "test-id-authority-candidate",
                        "authority_format": "json",
                        "authority_status": "active",
                        "implementation_input": False,
                    },
                    {
                        "artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE",
                        "canonical_path": "strategy-test-authority.json",
                        "layer": "L3-system-requirements",
                        "artifact_type": "strategy-test-authority",
                        "authority_format": "json",
                        "authority_status": "active",
                        "implementation_input": False,
                    },
                    {
                        "artifact_id": "L3-AC-CONTRACTS",
                        "canonical_path": "docs/L3-system-requirements/canonical/acceptance/ac-contracts.json",
                        "implementation_input": False,
                        "applicability_status": "revalidation_required",
                    },
                    {
                        "artifact_id": "L3-AC-SR",
                        "canonical_path": "docs/L3-system-requirements/canonical/strategy/ac-sr.json",
                        "implementation_input": False,
                        "applicability_status": "revalidation_required",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    state["candidate_artifact_binding"] = {
        "artifact_id": "AUTH-DEVELOPMENT-TEST-ID-AUTHORITY-CANDIDATE",
        "content_digest": candidate_digest,
    }
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "MANIFEST", manifest_path)
    assert requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), classified) == []

    wrong_owner = copy.deepcopy(classified)
    next(iter(wrong_owner["test_id_authority_alignment_policy"]["classification_state"]["legacy_tc_mapping_rows"].values()))["owner_subject_id"] = "UNKNOWN"
    assert any(
        "owner又はrationale" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), wrong_owner)
    )

    unknown_target = copy.deepcopy(classified)
    target_row = next(iter(unknown_target["test_id_authority_alignment_policy"]["classification_state"]["legacy_tc_mapping_rows"].values()))
    target_row.update(disposition="merge", target_test_ids=["TCC-UNKNOWN"], target_oracle_semantic_digests={}, merge_group_id="TMG-UNKNOWN", collision_source_set_digest=requirement_engine._digest([next(iter(mapping))]))
    assert any(
        "target TCC" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), unknown_target)
    )

    collision = copy.deepcopy(classified)
    collision_rows = collision["test_id_authority_alignment_policy"]["classification_state"]["legacy_tc_mapping_rows"]
    collision_ids = list(collision_rows)[:2]
    target_id, target_semantics = next(
        iter(collision["legacy_tc_meaning_inventory"]["meaning_migrations"].items())
    )
    for index, legacy_id in enumerate(collision_ids):
        collision_rows[legacy_id].update(
            disposition="merge",
            target_test_ids=[target_id],
            target_oracle_semantic_digests={target_id: requirement_engine._digest(target_semantics)},
            merge_group_id=f"TMG-{index}",
            collision_source_set_digest=requirement_engine._digest(collision_ids),
        )
    assert any(
        "many-to-one" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), collision)
    )

    unioned = copy.deepcopy(classified)
    unioned["test_id_authority_alignment_policy"]["classification_state"]["strategy_test_owner"]["current_authority_artifact_id"] = "L3-AC-SR"
    assert any(
        "単一の新実在artifact" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), unioned)
    )

    reversed_oracle = copy.deepcopy(classified)
    authority_data = json.loads(authority_path.read_text(encoding="utf-8"))
    first_oracle = next(iter(authority_data["ac_sr_oracles"].values()))
    first_oracle["source_disposition"] = "union_both"
    authority_data["ac_sr_oracle_row_digests"] = {
        stable_id: requirement_engine._digest(row)
        for stable_id, row in authority_data["ac_sr_oracles"].items()
    }
    authority_path.write_text(json.dumps(authority_data), encoding="utf-8")
    reversed_owner = reversed_oracle["test_id_authority_alignment_policy"]["classification_state"]["strategy_test_owner"]
    reversed_owner["current_authority_content_digest"] = "sha256:" + hashlib.sha256(authority_path.read_bytes()).hexdigest()
    reversed_owner["duplicate_oracle_projection_digest"] = requirement_engine._digest(
        authority_data["ac_sr_oracle_row_digests"]
    )
    assert any(
        "source disposition" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), reversed_oracle)
    )

    invalid_semantics = copy.deepcopy(classified)
    authority_path.write_text(
        json.dumps(
            {
                "ac_sr_oracles": authority_oracles,
                "ac_sr_oracle_row_digests": authority_projection,
            }
        ),
        encoding="utf-8",
    )
    authority_data = json.loads(authority_path.read_text(encoding="utf-8"))
    first_oracle = next(iter(authority_data["ac_sr_oracles"].values()))["oracle"]
    first_oracle["target_requirement_ids"] = ["SR-999"]
    first_oracle["evidence_dimensions"].append("unknown_dimension")
    first_oracle["phase_disposition"] = "defer"
    first_oracle["resume_conditions"] = []
    authority_data["ac_sr_oracle_row_digests"] = {
        stable_id: requirement_engine._digest(row)
        for stable_id, row in authority_data["ac_sr_oracles"].items()
    }
    authority_path.write_text(json.dumps(authority_data), encoding="utf-8")
    invalid_owner = invalid_semantics["test_id_authority_alignment_policy"]["classification_state"]["strategy_test_owner"]
    invalid_owner["current_authority_content_digest"] = "sha256:" + hashlib.sha256(authority_path.read_bytes()).hexdigest()
    invalid_owner["duplicate_oracle_projection_digest"] = requirement_engine._digest(
        authority_data["ac_sr_oracle_row_digests"]
    )
    assert any(
        "typed polarity" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(Ctx(), invalid_semantics)
    )

    # Complete is reachable only after live DU legacy refs disappear and all artifacts are in one HEAD tree.
    authority_path.write_text(
        json.dumps(
            {
                "ac_sr_oracles": authority_oracles,
                "ac_sr_oracle_row_digests": authority_projection,
            }
        ),
        encoding="utf-8",
    )
    complete = copy.deepcopy(classified)
    complete_policy = complete["test_id_authority_alignment_policy"]
    complete_policy["status"] = "ratified"
    complete_state = complete_policy["classification_state"]
    complete_state["status"] = "cutover_complete"
    complete_state["cutover_blocked"] = False
    authority_digest = "sha256:" + hashlib.sha256(authority_path.read_bytes()).hexdigest()
    complete_owner = complete_state["strategy_test_owner"]
    complete_owner["current_authority_content_digest"] = authority_digest
    complete_state["classification_approval"]["strategy_owner_digest"] = requirement_engine._digest(
        complete_owner
    )
    candidate_path.write_text(
        json.dumps(
            {
                "legacy_tc_mapping_row_digests": {
                    key: requirement_engine._digest(value) for key, value in mapping.items()
                },
                "strategy_test_owner_digest": requirement_engine._digest(complete_owner),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    complete_state["candidate_artifact_binding"]["content_digest"] = candidate_digest
    complete_ctx = Ctx()
    complete_ctx.__dict__["duc"] = [
        {
            **du,
            "trace": {
                **du.get("trace", {}),
                "tc": [ref for ref in du.get("trace", {}).get("tc", []) if not ref.startswith("TC-")],
            },
        }
        for du in Ctx().duc
    ]
    trace_path = tmp_path / "du-trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "du_tc_projection": {
                    str(du.get("id")): sorted(du.get("trace", {}).get("tc", []))
                    for du in complete_ctx.duc
                },
                "legacy_mapping_resolution": {
                    legacy_id: {
                        "disposition": row["disposition"],
                        "target_test_ids": row["target_test_ids"],
                        "referenced_by": row["referenced_by"],
                        "du_trace_impact": row["du_trace_impact"],
                    }
                    for legacy_id, row in mapping.items()
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    trace_digest = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    review_path = tmp_path / "go-review.json"
    review = {
        "separation_status": "ci_attested",
        "verdict": "Go",
        "reviewer_principal": "ci-independent-reviewer",
        "author_principal": "requirements-authority-resolver",
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "reviewed_artifact_digests": {
            "candidate": candidate_digest,
            "trace": trace_digest,
            "authority": authority_digest,
        },
    }
    review_path.write_text(json.dumps(review), encoding="utf-8")
    review_digest = "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["items"]:
        if item["artifact_id"] in {
            "AUTH-DEVELOPMENT-TEST-ID-AUTHORITY-CANDIDATE",
            "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE",
        }:
            item["implementation_input"] = True
    manifest["items"].extend(
        [
            {"artifact_id": "L5-DU-TRACE-CANDIDATE", "canonical_path": "du-trace.json"},
            {"artifact_id": "AUTH-TEST-ID-GO-REVIEW", "canonical_path": "go-review.json"},
        ]
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    baseline_path = tmp_path / "docs/00-authority/baselines/baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text(json.dumps({"fixture": True}), encoding="utf-8")
    complete_state["cutover_artifact_bindings"] = {
        "du_trace_artifact_id": "L5-DU-TRACE-CANDIDATE",
        "du_trace_digest": trace_digest,
        "test_authority_artifact_id": "L3-STRATEGY-TEST-AUTHORITY-CANDIDATE",
        "test_authority_digest": authority_digest,
        "manifest_digest": "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "baseline_digest": "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        "target_commit": "fixture-head",
        "target_tree": "fixture-tree",
        "same_commit": True,
        "trace_diff_count": 0,
        "independent_go_artifact_id": "AUTH-TEST-ID-GO-REVIEW",
        "independent_go_digest": review_digest,
    }
    original_git = requirement_engine.git

    def fixture_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout="fixture-head\n")
        if args[:2] == ("rev-parse", "HEAD^{tree}"):
            return SimpleNamespace(returncode=0, stdout="fixture-tree\n")
        if args and args[0] == "show":
            relative = str(args[1]).removeprefix("HEAD:")
            path = tmp_path / relative
            return SimpleNamespace(
                returncode=0 if path.is_file() else 1,
                stdout=path.read_text(encoding="utf-8") if path.is_file() else "",
            )
        return original_git(*args)

    monkeypatch.setattr(requirement_engine, "git", fixture_git)
    assert requirement_engine.test_id_authority_alignment_policy_faults(complete_ctx, complete) == []
    assert requirement_engine.legacy_test_authority_disposition_faults(complete_ctx, complete) == []
    assert requirement_engine.legacy_test_authority_cutover_faults(complete_ctx, complete) == []

    old_ref = copy.deepcopy(complete_ctx)
    old_ref.__dict__["duc"] = [{"id": "DU-X", "trace": {"tc": ["TC-023"]}}]
    assert any(
        "live DU" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(old_ref, complete)
    )

    trace_mismatch = copy.deepcopy(complete)
    valid_trace = json.loads(trace_path.read_text(encoding="utf-8"))
    invalid_trace = copy.deepcopy(valid_trace)
    invalid_trace["du_tc_projection"] = {}
    trace_path.write_text(json.dumps(invalid_trace), encoding="utf-8")
    invalid_trace_digest = "sha256:" + hashlib.sha256(trace_path.read_bytes()).hexdigest()
    trace_mismatch_state = trace_mismatch["test_id_authority_alignment_policy"]["classification_state"]
    trace_mismatch_state["cutover_artifact_bindings"]["du_trace_digest"] = invalid_trace_digest
    assert any(
        "live DU projection" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(complete_ctx, trace_mismatch)
    )
    trace_path.write_text(json.dumps(valid_trace, ensure_ascii=False), encoding="utf-8")

    no_go = copy.deepcopy(complete)
    review["verdict"] = "No-Go"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    no_go_state = no_go["test_id_authority_alignment_policy"]["classification_state"]
    no_go_state["cutover_artifact_bindings"]["independent_go_digest"] = (
        "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
    )
    assert any(
        "independent Go" in fault
        for fault in requirement_engine.test_id_authority_alignment_policy_faults(complete_ctx, no_go)
    )


def test_every_legacy_phase_fault_has_an_edge_disposition(monkeypatch) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_phase_fault_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_phase_fault_dispositions"] = missing["legacy_phase_fault_dispositions"][1:]
    assert any(
        "exactly被覆" in fault
        for fault in requirement_engine.legacy_phase_fault_disposition_faults(Ctx(), missing)
    )

    adopted = copy.deepcopy(refinements)
    adopted["legacy_phase_fault_dispositions"][0]["disposition"] = "split_and_redescent"
    assert any(
        "PO未分類" in fault
        for fault in requirement_engine.legacy_phase_fault_disposition_faults(Ctx(), adopted)
    )

    untyped = copy.deepcopy(refinements)
    untyped["legacy_phase_fault_classifications"][0]["fault_class"] = "phase_typo"
    assert any(
        "typed edge分類" in fault
        for fault in requirement_engine.legacy_phase_fault_disposition_faults(Ctx(), untyped)
    )

    monkeypatch.setattr(requirement_engine, "phase_alignment_faults", lambda ctx: [])
    assert any(
        "immutable snapshot" in fault
        for fault in requirement_engine.legacy_phase_fault_disposition_faults(Ctx(), refinements)
    )


def test_fr_slice_authority_alignment_policy_preserves_snapshot_and_fails_closed(
    monkeypatch, tmp_path
) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_phase_fault_classifications"] = missing["legacy_phase_fault_classifications"][1:]
    assert any(
        "30 edge" in fault or "snapshot digest" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), missing)
    )

    stale = copy.deepcopy(refinements)
    stale["fr_slice_authority_alignment_policy"]["source_snapshot_digest"] = "sha256:" + "0" * 64
    assert any(
        "snapshot digest" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), stale)
    )

    premature = copy.deepcopy(refinements)
    premature["fr_slice_authority_alignment_policy"]["status"] = "ratified"
    assert any(
        "PO未分類" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), premature)
    )

    selected_early = copy.deepcopy(refinements)
    selected_early["fr_slice_authority_alignment_policy"]["classification_state"]["selected_rows"] = {"x": {}}
    assert any(
        "選択又はcutover解除" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), selected_early)
    )

    classified = copy.deepcopy(refinements)
    policy = classified["fr_slice_authority_alignment_policy"]
    state = policy["classification_state"]
    state["status"] = "classified_pending_cutover"
    selected = {}
    for source in classified["legacy_phase_fault_classifications"]:
        selected[source["fault_key"]] = {
            "parent_fault_digest": requirement_engine._digest(source),
            "source_fr_id": source["source_fr_id"],
            "target_kind": source["target_kind"],
            "target_id": source["target_id"],
            "source_phase_snapshot": source["source_phase"],
            "target_phase_snapshot": source["target_phase"],
            "disposition": "phase_typo",
            "authoritative_phase": "release:initial",
            "owner_subject_id": "FR-SLICE-AUTHORITY-ALIGNMENT",
            "rationale": "PO classification fixture",
            "supersession_target_id": None,
            "resume_conditions": [],
        }
    state["selected_rows"] = selected
    state["classification_approval"] = {
        "authority": "PO",
        "subject_id": "FR-SLICE-AUTHORITY-ALIGNMENT",
        "source_snapshot_digest": requirement_engine._digest(
            classified["legacy_phase_fault_classifications"]
        ),
        "selected_rows_digest": requirement_engine._digest(selected),
        "approved_revision": "fixture-revision",
    }
    candidate_path = tmp_path / "phase-candidate.json"
    candidate_path.write_text(
        json.dumps(
            {"phase_alignment_row_digests": {key: requirement_engine._digest(row) for key, row in selected.items()}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "artifact_id": "AUTH-DEVELOPMENT-FR-SLICE-AUTHORITY-CANDIDATE",
                        "canonical_path": "phase-candidate.json",
                        "layer": "00-authority",
                        "artifact_type": "fr-slice-authority-candidate",
                        "authority_format": "json",
                        "authority_status": "active",
                        "implementation_input": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    state["candidate_artifact_binding"] = {
        "artifact_id": "AUTH-DEVELOPMENT-FR-SLICE-AUTHORITY-CANDIDATE",
        "content_digest": candidate_digest,
    }
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "MANIFEST", manifest_path)
    classified_faults = requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), classified)
    assert classified_faults == []

    candidate_path.write_text(json.dumps({"phase_alignment_row_digests": {}}), encoding="utf-8")
    stale_candidate = requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), classified)
    assert any("candidate artifact" in fault or "candidate projection" in fault for fault in stale_candidate)
    candidate_path.write_text(
        json.dumps(
            {"phase_alignment_row_digests": {key: requirement_engine._digest(row) for key, row in selected.items()}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    inclusive = next(key for key, row in selected.items() if row["target_kind"] == "FR")
    assert selected[inclusive]["target_phase_snapshot"] is None

    swapped = copy.deepcopy(classified)
    swapped["fr_slice_authority_alignment_policy"]["classification_state"]["selected_rows"][inclusive]["source_phase_snapshot"] = "S0"
    assert any(
        "snapshotが入替又は不一致" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), swapped)
    )

    split = copy.deepcopy(classified)
    split_row = next(iter(split["fr_slice_authority_alignment_policy"]["classification_state"]["selected_rows"].values()))
    split_row.update(disposition="split_responsibility", supersession_target_id="not-an-id")
    assert any(
        "split responsibility" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), split)
    )

    deferred = copy.deepcopy(classified)
    defer_row = next(iter(deferred["fr_slice_authority_alignment_policy"]["classification_state"]["selected_rows"].values()))
    defer_row.update(disposition="defer_target", authoritative_phase=None, resume_conditions=[{}])
    assert any(
        "defer field partition" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), deferred)
    )

    redescent = copy.deepcopy(classified)
    redescent_row = next(iter(redescent["fr_slice_authority_alignment_policy"]["classification_state"]["selected_rows"].values()))
    redescent_row.update(disposition="redescent_test", authoritative_phase="S0")
    assert any(
        "direct alignment field partition" in fault
        for fault in requirement_engine.fr_slice_authority_alignment_policy_faults(Ctx(), redescent)
    )


def test_legacy_media_br_and_mr_edges_are_bidirectional(monkeypatch, tmp_path) -> None:
    current_faults = requirement_engine.legacy_media_trace_faults()
    assert any("BR-M-AFF-4->MR-AFF-2" in fault for fault in current_faults)
    assert any("BR-M-DC-4->MR-DC-1" in fault for fault in current_faults)

    br_dir = tmp_path / "br"
    mr_dir = tmp_path / "mr"
    br_dir.mkdir()
    mr_dir.mkdir()
    (br_dir / "x.json").write_text(
        json.dumps({"items": [{"id": "BR-M-X-1", "trace": {"upstream": [], "downstream": ["MR-X-1"]}}]}),
        encoding="utf-8",
    )
    (mr_dir / "x.json").write_text(
        json.dumps({"items": [{"id": "MR-X-1", "trace": {"upstream": [], "downstream": []}}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(requirement_engine, "BR_MEDIA_DIR", br_dir)
    monkeypatch.setattr(requirement_engine, "MR_DIR", mr_dir)
    assert any("reverse edge" in fault for fault in requirement_engine.legacy_media_trace_faults())

    (br_dir / "x.json").write_text(
        json.dumps({"items": [{"id": "BR-M-X-1", "trace": {"upstream": [], "downstream": []}}]}),
        encoding="utf-8",
    )
    assert any("downstream MR" in fault for fault in requirement_engine.legacy_media_trace_faults())


def test_legacy_media_trace_fault_set_is_digest_bound_for_redescent() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_media_trace_fault_policy_faults(refinements) == []

    stale = copy.deepcopy(refinements)
    stale["legacy_media_trace_fault_policy"]["fault_digest"] = "sha256:" + "0" * 64
    assert any(
        "digest" in fault for fault in requirement_engine.legacy_media_trace_fault_policy_faults(stale)
    )

    unclassified = copy.deepcopy(refinements)
    unclassified["legacy_media_trace_fault_policy"]["classification_partitions"]["missing_mr_reverse_edge"][
        "count"
    ] -= 1
    assert any(
        "exactly partition" in fault
        for fault in requirement_engine.legacy_media_trace_fault_policy_faults(unclassified)
    )

    wrong_owner = copy.deepcopy(refinements)
    wrong_owner["legacy_media_trace_fault_dispositions"][0]["owner_subject_ids"] = ["UNKNOWN"]
    assert any(
        "個別edge/class/disposition/owner/digest" in fault
        for fault in requirement_engine.legacy_media_trace_fault_policy_faults(wrong_owner)
    )


def test_legacy_trace_fault_set_and_semantic_exceptions_are_digest_bound(monkeypatch) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_trace_fault_policy_faults(Ctx(), refinements) == []

    stale = copy.deepcopy(refinements)
    stale["legacy_trace_fault_policy"]["direct_fault_digest"] = "sha256:" + "0" * 64
    assert any(
        "direct" in fault and "digest" in fault
        for fault in requirement_engine.legacy_trace_fault_policy_faults(Ctx(), stale)
    )

    restored_bad_edge = copy.deepcopy(refinements)
    restored_bad_edge["legacy_trace_fault_policy"]["semantic_exception_dispositions"]["FR-21→FR-4x"] = (
        "semantic_redescent"
    )
    assert any(
        "誤ったtrace" in fault
        for fault in requirement_engine.legacy_trace_fault_policy_faults(Ctx(), restored_bad_edge)
    )

    unclassified = copy.deepcopy(refinements)
    unclassified["legacy_trace_fault_policy"]["classification_partitions"]["missing_reverse_edge"][
        "count"
    ] -= 1
    assert any(
        "exactly partition" in fault
        for fault in requirement_engine.legacy_trace_fault_policy_faults(Ctx(), unclassified)
    )

    original_direct = requirement_engine.bidirectional_trace_faults
    original_semantic = requirement_engine.trace_semantic_responsibility_faults
    monkeypatch.setattr(
        requirement_engine,
        "trace_semantic_responsibility_faults",
        lambda ctx: original_semantic(ctx) + [original_direct(ctx)[0]],
    )
    assert any(
        "重複なく1回だけ被覆" in fault
        for fault in requirement_engine.legacy_trace_fault_policy_faults(Ctx(), refinements)
    )

    individual = copy.deepcopy(refinements)
    individual["legacy_trace_fault_dispositions"][0]["owner_subject_ids"] = ["UNKNOWN"]
    assert any(
        "個別class/disposition/owner/digest" in fault
        for fault in requirement_engine.legacy_trace_fault_policy_faults(Ctx(), individual)
    )


def test_legacy_test_authority_cannot_cut_over_while_mapping_or_owner_is_pending() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    faults = requirement_engine.legacy_test_authority_cutover_faults(Ctx(), refinements)
    assert any("mappingがPO未決" in fault for fault in faults)
    assert any("実在artifact ID" in fault for fault in faults)

    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["implementation_authorized"] = True
    policy["requirements_baseline_status"] = "approved"
    discovery = requirement_engine.requirement_discovery.load_discovery_ledger()
    cutover = requirement_engine.authority_cutover_faults(Ctx(), policy, refinements, discovery)
    assert any("意味inventoryがcutoverを直接停止" in fault for fault in cutover)
    assert any("legacy test authority未決" in fault for fault in cutover)
    assert any("provider execution policy" in fault for fault in cutover)
    assert any("全objectiveがprovenでない" in fault for fault in cutover)
    assert any("設計・実装admission" in fault for fault in cutover)
    assert any("新設計・検証・実装入力" in fault for fault in cutover)
    assert any("PO receipt" in fault for fault in cutover)
    assert any("独立Go review" in fault for fault in cutover)


def test_authority_revision_is_recommended_but_not_self_approved() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.authority_revision_candidate_faults(refinements) == []

    in_place = copy.deepcopy(refinements)
    in_place["authority_revision_candidate"]["recommended_strategy"] = "rewrite_legacy_ids_in_place"
    assert any(
        "in-place" in fault for fault in requirement_engine.authority_revision_candidate_faults(in_place)
    )

    self_approved = copy.deepcopy(refinements)
    self_approved["authority_revision_candidate"]["po_decision"] = "new_revision_single_json_authority"
    self_approved["authority_revision_candidate"]["status"] = "decided"
    assert any(
        "PO未回答" in fault for fault in requirement_engine.authority_revision_candidate_faults(self_approved)
    )


def test_objective_completion_audit_does_not_overclaim_requirements_freeze() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.objective_completion_audit_faults(Ctx(), refinements) == []

    overclaim = copy.deepcopy(refinements)
    freeze = next(row for row in overclaim["objective_completion_audit"] if row["objective_id"] == "OBJ-05")
    freeze["status"] = "proven"
    freeze["remaining_condition"] = None
    assert any(
        "OBJ-05" in fault for fault in requirement_engine.objective_completion_audit_faults(Ctx(), overclaim)
    )

    inventory_overclaim = copy.deepcopy(refinements)
    inventory = next(
        row for row in inventory_overclaim["objective_completion_audit"] if row["objective_id"] == "OBJ-01"
    )
    inventory["status"] = "proven"
    inventory["remaining_condition"] = None
    assert any(
        "OBJ-01" in fault
        for fault in requirement_engine.objective_completion_audit_faults(Ctx(), inventory_overclaim)
    )


def test_vps_ui_objective_requires_quality_and_product_state_freeze(monkeypatch) -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    required = {
        "VPS-UI-PRIMARY-HUMAN-INTERFACE",
        "VPS-UI-INBOX-LIFECYCLE",
        "VPS-UI-AUTHENTICATION-SESSION",
        "VPS-UI-QUALITY-ATTRIBUTES",
        "PRODUCT-STATE-AUTHORITY",
        "FR-16-NOTIFICATION-BOUNDARY",
        "DISCORD-NOTIFICATION-REJECTION-BOUNDARY",
    }
    for record in refinements["records"]:
        if record["subject_id"] in required:
            record["lifecycle_status"] = "frozen"
            record["approval"] = {"receipt": "test-only"}
    objective = next(
        row for row in refinements["objective_completion_audit"] if row["objective_id"] == "OBJ-03"
    )
    objective["status"] = "proven"
    objective["remaining_condition"] = None
    monkeypatch.setattr(requirement_engine, "notification_purpose_boundary_faults", lambda ctx: [])
    monkeypatch.setattr(requirement_engine, "vps_ui_requirement_descent_faults", lambda ctx: [])
    monkeypatch.setattr(requirement_engine, "obsolete_runtime_route_faults", lambda: [])
    assert requirement_engine.objective_completion_audit_faults(Ctx(), refinements) == []

    missing_quality = copy.deepcopy(refinements)
    quality = next(
        row for row in missing_quality["records"] if row["subject_id"] == "VPS-UI-QUALITY-ATTRIBUTES"
    )
    quality["lifecycle_status"] = "draft"
    quality["approval"] = None
    assert any(
        "OBJ-03" in fault
        for fault in requirement_engine.objective_completion_audit_faults(Ctx(), missing_quality)
    )


def test_current_brand_plan_trace_points_to_unrelated_schema_contract() -> None:
    faults = requirement_engine.trace_semantic_responsibility_faults(Ctx())
    assert "BR-A3/REQ-004→FR-71: brand plan保持・action plan trace責務がDDL生成契約にない" in faults


def test_legacy_requirements_view_is_only_a_semantic_drift_input() -> None:
    """通常ゲートが旧 requirements view を現行分母へ戻さない。"""
    gate_dir = requirement_engine.REPO_ROOT / "tools/gates"
    consumers = []
    for path in sorted(gate_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\b(?:ctx|CTX)\.requirements\b", text):
            consumers.append(path.name)
    assert consumers == ["requirement_engine.py"]


def test_legacy_consumer_isolation_derives_manifest_implementation_inputs(monkeypatch) -> None:
    manifest = {
        "items": [
            {
                "canonical_path": "tests/gates/test_requirement_engine.py",
                "implementation_input": True,
            }
        ]
    }
    monkeypatch.setattr(requirement_engine, "load", lambda path: manifest)
    assert any(
        "implementation inputが旧正本を参照" in fault
        for fault in requirement_engine.legacy_requirement_consumer_faults()
    )


def test_product_code_cannot_import_legacy_contract_context(monkeypatch, tmp_path) -> None:
    (tmp_path / "src/helix").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "src/helix/bad.py").write_text("from tools.gates.common import CTX\n", encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(requirement_engine, "load", lambda path: {"items": []})
    assert any(
        "product codeが旧契約" in fault for fault in requirement_engine.legacy_requirement_consumer_faults()
    )


def test_mutation_historical_view_with_manifest_input_is_rejected(monkeypatch, tmp_path) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    relative = "legacy.md"
    (tmp_path / relative).write_text("confirmed", encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        requirement_engine,
        "HISTORICAL_VIEW_BANNERS",
        {relative: ["historical", "implementation_authorized=false"]},
    )
    monkeypatch.setattr(
        requirement_engine,
        "load",
        lambda path: {
            "items": [
                {
                    "canonical_path": relative,
                    "applicability_status": "current",
                    "implementation_input": True,
                }
            ]
        },
    )
    faults = requirement_engine.compatibility_authority_faults(policy)
    assert any("manifest historical/non-input境界" in fault for fault in faults)


def test_mutation_agents_summary_cannot_claim_same_content(monkeypatch, tmp_path) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    (tmp_path / "AGENTS.md").write_text("CLAUDE.mdと同内容", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("正本", encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    faults = requirement_engine.authority_faults(policy)
    assert any("AGENTS要約" in fault for fault in faults)
    assert any("CLAUDE詳細正本" in fault for fault in faults)


def test_legacy_fault_stage_audit_accepts_only_exact_quarantined_faults() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_fault_stage_audit_faults(Ctx(), policy, refinements) == []


def test_mutation_legacy_fault_stage_audit_rejects_fault_set_drift(monkeypatch) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    actual = requirement_engine.semantic_dimension_faults
    monkeypatch.setattr(
        requirement_engine,
        "semantic_dimension_faults",
        lambda ctx: actual(ctx) + ["MUTATED unclassified semantic fault"],
    )
    faults = requirement_engine.legacy_fault_stage_audit_faults(Ctx(), policy, refinements)
    assert any("G-REQ-SEMANTIC-DIMENSIONS" in fault for fault in faults)


def test_mutation_legacy_fault_stage_audit_rejects_inventory_drift(monkeypatch) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        requirement_engine,
        "legacy_ac_meaning_inventory_faults",
        lambda ctx, value: ["旧AC row missing"],
    )
    faults = requirement_engine.legacy_fault_stage_audit_faults(Ctx(), policy, refinements)
    assert any("legacy_ac_meaning_inventory" in fault for fault in faults)


def test_legacy_fault_stage_audit_does_not_quarantine_raw_faults_after_cutover() -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    policy["requirements_baseline_status"] = "approved"
    policy["implementation_authorized"] = True
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert any(
        "raw faultをquarantineせずzero closure" in fault
        for fault in requirement_engine.legacy_fault_stage_audit_faults(Ctx(), policy, refinements)
    )


def test_actionable_engine_faults_hides_only_audited_legacy_quarantine() -> None:
    state = {
        "policy": {
            "requirements_baseline_status": "revising",
            "implementation_authorized": False,
        }
    }
    faults = {
        "legacy_fault_stage_audit": [],
        "semantic_drift": ["known legacy fault"],
        "open_refinements": ["PO approval required"],
    }
    assert requirement_engine.actionable_engine_faults(state, faults) == {
        "open_refinements": ["PO approval required"]
    }


def test_actionable_engine_faults_exposes_raw_fault_when_stage_audit_fails() -> None:
    state = {
        "policy": {
            "requirements_baseline_status": "revising",
            "implementation_authorized": False,
        }
    }
    faults = {
        "legacy_fault_stage_audit": ["snapshot drift"],
        "semantic_drift": ["untrusted fault"],
    }
    assert requirement_engine.actionable_engine_faults(state, faults) == faults
