"""HELIX 要件確定エンジン adaptation の mutation tests。"""

from __future__ import annotations

import copy
import json
import re

from scripts.render_views import render_requirement_candidates
from tools.gates import requirement_engine
from tools.gates.common import Ctx


def test_projection_is_deterministic_and_non_authoritative() -> None:
    first = requirement_engine.semantic_projection(Ctx())
    second = requirement_engine.semantic_projection(Ctx())
    assert first == second
    assert first["authority"] == "generated_non_authoritative_projection"
    assert first["partition"] == "stable_id_keyed_shards"
    assert [shard["kind"] for shard in first["shards"]] == ["requirements", "system_contracts", "acceptance_cases", "system_tests", "refinement_contracts"]
    assert any(record["kind"] == "RRF" for record in first["records"])
    assert sum(record["kind"] == "REQ" for record in first["records"]) == 55
    assert first["revalidation_inventory"]["counts"] == {
        "BR": 41, "BRM": 70, "REQ": 55, "FR": 43, "SR": 19, "NFR": 11,
        "MR": 54, "FN": 61, "AC": 252, "TC": 258, "total": 864,
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
    assert {record["source_authority"] for record in req_records} == {
        "read_only_req_revalidation_ledger"
    }
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
        assert {record["source_authority"] for record in records} == {
            "read_only_legacy_requirement_ledger"
        }
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
    policy["compatibility_inputs"]["docs/L3-system-requirements/canonical/functional/requirements.json"] = "canonical"
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
    assert any("parent trace_down missing child" in fault for fault in requirement_engine.bidirectional_trace_faults(ctx))


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
    assert requirement_engine.refinement_coverage_faults(refinements, discovery) == []
    open_faults = requirement_engine.open_refinement_faults(refinements)
    assert any("VPS-UI-PRIMARY-HUMAN-INTERFACE: lifecycle=specified" in fault for fault in open_faults)
    assert any("VPS-UI-QUALITY-ATTRIBUTES: lifecycle=draft" in fault for fault in open_faults)
    assert any("MEDIA-POC-SCRUM-RELEASE: pending_resolution=1" in fault for fault in open_faults)
    assert any("AGENT-NEO-HELIX-REDEFINITION: lifecycle=draft" in fault for fault in open_faults)
    assert any("PO approval receiptがない" in fault for fault in open_faults)


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
        record for record in mutated["records"]
        if record["subject_id"] == "WORDPRESS-SECURITY-MAINTENANCE-RELEASE"
    )
    security["delivery_admission"]["standard_model"] = "discovery_scrum"
    security["delivery_admission"]["predecessor_subject_ids"] = [
        "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE"
    ]
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
        "records": [{
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
        }],
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
        "subject_id": "FR-16-NOTIFICATION-BOUNDARY", "revision": 1,
        "lifecycle_status": "approved", "source_event_ids": ["RDE-000002"],
        "source_set_digest": requirement_engine._digest(source),
        "semantic_dimensions": {
            "actors": ["kernel"], "beneficiaries": ["PO"], "value": "安全停止",
            "tasks": ["停止"], "workflow": ["異常→停止"], "scope_in": ["停止"],
            "scope_out": ["外部通知"], "prohibitions": ["誤承認禁止"],
            "human_judgement": ["再開はPO"], "side_effects": ["状態変更"],
            "evidence": ["遷移証跡"], "phase": "S0"
        },
        "acceptance_cases": [
            {"acceptance_id": f"RAC-FR-16-{suffix}", "polarity": polarity,
             "statement": polarity, "system_test_id": f"RST-FR-16-{suffix}"}
            for suffix, polarity in (("P", "positive"), ("N", "negative"), ("B", "boundary"))
        ],
        "pending_resolution": [], "approval": None,
    }
    semantic = {key: value for key, value in record.items() if key not in {"semantic_digest", "approval"}}
    record["semantic_digest"] = requirement_engine._digest(semantic)
    record["approval"] = {
        "authority": "PO", "approver_principal": "codex-terra",
        "subject_digest": record["semantic_digest"], "source_set_digest": record["source_set_digest"],
        "decision_receipt_digest": "sha256:" + "1" * 64, "approved_revision": 1,
        "approved_at": "2026-08-14T00:00:00Z",
    }
    faults = requirement_engine.refinement_faults(
        {"schema_version": "marketing-harness-requirements-refinement.v1", "authority": "canonical", "records": [record]},
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
    assert any("全refinement" in fault for fault in faults)


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
    assert any("content operationとmaintenance" in fault for fault in requirement_engine.semantic_closure_faults(Ctx()))


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
        record for record in mutated["records"]
        if record["subject_id"] == "LEGACY-MEDIA-ADMISSION-INVENTORY"
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
        "actors", "beneficiaries", "value", "tasks", "workflow", "scope_in",
        "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase",
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
    mutated["root_digest"] = requirement_engine._digest({
        "shards": mutated["shards"],
        "records": mutated["records"],
        "revalidation_inventory": mutated["revalidation_inventory"],
    })
    assert any("実在refinement subjectへ未束縛" in fault for fault in requirement_engine.projection_faults(mutated))


def test_refinement_scope_assignments_separate_initial_and_deferred_candidates() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.scope_assignment_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["scope_assignments"]["GENAI-EXECUTION-ROUTE"] = "initial_candidate"
    assert any("旧Discord/生成AI/旧媒体" in fault for fault in requirement_engine.scope_assignment_faults(mutated))


def test_decision_packets_cover_each_subject_once_without_bulk_approval() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.decision_packet_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["decision_packets"][0]["subject_ids"].append(
        mutated["decision_packets"][1]["subject_ids"][0]
    )
    mutated["decision_packets"][0]["bulk_decision_forbidden"] = False
    mutated["decision_response_contract"]["unanswered_default"] = "approve_as_written"
    mutated["records"][0]["lifecycle_status"] = "draft"
    pending_record = next(record for record in mutated["records"] if record["pending_resolution"])
    mutated["records"][1]["pending_resolution"].append(pending_record["pending_resolution"][0])
    mutated["question_classifications"].pop(next(iter(mutated["question_classifications"])))
    mutated["decision_class_contracts"].pop("quality_target")
    mutated["captured_po_decisions"][0]["design_not_started"] = False
    mutated["captured_po_decisions"][0]["required_new_subject_ids"].append(
        "UNMATERIALIZED-SUBJECT"
    )
    browser_record = next(
        record for record in mutated["records"]
        if record["subject_id"] == "EXTERNAL-BROWSER-AUTOMATION-ROUTE"
    )
    browser_record["semantic_dimensions"] = json.loads(
        json.dumps(browser_record["semantic_dimensions"], ensure_ascii=False).replace(
            "Playwright", "browser"
        )
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


def test_candidate_prc_headings_bind_to_real_refinement_subjects() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.candidate_requirement_binding_faults(refinements) == []
    mutated = copy.deepcopy(refinements)
    mutated["candidate_requirement_bindings"].pop("PRC-01")
    mutated["candidate_requirement_bindings"]["PRC-02"].append("UNKNOWN-SUBJECT")
    faults = requirement_engine.candidate_requirement_binding_faults(mutated)
    assert any("heading" in fault for fault in faults)
    assert any("未知refinement" in fault for fault in faults)

    notification_mutation = copy.deepcopy(refinements)
    notification_mutation["candidate_requirement_bindings"]["PRC-05"] = ["DISCORD-MULTI-PURPOSE-BOUNDARIES"]
    faults = requirement_engine.candidate_requirement_binding_faults(notification_mutation)
    assert any("通知／Discord community" in fault for fault in faults)

    approval_mutation = copy.deepcopy(refinements)
    ui_record = next(
        record for record in approval_mutation["records"]
        if record["subject_id"] == "VPS-UI-PRIMARY-HUMAN-INTERFACE"
    )
    ui_record["semantic_dimensions"]["scope_in"].append("投稿承認")
    faults = requirement_engine.candidate_requirement_binding_faults(approval_mutation)
    assert any("旧個別投稿承認" in fault for fault in faults)

    auto_mode_mutation = copy.deepcopy(refinements)
    auto_mode_mutation["candidate_requirement_bindings"]["PRC-06"] = [
        "AUTO-MODE-DECISION-AUTHORITY", "CONTRACT-SEMANTIC-DESCENT-V2",
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
        row for row in regressed["legacy_l0_clause_dispositions"]
        if row["clause_id"] == "L0V04-DISCORD-APPROVAL"
    )
    discord["disposition"] = "retain"
    assert any("意味移送" in fault for fault in requirement_engine.l0_clause_disposition_faults(regressed))

    undeferred = copy.deepcopy(refinements)
    pwa = next(
        row for row in undeferred["legacy_l0_clause_dispositions"]
        if row["clause_id"] == "L0V04-PWA-PLAY"
    )
    pwa["resume_conditions"] = []
    assert any("deferred再開条件" in fault for fault in requirement_engine.l0_clause_disposition_faults(undeferred))


def test_legacy_critical_responsibilities_are_split_into_current_meaning_owners() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.critical_responsibility_disposition_faults(refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_critical_responsibility_dispositions"] = [
        row for row in missing["legacy_critical_responsibility_dispositions"]
        if row["legacy_id"] != "FR-76"
    ]
    assert any("critical責務被覆" in fault for fault in requirement_engine.critical_responsibility_disposition_faults(missing))

    discord_regression = copy.deepcopy(refinements)
    fr46 = next(
        row for row in discord_regression["legacy_critical_responsibility_dispositions"]
        if row["legacy_id"] == "FR-46"
    )
    fr46["disposition"] = "retain"
    fr46["prohibited_inheritance"] = ["個別投稿の毎回承認"]
    faults = requirement_engine.critical_responsibility_disposition_faults(discord_regression)
    assert any("FR-46" in fault for fault in faults)

    api_only_regression = copy.deepcopy(refinements)
    fr77 = next(
        row for row in api_only_regression["legacy_critical_responsibility_dispositions"]
        if row["legacy_id"] == "FR-77"
    )
    fr77["disposition"] = "retain"
    assert any("FR-77" in fault for fault in requirement_engine.critical_responsibility_disposition_faults(api_only_regression))


def test_semantic_descent_policy_requires_direct_high_risk_axes_and_blocks_design() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.semantic_descent_policy_faults(refinements) == []

    implicit_scope = copy.deepcopy(refinements)
    implicit_scope["semantic_descent_policy"]["dimensions"]["scope_in"]["mode"] = "explicit_inheritance_or_direct"
    assert any("scope_in" in fault for fault in requirement_engine.semantic_descent_policy_faults(implicit_scope))

    design_early = copy.deepcopy(refinements)
    fn_cmp = next(
        edge for edge in design_early["semantic_descent_policy"]["edge_contracts"]
        if edge["edge_id"] == "SED-FN-CMP"
    )
    fn_cmp["admission"] = "requirements_candidate"
    assert any("要求freeze前" in fault for fault in requirement_engine.semantic_descent_policy_faults(design_early))

    missing_edge = copy.deepcopy(refinements)
    missing_edge["semantic_descent_policy"]["edge_contracts"] = missing_edge["semantic_descent_policy"]["edge_contracts"][1:]
    assert any("edge被覆" in fault for fault in requirement_engine.semantic_descent_policy_faults(missing_edge))


def test_legacy_nfrs_have_business_rooted_or_deferred_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_nfr_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_nfr_dispositions"] = missing["legacy_nfr_dispositions"][:-1]
    assert any("旧NFR被覆" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), missing))

    false_root = copy.deepcopy(refinements)
    nfr9 = next(row for row in false_root["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-9")
    nfr9["disposition"] = "redescent"
    assert any("stable BR/REQ root" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), false_root))

    old_rate = copy.deepcopy(refinements)
    nfr7 = next(row for row in old_rate["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-7")
    nfr7["replacement_meaning"] = "全経路を1〜5秒一様乱数にする"
    assert any("NFR-7" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), old_rate))

    early_paid = copy.deepcopy(refinements)
    nfr6 = next(row for row in early_paid["legacy_nfr_dispositions"] if row["nfr_id"] == "NFR-6")
    nfr6["disposition"] = "redescent"
    assert any("NFR-6" in fault for fault in requirement_engine.legacy_nfr_disposition_faults(Ctx(), early_paid))


