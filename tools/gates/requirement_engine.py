"""HELIX 要件確定エンジンの Python-native admission core。

既存契約 JSON を source authority として読み、互換一覧との意味差分、trace の
双方向性、未終端の承認要求を fail-close にする。生成 IR は正本ではなく、同じ
入力から再計算できる projection である。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools.gates import requirement_discovery
from tools.gates.common import (
    BR_MEDIA_DIR,
    CTX,
    IMPL_UNITS_CONTRACTS,
    MANIFEST,
    MR_DIR,
    Ctx,
    gate,
    load,
    schema_check,
)

ENGINE_DIR = Path(__file__).resolve().parents[2] / "docs/00-authority/development"
AUTHORITY_POLICY = ENGINE_DIR / "requirement-engine-authority.json"
IR_SCHEMA = ENGINE_DIR / "requirement-ir.schema.json"
REFINEMENT_SCHEMA = ENGINE_DIR / "requirement-refinement.schema.json"
REFINEMENTS = ENGINE_DIR / "requirement-refinements.json"
COMPATIBILITY_VIEW = Path(__file__).resolve().parents[2] / "docs/L3-system-requirements/canonical/functional/requirements.json"
REQ_COMPATIBILITY_VIEW = Path(__file__).resolve().parents[2] / "docs/L1-business-requirements/canonical/requirement-list_v0.1.md"
REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_VIEW = REPO_ROOT / "docs/00-authority/views/requirement-candidates_v0.1.md"
CANDIDATE_BASELINE = REPO_ROOT / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md"

HISTORICAL_VIEW_BANNERS = {
    "docs/L1-business-requirements/canonical/br-backbone_v0.1.md": [
        "旧baselineの承認履歴", "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/br-media_v0.1.md": [
        "旧baselineの承認履歴", "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/loop-task-workflow_v0.1.md": [
        "旧baselineの承認履歴", "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/requirement-list_v0.1.md": [
        "旧baselineの承認履歴view", "現行要求の正本・設計・実装入力ではない",
        "requirements_baseline_status=revising", "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md": [
        "旧baselineの履歴view", "現行要件の正本・設計・実装入力ではない",
        "requirements_baseline_status=revising", "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/s0-contract_v0.1.md": [
        "旧baselineのS0契約", "現行要求の設計・実装入力ではない",
        "requirements_baseline_status=revising", "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/functional/function-list_v0.1.md": [
        "旧baselineの機能台帳", "現行要求の設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L3-system-requirements/canonical/functional/media-requirements_v0.1.md": [
        "旧baselineの媒体要件", "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L3-system-requirements/verification/verification-design_v0.1.md": [
        "旧baselineの検証設計", "現行要求の設計・実装入力ではない",
        "applicability_status=revalidation_required", "implementation_input=false",
    ],
    "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md": [
        "旧baselineの承認履歴", "設計・実装入力ではない",
    ],
    "docs/L4-basic-design/canonical/basic-design_v0.1.md": [
        "旧baselineの設計履歴", "現要求に対するL4は未設計",
    ],
    "docs/L4-basic-design/canonical/tech-stack_v0.1.md": [
        "旧baselineの設計履歴", "現在の技術選定・実装入力ではない",
    ],
    "docs/L4-basic-design/canonical/approval/approval-design_v0.1.md": [
        "旧Discord初期経路", "現要求の承認設計ではない",
    ],
    "docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md": [
        "旧baselineのL4設計", "現要求に対するL4は未設計", "implementation_input=false",
    ],
    "docs/L5-detailed-design/canonical/detailed-design_v0.1.md": [
        "旧baselineのL5設計", "現要求に対するL5は未設計", "implementation_input=false",
    ],
    "docs/L6-feature-design/S0/approval.md": [
        "旧baselineのL6設計", "VPS Web UI＋UI内inbox承認経路は未設計", "implementation_input=false",
    ],
}

OBSOLETE_RUNTIME_ROUTE_MARKERS = {
    "docs/L3-system-requirements/canonical/schemas/s0/ddl.sql": ["CHECK (channel = 'discord')"],
    "docs/L3-system-requirements/canonical/s0-contract_v0.1.md": ["CHECK (channel = 'discord')"],
    "docs/L3-system-requirements/canonical/functional/fr-contracts.json": [
        '"service": "discord_app"',
        '"operation": "approval_request"',
    ],
    "docs/L4-basic-design/canonical/tech-stack_v0.1.md": ["cron（WSL）"],
}


def _digest(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return []
    return [item for item in value["items"] if isinstance(item, dict)]


def _trace(item: dict[str, Any], *, contract: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if contract:
        up = item.get("trace_up", [])
        down = item.get("trace_down", {})
        if isinstance(down, dict):
            flattened = [ref for refs in down.values() if isinstance(refs, list) for ref in refs]
        else:
            flattened = down if isinstance(down, list) else []
    else:
        raw = item.get("trace", {})
        up = raw.get("upstream", []) if isinstance(raw, dict) else []
        flattened = raw.get("downstream", []) if isinstance(raw, dict) else []
    return (
        tuple(sorted({str(ref) for ref in up if isinstance(ref, str)})),
        tuple(sorted({str(ref) for ref in flattened if isinstance(ref, str)})),
    )


def contract_revalidation_inventory(ctx: Ctx) -> dict[str, Any]:
    """旧要求系10台帳の全件を、採否を推測せず再降下判断の単位へ射影する。"""
    trace_faults = bidirectional_trace_faults(ctx) + layered_trace_faults(ctx)
    phase_faults = phase_alignment_faults(ctx)
    descent_faults = requirement_descent_admission_faults(ctx)
    judgement_faults = human_judgement_descent_faults(ctx)
    dimension_faults = semantic_dimension_faults(ctx)
    conflict_ids = {
        "FR-16", "FR-41", "FR-42", "FR-43", "FR-44", "FR-45", "FR-46",
        "FR-47", "FR-52", "FR-53", "FR-71", "FR-74", "FR-75", "FR-76", "FR-77",
    }
    brm = [item for path in sorted(BR_MEDIA_DIR.glob("*.json")) for item in _items(load(path))]
    mr = [item for path in sorted(MR_DIR.glob("*.json")) for item in _items(load(path))]
    sources = (
        ("BR", ctx.brc), ("BRM", brm), ("REQ", ctx.req), ("FR", ctx.frc),
        ("SR", ctx.src), ("NFR", ctx.nfc), ("MR", mr), ("FN", ctx.fn),
        ("AC", ctx.acc), ("TC", ctx.tcc),
    )
    required_dimensions = [
        "actors", "beneficiaries", "value", "tasks", "workflow", "scope_in",
        "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase",
    ]

    def decision_subjects(kind: str, stable_id: str) -> list[str]:
        subjects = {"CONTRACT-SEMANTIC-DESCENT-V2"}
        if kind in {"BRM", "MR"}:
            subjects.add("LEGACY-MEDIA-ADMISSION-INVENTORY")
        if kind == "NFR":
            subjects.add("NFR-BUSINESS-AUTHORITY")
        if stable_id in {"FR-16", "FR-43", "FR-76"}:
            subjects.update({"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"})
        if stable_id == "BR-H2":
            subjects.update({
                "VPS-UI-PRIMARY-HUMAN-INTERFACE", "AUTOMATED-PUBLISHING-ADMISSION",
                "CONTENT-QUALITY-GATE-LEARNING",
            })
        if stable_id == "BR-H3":
            subjects.update({"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"})
        if stable_id == "FR-46":
            subjects.update({
                "VPS-UI-PRIMARY-HUMAN-INTERFACE", "VPS-UI-AUTHENTICATION-SESSION",
                "AUTOMATED-PUBLISHING-ADMISSION", "CONTENT-QUALITY-GATE-LEARNING",
            })
        if stable_id == "FR-75":
            subjects.update({
                "BUSINESS-PROFILE-AUTHORIZATION", "AUTOMATED-PUBLISHING-ADMISSION",
                "PRODUCT-STATE-AUTHORITY",
            })
        if stable_id in {"MR-DC-1", "MR-DC-2", "MR-DC-3"}:
            subjects.add("DISCORD-COMMUNITY-MARKETING-ROUTE")
        if stable_id == "FR-77":
            subjects.update({
                "VPS-UI-PRIMARY-HUMAN-INTERFACE", "VPS-UI-AUTHENTICATION-SESSION",
                "PRODUCT-STATE-AUTHORITY",
            })
        if kind in {"FR", "FN", "AC", "TC"}:
            subjects.add("FR-SLICE-AUTHORITY-ALIGNMENT")
        return sorted(subjects)

    items: list[dict[str, Any]] = []
    for kind, source in sources:
        for contract in _items(source):
            stable_id = str(contract.get("id", "?"))
            issue_codes = {"legacy_revalidation_required"}
            if any(stable_id in fault for fault in dimension_faults):
                issue_codes.add("semantic_dimensions_missing")
            if kind in {"FR", "SR", "NFR"} and not any(
                ref.startswith("REQ-") for ref in _trace(contract, contract=True)[0]
            ):
                issue_codes.add("stable_req_root_missing")
            if any(stable_id in fault for fault in trace_faults):
                issue_codes.add("trace_inconsistent")
            if any(stable_id in fault for fault in phase_faults):
                issue_codes.add("phase_inconsistent")
            if any(stable_id in fault for fault in descent_faults):
                issue_codes.add("implementation_descent_missing")
            if any(stable_id in fault for fault in judgement_faults):
                issue_codes.add("human_judgement_descent_missing")
            if stable_id in conflict_ids:
                issue_codes.add("known_runtime_or_policy_conflict")
            items.append({
                "stable_id": stable_id,
                "kind": kind,
                "legacy_slice": contract.get("slice"),
                "scope_assignment": "legacy_revalidation_only",
                "applicability": "revalidation_required",
                "issue_codes": sorted(issue_codes),
                "required_semantic_dimensions": required_dimensions,
                "decision_subject_ids": decision_subjects(kind, stable_id),
                "allowed_dispositions": ["redescent", "deferred", "superseded"],
                "treatment": (
                    "po_decision_then_redescent_or_deferred"
                    if "stable_req_root_missing" in issue_codes
                    else "redescent_required"
                ),
                "decision_status": "unresolved",
            })
    items.sort(key=lambda row: (row["kind"], row["stable_id"]))
    counts = {kind: sum(row["kind"] == kind for row in items) for kind, _ in sources}
    counts["total"] = len(items)
    return {
        "status": "unresolved_not_implementation_input",
        "decision_policy": "po_receipt_per_refinement_no_bulk_inference",
        "counts": counts,
        "items": items,
        "digest": _digest(items),
    }


def semantic_projection(ctx: Ctx) -> dict[str, Any]:
    """現行正本を stable ID keyed の決定的な非権威 IR に射影する。"""
    brm = [item for path in sorted(BR_MEDIA_DIR.glob("*.json")) for item in _items(load(path))]
    mr = [item for path in sorted(MR_DIR.glob("*.json")) for item in _items(load(path))]
    sources = {
        "BR": ctx.brc,
        "BRM": brm,
        "REQ": ctx.req,
        "FR": ctx.frc,
        "SR": ctx.src,
        "NFR": ctx.nfc,
        "MR": mr,
        "FN": ctx.fn,
        "AC": ctx.acc,
        "TC": ctx.tcc,
        "CMP": ctx.cmpc,
        "DU": ctx.duc,
        "IU": load(IMPL_UNITS_CONTRACTS),
    }
    partitions = {
        "BR": "requirements", "BRM": "requirements", "REQ": "requirements",
        "FR": "requirements", "SR": "requirements", "NFR": "requirements",
        "MR": "requirements", "FN": "requirements", "CMP": "system_contracts",
        "DU": "system_contracts", "IU": "system_contracts", "AC": "acceptance_cases",
        "TC": "system_tests",
    }
    records: list[dict[str, Any]] = []
    for kind, source in sources.items():
        for item in _items(source):
            stable_id = item.get("id")
            if not isinstance(stable_id, str):
                continue
            semantic = {key: value for key, value in item.items() if key != "semantic_digest"}
            records.append(
                {
                    "stable_id": stable_id,
                    "kind": kind,
                    "partition": partitions[kind],
                    "source_authority": (
                        "read_only_req_revalidation_ledger"
                        if kind == "REQ"
                        else "read_only_legacy_requirement_ledger"
                        if kind in {"BRM", "MR", "FN"}
                        else "canonical_contract_json"
                    ),
                    "applicability": "revalidation_required",
                    "semantic_digest": _digest(semantic),
                    "semantic": semantic,
                }
            )
    refinements = load(REFINEMENTS)
    for item in refinements.get("records", []) if isinstance(refinements, dict) else []:
        if isinstance(item, dict) and isinstance(item.get("refinement_id"), str):
            semantic = {key: value for key, value in item.items() if key != "semantic_digest"}
            records.append({"stable_id": item["refinement_id"], "kind": "RRF", "partition": "refinement_contracts", "source_authority": "canonical_refinement_registry", "applicability": "proposal_only", "semantic_digest": _digest(semantic), "semantic": semantic})
    records.sort(key=lambda row: (row["kind"], row["stable_id"]))
    partition_names = ["requirements", "system_contracts", "acceptance_cases", "system_tests", "refinement_contracts"]
    shards = []
    for name in partition_names:
        subset = [record for record in records if record["partition"] == name]
        shards.append({"kind": name, "count": len(subset), "digest": _digest(subset)})
    inventory = contract_revalidation_inventory(ctx)
    return {
        "schema_version": "marketing-harness-requirement-ir.v1",
        "authority": "generated_non_authoritative_projection",
        "source_authority": "mixed_revalidation_sources",
        "partition": "stable_id_keyed_shards",
        "shards": shards,
        "records": records,
        "revalidation_inventory": inventory,
        "root_digest": _digest({"shards": shards, "records": records, "revalidation_inventory": inventory}),
    }


def projection_faults(projection: dict[str, Any]) -> list[str]:
    faults: list[str] = [f"IR schema: {fault}" for fault in schema_check(load(IR_SCHEMA), projection)]
    if projection.get("schema_version") != "marketing-harness-requirement-ir.v1":
        faults.append("IR schema_version不正")
    if projection.get("authority") != "generated_non_authoritative_projection":
        faults.append("IR authority不正")
    if projection.get("source_authority") != "mixed_revalidation_sources":
        faults.append("IR source authority不正")
    if projection.get("partition") != "stable_id_keyed_shards":
        faults.append("IR partition方式不正")
    records = projection.get("records")
    if not isinstance(records, list) or not records:
        return faults + ["IR recordsが空又は配列でない"]
    keys: list[tuple[str, str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            faults.append(f"IR[{index}] objectでない")
            continue
        stable_id, kind = record.get("stable_id"), record.get("kind")
        if not isinstance(stable_id, str) or not stable_id or kind not in {"BR", "BRM", "REQ", "FR", "SR", "NFR", "MR", "FN", "AC", "TC", "CMP", "DU", "IU", "RRF"}:
            faults.append(f"IR[{index}] stable_id/kind不正")
            continue
        keys.append((kind, stable_id))
        semantic = record.get("semantic")
        if not isinstance(semantic, dict) or record.get("semantic_digest") != _digest(semantic):
            faults.append(f"{kind}/{stable_id}: semantic digest不一致")
        expected_source = (
            "canonical_refinement_registry"
            if kind == "RRF"
            else "read_only_req_revalidation_ledger"
            if kind == "REQ"
            else "read_only_legacy_requirement_ledger"
            if kind in {"BRM", "MR", "FN"}
            else "canonical_contract_json"
        )
        if record.get("source_authority") != expected_source:
            faults.append(f"{kind}/{stable_id}: record source authority不正")
        expected_applicability = "proposal_only" if kind == "RRF" else "revalidation_required"
        if record.get("applicability") != expected_applicability:
            faults.append(f"{kind}/{stable_id}: record applicability不正")
    if len(keys) != len(set(keys)):
        faults.append("IR stable_id/kind重複")
    if keys != sorted(keys):
        faults.append("IR recordsが決定順でない")
    expected_names = ["requirements", "system_contracts", "acceptance_cases", "system_tests", "refinement_contracts"]
    shards = projection.get("shards")
    if not isinstance(shards, list) or [x.get("kind") for x in shards if isinstance(x, dict)] != expected_names:
        faults.append("IR 5 partitionが不完全又は順序不正")
        shards = []
    else:
        for shard in shards:
            subset = [record for record in records if record.get("partition") == shard["kind"]]
            if shard.get("count") != len(subset) or shard.get("digest") != _digest(subset):
                faults.append(f"IR partition {shard['kind']} count/digest不一致")
    inventory = projection.get("revalidation_inventory")
    if not isinstance(inventory, dict) or inventory.get("digest") != _digest(inventory.get("items", [])):
        faults.append("IR revalidation inventory digest不一致")
    elif inventory.get("counts") != {
        "BR": 41, "BRM": 70, "REQ": 55, "FR": 43, "SR": 19, "NFR": 11,
        "MR": 54, "FN": 61, "AC": 252, "TC": 258, "total": 864,
    }:
        faults.append("IR revalidation inventoryが要求系10台帳全864件を被覆しない")
    elif any(item.get("applicability") != "revalidation_required" or item.get("decision_status") != "unresolved" for item in inventory.get("items", [])):
        faults.append("IR revalidation inventoryが未決旧契約をcurrent扱いする")
    else:
        refinement_subjects = {
            str(item.get("subject_id"))
            for item in json.loads(REFINEMENTS.read_text(encoding="utf-8")).get("records", [])
            if isinstance(item, dict)
        }
        required_dimensions = {
            "actors", "beneficiaries", "value", "tasks", "workflow", "scope_in",
            "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase",
        }
        critical_owner_sets = {
            "BR-H2": {"VPS-UI-PRIMARY-HUMAN-INTERFACE", "AUTOMATED-PUBLISHING-ADMISSION", "CONTENT-QUALITY-GATE-LEARNING"},
            "BR-H3": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-16": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-43": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-46": {"VPS-UI-PRIMARY-HUMAN-INTERFACE", "VPS-UI-AUTHENTICATION-SESSION", "AUTOMATED-PUBLISHING-ADMISSION", "CONTENT-QUALITY-GATE-LEARNING"},
            "FR-75": {"BUSINESS-PROFILE-AUTHORIZATION", "AUTOMATED-PUBLISHING-ADMISSION", "PRODUCT-STATE-AUTHORITY"},
            "FR-76": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-77": {"VPS-UI-PRIMARY-HUMAN-INTERFACE", "VPS-UI-AUTHENTICATION-SESSION", "PRODUCT-STATE-AUTHORITY"},
            "MR-DC-1": {"DISCORD-COMMUNITY-MARKETING-ROUTE"},
            "MR-DC-2": {"DISCORD-COMMUNITY-MARKETING-ROUTE"},
            "MR-DC-3": {"DISCORD-COMMUNITY-MARKETING-ROUTE"},
        }
        for item in inventory.get("items", []):
            stable_id = item.get("stable_id", "?")
            if item.get("scope_assignment") != "legacy_revalidation_only":
                faults.append(f"IR inventory {stable_id}: 旧IDが新scopeへ直接昇格")
            if set(item.get("required_semantic_dimensions", [])) != required_dimensions:
                faults.append(f"IR inventory {stable_id}: 必須意味軸が不完全")
            subjects = item.get("decision_subject_ids", [])
            if not subjects or any(subject not in refinement_subjects for subject in subjects):
                faults.append(f"IR inventory {stable_id}: 実在refinement subjectへ未束縛")
            critical_owners = critical_owner_sets.get(str(stable_id))
            if critical_owners is not None and not critical_owners <= set(subjects):
                faults.append(f"IR inventory {stable_id}: 現要求meaning ownerが不足")
            if str(stable_id) in critical_owner_sets and any(
                subject in {"AUTO-MODE-DECISION-AUTHORITY", "DISCORD-MULTI-PURPOSE-BOUNDARIES"}
                for subject in subjects
            ):
                faults.append(f"IR inventory {stable_id}: 旧auto-mode／Discord通知ownerを参照")
            if set(item.get("allowed_dispositions", [])) != {"redescent", "deferred", "superseded"}:
                faults.append(f"IR inventory {stable_id}: 処置閉集合が不正")
    if projection.get("root_digest") != _digest({"shards": shards, "records": records, "revalidation_inventory": inventory}):
        faults.append("IR root digest不一致")
    return faults


def scope_assignment_faults(refinements: dict[str, Any]) -> list[str]:
    """旧IDと新refinementのscopeを分離し、全subjectへ候補scopeを一意に割り当てる。"""
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    subjects = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    assignments = refinements.get("scope_assignments")
    if not isinstance(assignments, dict):
        return ["refinement scope_assignmentsがない"]
    faults: list[str] = []
    if set(assignments) != subjects:
        faults.append("refinement全subjectとscope assignmentが一対一でない")
    allowed = {
        "requirements_governance", "initial_candidate", "follow_on_candidate", "deferred_candidate",
    }
    if any(value not in allowed for value in assignments.values()):
        faults.append("scope assignmentに未知区分がある")
    required_initial = {
        "VPS-UI-PRIMARY-HUMAN-INTERFACE", "FR-16-NOTIFICATION-BOUNDARY",
        "VPS-UI-INBOX-LIFECYCLE", "VPS-UI-QUALITY-ATTRIBUTES",
        "VPS-CREDENTIAL-SECURITY-BOUNDARY",
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
        "PRODUCT-STATE-AUTHORITY", "BUSINESS-PROFILE-AUTHORIZATION",
        "VPS-UI-AUTHENTICATION-SESSION",
        "AUTOMATED-PUBLISHING-ADMISSION", "CONTENT-QUALITY-GATE-LEARNING",
        "CONTENT-RISK-CLASSIFICATION", "RESEARCH-LED-CONTENT-GROWTH",
    }
    if any(assignments.get(subject) != "initial_candidate" for subject in required_initial):
        faults.append("VPS UI/inbox/security/人間判断/WP content初期候補のscopeが不正")
    required_deferred = {
        "AUTO-MODE-DECISION-AUTHORITY", "DISCORD-MULTI-PURPOSE-BOUNDARIES", "GENAI-EXECUTION-ROUTE",
        "LEGACY-MEDIA-ADMISSION-INVENTORY",
    }
    if any(assignments.get(subject) != "deferred_candidate" for subject in required_deferred):
        faults.append("旧Discord/生成AI/旧媒体の安全側deferred scopeが不正")
    required_follow_on = {
        "EXTERNAL-BROWSER-AUTOMATION-ROUTE", "DISCORD-COMMUNITY-MARKETING-ROUTE",
    }
    if any(assignments.get(subject) != "follow_on_candidate" for subject in required_follow_on):
        faults.append("Playwright/Discord communityのfollow-on scopeが不正")
    return faults


def decision_packet_faults(refinements: dict[str, Any]) -> list[str]:
    """PO確認用packetが全subjectを一度だけ覆い、packet単位の一括承認を禁止する。"""
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    subjects = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    packets = refinements.get("decision_packets")
    if not isinstance(packets, list) or not packets:
        return ["decision packetがない"]
    faults: list[str] = []
    packet_ids = [packet.get("packet_id") for packet in packets if isinstance(packet, dict)]
    orders = [
        order
        for packet in packets if isinstance(packet, dict)
        if isinstance((order := packet.get("decision_order")), int)
    ]
    if len(packet_ids) != len(set(packet_ids)):
        faults.append("decision packet ID重複")
    if sorted(orders) != list(range(1, len(packets) + 1)):
        faults.append("decision packet順序が連続でない")
    covered = [
        subject
        for packet in packets if isinstance(packet, dict)
        for subject in packet.get("subject_ids", []) if isinstance(subject, str)
    ]
    if set(covered) != subjects or len(covered) != len(set(covered)):
        faults.append("decision packetが全subjectをexactly onceで覆わない")
    if any(packet.get("bulk_decision_forbidden") is not True for packet in packets if isinstance(packet, dict)):
        faults.append("decision packetの一括承認禁止がない")
    pending_questions = [
        question
        for record in records if isinstance(record, dict)
        for question in record.get("pending_resolution", []) if isinstance(question, str)
    ]
    if len(pending_questions) != len(set(pending_questions)):
        faults.append("同一PO質問が複数subjectに重複している")
    expected_question_ids = {
        f"RDQ-{record['refinement_id'][4:]}-{index:02d}"
        for record in records if isinstance(record, dict) and isinstance(record.get("refinement_id"), str)
        for index, _question in enumerate(record.get("pending_resolution", []), start=1)
    }
    classifications = refinements.get("question_classifications")
    allowed_classes = {
        "requirements_policy", "authority_choice", "safety_policy", "quality_target",
        "release_scope", "deferred_resume",
    }
    if not isinstance(classifications, dict) or set(classifications) != expected_question_ids:
        faults.append("PO質問IDとdecision classがexactly一致しない")
    elif any(value not in allowed_classes for value in classifications.values()):
        faults.append("PO質問に未知decision classがある")
    class_contracts = refinements.get("decision_class_contracts")
    if not isinstance(class_contracts, dict) or set(class_contracts) != allowed_classes:
        faults.append("decision classごとの回答契約が完全でない")
    elif any(
        not isinstance(fields, list) or not fields or len(fields) != len(set(fields))
        for fields in class_contracts.values()
    ):
        faults.append("decision class回答契約の必須fieldが不正")
    boundary = refinements.get("question_boundary")
    if not isinstance(boundary, dict) or not all(boundary.get(key) for key in ("po_decides", "design_later", "rule")):
        faults.append("要求判断とL2以降の設計判断の境界がない")
    captured = refinements.get("captured_po_decisions")
    if not isinstance(captured, list) or not captured:
        faults.append("回答済みPO判断の構造化snapshotがない")
    else:
        decision_ids = [item.get("decision_id") for item in captured if isinstance(item, dict)]
        if len(decision_ids) != len(set(decision_ids)):
            faults.append("回答済みPO decision IDが重複")
        for item in captured:
            if not isinstance(item, dict):
                faults.append("回答済みPO decisionがobjectでない")
                continue
            affected = set(item.get("affected_subject_ids", []))
            new_subjects = set(item.get("required_new_subject_ids", []))
            if not affected or not affected <= subjects:
                faults.append(f"{item.get('decision_id')}: affected subjectが未知")
            if not new_subjects or not new_subjects <= subjects:
                faults.append(f"{item.get('decision_id')}: 新規要求subjectがrefinementへ未materialize")
            if item.get("status") != "captured_unratified" or item.get("design_not_started") is not True:
                faults.append(f"{item.get('decision_id')}: 未承認・未設計境界が不正")
        records_by_subject = {
            str(record.get("subject_id")): record
            for record in records
            if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
        }
        required_meaning_tokens = {
            "EXTERNAL-BROWSER-AUTOMATION-ROUTE": {"公式API", "公式MCP", "Playwright"},
            "DISCORD-COMMUNITY-MARKETING-ROUTE": {"community", "製品承認通知", "運用通知"},
            "AUTOMATED-PUBLISHING-ADMISSION": {"初回", "毎回承認せず", "gate"},
            "CONTENT-QUALITY-GATE-LEARNING": {"不合格", "人間review", "再生成", "rule revision"},
            "CONTENT-RISK-CLASSIFICATION": {"YMYL", "case-by-case", "低riskへ推測しない"},
            "RESEARCH-LED-CONTENT-GROWTH": {"research", "funnel", "KPI", "超後期"},
        }
        captured_new_subjects = {
            subject
            for item in captured if isinstance(item, dict)
            for subject in item.get("required_new_subject_ids", []) if isinstance(subject, str)
        }
        for subject, tokens in required_meaning_tokens.items():
            record = records_by_subject.get(subject)
            dimensions = record.get("semantic_dimensions") if isinstance(record, dict) else None
            semantic_text = json.dumps(dimensions, ensure_ascii=False, sort_keys=True) if isinstance(dimensions, dict) else ""
            if subject not in captured_new_subjects or any(token not in semantic_text for token in tokens):
                faults.append(f"{subject}: captured PO回答の意味materializationが不完全")
    for record in records:
        if not isinstance(record, dict):
            continue
        pending = record.get("pending_resolution")
        if record.get("lifecycle_status") == "draft" and pending == []:
            faults.append(f"{record.get('subject_id')}: draftなのにPO質問がない")
    response_contract = refinements.get("decision_response_contract")
    expected_response_contract = {
        "allowed_responses": ["approve_as_written", "revise", "defer", "reject"],
        "unanswered_default": "defer",
        "required_bindings": [
            "refinement_id", "revision", "semantic_digest", "question_id", "response",
            "rationale", "approver_principal", "decided_at",
        ],
    }
    if not isinstance(response_contract, dict):
        faults.append("PO個別回答契約がない")
    else:
        for key, expected in expected_response_contract.items():
            if response_contract.get(key) != expected:
                faults.append(f"PO個別回答契約の{key}が不正")
        if not response_contract.get("approval_effect") or not response_contract.get("revision_effect"):
            faults.append("PO個別回答の効力が未定義")
    return faults


def candidate_requirement_binding_faults(refinements: dict[str, Any]) -> list[str]:
    """候補PRC本文を実在refinement subjectへ漏れなく束縛する。"""
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    subjects: set[str] = {
        str(record.get("subject_id")) for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    bindings = refinements.get("candidate_requirement_bindings")
    if not isinstance(bindings, dict):
        return ["PRC意味所有者bindingがない"]
    headings = set(re.findall(r"^### (PRC-[0-9]{2})\b", CANDIDATE_BASELINE.read_text(encoding="utf-8"), re.MULTILINE))
    faults: list[str] = []
    if set(bindings) != headings:
        faults.append(
            f"PRC headingとbinding keyが不一致 missing={sorted(headings - set(bindings))} "
            f"extra={sorted(set(bindings) - headings)}"
        )
    bound_subjects: set[str] = set()
    for prc_id, owners in bindings.items():
        if not isinstance(owners, list) or not owners:
            faults.append(f"{prc_id}: 意味所有者がない")
            continue
        unknown = {owner for owner in owners if owner not in subjects}
        if unknown:
            faults.append(f"{prc_id}: 未知refinement subject={sorted(unknown)}")
        bound_subjects.update(owner for owner in owners if isinstance(owner, str))
    if bound_subjects != subjects:
        faults.append(f"PRCへ未束縛のrefinement subject={sorted(subjects - bound_subjects)}")
    notification_bindings = {
        "PRC-04": ["VPS-UI-INBOX-LIFECYCLE"],
        "PRC-05": ["DISCORD-COMMUNITY-MARKETING-ROUTE"],
        "PRC-31": ["DISCORD-COMMUNITY-MARKETING-ROUTE"],
    }
    for prc_id, expected in notification_bindings.items():
        if bindings.get(prc_id) != expected:
            faults.append(f"{prc_id}: 通知／Discord community意味所有者が不正")
    for prc_id in ("PRC-06", "PRC-22"):
        owners = bindings.get(prc_id, [])
        if "AUTOMATED-PUBLISHING-ADMISSION" not in owners or "AUTO-MODE-DECISION-AUTHORITY" in owners:
            faults.append(f"{prc_id}: 旧auto-modeでなく初回activation後自動運用を意味所有者にする必要がある")
    deferred_owners = bindings.get("PRC-24", [])
    if "AUTO-MODE-DECISION-AUTHORITY" not in deferred_owners:
        faults.append("PRC-24: 旧auto-mode refinementを履歴deferredとして隔離していない")
    ui_record = next(
        (record for record in records if isinstance(record, dict) and record.get("subject_id") == "VPS-UI-PRIMARY-HUMAN-INTERFACE"),
        None,
    )
    dimensions = ui_record.get("semantic_dimensions") if isinstance(ui_record, dict) else None
    ui_text = json.dumps(dimensions, ensure_ascii=False, sort_keys=True) if isinstance(dimensions, dict) else ""
    if "投稿承認" in ui_text or "初回activation" not in ui_text or "毎回承認を要求しない" not in ui_text:
        faults.append("VPS UIが初回activation後の自動運用ではなく旧個別投稿承認を保持")
    return faults


def l0_clause_disposition_faults(refinements: dict[str, Any]) -> list[str]:
    """旧L0の価値と実現手段をclause単位で新PRCへ明示移送する。"""
    rows = refinements.get("legacy_l0_clause_dispositions") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["旧L0 clause disposition mapがない"]
    faults: list[str] = []
    expected_ids = {
        "L0V04-PURPOSE", "L0V04-DUAL-LOOP", "L0V04-MEDIA-PARALLEL", "L0V04-PWA-PLAY",
        "L0V04-HUMAN-AI", "L0V04-PILLARS", "L0V04-CONSUMER-WEB-AUTOMATION",
        "L0V04-CONNECTOR-PRIORITY", "L0V04-CLAUDE-DESIGN", "L0V04-BROWSER-MEASUREMENT",
        "L0V04-FULL-V", "L0V04-RUNTIME", "L0V04-DISCORD-APPROVAL",
        "L0V04-DISCORD-COMMUNITY", "L0V04-AUTO-MODE",
    }
    ids = [row.get("clause_id") for row in rows if isinstance(row, dict)]
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        faults.append(f"旧L0 clause被覆が不正 missing={sorted(expected_ids - set(ids))}")
    prc_ids = set((refinements.get("candidate_requirement_bindings") or {}).keys())
    by_id = {str(row.get("clause_id")): row for row in rows if isinstance(row, dict)}
    for clause_id, row in by_id.items():
        replacements = row.get("replacement_prc_ids")
        if not isinstance(replacements, list) or not replacements or any(item not in prc_ids for item in replacements):
            faults.append(f"{clause_id}: replacement PRCが空又は未知")
        if row.get("disposition") == "defer" and not row.get("resume_conditions"):
            faults.append(f"{clause_id}: deferred再開条件がない")
        if row.get("status") != "candidate_unratified" or row.get("design_not_started") is not True:
            faults.append(f"{clause_id}: 未承認・未設計境界が不正")
    required_meaning = {
        "L0V04-RUNTIME": ("replace", {"PRC-01"}),
        "L0V04-DISCORD-APPROVAL": ("replace", {"PRC-03", "PRC-04", "PRC-05", "PRC-15"}),
        "L0V04-DISCORD-COMMUNITY": ("retain", {"PRC-31"}),
        "L0V04-CONSUMER-WEB-AUTOMATION": ("replace", {"PRC-30"}),
        "L0V04-CLAUDE-DESIGN": ("replace", {"PRC-18"}),
        "L0V04-AUTO-MODE": ("replace", {"PRC-32", "PRC-33", "PRC-34"}),
        "L0V04-PWA-PLAY": ("defer", {"PRC-24"}),
    }
    for clause_id, (disposition, required_prcs) in required_meaning.items():
        row = by_id.get(clause_id, {})
        actual_prcs = set(row.get("replacement_prc_ids", [])) if isinstance(row, dict) else set()
        if row.get("disposition") != disposition or not required_prcs <= actual_prcs:
            faults.append(f"{clause_id}: 現要求への意味移送が不正")
    return faults


def critical_responsibility_disposition_faults(refinements: dict[str, Any]) -> list[str]:
    """旧通知・承認・自動運用・UI責務を新要求へ明示分割する。"""
    rows = refinements.get("legacy_critical_responsibility_dispositions") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["旧critical responsibility disposition mapがない"]
    expected_ids = {"BR-H2", "BR-H3", "FR-16", "FR-43", "FR-46", "FR-75", "FR-76", "FR-77"}
    ids = [row.get("legacy_id") for row in rows if isinstance(row, dict)]
    faults: list[str] = []
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        faults.append(f"旧critical責務被覆が不正 missing={sorted(expected_ids - set(ids))}")
    records = refinements.get("records")
    subjects = {
        record.get("subject_id") for record in records or []
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    by_id = {str(row.get("legacy_id")): row for row in rows if isinstance(row, dict)}
    for legacy_id, row in by_id.items():
        owners = row.get("owner_subject_ids")
        if not isinstance(owners, list) or not owners or any(owner not in subjects for owner in owners):
            faults.append(f"{legacy_id}: meaning ownerが空又は未知")
        if not row.get("replacement_responsibilities") or not row.get("prohibited_inheritance"):
            faults.append(f"{legacy_id}: 置換責務又は禁止継承がない")
        if row.get("status") != "candidate_unratified" or row.get("design_not_started") is not True:
            faults.append(f"{legacy_id}: 未承認・未設計境界が不正")

    def combined(legacy_id: str) -> str:
        return json.dumps(by_id.get(legacy_id, {}), ensure_ascii=False, sort_keys=True)

    required_markers = {
        "BR-H2": ["VPS-UI-PRIMARY-HUMAN-INTERFACE", "AUTOMATED-PUBLISHING-ADMISSION", "毎回承認なし", "Discordを通知又は承認transportにする"],
        "BR-H3": ["VPS-UI-INBOX-LIFECYCLE", "ApprovalTransport再利用", "Discord通知"],
        "FR-16": ["safety-stop", "operational inbox event", "FR-46 ApprovalTransport呼出"],
        "FR-43": ["repair lifecycle", "operational inbox event", "Discord通知"],
        "FR-46": ["初回activation", "通常投稿はactivation scope内", "channel=discord固定", "機械criteriaだけのauto-mode移行"],
        "FR-75": ["BUSINESS-PROFILE-AUTHORIZATION", "preflight", "自動付替え"],
        "FR-76": ["VPS UI内inbox", "将来の外部通知adapter", "Discord transport", "ApprovalTransport同型tuple"],
        "FR-77": ["VPS Web UI", "VPS-UI-AUTHENTICATION-SESSION", "Web UI対象外", "正本状態を直接更新"],
    }
    for legacy_id, markers in required_markers.items():
        text = combined(legacy_id)
        if any(marker not in text for marker in markers):
            faults.append(f"{legacy_id}: 現要求への責務移送が不完全")
    if by_id.get("FR-46", {}).get("disposition") != "replace":
        faults.append("FR-46: 旧Discord個別投稿承認をreplaceしていない")
    if by_id.get("FR-76", {}).get("disposition") != "replace":
        faults.append("FR-76: 旧Discord運用通知をreplaceしていない")
    if by_id.get("FR-77", {}).get("disposition") != "split":
        faults.append("FR-77: API read責務とWeb UI主入口をsplitしていない")
    return faults


def semantic_descent_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """全要求層の意味継承を暗黙コピーでなく型付きedgeとして固定する。"""
    policy = refinements.get("semantic_descent_policy") if isinstance(refinements, dict) else None
    if not isinstance(policy, dict):
        return ["semantic descent policyがない"]
    faults: list[str] = []
    dimensions = {
        "actors", "beneficiaries", "value", "tasks", "workflow", "scope_in",
        "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase",
    }
    configured = policy.get("dimensions")
    if not isinstance(configured, dict) or set(configured) != dimensions:
        faults.append("12意味軸policyが過不足")
        configured = {}
    direct_required = {
        "actors", "tasks", "workflow", "scope_in", "scope_out",
        "human_judgement", "side_effects", "evidence", "phase",
    }
    for dimension in direct_required:
        if (configured.get(dimension) or {}).get("mode") != "direct_required":
            faults.append(f"{dimension}: 対象層で直接宣言されない")
    if (configured.get("prohibitions") or {}).get("mode") != "inherit_plus_local":
        faults.append("prohibitions: 上位禁止の非弱化継承がない")
    if policy.get("unknown_default") != "question_then_deferred":
        faults.append("未知意味fieldが質問又はdeferredにならない")
    expected_binding = [
        "source_kind", "source_stable_id", "source_revision", "source_semantic_digest",
        "dimension", "scope_transform", "rationale",
    ]
    if policy.get("inheritance_binding_required") != expected_binding:
        faults.append("意味継承がsource revision/digest/scope transformへ束縛されない")
    edges = policy.get("edge_contracts")
    expected_edges = {
        "SED-BR-REQ", "SED-BRM-MR", "SED-REQ-FR", "SED-REQ-SR", "SED-REQ-NFR",
        "SED-REQUIREMENT-FN", "SED-REQUIREMENT-AC", "SED-AC-TC", "SED-FN-CMP", "SED-CMP-DU",
    }
    if not isinstance(edges, list):
        return faults + ["semantic descent edge contractがない"]
    edge_ids = [edge.get("edge_id") for edge in edges if isinstance(edge, dict)]
    if set(edge_ids) != expected_edges or len(edge_ids) != len(set(edge_ids)):
        faults.append(f"semantic descent edge被覆が不正 missing={sorted(expected_edges - set(edge_ids))}")
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        required = set(edge.get("required_dimensions", []))
        if not required or not required <= dimensions:
            faults.append(f"{edge.get('edge_id')}: 必須意味軸が空又は未知")
        if edge.get("edge_id") in {"SED-FN-CMP", "SED-CMP-DU"}:
            if edge.get("admission") != "blocked_until_frozen_requirements":
                faults.append(f"{edge.get('edge_id')}: 要求freeze前の設計降下を許可")
        elif edge.get("admission") != "requirements_candidate":
            faults.append(f"{edge.get('edge_id')}: 要求候補edgeのadmissionが不正")
    if policy.get("status") != "candidate_unratified" or policy.get("design_not_started") is not True:
        faults.append("semantic descent policyの未承認・未設計境界が不正")
    return faults


def legacy_nfr_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧NFR-1〜11を業務根拠付き再降下又は安全側deferredへ分類する。"""
    rows = refinements.get("legacy_nfr_dispositions") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["旧NFR disposition mapがない"]
    expected_ids = {f"NFR-{index}" for index in range(1, 12)}
    ids = [row.get("nfr_id") for row in rows if isinstance(row, dict)]
    faults: list[str] = []
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        faults.append(f"旧NFR被覆が不正 missing={sorted(expected_ids - set(ids))}")
    known_brs = {str(item.get("id")) for item in _items(ctx.brc)}
    known_reqs = {str(item.get("id")) for item in _items(ctx.req)}
    records = refinements.get("records", [])
    known_subjects = {
        str(record.get("subject_id")) for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    by_id = {str(row.get("nfr_id")): row for row in rows if isinstance(row, dict)}
    for nfr_id, row in by_id.items():
        br_refs = set(row.get("stable_br_refs", []))
        req_refs = set(row.get("stable_req_refs", []))
        if not br_refs <= known_brs or not req_refs <= known_reqs:
            faults.append(f"{nfr_id}: unknown stable BR/REQ root")
        owners = row.get("owner_subject_ids", [])
        if not owners or any(owner not in known_subjects for owner in owners):
            faults.append(f"{nfr_id}: meaning ownerが空又は未知")
        if row.get("disposition") in {"redescent", "replace"} and (not br_refs or not req_refs):
            faults.append(f"{nfr_id}: 再降下候補にstable BR/REQ rootがない")
        if row.get("disposition") == "defer" and not row.get("resume_conditions"):
            faults.append(f"{nfr_id}: deferred再開条件がない")
        if row.get("status") != "candidate_unratified" or row.get("design_not_started") is not True:
            faults.append(f"{nfr_id}: 未承認・未設計境界が不正")
        if not row.get("actors") or not row.get("scope") or not row.get("business_value"):
            faults.append(f"{nfr_id}: actor/value/scopeがない")
    expected_dispositions = {
        "NFR-1": "redescent", "NFR-2": "redescent", "NFR-3": "redescent",
        "NFR-4": "redescent", "NFR-5": "redescent", "NFR-6": "defer",
        "NFR-7": "replace", "NFR-8": "redescent", "NFR-9": "defer",
        "NFR-10": "defer", "NFR-11": "defer",
    }
    for nfr_id, expected in expected_dispositions.items():
        if by_id.get(nfr_id, {}).get("disposition") != expected:
            faults.append(f"{nfr_id}: 現要求での処置が不正")
    marker_sets = {
        "NFR-3": ["VPS製品状態正本", "SQLiteという旧手段ではなく"],
        "NFR-4": ["暗号化store", "平文env fileを許可せず"],
        "NFR-5": ["VPS UI内inbox", "一つのSQLという旧実装条件ではなく"],
        "NFR-6": ["超後期capability", "顧客入金と事業支出を別台帳"],
        "NFR-7": ["公式API/MCP", "Playwright", "旧1〜5秒一様乱数を全経路へ強制せず"],
        "NFR-9": ["stable BR/REQ", "jurisdiction"],
        "NFR-10": ["旧SQLite日次14世代", "RPO/RTO"],
        "NFR-11": ["FR-74や別NFRを根拠にせず", "stable REQ root"],
    }
    for nfr_id, markers in marker_sets.items():
        text = json.dumps(by_id.get(nfr_id, {}), ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in markers):
            faults.append(f"{nfr_id}: 旧手段から現要求への意味置換が不完全")
    return faults


def orphan_requirement_group_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """stable root又は実装降下を欠く旧FR/SRを全件候補処置へ束縛する。"""
    groups = refinements.get("legacy_orphan_requirement_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧orphan FR/SR group dispositionがない"]
    expected_ids = {
        "FR-17", "FR-35", "FR-45", "FR-48", "FR-53", "FR-72", "FR-73",
        "FR-74", "FR-75", "FR-76", "FR-77",
        *(f"SR-{index:02d}" for index in range(1, 20)),
    }
    covered = [stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧orphan FR/SR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    known_ids = {str(item.get("id")) for item in _items(ctx.frc)} | {str(item.get("id")) for item in _items(ctx.src)}
    records = refinements.get("records", [])
    subjects = {
        str(record.get("subject_id")) for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    by_id: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = group.get("stable_ids", [])
        if any(stable_id not in known_ids for stable_id in ids):
            faults.append(f"{group.get('group_id')}: unknown FR/SR ID")
        owners = group.get("owner_subject_ids", [])
        if not owners or any(owner not in subjects for owner in owners):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("disposition") == "defer" and not group.get("resume_conditions"):
            faults.append(f"{group.get('group_id')}: deferred再開条件がない")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id in ids:
            by_id[str(stable_id)] = group
    expected_dispositions = {
        "FR-45": "defer", "FR-53": "defer", "FR-72": "replace", "FR-73": "defer",
        "FR-74": "replace", "FR-75": "replace", "FR-76": "replace", "FR-77": "replace",
        "SR-15": "replace", "SR-17": "defer", "SR-18": "defer", "SR-19": "defer",
    }
    for stable_id, expected in expected_dispositions.items():
        if by_id.get(stable_id, {}).get("disposition") != expected:
            faults.append(f"{stable_id}: 現要求での処置が不正")
    markers = {
        "FR-72": ["VPS製品状態", "要求freeze後"],
        "FR-73": ["顧客入金と事業支出", "超後期"],
        "FR-74": ["profile/account登録", "新BR/REQ"],
        "FR-76": ["VPS UI内inbox", "外部通知adapterはdeferred"],
        "FR-77": ["Web UI", "認証・認可"],
        "SR-15": ["新baseline", "旧S0"],
        "SR-17": ["高度分析capability", "基本research/funnel/KPI loop"],
    }
    for stable_id, required in markers.items():
        text = json.dumps(by_id.get(stable_id, {}), ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in required):
            faults.append(f"{stable_id}: 旧責務から現要求への意味処置が不完全")
    return faults


def legacy_req_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧REQ 55件をMD/JSONのどちらも採用せず新意味への処置単位へ分類する。"""
    groups = refinements.get("legacy_req_disposition_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧REQ disposition groupがない"]
    expected_ids = {f"REQ-{index:03d}" for index in range(1, 56)}
    covered = [stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧REQ被覆が不正 missing={sorted(expected_ids - set(covered))}")
    known_ids = {str(item.get("id")) for item in _items(ctx.req)}
    records = refinements.get("records", [])
    subjects = {
        str(record.get("subject_id")) for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    by_id: dict[str, tuple[dict[str, Any], str]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = set(group.get("stable_ids", []))
        dispositions = group.get("item_dispositions", {})
        if ids != set(dispositions):
            faults.append(f"{group.get('group_id')}: stable IDと個別処置keyが不一致")
        if not ids <= known_ids:
            faults.append(f"{group.get('group_id')}: unknown REQ ID")
        deferred = {stable_id for stable_id, value in dispositions.items() if value == "defer"}
        resume = group.get("deferred_resume_by_id", {})
        if set(resume) != deferred:
            faults.append(f"{group.get('group_id')}: deferred IDと再開条件keyが不一致")
        owners = group.get("owner_subject_ids", [])
        if not owners or any(owner not in subjects for owner in owners):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id, disposition in dispositions.items():
            by_id[str(stable_id)] = (group, str(disposition))
    expected_dispositions = {
        "REQ-006": "replace", "REQ-012": "replace", "REQ-015": "replace",
        "REQ-021": "defer", "REQ-022": "replace", "REQ-024": "replace", "REQ-025": "defer",
        "REQ-026": "replace", "REQ-027": "defer", "REQ-028": "replace", "REQ-029": "replace",
        "REQ-031": "replace", "REQ-033": "replace", "REQ-034": "defer", "REQ-035": "replace",
        "REQ-036": "replace", "REQ-037": "replace", "REQ-038": "replace", "REQ-039": "replace",
        "REQ-042": "replace", "REQ-043": "replace", "REQ-044": "replace", "REQ-045": "defer",
    }
    for stable_id, expected in expected_dispositions.items():
        if by_id.get(stable_id, ({}, ""))[1] != expected:
            faults.append(f"{stable_id}: 現要求での処置が不正")
    marker_sets = {
        "REQ-006": ["VPS製品状態正本"],
        "REQ-022": ["API/MCP優先", "Playwright"],
        "REQ-024": ["VPS Web UI"],
        "REQ-026": ["公式API/MCP", "Playwright"],
        "REQ-027": ["超後期"],
        "REQ-031": ["暗号化store"],
        "REQ-033": ["content正本をWPへ一律固定せず"],
        "REQ-035": ["provider-neutral"],
        "REQ-036": ["WP content/platform/security"],
        "REQ-037": ["通常/初期setup/例外/governance/external-write"],
        "REQ-038": ["初回scope activation", "毎回承認なし"],
        "REQ-039": ["VPS UI内inbox"],
        "REQ-042": ["VPS製品状態"],
        "REQ-043": ["VPS UI read model"],
        "REQ-044": ["API/MCP quota", "Playwright節度"],
        "REQ-045": ["個別capability admission"],
    }
    for stable_id, markers in marker_sets.items():
        group = by_id.get(stable_id, ({}, ""))[0]
        text = json.dumps(group, ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in markers):
            faults.append(f"{stable_id}: 旧実現手段から現要求への置換が不完全")
    return faults


def legacy_br_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧BR 41件の価値を保持し旧実現手段だけを明示置換する。"""
    groups = refinements.get("legacy_br_disposition_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧BR disposition groupがない"]
    expected_ids = {str(item.get("id")) for item in _items(ctx.brc)}
    covered = [stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧BR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    records = refinements.get("records", [])
    subjects = {str(record.get("subject_id")) for record in records if isinstance(record, dict)}
    by_id: dict[str, tuple[dict[str, Any], str]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = set(group.get("stable_ids", []))
        dispositions = group.get("item_dispositions", {})
        if ids != set(dispositions):
            faults.append(f"{group.get('group_id')}: stable IDと個別処置keyが不一致")
        if not group.get("owner_subject_ids") or any(owner not in subjects for owner in group.get("owner_subject_ids", [])):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id, disposition in dispositions.items():
            by_id[str(stable_id)] = (group, str(disposition))
    replacements = {
        "BR-C1", "BR-C4", "BR-E2", "BR-E3", "BR-F1", "BR-F2", "BR-F4", "BR-F5",
        "BR-G2", "BR-G3", "BR-G4", "BR-H1", "BR-H2", "BR-H3",
    }
    for stable_id in replacements:
        if by_id.get(stable_id, ({}, ""))[1] != "replace":
            faults.append(f"{stable_id}: 旧実現手段をreplaceしていない")
    marker_sets = {
        "BR-E3": ["VPS Web UI"],
        "BR-F1": ["公式API/MCP", "Playwright"],
        "BR-F4": ["暗号化credential"],
        "BR-G2": ["WP一律収束"],
        "BR-G3": ["provider-neutral"],
        "BR-G4": ["content/platform/security"],
        "BR-H1": ["phase別判断"],
        "BR-H2": ["VPS UI初回activation", "自動運用"],
        "BR-H3": ["UI内inbox"],
    }
    for stable_id, markers in marker_sets.items():
        text = json.dumps(by_id.get(stable_id, ({}, ""))[0], ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in markers):
            faults.append(f"{stable_id}: 現要求への価値/手段分離が不完全")
    return faults


def legacy_media_br_disposition_faults(refinements: dict[str, Any]) -> list[str]:
    """旧媒体BR 70件を媒体名だけで有効化せずcapability候補へ分類する。"""
    rows = refinements.get("legacy_media_br_dispositions") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["旧media BR dispositionがない"]
    expected_ids = {
        str(item.get("id"))
        for path in sorted(BR_MEDIA_DIR.glob("*.json"))
        for item in _items(load(path))
    }
    covered = [stable_id for row in rows if isinstance(row, dict) for stable_id in row.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧media BR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    records = refinements.get("records", [])
    subjects = {str(record.get("subject_id")) for record in records if isinstance(record, dict)}
    by_media = {str(row.get("media_id")): row for row in rows if isinstance(row, dict)}
    for media_id, row in by_media.items():
        if not row.get("resume_conditions"):
            faults.append(f"{media_id}: capability再開条件がない")
        if not row.get("owner_subject_ids") or any(owner not in subjects for owner in row.get("owner_subject_ids", [])):
            faults.append(f"{media_id}: meaning ownerが空又は未知")
        if row.get("status") != "candidate_unratified" or row.get("design_not_started") is not True:
            faults.append(f"{media_id}: 未承認・未設計境界が不正")
    expected_replace = {"aff", "dc", "ds", "genai", "line", "meas", "wp", "x"}
    for media_id in expected_replace:
        if by_media.get(media_id, {}).get("disposition") != "replace":
            faults.append(f"{media_id}: 旧媒体意味を現capabilityへreplaceしていない")
    markers = {
        "aff": ["offerごとのowner", "権限不明なら変更しない"],
        "dc": ["通知ではないcommunity marketing", "製品通知・承認・開発PR"],
        "genai": ["Codex CLI/home", "consumer Web UI", "公式API/MCP"],
        "line": ["Messaging API第一", "attended確認"],
        "meas": ["API/MCP優先", "Playwright read確認"],
        "play": ["on-hold", "実装入力にしない"],
        "stripe": ["顧客charge", "事業支出ledgerから分離"],
        "wp": ["投稿draft/publish/update", "platform/security", "別principal/policy"],
        "x": ["公式API", "Playwright write", "attended-only"],
    }
    for media_id, required in markers.items():
        text = json.dumps(by_media.get(media_id, {}), ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in required):
            faults.append(f"{media_id}: 媒体capability意味が不完全")
    return faults


def legacy_fr_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧FR 43件を現要求へ再降下・置換・延期する処置が完全か検査する。"""
    groups = refinements.get("legacy_fr_disposition_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧FR disposition groupがない"]
    expected_ids = {str(item.get("id")) for item in _items(ctx.frc)}
    covered = [stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧FR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    subjects = {str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)}
    by_id: dict[str, tuple[dict[str, Any], str]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = set(group.get("stable_ids", []))
        dispositions = group.get("item_dispositions", {})
        if ids != set(dispositions):
            faults.append(f"{group.get('group_id')}: stable IDと個別処置keyが不一致")
        deferred = {stable_id for stable_id, value in dispositions.items() if value == "defer"}
        if deferred != set(group.get("deferred_resume_by_id", {})):
            faults.append(f"{group.get('group_id')}: deferred IDと再開条件keyが不一致")
        if any(not conditions for conditions in group.get("deferred_resume_by_id", {}).values()):
            faults.append(f"{group.get('group_id')}: deferred再開条件が空")
        if not group.get("owner_subject_ids") or any(owner not in subjects for owner in group.get("owner_subject_ids", [])):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id, disposition in dispositions.items():
            by_id[str(stable_id)] = (group, str(disposition))
    replacements = {
        "FR-11", "FR-16", "FR-23", "FR-26", "FR-41", "FR-42", "FR-43", "FR-44",
        "FR-46", "FR-47", "FR-52", "FR-55", "FR-62", "FR-63", "FR-71", "FR-72",
        "FR-74", "FR-75", "FR-76", "FR-77",
    }
    defers = {"FR-45", "FR-53", "FR-73"}
    for stable_id in replacements:
        if by_id.get(stable_id, ({}, ""))[1] != "replace":
            faults.append(f"{stable_id}: 旧実現手段をreplaceしていない")
    for stable_id in defers:
        if by_id.get(stable_id, ({}, ""))[1] != "defer":
            faults.append(f"{stable_id}: 後続価値確定までdeferしていない")
    marker_sets = {
        "FR-11": ["VPS製品状態"], "FR-16": ["安全停止", "VPS UI内inbox"],
        "FR-23": ["超後期"], "FR-41": ["公式API/MCP", "Playwright"],
        "FR-44": ["content/platform/security"], "FR-46": ["VPS UI初回activation"],
        "FR-47": ["暗号化credential"], "FR-52": ["provider-neutral"],
        "FR-55": ["媒体operation別authority"], "FR-62": ["API/MCP優先", "Playwright read確認"],
        "FR-63": ["VPS Web UI"], "FR-71": ["汎用DDL", "brand plan approvalの代替にせず"],
        "FR-72": ["migration/rollback"], "FR-74": ["profile/account lifecycle"],
        "FR-75": ["binding preflight"], "FR-76": ["VPS UI内inbox"],
        "FR-77": ["read model", "authentication/session"],
    }
    for stable_id, markers in marker_sets.items():
        text = json.dumps(by_id.get(stable_id, ({}, ""))[0], ensure_ascii=False, sort_keys=True)
        if any(marker not in text for marker in markers):
            faults.append(f"{stable_id}: 現要求への責務置換が不完全")
    return faults


def legacy_derived_contract_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧FN/AC/TCを親要求の再降下前に設計・受入証拠へ戻さない。"""
    rows = refinements.get("legacy_derived_contract_policy") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["旧派生契約policyがない"]
    actual = {"FN": ctx.fn, "AC": ctx.acc, "TC": ctx.tcc}
    by_kind = {str(row.get("kind")): row for row in rows if isinstance(row, dict)}
    faults: list[str] = []
    if set(by_kind) != set(actual) or len(rows) != len(by_kind):
        faults.append("旧派生契約kind被覆が不正")
    for kind, items in actual.items():
        row = by_kind.get(kind, {})
        stable_ids = sorted(str(item.get("id")) for item in items)
        if row.get("stable_id_count") != len(stable_ids):
            faults.append(f"{kind}: stable ID countが不一致")
        if row.get("stable_id_digest") != _digest(stable_ids):
            faults.append(f"{kind}: stable ID digestが不一致")
        if row.get("disposition") != "defer_until_parent_redescent":
            faults.append(f"{kind}: 親要求再降下までdeferしていない")
        if row.get("status") != "legacy_revalidation_only" or row.get("design_not_started") is not True:
            faults.append(f"{kind}: legacy・未設計境界が不正")
        text = json.dumps(row, ensure_ascii=False, sort_keys=True)
        rejects_claim = "みなさない" in text or "証拠にしない" in text
        if "frozen" not in text or "再生成" not in text or not rejects_claim:
            faults.append(f"{kind}: 再利用又は禁止claim境界が不完全")
    return faults


def authority_revision_candidate_faults(refinements: dict[str, Any]) -> list[str]:
    """新revision推奨案をPO未決のまま旧正本へ混入させない。"""
    candidate = refinements.get("authority_revision_candidate") if isinstance(refinements, dict) else None
    if not isinstance(candidate, dict):
        return ["authority revision候補がない"]
    faults: list[str] = []
    if candidate.get("recommended_strategy") != "new_revision_single_json_authority":
        faults.append("旧ID in-place更新を推奨している")
    if set(candidate.get("alternatives", [])) != {
        "new_revision_single_json_authority", "rewrite_legacy_ids_in_place",
    }:
        faults.append("revision strategy選択肢が不正")
    if candidate.get("po_decision") is not None or candidate.get("status") != "pending_po":
        faults.append("PO未回答を決定済みにしている")
    if candidate.get("design_not_started") is not True:
        faults.append("revision判断前に設計開始している")
    text = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
    for marker in ("supersedes", "Markdown", "旧requirements参照", "自動移植しない"):
        if marker not in text:
            faults.append("新revision又はlegacy consumer処置が不完全")
    return faults


def objective_completion_audit_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """目的別の証明済み／未完を実状態より過大に宣言させない。"""
    rows = refinements.get("objective_completion_audit") if isinstance(refinements, dict) else None
    if not isinstance(rows, list):
        return ["objective completion auditがない"]
    by_id = {str(row.get("objective_id")): row for row in rows if isinstance(row, dict)}
    faults: list[str] = []
    if set(by_id) != {"OBJ-01", "OBJ-02", "OBJ-03", "OBJ-04", "OBJ-05"} or len(rows) != len(by_id):
        faults.append("objective被覆が不正")
    expected_status = {
        "OBJ-01": "proven", "OBJ-02": "proven", "OBJ-03": "incomplete",
        "OBJ-04": "proven", "OBJ-05": "blocked_by_po",
    }
    for objective_id, status in expected_status.items():
        row = by_id.get(objective_id, {})
        if row.get("status") != status:
            faults.append(f"{objective_id}: statusが実状態と不一致")
        if not row.get("evidence"):
            faults.append(f"{objective_id}: evidenceがない")
        if status == "proven" and row.get("remaining_condition") is not None:
            faults.append(f"{objective_id}: provenなのに残条件がある")
        if status != "proven" and not row.get("remaining_condition"):
            faults.append(f"{objective_id}: 未完なのに残条件がない")
    policy = json.loads(AUTHORITY_POLICY.read_text(encoding="utf-8"))
    if policy.get("implementation_authorized") is not False:
        faults.append("implementation_authorized=falseでない")
    if by_id.get("OBJ-05", {}).get("status") == "proven":
        faults.append("新要求正本を未承認のまま完了扱い")
    return faults


def authority_faults(policy: dict[str, Any]) -> list[str]:
    faults: list[str] = []
    if policy.get("schema_version") != "marketing-harness-requirement-authority.v1":
        faults.append("authority schema_version不正")
    if policy.get("authority") != "canonical":
        faults.append("authority policyがcanonicalでない")
    adoption = policy.get("helix_engine_adoption")
    expected_adoption = {
        "status": "bridge",
        "source_model": "current_full_v_l1_l12",
        "v_pairs": ["L1-L12", "L2-L11", "L3-L10", "L4-L9", "L5-L8", "L6-L7"],
        "delivery_routes": ["production_scrum", "v_design_scrum_impl_hybrid", "discovery"],
        "scrum_reverse_stages": ["SR0", "SR1", "SR2", "SR3", "SR4"],
        "required_ir_partitions": [
            "requirements",
            "system_contracts",
            "acceptance_cases",
            "system_tests",
            "refinement_contracts",
        ],
        "missing_before_adapted": [
            "full_v_pair_authority",
            "five_partition_ir_cutover",
            "route_admission",
            "scrum_reverse_closure",
        ],
    }
    if adoption != expected_adoption:
        faults.append("現行HELIX要件エンジンのbridge境界又は未移植項目が不正")
    refinements = json.loads(REFINEMENTS.read_text(encoding="utf-8"))
    candidate_text = CANDIDATE_VIEW.read_text(encoding="utf-8") if CANDIDATE_VIEW.is_file() else ""
    refinement_ids = {
        item.get("refinement_id") for item in refinements.get("records", [])
        if isinstance(item, dict)
    }
    required_candidate_markers = {
        "GENERATED FILE", "提案専用の生成view", "現行要求の正本・PO承認・設計・実装入力ではない",
        "implementation_authorized=false", "本view全体を一括承認として扱わない",
    }
    if not candidate_text or not required_candidate_markers.issubset(set(
        marker for marker in required_candidate_markers if marker in candidate_text
    )) or any(stable_id not in candidate_text for stable_id in refinement_ids if isinstance(stable_id, str)):
        faults.append("generated requirement candidate viewが欠落又はrefinement全件・非権威境界と不一致")
    sources = policy.get("canonical_sources")
    if not isinstance(sources, list) or len(sources) != 9 or len(set(sources)) != 9:
        faults.append("canonical source 9本が一意に宣言されていない")
    elif any(not (Path(__file__).resolve().parents[2] / path).is_file() for path in sources):
        faults.append("canonical source pathが実在しない")
    applicability = policy.get("source_applicability")
    if not isinstance(applicability, dict) or set(applicability) != set(sources or []):
        faults.append("9正本のapplicability mappingが不完全")
    elif policy.get("requirements_baseline_status") == "revising" and any(
        status != "revalidation_required" for status in applicability.values()
    ):
        faults.append("revising中の9正本は全てrevalidation_requiredでなければならない")
    expected_unresolved_gates = {
        "G-REQ-SEMANTIC-DRIFT",
        "G-REQ-TRACE-BIDIR",
        "G-REQ-TRACE-LAYERS",
        "G-REQ-TRACE-IMPLEMENTATION",
        "G-REQ-TRACE-FUNCTION-LEDGER",
        "G-REQ-PHASE-ALIGNMENT",
        "G-REQ-SEMANTIC-DIMENSIONS",
        "G-REQ-OBSOLETE-RUNTIME-ROUTES",
        "G-REQ-WP-RESPONSIBILITY-BOUNDARY",
        "G-REQ-NOTIFICATION-PURPOSE-BOUNDARY",
        "G-REQ-MEDIA-ROUTE-SEMANTICS",
        "G-REQ-CONNECTOR-PRIORITY-SEMANTICS",
        "G-REQ-L2-REVALIDATION-SEMANTICS",
        "G-REQ-VPS-CREDENTIAL-BOUNDARY",
        "G-REQ-MEDIA-ADMISSION",
        "G-REQ-TRACE-SEMANTIC-RESPONSIBILITY",
        "G-REQ-DESCENT-ADMISSION",
        "G-REQ-VPS-UI-DESCENT",
        "G-REQ-HUMAN-JUDGEMENT-DESCENT",
        "G-REQ-NFR-AUTHORITY",
        "G-REQ-STRATEGY-TEST-AUTHORITY",
        "G-REQ-PROVIDER-DEPENDENCY",
        "G-REQ-OPEN-REFINEMENTS",
    }
    allowed_dispositions = {
        "po_decision_then_redescent",
        "redescent_or_deferred",
        "historical_isolation_then_redescent",
        "media_deferred_until_frozen",
        "security_po_decision_then_redescent",
        "po_decision_required",
    }
    disposition = policy.get("unresolved_semantic_gate_disposition")
    disposition_gates = disposition.get("gates") if isinstance(disposition, dict) else None
    if not isinstance(disposition, dict) or disposition.get("waiver_forbidden") is not True:
        faults.append("未解決semantic gateのwaiver禁止がない")
    if not isinstance(disposition_gates, dict) or set(disposition_gates) != expected_unresolved_gates:
        faults.append("未解決semantic gateの処理分類が不完全")
    elif any(value not in allowed_dispositions for value in disposition_gates.values()):
        faults.append("未解決semantic gateに不正な処理分類がある")
    projection = policy.get("projection")
    if not isinstance(projection, dict) or projection.get("dual_authority") != "forbidden":
        faults.append("IR dual authority禁止がない")
    refinement = policy.get("refinement")
    if not isinstance(refinement, dict) or refinement.get("bulk_approval") != "forbidden":
        faults.append("refinement一括承認禁止がない")
    if policy.get("requirements_baseline_status") == "revising" and policy.get("implementation_authorized") is not False:
        faults.append("revising中にimplementation_authorizedをtrueにできない")
    artifact_policy = policy.get("artifact_applicability_policy")
    if not isinstance(artifact_policy, dict):
        faults.append("artifact applicability policyがない")
    else:
        if artifact_policy.get("manifest_layers") != ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]:
            faults.append("revalidation対象layerがL0〜L6の閉集合でない")
        if artifact_policy.get("when_requirements_baseline_revising") != "revalidation_required":
            faults.append("revising中の既存成果物をrevalidation_requiredに固定していない")
        if artifact_policy.get("implementation_input") is not False:
            faults.append("revising中のL0〜L6成果物を実装入力にできる")
        if artifact_policy.get("confirmed_meaning") != "historical_maturity_and_receipt_only":
            faults.append("confirmedを現baseline適用済みと誤読できる")
        if artifact_policy.get("candidate_meaning") != "proposal_only_not_implementation_input":
            faults.append("candidateを実装入力にできる")
        if artifact_policy.get("exception_artifact_ids") != []:
            faults.append("revising中の実装入力例外は許可しない")
    manifest_policy = load(MANIFEST).get("applicability_policy")
    expected_manifest_policy = {
        "requirements_baseline_status": "revising",
        "current_layers": ["00-authority"],
        "revalidation_required_layers": ["L0", "L1", "L2", "L3", "L4", "L5", "L6"],
        "implementation_input": False,
        "exception_artifact_ids": [],
        "layer_policy_is_default": True,
        "per_artifact_applicability_required": True,
    }
    if manifest_policy != expected_manifest_policy:
        faults.append("manifestのL0〜L6 applicabilityがrevalidation_requiredに固定されていない")
    trusted = policy.get("trusted_decision_authorities")
    if not isinstance(trusted, dict) or trusted.get("PO") != ["po"]:
        faults.append("信頼済みPO principal閉集合が不正")
    elif set(trusted["PO"]) != requirement_discovery.TRUSTED_PO_PRINCIPALS:
        faults.append("authority policyとdiscovery gateのPO principalが不一致")
    consumer = policy.get("consumer_policy")
    if not isinstance(consumer, dict) or consumer.get("implementation_input") != "frozen_revision_only":
        faults.append("実装入力がfrozen revisionに限定されていない")
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude_text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if not all(marker in agents_text for marker in (
        "詳細な作業規律の唯一の正本は CLAUDE.md", "本ファイルと同文ではない",
        "CLAUDE.mdを優先", "requirements_baseline_status=revising",
        "implementation_authorized=false", "全媒体writeを無効",
    )):
        faults.append("AGENTS要約がCLAUDE詳細正本・revising・全write無効境界を保持しない")
    if not all(marker in claude_text for marker in (
        "本ファイルはエージェントの作業ルールの正本", "requirements_baseline_status=revising",
        "implementation_authorized=false", "全媒体writeを無効",
    )):
        faults.append("CLAUDE詳細正本がrevising・全write無効境界を保持しない")
    return faults


def obsolete_runtime_route_faults() -> list[str]:
    """VPS UI/inbox採用後も残る旧WSL／Discord初期経路を列挙する。"""
    faults: list[str] = []
    for relative_path, markers in OBSOLETE_RUNTIME_ROUTE_MARKERS.items():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            faults.append(f"{relative_path}: route監査対象が存在しない")
            continue
        body = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker in body:
                faults.append(f"{relative_path}: 旧runtime routeが残存={marker}")
    return faults


def wordpress_responsibility_boundary_faults() -> list[str]:
    """WPの日常コンテンツ運用とcore/theme/plugin保守を同じ媒体操作契約へ混在させない。"""
    data = load(MR_DIR / "wp.json")
    faults: list[str] = []
    operation_terms = ("記事作成", "更新", "下書き", "公開", "メディアアップロード", "固定ページ")
    maintenance_terms = ("子テーマ", "プラグイン", "WP-CLI", "パーマリンク", "SEO 設定")
    for item in _items(data):
        stable_id = item.get("id", "?")
        actions = item.get("actions")
        connection = item.get("connection")
        if not isinstance(actions, str):
            faults.append(f"{stable_id}: actionsが型付き責務でない")
            continue
        if any(term in actions for term in operation_terms) and any(term in actions for term in maintenance_terms):
            faults.append(f"{stable_id}: content operationとmaintenanceが同一actionsに混在")
        if isinstance(connection, str) and "REST API" in connection and "WP-CLI" in connection:
            faults.append(f"{stable_id}: REST content経路とWP-CLI maintenance経路が同一connection")
    return faults


def notification_purpose_boundary_faults(ctx: Ctx) -> list[str]:
    """投稿承認・運用通知・媒体投稿・開発PR通知の相互流用を拒否する。"""
    contracts = {str(item.get("id")): item for item in _items(ctx.frc)}
    faults: list[str] = []
    for stable_id in ("FR-16", "FR-43"):
        body = json.dumps(contracts.get(stable_id, {}), ensure_ascii=False)
        if "FR-46" in body or "ApprovalTransport" in body:
            faults.append(f"{stable_id}: escalation/repair通知が投稿可否承認FR-46へ接続")
    fr46 = json.dumps(contracts.get("FR-46", {}), ensure_ascii=False)
    if "approval_notification" not in fr46:
        faults.append("FR-46: approval_notification専用categoryがない")
    fr76 = json.dumps(contracts.get("FR-76", {}), ensure_ascii=False)
    if "operational_notification" not in fr76:
        faults.append("FR-76: operational_notification categoryがない")
    if "ApprovalTransport" in fr76 or "初期 Discord" in fr76:
        faults.append("FR-76: 運用通知が承認transport又は旧Discord初期経路を再利用")
    return faults


def media_route_semantic_faults() -> list[str]:
    """媒体BRの許可／禁止経路とMRのconnection/actionsが逆転する既知衝突を拒否する。"""
    faults: list[str] = []
    pairs = {
        name: (json.dumps(load(BR_MEDIA_DIR / f"{name}.json"), ensure_ascii=False), json.dumps(load(MR_DIR / f"{name}.json"), ensure_ascii=False))
        for name in ("line", "genai", "x", "play")
    }
    line_br, line_mr = pairs["line"]
    if "Messaging API" in line_br and "第一経路" in line_br and "Messaging API は使わない" in line_mr:
        faults.append("LINE: BRはMessaging API第一だがMRはAPI不使用browser route")
    genai_br, genai_mr = pairs["genai"]
    if "Web UI 自動操作" in genai_br and "規約明示違反" in genai_br and "Web UI 操作" in genai_mr:
        faults.append("GENAI: BRが禁止するconsumer Web UI自動操作をMRが実行経路化")
    x_br, x_mr = pairs["x"]
    if "ブラウザ書込みは事前禁止" in x_br and "Playwright" in x_mr and "ポスト投稿" in x_mr:
        faults.append("X: prohibited browser writeとMR browser connection/actionsが型分離されていない")
    play_br, play_mr = pairs["play"]
    if "保留へ降格" in play_br and "公開" in play_mr and '"lifecycle_status": "deferred"' not in play_mr:
        faults.append("PLAY: on-hold BRがMR公開routeへ伝播していない")
    return faults


def connector_priority_semantic_faults() -> list[str]:
    """外部接続route resolverの優先順が正本層ごとに分裂していないか検査する。"""
    paths = {
        "BR": REPO_ROOT / "docs/L1-business-requirements/canonical/br/br-contracts.json",
        "FR": REPO_ROOT / "docs/L3-system-requirements/canonical/functional/fr-contracts.json",
        "ADR": REPO_ROOT / "docs/00-authority/adr/ADR-006-official-api-routes.md",
        "L4": REPO_ROOT / "docs/L4-basic-design/canonical/basic-design_v0.1.md",
        "L5": REPO_ROOT / "docs/L5-detailed-design/canonical/apis/du-contracts.json",
    }
    bodies = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    old_order = "MCP → ブラウザ → 有償 API"
    faults: list[str] = []
    if old_order in bodies["BR"] or old_order in bodies["FR"]:
        if "MCP → **無料公式 API** → ブラウザ → 有償 API" in bodies["ADR"]:
            faults.append("BR/FRのMCP→browser→paidがADR-006の公式API優先と不一致")
    if "mcp → api → browser" in bodies["L4"] and "mcp → api → browser" in bodies["L5"] and old_order in bodies["FR"]:
        faults.append("FR-41とL4/L5 route resolverのAPI優先順が不一致")
    return faults


def l2_revalidation_semantic_faults(ctx: Ctx) -> list[str]:
    """旧要求から作られたL2 prototypeの未定義操作・trace・越境候補を列挙する。"""
    paths = [
        REPO_ROOT / "docs/L2-prototypes/screens/ui-screen-list_v0.1.md",
        REPO_ROOT / "docs/L2-prototypes/screens/screen-flow_v0.1.md",
        REPO_ROOT / "docs/L2-prototypes/screens/ui-element_v0.1.md",
        REPO_ROOT / "docs/L2-prototypes/screens/wireframe_v0.1.md",
        REPO_ROOT / "docs/L2-prototypes/screens/screen-detail_v0.1.md",
        REPO_ROOT / "docs/L2-prototypes/workflows/business-flow_v0.1.md",
    ]
    body = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    faults: list[str] = []
    if "Discord" in body and "AP-02" in body and "policy_category" not in body:
        faults.append("L2: Discord deep-linkがnotification classなしでapproval surfaceへ接続")
    if any(token in body for token in ("差戻し", "[return]", "／return")):
        faults.append("L2: canonical approval decisionに存在しないreturn/差戻し操作")
    fr_ids = {str(item.get("id")) for item in _items(ctx.frc)}
    if "FR-78" in body and "FR-78" not in fr_ids:
        faults.append("L2: 実在しないFR-78 trace")
    if "購読設定" in body and "subscription" in body:
        faults.append("L2: 要求契約のないnotification subscription write")
    if "全ブランド" in body and "BI-02" in body:
        faults.append("L2: cross-profile aggregate authority未定義の全ブランドBI")
    return faults


def vps_credential_boundary_faults() -> list[str]:
    """VPS credentialの平文env保存と暗号化store契約の二重正本を拒否する。"""
    adr = (REPO_ROOT / "docs/00-authority/adr/ADR-007-unattended-execution-vps.md").read_text(encoding="utf-8")
    s0 = (REPO_ROOT / "docs/L3-system-requirements/canonical/s0-contract_v0.1.md").read_text(encoding="utf-8")
    external_if = (REPO_ROOT / "docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md").read_text(encoding="utf-8")
    faults: list[str] = []
    if "環境ファイル（600 権限）" in adr and "暗号化ストアから実行時注入" in s0:
        faults.append("ADR-007の0600平文env fileとS0暗号化store契約が不一致")
    if "環境ファイル（600 権限）" in adr and "環境変数として横流ししない" in external_if:
        faults.append("ADR-007 env fileとexternal-ifの実行時secret注入境界が不一致")
    return faults


def media_requirement_admission_faults() -> list[str]:
    """全MRに実行可否・主体・副作用・policy・検証降下の型付き境界を要求する。"""
    faults: list[str] = []
    allowed_status = {"enabled", "attended-only", "read-only", "deferred"}
    for path in sorted(MR_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        for item in _items(load(path)):
            stable_id = str(item.get("id", "?"))
            if item.get("capability_status") not in allowed_status:
                faults.append(f"{stable_id}: capability_status未定義")
            for field in ("execution_mode", "principal", "effect", "policy_category"):
                if field not in item:
                    faults.append(f"{stable_id}: {field}未定義")
            trace = item.get("trace")
            downstream = trace.get("downstream") if isinstance(trace, dict) else None
            if not isinstance(downstream, list) or not downstream:
                faults.append(f"{stable_id}: downstream AC/TC/contract又はdeferred再開契約がない")
    return faults


def legacy_media_inventory_faults(refinements: dict[str, Any]) -> list[str]:
    """旧MR全件が新baselineでdeferred扱いされ、旧本文から実行許可を推測できないことを検査する。"""
    actual_ids = {
        str(item.get("id"))
        for path in sorted(MR_DIR.glob("*.json"))
        if path.name != "index.json"
        for item in _items(load(path))
        if isinstance(item.get("id"), str)
    }
    records = refinements.get("records", [])
    route = next(
        (
            record.get("legacy_media_admission")
            for record in records
            if isinstance(record, dict)
            and record.get("subject_id") == "LEGACY-MEDIA-ADMISSION-INVENTORY"
        ),
        None,
    )
    if not isinstance(route, dict):
        return ["LEGACY-MEDIA-ADMISSION-INVENTORY: legacy media admission inventoryがない"]
    faults: list[str] = []
    covered = route.get("covered_legacy_mr_ids")
    if not isinstance(covered, list) or set(covered) != actual_ids:
        faults.append("legacy media admission inventoryが旧MR全54件と一致しない")
    if route.get("default_status") != "deferred":
        faults.append("旧MRの安全側defaultがdeferredでない")
    required = {
        "business_value", "execution_mode", "principal", "effect", "policy_category",
        "credential_scope", "quota", "evidence", "acceptance_trace",
    }
    unresolved = route.get("unresolved_fields")
    if not isinstance(unresolved, list) or set(unresolved) != required:
        faults.append("旧MR再開前に閉じる意味fieldが不完全")
    resume = route.get("resume_conditions")
    if not isinstance(resume, list) or len(resume) < 2:
        faults.append("旧MRのdeferred再開条件が不完全")
    return faults


def trace_semantic_responsibility_faults(ctx: Ctx) -> list[str]:
    """ID実在だけでは検出できない既知の上位要求と下位責務の意味不一致を拒否する。"""
    brs = {str(item.get("id")): item for item in _items(ctx.brc)}
    frs = {str(item.get("id")): item for item in _items(ctx.frc)}
    faults: list[str] = []
    br_a3 = json.dumps(brs.get("BR-A3", {}), ensure_ascii=False)
    fr_71 = json.dumps(frs.get("FR-71", {}), ensure_ascii=False)
    if "brand_plans" in br_a3 and "action_plans.brand_plan_id" in br_a3:
        if "brand_plans" not in fr_71 or "action_plans.brand_plan_id" not in fr_71:
            faults.append("BR-A3/REQ-004→FR-71: brand plan保持・action plan trace責務がDDL生成契約にない")
    fr_21 = json.dumps(frs.get("FR-21", {}), ensure_ascii=False)
    if "FR-4x" in fr_21:
        faults.append("FR-21: 実行契約本文が未定義wildcard ID FR-4xを参照（FR-44等へ正規化未完）")
    cmp_contracts = json.dumps(ctx.cmpc, ensure_ascii=False)
    if "BR-31" in cmp_contracts:
        faults.append("CMP-10: security boundaryが存在しない要求ID BR-31を参照（レート節度の正規BRへ未接続）")
    return faults


def requirement_descent_admission_faults(ctx: Ctx) -> list[str]:
    """要求定義だけの契約を、実装へ降下済み又は明示延期のどちらかへ閉じる。"""
    faults: list[str] = []
    for kind, source in (("FR", ctx.frc), ("SR", ctx.src)):
        for item in _items(source):
            if item.get("design_status") != "requirements_defined":
                continue
            stable_id = str(item.get("id", "?"))
            trace_down = item.get("trace_down")
            trace_down = trace_down if isinstance(trace_down, dict) else {}
            ac_refs = trace_down.get("ac")
            fn_refs = trace_down.get("fn")
            cmp_refs = trace_down.get("cmp")
            has_acceptance = isinstance(ac_refs, list) and bool(ac_refs)
            has_implementation = (
                isinstance(fn_refs, list)
                and bool(fn_refs)
                and isinstance(cmp_refs, list)
                and bool(cmp_refs)
            )
            if has_acceptance and has_implementation:
                continue
            if item.get("admission_status") != "deferred":
                faults.append(
                    f"{kind}/{stable_id}: requirements_definedだが実装降下未完・admission_status=deferredでない"
                )
            resume = item.get("resume_conditions")
            if not isinstance(resume, list) or not resume:
                faults.append(f"{kind}/{stable_id}: deferred再開条件がない")
            if not has_acceptance:
                faults.append(f"{kind}/{stable_id}: acceptance contractへ未降下")
            if not has_implementation:
                faults.append(f"{kind}/{stable_id}: FN/CMPへ未降下")
    return faults


def vps_ui_requirement_descent_faults(ctx: Ctx) -> list[str]:
    """VPS UI主入口要求と、旧API-only閲覧契約の直接衝突を拒否する。"""
    frs = {str(item.get("id")): item for item in _items(ctx.frc)}
    fr_77 = json.dumps(frs.get("FR-77", {}), ensure_ascii=False)
    faults: list[str] = []
    if "Web UI は対象外" in fr_77 or "Web UI を提供しない" in fr_77:
        faults.append("FR-77: VPS UI主入口に必要なevidence/KPI閲覧を旧API-only契約が明示禁止")
    adr = (REPO_ROOT / "docs/00-authority/adr/ADR-013-vps-product-ui-primary-human-interface.md").read_text(encoding="utf-8")
    if "製品runtime、service、Web UI、これらの製品状態正本は\n実装・配備されていない" not in adr:
        faults.append("ADR-013: VPS配置方針と未実装runtime/UI/状態正本の現状を分離していない")
    candidate = (REPO_ROOT / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md").read_text(encoding="utf-8")
    inbox_markers = {
        "`approval_waiting`", "`safety_stopped`", "`execution_failed`",
        "`action_required`", "`operational_alert`", "`recorded`", "`failed`",
        "`retry_exhausted`", "inbox記録成立、外部配送成立、\n業務状態成立",
        "`seen`", "`acknowledged`", "`resolved`", "`expired`",
        "通知状態をapprove／reject", "業務状態に追随", "実装者が\n数値を補完しない",
    }
    missing = sorted(marker for marker in inbox_markers if marker not in candidate)
    if missing:
        faults.append(f"PRC-15: VPS UI inboxの要求意味閉集合が欠落={missing}")
    return faults


def human_judgement_descent_faults(ctx: Ctx) -> list[str]:
    """上位で必須のPO判断が下位ACで機械処理に置換される既知経路を拒否する。"""
    brs = {str(item.get("id")): item for item in _items(ctx.brc)}
    frs = {str(item.get("id")): item for item in _items(ctx.frc)}
    srs = {str(item.get("id")): item for item in _items(ctx.src)}
    ac_by_target: dict[str, list[dict[str, Any]]] = {}
    for ac in _items(ctx.acc):
        target = ac.get("target")
        if isinstance(target, str):
            ac_by_target.setdefault(target, []).append(ac)
    checks = [
        ("BR-A3", "FR-71", "brand計画確定・改訂承認"),
        ("BR-D2", "FR-32", "draft採否の人間承認"),
        ("BR-D3", "FR-33", "危険側config変更承認"),
        ("BR-D4", "FR-34", "事業profile内容確定"),
        ("BR-E1", "FR-61", "KPI tree初期承認"),
        ("BR-F1", "FR-41", "有償API例外追加承認"),
        ("BR-F3", "FR-41", "媒体追加PO判断"),
        ("BR-G3", "FR-52", "Design System改訂承認"),
        ("BR-H2", "FR-46", "オートモード移行の最終承認"),
        ("BR-H2", "FR-75", "preflight前の公開・auto-mode最終承認"),
        ("BR-F5", "FR-75", "警告停止後の再開判断"),
        ("BR-I1", "FR-34", "brand/profile追加廃止判断"),
        ("BR-I1", "FR-75", "preflight対象profile追加廃止判断"),
        ("BR-I5", "SR-06", "campaign brief確定判断"),
        ("BR-I5", "SR-14", "campaign語彙変更承認"),
        ("BR-I6", "SR-13", "企画確定判断"),
    ]
    faults: list[str] = []
    for br_id, target_id, label in checks:
        br = brs.get(br_id, {})
        target = frs.get(target_id, srs.get(target_id, {}))
        br_judgement = str(br.get("human_judgement", ""))
        target_judgement = str(target.get("human_judgement", ""))
        ac_text = json.dumps(ac_by_target.get(target_id, []), ensure_ascii=False)
        if br_judgement and not any(token in ac_text for token in ("approval_id", "PO receipt", "approver_principal")):
            faults.append(f"{br_id}->{target_id}: {label}がAC/evidenceへ降下していない")
        if target_id == "SR-13" and target_judgement.startswith("なし"):
            faults.append("BR-I6->SR-13: 企画確定の人間判断を別agent審査で代替")
        if target_id == "FR-46" and "機械判定で承認を省略" in target_judgement:
            faults.append("BR-H2->FR-46: auto適格性の機械判定がPOの移行承認を代替")
        if target_id == "FR-75" and (
            target_judgement.startswith("なし") or "自動判定" in target_judgement
        ):
            faults.append(f"{br_id}->FR-75: preflight自動判定が{label}を代替")
    return faults


def nfr_requirement_authority_faults(ctx: Ctx) -> list[str]:
    """NFRをstable REQ／BR根拠又は再開条件付きdeferredへ束縛する。"""
    reqs = {str(item.get("id")): item for item in _items(ctx.req)}
    brs = {str(item.get("id")): item for item in _items(ctx.brc)}
    faults: list[str] = []
    for nfr in _items(ctx.nfc):
        stable_id = str(nfr.get("id", "?"))
        upstream = set(_trace(nfr, contract=True)[0])
        req_refs = sorted(ref for ref in upstream if ref.startswith("REQ-"))
        br_refs = sorted(ref for ref in upstream if ref.startswith("BR-"))
        deferred = nfr.get("admission_status") == "deferred"
        resume = nfr.get("resume_conditions")
        if not req_refs and not (deferred and isinstance(resume, list) and resume):
            faults.append(f"{stable_id}: stable REQ根拠又は再開条件付きdeferredがない")
        for ref in req_refs:
            if ref not in reqs:
                faults.append(f"{stable_id}: unknown REQ root {ref}")
        for ref in br_refs:
            if ref not in brs:
                faults.append(f"{stable_id}: unknown BR root {ref}")
        if not br_refs and stable_id in {"NFR-9", "NFR-10"}:
            faults.append(f"{stable_id}: stable BR/actor/value根拠がない")
    return faults


def strategy_test_authority_faults(ctx: Ctx) -> list[str]:
    """confirmed ACがdraft strategy test ledgerを受入oracleに使うことを拒否する。"""
    refs = sorted(
        {
            str(ref)
            for ac in _items(ctx.acc)
            for ref in (ac.get("tc", []) if isinstance(ac.get("tc"), list) else [])
            if isinstance(ref, str) and ref.startswith("STC-")
        }
    )
    if not refs:
        return []
    manifest_item = next(
        (item for item in ctx.manifest_items if item.get("artifact_id") == "L4-STRATEGY-TESTS"),
        None,
    )
    if not isinstance(manifest_item, dict):
        return ["ACが参照するstrategy test ledgerがmanifestにない"]
    faults: list[str] = []
    if manifest_item.get("lifecycle_status") != "confirmed":
        faults.append(f"strategy test ledger lifecycle={manifest_item.get('lifecycle_status')} references={refs}")
    if not manifest_item.get("approval_digest"):
        faults.append("strategy test ledgerにPO content receiptがない")
    return faults


def provider_dependency_semantic_faults() -> list[str]:
    """provider-neutral候補と旧Claude/Codex/consumer UI必須経路の同時適用を拒否する。"""
    paths = {
        "charter": REPO_ROOT / "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md",
        "br": REPO_ROOT / "docs/L1-business-requirements/canonical/br/br-contracts.json",
        "genai": REPO_ROOT / "docs/L1-business-requirements/canonical/br-media/genai.json",
        "tech": REPO_ROOT / "docs/L4-basic-design/canonical/tech-stack_v0.1.md",
    }
    text = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    faults: list[str] = []
    if "Claude Design 連携（必須）" in text["charter"] or "Claude Design 正本" in text["br"]:
        faults.append("旧L0/BRがClaude Designを製品必須正本に固定")
    if "Codex CLI 内蔵 image_gen" in text["genai"] or "~/.codex/generated_images/" in text["genai"]:
        faults.append("旧媒体BRが個人Codex CLI/home証跡を製品第一経路に固定")
    if "保有アカウント Web UI" in text["tech"] or "ブラウザ生成 AI" in text["tech"]:
        faults.append("旧tech stackがconsumer Web UIを無人fallbackとして残す")
    return faults


def compatibility_drift_faults(ctx: Ctx) -> list[str]:
    """旧requirements viewが契約と同じIDで別の意味を宣言する場合に拒否する。"""
    view = {str(item["id"]): item for item in _items(ctx.requirements) if isinstance(item.get("id"), str)}
    contracts = {
        str(item["id"]): item
        for source in (ctx.frc, ctx.nfc)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    faults: list[str] = []
    for stable_id in sorted(set(view) & set(contracts)):
        old, canonical = view[stable_id], contracts[stable_id]
        old_slice, canonical_slice = old.get("slice"), canonical.get("slice")
        if old_slice is not None and canonical_slice is not None and old_slice != canonical_slice:
            faults.append(f"{stable_id}: compatibility view slice={old_slice} != contract slice={canonical_slice}")
        old_up, old_down = _trace(old, contract=False)
        canonical_up, canonical_down = _trace(canonical, contract=True)
        if old_up != canonical_up:
            faults.append(f"{stable_id}: upstream trace semantic drift")
        if old_down != canonical_down:
            faults.append(f"{stable_id}: downstream trace semantic drift")
    return faults


def req_compatibility_drift_faults(ctx: Ctx) -> list[str]:
    """確認済みREQ Markdownと機械REQ ledgerの同一ID異義を拒否する。"""
    rows: dict[str, dict[str, Any]] = {}
    for line in REQ_COMPATIBILITY_VIEW.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| REQ-[0-9]{3} \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        stable_id, text, source, related, fill, priority = cells
        rows[stable_id] = {
            "text": text,
            "source_refs": sorted(token.strip() for token in source.split("/") if token.strip() and token.strip() != "—"),
            "related": sorted(token.strip() for token in related.split(",") if token.strip() and token.strip() != "—"),
            "fill_route": None if fill == "—" else fill,
            "priority": priority,
        }
    ledger = {str(item.get("id")): item for item in _items(ctx.req)}
    faults: list[str] = []
    for stable_id in sorted(set(rows) | set(ledger)):
        if stable_id not in rows:
            faults.append(f"{stable_id}: confirmed REQ viewに存在しない")
            continue
        if stable_id not in ledger:
            faults.append(f"{stable_id}: REQ ledgerに存在しない")
            continue
        view, canonical = rows[stable_id], ledger[stable_id]
        comparisons = {
            "text": canonical.get("text"),
            "source_refs": sorted(str(value) for value in canonical.get("source_refs", [])),
            "related": sorted(str(value) for value in canonical.get("related", [])),
            "fill_route": None if canonical.get("fill_route") in {None, "—"} else canonical.get("fill_route"),
            "priority": canonical.get("priority"),
        }
        for field, canonical_value in comparisons.items():
            if view[field] != canonical_value:
                faults.append(f"{stable_id}: REQ {field} semantic drift")
    return faults


def compatibility_authority_faults(policy: dict[str, Any]) -> list[str]:
    compatibility = policy.get("compatibility_inputs")
    expected = {
        "docs/L1-business-requirements/canonical/req/req.json": "read_only_revalidation_ledger",
        "docs/L1-business-requirements/canonical/requirement-list_v0.1.md": "historical_confirmed_view_not_current_authority",
        str(COMPATIBILITY_VIEW.relative_to(Path(__file__).resolve().parents[2])): "read_only_revalidation_view",
        "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md": "historical_confirmed_view_not_current_authority",
    }
    faults = [] if compatibility == expected else ["requirements.json compatibility viewの非権威境界が不正"]
    for relative_path, markers in HISTORICAL_VIEW_BANNERS.items():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            faults.append(f"{relative_path}: historical/revalidation文書が存在しない")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            faults.append(f"{relative_path}: historical/non-input banner不足={missing}")
    return faults


def legacy_requirement_consumer_faults() -> list[str]:
    """旧REQ/requirements viewを上位・設計・検証の規範入力として参照する導線を拒否する。"""
    consumers = {
        "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md",
        "docs/L3-system-requirements/canonical/s0-contract_v0.1.md",
        "docs/L3-system-requirements/verification/verification-design_v0.1.md",
        "docs/L4-basic-design/canonical/basic-design_v0.1.md",
        "docs/L3-system-requirements/canonical/schemas/s0/trace.json",
    }
    legacy_reference = re.compile(
        r"(?<![A-Za-z0-9_-])(?:docs/L3-system-requirements/canonical/functional/)?requirements_v0\.1\.md(?![A-Za-z0-9_-])"
    )
    faults: list[str] = []
    for relative_path in sorted(consumers):
        path = REPO_ROOT / relative_path
        if not path.is_file():
            faults.append(f"{relative_path}: consumerが存在しない")
        elif legacy_reference.search(path.read_text(encoding="utf-8")):
            faults.append(f"{relative_path}: 旧requirements viewを規範参照")
    return faults


def design_not_started_faults(ctx: Ctx) -> list[str]:
    """要求revising中にL2以降を現行設計・実装入力として扱うことを拒否する。"""
    faults: list[str] = []
    for item in ctx.manifest_items:
        path = str(item.get("canonical_path", ""))
        if not re.match(r"docs/L[2-6]-", path):
            continue
        artifact_id = str(item.get("artifact_id", path))
        if item.get("applicability_status") != "revalidation_required":
            faults.append(f"{artifact_id}: L2-L6 applicabilityがrevalidation_requiredでない")
        if item.get("implementation_input") is not False:
            faults.append(f"{artifact_id}: 要求freeze前にimplementation_input=true")
        if path.startswith("docs/L2-") and item.get("lifecycle_status") != "draft":
            faults.append(f"{artifact_id}: 旧L2がdraftでない")
    candidate = (
        REPO_ROOT
        / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md"
    ).read_text(encoding="utf-8")
    required_markers = {
        "本ベースライン承認後にL2以降を新規に降下する",
        "旧画面、API、DDL、状態、slice、AC／TC、実装単位は\n参考資料に限り",
        "framework、component、URL、port、reverse proxy、認証protocol、session実装、CSRF方式、DB table、API、\nscreen ID、状態enum、retry回数、deployment topologyは設計事項である",
    }
    missing = sorted(marker for marker in required_markers if marker not in candidate)
    if missing:
        faults.append(f"要求候補に設計未着手境界がない={missing}")
    return faults


def bidirectional_trace_faults(ctx: Ctx) -> list[str]:
    """BR trace_down と FR/SR trace_up の相互参照を検査する。"""
    brs = {str(item["id"]): item for item in _items(ctx.brc) if isinstance(item.get("id"), str)}
    children = {
        str(item["id"]): item
        for source in (ctx.frc, ctx.src)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    faults: list[str] = []
    for br_id, br in sorted(brs.items()):
        if not isinstance(br_id, str):
            continue
        _, declared = _trace(br, contract=True)
        for child_id in (ref for ref in declared if ref.startswith(("FR-", "SR-"))):
            child = children.get(child_id)
            if child is None:
                faults.append(f"{br_id}: trace_down orphan {child_id}")
            elif br_id not in _trace(child, contract=True)[0]:
                faults.append(f"{br_id}->{child_id}: child trace_up missing parent")
    for child_id, child in sorted(children.items()):
        for br_id in (ref for ref in _trace(child, contract=True)[0] if ref.startswith("BR-")):
            parent = brs.get(br_id)
            if parent is None:
                faults.append(f"{child_id}: trace_up orphan {br_id}")
            elif child_id not in _trace(parent, contract=True)[1]:
                faults.append(f"{br_id}->{child_id}: parent trace_down missing child")
    return faults


def layered_trace_faults(ctx: Ctx) -> list[str]:
    """BR→REQ→FR/SR/NFR の各隣接辺を双方向に検査する。"""
    brs = {str(item["id"]): item for item in _items(ctx.brc) if isinstance(item.get("id"), str)}
    reqs = {str(item["id"]): item for item in _items(ctx.req) if isinstance(item.get("id"), str)}
    contracts = {
        str(item["id"]): item
        for source in (ctx.frc, ctx.src, ctx.nfc)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    faults: list[str] = []

    for br_id, br in sorted(brs.items()):
        declared_req = {
            ref for ref in _trace(br, contract=True)[1] if ref.startswith("REQ-")
        }
        for req_id in sorted(declared_req):
            req = reqs.get(req_id)
            if req is None:
                faults.append(f"{br_id}: REQ orphan {req_id}")
            elif br_id not in _trace(req, contract=False)[0]:
                faults.append(f"{br_id}->{req_id}: REQ upstream missing BR")

    for req_id, req in sorted(reqs.items()):
        req_up, req_down = _trace(req, contract=False)
        for br_id in sorted(ref for ref in req_up if ref.startswith("BR-")):
            parent = brs.get(br_id)
            if parent is None:
                faults.append(f"{req_id}: BR orphan {br_id}")
            elif req_id not in _trace(parent, contract=True)[1]:
                faults.append(f"{br_id}->{req_id}: BR downstream missing REQ")
        for contract_id in sorted(
            ref for ref in req_down if ref.startswith(("FR-", "SR-", "NFR-"))
        ):
            contract = contracts.get(contract_id)
            if contract is None:
                faults.append(f"{req_id}: contract orphan {contract_id}")
            elif req_id not in _trace(contract, contract=True)[0]:
                faults.append(f"{req_id}->{contract_id}: contract upstream missing REQ")

    for contract_id, contract in sorted(contracts.items()):
        req_roots = sorted(
            ref for ref in _trace(contract, contract=True)[0] if ref.startswith("REQ-")
        )
        deferred = contract.get("admission_status") == "deferred"
        resume = contract.get("resume_conditions")
        if not req_roots and not (deferred and isinstance(resume, list) and resume):
            faults.append(
                f"{contract_id}: stable REQ root又は再開条件付きdeferredがない"
            )
        for req_id in req_roots:
            req = reqs.get(req_id)
            if req is None:
                faults.append(f"{contract_id}: REQ orphan {req_id}")
            elif contract_id not in _trace(req, contract=False)[1]:
                faults.append(f"{req_id}->{contract_id}: REQ downstream missing contract")
    return faults


def implementation_trace_faults(ctx: Ctx) -> list[str]:
    """DUからAC/TCへの参照が現行契約IDへ解決することを検査する。"""
    ac_ids = {str(item["id"]) for item in _items(ctx.acc) if isinstance(item.get("id"), str)}
    tc_ids = {str(item["id"]) for item in _items(ctx.tcc) if isinstance(item.get("id"), str)}
    strategy_test_ids = {str(item["id"]) for item in _items(ctx.stc) if isinstance(item.get("id"), str)}
    faults: list[str] = []
    for du in _items(ctx.duc):
        du_id = str(du.get("id", "?"))
        trace = du.get("trace", {})
        if not isinstance(trace, dict):
            faults.append(f"{du_id}: traceがobjectでない")
            continue
        ac_refs = trace.get("ac", [])
        tc_refs = trace.get("tc", [])
        if not isinstance(ac_refs, list) or not isinstance(tc_refs, list):
            faults.append(f"{du_id}: trace.ac/tcが配列でない")
            continue
        for ref in ac_refs:
            if not isinstance(ref, str) or ref not in ac_ids:
                faults.append(f"{du_id}: unknown AC reference {ref}")
        for ref in tc_refs:
            if not isinstance(ref, str) or ref not in tc_ids | strategy_test_ids:
                faults.append(f"{du_id}: unknown TC reference {ref}")
            elif not ref.startswith(("TCC-", "STC-")):
                faults.append(f"{du_id}: non-canonical TC ID {ref}")
    return faults


def functional_ledger_trace_faults(ctx: Ctx) -> list[str]:
    """REQ compatibility ledgerとFN ledgerの隣接traceを双方向に検査する。"""
    reqs = {str(item["id"]): item for item in _items(ctx.req) if isinstance(item.get("id"), str)}
    functions = {str(item["id"]): item for item in _items(ctx.fn) if isinstance(item.get("id"), str)}
    faults: list[str] = []
    for req_id, req in sorted(reqs.items()):
        for fn_id in sorted(ref for ref in _trace(req, contract=False)[1] if ref.startswith("FN-")):
            function = functions.get(fn_id)
            if function is None:
                faults.append(f"{req_id}: FN orphan {fn_id}")
            elif req_id not in _trace(function, contract=False)[0]:
                faults.append(f"{req_id}->{fn_id}: FN upstream missing REQ")
    for fn_id, function in sorted(functions.items()):
        for req_id in sorted(ref for ref in _trace(function, contract=False)[0] if ref.startswith("REQ-")):
            req_entry = reqs.get(req_id)
            if req_entry is None:
                faults.append(f"{fn_id}: REQ orphan {req_id}")
            elif fn_id not in _trace(req_entry, contract=False)[1]:
                faults.append(f"{req_id}->{fn_id}: REQ downstream missing FN")
    return faults


def phase_alignment_faults(ctx: Ctx) -> list[str]:
    """FR→FN→AC/TCCの導入phaseが同じ責務内で一致することを検査する。"""
    frs = {str(item["id"]): item for item in _items(ctx.frc) if isinstance(item.get("id"), str)}
    faults: list[str] = []
    for function in _items(ctx.fn):
        fn_id = str(function.get("id", "?"))
        fn_phase = function.get("slice")
        for fr_id in (ref for ref in _trace(function, contract=False)[0] if ref.startswith("FR-")):
            fr = frs.get(fr_id)
            if fr is None:
                continue
            fr_phase = fr.get("slice")
            if fn_phase != fr_phase:
                faults.append(f"{fr_id}({fr_phase})->{fn_id}({fn_phase}): phase mismatch")
    for ac in _items(ctx.acc):
        ac_id = str(ac.get("id", "?"))
        target = ac.get("target")
        if not isinstance(target, str) or target not in frs:
            continue
        fr_phase = frs[target].get("slice")
        update = ac.get("target_update")
        match = re.match(r"^(S[0-9]+)(?:\.[0-9]+|\+)?", update) if isinstance(update, str) else None
        if match is None:
            faults.append(f"{ac_id}: target_updateから厳密phaseを導出できない")
            continue
        ac_phase = match.group(1)
        if isinstance(fr_phase, str) and fr_phase.endswith("+"):
            faults.append(f"{target}: 包含phase {fr_phase} を実装phaseに使えない")
        elif ac_phase != fr_phase:
            faults.append(f"{target}({fr_phase})->{ac_id}({ac_phase}): phase mismatch")
    return faults


def semantic_dimension_faults(ctx: Ctx) -> list[str]:
    """各要求・受入層が実装判断に必要な意味軸を直接又は型付きで持つか検査する。"""
    required = {
        "BR": {"actor", "value", "scope_in", "scope_out", "prohibitions", "human_judgement", "completion_evidence"},
        "BRM": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "REQ": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "FR": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "SR": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "NFR": {"actor", "beneficiaries", "value", "scope_in", "scope_out", "human_judgement", "side_effects", "evidence", "phase"},
        "MR": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "FN": {"actor", "beneficiaries", "value", "workflow", "scope_in", "scope_out", "prohibitions", "human_judgement", "side_effects", "evidence", "phase"},
        "AC": {"actor", "scope", "human_judgement", "side_effects", "evidence", "phase"},
        "TC": {"actor", "scope", "side_effects", "evidence", "phase"},
    }
    sources = {
        "BR": ctx.brc,
        "BRM": [item for path in sorted(BR_MEDIA_DIR.glob("*.json")) for item in _items(load(path))],
        "REQ": ctx.req,
        "FR": ctx.frc,
        "SR": ctx.src,
        "NFR": ctx.nfc,
        "MR": [item for path in sorted(MR_DIR.glob("*.json")) if path.name != "index.json" for item in _items(load(path))],
        "FN": ctx.fn,
        "AC": ctx.acc,
        "TC": ctx.tcc,
    }
    aliases = {
        "phase": ("phase", "slice"),
        "evidence": ("evidence", "completion_evidence", "expected_evidence", "verifies_evidence"),
        "side_effects": ("side_effects", "forbidden_side_effects", "external_calls"),
        # AC.target/target_updateは要求ID・更新worksetであり、business/profile/data/
        # permission scopeではない。scopeの代用品にすると越境ACをgreenにできる。
        "scope": ("scope",),
    }
    faults: list[str] = []
    for kind, source in sources.items():
        for item in _items(source):
            stable_id = str(item.get("id", "?"))
            for dimension in sorted(required[kind]):
                keys = aliases.get(dimension, (dimension,))
                if not any(key in item and item.get(key) not in (None, "", []) for key in keys):
                    faults.append(f"{kind}/{stable_id}: semantic dimension {dimension} missing")
    return faults


def active_approval_requests(data: dict[str, Any]) -> list[str]:
    events = [event for event in data.get("events", []) if isinstance(event, dict)]
    terminal = {
        event.get("subject_id")
        for event in events
        if event.get("event_type") in {"approval_decided", "withdrawn"}
    }
    return sorted(
        {
            str(event.get("subject_id"))
            for event in events
            if event.get("event_type") == "approval_requested"
            and event.get("subject_id") not in terminal
        }
    )


def refinement_faults(data: dict[str, Any], discovery: dict[str, Any]) -> list[str]:
    """refinement recordの意味閉包・digest・承認束縛を検査する。"""
    faults: list[str] = []
    if data.get("schema_version") != "marketing-harness-requirements-refinement.v1":
        faults.append("refinement schema_version が不正")
    if data.get("authority") != "canonical":
        faults.append("refinement authority がcanonicalでない")
    records = data.get("records")
    if not isinstance(records, list):
        return faults + ["refinement records が配列でない"]
    delivery_sequence = {
        "MEDIA-POC-SCRUM-RELEASE": (1, 1, set()),
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE": (1, 1, set()),
        "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE": (
            1, 2, {"WORDPRESS-CONTENT-OPERATIONS-RELEASE"},
        ),
        "WORDPRESS-SECURITY-MAINTENANCE-RELEASE": (
            1, 2, {"WORDPRESS-CONTENT-OPERATIONS-RELEASE"},
        ),
        "AGENT-NEO-SITE-BUILD-RELEASE": (
            2,
            3,
            {
                "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE",
                "WORDPRESS-SECURITY-MAINTENANCE-RELEASE",
            },
        ),
        "AGENT-NEO-PRODUCT-EVOLUTION-RELEASE": (
            3, 4, {"AGENT-NEO-SITE-BUILD-RELEASE"},
        ),
    }
    events = {
        event.get("event_id"): event
        for event in discovery.get("events", [])
        if isinstance(event, dict) and isinstance(event.get("event_id"), str)
    }
    seen: set[tuple[str, int]] = set()
    for index, record in enumerate(records):
        label = f"refinement[{index}]"
        if not isinstance(record, dict):
            faults.append(f"{label}: objectでない")
            continue
        subject = record.get("subject_id")
        revision = record.get("revision")
        key = (str(subject), revision) if isinstance(revision, int) else (str(subject), -1)
        if key in seen:
            faults.append(f"{label}: subject/revision重複 {key}")
        seen.add(key)
        source_ids = record.get("source_event_ids")
        if not isinstance(source_ids, list) or not source_ids or any(item not in events for item in source_ids):
            faults.append(f"{label}: source_event_ids が空又はorphan")
            source_events: list[dict[str, Any]] = []
        else:
            source_events = [events[item] for item in source_ids]
            if any(event.get("subject_id") != subject for event in source_events):
                faults.append(f"{label}: source event subject不一致")
        expected_source_digest = _digest(source_events)
        if record.get("source_set_digest") != expected_source_digest:
            faults.append(f"{label}: source_set_digest不一致")
        dimensions = record.get("semantic_dimensions")
        required_dimensions = {
            "actors", "beneficiaries", "value", "tasks", "workflow", "scope_in", "scope_out",
            "prohibitions", "human_judgement", "side_effects", "evidence", "phase",
        }
        if not isinstance(dimensions, dict) or set(dimensions) != required_dimensions:
            faults.append(f"{label}: semantic dimensions不完全")
        if subject in delivery_sequence:
            admission = record.get("delivery_admission")
            expected_stage, expected_sequence, expected_predecessors = delivery_sequence[str(subject)]
            if not isinstance(admission, dict):
                faults.append(f"{label}: delivery_admissionがない")
            else:
                if admission.get("standard_model") != "full_v_l1_l12":
                    faults.append(f"{label}: Full V L1-L12が標準工程でない")
                routes = admission.get("increment_routes")
                if not isinstance(routes, list) or not routes or "none" in routes:
                    faults.append(f"{label}: Scrum/Hybrid increment routeが不正")
                if admission.get("discovery_condition") != (
                    "only_when_feasibility_or_success_condition_unknown"
                ):
                    faults.append(f"{label}: Discoveryが未知条件限定でない")
                if admission.get("sequence") != expected_sequence:
                    faults.append(f"{label}: delivery sequence不一致")
                if admission.get("program_stage") != expected_stage:
                    faults.append(f"{label}: program stage不一致")
                predecessors = admission.get("predecessor_subject_ids")
                if not isinstance(predecessors, list) or set(predecessors) != expected_predecessors:
                    faults.append(f"{label}: predecessor release不一致")
                if admission.get("completion_boundary") != (
                    "po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure"
                ):
                    faults.append(f"{label}: completion boundary不一致")
        acceptance = record.get("acceptance_cases")
        polarities = {
            item.get("polarity") for item in acceptance if isinstance(item, dict)
        } if isinstance(acceptance, list) else set()
        if polarities != {"positive", "negative", "boundary"}:
            faults.append(f"{label}: positive/negative/boundary acceptanceが揃っていない")
        pending = record.get("pending_resolution")
        lifecycle = record.get("lifecycle_status")
        if lifecycle in {"specified", "approved", "frozen"} and pending != []:
            faults.append(f"{label}: {lifecycle}にpending_resolutionを残せない")
        semantic = {key: value for key, value in record.items() if key not in {"semantic_digest", "approval"}}
        if record.get("semantic_digest") != _digest(semantic):
            faults.append(f"{label}: semantic_digest不一致")
        approval = record.get("approval")
        if lifecycle in {"approved", "frozen"}:
            if not isinstance(approval, dict):
                faults.append(f"{label}: approved/frozenにPO approvalがない")
            else:
                if approval.get("authority") != "PO":
                    faults.append(f"{label}: approval authorityがPOでない")
                if approval.get("approver_principal") != "po":
                    faults.append(f"{label}: approver principalが信頼済みPOでない")
                if approval.get("approved_revision") != revision:
                    faults.append(f"{label}: approved_revision不一致")
                if approval.get("subject_digest") != record.get("semantic_digest"):
                    faults.append(f"{label}: approval subject_digest不一致")
                if approval.get("source_set_digest") != record.get("source_set_digest"):
                    faults.append(f"{label}: approval source_set_digest不一致")
        elif approval is not None:
            faults.append(f"{label}: 未承認lifecycleにapprovalを持てない")
    return faults


def refinement_coverage_faults(data: dict[str, Any], discovery: dict[str, Any]) -> list[str]:
    """discoveryへ記録した全要求候補が個別refinementを持つことを検査する。"""
    candidate_subjects = {
        str(event.get("subject_id"))
        for event in discovery.get("events", [])
        if isinstance(event, dict)
        and event.get("event_type") == "candidate_recorded"
        and isinstance(event.get("subject_id"), str)
    }
    records = data.get("records", [])
    refinement_subjects = (
        {
            str(record.get("subject_id"))
            for record in records
            if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
        }
        if isinstance(records, list)
        else set()
    )
    faults = [
        f"{subject}: discovery候補に対応するrefinementがない"
        for subject in sorted(candidate_subjects - refinement_subjects)
    ]
    faults.extend(
        f"{subject}: candidate_recordedのないrefinement"
        for subject in sorted(refinement_subjects - candidate_subjects)
    )
    return faults


def open_refinement_faults(data: dict[str, Any]) -> list[str]:
    """要求完了を妨げる未凍結refinementを列挙する。"""
    records = data.get("records", [])
    if not isinstance(records, list):
        return ["refinement recordsが配列でない"]
    faults: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        subject = str(record.get("subject_id", "?"))
        lifecycle = record.get("lifecycle_status")
        pending = record.get("pending_resolution")
        approval = record.get("approval")
        if lifecycle != "frozen":
            faults.append(f"{subject}: lifecycle={lifecycle}（frozenでない）")
        if pending != []:
            count = len(pending) if isinstance(pending, list) else "不正"
            faults.append(f"{subject}: pending_resolution={count}")
        if not isinstance(approval, dict):
            faults.append(f"{subject}: PO approval receiptがない")
    return faults


def semantic_closure_faults(ctx: Ctx) -> list[str]:
    """要求承認・authority cutoverの双方を止める意味レベル違反の完全集合。"""
    return (
        compatibility_drift_faults(ctx)
        + req_compatibility_drift_faults(ctx)
        + bidirectional_trace_faults(ctx)
        + layered_trace_faults(ctx)
        + implementation_trace_faults(ctx)
        + functional_ledger_trace_faults(ctx)
        + phase_alignment_faults(ctx)
        + semantic_dimension_faults(ctx)
        + obsolete_runtime_route_faults()
        + wordpress_responsibility_boundary_faults()
        + notification_purpose_boundary_faults(ctx)
        + media_route_semantic_faults()
        + connector_priority_semantic_faults()
        + l2_revalidation_semantic_faults(ctx)
        + vps_credential_boundary_faults()
        + media_requirement_admission_faults()
        + trace_semantic_responsibility_faults(ctx)
        + requirement_descent_admission_faults(ctx)
        + vps_ui_requirement_descent_faults(ctx)
        + human_judgement_descent_faults(ctx)
        + nfr_requirement_authority_faults(ctx)
        + strategy_test_authority_faults(ctx)
        + provider_dependency_semantic_faults()
        + legacy_requirement_consumer_faults()
    )


def approval_admission_faults(
    ctx: Ctx, data: dict[str, Any], refinements: dict[str, Any] | None = None
) -> list[str]:
    active = active_approval_requests(data)
    if not active:
        return []
    semantic = semantic_closure_faults(ctx)
    if semantic:
        return [f"approval admission: semantic faults={len(semantic)} active={active}"]
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    specified = {
        record.get("subject_id")
        for record in records
        if isinstance(record, dict)
        and record.get("lifecycle_status") == "specified"
        and record.get("pending_resolution") == []
    }
    missing = sorted(set(active) - specified)
    if missing:
        return [f"approval admission: specified refinementがない active={missing}"]
    return []


def authority_cutover_faults(
    ctx: Ctx,
    policy: dict[str, Any],
    refinements: dict[str, Any],
    discovery: dict[str, Any],
) -> list[str]:
    """実装入力へのauthority cutoverを全条件同時成立でのみ許可する。"""
    authorized = policy.get("implementation_authorized") is True
    status = policy.get("requirements_baseline_status")
    if not authorized:
        return [] if status == "revising" else ["implementation禁止時はbaseline status=revisingが必要"]
    faults: list[str] = []
    if status != "approved":
        faults.append("implementation_authorized=trueにはbaseline status=approvedが必要")
    semantic = semantic_closure_faults(ctx)
    if semantic:
        faults.append(f"semantic closure未成立={len(semantic)}")
    refinement = refinement_faults(refinements, discovery)
    if refinement:
        faults.append(f"refinement validation未成立={len(refinement)}")
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    if not isinstance(records, list) or not records:
        faults.append("cutover対象refinementがない")
    elif any(
        not isinstance(record, dict)
        or record.get("lifecycle_status") != "frozen"
        or not isinstance(record.get("approval"), dict)
        for record in records
    ):
        faults.append("全refinementがPO receipt付きfrozenでない")
    if active_approval_requests(discovery):
        faults.append("未決のapproval requestが残っている")
    return faults


def engine_report(ctx: Ctx) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """要件エンジンの現状態と、工程別の全違反を副作用なく返す。"""
    data = requirement_discovery.load_discovery_ledger()
    policy = json.loads(AUTHORITY_POLICY.read_text(encoding="utf-8"))
    refinements = json.loads(REFINEMENTS.read_text(encoding="utf-8"))
    projection = semantic_projection(ctx)
    faults = {
        "authority": authority_faults(policy),
        "compatibility_authority": compatibility_authority_faults(policy),
        "projection": projection_faults(projection),
        "semantic_drift": compatibility_drift_faults(ctx) + req_compatibility_drift_faults(ctx),
        "direct_trace": bidirectional_trace_faults(ctx),
        "layered_trace": layered_trace_faults(ctx),
        "implementation_trace": implementation_trace_faults(ctx),
        "functional_ledger_trace": functional_ledger_trace_faults(ctx),
        "phase_alignment": phase_alignment_faults(ctx),
        "semantic_dimensions": semantic_dimension_faults(ctx),
        "obsolete_runtime_routes": obsolete_runtime_route_faults(),
        "wordpress_responsibility_boundary": wordpress_responsibility_boundary_faults(),
        "notification_purpose_boundary": notification_purpose_boundary_faults(ctx),
        "media_route_semantics": media_route_semantic_faults(),
        "connector_priority_semantics": connector_priority_semantic_faults(),
        "l2_revalidation_semantics": l2_revalidation_semantic_faults(ctx),
        "vps_credential_boundary": vps_credential_boundary_faults(),
        "media_requirement_admission": media_requirement_admission_faults(),
        "legacy_media_inventory": legacy_media_inventory_faults(refinements),
        "trace_semantic_responsibility": trace_semantic_responsibility_faults(ctx),
        "requirement_descent_admission": requirement_descent_admission_faults(ctx),
        "vps_ui_requirement_descent": vps_ui_requirement_descent_faults(ctx),
        "human_judgement_descent": human_judgement_descent_faults(ctx),
        "nfr_requirement_authority": nfr_requirement_authority_faults(ctx),
        "strategy_test_authority": strategy_test_authority_faults(ctx),
        "provider_dependency_semantics": provider_dependency_semantic_faults(),
        "legacy_requirement_consumers": legacy_requirement_consumer_faults(),
        "design_not_started": design_not_started_faults(ctx),
        "scope_assignment": scope_assignment_faults(refinements),
        "decision_packets": decision_packet_faults(refinements),
        "candidate_requirement_bindings": candidate_requirement_binding_faults(refinements),
        "l0_clause_dispositions": l0_clause_disposition_faults(refinements),
        "critical_responsibility_dispositions": critical_responsibility_disposition_faults(refinements),
        "semantic_descent_policy": semantic_descent_policy_faults(refinements),
        "legacy_nfr_dispositions": legacy_nfr_disposition_faults(ctx, refinements),
        "orphan_requirement_groups": orphan_requirement_group_faults(ctx, refinements),
        "legacy_req_dispositions": legacy_req_disposition_faults(ctx, refinements),
        "legacy_br_dispositions": legacy_br_disposition_faults(ctx, refinements),
        "legacy_media_br_dispositions": legacy_media_br_disposition_faults(refinements),
        "legacy_fr_dispositions": legacy_fr_disposition_faults(ctx, refinements),
        "legacy_derived_contracts": legacy_derived_contract_faults(ctx, refinements),
        "authority_revision_candidate": authority_revision_candidate_faults(refinements),
        "objective_completion_audit": objective_completion_audit_faults(ctx, refinements),
        "refinement": refinement_faults(refinements, data),
        "refinement_coverage": refinement_coverage_faults(refinements, data),
        "open_refinements": open_refinement_faults(refinements),
        "approval_admission": approval_admission_faults(ctx, data, refinements),
        "authority_cutover": authority_cutover_faults(ctx, policy, refinements, data),
    }
    state = {
        "projection": projection,
        "policy": policy,
        "refinements": refinements,
        "discovery": data,
    }
    return state, faults


def run(ctx: Ctx) -> None:
    state, faults = engine_report(ctx)
    projection = state["projection"]
    authority = faults["authority"]
    compatibility_authority = faults["compatibility_authority"]
    projection_errors = faults["projection"]
    drift = faults["semantic_drift"]
    trace = faults["direct_trace"]
    layered_trace = faults["layered_trace"]
    implementation_trace = faults["implementation_trace"]
    functional_ledger_trace = faults["functional_ledger_trace"]
    phase_alignment = faults["phase_alignment"]
    semantic_dimensions = faults["semantic_dimensions"]
    obsolete_runtime_routes = faults["obsolete_runtime_routes"]
    wordpress_responsibility_boundary = faults["wordpress_responsibility_boundary"]
    notification_purpose_boundary = faults["notification_purpose_boundary"]
    media_route_semantics = faults["media_route_semantics"]
    connector_priority_semantics = faults["connector_priority_semantics"]
    l2_revalidation_semantics = faults["l2_revalidation_semantics"]
    vps_credential_boundary = faults["vps_credential_boundary"]
    media_requirement_admission = faults["media_requirement_admission"]
    legacy_media_inventory = faults["legacy_media_inventory"]
    trace_semantic_responsibility = faults["trace_semantic_responsibility"]
    requirement_descent_admission = faults["requirement_descent_admission"]
    vps_ui_requirement_descent = faults["vps_ui_requirement_descent"]
    human_judgement_descent = faults["human_judgement_descent"]
    nfr_requirement_authority = faults["nfr_requirement_authority"]
    strategy_test_authority = faults["strategy_test_authority"]
    provider_dependency_semantics = faults["provider_dependency_semantics"]
    legacy_requirement_consumers = faults["legacy_requirement_consumers"]
    design_not_started = faults["design_not_started"]
    scope_assignment = faults["scope_assignment"]
    decision_packets = faults["decision_packets"]
    candidate_requirement_bindings = faults["candidate_requirement_bindings"]
    l0_clause_dispositions = faults["l0_clause_dispositions"]
    critical_responsibility_dispositions = faults["critical_responsibility_dispositions"]
    semantic_descent_policy = faults["semantic_descent_policy"]
    legacy_nfr_dispositions = faults["legacy_nfr_dispositions"]
    orphan_requirement_groups = faults["orphan_requirement_groups"]
    legacy_req_dispositions = faults["legacy_req_dispositions"]
    legacy_br_dispositions = faults["legacy_br_dispositions"]
    legacy_media_br_dispositions = faults["legacy_media_br_dispositions"]
    legacy_fr_dispositions = faults["legacy_fr_dispositions"]
    legacy_derived_contracts = faults["legacy_derived_contracts"]
    authority_revision_candidate = faults["authority_revision_candidate"]
    objective_completion_audit = faults["objective_completion_audit"]
    refinement = faults["refinement"]
    refinement_coverage = faults["refinement_coverage"]
    open_refinements = faults["open_refinements"]
    admission = faults["approval_admission"]
    cutover = faults["authority_cutover"]
    gate("G-REQ-AUTHORITY", not authority, f"9正本・非二重化・revising・frozen cutover境界を検査 (違反={authority})")
    gate("G-REQ-COMPATIBILITY-AUTHORITY", not compatibility_authority, f"旧requirements viewを非権威・read-onlyに固定 (違反={compatibility_authority})")
    gate("G-REQ-IR-PROJECTION", not projection_errors, f"決定的IR projection {len(projection['records'])}件 (違反={projection_errors})")
    gate("G-REQ-SEMANTIC-DRIFT", not drift, f"同一IDの意味差分を拒否 (違反={drift[:5]})")
    gate("G-REQ-TRACE-BIDIR", not trace, f"BR→FR/SR意味traceを双方向検査 (違反={trace[:5]})")
    gate("G-REQ-TRACE-LAYERS", not layered_trace, f"BR→REQ→FR/SR/NFR隣接traceを双方向検査 (違反={layered_trace[:5]})")
    gate("G-REQ-TRACE-IMPLEMENTATION", not implementation_trace, f"DU→AC/TCC参照を現行IDへ解決 (違反={implementation_trace[:5]})")
    gate("G-REQ-TRACE-FUNCTION-LEDGER", not functional_ledger_trace, f"REQ→FN ledger参照を双方向検査 (違反={functional_ledger_trace[:5]})")
    gate("G-REQ-PHASE-ALIGNMENT", not phase_alignment, f"FR→FN→ACの導入phaseを厳密照合 (違反={phase_alignment[:5]})")
    gate("G-REQ-SEMANTIC-DIMENSIONS", not semantic_dimensions, f"BR/BRM/REQ/FR/SR/NFR/MR/FN/AC/TCの意味軸閉包を検査 (違反={semantic_dimensions[:5]})")
    gate("G-REQ-OBSOLETE-RUNTIME-ROUTES", not obsolete_runtime_routes, f"VPS UI/inbox採用後のWSL cron・Discord初期固定を拒否 (違反={obsolete_runtime_routes[:5]})")
    gate("G-REQ-WP-RESPONSIBILITY-BOUNDARY", not wordpress_responsibility_boundary, f"WPコンテンツ運用と通常／security保守の混在を拒否 (違反={wordpress_responsibility_boundary[:5]})")
    gate("G-REQ-NOTIFICATION-PURPOSE-BOUNDARY", not notification_purpose_boundary, f"承認通知・運用通知・媒体投稿・開発PR通知のtransport再利用を拒否 (違反={notification_purpose_boundary[:5]})")
    gate("G-REQ-MEDIA-ROUTE-SEMANTICS", not media_route_semantics, f"媒体BRの許可／禁止／保留routeとMR connection/actionsを意味照合 (違反={media_route_semantics[:5]})")
    gate("G-REQ-CONNECTOR-PRIORITY-SEMANTICS", not connector_priority_semantics, f"BR／FR／ADR／L4／L5のconnector優先順を一意に要求 (違反={connector_priority_semantics})")
    gate("G-REQ-L2-REVALIDATION-SEMANTICS", not l2_revalidation_semantics, f"旧L2 prototypeの通知class・decision・trace・write・profile scopeを再検証 (違反={l2_revalidation_semantics[:5]})")
    gate("G-REQ-VPS-CREDENTIAL-BOUNDARY", not vps_credential_boundary, f"VPS credentialのat-rest保護・runtime注入・scope分離を一意に要求 (違反={vps_credential_boundary})")
    gate("G-REQ-MEDIA-ADMISSION", not media_requirement_admission, f"全MRのcapability status・execution mode・principal・effect・policy・検証降下を要求 (違反={media_requirement_admission[:5]})")
    gate("G-REQ-LEGACY-MEDIA-INVENTORY", not legacy_media_inventory, f"旧MR全件を安全側deferred inventoryへ収載し旧経路の黙示採用を拒否 (違反={legacy_media_inventory})")
    gate("G-REQ-TRACE-SEMANTIC-RESPONSIBILITY", not trace_semantic_responsibility, f"BR／REQの責務・状態・証跡が下位FRのbehavior／ACへ実際に降下したか検査 (違反={trace_semantic_responsibility})")
    gate("G-REQ-DESCENT-ADMISSION", not requirement_descent_admission, f"要求定義だけのFR／SRをFN／CMP／ACへ降下又は再開条件付きdeferredへ閉じる (違反={requirement_descent_admission[:5]})")
    gate("G-REQ-VPS-UI-DESCENT", not vps_ui_requirement_descent, f"VPS UI主入口の状態・証跡・KPI閲覧要求と旧API-only契約を意味照合 (違反={vps_ui_requirement_descent})")
    gate("G-REQ-HUMAN-JUDGEMENT-DESCENT", not human_judgement_descent, f"上位BRのPO判断をFR／SR／AC／evidenceまで追跡し機械処理・agent審査による代替を拒否 (違反={human_judgement_descent})")
    gate("G-REQ-NFR-AUTHORITY", not nfr_requirement_authority, f"全NFRをstable REQ／BR根拠又は再開条件付きdeferredへ束縛 (違反={nfr_requirement_authority[:5]})")
    gate("G-REQ-STRATEGY-TEST-AUTHORITY", not strategy_test_authority, f"confirmed ACが参照するstrategy STCをPO receipt付き正本又は明示deferredへ束縛 (違反={strategy_test_authority})")
    gate("G-REQ-PROVIDER-DEPENDENCY", not provider_dependency_semantics, f"provider-neutral要求と旧Claude／Codex／consumer Web UI必須経路を意味照合 (違反={provider_dependency_semantics})")
    gate("G-REQ-LEGACY-CONSUMER-ISOLATION", not legacy_requirement_consumers, f"旧REQ／requirements viewを上位・設計・検証の規範入力から隔離 (違反={legacy_requirement_consumers})")
    gate("G-REQ-DESIGN-NOT-STARTED", not design_not_started, f"要求freeze前のL2〜L6を再検証資料に限定し設計・実装入力化を拒否 (違反={design_not_started[:5]})")
    gate("G-REQ-SCOPE-ASSIGNMENT", not scope_assignment, f"旧864 IDをlegacy限定とし新refinementへ初期／後続／deferred scopeを一意に割当 (違反={scope_assignment})")
    gate("G-REQ-DECISION-PACKETS", not decision_packets, f"PO確認packetが全refinement subjectを順序付きexactly onceで覆い一括承認を禁止 (違反={decision_packets})")
    gate("G-REQ-CANDIDATE-BINDINGS", not candidate_requirement_bindings, f"候補PRCを実在refinement meaning ownerへexactlyに束縛 (違反={candidate_requirement_bindings})")
    gate("G-REQ-L0-CLAUSE-DISPOSITION", not l0_clause_dispositions, f"旧L0の価値／手段をclause単位で維持・置換・deferredへ明示移送 (違反={l0_clause_dispositions})")
    gate("G-REQ-CRITICAL-RESPONSIBILITY-DISPOSITION", not critical_responsibility_dispositions, f"旧通知・承認・自動運用・UI責務をVPS UI／inbox／activationへ明示移送 (違反={critical_responsibility_dispositions})")
    gate("G-REQ-SEMANTIC-DESCENT-POLICY", not semantic_descent_policy, f"BRからTCまで12意味軸を直接宣言又はdigest束縛継承し設計降下を要求freezeまで拒否 (違反={semantic_descent_policy})")
    gate("G-REQ-LEGACY-NFR-DISPOSITION", not legacy_nfr_dispositions, f"旧NFR-1〜11をstable業務根拠付き再降下・置換又は再開条件付きdeferredへ分類 (違反={legacy_nfr_dispositions})")
    gate("G-REQ-ORPHAN-REQUIREMENT-DISPOSITION", not orphan_requirement_groups, f"stable root又はFN/CMP/AC降下を欠く旧FR 11件・SR 19件を再降下・置換・deferredへ全件分類 (違反={orphan_requirement_groups})")
    gate("G-REQ-LEGACY-REQ-DISPOSITION", not legacy_req_dispositions, f"旧REQ 55件をMD/JSON二重意味から分離しID別に再降下・置換・deferredへ全件分類 (違反={legacy_req_dispositions})")
    gate("G-REQ-LEGACY-BR-DISPOSITION", not legacy_br_dispositions, f"旧BR 41件の事業価値を保持し旧runtime/provider/approval/notification手段をID別に再降下・置換 (違反={legacy_br_dispositions})")
    gate("G-REQ-LEGACY-MEDIA-BR-DISPOSITION", not legacy_media_br_dispositions, f"旧媒体BR 70件を媒体別capability候補へ全件分類し媒体名だけの実行許可を拒否 (違反={legacy_media_br_dispositions})")
    gate("G-REQ-LEGACY-FR-DISPOSITION", not legacy_fr_dispositions, f"旧FR 43件を現要求へID別に再降下・置換・延期し旧runtime／provider／approval経路を拒否 (違反={legacy_fr_dispositions})")
    gate("G-REQ-LEGACY-DERIVED-CONTRACTS", not legacy_derived_contracts, f"旧FN 61／AC 252／TC 258を親要求の再降下までlegacy・未設計・非受入証拠へ固定 (違反={legacy_derived_contracts})")
    gate("G-REQ-AUTHORITY-REVISION-CANDIDATE", not authority_revision_candidate, f"新revision単一JSON正本を推奨案として保持しPO未決のまま旧ID書換え・cutover・設計開始を拒否 (違反={authority_revision_candidate})")
    gate("G-REQ-OBJECTIVE-COMPLETION-AUDIT", not objective_completion_audit, f"意味棚卸し・旧参照隔離・VPS UI/inbox・設計未着手・新正本freezeを目的別証拠で判定し未完の過大主張を拒否 (違反={objective_completion_audit})")
    gate("G-REQ-REFINEMENT", not refinement, f"refinement意味閉包・digest・受入・PO束縛を検査 (違反={refinement[:5]})")
    gate("G-REQ-REFINEMENT-COVERAGE", not refinement_coverage, f"全discovery候補を個別refinementへ対応 (違反={refinement_coverage[:5]})")
    gate("G-REQ-OPEN-REFINEMENTS", not open_refinements, f"全refinementのpending解消・PO receipt・frozenを要求 (違反={open_refinements[:5]})")
    gate("G-REQ-APPROVAL-ADMISSION", not admission, f"意味閉包前の承認要求を拒否 (違反={admission})")
    gate("G-REQ-AUTHORITY-CUTOVER", not cutover, f"frozen要求だけを実装入力へ切替 (違反={cutover})")


if __name__ == "__main__":
    run(CTX)