def test_orphan_fr_sr_requirements_have_exact_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.orphan_requirement_group_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_orphan_requirement_groups"] = missing["legacy_orphan_requirement_groups"][1:]
    assert any("orphan FR/SR被覆" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), missing))

    early_paid = copy.deepcopy(refinements)
    paid = next(group for group in early_paid["legacy_orphan_requirement_groups"] if "FR-73" in group["stable_ids"])
    paid["disposition"] = "redescent"
    assert any("FR-73" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), early_paid))

    old_ui = copy.deepcopy(refinements)
    inbox = next(group for group in old_ui["legacy_orphan_requirement_groups"] if "FR-76" in group["stable_ids"])
    inbox["replacement_meaning"] = "Discord operational notificationとAPI-only閲覧を維持する"
    assert any("FR-76" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), old_ui))

    premature_strategy = copy.deepcopy(refinements)
    advanced = next(group for group in premature_strategy["legacy_orphan_requirement_groups"] if "SR-17" in group["stable_ids"])
    advanced["resume_conditions"] = []
    assert any("deferred再開条件" in fault for fault in requirement_engine.orphan_requirement_group_faults(Ctx(), premature_strategy))


def test_all_legacy_req_ids_have_item_level_candidate_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_req_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_req_disposition_groups"][0]["stable_ids"].remove("REQ-001")
    missing["legacy_req_disposition_groups"][0]["item_dispositions"].pop("REQ-001")
    assert any("旧REQ被覆" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), missing))

    no_resume = copy.deepcopy(refinements)
    reporting = next(group for group in no_resume["legacy_req_disposition_groups"] if "REQ-025" in group["stable_ids"])
    reporting["deferred_resume_by_id"].pop("REQ-025")
    assert any("deferred ID" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), no_resume))

    old_connector = copy.deepcopy(refinements)
    connector = next(group for group in old_connector["legacy_req_disposition_groups"] if "REQ-026" in group["stable_ids"])
    connector["replacement_policy"] = "MCP→browser→paid APIを維持する"
    assert any("REQ-026" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), old_connector))

    old_notification = copy.deepcopy(refinements)
    human = next(group for group in old_notification["legacy_req_disposition_groups"] if "REQ-039" in group["stable_ids"])
    human["replacement_policy"] = "Discordへ通知する"
    assert any("REQ-039" in fault for fault in requirement_engine.legacy_req_disposition_faults(Ctx(), old_notification))


def test_all_legacy_br_ids_preserve_value_without_old_runtime_routes() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_br_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_br_disposition_groups"][0]["stable_ids"].remove("BR-A1")
    missing["legacy_br_disposition_groups"][0]["item_dispositions"].pop("BR-A1")
    assert any("旧BR被覆" in fault for fault in requirement_engine.legacy_br_disposition_faults(Ctx(), missing))

    old_approval = copy.deepcopy(refinements)
    human = next(group for group in old_approval["legacy_br_disposition_groups"] if "BR-H2" in group["stable_ids"])
    human["replacement_policy"] = "Discordで全投稿を毎回承認する"
    assert any("BR-H2" in fault for fault in requirement_engine.legacy_br_disposition_faults(Ctx(), old_approval))


def test_all_legacy_media_brs_are_capability_candidates_not_permissions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_media_br_disposition_faults(refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_media_br_dispositions"] = missing["legacy_media_br_dispositions"][1:]
    assert any("media BR被覆" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(missing))

    discord_notice = copy.deepcopy(refinements)
    discord = next(row for row in discord_notice["legacy_media_br_dispositions"] if row["media_id"] == "dc")
    discord["route_policy"] = "製品通知と投稿承認に使う"
    assert any("dc" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(discord_notice))

    x_browser = copy.deepcopy(refinements)
    x = next(row for row in x_browser["legacy_media_br_dispositions"] if row["media_id"] == "x")
    x["route_policy"] = "Playwrightで無人投稿する"
    assert any("x" in fault for fault in requirement_engine.legacy_media_br_disposition_faults(x_browser))


def test_all_legacy_frs_have_exact_current_requirement_dispositions() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.legacy_fr_disposition_faults(Ctx(), refinements) == []

    missing = copy.deepcopy(refinements)
    missing["legacy_fr_disposition_groups"][0]["stable_ids"].remove("FR-11")
    missing["legacy_fr_disposition_groups"][0]["item_dispositions"].pop("FR-11")
    assert any("旧FR被覆" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), missing))

    missing_resume = copy.deepcopy(refinements)
    connectors = next(group for group in missing_resume["legacy_fr_disposition_groups"] if "FR-45" in group["stable_ids"])
    connectors["deferred_resume_by_id"].pop("FR-45")
    assert any("deferred ID" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), missing_resume))

    old_approval = copy.deepcopy(refinements)
    connectors = next(group for group in old_approval["legacy_fr_disposition_groups"] if "FR-46" in group["stable_ids"])
    connectors["replacement_policy"] = "Discordで投稿を毎回承認する"
    assert any("FR-46" in fault for fault in requirement_engine.legacy_fr_disposition_faults(Ctx(), old_approval))

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
    assert any("FN" in fault and "digest" in fault for fault in requirement_engine.legacy_derived_contract_faults(Ctx(), wrong_digest))

    current_acceptance = copy.deepcopy(refinements)
    ac = next(row for row in current_acceptance["legacy_derived_contract_policy"] if row["kind"] == "AC")
    ac["disposition"] = "current_acceptance_evidence"
    assert any("AC" in fault and "defer" in fault for fault in requirement_engine.legacy_derived_contract_faults(Ctx(), current_acceptance))


def test_authority_revision_is_recommended_but_not_self_approved() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.authority_revision_candidate_faults(refinements) == []

    in_place = copy.deepcopy(refinements)
    in_place["authority_revision_candidate"]["recommended_strategy"] = "rewrite_legacy_ids_in_place"
    assert any("in-place" in fault for fault in requirement_engine.authority_revision_candidate_faults(in_place))

    self_approved = copy.deepcopy(refinements)
    self_approved["authority_revision_candidate"]["po_decision"] = "new_revision_single_json_authority"
    self_approved["authority_revision_candidate"]["status"] = "decided"
    assert any("PO未回答" in fault for fault in requirement_engine.authority_revision_candidate_faults(self_approved))


def test_objective_completion_audit_does_not_overclaim_requirements_freeze() -> None:
    refinements = json.loads(requirement_engine.REFINEMENTS.read_text(encoding="utf-8"))
    assert requirement_engine.objective_completion_audit_faults(Ctx(), refinements) == []

    overclaim = copy.deepcopy(refinements)
    freeze = next(row for row in overclaim["objective_completion_audit"] if row["objective_id"] == "OBJ-05")
    freeze["status"] = "proven"
    freeze["remaining_condition"] = None
    assert any("OBJ-05" in fault for fault in requirement_engine.objective_completion_audit_faults(Ctx(), overclaim))


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


def test_mutation_historical_view_without_non_input_banner_is_rejected(monkeypatch, tmp_path) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    relative = "legacy.md"
    (tmp_path / relative).write_text("confirmed", encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        requirement_engine,
        "HISTORICAL_VIEW_BANNERS",
        {relative: ["historical", "implementation_authorized=false"]},
    )
    faults = requirement_engine.compatibility_authority_faults(policy)
    assert any("historical/non-input banner不足" in fault for fault in faults)


def test_mutation_agents_summary_cannot_claim_same_content(monkeypatch, tmp_path) -> None:
    policy = json.loads(requirement_engine.AUTHORITY_POLICY.read_text(encoding="utf-8"))
    (tmp_path / "AGENTS.md").write_text("CLAUDE.mdと同内容", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("正本", encoding="utf-8")
    monkeypatch.setattr(requirement_engine, "REPO_ROOT", tmp_path)
    faults = requirement_engine.authority_faults(policy)
    assert any("AGENTS要約" in fault for fault in faults)
    assert any("CLAUDE詳細正本" in fault for fault in faults)
