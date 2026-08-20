"""HELIX 要件確定エンジンの Python-native admission core。

既存契約 JSON を source authority として読み、互換一覧との意味差分、trace の
双方向性、未終端の承認要求を fail-close にする。生成 IR は正本ではなく、同じ
入力から再計算できる projection である。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
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
    git,
    load,
    schema_check,
)


def _completed_media_independent_go(head: str, expected_digests: dict[str, str]) -> bool:
    """同一SHAに対する別runの完了済みGitHub check-runを外部検証する。"""
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    current_run = os.environ.get("GITHUB_RUN_ID")
    if repository != "RetryYN/HELIX-MARKETING-HARNESS" or not token or not current_run:
        return False
    headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}","X-GitHub-Api-Version":"2022-11-28"}
    def github_json(path: str) -> dict[str, Any] | None:
        request = urllib.request.Request(f"https://api.github.com/repos/{repository}/{path}",headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=10) as response:  # noqa: S310 -- fixed GitHub HTTPS endpoint
                value=json.loads(response.read())
                return value if isinstance(value,dict) else None
        except (OSError,urllib.error.URLError,json.JSONDecodeError):
            return None
    payload=github_json(f"commits/{head}/check-runs")
    if payload is None:
        return False
    for check in payload.get("check_runs", []) if isinstance(payload,dict) else []:
        details = str(check.get("details_url", ""))
        match=re.fullmatch(r"https://github\.com/RetryYN/HELIX-MARKETING-HARNESS/actions/runs/([0-9]+)(?:/job/[0-9]+)?",details)
        run_id=match.group(1) if match else None
        run=github_json(f"actions/runs/{run_id}") if run_id else None
        workflow=github_json(f"actions/workflows/{run.get('workflow_id')}") if isinstance(run,dict) and run.get("workflow_id") else None
        summary = check.get("output", {}).get("summary")
        try:
            attestation = json.loads(summary) if isinstance(summary,str) else None
        except json.JSONDecodeError:
            attestation = None
        if (
            check.get("name") == "media-requirements-independent-go"
            and check.get("status") == "completed"
            and check.get("conclusion") == "success"
            and check.get("head_sha") == head
            and check.get("app", {}).get("slug") == "github-actions"
            and run_id != current_run
            and isinstance(run,dict) and run.get("head_sha")==head
            and run.get("status")=="completed" and run.get("conclusion")=="success"
            and run.get("repository",{}).get("full_name")==repository
            and run.get("head_branch")=="main"
            and run.get("path")==".github/workflows/requirements.yml"
            and run.get("event")=="workflow_dispatch"
            and isinstance(workflow,dict) and workflow.get("path")==".github/workflows/requirements.yml"
            and attestation == {"verdict":"Go","reviewed_artifact_digests":expected_digests,"reviewer_principal":"github-actions"}
        ):
            return True
    return False

ENGINE_DIR = Path(__file__).resolve().parents[2] / "docs/00-authority/development"
AUTHORITY_POLICY = ENGINE_DIR / "requirement-engine-authority.json"
IR_SCHEMA = ENGINE_DIR / "requirement-ir.schema.json"
REFINEMENT_SCHEMA = ENGINE_DIR / "requirement-refinement.schema.json"
REFINEMENTS = ENGINE_DIR / "requirement-refinements.json"
CANDIDATE_IR_DIR = ENGINE_DIR / "requirements-ir"
CANDIDATE_IR_MANIFEST = CANDIDATE_IR_DIR / "manifest.json"
CANDIDATE_IR_SCHEMA = ENGINE_DIR / "candidate-requirement-ir-v2.schema.json"
COMPATIBILITY_VIEW = (
    Path(__file__).resolve().parents[2] / "docs/L3-system-requirements/canonical/functional/requirements.json"
)
REQ_COMPATIBILITY_VIEW = (
    Path(__file__).resolve().parents[2] / "docs/L1-business-requirements/canonical/requirement-list_v0.1.md"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_VIEW = REPO_ROOT / "docs/00-authority/views/requirement-candidates_v0.1.md"
CANDIDATE_BASELINE = (
    REPO_ROOT / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md"
)
LEGACY_STRATEGY_AC = REPO_ROOT / "docs/L3-system-requirements/canonical/strategy/ac-sr.json"
LEGACY_L0_CHARTER = REPO_ROOT / "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md"

HISTORICAL_VIEW_BANNERS = {
    "docs/L1-business-requirements/canonical/br-backbone_v0.1.md": [
        "旧baselineの承認履歴",
        "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/br-media_v0.1.md": [
        "旧baselineの承認履歴",
        "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/loop-task-workflow_v0.1.md": [
        "旧baselineの承認履歴",
        "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L1-business-requirements/canonical/requirement-list_v0.1.md": [
        "旧baselineの承認履歴view",
        "現行要求の正本・設計・実装入力ではない",
        "requirements_baseline_status=revising",
        "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md": [
        "旧baselineの履歴view",
        "現行要件の正本・設計・実装入力ではない",
        "requirements_baseline_status=revising",
        "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/s0-contract_v0.1.md": [
        "旧baselineのS0契約",
        "現行要求の設計・実装入力ではない",
        "requirements_baseline_status=revising",
        "implementation_authorized=false",
    ],
    "docs/L3-system-requirements/canonical/functional/function-list_v0.1.md": [
        "旧baselineの機能台帳",
        "現行要求の設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L3-system-requirements/canonical/functional/media-requirements_v0.1.md": [
        "旧baselineの媒体要件",
        "現行要求の正本・設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L3-system-requirements/verification/verification-design_v0.1.md": [
        "旧baselineの検証設計",
        "現行要求の設計・実装入力ではない",
        "applicability_status=revalidation_required",
        "implementation_input=false",
    ],
    "docs/L0-charter/canonical/marketing-harness-charter_v0.4.md": [
        "旧baselineの承認履歴",
        "設計・実装入力ではない",
    ],
    "docs/L4-basic-design/canonical/basic-design_v0.1.md": [
        "旧baselineの設計履歴",
        "現要求に対するL4は未設計",
    ],
    "docs/L4-basic-design/canonical/tech-stack_v0.1.md": [
        "旧baselineの設計履歴",
        "現在の技術選定・実装入力ではない",
    ],
    "docs/L4-basic-design/canonical/approval/approval-design_v0.1.md": [
        "旧Discord初期経路",
        "現要求の承認設計ではない",
    ],
    "docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md": [
        "旧baselineのL4設計",
        "現要求に対するL4は未設計",
        "implementation_input=false",
    ],
    "docs/L5-detailed-design/canonical/detailed-design_v0.1.md": [
        "旧baselineのL5設計",
        "現要求に対するL5は未設計",
        "implementation_input=false",
    ],
    "docs/L6-feature-design/S0/approval.md": [
        "旧baselineのL6設計",
        "VPS Web UI＋UI内inbox承認経路は未設計",
        "implementation_input=false",
    ],
}

OBSOLETE_RUNTIME_ROUTE_MARKERS = {
    "docs/L3-system-requirements/canonical/schemas/s0/ddl.sql": ["CHECK (channel = 'discord')"],
    "docs/L3-system-requirements/canonical/s0-contract_v0.1.md": ["CHECK (channel = 'discord')"],
    "docs/L3-system-requirements/canonical/functional/fr-contracts.json": [
        '"service": "discord_app"',
        '"operation": "approval_request"',
        # FR-46 is a JSON document whose legacy tuple is embedded in prose
        # (single-quoted values), not a current JSON object field.  Keep this
        # precise tuple in the quarantine snapshot so the old ApprovalTransport
        # route cannot disappear merely because the marker format differs.
        "service='discord_app'・operation='approval_request'",
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
        "FR-16",
        "FR-41",
        "FR-42",
        "FR-43",
        "FR-44",
        "FR-45",
        "FR-46",
        "FR-47",
        "FR-52",
        "FR-53",
        "FR-71",
        "FR-74",
        "FR-75",
        "FR-76",
        "FR-77",
    }
    brm = [item for path in sorted(BR_MEDIA_DIR.glob("*.json")) for item in _items(load(path))]
    mr = [item for path in sorted(MR_DIR.glob("*.json")) for item in _items(load(path))]
    sources = (
        ("BR", ctx.brc),
        ("BRM", brm),
        ("REQ", ctx.req),
        ("FR", ctx.frc),
        ("SR", ctx.src),
        ("NFR", ctx.nfc),
        ("MR", mr),
        ("FN", ctx.fn),
        ("AC", ctx.acc),
        ("TC", ctx.tcc),
    )
    required_dimensions = [
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
            subjects.update(
                {
                    "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                    "AUTOMATED-PUBLISHING-ADMISSION",
                    "CONTENT-QUALITY-GATE-LEARNING",
                }
            )
        if stable_id == "BR-H3":
            subjects.update({"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"})
        if stable_id == "FR-46":
            subjects.update(
                {
                    "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                    "VPS-UI-AUTHENTICATION-SESSION",
                    "AUTOMATED-PUBLISHING-ADMISSION",
                    "CONTENT-QUALITY-GATE-LEARNING",
                }
            )
        if stable_id == "FR-75":
            subjects.update(
                {
                    "BUSINESS-PROFILE-AUTHORIZATION",
                    "AUTOMATED-PUBLISHING-ADMISSION",
                    "PRODUCT-STATE-AUTHORITY",
                }
            )
        if stable_id in {"MR-DC-1", "MR-DC-2", "MR-DC-3"}:
            subjects.add("DISCORD-COMMUNITY-MARKETING-ROUTE")
        if stable_id == "FR-77":
            subjects.update(
                {
                    "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                    "VPS-UI-AUTHENTICATION-SESSION",
                    "PRODUCT-STATE-AUTHORITY",
                }
            )
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
            items.append(
                {
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
                }
            )
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
        "BR": "requirements",
        "BRM": "requirements",
        "REQ": "requirements",
        "FR": "requirements",
        "SR": "requirements",
        "NFR": "requirements",
        "MR": "requirements",
        "FN": "requirements",
        "CMP": "system_contracts",
        "DU": "system_contracts",
        "IU": "system_contracts",
        "AC": "acceptance_cases",
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
            records.append(
                {
                    "stable_id": item["refinement_id"],
                    "kind": "RRF",
                    "partition": "refinement_contracts",
                    "source_authority": "canonical_refinement_registry",
                    "applicability": "proposal_only",
                    "semantic_digest": _digest(semantic),
                    "semantic": semantic,
                }
            )
    records.sort(key=lambda row: (row["kind"], row["stable_id"]))
    partition_names = [
        "requirements",
        "system_contracts",
        "acceptance_cases",
        "system_tests",
        "refinement_contracts",
    ]
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


def candidate_ir_v2_faults() -> list[str]:
    """HELIX-HARNESS v2 envelope/shards の候補 projection を検証する。

    外部テンプレートの canonical/frozen envelope を現在の未批准要求へ
    そのまま適用すると、承認・凍結を捏造する。そこで field/partition は
    upstream 形式へ合わせる一方、authority/status は local candidate の
    閉集合にし、registry からの再生成結果と実ファイルを exact 比較する。
    """
    faults: list[str] = []
    try:
        from scripts.render_requirement_ir_v2_candidate import PARTITIONS, build_candidate_ir

        built = build_candidate_ir()
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as exc:
        return [f"HELIX-HARNESS v2 candidate projection を生成できない: {exc}"]

    if not CANDIDATE_IR_SCHEMA.is_file():
        faults.append("HELIX-HARNESS v2 candidate schema がない")
    else:
        try:
            faults.extend(f"candidate manifest schema: {fault}" for fault in schema_check(
                load(CANDIDATE_IR_SCHEMA), built["manifest"]
            ))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            faults.append(f"candidate manifest schema を読めない: {exc}")

    manifest = built["manifest"]
    if manifest.get("schema_version") != "helix-requirement-ir.v2":
        faults.append("candidate IR schema_version が upstream v2 でない")
    if manifest.get("authority") != "candidate_non_authoritative":
        faults.append("candidate IR が canonical authority を名乗る又は型が不正")
    if manifest.get("source_authority") != "requirement_refinement_registry_projection":
        faults.append("candidate IR source authority が refinement registry projection でない")
    if manifest.get("partition") != "stable_id_keyed_shards":
        faults.append("candidate IR partition が stable_id_keyed_shards でない")

    paths = [CANDIDATE_IR_MANIFEST, *(CANDIDATE_IR_DIR / f"{kind}.json" for kind in PARTITIONS)]
    if any(not path.is_file() for path in paths):
        faults.extend(f"candidate IR generated file がない: {path.relative_to(REPO_ROOT)}" for path in paths if not path.is_file())
        return faults

    try:
        actual_manifest = load(CANDIDATE_IR_MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        return faults + [f"candidate IR manifest を読めない: {exc}"]
    if actual_manifest != manifest:
        faults.append("candidate IR manifest が refinement registry からの決定的生成結果と不一致")

    required_fields = {
        "requirements": {"schema_version", "requirement_id", "revision", "kind", "status", "definition_status", "evidence_origin", "statement", "source", "assertion_id", "primary_system_contract_id", "acceptance_ids", "system_test_id", "downstream_obligation", "actor_ids", "task_ids", "surface_ids", "design_template_ids", "design_obligation_ids", "required_design_artifact_kinds", "pending_resolution", "semantic_digest"},
        "system_contracts": {"schema_version", "system_contract_id", "revision", "status", "requirement_ids", "behavior", "transition_contract", "failure_and_evidence", "acceptance_ids", "system_test_id", "semantic_digest"},
        "acceptance_cases": {"schema_version", "acceptance_id", "revision", "status", "system_contract_id", "polarity", "statement", "system_test_id", "semantic_digest"},
        "system_tests": {"schema_version", "system_test_id", "revision", "status", "system_contract_id", "acceptance_ids", "supporting_test_ids", "scenario", "required_evidence", "negative_boundary", "semantic_digest"},
        "refinement_contracts": {"schema_version", "refinement_contract_id", "revision", "lifecycle_status", "primary_system_contract_id", "related_system_contract_ids", "source", "plan_id", "responsibility_owner", "contract_requirement", "supporting_requirements", "acceptance_cases", "downstream_issue_ids", "acceptance_owners", "approval", "semantic_digest"},
    }
    exact_fields = {kind: fields for kind, fields in required_fields.items()}
    id_patterns = {
        "requirements": re.compile(r"^MHH-REQ-[A-Z0-9-]+$"),
        "system_contracts": re.compile(r"^MHH-SC-[A-Z0-9-]+$"),
        "acceptance_cases": re.compile(r"^MHH-AC-[A-Z0-9-]+-[PNB]$"),
        "system_tests": re.compile(r"^MHH-ST-[A-Z0-9-]+$"),
        "refinement_contracts": re.compile(r"^RRF-[A-Z0-9-]+$"),
    }
    id_fields = {
        "requirements": "requirement_id",
        "system_contracts": "system_contract_id",
        "acceptance_cases": "acceptance_id",
        "system_tests": "system_test_id",
        "refinement_contracts": "refinement_contract_id",
    }
    expected_schema_versions = {
        "requirements": "helix-requirement.v1",
        "system_contracts": "helix-system-contract.v1",
        "acceptance_cases": "helix-acceptance-case.v1",
        "system_tests": "helix-system-test.v1",
        "refinement_contracts": "helix-requirement-refinement.v1",
    }
    for kind in PARTITIONS:
        try:
            actual = load(CANDIDATE_IR_DIR / f"{kind}.json")
        except (OSError, json.JSONDecodeError) as exc:
            faults.append(f"candidate IR shard {kind} を読めない: {exc}")
            continue
        expected = built["shards"][kind]
        if actual != expected:
            faults.append(f"candidate IR shard {kind} が決定的生成結果と不一致")
        if not isinstance(actual, dict) or list(actual) != sorted(actual):
            faults.append(f"candidate IR shard {kind} が stable ID keyed・決定順でない")
            continue
        for stable_id, record in actual.items():
            if not isinstance(record, dict):
                faults.append(f"candidate IR {kind}/{stable_id} が object でない")
                continue
            fields = set(record)
            missing = required_fields[kind] - fields
            if missing:
                faults.append(f"candidate IR {kind}/{stable_id} required field 欠落={sorted(missing)}")
            extra = fields - exact_fields[kind]
            if extra:
                faults.append(f"candidate IR {kind}/{stable_id} が upstream shard field 外を持つ={sorted(extra)}")
            if not id_patterns[kind].fullmatch(stable_id):
                faults.append(f"candidate IR {kind}/{stable_id} stable ID が候補ID語彙でない")
            if record.get(id_fields[kind]) != stable_id:
                faults.append(f"candidate IR {kind}/{stable_id} の内部IDがkeyと不一致")
            if record.get("schema_version") != expected_schema_versions[kind]:
                faults.append(f"candidate IR {kind}/{stable_id} schema_version が不正")
            revision = record.get("revision")
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                faults.append(f"candidate IR {kind}/{stable_id} revision が正の整数でない")
            semantic = {key: value for key, value in record.items() if key != "semantic_digest"}
            if record.get("semantic_digest") != _digest(semantic):
                faults.append(f"candidate IR {kind}/{stable_id} semantic digest 不一致")
            if kind == "requirements":
                if record.get("status") not in {"candidate_unratified", "historical_superseded"}:
                    faults.append(f"candidate IR {stable_id} status が候補閉包外")
                if record.get("definition_status") not in {"unfrozen", "superseded_history"}:
                    faults.append(f"candidate IR {stable_id} が要求freezeを過大主張")
                statement = record.get("statement")
                if not isinstance(statement, dict) or set(statement) != {"text", "semantic_digest"}:
                    faults.append(f"candidate IR {stable_id} statement がupstream shapeでない")
                source = record.get("source")
                if not isinstance(source, dict) or set(source) != {"canonical_pointer", "migration_source_pointer", "authority_id"}:
                    faults.append(f"candidate IR {stable_id} source がupstream shapeでない")
            elif kind in {"system_contracts", "acceptance_cases"}:
                if record.get("status") not in {"candidate_unratified", "historical_superseded"}:
                    faults.append(f"candidate IR {kind}/{stable_id} status が候補閉包外")
            elif kind == "system_tests":
                if record.get("status") not in {"designed_not_implemented", "historical_superseded"}:
                    faults.append(f"candidate IR {stable_id} が未着手テスト境界を外れる")
            else:
                if record.get("lifecycle_status") not in {"draft", "specified", "superseded", "rejected"}:
                    faults.append(f"candidate IR {stable_id} lifecycle が候補閉包外")
                source = record.get("source")
                if not isinstance(source, dict) or set(source) != {"requirement_path", "requirement_digest", "acceptance_path", "acceptance_digest"}:
                    faults.append(f"candidate IR {stable_id} refinement source がupstream shapeでない")
                if record.get("approval") is not None:
                    faults.append(f"candidate IR {stable_id} が未承認なのに approval を持つ")
    return faults


def projection_faults(projection: dict[str, Any]) -> list[str]:
    faults: list[str] = [f"IR schema: {fault}" for fault in schema_check(load(IR_SCHEMA), projection)]
    faults.extend(candidate_ir_v2_faults())
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
        if (
            not isinstance(stable_id, str)
            or not stable_id
            or kind
            not in {"BR", "BRM", "REQ", "FR", "SR", "NFR", "MR", "FN", "AC", "TC", "CMP", "DU", "IU", "RRF"}
        ):
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
    expected_names = [
        "requirements",
        "system_contracts",
        "acceptance_cases",
        "system_tests",
        "refinement_contracts",
    ]
    shards = projection.get("shards")
    if (
        not isinstance(shards, list)
        or [x.get("kind") for x in shards if isinstance(x, dict)] != expected_names
    ):
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
    }:
        faults.append("IR revalidation inventoryが要求系10台帳全864件を被覆しない")
    elif any(
        item.get("applicability") != "revalidation_required" or item.get("decision_status") != "unresolved"
        for item in inventory.get("items", [])
    ):
        faults.append("IR revalidation inventoryが未決旧契約をcurrent扱いする")
    else:
        refinement_subjects = {
            str(item.get("subject_id"))
            for item in json.loads(REFINEMENTS.read_text(encoding="utf-8")).get("records", [])
            if isinstance(item, dict)
        }
        required_dimensions = {
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
        critical_owner_sets = {
            "BR-H2": {
                "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                "AUTOMATED-PUBLISHING-ADMISSION",
                "CONTENT-QUALITY-GATE-LEARNING",
            },
            "BR-H3": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-16": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-43": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-46": {
                "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                "VPS-UI-AUTHENTICATION-SESSION",
                "AUTOMATED-PUBLISHING-ADMISSION",
                "CONTENT-QUALITY-GATE-LEARNING",
            },
            "FR-75": {
                "BUSINESS-PROFILE-AUTHORIZATION",
                "AUTOMATED-PUBLISHING-ADMISSION",
                "PRODUCT-STATE-AUTHORITY",
            },
            "FR-76": {"FR-16-NOTIFICATION-BOUNDARY", "VPS-UI-INBOX-LIFECYCLE"},
            "FR-77": {
                "VPS-UI-PRIMARY-HUMAN-INTERFACE",
                "VPS-UI-AUTHENTICATION-SESSION",
                "PRODUCT-STATE-AUTHORITY",
            },
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
    if projection.get("root_digest") != _digest(
        {"shards": shards, "records": records, "revalidation_inventory": inventory}
    ):
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
        "requirements_governance",
        "initial_candidate",
        "follow_on_candidate",
        "deferred_candidate",
        "historical_superseded",
    }
    if any(value not in allowed for value in assignments.values()):
        faults.append("scope assignmentに未知区分がある")
    required_initial = {
        "VPS-UI-PRIMARY-HUMAN-INTERFACE",
        "FR-16-NOTIFICATION-BOUNDARY",
        "DISCORD-NOTIFICATION-REJECTION-BOUNDARY",
        "VPS-UI-INBOX-LIFECYCLE",
        "VPS-UI-QUALITY-ATTRIBUTES",
        "VPS-CREDENTIAL-SECURITY-BOUNDARY",
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
        "PRODUCT-STATE-AUTHORITY",
        "BUSINESS-PROFILE-AUTHORIZATION",
        "VPS-UI-AUTHENTICATION-SESSION",
        "AUTOMATED-PUBLISHING-ADMISSION",
        "CONTENT-QUALITY-GATE-LEARNING",
        "CONTENT-RISK-CLASSIFICATION",
        "RESEARCH-LED-CONTENT-GROWTH",
        "STRATEGY-REQUIREMENT-ADMISSION",
    }
    if any(assignments.get(subject) != "initial_candidate" for subject in required_initial):
        faults.append("VPS UI/inbox/security/人間判断/WP content/strategy core初期候補のscopeが不正")
    required_deferred = {"GENAI-EXECUTION-ROUTE", "LEGACY-MEDIA-ADMISSION-INVENTORY"}
    if any(assignments.get(subject) != "deferred_candidate" for subject in required_deferred):
        faults.append("生成AI/旧媒体の安全側deferred scopeが不正")
    historical = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and record.get("lifecycle_status") == "superseded"
    }
    if historical != {
        "AUTO-MODE-DECISION-AUTHORITY",
        "DISCORD-MULTI-PURPOSE-BOUNDARIES",
        "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE",
    } or any(assignments.get(subject) != "historical_superseded" for subject in historical):
        faults.append("superseded履歴subjectがhistorical-only scopeでない")
    expected_replacements = {
        "AUTO-MODE-DECISION-AUTHORITY": ["AUTOMATED-PUBLISHING-ADMISSION"],
        "DISCORD-MULTI-PURPOSE-BOUNDARIES": [
            "DISCORD-NOTIFICATION-REJECTION-BOUNDARY",
            "DISCORD-COMMUNITY-MARKETING-ROUTE",
        ],
        "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE": [
            "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2"
        ],
    }
    for record in records:
        if not isinstance(record, dict) or record.get("lifecycle_status") != "superseded":
            continue
        replacements = record.get("superseded_by_subject_ids")
        if (
            not isinstance(replacements, list)
            or replacements != expected_replacements.get(str(record.get("subject_id")))
            or any(replacement not in subjects for replacement in replacements)
            or any(replacement in historical for replacement in replacements)
        ):
            faults.append(f"{record.get('subject_id')}: supersession先が正しい現役意味ownerへexactに閉じない")
    required_follow_on = {
        "EXTERNAL-BROWSER-AUTOMATION-ROUTE",
        "DISCORD-COMMUNITY-MARKETING-ROUTE",
    }
    if any(assignments.get(subject) != "follow_on_candidate" for subject in required_follow_on):
        faults.append("Playwright/Discord communityのfollow-on scopeが不正")
    return faults


def _expected_captured_po_decision_controls() -> dict[str, Any]:
    """対話で確定した要求意味をtoken検索ではなく型とdigestで固定する。"""
    return {
        "POD-20260815-001": {
            "decision_snapshot_digest": "sha256:a108c02eba247caec3c66fa58b183bcfeafbfead26e888ede4b2aa74ddbe80ea",
            "facts": {
                "route_priority": ["official_api", "official_mcp"],
                "browser_engine": "playwright",
                "browser_roles": ["capability_fallback", "read_confirmation"],
                "permission_scope": "account_operation_resource",
            },
            "subject_semantic_digests": {
                "EXTERNAL-BROWSER-AUTOMATION-ROUTE": "sha256:656e7c8cab8e861e8c0cc39f2633f2f59605471734441a9fb7f41a127d6fc5d8"
            },
        },
        "POD-20260815-002": {
            "decision_snapshot_digest": "sha256:29756112668435ad619ca819beb41e4fdfdbce8a9e3e85ada82cfdb495ccd624",
            "facts": {
                "product_notification_route": "vps_ui_inbox",
                "discord_role": "community_marketing_only",
                "discord_prohibited_purposes": [
                    "product_approval_notification",
                    "operational_notification",
                    "developer_pr_notification",
                ],
            },
            "subject_semantic_digests": {
                "DISCORD-COMMUNITY-MARKETING-ROUTE": "sha256:70c0b5ab8cf5b8a163454726f2b18a0e4d4db23eeff4974409ae260358d81134"
            },
        },
        "POD-20260815-003": {
            "decision_snapshot_digest": "sha256:4e8b18532809d7b32965594d025e167ae4caa75b80d00696879accf7ebe1ae00",
            "facts": {
                "activation_authority": "authenticated_ui_explicit_user_decision",
                "activation_notice": "vps_ui_inbox",
                "per_post_approval_required": False,
                "per_artifact_admission": ["purpose_gate", "risk_gate", "quality_gate"],
                "failure_action": "deny_external_write",
            },
            "subject_semantic_digests": {
                "AUTOMATED-PUBLISHING-ADMISSION": "sha256:4e3df9a130b8c7b919b6eb5dafe68112d84bfc3210cc1538c991c1db24c74313"
            },
        },
        "POD-20260815-004": {
            "decision_snapshot_digest": "sha256:f86634ab8eb788d10d9358cb9b46867af6ac03429c1c864afc8f0dc4057b3095",
            "facts": {
                "admission_order": [
                    "generate",
                    "machine_gate",
                    "regenerate_or_fix",
                    "machine_regate",
                    "human_review_or_next_stage",
                ],
                "failed_artifact_human_review": "prohibited",
                "pass_required_before_progress": True,
            },
            "subject_semantic_digests": {
                "CONTENT-QUALITY-GATE-LEARNING": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721"
            },
        },
        "POD-20260815-005": {
            "decision_snapshot_digest": "sha256:a4fd5638143c7f4e39c087661f5ad8eefc3157c4cf632560485453426c310a8f",
            "facts": {
                "feedback_storage": "externalized_structured_versioned_rule",
                "explicit_scope_actor": "user",
                "missing_scope_default": "source_feedback.media_account_id",
                "implicit_scope_expansion": "prohibited",
                "derived_scope_evidence": ["source_feedback_id", "media_account_id"],
            },
            "subject_semantic_digests": {
                "CONTENT-QUALITY-GATE-LEARNING": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721"
            },
        },
        "POD-20260815-006": {
            "decision_snapshot_digest": "sha256:b671f888a338c953ba1aecd9da4b62d7abfde6b0dc91f677cfd061628885ad84",
            "facts": {
                "rule_update_actor": "ai_within_mandatory_risk_boundary",
                "risk_unknown_default": "highest_applicable_strictness",
                "user_preference_can_weaken_mandatory_risk": False,
                "published_update_condition": "explicit_update_in_place_capability_and_gate_pass",
                "unsupported_update_action": "no_action_including_notification",
            },
            "subject_semantic_digests": {
                "CONTENT-QUALITY-GATE-LEARNING": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721",
                "CONTENT-RISK-CLASSIFICATION": "sha256:4ba4a208fcc0dcdcd551be40c81eadc31b75f311fa8274f8d8dfe66b20b88c49",
            },
        },
        "POD-20260815-007": {
            "decision_snapshot_digest": "sha256:e3c945cb184f6c12c252626660f8a9e73d43ec7b327c92e7cb456f31fc8f790c",
            "facts": {
                "research_timing": "before_content_creation",
                "media_role_authority": "offer_funnel_stage",
                "growth_feedback": ["research", "plan", "funnel", "rule", "hypothesis"],
                "offer_mutation": "capability_and_authority_dependent",
                "paid_acquisition_phase": "ultra_late_deferred",
            },
            "subject_semantic_digests": {
                "CONTENT-QUALITY-GATE-LEARNING": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721",
                "CONTENT-RISK-CLASSIFICATION": "sha256:4ba4a208fcc0dcdcd551be40c81eadc31b75f311fa8274f8d8dfe66b20b88c49",
                "RESEARCH-LED-CONTENT-GROWTH": "sha256:ea8db288dc6dd44db103766832cb6d8f73862e5de15c21c18fa0b43087e50b9e",
            },
        },
        "POD-20260815-008": {
            "decision_snapshot_digest": "sha256:b10ecdf8d2306587f098488f91a00d79a2849399bf9235f4e514f239b28dd142",
            "facts": {
                "current_runtime_lifecycle": "agent_processes_stop_on_vps_reboot",
                "post_reboot_external_effects": "stopped",
                "credential_unlock": "human_reauthorization_with_runtime_reinitialization",
                "credential_only_auto_unlock": "prohibited",
                "future_persistent_service": "separate_po_requirement",
            },
            "subject_semantic_digests": {
                "VPS-CREDENTIAL-SECURITY-BOUNDARY": "sha256:16f222c23f0071263f5b28fc09a62e23c50719dbff0f9c4747d8de00bcb014df"
            },
        },
        "POD-20260815-009": {
            "decision_snapshot_digest": "sha256:2e85fb60a138d12aaeafb9f0152bef194905bf48c1659eb01acaa30a776572af",
            "facts": {
                "ordinary_failed_retry_notification": "none",
                "retry_exhaustion_state": "blocked",
                "retry_exhaustion_notification": "vps_ui_inbox",
                "notification_failure_state_effect": "no_rollback",
                "unsupported_published_update_action": "no_action_including_notification",
            },
            "subject_semantic_digests": {
                "CONTENT-QUALITY-GATE-LEARNING": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721",
            },
            "subject_projection_digests": {
                "VPS-UI-INBOX-LIFECYCLE": "sha256:4678a271d86681984c435133810d7ddc4de6303df1a02ce3c2673caab4b4aeab",
            },
        },
    }


def _captured_po_subject_projection(
    decision_id: str, subject: str, record: dict[str, Any]
) -> dict[str, str] | None:
    """PO回答から直接降下した句だけをresolver候補から分離して束縛する。"""
    if decision_id != "POD-20260815-009" or subject != "VPS-UI-INBOX-LIFECYCLE":
        return None
    dimensions = record.get("semantic_dimensions")
    if not isinstance(dimensions, dict):
        return None
    tasks = dimensions.get("tasks", [])
    scope_in = dimensions.get("scope_in", [])
    prohibitions = dimensions.get("prohibitions", [])
    evidence = dimensions.get("evidence", [])
    expected: dict[str, Any] = {
        "task": "content quality retry exhaustionを一意なoperational alertとして記録する",
        "purpose": "purpose=action_required又はoperational_alert",
        "source": "source=content_quality_retry_exhausted（通常retryを除外）",
        "dedupe": "artifact/rule revision/retry exhaustion source identityによる一件dedupe",
        "ordinary_retry_prohibited": "通常のcontent quality retryをinbox itemにする",
        "no_rollback": "通知記録失敗又はretry_exhaustedで先行する安全停止・失敗・承認待ち状態をrollbackしない",
        "evidence": "content quality blocked source identity、artifact、rule revision及びretry exhaustion receipt",
    }
    memberships = {
        "task": tasks,
        "purpose": scope_in,
        "source": scope_in,
        "dedupe": scope_in,
        "ordinary_retry_prohibited": prohibitions,
        "no_rollback": prohibitions,
        "evidence": evidence,
    }
    if any(value not in memberships[key] for key, value in expected.items()):
        return None
    return expected


def _expected_resolver_candidate_controls() -> dict[str, Any]:
    """PO回答ではないresolver候補をprovenance付きで独立に固定する。"""
    return {
        "VPS-UI-INBOX-LIFECYCLE": {
            "source_event_ids": ["RDE-000167", "RDE-000168"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:8e7014577d4ad96f3ded703a42f97f618cf2b56f3c89866d948fa7b9d1ed1fad",
        },
        "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2": {
            "source_event_ids": ["RDE-000169"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:68ce8384a857fac070f2394e20e6188358cae6fae262ea6f2c18b5f03a9ed403",
        },
        "CONTRACT-SEMANTIC-DESCENT-V2": {
            "source_event_ids": ["RDE-000170"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:b1fe074d7bbcc73d48f1d2f7e0683e4ee5b3a19a8e67ea6fbf62f864cffdd2e3",
        },
        "RATE-QUOTA-COST-AUTHORITY": {
            "source_event_ids": ["RDE-000171"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:4d1941c135f4100df4286135bf534b7058473abaef0396495778df0fcccdcf41",
        },
        "PRODUCT-STATE-AUTHORITY": {
            "source_event_ids": ["RDE-000172", "RDE-000173", "RDE-000175"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:634bd6202e1a5d464d9696ce4f698cc5d5eb40907eea96e198cc5d885e2b9878",
        },
        "BUSINESS-PROFILE-AUTHORIZATION": {
            "source_event_ids": ["RDE-000174"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:ad26d3f40b9250e77f8e8be1aa3e387f294d170b05d3eef01b91e819c061b87a",
        },
        "VPS-UI-AUTHENTICATION-SESSION": {
            "source_event_ids": ["RDE-000176", "RDE-000177"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:59583ac23bfdef85aafee36c120abced6cf938c25b6c905bf7bf364890468d04",
        },
        "VPS-UI-QUALITY-ATTRIBUTES": {
            "source_event_ids": ["RDE-000178"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:a01e41d02b365a1eccb468d3bfbff53f3339b83904551addb102e0232ff63b28",
        },
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE": {
            "source_event_ids": ["RDE-000179"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:ec927831a0dcf8ccdb6df150815fbad24fa40f6623c8340e60671ecb8efc33ae",
        },
        "WORDPRESS-SECURITY-MAINTENANCE-RELEASE": {
            "source_event_ids": ["RDE-000180"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:7664222be30ace640e3a9780c6dc6da1c226dfdb46556f3eba36068537bf20a3",
        },
        "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE": {
            "source_event_ids": ["RDE-000181"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:32e41614f15f39347859b6c718d7321644bc5316a5a9daae719e3725adb346c3",
        },
        "REQ-AUTHORITY-NORMALIZATION": {
            "source_event_ids": ["RDE-000182"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:3b83b3e1af295d0e0152cce199a294f6591dccc61ac33067926b64aa3ea5ee80",
        },
        "NFR-BUSINESS-AUTHORITY": {
            "source_event_ids": ["RDE-000183"],
            "status": "candidate_unratified",
            "semantic_digest": "sha256:f70dd7d7fcbfc46be0c34ddc379e49703ea765b6cff0e8a8fd6c308db9b52834",
        },
    }


def _expected_semantic_coverage_policy() -> dict[str, Any]:
    """意味軸の欠落・曖昧N/A・stale継承を安全側候補として閉じる。"""
    return {
        "status": "candidate_unratified",
        "dimension_dispositions": ["direct", "digest_inherited", "not_applicable", "deferred"],
        "core_dimensions": [
            "actor",
            "beneficiary",
            "value",
            "task",
            "workflow",
            "scope",
            "prohibition",
            "human_judgement",
            "side_effect",
            "evidence",
            "phase",
        ],
        "quality_dimensions": [
            "security",
            "privacy",
            "accessibility",
            "performance",
            "availability",
            "recovery",
            "operation",
            "migration",
            "rollback",
        ],
        "digest_inheritance_contract": [
            "parent_subject_id",
            "parent_semantic_digest",
            "explicit_delta",
            "cycle_free",
        ],
        "not_applicable_contract": [
            "quality_dimension",
            "rationale",
            "applicability_evidence",
            "decision_owner_subject_id",
            "review_trigger",
            "resume_condition",
        ],
        "threshold_registration_contract": [
            "subject_id",
            "quality_dimension",
            "risk_class",
            "scope",
            "effective_revision",
            "value",
            "unit",
            "measurement_window",
            "source",
        ],
        "fail_close_conditions": [
            "unknown_dimension",
            "empty_dimension",
            "generic_not_applicable",
            "stale_parent_digest",
            "missing_required_threshold_registration",
            "expired_threshold_registration",
            "unmeasurable_threshold",
        ],
        "evidence_contract": [
            "per_dimension_disposition",
            "parent_and_delta_digest",
            "not_applicable_receipt",
            "threshold_registration_revision",
            "coverage_partition_digest",
            "mutation_results",
        ],
        "design_later": [
            "semantic coverage schema representation",
            "inheritance cycle detector implementation",
            "threshold registry storage and measurement adapter",
        ],
    }


def _expected_contract_semantic_descent_policy() -> dict[str, Any]:
    """下位契約の暗黙継承・安全弱化・旧方式再混入を拒否する。"""
    return {
        "status": "candidate_unratified",
        "direct_required_dimensions": [
            "actor_or_principal",
            "scope",
            "human_judgement",
            "allowed_side_effects",
            "forbidden_side_effects",
            "evidence_or_observation",
            "phase",
        ],
        "ac_tc_additional_dimensions": ["polarity", "failure", "recovery"],
        "inheritable_dimensions": [
            "beneficiary",
            "value",
            "task",
            "workflow",
            "selected_parent_safety_clause",
        ],
        "inheritance_binding": [
            "child_clause_id",
            "parent_subject_id",
            "parent_clause_ids",
            "parent_semantic_digest",
            "explicit_delta",
            "conflict_disposition",
        ],
        "prohibited_positive_inheritance": [
            "provider",
            "runtime",
            "route",
            "storage",
            "fixture",
            "mock",
            "fixed_threshold",
            "legacy_phase",
            "legacy_approval_transport",
            "legacy_notification_transport",
            "parent_permission_as_child_execution_permission",
        ],
        "monotonic_dimensions": ["safety", "prohibition", "human_judgement"],
        "multi_parent_contract": [
            "selected_clause_exact_union",
            "conflict_disposition",
            "implicit_union_prohibited",
            "cycle_free",
            "stale_digest_rejected",
        ],
        "classification_contract": ["direct", "digest_inherited", "replaced", "deferred"],
        "fail_close_conditions": [
            "missing_direct_high_effect_dimension",
            "inherited_only_high_effect_contract",
            "implicit_multi_parent_union",
            "safety_weakening",
            "stale_parent_digest",
            "inheritance_cycle",
            "parent_not_classified_or_cutover_blocked",
        ],
        "design_later": [
            "stable clause ID schema representation",
            "inheritance graph and cycle detector implementation",
            "clause conflict resolver implementation",
        ],
    }


def _expected_rate_quota_cost_policy() -> dict[str, Any]:
    """未知limit時もread確認と外部作用を混同せずeffect別にfail-closeする。"""
    return {
        "status": "candidate_unratified",
        "limit_classes": [
            "provider_rate",
            "provider_quota",
            "internal_safety_cap",
            "money_cost_ceiling",
            "retry_budget",
            "retry_after",
        ],
        "registration_fields": {
            "provider_rate": [
                "subject_id",
                "profile_id",
                "account_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "window",
                "source",
                "effective_revision",
                "expires_at",
            ],
            "provider_quota": [
                "subject_id",
                "profile_id",
                "account_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "window",
                "source",
                "effective_revision",
                "expires_at",
            ],
            "internal_safety_cap": [
                "subject_id",
                "profile_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "window",
                "source",
                "effective_revision",
                "expires_at",
            ],
            "money_cost_ceiling": [
                "subject_id",
                "profile_id",
                "account_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "window",
                "currency",
                "source",
                "effective_revision",
                "expires_at",
            ],
            "retry_budget": [
                "subject_id",
                "profile_id",
                "account_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "window",
                "source",
                "effective_revision",
                "expires_at",
            ],
            "retry_after": [
                "subject_id",
                "profile_id",
                "account_id",
                "operation",
                "effect",
                "risk_class",
                "value",
                "unit",
                "source",
                "effective_revision",
                "expires_at",
            ],
        },
        "not_applicable_field_contract": [
            "limit_class",
            "field",
            "reason",
            "decision_owner_subject_id",
            "review_trigger",
        ],
        "blocked_effects_when_unknown": ["external_write", "publish", "money", "additional_retry"],
        "conditionally_allowed_effects": ["read_only_limit_or_remaining_capacity_fetch"],
        "state_invariants": [
            "no_rollback_of_blocked_failed_or_safety_stopped",
            "durable_configuration_or_limit_failure_receipt",
            "no_cross_scope_limit_reuse",
        ],
        "po_decisions": [
            "business_outcome_on_limit",
            "allowed_overage",
            "money_approval_principal",
            "exception_and_resume_authority",
        ],
        "fail_close_conditions": [
            "missing_registration",
            "expired_registration",
            "unknown_value",
            "unmeasurable_limit",
            "scope_mismatch",
            "retry_after_violation",
            "cost_ceiling_missing",
        ],
        "design_later": [
            "provider adapter implementation",
            "backoff and retry scheduler",
            "counter and storage mechanism",
        ],
    }


def _expected_product_state_authority_policy() -> dict[str, Any]:
    """通知等のsignalから状態を暗黙変更せずtyped transitionだけをauthorityにする。"""
    return {
        "status": "candidate_unratified",
        "transition_binding": [
            "transition_id",
            "subject_id",
            "source_state",
            "target_state",
            "expected_prior_revision",
            "resulting_revision",
            "owner_subject_id",
            "authorization_grant_id",
            "authorization_grant_revision",
            "authorization_grant_semantic_digest",
            "effect",
            "result",
            "receipt",
        ],
        "transition_outcomes": [
            "success_requires_resulting_revision_greater_than_expected_prior_revision",
            "rejected_preserves_current_state_and_revision",
            "persistence_failure_preserves_current_state_and_revision",
        ],
        "non_authoritative_signals": [
            "notification_delivery",
            "inbox_seen",
            "inbox_acknowledged",
            "external_adapter_result",
            "retry_failure",
        ],
        "state_invariants": [
            "single_authoritative_revision",
            "no_implicit_state_change_from_signal",
            "no_rollback_from_notification_or_retry_failure",
            "append_only_transition_history",
            "current_state_preserved_on_rejection",
        ],
        "recovery_contract": [
            "new_authorized_transition",
            "source_failure_and_prior_revision",
            "recovery_actor_identity",
            "recovery_authorization_grant_ref",
            "result_and_receipt",
            "history_rewrite_prohibited",
        ],
        "po_decisions": [
            "state_taxonomy",
            "transition_required_authorization_effect_map",
            "business_outcome_on_conflict",
            "retention_quality_target",
            "recovery_quality_target",
        ],
        "registration_bindings": [
            "state_subject",
            "transition",
            "owner",
            "scope",
            "effect",
            "effective_revision",
            "quality_target",
            "authorization_grant_ref",
        ],
        "fail_close_conditions": [
            "unknown_transition",
            "stale_revision",
            "conflict",
            "unknown_owner",
            "invalid_authorization_grant",
            "persistence_failure",
            "missing_authorization_grant",
            "stale_or_expired_authorization_grant",
        ],
        "design_later": [
            "database and storage layout",
            "locking and concurrency mechanism",
            "event transport implementation",
            "recovery workflow implementation",
        ],
    }


def _expected_business_profile_authorization_policy() -> dict[str, Any]:
    """認証と認可を分離しprofile/resource/operation/effect別grantだけを許可根拠にする。"""
    return {
        "status": "candidate_unratified",
        "grant_binding": [
            "grant_id",
            "principal_id",
            "profile_id",
            "resource_id",
            "operation",
            "effect",
            "grant_revision",
            "grant_semantic_digest",
            "expires_at",
        ],
        "effect_classes": [
            "list",
            "read",
            "seen",
            "acknowledge",
            "state_write",
            "external_write",
            "money",
            "delete",
            "transfer",
        ],
        "deny_conditions": [
            "missing_grant",
            "unknown_grant",
            "stale_grant_revision",
            "expired_grant",
            "scope_mismatch",
            "cross_profile_without_explicit_grant",
            "effect_not_granted",
        ],
        "non_implication_rules": [
            "authentication_does_not_imply_authorization",
            "session_does_not_imply_authorization",
            "membership_or_role_name_does_not_imply_permission",
            "read_does_not_imply_write",
            "read_does_not_imply_cross_profile_aggregate",
            "one_effect_does_not_imply_another",
        ],
        "high_effect_contract": [
            "delete_and_transfer_are_separate_transitions",
            "no_implicit_cascade",
            "session_continuation_does_not_reuse_old_grant",
            "multi_principal_migration_requires_reauthorization",
        ],
        "state_invariants": [
            "denial_preserves_product_state_and_revision",
            "durable_authorization_receipt",
            "no_cross_profile_data_credential_or_evidence_leak",
        ],
        "po_decisions": [
            "role_taxonomy",
            "profile_owner_transfer_delete_business_outcome",
            "cross_profile_aggregate_principal",
            "delegation_break_glass_recovery_authority",
        ],
        "registration_bindings": [
            "principal",
            "profile",
            "resource",
            "operation",
            "effect",
            "grant_revision",
            "grant_semantic_digest",
            "expires_at",
        ],
        "design_later": [
            "RBAC or ABAC evaluation mechanism",
            "policy store and cache",
            "authorization UI and bootstrap flow",
        ],
    }


def _expected_vps_ui_authentication_session_policy() -> dict[str, Any]:
    """authentication/sessionとauthorizationを分離し再起動後の旧authority再利用を拒否する。"""
    return {
        "status": "candidate_unratified",
        "session_binding": [
            "session_id",
            "authenticated_principal_id",
            "identity_revision",
            "authentication_event_id",
            "authentication_event_digest",
            "issued_at",
            "expires_at",
            "revocation_revision",
            "authentication_strength",
            "last_reauthenticated_at",
        ],
        "authorization_separation": [
            "authentication_does_not_imply_authorization",
            "session_does_not_imply_authorization",
            "deep_link_does_not_imply_authentication",
            "operation_requires_grant_id_revision_and_semantic_digest",
        ],
        "deny_conditions": [
            "unknown_identity",
            "stale_identity_revision",
            "expired_session",
            "revoked_session",
            "session_fixation",
            "session_replay",
            "csrf_invalid",
            "authentication_strength_insufficient",
            "reauth_freshness_insufficient",
            "grant_missing_stale_or_expired",
        ],
        "secret_boundaries": [
            "no_raw_secret_in_repo",
            "no_raw_secret_or_bearer_token_in_product_db",
            "no_raw_secret_or_bearer_token_in_log",
            "no_raw_secret_or_bearer_token_in_inbox",
        ],
        "restart_boundary": [
            "existing_web_session_does_not_reauthorize_runtime_credential",
            "post_reboot_external_effects_stopped",
            "human_runtime_reinitialization_and_credential_reauthorization_required",
            "fresh_authorization_grant_required",
            "credential_only_auto_unlock_prohibited",
        ],
        "state_invariants": [
            "denial_preserves_product_state_and_revision",
            "durable_authentication_rejection_receipt",
            "recovery_or_break_glass_does_not_bypass_authorization_grant",
        ],
        "po_decisions": [
            "allowed_authentication_methods_and_strength",
            "identity_lifecycle_authority",
            "effect_and_risk_reauthentication_policy",
            "session_and_idle_expiry_policy",
            "lockout_business_outcome",
            "recovery_emergency_break_glass_authority",
        ],
        "registration_bindings": [
            "identity_principal",
            "allowed_authentication_method",
            "risk_and_effect_max_age",
            "idle_timeout",
            "reauth_window",
            "identity_revision",
            "session_revision",
            "revocation_revision",
        ],
        "design_later": [
            "IdP protocol and reverse proxy",
            "cookie or token mechanism",
            "CSRF mechanism",
            "session store and cache",
            "lockout recovery and authentication UI",
        ],
        "credential_material_handling": [
            "human_reauthorization_precedes_bounded_process_memory_injection",
            "dedicated_secret_authority_is_separate_unratified_choice",
            "session_persistence_allows_only_non_secret_identifier_or_one_way_digest",
            "authentication_event_digest_uses_secret_free_canonical_projection",
        ],
    }


def _expected_vps_ui_quality_attributes_policy() -> dict[str, Any]:
    """品質値を捏造せず、属性別測定と部分pass非昇格を固定する。"""
    return {
        "status": "candidate_unratified",
        "attribute_set": [
            "accessibility",
            "performance",
            "availability",
            "recovery",
            "operation",
            "migration",
            "rollback",
        ],
        "attribute_binding": [
            "attribute",
            "profile_or_scope",
            "user_journey_or_operation",
            "metric",
            "unit",
            "measurement_environment",
            "measurement_window",
            "applicability",
            "threshold_registration_id",
            "threshold_registration_revision",
            "threshold_registration_digest",
            "evidence",
            "failure_outcome",
            "recovery_or_resume_condition",
        ],
        "attribute_field_universe": [
            "attribute",
            "profile_or_scope",
            "user_journey_or_operation",
            "metric",
            "unit",
            "measurement_environment",
            "measurement_window",
            "applicability",
            "threshold_registration_id",
            "threshold_registration_revision",
            "threshold_registration_digest",
            "evidence",
            "failure_outcome",
            "recovery_or_resume_condition",
            "not_applicable_rationale",
            "applicability_evidence",
            "decision_owner_subject_id",
            "review_trigger",
            "resume_condition",
            "defer_reason",
            "defer_owner_subject_id",
            "defer_resume_trigger",
        ],
        "applicability_values": ["direct", "not_applicable", "deferred"],
        "applicability_field_contracts": {
            "direct": {
                "required": [
                    "attribute",
                    "profile_or_scope",
                    "user_journey_or_operation",
                    "metric",
                    "unit",
                    "measurement_environment",
                    "measurement_window",
                    "applicability",
                    "threshold_registration_id",
                    "threshold_registration_revision",
                    "threshold_registration_digest",
                    "evidence",
                    "failure_outcome",
                    "recovery_or_resume_condition",
                ],
                "prohibited": [
                    "not_applicable_rationale",
                    "applicability_evidence",
                    "decision_owner_subject_id",
                    "review_trigger",
                    "resume_condition",
                    "defer_reason",
                    "defer_owner_subject_id",
                    "defer_resume_trigger",
                ],
            },
            "not_applicable": {
                "required": [
                    "attribute",
                    "profile_or_scope",
                    "applicability",
                    "not_applicable_rationale",
                    "applicability_evidence",
                    "decision_owner_subject_id",
                    "review_trigger",
                    "resume_condition",
                ],
                "prohibited": [
                    "user_journey_or_operation",
                    "metric",
                    "unit",
                    "measurement_environment",
                    "measurement_window",
                    "threshold_registration_id",
                    "threshold_registration_revision",
                    "threshold_registration_digest",
                    "evidence",
                    "failure_outcome",
                    "recovery_or_resume_condition",
                    "defer_reason",
                    "defer_owner_subject_id",
                    "defer_resume_trigger",
                ],
            },
            "deferred": {
                "required": [
                    "attribute",
                    "profile_or_scope",
                    "applicability",
                    "defer_reason",
                    "defer_owner_subject_id",
                    "defer_resume_trigger",
                ],
                "prohibited": [
                    "user_journey_or_operation",
                    "metric",
                    "unit",
                    "measurement_environment",
                    "measurement_window",
                    "threshold_registration_id",
                    "threshold_registration_revision",
                    "threshold_registration_digest",
                    "evidence",
                    "failure_outcome",
                    "recovery_or_resume_condition",
                    "not_applicable_rationale",
                    "applicability_evidence",
                    "decision_owner_subject_id",
                    "review_trigger",
                    "resume_condition",
                ],
            },
        },
        "not_applicable_contract": [
            "rationale",
            "applicability_evidence",
            "decision_owner_subject_id",
            "review_trigger",
            "resume_condition",
        ],
        "fail_close_conditions": [
            "unknown_attribute",
            "unmeasured_attribute",
            "missing_threshold_registration",
            "expired_threshold_registration",
            "unknown_measurement_environment",
            "missing_evidence",
        ],
        "non_implication_rules": [
            "partial_pass_does_not_imply_overall_pass",
            "ui_quality_does_not_cover_product_state_backup_restore",
            "ui_quality_does_not_cover_worker_or_connector_availability",
            "candidate_policy_does_not_authorize_release",
        ],
        "po_decisions": [
            "attribute_applicability_and_not_applicable",
            "quality_targets_and_accepted_risk",
            "degraded_availability_business_outcome",
            "recovery_rollback_acceptance_and_resume_authority",
            "release_required_attribute_set",
        ],
        "registration_bindings": [
            "profile",
            "journey_or_operation",
            "risk_class",
            "metric",
            "value",
            "unit",
            "measurement_window",
            "measurement_environment",
            "source",
            "effective_revision",
            "expires_at",
        ],
        "design_later": [
            "measurement tooling",
            "synthetic load and accessibility harness",
            "monitoring and alerting",
            "fault injection",
            "migration and rollback mechanism",
        ],
    }


def _expected_wordpress_content_operations_policy() -> dict[str, Any]:
    """WordPress content writeをoperation別に分離し旧成功の権限化を拒否する。"""
    return {
        "status": "candidate_unratified",
        "operations": [
            "create_draft",
            "update_draft",
            "publish",
            "update_published_in_place",
            "unpublish",
            "delete",
            "rollback",
        ],
        "attempt_binding": [
            "profile_id",
            "site_id",
            "account_id",
            "stable_content_id",
            "source_revision",
            "current_remote_revision",
            "desired_digest",
            "operation",
            "effect",
            "capability_binding_revision",
            "capability_binding_digest",
            "route",
            "authorization_grant_id",
            "authorization_grant_revision",
            "authorization_grant_semantic_digest",
            "activation_decision_or_scope_id",
            "activation_scope_revision",
            "activation_scope_semantic_digest",
            "content_gate_receipt",
            "risk_gate_receipt",
            "quality_gate_receipt",
            "idempotency_key",
            "result_receipt",
        ],
        "route_policy": [
            "official_api_first_when_available",
            "official_mcp_second_when_available",
            "playwright_is_confirmation_or_separately_ratified_operation",
            "browser_confirmation_does_not_imply_write_authority",
        ],
        "unsupported_in_place_contract": [
            "no_adjacent_operation_substitution",
            "published_state_unchanged",
            "durable_unsupported_non_action_receipt",
            "no_notification",
        ],
        "non_implication_rules": [
            "update_does_not_imply_publish",
            "publish_does_not_imply_unpublish",
            "publish_does_not_imply_delete",
            "delete_does_not_imply_unpublish",
            "legacy_docker_wp_success_does_not_authorize_new_baseline",
        ],
        "fail_close_conditions": [
            "stale_remote_revision",
            "missing_stale_or_digest_mismatched_grant",
            "missing_stale_or_digest_mismatched_activation_scope",
            "activation_scope_identity_mismatch",
            "missing_gate_receipt",
            "missing_or_stale_capability",
            "scope_mismatch",
            "unsupported_operation",
            "missing_rollback_evidence",
        ],
        "po_decisions": [
            "delete_and_unpublish_scope_and_principal",
            "publication_release_admission",
            "retention_and_restore_business_outcome",
            "browser_write_admission",
            "rollback_acceptance_and_resume_authority",
        ],
        "registration_bindings": [
            "profile",
            "site",
            "account",
            "content_type",
            "stable_remote_id",
            "operation_capability",
            "execution_mode",
            "route_revision",
            "permission",
            "quota",
            "retention_version",
            "rollback_target",
        ],
        "design_later": [
            "WordPress API MCP and browser adapters",
            "diff ETag and conflict handling",
            "version archive and backup",
            "idempotency store",
            "rollback implementation",
        ],
    }


def _expected_wordpress_security_maintenance_policy() -> dict[str, Any]:
    """security変更をcontent権限・scanner signal・旧PoCから分離する。"""
    return {
        "status": "candidate_unratified",
        "operations": [
            "assess",
            "patch_core",
            "patch_plugin",
            "patch_theme",
            "permission_change",
            "credential_rotation",
            "quarantine",
            "restore_or_rollback",
        ],
        "attempt_binding": [
            "profile_id",
            "site_id",
            "account_id",
            "component_stable_id",
            "component_type",
            "installed_version",
            "current_version",
            "inventory_digest",
            "target_version",
            "advisory_source_revision",
            "advisory_source_digest",
            "risk_classification",
            "operation",
            "effect",
            "security_grant_id",
            "security_grant_revision",
            "security_grant_semantic_digest",
            "maintenance_activation_id",
            "maintenance_window_revision",
            "maintenance_window_semantic_digest",
            "compatibility_preflight_receipt",
            "backup_restore_evidence_revision",
            "backup_restore_evidence_digest",
            "credential_authority_ref",
            "route_capability_digest",
            "result_receipt",
            "rollback_receipt",
            "assessment_evidence",
            "permission_target_ref",
            "quarantine_target_ref",
            "source_failure_receipt",
            "restore_target_ref",
        ],
        "attempt_field_groups": {
            "identity": ["profile_id", "site_id", "account_id", "operation", "effect"],
            "component_inventory": [
                "component_stable_id",
                "component_type",
                "installed_version",
                "current_version",
                "inventory_digest",
            ],
            "target_version": ["target_version"],
            "advisory_source": ["advisory_source_revision", "advisory_source_digest"],
            "risk_classification": ["risk_classification"],
            "security_grant": [
                "security_grant_id",
                "security_grant_revision",
                "security_grant_semantic_digest",
            ],
            "maintenance_window": [
                "maintenance_activation_id",
                "maintenance_window_revision",
                "maintenance_window_semantic_digest",
            ],
            "preflight": ["compatibility_preflight_receipt"],
            "backup_restore": ["backup_restore_evidence_revision", "backup_restore_evidence_digest"],
            "credential_authority": ["credential_authority_ref"],
            "route": ["route_capability_digest"],
            "result": ["result_receipt"],
            "rollback": ["rollback_receipt"],
            "assessment": ["assessment_evidence"],
            "permission_target": ["permission_target_ref"],
            "quarantine_target": ["quarantine_target_ref"],
            "restore_context": ["source_failure_receipt", "restore_target_ref"],
        },
        "operation_group_contracts": {
            "assess": {
                "required": [
                    "identity",
                    "component_inventory",
                    "advisory_source",
                    "risk_classification",
                    "security_grant",
                    "route",
                    "result",
                    "assessment",
                ],
                "prohibited": [
                    "target_version",
                    "maintenance_window",
                    "preflight",
                    "backup_restore",
                    "credential_authority",
                    "rollback",
                    "permission_target",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "patch_core": {
                "required": [
                    "identity",
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "preflight",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                ],
                "prohibited": [
                    "credential_authority",
                    "assessment",
                    "permission_target",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "patch_plugin": {
                "required": [
                    "identity",
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "preflight",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                ],
                "prohibited": [
                    "credential_authority",
                    "assessment",
                    "permission_target",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "patch_theme": {
                "required": [
                    "identity",
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "preflight",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                ],
                "prohibited": [
                    "credential_authority",
                    "assessment",
                    "permission_target",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "permission_change": {
                "required": [
                    "identity",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                    "permission_target",
                ],
                "prohibited": [
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "preflight",
                    "credential_authority",
                    "assessment",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "credential_rotation": {
                "required": [
                    "identity",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "backup_restore",
                    "credential_authority",
                    "route",
                    "result",
                    "rollback",
                ],
                "prohibited": [
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "preflight",
                    "assessment",
                    "permission_target",
                    "quarantine_target",
                    "restore_context",
                ],
            },
            "quarantine": {
                "required": [
                    "identity",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                    "quarantine_target",
                ],
                "prohibited": [
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "preflight",
                    "credential_authority",
                    "assessment",
                    "permission_target",
                    "restore_context",
                ],
            },
            "restore_or_rollback": {
                "required": [
                    "identity",
                    "risk_classification",
                    "security_grant",
                    "maintenance_window",
                    "backup_restore",
                    "route",
                    "result",
                    "rollback",
                    "restore_context",
                ],
                "prohibited": [
                    "component_inventory",
                    "target_version",
                    "advisory_source",
                    "preflight",
                    "credential_authority",
                    "assessment",
                    "permission_target",
                    "quarantine_target",
                ],
            },
        },
        "non_authority_signals": [
            "content_grant",
            "publication_approval",
            "advisory_presence",
            "scanner_result",
            "browser_confirmation",
            "legacy_wp_poc_success",
        ],
        "fail_close_conditions": [
            "unknown_component",
            "unknown_version",
            "unknown_advisory_source",
            "unsupported_target",
            "missing_stale_or_digest_mismatched_security_grant",
            "credential_material_exposure",
            "scope_mismatch",
            "operation_required_group_missing",
        ],
        "emergency_contract": [
            "separate_grant",
            "bounded_scope",
            "expires_at",
            "durable_receipt",
            "no_automatic_normal_operation_resume",
            "post_change_revalidation_required",
        ],
        "po_decisions": [
            "threat_and_risk_acceptance",
            "severity_to_response_outcome",
            "patch_rotation_quarantine_principals",
            "maintenance_window_and_allowed_downtime",
            "emergency_break_glass_authority",
            "support_and_eol_policy",
            "rollback_resume_authority",
        ],
        "registration_bindings": [
            "site_component_inventory",
            "supported_version_source",
            "advisory_source",
            "risk_mapping",
            "permission_baseline",
            "credential_authority_id",
            "maintenance_window",
            "backup_freshness",
            "restore_target",
            "route_capability",
        ],
        "design_later": [
            "scanner and advisory adapter",
            "staging and preflight",
            "WordPress update adapter",
            "backup and restore",
            "quarantine",
            "credential rotation mechanism",
        ],
    }


def _actionable_refinement_subjects(records: list[Any]) -> set[str]:
    """Return current decision subjects; superseded records are history only."""
    return {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("subject_id"), str)
        and record.get("lifecycle_status") != "superseded"
    }


def decision_packet_faults(refinements: dict[str, Any]) -> list[str]:
    """PO確認用packetが全subjectを一度だけ覆い、packet単位の一括承認を禁止する。"""
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    all_subjects = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    subjects = _actionable_refinement_subjects(records)
    packets = refinements.get("decision_packets")
    if not isinstance(packets, list) or not packets:
        return ["decision packetがない"]
    faults: list[str] = []
    packet_ids = [packet.get("packet_id") for packet in packets if isinstance(packet, dict)]
    orders = [
        order
        for packet in packets
        if isinstance(packet, dict)
        if isinstance((order := packet.get("decision_order")), int)
    ]
    if len(packet_ids) != len(set(packet_ids)):
        faults.append("decision packet ID重複")
    if sorted(orders) != list(range(1, len(packets) + 1)):
        faults.append("decision packet順序が連続でない")
    covered = [
        subject
        for packet in packets
        if isinstance(packet, dict)
        for subject in packet.get("subject_ids", [])
        if isinstance(subject, str)
    ]
    if set(covered) != subjects or len(covered) != len(set(covered)):
        faults.append("decision packetが全subjectをexactly onceで覆わない")
    if any(
        packet.get("bulk_decision_forbidden") is not True for packet in packets if isinstance(packet, dict)
    ):
        faults.append("decision packetの一括承認禁止がない")
    pending_questions = [
        question
        for record in records
        if isinstance(record, dict)
        for question in record.get("pending_resolution", [])
        if isinstance(question, str)
    ]
    if len(pending_questions) != len(set(pending_questions)):
        faults.append("同一PO質問が複数subjectに重複している")
    expected_question_ids = {
        f"RDQ-{record['refinement_id'][4:]}-{index:02d}"
        for record in records
        if isinstance(record, dict) and isinstance(record.get("refinement_id"), str)
        for index, _question in enumerate(record.get("pending_resolution", []), start=1)
    }
    classifications = refinements.get("question_classifications")
    allowed_classes = {
        "requirements_policy",
        "authority_choice",
        "safety_policy",
        "quality_target",
        "release_scope",
        "deferred_resume",
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
    if not isinstance(boundary, dict) or not all(
        boundary.get(key) for key in ("po_decides", "design_later", "rule")
    ):
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
            if not affected or not affected <= all_subjects:
                faults.append(f"{item.get('decision_id')}: affected subjectが未知")
            if not new_subjects or not new_subjects <= all_subjects:
                faults.append(f"{item.get('decision_id')}: 新規要求subjectがrefinementへ未materialize")
            if item.get("status") != "captured_unratified" or item.get("design_not_started") is not True:
                faults.append(f"{item.get('decision_id')}: 未承認・未設計境界が不正")
        records_by_subject = {
            str(record.get("subject_id")): record
            for record in records
            if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
        }
        expected_controls = _expected_captured_po_decision_controls()
        controls = refinements.get("captured_po_decision_controls")
        if controls != expected_controls:
            faults.append("captured PO回答のtyped controlが正本とexactly一致しない")
        else:
            captured_by_id = {
                str(item.get("decision_id")): item for item in captured if isinstance(item, dict)
            }
            for decision_id, control in expected_controls.items():
                decision = captured_by_id.get(decision_id, {})
                decision_snapshot = {key: value for key, value in decision.items() if key != "decision_id"}
                if _digest(decision_snapshot) != control["decision_snapshot_digest"]:
                    faults.append(f"{decision_id}: captured PO回答snapshotが反転又は欠落")
                projection_digests = control.get("subject_projection_digests", {})
                expected_subjects = set(control["subject_semantic_digests"]) | set(projection_digests)
                if set(decision.get("required_new_subject_ids", [])) != expected_subjects:
                    faults.append(f"{decision_id}: typed controlのsubject集合がPO snapshotと不一致")
                for subject, expected_digest in control["subject_semantic_digests"].items():
                    record = records_by_subject.get(subject)
                    semantic = (
                        {
                            key: value
                            for key, value in record.items()
                            if key not in {"semantic_digest", "approval"}
                        }
                        if isinstance(record, dict)
                        else None
                    )
                    if not isinstance(semantic, dict) or _digest(semantic) != expected_digest:
                        faults.append(
                            f"{decision_id}/{subject}: captured PO回答の意味materializationが反転又は欠落"
                        )
                for subject, expected_digest in projection_digests.items():
                    record = records_by_subject.get(subject)
                    projection = (
                        _captured_po_subject_projection(decision_id, subject, record)
                        if isinstance(record, dict)
                        else None
                    )
                    if not isinstance(projection, dict) or _digest(projection) != expected_digest:
                        faults.append(f"{decision_id}/{subject}: captured PO回答projectionが反転又は欠落")
        expected_resolver_controls = _expected_resolver_candidate_controls()
        resolver_controls = refinements.get("resolver_candidate_controls")
        if resolver_controls != expected_resolver_controls:
            faults.append("resolver候補controlが正本とexactly一致しない")
        else:
            for subject, control in expected_resolver_controls.items():
                record = records_by_subject.get(subject)
                semantic = (
                    {
                        key: value
                        for key, value in record.items()
                        if key not in {"semantic_digest", "approval"}
                    }
                    if isinstance(record, dict)
                    else None
                )
                if not isinstance(semantic, dict) or _digest(semantic) != control["semantic_digest"]:
                    faults.append(f"{subject}: resolver候補の意味が反転又は欠落")
        if refinements.get("semantic_coverage_policy") != _expected_semantic_coverage_policy():
            faults.append("semantic coverage resolver policyが正本とexactly一致しない")
        if (
            refinements.get("contract_semantic_descent_policy")
            != _expected_contract_semantic_descent_policy()
        ):
            faults.append("contract semantic descent resolver policyが正本とexactly一致しない")
        if refinements.get("rate_quota_cost_policy") != _expected_rate_quota_cost_policy():
            faults.append("rate/quota/cost resolver policyが正本とexactly一致しない")
        if refinements.get("product_state_authority_policy") != _expected_product_state_authority_policy():
            faults.append("product state authority resolver policyが正本とexactly一致しない")
        if (
            refinements.get("business_profile_authorization_policy")
            != _expected_business_profile_authorization_policy()
        ):
            faults.append("business profile authorization resolver policyが正本とexactly一致しない")
        if (
            refinements.get("vps_ui_authentication_session_policy")
            != _expected_vps_ui_authentication_session_policy()
        ):
            faults.append("VPS UI authentication/session resolver policyが正本とexactly一致しない")
        if (
            refinements.get("vps_ui_quality_attributes_policy")
            != _expected_vps_ui_quality_attributes_policy()
        ):
            faults.append("VPS UI quality attributes resolver policyが正本とexactly一致しない")
        quality_policy = refinements.get("vps_ui_quality_attributes_policy")
        if isinstance(quality_policy, dict):
            universe = set(quality_policy.get("attribute_field_universe", []))
            contracts = quality_policy.get("applicability_field_contracts", {})
            for disposition in quality_policy.get("applicability_values", []):
                contract = contracts.get(disposition, {}) if isinstance(contracts, dict) else {}
                required = set(contract.get("required", []))
                prohibited = set(contract.get("prohibited", []))
                if required & prohibited or required | prohibited != universe:
                    faults.append(f"VPS UI quality {disposition}: field partitionがexactでない")
        if (
            refinements.get("wordpress_content_operations_policy")
            != _expected_wordpress_content_operations_policy()
        ):
            faults.append("WordPress content operations resolver policyが正本とexactly一致しない")
        if (
            refinements.get("wordpress_security_maintenance_policy")
            != _expected_wordpress_security_maintenance_policy()
        ):
            faults.append("WordPress security maintenance resolver policyが正本とexactly一致しない")
        security_policy = refinements.get("wordpress_security_maintenance_policy")
        if isinstance(security_policy, dict):
            fields = security_policy.get("attempt_binding", [])
            groups = security_policy.get("attempt_field_groups", {})
            grouped_fields = [field for values in groups.values() for field in values]
            if sorted(grouped_fields) != sorted(fields) or len(grouped_fields) != len(set(grouped_fields)):
                faults.append("WordPress security attempt field group partitionがexactでない")
            group_universe = set(groups)
            contracts = security_policy.get("operation_group_contracts", {})
            for operation in security_policy.get("operations", []):
                contract = contracts.get(operation, {}) if isinstance(contracts, dict) else {}
                required = set(contract.get("required", []))
                prohibited = set(contract.get("prohibited", []))
                if required & prohibited or required | prohibited != group_universe:
                    faults.append(f"WordPress security {operation}: group partitionがexactでない")
        platform_policy = refinements.get("wordpress_platform_maintenance_policy")
        if not isinstance(platform_policy, dict) or _digest(platform_policy) != (
            "sha256:dc6718df859dc9a997ce62ede7c16f62fb73d5eab6c74da9340bddaa0f578595"
        ):
            faults.append("WordPress platform maintenance resolver policyが正本digestと一致しない")
        if isinstance(platform_policy, dict):
            fields = platform_policy.get("attempt_binding", [])
            groups = platform_policy.get("field_groups", {})
            grouped_fields = [field for values in groups.values() for field in values]
            if sorted(grouped_fields) != sorted(fields) or len(grouped_fields) != len(set(grouped_fields)):
                faults.append("WordPress platform attempt field group partitionがexactでない")
            group_universe = set(groups)
            contracts = platform_policy.get("operation_group_contracts", {})
            for operation in platform_policy.get("operations", []):
                contract = contracts.get(operation, {}) if isinstance(contracts, dict) else {}
                required = set(contract.get("required", []))
                conditional = set(contract.get("conditional", []))
                prohibited = set(contract.get("prohibited", []))
                if (
                    required & conditional
                    or required & prohibited
                    or conditional & prohibited
                    or required | conditional | prohibited != group_universe
                ):
                    faults.append(f"WordPress platform {operation}: group partitionがexactでない")
            inspect = contracts.get("inspect_inventory", {}) if isinstance(contracts, dict) else {}
            presence = platform_policy.get("presence_contract", {})
            inspect_presence = presence.get("inspect_inventory", {}) if isinstance(presence, dict) else {}
            if (
                "observed_installed_state" not in inspect.get("conditional", [])
                or "observed_installed_state" in inspect.get("required", [])
                or inspect_presence
                != {
                    "present": "installed_state_required",
                    "absent": "installed_state_prohibited",
                    "unknown": "deferred",
                }
            ):
                faults.append("WordPress platform inspect presence cross contractが不正")
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
            "refinement_id",
            "revision",
            "semantic_digest",
            "question_id",
            "response",
            "rationale",
            "approver_principal",
            "decided_at",
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
    subjects = _actionable_refinement_subjects(records)
    bindings = refinements.get("candidate_requirement_bindings")
    if not isinstance(bindings, dict):
        return ["PRC意味所有者bindingがない"]
    headings = set(
        re.findall(r"^### (PRC-[0-9]{2})\b", CANDIDATE_BASELINE.read_text(encoding="utf-8"), re.MULTILINE)
    )
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
    historical_subjects = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and record.get("lifecycle_status") == "superseded"
    }
    if historical_subjects & bound_subjects:
        faults.append("superseded履歴subjectをPRC meaning ownerへ再混入")
    if bound_subjects != subjects:
        faults.append(f"PRCへ未束縛のrefinement subject={sorted(subjects - bound_subjects)}")
    notification_bindings = {
        "PRC-04": ["VPS-UI-INBOX-LIFECYCLE"],
        "PRC-05": ["DISCORD-COMMUNITY-MARKETING-ROUTE", "DISCORD-NOTIFICATION-REJECTION-BOUNDARY"],
        "PRC-31": ["DISCORD-COMMUNITY-MARKETING-ROUTE"],
    }
    for prc_id, expected in notification_bindings.items():
        if bindings.get(prc_id) != expected:
            faults.append(f"{prc_id}: 通知／Discord community意味所有者が不正")
    for prc_id in ("PRC-06", "PRC-22"):
        owners = bindings.get(prc_id, [])
        if "AUTOMATED-PUBLISHING-ADMISSION" not in owners or "AUTO-MODE-DECISION-AUTHORITY" in owners:
            faults.append(f"{prc_id}: 旧auto-modeでなく初回activation後自動運用を意味所有者にする必要がある")
    if bindings.get("PRC-24") != [
        "GENAI-EXECUTION-ROUTE",
        "LEGACY-MEDIA-ADMISSION-INVENTORY",
        "STRATEGY-REQUIREMENT-ADMISSION",
    ]:
        faults.append("PRC-24: 現役deferred/follow-on意味owner集合が不正")
    ui_record = next(
        (
            record
            for record in records
            if isinstance(record, dict) and record.get("subject_id") == "VPS-UI-PRIMARY-HUMAN-INTERFACE"
        ),
        None,
    )
    dimensions = ui_record.get("semantic_dimensions") if isinstance(ui_record, dict) else None
    ui_text = (
        json.dumps(dimensions, ensure_ascii=False, sort_keys=True) if isinstance(dimensions, dict) else ""
    )
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
        "L0V04-PURPOSE",
        "L0V04-DUAL-LOOP",
        "L0V04-MEDIA-PARALLEL",
        "L0V04-PWA-PLAY",
        "L0V04-HUMAN-AI",
        "L0V04-PILLARS",
        "L0V04-CONSUMER-WEB-AUTOMATION",
        "L0V04-CONNECTOR-PRIORITY",
        "L0V04-CLAUDE-DESIGN",
        "L0V04-BROWSER-MEASUREMENT",
        "L0V04-FULL-V",
        "L0V04-RUNTIME",
        "L0V04-DISCORD-APPROVAL",
        "L0V04-DISCORD-COMMUNITY",
        "L0V04-AUTO-MODE",
    }
    ids = [row.get("clause_id") for row in rows if isinstance(row, dict)]
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        faults.append(f"旧L0 clause被覆が不正 missing={sorted(expected_ids - set(ids))}")
    prc_ids = set((refinements.get("candidate_requirement_bindings") or {}).keys())
    by_id = {str(row.get("clause_id")): row for row in rows if isinstance(row, dict)}
    for clause_id, row in by_id.items():
        replacements = row.get("replacement_prc_ids")
        if (
            not isinstance(replacements, list)
            or not replacements
            or any(item not in prc_ids for item in replacements)
        ):
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


def _legacy_l0_source_clause_digests(refinements: dict[str, Any]) -> dict[str, str]:
    """旧charterの一意な意味segmentをclause locatorと組にしてsnapshot化する。"""
    text = LEGACY_L0_CHARTER.read_text(encoding="utf-8")
    needles = {
        "L0V04-PURPOSE": "TAKUMI-CMO のマーケティング頭脳を、HELIX 流",
        "L0V04-DUAL-LOOP": "上流戦略 OS は市場・顧客・価値仮説・戦略選択・媒体役割・KPI を版付き brief",
        "L0V04-MEDIA-PARALLEL": "媒体ごとに独立して並走（X / note / YouTube / owned media / Discord コミュニティ",
        "L0V04-PWA-PLAY": "**App 系（確定 2026-07-30）**: **主 = PWA**",
        "L0V04-HUMAN-AI": "外部公開（投稿・公開）という高影響 action",
        "L0V04-PILLARS": "**P0 ゼロ広告費ゲート**",
        "L0V04-CONSUMER-WEB-AUTOMATION": "生成 AI 画像・動画 | **保有アカウント",
        "L0V04-CONNECTOR-PRIORITY": "### 外部接続の一般原則 — MCP → ブラウザ → 有償 API",
        "L0V04-CLAUDE-DESIGN": "### デザインシステム — Claude Design 連携（必須）",
        "L0V04-BROWSER-MEASUREMENT": "### 計測データの取り込み — ブラウザエクスポート → 解体 → SQLite",
        "L0V04-FULL-V": "## §7 HELIX V-model への写像",
        "L0V04-RUNTIME": "## §8 実行環境・配置",
        "L0V04-DISCORD-APPROVAL": "**通知・承認（改訂 2026-08-12）**",
        "L0V04-DISCORD-COMMUNITY": "**Discord = コミュニティマーケティング媒体",
        "L0V04-AUTO-MODE": "**公開承認（④ 確定 2026-07-30）**",
    }
    result: dict[str, str] = {}
    for row in refinements.get("legacy_l0_clause_dispositions", []):
        if not isinstance(row, dict):
            continue
        clause_id = str(row.get("clause_id"))
        needle = needles.get(clause_id, "")
        occurrences = [match.start() for match in re.finditer(re.escape(needle), text)] if needle else []
        segment = ""
        if len(occurrences) == 1:
            start = text.rfind("\n\n", 0, occurrences[0]) + 2
            end = text.find("\n\n", occurrences[0])
            segment = text[start : (len(text) if end < 0 else end)].strip()
        result[clause_id] = _digest(
            {
                "source_path": str(LEGACY_L0_CHARTER.relative_to(REPO_ROOT)),
                "locator": str(row.get("source_ref", "")),
                "needle": needle,
                "occurrence_count": len(occurrences),
                "segment": segment,
            }
        )
    return result


def _l0_candidate_clause_semantics(legacy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """候補価値と廃止対象の旧mechanismを混ぜずに型付き投影する。"""
    mechanisms: dict[str, list[tuple[str, str]]] = {
        "L0V04-MEDIA-PARALLEL": [("fixed_media_scope", "固定媒体一覧をkernel又は初期release scopeへ焼き付ける")],
        "L0V04-PWA-PLAY": [("fixed_app_priority", "PWAを主、Google Playを従として初期媒体scopeへ固定する")],
        "L0V04-HUMAN-AI": [("machine_permission_bypass", "安定稼働証跡だけでscope activationを省略する")],
        "L0V04-CONSUMER-WEB-AUTOMATION": [("consumer_ui_automation", "consumer Web UIの無人操作を製品実行経路にする")],
        "L0V04-CONNECTOR-PRIORITY": [("fixed_route_priority", "MCP→browser→有償APIの順を全operationへ固定する")],
        "L0V04-CLAUDE-DESIGN": [("provider_lock_in", "Claude Designを必須かつ単一のdesign-token正本にする")],
        "L0V04-BROWSER-MEASUREMENT": [("browser_bypass", "browser export又はbrowser突破を計測・SNSの一般経路にする")],
        "L0V04-RUNTIME": [("runtime_placement", "旧development workspace又は旧runtime配置を現製品authorityとして継承する")],
        "L0V04-DISCORD-APPROVAL": [("approval_transport", "Discordを製品通知又は投稿可否decision経路にする")],
        "L0V04-AUTO-MODE": [("machine_permission_bypass", "gate証跡だけで初回activation・scope拡張・停止後再開を行う")],
    }
    result: dict[str, Any] = {}
    for row in legacy_rows:
        clause_id = str(row["clause_id"])
        value_id = f"L0N-{clause_id.removeprefix('L0V04-')}-VALUE"
        value_text = str(row["retained_value"])
        prohibited = [
            {
                "clause_id": f"L0P-{clause_id.removeprefix('L0V04-')}-{index}",
                "kind": kind,
                "text": mechanism,
                "semantic_digest": _digest({"kind": kind, "text": mechanism}),
            }
            for index, (kind, mechanism) in enumerate(mechanisms.get(clause_id, []), start=1)
        ]
        result[clause_id] = {
            "retained_value_clauses": [
                {"clause_id": value_id, "text": value_text, "semantic_digest": _digest({"text": value_text})}
            ],
            "prohibited_mechanism_clauses": prohibited,
            "source_meaning_digest": _digest(str(row["meaning"])),
            "no_retained_reason": None,
        }
    return result


def _candidate_prc_digests() -> dict[str, str]:
    text = CANDIDATE_BASELINE.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^### (PRC-[0-9]{2})\b.*$", text, re.MULTILINE))
    return {
        match.group(1): _digest(
            text[match.start() : (matches[index + 1].start() if index + 1 < len(matches) else len(text))].strip()
        )
        for index, match in enumerate(matches)
    }


def l0_north_star_authority_normalization_policy_faults(
    refinements: dict[str, Any]
) -> list[str]:
    """旧L0 15 clause候補とPO/PCR projectionを一意な新L0 cutoverへ束縛する。"""
    policy = refinements.get("l0_north_star_authority_normalization_policy")
    if not isinstance(policy, dict):
        return ["L0 north-star authority normalization policyがない"]
    legacy_rows = refinements.get("legacy_l0_clause_dispositions")
    controls = refinements.get("captured_po_decision_controls")
    if not isinstance(legacy_rows, list) or not isinstance(controls, dict):
        return ["L0 normalization source snapshotがない"]
    faults: list[str] = []
    expected_legacy_digest = "sha256:7d557ec3a36c893facff7a4fc09f09930ef74202b07a2b2bd4e4e8394611e704"
    if len(legacy_rows) != 15 or policy.get("legacy_clause_count") != 15:
        faults.append("L0 immutable candidate snapshotが15 clauseをexact被覆しない")
    if _digest(legacy_rows) != expected_legacy_digest or policy.get("legacy_clause_snapshot_digest") != _digest(legacy_rows):
        faults.append("L0 immutable candidate snapshot digestが不一致")
    source_digests = _legacy_l0_source_clause_digests(refinements)
    if policy.get("legacy_source_clause_digests") != source_digests:
        faults.append("L0 source path/locator/content digestが旧charter実体と不一致")
    expected_clause_semantics = _l0_candidate_clause_semantics(
        [row for row in legacy_rows if isinstance(row, dict)]
    )
    if policy.get("candidate_clause_semantics_digest") != _digest(expected_clause_semantics):
        faults.append("L0 retained value/prohibited mechanism候補が型付き意味projectionと不一致")
    prc_digests = _candidate_prc_digests()
    referenced_prcs = sorted({prc for row in legacy_rows for prc in row.get("replacement_prc_ids", [])})
    expected_prcs = {prc: prc_digests.get(prc) for prc in referenced_prcs}
    if policy.get("replacement_prc_digests") != expected_prcs or any(value is None for value in expected_prcs.values()):
        faults.append("L0 replacement PRC digest projectionが不一致")
    pod_ids = [f"POD-20260815-{index:03d}" for index in (1, 2, 3, 4, 5, 6, 7, 9)]
    expected_pod_projection = {decision_id: controls.get(decision_id) for decision_id in pod_ids}
    if policy.get("captured_po_projection_digest") != _digest(expected_pod_projection):
        faults.append("L0確定事項projection digestがVPS/UI/Discord/route/auto/research controlsと不一致")
    state = policy.get("classification_state")
    if not isinstance(state, dict):
        return faults + ["L0 classification stateがない"]
    stage = state.get("status")
    if stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified":
            faults.append("L0未分類なのにpolicyがratified")
        if (
            state.get("selected_rows") != {}
            or state.get("classification_approval") is not None
            or state.get("candidate_artifact_binding") is not None
            or state.get("cutover_artifact_bindings") is not None
            or state.get("cutover_blocked") is not True
        ):
            faults.append("L0未分類なのに選択又はcutover解除されている")
        return faults
    if stage not in {"classified_pending_cutover", "cutover_complete"}:
        return faults + ["L0 classification stageが不正"]
    expected_status = "ratified" if stage == "cutover_complete" else "candidate_unratified"
    if policy.get("status") != expected_status:
        faults.append("L0 stageとpolicy statusが不一致")
    source_by_id = {str(row.get("clause_id")): row for row in legacy_rows if isinstance(row, dict)}
    selected = state.get("selected_rows")
    if not isinstance(selected, dict) or set(selected) != set(source_by_id):
        return faults + ["L0 classified rowsが15 clauseをexact被覆しない"]
    known_subjects = {
        str(record.get("subject_id"))
        for record in refinements.get("records", [])
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    fields = {"parent_row_digest", "source_clause_digest", "disposition", "retained_value_clause_ids", "prohibited_legacy_mechanisms", "replacement_prc_digests", "captured_po_control_ids", "scope_subject_ids", "owner_subject_id", "rationale", "resume_conditions"}
    required_controls_by_clause = {
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
    for clause_id, row in selected.items():
        source = source_by_id[clause_id]
        if not isinstance(row, dict) or set(row) != fields:
            faults.append(f"{clause_id}: L0 classified row field閉集合が不正")
            continue
        if row.get("parent_row_digest") != _digest(source) or row.get("source_clause_digest") != source_digests.get(clause_id):
            faults.append(f"{clause_id}: L0 parent/source clause digestがstale")
        disposition = row.get("disposition")
        retained = row.get("retained_value_clause_ids")
        prohibited = row.get("prohibited_legacy_mechanisms")
        resume = row.get("resume_conditions")
        replacement = row.get("replacement_prc_digests")
        if disposition not in {"retain", "replace", "defer", "obsolete"}:
            faults.append(f"{clause_id}: L0 dispositionが不正")
        semantic_contract = expected_clause_semantics.get(clause_id, {})
        expected_retained = [
            value["clause_id"] for value in semantic_contract.get("retained_value_clauses", [])
        ]
        expected_prohibited = [
            value["clause_id"] for value in semantic_contract.get("prohibited_mechanism_clauses", [])
        ]
        if retained != ([] if disposition == "obsolete" else expected_retained):
            faults.append(f"{clause_id}: retained value clause IDが不正")
        if prohibited != expected_prohibited:
            faults.append(f"{clause_id}: prohibited legacy mechanismsが不正")
        if set(retained or []) & set(prohibited or []):
            faults.append(f"{clause_id}: retained valueとprohibited mechanismが重複")
        expected_replacement = {prc: expected_prcs[prc] for prc in source.get("replacement_prc_ids", [])}
        if replacement != expected_replacement:
            faults.append(f"{clause_id}: replacement PRC digestがsource候補と不一致")
        control_ids = row.get("captured_po_control_ids")
        if control_ids != required_controls_by_clause.get(clause_id):
            faults.append(f"{clause_id}: captured PO control参照が不正")
        if not isinstance(row.get("scope_subject_ids"), list) or not row["scope_subject_ids"] or not set(row["scope_subject_ids"]) <= known_subjects or row.get("owner_subject_id") not in known_subjects:
            faults.append(f"{clause_id}: L0 scope/ownerが空又は未知")
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            faults.append(f"{clause_id}: rationaleがない")
        if disposition == "retain" and (not retained or prohibited or resume != []):
            faults.append(f"{clause_id}: retain field partitionが不正")
        elif disposition == "replace" and (not retained or not prohibited or resume != []):
            faults.append(f"{clause_id}: replace field partitionが不正")
        elif disposition == "defer" and (not isinstance(resume, list) or not resume or not all(isinstance(value, str) and value.strip() for value in resume)):
            faults.append(f"{clause_id}: defer field partitionが不正")
        elif disposition == "obsolete" and (retained or not prohibited or resume != []):
            faults.append(f"{clause_id}: obsolete field partitionが不正")
    selected_digest = _digest(selected)
    approval = state.get("classification_approval")
    if (
        not isinstance(approval, dict)
        or approval.get("authority") != "PO"
        or approval.get("subject_id") != "L0-NORTH-STAR-AUTHORITY-NORMALIZATION"
        or approval.get("legacy_snapshot_digest") != _digest(legacy_rows)
        or approval.get("source_clause_digests_digest") != _digest(source_digests)
        or approval.get("selected_rows_digest") != selected_digest
        or approval.get("candidate_clause_semantics_digest") != _digest(expected_clause_semantics)
        or approval.get("captured_po_projection_digest") != _digest(expected_pod_projection)
    ):
        faults.append("L0 classification approvalがPO・source・projection・row-setへ束縛されていない")
    manifest = load(MANIFEST)
    manifest_by_id = {
        str(item.get("artifact_id")): item
        for item in manifest.get("items", [])
        if isinstance(item, dict)
    }
    candidate = state.get("candidate_artifact_binding")
    candidate_item = manifest_by_id.get(str(candidate.get("artifact_id"))) if isinstance(candidate, dict) else None
    candidate_path = REPO_ROOT / str(candidate_item.get("canonical_path")) if isinstance(candidate_item, dict) else None
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest() if candidate_path is not None and candidate_path.is_file() else None
    if (
        not isinstance(candidate, dict)
        or set(candidate) != {"artifact_id", "content_digest"}
        or candidate.get("artifact_id") != "AUTH-DEVELOPMENT-L0-NORTH-STAR-CANDIDATE"
        or not isinstance(candidate_item, dict)
        or candidate_item.get("layer") != "L0-charter"
        or candidate_item.get("artifact_type") != "north-star-authority-candidate"
        or candidate_item.get("authority_format") != "json"
        or candidate_item.get("authority_status") != "active"
        or candidate_item.get("implementation_input") is not (stage == "cutover_complete")
        or candidate.get("content_digest") != candidate_digest
    ):
        faults.append("L0 candidate artifact identity/digest/input境界が不正")
    else:
        try:
            candidate_data = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else {}
        except (OSError, json.JSONDecodeError):
            candidate_data = {}
        if (
            candidate_data.get("north_star_clause_row_digests")
            != {clause_id: _digest(row) for clause_id, row in selected.items()}
            or candidate_data.get("north_star_clause_semantics") != expected_clause_semantics
            or candidate_data.get("captured_po_projection_digest") != _digest(expected_pod_projection)
            or candidate_data.get("captured_po_controls") != expected_pod_projection
        ):
            faults.append("L0 candidate projectionが15 row/確定PO controlsと不一致")
        if not isinstance(approval, dict) or approval.get("candidate_content_digest") != candidate_digest:
            faults.append("L0 classification approvalがcandidate実内容へ束縛されていない")
    if stage == "classified_pending_cutover":
        if state.get("cutover_blocked") is not True or state.get("cutover_artifact_bindings") is not None:
            faults.append("L0 classified pendingがfail-closeでない")
    else:
        if state.get("cutover_blocked") is not False:
            faults.append("L0 cutover completeが解除されていない")
        bindings = state.get("cutover_artifact_bindings")
        required = {"l0_json_artifact_id", "l0_json_digest", "generated_view_artifact_id", "generated_view_digest", "l1_trace_artifact_id", "l1_trace_digest", "manifest_digest", "baseline_digest", "target_commit", "target_tree", "same_commit", "trace_diff_count", "independent_go_artifact_id", "independent_go_digest"}
        if not isinstance(bindings, dict) or set(bindings) != required:
            faults.append("L0 cutover artifact bindingが不完全")
        elif (
            bindings.get("same_commit") is not True
            or bindings.get("trace_diff_count") != 0
            or bindings.get("l0_json_artifact_id") != (candidate.get("artifact_id") if isinstance(candidate, dict) else None)
            or bindings.get("l0_json_digest") != (candidate.get("content_digest") if isinstance(candidate, dict) else None)
            or any(
                not isinstance(bindings.get(key), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", bindings[key])
                for key in ("l0_json_digest", "generated_view_digest", "l1_trace_digest", "manifest_digest", "baseline_digest", "independent_go_digest")
            )
        ):
            faults.append("L0 cutover digest/same-commit/trace境界が不正")
        else:
            artifact_paths: dict[str, Path] = {}
            for id_key, digest_key in (
                ("l0_json_artifact_id", "l0_json_digest"),
                ("generated_view_artifact_id", "generated_view_digest"),
                ("l1_trace_artifact_id", "l1_trace_digest"),
                ("independent_go_artifact_id", "independent_go_digest"),
            ):
                manifest_item = manifest_by_id.get(str(bindings.get(id_key)))
                bound_path = (
                    REPO_ROOT / str(manifest_item.get("canonical_path"))
                    if isinstance(manifest_item, dict)
                    else None
                )
                if bound_path is not None:
                    artifact_paths[id_key] = bound_path
                actual = (
                    "sha256:" + hashlib.sha256(bound_path.read_bytes()).hexdigest()
                    if bound_path is not None and bound_path.is_file()
                    else None
                )
                if actual != bindings.get(digest_key):
                    faults.append(f"L0 {id_key}がmanifest実artifactへ束縛されていない")
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            for path, key in ((MANIFEST, "manifest_digest"), (baseline_path, "baseline_digest")):
                actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                if actual != bindings.get(key):
                    faults.append(f"L0 {key}が実fileと不一致")
            head = git("rev-parse", "HEAD").stdout.strip()
            tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
            if bindings.get("target_commit") != head or bindings.get("target_tree") != tree:
                faults.append("L0 cutoverが現HEAD/treeへ束縛されていない")
            for path in [MANIFEST, baseline_path, *artifact_paths.values()]:
                try:
                    relative = str(path.relative_to(REPO_ROOT))
                except ValueError:
                    faults.append("L0 cutover artifactがrepo外")
                    continue
                shown = git("show", f"HEAD:{relative}")
                if shown.returncode != 0 or hashlib.sha256(shown.stdout.encode()).hexdigest() != hashlib.sha256(path.read_bytes()).hexdigest():
                    faults.append(f"L0 {relative}がHEAD blobと不一致")
            review_path = artifact_paths.get("independent_go_artifact_id")
            view_path = artifact_paths.get("generated_view_artifact_id")
            trace_path = artifact_paths.get("l1_trace_artifact_id")
            try:
                view = json.loads(view_path.read_text(encoding="utf-8")) if view_path else {}
                trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path else {}
            except (OSError, json.JSONDecodeError):
                view, trace = {}, {}
            expected_row_digests = {clause_id: _digest(row) for clause_id, row in selected.items()}
            expected_trace = {
                "source_l0_content_digest": candidate_digest,
                "l0_clause_to_prcs": {
                    clause_id: sorted(source_by_id[clause_id].get("replacement_prc_ids", []))
                    for clause_id in sorted(selected)
                },
                "l0_clause_to_scope_subjects": {
                    clause_id: sorted(selected[clause_id]["scope_subject_ids"])
                    for clause_id in sorted(selected)
                },
            }
            if view != {
                "source_l0_content_digest": candidate_digest,
                "rendered_clause_row_digests": expected_row_digests,
                "rendered_clause_semantics": expected_clause_semantics,
            }:
                faults.append("L0 generated viewがcandidate canonical projectionと不一致")
            if trace != expected_trace:
                faults.append("L0→L1 traceが15 clauseのPRC/scope exact mappingと不一致")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
            except (OSError, ValueError, json.JSONDecodeError):
                review = {}
            reviewed = review.get("reviewed_artifact_digests", {})
            if (
                review.get("separation_status") != "ci_attested"
                or review.get("verdict") != "Go"
                or not isinstance(review.get("reviewer_principal"), str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po", review.get("author_principal")}
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(reviewed, dict)
                or any(bindings[key] not in reviewed.values() for key in ("l0_json_digest", "generated_view_digest", "l1_trace_digest"))
            ):
                faults.append("L0 independent Goがcommit/tree/L0/view/L1 traceを被覆しない")
    return faults


def strategy_requirement_admission_policy_faults(
    ctx: Ctx, refinements: dict[str, Any]
) -> list[str]:
    """SR19件を旧意味、L0、test authority、research/risk候補へ束縛して隔離する。"""
    policy = refinements.get("strategy_requirement_admission_policy")
    if not isinstance(policy, dict):
        return ["strategy requirement admission policyがない"]
    snapshot = {
        stable_id: value
        for stable_id, value in _legacy_strategy_quality_meaning_snapshot(ctx).items()
        if stable_id.startswith("SR-")
    }
    inventory = refinements.get("legacy_strategy_quality_meaning_inventory", {})
    migrations = inventory.get("meaning_migrations", {}) if isinstance(inventory, dict) else {}
    sr_inventory = {
        stable_id: value
        for stable_id, value in migrations.items()
        if isinstance(stable_id, str) and stable_id.startswith("SR-")
    }
    l0_policy = refinements.get("l0_north_star_authority_normalization_policy")
    test_policy = refinements.get("test_id_authority_alignment_policy")
    controls = refinements.get("captured_po_decision_controls", {})
    pod7 = controls.get("POD-20260815-007", {}) if isinstance(controls, dict) else {}
    facts7 = pod7.get("facts", {}) if isinstance(pod7, dict) else {}
    admission_record = next(
        (
            record
            for record in refinements.get("records", [])
            if isinstance(record, dict)
            and record.get("subject_id") == "STRATEGY-REQUIREMENT-ADMISSION"
        ),
        {},
    )
    axis_sources = {
        "research_growth": {"research_timing": facts7.get("research_timing"), "growth_feedback": facts7.get("growth_feedback")},
        "product_offer_authority": {"offer_mutation": facts7.get("offer_mutation")},
        "marketing_funnel": {"media_role_authority": facts7.get("media_role_authority"), "growth_feedback": facts7.get("growth_feedback")},
        "media_role": {"media_role_authority": facts7.get("media_role_authority")},
        "hypothesis_kpi_return": {"growth_feedback": facts7.get("growth_feedback")},
        "paid_acquisition_phase": {"paid_acquisition_phase": facts7.get("paid_acquisition_phase")},
        "content_risk_quality": {
            "pod4": controls.get("POD-20260815-004"),
            "pod6": controls.get("POD-20260815-006"),
        },
        "strategy_human_judgement": admission_record.get("semantic_dimensions", {}).get("human_judgement"),
    }
    expected_axis_bindings = {
        axis: {
            "source_refs": (
                ["RRF-STRATEGY-REQUIREMENT-ADMISSION"]
                if axis == "strategy_human_judgement"
                else (["POD-20260815-004", "POD-20260815-006"] if axis == "content_risk_quality" else ["POD-20260815-007"])
            ),
            "semantic_projection_digest": _digest(value),
        }
        for axis, value in sorted(axis_sources.items())
    }
    faults: list[str] = []
    if len(snapshot) != 19 or policy.get("sr_count") != 19:
        faults.append("strategy admissionがSR19件をexact被覆しない")
    if policy.get("sr_ids_digest") != _digest(sorted(snapshot)):
        faults.append("strategy admission SR ID digestが不一致")
    if policy.get("source_sr_snapshot_digest") != _digest(snapshot):
        faults.append("strategy admission source SR snapshotがstale")
    if set(sr_inventory) != set(snapshot) or policy.get("parent_meaning_inventory_digest") != _digest(sr_inventory):
        faults.append("strategy admissionが既存SR意味inventoryへ束縛されていない")
    if policy.get("l0_north_star_policy_digest") != _digest(l0_policy):
        faults.append("strategy admissionのL0 north-star parent digestがstale")
    if policy.get("test_authority_policy_digest") != _digest(test_policy):
        faults.append("strategy admissionのtest authority parent digestがstale")
    if policy.get("meaning_axis_bindings") != expected_axis_bindings:
        faults.append("strategy admissionの商品/offer/funnel/media role/仮説KPI/risk/HJ軸が欠落又はstale")
    state = policy.get("classification_state")
    if not isinstance(state, dict):
        return faults + ["strategy admission classification stateがない"]
    stage = state.get("status")
    l0_state = l0_policy.get("classification_state", {}) if isinstance(l0_policy, dict) else {}
    test_state = test_policy.get("classification_state", {}) if isinstance(test_policy, dict) else {}
    if stage == "pending_po_classification":
        if (
            policy.get("status") != "candidate_unratified"
            or state.get("selected_rows") != {}
            or state.get("classification_approval") is not None
            or state.get("candidate_artifact_binding") is not None
            or state.get("cutover_artifact_bindings") is not None
            or state.get("cutover_blocked") is not True
        ):
            faults.append("strategy admission未分類なのに選択・批准・cutover解除されている")
        return faults
    if stage not in {"classified_pending_cutover", "cutover_complete"}:
        return faults + ["strategy admission classification stageが不正"]
    if policy.get("status") != ("ratified" if stage == "cutover_complete" else "candidate_unratified"):
        faults.append("strategy admission stageとpolicy statusが不一致")
    if (
        inventory.get("status") != "classified"
        or inventory.get("cutover_blocked") is not False
        or legacy_strategy_quality_meaning_inventory_faults(ctx, refinements)
        or l0_state.get("status") != "cutover_complete"
        or l0_state.get("cutover_blocked") is not False
        or test_state.get("status") != "cutover_complete"
        or test_state.get("cutover_blocked") is not False
        or l0_north_star_authority_normalization_policy_faults(refinements)
        or test_id_authority_alignment_policy_faults(ctx, refinements)
    ):
        faults.append("strategy admission親inventory/L0/test authorityがclassified cutover completeでない")
    selected = state.get("selected_rows")
    if not isinstance(selected, dict) or set(selected) != set(snapshot):
        return faults + ["strategy admission selected rowsがSR19件をexact被覆しない"]
    known_l0 = set(_l0_candidate_clause_semantics(refinements.get("legacy_l0_clause_dispositions", [])))
    axis_bindings = policy.get("meaning_axis_bindings", {})
    known_fn = {str(item.get("id")) for item in ctx.fn}
    known_cmp = {str(item.get("id")) for item in ctx.cmpc}
    known_ac = {str(item.get("id")) for item in ctx.acc}
    known_subjects = {
        str(record.get("subject_id"))
        for record in refinements.get("records", [])
        if isinstance(record, dict)
    }
    row_fields = {
        "parent_meaning_digest", "source_sr_digest", "disposition", "l0_clause_refs",
        "l0_clause_semantic_digests", "meaning_axis_refs", "meaning_axis_digests",
        "human_judgement_authority", "descent_targets", "strategy_test_oracle_refs",
        "owner_subject_id", "rationale", "resume_conditions",
    }
    l0_semantics = _l0_candidate_clause_semantics(refinements.get("legacy_l0_clause_dispositions", []))
    for sr_id, row in selected.items():
        if not isinstance(row, dict) or set(row) != row_fields:
            faults.append(f"{sr_id}: strategy admission row field閉集合が不正")
            continue
        if row.get("parent_meaning_digest") != _digest(sr_inventory[sr_id]) or row.get("source_sr_digest") != _digest(snapshot[sr_id]):
            faults.append(f"{sr_id}: strategy parent/source digestがstale")
        disposition = row.get("disposition")
        if disposition not in {"initial_candidate", "later_candidate", "defer", "replace", "obsolete"}:
            faults.append(f"{sr_id}: strategy dispositionが不正")
        l0_refs = row.get("l0_clause_refs")
        l0_digests = row.get("l0_clause_semantic_digests")
        if not isinstance(l0_refs, list) or len(l0_refs) != len(set(l0_refs)) or not set(l0_refs) <= known_l0 or l0_digests != {ref: _digest(l0_semantics[ref]) for ref in l0_refs}:
            faults.append(f"{sr_id}: L0 clause meaning bindingが不正")
        axis_refs = row.get("meaning_axis_refs")
        axis_digests = row.get("meaning_axis_digests")
        if not isinstance(axis_refs, list) or len(axis_refs) != len(set(axis_refs)) or not set(axis_refs) <= set(axis_bindings) or axis_digests != {ref: axis_bindings[ref]["semantic_projection_digest"] for ref in axis_refs}:
            faults.append(f"{sr_id}: strategy意味軸bindingが不正")
        hj = row.get("human_judgement_authority")
        if not isinstance(hj, dict) or set(hj) != {"authority_subject_id", "receipt_required"} or hj.get("authority_subject_id") not in known_subjects or hj.get("receipt_required") is not True:
            faults.append(f"{sr_id}: strategy人間判断authorityが不正")
        targets = row.get("descent_targets")
        if not isinstance(targets, dict) or set(targets) != {"fn_ids", "cmp_ids", "ac_ids"}:
            faults.append(f"{sr_id}: strategy descent target shapeが不正")
            targets = {"fn_ids": [], "cmp_ids": [], "ac_ids": []}
        if not set(targets["fn_ids"]) <= known_fn or not set(targets["cmp_ids"]) <= known_cmp or not set(targets["ac_ids"]) <= known_ac:
            faults.append(f"{sr_id}: strategy descent targetが未知")
        oracle_refs = row.get("strategy_test_oracle_refs")
        if (
            not isinstance(oracle_refs, list)
            or not set(oracle_refs) <= known_ac
            or not set(oracle_refs) <= set(targets["ac_ids"])
        ):
            faults.append(f"{sr_id}: strategy test oracle参照が未知")
        if row.get("owner_subject_id") not in known_subjects or not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            faults.append(f"{sr_id}: strategy owner/rationaleが不正")
        resume = row.get("resume_conditions")
        if disposition in {"defer", "obsolete"}:
            if l0_refs or axis_refs or any(targets.values()) or oracle_refs or not isinstance(resume, list) or not resume:
                faults.append(f"{sr_id}: deferred/obsolete strategy field partitionが不正")
        elif not l0_refs or not axis_refs or not oracle_refs or not any(targets.values()) or resume != []:
            faults.append(f"{sr_id}: active strategy field partitionが不正")
    selected_digest = _digest(selected)
    approval = state.get("classification_approval")
    if (
        not isinstance(approval, dict)
        or approval.get("authority") != "PO"
        or approval.get("subject_id") != "STRATEGY-REQUIREMENT-ADMISSION"
        or approval.get("selected_rows_digest") != selected_digest
        or approval.get("source_sr_snapshot_digest") != _digest(snapshot)
        or approval.get("parent_meaning_inventory_digest") != _digest(sr_inventory)
        or approval.get("meaning_axis_bindings_digest") != _digest(axis_bindings)
    ):
        faults.append("strategy admission classification approvalがPO/source/meaning axis/row-setへ束縛されていない")
    manifest = load(MANIFEST)
    manifest_by_id = {str(item.get("artifact_id")): item for item in manifest.get("items", []) if isinstance(item, dict)}
    candidate = state.get("candidate_artifact_binding")
    candidate_item = manifest_by_id.get(str(candidate.get("artifact_id"))) if isinstance(candidate, dict) else None
    candidate_path = REPO_ROOT / str(candidate_item.get("canonical_path")) if isinstance(candidate_item, dict) else None
    candidate_in_repo = False
    if candidate_path is not None:
        try:
            candidate_path.resolve().relative_to(REPO_ROOT.resolve())
            candidate_in_repo = True
        except ValueError:
            candidate_in_repo = False
    candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest() if candidate_in_repo and candidate_path is not None and candidate_path.is_file() else None
    if (
        not isinstance(candidate, dict)
        or candidate.get("artifact_id") != "AUTH-DEVELOPMENT-STRATEGY-REQUIREMENT-ADMISSION-CANDIDATE"
        or candidate.get("content_digest") != candidate_digest
        or not isinstance(candidate_item, dict)
        or candidate_item.get("layer") != "L3-system-requirements"
        or candidate_item.get("artifact_type") != "strategy-requirement-admission-candidate"
        or candidate_item.get("authority_format") != "json"
        or candidate_item.get("authority_status") != "active"
        or not candidate_in_repo
        or candidate_item.get("implementation_input") is not (stage == "cutover_complete")
    ):
        faults.append("strategy admission candidate artifact identity/digest/input境界が不正")
    else:
        try:
            candidate_data = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else {}
        except (OSError, json.JSONDecodeError):
            candidate_data = {}
        if candidate_data.get("strategy_admission_row_digests") != {key: _digest(value) for key, value in selected.items()} or candidate_data.get("meaning_axis_bindings") != axis_bindings:
            faults.append("strategy admission candidate projectionがSR19 row/meaning axisと不一致")
        if not isinstance(approval, dict) or approval.get("candidate_content_digest") != candidate_digest:
            faults.append("strategy admission PO receiptがcandidate実内容へ束縛されていない")
    if stage == "classified_pending_cutover":
        if state.get("cutover_blocked") is not True or state.get("cutover_artifact_bindings") is not None:
            faults.append("strategy classified pendingがfail-closeでない")
    else:
        bindings = state.get("cutover_artifact_bindings")
        required_bindings = {
            "strategy_json_artifact_id", "strategy_json_digest", "descent_trace_artifact_id",
            "descent_trace_digest", "test_authority_artifact_id", "test_authority_digest",
            "manifest_digest", "baseline_digest", "target_commit", "target_tree", "same_commit",
            "trace_diff_count", "independent_go_artifact_id", "independent_go_digest",
        }
        if state.get("cutover_blocked") is not False or not isinstance(bindings, dict) or set(bindings) != required_bindings:
            faults.append("strategy cutover complete証跡がない又はfield閉集合が不正")
        elif (
            bindings.get("strategy_json_artifact_id") != (candidate or {}).get("artifact_id")
            or bindings.get("strategy_json_digest") != candidate_digest
            or bindings.get("same_commit") is not True
            or bindings.get("trace_diff_count") != 0
        ):
            faults.append("strategy cutover candidate/same-commit/trace境界が不正")
        else:
            artifact_paths: dict[str, Path] = {}
            for id_key, digest_key in (
                ("strategy_json_artifact_id", "strategy_json_digest"),
                ("descent_trace_artifact_id", "descent_trace_digest"),
                ("test_authority_artifact_id", "test_authority_digest"),
                ("independent_go_artifact_id", "independent_go_digest"),
            ):
                item = manifest_by_id.get(str(bindings.get(id_key)))
                path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
                actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path is not None and path.is_file() else None
                if path is not None:
                    artifact_paths[id_key] = path
                if actual != bindings.get(digest_key):
                    faults.append(f"strategy {id_key}がmanifest実artifactへ束縛されていない")
            trace_path = artifact_paths.get("descent_trace_artifact_id")
            try:
                trace_data = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path else {}
            except (OSError, json.JSONDecodeError):
                trace_data = {}
            expected_trace = {
                sr_id: {
                    "descent_targets": selected[sr_id]["descent_targets"],
                    "strategy_test_oracle_refs": selected[sr_id]["strategy_test_oracle_refs"],
                }
                for sr_id in sorted(selected)
            }
            if trace_data != {"strategy_descent_projection": expected_trace}:
                faults.append("strategy descent traceがSR19 rowのFN/CMP/AC/oracle exact projectionと不一致")
            test_owner = test_state.get("strategy_test_owner", {})
            if not isinstance(test_owner, dict) or bindings.get("test_authority_artifact_id") != test_owner.get("current_authority_artifact_id"):
                faults.append("strategy test authority artifactがTEST-IDの単一current ownerと不一致")
            test_authority_path = artifact_paths.get("test_authority_artifact_id")
            try:
                test_authority_data = json.loads(test_authority_path.read_text(encoding="utf-8")) if test_authority_path else {}
            except (OSError, json.JSONDecodeError):
                test_authority_data = {}
            authority_oracles = test_authority_data.get("ac_sr_oracles")
            authority_projection = test_authority_data.get("ac_sr_oracle_row_digests")
            for sr_id in sorted(selected):
                for ac_id in selected[sr_id]["strategy_test_oracle_refs"]:
                    selected_oracle = authority_oracles.get(ac_id) if isinstance(authority_oracles, dict) else None
                    if not isinstance(selected_oracle, dict):
                        faults.append(f"{sr_id}: strategy test authorityにoracle {ac_id}がない")
                        continue
                    source_disposition = selected_oracle.get("source_disposition")
                    oracle = selected_oracle.get("oracle")
                    target_ids: set[str] = set()
                    if isinstance(oracle, dict):
                        if isinstance(oracle.get("target_requirement_ids"), list):
                            target_ids = {str(value) for value in oracle["target_requirement_ids"]}
                        elif isinstance(oracle.get("target"), str):
                            target_ids = {oracle["target"]}
                    if (
                        source_disposition not in {"general_selected", "strategy_selected", "new_oracle"}
                        or sr_id not in target_ids
                        or not isinstance(authority_projection, dict)
                        or authority_projection.get(ac_id) != _digest(selected_oracle)
                    ):
                        faults.append(f"{sr_id}: {ac_id}のTEST-ID正準oracle帰属/digestが不一致")
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            for path, key in ((MANIFEST, "manifest_digest"), (baseline_path, "baseline_digest")):
                actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                if actual != bindings.get(key):
                    faults.append(f"strategy {key}が実fileと不一致")
            head = git("rev-parse", "HEAD").stdout.strip()
            tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
            if bindings.get("target_commit") != head or bindings.get("target_tree") != tree:
                faults.append("strategy cutoverが現HEAD/treeへ束縛されていない")
            for path in [MANIFEST, baseline_path, *artifact_paths.values()]:
                try:
                    relative = str(path.relative_to(REPO_ROOT))
                except ValueError:
                    faults.append("strategy cutover artifactがrepo外")
                    continue
                shown = git("show", f"HEAD:{relative}")
                if shown.returncode != 0 or hashlib.sha256(shown.stdout.encode()).hexdigest() != hashlib.sha256(path.read_bytes()).hexdigest():
                    faults.append(f"strategy {relative}がHEAD blobと不一致")
            review_path = artifact_paths.get("independent_go_artifact_id")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
            except (OSError, json.JSONDecodeError):
                review = {}
            reviewed = review.get("reviewed_artifact_digests", {})
            if (
                review.get("separation_status") != "ci_attested"
                or review.get("verdict") != "Go"
                or not isinstance(review.get("reviewer_principal"), str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po", review.get("author_principal")}
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(reviewed, dict)
                or any(bindings[key] not in reviewed.values() for key in ("strategy_json_digest", "descent_trace_digest", "test_authority_digest"))
            ):
                faults.append("strategy independent Goがcommit/tree/strategy/trace/test authorityを被覆しない")
    return faults


def _agent_neo_capability_source_inventory() -> dict[str, dict[str, str]]:
    """RDE-000099に記録した観測能力と旧任意判断の閉集合。"""
    fixed = {
        "site_identity": "site/profile identity and boundary",
        "fse_styles": "FSE global styles, design tokens, theme settings",
        "templates_navigation": "templates, template parts, navigation",
        "patterns_blocks_media": "patterns, blocks, sections, CTA, media",
        "content_crud": "page, post, taxonomy, menu stable-ID CRUD",
        "preview_apply_rollback": "preview, dry-run, diff, apply, version, rollback",
        "seo": "SEO metadata, schema, OGP, indexing",
        "measurement": "consented measurement, tracking, export",
        "migration": "migration, import, export",
        "quality_security": "accessibility, performance, i18n, privacy, security",
        "health_audit": "health, status, log, audit",
        "harness_neo_integration_boundary": "HARNESS decision and AGENT NEO deterministic execution boundary",
    }
    optional = {
        "package": "legacy package decision",
        "license": "legacy license and cost decision",
        "automation_seo": "legacy Automation SEO decision",
        "crm": "legacy CRM decision",
        "sns": "legacy SNS decision",
        "external_api": "legacy external API decision",
        "ai": "legacy AI-in-theme/plugin decision",
    }
    source_ref = "source:github:RetryYN/AGENT-NEO@9f5d679c0befce093ba077fcf11d514e4c75f17a"
    inventory: dict[str, dict[str, str]] = {}
    for stable_id, clause in {**fixed, **optional}.items():
        row = {
            "source_kind": "fixed_capability" if stable_id in fixed else "legacy_optional_decision",
            "source_event_id": "RDE-000099",
            "source_ref": source_ref,
            "source_clause": clause,
        }
        inventory[stable_id] = {**row, "source_digest": _digest(row)}
    return inventory


def _agent_neo_capability_classification_candidates() -> dict[str, Any]:
    """PO選択前のID別処遇候補。候補列挙は採用決定を意味しない。"""
    inventory = _agent_neo_capability_source_inventory()
    site_build = {
        "site_identity", "fse_styles", "templates_navigation", "patterns_blocks_media",
        "content_crud", "preview_apply_rollback", "seo", "measurement", "migration",
    }
    evolution = {"quality_security", "health_audit", "harness_neo_integration_boundary"}
    defaults = {
        "repo_authority": "helix_read_only",
        "prohibited_inheritance": [
            "legacy_g4_or_s3_acceptance", "wordpress_success_as_agent_neo_admission",
            "shared_credential_or_review_authority", "external_repo_write_without_separate_authorization",
        ],
        "owner_subject_id": "AGENT-NEO-HELIX-REDEFINITION",
        "rationale": "PO分類前の候補。固定source観測をpermission又はrelease admissionへ読み替えない",
        "resume_conditions": [
            "PO capability classification receipt", "release owner and effect closure",
            "target repository commit and independent review evidence",
        ],
    }
    rows: dict[str, dict[str, Any]] = {}
    for stable_id, source in inventory.items():
        optional = source["source_kind"] == "legacy_optional_decision"
        owners = (
            ["none", "site_build", "product_evolution"]
            if optional
            else (["site_build", "product_evolution"] if stable_id in site_build | evolution else ["none"])
        )
        effects = {
            "site_identity": ["read", "state_write"],
            "content_crud": ["read", "external_write", "publish"],
            "preview_apply_rollback": ["read", "external_write", "release"],
            "measurement": ["read"],
            "migration": ["read", "external_write", "release"],
            "quality_security": ["read", "external_write", "credential", "release"],
            "health_audit": ["read"],
            "harness_neo_integration_boundary": ["read", "state_write"],
        }.get(stable_id, ["read", "external_write"])
        rows[stable_id] = {
            "source_capability_digest": source["source_digest"],
            "candidate_dispositions": ["defer", "obsolete", "replace"] if optional else ["candidate", "defer", "replace"],
            "candidate_release_owners": owners,
            "allowed_effect_candidates": effects,
            "additional_prohibited_inheritance": ["legacy_optional_capability_auto_adoption"] if optional else [],
        }
    effective_row_digests = {
        stable_id: _digest({**defaults, **row}) for stable_id, row in rows.items()
    }
    selected_row_contract = {
        "active": {
            "dispositions": ["candidate", "replace"],
            "required": ["release_owner", "allowed_effects", "separate_authorization_dependency_ids"],
            "prohibited": ["defer_resume_conditions", "obsolete_reason"],
            "value_invariants": {
                "release_owner": "one_of_row_candidates_except_none",
                "allowed_effects": "nonempty_subset_of_row_candidates",
                "high_effect_dependency": "exact_required_dependency_when_any_high_effect",
                "read_only_dependency": "empty_allowed",
            },
        },
        "defer": {
            "dispositions": ["defer"],
            "required": ["release_owner", "defer_resume_conditions"],
            "fixed": {"release_owner": "none", "allowed_effects": [], "separate_authorization_dependency_ids": []},
            "prohibited": ["obsolete_reason"],
        },
        "obsolete": {
            "dispositions": ["obsolete"],
            "required": ["release_owner", "obsolete_reason"],
            "fixed": {"release_owner": "none", "allowed_effects": [], "separate_authorization_dependency_ids": []},
            "prohibited": ["defer_resume_conditions"],
        },
        "high_effect_dependency_rule": {
            "effects": ["external_write", "publish", "credential", "release"],
            "required_dependency": "separate_repo_authorization_commit_review_go",
        },
        "optional_positive_retain": "prohibited",
    }
    return {
        "defaults": defaults,
        "rows": rows,
        "effective_row_digests": effective_row_digests,
        "selected_row_contract": selected_row_contract,
    }


def agent_neo_helix_redefinition_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """AGENT NEO固定sourceをread-only能力候補として隔離する。"""
    faults: list[str] = []
    policy = refinements.get("agent_neo_helix_redefinition_policy")
    if not isinstance(policy, dict):
        return ["AGENT NEO redefinition policyがない"]
    discovery = requirement_discovery.load_discovery_ledger()
    event = next(
        (row for row in discovery.get("events", []) if row.get("event_id") == "RDE-000099"),
        None,
    )
    record = next(
        (
            row
            for row in refinements.get("records", [])
            if row.get("subject_id") == "AGENT-NEO-HELIX-REDEFINITION"
        ),
        None,
    )
    inventory = _agent_neo_capability_source_inventory()
    candidates = _agent_neo_capability_classification_candidates()
    source_ref = "source:github:RetryYN/AGENT-NEO@9f5d679c0befce093ba077fcf11d514e4c75f17a"
    if (
        policy.get("source_event_id") != "RDE-000099"
        or policy.get("source_event_digest") != _digest(event)
        or policy.get("source_ref") != source_ref
        or policy.get("refinement_record_digest") != _digest(record)
        or policy.get("capability_count") != 19
        or policy.get("capability_inventory_digest") != _digest(inventory)
        or policy.get("capability_classification_candidates") != candidates
        or policy.get("capability_classification_candidates_digest") != _digest(candidates)
    ):
        faults.append("AGENT NEO captured-observation inventoryがRDE/refinementへexact束縛されていない")
    if not isinstance(record, dict) or record.get("pending_resolution") != [
        "旧package／license／Automation SEO／CRM／SNS／外部API／AI機能の採用・deferred・廃止を個別に決める"
    ]:
        faults.append("AGENT NEOの解決済みrepo境界がPO質問へ再混入又はcapability採否質問が欠落")
    expected_parents = {
        key: _digest(refinements.get(key))
        for key in (
            "business_profile_authorization_policy",
            "l0_north_star_authority_normalization_policy",
            "nfr_business_authority_policy",
            "req_authority_normalization_policy",
            "wordpress_content_operations_policy",
            "wordpress_platform_maintenance_policy",
            "wordpress_security_maintenance_policy",
        )
    }
    if policy.get("parent_policy_digests") != expected_parents:
        faults.append("AGENT NEO parent authority policy digestがstale又は欠落")
    expected_meaning = {
        key: refinements.get(key, {}).get("meaning_migrations_digest")
        for key in ("legacy_requirement_meaning_inventory", "legacy_strategy_quality_meaning_inventory")
    }
    if policy.get("parent_meaning_inventory_digests") != expected_meaning:
        faults.append("AGENT NEO legacy meaning inventory digestがstale又は欠落")
    expected_repo = {
        "current_repo": "HELIX-MARKETING-HARNESS",
        "current_repo_allowed_effects": ["requirements_authority", "integration_contract", "evidence_reference"],
        "external_repo": "RetryYN/AGENT-NEO",
        "external_repo_access": "read_only",
        "external_repo_write_current_scope": "prohibited",
        "future_change_contract": "separate_authorization_commit_review_go",
        "prohibited_admission_evidence": ["legacy_g4_pass", "legacy_s3_green", "wordpress_operation_success", "other_site_success"],
        "credential_authority_sharing": "prohibited",
        "review_authority_sharing": "prohibited",
    }
    if policy.get("repo_authority_contract") != expected_repo:
        faults.append("AGENT NEO repo read-only／旧成功非流用／authority分離境界が反転")
    expected_authority_semantics = _digest({
        "source_event_digest": _digest(event),
        "refinement_record_digest": _digest(record),
        "capability_inventory_digest": _digest(inventory),
        "candidate_rows_digest": _digest(candidates),
        "parent_policy_digests": expected_parents,
        "parent_meaning_inventory_digests": expected_meaning,
        "repo_authority_contract": expected_repo,
    })
    if policy.get("authority_semantic_digest") != expected_authority_semantics:
        faults.append("AGENT NEO authority semantic aggregateがsource/parent/repo境界へ束縛されていない")
    state = policy.get("classification_state", {})
    stage = state.get("status") if isinstance(state, dict) else None
    pending_state: dict[str, Any] = {
        "status": "pending_po_classification",
        "selected_rows": {},
        "classification_approval": None,
        "candidate_artifact_binding": None,
        "cutover_artifact_bindings": None,
        "cutover_blocked": True,
    }
    if stage == "pending_po_classification" and state != pending_state:
        faults.append("AGENT NEO capabilityはPO未分類なのに選択・cutoverされた")
    elif stage in {"classified_pending_cutover", "cutover_complete"}:
        selected = state.get("selected_rows", {})
        candidate_rows = candidates["rows"]
        high_effects = set(candidates["selected_row_contract"]["high_effect_dependency_rule"]["effects"])
        required_dependency = candidates["selected_row_contract"]["high_effect_dependency_rule"]["required_dependency"]
        complete = stage == "cutover_complete"
        if policy.get("status") != ("ratified" if complete else "candidate_unratified") or state.get("cutover_blocked") is not (not complete):
            faults.append("AGENT NEO stage/status/cutover blockedの組合せが不正")
        if not isinstance(selected, dict) or set(selected) != set(candidate_rows):
            faults.append("AGENT NEO classified rowsが19 capability exact集合でない")
        else:
            for stable_id, row in selected.items():
                source = candidate_rows[stable_id]
                if not isinstance(row, dict) or row.get("effective_candidate_row_digest") != candidates["effective_row_digests"][stable_id]:
                    faults.append(f"AGENT NEO {stable_id}: effective candidate digest不一致")
                    continue
                disposition = row.get("disposition")
                owner = row.get("release_owner")
                effects = row.get("allowed_effects")
                dependencies = row.get("separate_authorization_dependency_ids")
                if disposition not in source["candidate_dispositions"]:
                    faults.append(f"AGENT NEO {stable_id}: dispositionが候補外")
                elif disposition in {"candidate", "replace"}:
                    if owner == "none" or owner not in source["candidate_release_owners"]:
                        faults.append(f"AGENT NEO {stable_id}: active release owner不正")
                    if not isinstance(effects, list) or not effects or not set(effects) <= set(source["allowed_effect_candidates"]):
                        faults.append(f"AGENT NEO {stable_id}: active effectが候補の非空部分集合でない")
                    expected_deps = [required_dependency] if set(effects or []) & high_effects else []
                    if dependencies != expected_deps:
                        faults.append(f"AGENT NEO {stable_id}: high-effect別repo authorization dependency不正")
                    if row.get("defer_resume_conditions") is not None or row.get("obsolete_reason") is not None:
                        faults.append(f"AGENT NEO {stable_id}: active rowへdefer/obsolete field混入")
                elif disposition == "defer":
                    if owner != "none" or effects != [] or dependencies != [] or not row.get("defer_resume_conditions") or row.get("obsolete_reason") is not None:
                        faults.append(f"AGENT NEO {stable_id}: defer partition不正")
                elif disposition == "obsolete":
                    if owner != "none" or effects != [] or dependencies != [] or not row.get("obsolete_reason") or row.get("defer_resume_conditions") is not None:
                        faults.append(f"AGENT NEO {stable_id}: obsolete partition不正")
        approval = state.get("classification_approval")
        selected_digest = _digest(selected)
        if not isinstance(approval, dict) or approval != {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "capability_inventory_digest": _digest(inventory),
            "candidate_rows_digest": _digest(candidates),
            "selected_rows_digest": selected_digest,
            "authority_semantic_digest": expected_authority_semantics,
        }:
            faults.append("AGENT NEO PO classification receiptがinventory/candidate/selected rowsへ束縛されていない")
        binding = state.get("candidate_artifact_binding")
        candidate_id = "AUTH-DEVELOPMENT-AGENT-NEO-REDEFINITION-CANDIDATE"
        manifest = load(MANIFEST)
        manifest_item = next(
            (item for item in manifest.get("items", []) if item.get("artifact_id") == candidate_id),
            None,
        )
        candidate_data: dict[str, Any] = {}
        candidate_digest = ""
        candidate_path: Path | None = None
        if isinstance(manifest_item, dict):
            try:
                canonical_path = Path(str(manifest_item.get("canonical_path")))
                if canonical_path.is_absolute():
                    raise ValueError("absolute canonical path")
                candidate_path = (REPO_ROOT / canonical_path).resolve()
                candidate_path.relative_to(REPO_ROOT.resolve())
                candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
                candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
            except (OSError, ValueError, json.JSONDecodeError):
                candidate_data = {}
        if (
            not isinstance(binding, dict)
            or binding.get("artifact_id") != candidate_id
            or binding.get("implementation_input") is not complete
            or binding.get("selected_rows_digest") != selected_digest
            or binding.get("content_digest") != candidate_digest
            or not isinstance(manifest_item, dict)
            or manifest_item.get("layer") != "00-authority"
            or manifest_item.get("artifact_type") != "requirement-authority-candidate"
            or manifest_item.get("authority_format") != "json"
            or manifest_item.get("authority_status") != "active"
            or manifest_item.get("implementation_input") is not complete
            or candidate_data != {
                "authority_semantic_digest": expected_authority_semantics,
                "selected_rows_digest": selected_digest,
                "selected_rows": selected,
            }
        ):
            faults.append("AGENT NEO classified candidate artifactが専用ID・非実装入力・selected rowsへ束縛されていない")
        if not complete and state.get("cutover_artifact_bindings") is not None:
            faults.append("AGENT NEO classified pendingにcutover artifactが混入")
        if complete:
            cutover = state.get("cutover_artifact_bindings")
            try:
                head_result = git("rev-parse", "HEAD")
                tree_result = git("rev-parse", "HEAD^{tree}")
                head = head_result.stdout.strip() if head_result.returncode == 0 else ""
                tree = tree_result.stdout.strip() if tree_result.returncode == 0 else ""
            except OSError:
                head = tree = ""
            manifest_digest = "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            baseline_digest = "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest() if baseline_path.is_file() else ""
            captured_source_observation = {
                "repository": "RetryYN/AGENT-NEO",
                "source_commit": "9f5d679c0befce093ba077fcf11d514e4c75f17a",
                "access": "read_only",
                "capability_inventory_digest": _digest(inventory),
                "external_write_authorized": False,
            }
            expected_cutover = {
                "target_commit": head,
                "target_tree": tree,
                "candidate_content_digest": candidate_digest,
                "manifest_digest": manifest_digest,
                "baseline_digest": baseline_digest,
                "captured_source_observation_binding": captured_source_observation,
                "independent_go_artifact_id": "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO",
            }
            if not isinstance(cutover, dict) or any(cutover.get(key) != value for key, value in expected_cutover.items()):
                faults.append("AGENT NEO cutoverがcommit/tree/candidate/manifest/baseline/external sourceへ束縛されていない")
            review_digest = cutover.get("independent_go_digest") if isinstance(cutover, dict) else None
            review_item = next(
                (item for item in manifest.get("items", []) if item.get("artifact_id") == "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO"),
                None,
            )
            review_path: Path | None = None
            try:
                if not isinstance(review_item, dict) or review_item.get("artifact_type") != "review" or review_item.get("authority_status") != "active":
                    raise ValueError("review manifest item")
                review_rel = Path(str(review_item.get("canonical_path")))
                if review_rel.is_absolute():
                    raise ValueError("absolute review path")
                review_path = (REPO_ROOT / review_rel).resolve()
                review_path.relative_to(REPO_ROOT.resolve())
                review = json.loads(review_path.read_text(encoding="utf-8"))
                actual_review_digest = "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
            except (OSError, ValueError, json.JSONDecodeError):
                review = {}
                actual_review_digest = ""
            reviewed = review.get("reviewed_artifact_digests", {}) if isinstance(review, dict) else {}
            head_blob_mismatch = False
            for artifact_path in (candidate_path, MANIFEST, baseline_path, review_path):
                if not isinstance(artifact_path, Path):
                    head_blob_mismatch = True
                    continue
                try:
                    relative = artifact_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
                    blob = git("show", f"HEAD:{relative}")
                    if blob.returncode != 0 or blob.stdout.encode() != artifact_path.read_bytes():
                        head_blob_mismatch = True
                except (OSError, ValueError):
                    head_blob_mismatch = True
            if (
                review_digest != actual_review_digest
                or not isinstance(review_item, dict)
                or cutover.get("independent_go_path") != review_item.get("canonical_path")
                or review.get("review_id") != "AUTH-REVIEW-AGENT-NEO-REDEFINITION-GO"
                or review.get("verdict") != "Go"
                or review.get("separation_status") != "ci_attested"
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(review.get("reviewer_principal"), str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po", review.get("author_principal")}
                or reviewed != {"candidate": candidate_digest, "manifest": manifest_digest, "baseline": baseline_digest}
                or head_blob_mismatch
            ):
                faults.append("AGENT NEO independent Goが主体分離・commit/tree・HEAD blob・artifact集合を被覆しない")
    elif stage != "pending_po_classification":
        faults.append("AGENT NEO classification stageが不明")
    return faults


def agent_neo_site_build_release_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """Site-buildを親capability分類とWP責務authorityへ従属させる。"""
    faults: list[str] = []
    policy = refinements.get("agent_neo_site_build_release_policy")
    if not isinstance(policy, dict):
        return ["AGENT NEO site-build release policyがない"]
    discovery = requirement_discovery.load_discovery_ledger()
    events = {
        row.get("event_id"): row
        for row in discovery.get("events", [])
        if row.get("event_id") in {"RDE-000120", "RDE-000121"}
    }
    record = next((row for row in refinements.get("records", []) if row.get("subject_id") == "AGENT-NEO-SITE-BUILD-RELEASE"), None)
    parent_keys = (
        "agent_neo_helix_redefinition_policy", "business_profile_authorization_policy",
        "product_state_authority_policy", "wordpress_content_operations_policy",
        "wordpress_platform_maintenance_policy", "wordpress_security_maintenance_policy",
    )
    expected_parents = {key: _digest(refinements.get(key)) for key in parent_keys}
    parent = refinements.get("agent_neo_helix_redefinition_policy", {})
    parent_state = parent.get("classification_state", {}) if isinstance(parent, dict) else {}
    parent_selected = parent_state.get("selected_rows", {}) if isinstance(parent_state, dict) else {}
    expected_projection = {
        stable_id: {
            "effective_candidate_row_digest": row.get("effective_candidate_row_digest"),
            "disposition": row.get("disposition"),
            "allowed_effects": row.get("allowed_effects"),
        }
        for stable_id, row in parent_selected.items()
        if isinstance(row, dict)
        and row.get("disposition") in {"candidate", "replace"}
        and row.get("release_owner") == "site_build"
    }
    if policy.get("source_event_digests") != {key: _digest(events.get(key)) for key in ("RDE-000120", "RDE-000121")} or policy.get("refinement_record_digest") != _digest(record):
        faults.append("AGENT NEO site-build source events/refinement digest不一致")
    if policy.get("parent_policy_digests") != expected_parents:
        faults.append("AGENT NEO site-build parent authority digestがstale又は欠落")
    if policy.get("eligible_parent_capability_projection") != expected_projection:
        faults.append("AGENT NEO site-build capabilityが親selected site_build集合と不一致")
    expected_responsibility = {
        "families": ["content", "platform", "security", "read_only_evidence"],
        "agent_neo_repo_effect": "read_only",
        "target_site_effects": ["read", "state_write", "external_write", "publish", "release"],
        "content_parent": "wordpress_content_operations_policy",
        "platform_parent": "wordpress_platform_maintenance_policy",
        "security_parent": "wordpress_security_maintenance_policy",
        "cross_family_authority_inference": "prohibited",
        "product_evolution_authority_reuse": "prohibited",
        "legacy_success_admission": "prohibited",
    }
    expected_attempt = ["target_site_id", "profile_id", "account_id", "capability_id", "operation", "effect", "source_revision", "current_revision", "desired_revision_digest", "capability_set_digest", "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest", "authorization_scope_digest", "activation_scope_id", "activation_scope_revision", "activation_scope_semantic_digest", "operation_effect_scope_digest", "preflight_receipt", "preview_diff_evidence", "result_receipt", "rollback_recovery_evidence"]
    id_fields = {"target_site_id":"site_registration","profile_id":"business_profile_authorization","account_id":"account_registration","capability_id":"agent_neo_parent_projection","authorization_grant_id":"business_profile_authorization","activation_scope_id":"automated_publishing_admission"}
    operation_fields = {"operation":"site_build_operation_registry","effect":"business_profile_authorization"}
    revision_fields = {"source_revision":"source_state","current_revision":"product_state_authority","authorization_grant_revision":"business_profile_authorization","activation_scope_revision":"automated_publishing_admission"}
    digest_fields = {"desired_revision_digest":"site_build_intent","capability_set_digest":"agent_neo_parent_projection","authorization_grant_semantic_digest":"business_profile_authorization","authorization_scope_digest":"business_profile_authorization","activation_scope_semantic_digest":"automated_publishing_admission","operation_effect_scope_digest":"business_profile_authorization"}
    evidence_fields = {"preflight_receipt":"site_build_preflight","preview_diff_evidence":"site_build_preview","result_receipt":"product_state_authority","rollback_recovery_evidence":"site_build_recovery"}
    expected_field_contracts = {
        **{key:{"type":"stable_id","authority":source,"source":"registration"} for key,source in id_fields.items()},
        **{key:{"type":"closed_operation_or_effect","authority":source,"source":"registration_or_authority_receipt"} for key,source in operation_fields.items()},
        **{key:{"type":"positive_revision","authority":source,"source":"registration_or_authority_receipt"} for key,source in revision_fields.items()},
        **{key:{"type":"sha256_digest","authority":source,"source":"authority_receipt"} for key,source in digest_fields.items()},
        **{key:{"type":"receipt_digest","authority":source,"source":"release_attempt_evidence"} for key,source in evidence_fields.items()},
    }
    responsibility_by_capability = {"site_identity":"platform","fse_styles":"platform","templates_navigation":"platform","patterns_blocks_media":"content","content_crud":"content","preview_apply_rollback":"platform","seo":"content","measurement":"read_only_evidence","migration":"platform","quality_security":"security","health_audit":"read_only_evidence","harness_neo_integration_boundary":"read_only_evidence"}
    binding_dimensions = ["target_site_id","profile_id","account_id","capability_id","operation","effect","authorization_grant_id","authorization_grant_revision","authorization_grant_semantic_digest","authorization_scope_digest","activation_scope_id","activation_scope_revision","activation_scope_semantic_digest","operation_effect_scope_digest"]
    expected_overlay_contract = {"responsibility_by_capability":responsibility_by_capability,"release_dispositions":["candidate","defer"],"active_owner_subject_id":"AGENT-NEO-SITE-BUILD-RELEASE","required_binding_dimensions":binding_dimensions,"write_effects_requiring_grant":["state_write","external_write","publish","release"],"agent_neo_repo_effect":"read_only"}
    expected_authority_semantics = _digest({"source_event_digests":{key:_digest(events.get(key)) for key in ("RDE-000120","RDE-000121")},"refinement_record_digest":_digest(record),"parent_policy_digests":expected_parents,"eligible_parent_capability_projection":expected_projection,"responsibility_contract":expected_responsibility,"capability_overlay_contract":expected_overlay_contract,"release_attempt_contract":expected_attempt,"release_attempt_field_contracts":expected_field_contracts})
    if policy.get("authority_semantic_digest") != expected_authority_semantics:
        faults.append("site-build authority semantic digestがsource/parents/contractsへ束縛されていない")
    if policy.get("responsibility_contract") != expected_responsibility or policy.get("capability_overlay_contract") != expected_overlay_contract or policy.get("release_attempt_contract") != expected_attempt or policy.get("release_attempt_field_contracts") != expected_field_contracts:
        faults.append("AGENT NEO repo read-only／target site作用／WP三責務／release attempt境界が反転")
    actual_dimensions = policy.get("capability_overlay_contract", {}).get(
        "required_binding_dimensions", []
    )
    actual_attempt = policy.get("release_attempt_contract", [])
    if not (
        isinstance(actual_dimensions, list)
        and isinstance(actual_attempt, list)
        and set(actual_dimensions) <= set(actual_attempt)
    ):
        faults.append("site-build capability binding dimensionsがrelease attempt実fieldに閉じていない")
    parent_ready = parent_state.get("status") in {"classified_pending_cutover", "cutover_complete"}
    state = policy.get("classification_state", {})
    expected_state: dict[str, Any] = {"status":"pending_po_classification" if parent_ready else "blocked_by_parent_classification","selected_rows":{},"classification_approval":None,"candidate_artifact_binding":None,"cutover_artifact_bindings":None,"cutover_blocked":True}
    if not parent_ready or state.get("status") == "pending_po_classification":
        if policy.get("status") != "candidate_unratified" or state != expected_state:
            faults.append("親AGENT NEO状態に対応しないsite-build選択又は早期cutover")
    elif state.get("status") in {"classified_pending_cutover", "cutover_complete"}:
        complete = state.get("status") == "cutover_complete"
        if agent_neo_helix_redefinition_policy_faults(refinements):
            faults.append("site-build classified parent AGENT NEO policy gateが閉じていない")
        if complete and parent_state.get("status") != "cutover_complete":
            faults.append("site-build cutoverは親AGENT NEO cutover完了前に実行できない")
        selected = state.get("selected_rows", {})
        if policy.get("status") != ("ratified" if complete else "candidate_unratified") or state.get("cutover_blocked") is not (not complete) or set(selected) != set(expected_projection):
            faults.append("site-build classified rowsが親eligible capability exact集合でない")
        else:
            for stable_id, row in selected.items():
                parent_row = expected_projection[stable_id]
                expected_row_keys = {"parent_row_digest","responsibility_family","allowed_site_effects","required_grant_effects","required_binding_dimensions","release_disposition","owner_subject_id","rationale","resume_conditions"}
                disposition = row.get("release_disposition")
                effects = row.get("allowed_site_effects")
                grant_effects = row.get("required_grant_effects")
                if set(row) != expected_row_keys or not isinstance(row.get("rationale"), str) or not row.get("rationale") or row.get("parent_row_digest") != _digest(parent_row) or row.get("responsibility_family") != responsibility_by_capability.get(stable_id) or row.get("required_binding_dimensions") != binding_dimensions:
                    faults.append(f"site-build {stable_id}: parent/responsibility/binding不一致")
                if disposition == "candidate":
                    if row.get("owner_subject_id") != "AGENT-NEO-SITE-BUILD-RELEASE" or not isinstance(effects, list) or not effects or not set(effects) <= set(parent_row.get("allowed_effects") or []):
                        faults.append(f"site-build {stable_id}: active owner/effect不正")
                    expected_grants = sorted(set(effects or []) & {"state_write","external_write","publish","release"})
                    if grant_effects != expected_grants or row.get("resume_conditions") != []:
                        faults.append(f"site-build {stable_id}: grant effect/resume partition不正")
                elif disposition == "defer":
                    if effects != [] or grant_effects != [] or row.get("owner_subject_id") != "AGENT-NEO-SITE-BUILD-RELEASE" or not row.get("resume_conditions"):
                        faults.append(f"site-build {stable_id}: defer partition不正")
                else:
                    faults.append(f"site-build {stable_id}: release disposition不正")
        selected_digest = _digest(selected)
        approval = state.get("classification_approval")
        if approval != {"authority":"PO","approver_principal":"po","approved_revision":1,"parent_projection_digest":_digest(expected_projection),"selected_rows_digest":selected_digest,"parent_policy_digest":_digest(parent),"authority_semantic_digest":expected_authority_semantics}:
            faults.append("site-build PO classification receiptが親projection/selected rowsへ束縛されていない")
        binding = state.get("candidate_artifact_binding")
        candidate_id = "AUTH-DEVELOPMENT-AGENT-NEO-SITE-BUILD-CANDIDATE"
        manifest = load(MANIFEST)
        item = next((x for x in manifest.get("items",[]) if x.get("artifact_id")==candidate_id),None)
        data: dict[str,Any] = {}
        content_digest = ""
        candidate_path: Path | None = None
        try:
            if not isinstance(item,dict) or item.get("layer")!="00-authority" or item.get("artifact_type")!="requirement-authority-candidate" or item.get("authority_format")!="json" or item.get("authority_status")!="active" or item.get("implementation_input") is not complete:
                raise ValueError("candidate manifest")
            rel = Path(str(item.get("canonical_path")))
            if rel.is_absolute():
                raise ValueError("absolute")
            candidate_path = (REPO_ROOT / rel).resolve()
            candidate_path.relative_to(REPO_ROOT.resolve())
            data = json.loads(candidate_path.read_text(encoding="utf-8"))
            content_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        except (OSError, ValueError, json.JSONDecodeError):
            data = {}
        expected_data={"authority_semantic_digest":expected_authority_semantics,"selected_rows_digest":selected_digest,"selected_rows":selected,"release_attempt_field_contracts":expected_field_contracts}
        if not isinstance(binding,dict) or binding!={"artifact_id":candidate_id,"implementation_input":complete,"selected_rows_digest":selected_digest,"content_digest":content_digest} or data!=expected_data:
            faults.append("site-build classified candidate境界が不正")
        if not complete and state.get("cutover_artifact_bindings") is not None:
            faults.append("site-build classified pendingにcutover artifactが混入")
        if complete:
            cutover = state.get("cutover_artifact_bindings")
            try:
                head_result = git("rev-parse", "HEAD")
                tree_result = git("rev-parse", "HEAD^{tree}")
                head = head_result.stdout.strip() if head_result.returncode == 0 else ""
                tree = tree_result.stdout.strip() if tree_result.returncode == 0 else ""
            except OSError:
                head = tree = ""
            manifest_digest = "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            baseline_digest = "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest() if baseline_path.is_file() else ""
            expected_cutover = {
                "target_commit": head,
                "target_tree": tree,
                "candidate_content_digest": content_digest,
                "manifest_digest": manifest_digest,
                "baseline_digest": baseline_digest,
                "parent_policy_digest": _digest(parent),
                "parent_cutover_status": "cutover_complete",
                "agent_neo_external_repo_access": "read_only",
                "independent_go_artifact_id": "AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO",
            }
            if not isinstance(cutover, dict) or any(cutover.get(key) != value for key,value in expected_cutover.items()):
                faults.append("site-build cutoverが親・commit/tree・candidate・manifest・baselineへ束縛されていない")
            review_item = next((x for x in manifest.get("items",[]) if x.get("artifact_id")=="AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO"),None)
            review_path: Path | None = None
            try:
                if not isinstance(review_item,dict) or review_item.get("artifact_type")!="review" or review_item.get("authority_status")!="active":
                    raise ValueError("review manifest")
                review_rel = Path(str(review_item.get("canonical_path")))
                if review_rel.is_absolute():
                    raise ValueError("absolute review")
                review_path = (REPO_ROOT / review_rel).resolve()
                review_path.relative_to(REPO_ROOT.resolve())
                review = json.loads(review_path.read_text(encoding="utf-8"))
                actual_review_digest = "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest()
            except (OSError,ValueError,json.JSONDecodeError):
                review = {}
                actual_review_digest = ""
            reviewed = review.get("reviewed_artifact_digests",{}) if isinstance(review,dict) else {}
            head_blob_mismatch = False
            for artifact_path in (candidate_path, MANIFEST, baseline_path, review_path):
                if not isinstance(artifact_path,Path):
                    head_blob_mismatch = True
                    continue
                try:
                    relative = artifact_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
                    blob = git("show",f"HEAD:{relative}")
                    if blob.returncode != 0 or blob.stdout.encode() != artifact_path.read_bytes():
                        head_blob_mismatch = True
                except (OSError,ValueError):
                    head_blob_mismatch = True
            if (
                not isinstance(cutover,dict)
                or cutover.get("independent_go_path") != (review_item.get("canonical_path") if isinstance(review_item,dict) else None)
                or cutover.get("independent_go_digest") != actual_review_digest
                or review.get("review_id") != "AUTH-REVIEW-AGENT-NEO-SITE-BUILD-GO"
                or review.get("verdict") != "Go"
                or review.get("separation_status") != "ci_attested"
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(review.get("reviewer_principal"),str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po",review.get("author_principal")}
                or reviewed != {"candidate":content_digest,"manifest":manifest_digest,"baseline":baseline_digest,"parent_policy":_digest(parent)}
                or head_blob_mismatch
            ):
                faults.append("site-build independent Goが主体分離・親・commit/tree・HEAD blob・artifact集合を被覆しない")
    else:
        faults.append("site-build classification stageが不明")
    return faults


def agent_neo_product_evolution_release_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """製品進化要求と外部AGENT NEO repo write authorityを分離する。"""
    policy = refinements.get("agent_neo_product_evolution_release_policy")
    if not isinstance(policy, dict):
        return ["AGENT NEO product-evolution release policyがない"]
    faults: list[str] = []
    discovery = requirement_discovery.load_discovery_ledger()
    events = {row.get("event_id"):row for row in discovery.get("events",[]) if row.get("event_id") in {"RDE-000122","RDE-000123"}}
    record = next((row for row in refinements.get("records",[]) if row.get("subject_id")=="AGENT-NEO-PRODUCT-EVOLUTION-RELEASE"),None)
    parent_keys = (
        "agent_neo_helix_redefinition_policy","agent_neo_site_build_release_policy",
        "business_profile_authorization_policy","product_state_authority_policy",
        "wordpress_content_operations_policy","wordpress_platform_maintenance_policy",
        "wordpress_security_maintenance_policy",
    )
    expected_parents = {key:_digest(refinements.get(key)) for key in parent_keys}
    parent = refinements.get("agent_neo_helix_redefinition_policy",{})
    parent_state = parent.get("classification_state",{}) if isinstance(parent,dict) else {}
    parent_selected = parent_state.get("selected_rows",{}) if isinstance(parent_state,dict) else {}
    expected_projection = {
        stable_id:{"effective_candidate_row_digest":row.get("effective_candidate_row_digest"),"disposition":row.get("disposition"),"allowed_effects":row.get("allowed_effects")}
        for stable_id,row in parent_selected.items()
        if isinstance(row,dict) and row.get("disposition") in {"candidate","replace"} and row.get("release_owner")=="product_evolution"
    }
    expected_repo = {
        "requirements_cutover_repo_write_authorized":False,"external_repo":"RetryYN/AGENT-NEO",
        "current_access":"read_only","site_build_grant_reuse":"prohibited","wordpress_grant_reuse":"prohibited",
        "separate_change_unit_po_grant":"required","base_commit_tree_binding":"required",
        "external_repo_review_ci_release_admission":"required",
    }
    expected_noninheritance = {
        "prohibited_as_compatibility_or_release_proof":["legacy_g4_pass","legacy_s3_green","site_build_closure","single_site_success","wordpress_content_success","wordpress_platform_success","wordpress_security_success","legacy_release_tag"],
        "site_build_result_usage":"impact_and_regression_candidate_input_only",
    }
    expected_overlay: dict[str, Any] = {
        "component_families":["theme","plugin","integration_contract","release_tooling"],
        "responsibility_by_capability":{"site_identity":"integration_contract","fse_styles":"theme","templates_navigation":"theme","patterns_blocks_media":"theme","content_crud":"plugin","preview_apply_rollback":"release_tooling","seo":"plugin","measurement":"plugin","migration":"release_tooling","quality_security":"release_tooling","health_audit":"release_tooling","harness_neo_integration_boundary":"integration_contract","package":"release_tooling","license":"release_tooling","automation_seo":"plugin","crm":"plugin","sns":"plugin","external_api":"integration_contract","ai":"integration_contract"},
        "change_effects":["repo_read","repo_write","release","migration"],
        "parent_effect_to_change_effect":{"read":["repo_read"],"external_write":["repo_write","migration"],"release":["release"],"credential":[]},
        "release_dispositions":["candidate","defer"],
        "high_effects_requiring_external_repo_authorization":["repo_write","release","migration"],
        "external_repo_authorization_subject_id":"AGENT-NEO-PRODUCT-EVOLUTION-CHANGE-AUTHORIZATION",
        "active_owner_subject_id":"AGENT-NEO-PRODUCT-EVOLUTION-RELEASE",
        "compatibility_dimensions":["source_target_version_range","data_schema_api_content_compatibility","affected_site_class","breaking_change","migration_evidence","rollback_evidence","regression_evidence"],
        "selected_row_fields":["parent_projection_digest","component_family","change_effects","compatibility_obligations","regression_scope_class","breaking_change_disposition","migration_required","rollback_required","release_disposition","separate_authorization_dependency_ids","owner_subject_id","rationale","resume_conditions"],
    }
    expected_attempt = ["repository_id","base_commit","base_tree","component_id","component_revision","change_unit_digest","source_version","target_version","affected_site_set_digest","impact_map_digest","compatibility_matrix_digest","migration_plan_evidence_digest","rollback_plan_evidence_digest","regression_suite_result_digest","authorization_grant_id","authorization_grant_revision","authorization_grant_semantic_digest","authorization_scope_digest","author_principal","independent_review_receipt","ci_result_receipt","release_decision_receipt"]
    source_digests = {key:_digest(events.get(key)) for key in ("RDE-000122","RDE-000123")}
    expected_semantic = _digest({
        "source_event_digests":source_digests,"refinement_record_digest":_digest(record),
        "parent_policy_digests":expected_parents,"eligible_parent_capability_projection":expected_projection,
        "repo_authority_contract":expected_repo,"evidence_non_inheritance_contract":expected_noninheritance,
        "capability_overlay_contract":expected_overlay,"repo_change_attempt_contract":expected_attempt,
    })
    if policy.get("source_event_digests") != source_digests or policy.get("refinement_record_digest") != _digest(record):
        faults.append("product-evolution source events/refinement digest不一致")
    if policy.get("parent_policy_digests") != expected_parents or policy.get("eligible_parent_capability_projection") != expected_projection:
        faults.append("product-evolution parent authority/projectionがstale又はowner越境")
    if policy.get("repo_authority_contract") != expected_repo or policy.get("evidence_non_inheritance_contract") != expected_noninheritance:
        faults.append("product-evolution repo read-only／grant分離／旧成功非証拠化境界が反転")
    if policy.get("capability_overlay_contract") != expected_overlay or policy.get("repo_change_attempt_contract") != expected_attempt:
        faults.append("product-evolution component/compatibility/change attempt契約が不正")
    if policy.get("authority_semantic_digest") != expected_semantic:
        faults.append("product-evolution authority semantic digestがsource/parents/contractsへ束縛されていない")
    state = policy.get("classification_state",{})
    stage = state.get("status") if isinstance(state,dict) else None
    parent_ready = parent_state.get("status") in {"classified_pending_cutover","cutover_complete"}
    expected_state: dict[str, Any] = {
        "status":"pending_po_classification" if parent_ready else "blocked_by_parent_classification",
        "selected_rows":{},"classification_approval":None,"candidate_artifact_binding":None,
        "cutover_artifact_bindings":None,"cutover_blocked":True,"repo_write_authorized":False,
    }
    if not parent_ready or stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified" or state != expected_state:
            faults.append("product-evolutionは親分類前又はPO未分類なのに選択・cutover・repo writeされた")
    elif stage in {"classified_pending_cutover","cutover_complete"}:
        complete = stage == "cutover_complete"
        if agent_neo_helix_redefinition_policy_faults(refinements):
            faults.append("product-evolution parent AGENT NEO policy gateが閉じていない")
        site_policy = refinements.get("agent_neo_site_build_release_policy",{})
        site_state = site_policy.get("classification_state",{}) if isinstance(site_policy,dict) else {}
        if complete and (parent_state.get("status") != "cutover_complete" or site_state.get("status") != "cutover_complete" or agent_neo_site_build_release_policy_faults(refinements)):
            faults.append("product-evolution cutoverは親AGENT NEOとsite-buildのcutover/gate完了前に実行できない")
        selected = state.get("selected_rows",{})
        if policy.get("status") != ("ratified" if complete else "candidate_unratified") or state.get("cutover_blocked") is not (not complete) or state.get("repo_write_authorized") is not False or set(selected) != set(expected_projection):
            faults.append("product-evolution classified rows/stateが親eligible exact集合又はread-onlyでない")
        else:
            row_fields = set(expected_overlay["selected_row_fields"])
            family_map = expected_overlay["responsibility_by_capability"]
            effect_map = expected_overlay["parent_effect_to_change_effect"]
            compatibility = expected_overlay["compatibility_dimensions"]
            dependency = expected_overlay["external_repo_authorization_subject_id"]
            high_effects = set(expected_overlay["high_effects_requiring_external_repo_authorization"])
            for stable_id,row in selected.items():
                parent_row = expected_projection[stable_id]
                allowed_change_effects = {
                    effect
                    for parent_effect in parent_row.get("allowed_effects") or []
                    for effect in effect_map.get(parent_effect,[])
                }
                effects = row.get("change_effects")
                disposition = row.get("release_disposition")
                if set(row) != row_fields or row.get("parent_projection_digest") != _digest(parent_row) or row.get("component_family") != family_map.get(stable_id) or not isinstance(row.get("rationale"),str) or not row.get("rationale"):
                    faults.append(f"product-evolution {stable_id}: parent/component/row shape不一致")
                if disposition == "candidate":
                    if not isinstance(effects,list) or not effects or not set(effects) <= allowed_change_effects:
                        faults.append(f"product-evolution {stable_id}: change effectsが親effect候補の非空subsetでない")
                    obligations = row.get("compatibility_obligations")
                    breaking = row.get("breaking_change_disposition")
                    migration_required = "migration" in set(effects or []) or breaking == "po_risk_acceptance_required"
                    rollback_required = bool(set(effects or []) & high_effects)
                    required_dimensions = {
                        "source_target_version_range","data_schema_api_content_compatibility",
                        "affected_site_class","breaking_change","regression_evidence",
                    }
                    if migration_required:
                        required_dimensions.add("migration_evidence")
                    if rollback_required:
                        required_dimensions.add("rollback_evidence")
                    na_dimensions = set(compatibility) - required_dimensions
                    expected_na = {
                        dimension:{
                            "reason":"not_applicable_to_selected_change_effects",
                            "owner_subject_id":"AGENT-NEO-PRODUCT-EVOLUTION-RELEASE",
                            "review_trigger":"change_effect_or_breaking_classification_changes",
                        }
                        for dimension in sorted(na_dimensions)
                    }
                    if obligations != {"required_dimensions":sorted(required_dimensions),"not_applicable_dimensions":expected_na} or row.get("regression_scope_class") not in {"affected_sites","all_supported_sites"} or breaking not in {"compatible_only","po_risk_acceptance_required"}:
                        faults.append(f"product-evolution {stable_id}: compatibility/regression/breaking契約不正")
                    expected_dependencies = [dependency] if set(effects or []) & high_effects else []
                    if row.get("separate_authorization_dependency_ids") != expected_dependencies or row.get("owner_subject_id") != "AGENT-NEO-PRODUCT-EVOLUTION-RELEASE" or row.get("resume_conditions") != []:
                        faults.append(f"product-evolution {stable_id}: external repo authorization/owner partition不正")
                    if row.get("migration_required") is not migration_required or row.get("rollback_required") is not rollback_required:
                        faults.append(f"product-evolution {stable_id}: migration/rollback applicability不正")
                elif disposition == "defer":
                    if effects != [] or row.get("compatibility_obligations") != [] or row.get("regression_scope_class") is not None or row.get("breaking_change_disposition") is not None or row.get("migration_required") is not False or row.get("rollback_required") is not False or row.get("separate_authorization_dependency_ids") != [] or row.get("owner_subject_id") != "AGENT-NEO-PRODUCT-EVOLUTION-RELEASE" or not row.get("resume_conditions"):
                        faults.append(f"product-evolution {stable_id}: defer partition不正")
                else:
                    faults.append(f"product-evolution {stable_id}: release disposition不正")
        selected_digest = _digest(selected)
        approval = state.get("classification_approval")
        if approval != {"authority":"PO","approver_principal":"po","approved_revision":1,"parent_projection_digest":_digest(expected_projection),"selected_rows_digest":selected_digest,"parent_policy_digest":_digest(parent),"authority_semantic_digest":expected_semantic,"repo_write_authorized":False}:
            faults.append("product-evolution PO receiptがparent/selected/read-only意味へ束縛されていない")
        binding = state.get("candidate_artifact_binding")
        candidate_id = "AUTH-DEVELOPMENT-AGENT-NEO-PRODUCT-EVOLUTION-CANDIDATE"
        manifest = load(MANIFEST)
        item = next((x for x in manifest.get("items",[]) if x.get("artifact_id")==candidate_id),None)
        candidate_data: dict[str,Any] = {}
        candidate_digest = ""
        candidate_path: Path|None = None
        try:
            if not isinstance(item,dict) or item.get("layer")!="00-authority" or item.get("artifact_type")!="requirement-authority-candidate" or item.get("authority_format")!="json" or item.get("authority_status")!="active" or item.get("implementation_input") is not complete:
                raise ValueError("candidate manifest")
            rel = Path(str(item.get("canonical_path")))
            if rel.is_absolute():
                raise ValueError("absolute")
            candidate_path = (REPO_ROOT / rel).resolve()
            candidate_path.relative_to(REPO_ROOT.resolve())
            candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        except (OSError,ValueError,json.JSONDecodeError):
            candidate_data = {}
        expected_candidate = {"authority_semantic_digest":expected_semantic,"selected_rows_digest":selected_digest,"selected_rows":selected,"repo_authority_contract":expected_repo,"repo_change_attempt_contract":expected_attempt}
        if binding != {"artifact_id":candidate_id,"implementation_input":complete,"selected_rows_digest":selected_digest,"content_digest":candidate_digest} or candidate_data != expected_candidate:
            faults.append("product-evolution classified candidate artifact境界が不正")
        if not complete and state.get("cutover_artifact_bindings") is not None:
            faults.append("product-evolution classified pendingにcutover artifactが混入")
        if complete:
            cutover = state.get("cutover_artifact_bindings")
            try:
                head_result = git("rev-parse","HEAD")
                tree_result = git("rev-parse","HEAD^{tree}")
                head = head_result.stdout.strip() if head_result.returncode == 0 else ""
                tree = tree_result.stdout.strip() if tree_result.returncode == 0 else ""
            except OSError:
                head = tree = ""
            manifest_digest = "sha256:"+hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            baseline_path = REPO_ROOT/"docs/00-authority/baselines/baseline.json"
            baseline_digest = "sha256:"+hashlib.sha256(baseline_path.read_bytes()).hexdigest() if baseline_path.is_file() else ""
            expected_cutover = {
                "target_commit":head,"target_tree":tree,"candidate_content_digest":candidate_digest,
                "manifest_digest":manifest_digest,"baseline_digest":baseline_digest,
                "parent_policy_digest":_digest(parent),"parent_cutover_status":"cutover_complete",
                "site_build_policy_digest":_digest(site_policy),"site_build_cutover_status":"cutover_complete",
                "requirements_cutover_repo_write_authorized":False,
                "external_repo_access":"read_only",
                "independent_go_artifact_id":"AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO",
            }
            if not isinstance(cutover,dict) or any(cutover.get(key)!=value for key,value in expected_cutover.items()):
                faults.append("product-evolution cutoverがparents/commit/tree/artifacts/read-onlyへ束縛されていない")
            review_item = next((x for x in manifest.get("items",[]) if x.get("artifact_id")=="AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO"),None)
            review_path: Path|None = None
            try:
                if not isinstance(review_item,dict) or review_item.get("artifact_type")!="review" or review_item.get("authority_status")!="active":
                    raise ValueError("review manifest")
                review_rel = Path(str(review_item.get("canonical_path")))
                if review_rel.is_absolute():
                    raise ValueError("absolute review")
                review_path = (REPO_ROOT/review_rel).resolve()
                review_path.relative_to(REPO_ROOT.resolve())
                review = json.loads(review_path.read_text(encoding="utf-8"))
                review_digest = "sha256:"+hashlib.sha256(review_path.read_bytes()).hexdigest()
            except (OSError,ValueError,json.JSONDecodeError):
                review = {}
                review_digest = ""
            reviewed = review.get("reviewed_artifact_digests",{}) if isinstance(review,dict) else {}
            head_blob_mismatch = False
            for artifact_path in (candidate_path,MANIFEST,baseline_path,review_path):
                if not isinstance(artifact_path,Path):
                    head_blob_mismatch = True
                    continue
                try:
                    relative_path = artifact_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
                    blob = git("show",f"HEAD:{relative_path}")
                    if blob.returncode != 0 or blob.stdout.encode()!=artifact_path.read_bytes():
                        head_blob_mismatch = True
                except (OSError,ValueError):
                    head_blob_mismatch = True
            expected_reviewed = {"candidate":candidate_digest,"manifest":manifest_digest,"baseline":baseline_digest,"parent_policy":_digest(parent),"site_build_policy":_digest(site_policy)}
            if (
                not isinstance(cutover,dict)
                or cutover.get("independent_go_path") != (review_item.get("canonical_path") if isinstance(review_item,dict) else None)
                or cutover.get("independent_go_digest") != review_digest
                or review.get("review_id") != "AUTH-REVIEW-AGENT-NEO-PRODUCT-EVOLUTION-GO"
                or review.get("verdict") != "Go" or review.get("separation_status") != "ci_attested"
                or review.get("target_commit") != head or review.get("target_tree") != tree
                or not isinstance(review.get("reviewer_principal"),str) or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po",review.get("author_principal")}
                or reviewed != expected_reviewed or head_blob_mismatch
            ):
                faults.append("product-evolution independent Goが主体分離・parents・HEAD blob・artifact集合を被覆しない")
    else:
        faults.append("product-evolution classification stageが不明")
    return faults


def fr16_notification_boundary_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """安全停止とVPS UI inboxを順序・非権威・失敗不変条件へ閉じる。"""
    records={row.get("subject_id"):row for row in refinements.get("records",[]) if isinstance(row,dict)}
    inbox_record = records.get("VPS-UI-INBOX-LIFECYCLE")
    inbox_bindings = inbox_record.get("registration_bindings", []) if isinstance(inbox_record, dict) else []

    def registration_ref(binding: str, dimensions: list[str]) -> dict[str, Any]:
        indexes = [index for index, value in enumerate(inbox_bindings) if value == binding]
        return {
            "subject_id": "VPS-UI-INBOX-LIFECYCLE",
            "binding_index": indexes[0] if len(indexes) == 1 else None,
            "binding_digest": _digest(binding) if len(indexes) == 1 else None,
            "required_dimensions": dimensions,
        }

    dedupe_universe = ["source_class","source_subject_id","source_state_revision","artifact_id","rule_revision_digest","source_identity_digest","purpose"]
    default_required = ["source_class","source_subject_id","source_state_revision","purpose"]
    default_prohibited = ["artifact_id","rule_revision_digest","source_identity_digest"]
    dedupe_contract: dict[str, Any] = {
        "field_universe": dedupe_universe,
        "class_field_contracts": {
            "safety_stop": {"required": default_required, "prohibited": default_prohibited},
            "blocked_retry_exhausted": {"required": ["source_class","artifact_id","rule_revision_digest","source_identity_digest","purpose"], "prohibited": ["source_subject_id","source_state_revision"]},
            "approval_waiting": {"required": default_required, "prohibited": default_prohibited},
            "recovery_decision_required": {"required": default_required, "prohibited": default_prohibited},
        },
        "retry_behavior": "same_inbox_item",
    }
    expected={
        "status":"candidate_unratified","approval":None,"design_not_started":True,
        "source_event_ids":["RDE-000002","RDE-000015","RDE-000016","RDE-000036","RDE-000037"],
        "source_event_digests":{key:_digest(value) for key,value in {row.get("event_id"):row for row in requirement_discovery.load_discovery_ledger().get("events",[]) if isinstance(row,dict)}.items() if key in {"RDE-000002","RDE-000015","RDE-000016","RDE-000036","RDE-000037"}},
        "refinement_record_digest":_digest(records.get("FR-16-NOTIFICATION-BOUNDARY")),
        "refinement_record_semantic_digest":"sha256:fa328819de985985217c8b7268ee67b0fb1c725e7437b19c3dde8dc6498e0b2d",
        "refinement_record_content_digest":"sha256:cd84c331daf989ed0befb38ccab2b297a0de029b9f98f4e30bdf8631f05eea14",
        "parent_semantic_digests":{"vps_ui_inbox_lifecycle":_digest(records.get("VPS-UI-INBOX-LIFECYCLE")),"product_state_authority_policy":_digest(refinements.get("product_state_authority_policy")),"content_quality_gate_learning":_digest(records.get("CONTENT-QUALITY-GATE-LEARNING")),"pod_009":_digest(refinements.get("captured_po_decision_controls",{}).get("POD-20260815-009")),"discord_notification_rejection":_digest(records.get("DISCORD-NOTIFICATION-REJECTION-BOUNDARY"))},
        "legacy_boundary_digests":{"fr_16_meaning":_digest(refinements.get("legacy_requirement_meaning_inventory",{}).get("meaning_migrations",{}).get("FR-16")),"critical_responsibility_dispositions":_digest(refinements.get("legacy_critical_responsibility_dispositions")),"phase_fault_classifications":_digest(refinements.get("legacy_phase_fault_classifications"))},
        "notification_purpose":"operational_state_route_only",
        "source_classes":["safety_stop","blocked_retry_exhausted","approval_waiting","recovery_decision_required"],
        "event_binding_fields":["notification_event_id","source_class","source_subject_id","source_state","source_state_revision","source_receipt_digest","purpose","inbox_item_id","dedupe_identity","attempt_no","outcome","outcome_receipt_digest"],
        "source_class_contracts":{"safety_stop":{"source_subject_id":"PRODUCT-STATE-AUTHORITY","source_state":"safety_stopped","required_predecessor":"authorized_stop_transition_committed","required_receipt":"product_state_transition_receipt"},"blocked_retry_exhausted":{"source_subject_id":"CONTENT-QUALITY-GATE-LEARNING","source_state":"blocked","required_predecessor":"retry_exhaustion_blocked_committed","required_receipt":"retry_exhaustion_receipt"},"approval_waiting":{"source_subject_id":"AUTOMATED-PUBLISHING-ADMISSION","source_state":"approval_waiting","required_predecessor":"decision_pending_committed","required_receipt":"activation_decision_pending_receipt"},"recovery_decision_required":{"source_subject_id":"PRODUCT-STATE-AUTHORITY","source_state":"recovery_required","required_predecessor":"recovery_required_committed","required_receipt":"product_state_transition_receipt"}},
        "outcome_values":["attempted","recorded","failed","retry_exhausted"],
        "ordering_invariant":"class_required_predecessor_committed_before_inbox_attempt",
        "authority_invariants":["seen_ack_and_notification_outcome_do_not_change_source_state","notification_does_not_approve_reject_or_resume","recovery_requires_new_authorized_product_state_transition"],
        "failure_invariants":["inbox_failure_or_retry_exhaustion_preserves_source_state_revision_and_history","no_external_fallback"],
        "dedupe_contract":dedupe_contract,
        "route_contract":{"allowed":["vps_ui_inbox"],"prohibited_inheritance":["discord","product_approval_transport","development_pr_notification","consumer_browser_automation","legacy_approval_transport","provider_fixed_route"]},
        "phase_contract":{"legacy_s0":"obsolete_as_runtime_permission","current":"requirements_candidate","runtime":"only_after_activation_and_admission"},
        "registration_refs":{"inbox_retry_budget":registration_ref("profile/purpose/risk class別 inbox retry budget（max attempts/max elapsed/effective revision）",["max_attempts","max_elapsed","effective_revision"]),"notification_availability":registration_ref("profile/purpose/risk class別 inbox retry budget（max attempts/max elapsed/effective revision）",["max_elapsed","effective_revision"]),"retention_data_class":registration_ref("terminal retention policy（data classification/legal hold/archive/redact/purge/effective revision）",["data_classification","legal_hold","archive","redact","purge","effective_revision"])},
        "design_later":["queue_and_backoff","persistence","ui_badge_and_stale_rendering","archive_and_purge","web_framework"],
    }
    expected["authority_semantic_digest"]=_digest(expected)
    faults = [] if refinements.get("fr16_notification_boundary_policy")==expected else ["FR-16 notification policyが停止先行・VPS inbox非権威・失敗不変・旧経路禁止のexact contractと不一致"]
    if records.get("FR-16-NOTIFICATION-BOUNDARY", {}).get("semantic_digest") != expected["refinement_record_semantic_digest"]:
        faults.append("FR-16 notification record semantic digestがcode正本と不一致")
    if _digest({key: value for key, value in records.get("FR-16-NOTIFICATION-BOUNDARY", {}).items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("FR-16 notification record実semantic contentがcode正本と不一致")
    for source_class, contract in dedupe_contract["class_field_contracts"].items():
        required = contract["required"]
        prohibited = contract["prohibited"]
        if set(required) & set(prohibited) or set(required) | set(prohibited) != set(dedupe_universe):
            faults.append(f"FR-16 dedupe identity {source_class}のfield partitionが閉じていない")
    return faults


def discord_notification_rejection_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """Discord community capabilityを製品通知・承認・PR経路から隔離する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    event_ids = ("RDE-000156", "RDE-000157", "RDE-000158")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in event_ids}
    req_meaning = refinements.get("legacy_requirement_meaning_inventory", {}).get("meaning_migrations", {})
    media_meaning = refinements.get("legacy_media_br_meaning_migrations", {})
    mr_meaning = refinements.get("legacy_mr_meaning_inventory", {}).get("meaning_migrations", {})
    critical = [row for row in refinements.get("legacy_critical_responsibility_dispositions", []) if isinstance(row, dict) and "discord" in json.dumps(row, ensure_ascii=False).lower()]
    decision_control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-002", {})
    decision_facts = {"product_notification_route": "vps_ui_inbox", "discord_role": "community_marketing_only", "discord_prohibited_purposes": ["product_approval_notification", "operational_notification", "developer_pr_notification"]}
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True,
        "source_event_ids": list(event_ids), "source_event_digests": {event_id: _digest(events.get(event_id)) for event_id in event_ids},
        "refinement_record_digest": _digest(records.get("DISCORD-NOTIFICATION-REJECTION-BOUNDARY")),
        "refinement_record_semantic_digest": "sha256:9eaf6bb8e88b9ef540c8e0d26ba71ecff670cb0e38f05ce74397722b0ec7d88b",
        "refinement_record_content_digest": "sha256:f0f760aac3aa58c233f6a55ef2671f43c559aa3826917b1c4520bf2663b021f7",
        "decision_binding": {"decision_snapshot_digest": "sha256:29756112668435ad619ca819beb41e4fdfdbce8a9e3e85ada82cfdb495ccd624", "facts": decision_facts},
        "parent_semantic_digests": {"fr16_notification_policy": _digest(refinements.get("fr16_notification_boundary_policy")), "vps_ui_inbox_lifecycle": _digest(records.get("VPS-UI-INBOX-LIFECYCLE")), "discord_community_route": _digest(records.get("DISCORD-COMMUNITY-MARKETING-ROUTE"))},
        "legacy_boundary_digests": {"fr_16": _digest(req_meaning.get("FR-16")), "br_h2_h3": _digest({key: req_meaning.get(key) for key in ("BR-H2", "BR-H3")}), "media_br_dc": _digest({key: media_meaning.get(key) for key in sorted(media_meaning) if key.startswith("BR-M-DC-")}), "mr_dc": _digest({key: mr_meaning.get(key) for key in sorted(mr_meaning) if key.startswith("MR-DC-")}), "critical_discord_responsibilities": _digest(critical)},
        "purpose_partition": {"allowed_discord_purposes": ["community_marketing"], "prohibited_notification_purposes": ["product_approval", "operational_notification", "development_pr_notification", "approval_deep_link_delivery"], "community_execution_authority": "not_granted_by_this_policy", "unknown_purpose": "reject_without_resume_condition"},
        "rejection_event_fields": ["request_id", "purpose", "requested_route", "source_subject_id", "source_revision", "decision", "rejection_reason", "source_state_before", "source_state_after", "receipt_digest"],
        "rejection_contract": {"requested_route": "discord", "decision": "rejected", "source_state_invariant": "source_state_before_equals_source_state_after", "send_effect": "none", "fallback": "prohibited"},
        "authority_invariants": ["rejection_receipt_does_not_approve_reject_or_resume_business_state", "rejection_receipt_is_not_a_community_grant", "community_capability_is_separate_and_unratified"],
        "cross_purpose_prohibitions": ["account_sharing", "guild_sharing", "channel_sharing", "credential_sharing", "policy_sharing", "evidence_sharing", "receipt_sharing", "alternate_discord_fallback"],
        "prohibited_legacy_mechanisms": ["discord_webhook_notification", "discord_bot_notification", "approval_transport_tuple", "notion_discord_approval_sync", "consumer_browser_automation", "legacy_success_as_permission", "legacy_phase_as_permission"],
        "registration_contract": {"disposition": "not_applicable", "reason": "rejection_route_has_no_runtime_registration", "owner_subject_id": "DISCORD-NOTIFICATION-REJECTION-BOUNDARY", "review_trigger": "explicit_po_policy_revision", "community_registration_substitution": "prohibited"},
        "design_later": ["rejection_receipt_storage", "rejection_diagnostic_ui", "route_dispatcher_implementation"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    faults = [] if refinements.get("discord_notification_rejection_policy") == expected else ["Discord通知拒否policyがVPS inbox・community専用・no-send・cross-purpose隔離のexact contractと不一致"]
    if records.get("DISCORD-NOTIFICATION-REJECTION-BOUNDARY", {}).get("semantic_digest") != expected["refinement_record_semantic_digest"]:
        faults.append("Discord notification rejection record semantic digestがcode正本と不一致")
    if _digest({key: value for key, value in records.get("DISCORD-NOTIFICATION-REJECTION-BOUNDARY", {}).items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("Discord notification rejection record実semantic contentがcode正本と不一致")
    if decision_control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or decision_control.get("facts") != decision_facts:
        faults.append("Discord通知拒否policyのPOD-002 decision snapshot又はtyped factsが不一致")
    return faults


def vps_ui_primary_interface_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """VPS Web UIをhuman product entryに限定し操作ごとのauthority非含意を閉じる。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    source_ids = ("RDE-000007", "RDE-000010", "RDE-000011", "RDE-000012", "RDE-000013", "RDE-000030", "RDE-000031", "RDE-000032", "RDE-000035")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    controls = refinements.get("captured_po_decision_controls", {})
    decision_bindings = {
        "POD-20260815-001": {"decision_snapshot_digest": "sha256:a108c02eba247caec3c66fa58b183bcfeafbfead26e888ede4b2aa74ddbe80ea", "ui_projection": {"browser_confirmation_engine": "playwright", "browser_confirmation_role": "read_confirmation", "permission_scope": "account_operation_resource"}},
        "POD-20260815-003": {"decision_snapshot_digest": "sha256:4e8b18532809d7b32965594d025e167ae4caa75b80d00696879accf7ebe1ae00", "ui_projection": {"activation_authority": "authenticated_ui_explicit_user_decision", "activation_notice": "vps_ui_inbox", "per_post_approval_required": False, "failure_action": "deny_external_write"}},
        "POD-20260815-004": {"decision_snapshot_digest": "sha256:f86634ab8eb788d10d9358cb9b46867af6ac03429c1c864afc8f0dc4057b3095", "ui_projection": {"failed_artifact_human_review": "prohibited", "pass_required_before_progress": True}},
        "POD-20260815-008": {"decision_snapshot_digest": "sha256:b10ecdf8d2306587f098488f91a00d79a2849399bf9235f4e514f239b28dd142", "ui_projection": {"post_reboot_external_effects": "stopped", "credential_unlock": "human_reauthorization_with_runtime_reinitialization", "credential_only_auto_unlock": "prohibited"}},
        "POD-20260815-009": {"decision_snapshot_digest": "sha256:2e85fb60a138d12aaeafb9f0152bef194905bf48c1659eb01acaa30a776572af", "ui_projection": {"ordinary_failed_retry_notification": "none", "retry_exhaustion_state": "blocked", "retry_exhaustion_notification": "vps_ui_inbox", "notification_failure_state_effect": "no_rollback", "unsupported_published_update_action": "no_action_including_notification"}},
    }
    registration_subjects = ("VPS-UI-AUTHENTICATION-SESSION", "BUSINESS-PROFILE-AUTHORIZATION", "VPS-UI-INBOX-LIFECYCLE", "VPS-UI-QUALITY-ATTRIBUTES", "PRODUCT-STATE-AUTHORITY")
    field_universe = ["ui_operation_id", "session_id", "authenticated_identity_digest", "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest", "profile_id", "resource_id", "operation", "effect", "source_revision", "interaction_intent_id", "business_decision_id", "product_state_transition_receipt", "feedback_scope_digest", "feedback_candidate_receipt", "notification_state_receipt", "result_receipt"]
    base = field_universe[:11] + ["result_receipt"]
    def partition(extra: list[str]) -> dict[str, list[str]]:
        required = base[:-1] + extra + ["result_receipt"]
        return {"required": required, "prohibited": [field for field in field_universe if field not in required]}
    operation_contracts = {
        "state_evidence_diagnostic_view": {**partition([]), "allowed_effects": ["read"]},
        "inbox_seen_ack": {**partition(["interaction_intent_id", "notification_state_receipt"]), "allowed_effects": ["notification_state_write"]},
        "explicit_business_decision": {**partition(["interaction_intent_id", "business_decision_id", "product_state_transition_receipt"]), "allowed_effects": ["state_write", "revoke"]},
        "structured_feedback": {**partition(["interaction_intent_id", "feedback_scope_digest", "feedback_candidate_receipt"]), "allowed_effects": ["feedback_candidate_write"]},
    }
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "cutover_blocked_until_parent_ratification": True,
        "source_event_ids": list(source_ids), "source_event_digests": {event_id: _digest(events.get(event_id)) for event_id in source_ids},
        "refinement_record_digest": _digest(records.get("VPS-UI-PRIMARY-HUMAN-INTERFACE")),
        "refinement_record_semantic_digest": "sha256:229880f28abe6afce7c9576079bf3844130c3f47aa8d60a42e8079439e12478f",
        "refinement_record_content_digest": "sha256:b94adfe595e3a549c149e4ffc94ce405cf402d33ca5687e7d429038003de316a",
        "decision_bindings": decision_bindings,
        "parent_semantic_digests": {
            "vps_ui_authentication_session": _digest(refinements.get("vps_ui_authentication_session_policy")),
            "business_profile_authorization": _digest(refinements.get("business_profile_authorization_policy")),
            "vps_ui_inbox": _digest(records.get("VPS-UI-INBOX-LIFECYCLE")),
            "vps_ui_quality": _digest(refinements.get("vps_ui_quality_attributes_policy")),
            "product_state": _digest(refinements.get("product_state_authority_policy")),
            "fr16_notification": _digest(refinements.get("fr16_notification_boundary_policy")),
            "credential_boundary": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")),
            "automated_publishing_admission": _digest(records.get("AUTOMATED-PUBLISHING-ADMISSION")),
        },
        "primary_route_contract": {"human_product_entry": ["vps_web_ui", "vps_ui_inbox"], "notification_route": "vps_ui_inbox", "external_routes": "not_primary_and_not_authorized", "consumer_ui_automation": "prohibited"},
        "operation_binding_field_universe": field_universe,
        "operation_contracts": operation_contracts,
        "decision_operation_scope": ["initial_activation", "scope_expansion", "high_risk_exception", "recovery", "revoke"],
        "non_implication_invariants": ["authentication_does_not_imply_authorization", "view_seen_ack_notification_do_not_approve_reject_or_resume", "diagnostic_view_does_not_imply_secret_access", "feedback_submission_does_not_activate_rule_or_requirement", "playwright_or_browser_confirmation_does_not_replace_human_decision"],
        "data_minimization": {"allowed": ["authority_reference", "minimal_redacted_projection"], "prohibited": ["raw_credential", "raw_secret", "raw_policy_evidence", "unnecessary_pii"]},
        "prohibited_legacy_interfaces": ["discord_product_notification", "notion_approval_sync", "approval_transport", "cli_only_human_entry", "api_only_consumer_ui", "claude_design_required", "codex_runtime_required", "browser_automation_as_decision_authority", "legacy_sqlite_home_ui"],
        "registration_source_digests": {subject_id: _digest(records.get(subject_id, {}).get("registration_bindings")) for subject_id in registration_subjects},
        "registration_values_in_policy": "prohibited",
        "phase_contract": {"current": "requirements_candidate", "l2_screen_layout_navigation": "not_started", "runtime": "blocked_until_ratification_activation_and_admission"},
        "design_later": ["screen_list", "layout_and_navigation", "web_framework_and_reverse_proxy", "api_composition", "refresh_and_pagination", "redaction_ui", "playwright_e2e"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    faults = [] if refinements.get("vps_ui_primary_interface_policy") == expected else ["VPS UI primary interface policyが主入口・操作authority・親未批准block・未設計境界のexact contractと不一致"]
    if records.get("VPS-UI-PRIMARY-HUMAN-INTERFACE", {}).get("semantic_digest") != expected["refinement_record_semantic_digest"]:
        faults.append("VPS UI primary record semantic digestがcode正本と不一致")
    if _digest({key: value for key, value in records.get("VPS-UI-PRIMARY-HUMAN-INTERFACE", {}).items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("VPS UI primary record実semantic contentがcode正本と不一致")
    actual_projection = {
        "POD-20260815-001": {"browser_confirmation_engine": controls.get("POD-20260815-001", {}).get("facts", {}).get("browser_engine"), "browser_confirmation_role": "read_confirmation" if "read_confirmation" in controls.get("POD-20260815-001", {}).get("facts", {}).get("browser_roles", []) else None, "permission_scope": controls.get("POD-20260815-001", {}).get("facts", {}).get("permission_scope")},
        "POD-20260815-003": {key: controls.get("POD-20260815-003", {}).get("facts", {}).get(key) for key in ("activation_authority", "activation_notice", "per_post_approval_required", "failure_action")},
        "POD-20260815-004": {key: controls.get("POD-20260815-004", {}).get("facts", {}).get(key) for key in ("failed_artifact_human_review", "pass_required_before_progress")},
        "POD-20260815-008": {key: controls.get("POD-20260815-008", {}).get("facts", {}).get(key) for key in ("post_reboot_external_effects", "credential_unlock", "credential_only_auto_unlock")},
        "POD-20260815-009": {key: controls.get("POD-20260815-009", {}).get("facts", {}).get(key) for key in ("ordinary_failed_retry_notification", "retry_exhaustion_state", "retry_exhaustion_notification", "notification_failure_state_effect", "unsupported_published_update_action")},
    }
    if any(controls.get(decision_id, {}).get("decision_snapshot_digest") != binding["decision_snapshot_digest"] or actual_projection[decision_id] != binding["ui_projection"] for decision_id, binding in decision_bindings.items()):
        faults.append("VPS UIに必要なPO decision snapshot又はtyped projectionが不一致")
    actual_policy = refinements.get("vps_ui_primary_interface_policy", {})
    actual_contracts = actual_policy.get("operation_contracts", {}) if isinstance(actual_policy, dict) else {}
    actual_universe = actual_policy.get("operation_binding_field_universe", []) if isinstance(actual_policy, dict) else []
    universe_valid = isinstance(actual_universe, list) and all(isinstance(value, str) and value for value in actual_universe) and len(actual_universe) == len(set(actual_universe))
    if not universe_valid:
        faults.append("VPS UI operation binding field universeがtyped unique string集合でない")
    if not isinstance(actual_contracts, dict) or set(actual_contracts) != {"state_evidence_diagnostic_view", "inbox_seen_ack", "explicit_business_decision", "structured_feedback"}:
        faults.append("VPS UI operation class集合が不正")
    for operation_class, contract in actual_contracts.items() if isinstance(actual_contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (universe_valid and set(required) | set(prohibited) != set(actual_universe)):
            faults.append(f"VPS UI {operation_class} binding field partitionが閉じていない")
    return faults


def external_browser_automation_route_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """API/MCP優先とPlaywright read確認をbrowser write authorityから分離する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    source_ids = ("RDE-000136", "RDE-000142", "RDE-000148")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    controls = refinements.get("captured_po_decision_controls", {})
    pod1 = controls.get("POD-20260815-001", {})
    pod1_facts = pod1.get("facts", {}) if isinstance(pod1, dict) else {}
    pod_projection = {"route_precedence": ["official_api", "official_mcp"], "browser_engine": "playwright", "browser_roles": ["capability_fallback", "read_confirmation"], "permission_scope": "account_operation_resource"}
    fields = ["route_decision_id", "media_id", "profile_id", "account_id", "resource_id", "operation", "effect", "capability_source_id", "capability_revision", "capability_semantic_digest", "terms_revision_digest", "route", "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest", "authorization_scope_digest", "activation_scope_digest", "credential_authority_digest", "risk_gate_receipt", "quality_gate_receipt", "quota_policy_receipt", "execution_plan_digest", "result_or_confirmation_receipt", "rollback_recovery_receipt", "handoff_reason", "handoff_authority_digest", "attended_handoff_receipt"]
    base = fields[:18] + ["quota_policy_receipt", "execution_plan_digest", "result_or_confirmation_receipt"]
    def field_partition(extra: list[str]) -> dict[str, list[str]]:
        required = base + extra
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    official_read_contract = field_partition([])
    official_write_contract = field_partition(["risk_gate_receipt", "quality_gate_receipt", "rollback_recovery_receipt"])
    attended_required = [
        "route_decision_id", "media_id", "profile_id", "account_id", "resource_id", "operation", "effect",
        "capability_source_id", "capability_revision", "capability_semantic_digest", "terms_revision_digest", "route",
        "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest",
        "authorization_scope_digest", "handoff_reason", "handoff_authority_digest", "attended_handoff_receipt",
    ]
    route_contracts = {
        "official_api": {**official_read_contract, "allowed_effects": ["read", "external_write_if_separately_admitted"], "write_effect_contract": official_write_contract},
        "official_mcp": {**official_read_contract, "allowed_effects": ["read", "external_write_if_separately_admitted"], "write_effect_contract": official_write_contract},
        "playwright_confirmation": {**field_partition([]), "allowed_effects": ["read_confirmation"], "authority_result": "confirmation_only"},
        "playwright_registered_fallback": {**field_partition([]), "allowed_effects": ["read"], "authority_result": "registered_read_only_fallback"},
        "attended_manual": {
            "required": attended_required,
            "prohibited": [field for field in fields if field not in attended_required],
            "allowed_effects": ["none"],
            "authority_result": "new_human_operation_not_automation_success",
        },
    }
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "browser_write_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {event_id: _digest(events.get(event_id)) for event_id in source_ids},
        "refinement_record_digest": _digest(records.get("EXTERNAL-BROWSER-AUTOMATION-ROUTE")),
        "refinement_record_semantic_digest": "sha256:656e7c8cab8e861e8c0cc39f2633f2f59605471734441a9fb7f41a127d6fc5d8",
        "refinement_record_content_digest": "sha256:2bd409bf89cd61ae6c60a4c652aa69c78afaa9e2a840610dd38f2ef297fc203d",
        "decision_binding": {"decision_snapshot_digest": "sha256:a108c02eba247caec3c66fa58b183bcfeafbfead26e888ede4b2aa74ddbe80ea", "route_projection": pod_projection},
        "parent_semantic_digests": {
            "provider_neutral_execution": _digest(refinements.get("provider_neutral_execution_policy")),
            "official_api_route": _digest(records.get("OFFICIAL-API-ROUTE-AUTHORITY")),
            "business_profile_authorization": _digest(refinements.get("business_profile_authorization_policy")),
            "automated_publishing_admission": _digest(records.get("AUTOMATED-PUBLISHING-ADMISSION")),
            "credential_boundary": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")),
            "rate_quota_cost": _digest(refinements.get("rate_quota_cost_policy")),
            "content_risk": _digest(records.get("CONTENT-RISK-CLASSIFICATION")),
            "content_quality": _digest(records.get("CONTENT-QUALITY-GATE-LEARNING")),
            "product_state": _digest(refinements.get("product_state_authority_policy")),
        },
        "route_classes": ["official_api", "official_mcp", "playwright_confirmation", "playwright_registered_fallback", "attended_manual"],
        "precedence_contract": {"order": ["official_api", "official_mcp"], "playwright_confirmation": "read_only_result_confirmation", "fallback_requires": ["official_routes_unavailable", "operation_specific_registration"], "fallback_forbidden_reasons": ["official_route_failure", "quota_rejection", "cost_rejection", "credential_rejection", "terms_rejection"]},
        "attempt_binding_field_universe": fields,
        "route_field_contracts": route_contracts,
        "browser_write_contract": {"current": "prohibited", "future_candidate_requires": ["po_ratified_operation_class", "exact_authorization_grant", "activation_scope", "fresh_terms", "credential_authority", "risk_gate", "quality_gate", "quota_and_cost", "rollback_and_recovery"], "media_wide_write": "prohibited"},
        "unknown_and_unsupported": {"outcome": "fail_close", "attended_handoff": "new_human_operation", "automatic_success": "prohibited"},
        "engine_contract": {"allowed_browser_engine": "playwright", "automatic_engine_substitution": "prohibited", "consumer_web_ui_unattended": "prohibited"},
        "prohibited_inheritance": ["media_wide_browser_write", "consumer_genai_web_ui_unattended", "out_of_allow_list_external_read", "confirmation_as_write_or_release_authority", "legacy_docker_wp_browser_success", "fixed_provider_or_route", "credential_or_terms_inference", "legacy_phase_as_permission"],
        "registration_source_digests": {"official_route": _digest(records.get("OFFICIAL-API-ROUTE-AUTHORITY", {}).get("registration_bindings")), "business_authorization": _digest(records.get("BUSINESS-PROFILE-AUTHORIZATION", {}).get("registration_bindings")), "rate_quota_cost": _digest(records.get("RATE-QUOTA-COST-AUTHORITY", {}).get("registration_bindings"))},
        "registration_values_in_policy": "prohibited",
        "design_later": ["playwright_adapter_and_context_isolation", "locator_and_selector", "navigation_wait_and_retry", "download_and_upload", "screenshot_and_redaction", "session_cleanup", "terms_and_anti_bot_evidence_collection"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("external_browser_automation_route_policy")
    faults = [] if policy == expected else ["external browser route policyがAPI/MCP優先・Playwright確認・write既定禁止のexact contractと不一致"]
    record = records.get("EXTERNAL-BROWSER-AUTOMATION-ROUTE", {})
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("external browser route record実semantic contentがcode正本と不一致")
    actual_projection = {"route_precedence": pod1_facts.get("route_priority"), "browser_engine": pod1_facts.get("browser_engine"), "browser_roles": pod1_facts.get("browser_roles"), "permission_scope": pod1_facts.get("permission_scope")}
    if pod1.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or actual_projection != pod_projection:
        faults.append("external browser routeのPOD-001 decision projectionが不一致")
    actual_universe = policy.get("attempt_binding_field_universe", []) if isinstance(policy, dict) else []
    universe_valid = isinstance(actual_universe, list) and all(isinstance(value, str) and value for value in actual_universe) and len(actual_universe) == len(set(actual_universe))
    if not universe_valid:
        faults.append("external browser attempt field universeがtyped unique string集合でない")
    actual_contracts = policy.get("route_field_contracts", {}) if isinstance(policy, dict) else {}
    if not isinstance(actual_contracts, dict) or set(actual_contracts) != set(expected["route_classes"]):
        faults.append("external browser route class集合が不正")

    def partition_closed(contract: Any) -> bool:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        return bool(
            isinstance(required, list)
            and isinstance(prohibited, list)
            and all(isinstance(value, str) for value in required + prohibited)
            and not set(required) & set(prohibited)
            and (not universe_valid or set(required) | set(prohibited) == set(actual_universe))
        )

    for route_class, contract in actual_contracts.items() if isinstance(actual_contracts, dict) else []:
        if route_class in {"official_api", "official_mcp"}:
            if not partition_closed(contract):
                faults.append(f"external browser {route_class}/read field partitionが閉じていない")
            if not partition_closed(contract.get("write_effect_contract") if isinstance(contract, dict) else None):
                faults.append(f"external browser {route_class}/external_write field partitionが閉じていない")
        elif not partition_closed(contract):
            faults.append(f"external browser {route_class} field partitionが閉じていない")
    return faults


def official_api_route_authority_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """公式route registryをoperation/effect単位に閉じbrowser暗黙fallbackを拒否する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("OFFICIAL-API-ROUTE-AUTHORITY", {})
    source_ids = ("RDE-000008", "RDE-000026", "RDE-000027", "RDE-000045", "RDE-000046")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    pod1 = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-001", {})
    pod_facts = pod1.get("facts", {}) if isinstance(pod1, dict) else {}
    route_fields = ["media_id", "profile_id", "account_id", "resource_id", "operation", "effect", "route_kind", "official_source_id", "source_revision", "source_semantic_digest", "terms_revision_digest", "capability_semantic_digest", "credential_scope_digest", "quota_cost_policy_digest", "operation_authorization_ref", "effective_revision", "expires_at"]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "execution_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record),
        "refinement_record_semantic_digest": "sha256:a2614cd4a2b2ea8347e9f9f04e8378303628965d9e81909643a0fb9c208b9e7d",
        "refinement_record_content_digest": "sha256:2fb299bae6c47c9414ba10110cec67498d244b8c21060f6543678a34e759a698",
        "decision_binding": {"decision_snapshot_digest": "sha256:a108c02eba247caec3c66fa58b183bcfeafbfead26e888ede4b2aa74ddbe80ea", "route_projection": {"route_precedence": ["official_api", "official_mcp"], "permission_scope": "account_operation_resource"}},
        "parent_semantic_digests": {
            "provider_neutral_execution": _digest(refinements.get("provider_neutral_execution_policy")),
            "business_profile_authorization": _digest(refinements.get("business_profile_authorization_policy")),
            "credential_boundary": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")),
            "rate_quota_cost": _digest(refinements.get("rate_quota_cost_policy")),
            "product_state": _digest(refinements.get("product_state_authority_policy")),
            "external_browser_boundary": _digest(refinements.get("external_browser_automation_route_policy")),
        },
        "route_registry_field_universe": route_fields,
        "route_kinds": ["official_api", "official_mcp", "official_export", "attended_manual"],
        "precedence_contract": {"automation_order": ["official_api", "official_mcp"], "official_export": "separate_read_effect", "attended_manual": "new_human_operation", "media_override": "registration_and_po_revision_only"},
        "effect_contract": {"read": "route_success_is_receipt_only", "external_write": "separate_operation_authorization_required", "official_export": "read_or_download_only", "attended_manual": "no_automation_success"},
        "route_kind_effect_contracts": {
            "official_api": {"allowed_effects": ["read", "external_write_if_separately_admitted"], "read_prohibited_fields": ["operation_authorization_ref"], "write_required_fields": ["operation_authorization_ref"]},
            "official_mcp": {"allowed_effects": ["read", "external_write_if_separately_admitted"], "read_prohibited_fields": ["operation_authorization_ref"], "write_required_fields": ["operation_authorization_ref"]},
            "official_export": {"allowed_effects": ["read", "download"], "prohibited_fields": ["operation_authorization_ref"]},
            "attended_manual": {"allowed_effects": ["none"], "prohibited_fields": ["operation_authorization_ref"]},
        },
        "fail_close_conditions": ["unknown_route", "stale_source", "expired_registration", "terms_mismatch", "quota_or_cost_rejection", "credential_scope_mismatch", "authorization_scope_mismatch"],
        "non_implication": ["read_does_not_imply_write", "route_success_does_not_grant_next_operation", "route_success_does_not_grant_release", "official_failure_does_not_imply_browser_fallback", "attended_handoff_does_not_equal_automation_success"],
        "browser_boundary": {"policy_ref": "external_browser_automation_route_policy", "implicit_fallback": "prohibited", "consumer_ui_unattended": "prohibited"},
        "registration_values_in_policy": "prohibited",
        "design_later": ["route_registry_storage", "connector_adapters", "capability_discovery_and_cache", "terms_freshness_adapter", "pagination_and_retry", "receipt_storage"],
        "prohibited_inheritance": ["mcp_first_for_all_media", "fixed_provider", "legacy_route_success", "legacy_phase_as_permission", "browser_fallback_on_rejection", "credential_or_terms_inference"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("official_api_route_authority_policy")
    faults = [] if policy == expected else ["official API route authority policyがtyped registry/fail-close exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("official API route record実semantic contentがcode正本と不一致")
    actual_projection = {"route_precedence": pod_facts.get("route_priority"), "permission_scope": pod_facts.get("permission_scope")}
    if pod1.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or actual_projection != expected["decision_binding"]["route_projection"]:
        faults.append("official API routeのPOD-001 projectionが不一致")
    universe = policy.get("route_registry_field_universe", []) if isinstance(policy, dict) else []
    if not isinstance(universe, list) or not all(isinstance(value, str) and value for value in universe) or len(universe) != len(set(universe)):
        faults.append("official API route registry field universeがtyped uniqueでない")
    return faults


def genai_execution_route_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """生成routeをprovider-neutralにしconsumer UI無人操作とpublish authorityを排除する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("GENAI-EXECUTION-ROUTE", {})
    source_ids = ("RDE-000006", "RDE-000024", "RDE-000025", "RDE-000043", "RDE-000044")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    fields = ["attempt_id", "profile_id", "account_id", "provider_id", "model_or_capability_id", "operation", "effect", "route_kind", "route_registration_revision", "route_semantic_digest", "terms_revision_digest", "credential_scope_digest", "quota_cost_policy_digest", "authorization_grant_digest", "operation_authorization_ref", "activation_scope_digest", "input_digest", "prompt_or_instruction_digest", "data_handling_policy_digest", "risk_gate_receipt", "quality_gate_receipt", "request_receipt_digest", "response_digest", "output_lineage_digest", "confirmation_target_digest", "confirmation_evidence_digest", "handoff_reason", "handoff_authority_digest", "attended_handoff_receipt", "publication_authorization_ref"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    generation_required = [field for field in fields if field not in {"confirmation_target_digest", "confirmation_evidence_digest", "handoff_reason", "handoff_authority_digest", "attended_handoff_receipt", "publication_authorization_ref"}]
    confirmation_required = ["attempt_id", "profile_id", "account_id", "operation", "effect", "route_kind", "route_registration_revision", "route_semantic_digest", "terms_revision_digest", "authorization_grant_digest", "confirmation_target_digest", "request_receipt_digest", "confirmation_evidence_digest"]
    handoff_required = ["attempt_id", "profile_id", "account_id", "operation", "effect", "route_kind", "terms_revision_digest", "authorization_grant_digest", "handoff_reason", "handoff_authority_digest", "attended_handoff_receipt"]
    pod1 = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-001", {})
    pod_facts = pod1.get("facts", {}) if isinstance(pod1, dict) else {}
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "execution_authorized": False, "publication_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:37d8371bbc7053ae3168627da6c58b39cc44c9816d5bf5904fdd6bfef8e5d755", "refinement_record_content_digest": "sha256:c2c6d20e4773015d50d0d4f0f533fea1ece53fbd1db9b7aeb2c892b43ad48da3",
        "decision_binding": {"decision_snapshot_digest": "sha256:a108c02eba247caec3c66fa58b183bcfeafbfead26e888ede4b2aa74ddbe80ea", "route_projection": {"route_precedence": ["official_api", "official_mcp"], "browser_engine": "playwright", "browser_roles": ["capability_fallback", "read_confirmation"]}},
        "parent_semantic_digests": {
            "official_route": _digest(refinements.get("official_api_route_authority_policy")), "browser_boundary": _digest(refinements.get("external_browser_automation_route_policy")), "provider_neutral_execution": _digest(refinements.get("provider_neutral_execution_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy")), "activation": _digest(records.get("AUTOMATED-PUBLISHING-ADMISSION")), "credential": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")), "rate_quota_cost": _digest(refinements.get("rate_quota_cost_policy")), "content_risk": _digest(records.get("CONTENT-RISK-CLASSIFICATION")), "content_quality": _digest(records.get("CONTENT-QUALITY-GATE-LEARNING")), "product_state": _digest(refinements.get("product_state_authority_policy")),
        },
        "attempt_field_universe": fields,
        "route_contracts": {
            "official_api": {**partition(generation_required), "business_operation": "generate", "parent_route_effect": "external_write_if_separately_admitted", "required_authorities": ["route", "operation_authorization", "credential", "quota_cost", "authorization", "activation", "risk", "quality"]},
            "official_mcp": {**partition(generation_required), "business_operation": "generate", "parent_route_effect": "external_write_if_separately_admitted", "required_authorities": ["route", "operation_authorization", "credential", "quota_cost", "authorization", "activation", "risk", "quality"]},
            "registered_cli": {**partition(generation_required), "business_operation": "generate", "parent_route_effect": "external_write_if_separately_admitted", "adoption": "separate_po_ratified_registration", "runtime_dependency": "optional_not_required"},
            "playwright_confirmation": {**partition(confirmation_required), "allowed_effects": ["read_confirmation"], "authority_result": "confirmation_only"},
            "attended_manual": {**partition(handoff_required), "allowed_effects": ["none"], "authority_result": "handoff_only_not_generation_success"},
        },
        "provider_contract": {"selection": "provider_neutral_registration", "fixed_provider": "prohibited", "codex_or_claude_runtime_required": "prohibited", "consumer_web_ui_unattended": "prohibited"},
        "fail_close_conditions": ["unknown_or_unregistered_route", "stale_terms", "credential_scope_mismatch", "quota_or_cost_rejection", "authorization_or_activation_mismatch", "risk_or_quality_gate_missing", "data_handling_policy_missing"],
        "non_implication": ["generation_response_does_not_grant_publish", "generation_response_does_not_change_product_state", "generation_success_does_not_grant_next_attempt", "confirmation_does_not_grant_generation", "attended_handoff_does_not_equal_success"],
        "fallback_contract": {"api_or_mcp_failure": "fail_close", "registered_cli": "separate_admission_only", "attended_manual": "evidenced_handoff_only", "consumer_web_ui": "prohibited"},
        "registration_values_in_policy": "prohibited",
        "design_later": ["provider_adapters", "streaming_and_retry", "response_normalization", "redaction", "cache", "runtime_integration"],
        "prohibited_inheritance": ["consumer_web_ui_unattended", "codex_or_claude_required_runtime", "fixed_provider_or_model", "legacy_browser_generation_success", "response_as_publish_authority", "credential_or_quota_bypass", "legacy_phase_as_permission"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("genai_execution_route_policy")
    faults = [] if policy == expected else ["GENAI execution route policyがprovider-neutral/consumer UI禁止/publish非含意exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("GENAI route record実semantic contentがcode正本と不一致")
    projection = {"route_precedence": pod_facts.get("route_priority"), "browser_engine": pod_facts.get("browser_engine"), "browser_roles": pod_facts.get("browser_roles")}
    if pod1.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or projection != expected["decision_binding"]["route_projection"]:
        faults.append("GENAI route POD-001 projectionが不一致")
    universe = policy.get("attempt_field_universe", []) if isinstance(policy, dict) else []
    universe_valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not universe_valid:
        faults.append("GENAI attempt field universeがtyped uniqueでない")
    contracts = policy.get("route_contracts", {}) if isinstance(policy, dict) else {}
    for route, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (universe_valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"GENAI {route} attempt partitionが閉じていない")
    return faults


def automated_publishing_admission_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """初回scope activation後のgate合格自動運用と停止・再activationを閉じる。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("AUTOMATED-PUBLISHING-ADMISSION", {})
    old_record = records.get("AUTO-MODE-DECISION-AUTHORITY", {})
    source_ids = ("RDE-000138", "RDE-000144", "RDE-000150", "RDE-000154", "RDE-000155")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    controls = refinements.get("captured_po_decision_controls", {})
    pod_ids = ("POD-20260815-003", "POD-20260815-004", "POD-20260815-006", "POD-20260815-009")
    pod_facts = {key: controls.get(key, {}).get("facts", {}) for key in pod_ids}
    decision_projections = {
        "POD-20260815-003": {"activation_authority": "authenticated_ui_explicit_user_decision", "activation_notice": "vps_ui_inbox", "per_post_approval_required": False, "per_artifact_admission": ["purpose_gate", "risk_gate", "quality_gate"], "failure_action": "deny_external_write"},
        "POD-20260815-004": {"admission_order": ["generate", "machine_gate", "regenerate_or_fix", "machine_regate", "human_review_or_next_stage"], "failed_artifact_human_review": "prohibited", "pass_required_before_progress": True},
        "POD-20260815-006": {"rule_update_actor": "ai_within_mandatory_risk_boundary", "risk_unknown_default": "highest_applicable_strictness", "user_preference_can_weaken_mandatory_risk": False, "published_update_condition": "explicit_update_in_place_capability_and_gate_pass", "unsupported_update_action": "no_action_including_notification"},
        "POD-20260815-009": {"ordinary_failed_retry_notification": "none", "retry_exhaustion_state": "blocked", "retry_exhaustion_notification": "vps_ui_inbox", "notification_failure_state_effect": "no_rollback", "unsupported_published_update_action": "no_action_including_notification"},
    }
    fields = ["attempt_id", "activation_decision_id", "activation_scope_revision", "activation_scope_semantic_digest", "profile_id", "media_id", "account_id", "campaign_id", "operation", "effect", "authorization_grant_digest", "credential_scope_digest", "quota_cost_policy_digest", "route_semantic_digest", "rule_set_revision", "rule_set_semantic_digest", "content_purpose_digest", "funnel_role_digest", "risk_gate_receipt", "quality_gate_receipt", "source_artifact_digest", "retry_budget_revision", "retry_budget_digest", "attempt_no", "gate_verdict", "gate_evidence_digest", "prior_state_revision", "result_state_revision", "result_receipt_digest", "inbox_item_receipt", "notification_receipt", "update_in_place_capability_digest"]
    common = fields[:21] + ["prior_state_revision"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "external_write_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:4e3df9a130b8c7b919b6eb5dafe68112d84bfc3210cc1538c991c1db24c74313", "refinement_record_content_digest": "sha256:250b9664cec7ef16a8285b625d414a4c1fda1ee5916a83faddc7ff39b85b0c61",
        "superseded_record_binding": {"subject_id": "AUTO-MODE-DECISION-AUTHORITY", "record_digest": _digest(old_record), "lifecycle_status": "superseded", "replacement_subject_id": "AUTOMATED-PUBLISHING-ADMISSION", "positive_authority": "prohibited"},
        "decision_bindings": {key: {"decision_snapshot_digest": controls.get(key, {}).get("decision_snapshot_digest"), "facts_projection": decision_projections[key]} for key in pod_ids},
        "parent_semantic_digests": {"vps_ui": _digest(refinements.get("vps_ui_primary_interface_policy")), "inbox": _digest(records.get("VPS-UI-INBOX-LIFECYCLE")), "notification": _digest(refinements.get("fr16_notification_boundary_policy")), "content_quality": _digest(records.get("CONTENT-QUALITY-GATE-LEARNING")), "content_risk": _digest(records.get("CONTENT-RISK-CLASSIFICATION")), "product_state": _digest(refinements.get("product_state_authority_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy")), "credential": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")), "quota_cost": _digest(refinements.get("rate_quota_cost_policy")), "official_route": _digest(refinements.get("official_api_route_authority_policy"))},
        "attempt_field_universe": fields,
        "outcome_contracts": {
            "gate_pass_auto_operation": {**partition(common + ["gate_verdict", "gate_evidence_digest", "result_state_revision", "result_receipt_digest"]), "value_contract": {"gate_verdict": "pass", "effect": "scope_bound_external_write", "result_revision_relation": "greater_than_prior", "result_receipt": "authorized_effect_result"}, "requires_activation": True},
            "gate_fail_regenerate": {**partition(common + ["retry_budget_revision", "retry_budget_digest", "attempt_no", "gate_verdict", "gate_evidence_digest", "result_state_revision", "result_receipt_digest"]), "value_contract": {"gate_verdict": "fail", "effect": "none", "result_revision_relation": "equal_to_prior", "result_receipt": "no_effect_and_regeneration_required"}, "human_review_before_regeneration": "prohibited", "notification": "none"},
            "retry_exhausted_blocked": {**partition(common + ["retry_budget_revision", "retry_budget_digest", "attempt_no", "gate_verdict", "gate_evidence_digest", "result_state_revision", "result_receipt_digest", "inbox_item_receipt", "notification_receipt"]), "value_contract": {"gate_verdict": "fail", "retry_budget": "exhausted", "target_state": "blocked", "result_revision_relation": "greater_than_prior", "notification_failure_revision_relation": "equal_to_committed_blocked_revision"}, "notification_route": "vps_ui_inbox", "notification_failure": "no_rollback"},
            "unsupported_update_non_action": {**partition(common + ["gate_verdict", "gate_evidence_digest", "result_state_revision", "result_receipt_digest", "update_in_place_capability_digest"]), "value_contract": {"update_capability": "unsupported", "effect": "none", "result_revision_relation": "equal_to_prior", "result_receipt": "no_action"}, "notification": "none"},
        },
        "activation_contract": {"initial_scope_activation": "explicit_authenticated_ui_decision", "scope_expansion": "new_explicit_decision", "stop_or_revocation": "external_write_stopped", "resume": "explicit_scope_redisplay_and_reactivation", "machine_eligibility": "not_authority", "inbox_seen_or_ack": "not_authority"},
        "rule_update_contract": {"external_revision_required": True, "scope_expansion": "prohibited", "mandatory_risk_weakening": "prohibited", "unknown_risk": "highest_applicable_strictness"},
        "registration_values_in_policy": "prohibited",
        "design_later": ["scheduler", "state_machine", "queue_and_backoff", "rule_storage", "vps_ui_presentation"],
        "prohibited_inheritance": ["legacy_auto_mode_expiry", "machine_eligibility_as_activation", "per_post_approval", "failed_artifact_human_review", "ordinary_retry_notification", "notification_failure_rollback", "feedback_scope_expansion", "unsupported_update_notification", "legacy_phase_as_permission"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("automated_publishing_admission_policy")
    faults = [] if policy == expected else ["automated publishing admission policyがscope activation/gate/regeneration/inbox exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("automated publishing record実semantic contentがcode正本と不一致")
    for pod_id in pod_ids:
        if pod_facts[pod_id] != decision_projections[pod_id]:
            faults.append(f"automated publishing {pod_id} facts projectionが不一致")
    universe = policy.get("attempt_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("automated publishing attempt universeがtyped uniqueでない")
    contracts = policy.get("outcome_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"automated publishing {name} field partitionが閉じていない")
    return faults


def content_quality_gate_learning_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """content quality検査・再生成・scope付き外部rule学習を分離する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("CONTENT-QUALITY-GATE-LEARNING", {})
    source_ids = ("RDE-000139", "RDE-000145", "RDE-000151", "RDE-000163", "RDE-000164")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    controls = refinements.get("captured_po_decision_controls", {})
    pod_ids = ("POD-20260815-004", "POD-20260815-005", "POD-20260815-006", "POD-20260815-007", "POD-20260815-009")
    facts = {key: controls.get(key, {}).get("facts", {}) for key in pod_ids}
    decision_snapshots = {"POD-20260815-004": "sha256:f86634ab8eb788d10d9358cb9b46867af6ac03429c1c864afc8f0dc4057b3095", "POD-20260815-005": "sha256:a4fd5638143c7f4e39c087661f5ad8eefc3157c4cf632560485453426c310a8f", "POD-20260815-006": "sha256:b671f888a338c953ba1aecd9da4b62d7abfde6b0dc91f677cfd061628885ad84", "POD-20260815-007": "sha256:e3c945cb184f6c12c252626660f8a9e73d43ec7b327c92e7cb456f31fc8f790c", "POD-20260815-009": "sha256:2e85fb60a138d12aaeafb9f0152bef194905bf48c1659eb01acaa30a776572af"}
    fact_projections = {
        "POD-20260815-004": {"admission_order": ["generate", "machine_gate", "regenerate_or_fix", "machine_regate", "human_review_or_next_stage"], "failed_artifact_human_review": "prohibited", "pass_required_before_progress": True},
        "POD-20260815-005": {"feedback_storage": "externalized_structured_versioned_rule", "explicit_scope_actor": "user", "missing_scope_default": "source_feedback.media_account_id", "implicit_scope_expansion": "prohibited", "derived_scope_evidence": ["source_feedback_id", "media_account_id"]},
        "POD-20260815-006": {"rule_update_actor": "ai_within_mandatory_risk_boundary", "risk_unknown_default": "highest_applicable_strictness", "user_preference_can_weaken_mandatory_risk": False, "published_update_condition": "explicit_update_in_place_capability_and_gate_pass", "unsupported_update_action": "no_action_including_notification"},
        "POD-20260815-007": {"research_timing": "before_content_creation", "media_role_authority": "offer_funnel_stage", "growth_feedback": ["research", "plan", "funnel", "rule", "hypothesis"], "offer_mutation": "capability_and_authority_dependent", "paid_acquisition_phase": "ultra_late_deferred"},
        "POD-20260815-009": {"ordinary_failed_retry_notification": "none", "retry_exhaustion_state": "blocked", "retry_exhaustion_notification": "vps_ui_inbox", "notification_failure_state_effect": "no_rollback", "unsupported_published_update_action": "no_action_including_notification"},
    }
    dimensions = ["prohibited_terms", "expression", "format_and_type", "source_and_factual_support", "audience_utility", "original_research_analysis_or_experience", "claim_source_alignment_and_freshness", "non_exaggerated_heading"]
    dimension_fields = ["dimension", "disposition", "verdict", "finding_ids_digest", "evidence_digest", "na_reason", "decision_owner_subject_id", "review_trigger", "defer_reason", "resume_conditions"]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "publication_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721", "refinement_record_content_digest": "sha256:fc1996c50941f4cebf50ca8c8ff75cea5c76a9598b235ca0cec902699797ac84",
        "decision_bindings": {key: {"decision_snapshot_digest": decision_snapshots[key], "facts_projection": fact_projections[key]} for key in pod_ids},
        "parent_semantic_digests": {"automated_publishing": _digest(refinements.get("automated_publishing_admission_policy")), "content_risk": _digest(records.get("CONTENT-RISK-CLASSIFICATION")), "vps_inbox": _digest(records.get("VPS-UI-INBOX-LIFECYCLE")), "notification": _digest(refinements.get("fr16_notification_boundary_policy")), "product_state": _digest(refinements.get("product_state_authority_policy"))},
        "quality_dimensions": dimensions,
        "quality_dimension_coverage_digest": _digest(dimensions),
        "dimension_field_universe": dimension_fields,
        "dimension_disposition_contracts": {
            "direct": {"required": ["dimension", "disposition", "verdict", "finding_ids_digest", "evidence_digest"], "prohibited": ["na_reason", "decision_owner_subject_id", "review_trigger", "defer_reason", "resume_conditions"]},
            "not_applicable": {"required": ["dimension", "disposition", "na_reason", "decision_owner_subject_id", "review_trigger"], "prohibited": ["verdict", "finding_ids_digest", "evidence_digest", "defer_reason", "resume_conditions"]},
            "deferred": {"required": ["dimension", "disposition", "defer_reason", "decision_owner_subject_id", "resume_conditions"], "prohibited": ["verdict", "finding_ids_digest", "evidence_digest", "na_reason", "review_trigger"]},
        },
        "dimension_coverage_contract": {"exact_dimensions": dimensions, "generic_na": "prohibited", "missing_or_duplicate_dimension": "fail_close", "unclassified_dimension": "deferred_not_pass"},
        "artifact_binding_fields": ["artifact_id", "source_identity_digest", "media_id", "media_account_id", "purpose_digest", "funnel_role_digest", "risk_class", "ymyl_applicability", "brand_policy_digest", "user_preference_digest", "rule_set_id", "rule_revision", "rule_semantic_digest", "quality_dimension_results_digest", "finding_ids_digest", "verdict", "evidence_digest", "regeneration_lineage_digest"],
        "verdict_contract": {"pass": "next_stage_candidate_only_not_publish_authority", "fail": "no_review_no_next_stage_no_publish", "regenerate": "same_rule_revision_within_registered_budget", "exhausted": "blocked_then_vps_inbox_no_rollback"},
        "feedback_scope_contract": {"explicit_scope_actor": "user", "missing_scope_default": "source_feedback.media_account_id", "derived_scope_evidence": ["source_feedback_id", "media_account_id"], "same_media_other_account": "prohibited", "profile_or_global_expansion": "prohibited", "activation_scope_expansion": "prohibited"},
        "rule_update_contract": {"storage": "externalized_structured_versioned_rule", "actor": "ai_within_mandatory_risk_boundary", "mandatory_risk_priority": "highest", "account_rule_priority": "after_mandatory_risk", "feedback_rule_priority": "after_account_rule", "retry_series_revision": "frozen", "rollback_evidence": "required"},
        "strictness_contract": {"unknown_risk": "highest_applicable_strictness", "user_preference_can_weaken_mandatory_risk": False, "brand_or_ymyl_weakening": "prohibited"},
        "growth_non_implication": {"quality_pass": "not_growth_evidence", "research_plan_funnel_hypothesis": "separate_authority"},
        "published_update_contract": {"requires": ["explicit_update_in_place_capability", "gate_pass", "scope_authority"], "unsupported": "no_action_including_notification"},
        "registration_values_in_policy": "prohibited",
        "design_later": ["lint_engine", "rule_storage_and_index", "finding_ui", "regeneration_adapter"],
        "prohibited_inheritance": ["failed_artifact_human_review", "scope_missing_global_default", "retry_rule_self_weakening", "infinite_retry", "unknown_budget_continue", "quality_pass_as_publish_or_growth_authority", "hard_coded_rules", "ordinary_retry_notification", "notification_failure_rollback", "legacy_phase_as_permission"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("content_quality_gate_learning_policy")
    faults = [] if policy == expected else ["content quality gate learning policyが検査・再生成・scope rule exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("content quality record実semantic contentがcode正本と不一致")
    for pod_id in pod_ids:
        if controls.get(pod_id, {}).get("decision_snapshot_digest") != decision_snapshots[pod_id] or facts[pod_id] != fact_projections[pod_id]:
            faults.append(f"content quality {pod_id} decision projectionが不一致")
    contracts = policy.get("dimension_disposition_contracts", {}) if isinstance(policy, dict) else {}
    universe = policy.get("dimension_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("content quality dimension field universeがtyped uniqueでない")
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"content quality {name} dimension partitionが閉じていない")
    return faults


def content_risk_classification_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """claim risk/YMYL/不確実性をstrictness・gate・HJへ束縛する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("CONTENT-RISK-CLASSIFICATION", {})
    source_ids = ("RDE-000140", "RDE-000146", "RDE-000152")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-006", {})
    facts = {"rule_update_actor": "ai_within_mandatory_risk_boundary", "risk_unknown_default": "highest_applicable_strictness", "user_preference_can_weaken_mandatory_risk": False, "published_update_condition": "explicit_update_in_place_capability_and_gate_pass", "unsupported_update_action": "no_action_including_notification"}
    domains = ["health", "financial_stability", "safety", "social_welfare_or_well_being"]
    dimension_fields = ["risk_domain", "disposition", "risk_class", "strictness", "rationale_digest", "source_evidence_digest", "source_freshness_digest", "required_gate_set_digest", "human_judgement_required", "human_judgement_owner_subject_id", "na_reason", "review_trigger", "defer_reason", "resume_conditions"]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "classification_authorized": False, "publication_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:4ba4a208fcc0dcdcd551be40c81eadc31b75f311fa8274f8d8dfe66b20b88c49", "refinement_record_content_digest": "sha256:497141027daf214a5ca0febce0db3282c90393a1ed85bb4966136f9f0ad8715c",
        "decision_binding": {"decision_snapshot_digest": "sha256:b671f888a338c953ba1aecd9da4b62d7abfde6b0dc91f677cfd061628885ad84", "facts_projection": facts},
        "parent_semantic_digests": {"content_quality": _digest(refinements.get("content_quality_gate_learning_policy")), "automated_publishing": _digest(refinements.get("automated_publishing_admission_policy")), "product_state": _digest(refinements.get("product_state_authority_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy"))},
        "risk_domains": domains, "risk_domain_coverage_digest": _digest(domains), "dimension_field_universe": dimension_fields,
        "dimension_disposition_contracts": {
            "direct": {"required": ["risk_domain", "disposition", "risk_class", "strictness", "rationale_digest", "source_evidence_digest", "source_freshness_digest", "required_gate_set_digest", "human_judgement_required", "human_judgement_owner_subject_id"], "prohibited": ["na_reason", "review_trigger", "defer_reason", "resume_conditions"]},
            "not_applicable": {"required": ["risk_domain", "disposition", "na_reason", "human_judgement_owner_subject_id", "review_trigger"], "prohibited": ["risk_class", "strictness", "rationale_digest", "source_evidence_digest", "source_freshness_digest", "required_gate_set_digest", "human_judgement_required", "defer_reason", "resume_conditions"]},
            "deferred": {"required": ["risk_domain", "disposition", "defer_reason", "human_judgement_owner_subject_id", "resume_conditions"], "prohibited": ["risk_class", "strictness", "rationale_digest", "source_evidence_digest", "source_freshness_digest", "required_gate_set_digest", "human_judgement_required", "na_reason", "review_trigger"]},
        },
        "classification_contract": {"unknown_or_missing": "deferred_and_highest_applicable_strictness_not_pass", "ymyl_applicable": "mandatory_stricter_gate_set", "human_judgement_required": "cannot_be_replaced_by_ai", "source_freshness_missing": "fail_close", "diagnostic_read": "allowed_without_progress"},
        "strictness_contract": {"user_preference_can_weaken_mandatory_risk": False, "feedback_or_growth_can_weaken_mandatory_risk": False, "brand_policy_can_weaken_ymyl": False, "unknown_default": "highest_applicable_strictness"},
        "non_implication": ["risk_pass_does_not_grant_publish", "risk_pass_does_not_change_product_state", "risk_pass_is_not_growth_evidence", "classifier_result_does_not_replace_human_judgement"],
        "artifact_binding_fields": ["artifact_id", "claim_id", "source_identity_digest", "profile_id", "media_id", "media_account_id", "purpose_digest", "funnel_role_digest", "offer_digest", "audience_digest", "brand_policy_revision_digest", "user_preference_revision_digest", "classifier_revision_digest", "risk_domain_results_digest", "required_quality_dimensions_digest", "verdict", "evidence_digest"],
        "registration_values_in_policy": "prohibited", "design_later": ["risk_classifier", "evidence_retrieval", "vps_ui_diagnostic_presentation", "cache"],
        "prohibited_inheritance": ["unknown_as_low_risk", "generic_ymyl_na", "preference_weakens_mandatory_gate", "ai_replaces_required_human_judgement", "stale_source_evidence", "risk_pass_as_publish_state_or_growth_authority", "fixed_threshold_or_provider", "legacy_phase_as_permission"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("content_risk_classification_policy")
    faults = [] if policy == expected else ["content risk classification policyがYMYL/strictness/HJ exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("content risk record実semantic contentがcode正本と不一致")
    if control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or control.get("facts") != facts:
        faults.append("content risk POD-006 decision projectionが不一致")
    universe = policy.get("dimension_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("content risk dimension field universeがtyped uniqueでない")
    contracts = policy.get("dimension_disposition_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"content risk {name} dimension partitionが閉じていない")
    return faults


def research_led_content_growth_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """research→仮説→媒体role→測定→TLP学習をstrategy authorityから分離する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("RESEARCH-LED-CONTENT-GROWTH", {})
    source_ids = ("RDE-000141", "RDE-000147", "RDE-000153")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-007", {})
    facts = {"research_timing": "before_content_creation", "media_role_authority": "offer_funnel_stage", "growth_feedback": ["research", "plan", "funnel", "rule", "hypothesis"], "offer_mutation": "capability_and_authority_dependent", "paid_acquisition_phase": "ultra_late_deferred"}
    fields = ["growth_cycle_id", "profile_id", "media_id", "media_account_id", "campaign_id", "offer_id", "offer_revision", "offer_authority_digest", "offer_mutability", "funnel_stage", "media_role", "audience_digest", "research_brief_digest", "research_source_digest", "research_source_freshness_digest", "research_evidence_digest", "original_value_statement_digest", "hypothesis_id", "hypothesis_revision", "hypothesis_digest", "kpi_profile_revision_digest", "measurement_environment_digest", "measurement_window", "baseline_evidence_digest", "observation_evidence_digest", "attribution_scope_digest", "uncertainty_digest", "outcome", "human_judgement_owner_subject_id", "tlp_feedback_digest", "decision_receipt_digest", "prior_learning_revision", "result_learning_revision", "result_receipt_digest", "paid_acquisition_authorization_ref"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    identity = fields[:12]
    research = identity + fields[12:17]
    hypothesis = research + fields[17:20]
    measurement = hypothesis + fields[20:27]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "strategy_mutation_authorized": False, "paid_acquisition_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:ea8db288dc6dd44db103766832cb6d8f73862e5de15c21c18fa0b43087e50b9e", "refinement_record_content_digest": "sha256:cb6a44673ee8d0fd20b1799f83102e36812ca236b5e1af7fbb484bb1c1646067",
        "decision_binding": {"decision_snapshot_digest": "sha256:e3c945cb184f6c12c252626660f8a9e73d43ec7b327c92e7cb456f31fc8f790c", "facts_projection": facts},
        "parent_semantic_digests": {"content_quality": _digest(refinements.get("content_quality_gate_learning_policy")), "content_risk": _digest(refinements.get("content_risk_classification_policy")), "strategy_admission": _digest(refinements.get("strategy_requirement_admission_policy")), "strategy_authority_record": _digest(records.get("STRATEGY-REQUIREMENT-ADMISSION"))},
        "cycle_field_universe": fields,
        "outcome_contracts": {
            "research_complete": {**partition(research + ["outcome", "human_judgement_owner_subject_id", "result_receipt_digest"]), "value_contract": {"outcome": "research_candidate", "content_creation_authority": "not_granted"}},
            "hypothesis_candidate": {**partition(hypothesis + ["outcome", "human_judgement_owner_subject_id", "result_receipt_digest"]), "value_contract": {"outcome": "hypothesis_candidate", "proof": "not_established"}},
            "measurement_observed": {**partition(measurement + ["outcome", "human_judgement_owner_subject_id", "result_receipt_digest"]), "value_contract": {"outcome": "observation_only", "hypothesis_proven": "not_implied"}},
            "learning_proposal": {**partition(measurement + ["outcome", "human_judgement_owner_subject_id", "tlp_feedback_digest", "decision_receipt_digest", "prior_learning_revision", "result_learning_revision", "result_receipt_digest"]), "value_contract": {"outcome": ["retain", "revise", "defer", "stop_operation"], "strategy_update_route": "tlp_only", "result_revision_relation": "greater_than_prior_after_authorized_decision"}},
        },
        "evidence_non_implication": ["quality_pass_is_not_growth_evidence", "risk_pass_is_not_growth_evidence", "publication_success_does_not_prove_hypothesis", "single_media_result_not_cross_media_evidence", "observation_does_not_self_authorize_strategy_change"],
        "offer_contract": {"mutation": "capability_and_authority_dependent", "immutable_or_unknown": "no_mutation", "selection_or_replacement": "human_judgement_and_receipt"},
        "measurement_contract": {"kpi_threshold_window_freshness_hypothesis_period_exploration": "profile_offer_funnel_media_campaign_risk_source_registration", "missing_environment_or_window": "deferred_not_success", "degradation": ["re_research", "revise_hypothesis", "stop_operation"]},
        "paid_acquisition_contract": {"phase": "ultra_late_deferred", "current": "disabled", "resume": "separate_po_requirement_and_authorization"},
        "strategy_feedback_contract": {"direct_upstream_mutation": "prohibited", "route": "tlp_only", "human_adoption_required": True},
        "registration_values_in_policy": "prohibited", "design_later": ["research_connectors", "analytics_ingestion", "experiment_scheduler", "dashboard"],
        "prohibited_inheritance": ["researchless_content_generation", "quality_or_risk_pass_as_growth", "publish_success_as_proof", "cross_media_evidence_reuse", "unauthorized_offer_mutation", "paid_acquisition_early", "direct_strategy_mutation", "legacy_browser_provider_or_phase_success"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("research_led_content_growth_policy")
    faults = [] if policy == expected else ["research-led content growth policyがresearch/funnel/media/KPI/TLP exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("research-led growth record実semantic contentがcode正本と不一致")
    if control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or control.get("facts") != facts:
        faults.append("research-led growth POD-007 projectionが不一致")
    universe = policy.get("cycle_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("research growth cycle field universeがtyped uniqueでない")
    contracts = policy.get("outcome_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"research growth {name} field partitionが閉じていない")
    return faults


def discord_community_marketing_route_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """Discordをcommunity marketingだけのBot capabilityへ限定する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("DISCORD-COMMUNITY-MARKETING-ROUTE", {})
    source_ids = ("RDE-000137", "RDE-000143", "RDE-000149")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-002", {})
    facts = {"product_notification_route": "vps_ui_inbox", "discord_role": "community_marketing_only", "discord_prohibited_purposes": ["product_approval_notification", "operational_notification", "developer_pr_notification"]}
    fields = ["attempt_id", "profile_id", "media_id", "media_account_id", "discord_app_id", "bot_principal_id", "guild_id", "channel_id", "community_identity_digest", "purpose", "funnel_stage", "media_role", "operation", "effect", "route_registration_revision", "route_semantic_digest", "terms_revision_digest", "authorization_grant_digest", "activation_scope_digest", "credential_scope_digest", "quota_cost_policy_digest", "risk_gate_receipt", "quality_gate_receipt", "research_hypothesis_digest", "kpi_profile_digest", "message_id", "thread_id", "reply_to_message_id", "moderation_policy_digest", "human_judgement_owner_subject_id", "request_receipt_digest", "result_or_evidence_receipt_digest", "handoff_receipt_digest"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    base = fields[:25]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "execution_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:70c0b5ab8cf5b8a163454726f2b18a0e4d4db23eeff4974409ae260358d81134", "refinement_record_content_digest": "sha256:503662daf79503a4651a33e1bf81e17319104719f445f61e9a0cb2d17c4f8b3c",
        "decision_binding": {"decision_snapshot_digest": "sha256:29756112668435ad619ca819beb41e4fdfdbce8a9e3e85ada82cfdb495ccd624", "facts_projection": facts},
        "parent_semantic_digests": {"notification_rejection": _digest(refinements.get("discord_notification_rejection_policy")), "research_growth": _digest(refinements.get("research_led_content_growth_policy")), "content_quality": _digest(refinements.get("content_quality_gate_learning_policy")), "content_risk": _digest(refinements.get("content_risk_classification_policy")), "official_route": _digest(refinements.get("official_api_route_authority_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy")), "activation": _digest(refinements.get("automated_publishing_admission_policy")), "credential": _digest(records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY")), "quota_cost": _digest(refinements.get("rate_quota_cost_policy"))},
        "attempt_field_universe": fields,
        "operation_contracts": {
            "read_or_listen": {**partition(base + ["message_id", "thread_id", "request_receipt_digest", "result_or_evidence_receipt_digest"]), "allowed_effect": "read", "growth_authority": "none"},
            "community_post": {**partition(base + ["message_id", "thread_id", "request_receipt_digest", "result_or_evidence_receipt_digest"]), "allowed_effect": "community_external_write", "reply_to_message_id": "prohibited", "requires": ["bot_principal", "registered_guild_channel_operation", "activation", "risk", "quality"]},
            "community_reply": {**partition(base + ["message_id", "thread_id", "reply_to_message_id", "request_receipt_digest", "result_or_evidence_receipt_digest"]), "allowed_effect": "community_external_write", "reply_target_contract": {"reply_to_message_id": "required", "target_guild_channel_thread_scope": "exact", "cross_thread_or_channel": "prohibited"}, "requires": ["bot_principal", "registered_guild_channel_operation", "activation", "risk", "quality"]},
            "moderation_handoff": {**partition(base + ["message_id", "thread_id", "moderation_policy_digest", "human_judgement_owner_subject_id", "handoff_receipt_digest"]), "allowed_effect": "none", "authority_result": "human_moderation_required"},
        },
        "purpose_contract": {"allowed": ["community_marketing"], "prohibited": ["product_approval_notification", "operational_notification", "developer_pr_notification", "approval_deep_link_delivery"], "unknown": "fail_close"},
        "principal_contract": {"allowed": "registered_discord_bot_application", "self_bot": "prohibited", "personal_user_account_unattended": "prohibited"},
        "cross_purpose_separation": ["account", "guild", "channel", "credential", "policy", "evidence", "receipt"],
        "non_implication": ["post_success_does_not_prove_growth", "post_success_does_not_grant_offer_mutation", "post_success_does_not_change_product_state", "post_success_does_not_grant_next_operation", "moderation_handoff_does_not_equal_decision"],
        "registration_values_in_policy": "prohibited", "design_later": ["discord_adapter", "thread_mapping", "moderation_queue", "analytics_ingestion"],
        "prohibited_inheritance": ["discord_product_notification", "discord_approval_or_pr_tuple", "self_bot", "personal_account_browser_automation", "cross_purpose_credential_or_receipt", "unregistered_channel_write", "post_success_as_growth_or_authority", "legacy_browser_provider_or_phase_success"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("discord_community_marketing_route_policy")
    faults = [] if policy == expected else ["Discord community marketing route policyがpurpose/Bot/guild/channel/cross-purpose exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("Discord community record実semantic contentがcode正本と不一致")
    if control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or control.get("facts") != facts:
        faults.append("Discord community POD-002 projectionが不一致")
    universe = policy.get("attempt_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("Discord community attempt universeがtyped uniqueでない")
    contracts = policy.get("operation_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"Discord community {name} field partitionが閉じていない")
    return faults


def ratification_dependency_audit_faults(refinements: dict[str, Any]) -> list[str]:
    """未批准authorityのPO判断順序をSCCを保ったcandidate DAGとして固定する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    coverage = refinements.get("resolved_subject_authority_coverage_audit", {})
    stage0 = ["semantic_coverage_policy", "contract_semantic_descent_policy"]
    stage1 = ["business_profile_authorization_policy", "product_state_authority_policy", "rate_quota_cost_policy", "vps_ui_authentication_session_policy", "vps_credential_security_boundary_policy", "provider_neutral_execution_policy", "vps_ui_quality_attributes_policy", "strategy_requirement_admission_policy"]
    stage2 = ["vps_ui_primary_interface_policy", "vps_ui_inbox_lifecycle_policy", "fr16_notification_boundary_policy", "discord_notification_rejection_policy", "external_browser_automation_route_policy", "official_api_route_authority_policy", "genai_execution_route_policy", "automated_publishing_admission_policy", "content_quality_gate_learning_policy", "content_risk_classification_policy", "research_led_content_growth_policy", "discord_community_marketing_route_policy"]
    stage3 = ["wordpress_maintenance_boundaries_policy", "legacy_media_admission_composite"]
    core_parents = {
        "business_profile_authorization_policy": [],
        "product_state_authority_policy": ["business_profile_authorization_policy"],
        "rate_quota_cost_policy": ["business_profile_authorization_policy"],
        "vps_ui_authentication_session_policy": ["business_profile_authorization_policy", "product_state_authority_policy"],
        "vps_credential_security_boundary_policy": ["business_profile_authorization_policy", "product_state_authority_policy", "vps_ui_authentication_session_policy"],
        "provider_neutral_execution_policy": [],
        "vps_ui_quality_attributes_policy": ["business_profile_authorization_policy"],
        "strategy_requirement_admission_policy": [],
    }
    rows: list[dict[str, Any]] = []
    for authority in stage0:
        rows.append({"authority_id": authority, "stage_id": "semantic_governance", "scc_id": None, "parent_authority_ids": [], "semantic_digest": _digest(refinements.get(authority)), "ratification_state": "candidate_unratified", "ratification_readiness": "ready_for_po_consideration", "downstream_admission": "blocked", "implementation_authority": "not_granted", "external_write_authority": "not_granted"})
    for authority in stage1:
        readiness = "blocked_on_true_po_refinement" if authority in {"vps_ui_quality_attributes_policy", "strategy_requirement_admission_policy"} else "ready_for_po_consideration"
        rows.append({"authority_id": authority, "stage_id": "core_authority", "scc_id": None, "parent_authority_ids": stage0 + core_parents[authority], "semantic_digest": _digest(refinements.get(authority)), "ratification_state": "candidate_unratified", "ratification_readiness": readiness, "downstream_admission": "blocked", "implementation_authority": "not_granted", "external_write_authority": "not_granted"})
    for authority in stage2:
        rows.append({"authority_id": authority, "stage_id": "operational_semantic_scc", "scc_id": "SCC-OPERATIONAL-SEMANTICS", "parent_authority_ids": stage0 + stage1, "semantic_digest": _digest(refinements.get(authority)), "ratification_state": "candidate_unratified", "ratification_readiness": "blocked_on_foundation_prerequisites", "downstream_admission": "blocked_until_all_scc_members_and_foundations_ratified", "implementation_authority": "not_granted", "external_write_authority": "not_granted"})
    wp_children = ["wordpress_content_operations_policy", "wordpress_platform_maintenance_policy", "wordpress_security_maintenance_policy"]
    rows.append({"authority_id": "wordpress_maintenance_boundaries_policy", "stage_id": "release_and_legacy_composites", "scc_id": None, "parent_authority_ids": stage0 + wp_children, "semantic_digest": _digest(refinements.get("wordpress_maintenance_boundaries_policy")), "ratification_state": "candidate_unratified", "ratification_readiness": "blocked_on_child_ratification", "downstream_admission": "blocked", "implementation_authority": "not_granted", "external_write_authority": "not_granted"})
    rows.append({"authority_id": "legacy_media_admission_composite", "stage_id": "release_and_legacy_composites", "scc_id": None, "parent_authority_ids": stage0 + stage1 + stage2 + ["legacy_mr_meaning_inventory", "media_poc_scrum_release_policy"], "semantic_digest": _digest({"meaning_inventory": refinements.get("legacy_mr_meaning_inventory"), "runtime_admission": refinements.get("media_poc_scrum_release_policy")}), "ratification_state": "pending_po_classification", "ratification_readiness": "blocked_on_meaning_classification", "downstream_admission": "blocked", "implementation_authority": "not_granted", "external_write_authority": "not_granted"})
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "implementation_authorized": False, "external_write_authorized": False,
        "coverage_audit_digest": coverage.get("audit_digest"),
        "stage_order": ["semantic_governance", "core_authority", "operational_semantic_scc", "release_and_legacy_composites"],
        "stage_members": {"semantic_governance": stage0, "core_authority": stage1, "operational_semantic_scc": stage2, "release_and_legacy_composites": stage3},
        "authority_rows": rows, "authority_rows_digest": _digest(rows),
        "readiness_bindings": {
            "vps_ui_quality_attributes_policy": {"record_subject_id": "VPS-UI-QUALITY-ATTRIBUTES", "record_digest": _digest(records.get("VPS-UI-QUALITY-ATTRIBUTES")), "pending_resolution_digest": _digest(records.get("VPS-UI-QUALITY-ATTRIBUTES", {}).get("pending_resolution")), "resume_condition": "all_quality_attribute_applicability_threshold_and_na_decisions_po_resolved"},
            "strategy_requirement_admission_policy": {"record_subject_id": "STRATEGY-REQUIREMENT-ADMISSION", "record_digest": _digest(records.get("STRATEGY-REQUIREMENT-ADMISSION")), "pending_resolution_digest": _digest(records.get("STRATEGY-REQUIREMENT-ADMISSION", {}).get("pending_resolution")), "resume_condition": "sr_descent_and_unique_test_authority_po_resolved", "parent_closure_digests": {"l0": _digest(refinements.get("l0_north_star_authority_normalization_policy")), "test_id": _digest(refinements.get("test_id_authority_alignment_policy")), "strategy_meaning_inventory": _digest(refinements.get("legacy_strategy_quality_meaning_inventory"))}},
        },
        "scc_contract": {"SCC-OPERATIONAL-SEMANTICS": {"members": stage2, "member_ratification": "individual_po_decision", "downstream_ready": "only_after_all_members_ratified", "partial_ready": "prohibited", "split_requires": "stable_interface_projection_requirement_revision"}},
        "historical_exclusions": ["DISCORD-MULTI-PURPOSE-BOUNDARIES", "AUTO-MODE-DECISION-AUTHORITY", "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE"],
        "composite_contracts": {"wordpress": {"child_policies": wp_children, "all_child_ratification_required": True}, "legacy_media": {"ordered_roles": ["legacy_mr_meaning_inventory", "media_poc_scrum_release_policy"], "meaning_classification_before_runtime_admission": True, "single_role_complete": "prohibited"}},
        "separation_contract": {"ratification_is_implementation_authority": False, "ratification_is_external_write_authority": False, "registration_instance_values_in_packet": "prohibited", "design_artifacts_in_packet": "prohibited"},
    }
    expected["audit_digest"] = _digest(expected)
    actual = refinements.get("ratification_dependency_audit")
    faults = [] if actual == expected else ["ratification dependency auditが4 stage/SCC/composite exact contractと不一致"]
    if resolved_subject_authority_coverage_audit_faults(refinements):
        faults.append("ratification順序の親coverage auditが健全でない")
    if provider_neutral_execution_policy_faults(refinements):
        faults.append("provider-neutral foundation prerequisiteが健全でない")
    if refinements.get("vps_ui_quality_attributes_policy") != _expected_vps_ui_quality_attributes_policy():
        faults.append("VPS UI quality foundation prerequisiteがcode正本と不一致")
    if _digest(refinements.get("strategy_requirement_admission_policy")) != "sha256:4a1084cb7cf02e61ec4c3bdd96d0ed6088373eb9badbfd1d3554ed50e85c400a":
        faults.append("strategy admission foundation prerequisiteがcode正本digestと不一致")
    quality_record = records.get("VPS-UI-QUALITY-ATTRIBUTES", {})
    strategy_record = records.get("STRATEGY-REQUIREMENT-ADMISSION", {})
    if quality_record.get("lifecycle_status") != "draft" or not quality_record.get("pending_resolution"):
        faults.append("VPS UI quality true-PO pending readinessが不正")
    if strategy_record.get("lifecycle_status") != "draft" or len(strategy_record.get("pending_resolution", [])) != 2:
        faults.append("strategy admission true-PO pending readinessが不正")
    for authority in stage0 + stage1 + stage2 + ["wordpress_maintenance_boundaries_policy"] + wp_children:
        policy = refinements.get(authority, {})
        if not isinstance(policy, dict) or policy.get("status") != "candidate_unratified" or policy.get("approval") is not None:
            faults.append(f"{authority}: 未批准candidate境界が反転")
    return faults


def resolved_subject_authority_coverage_audit_faults(refinements: dict[str, Any]) -> list[str]:
    """pending=[] recordを唯一又は役割分離したauthority正本へexact対応付けする。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    mappings = {
        "VPS-UI-PRIMARY-HUMAN-INTERFACE": [("primary_policy", "vps_ui_primary_interface_policy")],
        "FR-16-NOTIFICATION-BOUNDARY": [("primary_policy", "fr16_notification_boundary_policy")],
        "DISCORD-MULTI-PURPOSE-BOUNDARIES": [("historical_replacement", "discord_notification_rejection_policy"), ("historical_replacement", "discord_community_marketing_route_policy")],
        "DISCORD-NOTIFICATION-REJECTION-BOUNDARY": [("primary_policy", "discord_notification_rejection_policy")],
        "AUTO-MODE-DECISION-AUTHORITY": [("historical_replacement", "automated_publishing_admission_policy")],
        "GENAI-EXECUTION-ROUTE": [("primary_policy", "genai_execution_route_policy")],
        "OFFICIAL-API-ROUTE-AUTHORITY": [("primary_policy", "official_api_route_authority_policy")],
        "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE": [("historical_replacement", "semantic_coverage_policy")],
        "REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2": [("primary_policy", "semantic_coverage_policy")],
        "WORDPRESS-MAINTENANCE-BOUNDARIES": [("primary_policy", "wordpress_maintenance_boundaries_policy")],
        "VPS-UI-INBOX-LIFECYCLE": [("primary_policy", "vps_ui_inbox_lifecycle_policy")],
        "CONTRACT-SEMANTIC-DESCENT-V2": [("primary_policy", "contract_semantic_descent_policy")],
        "VPS-CREDENTIAL-SECURITY-BOUNDARY": [("primary_policy", "vps_credential_security_boundary_policy")],
        "PRODUCT-STATE-AUTHORITY": [("primary_policy", "product_state_authority_policy")],
        "BUSINESS-PROFILE-AUTHORIZATION": [("primary_policy", "business_profile_authorization_policy")],
        "VPS-UI-AUTHENTICATION-SESSION": [("primary_policy", "vps_ui_authentication_session_policy")],
        "RATE-QUOTA-COST-AUTHORITY": [("primary_policy", "rate_quota_cost_policy")],
        "LEGACY-MEDIA-ADMISSION-INVENTORY": [("meaning_inventory", "legacy_mr_meaning_inventory"), ("runtime_admission", "media_poc_scrum_release_policy")],
        "EXTERNAL-BROWSER-AUTOMATION-ROUTE": [("primary_policy", "external_browser_automation_route_policy")],
        "DISCORD-COMMUNITY-MARKETING-ROUTE": [("primary_policy", "discord_community_marketing_route_policy")],
        "AUTOMATED-PUBLISHING-ADMISSION": [("primary_policy", "automated_publishing_admission_policy")],
        "CONTENT-QUALITY-GATE-LEARNING": [("primary_policy", "content_quality_gate_learning_policy")],
        "CONTENT-RISK-CLASSIFICATION": [("primary_policy", "content_risk_classification_policy")],
        "RESEARCH-LED-CONTENT-GROWTH": [("primary_policy", "research_led_content_growth_policy")],
    }
    validator_bindings = {
        "vps_ui_primary_interface_policy": ("G-REQ-VPS-UI-PRIMARY-INTERFACE-POLICY", "vps_ui_primary_interface_policy_faults"),
        "fr16_notification_boundary_policy": ("G-REQ-FR16-NOTIFICATION-BOUNDARY-POLICY", "fr16_notification_boundary_policy_faults"),
        "discord_notification_rejection_policy": ("G-REQ-DISCORD-NOTIFICATION-REJECTION-POLICY", "discord_notification_rejection_policy_faults"),
        "discord_community_marketing_route_policy": ("G-REQ-DISCORD-COMMUNITY-MARKETING-ROUTE-POLICY", "discord_community_marketing_route_policy_faults"),
        "automated_publishing_admission_policy": ("G-REQ-AUTOMATED-PUBLISHING-ADMISSION-POLICY", "automated_publishing_admission_policy_faults"),
        "genai_execution_route_policy": ("G-REQ-GENAI-EXECUTION-ROUTE-POLICY", "genai_execution_route_policy_faults"),
        "official_api_route_authority_policy": ("G-REQ-OFFICIAL-API-ROUTE-AUTHORITY-POLICY", "official_api_route_authority_policy_faults"),
        "semantic_coverage_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_semantic_coverage_policy"),
        "wordpress_maintenance_boundaries_policy": ("G-REQ-WORDPRESS-MAINTENANCE-BOUNDARIES-POLICY", "wordpress_maintenance_boundaries_policy_faults"),
        "vps_ui_inbox_lifecycle_policy": ("G-REQ-VPS-UI-INBOX-LIFECYCLE-POLICY", "vps_ui_inbox_lifecycle_policy_faults"),
        "contract_semantic_descent_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_contract_semantic_descent_policy"),
        "vps_credential_security_boundary_policy": ("G-REQ-VPS-CREDENTIAL-SECURITY-BOUNDARY-POLICY", "vps_credential_security_boundary_policy_faults"),
        "product_state_authority_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_product_state_authority_policy"),
        "business_profile_authorization_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_business_profile_authorization_policy"),
        "vps_ui_authentication_session_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_vps_ui_authentication_session_policy"),
        "rate_quota_cost_policy": ("G-REQ-OPEN-REFINEMENTS", "_expected_rate_quota_cost_policy"),
        "legacy_mr_meaning_inventory": ("G-REQ-LEGACY-MR-MEANING-INVENTORY", "legacy_mr_meaning_inventory_expected_pending_fault"),
        "media_poc_scrum_release_policy": ("G-REQ-MEDIA-POC-SCRUM-RELEASE-POLICY", "media_poc_scrum_release_policy_faults"),
        "external_browser_automation_route_policy": ("G-REQ-EXTERNAL-BROWSER-AUTOMATION-ROUTE-POLICY", "external_browser_automation_route_policy_faults"),
        "content_quality_gate_learning_policy": ("G-REQ-CONTENT-QUALITY-GATE-LEARNING-POLICY", "content_quality_gate_learning_policy_faults"),
        "content_risk_classification_policy": ("G-REQ-CONTENT-RISK-CLASSIFICATION-POLICY", "content_risk_classification_policy_faults"),
        "research_led_content_growth_policy": ("G-REQ-RESEARCH-LED-CONTENT-GROWTH-POLICY", "research_led_content_growth_policy_faults"),
    }
    historical_subjects = {"DISCORD-MULTI-PURPOSE-BOUNDARIES", "AUTO-MODE-DECISION-AUTHORITY", "REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE"}
    rows = []
    for subject, refs in mappings.items():
        record = records.get(subject, {})
        rows.append({
            "subject_id": subject,
            "record_lifecycle_status": record.get("lifecycle_status"),
            "record_semantic_digest": record.get("semantic_digest"),
            "coverage_mode": "superseded_history_only" if subject in historical_subjects else ("role_separated_composite" if len(refs) > 1 else "single_primary"),
            "authority_refs": [{"role": role, "authority_id": authority, "authority_digest": _digest(refinements.get(authority)), "gate_id": validator_bindings[authority][0], "fault_binding": validator_bindings[authority][1]} for role, authority in refs],
            "implementation_authority": "not_granted",
        })
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "implementation_authorized": False,
        "pending_empty_subject_count": len(mappings), "pending_empty_subject_ids": list(mappings), "pending_empty_subject_id_digest": _digest(list(mappings)),
        "coverage_rows": rows, "coverage_rows_digest": _digest(rows),
        "authority_validation_bindings": {key: {"gate_id": value[0], "fault_binding": value[1]} for key, value in validator_bindings.items()},
        "coverage_contract": {"exact_pending_empty_population": True, "missing_or_extra": "fault", "single_primary_duplicate": "fault", "composite_roles_must_differ": True, "superseded_active_authority": "prohibited", "candidate_as_ratified": "prohibited", "registration_or_design_values_as_requirement_authority": "prohibited"},
    }
    expected["audit_digest"] = _digest(expected)
    actual = refinements.get("resolved_subject_authority_coverage_audit")
    faults = [] if actual == expected else ["resolved subject authority coverage auditが24 record exact対応と不一致"]
    pending_empty = [row.get("subject_id") for row in refinements.get("records", []) if isinstance(row, dict) and row.get("pending_resolution") == []]
    if pending_empty != list(mappings):
        faults.append("pending=[] subject母集団がcoverage matrixと不一致")
    for subject in historical_subjects:
        if records.get(subject, {}).get("lifecycle_status") != "superseded":
            faults.append(f"{subject}: superseded履歴recordのlifecycleが反転")
    expected_helpers = {
        "semantic_coverage_policy": _expected_semantic_coverage_policy,
        "contract_semantic_descent_policy": _expected_contract_semantic_descent_policy,
        "product_state_authority_policy": _expected_product_state_authority_policy,
        "business_profile_authorization_policy": _expected_business_profile_authorization_policy,
        "vps_ui_authentication_session_policy": _expected_vps_ui_authentication_session_policy,
        "rate_quota_cost_policy": _expected_rate_quota_cost_policy,
    }
    fault_functions = {
        "vps_ui_primary_interface_policy": vps_ui_primary_interface_policy_faults, "fr16_notification_boundary_policy": fr16_notification_boundary_policy_faults,
        "discord_notification_rejection_policy": discord_notification_rejection_policy_faults, "discord_community_marketing_route_policy": discord_community_marketing_route_policy_faults,
        "automated_publishing_admission_policy": automated_publishing_admission_policy_faults, "genai_execution_route_policy": genai_execution_route_policy_faults,
        "official_api_route_authority_policy": official_api_route_authority_policy_faults, "wordpress_maintenance_boundaries_policy": wordpress_maintenance_boundaries_policy_faults,
        "vps_ui_inbox_lifecycle_policy": vps_ui_inbox_lifecycle_policy_faults, "vps_credential_security_boundary_policy": vps_credential_security_boundary_policy_faults,
        "media_poc_scrum_release_policy": media_poc_scrum_release_policy_faults,
        "external_browser_automation_route_policy": external_browser_automation_route_policy_faults, "content_quality_gate_learning_policy": content_quality_gate_learning_policy_faults,
        "content_risk_classification_policy": content_risk_classification_policy_faults, "research_led_content_growth_policy": research_led_content_growth_policy_faults,
    }
    for authority, helper in expected_helpers.items():
        if refinements.get(authority) != helper():
            faults.append(f"{authority}: expected helperとの意味照合に失敗")
    for authority, function in fault_functions.items():
        if function(refinements):
            faults.append(f"{authority}: 専用fault経路が0でない")
    if legacy_mr_meaning_inventory_faults(refinements) != ["旧MR意味分類候補がPO未承認 remaining=0"]:
        faults.append("legacy_mr_meaning_inventory: 想定内PO未承認以外のfaultがある")
    for row in actual.get("coverage_rows", []) if isinstance(actual, dict) else []:
        refs = row.get("authority_refs", [])
        if row.get("coverage_mode") == "single_primary" and len(refs) != 1:
            faults.append(f"{row.get('subject_id')}: primary authorityが一意でない")
        if row.get("coverage_mode") == "single_primary" and any(ref.get("role") != "primary_policy" for ref in refs if isinstance(ref, dict)):
            faults.append(f"{row.get('subject_id')}: single primaryのroleが不正")
        if row.get("coverage_mode") == "superseded_history_only" and any(ref.get("role") != "historical_replacement" for ref in refs if isinstance(ref, dict)):
            faults.append(f"{row.get('subject_id')}: superseded subjectがactive authorityへ再混入")
    return faults


def wordpress_maintenance_boundaries_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """WordPress content/platform/security operationの責務横流用を拒否する。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("WORDPRESS-MAINTENANCE-BOUNDARIES", {})
    source_ids = ("RDE-000083", "RDE-000084", "RDE-000085", "RDE-000086", "RDE-000087", "RDE-000088")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    parents = {
        "content": refinements.get("wordpress_content_operations_policy", {}),
        "platform": refinements.get("wordpress_platform_maintenance_policy", {}),
        "security": refinements.get("wordpress_security_maintenance_policy", {}),
    }
    family_specs: dict[str, Any] = {
        "content": {
            "owner_subject_id": "WORDPRESS-CONTENT-OPERATIONS-RELEASE", "required_parent_policy": "wordpress_content_operations_policy",
            "effects": {"create_draft": "state_write", "update_draft": "state_write", "publish": "external_write", "update_published_in_place": "external_write", "unpublish": "external_write", "delete": "delete", "rollback": "recovery_write"},
        },
        "platform": {
            "owner_subject_id": "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE", "required_parent_policy": "wordpress_platform_maintenance_policy",
            "effects": {"inspect_inventory": "read", "create_backup": "state_write", "verify_restore": "read", "update_core_nonsecurity": "platform_write", "install_plugin": "platform_write", "change_plugin_state": "platform_write", "update_plugin_nonsecurity": "platform_write", "schema_or_config_change": "platform_write", "rollback": "recovery_write"},
        },
        "security": {
            "owner_subject_id": "WORDPRESS-SECURITY-MAINTENANCE-RELEASE", "required_parent_policy": "wordpress_security_maintenance_policy",
            "effects": {"assess": "read", "patch_core": "security_write", "patch_plugin": "security_write", "patch_theme": "security_write", "permission_change": "permission_write", "credential_rotation": "credential_write", "quarantine": "security_write", "restore_or_rollback": "recovery_write"},
        },
    }
    routing: dict[str, dict[str, Any]] = {}
    for family, spec in family_specs.items():
        for operation, effect in spec["effects"].items():
            key = f"{family}:{operation}"
            routing[key] = {
                "responsibility_family": family, "operation": operation, "owner_subject_id": spec["owner_subject_id"], "allowed_effect": effect,
                "required_child_policy": spec["required_parent_policy"], "required_authority_receipt": f"{family}_operation_authorization_receipt",
                "required_release_receipt": f"{family}_independent_release_receipt", "other_family_authority_inference": "prohibited",
            }
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "site_enabled_as_whole": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:eafdb5ab01a64154bc42df57594ce221f4327aed4a5beb2b77ec0f80047f8201", "refinement_record_content_digest": "sha256:ca01aefa8950e0f1dd65c6c7e787095c68d481301dc4a8b98e45bf5eca0deafe",
        "parent_policy_digests": {key: _digest(value) for key, value in parents.items()},
        "family_operation_sets": {family: list(spec["effects"]) for family, spec in family_specs.items()},
        "operation_routing_matrix": routing, "operation_routing_digest": _digest(routing),
        "routing_contract": {"key": "responsibility_family:operation", "exact_union_of_child_operations": True, "duplicate_route_keys": "prohibited", "unowned_operation": "prohibited", "cross_family_grant_or_receipt_reuse": "prohibited"},
        "security_intersection_contract": {"change_execution_owner": "platform", "threat_acceptance_emergency_release_credential_permission_owner": "security", "required_receipts": ["platform_operation_authorization_receipt", "security_risk_or_authorization_receipt"], "single_receipt_substitution": "prohibited"},
        "release_contract": {"content_platform_security": "independent_release_and_acceptance", "backup_smoke_rollback": "required_by_applicable_child_contract", "failure": "family_state_blocked_until_family_specific_recovery_and_resume", "site_wide_success_inference": "prohibited"},
        "non_implication": ["content_grant_does_not_authorize_platform_or_security", "platform_receipt_does_not_accept_security_risk", "security_patch_does_not_authorize_content_publish", "backup_or_route_success_is_not_release_acceptance", "legacy_wp_green_s4_or_success_is_not_current_authority"],
        "registration_values_in_policy": "prohibited", "registration_dimensions": ["site", "profile", "account", "operation", "effect", "child_authority_revision", "maintenance_window", "component", "security_relevance"],
        "design_later": ["responsibility_dispatcher", "cross_family_handoff_ui", "receipt_aggregation"],
        "prohibited_inheritance": ["content_to_platform_authority", "platform_to_security_authority", "security_to_content_authority", "operation_overlap_or_gap", "single_receipt_for_security_intersection", "backup_smoke_or_rollback_omission", "stale_child_semantic", "legacy_wp_green_s4_or_route_success", "whole_site_enablement"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("wordpress_maintenance_boundaries_policy")
    faults = [] if policy == expected else ["WordPress maintenance boundaries policyが3責務exact routingと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("WordPress maintenance boundary record実semantic contentがcode正本と不一致")
    if parents["content"] != _expected_wordpress_content_operations_policy():
        faults.append("WordPress content parent policyがcode正本と不一致")
    if parents["security"] != _expected_wordpress_security_maintenance_policy():
        faults.append("WordPress security parent policyがcode正本と不一致")
    if _digest(parents["platform"]) != "sha256:dc6718df859dc9a997ce62ede7c16f62fb73d5eab6c74da9340bddaa0f578595":
        faults.append("WordPress platform parent policyがcode正本と不一致")
    actual_keys = set(policy.get("operation_routing_matrix", {})) if isinstance(policy, dict) and isinstance(policy.get("operation_routing_matrix"), dict) else set()
    if actual_keys != set(routing):
        faults.append("WordPress 3責務operation exact unionに欠落・余剰がある")
    return faults


def vps_ui_inbox_lifecycle_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """VPS UI inboxをsource stateへの非decision導線として型付きで閉じる。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("VPS-UI-INBOX-LIFECYCLE", {})
    source_ids = ("RDE-000100", "RDE-000101", "RDE-000102", "RDE-000119", "RDE-000165", "RDE-000166", "RDE-000167", "RDE-000168")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-009", {})
    facts = {"ordinary_failed_retry_notification": "none", "retry_exhaustion_state": "blocked", "retry_exhaustion_notification": "vps_ui_inbox", "notification_failure_state_effect": "no_rollback", "unsupported_published_update_action": "no_action_including_notification"}
    fields = ["inbox_operation_id", "inbox_item_id", "inbox_item_revision", "profile_id", "account_id", "resource_id", "principal_id", "source_class", "source_subject_id", "source_state", "source_state_revision", "source_event_receipt_digest", "purpose", "severity", "action_required", "dedupe_identity_digest", "artifact_id", "rule_revision_digest", "source_identity_digest", "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest", "authorization_scope_digest", "secret_free_projection_digest", "created_at", "seen_at", "acknowledged_at", "source_terminal_receipt_digest", "source_expiry_receipt_digest", "retention_policy_revision_digest", "data_classification", "legal_hold_status", "archive_or_redact_or_purge_outcome", "retry_budget_revision_digest", "retry_attempt_no", "retry_outcome", "reminder_policy_revision_digest", "result_receipt_digest"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    identity = fields[:7]
    source = fields[7:16]
    authorization = fields[19:24]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "decision_authorized": False, "external_fallback_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:8e7014577d4ad96f3ded703a42f97f618cf2b56f3c89866d948fa7b9d1ed1fad", "refinement_record_content_digest": "sha256:23530337837e6c23643d38825dd7f565c68ca8bf29d49428a4054089e8d423cb",
        "decision_binding": {"decision_snapshot_digest": "sha256:2e85fb60a138d12aaeafb9f0152bef194905bf48c1659eb01acaa30a776572af", "facts_projection": facts},
        "resolver_candidate_binding": refinements.get("resolver_candidate_controls", {}).get("VPS-UI-INBOX-LIFECYCLE"),
        "parent_semantic_digests": {"fr16_notification": _digest(refinements.get("fr16_notification_boundary_policy")), "vps_ui_primary": _digest(refinements.get("vps_ui_primary_interface_policy")), "product_state": _digest(refinements.get("product_state_authority_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy")), "content_quality": _digest(refinements.get("content_quality_gate_learning_policy"))},
        "operation_field_universe": fields,
        "operation_contracts": {
            "create_approval_waiting": {**partition(identity + source + authorization + ["secret_free_projection_digest", "created_at", "retry_budget_revision_digest", "retry_attempt_no", "retry_outcome", "result_receipt_digest"]), "value_contract": {"source_class": "approval_waiting", "purpose": "action_required", "predecessor": "decision_pending_committed", "failure_effect": "source_state_and_revision_unchanged", "external_fallback": "prohibited"}},
            "create_safety_stopped": {**partition(identity + source + authorization + ["secret_free_projection_digest", "created_at", "retry_budget_revision_digest", "retry_attempt_no", "retry_outcome", "result_receipt_digest"]), "value_contract": {"source_class": "safety_stopped", "purpose": "action_required", "predecessor": "safety_stop_committed", "failure_effect": "source_state_and_revision_unchanged", "external_fallback": "prohibited"}},
            "create_execution_failed": {**partition(identity + source + authorization + ["secret_free_projection_digest", "created_at", "retry_budget_revision_digest", "retry_attempt_no", "retry_outcome", "result_receipt_digest"]), "value_contract": {"source_class": "execution_failed", "purpose": "operational_alert", "predecessor": "failure_state_committed", "failure_effect": "source_state_and_revision_unchanged", "external_fallback": "prohibited"}},
            "create_content_quality_retry_exhausted": {**partition(identity + source + fields[16:19] + authorization + ["secret_free_projection_digest", "created_at", "retry_budget_revision_digest", "retry_attempt_no", "retry_outcome", "result_receipt_digest"]), "value_contract": {"source_class": "content_quality_retry_exhausted", "purpose": "operational_alert", "predecessor": "blocked_transition_committed", "dedupe": ["artifact_id", "rule_revision_digest", "source_identity_digest", "purpose"], "failure_effect": "blocked_state_and_revision_unchanged", "external_fallback": "prohibited"}},
            "read": {**partition(identity + authorization + ["secret_free_projection_digest", "result_receipt_digest"]), "value_contract": {"effect": "read_only", "raw_secret_pii_error": "prohibited"}},
            "mark_seen": {**partition(identity + authorization + ["seen_at", "result_receipt_digest"]), "value_contract": {"source_state_effect": "none", "decision_authority": "none"}},
            "acknowledge": {**partition(identity + authorization + ["acknowledged_at", "result_receipt_digest"]), "value_contract": {"source_state_effect": "none", "approve_reject_resume_authority": "none"}},
            "source_resolve": {**partition(identity + source + authorization + ["source_terminal_receipt_digest", "result_receipt_digest"]), "value_contract": {"prior_item_state": "active", "result_item_state": "resolved", "authority": "source_terminal_event_only"}},
            "source_expire": {**partition(identity + source + authorization + ["source_expiry_receipt_digest", "result_receipt_digest"]), "value_contract": {"prior_item_state": "active", "result_item_state": "expired", "authority": "source_lifecycle_revision_or_scope_event_only", "inbox_time_or_unseen": "not_authority"}},
            "archive_redact_or_purge": {**partition(identity + authorization + ["source_terminal_receipt_digest", "retention_policy_revision_digest", "data_classification", "legal_hold_status", "archive_or_redact_or_purge_outcome", "result_receipt_digest"]), "value_contract": {"active_item": "prohibited", "unknown_policy_or_legal_hold": "irreversible_purge_prohibited", "tombstone": "secret_free_minimal"}},
        },
        "source_class_contracts": {
            "approval_waiting": {"purpose": "action_required", "predecessor": "decision_pending_committed"},
            "safety_stopped": {"purpose": "action_required", "predecessor": "safety_stop_committed"},
            "execution_failed": {"purpose": "operational_alert", "predecessor": "failure_state_committed"},
            "content_quality_retry_exhausted": {"purpose": "operational_alert", "predecessor": "blocked_transition_committed", "dedupe_required": ["artifact_id", "rule_revision_digest", "source_identity_digest", "purpose"]},
        },
        "lifecycle_contract": {"states": ["active", "resolved", "expired"], "source_derived_terminal_only": True, "inbox_auto_expiry": "prohibited", "active_archive_or_purge": "prohibited", "seen_ack_reminder": "non_decision"},
        "retry_contract": {"budget": "external_registration", "unknown_or_stale": "fail_stop_no_additional_retry", "exhausted": "failed_receipt_and_source_state_unchanged", "infinite_retry": "prohibited"},
        "notification_contract": {"ordinary_content_retry": "none", "unsupported_published_update": "none", "content_quality_retry_exhausted": "single_inbox_item", "external_transport_fallback": "prohibited"},
        "reminder_contract": {"default": "disabled", "enabled_only_by_registration": True, "same_item_only": True, "decision_or_expiry_authority": "none"},
        "registration_binding_digests": [_digest(value) for value in record.get("registration_bindings", [])],
        "registration_values_in_policy": "prohibited", "design_later": list(record.get("design_later", [])),
        "prohibited_inheritance": ["seen_or_ack_as_decision", "inbox_time_as_expiry", "active_item_purge", "record_failure_rolls_back_source", "discord_email_or_webpush_fallback", "ordinary_retry_notification", "raw_secret_pii_or_error", "unknown_retry_budget_continues", "hard_coded_retention", "reminder_as_business_decision", "legacy_fr43_or_approval_transport"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("vps_ui_inbox_lifecycle_policy")
    faults = [] if policy == expected else ["VPS UI inbox lifecycle policyがsource-derived lifecycle/non-decision exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("VPS UI inbox record実semantic contentがcode正本と不一致")
    if control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or control.get("facts") != facts:
        faults.append("VPS UI inbox POD-009 decision projectionが不一致")
    universe = policy.get("operation_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("VPS UI inbox operation universeがtyped uniqueでない")
    contracts = policy.get("operation_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"VPS UI inbox {name} field partitionが閉じていない")
    return faults


def vps_credential_security_boundary_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """VPS restart後の停止、有人再初期化、credential再認可を型付きで閉じる。"""
    records = {row.get("subject_id"): row for row in refinements.get("records", []) if isinstance(row, dict)}
    record = records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY", {})
    source_ids = ("RDE-000109", "RDE-000110", "RDE-000159", "RDE-000162")
    events = {row.get("event_id"): row for row in requirement_discovery.load_discovery_ledger().get("events", []) if isinstance(row, dict) and row.get("event_id") in source_ids}
    control = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-008", {})
    facts = {"current_runtime_lifecycle": "agent_processes_stop_on_vps_reboot", "post_reboot_external_effects": "stopped", "credential_unlock": "human_reauthorization_with_runtime_reinitialization", "credential_only_auto_unlock": "prohibited", "future_persistent_service": "separate_po_requirement"}
    fields = ["credential_event_id", "credential_authority_id", "credential_authority_revision", "credential_authority_semantic_digest", "credential_scope_digest", "profile_id", "account_id", "resource_id", "operation", "effect", "runtime_instance_id", "runtime_revision", "restart_epoch", "prior_state", "result_state", "human_identity_id", "authentication_session_id", "authentication_event_digest", "authorization_grant_id", "authorization_grant_revision", "authorization_grant_semantic_digest", "runtime_reinitialization_receipt_digest", "injection_receipt_digest", "bounded_lifetime_digest", "revocation_or_expiry_receipt_digest", "secret_free_evidence_digest", "result_receipt_digest"]
    def partition(required: list[str]) -> dict[str, list[str]]:
        return {"required": required, "prohibited": [field for field in fields if field not in required]}
    identity = fields[:15]
    authority = fields[15:21]
    expected: dict[str, Any] = {
        "status": "candidate_unratified", "approval": None, "design_not_started": True, "credential_operation_authorized": False, "persistent_service_authorized": False,
        "source_event_ids": list(source_ids), "source_event_digests": {key: _digest(events.get(key)) for key in source_ids},
        "refinement_record_digest": _digest(record), "refinement_record_semantic_digest": "sha256:16f222c23f0071263f5b28fc09a62e23c50719dbff0f9c4747d8de00bcb014df", "refinement_record_content_digest": "sha256:9d16185c96134142d2b8f2191f8ac38b82cffc7ff589c9e33e3c3879120d61d9",
        "decision_binding": {"decision_snapshot_digest": "sha256:b10ecdf8d2306587f098488f91a00d79a2849399bf9235f4e514f239b28dd142", "facts_projection": facts},
        "parent_semantic_digests": {"authentication_session": _digest(refinements.get("vps_ui_authentication_session_policy")), "business_authorization": _digest(refinements.get("business_profile_authorization_policy")), "product_state": _digest(refinements.get("product_state_authority_policy"))},
        "credential_event_field_universe": fields,
        "state_contracts": {
            "stopped_after_restart": {**partition(identity + ["secret_free_evidence_digest", "result_receipt_digest"]), "value_contract": {"prior_state": "runtime_active_or_unknown", "result_state": "stopped_after_restart", "external_effects": "stopped", "agent_auto_resume": "prohibited"}},
            "human_reinitialized_locked": {**partition(identity + authority[:3] + ["runtime_reinitialization_receipt_digest", "secret_free_evidence_digest", "result_receipt_digest"]), "value_contract": {"prior_state": "stopped_after_restart", "result_state": "human_reinitialized_locked", "credential_injected": False}},
            "credential_reauthorized_injected": {**partition(identity + authority + ["runtime_reinitialization_receipt_digest", "injection_receipt_digest", "bounded_lifetime_digest", "secret_free_evidence_digest", "result_receipt_digest"]), "value_contract": {"prior_state": "human_reinitialized_locked", "result_state": "credential_reauthorized_injected", "human_reauthorization": "required", "fresh_session_and_grant": "required", "scope_relation": "exact", "storage": "bounded_process_memory_only"}},
            "revoked_or_expired": {**partition(identity + ["revocation_or_expiry_receipt_digest", "secret_free_evidence_digest", "result_receipt_digest"]), "value_contract": {"prior_state": "credential_reauthorized_injected", "result_state": "revoked_or_expired", "external_effects": "stopped", "continued_use": "prohibited"}},
        },
        "restart_contract": {"credential_only_auto_unlock": "prohibited", "old_session_or_grant_reuse": "prohibited", "agent_auto_restart_or_resume": "prohibited", "runtime_reinitialization_and_credential_reauthorization": "human_coordinated", "persistent_service": "separate_po_requirement"},
        "secret_material_contract": {"raw_secret_or_bearer_or_credential_material": {"repo": "prohibited", "product_database": "prohibited", "log_or_journal": "prohibited", "service_unit_or_argv_or_dump": "prohibited", "inbox_or_evidence": "prohibited", "product_state_backup": "prohibited"}, "allowed_candidate": "bounded_process_memory_after_human_reauthorization", "evidence_projection": "secret_free_reference_and_digest_only"},
        "non_implication": ["credential_receipt_does_not_prove_operation_success", "authentication_does_not_grant_authorization", "runtime_reinitialization_does_not_grant_external_effect", "injection_does_not_expand_scope", "restart_does_not_preserve_old_authority"],
        "registration_values_in_policy": "prohibited", "design_later": ["secret_backend", "injection_mechanism", "process_isolation", "rotation_and_recovery_ui"],
        "prohibited_inheritance": ["credential_only_auto_unlock", "old_session_or_grant_reuse", "agent_auto_resume_after_restart", "raw_secret_persistence", "test_to_production_scope_reuse", "expired_credential_continued_use", "credential_receipt_as_operation_success", "implicit_persistent_service"],
    }
    expected["authority_semantic_digest"] = _digest(expected)
    policy = refinements.get("vps_credential_security_boundary_policy")
    faults = [] if policy == expected else ["VPS credential security boundary policyがrestart/reauthorization/secret exact contractと不一致"]
    if record.get("semantic_digest") != expected["refinement_record_semantic_digest"] or _digest({key: value for key, value in record.items() if key != "semantic_digest"}) != expected["refinement_record_content_digest"]:
        faults.append("VPS credential record実semantic contentがcode正本と不一致")
    if control.get("decision_snapshot_digest") != expected["decision_binding"]["decision_snapshot_digest"] or control.get("facts") != facts:
        faults.append("VPS credential POD-008 decision projectionが不一致")
    universe = policy.get("credential_event_field_universe", []) if isinstance(policy, dict) else []
    valid = isinstance(universe, list) and all(isinstance(value, str) and value for value in universe) and len(universe) == len(set(universe))
    if not valid:
        faults.append("VPS credential field universeがtyped uniqueでない")
    contracts = policy.get("state_contracts", {}) if isinstance(policy, dict) else {}
    for name, contract in contracts.items() if isinstance(contracts, dict) else []:
        required = contract.get("required") if isinstance(contract, dict) else None
        prohibited = contract.get("prohibited") if isinstance(contract, dict) else None
        if not isinstance(required, list) or not isinstance(prohibited, list) or not all(isinstance(value, str) for value in required + prohibited) or set(required) & set(prohibited) or (valid and set(required) | set(prohibited) != set(universe)):
            faults.append(f"VPS credential {name} field partitionが閉じていない")
    return faults


def media_poc_scrum_release_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """媒体release、PoC evidence、本番write authorityを分離する。"""
    policy = refinements.get("media_poc_scrum_release_policy")
    if not isinstance(policy,dict):
        return ["media PoC/Scrum release policyがない"]
    faults: list[str] = []
    event_ids = ("RDE-000073","RDE-000074","RDE-000075","RDE-000076","RDE-000077","RDE-000078","RDE-000079","RDE-000082","RDE-000095")
    discovery = requirement_discovery.load_discovery_ledger()
    events = {row.get("event_id"):row for row in discovery.get("events",[]) if row.get("event_id") in set(event_ids)}
    records = {row.get("subject_id"):row for row in refinements.get("records",[]) if isinstance(row,dict)}
    record = records.get("MEDIA-POC-SCRUM-RELEASE")
    parent_keys = ("wordpress_content_operations_policy","business_profile_authorization_policy","product_state_authority_policy","provider_neutral_execution_policy","rate_quota_cost_policy")
    expected_parents = {key:_digest(refinements.get(key)) for key in parent_keys}
    record_subjects = ("AUTOMATED-PUBLISHING-ADMISSION","CONTENT-QUALITY-GATE-LEARNING","CONTENT-RISK-CLASSIFICATION","OFFICIAL-API-ROUTE-AUTHORITY","VPS-CREDENTIAL-SECURITY-BOUNDARY","DISCORD-COMMUNITY-MARKETING-ROUTE")
    expected_records = {key:_digest(records.get(key)) for key in record_subjects}
    dependency_subjects = (
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE","BUSINESS-PROFILE-AUTHORIZATION",
        "PRODUCT-STATE-AUTHORITY","RATE-QUOTA-COST-AUTHORITY",
        "AUTOMATED-PUBLISHING-ADMISSION","CONTENT-QUALITY-GATE-LEARNING",
        "CONTENT-RISK-CLASSIFICATION","OFFICIAL-API-ROUTE-AUTHORITY",
        "VPS-CREDENTIAL-SECURITY-BOUNDARY",
    )
    dependency_policy_bindings = {
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE": ("wordpress_content_operations_policy", expected_parents["wordpress_content_operations_policy"]),
        "BUSINESS-PROFILE-AUTHORIZATION": ("business_profile_authorization_policy", expected_parents["business_profile_authorization_policy"]),
        "PRODUCT-STATE-AUTHORITY": ("product_state_authority_policy", expected_parents["product_state_authority_policy"]),
        "RATE-QUOTA-COST-AUTHORITY": ("rate_quota_cost_policy", expected_parents["rate_quota_cost_policy"]),
        "AUTOMATED-PUBLISHING-ADMISSION": ("AUTOMATED-PUBLISHING-ADMISSION", records.get("AUTOMATED-PUBLISHING-ADMISSION", {}).get("semantic_digest")),
        "CONTENT-QUALITY-GATE-LEARNING": ("CONTENT-QUALITY-GATE-LEARNING", records.get("CONTENT-QUALITY-GATE-LEARNING", {}).get("semantic_digest")),
        "CONTENT-RISK-CLASSIFICATION": ("CONTENT-RISK-CLASSIFICATION", records.get("CONTENT-RISK-CLASSIFICATION", {}).get("semantic_digest")),
        "OFFICIAL-API-ROUTE-AUTHORITY": ("OFFICIAL-API-ROUTE-AUTHORITY", records.get("OFFICIAL-API-ROUTE-AUTHORITY", {}).get("semantic_digest")),
        "VPS-CREDENTIAL-SECURITY-BOUNDARY": ("VPS-CREDENTIAL-SECURITY-BOUNDARY", records.get("VPS-CREDENTIAL-SECURITY-BOUNDARY", {}).get("semantic_digest")),
    }
    all_events = {
        row.get("event_id"): row
        for row in discovery.get("events", [])
        if isinstance(row, dict)
    }

    def dependency_receipt(subject: str, approval: Any, revision: Any, policy_id: str, semantic_digest: Any) -> dict[str, Any] | None:
        if not isinstance(approval, dict):
            return None
        decision = all_events.get(approval.get("decision_id"))
        if (
            not isinstance(decision, dict)
            or decision.get("subject_id") != subject
            or decision.get("event_type") != "policy_ratification_decided"
            or decision.get("payload", {}).get("decision") != "accepted"
            or decision.get("actor_principal") != "po"
            or decision.get("payload", {}).get("approver_principal") != "po"
            or decision.get("actor_principal") != approval.get("approver_principal")
            or decision.get("payload", {}).get("approved_policy_id") != policy_id
            or decision.get("payload", {}).get("approved_revision") != revision
            or decision.get("payload", {}).get("approved_policy_semantic_digest") != semantic_digest
        ):
            return None
        expected = {
            "decision_id": decision.get("event_id"),
            "authority": "PO",
            "approver_principal": decision.get("actor_principal"),
            "approved_revision": revision,
            "approved_policy_id": policy_id,
            "approved_policy_semantic_digest": semantic_digest,
            "source_event_or_artifact_digest": _digest(decision),
        }
        return expected if approval == expected else None

    expected_dependency_receipts = {}
    for subject in dependency_subjects:
        row = records.get(subject, {})
        policy_id, semantic_digest = dependency_policy_bindings[subject]
        receipt = dependency_receipt(subject, row.get("approval"), row.get("revision"), policy_id, semantic_digest)
        expected_dependency_receipts[subject] = {
            "authority_id": subject,
            "revision": row.get("revision"),
            "semantic_digest": semantic_digest,
            "approval_or_ratification_receipt": receipt,
            "approval_or_ratification_receipt_digest": _digest(receipt),
            "frozen": row.get("lifecycle_status") == "frozen" and receipt is not None,
        }
    provider_binding = refinements.get("provider_policy_bindings",{})
    provider_receipt = dependency_receipt(
        "PROVIDER-NEUTRAL-EXECUTION-POLICY",
        provider_binding.get("approval"),
        provider_binding.get("policy_revision"),
        "provider_neutral_execution_policy",
        provider_binding.get("policy_digest"),
    )
    expected_dependency_receipts["PROVIDER-NEUTRAL-EXECUTION-POLICY"] = {
        "authority_id":"PROVIDER-NEUTRAL-EXECUTION-POLICY",
        "revision":provider_binding.get("policy_revision"),
        "semantic_digest":provider_binding.get("policy_digest"),
        "approval_or_ratification_receipt": provider_receipt,
        "approval_or_ratification_receipt_digest":_digest(provider_receipt),
        "frozen":provider_binding.get("status")=="ratified" and provider_receipt is not None,
    }
    expected_inventories = {
        "legacy_mr_meaning_inventory":refinements.get("legacy_mr_meaning_inventory",{}).get("meaning_migrations_digest"),
        "legacy_media_br_meaning_migrations":_digest(refinements.get("legacy_media_br_meaning_migrations")),
    }
    expected_projection = {
        "release_granularity":{"release_unit":"media","increment_unit":"media_operation_capability","operation_classes":["read","publish","measure","community"],"partial_success_media_acceptance":"prohibited"},
        "initial_release":{"media":"wordpress","responsibility":"content_database_and_publication","operations":["create","read","update","stable_identity","publish","publication_evidence"],"excluded_responsibilities":["platform_maintenance","security_maintenance"]},
        "delivery_model":{"standard":"full_v_l1_l12","scrum_usage":"target_known_increment_delivery_only","discovery_usage":"feasibility_or_success_condition_unknown_only","poc_mandatory_for_all_media":False},
    }
    expected_poc = {
        "authority":"feasibility_evidence_only","production_permission_inference":"prohibited",
        "production_compatibility_inference":"prohibited","production_release_acceptance_inference":"prohibited",
        "credential_data_write_policy_sharing":"prohibited","cross_media_inference":"prohibited",
    }
    expected_community = {
        "operation_class":"community","initial_provider":"discord",
        "allowed_purpose":"community_marketing",
        "prohibited_purposes":["product_notification","product_approval","development_pr_notification"],
        "credential_policy_evidence_sharing":"prohibited","self_bot":"prohibited",
        "activation_requires_separate_registration_and_admission":True,
    }
    expected_release_units: dict[str, Any] = {
        "eligible_release_unit_ids":["wordpress_content","discord_community"],
        "row_fields":["release_unit_id","media_id","responsibility_family","operation_classes","capability_ids","parent_semantic_digests","included_responsibilities","excluded_responsibilities","disposition","owner_subject_id","selection_source_event_ids","selection_source_digest","selection_rationale","production_authority","admission_policy_ref","resume_conditions"],
        "dispositions":["selected_requirement_candidate","deferred","obsolete"],
        "production_authority":"prohibited_by_selection",
        "active_owner_subject_id":"MEDIA-POC-SCRUM-RELEASE",
        "admission_policy_ref":"media_poc_scrum_release_policy.production_write_authority_contract",
        "wordpress_capability_map":{
            "CAP-MEDIA-WP-CREATE":{"requirement_operation":"create","parent_policy":"wordpress_content_operations_policy","parent_semantic_members":["create_draft"],"semantic_role":"operation","effect":"state_write"},
            "CAP-MEDIA-WP-READ":{"requirement_operation":"read","parent_policy":"business_profile_authorization_policy","parent_semantic_members":["read","read_does_not_imply_write"],"semantic_role":"operation","effect":"read"},
            "CAP-MEDIA-WP-UPDATE":{"requirement_operation":"update","parent_policy":"wordpress_content_operations_policy","parent_semantic_members":["update_draft","update_published_in_place"],"semantic_role":"operation","effect":"state_write"},
            "CAP-MEDIA-WP-STABLE-IDENTITY":{"requirement_operation":"stable_identity","parent_policy":"wordpress_content_operations_policy","parent_semantic_members":["stable_content_id"],"semantic_role":"identity_binding","effect":"none"},
            "CAP-MEDIA-WP-PUBLISH":{"requirement_operation":"publish","parent_policy":"wordpress_content_operations_policy","parent_semantic_members":["publish"],"semantic_role":"operation","effect":"publish"},
            "CAP-MEDIA-WP-PUBLICATION-EVIDENCE":{"requirement_operation":"publication_evidence","parent_policy":"wordpress_content_operations_policy","parent_semantic_members":["result_receipt"],"semantic_role":"evidence_binding","effect":"none"},
        },
        "additional_release_unit_rule":"policy_revision_plus_new_source_plus_po_receipt_plus_full_row_digest",
    }
    restart_decision = refinements.get("captured_po_decision_controls",{}).get("POD-20260815-008")
    expected_write = {
        "requirements_cutover_write_authorized":False,
        "required_scope_dimensions":["media_id","profile_id","account_id","operation","effect"],
        "required_bindings":["registration_revision_digest","authorization_grant_id_revision_digest","activation_scope_id_revision_digest","route_capability_revision_digest","credential_authority_id","credential_revision","credential_semantic_digest","credential_scope_digest","runtime_reinitialization_receipt","risk_gate_receipt","quality_gate_receipt","quota_policy_revision_digest","product_state_revision"],
        "unknown_or_stale_binding_outcome":"deny_without_state_change",
        "poc_or_release_unit_success_as_write_grant":"prohibited",
        "post_restart_effects_before_reauthorization":"stopped",
        "credential_only_auto_unlock":"prohibited",
    }
    expected_attempt = {
        "required_fields":["attempt_id","release_unit_id","media_id","profile_id","account_id","operation","effect","registration_revision_digest","authorization_grant_id_revision_digest","activation_scope_id_revision_digest","route_capability_revision_digest","credential_authority_id","credential_revision","credential_semantic_digest","credential_scope_digest","runtime_reinitialization_receipt","risk_gate_receipt","quality_gate_receipt","quota_policy_revision_digest","expected_prior_product_state_revision","rollback_recovery_requirement","final_release_verdict_receipt"],
        "attempt_effect_values":["read","state_write","publish"],
        "binding_only_roles":["identity_binding","evidence_binding"],
        "binding_only_effect":"none",
        "success_receipt_next_attempt_authority":"prohibited",
        "missing_or_stale_outcome":"deny_without_state_change",
    }
    source_digests = {key:_digest(events.get(key)) for key in event_ids}
    expected_semantic = _digest({
        "source_event_digests":source_digests,"refinement_record_digest":_digest(record),
        "parent_policy_digests":expected_parents,"parent_requirement_record_digests":expected_records,
        "credential_restart_decision_digest":_digest(restart_decision),
        "legacy_media_inventory_digests":expected_inventories,"captured_po_decision_projection":expected_projection,
        "poc_evidence_contract":expected_poc,"community_purpose_contract":expected_community,
        "release_unit_classification_contract":expected_release_units,
        "production_write_authority_contract":expected_write,"production_write_attempt_contract":expected_attempt,
    })
    if policy.get("source_event_digests") != source_digests or policy.get("refinement_record_digest") != _digest(record):
        faults.append("media release source events/refinement digest不一致")
    if policy.get("parent_policy_digests") != expected_parents or policy.get("parent_requirement_record_digests") != expected_records or policy.get("credential_restart_decision_digest") != _digest(restart_decision) or policy.get("legacy_media_inventory_digests") != expected_inventories:
        faults.append("media release parent authority/legacy inventory digestがstale又は欠落")
    if policy.get("captured_po_decision_projection") != expected_projection:
        faults.append("媒体release単位／WordPress content初回release／Full V境界がPO回答から反転")
    if policy.get("poc_evidence_contract") != expected_poc:
        faults.append("PoC evidenceが本番permission/compatibility/release又は別媒体へ流用された")
    if policy.get("community_purpose_contract") != expected_community:
        faults.append("community operationがDiscord community marketing専用purpose又は資格情報分離から逸脱")
    if policy.get("release_unit_classification_contract") != expected_release_units or policy.get("production_write_attempt_contract") != expected_attempt:
        faults.append("media release unit分類又は個別production write attempt契約が不正")
    else:
        attempt_effects = set(expected_attempt["attempt_effect_values"])
        binding_roles = set(expected_attempt["binding_only_roles"])
        for capability_id, mapping in expected_release_units["wordpress_capability_map"].items():
            parent_policy = refinements.get(mapping["parent_policy"])
            parent_body = json.dumps(parent_policy, ensure_ascii=False, sort_keys=True)
            if any(member not in parent_body for member in mapping["parent_semantic_members"]):
                faults.append(f"{capability_id}: parent operation/effect semantic memberが実authorityにない")
            if (
                mapping["semantic_role"] in binding_roles
                and mapping["effect"] != expected_attempt["binding_only_effect"]
            ) or (
                mapping["semantic_role"] == "operation"
                and mapping["effect"] not in attempt_effects
            ):
                faults.append(f"{capability_id}: binding責務とproduction attempt effectが混同")
    if policy.get("production_write_authority_contract") != expected_write:
        faults.append("媒体本番writeがprofile/account/operation/effect grant又はVPS運用境界から逸脱")
    if policy.get("authority_semantic_digest") != expected_semantic:
        faults.append("media release authority semantic digestがsource/parents/PO/write境界へ束縛されていない")
    state = policy.get("classification_state",{})
    stage = state.get("status") if isinstance(state,dict) else None
    expected_state: dict[str, Any] = {"status":"pending_po_classification","selected_release_units":{},"classification_approval":None,"candidate_artifact_binding":None,"cutover_artifact_bindings":None,"cutover_blocked":True,"production_write_authorized":False}
    if stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified" or state != expected_state:
            faults.append("media releaseはPO未分類なのにrelease選択・cutover・本番writeされた")
    elif stage in {"classified_pending_cutover","cutover_complete"}:
        complete = stage == "cutover_complete"
        if refinements.get("wordpress_content_operations_policy") != _expected_wordpress_content_operations_policy():
            faults.append("media classified WordPress parent content operations gateが閉じていない")
        if refinements.get("product_state_authority_policy") != _expected_product_state_authority_policy():
            faults.append("media classified product state parent gateが閉じていない")
        if refinements.get("business_profile_authorization_policy") != _expected_business_profile_authorization_policy():
            faults.append("media classified business profile authorization parent gateが閉じていない")
        wp_parent = expected_parents["wordpress_content_operations_policy"]
        discord_parent = expected_records["DISCORD-COMMUNITY-MARKETING-ROUTE"]
        expected_rows = {
            "wordpress_content":{
                "release_unit_id":"wordpress_content","media_id":"wordpress","responsibility_family":"content_database_and_publication",
                "operation_classes":["create","read","update","stable_identity","publish","publication_evidence"],
                "capability_ids":["CAP-MEDIA-WP-CREATE","CAP-MEDIA-WP-READ","CAP-MEDIA-WP-UPDATE","CAP-MEDIA-WP-STABLE-IDENTITY","CAP-MEDIA-WP-PUBLISH","CAP-MEDIA-WP-PUBLICATION-EVIDENCE"],
                "parent_semantic_digests":{"wordpress_content_operations_policy":wp_parent,"business_profile_authorization_policy":expected_parents["business_profile_authorization_policy"],"product_state_authority_policy":expected_parents["product_state_authority_policy"],"wordpress_capability_map":_digest(expected_release_units["wordpress_capability_map"]),"selection_event":source_digests["RDE-000082"]},
                "included_responsibilities":["content_database","content_crud","stable_identity","publication","publication_evidence"],
                "excluded_responsibilities":["platform_maintenance","security_maintenance"],
                "disposition":"selected_requirement_candidate","owner_subject_id":"MEDIA-POC-SCRUM-RELEASE",
                "selection_source_event_ids":["RDE-000082"],"selection_source_digest":source_digests["RDE-000082"],
                "selection_rationale":"PO selected WordPress content database and publication as the first release unit",
                "production_authority":"prohibited_by_selection","admission_policy_ref":"media_poc_scrum_release_policy.production_write_authority_contract","resume_conditions":[],
            },
            "discord_community":{
                "release_unit_id":"discord_community","media_id":"discord","responsibility_family":"community_marketing",
                "operation_classes":[],"capability_ids":[],
                "parent_semantic_digests":{"discord_community_requirement":discord_parent,"community_purpose_contract":_digest(expected_community)},
                "included_responsibilities":["community_marketing"],
                "excluded_responsibilities":["product_notification","product_approval","development_pr_notification"],
                "disposition":"deferred","owner_subject_id":"MEDIA-POC-SCRUM-RELEASE",
                "selection_source_event_ids":records["DISCORD-COMMUNITY-MARKETING-ROUTE"].get("source_event_ids",[]),
                "selection_source_digest":discord_parent,
                "selection_rationale":"community route is distinct from the initial WordPress content release",
                "production_authority":"prohibited_by_selection","admission_policy_ref":"media_poc_scrum_release_policy.production_write_authority_contract",
                "resume_conditions":["community release candidate PO classification","guild/account/operation registration","moderation and crisis authority review"],
            },
        }
        rows = state.get("selected_release_units",{})
        if policy.get("status") != ("ratified" if complete else "candidate_unratified") or state.get("cutover_blocked") is not (not complete) or state.get("production_write_authorized") is not False or rows != expected_rows:
            faults.append("media classified release unitsがWP selected／Discord deferred exact partition又はwrite禁止と不一致")
        rows_digest = _digest(rows)
        approval = state.get("classification_approval")
        classification_decision = all_events.get(approval.get("decision_id")) if isinstance(approval,dict) else None
        expected_classification_approval = {
            "decision_id": classification_decision.get("event_id") if isinstance(classification_decision,dict) else None,
            "authority":"PO",
            "approver_principal": classification_decision.get("actor_principal") if isinstance(classification_decision,dict) else None,
            "approved_revision":1,
            "authority_semantic_digest":expected_semantic,
            "release_unit_rows_digest":rows_digest,
            "candidate_content_digest": None,
            "source_event_or_artifact_digest":_digest(classification_decision) if isinstance(classification_decision,dict) else None,
            "production_write_authorized":False,
        }
        if (
            not isinstance(classification_decision,dict)
            or classification_decision.get("subject_id") != "MEDIA-POC-SCRUM-RELEASE"
            or classification_decision.get("event_type") != "authority_classification_decided"
            or classification_decision.get("payload",{}).get("decision") != "accepted"
            or classification_decision.get("actor_principal") != "po"
            or classification_decision.get("payload",{}).get("approver_principal") != "po"
            or classification_decision.get("payload",{}).get("approved_policy_id") != "media_poc_scrum_release_policy"
            or classification_decision.get("payload",{}).get("approved_revision") != 1
            or classification_decision.get("payload",{}).get("approved_policy_semantic_digest") != expected_semantic
            or classification_decision.get("payload",{}).get("approved_rows_digest") != rows_digest
            or classification_decision.get("payload",{}).get("production_write_authorized") is not False
        ):
            faults.append("media release PO classification receiptがrows/semantic/write禁止へ束縛されていない")
        candidate_id = "AUTH-DEVELOPMENT-MEDIA-POC-SCRUM-RELEASE-CANDIDATE"
        manifest = load(MANIFEST)
        item = next((x for x in manifest.get("items",[]) if x.get("artifact_id")==candidate_id),None)
        candidate_data: dict[str,Any] = {}
        candidate_digest = ""
        candidate_path: Path|None = None
        try:
            if not isinstance(item,dict) or item.get("layer")!="00-authority" or item.get("artifact_type")!="requirement-authority-candidate" or item.get("authority_format")!="json" or item.get("authority_status")!="active" or item.get("implementation_input") is not complete:
                raise ValueError("candidate manifest")
            rel = Path(str(item.get("canonical_path")))
            if rel.is_absolute():
                raise ValueError("absolute")
            candidate_path = (REPO_ROOT/rel).resolve()
            candidate_path.relative_to(REPO_ROOT.resolve())
            candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate_digest = "sha256:"+hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        except (OSError,ValueError,json.JSONDecodeError):
            candidate_data = {}
        expected_candidate = {"authority_semantic_digest":expected_semantic,"release_unit_rows_digest":rows_digest,"selected_release_units":rows,"production_write_authorized":False,"production_write_attempt_contract":expected_attempt}
        binding = state.get("candidate_artifact_binding")
        if isinstance(expected_classification_approval,dict):
            expected_classification_approval["candidate_content_digest"] = candidate_digest
        if binding != {"artifact_id":candidate_id,"implementation_input":complete,"release_unit_rows_digest":rows_digest,"content_digest":candidate_digest} or candidate_data != expected_candidate:
            faults.append("media classified candidate artifact境界が不正")
        if (
            not isinstance(classification_decision,dict)
            or classification_decision.get("payload",{}).get("approved_candidate_content_digest") != candidate_digest
            or approval != expected_classification_approval
        ):
            faults.append("media release PO classification receiptがcandidate contentへ束縛されていない")
        if not complete and state.get("cutover_artifact_bindings") is not None:
            faults.append("media classified pendingにcutover artifactが混入")
        if complete:
            dependencies_ready = all(
                row.get("frozen") is True
                and isinstance(row.get("approval_or_ratification_receipt"), dict)
                for row in expected_dependency_receipts.values()
            )
            if not dependencies_ready:
                faults.append("media cutover selected WP依存authorityがapproval receipt付きfrozenでない")
            cutover = state.get("cutover_artifact_bindings")
            try:
                head_result = git("rev-parse","HEAD")
                head = head_result.stdout.strip() if head_result.returncode==0 else ""
            except OSError:
                head = ""
            manifest_digest = "sha256:"+hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            baseline_path = REPO_ROOT/"docs/00-authority/baselines/baseline.json"
            baseline_digest = "sha256:"+hashlib.sha256(baseline_path.read_bytes()).hexdigest() if baseline_path.is_file() else ""
            parent_receipts_digest = _digest(expected_dependency_receipts)
            cutover_actual = state.get("cutover_artifact_bindings")
            cutover_receipt_actual = cutover_actual.get("requirements_cutover_receipt") if isinstance(cutover_actual,dict) else None
            cutover_decision = all_events.get(cutover_receipt_actual.get("decision_id")) if isinstance(cutover_receipt_actual,dict) else None
            requirements_cutover_receipt = {
                "decision_id":cutover_decision.get("event_id") if isinstance(cutover_decision,dict) else None,
                "authority":"PO","approver_principal":cutover_decision.get("actor_principal") if isinstance(cutover_decision,dict) else None,
                "authority_semantic_digest":expected_semantic,
                "release_unit_rows_digest":rows_digest,
                "candidate_content_digest":candidate_digest,
                "parent_dependency_receipts_digest":parent_receipts_digest,
                "source_event_or_artifact_digest":_digest(cutover_decision) if isinstance(cutover_decision,dict) else None,
                "production_write_authorized":False,
            }
            if (
                not isinstance(cutover_decision,dict)
                or cutover_decision.get("subject_id") != "MEDIA-POC-SCRUM-RELEASE"
                or cutover_decision.get("event_type") != "authority_cutover_decided"
                or cutover_decision.get("payload",{}).get("decision") != "accepted"
                or cutover_decision.get("actor_principal") != "po"
                or cutover_decision.get("payload",{}).get("approver_principal") != "po"
                or cutover_decision.get("payload",{}).get("approved_policy_id") != "media_poc_scrum_release_policy.cutover"
                or cutover_decision.get("payload",{}).get("approved_revision") != 1
                or cutover_decision.get("payload",{}).get("approved_policy_semantic_digest") != expected_semantic
                or cutover_decision.get("payload",{}).get("approved_rows_digest") != rows_digest
                or cutover_decision.get("payload",{}).get("approved_candidate_content_digest") != candidate_digest
                or cutover_decision.get("payload",{}).get("approved_parent_receipts_digest") != parent_receipts_digest
                or cutover_decision.get("payload",{}).get("production_write_authorized") is not False
            ):
                faults.append("media requirements cutover PO decisionがsemantic/rows/candidate/parents/write禁止へ束縛されていない")
            expected_cutover = {
                "authority_semantic_digest":expected_semantic,
                "release_unit_rows_digest":rows_digest,"candidate_content_digest":candidate_digest,
                "parent_dependency_receipts":expected_dependency_receipts,
                "parent_dependency_receipts_digest":parent_receipts_digest,
                "requirements_cutover_receipt":requirements_cutover_receipt,
                "manifest_digest":manifest_digest,"baseline_digest":baseline_digest,
                "production_write_authorized":False,"requirements_cutover_write_authorized":False,
                "ci_attestation_policy":{"provider":"github_actions","repository":"RetryYN/HELIX-MARKETING-HARNESS","workflow_ref":"RetryYN/HELIX-MARKETING-HARNESS/.github/workflows/requirements.yml@refs/heads/main","reviewer_principal":"github-actions"},
            }
            if cutover != expected_cutover:
                faults.append("media cutoverがcommit/tree/semantic/rows/parent receipts/artifacts/write禁止へ束縛されていない")
            head_blob_mismatch=False
            for artifact_path in (candidate_path,MANIFEST,baseline_path):
                if not isinstance(artifact_path,Path):
                    head_blob_mismatch=True
                    continue
                try:
                    relative_path=artifact_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
                    blob=git("show",f"HEAD:{relative_path}")
                    if blob.returncode!=0 or blob.stdout.encode()!=artifact_path.read_bytes():
                        head_blob_mismatch=True
                except (OSError,ValueError):
                    head_blob_mismatch=True
            ci_environment_valid = (
                os.environ.get("GITHUB_ACTIONS") == "true"
                and os.environ.get("GITHUB_SHA") == head
                and os.environ.get("GITHUB_REPOSITORY") == "RetryYN/HELIX-MARKETING-HARNESS"
                and isinstance(os.environ.get("GITHUB_RUN_ID"), str)
                and bool(os.environ.get("GITHUB_RUN_ID"))
                and _completed_media_independent_go(head, {
                    "candidate":candidate_digest,"manifest":manifest_digest,"baseline":baseline_digest,
                    "authority_semantic":expected_semantic,"release_unit_rows":rows_digest,
                    "parent_dependency_receipts":parent_receipts_digest,
                })
            )
            if (
                not isinstance(cutover,dict)
                or not ci_environment_valid
                or head_blob_mismatch
            ):
                faults.append("media independent Goがtrusted GitHub Actions run・HEAD blob・semantic/rows/parentsを被覆しない")
    else:
        faults.append("media release cutover completeは未実装のためfail-close")
    return faults


def critical_responsibility_disposition_faults(refinements: dict[str, Any]) -> list[str]:
    """旧通知・承認・自動運用・UI責務を新要求へ明示分割する。"""
    rows = (
        refinements.get("legacy_critical_responsibility_dispositions")
        if isinstance(refinements, dict)
        else None
    )
    if not isinstance(rows, list):
        return ["旧critical responsibility disposition mapがない"]
    expected_ids = {"BR-H2", "BR-H3", "FR-16", "FR-43", "FR-46", "FR-75", "FR-76", "FR-77"}
    ids = [row.get("legacy_id") for row in rows if isinstance(row, dict)]
    faults: list[str] = []
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        faults.append(f"旧critical責務被覆が不正 missing={sorted(expected_ids - set(ids))}")
    records = refinements.get("records")
    subjects = {
        record.get("subject_id")
        for record in records or []
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
        "BR-H2": [
            "VPS-UI-PRIMARY-HUMAN-INTERFACE",
            "AUTOMATED-PUBLISHING-ADMISSION",
            "毎回承認なし",
            "Discordを通知又は承認transportにする",
        ],
        "BR-H3": ["VPS-UI-INBOX-LIFECYCLE", "ApprovalTransport再利用", "Discord通知"],
        "FR-16": ["safety-stop", "operational inbox event", "FR-46 ApprovalTransport呼出"],
        "FR-43": ["repair lifecycle", "operational inbox event", "Discord通知"],
        "FR-46": [
            "初回activation",
            "通常投稿はactivation scope内",
            "channel=discord固定",
            "機械criteriaだけのauto-mode移行",
        ],
        "FR-75": ["BUSINESS-PROFILE-AUTHORIZATION", "preflight", "自動付替え"],
        "FR-76": [
            "VPS UI内inbox",
            "将来の外部通知adapter",
            "Discord transport",
            "ApprovalTransport同型tuple",
        ],
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
    configured = policy.get("dimensions")
    if not isinstance(configured, dict) or set(configured) != dimensions:
        faults.append("12意味軸policyが過不足")
        configured = {}
    direct_required = {
        "actors",
        "tasks",
        "workflow",
        "scope_in",
        "scope_out",
        "human_judgement",
        "side_effects",
        "evidence",
        "phase",
    }
    for dimension in direct_required:
        if (configured.get(dimension) or {}).get("mode") != "direct_required":
            faults.append(f"{dimension}: 対象層で直接宣言されない")
    if (configured.get("prohibitions") or {}).get("mode") != "inherit_plus_local":
        faults.append("prohibitions: 上位禁止の非弱化継承がない")
    if policy.get("unknown_default") != "question_then_deferred":
        faults.append("未知意味fieldが質問又はdeferredにならない")
    expected_binding = [
        "source_kind",
        "source_stable_id",
        "source_revision",
        "source_semantic_digest",
        "dimension",
        "scope_transform",
        "rationale",
    ]
    if policy.get("inheritance_binding_required") != expected_binding:
        faults.append("意味継承がsource revision/digest/scope transformへ束縛されない")
    edges = policy.get("edge_contracts")
    expected_edges = {
        "SED-BR-REQ",
        "SED-BRM-MR",
        "SED-REQ-FR",
        "SED-REQ-SR",
        "SED-REQ-NFR",
        "SED-REQUIREMENT-FN",
        "SED-REQUIREMENT-AC",
        "SED-AC-TC",
        "SED-FN-CMP",
        "SED-CMP-DU",
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
        str(record.get("subject_id"))
        for record in records
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
        "NFR-1": "redescent",
        "NFR-2": "redescent",
        "NFR-3": "redescent",
        "NFR-4": "redescent",
        "NFR-5": "redescent",
        "NFR-6": "defer",
        "NFR-7": "replace",
        "NFR-8": "redescent",
        "NFR-9": "defer",
        "NFR-10": "defer",
        "NFR-11": "defer",
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
        "FR-17",
        "FR-35",
        "FR-45",
        "FR-48",
        "FR-53",
        "FR-72",
        "FR-73",
        "FR-74",
        "FR-75",
        "FR-76",
        "FR-77",
        *(f"SR-{index:02d}" for index in range(1, 20)),
    }
    covered = [
        stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])
    ]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧orphan FR/SR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    known_ids = {str(item.get("id")) for item in _items(ctx.frc)} | {
        str(item.get("id")) for item in _items(ctx.src)
    }
    records = refinements.get("records", [])
    subjects = {
        str(record.get("subject_id"))
        for record in records
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
        "FR-45": "defer",
        "FR-53": "defer",
        "FR-72": "replace",
        "FR-73": "defer",
        "FR-74": "replace",
        "FR-75": "replace",
        "FR-76": "replace",
        "FR-77": "replace",
        "SR-15": "replace",
        "SR-17": "defer",
        "SR-18": "defer",
        "SR-19": "defer",
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
    covered = [
        stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])
    ]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧REQ被覆が不正 missing={sorted(expected_ids - set(covered))}")
    known_ids = {str(item.get("id")) for item in _items(ctx.req)}
    records = refinements.get("records", [])
    subjects = {
        str(record.get("subject_id"))
        for record in records
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
        "REQ-006": "replace",
        "REQ-012": "replace",
        "REQ-015": "replace",
        "REQ-021": "defer",
        "REQ-022": "replace",
        "REQ-024": "replace",
        "REQ-025": "defer",
        "REQ-026": "replace",
        "REQ-027": "defer",
        "REQ-028": "replace",
        "REQ-029": "replace",
        "REQ-031": "replace",
        "REQ-033": "replace",
        "REQ-034": "defer",
        "REQ-035": "replace",
        "REQ-036": "replace",
        "REQ-037": "replace",
        "REQ-038": "replace",
        "REQ-039": "replace",
        "REQ-042": "replace",
        "REQ-043": "replace",
        "REQ-044": "replace",
        "REQ-045": "defer",
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
        "REQ-031": [
            "暗号化store",
            "現行runtime再起動後は外部操作停止",
            "credential単独auto-unlockは禁止",
        ],
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


def _legacy_requirement_meaning_snapshot(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """旧BR/REQ/FRの意味をID別に固定し、group分類で固有句を失わせない。"""
    br_keys = (
        "title",
        "purpose",
        "actor",
        "problem",
        "value",
        "scope_in",
        "scope_out",
        "constraints",
        "prohibitions",
        "human_judgement",
        "failure_impact",
        "completion_evidence",
    )
    req_keys = ("text", "source_refs", "related", "fill_route", "priority", "trace")
    fr_keys = (
        "title",
        "input",
        "output",
        "precondition",
        "postcondition",
        "invariants",
        "normal_behavior",
        "rejection_behavior",
        "boundary_behavior",
        "retry_resume_recovery",
        "human_judgement",
        "side_effects",
        "idempotency",
        "evidence",
        "external_deps",
        "config_values",
        "fixed_values",
        "slice",
    )
    result: dict[str, dict[str, Any]] = {}
    for layer, items, keys in (
        ("BR", _items(ctx.brc), br_keys),
        ("REQ", _items(ctx.req), req_keys),
        ("FR", _items(ctx.frc), fr_keys),
    ):
        for item in items:
            stable_id = str(item.get("id"))
            result[stable_id] = {
                "layer": layer,
                "source_semantics": {key: item.get(key) for key in keys if key in item},
            }
    return dict(sorted(result.items()))


def _legacy_strategy_quality_meaning_snapshot(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """旧SR/NFRの意味をID別に固定し、group要約だけの棚卸しを拒否する。"""
    result: dict[str, dict[str, Any]] = {}
    for layer, items in (("SR", ctx.src), ("NFR", ctx.nfc)):
        for item in items:
            stable_id = str(item.get("id"))
            result[stable_id] = {
                "layer": layer,
                "source_semantics": {key: value for key, value in item.items() if key != "id"},
            }
    return dict(sorted(result.items()))


def legacy_strategy_quality_meaning_inventory_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧SR19/NFR11をvalue/safety/HJ/obsolete単位でID別に固定する。"""
    policy = refinements.get("legacy_strategy_quality_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧SR/NFR意味inventoryがない"]
    snapshot = _legacy_strategy_quality_meaning_snapshot(ctx)
    expected_ids = set(snapshot)
    rows = policy.get("meaning_migrations")
    faults: list[str] = []
    if policy.get("stable_id_count") != 30 or policy.get("stable_id_digest") != _digest(sorted(expected_ids)):
        faults.append("旧SR/NFR意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧SR/NFR意味inventoryのsource digestが不一致")
    restart_decision = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-008")
    if policy.get("credential_restart_decision_digest") != _digest(restart_decision):
        faults.append("旧SR/NFR意味inventoryがVPS再起動判断へ束縛されていない")
    if not isinstance(rows, dict) or set(rows) != expected_ids:
        faults.append("旧SR/NFR全30 IDの意味移送被覆がない")
        rows = rows if isinstance(rows, dict) else {}
    expected_keys = {
        "source_digest",
        "disposition",
        "retained_value_clauses",
        "retained_safety_clauses",
        "retained_human_judgement_clauses",
        "obsolete_or_prohibited_clauses",
        "owner_subject_ids",
        "resume_conditions",
    }
    known_subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    sr_dispositions: dict[str, tuple[str, list[str], list[str]]] = {}
    for group in refinements.get("legacy_orphan_requirement_groups", []):
        if not isinstance(group, dict):
            continue
        for stable_id in group.get("stable_ids", []):
            if str(stable_id).startswith("SR-"):
                sr_dispositions[str(stable_id)] = (
                    str(group.get("disposition")),
                    list(group.get("owner_subject_ids", [])),
                    list(group.get("resume_conditions", [])),
                )
    nfr_dispositions = {
        str(row.get("nfr_id")): (
            str(row.get("disposition")),
            list(row.get("owner_subject_ids", [])),
            list(row.get("resume_conditions", [])),
        )
        for row in refinements.get("legacy_nfr_dispositions", [])
        if isinstance(row, dict)
    }
    expected_dispositions = {**sr_dispositions, **nfr_dispositions}
    for stable_id, row in rows.items():
        if not isinstance(row, dict) or set(row) != expected_keys:
            faults.append(f"{stable_id}: SR/NFR意味移送field閉集合が不正")
            continue
        if row.get("source_digest") != _digest(snapshot[stable_id]):
            faults.append(f"{stable_id}: SR/NFR source meaning digest不一致")
        expected = expected_dispositions.get(stable_id)
        if expected is None or row.get("disposition") != expected[0]:
            faults.append(f"{stable_id}: SR/NFR ID別処置が不一致")
        for key in (
            "retained_value_clauses",
            "retained_safety_clauses",
            "retained_human_judgement_clauses",
            "obsolete_or_prohibited_clauses",
        ):
            values = row.get(key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                faults.append(f"{stable_id}: {key}が空・重複又は不正")
        owners = row.get("owner_subject_ids")
        if (
            not isinstance(owners, list)
            or not owners
            or len(owners) != len(set(owners))
            or not set(owners) <= known_subjects
            or (expected is not None and not set(expected[1]) <= set(owners))
        ):
            faults.append(f"{stable_id}: SR/NFR meaning ownerが不正")
        resume = row.get("resume_conditions")
        if (
            not isinstance(resume, list)
            or len(resume) != len(set(resume))
            or (row.get("disposition") == "defer") != bool(resume)
        ):
            faults.append(f"{stable_id}: SR/NFR defer境界が不正")
    critical = {
        "SR-13": {
            "retained_human_judgement_clauses": ["企画内容の採否は人間が判断しagentは提案と検査だけを行う"],
            "obsolete_or_prohibited_clauses": [
                "別agent審査を人間判断の代替にせず固定5 field名を品質そのものにしない"
            ],
        },
        "SR-15": {
            "retained_human_judgement_clauses": ["release scopeはPOが判断する"],
            "obsolete_or_prohibited_clauses": ["旧S0名称・5点固定・旧L2-L6を現releaseへ流用しない"],
        },
        "SR-17": {
            "obsolete_or_prohibited_clauses": ["8軸語彙・旧schema・draft STCを受入authorityにしない"],
        },
        "SR-18": {
            "obsolete_or_prohibited_clauses": [
                "全自動判定・旧append-only方式・draft STCを受入authorityにしない"
            ],
        },
        "SR-19": {
            "obsolete_or_prohibited_clauses": [
                "3水準・旧分析手法・自動決定・draft STCを受入authorityにしない"
            ],
        },
        "NFR-4": {
            "retained_human_judgement_clauses": [
                "現行runtimeのrestart/unlockは人間が再認可し、credential単独auto-unlockを禁止する。recovery/break-glass方式とprincipalは別途PO判断する"
            ],
            "obsolete_or_prohibited_clauses": [
                "平文envを禁止しつつ特定store又は有人注入方式をPO判断前に確定しない"
            ],
        },
        "NFR-9": {
            "obsolete_or_prohibited_clauses": ["旧MR-HS・LINE・旧法名・機械gateだけをstable rootにしない"],
        },
        "NFR-10": {
            "obsolete_or_prohibited_clauses": [
                "SQLite日次14世代・browser session・Docker WP一括backupを継承しない"
            ],
        },
        "NFR-11": {
            "obsolete_or_prohibited_clauses": [
                "FR-74又は別NFRをroot代替にせずUTC月次窓や固定scopeを継承しない"
            ],
        },
    }
    for stable_id, required_by_field in critical.items():
        row = rows.get(stable_id, {})
        for field, required_values in required_by_field.items():
            if not set(required_values) <= set(row.get(field, [])):
                faults.append(f"{stable_id}: 重要意味境界{field}が欠落又は反転")
    migrations_digest = _digest(rows)
    if policy.get("meaning_migrations_digest") != migrations_digest:
        faults.append("旧SR/NFR全30 ID意味移送の閉集合digestが不一致")
    status = policy.get("status")
    approval = policy.get("classification_approval")
    if status == "pending_po_semantic_classification":
        if policy.get("cutover_blocked") is not True or approval is not None:
            faults.append("旧SR/NFR意味inventoryの未承認cutover境界が不正")
        faults.append("旧SR/NFR意味分類候補がPO未承認 remaining=0")
    elif status == "classified":
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "source_snapshot_digest": policy.get("source_snapshot_digest"),
            "meaning_migrations_digest": migrations_digest,
        }
        if (
            policy.get("cutover_blocked") is not False
            or not isinstance(approval, dict)
            or {key: approval.get(key) for key in expected_approval} != expected_approval
            or not isinstance(approval.get("approved_at"), str)
        ):
            faults.append("旧SR/NFR全30 ID意味分類にPO receiptがない又はdigest不一致")
    else:
        faults.append("旧SR/NFR意味inventory statusが不正")
    return faults


def _legacy_mr_meaning_snapshot() -> dict[str, dict[str, Any]]:
    """旧MRのfile/media identityを含む全意味fieldをID別に固定する。"""
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(MR_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        for item in _items(load(path)):
            stable_id = str(item.get("id"))
            result[stable_id] = {
                "media_id": path.stem,
                "source_semantics": {key: value for key, value in item.items() if key != "id"},
            }
    return dict(sorted(result.items()))


def legacy_mr_meaning_inventory_faults(refinements: dict[str, Any]) -> list[str]:
    """旧MR54件の価値・route禁止・人間判断・再開条件をID別に固定する。"""
    policy = refinements.get("legacy_mr_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧MR意味inventoryがない"]
    snapshot = _legacy_mr_meaning_snapshot()
    expected_ids = set(snapshot)
    rows = policy.get("meaning_migrations")
    faults: list[str] = []
    if policy.get("stable_id_count") != 54 or policy.get("stable_id_digest") != _digest(sorted(expected_ids)):
        faults.append("旧MR意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧MR意味inventoryのsource digestが不一致")
    if not isinstance(rows, dict) or set(rows) != expected_ids:
        faults.append("旧MR全54 IDの意味移送被覆がない")
        rows = rows if isinstance(rows, dict) else {}
    media_policies = {
        str(row.get("media_id")): row
        for row in refinements.get("legacy_media_br_dispositions", [])
        if isinstance(row, dict)
    }
    known_subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    expected_keys = {
        "source_digest",
        "disposition",
        "retained_value_clauses",
        "retained_safety_clauses",
        "retained_human_judgement_clauses",
        "obsolete_or_prohibited_clauses",
        "owner_subject_ids",
        "resume_conditions",
    }
    wp_owner_bindings = {
        "MR-WP-1": [
            {
                "operation": "content_publish",
                "effect": "publish",
                "owner_subject_id": "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
            }
        ],
        "MR-WP-2": [
            {
                "operation": "content_authority",
                "effect": "state_write",
                "owner_subject_id": "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
            }
        ],
        "MR-WP-3": [
            {
                "operation": "platform_maintenance",
                "effect": "release",
                "owner_subject_id": "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE",
            }
        ],
        "MR-WP-4": [
            {
                "operation": "content_feed_distribution",
                "effect": "publish",
                "owner_subject_id": "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
            }
        ],
        "MR-WP-5": [
            {
                "operation": "content_operation_quota",
                "effect": "state_write",
                "owner_subject_id": "WORDPRESS-CONTENT-OPERATIONS-RELEASE",
            },
            {
                "operation": "platform_operation_quota",
                "effect": "release",
                "owner_subject_id": "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE",
            },
            {
                "operation": "security_operation_quota",
                "effect": "credential",
                "owner_subject_id": "WORDPRESS-SECURITY-MAINTENANCE-RELEASE",
            },
        ],
    }
    for stable_id, row in rows.items():
        row_keys = expected_keys | ({"owner_bindings"} if stable_id in wp_owner_bindings else set())
        if not isinstance(row, dict) or set(row) != row_keys:
            faults.append(f"{stable_id}: MR意味移送field閉集合が不正")
            continue
        if row.get("source_digest") != _digest(snapshot[stable_id]):
            faults.append(f"{stable_id}: MR source meaning digest不一致")
        media = media_policies.get(snapshot[stable_id]["media_id"], {})
        if row.get("disposition") != media.get("disposition"):
            faults.append(f"{stable_id}: MR処置が媒体policyと不一致")
        for key in (
            "retained_value_clauses",
            "retained_safety_clauses",
            "retained_human_judgement_clauses",
            "obsolete_or_prohibited_clauses",
        ):
            values = row.get(key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                faults.append(f"{stable_id}: {key}が空・重複又は不正")
        owners = row.get("owner_subject_ids")
        media_owners = set(media.get("owner_subject_ids", []))
        if (
            not isinstance(owners, list)
            or not owners
            or len(owners) != len(set(owners))
            or not set(owners) <= known_subjects
        ):
            faults.append(f"{stable_id}: MR meaning ownerが不正")
        if stable_id in wp_owner_bindings:
            bindings = row.get("owner_bindings")
            expected_bindings = wp_owner_bindings[stable_id]
            if bindings != expected_bindings or set(owners or []) != {
                binding["owner_subject_id"] for binding in expected_bindings
            }:
                faults.append(f"{stable_id}: WP operation/effect owner bindingが不正")
        elif not media_owners <= set(owners or []):
            faults.append(f"{stable_id}: MR meaning ownerが媒体policyを包含しない")
        resume = row.get("resume_conditions")
        if (
            not isinstance(resume, list)
            or not resume
            or len(resume) != len(set(resume))
            or not set(media.get("resume_conditions", [])) <= set(resume)
        ):
            faults.append(f"{stable_id}: MR再開条件が媒体policyを包含しない")
    critical = {
        "MR-DC-1": ("retained_safety_clauses", "製品通知・承認・PR通知と経路credentialを共有しない"),
        "MR-GENAI-1": ("obsolete_or_prohibited_clauses", "consumer Web UI、API無課金、特定生成種別固定"),
        "MR-LINE-3": ("retained_safety_clauses", "API優先、browserはattended確認のみ、unknown時停止"),
        "MR-PLAY-1": ("retained_human_judgement_clauses", "超後期app releaseはPO/release ownerが判断する"),
        "MR-X-3": ("retained_safety_clauses", "Playwright write禁止、API採用時もprovider quotaを適用する"),
        "MR-WP-3": ("retained_safety_clauses", "未検証知識でplatform又はsecurity変更を行わない"),
        "MR-STRIPE-1": ("retained_human_judgement_clauses", "全money operationは対応authorityが判断する"),
        "MR-HS-3": ("obsolete_or_prohibited_clauses", "旧法名・HubSpot保管・SQLite非PII分類をroot化しない"),
    }
    for stable_id, (field, required) in critical.items():
        if required not in rows.get(stable_id, {}).get(field, []):
            faults.append(f"{stable_id}: 重要MR意味境界{field}が欠落又は反転")
    migrations_digest = _digest(rows)
    if policy.get("meaning_migrations_digest") != migrations_digest:
        faults.append("旧MR全54 ID意味移送の閉集合digestが不一致")
    status = policy.get("status")
    approval = policy.get("classification_approval")
    if status == "pending_po_semantic_classification":
        if policy.get("cutover_blocked") is not True or approval is not None:
            faults.append("旧MR意味inventoryの未承認cutover境界が不正")
        faults.append("旧MR意味分類候補がPO未承認 remaining=0")
    elif status == "classified":
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "source_snapshot_digest": policy.get("source_snapshot_digest"),
            "meaning_migrations_digest": migrations_digest,
        }
        if (
            policy.get("cutover_blocked") is not False
            or not isinstance(approval, dict)
            or {key: approval.get(key) for key in expected_approval} != expected_approval
            or not isinstance(approval.get("approved_at"), str)
        ):
            faults.append("旧MR全54 ID意味分類にPO receiptがない又はdigest不一致")
    else:
        faults.append("旧MR意味inventory statusが不正")
    return faults


def _legacy_fn_meaning_snapshot(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """旧FNの表示順やidを除く意味sourceを安定snapshot化する。"""
    return {
        str(item["id"]): {
            "file_identity": "docs/L3-system-requirements/canonical/functional/fn.json",
            **{key: value for key, value in item.items() if key != "id"},
        }
        for item in _items(ctx.fn)
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _fn_parent_semantic_rows(
    parent_refs: list[str], refinements: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    inventories = {
        "FR": refinements.get("legacy_requirement_meaning_inventory", {}).get("meaning_migrations", {}),
        "SR": refinements.get("legacy_strategy_quality_meaning_inventory", {}).get("meaning_migrations", {}),
        "NFR": refinements.get("legacy_strategy_quality_meaning_inventory", {}).get("meaning_migrations", {}),
        "MR": refinements.get("legacy_mr_meaning_inventory", {}).get("meaning_migrations", {}),
    }
    result: dict[str, dict[str, Any]] = {}
    for parent_ref in sorted(parent_refs):
        kind = parent_ref.split("-", 1)[0]
        row = inventories.get(kind, {}).get(parent_ref)
        if isinstance(row, dict):
            result[parent_ref] = row
    return result


def legacy_fn_meaning_inventory_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧FN61件を親意味digestとFN固有作用deltaへ束縛し、再降下前の利用を止める。"""
    policy = refinements.get("legacy_fn_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧FN意味inventoryがない"]
    snapshot = _legacy_fn_meaning_snapshot(ctx)
    expected_ids = set(snapshot)
    rows = policy.get("meaning_migrations")
    faults: list[str] = []
    if policy.get("stable_id_count") != 61 or policy.get("stable_id_digest") != _digest(sorted(expected_ids)):
        faults.append("旧FN意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧FN意味inventoryのsource digestが不一致")
    if not isinstance(rows, dict) or set(rows) != expected_ids:
        faults.append("旧FN全61 IDの意味移送被覆がない")
        rows = rows if isinstance(rows, dict) else {}
    expected_keys = {
        "source_digest",
        "parent_refs",
        "parent_semantic_digest",
        "disposition",
        "direct_semantics",
        "no_direct_semantics_reason",
        "owner_bindings",
        "legacy_phase",
        "phase_disposition",
        "evidence_requirements",
        "obsolete_mechanisms",
        "resume_conditions",
    }
    semantic_keys = {"actors", "value", "scope_in", "scope_out", "human_judgement", "side_effects"}
    high_effects = {"external_write", "publish", "money", "credential", "release"}
    for stable_id, row in rows.items():
        if not isinstance(row, dict) or set(row) != expected_keys:
            faults.append(f"{stable_id}: FN意味移送field閉集合が不正")
            continue
        source = snapshot[stable_id]
        if row.get("source_digest") != _digest(source):
            faults.append(f"{stable_id}: FN source meaning digest不一致")
        related = sorted(ref for ref in source.get("related", []) if isinstance(ref, str))
        trace = source.get("trace", {})
        upstream = (
            sorted(ref for ref in trace.get("upstream", []) if isinstance(ref, str))
            if isinstance(trace, dict)
            else []
        )
        parent_refs = row.get("parent_refs")
        if related != upstream or parent_refs != related:
            faults.append(f"{stable_id}: related/trace/parent_refsがexact一致しない")
        parent_rows = _fn_parent_semantic_rows(related, refinements)
        if len(parent_rows) != len(related) or row.get("parent_semantic_digest") != _digest(parent_rows):
            faults.append(f"{stable_id}: parent semantic digestが不一致")
        disposition = row.get("disposition")
        if stable_id == "FN-413":
            if parent_refs != [] or disposition != "defer_until_stable_parent":
                faults.append("FN-413: stable parentなしの媒体omnibusをdeferしていない")
        elif disposition not in {"inherit_and_redescent", "defer_until_parent_redescent"}:
            faults.append(f"{stable_id}: FN dispositionが不正")
        semantics = row.get("direct_semantics")
        if not isinstance(semantics, dict) or set(semantics) != semantic_keys:
            faults.append(f"{stable_id}: FN direct semantics型が不正")
            continue
        for key, values in semantics.items():
            if not isinstance(values, list) or len(values) != len(set(map(str, values))):
                faults.append(f"{stable_id}: direct_semantics.{key}が不正")
        has_direct = any(semantics.values())
        reason = row.get("no_direct_semantics_reason")
        if has_direct == bool(reason):
            faults.append(f"{stable_id}: direct semanticsと継承理由が矛盾")
        bindings = row.get("owner_bindings")
        effects = set(semantics.get("side_effects", []))
        if not isinstance(bindings, list) or len(bindings) != len(
            {json.dumps(binding, ensure_ascii=False, sort_keys=True) for binding in bindings}
        ):
            faults.append(f"{stable_id}: FN owner bindingsが不正")
        if effects & high_effects and (not bindings or not semantics.get("human_judgement")):
            faults.append(f"{stable_id}: 高作用FNにprincipal/HJ bindingがない")
        if row.get("legacy_phase") != source.get("slice"):
            faults.append(f"{stable_id}: legacy phase snapshotが不一致")
        if row.get("phase_disposition") != "pending_po_classification":
            faults.append(f"{stable_id}: 旧sliceをcurrent phaseへ昇格している")
        for key in ("evidence_requirements", "obsolete_mechanisms", "resume_conditions"):
            values = row.get(key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                faults.append(f"{stable_id}: {key}が空・重複又は不正")
    critical = {
        "FN-101": ("value", "有効なstrategic briefで下位run開始をguardする"),
        "FN-102": ("scope_out", "下流から上流戦略正本への直接更新"),
        "FN-105": ("human_judgement", "検査基準の改訂は許可principalが判断する"),
        "FN-107": ("scope_out", "上流戦略正本の直接更新"),
        "FN-108": ("human_judgement", "上位戦略の採否と改訂はstrategy authorityが判断する"),
        "FN-110": ("side_effects", "state_write"),
        "FN-202": ("side_effects", "publish"),
        "FN-207": ("side_effects", "money"),
        "FN-302": ("human_judgement", "business premiseとscopeはユーザーが確定する"),
        "FN-401": ("value", "API/MCP優先と必要時Playwright確認をoperation単位で選ぶ"),
        "FN-410": ("human_judgement", "scope activationは許可principalが判断する"),
        "FN-411": ("side_effects", "credential"),
        "FN-413": ("scope_out", "stable parent未確定の媒体omnibus外部操作"),
        "FN-603": ("scope_out", "部分投入を完全データとして扱うこと"),
        "FN-702": ("side_effects", "release"),
    }
    for stable_id, (field, required) in critical.items():
        values = rows.get(stable_id, {}).get("direct_semantics", {}).get(field, [])
        if required not in values:
            faults.append(f"{stable_id}: 重要FN意味境界{field}が欠落又は反転")
    migrations_digest = _digest(rows)
    if policy.get("meaning_migrations_digest") != migrations_digest:
        faults.append("旧FN全61 ID意味移送の閉集合digestが不一致")
    status = policy.get("status")
    approval = policy.get("classification_approval")
    if status == "pending_po_semantic_classification":
        if policy.get("cutover_blocked") is not True or approval is not None:
            faults.append("旧FN意味inventoryの未承認cutover境界が不正")
        faults.append("旧FN意味分類候補がPO未承認 remaining=0")
    elif status == "classified":
        parent_inventory_keys = {
            "FR": "legacy_requirement_meaning_inventory",
            "SR": "legacy_strategy_quality_meaning_inventory",
            "NFR": "legacy_strategy_quality_meaning_inventory",
            "MR": "legacy_mr_meaning_inventory",
        }
        used_parent_kinds = {
            parent_ref.split("-", 1)[0]
            for row in rows.values()
            if isinstance(row, dict)
            for parent_ref in row.get("parent_refs", [])
            if isinstance(parent_ref, str)
        }
        for inventory_key in {
            parent_inventory_keys[kind] for kind in used_parent_kinds if kind in parent_inventory_keys
        }:
            parent_inventory = refinements.get(inventory_key, {})
            parent_approval = parent_inventory.get("classification_approval", {})
            parent_rows = parent_inventory.get("meaning_migrations", {})
            if (
                parent_inventory.get("status") != "classified"
                or parent_inventory.get("cutover_blocked") is not False
                or not isinstance(parent_approval, dict)
                or parent_approval.get("source_snapshot_digest")
                != parent_inventory.get("source_snapshot_digest")
                or parent_approval.get("meaning_migrations_digest") != _digest(parent_rows)
            ):
                faults.append(f"旧FN分類の親inventory {inventory_key} がPO承認済みclassifiedでない")
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "source_snapshot_digest": policy.get("source_snapshot_digest"),
            "meaning_migrations_digest": migrations_digest,
        }
        if (
            policy.get("cutover_blocked") is not False
            or not isinstance(approval, dict)
            or {key: approval.get(key) for key in expected_approval} != expected_approval
            or not isinstance(approval.get("approved_at"), str)
        ):
            faults.append("旧FN全61 ID意味分類にPO receiptがない又はdigest不一致")
    else:
        faults.append("旧FN意味inventory statusが不正")
    return faults


def _legacy_ac_meaning_snapshot(ctx: Ctx) -> dict[str, dict[str, Any]]:
    return {
        str(item["id"]): {
            "file_identity": "docs/L3-system-requirements/canonical/acceptance/ac-contracts.json",
            **{key: value for key, value in item.items() if key != "id"},
        }
        for item in _items(ctx.acc)
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def legacy_ac_meaning_inventory_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧AC252件のoracle構造を親要求/FN意味とAC固有deltaへ束縛する。"""
    policy = refinements.get("legacy_ac_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧AC意味inventoryがない"]
    snapshot = _legacy_ac_meaning_snapshot(ctx)
    expected_ids = set(snapshot)
    rows = policy.get("meaning_migrations")
    faults: list[str] = []
    if policy.get("stable_id_count") != 252 or policy.get("stable_id_digest") != _digest(
        sorted(expected_ids)
    ):
        faults.append("旧AC意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧AC意味inventoryのsource digestが不一致")
    restart_decision = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-008")
    if policy.get("credential_restart_decision_digest") != _digest(restart_decision):
        faults.append("旧AC意味inventoryがVPS再起動判断へ束縛されていない")
    if not isinstance(rows, dict) or set(rows) != expected_ids:
        faults.append("旧AC全252 IDの意味移送被覆がない")
        rows = rows if isinstance(rows, dict) else {}
    fn_rows = refinements.get("legacy_fn_meaning_inventory", {}).get("meaning_migrations", {})
    expected_keys = {
        "source_digest",
        "target",
        "parent_requirement_digest",
        "fn_refs",
        "fn_semantic_digest",
        "source_oracle_digest",
        "polarity",
        "disposition",
        "oracle_delta",
        "no_direct_oracle_reason",
        "owner_bindings",
        "phase_snapshot",
        "phase_disposition",
        "evidence_dimensions",
        "obsolete_oracle_clauses",
        "resume_conditions",
        "critical_family_refs",
        "critical_family_digest",
        "family_compliance",
    }
    delta_keys = {
        "actors",
        "value",
        "scope_in",
        "scope_out",
        "human_judgement",
        "allowed_effects",
        "forbidden_effects",
        "evidence",
    }
    source_oracle_keys = {
        "given",
        "when",
        "then",
        "fixture",
        "observation_point",
        "expected_state",
        "expected_db_delta",
        "expected_evidence",
        "forbidden_side_effects",
        "error_type",
    }
    high_effects = {"external_write", "publish", "money", "credential", "release", "notification"}
    family_policies = {
        "notification-purpose-separation": {
            "required": ["VPS UI内inbox", "approval/operational/community/dev PRのpurpose分離"],
            "prohibited": ["Discord製品通知", "ApprovalTransportによる異常通知"],
            "controls": {
                "product_notification_channel": "vps_ui_inbox",
                "decision_surface": "vps_ui",
                "discord_role": "community_marketing_only",
            },
        },
        "activation-human-authority": {
            "required": ["初回activation・scope拡張・停止後再開は許可principal判断"],
            "prohibited": ["preflight又はcriteriaによる人間判断代替"],
            "controls": {
                "activation_authority": "permission_principal",
                "automated_gate_role": "eligibility_only",
            },
        },
        "money-operation-authority": {
            "required": ["operation/amount/target/currency/deadline/principal束縛"],
            "prohibited": ["未承認money operation", "顧客入金・事業支出・返金の混在"],
            "controls": {
                "decision_authority": "money_principal",
                "operation_partition": "charge_spend_refund_separate",
            },
        },
        "credential-lifecycle-authority": {
            "required": [
                "repo/DB/log/evidenceへのsecret保存禁止",
                "現行runtime再起動後は外部操作停止を維持し、実行系再初期化時に人間がunlockを再認可する",
            ],
            "prohibited": [
                "SQLite又は平文envをcredential正本にすること",
                "credential単独auto-unlockで停止中runtimeが継続すると仮定すること",
            ],
            "controls": {
                "storage_boundary": "no_repo_db_log_evidence",
                "current_restart": "external_effects_stopped",
                "unlock_mode": "human_reauthorization_with_runtime_reinitialization",
                "credential_only_auto_unlock": "prohibited",
                "future_persistent_service": "separate_po_requirement",
            },
        },
        "vps-ui-primary": {
            "required": ["認証/session/profile scope付きVPS Web UI", "UI内inbox lifecycle"],
            "prohibited": ["static HTML又はAPI-onlyを製品UIの代替にすること"],
            "controls": {"primary_surface": "authenticated_vps_web_ui", "notification_surface": "ui_inbox"},
        },
        "wordpress-three-authorities": {
            "required": ["content/platform/securityのoperation・owner・release分離"],
            "prohibited": ["content publishとplatform/security maintenanceの同一oracle化"],
            "controls": {
                "authority_partition": "content_platform_security_separate",
                "release_partition": "operation_specific",
            },
        },
        "strategy-acceptance-authority": {
            "required": ["戦略・企画採否は許可principal判断", "旧二重AC-SRをunionしない"],
            "prohibited": ["別agent又はdraft STCによる人間判断代替"],
            "controls": {"acceptance_authority": "permission_principal", "legacy_ac_sr_union": "prohibited"},
        },
    }
    if policy.get("critical_family_policies") != family_policies:
        faults.append("AC critical family policyが不一致")
    strategy_disposition = refinements.get("legacy_strategy_ac_ledger_disposition", {})
    if policy.get("strategy_ac_ledger_disposition_digest") != _digest(strategy_disposition):
        faults.append("AC inventoryがstrategy二重台帳処遇digestへ束縛されていない")
    family_ids = {
        "notification-purpose-separation": {
            "AC-16-1",
            *{f"AC-46-{i}" for i in range(1, 5)},
            *{f"AC-76-{i}" for i in range(1, 4)},
        },
        "activation-human-authority": {
            *{f"AC-46-{i}" for i in range(1, 5)},
            *{f"AC-75-{i}" for i in range(1, 4)},
        },
        "money-operation-authority": {
            *{f"AC-26-{i}" for i in range(1, 4)},
            "AC-906",
        },
        "credential-lifecycle-authority": {
            *{f"AC-47-{i}" for i in range(1, 7)},
            "AC-904",
        },
        "vps-ui-primary": {
            *{f"AC-63-{i}" for i in range(1, 4)},
            *{f"AC-76-{i}" for i in range(1, 4)},
            *{f"AC-77-{i}" for i in range(1, 4)},
            "AC-905",
        },
        "wordpress-three-authorities": {f"AC-44-{i}" for i in range(1, 4)},
        "strategy-acceptance-authority": {
            ac_id for ac_id, source in snapshot.items() if str(source.get("target", "")).startswith("SR-")
        },
    }
    known_subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    for stable_id, row in rows.items():
        if not isinstance(row, dict) or set(row) != expected_keys:
            faults.append(f"{stable_id}: AC意味移送field閉集合が不正")
            continue
        source = snapshot[stable_id]
        if row.get("source_digest") != _digest(source):
            faults.append(f"{stable_id}: AC source meaning digest不一致")
        target = source.get("target")
        if row.get("target") != target or not isinstance(target, str):
            faults.append(f"{stable_id}: AC targetがsourceと不一致")
            continue
        parent_rows = _fn_parent_semantic_rows([target], refinements)
        if len(parent_rows) != 1 or row.get("parent_requirement_digest") != _digest(parent_rows):
            faults.append(f"{stable_id}: parent requirement semantic digestが不一致")
        expected_fn_refs = sorted(
            fn_id
            for fn_id, fn_row in fn_rows.items()
            if isinstance(fn_row, dict) and target in fn_row.get("parent_refs", [])
        )
        if row.get("fn_refs") != expected_fn_refs or row.get("fn_semantic_digest") != _digest(
            {fn_id: fn_rows[fn_id] for fn_id in expected_fn_refs}
        ):
            faults.append(f"{stable_id}: FN semantic digest又は逆引きが不一致")
        source_oracle = {key: source.get(key) for key in sorted(source_oracle_keys)}
        if row.get("source_oracle_digest") != _digest(source_oracle):
            faults.append(f"{stable_id}: source oracle digestが不一致")
        if row.get("polarity") != source.get("polarity"):
            faults.append(f"{stable_id}: polarityがsourceと不一致")
        if row.get("disposition") not in {"inherit_shape_and_redescent", "replace", "defer"}:
            faults.append(f"{stable_id}: AC oracle dispositionが不正")
        delta = row.get("oracle_delta")
        if not isinstance(delta, dict) or set(delta) != delta_keys:
            faults.append(f"{stable_id}: AC oracle delta型が不正")
            continue
        for key, values in delta.items():
            if not isinstance(values, list) or len(values) != len(set(values)):
                faults.append(f"{stable_id}: oracle_delta.{key}が不正")
        has_delta = any(delta.values())
        if has_delta == bool(row.get("no_direct_oracle_reason")):
            faults.append(f"{stable_id}: oracle deltaと継承理由が矛盾")
        effects = set(delta.get("allowed_effects", []))
        bindings = row.get("owner_bindings")
        if not isinstance(bindings, list) or len(bindings) != len(
            {json.dumps(binding, ensure_ascii=False, sort_keys=True) for binding in bindings}
        ):
            faults.append(f"{stable_id}: AC owner bindingsが不正")
            bindings = []
        binding_effects = {str(binding.get("effect")) for binding in bindings if isinstance(binding, dict)}
        binding_owners = {
            str(binding.get("owner_subject_id")) for binding in bindings if isinstance(binding, dict)
        }
        if not binding_effects <= effects or not binding_owners <= known_subjects:
            faults.append(f"{stable_id}: AC owner bindingのeffect又はownerが不正")
        if effects - {"none"} != binding_effects:
            faults.append(f"{stable_id}: allowed effectがownerへexactly束縛されていない")
        if effects & high_effects and (
            not bindings
            or not delta.get("human_judgement")
            or not delta.get("scope_in")
            or not delta.get("evidence")
        ):
            faults.append(f"{stable_id}: 高作用ACにprincipal/scope/HJ/evidenceがない")
        if row.get("phase_snapshot") != source.get("target_update"):
            faults.append(f"{stable_id}: AC phase snapshotが不一致")
        if row.get("phase_disposition") != "pending_po_classification":
            faults.append(f"{stable_id}: 旧target_updateをcurrent phaseへ昇格している")
        for key in ("evidence_dimensions", "obsolete_oracle_clauses", "resume_conditions"):
            values = row.get(key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                faults.append(f"{stable_id}: {key}が空・重複又は不正")
        expected_refs = sorted(family for family, ids in family_ids.items() if stable_id in ids)
        if row.get("critical_family_refs") != expected_refs or row.get("critical_family_digest") != _digest(
            {family: family_policies[family] for family in expected_refs}
        ):
            faults.append(f"{stable_id}: critical family意味継承が不一致")
        expected_compliance = {
            family: {
                "required_ack": family_policies[family]["required"],
                "prohibited_ack": family_policies[family]["prohibited"],
                "controls": family_policies[family]["controls"],
                "oracle_delta_authority": "subordinate_to_family_controls",
            }
            for family in expected_refs
        }
        if row.get("family_compliance") != expected_compliance:
            faults.append(f"{stable_id}: critical family complianceが不一致")
        family_representatives = {
            "AC-16-1",
            "AC-46-1",
            "AC-75-1",
            "AC-76-1",
            "AC-26-1",
            "AC-47-1",
            "AC-63-1",
            "AC-77-1",
            "AC-44-1",
            "AC-SR-13-1",
        }
        if expected_refs and stable_id not in family_representatives and has_delta:
            faults.append(f"{stable_id}: family control再降下前に個別oracle deltaを上書きしている")
    critical = {
        "AC-16-1": ("scope_out", "投稿可否承認transportへの異常通知接続"),
        "AC-46-1": ("scope_in", "VPS UI上の投稿可否decision"),
        "AC-75-1": ("human_judgement", "初回activation・scope拡張・停止後再開は許可principalが判断する"),
        "AC-76-1": ("scope_out", "approval・community・開発PR通知とのtransport共有"),
        "AC-26-1": ("allowed_effects", "money"),
        "AC-47-1": ("allowed_effects", "credential"),
        "AC-63-1": ("value", "認証済みVPS Web UI read modelで状態を表示する"),
        "AC-77-1": ("scope_out", "API-onlyを製品UI要件の代替にすること"),
        "AC-44-1": ("scope_in", "WordPress content publish operation"),
        "AC-SR-13-1": ("human_judgement", "企画内容の採否は許可principalが判断する"),
    }
    critical_delta_digests = {
        "AC-16-1": "sha256:b124f212d6d5ab21198be51487e51b9e5df4d15ffbc21187d41536cc0001fe35",
        "AC-46-1": "sha256:6c86510f8a46f7eec634225dfbda6ceaea692d56543ffd809233f60bfb201a4f",
        "AC-75-1": "sha256:0f36366d6d9bee3edb612c9b08f4781313707cfe7f95ab805e65cdec1be9e58f",
        "AC-76-1": "sha256:24acad2571fc07a6eda52f7ebefd6cd09c9f091fed2375862207def242fb7476",
        "AC-26-1": "sha256:0b7b91d5c4d35e94267baf8a88318d6ca39115fd4cd303a39b5a106e7a525460",
        "AC-47-1": "sha256:38d903c7d0778db408b8df3c1dbb71e768eebd464b0f50ac87ddafacb5a58fae",
        "AC-63-1": "sha256:52f0bdd07ee95fa367a50872d9ac141e84995fa68458a7018ad08d75ddae9059",
        "AC-77-1": "sha256:fcceac0b78cda41109616aaa1258f1a0423df0868e54af31ed9849960ddc6476",
        "AC-44-1": "sha256:d9435fb76f00fcf56786d66c85bcb5baf3cb956ce0865a74df777f10ce549a59",
        "AC-SR-13-1": "sha256:06ad3f0408d239e985a23675e196d4af12b62eb67dfd07d2640c1671f26fd0a7",
    }
    if policy.get("critical_representative_delta_digests") != critical_delta_digests:
        faults.append("AC family代表oracle delta digest台帳が不一致")
    for stable_id, (field, required) in critical.items():
        values = rows.get(stable_id, {}).get("oracle_delta", {}).get(field, [])
        if required not in values:
            faults.append(f"{stable_id}: 重要AC意味境界{field}が欠落又は反転")
        if _digest(rows.get(stable_id, {}).get("oracle_delta", {})) != critical_delta_digests[stable_id]:
            faults.append(f"{stable_id}: family代表oracle deltaが追加・削除又は反転")
    migrations_digest = _digest(rows)
    if policy.get("meaning_migrations_digest") != migrations_digest:
        faults.append("旧AC全252 ID意味移送の閉集合digestが不一致")
    status = policy.get("status")
    polarities = {"normal", "reject", "boundary-recovery"}
    by_target: dict[str, set[str]] = {}
    for source in snapshot.values():
        by_target.setdefault(str(source.get("target")), set()).add(str(source.get("polarity")))
    expected_gaps = [
        {
            "target": target,
            "missing_polarities": sorted(polarities - present),
            "disposition": "pending_po_classification",
            "reason": "親要求・FN再降下後に新ACを追加するかPO承認N/Aへ分類する",
            "owner_subject_id": "CONTRACT-SEMANTIC-DESCENT-V2",
        }
        for target, present in sorted(by_target.items())
        if present != polarities
    ]
    gaps = policy.get("polarity_gap_dispositions")
    gaps_digest = _digest(gaps)
    if policy.get("polarity_gap_dispositions_digest") != gaps_digest:
        faults.append("AC target別3極性gap digestが不一致")
    if status == "pending_po_semantic_classification":
        if gaps != expected_gaps:
            faults.append("AC target別3極性gap台帳がexact一致しない")
    elif not isinstance(gaps, list):
        faults.append("AC target別3極性gapがPO分類済みでない")
    else:
        expected_gap_keys = {(row["target"], tuple(row["missing_polarities"])) for row in expected_gaps}
        actual_gap_keys = {
            (row.get("target"), tuple(row.get("missing_polarities", [])))
            for row in gaps
            if isinstance(row, dict)
        }
        if actual_gap_keys != expected_gap_keys or any(
            row.get("disposition") not in {"redescent_new_ac", "po_approved_na"}
            for row in gaps
            if isinstance(row, dict)
        ):
            faults.append("AC target別3極性gapがPO分類済みでない又はsource gapと不一致")
    approval = policy.get("classification_approval")
    if status == "pending_po_semantic_classification":
        if policy.get("cutover_blocked") is not True or approval is not None:
            faults.append("旧AC意味inventoryの未承認cutover境界が不正")
        faults.append("旧AC意味分類候補がPO未承認 remaining=0")
    elif status == "classified":
        for parent_key in (
            "legacy_requirement_meaning_inventory",
            "legacy_strategy_quality_meaning_inventory",
            "legacy_mr_meaning_inventory",
            "legacy_fn_meaning_inventory",
        ):
            parent = refinements.get(parent_key, {})
            parent_approval = parent.get("classification_approval", {})
            if (
                parent.get("status") != "classified"
                or parent.get("cutover_blocked") is not False
                or not isinstance(parent_approval, dict)
                or parent_approval.get("source_snapshot_digest") != parent.get("source_snapshot_digest")
                or parent_approval.get("meaning_migrations_digest")
                != _digest(parent.get("meaning_migrations", {}))
            ):
                faults.append(f"旧AC分類の親inventory {parent_key} が承認済みでない")
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "source_snapshot_digest": policy.get("source_snapshot_digest"),
            "meaning_migrations_digest": migrations_digest,
            "polarity_gap_dispositions_digest": gaps_digest,
        }
        if (
            policy.get("cutover_blocked") is not False
            or not isinstance(approval, dict)
            or {key: approval.get(key) for key in expected_approval} != expected_approval
            or not isinstance(approval.get("approved_at"), str)
        ):
            faults.append("旧AC全252 ID意味分類にPO receiptがない又はdigest不一致")
    else:
        faults.append("旧AC意味inventory statusが不正")
    return faults


def _legacy_tc_meaning_snapshot(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """旧TCCの全fieldを履歴snapshotとして固定する。"""
    return {
        str(item.get("id")): {
            "source_artifact": "docs/L3-system-requirements/verification/tc-contracts.json",
            **{key: item.get(key) for key in sorted(item) if key != "id"},
        }
        for item in ctx.tcc
    }


def legacy_tc_meaning_inventory_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧TC 258件を親AC意味へ束縛し、旧成功oracleの昇格を拒否する。"""
    policy = refinements.get("legacy_tc_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧TC意味inventoryがない"]
    snapshot = _legacy_tc_meaning_snapshot(ctx)
    rows = policy.get("meaning_migrations")
    expected_ids = set(snapshot)
    faults: list[str] = []
    if policy.get("stable_id_count") != 258 or policy.get("stable_id_digest") != _digest(
        sorted(expected_ids)
    ):
        faults.append("旧TC意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧TC意味inventoryのsource digestが不一致")
    restart_decision = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-008")
    if policy.get("credential_restart_decision_digest") != _digest(restart_decision):
        faults.append("旧TC意味inventoryがVPS再起動判断へ束縛されていない")
    if not isinstance(rows, dict) or set(rows) != expected_ids:
        faults.append("旧TC全258 IDの意味移送被覆がない")
        rows = rows if isinstance(rows, dict) else {}
    ac_rows = refinements.get("legacy_ac_meaning_inventory", {}).get("meaning_migrations", {})
    group_policies = {
        "notification-purpose": {
            "product_channel": "vps_ui_inbox",
            "discord_role": "community_marketing_only",
        },
        "activation-authority": {"decision": "permission_principal", "gate_role": "eligibility_only"},
        "money-authority": {"decision": "money_principal", "partition": "charge_spend_refund"},
        "credential-boundary": {
            "secret_storage": "no_repo_db_log_evidence",
            "current_restart": "external_effects_stopped",
            "unlock": "human_reauthorization_with_runtime_reinitialization",
            "credential_only_auto_unlock": "prohibited",
            "future_persistent_service": "separate_po_requirement",
        },
        "external-effect": {
            "owner_binding": "required",
            "browser": "playwright_confirmation_only",
            "route_priority": "api_mcp_first",
        },
        "vps-ui": {"surface": "authenticated_vps_web_ui", "notification": "ui_inbox"},
        "wordpress-authority": {"partition": "content_platform_security"},
        "strategy-authority": {"acceptance": "permission_principal", "draft_stc_union": "prohibited"},
        "state-recovery": {"unknown_result": "fail_close", "resume": "authorized_and_evidenced"},
        "legacy-alias": {"old_success_evidence": "not_current", "orphan_mapping": "pending_po"},
    }
    if policy.get("critical_group_policies") != group_policies:
        faults.append("TC critical group policyがtyped exact contractと不一致")
    expected_keys = {
        "source_digest",
        "parent_ac_refs",
        "parent_ac_semantic_digest",
        "source_oracle_digest",
        "kind_snapshot",
        "disposition",
        "test_oracle_delta",
        "no_direct_delta_reason",
        "phase_snapshot",
        "phase_disposition",
        "effect_owner_bindings",
        "legacy_alias_disposition",
        "resume_conditions",
        "critical_group_refs",
        "critical_group_digest",
        "critical_group_compliance",
    }
    for stable_id, row in rows.items():
        if not isinstance(row, dict) or set(row) != expected_keys:
            faults.append(f"{stable_id}: TC意味移送field閉集合が不正")
            continue
        source = snapshot[stable_id]
        if row.get("source_digest") != _digest(source):
            faults.append(f"{stable_id}: TC source digestが不一致")
        ac_refs = sorted(source.get("ac", []))
        expected_ac_rows = {ac_id: ac_rows.get(ac_id) for ac_id in ac_refs}
        if row.get("parent_ac_refs") != ac_refs or any(value is None for value in expected_ac_rows.values()):
            faults.append(f"{stable_id}: parent AC参照が不正")
        if row.get("parent_ac_semantic_digest") != _digest(expected_ac_rows):
            faults.append(f"{stable_id}: parent AC semantic digestが不一致")
        source_oracle = {
            key: value
            for key, value in source.items()
            if key not in {"source_artifact", "ac", "kind", "slice"}
        }
        if row.get("source_oracle_digest") != _digest(source_oracle):
            faults.append(f"{stable_id}: source test oracle digestが不一致")
        if row.get("kind_snapshot") != source.get("kind"):
            faults.append(f"{stable_id}: test kind snapshotが不一致")
        if row.get("disposition") != "defer_until_parent_redescent":
            faults.append(f"{stable_id}: 旧TC成功oracleをcurrentへ昇格している")
        delta = row.get("test_oracle_delta")
        if delta != {
            "principal": [],
            "scope": [],
            "preconditions": [],
            "stimulus": [],
            "observation": [],
            "expected_result": [],
            "forbidden_side_effects": [],
            "recovery": [],
            "evidence": [],
        }:
            faults.append(f"{stable_id}: 親再降下前にTC固有oracleを肯定している")
        if row.get("no_direct_delta_reason") != "candidate_parent_ac_and_group_semantics_only":
            faults.append(f"{stable_id}: TC直接deltaなし理由が不正")
        if (
            row.get("phase_snapshot") != source.get("slice")
            or row.get("phase_disposition") != "pending_po_classification"
        ):
            faults.append(f"{stable_id}: 旧TC phaseをcurrentへ昇格している")
        if row.get("effect_owner_bindings") != []:
            faults.append(f"{stable_id}: 親再降下前に旧TC effect ownerを肯定している")
        if row.get("legacy_alias_disposition") != "pending_po_mapping":
            faults.append(f"{stable_id}: 旧TC alias処置が未隔離")
        refs = {
            family
            for ac_id in ac_refs
            for family in (ac_rows.get(ac_id) or {}).get("critical_family_refs", [])
        }
        semantic = source.get("semantic_refs", {}) or {}
        source_text = json.dumps(source_oracle, ensure_ascii=False).lower()
        if any(
            marker in source_text
            for marker in (
                "spend_ledger",
                "paid",
                "charge",
                "reversal",
                "amount",
                "currency",
                "budget",
                "予算",
                "支出",
                "課金",
                "返金",
            )
        ):
            refs.add("money-authority")
        if any(
            marker in source_text
            for marker in (
                "secret",
                "credential",
                "mask",
                "token",
                "application password",
                "資格情報",
                "認証情報",
                "秘密",
            )
        ):
            refs.add("credential-boundary")
        if source.get("external_calls") != "0 回":
            refs.add("external-effect")
        if semantic.get("state_refs") or semantic.get("event_refs"):
            refs.add("state-recovery")
        refs.add("legacy-alias")
        mapping = {
            "notification-purpose-separation": "notification-purpose",
            "activation-human-authority": "activation-authority",
            "money-operation-authority": "money-authority",
            "credential-lifecycle-authority": "credential-boundary",
            "vps-ui-primary": "vps-ui",
            "wordpress-three-authorities": "wordpress-authority",
            "strategy-acceptance-authority": "strategy-authority",
        }
        refs = {mapping.get(ref, ref) for ref in refs}
        expected_refs = sorted(refs)
        expected_compliance = {
            ref: {"controls": group_policies[ref], "test_oracle_authority": "subordinate_to_critical_group"}
            for ref in expected_refs
        }
        if row.get("critical_group_refs") != expected_refs or row.get("critical_group_digest") != _digest(
            {ref: group_policies[ref] for ref in expected_refs}
        ):
            faults.append(f"{stable_id}: TC critical group継承が不一致")
        if row.get("critical_group_compliance") != expected_compliance:
            faults.append(f"{stable_id}: TC critical group complianceが不一致")
        if not isinstance(row.get("resume_conditions"), list) or not row.get("resume_conditions"):
            faults.append(f"{stable_id}: TC再開条件がない")
    migrations_digest = _digest(rows)
    if policy.get("meaning_migrations_digest") != migrations_digest:
        faults.append("旧TC全258 ID意味移送digestが不一致")
    approval = policy.get("classification_approval")
    if policy.get("status") == "pending_po_semantic_classification":
        if policy.get("cutover_blocked") is not True or approval is not None:
            faults.append("旧TC意味inventoryの未承認cutover境界が不正")
        faults.append("旧TC意味分類候補がPO未承認 remaining=0")
    elif policy.get("status") == "classified":
        ac_inventory = refinements.get("legacy_ac_meaning_inventory", {})
        ac_approval = ac_inventory.get("classification_approval", {})
        if (
            ac_inventory.get("status") != "classified"
            or ac_inventory.get("cutover_blocked") is not False
            or not isinstance(ac_approval, dict)
            or ac_approval.get("meaning_migrations_digest") != ac_inventory.get("meaning_migrations_digest")
        ):
            faults.append("旧TC分類の親AC inventoryが承認済みでない")
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "approved_revision": 1,
            "source_snapshot_digest": policy.get("source_snapshot_digest"),
            "meaning_migrations_digest": migrations_digest,
            "parent_ac_inventory_digest": _digest(ac_inventory),
        }
        if (
            policy.get("cutover_blocked") is not False
            or not isinstance(approval, dict)
            or {key: approval.get(key) for key in expected_approval} != expected_approval
            or not isinstance(approval.get("approved_at"), str)
        ):
            faults.append("旧TC全258 ID分類にPO receiptがない又は親AC digest不一致")
    else:
        faults.append("旧TC意味inventory statusが不正")
    return faults


def legacy_requirement_meaning_inventory_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧BR/REQ/FR全IDの原意味と高risk意味移送をfail-closeで固定する。"""
    policy = refinements.get("legacy_requirement_meaning_inventory")
    if not isinstance(policy, dict):
        return ["旧BR/REQ/FR意味inventoryがない"]
    snapshot = _legacy_requirement_meaning_snapshot(ctx)
    faults: list[str] = []
    expected_ids = sorted(snapshot)
    if policy.get("stable_id_count") != len(expected_ids) or policy.get("stable_id_digest") != _digest(
        expected_ids
    ):
        faults.append("旧BR/REQ/FR意味inventoryのID被覆が不正")
    if policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("旧BR/REQ/FR意味inventoryのsource digestが不一致")
    restart_decision = refinements.get("captured_po_decision_controls", {}).get("POD-20260815-008")
    if policy.get("credential_restart_decision_digest") != _digest(restart_decision):
        faults.append("旧BR/REQ/FR意味inventoryがVPS再起動判断へ束縛されていない")
    status = policy.get("status")
    migrations = policy.get("meaning_migrations", {})
    if status == "pending_po_semantic_classification":
        remaining = len(expected_ids) - len(migrations) if isinstance(migrations, dict) else len(expected_ids)
        faults.append(f"旧BR/REQ/FR意味分類候補がPO未承認 remaining={remaining}")
    elif status != "classified":
        faults.append("旧BR/REQ/FR意味inventory statusが不正")
    else:
        if not isinstance(migrations, dict) or set(migrations) != set(expected_ids):
            faults.append("旧BR/REQ/FR全139 IDの意味移送被覆がない")
        else:
            subjects = {
                str(record.get("subject_id"))
                for record in refinements.get("records", [])
                if isinstance(record, dict)
            }
            expected_keys = {
                "source_digest",
                "disposition",
                "retained_value_clauses",
                "retained_safety_clauses",
                "retained_human_judgement_clauses",
                "obsolete_or_prohibited_clauses",
                "owner_subject_ids",
                "no_retained_reason",
                "resume_conditions",
            }
            clause_keys = (
                "retained_value_clauses",
                "retained_safety_clauses",
                "retained_human_judgement_clauses",
                "obsolete_or_prohibited_clauses",
            )
            expected_dispositions: dict[str, str] = {}
            for group_key in (
                "legacy_br_disposition_groups",
                "legacy_req_disposition_groups",
                "legacy_fr_disposition_groups",
            ):
                for group in refinements.get(group_key, []):
                    if isinstance(group, dict):
                        expected_dispositions.update(
                            {
                                str(stable_id): str(disposition)
                                for stable_id, disposition in group.get("item_dispositions", {}).items()
                            }
                        )
            for stable_id, row in migrations.items():
                if not isinstance(row, dict) or set(row) != expected_keys:
                    faults.append(f"{stable_id}: 意味移送field閉集合が不正")
                    continue
                if row.get("source_digest") != _digest(snapshot[stable_id]):
                    faults.append(f"{stable_id}: source meaning digest不一致")
                disposition = row.get("disposition")
                if disposition != expected_dispositions.get(stable_id):
                    faults.append(f"{stable_id}: 既存ID別処置と意味処置が不一致")
                if any(
                    not isinstance(row.get(key), list)
                    or len(row[key]) != len(set(row[key]))
                    or any(not isinstance(value, str) or not value.strip() for value in row[key])
                    for key in clause_keys
                ):
                    faults.append(f"{stable_id}: 意味句配列が不正")
                retained: list[Any] = sum((row.get(key, []) for key in clause_keys[:3]), [])
                reason = row.get("no_retained_reason")
                if bool(retained) == bool(isinstance(reason, str) and reason.strip()):
                    faults.append(f"{stable_id}: 保持句又は保持なし理由を一意に要求")
                obsolete = row.get("obsolete_or_prohibited_clauses", [])
                if disposition == "replace" and not obsolete:
                    faults.append(f"{stable_id}: replace対象の廃止・非継承句がない")
                resume = row.get("resume_conditions")
                if (
                    not isinstance(resume, list)
                    or len(resume) != len(set(resume))
                    or any(not isinstance(value, str) or not value.strip() for value in resume)
                    or (disposition == "defer") != bool(resume)
                ):
                    faults.append(f"{stable_id}: defer処置と再開条件が不一致")
                owners = row.get("owner_subject_ids")
                if (
                    not isinstance(owners, list)
                    or not owners
                    or len(owners) != len(set(owners))
                    or not set(owners) <= subjects
                ):
                    faults.append(f"{stable_id}: 意味ownerが空・重複又は未知")
            if policy.get("meaning_migrations_digest") != _digest(migrations):
                faults.append("旧BR/REQ/FR全139 ID意味移送の閉集合digestが不一致")
            approval = policy.get("classification_approval")
            expected_approval = {
                "authority": "PO",
                "approver_principal": "po",
                "approved_revision": 1,
                "source_snapshot_digest": policy.get("source_snapshot_digest"),
                "meaning_migrations_digest": policy.get("meaning_migrations_digest"),
            }
            if (
                not isinstance(approval, dict)
                or {key: approval.get(key) for key in expected_approval} != expected_approval
                or not isinstance(approval.get("approved_at"), str)
            ):
                faults.append("旧BR/REQ/FR全139 ID意味分類にPO receiptがない又はdigest不一致")
        if policy.get("cutover_blocked") is not False:
            faults.append("旧BR/REQ/FR意味分類済みなのにcutover blockが解除されていない")
    if not isinstance(policy.get("cutover_blocked"), bool):
        faults.append("旧BR/REQ/FR意味inventoryのcutover境界が不正")

    if status == "pending_po_semantic_classification" and isinstance(migrations, dict):
        pending_expected_dispositions: dict[str, str] = {}
        for group_key in (
            "legacy_br_disposition_groups",
            "legacy_req_disposition_groups",
            "legacy_fr_disposition_groups",
        ):
            for group in refinements.get(group_key, []):
                if isinstance(group, dict):
                    pending_expected_dispositions.update(
                        {
                            str(stable_id): str(disposition)
                            for stable_id, disposition in group.get("item_dispositions", {}).items()
                        }
                    )
        expected_row_keys = {
            "source_digest",
            "disposition",
            "retained_value_clauses",
            "retained_safety_clauses",
            "retained_human_judgement_clauses",
            "obsolete_or_prohibited_clauses",
            "owner_subject_ids",
            "no_retained_reason",
            "resume_conditions",
        }
        known_subjects = {
            str(record.get("subject_id"))
            for record in refinements.get("records", [])
            if isinstance(record, dict)
        }
        if not set(migrations) <= set(expected_ids):
            faults.append("旧BR/REQ/FR部分意味移送に未知IDがある")
        for stable_id, row in migrations.items():
            if not isinstance(row, dict) or set(row) != expected_row_keys:
                faults.append(f"{stable_id}: 部分意味移送field閉集合が不正")
                continue
            if row.get("source_digest") != _digest(snapshot[stable_id]):
                faults.append(f"{stable_id}: 部分意味移送source digest不一致")
            disposition = row.get("disposition")
            if disposition != pending_expected_dispositions.get(stable_id):
                faults.append(f"{stable_id}: 部分意味移送のID別処置が不一致")
            if disposition == "replace" and not row.get("obsolete_or_prohibited_clauses"):
                faults.append(f"{stable_id}: 部分replaceの廃止・非継承句がない")
            resume = row.get("resume_conditions")
            if not isinstance(resume, list) or (disposition == "defer") != bool(resume):
                faults.append(f"{stable_id}: 部分defer処置と再開条件が不一致")
            owners = row.get("owner_subject_ids")
            if not isinstance(owners, list) or not owners or not set(owners) <= known_subjects:
                faults.append(f"{stable_id}: 部分意味ownerが空又は未知")

    expected_high_risk = {
        "BR-C4": {
            "retain": ["金銭operationごとに許可principalの人間判断を要求する"],
            "prohibit": ["包括承認又は別operationの承認を流用しない"],
            "target_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        },
        "REQ-015": {
            "retain": ["金銭operationごとの束縛承認を要求する"],
            "prohibit": ["金銭額又は対象を束縛しない承認を採用しない"],
            "target_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        },
        "BR-I4": {
            "retain": ["観測前failureについて未観測の因果解釈を生成しない"],
            "prohibit": ["後知恵で原因又は効果を捏造しない"],
            "target_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        },
        "REQ-049": {
            "retain": ["観測時点より前のfailureへ因果説明を遡及付与しない"],
            "prohibit": ["証跡のない因果関係を確定事実として扱わない"],
            "target_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        },
        "BR-I7": {
            "retain": ["証跡を保持する", "安全な再開条件を定義する", "再実行を冪等にする"],
            "prohibit": ["三要件の一部だけで復旧可能とみなさない"],
            "target_subject_ids": ["PRODUCT-STATE-AUTHORITY"],
        },
        "REQ-052": {
            "retain": ["証跡・再開条件・冪等性を一組の復旧要件として保持する"],
            "prohibit": ["ログ存在だけを復旧成立の証拠にしない"],
            "target_subject_ids": ["PRODUCT-STATE-AUTHORITY"],
        },
        "FR-13": {
            "retain": ["author principalとverifier principalを分離する", "FAIL理由と検証証跡を必須にする"],
            "prohibit": ["同一主体の自己検証だけで合格にしない"],
            "target_subject_ids": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        },
        "FR-47": {
            "retain": [
                "secretをmaskする",
                "漏洩検知時に失効・再発行する",
                "testとproductionのcredential境界を分離する",
            ],
            "prohibit": ["secretをrepo・DB・logへ保存しない"],
            "target_subject_ids": ["VPS-CREDENTIAL-SECURITY-BOUNDARY"],
        },
        "FR-74": {
            "retain": ["account lifecycleの追加・停止・廃止・差替えを許可principalの判断へ束縛する"],
            "prohibit": ["binding preflightの機械判定をaccount lifecycle判断の代替にしない"],
            "target_subject_ids": ["BUSINESS-PROFILE-AUTHORIZATION"],
        },
        "FR-75": {
            "retain": ["公開前にprofile・media・account bindingを機械検証する"],
            "prohibit": ["preflight成功をaccount追加・廃止又はauto-mode許可の人間判断に代用しない"],
            "target_subject_ids": ["BUSINESS-PROFILE-AUTHORIZATION", "AUTO-MODE-DECISION-AUTHORITY"],
        },
    }
    if policy.get("high_risk_meaning_migrations") != expected_high_risk:
        faults.append("旧BR/REQ/FRの高risk ID別意味移送が不完全")
    if isinstance(migrations, dict):
        for stable_id, required in expected_high_risk.items():
            if stable_id not in migrations:
                continue
            row = migrations.get(stable_id, {})
            if not isinstance(row, dict):
                continue
            high_risk_retained = {
                str(value)
                for key in (
                    "retained_value_clauses",
                    "retained_safety_clauses",
                    "retained_human_judgement_clauses",
                )
                for value in row.get(key, [])
            }
            prohibited = {str(value) for value in row.get("obsolete_or_prohibited_clauses", [])}
            owners = {str(value) for value in row.get("owner_subject_ids", [])}
            if (
                not set(required["retain"]) <= high_risk_retained
                or not set(required["prohibit"]) <= prohibited
                or not set(required["target_subject_ids"]) <= owners
            ):
                faults.append(f"{stable_id}: 通常意味rowが高risk保持・禁止・ownerを包含しない")
    subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    target_subjects = {
        subject for row in expected_high_risk.values() for subject in row["target_subject_ids"]
    }
    if not target_subjects <= subjects:
        faults.append("旧BR/REQ/FRの高risk意味移送先が実在refinementでない")
    return faults


def legacy_br_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧BR 41件の価値を保持し旧実現手段だけを明示置換する。"""
    groups = refinements.get("legacy_br_disposition_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧BR disposition groupがない"]
    expected_ids = {str(item.get("id")) for item in _items(ctx.brc)}
    covered = [
        stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])
    ]
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
        if not group.get("owner_subject_ids") or any(
            owner not in subjects for owner in group.get("owner_subject_ids", [])
        ):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id, disposition in dispositions.items():
            by_id[str(stable_id)] = (group, str(disposition))
    replacements = {
        "BR-C1",
        "BR-C4",
        "BR-E2",
        "BR-E3",
        "BR-F1",
        "BR-F2",
        "BR-F4",
        "BR-F5",
        "BR-G2",
        "BR-G3",
        "BR-G4",
        "BR-H1",
        "BR-H2",
        "BR-H3",
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
    source_by_media = {
        path.stem: _items(load(path))
        for path in sorted(BR_MEDIA_DIR.glob("*.json"))
        if path.name != "index.json"
    }
    expected_ids = {str(item.get("id")) for items in source_by_media.values() for item in items}
    covered = [stable_id for row in rows if isinstance(row, dict) for stable_id in row.get("stable_ids", [])]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧media BR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    source_digests = refinements.get("legacy_media_br_source_digests", {})
    expected_digests = {media_id: _digest(items) for media_id, items in source_by_media.items()}
    if source_digests != expected_digests:
        faults.append("旧media BR source semantic digestが媒体別正本と不一致")
    expected_item_digests = {
        str(item.get("id")): _digest(item) for items in source_by_media.values() for item in items
    }
    if refinements.get("legacy_media_br_item_digests") != expected_item_digests:
        faults.append("旧media BR 70 IDのsource semantic digestが個別正本と不一致")
    item_dispositions = refinements.get("legacy_media_br_item_dispositions", {})
    if not isinstance(item_dispositions, dict) or set(item_dispositions) != expected_ids:
        faults.append("旧media BR ID別処置が70件をexactly被覆しない")
    records = refinements.get("records", [])
    subjects = {str(record.get("subject_id")) for record in records if isinstance(record, dict)}
    by_media = {str(row.get("media_id")): row for row in rows if isinstance(row, dict)}
    media_ids = [str(row.get("media_id")) for row in rows if isinstance(row, dict)]
    expected_media_ids = {path.stem for path in BR_MEDIA_DIR.glob("*.json") if path.name != "index.json"}
    if set(media_ids) != expected_media_ids or len(media_ids) != len(set(media_ids)):
        faults.append("media_id集合又は一媒体一行の一意性が不正")
    migrations = refinements.get("legacy_media_br_meaning_migrations", {})
    retained_clause_projection = (
        {
            stable_id: {
                key: migration.get(key)
                for key in (
                    "retained_value_clauses",
                    "retained_safety_clauses",
                    "no_retained_reason",
                )
            }
            for stable_id, migration in migrations.items()
            if isinstance(migration, dict)
        }
        if isinstance(migrations, dict)
        else {}
    )
    if _digest(retained_clause_projection) != (
        "sha256:1d3b2905adc188373cdabf92a12870872439e95629d5c41d8166e4754028a5f5"
    ):
        faults.append("旧media BR 70 IDの保持価値・安全制約の閉集合が不一致")
    for stable_id, retained in retained_clause_projection.items():
        values = retained.get("retained_value_clauses")
        safety = retained.get("retained_safety_clauses")
        reason = retained.get("no_retained_reason")
        if not isinstance(values, list) or not isinstance(safety, list):
            faults.append(f"{stable_id}: 保持価値・安全制約が配列でない")
        elif not values and not safety and not isinstance(reason, str):
            faults.append(f"{stable_id}: 保持句が空なのに理由がない")
        elif (values or safety) and reason is not None:
            faults.append(f"{stable_id}: 保持句とno_retained_reasonが競合する")
    expected_migrations: dict[str, dict[str, Any]] = {}
    for media_id, items in source_by_media.items():
        row = by_media.get(media_id, {})
        for item in items:
            stable_id = str(item.get("id"))
            source_meaning = item.get("text")
            expected_migrations[stable_id] = {
                "source_digest": expected_item_digests[stable_id],
                "source_meaning": source_meaning,
                "disposition": item_dispositions.get(stable_id),
                "retained_meaning": (
                    "retained_value_clauses及びretained_safety_clausesに明示した意味だけを"
                    "再検証候補として保持する"
                ),
                "retained_value_clauses": retained_clause_projection.get(stable_id, {}).get(
                    "retained_value_clauses"
                ),
                "retained_safety_clauses": retained_clause_projection.get(stable_id, {}).get(
                    "retained_safety_clauses"
                ),
                "no_retained_reason": retained_clause_projection.get(stable_id, {}).get("no_retained_reason"),
                "replacement_meaning": f"{row.get('current_role')}。{row.get('route_policy')}",
                "prohibited_inheritance": [
                    "旧structure、接続経路又は自動化手段をcurrent permissionとして継承しない",
                    "source_meaningに含まれる固有provider、CLI、consumer Web UI、home directory、"
                    "SQLite、固定閾値又は旧媒体routeをcurrent要件へ自動継承しない",
                ],
                "target_subject_ids": row.get("owner_subject_ids"),
                "status": "candidate_unratified",
            }
    if refinements.get("legacy_media_br_meaning_migrations") != expected_migrations:
        faults.append("旧media BR 70 IDのsource/retained/replacement/prohibited meaning移送が不一致")
    for media_id, row in by_media.items():
        row_ids = set(row.get("stable_ids", []))
        if any(item_dispositions.get(stable_id) != row.get("disposition") for stable_id in row_ids):
            faults.append(f"{media_id}: ID別処置が媒体処置と不一致")
        if not row.get("resume_conditions"):
            faults.append(f"{media_id}: capability再開条件がない")
        if not row.get("owner_subject_ids") or any(
            owner not in subjects for owner in row.get("owner_subject_ids", [])
        ):
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
        "ds": ["単一providerを必須にせず", "token schema", "source authority", "fallback"],
        "genai": [
            "provider-neutral",
            "Codex CLI/home",
            "consumer Web UI",
            "公式API/MCP",
            "credential",
            "license",
            "evidence",
        ],
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


def provider_neutral_execution_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """API/MCP優先・Playwright確認・provider非固定を否定方向まで型検査する。"""
    policy = refinements.get("provider_neutral_execution_policy")
    expected = {
        "required_route_priority": ["official_api", "official_mcp", "approved_cli_adapter"],
        "browser_role": "playwright_attended_or_read_confirmation_only",
        "prohibited_routes": [
            "consumer_web_ui_unattended_automation",
            "personal_home_directory_as_product_evidence",
            "single_provider_mandatory_without_po_binding",
        ],
        "provider_binding": [
            "capability",
            "operation",
            "principal",
            "account",
            "scope",
            "provider_version",
            "terms_version",
        ],
        "credential_contract": ["provider_account_scoped", "runtime_injection", "no_repo_db_log"],
        "license_contract": ["input_license", "output_license", "allowed_uses", "retention"],
        "evidence_contract": [
            "request_digest",
            "response_digest",
            "provider_version",
            "route",
            "quota",
            "license",
            "principal",
        ],
        "status": "candidate_unratified",
        "design_not_started": True,
    }
    faults = [] if policy == expected else ["provider-neutral execution policyがtyped exact contractと不一致"]
    media_ids = sorted(
        str(row.get("media_id"))
        for row in refinements.get("legacy_media_br_dispositions", [])
        if isinstance(row, dict)
    )
    expected_binding_base = {
        "policy_id": "PROVIDER-NEUTRAL-EXECUTION-POLICY",
        "policy_revision": 1,
        "policy_digest": _digest(expected),
        "media_ids": media_ids,
        "refinement_subject_ids": [
            "EXTERNAL-BROWSER-AUTOMATION-ROUTE",
            "GENAI-EXECUTION-ROUTE",
            "LEGACY-MEDIA-ADMISSION-INVENTORY",
            "OFFICIAL-API-ROUTE-AUTHORITY",
        ],
    }
    bindings = refinements.get("provider_policy_bindings")
    if not isinstance(bindings, dict):
        faults.append("provider policyが全媒体候補とroute refinementへrevision/digest束縛されていない")
        return faults
    binding_base = {key: value for key, value in bindings.items() if key not in {"status", "approval"}}
    if binding_base != expected_binding_base:
        faults.append("provider policyが全媒体候補とroute refinementへrevision/digest束縛されていない")
    elif bindings.get("status") == "candidate_unratified":
        if bindings.get("approval") is not None:
            faults.append("未承認provider policy bindingにapprovalがある")
    elif bindings.get("status") == "ratified":
        approval = bindings.get("approval")
        ledger = requirement_discovery.load_discovery_ledger()
        decision = next(
            (
                row for row in ledger.get("events", [])
                if isinstance(row, dict)
                and isinstance(approval, dict)
                and row.get("event_id") == approval.get("decision_id")
            ),
            None,
        )
        expected_approval = {
            "decision_id": decision.get("event_id") if isinstance(decision, dict) else None,
            "authority": "PO",
            "approver_principal": decision.get("actor_principal") if isinstance(decision, dict) else None,
            "approved_revision": 1,
            "approved_policy_id": "provider_neutral_execution_policy",
            "approved_policy_semantic_digest": _digest(expected),
            "source_event_or_artifact_digest": _digest(decision) if isinstance(decision, dict) else None,
        }
        if (
            not isinstance(decision, dict)
            or decision.get("subject_id") != "PROVIDER-NEUTRAL-EXECUTION-POLICY"
            or decision.get("event_type") != "policy_ratification_decided"
            or decision.get("payload", {}).get("decision") != "accepted"
            or decision.get("actor_principal") != "po"
            or decision.get("payload", {}).get("approver_principal") != "po"
            or decision.get("payload", {}).get("approved_policy_id") != "provider_neutral_execution_policy"
            or decision.get("payload", {}).get("approved_revision") != 1
            or decision.get("payload", {}).get("approved_policy_semantic_digest") != _digest(expected)
            or bindings.get("approval") != expected_approval
        ):
            faults.append("ratified provider policy bindingにPO receiptがない又はdigest不一致")
    else:
        faults.append("provider policy binding statusが不正")
    return faults


def legacy_fr_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧FR 43件を現要求へ再降下・置換・延期する処置が完全か検査する。"""
    groups = refinements.get("legacy_fr_disposition_groups") if isinstance(refinements, dict) else None
    if not isinstance(groups, list):
        return ["旧FR disposition groupがない"]
    expected_ids = {str(item.get("id")) for item in _items(ctx.frc)}
    covered = [
        stable_id for group in groups if isinstance(group, dict) for stable_id in group.get("stable_ids", [])
    ]
    faults: list[str] = []
    if set(covered) != expected_ids or len(covered) != len(set(covered)):
        faults.append(f"旧FR被覆が不正 missing={sorted(expected_ids - set(covered))}")
    subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
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
        if not group.get("owner_subject_ids") or any(
            owner not in subjects for owner in group.get("owner_subject_ids", [])
        ):
            faults.append(f"{group.get('group_id')}: meaning ownerが空又は未知")
        if group.get("status") != "candidate_unratified" or group.get("design_not_started") is not True:
            faults.append(f"{group.get('group_id')}: 未承認・未設計境界が不正")
        for stable_id, disposition in dispositions.items():
            by_id[str(stable_id)] = (group, str(disposition))
    replacements = {
        "FR-11",
        "FR-16",
        "FR-23",
        "FR-26",
        "FR-41",
        "FR-42",
        "FR-43",
        "FR-44",
        "FR-46",
        "FR-47",
        "FR-52",
        "FR-55",
        "FR-62",
        "FR-63",
        "FR-71",
        "FR-72",
        "FR-74",
        "FR-75",
        "FR-76",
        "FR-77",
    }
    defers = {"FR-45", "FR-53", "FR-73"}
    for stable_id in replacements:
        if by_id.get(stable_id, ({}, ""))[1] != "replace":
            faults.append(f"{stable_id}: 旧実現手段をreplaceしていない")
    for stable_id in defers:
        if by_id.get(stable_id, ({}, ""))[1] != "defer":
            faults.append(f"{stable_id}: 後続価値確定までdeferしていない")
    marker_sets = {
        "FR-11": ["VPS製品状態"],
        "FR-16": ["安全停止", "VPS UI内inbox"],
        "FR-23": ["超後期"],
        "FR-41": ["公式API/MCP", "Playwright"],
        "FR-44": ["content/platform/security"],
        "FR-46": ["VPS UI初回activation"],
        "FR-47": ["暗号化credential"],
        "FR-52": ["provider-neutral"],
        "FR-55": ["媒体operation別authority"],
        "FR-62": ["API/MCP優先", "Playwright read確認"],
        "FR-63": ["VPS Web UI"],
        "FR-71": ["汎用DDL", "brand plan approvalの代替にせず"],
        "FR-72": ["migration/rollback"],
        "FR-74": ["profile/account lifecycle"],
        "FR-75": ["binding preflight"],
        "FR-76": ["VPS UI内inbox"],
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


def legacy_test_authority_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """未解決の旧TC IDと二重AC-SR台帳を黙示削除・採用させない。"""
    canonical_test_ids = {
        str(item.get("id"))
        for source in (ctx.tcc, ctx.stc)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    expected_refs: dict[str, set[str]] = {}
    for du in _items(ctx.duc):
        du_id = str(du.get("id", "?"))
        trace = du.get("trace")
        for ref in trace.get("tc", []) if isinstance(trace, dict) else []:
            if isinstance(ref, str) and ref.startswith("TC-") and ref not in canonical_test_ids:
                expected_refs.setdefault(ref, set()).add(du_id)

    rows = refinements.get("legacy_test_id_dispositions")
    faults: list[str] = []
    if not isinstance(rows, list):
        faults.append("旧TC ID disposition台帳がない")
    else:
        by_id = {str(row.get("legacy_test_id")): row for row in rows if isinstance(row, dict)}
        stage = refinements.get("test_id_authority_alignment_policy", {}).get(
            "classification_state", {}
        ).get("status")
        if len(by_id) != len(rows) or len(rows) != 14:
            faults.append("旧TC ID disposition immutable snapshotが14件をexactly被覆しない")
        if stage == "cutover_complete":
            if expected_refs:
                faults.append("test ID cutover完了後もlive DUに旧TC参照が残る")
        elif set(by_id) != set(expected_refs):
            faults.append("旧TC ID snapshotとlive DU参照がcutover前に不一致")
        for legacy_id, row in by_id.items():
            du_ids = set(row.get("referenced_by", []))
            row = by_id.get(legacy_id, {})
            if stage != "cutover_complete" and expected_refs.get(legacy_id) != du_ids:
                faults.append(f"{legacy_id}: referenced_by不一致")
            disposition = row.get("disposition")
            targets = row.get("candidate_target_ids")
            if disposition == "pending_po_mapping" and targets != []:
                faults.append(f"{legacy_id}: PO未決なのにcandidate targetがある")
            if disposition in {"merge", "new_test"} and (not isinstance(targets, list) or not targets):
                faults.append(f"{legacy_id}: 採用処分にtarget test IDがない")
            if disposition == "abolish" and targets != []:
                faults.append(f"{legacy_id}: 廃止処分にtarget test IDがある")
            if row.get("decision_owner_subject_id") != "TEST-ID-AUTHORITY-ALIGNMENT":
                faults.append(f"{legacy_id}: mapping判断ownerが不正")
            if row.get("status") != "legacy_revalidation_only" or row.get("design_not_started") is not True:
                faults.append(f"{legacy_id}: legacy・未設計境界が不正")

    strategy_ac = json.loads(LEGACY_STRATEGY_AC.read_text(encoding="utf-8"))
    general_ids = {
        str(item.get("id"))
        for item in _items(ctx.acc)
        if isinstance(item.get("id"), str) and re.fullmatch(r"AC-SR-[0-9]+", str(item.get("id")))
    }
    strategy_ids = {
        str(item.get("id"))
        for item in _items(strategy_ac)
        if isinstance(item.get("id"), str) and re.fullmatch(r"AC-SR-[0-9]+", str(item.get("id")))
    }
    policy = refinements.get("legacy_strategy_ac_ledger_disposition")
    if not isinstance(policy, dict):
        faults.append("AC-SR二重台帳dispositionがない")
    else:
        required_claims = {
            "どちらの旧台帳も現要求の受入正本又は実装入力とみなさない",
            "同一AC-SR IDのthenを自動unionしない",
            "draft strategy ledger又は旧confirmed ACだけでstrategy受入完了としない",
        }
        if set(policy.get("aggregate_duplicate_ids", [])) != general_ids & strategy_ids:
            faults.append("AC-SR二重ID被覆が不一致")
        if policy.get("disposition") != "dual_legacy_revalidation_only":
            faults.append("AC-SR二重台帳をlegacy限定していない")
        if policy.get("candidate_current_owner") != "new_revision_acceptance_contract_after_po_cutover":
            faults.append("AC-SR current ownerをPO cutover前に確定又は欠落している")
        if policy.get("status") != "candidate_unratified" or policy.get("design_not_started") is not True:
            faults.append("AC-SR authority候補の未承認・未設計境界が不正")
        if set(policy.get("prohibited_claims", [])) != required_claims:
            faults.append("AC-SR二重台帳の非union・非受入claim境界が不正")

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        artifacts = {
            str(item.get("artifact_id")): item for item in manifest.get("items", []) if isinstance(item, dict)
        }
        expected_paths = {
            "L3-AC-CONTRACTS": "docs/L3-system-requirements/canonical/acceptance/ac-contracts.json",
            "L3-AC-SR": "docs/L3-system-requirements/canonical/strategy/ac-sr.json",
        }
        for artifact_id, canonical_path in expected_paths.items():
            artifact = artifacts.get(artifact_id, {})
            if artifact.get("canonical_path") != canonical_path:
                faults.append(f"{artifact_id}: AC-SR legacy artifact pathが不正")
            if (
                artifact.get("implementation_input") is not False
                or artifact.get("applicability_status") != "revalidation_required"
            ):
                faults.append(f"{artifact_id}: AC-SR legacy artifactが実装入力から隔離されていない")
    return faults


def legacy_phase_fault_disposition_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧FR→FN/ACのphase逆転と包含phaseをedge単位で棚卸しする。"""
    snapshot = refinements.get("legacy_phase_fault_classifications")
    if not isinstance(snapshot, list):
        return ["phase fault classification snapshotがない"]
    expected = {
        str(row.get("fault_key")) for row in snapshot if isinstance(row, dict)
    }
    live = {fault.removesuffix(": phase mismatch") for fault in phase_alignment_faults(ctx)}
    stage = refinements.get("fr_slice_authority_alignment_policy", {}).get(
        "classification_state", {}
    ).get("status")
    faults: list[str] = []
    if stage == "cutover_complete":
        if live:
            faults.append("phase cutover完了後もlive faultが残る")
    elif live != expected:
        faults.append("phase immutable snapshotとlive fault集合がcutover前に不一致")
    rows = refinements.get("legacy_phase_fault_dispositions")
    if not isinstance(rows, list):
        return ["phase fault disposition台帳がない"]
    by_key = {str(row.get("fault_key")): row for row in rows if isinstance(row, dict)}
    if set(by_key) != expected or len(by_key) != len(rows):
        faults.append("phase fault dispositionが現行edge集合をexactly被覆しない")
    for key, row in by_key.items():
        if row.get("disposition") != "pending_po_classification":
            faults.append(f"{key}: PO未分類の安全側処遇でない")
        if row.get("decision_owner_subject_id") != "FR-SLICE-AUTHORITY-ALIGNMENT":
            faults.append(f"{key}: phase判断ownerが不正")
        if row.get("status") != "legacy_revalidation_only" or row.get("design_not_started") is not True:
            faults.append(f"{key}: legacy・未設計境界が不正")
    expected_classifications: list[dict[str, Any]] = []
    candidates = ["phase_typo", "split_responsibility", "defer_target", "redescent_test"]
    for key in sorted(expected):
        edge = re.fullmatch(r"(FR-[0-9]+)\(([^)]+)\)->((FN|AC|TCC)-[A-Z0-9-]+)\(([^)]+)\)", key)
        inclusive = re.fullmatch(r"(FR-[0-9]+): 包含phase ([^ ]+) を実装phaseに使えない", key)
        if edge:
            source_fr_id, source_phase, target_id, target_kind, target_phase = edge.groups()
        elif inclusive:
            source_fr_id, source_phase = inclusive.groups()
            target_id, target_kind, target_phase = source_fr_id, "FR", None
        else:
            faults.append(f"{key}: typed phase faultへ解析できない")
            continue
        expected_classifications.append(
            {
                "fault_key": key,
                "source_fr_id": source_fr_id,
                "target_kind": target_kind,
                "target_id": target_id,
                "source_phase": source_phase,
                "target_phase": target_phase,
                "fault_class": "pending_po_classification",
                "candidate_dispositions": candidates,
                "decision_owner_subject_id": "FR-SLICE-AUTHORITY-ALIGNMENT",
                "status": "legacy_revalidation_only",
            }
        )
    if refinements.get("legacy_phase_fault_classifications") != expected_classifications:
        faults.append("phase faultのtyped edge分類・PO未決境界が不一致")
    return faults


def fr_slice_authority_alignment_policy_faults(
    ctx: Ctx, refinements: dict[str, Any]
) -> list[str]:
    """30件の旧phase fault snapshotとPO分類/cutoverを別状態として束縛する。"""
    policy = refinements.get("fr_slice_authority_alignment_policy")
    if not isinstance(policy, dict):
        return ["FR slice authority alignment policyがない"]
    snapshot = refinements.get("legacy_phase_fault_classifications")
    dispositions = refinements.get("legacy_phase_fault_dispositions")
    if not isinstance(snapshot, list) or not isinstance(dispositions, list):
        return ["FR phase source snapshot又はpending receiptがない"]
    faults: list[str] = []
    expected_snapshot_digest = "sha256:0f3bc482ca7d821e466cc4bde6bb2434b0c092653a4f1e4e5fb621bcbe67ccbd"
    expected_disposition_digest = "sha256:1531546ec87a790453763210961aa38070a27cee3018c1e02fd101710bec5907"
    if len(snapshot) != 30 or policy.get("source_snapshot_count") != len(snapshot):
        faults.append("FR phase immutable snapshotが30 edgeをexact被覆しない")
    if _digest(snapshot) != expected_snapshot_digest or policy.get("source_snapshot_digest") != _digest(snapshot):
        faults.append("FR phase immutable snapshot digestが不一致")
    if _digest(dispositions) != expected_disposition_digest or policy.get(
        "source_disposition_receipt_digest"
    ) != _digest(dispositions):
        faults.append("FR phase pending disposition receipt digestが不一致")
    allowed = ["phase_typo", "split_responsibility", "defer_target", "redescent_test"]
    if policy.get("allowed_dispositions") != allowed:
        faults.append("FR phase disposition語彙が不正")
    if policy.get("authoritative_phase_pattern") != r"^release:[a-z0-9][a-z0-9_-]*$":
        faults.append("FR authoritative phase語彙が不正")
    by_key = {
        str(row.get("fault_key")): row for row in snapshot if isinstance(row, dict)
    }
    state = policy.get("classification_state")
    if not isinstance(state, dict):
        return faults + ["FR phase classification stateがない"]
    stage = state.get("status")
    if stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified":
            faults.append("FR phase PO未分類なのにpolicyがratified")
        if (
            state.get("selected_rows") != {}
            or state.get("classification_approval") is not None
            or state.get("candidate_artifact_binding") is not None
            or state.get("cutover_artifact_bindings") is not None
            or state.get("cutover_blocked") is not True
        ):
            faults.append("FR phase PO未分類なのに選択又はcutover解除されている")
        return faults
    if stage not in {"classified_pending_cutover", "cutover_complete"}:
        return faults + ["FR phase classification stageが不正"]
    expected_status = "ratified" if stage == "cutover_complete" else "candidate_unratified"
    if policy.get("status") != expected_status:
        faults.append("FR phase stageとpolicy statusが不一致")
    selected = state.get("selected_rows")
    if not isinstance(selected, dict) or set(selected) != set(by_key):
        return faults + ["FR phase classified rowsが30 edgeをexact被覆しない"]
    row_keys = {
        "parent_fault_digest", "source_fr_id", "target_kind", "target_id",
        "source_phase_snapshot", "target_phase_snapshot", "disposition",
        "authoritative_phase", "owner_subject_id", "rationale",
        "supersession_target_id", "resume_conditions",
    }
    known_targets = {
        str(item.get("id"))
        for source in (ctx.frc, ctx.fn, ctx.acc, ctx.tcc)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    for key, row in selected.items():
        source = by_key[key]
        if not isinstance(row, dict) or set(row) != row_keys:
            faults.append(f"{key}: FR phase classified row field閉集合が不正")
            continue
        if row.get("parent_fault_digest") != _digest(source):
            faults.append(f"{key}: parent phase fault digestがstale")
        for target, source_key in (
            ("source_fr_id", "source_fr_id"), ("target_kind", "target_kind"),
            ("target_id", "target_id"), ("source_phase_snapshot", "source_phase"),
            ("target_phase_snapshot", "target_phase"),
        ):
            if row.get(target) != source.get(source_key):
                faults.append(f"{key}: source/target phase snapshotが入替又は不一致")
        disposition = row.get("disposition")
        phase = row.get("authoritative_phase")
        supersession = row.get("supersession_target_id")
        resume = row.get("resume_conditions")
        rationale = row.get("rationale")
        if disposition not in allowed or not isinstance(rationale, str) or not rationale.strip():
            faults.append(f"{key}: disposition又はrationaleが不正")
            continue
        if row.get("owner_subject_id") != "FR-SLICE-AUTHORITY-ALIGNMENT":
            faults.append(f"{key}: phase decision ownerが不正")
        valid_phase = isinstance(phase, str) and re.fullmatch(r"release:[a-z0-9][a-z0-9_-]*", phase)
        if disposition in {"phase_typo", "redescent_test"}:
            if not valid_phase or supersession is not None or resume != []:
                faults.append(f"{key}: direct alignment field partitionが不正")
        elif disposition == "split_responsibility":
            if (
                not valid_phase
                or not isinstance(supersession, str)
                or not re.fullmatch(r"(?:FR|FN|AC|TCC)-[A-Z0-9-]+", supersession)
                or supersession not in known_targets
                or resume != []
            ):
                faults.append(f"{key}: split responsibility field partitionが不正")
        elif disposition == "defer_target":
            if (
                phase is not None
                or supersession is not None
                or not isinstance(resume, list)
                or not resume
                or not all(isinstance(value, str) and value.strip() for value in resume)
            ):
                faults.append(f"{key}: defer field partitionが不正")
        if source.get("target_kind") == "FR" and source.get("target_phase") is not None:
            faults.append(f"{key}: inclusive phase snapshot形状が不正")
    approval = state.get("classification_approval")
    selected_digest = _digest(selected)
    if (
        not isinstance(approval, dict)
        or approval.get("authority") != "PO"
        or approval.get("subject_id") != "FR-SLICE-AUTHORITY-ALIGNMENT"
        or approval.get("source_snapshot_digest") != _digest(snapshot)
        or approval.get("selected_rows_digest") != selected_digest
        or not isinstance(approval.get("approved_revision"), str)
        or not approval.get("approved_revision")
    ):
        faults.append("FR phase classification approvalがPO・snapshot・row-setへ束縛されていない")
    candidate_binding = state.get("candidate_artifact_binding")
    manifest = load(MANIFEST)
    manifest_by_id = {
        str(item.get("artifact_id")): item
        for item in manifest.get("items", [])
        if isinstance(item, dict)
    }
    candidate_item = (
        manifest_by_id.get(str(candidate_binding.get("artifact_id")))
        if isinstance(candidate_binding, dict)
        else None
    )
    candidate_path = (
        REPO_ROOT / str(candidate_item.get("canonical_path"))
        if isinstance(candidate_item, dict)
        else None
    )
    candidate_digest = (
        "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        if candidate_path is not None and candidate_path.is_file()
        else None
    )
    def _head_bound(path: Path | None) -> bool:
        if path is None or not path.is_file():
            return False
        try:
            relative = str(path.relative_to(REPO_ROOT))
        except ValueError:
            return False
        shown = git("show", f"HEAD:{relative}")
        return shown.returncode == 0 and hashlib.sha256(shown.stdout.encode()).hexdigest() == hashlib.sha256(path.read_bytes()).hexdigest()
    expected_input = stage == "cutover_complete"
    if (
        not isinstance(candidate_binding, dict)
        or set(candidate_binding) != {"artifact_id", "content_digest"}
        or candidate_binding.get("artifact_id")
        != "AUTH-DEVELOPMENT-FR-SLICE-AUTHORITY-CANDIDATE"
        or not isinstance(candidate_item, dict)
        or candidate_item.get("layer") != "00-authority"
        or candidate_item.get("artifact_type") != "fr-slice-authority-candidate"
        or candidate_item.get("authority_format") != "json"
        or candidate_item.get("authority_status") != "active"
        or candidate_item.get("implementation_input") is not expected_input
        or candidate_binding.get("content_digest") != candidate_digest
    ):
        faults.append("FR phase candidate artifact identity/digest/input境界が不正")
    else:
        try:
            candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else {}
        except (OSError, json.JSONDecodeError):
            candidate = {}
        expected_projection = {key: _digest(row) for key, row in selected.items()}
        if candidate.get("phase_alignment_row_digests") != expected_projection:
            faults.append("FR phase candidate projectionが30 classified rowと不一致")
    if stage == "classified_pending_cutover":
        if state.get("cutover_blocked") is not True or state.get("cutover_artifact_bindings") is not None:
            faults.append("FR phase classified pendingでcutoverがfail-closeでない")
    else:
        if state.get("cutover_blocked") is not False:
            faults.append("FR phase cutover completeが解除されていない")
        live = phase_alignment_faults(ctx)
        if live:
            faults.append("FR phase cutover completeでもphase faultが残る")
        bindings = state.get("cutover_artifact_bindings")
        required = {"projection_artifact_id", "projection_digest", "trace_artifact_id", "trace_digest", "manifest_digest", "baseline_digest", "target_commit", "target_tree", "same_commit", "trace_diff_count", "independent_go_artifact_id", "independent_go_digest"}
        if not isinstance(bindings, dict) or set(bindings) != required:
            faults.append("FR phase cutover artifact bindingが不完全")
        elif (
            bindings.get("same_commit") is not True
            or bindings.get("trace_diff_count") != 0
            or any(
                not isinstance(bindings.get(name), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", bindings[name])
                for name in ("projection_digest", "trace_digest", "manifest_digest", "baseline_digest", "independent_go_digest")
            )
        ):
            faults.append("FR phase projection/traceが同一commitで閉じていない")
        else:
            for id_key, digest_key in (
                ("projection_artifact_id", "projection_digest"),
                ("trace_artifact_id", "trace_digest"),
                ("independent_go_artifact_id", "independent_go_digest"),
            ):
                item = manifest_by_id.get(str(bindings.get(id_key)))
                path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
                actual = (
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                    if path is not None and path.is_file()
                    else None
                )
                if actual != bindings.get(digest_key):
                    faults.append(f"FR phase {id_key}がmanifest実artifactへ束縛されていない")
                if not _head_bound(path):
                    faults.append(f"FR phase {id_key}がHEAD blobと不一致")
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            for path, key in ((MANIFEST, "manifest_digest"), (baseline_path, "baseline_digest")):
                actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                if bindings.get(key) != actual:
                    faults.append(f"FR phase {key}が実fileと不一致")
                if not _head_bound(path):
                    faults.append(f"FR phase {key}がHEAD blobと不一致")
            if not _head_bound(candidate_path):
                faults.append("FR phase candidateがHEAD blobと不一致")
            head = git("rev-parse", "HEAD").stdout.strip()
            tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
            if bindings.get("target_commit") != head or bindings.get("target_tree") != tree:
                faults.append("FR phase cutoverが現HEAD/treeへ束縛されていない")
            review_item = manifest_by_id.get(str(bindings.get("independent_go_artifact_id")))
            review_path = REPO_ROOT / str(review_item.get("canonical_path")) if isinstance(review_item, dict) else None
            try:
                review = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
            except (OSError, json.JSONDecodeError):
                review = {}
            reviewed = review.get("reviewed_artifact_digests", {})
            if (
                review.get("separation_status") != "ci_attested"
                or review.get("verdict") != "Go"
                or not isinstance(review.get("reviewer_principal"), str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po", review.get("author_principal")}
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(reviewed, dict)
                or (candidate_binding or {}).get("content_digest") not in reviewed.values()
                or bindings.get("projection_digest") not in reviewed.values()
                or bindings.get("trace_digest") not in reviewed.values()
            ):
                faults.append("FR phase independent Goがcommit/tree/candidate/projection/traceを被覆しない")
    return faults


def legacy_media_trace_faults() -> list[str]:
    """旧BR-M↔MR隣接edgeを通常BR trace圏外のまま放置しない。"""
    br_items = [item for path in sorted(BR_MEDIA_DIR.glob("*.json")) for item in _items(load(path))]
    mr_items = [
        item
        for path in sorted(MR_DIR.glob("*.json"))
        if path.name != "index.json"
        for item in _items(load(path))
    ]
    br_ids = {str(item.get("id")) for item in br_items}
    mr_ids = {str(item.get("id")) for item in mr_items}
    br_edges = {
        (str(item.get("id")), ref)
        for item in br_items
        for ref in _trace(item, contract=False)[1]
        if ref.startswith("MR-")
    }
    mr_edges = {
        (ref, str(item.get("id")))
        for item in mr_items
        for ref in _trace(item, contract=False)[0]
        if ref.startswith("BR-M-")
    }
    faults: list[str] = []
    for item in br_items:
        source = str(item.get("id", "?"))
        if not any(ref.startswith("MR-") for ref in _trace(item, contract=False)[1]):
            faults.append(f"{source}: downstream MRがない")
    for item in mr_items:
        target = str(item.get("id", "?"))
        if not any(ref.startswith("BR-M-") for ref in _trace(item, contract=False)[0]):
            faults.append(f"{target}: upstream BR-Mがない")
    for source, target in sorted(br_edges - mr_edges):
        faults.append(f"{source}->{target}: MR upstream reverse edgeがない")
    for source, target in sorted(mr_edges - br_edges):
        faults.append(f"{source}->{target}: BR-M downstream forward edgeがない")
    for source, target in sorted(br_edges | mr_edges):
        if source not in br_ids or target not in mr_ids:
            faults.append(f"{source}->{target}: media trace IDが旧台帳に実在しない")
    if not br_edges or not mr_edges:
        faults.append("BR-M↔MR trace edge集合が空")
    return faults


def legacy_trace_fault_policy_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧trace fault集合を件数だけでなくdigest・意味種別・例外処遇へ固定する。"""
    policy = refinements.get("legacy_trace_fault_policy")
    if not isinstance(policy, dict):
        return ["legacy trace fault policyがない"]
    direct = sorted(bidirectional_trace_faults(ctx))
    layered = sorted(layered_trace_faults(ctx))
    semantic = sorted(trace_semantic_responsibility_faults(ctx))
    faults: list[str] = []
    for label, values in (("direct", direct), ("layered", layered), ("semantic", semantic)):
        if policy.get(f"{label}_fault_count") != len(values):
            faults.append(f"{label}: trace fault countが不一致")
        if policy.get(f"{label}_fault_digest") != _digest(values):
            faults.append(f"{label}: trace fault digestが不一致")
    required_rules = {
        "missing_reverse_edge": "semantic_redescent",
        "media_parent_outside_backbone": "defer_with_parent",
        "missing_stable_req_root": "defer_with_parent",
        "req_contract_reverse_missing": "semantic_redescent",
        "semantic_responsibility_mismatch": "supersede_edge",
    }
    if policy.get("classification_rules") != required_rules:
        faults.append("trace fault分類規則が不正")
    classified = {
        "missing_reverse_edge": [fault for fault in direct if "trace_up orphan BR-M-" not in fault],
        "media_parent_outside_backbone": [fault for fault in direct if "trace_up orphan BR-M-" in fault],
        "req_contract_reverse_missing": [
            fault for fault in layered if "contract upstream missing REQ" in fault
        ],
        "missing_stable_req_root": [fault for fault in layered if "stable REQ root" in fault],
        "semantic_responsibility_mismatch": semantic,
    }
    expected_partitions = {
        label: {"count": len(values), "digest": _digest(sorted(values))}
        for label, values in classified.items()
    }
    if policy.get("classification_partitions") != expected_partitions:
        faults.append("全trace faultが分類別count/digestへexactly partitionされていない")
    all_faults = direct + layered + semantic
    classified_faults = [fault for values in classified.values() for fault in values]
    classified_counter = Counter(classified_faults)
    if Counter(all_faults) != classified_counter or any(count != 1 for count in classified_counter.values()):
        faults.append("trace fault分類partitionが全faultを重複なく1回だけ被覆しない")
    owner_by_class = {
        "missing_reverse_edge": ["CONTRACT-SEMANTIC-DESCENT-V2"],
        "media_parent_outside_backbone": ["LEGACY-MEDIA-ADMISSION-INVENTORY", "CONTRACT-SEMANTIC-DESCENT-V2"],
        "req_contract_reverse_missing": ["REQ-AUTHORITY-NORMALIZATION", "CONTRACT-SEMANTIC-DESCENT-V2"],
        "missing_stable_req_root": ["REQ-AUTHORITY-NORMALIZATION", "CONTRACT-SEMANTIC-DESCENT-V2"],
        "semantic_responsibility_mismatch": ["CONTRACT-SEMANTIC-DESCENT-V2"],
    }
    scope_by_class = {
        "missing_reverse_edge": "direct",
        "media_parent_outside_backbone": "direct",
        "req_contract_reverse_missing": "layered",
        "missing_stable_req_root": "layered",
        "semantic_responsibility_mismatch": "semantic",
    }
    expected_rows = sorted(
        (
            {
                "fault": fault,
                "fault_digest": _digest(fault),
                "source_scope": scope_by_class[classification],
                "classification": classification,
                "disposition": required_rules[classification],
                "owner_subject_ids": owner_by_class[classification],
                "status": "legacy_revalidation_only",
            }
            for classification, values in classified.items()
            for fault in values
        ),
        key=lambda row: (str(row["source_scope"]), str(row["fault"])),
    )
    actual_rows = refinements.get("legacy_trace_fault_dispositions")
    if (
        not isinstance(actual_rows, list)
        or sorted(actual_rows, key=lambda row: (str(row.get("source_scope")), str(row.get("fault"))))
        != expected_rows
    ):
        faults.append("全trace faultの個別class/disposition/owner/digest台帳が不一致")
    required_exceptions = {
        "BR-A3/REQ-004→FR-71": "supersede_edge",
        "FR-21→FR-4x": "supersede_edge",
        "CMP-10→BR-31": "supersede_edge",
    }
    if policy.get("semantic_exception_dispositions") != required_exceptions:
        faults.append("意味責務が誤ったtrace 3件の処遇が不正")
    subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    owners = policy.get("decision_owner_subject_ids", [])
    if not isinstance(owners, list) or not owners or not set(owners) <= subjects:
        faults.append("trace fault meaning ownerが空又は未知")
    if policy.get("status") != "legacy_revalidation_only" or policy.get("design_not_started") is not True:
        faults.append("trace fault policyのlegacy・未設計境界が不正")
    return faults


def legacy_media_trace_fault_policy_faults(refinements: dict[str, Any]) -> list[str]:
    """旧BR-M↔MRの片方向edgeをdigest固定し、黙示修復でなく再降下へ送る。"""
    policy = refinements.get("legacy_media_trace_fault_policy")
    if not isinstance(policy, dict):
        return ["legacy media trace fault policyがない"]
    current = sorted(legacy_media_trace_faults())
    faults: list[str] = []
    if policy.get("fault_count") != len(current):
        faults.append("media trace fault countが不一致")
    if policy.get("fault_digest") != _digest(current):
        faults.append("media trace fault digestが不一致")
    expected_rules = {
        "missing_mr_reverse_edge": "semantic_redescent",
        "missing_brm_forward_edge": "semantic_redescent",
        "orphan_brm": "semantic_redescent",
        "orphan_mr": "semantic_redescent",
        "unknown_media_trace_id": "supersede_edge",
        "empty_media_trace": "semantic_redescent",
    }
    if policy.get("classification_rules") != expected_rules:
        faults.append("media trace fault分類が不正")
    classified = {
        "missing_mr_reverse_edge": [fault for fault in current if "MR upstream reverse edgeがない" in fault],
        "missing_brm_forward_edge": [
            fault for fault in current if "BR-M downstream forward edgeがない" in fault
        ],
        "orphan_brm": [fault for fault in current if fault.endswith(": downstream MRがない")],
        "orphan_mr": [fault for fault in current if fault.endswith(": upstream BR-Mがない")],
        "unknown_media_trace_id": [
            fault for fault in current if "media trace IDが旧台帳に実在しない" in fault
        ],
        "empty_media_trace": [fault for fault in current if fault == "BR-M↔MR trace edge集合が空"],
    }
    expected_partitions = {
        label: {"count": len(values), "digest": _digest(sorted(values))}
        for label, values in classified.items()
    }
    if policy.get("classification_partitions") != expected_partitions:
        faults.append("media trace faultが分類別count/digestへexactly partitionされていない")
    classified_faults = [fault for values in classified.values() for fault in values]
    classified_counter = Counter(classified_faults)
    if Counter(current) != classified_counter or any(count != 1 for count in classified_counter.values()):
        faults.append("media trace fault分類partitionが全faultを重複なく1回だけ被覆しない")
    owners_by_source = {
        str(stable_id): list(row.get("owner_subject_ids", []))
        for row in refinements.get("legacy_media_br_dispositions", [])
        if isinstance(row, dict)
        for stable_id in row.get("stable_ids", [])
    }
    expected_rows: list[dict[str, Any]] = []
    for fault in current:
        match = re.fullmatch(
            r"(BR-M-[A-Z0-9-]+)->(MR-[A-Z0-9-]+): "
            r"(MR upstream reverse|BR-M downstream forward) edgeがない",
            fault,
        )
        if match is None:
            continue
        source_id, target_id, direction = match.groups()
        expected_rows.append(
            {
                "fault": fault,
                "fault_digest": _digest(fault),
                "source_brm_id": source_id,
                "target_mr_id": target_id,
                "classification": (
                    "missing_mr_reverse_edge" if direction.startswith("MR ") else "missing_brm_forward_edge"
                ),
                "disposition": "semantic_redescent",
                "owner_subject_ids": owners_by_source.get(source_id, []),
                "status": "legacy_revalidation_only",
            }
        )
    if refinements.get("legacy_media_trace_fault_dispositions") != expected_rows:
        faults.append("media trace faultの個別edge/class/disposition/owner/digest台帳が不一致")
    subjects = {
        str(record.get("subject_id")) for record in refinements.get("records", []) if isinstance(record, dict)
    }
    owners = policy.get("decision_owner_subject_ids", [])
    if not isinstance(owners, list) or not owners or not set(owners) <= subjects:
        faults.append("media trace fault ownerが空又は未知")
    if policy.get("status") != "legacy_revalidation_only" or policy.get("design_not_started") is not True:
        faults.append("media trace faultのlegacy・未設計境界が不正")
    return faults


def legacy_test_authority_cutover_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """棚卸し済みでも未決・抽象ownerのままcurrent authorityへ昇格させない。"""
    stage = refinements.get("test_id_authority_alignment_policy", {}).get(
        "classification_state", {}
    ).get("status")
    if stage == "cutover_complete":
        return test_id_authority_alignment_policy_faults(ctx, refinements)
    faults = legacy_test_authority_disposition_faults(ctx, refinements)
    rows = refinements.get("legacy_test_id_dispositions", [])
    canonical_test_ids = {
        str(item.get("id"))
        for source in (ctx.tcc, ctx.stc)
        for item in _items(source)
        if isinstance(item.get("id"), str)
    }
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            legacy_id = str(row.get("legacy_test_id", "?"))
            disposition = row.get("disposition")
            targets = row.get("candidate_target_ids", [])
            if disposition == "pending_po_mapping":
                faults.append(f"{legacy_id}: mappingがPO未決")
            elif disposition in {"merge", "new_test"} and (
                not isinstance(targets, list) or not targets or not set(targets) <= canonical_test_ids
            ):
                faults.append(f"{legacy_id}: cutover先test IDが現行正本にない")

    records = refinements.get("records", [])
    decision = (
        next(
            (
                record
                for record in records
                if isinstance(record, dict) and record.get("subject_id") == "TEST-ID-AUTHORITY-ALIGNMENT"
            ),
            None,
        )
        if isinstance(records, list)
        else None
    )
    if (
        not isinstance(decision, dict)
        or decision.get("lifecycle_status") != "frozen"
        or not isinstance(decision.get("approval"), dict)
    ):
        faults.append("TEST-ID-AUTHORITY-ALIGNMENTがPO receipt付きfrozenでない")

    policy = refinements.get("legacy_strategy_ac_ledger_disposition", {})
    owner = policy.get("candidate_current_owner") if isinstance(policy, dict) else None
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifact_ids = {
        str(item.get("artifact_id")) for item in manifest.get("items", []) if isinstance(item, dict)
    }
    if not isinstance(owner, str) or owner not in artifact_ids:
        faults.append("AC-SR current ownerが実在artifact IDへ凍結されていない")
    elif owner in {"L3-AC-CONTRACTS", "L3-AC-SR"}:
        faults.append("旧AC-SR二重台帳をcurrent ownerへ再利用している")
    return faults


def test_id_authority_alignment_policy_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧TC mappingとstrategy test ownerを別trackでPO分類/cutoverへ束縛する。"""
    policy = refinements.get("test_id_authority_alignment_policy")
    if not isinstance(policy, dict):
        return ["test ID authority alignment policyがない"]
    legacy_rows = refinements.get("legacy_test_id_dispositions")
    strategy = refinements.get("legacy_strategy_ac_ledger_disposition")
    tc_inventory = refinements.get("legacy_tc_meaning_inventory")
    if not isinstance(legacy_rows, list) or not isinstance(strategy, dict) or not isinstance(tc_inventory, dict):
        return ["test ID authority source snapshotがない"]
    tc_rows = tc_inventory.get("meaning_migrations")
    if not isinstance(tc_rows, dict):
        return ["TC258 meaning inventory rowsがない"]
    faults: list[str] = []
    if len(legacy_rows) != 14 or policy.get("legacy_tc_snapshot_count") != 14:
        faults.append("旧TC snapshotが14 IDをexact被覆しない")
    if _digest(legacy_rows) != "sha256:23c646bb490b5e28485125de66141366369ce5d7029865114d9da71f2649df23" or policy.get("legacy_tc_snapshot_digest") != _digest(legacy_rows):
        faults.append("旧TC immutable snapshot digestが不一致")
    if _digest(strategy) != "sha256:41c2574eb3231e18f213bdaa79063682ed9b6266fbab31ab679dfe3dc54963c9" or policy.get("strategy_ledger_snapshot_digest") != _digest(strategy):
        faults.append("strategy test ledger snapshot digestが不一致")
    if _digest(tc_rows) != "sha256:dd4b1893ae7bb23dcc5f9b831ac1faea9a9d82976afbc66e9f93c82904adc78b" or policy.get("tc_inventory_rows_digest") != _digest(tc_rows):
        faults.append("TC258 inventory rows digestが不一致")
    allowed = ["merge", "new_test", "abolish", "defer"]
    if policy.get("allowed_mapping_dispositions") != allowed:
        faults.append("test ID mapping disposition語彙が不正")
    state = policy.get("classification_state")
    if not isinstance(state, dict):
        return faults + ["test ID classification stateがない"]
    stage = state.get("status")
    if stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified":
            faults.append("test ID未分類なのにpolicyがratified")
        if (
            state.get("legacy_tc_mapping_rows") != {}
            or state.get("strategy_test_owner") is not None
            or state.get("classification_approval") is not None
            or state.get("candidate_artifact_binding") is not None
            or state.get("cutover_artifact_bindings") is not None
            or state.get("cutover_blocked") is not True
        ):
            faults.append("test ID未分類なのに選択又はcutover解除されている")
        return faults
    if stage not in {"classified_pending_cutover", "cutover_complete"}:
        return faults + ["test ID classification stageが不正"]
    expected_status = "ratified" if stage == "cutover_complete" else "candidate_unratified"
    if policy.get("status") != expected_status:
        faults.append("test ID stageとpolicy statusが不一致")
    source_by_id = {str(row.get("legacy_test_id")): row for row in legacy_rows if isinstance(row, dict)}
    mapping = state.get("legacy_tc_mapping_rows")
    if not isinstance(mapping, dict) or set(mapping) != set(source_by_id):
        return faults + ["test ID classified mappingが14 IDをexact被覆しない"]
    row_fields = {"parent_row_digest", "referenced_by", "disposition", "target_test_ids", "target_oracle_semantic_digests", "merge_group_id", "collision_source_set_digest", "owner_subject_id", "rationale", "resume_conditions", "du_trace_impact"}
    for legacy_id, row in mapping.items():
        source = source_by_id[legacy_id]
        if not isinstance(row, dict) or set(row) != row_fields:
            faults.append(f"{legacy_id}: mapping row field閉集合が不正")
            continue
        if row.get("parent_row_digest") != _digest(source) or row.get("referenced_by") != source.get("referenced_by"):
            faults.append(f"{legacy_id}: source snapshot bindingが不一致")
        disposition = row.get("disposition")
        targets = row.get("target_test_ids")
        target_digests = row.get("target_oracle_semantic_digests")
        resume = row.get("resume_conditions")
        merge_group = row.get("merge_group_id")
        collision_digest = row.get("collision_source_set_digest")
        if row.get("owner_subject_id") != "TEST-ID-AUTHORITY-ALIGNMENT" or not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            faults.append(f"{legacy_id}: owner又はrationaleが不正")
        if not isinstance(row.get("du_trace_impact"), list) or not row["du_trace_impact"] or not all(isinstance(value, str) and value.strip() for value in row["du_trace_impact"]):
            faults.append(f"{legacy_id}: DU trace impactが不正")
        if disposition in {"merge", "new_test"}:
            if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or not set(targets) <= set(tc_rows):
                faults.append(f"{legacy_id}: target TCCが現TC inventoryに一意に閉じない")
            expected_digests = {target: _digest(tc_rows[target]) for target in targets if target in tc_rows} if isinstance(targets, list) else {}
            if target_digests != expected_digests or resume != []:
                faults.append(f"{legacy_id}: target oracle digest又はresume partitionが不正")
            if disposition == "merge":
                if not isinstance(merge_group, str) or not re.fullmatch(r"TMG-[A-Z0-9-]+", merge_group) or not isinstance(collision_digest, str):
                    faults.append(f"{legacy_id}: merge group/collision receiptがない")
            elif merge_group is not None or collision_digest is not None:
                faults.append(f"{legacy_id}: new_testにmerge groupが混入")
        elif disposition == "abolish":
            if targets != [] or target_digests != {} or resume != [] or merge_group is not None or collision_digest is not None:
                faults.append(f"{legacy_id}: abolish field partitionが不正")
        elif disposition == "defer":
            if targets != [] or target_digests != {} or merge_group is not None or collision_digest is not None or not isinstance(resume, list) or not resume or not all(isinstance(value, str) and value.strip() for value in resume):
                faults.append(f"{legacy_id}: defer field partitionが不正")
        else:
            faults.append(f"{legacy_id}: mapping dispositionが不正")
    owner = state.get("strategy_test_owner")
    target_sources: dict[str, list[str]] = {}
    for legacy_id, row in mapping.items():
        if isinstance(row, dict):
            for target in row.get("target_test_ids", []) if isinstance(row.get("target_test_ids"), list) else []:
                target_sources.setdefault(str(target), []).append(legacy_id)
    for target, sources in target_sources.items():
        rows_for_target = [mapping[source] for source in sources]
        if len(sources) > 1:
            if any(row.get("disposition") == "new_test" for row in rows_for_target):
                faults.append(f"{target}: new_test targetが複数旧IDで衝突")
            groups = {row.get("merge_group_id") for row in rows_for_target}
            expected_collision = _digest(sorted(sources))
            if len(groups) != 1 or None in groups or any(row.get("collision_source_set_digest") != expected_collision for row in rows_for_target):
                faults.append(f"{target}: many-to-one merge group/PO collision receiptが不一致")
        elif rows_for_target[0].get("disposition") == "merge" and rows_for_target[0].get("collision_source_set_digest") != _digest(sources):
            faults.append(f"{target}: merge source-set digestが不一致")
    owner_fields = {"parent_strategy_snapshot_digest", "duplicate_ids", "current_authority_artifact_id", "current_authority_content_digest", "duplicate_oracle_projection_digest", "general_legacy_artifact_id", "strategy_legacy_artifact_id", "prohibited_union_claims", "supersession_scope"}
    manifest = load(MANIFEST)
    manifest_by_id = {str(item.get("artifact_id")): item for item in manifest.get("items", []) if isinstance(item, dict)}
    if not isinstance(owner, dict) or set(owner) != owner_fields:
        faults.append("strategy test owner field閉集合が不正")
    else:
        current_id = owner.get("current_authority_artifact_id")
        current_item = manifest_by_id.get(str(current_id))
        if owner.get("parent_strategy_snapshot_digest") != _digest(strategy) or owner.get("duplicate_ids") != strategy.get("aggregate_duplicate_ids"):
            faults.append("strategy test ownerが旧二重ledger snapshotと不一致")
        current_path = REPO_ROOT / str(current_item.get("canonical_path")) if isinstance(current_item, dict) else None
        current_digest = "sha256:" + hashlib.sha256(current_path.read_bytes()).hexdigest() if current_path is not None and current_path.is_file() else None
        if (
            owner.get("general_legacy_artifact_id") != "L3-AC-CONTRACTS"
            or owner.get("strategy_legacy_artifact_id") != "L3-AC-SR"
            or current_id in {"L3-AC-CONTRACTS", "L3-AC-SR"}
            or not isinstance(current_item, dict)
            or current_item.get("layer") != "L3-system-requirements"
            or current_item.get("artifact_type") != "strategy-test-authority"
            or current_item.get("authority_format") != "json"
            or current_item.get("authority_status") != "active"
            or current_item.get("implementation_input") is not (stage == "cutover_complete")
            or owner.get("current_authority_content_digest") != current_digest
        ):
            faults.append("strategy current authorityが単一の新実在artifactでない")
        else:
            try:
                current_data = json.loads(current_path.read_text(encoding="utf-8")) if current_path else {}
            except (OSError, json.JSONDecodeError):
                current_data = {}
            projection = current_data.get("ac_sr_oracle_row_digests")
            oracle_rows = current_data.get("ac_sr_oracles")
            duplicate_ids = set(strategy.get("aggregate_duplicate_ids", []))
            general_by_id = {
                str(item.get("id")): item
                for item in _items(ctx.acc)
                if str(item.get("id")) in duplicate_ids
            }
            strategy_source = json.loads(LEGACY_STRATEGY_AC.read_text(encoding="utf-8"))
            strategy_by_id = {
                str(item.get("id")): item
                for item in _items(strategy_source)
                if str(item.get("id")) in duplicate_ids
            }
            expected_projection: dict[str, str] = {}
            if not isinstance(oracle_rows, dict) or set(oracle_rows) != duplicate_ids:
                faults.append("strategy current authorityがduplicate AC-SR全件をexact被覆しない")
            else:
                for stable_id, selected_oracle in oracle_rows.items():
                    if not isinstance(selected_oracle, dict) or set(selected_oracle) != {"source_disposition", "oracle"}:
                        faults.append(f"{stable_id}: strategy selected oracle field閉集合が不正")
                        continue
                    source_disposition = selected_oracle.get("source_disposition")
                    oracle = selected_oracle.get("oracle")
                    if source_disposition == "general_selected" and oracle != general_by_id.get(stable_id):
                        faults.append(f"{stable_id}: general oracle selectionがsourceと不一致")
                    elif source_disposition == "strategy_selected" and oracle != strategy_by_id.get(stable_id):
                        faults.append(f"{stable_id}: strategy oracle selectionがsourceと不一致")
                    elif source_disposition == "new_oracle":
                        required_oracle_fields = {
                            "target_requirement_ids", "polarity", "given", "when", "then",
                            "failure_oracle", "recovery_oracle", "evidence_dimensions",
                            "phase_disposition", "owner_subject_id", "resume_conditions",
                        }
                        known_sr_ids = {
                            str(item.get("id"))
                            for item in _items(ctx.src)
                            if isinstance(item.get("id"), str)
                        }
                        known_subjects = {
                            str(record.get("subject_id"))
                            for record in refinements.get("records", [])
                            if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
                        }
                        evidence_vocabulary = {
                            "subject_digest", "correlation", "source", "actor", "effect",
                            "result", "failure", "recovery",
                        }
                        if (
                            not isinstance(oracle, dict)
                            or set(oracle) != required_oracle_fields
                            or not isinstance(oracle.get("target_requirement_ids"), list)
                            or not oracle["target_requirement_ids"]
                            or not all(isinstance(value, str) and value in known_sr_ids for value in oracle["target_requirement_ids"])
                            or oracle.get("polarity") not in {"normal", "reject", "boundary"}
                            or any(not isinstance(oracle.get(field), str) or not oracle[field].strip() for field in ("given", "when", "then", "failure_oracle", "recovery_oracle"))
                            or not isinstance(oracle.get("evidence_dimensions"), list)
                            or not oracle["evidence_dimensions"]
                            or not all(isinstance(value, str) and value in evidence_vocabulary for value in oracle["evidence_dimensions"])
                            or not {"result", "failure", "recovery"} <= set(oracle["evidence_dimensions"])
                            or oracle.get("phase_disposition") not in {"redescent", "defer"}
                            or oracle.get("owner_subject_id") not in known_subjects
                            or not isinstance(oracle.get("resume_conditions"), list)
                            or (
                                oracle.get("phase_disposition") == "redescent"
                                and oracle.get("resume_conditions") != []
                            )
                            or (
                                oracle.get("phase_disposition") == "defer"
                                and (
                                    not oracle["resume_conditions"]
                                    or not all(isinstance(value, str) and value.strip() for value in oracle["resume_conditions"])
                                )
                            )
                        ):
                            faults.append(f"{stable_id}: new strategy oracleがtyped polarity/failure/recovery/evidence/phaseを満たさない")
                    elif source_disposition not in {"general_selected", "strategy_selected", "new_oracle"}:
                        faults.append(f"{stable_id}: strategy oracle source dispositionが不正")
                    expected_projection[stable_id] = _digest(selected_oracle)
            if projection != expected_projection or owner.get("duplicate_oracle_projection_digest") != _digest(expected_projection):
                faults.append("strategy current authorityがduplicate AC-SR oracle projectionへ束縛されていない")
        if set(owner.get("prohibited_union_claims", [])) != set(strategy.get("prohibited_claims", [])) or not isinstance(owner.get("supersession_scope"), list) or not owner["supersession_scope"]:
            faults.append("strategy test non-union/supersession境界が不正")
        for legacy_artifact in ("L3-AC-CONTRACTS", "L3-AC-SR"):
            item = manifest_by_id.get(legacy_artifact, {})
            if item.get("implementation_input") is not False:
                faults.append(f"{legacy_artifact}: strategy旧台帳が実装入力から隔離されていない")
    mapping_digest = _digest(mapping)
    owner_digest = _digest(owner)
    approval = state.get("classification_approval")
    if (
        not isinstance(approval, dict)
        or approval.get("authority") != "PO"
        or approval.get("subject_id") != "TEST-ID-AUTHORITY-ALIGNMENT"
        or approval.get("legacy_snapshot_digest") != _digest(legacy_rows)
        or approval.get("strategy_snapshot_digest") != _digest(strategy)
        or approval.get("mapping_rows_digest") != mapping_digest
        or approval.get("strategy_owner_digest") != owner_digest
    ):
        faults.append("test ID classification approvalがPO・2 snapshot・選択結果へ束縛されていない")
    candidate = state.get("candidate_artifact_binding")
    candidate_item = manifest_by_id.get(str(candidate.get("artifact_id"))) if isinstance(candidate, dict) else None
    candidate_path = REPO_ROOT / str(candidate_item.get("canonical_path")) if isinstance(candidate_item, dict) else None
    actual_candidate_digest = "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest() if candidate_path is not None and candidate_path.is_file() else None
    if (
        not isinstance(candidate, dict)
        or set(candidate) != {"artifact_id", "content_digest"}
        or candidate.get("artifact_id") != "AUTH-DEVELOPMENT-TEST-ID-AUTHORITY-CANDIDATE"
        or not isinstance(candidate_item, dict)
        or candidate_item.get("layer") != "00-authority"
        or candidate_item.get("artifact_type") != "test-id-authority-candidate"
        or candidate_item.get("authority_format") != "json"
        or candidate_item.get("authority_status") != "active"
        or candidate_item.get("implementation_input") is not (stage == "cutover_complete")
        or candidate.get("content_digest") != actual_candidate_digest
    ):
        faults.append("test ID candidate artifact identity/digest/input境界が不正")
    else:
        try:
            candidate_data = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else {}
        except (OSError, json.JSONDecodeError):
            candidate_data = {}
        if candidate_data.get("legacy_tc_mapping_row_digests") != {key: _digest(value) for key, value in mapping.items()} or candidate_data.get("strategy_test_owner_digest") != owner_digest:
            faults.append("test ID candidate projectionがmapping/strategy ownerと不一致")
    if stage == "classified_pending_cutover":
        if state.get("cutover_blocked") is not True or state.get("cutover_artifact_bindings") is not None:
            faults.append("test ID classified pendingがfail-closeでない")
    else:
        if state.get("cutover_blocked") is not False:
            faults.append("test ID cutover completeが解除されていない")
        canonical_test_ids = {
            str(item.get("id"))
            for source in (ctx.tcc, ctx.stc)
            for item in _items(source)
            if isinstance(item.get("id"), str)
        }
        live_legacy_refs = {
            ref
            for du in _items(ctx.duc)
            for ref in (du.get("trace", {}).get("tc", []) if isinstance(du.get("trace"), dict) else [])
            if isinstance(ref, str) and ref.startswith("TC-") and ref not in canonical_test_ids
        }
        if live_legacy_refs:
            faults.append("test ID cutover completeでもlive DUに旧TC参照が残る")
        bindings = state.get("cutover_artifact_bindings")
        required = {"du_trace_artifact_id", "du_trace_digest", "test_authority_artifact_id", "test_authority_digest", "manifest_digest", "baseline_digest", "target_commit", "target_tree", "same_commit", "trace_diff_count", "independent_go_artifact_id", "independent_go_digest"}
        if not isinstance(bindings, dict) or set(bindings) != required:
            faults.append("test ID cutover artifact bindingが不完全")
        elif (
            bindings.get("same_commit") is not True
            or bindings.get("trace_diff_count") != 0
            or any(
                not isinstance(bindings.get(name), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", bindings[name])
                for name in ("du_trace_digest", "test_authority_digest", "manifest_digest", "baseline_digest", "independent_go_digest")
            )
        ):
            faults.append("test ID cutover trace/commit境界が不正")
        else:
            artifact_paths: dict[str, Path] = {}
            for id_key, digest_key in (
                ("du_trace_artifact_id", "du_trace_digest"),
                ("test_authority_artifact_id", "test_authority_digest"),
                ("independent_go_artifact_id", "independent_go_digest"),
            ):
                bound_manifest_item = manifest_by_id.get(str(bindings.get(id_key)))
                bound_artifact_path = (
                    REPO_ROOT / str(bound_manifest_item.get("canonical_path"))
                    if isinstance(bound_manifest_item, dict)
                    else None
                )
                if bound_artifact_path is not None:
                    artifact_paths[id_key] = bound_artifact_path
                actual = (
                    "sha256:" + hashlib.sha256(bound_artifact_path.read_bytes()).hexdigest()
                    if bound_artifact_path is not None and bound_artifact_path.is_file()
                    else None
                )
                if actual != bindings.get(digest_key):
                    faults.append(f"test ID {id_key}がmanifest実artifactへ束縛されていない")
            trace_path = artifact_paths.get("du_trace_artifact_id")
            try:
                trace_data = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path else {}
            except (OSError, json.JSONDecodeError):
                trace_data = {}
            expected_du_projection = {
                str(du.get("id")): sorted(
                    str(ref)
                    for ref in (du.get("trace", {}).get("tc", []) if isinstance(du.get("trace"), dict) else [])
                )
                for du in _items(ctx.duc)
            }
            expected_mapping_resolution = {
                legacy_id: {
                    "disposition": row.get("disposition"),
                    "target_test_ids": row.get("target_test_ids"),
                    "referenced_by": row.get("referenced_by"),
                    "du_trace_impact": row.get("du_trace_impact"),
                }
                for legacy_id, row in mapping.items()
            }
            if (
                not isinstance(trace_data, dict)
                or set(trace_data) != {"du_tc_projection", "legacy_mapping_resolution"}
                or trace_data.get("du_tc_projection") != expected_du_projection
                or trace_data.get("legacy_mapping_resolution") != expected_mapping_resolution
            ):
                faults.append("test ID DU trace artifactがlive DU projectionと14 mapping結果に不一致")
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            for path, key in ((MANIFEST, "manifest_digest"), (baseline_path, "baseline_digest")):
                actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                if actual != bindings.get(key):
                    faults.append(f"test ID {key}が実fileと不一致")
            head = git("rev-parse", "HEAD").stdout.strip()
            tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
            if bindings.get("target_commit") != head or bindings.get("target_tree") != tree:
                faults.append("test ID cutoverが現HEAD/treeへ束縛されていない")
            paths_to_bind: list[Path | None] = [
                candidate_path,
                MANIFEST,
                baseline_path,
                *artifact_paths.values(),
            ]
            for bound_file in paths_to_bind:
                if bound_file is None or not bound_file.is_file():
                    continue
                try:
                    relative = str(bound_file.relative_to(REPO_ROOT))
                except ValueError:
                    faults.append("test ID cutover artifactがrepo外")
                    continue
                shown = git("show", f"HEAD:{relative}")
                if shown.returncode != 0 or hashlib.sha256(shown.stdout.encode()).hexdigest() != hashlib.sha256(bound_file.read_bytes()).hexdigest():
                    faults.append(f"test ID {relative}がHEAD blobと不一致")
            if bindings.get("test_authority_artifact_id") != (owner or {}).get("current_authority_artifact_id") or bindings.get("test_authority_digest") != (owner or {}).get("current_authority_content_digest"):
                faults.append("test ID cutover test authorityがclassified strategy ownerと不一致")
            review_path = artifact_paths.get("independent_go_artifact_id")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
            except (OSError, json.JSONDecodeError):
                review = {}
            reviewed = review.get("reviewed_artifact_digests", {})
            if (
                review.get("separation_status") != "ci_attested"
                or review.get("verdict") != "Go"
                or not isinstance(review.get("reviewer_principal"), str)
                or not review.get("reviewer_principal")
                or review.get("reviewer_principal") in {"po", review.get("author_principal")}
                or review.get("target_commit") != head
                or review.get("target_tree") != tree
                or not isinstance(reviewed, dict)
                or (candidate or {}).get("content_digest") not in reviewed.values()
                or bindings.get("du_trace_digest") not in reviewed.values()
                or bindings.get("test_authority_digest") not in reviewed.values()
            ):
                faults.append("test ID independent Goがcommit/tree/candidate/trace/authorityを被覆しない")
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
        "new_revision_single_json_authority",
        "rewrite_legacy_ids_in_place",
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
    policy = json.loads(AUTHORITY_POLICY.read_text(encoding="utf-8"))
    expected_status = {
        "OBJ-01": "incomplete",
        "OBJ-02": "incomplete",
        "OBJ-03": "incomplete",
        "OBJ-04": "incomplete",
        "OBJ-05": "blocked_by_po",
    }
    for objective_id in expected_status:
        row = by_id.get(objective_id, {})
        actual_status = row.get("status")
        if not row.get("evidence"):
            faults.append(f"{objective_id}: evidenceがない")
        if actual_status == "proven" and row.get("remaining_condition") is not None:
            faults.append(f"{objective_id}: provenなのに残条件がある")
        if actual_status != "proven" and not row.get("remaining_condition"):
            faults.append(f"{objective_id}: 未完なのに残条件がない")
    implementation_authorized = policy.get("implementation_authorized")
    baseline_status = policy.get("requirements_baseline_status")
    if type(implementation_authorized) is not bool:
        faults.append("implementation_authorizedがboolでない")
    elif baseline_status == "revising" and implementation_authorized is not False:
        faults.append("implementation_authorized=falseでない")
    records = refinements.get("records", [])
    frozen_subjects = (
        {
            str(record.get("subject_id"))
            for record in records
            if isinstance(record, dict)
            and record.get("lifecycle_status") == "frozen"
            and isinstance(record.get("approval"), dict)
        }
        if isinstance(records, list)
        else set()
    )
    ui_subjects = {
        "VPS-UI-PRIMARY-HUMAN-INTERFACE",
        "VPS-UI-INBOX-LIFECYCLE",
        "VPS-UI-AUTHENTICATION-SESSION",
        "VPS-UI-QUALITY-ATTRIBUTES",
        "PRODUCT-STATE-AUTHORITY",
        "FR-16-NOTIFICATION-BOUNDARY",
        "DISCORD-NOTIFICATION-REJECTION-BOUNDARY",
    }
    readiness = {
        "OBJ-01": not (
            # OBJ-01 is only proven after every inventory named by the
            # objective has passed its own disposition/authority check.  The
            # high-level trace gates below are not a substitute for these
            # per-inventory checks: otherwise a future malformed inventory
            # could be followed by digest updates and still allow the
            # objective row to claim ``proven``.
            l0_clause_disposition_faults(refinements)
            + critical_responsibility_disposition_faults(refinements)
            + legacy_br_disposition_faults(ctx, refinements)
            + legacy_media_trace_faults()
            + legacy_media_br_disposition_faults(refinements)
            + legacy_requirement_meaning_inventory_faults(ctx, refinements)
            + req_authority_normalization_policy_faults(ctx, refinements)
            + legacy_strategy_quality_meaning_inventory_faults(ctx, refinements)
            + legacy_nfr_disposition_faults(ctx, refinements)
            + nfr_business_authority_policy_faults(ctx, refinements)
            + legacy_mr_meaning_inventory_faults(refinements)
            + legacy_fn_meaning_inventory_faults(ctx, refinements)
            + legacy_ac_meaning_inventory_faults(ctx, refinements)
            + legacy_tc_meaning_inventory_faults(ctx, refinements)
            + legacy_req_disposition_faults(ctx, refinements)
            + orphan_requirement_group_faults(ctx, refinements)
            + legacy_fr_disposition_faults(ctx, refinements)
            + legacy_derived_contract_faults(ctx, refinements)
            + legacy_test_authority_disposition_faults(ctx, refinements)
            + legacy_phase_fault_disposition_faults(ctx, refinements)
            + fr_slice_authority_alignment_policy_faults(ctx, refinements)
            + legacy_trace_fault_policy_faults(ctx, refinements)
            + legacy_media_trace_fault_policy_faults(refinements)
            + legacy_media_inventory_faults(refinements)
            + test_id_authority_alignment_policy_faults(ctx, refinements)
            + bidirectional_trace_faults(ctx)
            + layered_trace_faults(ctx)
            + trace_semantic_responsibility_faults(ctx)
            + phase_alignment_faults(ctx)
            + semantic_dimension_faults(ctx)
        ),
        "OBJ-02": not (
            compatibility_authority_faults(policy)
            + legacy_requirement_consumer_faults()
            + legacy_derived_contract_faults(ctx, refinements)
        ),
        "OBJ-03": ui_subjects <= frozen_subjects
        and not (
            notification_purpose_boundary_faults(ctx)
            + vps_ui_requirement_descent_faults(ctx)
            + obsolete_runtime_route_faults()
        ),
        "OBJ-04": not design_not_started_faults(ctx),
        "OBJ-05": (
            isinstance(records, list)
            and bool(records)
            and len(frozen_subjects) == len(records)
            and not semantic_closure_faults(ctx, refinements)
            and refinements.get("authority_revision_candidate", {}).get("po_decision") is not None
            and refinements.get("provider_policy_bindings", {}).get("status") == "ratified"
        ),
    }
    for objective_id, ready in readiness.items():
        expected = "proven" if ready else expected_status[objective_id]
        if by_id.get(objective_id, {}).get("status") != expected:
            faults.append(f"{objective_id}: 独立した機械完了条件に対するstatusが不一致")
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
        item.get("refinement_id") for item in refinements.get("records", []) if isinstance(item, dict)
    }
    required_candidate_markers = {
        "GENERATED FILE",
        "提案専用の生成view",
        "現行要求の正本・PO承認・設計・実装入力ではない",
        "implementation_authorized=false",
        "本view全体を一括承認として扱わない",
    }
    if (
        not candidate_text
        or not required_candidate_markers.issubset(
            set(marker for marker in required_candidate_markers if marker in candidate_text)
        )
        or any(stable_id not in candidate_text for stable_id in refinement_ids if isinstance(stable_id, str))
    ):
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
    if (
        policy.get("requirements_baseline_status") == "revising"
        and policy.get("implementation_authorized") is not False
    ):
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
    if not all(
        marker in agents_text
        for marker in (
            "詳細な作業規律の唯一の正本は CLAUDE.md",
            "本ファイルと同文ではない",
            "CLAUDE.mdを優先",
            "requirements_baseline_status=revising",
            "implementation_authorized=false",
            "全媒体writeを無効",
        )
    ):
        faults.append("AGENTS要約がCLAUDE詳細正本・revising・全write無効境界を保持しない")
    if not all(
        marker in claude_text
        for marker in (
            "本ファイルはエージェントの作業ルールの正本",
            "requirements_baseline_status=revising",
            "implementation_authorized=false",
            "全媒体writeを無効",
        )
    ):
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
        if any(term in actions for term in operation_terms) and any(
            term in actions for term in maintenance_terms
        ):
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
    if any(
        marker in fr46
        for marker in ("ApprovalTransport", "初期 Discord", "service='discord_app'", "operation='approval_request'")
    ):
        faults.append("FR-46: 承認通知が旧Discord/ApprovalTransport経路を再利用")
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
        name: (
            json.dumps(load(BR_MEDIA_DIR / f"{name}.json"), ensure_ascii=False),
            json.dumps(load(MR_DIR / f"{name}.json"), ensure_ascii=False),
        )
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
    if (
        "mcp → api → browser" in bodies["L4"]
        and "mcp → api → browser" in bodies["L5"]
        and old_order in bodies["FR"]
    ):
        faults.append("FR-41とL4/L5 route resolverのAPI優先順が不一致")
    return faults


def _l2_discord_deep_link_without_notification_class(body: str) -> bool:
    """Detect the old Discord→approval deep-link in its local context.

    L2 prototypes are historical/revalidation material.  The old route must
    remain a raw fault even if an unrelated section happens to mention a
    ``policy_category`` field.  Inspecting a small line window around the
    Discord/AP-02 reference prevents that unrelated token from suppressing the
    quarantine while still allowing a future, explicitly classified route.
    """
    lines = body.splitlines()
    for index, _line in enumerate(lines):
        window = "\n".join(lines[max(0, index - 4) : index + 5])
        if "Discord" in window and "AP-02" in window and "policy_category" not in window:
            return True
    return False


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
    if _l2_discord_deep_link_without_notification_class(body):
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
    adr = (REPO_ROOT / "docs/00-authority/adr/ADR-007-unattended-execution-vps.md").read_text(
        encoding="utf-8"
    )
    s0 = (REPO_ROOT / "docs/L3-system-requirements/canonical/s0-contract_v0.1.md").read_text(encoding="utf-8")
    external_if = (
        REPO_ROOT / "docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md"
    ).read_text(encoding="utf-8")
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
            if isinstance(record, dict) and record.get("subject_id") == "LEGACY-MEDIA-ADMISSION-INVENTORY"
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
        "business_value",
        "execution_mode",
        "principal",
        "effect",
        "policy_category",
        "credential_scope",
        "quota",
        "evidence",
        "acceptance_trace",
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
                isinstance(fn_refs, list) and bool(fn_refs) and isinstance(cmp_refs, list) and bool(cmp_refs)
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
    adr = (REPO_ROOT / "docs/00-authority/adr/ADR-013-vps-product-ui-primary-human-interface.md").read_text(
        encoding="utf-8"
    )
    if "製品runtime、service、Web UI、これらの製品状態正本は\n実装・配備されていない" not in adr:
        faults.append("ADR-013: VPS配置方針と未実装runtime/UI/状態正本の現状を分離していない")
    manifest_item = next(
        (
            item
            for item in load(MANIFEST).get("items", [])
            if isinstance(item, dict)
            and item.get("artifact_id") == "AUTH-ADR-ADR-013-VPS-PRODUCT-UI-PRIMARY-HUMAN-INTERFACE"
        ),
        None,
    )
    if (
        not isinstance(manifest_item, dict)
        or manifest_item.get("applicability_status") != "revalidation_required"
        or manifest_item.get("implementation_input") is not False
    ):
        faults.append("ADR-013: 旧deep-link補助を現行baselineへ適用せず再検証資料として隔離していない")
    environment = (
        REPO_ROOT / "docs/00-authority/development/development-environment_v0.1.md"
    ).read_text(encoding="utf-8")
    if (
        "Discord 運用通知" not in environment
        or "製品の運用通知はVPS UI内inboxに限定し、Discordは採用しない。" not in environment
        or "一方向の運用通知候補" in environment
    ):
        faults.append("development environment: Discord運用通知をVPS UI inbox限定へ隔離していない")
    candidate = (
        REPO_ROOT / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md"
    ).read_text(encoding="utf-8")
    inbox_markers = {
        "`approval_waiting`",
        "`safety_stopped`",
        "`execution_failed`",
        "`action_required`",
        "`operational_alert`",
        "`recorded`",
        "`failed`",
        "`retry_exhausted`",
        "inbox記録成立、外部配送成立、\n業務状態成立",
        "`seen`",
        "`acknowledged`",
        "`resolved`",
        "`expired`",
        "通知状態をapprove／reject",
        "業務状態に追随",
        "自動expiry可否を補完しない",
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
        if br_judgement and not any(
            token in ac_text for token in ("approval_id", "PO receipt", "approver_principal")
        ):
            faults.append(f"{br_id}->{target_id}: {label}がAC/evidenceへ降下していない")
        if target_id == "SR-13" and target_judgement.startswith("なし"):
            faults.append("BR-I6->SR-13: 企画確定の人間判断を別agent審査で代替")
        if target_id == "FR-46" and "機械判定で承認を省略" in target_judgement:
            faults.append("BR-H2->FR-46: auto適格性の機械判定がPOの移行承認を代替")
        if target_id == "FR-75" and (target_judgement.startswith("なし") or "自動判定" in target_judgement):
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
        faults.append(
            f"strategy test ledger lifecycle={manifest_item.get('lifecycle_status')} references={refs}"
        )
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
            faults.append(
                f"{stable_id}: compatibility view slice={old_slice} != contract slice={canonical_slice}"
            )
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
            "source_refs": sorted(
                token.strip() for token in source.split("/") if token.strip() and token.strip() != "—"
            ),
            "related": sorted(
                token.strip() for token in related.split(",") if token.strip() and token.strip() != "—"
            ),
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


def _req_compatibility_delta_overlay(ctx: Ctx) -> dict[str, list[str]]:
    """機械REQ ledgerと旧confirmed Markdownの実差分をfield digestで固定する。"""
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
            "source_refs": sorted(
                token.strip() for token in source.split("/") if token.strip() and token.strip() != "—"
            ),
            "related": sorted(
                token.strip() for token in related.split(",") if token.strip() and token.strip() != "—"
            ),
            "fill_route": None if fill == "—" else fill,
            "priority": priority,
        }
    ledger = {str(item.get("id")): item for item in _items(ctx.req)}
    overlay: dict[str, list[str]] = {}
    for stable_id in sorted(set(rows) & set(ledger)):
        canonical = ledger[stable_id]
        comparisons = {
            "text": canonical.get("text"),
            "source_refs": sorted(str(value) for value in canonical.get("source_refs", [])),
            "related": sorted(str(value) for value in canonical.get("related", [])),
            "fill_route": (
                None if canonical.get("fill_route") in {None, "—"} else canonical.get("fill_route")
            ),
            "priority": canonical.get("priority"),
        }
        for field, canonical_value in comparisons.items():
            if rows[stable_id][field] != canonical_value:
                overlay[f"{stable_id}/{field}"] = [
                    _digest(canonical_value),
                    _digest(rows[stable_id][field]),
                ]
    return overlay


def req_authority_normalization_policy_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """既存REQ意味inventoryと19-field delta overlayを一意なcutover候補へ束縛する。"""
    policy = refinements.get("req_authority_normalization_policy")
    if not isinstance(policy, dict):
        return ["REQ authority normalization policyがない"]
    faults: list[str] = []
    policy_body = {
        key: value
        for key, value in policy.items()
        if key not in {"status", "delta_overlay_dispositions"}
    }
    if _digest(policy_body) != "sha256:0837540ada9c2549cc3f372e2a1b7c84e23cdb86f8289cd93caf7d3c5aa34bb2":
        faults.append("REQ authority normalization policy bodyが正本digestと不一致")
    if policy.get("status") not in {"candidate_unratified", "ratified"}:
        faults.append("REQ authority normalization policy statusが不正")
    inventory = refinements.get("legacy_requirement_meaning_inventory", {})
    migrations = inventory.get("meaning_migrations", {}) if isinstance(inventory, dict) else {}
    req_rows = {key: value for key, value in migrations.items() if str(key).startswith("REQ-")}
    if policy.get("existing_req_id_count") != len(req_rows):
        faults.append("REQ55 meaning inventory被覆が不一致")
    if policy.get("existing_req_subset_id_digest") != _digest(sorted(req_rows)):
        faults.append("REQ55 meaning inventory ID digestが不一致")
    if policy.get("existing_req_subset_meaning_digest") != _digest(req_rows):
        faults.append("REQ55 meaning inventory semantic digestが不一致")
    overlay = _req_compatibility_delta_overlay(ctx)
    if policy.get("delta_overlay") != overlay or len(overlay) != 19:
        faults.append("REQ 15 ID・19 field delta overlayがsource実測と不一致")
    disposition = policy.get("delta_overlay_dispositions", {})
    if isinstance(disposition, dict) and disposition.get("status") == "pending_po_classification":
        if policy.get("status") != "candidate_unratified":
            faults.append("REQ pending classificationなのにpolicyが早期ratified")
        if disposition.get("selected_rows") != {} or disposition.get("cutover_blocked") is not True:
            faults.append("REQ delta未承認なのに選択又はcutover解除されている")
    elif isinstance(disposition, dict) and disposition.get("status") in {
        "classified_pending_cutover",
        "cutover_complete",
    }:
        disposition_status = disposition.get("status")
        expected_policy_status = (
            "ratified" if disposition_status == "cutover_complete" else "candidate_unratified"
        )
        if policy.get("status") != expected_policy_status:
            faults.append("REQ normalization stageとpolicy statusが不一致")
        selected_rows = disposition.get("selected_rows")
        selected_rows_dict = selected_rows if isinstance(selected_rows, dict) else {}
        expected_row_keys = {
            "source_artifact_ids",
            "source_revisions",
            "source_content_digests",
            "source_value_digests",
            "selection",
            "selected_value_digest",
            "candidate_row_digest",
            "disposition",
            "rationale",
            "owner_subject_id",
            "source_refs",
            "prohibited_inheritance",
            "downstream_trace_impact",
            "resume_conditions",
        }
        if not isinstance(selected_rows, dict) or set(selected_rows) != set(overlay):
            faults.append("REQ classified delta rowsが19-field overlayをexact被覆しない")
        else:
            manifest = load(MANIFEST)
            manifest_by_id = {
                str(item.get("artifact_id")): item
                for item in manifest.get("items", [])
                if isinstance(item, dict)
            }
            source_items = [manifest_by_id.get("L1-REQ"), manifest_by_id.get("L1-REQUIREMENT-LIST")]
            source_revisions: list[str | None] = []
            source_content_digests = []
            for item in source_items:
                path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
                relative = str(item.get("canonical_path")) if isinstance(item, dict) else ""
                revision_result = git("log", "-1", "--format=%H", "--", relative) if relative else None
                source_revisions.append(
                    revision_result.stdout.strip()
                    if revision_result is not None and revision_result.returncode == 0
                    else None
                )
                source_content_digests.append(
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                    if path is not None and path.is_file()
                    else None
                )
            for key, row in selected_rows.items():
                if not isinstance(row, dict) or set(row) != expected_row_keys:
                    faults.append(f"{key}: REQ classified row field閉集合が不正")
                    continue
                if row.get("source_artifact_ids") != ["L1-REQ", "L1-REQUIREMENT-LIST"]:
                    faults.append(f"{key}: REQ classified row source artifactが不正")
                if row.get("source_revisions") != source_revisions:
                    faults.append(f"{key}: REQ classified row source revisionがmanifestと不一致")
                if row.get("source_content_digests") != source_content_digests:
                    faults.append(f"{key}: REQ classified row source content digestが実artifactと不一致")
                if row.get("source_value_digests") != overlay[key]:
                    faults.append(f"{key}: REQ classified row source value digest不一致")
                for digest_key in ("source_content_digests",):
                    values = row.get(digest_key)
                    if not isinstance(values, list) or len(values) != 2 or any(
                        not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value)
                        for value in values
                    ):
                        faults.append(f"{key}: REQ classified row source content digest不正")
                if not isinstance(row.get("source_revisions"), list) or len(row["source_revisions"]) != 2:
                    faults.append(f"{key}: REQ classified row source revision不正")
                selection = row.get("selection")
                expected_disposition = ({
                    "ledger": "retain",
                    "markdown": "replace",
                    "new_candidate": "replace",
                    "defer": "defer",
                    "obsolete": "obsolete",
                }.get(selection) if isinstance(selection, str) else None)
                if row.get("disposition") != expected_disposition:
                    faults.append(f"{key}: selectionとdispositionが不一致")
                selected_digest = row.get("selected_value_digest")
                if selection == "ledger" and selected_digest != overlay[key][0]:
                    faults.append(f"{key}: ledger選択digest不一致")
                elif selection == "markdown" and selected_digest != overlay[key][1]:
                    faults.append(f"{key}: Markdown選択digest不一致")
                elif selection == "new_candidate" and not isinstance(selected_digest, str):
                    faults.append(f"{key}: new candidate選択digestがない")
                elif selection in {"defer", "obsolete"} and selected_digest is not None:
                    faults.append(f"{key}: defer/obsoleteにselected digestがある")
                elif selection not in {"ledger", "markdown", "new_candidate", "defer", "obsolete"}:
                    faults.append(f"{key}: REQ selectionが不正")
                expected_candidate_row_digest = (
                    None
                    if selection in {"defer", "obsolete"}
                    else _digest(
                        {
                            "row_key": key,
                            "selection": selection,
                            "selected_value_digest": selected_digest,
                            "disposition": expected_disposition,
                        }
                    )
                )
                if row.get("candidate_row_digest") != expected_candidate_row_digest:
                    faults.append(f"{key}: candidate row digestが選択projectionと不一致")
                resume = row.get("resume_conditions")
                if not isinstance(resume, list) or (selection == "defer") != bool(resume):
                    faults.append(f"{key}: REQ deferとresume conditionが不一致")
                for required_text in ("rationale", "owner_subject_id", "downstream_trace_impact"):
                    if not isinstance(row.get(required_text), str) or not row[required_text].strip():
                        faults.append(f"{key}: {required_text}がない")
                for required_list in ("source_refs", "prohibited_inheritance"):
                    if not isinstance(row.get(required_list), list):
                        faults.append(f"{key}: {required_list}が配列でない")
        approval = disposition.get("classification_approval")
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "req_subset_meaning_digest": policy.get("existing_req_subset_meaning_digest"),
            "delta_overlay_digest": _digest(overlay),
            "selected_rows_digest": _digest(selected_rows),
        }
        if not isinstance(approval, dict) or any(
            approval.get(key) != value for key, value in expected_approval.items()
        ) or not isinstance(approval.get("approved_at"), str):
            faults.append("REQ classified deltaにPO row-set receiptがない又はdigest不一致")
        if disposition_status == "classified_pending_cutover":
            if disposition.get("cutover_blocked") is not True:
                faults.append("REQ classified pending cutoverなのにblockが解除されている")
            if disposition.get("cutover_artifact_bindings") is not None:
                faults.append("REQ classified pending cutoverにcutover完了bindingを先置きできない")
            candidate_binding = disposition.get("candidate_artifact_binding")
            manifest = load(MANIFEST)
            manifest_by_id = {
                str(item.get("artifact_id")): item
                for item in manifest.get("items", [])
                if isinstance(item, dict)
            }
            item = (
                manifest_by_id.get(str(candidate_binding.get("artifact_id")))
                if isinstance(candidate_binding, dict)
                else None
            )
            path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
            actual_digest = (
                "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                if path is not None and path.is_file()
                else None
            )
            if (
                not isinstance(candidate_binding, dict)
                or set(candidate_binding) != {"artifact_id", "content_digest"}
                or candidate_binding.get("artifact_id")
                != "AUTH-DEVELOPMENT-REQ-AUTHORITY-NORMALIZATION-CANDIDATE"
                or not isinstance(item, dict)
                or item.get("layer") != "00-authority"
                or item.get("artifact_type") != "requirement-normalization-candidate"
                or item.get("authority_format") != "json"
                or item.get("authority_status") != "active"
                or item.get("implementation_input") is not False
                or candidate_binding.get("content_digest") != actual_digest
            ):
                faults.append("REQ classified pending candidateがactive JSON・implementation_input=falseへ束縛されていない")
            else:
                try:
                    candidate = json.loads(path.read_text(encoding="utf-8")) if path else {}
                except (OSError, json.JSONDecodeError):
                    candidate = {}
                expected_rows = {
                    key: row.get("candidate_row_digest")
                    for key, row in selected_rows_dict.items()
                    if isinstance(row, dict) and row.get("candidate_row_digest") is not None
                }
                if candidate.get("normalization_row_digests") != expected_rows:
                    faults.append("REQ classified pending candidateが19 row selection projectionと不一致")
            return faults
        if policy.get("status") != "ratified":
            faults.append("REQ cutover completeなのにnormalization policyがratifiedでない")
        candidate_binding = disposition.get("candidate_artifact_binding")
        complete_manifest = load(MANIFEST)
        complete_manifest_by_id = {
            str(item.get("artifact_id")): item
            for item in complete_manifest.get("items", [])
            if isinstance(item, dict)
        }
        complete_candidate_item = (
            complete_manifest_by_id.get(str(candidate_binding.get("artifact_id")))
            if isinstance(candidate_binding, dict)
            else None
        )
        if (
            not isinstance(candidate_binding, dict)
            or candidate_binding.get("artifact_id")
            != "AUTH-DEVELOPMENT-REQ-AUTHORITY-NORMALIZATION-CANDIDATE"
            or not isinstance(complete_candidate_item, dict)
            or complete_candidate_item.get("layer") != "00-authority"
            or complete_candidate_item.get("artifact_type")
            != "requirement-normalization-candidate"
            or complete_candidate_item.get("authority_format") != "json"
            or complete_candidate_item.get("authority_status") != "active"
            or complete_candidate_item.get("implementation_input") is not True
        ):
            faults.append("REQ cutover complete candidateの専用identity又はimplementation inputが不正")
        bindings = disposition.get("cutover_artifact_bindings")
        required_bindings = {
            "candidate_json_artifact_id",
            "candidate_json_content_digest",
            "generated_view_artifact_id",
            "generated_view_content_digest",
            "trace_artifact_id",
            "trace_content_digest",
            "manifest_content_digest",
            "baseline_content_digest",
            "target_commit",
            "target_tree",
            "same_commit",
            "trace_diff_count",
            "independent_go_review_artifact_id",
            "independent_go_review_digest",
        }
        if not isinstance(bindings, dict) or set(bindings) != required_bindings:
            faults.append("REQ classified cutover artifact bindingが不完全")
        elif (
            not isinstance(candidate_binding, dict)
            or bindings.get("candidate_json_artifact_id") != candidate_binding.get("artifact_id")
            or bindings.get("candidate_json_content_digest") != candidate_binding.get("content_digest")
        ):
            faults.append("REQ cutover candidate bindingがclassified candidateと不一致")
        elif (
            bindings.get("same_commit") is not True
            or bindings.get("trace_diff_count") != 0
            or any(
                not isinstance(bindings.get(key), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", bindings[key])
                for key in required_bindings
                if key.endswith("_digest")
            )
        ):
            faults.append("REQ classified view/trace/manifest/baseline/Go束縛が不正")
        else:
            manifest = load(MANIFEST)
            manifest_by_id = {
                str(item.get("artifact_id")): item
                for item in manifest.get("items", [])
                if isinstance(item, dict)
            }
            artifact_pairs = [
                ("candidate_json_artifact_id", "candidate_json_content_digest"),
                ("generated_view_artifact_id", "generated_view_content_digest"),
                ("trace_artifact_id", "trace_content_digest"),
                ("independent_go_review_artifact_id", "independent_go_review_digest"),
            ]
            artifact_paths: dict[str, Path] = {}
            for id_key, digest_key in artifact_pairs:
                item = manifest_by_id.get(str(bindings.get(id_key)))
                path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
                if path is not None:
                    artifact_paths[id_key] = path
                actual_digest = (
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                    if path is not None and path.is_file()
                    else None
                )
                if actual_digest != bindings.get(digest_key):
                    faults.append(f"REQ classified {id_key}がmanifest実artifactへ束縛されていない")
            candidate_path = artifact_paths.get("candidate_json_artifact_id")
            try:
                candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path else {}
            except (OSError, json.JSONDecodeError):
                candidate = {}
            expected_candidate_rows = {
                key: row.get("candidate_row_digest")
                for key, row in selected_rows_dict.items()
                if isinstance(row, dict) and row.get("candidate_row_digest") is not None
            }
            if candidate.get("normalization_row_digests") != expected_candidate_rows:
                faults.append("REQ classified candidate JSONが選択row digest集合と不一致")
            manifest_digest = "sha256:" + hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
            baseline_path = REPO_ROOT / "docs/00-authority/baselines/baseline.json"
            baseline_digest = "sha256:" + hashlib.sha256(baseline_path.read_bytes()).hexdigest()
            if (
                bindings.get("manifest_content_digest") != manifest_digest
                or bindings.get("baseline_content_digest") != baseline_digest
            ):
                faults.append("REQ classified manifest/baseline digestが実artifactと不一致")
            commit_paths = [
                artifact_paths.get("candidate_json_artifact_id"),
                artifact_paths.get("generated_view_artifact_id"),
                artifact_paths.get("trace_artifact_id"),
                MANIFEST,
                baseline_path,
            ]
            commits = []
            for path in commit_paths:
                relative = str(path.relative_to(REPO_ROOT)) if isinstance(path, Path) else ""
                result = git("log", "-1", "--format=%H", "--", relative) if relative else None
                commits.append(
                    result.stdout.strip()
                    if result is not None and result.returncode == 0
                    else None
                )
            if len(set(commits)) != 1 or commits[0] != bindings.get("target_commit"):
                faults.append("REQ classified candidate/view/trace/manifest/baselineが同一target commitでない")
            review_path = artifact_paths.get("independent_go_review_artifact_id")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
            except (OSError, json.JSONDecodeError):
                review = {}
            if (
                review.get("verdict") != "Go"
                or review.get("separation_status") != "ci_attested"
                or review.get("target_commit") != bindings.get("target_commit")
                or review.get("target_tree") != bindings.get("target_tree")
                or review.get("reviewer_principal") in {None, "po", review.get("author_principal")}
            ):
                faults.append("REQ classified independent Go reviewのcommit・主体分離・CI attestationが不正")
            tree_result = git("rev-parse", f"{bindings.get('target_commit')}^{{tree}}")
            if tree_result.returncode != 0 or tree_result.stdout.strip() != bindings.get("target_tree"):
                faults.append("REQ classified target treeがtarget commitと不一致")
            reviewed = review.get("reviewed_artifact_digests", {})
            reviewed_paths = {
                str(manifest_by_id[str(bindings[id_key])]["canonical_path"]): bindings[digest_key]
                for id_key, digest_key in artifact_pairs[:3]
                if str(bindings.get(id_key)) in manifest_by_id
            }
            if not isinstance(reviewed, dict) or any(
                reviewed.get(path) != digest.removeprefix("sha256:")[:16]
                for path, digest in reviewed_paths.items()
            ):
                faults.append("REQ classified independent Go reviewがcandidate/view/trace digestを被覆しない")
        if faults and disposition.get("cutover_blocked") is not True:
            faults.append("REQ classified closure未完なのにcutover blockが解除されている")
        elif not faults and disposition.get("cutover_blocked") is not False:
            faults.append("REQ classified closure完了後もcutover block状態が不正")
    else:
        faults.append("REQ delta classification statusが不正")
    return faults


def nfr_business_authority_policy_faults(ctx: Ctx, refinements: dict[str, Any]) -> list[str]:
    """旧NFR11意味inventoryをstable root・scope・phase authorityへfail-closeで接続する。"""
    policy = refinements.get("nfr_business_authority_policy")
    if not isinstance(policy, dict):
        return ["NFR business authority policyがない"]
    faults: list[str] = []
    body = {
        key: value
        for key, value in policy.items()
        if key not in {"status", "authority_rows", "classification_state"}
    }
    if _digest(body) != "sha256:d8323cc814480fe3e18432da0bc11ae295042b9b52a08e13ba5de645cae8cbda":
        faults.append("NFR business authority policy bodyが正本digestと不一致")
    inventory = refinements.get("legacy_strategy_quality_meaning_inventory", {})
    migrations = inventory.get("meaning_migrations", {}) if isinstance(inventory, dict) else {}
    nfr_rows = {key: value for key, value in migrations.items() if str(key).startswith("NFR-")}
    rows = policy.get("authority_rows")
    expected_ids = {f"NFR-{index}" for index in range(1, 12)}
    expected_keys = {
        "parent_semantic_digest",
        "stable_root_subject_id",
        "actor_or_principal_scope",
        "applicability_scope",
        "lifecycle_phase",
        "disposition",
        "owner_subject_id",
        "resume_conditions",
        "evidence_or_measurement_authority",
        "disposition_rationale",
    }
    if not isinstance(rows, dict) or set(rows) != expected_ids or set(nfr_rows) != expected_ids:
        faults.append("NFR authority overlayが11 IDをexact被覆しない")
        return faults
    for stable_id, row in rows.items():
        if not isinstance(row, dict) or set(row) != expected_keys:
            faults.append(f"{stable_id}: NFR authority row field閉集合が不正")
            continue
        if row.get("parent_semantic_digest") != _digest(nfr_rows[stable_id]):
            faults.append(f"{stable_id}: NFR parent meaning digestがstale")
        if row.get("owner_subject_id") != "NFR-BUSINESS-AUTHORITY":
            faults.append(f"{stable_id}: NFR authority ownerが不正")
    universe = set(policy.get("classified_field_universe", []))
    contracts = policy.get("disposition_field_contracts", {})
    for disposition in ("retain", "replace", "defer", "obsolete"):
        contract = contracts.get(disposition, {}) if isinstance(contracts, dict) else {}
        required = set(contract.get("required", []))
        prohibited = set(contract.get("prohibited", []))
        if required & prohibited or required | prohibited != universe:
            faults.append(f"NFR {disposition}: disposition field partitionがexactでない")
    state = policy.get("classification_state", {})
    stage = state.get("status") if isinstance(state, dict) else None
    if stage == "pending_po_classification":
        if policy.get("status") != "candidate_unratified":
            faults.append("NFR未分類なのにpolicyが早期ratified")
        for stable_id, row in rows.items():
            if (
                row.get("disposition") != "pending_po"
                or any(
                    row.get(key) is not None
                    for key in (
                        "stable_root_subject_id",
                        "actor_or_principal_scope",
                        "applicability_scope",
                        "lifecycle_phase",
                        "evidence_or_measurement_authority",
                        "disposition_rationale",
                    )
                )
                or row.get("resume_conditions") != []
            ):
                faults.append(f"{stable_id}: NFR pending rowが未決境界を破る")
        if state.get("cutover_blocked") is not True or state.get("classification_approval") is not None:
            faults.append("NFR pending classificationのcutover/approval境界が不正")
    elif stage in {"classified_pending_cutover", "cutover_complete"}:
        expected_status = "ratified" if stage == "cutover_complete" else "candidate_unratified"
        if policy.get("status") != expected_status:
            faults.append("NFR classification stageとpolicy statusが不一致")
        for stable_id, row in rows.items():
            disposition = row.get("disposition")
            if disposition not in {"retain", "replace", "defer", "obsolete"}:
                faults.append(f"{stable_id}: NFR dispositionが未分類")
                continue
            contract = contracts.get(disposition, {}) if isinstance(contracts, dict) else {}
            for field in contract.get("required", []):
                if not row.get(field):
                    faults.append(f"{stable_id}: {disposition}必須field {field}が欠落")
            if not isinstance(row.get("disposition_rationale"), str) or not row[
                "disposition_rationale"
            ].strip():
                faults.append(f"{stable_id}: NFR disposition rationaleが非空文字列でない")
            for field in contract.get("prohibited", []):
                value = row.get(field)
                if value is not None and value != []:
                    faults.append(f"{stable_id}: {disposition}禁止field {field}が混入")
            if disposition in {"retain", "replace"}:
                known_subjects = {
                    str(record.get("subject_id"))
                    for record in refinements.get("records", [])
                    if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
                }
                known_roots = {
                    str(item.get("id"))
                    for source in (ctx.brc, ctx.req)
                    for item in _items(source)
                    if isinstance(item.get("id"), str)
                }
                if row.get("stable_root_subject_id") not in known_roots:
                    faults.append(f"{stable_id}: active NFR stable rootが未知BR/REQ")
                actor_scope = row.get("actor_or_principal_scope")
                if (
                    not isinstance(actor_scope, dict)
                    or set(actor_scope) != {"principal_subject_id", "scope_ids"}
                    or not isinstance(actor_scope.get("principal_subject_id"), str)
                    or actor_scope.get("principal_subject_id") not in known_subjects
                    or not isinstance(actor_scope.get("scope_ids"), list)
                    or not actor_scope["scope_ids"]
                    or any(not isinstance(value, str) or not value for value in actor_scope["scope_ids"])
                    or len(actor_scope["scope_ids"]) != len(set(actor_scope["scope_ids"]))
                    or any(
                        not value.startswith(("profile:", "operation:", "resource:", "risk:"))
                        for value in actor_scope["scope_ids"]
                    )
                ):
                    faults.append(f"{stable_id}: NFR actor/principal scope型が不正")
                applicability = row.get("applicability_scope")
                if (
                    not isinstance(applicability, dict)
                    or set(applicability) != {"profile_ids", "operation_ids", "risk_classes"}
                    or any(not isinstance(applicability.get(key), list) for key in applicability)
                    or not any(applicability.values())
                    or any(
                        any(not isinstance(value, str) or not value for value in values)
                        or len(values) != len(set(values))
                        for values in applicability.values()
                    )
                    or any(
                        not value.startswith("profile:")
                        for value in applicability.get("profile_ids", [])
                    )
                    or any(
                        not value.startswith("operation:")
                        for value in applicability.get("operation_ids", [])
                    )
                    or not set(applicability.get("risk_classes", []))
                    <= {"low", "medium", "high", "ymyl", "regulated"}
                ):
                    faults.append(f"{stable_id}: NFR applicability scope型が不正")
                if row.get("lifecycle_phase") not in {"initial", "later"}:
                    faults.append(f"{stable_id}: NFR phaseが未分類又は旧slice")
                measurement = row.get("evidence_or_measurement_authority")
                if (
                    not isinstance(measurement, dict)
                    or set(measurement)
                    != {"authority_subject_id", "registration_required", "quality_dimensions"}
                    or not isinstance(measurement.get("authority_subject_id"), str)
                    or measurement.get("authority_subject_id") not in known_subjects
                    or measurement.get("registration_required") is not True
                    or not isinstance(measurement.get("quality_dimensions"), list)
                    or not measurement["quality_dimensions"]
                    or any(
                        not isinstance(value, str) or not value
                        for value in measurement["quality_dimensions"]
                    )
                    or len(measurement["quality_dimensions"])
                    != len(set(measurement["quality_dimensions"]))
                    or not set(measurement["quality_dimensions"])
                    <= {
                        "security",
                        "privacy",
                        "accessibility",
                        "performance",
                        "availability",
                        "recovery",
                        "operation",
                        "migration",
                        "rollback",
                        "cost",
                        "quota",
                        "determinism",
                        "fail_close",
                    }
                ):
                    faults.append(f"{stable_id}: NFR measurement authority型が不正")
        approval = state.get("classification_approval")
        expected_approval = {
            "authority": "PO",
            "approver_principal": "po",
            "parent_inventory_digest": inventory.get("meaning_migrations_digest"),
            "authority_rows_digest": _digest(rows),
        }
        if not isinstance(approval, dict) or any(
            approval.get(key) != value for key, value in expected_approval.items()
        ) or not isinstance(approval.get("approved_at"), str):
            faults.append("NFR authority分類にPO row-set receiptがない又はdigest不一致")
        expected_blocked = stage != "cutover_complete"
        if state.get("cutover_blocked") is not expected_blocked:
            faults.append("NFR authority classification stageとcutover blockが不一致")
    else:
        faults.append("NFR authority classification stageが不正")
    return faults


def compatibility_authority_faults(policy: dict[str, Any]) -> list[str]:
    compatibility = policy.get("compatibility_inputs")
    expected = {
        "docs/L1-business-requirements/canonical/req/req.json": "read_only_revalidation_ledger",
        "docs/L1-business-requirements/canonical/requirement-list_v0.1.md": "historical_confirmed_view_not_current_authority",
        str(
            COMPATIBILITY_VIEW.relative_to(Path(__file__).resolve().parents[2])
        ): "read_only_revalidation_view",
        "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md": "historical_confirmed_view_not_current_authority",
    }
    faults = [] if compatibility == expected else ["requirements.json compatibility viewの非権威境界が不正"]
    manifest = load(MANIFEST)
    manifest_by_path = {
        str(item.get("canonical_path")): item
        for item in manifest.get("items", [])
        if isinstance(item, dict)
    }
    manifest_by_path.update(
        {
            str(item.get("view_path")): item
            for item in manifest.get("items", [])
            if isinstance(item, dict) and item.get("view_path")
        }
    )
    for relative_path in HISTORICAL_VIEW_BANNERS:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            faults.append(f"{relative_path}: historical/revalidation文書が存在しない")
            continue
        item = manifest_by_path.get(relative_path)
        if (
            not isinstance(item, dict)
            or item.get("applicability_status") != "revalidation_required"
            or item.get("implementation_input") is not False
        ):
            faults.append(f"{relative_path}: manifest historical/non-input境界が不正")
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
    faults: list[str] = []
    for relative_path in sorted(consumers):
        if not (REPO_ROOT / relative_path).is_file():
            faults.append(f"{relative_path}: consumerが存在しない")
    legacy_paths = {
        "docs/L1-business-requirements/canonical/req/req.json",
        "docs/L1-business-requirements/canonical/requirement-list_v0.1.md",
        "docs/L3-system-requirements/canonical/functional/requirements.json",
        "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md",
        *json.loads(AUTHORITY_POLICY.read_text(encoding="utf-8")).get("canonical_sources", []),
    }
    manifest = load(MANIFEST)
    implementation_inputs = {
        str(item.get("canonical_path"))
        for item in manifest.get("items", [])
        if isinstance(item, dict) and item.get("implementation_input") is True
    }
    for relative_path in sorted(implementation_inputs):
        path = REPO_ROOT / relative_path
        if not path.is_file() or path.suffix not in {".md", ".json", ".sql", ".py"}:
            continue
        text = path.read_text(encoding="utf-8")
        referenced = sorted(legacy for legacy in legacy_paths if legacy in text)
        if referenced:
            faults.append(f"{relative_path}: implementation inputが旧正本を参照={referenced}")
    allowed_audit_consumers = {
        "tools/gates/common.py",
        "tools/gates/requirement_discovery.py",
        "tools/gates/requirement_engine.py",
        "tools/gates/requirements.py",
        "tools/gates/test_pairing.py",
        "scripts/render_views.py",
    }
    code_roots = [REPO_ROOT / "src", REPO_ROOT / "scripts", REPO_ROOT / "tools"]
    for root in code_roots:
        for path in sorted(root.rglob("*.py")):
            relative = str(path.relative_to(REPO_ROOT))
            if relative in allowed_audit_consumers:
                continue
            text = path.read_text(encoding="utf-8")
            referenced = sorted(legacy for legacy in legacy_paths if legacy in text)
            if referenced:
                faults.append(f"{relative}: 非監査codeが旧要求正本を直接参照={referenced}")
    gate_import = re.compile(r"(?:from|import)\s+tools\.gates(?:\.|\s)")
    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        if gate_import.search(path.read_text(encoding="utf-8")):
            faults.append(
                f"{path.relative_to(REPO_ROOT)}: product codeが旧契約を公開する監査gate moduleをimport"
            )
    allowed_gate_scripts = {
        "scripts/dev.py",
        "scripts/check_skip_budget.py",
        "scripts/render_views.py",
        "scripts/validate_requirements.py",
    }
    for path in sorted((REPO_ROOT / "scripts").rglob("*.py")):
        relative = str(path.relative_to(REPO_ROOT))
        if relative not in allowed_gate_scripts and gate_import.search(path.read_text(encoding="utf-8")):
            faults.append(f"{relative}: 非監査scriptが旧契約contextをimport")
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
        REPO_ROOT / "docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md"
    ).read_text(encoding="utf-8")
    required_markers = {
        "本ベースライン承認後にL2以降を新規に降下する",
        "旧画面、API、DDL、状態、slice、AC／TC、実装単位は\n参考資料に限り",
        "framework、component、URL、port、reverse proxy、認証protocol、session実装、CSRF方式、DB table、API、\nscreen ID、状態enum、retry回数、deployment topologyは設計事項である",
    }
    missing = sorted(marker for marker in required_markers if marker not in candidate)
    if missing:
        faults.append(f"要求候補に設計未着手境界がない={missing}")
    readme_path = REPO_ROOT / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    required_readme_markers = {
        "旧baseline業務要求・新要求候補（manifest applicabilityに従う。実装入力ではない）",
        "旧機能別設計・再設計対象（全件`revalidation_required`／`implementation_input=false`）",
    }
    missing_readme = sorted(marker for marker in required_readme_markers if marker not in readme_text)
    if missing_readme:
        faults.append(f"READMEのL1/L6入口が旧baseline・設計未着手境界を保持しない={missing_readme}")
    prohibited_readme_markers = {
        "| [L1-business-requirements](docs/L1-business-requirements/) | 業務要求 |",
        "| [L6-feature-design](docs/L6-feature-design/) | 機能別設計 |",
        "現行の契約 JSON 9 本",
    }
    present_readme = sorted(marker for marker in prohibited_readme_markers if marker in readme_text)
    if present_readme:
        faults.append(f"READMEのL1/L6入口に旧current表示が残る={present_readme}")
    environment_path = REPO_ROOT / "docs/00-authority/development/development-environment_v0.1.md"
    environment_text = environment_path.read_text(encoding="utf-8") if environment_path.is_file() else ""
    required_environment_markers = {
        "旧要求に基づく L2 5点書式の評価用draft",
        "新要求からのL2画面設計は要求freeze後に再降下するまで開始しない。",
        "再検証対象の契約 JSON／DDL／状態遷移／evidence schema は旧baselineの構造資料であり、現行の要求・設計・実装入力ではない。",
        "要求freeze前の完了条件に製品L2画面設計を含めない。",
    }
    missing_environment = sorted(marker for marker in required_environment_markers if marker not in environment_text)
    if missing_environment:
        faults.append(f"開発環境入口にL2評価用draft・旧方式非継承境界がない={missing_environment}")
    prohibited_environment_markers = {
        "要件定義〜L3 要求確定と L2 プロトタイプ設計を行うための環境",
        "対象は要件定義、契約 JSON の更新、生成ビュー、L2 画面設計、検証",
        "正本は契約 JSON／DDL／状態遷移／evidence schema と artifact-manifest。",
        "4. L2 の画面は 5 点セットで入口・状態・失敗・戻る操作・アクセシビリティを記録する。",
    }
    present_environment = sorted(marker for marker in prohibited_environment_markers if marker in environment_text)
    if present_environment:
        faults.append(f"開発環境入口にL2設計又は旧方式の現在形命令が残る={present_environment}")
    workflow_path = REPO_ROOT / "docs/00-authority/development/requirement-definition-workflow_v0.1.md"
    workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else ""
    required_workflow_markers = {
        "旧BR／REQ／FR／NFR／AC／TC契約、s0-contract、9契約JSONは再検証sourceであり、現行の要求・設計・実装正本ではない。",
        "旧L2 5点書式の評価用draft／PoC evidence",
        "新要求からのL2画面設計・旧方式の採用は、PO freeze、L2〜L6再設計、別admissionの後に新正本から再選択する。",
        "新要求からの画面ID・状態・UI設計はPO freeze後に再降下し、現段階の評価用draftから継承しない。",
        "旧承認 API／既存 config INSERT は再検証対象であり、新要求のwrite方式として継承しない。",
        "旧L1要求ID（BR／REQ）と旧L3 FR／NFRの `trace_up` は再検証inventoryの固定参照として扱う。",
        "旧AC／TCの契約節接続は再検証inventoryのoracle確認に限る。",
    }
    missing_workflow = sorted(marker for marker in required_workflow_markers if marker not in workflow_text)
    if missing_workflow:
        faults.append(f"要件定義ワークフロー入口にL2評価用draft・旧方式非継承境界がない={missing_workflow}")
    prohibited_workflow_markers = {
        "現行のJSON契約正本へPython-nativeに適応する手順",
        "| intake | initiative、actor、背景、対象 domain | 対象と非対象が明示される | BR 背骨／br-media |",
        "| prototype | normal／cancel／failure／timeout の流れと画面・媒体境界 | 実物または観測で不確実性を減らす | L2 5 点セット／PoC evidence |",
        "| specified | BR→REQ→FR/NFR、状態、データ、権限、例外 | 受入可能な粒度で記述される | 9 契約 JSON／s0-contract |",
        "| verified | AC と TC を双方向接続 | normal／reject／boundary-recovery が実行可能 | AC／TC contracts |",
        "L2 の画面 ID は `L2-UI-*` artifact と画面 ID（AP-01 等）を分ける。画面は業務状態を独自定義せず、s0-contract と",
        "L2 の画面案は URL から承認を確定させず、write 操作は承認 API または既存の config INSERT の契約に限定する。",
        "`requirement-engine-authority.json`が9契約JSONをsource authorityとして列挙する。",
        "L1 の要求 ID（BR／REQ）は既存正本の ID を維持し、L3 FR／NFR は対応する上流 ID を `trace_up` に持つ。",
        "AC は検証する契約節を明示し、TC は AC と同じ契約節を観測する。",
    }
    present_workflow = sorted(marker for marker in prohibited_workflow_markers if marker in workflow_text)
    if present_workflow:
        faults.append(f"要件定義ワークフロー入口にL2設計又は旧方式の現在形命令が残る={present_workflow}")
    adr012_path = REPO_ROOT / "docs/00-authority/adr/ADR-012-helix-harness-template-adoption.md"
    adr012_text = adr012_path.read_text(encoding="utf-8") if adr012_path.is_file() else ""
    required_adr012_markers = {
        "L2は旧要求に基づく5点書式の評価用draftだけを扱い、新要求からのL2設計は要求freeze後に再降下する。",
        "旧要求評価用のL2 5点書式",
        "新要求からのL2プロトタイプ／画面設計は要求freeze・L2〜L6再設計・別admission後に開始する。",
        "旧baselineの契約 JSON 9 本、DDL・状態遷移・evidence 型は",
        "現行要求・設計・実装入力にしない。",
        "現段階では旧要求評価用の\n  L2 5点書式だけを検証し、新要求からのUI設計・認証・CSRF・再認証・principal束縛の方式は要求freeze後に再降下する。",
    }
    missing_adr012 = sorted(marker for marker in required_adr012_markers if marker not in adr012_text)
    if missing_adr012:
        faults.append(f"ADR-012のL2評価用draft・旧方式非継承境界がない={missing_adr012}")
    prohibited_adr012_markers = {
        "L2 プロトタイプ設計までを直ちに利用可能にする",
        "実装入力は既存の契約 JSON 9 本",
        "UI は L2 設計を先行し",
    }
    present_adr012 = sorted(marker for marker in prohibited_adr012_markers if marker in adr012_text)
    if present_adr012:
        faults.append(f"ADR-012にL2設計又は旧方式の現在形命令が残る={present_adr012}")
    claude_path = REPO_ROOT / "CLAUDE.md"
    claude_text = claude_path.read_text(encoding="utf-8") if claude_path.is_file() else ""
    required_claude_markers = {
        "要件候補〜L3再検証と旧L2 5点書式の評価用draftの開発入口",
        "新要求からのL2画面設計はrequirements freeze後の再降下・別admissionまで開始しない。",
        "旧baseline L6のslice 4点一致（G-SLICE-PLACEMENT）は構造再検証専用の資料であり、現行のslice・",
        "新要求のslice・forward_refs・実装降下先はPO freeze後に新正本から再選択する。",
        "既存`src/helix/`のDU-01〜12は旧baselineの再検証対象であり、freeze・L2〜L6再設計・admission後に",
        "旧baselineの文書ペア（HELIX 式・再検証資料。現行要求・設計・実装入力ではない）",
        "旧baselineの戦略層は strategy-loop-requirements／strategy-learning-contract ↔ strategy-loop-design／",
        "strategy-loop-test-design の再検証用ペア（SR 19／SCM 10／STC）である。現行戦略の受入・実装正本ではない。",
        "旧baselineのDDL・状態遷移・evidence型・WF契約は再検証資料であり、現行要求・設計・実装入力ではない",
        "旧baselineの契約 JSON 群（再検証資料・現行実装入力ではない）",
        "旧baselineの L6 implementation-units.json",
        "## 旧baselineの設計制約（再検証資料・現行実装入力ではない）",
        "以下は旧baselineの基本設計に存在した制約を、再検証資料として記録する。現行要求・設計・実装を拘束しない。",
        "新要求のPO凍結・設計再降下後に、必要な制約だけを別途選択し、正本・manifest・baseline・独立レビューへ束縛する。",
        "上流戦略正本の保護方式は現行設計では未選択であり、DB/API/DDL方式をここから継承しない。",
    }
    missing_claude = sorted(marker for marker in required_claude_markers if marker not in claude_text)
    if missing_claude:
        faults.append(f"CLAUDEの設計入口が旧baseline再検証・現行未拘束境界を保持しない={missing_claude}")
    prohibited_claude_markers = {
        "要件定義〜L3 と L2 画面設計の開発入口は",
        "**L6 のスライスは 4 点一致**",
        "強制実装は S1 側の文書が正本",
        "その後の条件付き実装候補は`src/helix/`のDU-01〜12",
        "文書ペア（HELIX 式・片肺禁止）3 層:",
        "- 戦略層は strategy-loop-requirements／strategy-learning-contract ↔ strategy-loop-design／",
        "DDL・状態遷移・evidence 型・WF 契約の正準は docs/L3-system-requirements/canonical/s0-contract_v0.1.md。",
        "契約 JSON 正本は9本（BR/FR/SR/NFR/AC/TC/CMP/DU contracts＋L6 implementation-units）。",
        "旧設計基準の契約正本は下記9本。",
        "**第 9 正本 implementation-units.json は手編集の confirmed 正本**",
        "## 実装時の設計制約（基本設計 §1・§4 の要点)",
        "第 3 層は文書ペア（⑤↔⑥）＋コードペア（モジュール↔pytest）の二重:",
        "du-contracts の `apis[].ut` が\nテストファイル対応",
        "各 S0 更新の完了条件 =",
        "**DDD 規律**: ドメイン語彙は glossary が正本",
        "実装開始時に pytest ジョブと「CMP↔テストファイル対応」のペアゲートを CI に追加する",
        "上流戦略正本は DB で保護する:",
    }
    present_prohibited = sorted(marker for marker in prohibited_claude_markers if marker in claude_text)
    if present_prohibited:
        faults.append(f"CLAUDEの設計入口に旧方式の現在形命令が残る={present_prohibited}")
    agents_path = REPO_ROOT / "AGENTS.md"
    agents_text = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
    required_agents_markers = {
        "旧baselineのDDL・状態遷移・evidence型は再検証資料であり、現行設計・実装入力ではない。",
        "旧baselineの上流戦略層の要件・契約と12 schemaは再検証資料であり、現要求・設計・実装入力ではない。",
        "旧baselineの契約 JSON 群は9本（BR/FR/SR/NFR/AC/TC/CMP/DU contracts＋L6 implementation-units）。",
    }
    missing_agents = sorted(marker for marker in required_agents_markers if marker not in agents_text)
    if missing_agents:
        faults.append(f"AGENTSの設計入口が旧baseline再検証・現行未拘束境界を保持しない={missing_agents}")
    prohibited_agents_markers = {
        "DDL・状態遷移・evidence 型の正準は docs/L3-system-requirements/canonical/s0-contract_v0.1.md。",
        "上流戦略層の正本は docs/L3-system-requirements/canonical/strategy/ の要件・契約 ＋",
        "契約 JSON 正本は9本（BR/FR/SR/NFR/AC/TC/CMP/DU contracts＋L6 implementation-units）。",
    }
    present_agents = sorted(marker for marker in prohibited_agents_markers if marker in agents_text)
    if present_agents:
        faults.append(f"AGENTSの設計入口に旧方式の現在形命令が残る={present_agents}")
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
        declared_req = {ref for ref in _trace(br, contract=True)[1] if ref.startswith("REQ-")}
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
        for contract_id in sorted(ref for ref in req_down if ref.startswith(("FR-", "SR-", "NFR-"))):
            contract = contracts.get(contract_id)
            if contract is None:
                faults.append(f"{req_id}: contract orphan {contract_id}")
            elif req_id not in _trace(contract, contract=True)[0]:
                faults.append(f"{req_id}->{contract_id}: contract upstream missing REQ")

    for contract_id, contract in sorted(contracts.items()):
        req_roots = sorted(ref for ref in _trace(contract, contract=True)[0] if ref.startswith("REQ-"))
        deferred = contract.get("admission_status") == "deferred"
        resume = contract.get("resume_conditions")
        if not req_roots and not (deferred and isinstance(resume, list) and resume):
            faults.append(f"{contract_id}: stable REQ root又は再開条件付きdeferredがない")
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
    acceptance = {str(item["id"]): item for item in _items(ctx.acc) if isinstance(item.get("id"), str)}
    faults: list[str] = []
    inclusive_phase_targets: set[str] = set()
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
            inclusive_phase_targets.add(target)
        elif ac_phase != fr_phase:
            faults.append(f"{target}({fr_phase})->{ac_id}({ac_phase}): phase mismatch")
    for target in sorted(inclusive_phase_targets):
        faults.append(f"{target}: 包含phase {frs[target].get('slice')} を実装phaseに使えない")
    for test in _items(ctx.tcc):
        test_id = str(test.get("id", "?"))
        test_phase = test.get("slice")
        for ac_id in test.get("ac", []):
            acceptance_case = acceptance.get(str(ac_id))
            target = acceptance_case.get("target") if isinstance(acceptance_case, dict) else None
            if not isinstance(target, str) or target not in frs:
                continue
            fr_phase = frs[target].get("slice")
            if isinstance(fr_phase, str) and not fr_phase.endswith("+") and test_phase != fr_phase:
                faults.append(f"{target}({fr_phase})->{test_id}({test_phase}): phase mismatch")
    return faults


def semantic_dimension_faults(ctx: Ctx) -> list[str]:
    """各要求・受入層が実装判断に必要な意味軸を直接又は型付きで持つか検査する。"""
    required = {
        "BR": {
            "actor",
            "value",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "completion_evidence",
        },
        "BRM": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "REQ": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "FR": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "SR": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "NFR": {
            "actor",
            "beneficiaries",
            "value",
            "scope_in",
            "scope_out",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "MR": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
        "FN": {
            "actor",
            "beneficiaries",
            "value",
            "workflow",
            "scope_in",
            "scope_out",
            "prohibitions",
            "human_judgement",
            "side_effects",
            "evidence",
            "phase",
        },
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
        "MR": [
            item
            for path in sorted(MR_DIR.glob("*.json"))
            if path.name != "index.json"
            for item in _items(load(path))
        ],
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
            if event.get("event_type") == "approval_requested" and event.get("subject_id") not in terminal
        }
    )


def refinement_faults(data: dict[str, Any], discovery: dict[str, Any]) -> list[str]:
    """refinement recordの意味閉包・digest・承認束縛を検査する。"""
    faults: list[str] = [
        f"refinement schema: {fault}"
        for fault in schema_check(load(REFINEMENT_SCHEMA), data)
    ]
    if data.get("schema_version") != "marketing-harness-requirements-refinement.v1":
        faults.append("refinement schema_version が不正")
    if data.get("authority") != "canonical":
        faults.append("refinement authority がcanonicalでない")
    records = data.get("records")
    if not isinstance(records, list):
        return faults + ["refinement records が配列でない"]
    subject_ids = {
        str(record.get("subject_id"))
        for record in records
        if isinstance(record, dict) and isinstance(record.get("subject_id"), str)
    }
    delivery_sequence = {
        "MEDIA-POC-SCRUM-RELEASE": (1, 1, set()),
        "WORDPRESS-CONTENT-OPERATIONS-RELEASE": (1, 1, set()),
        "WORDPRESS-PLATFORM-MAINTENANCE-RELEASE": (
            1,
            2,
            {"WORDPRESS-CONTENT-OPERATIONS-RELEASE"},
        ),
        "WORDPRESS-SECURITY-MAINTENANCE-RELEASE": (
            1,
            2,
            {"WORDPRESS-CONTENT-OPERATIONS-RELEASE"},
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
            3,
            4,
            {"AGENT-NEO-SITE-BUILD-RELEASE"},
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
        if (
            not isinstance(source_ids, list)
            or not source_ids
            or any(item not in events for item in source_ids)
        ):
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
        polarities = (
            {item.get("polarity") for item in acceptance if isinstance(item, dict)}
            if isinstance(acceptance, list)
            else set()
        )
        if polarities != {"positive", "negative", "boundary"}:
            faults.append(f"{label}: positive/negative/boundary acceptanceが揃っていない")
        pending = record.get("pending_resolution")
        lifecycle = record.get("lifecycle_status")
        if lifecycle in {"specified", "approved", "frozen"} and pending != []:
            faults.append(f"{label}: {lifecycle}にpending_resolutionを残せない")
        registration = record.get("registration_bindings", [])
        design_later = record.get("design_later", [])
        if not isinstance(registration, list) or not isinstance(design_later, list):
            faults.append(f"{label}: registration/design routingが配列でない")
        elif set(registration) & set(design_later):
            faults.append(f"{label}: registrationとdesign-laterが重複")
        if lifecycle == "superseded":
            replacements = record.get("superseded_by_subject_ids")
            if pending != [] or not isinstance(replacements, list) or not replacements:
                faults.append(f"{label}: superseded境界又は置換先がない")
            elif any(subject not in subject_ids for subject in replacements):
                faults.append(f"{label}: superseded置換先が未知")
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
    faults.extend(implementation_obligation_faults(data, require_complete=False))
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
        if lifecycle in {"rejected", "superseded"}:
            continue
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


def _implementation_obligations(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """要求freezeとは分離し、実装開始前に閉じる登録・設計obligationを型付きで導出する。"""
    obligations: dict[str, dict[str, str]] = {}
    records = data.get("records", []) if isinstance(data, dict) else []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict) or record.get("lifecycle_status") in {"rejected", "superseded"}:
            continue
        subject = str(record.get("subject_id", "?"))
        for field, kind in (("registration_bindings", "registration"), ("design_later", "design")):
            values = record.get(field, [])
            for index, statement in enumerate(values if isinstance(values, list) else [], start=1):
                if not isinstance(statement, str):
                    continue
                token = f"{subject}\x1f{kind}\x1f{index}\x1f{statement}"
                obligation_id = "OBL-" + hashlib.sha256(token.encode()).hexdigest()[:16].upper()
                obligations[obligation_id] = {
                    "kind": kind,
                    "subject_id": subject,
                    "statement": statement,
                }
    return obligations


def _obligation_target_digest(path: Path, locator: str, obligation_id: str | None = None) -> str | None:
    """JSON Pointer又は明示clause markerだけをstable node identityとして解決する。"""
    if path.suffix == ".json" and locator.startswith("/"):
        try:
            node: Any = json.loads(path.read_text(encoding="utf-8"))
            for raw_part in locator[1:].split("/"):
                part = raw_part.replace("~1", "/").replace("~0", "~")
                if isinstance(node, list):
                    node = node[int(part)]
                elif isinstance(node, dict):
                    node = node[part]
                else:
                    return None
            if obligation_id is not None and (
                not isinstance(node, dict) or obligation_id not in node.get("obligation_ids", [])
            ):
                return None
            return _digest(node)
        except KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError:
            return None
    if not re.fullmatch(r"CL-[A-Z0-9-]+", locator):
        return None
    text = path.read_text(encoding="utf-8")
    marker_patterns = (
        (rf"<!--\s*clause-id:\s*{re.escape(locator)}\s*-->",)
        if path.suffix in {".md", ".html"}
        else (rf"--\s*clause-id:\s*{re.escape(locator)}(?:\s|$)",)
    )
    matches = [match for pattern in marker_patterns for match in re.finditer(pattern, text)]
    if len(matches) != 1:
        return None
    start = matches[0].start()
    next_markers = [
        match.start()
        for pattern in (
            (r"<!--\s*clause-id:\s*CL-[A-Z0-9-]+\s*-->",)
            if path.suffix in {".md", ".html"}
            else (r"--\s*clause-id:\s*CL-[A-Z0-9-]+(?:\s|$)",)
        )
        for match in re.finditer(pattern, text[start + 1 :])
    ]
    end = start + 1 + min(next_markers) if next_markers else len(text)
    clause = text[start:end]
    if obligation_id is not None:
        obligation_marker = rf"(?:<!--|--)\s*obligation-ids:\s*[^\n]*\b{re.escape(obligation_id)}\b"
        if re.search(obligation_marker, clause) is None:
            return None
    return "sha256:" + hashlib.sha256(clause.encode()).hexdigest()


def implementation_obligation_faults(
    data: dict[str, Any],
    allowed_artifact_ids: set[str] | None = None,
    review_digest: str | None = None,
    *,
    require_complete: bool = True,
) -> list[str]:
    expected = _implementation_obligations(data)
    fulfilled = data.get("implementation_obligation_fulfillments")
    if not isinstance(fulfilled, list):
        return ["implementation obligation fulfillment台帳が配列でない"]
    faults: list[str] = []
    seen: set[str] = set()
    for row in fulfilled:
        if not isinstance(row, dict):
            faults.append("implementation obligation fulfillment行がobjectでない")
            continue
        obligation_id = str(row.get("obligation_id", "?"))
        if obligation_id in seen:
            faults.append(f"{obligation_id}: fulfillment重複")
        seen.add(obligation_id)
        obligation = expected.get(obligation_id)
        if obligation is None:
            faults.append(f"{obligation_id}: 未知又はstale obligation")
            continue
        if row.get("kind") != obligation["kind"] or row.get("subject_id") != obligation["subject_id"]:
            faults.append(f"{obligation_id}: kind/subject binding不一致")
        refs = row.get("target_refs")
        if not isinstance(refs, list) or not refs:
            faults.append(f"{obligation_id}: target receipt/evidence参照がない")
        elif allowed_artifact_ids is not None:
            malformed = sorted(str(ref) for ref in refs if "#" not in str(ref))
            if malformed:
                faults.append(f"{obligation_id}: target参照にartifact#clause/rowがない={malformed}")
            artifact_refs = {str(ref).split("#", 1)[0] for ref in refs}
            unknown = sorted(artifact_refs - allowed_artifact_ids)
            if unknown:
                faults.append(f"{obligation_id}: target artifactがadmission外={unknown}")
            manifest = load(MANIFEST)
            manifest_by_id = {
                str(item.get("artifact_id")): item
                for item in manifest.get("items", [])
                if isinstance(item, dict)
            }
            evidence_parts: list[dict[str, str]] = []
            for ref in map(str, refs):
                if "#" not in ref:
                    continue
                artifact_id, clause_id = ref.split("#", 1)
                item = manifest_by_id.get(artifact_id)
                path = REPO_ROOT / str(item.get("canonical_path")) if isinstance(item, dict) else None
                if not clause_id or path is None or not path.is_file():
                    faults.append(f"{obligation_id}: target clause/rowが実在しない={ref}")
                    continue
                node_digest = _obligation_target_digest(path, clause_id, obligation_id)
                if node_digest is None:
                    faults.append(f"{obligation_id}: target clause/rowが実在しない={ref}")
                    continue
                evidence_parts.append(
                    {
                        "ref": ref,
                        "content_digest": node_digest,
                    }
                )
            expected_evidence = _digest(evidence_parts)
            if row.get("evidence_digest") != expected_evidence:
                faults.append(f"{obligation_id}: target実体evidence digest不一致")
            expected_receipt = _digest(
                {
                    "obligation_id": obligation_id,
                    "kind": obligation["kind"],
                    "subject_id": obligation["subject_id"],
                    "target_refs": refs,
                    "evidence_digest": expected_evidence,
                }
            )
            if row.get("receipt_digest") != expected_receipt:
                faults.append(f"{obligation_id}: fulfillment receipt digest不一致")
            if review_digest is not None and row.get("review_digest") != review_digest:
                faults.append(f"{obligation_id}: independent review digest不一致")
    missing = sorted(set(expected) - seen)
    if require_complete and missing:
        faults.append(f"implementation obligation未充足={missing}")
    return faults


def semantic_closure_faults(ctx: Ctx, refinements: dict[str, Any] | None = None) -> list[str]:
    """要求承認・authority cutoverの双方を止める意味レベル違反の完全集合。"""
    refinement_data = refinements
    if refinement_data is None:
        refinement_data = json.loads(REFINEMENTS.read_text(encoding="utf-8"))
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
        + legacy_media_trace_faults()
        + trace_semantic_responsibility_faults(ctx)
        + requirement_descent_admission_faults(ctx)
        + vps_ui_requirement_descent_faults(ctx)
        + human_judgement_descent_faults(ctx)
        + nfr_requirement_authority_faults(ctx)
        + strategy_test_authority_faults(ctx)
        + provider_dependency_semantic_faults()
        + provider_neutral_execution_policy_faults(refinement_data)
        + legacy_requirement_consumer_faults()
        + legacy_requirement_meaning_inventory_faults(ctx, refinement_data)
        + req_authority_normalization_policy_faults(ctx, refinement_data)
        + legacy_strategy_quality_meaning_inventory_faults(ctx, refinement_data)
        + nfr_business_authority_policy_faults(ctx, refinement_data)
        + legacy_mr_meaning_inventory_faults(refinement_data)
        + legacy_fn_meaning_inventory_faults(ctx, refinement_data)
        + legacy_ac_meaning_inventory_faults(ctx, refinement_data)
        + legacy_tc_meaning_inventory_faults(ctx, refinement_data)
        + legacy_phase_fault_disposition_faults(ctx, refinement_data)
        + legacy_trace_fault_policy_faults(ctx, refinement_data)
        + legacy_test_authority_disposition_faults(ctx, refinement_data)
    )


def approval_admission_faults(
    ctx: Ctx, data: dict[str, Any], refinements: dict[str, Any] | None = None
) -> list[str]:
    active = active_approval_requests(data)
    if not active:
        return []
    semantic = semantic_closure_faults(ctx, refinements)
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
    """要求authority承認と、その後の設計・実装admissionを分離して検査する。"""
    authorized = policy.get("implementation_authorized") is True
    status = policy.get("requirements_baseline_status")
    if status == "revising":
        return [] if not authorized else ["requirements revising中にimplementationを許可できない"]
    faults: list[str] = []
    meaning_inventory = refinements.get("legacy_requirement_meaning_inventory", {})
    if not isinstance(meaning_inventory, dict) or meaning_inventory.get("cutover_blocked") is True:
        faults.append("旧BR/REQ/FR意味inventoryがcutoverを直接停止している")
    strategy_quality_inventory = refinements.get("legacy_strategy_quality_meaning_inventory", {})
    if (
        not isinstance(strategy_quality_inventory, dict)
        or strategy_quality_inventory.get("cutover_blocked") is True
    ):
        faults.append("旧SR/NFR意味inventoryがcutoverを直接停止している")
    mr_inventory = refinements.get("legacy_mr_meaning_inventory", {})
    if not isinstance(mr_inventory, dict) or mr_inventory.get("cutover_blocked") is True:
        faults.append("旧MR意味inventoryがcutoverを直接停止している")
    fn_inventory = refinements.get("legacy_fn_meaning_inventory", {})
    if not isinstance(fn_inventory, dict) or fn_inventory.get("cutover_blocked") is True:
        faults.append("旧FN意味inventoryがcutoverを直接停止している")
    ac_inventory = refinements.get("legacy_ac_meaning_inventory", {})
    if not isinstance(ac_inventory, dict) or ac_inventory.get("cutover_blocked") is True:
        faults.append("旧AC意味inventoryがcutoverを直接停止している")
    tc_inventory = refinements.get("legacy_tc_meaning_inventory", {})
    if not isinstance(tc_inventory, dict) or tc_inventory.get("cutover_blocked") is True:
        faults.append("旧TC意味inventoryがcutoverを直接停止している")
    if status != "approved":
        faults.append("requirements authority切替にはbaseline status=approvedが必要")
    semantic = semantic_closure_faults(ctx, refinements)
    if semantic:
        faults.append(f"semantic closure未成立={len(semantic)}")
    objective = objective_completion_audit_faults(ctx, refinements)
    if objective:
        faults.append(f"objective completion未成立={objective}")
    objective_rows = refinements.get("objective_completion_audit", [])
    if not isinstance(objective_rows, list) or any(
        not isinstance(row, dict) or row.get("status") != "proven" for row in objective_rows
    ):
        faults.append("全objectiveがprovenでない")
    provider_bindings = refinements.get("provider_policy_bindings")
    if not isinstance(provider_bindings, dict) or provider_bindings.get("status") != "ratified":
        faults.append("provider execution policyがPO receipt付きratifiedでない")
    legacy_test_cutover = legacy_test_authority_cutover_faults(ctx, refinements)
    if legacy_test_cutover:
        faults.append(f"legacy test authority未決={legacy_test_cutover}")
    refinement = refinement_faults(refinements, discovery)
    if refinement:
        faults.append(f"refinement validation未成立={len(refinement)}")
    records = refinements.get("records", []) if isinstance(refinements, dict) else []
    if not isinstance(records, list) or not records:
        faults.append("cutover対象refinementがない")
    elif any(
        not isinstance(record, dict)
        or (
            record.get("lifecycle_status") not in {"rejected", "superseded"}
            and (record.get("lifecycle_status") != "frozen" or not isinstance(record.get("approval"), dict))
        )
        for record in records
    ):
        faults.append("active refinementがPO receipt付きfrozenでない")
    if active_approval_requests(discovery):
        faults.append("未決のapproval requestが残っている")
    if not authorized:
        return faults
    admission = policy.get("implementation_admission")
    declared_requirement_ids: set[str] = set()
    declared_design_ids: set[str] = set()
    review_digest: str | None = None
    if not isinstance(admission, dict):
        faults.append("requirements承認後の設計・実装admissionがない")
    else:
        if admission.get("status") != "approved":
            faults.append("設計・実装admissionがapprovedでない")
        receipt = admission.get("po_receipt")
        if admission.get("authority") != "PO" or not isinstance(receipt, dict):
            faults.append("設計・実装admissionにPO receiptがない")
        elif (
            receipt.get("authority") != "PO"
            or receipt.get("approver_principal") != "po"
            or not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("target_commit", "")))
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(receipt.get("subject_digest", "")))
            or not isinstance(receipt.get("approved_at"), str)
        ):
            faults.append("設計・実装admissionのPO receipt主体・commit・digestが不正")
        requirement_ids = admission.get("requirements_authority_artifact_ids")
        design_ids = admission.get("design_artifact_ids")
        if not isinstance(requirement_ids, list) or not requirement_ids:
            faults.append("設計・実装admissionに新要求authority artifactがない")
        else:
            declared_requirement_ids = {str(item) for item in requirement_ids}
            if len(declared_requirement_ids) != len(requirement_ids):
                faults.append("新要求authority artifact IDが重複する")
        if not isinstance(design_ids, list) or not design_ids:
            faults.append("設計・実装admissionに新L2-L6成果物集合がない")
        else:
            declared_design_ids = {str(item) for item in design_ids}
            if len(declared_design_ids) != len(design_ids):
                faults.append("新L2-L6 artifact IDが重複する")
        review_ref = admission.get("independent_go_review")
        if not isinstance(review_ref, dict):
            faults.append("設計・実装admissionに独立Go reviewがない")
        else:
            review_digest = _digest(review_ref)
    manifest = load(MANIFEST)
    manifest_items = [item for item in manifest.get("items", []) if isinstance(item, dict)]
    manifest_by_id = {str(item.get("artifact_id")): item for item in manifest_items}
    manifest_policy = manifest.get("applicability_policy", {})
    if (
        manifest_policy.get("requirements_baseline_status") != "approved"
        or manifest_policy.get("implementation_input") is not True
    ):
        faults.append("manifestが要求承認後の設計・実装入力へ切替済みでない")
    current_inputs = {
        str(item.get("layer")): item
        for item in manifest_items
        if item.get("applicability_status") == "current" and item.get("implementation_input") is True
    }
    missing_layers = sorted({"L2", "L3", "L4", "L5", "L6"} - set(current_inputs))
    if missing_layers:
        faults.append(f"新設計・検証・実装入力がV-pair層を被覆しない={missing_layers}")
    current_input_ids = {
        str(item.get("artifact_id"))
        for item in manifest_items
        if item.get("applicability_status") == "current"
        and item.get("implementation_input") is True
        and item.get("layer") in {"L1", "L2", "L3", "L4", "L5", "L6"}
    }
    declared_ids = declared_requirement_ids | declared_design_ids
    faults.extend(implementation_obligation_faults(refinements, declared_ids, review_digest))
    unknown_declared = sorted(declared_ids - set(manifest_by_id))
    if unknown_declared:
        faults.append(f"設計・実装admissionが未知artifactを参照={unknown_declared}")
    for artifact_id in sorted(declared_ids & set(manifest_by_id)):
        item = manifest_by_id[artifact_id]
        if item.get("applicability_status") != "current" or item.get("implementation_input") is not True:
            faults.append(f"{artifact_id}: admission artifactがcurrent implementation inputでない")
    if any(
        manifest_by_id[item].get("layer") not in {"L1", "L3"}
        for item in declared_requirement_ids & set(manifest_by_id)
    ):
        faults.append("requirements_authority_artifact_idsにL1/L3以外が混入する")
    if {str(manifest_by_id[item].get("layer")) for item in declared_design_ids & set(manifest_by_id)} != {
        "L2",
        "L3",
        "L4",
        "L5",
        "L6",
    }:
        faults.append("design_artifact_idsがL2-L6をexactly被覆しない")
    if declared_ids != current_input_ids:
        faults.append("admission artifact IDsがmanifest current implementation inputsとexact一致しない")
    selected_artifacts = {
        artifact_id: {
            "canonical_path": str(manifest_by_id[artifact_id].get("canonical_path")),
            "content_digest": "sha256:"
            + hashlib.sha256(
                (REPO_ROOT / str(manifest_by_id[artifact_id].get("canonical_path"))).read_bytes()
            ).hexdigest(),
        }
        for artifact_id in sorted(declared_ids & set(manifest_by_id))
        if (REPO_ROOT / str(manifest_by_id[artifact_id].get("canonical_path"))).is_file()
    }
    try:
        commit_result = git("rev-parse", "HEAD")
        tree_result = git("rev-parse", "HEAD^{tree}")
        if commit_result.returncode != 0 or tree_result.returncode != 0:
            raise OSError("git rev-parse failed")
        head_commit = commit_result.stdout.strip()
        head_tree = tree_result.stdout.strip()
    except OSError:
        head_commit = ""
        head_tree = ""
        faults.append("admission対象Git commit/treeを解決できない")
    expected_subject_digest = _digest({"target_commit": head_commit, "artifacts": selected_artifacts})
    if isinstance(receipt, dict) and (
        receipt.get("target_commit") != head_commit
        or receipt.get("subject_digest") != expected_subject_digest
    ):
        faults.append("PO receiptが対象commitとartifact content digestへ束縛されていない")
    if isinstance(review_ref, dict):
        review_path = review_ref.get("review_path")
        review_file = REPO_ROOT / str(review_path)
        if (
            not isinstance(review_path, str)
            or not review_path.startswith("docs/00-authority/reviews/")
            or not review_file.is_file()
        ):
            faults.append("独立Go review evidence artifactが実在しない")
        else:
            review = json.loads(review_file.read_text(encoding="utf-8"))
            reviewed = review.get("reviewed_artifact_digests", {})
            selected_paths = {row["canonical_path"] for row in selected_artifacts.values()}
            reviewed_content_mismatch = not isinstance(reviewed, dict) or any(
                reviewed.get(row["canonical_path"]) != row["content_digest"].removeprefix("sha256:")[:16]
                for row in selected_artifacts.values()
            )
            if (
                review.get("review_id") != review_ref.get("review_id")
                or review.get("verdict") != "Go"
                or review.get("separation_status") != "ci_attested"
                or review.get("reviewer_principal")
                in {
                    None,
                    "po",
                    receipt.get("approver_principal") if isinstance(receipt, dict) else None,
                }
                or review.get("reviewer_principal") == review.get("author_principal")
                or review.get("target_commit") != head_commit
                or review.get("target_tree") != head_tree
                or not isinstance(reviewed, dict)
                or not selected_paths <= set(reviewed)
                or reviewed_content_mismatch
            ):
                faults.append("独立Go reviewの主体分離・verdict・commit・tree・artifact被覆が不正")
    return faults


def legacy_fault_stage_audit_faults(
    ctx: Ctx, policy: dict[str, Any], refinements: dict[str, Any]
) -> list[str]:
    """旧raw faultを消したことにせず、未cutover中の隔離集合へexact固定する。"""
    raw_faults = {
        "G-REQ-SEMANTIC-DRIFT": sorted(
            compatibility_drift_faults(ctx) + req_compatibility_drift_faults(ctx)
        ),
        "G-REQ-TRACE-BIDIR": sorted(bidirectional_trace_faults(ctx)),
        "G-REQ-TRACE-LAYERS": sorted(layered_trace_faults(ctx)),
        "G-REQ-TRACE-IMPLEMENTATION": sorted(implementation_trace_faults(ctx)),
        "G-REQ-TRACE-FUNCTION-LEDGER": sorted(functional_ledger_trace_faults(ctx)),
        "G-REQ-PHASE-ALIGNMENT": sorted(phase_alignment_faults(ctx)),
        "G-REQ-SEMANTIC-DIMENSIONS": sorted(semantic_dimension_faults(ctx)),
        "G-REQ-LEGACY-MEDIA-TRACE": sorted(legacy_media_trace_faults()),
        "G-REQ-OBSOLETE-RUNTIME-ROUTES": sorted(obsolete_runtime_route_faults()),
        "G-REQ-WP-RESPONSIBILITY-BOUNDARY": sorted(wordpress_responsibility_boundary_faults()),
        "G-REQ-NOTIFICATION-PURPOSE-BOUNDARY": sorted(notification_purpose_boundary_faults(ctx)),
        "G-REQ-MEDIA-ROUTE-SEMANTICS": sorted(media_route_semantic_faults()),
        "G-REQ-CONNECTOR-PRIORITY-SEMANTICS": sorted(connector_priority_semantic_faults()),
        "G-REQ-L2-REVALIDATION-SEMANTICS": sorted(l2_revalidation_semantic_faults(ctx)),
        "G-REQ-VPS-CREDENTIAL-BOUNDARY": sorted(vps_credential_boundary_faults()),
        "G-REQ-MEDIA-ADMISSION": sorted(media_requirement_admission_faults()),
        "G-REQ-TRACE-SEMANTIC-RESPONSIBILITY": sorted(trace_semantic_responsibility_faults(ctx)),
        "G-REQ-DESCENT-ADMISSION": sorted(requirement_descent_admission_faults(ctx)),
        "G-REQ-VPS-UI-DESCENT": sorted(vps_ui_requirement_descent_faults(ctx)),
        "G-REQ-HUMAN-JUDGEMENT-DESCENT": sorted(human_judgement_descent_faults(ctx)),
        "G-REQ-NFR-AUTHORITY": sorted(nfr_requirement_authority_faults(ctx)),
        "G-REQ-PROVIDER-DEPENDENCY": sorted(provider_dependency_semantic_faults()),
    }
    expected = {
        "G-REQ-SEMANTIC-DRIFT": (147, "sha256:15db9d058dd208d7af8fbc8a9cb9c9a466363115d6648da3df76aaea3bd3a8d4"),
        "G-REQ-TRACE-BIDIR": (71, "sha256:dcbca3b0f9d3570926f05f916a20dd02af0f4799d37d14a11e6b9f2d0792abe9"),
        "G-REQ-TRACE-LAYERS": (38, "sha256:776af023976f771b2c816caff2e474ae6cd1775c341e48b544300273ff2d19d2"),
        "G-REQ-TRACE-IMPLEMENTATION": (14, "sha256:b29d559d5542d3ce85b60201a9fe79ba4acd0159399c6f1ad426ee1c43138566"),
        "G-REQ-TRACE-FUNCTION-LEDGER": (1, "sha256:5750e4e3a80af7b926724dc5ac54fe010976b91dc2c40fc9738c410c684f287f"),
        "G-REQ-PHASE-ALIGNMENT": (30, "sha256:49e139a6ee3bf1e3d9b04c7908df8ccc9f44cff94b691e96b6cd222b034ae925"),
        "G-REQ-SEMANTIC-DIMENSIONS": (4517, "sha256:15f295fd33df219d007296bac7b35f085b9c78cdcac40bbb78fa89834b67678c"),
        "G-REQ-LEGACY-MEDIA-TRACE": (48, "sha256:abab4ce97cafc914ee3220aced29fb2f42eca7f3efb82e7b65c4b154a8041d9e"),
        "G-REQ-OBSOLETE-RUNTIME-ROUTES": (4, "sha256:73dee67b2acef2835fc2fd73ed4d6e082847c9a139570b398dffa11af06749a2"),
        "G-REQ-WP-RESPONSIBILITY-BOUNDARY": (10, "sha256:f1b139f8605ec8ed3559978c9c5ff1579f334c1d3c850e93635af3997dd8331e"),
        "G-REQ-NOTIFICATION-PURPOSE-BOUNDARY": (4, "sha256:b556b29f6ecb41549c6238c04e7828df98779071b5d8d16078442359b22000e2"),
        "G-REQ-MEDIA-ROUTE-SEMANTICS": (4, "sha256:bc3298eb78237d84161449d1289be635638135f08338c653043470d852211c19"),
        "G-REQ-CONNECTOR-PRIORITY-SEMANTICS": (2, "sha256:f3d62c459ecb20dc27d9dee59fbf9c06f8f2328607e8df208590e250fd876cd9"),
        "G-REQ-L2-REVALIDATION-SEMANTICS": (5, "sha256:9afd68cd81285117f7af90e398594372b7d92107fb9fa51e3a087872cb648aca"),
        "G-REQ-VPS-CREDENTIAL-BOUNDARY": (2, "sha256:d52041bdb1ad5416f42ecccff13681cdb405fb8f906e9d1da6bbfac0f892b98f"),
        "G-REQ-MEDIA-ADMISSION": (324, "sha256:55e6c870962cb89307c048d85cb0cf9fa5d1a995c34e521c5ddc8ff16bef32b9"),
        "G-REQ-TRACE-SEMANTIC-RESPONSIBILITY": (3, "sha256:26085ec0618c73421310e139440f701a57c7365ac7dfaaebedb32c5eb8e8a2e4"),
        "G-REQ-DESCENT-ADMISSION": (36, "sha256:48fd9ec9b75aa35c33394c23f4dad60e55d7d6ceec81097c39a63df589b8a750"),
        "G-REQ-VPS-UI-DESCENT": (1, "sha256:a6b0eee609c3c014dce9279594c75940f5a7bca15db79cedd63e74ff88007837"),
        "G-REQ-HUMAN-JUDGEMENT-DESCENT": (21, "sha256:86575e521e57e02715df1dfd2c48f9172a6f4981e7462941fe845908b0204dd1"),
        "G-REQ-NFR-AUTHORITY": (13, "sha256:30335e4e9d762c6b8995a2deef908e8532a18bc8fea8c9fc3559fed8ca1e2841"),
        "G-REQ-PROVIDER-DEPENDENCY": (3, "sha256:a5dff856aca3a4fb9e72eaf784f68a129f721ad349b322259d65ee95ea20d1a6"),
    }
    faults: list[str] = []
    source_digests = {
        name: _digest(getattr(ctx, name))
        for name in ("br", "req", "requirements", "fn", "brc", "frc", "src", "nfc", "acc", "tcc", "cmpc", "duc")
    }
    source_roots = (
        REPO_ROOT / "docs/00-authority/adr",
        REFINEMENTS,
        REPO_ROOT / "docs/L0-charter/canonical",
        REPO_ROOT / "docs/L1-business-requirements/canonical",
        REPO_ROOT / "docs/L2-prototypes",
        REPO_ROOT / "docs/L3-system-requirements/canonical",
        REPO_ROOT / "docs/L4-basic-design/canonical",
        REPO_ROOT / "docs/L5-detailed-design/canonical",
    )
    source_paths = sorted(
        {
            path
            for root in source_roots
            for path in ([root] if root.is_file() else root.rglob("*"))
            if path.is_file()
        }
    )
    expanded_source_digests = {
        str(path.relative_to(REPO_ROOT)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }
    revising = (
        policy.get("requirements_baseline_status") == "revising"
        and policy.get("implementation_authorized") is False
    )
    cutover_complete = (
        policy.get("requirements_baseline_status") == "approved"
        and policy.get("implementation_authorized") is True
    )
    if not revising and not cutover_complete:
        faults.append("legacy raw fault stageがrevising quarantine又はapproved cutover completeでない")
    if revising:
        for gate_id, values in raw_faults.items():
            count, digest = expected[gate_id]
            if len(values) != count or _digest(values) != digest:
                faults.append(f"{gate_id}: known quarantined fault集合が増減又は意味反転")
        if _digest(source_digests) != "sha256:ed8691d9069dca0e391996994c834f36f49beef33cf8dc9aad7440623d7ecbb9":
            faults.append("legacy contract source artifact集合digestがstale")
        if _digest(expanded_source_digests) != "sha256:5656e6e85c7f92222335c5a064d0fad5f0e88c7f57ba07a6f3c8ad2033067262":
            faults.append("legacy ADR/L2/refinement raw source snapshot digestがstale")
    elif cutover_complete and any(raw_faults.values()):
        faults.append("approved cutoverでは旧raw faultをquarantineせずzero closureが必要")
    authority_faults: list[str] = []
    if revising:
        authority_faults = (
            legacy_trace_fault_policy_faults(ctx, refinements)
            + legacy_phase_fault_disposition_faults(ctx, refinements)
            + fr_slice_authority_alignment_policy_faults(ctx, refinements)
            + test_id_authority_alignment_policy_faults(ctx, refinements)
            + legacy_media_trace_fault_policy_faults(refinements)
            + resolved_subject_authority_coverage_audit_faults(refinements)
            + ratification_dependency_audit_faults(refinements)
            + wordpress_maintenance_boundaries_policy_faults(refinements)
            + fr16_notification_boundary_policy_faults(refinements)
            + discord_notification_rejection_policy_faults(refinements)
            + media_poc_scrum_release_policy_faults(refinements)
            + official_api_route_authority_policy_faults(refinements)
            + external_browser_automation_route_policy_faults(refinements)
            + vps_credential_security_boundary_policy_faults(refinements)
            + vps_ui_primary_interface_policy_faults(refinements)
            + nfr_business_authority_policy_faults(ctx, refinements)
            + provider_neutral_execution_policy_faults(refinements)
            + design_not_started_faults(ctx)
        )
    elif cutover_complete:
        authority_faults.extend(legacy_requirement_consumer_faults())
    if authority_faults:
        faults.append("legacy raw faultのdisposition/inventory authorityが不健全")
    if revising:
        if refinements.get("semantic_coverage_policy") != _expected_semantic_coverage_policy():
            faults.append("semantic dimension隔離先policyがcode正本と不一致")
        if refinements.get("contract_semantic_descent_policy") != _expected_contract_semantic_descent_policy():
            faults.append("semantic dimension descent policyがcode正本と不一致")
        inventory_faults = {
            "legacy_requirement_meaning_inventory": legacy_requirement_meaning_inventory_faults(ctx, refinements),
            "legacy_strategy_quality_meaning_inventory": legacy_strategy_quality_meaning_inventory_faults(ctx, refinements),
            "legacy_mr_meaning_inventory": legacy_mr_meaning_inventory_faults(refinements),
            "legacy_fn_meaning_inventory": legacy_fn_meaning_inventory_faults(ctx, refinements),
            "legacy_ac_meaning_inventory": legacy_ac_meaning_inventory_faults(ctx, refinements),
            "legacy_tc_meaning_inventory": legacy_tc_meaning_inventory_faults(ctx, refinements),
        }
        expected_pending = {
            "legacy_requirement_meaning_inventory": ["旧BR/REQ/FR意味分類候補がPO未承認 remaining=0"],
            "legacy_strategy_quality_meaning_inventory": ["旧SR/NFR意味分類候補がPO未承認 remaining=0"],
            "legacy_mr_meaning_inventory": ["旧MR意味分類候補がPO未承認 remaining=0"],
            "legacy_fn_meaning_inventory": ["旧FN意味分類候補がPO未承認 remaining=0"],
            "legacy_ac_meaning_inventory": ["旧AC意味分類候補がPO未承認 remaining=0"],
            "legacy_tc_meaning_inventory": ["旧TC意味分類候補がPO未承認 remaining=0"],
        }
        for inventory_id, actual in inventory_faults.items():
            if actual != expected_pending[inventory_id]:
                faults.append(f"{inventory_id}: semantic dimension inventoryがpending-only exactでない")
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
        "legacy_fault_stage_audit": legacy_fault_stage_audit_faults(ctx, policy, refinements),
        "req_authority_normalization": req_authority_normalization_policy_faults(ctx, refinements),
        "nfr_business_authority_policy": nfr_business_authority_policy_faults(ctx, refinements),
        "direct_trace": bidirectional_trace_faults(ctx),
        "layered_trace": layered_trace_faults(ctx),
        "implementation_trace": implementation_trace_faults(ctx),
        "functional_ledger_trace": functional_ledger_trace_faults(ctx),
        "phase_alignment": phase_alignment_faults(ctx),
        "fr_slice_authority_alignment_policy": fr_slice_authority_alignment_policy_faults(ctx, refinements),
        "test_id_authority_alignment_policy": test_id_authority_alignment_policy_faults(ctx, refinements),
        "l0_north_star_authority_normalization_policy": l0_north_star_authority_normalization_policy_faults(refinements),
        "strategy_requirement_admission_policy": strategy_requirement_admission_policy_faults(ctx, refinements),
        "agent_neo_helix_redefinition_policy": agent_neo_helix_redefinition_policy_faults(refinements),
        "agent_neo_site_build_release_policy": agent_neo_site_build_release_policy_faults(refinements),
        "agent_neo_product_evolution_release_policy": agent_neo_product_evolution_release_policy_faults(refinements),
        "fr16_notification_boundary_policy": fr16_notification_boundary_policy_faults(refinements),
        "discord_notification_rejection_policy": discord_notification_rejection_policy_faults(refinements),
        "vps_ui_primary_interface_policy": vps_ui_primary_interface_policy_faults(refinements),
        "external_browser_automation_route_policy": external_browser_automation_route_policy_faults(refinements),
        "official_api_route_authority_policy": official_api_route_authority_policy_faults(refinements),
        "genai_execution_route_policy": genai_execution_route_policy_faults(refinements),
        "automated_publishing_admission_policy": automated_publishing_admission_policy_faults(refinements),
        "content_quality_gate_learning_policy": content_quality_gate_learning_policy_faults(refinements),
        "content_risk_classification_policy": content_risk_classification_policy_faults(refinements),
        "research_led_content_growth_policy": research_led_content_growth_policy_faults(refinements),
        "discord_community_marketing_route_policy": discord_community_marketing_route_policy_faults(refinements),
        "wordpress_maintenance_boundaries_policy": wordpress_maintenance_boundaries_policy_faults(refinements),
        "resolved_subject_authority_coverage_audit": resolved_subject_authority_coverage_audit_faults(refinements),
        "ratification_dependency_audit": ratification_dependency_audit_faults(refinements),
        "vps_ui_inbox_lifecycle_policy": vps_ui_inbox_lifecycle_policy_faults(refinements),
        "vps_credential_security_boundary_policy": vps_credential_security_boundary_policy_faults(refinements),
        "media_poc_scrum_release_policy": media_poc_scrum_release_policy_faults(refinements),
        "semantic_dimensions": semantic_dimension_faults(ctx),
        "obsolete_runtime_routes": obsolete_runtime_route_faults(),
        "wordpress_responsibility_boundary": wordpress_responsibility_boundary_faults(),
        "notification_purpose_boundary": notification_purpose_boundary_faults(ctx),
        "media_route_semantics": media_route_semantic_faults(),
        "connector_priority_semantics": connector_priority_semantic_faults(),
        "l2_revalidation_semantics": l2_revalidation_semantic_faults(ctx),
        "vps_credential_boundary": vps_credential_boundary_faults(),
        "media_requirement_admission": media_requirement_admission_faults(),
        "legacy_media_trace": legacy_media_trace_faults(),
        "legacy_media_trace_fault_policy": legacy_media_trace_fault_policy_faults(refinements),
        "legacy_media_inventory": legacy_media_inventory_faults(refinements),
        "trace_semantic_responsibility": trace_semantic_responsibility_faults(ctx),
        "requirement_descent_admission": requirement_descent_admission_faults(ctx),
        "vps_ui_requirement_descent": vps_ui_requirement_descent_faults(ctx),
        "human_judgement_descent": human_judgement_descent_faults(ctx),
        "nfr_requirement_authority": nfr_requirement_authority_faults(ctx),
        "strategy_test_authority": strategy_test_authority_faults(ctx),
        "provider_dependency_semantics": provider_dependency_semantic_faults(),
        "provider_neutral_execution_policy": provider_neutral_execution_policy_faults(refinements),
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
        "legacy_requirement_meaning_inventory": legacy_requirement_meaning_inventory_faults(ctx, refinements),
        "legacy_strategy_quality_meaning_inventory": legacy_strategy_quality_meaning_inventory_faults(
            ctx, refinements
        ),
        "legacy_mr_meaning_inventory": legacy_mr_meaning_inventory_faults(refinements),
        "legacy_fn_meaning_inventory": legacy_fn_meaning_inventory_faults(ctx, refinements),
        "legacy_ac_meaning_inventory": legacy_ac_meaning_inventory_faults(ctx, refinements),
        "legacy_tc_meaning_inventory": legacy_tc_meaning_inventory_faults(ctx, refinements),
        "legacy_media_br_dispositions": legacy_media_br_disposition_faults(refinements),
        "legacy_fr_dispositions": legacy_fr_disposition_faults(ctx, refinements),
        "legacy_derived_contracts": legacy_derived_contract_faults(ctx, refinements),
        "legacy_phase_fault_dispositions": legacy_phase_fault_disposition_faults(ctx, refinements),
        "legacy_trace_fault_policy": legacy_trace_fault_policy_faults(ctx, refinements),
        "legacy_test_authority_disposition": legacy_test_authority_disposition_faults(ctx, refinements),
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


LEGACY_RAW_FAULT_REPORT_KEYS = frozenset(
    {
        "semantic_drift",
        "direct_trace",
        "layered_trace",
        "implementation_trace",
        "functional_ledger_trace",
        "phase_alignment",
        "semantic_dimensions",
        "legacy_media_trace",
        "obsolete_runtime_routes",
        "wordpress_responsibility_boundary",
        "notification_purpose_boundary",
        "media_route_semantics",
        "connector_priority_semantics",
        "l2_revalidation_semantics",
        "vps_credential_boundary",
        "media_requirement_admission",
        "trace_semantic_responsibility",
        "requirement_descent_admission",
        "vps_ui_requirement_descent",
        "human_judgement_descent",
        "nfr_requirement_authority",
        "provider_dependency_semantics",
    }
)


def actionable_engine_faults(
    state: dict[str, Any], faults: dict[str, list[str]]
) -> dict[str, list[str]]:
    """Return current No-Go faults, excluding only audited legacy quarantine rows."""
    policy = state["policy"]
    legacy_quarantine_active = (
        not faults["legacy_fault_stage_audit"]
        and policy.get("requirements_baseline_status") == "revising"
        and policy.get("implementation_authorized") is False
    )
    return {
        name: values
        for name, values in faults.items()
        if values and (not legacy_quarantine_active or name not in LEGACY_RAW_FAULT_REPORT_KEYS)
    }


def run(ctx: Ctx) -> None:
    state, faults = engine_report(ctx)
    projection = state["projection"]
    authority = faults["authority"]
    compatibility_authority = faults["compatibility_authority"]
    projection_errors = faults["projection"]
    drift = faults["semantic_drift"]
    legacy_fault_stage_audit = faults["legacy_fault_stage_audit"]
    legacy_fault_quarantined = (
        not legacy_fault_stage_audit
        and state["policy"].get("requirements_baseline_status") == "revising"
        and state["policy"].get("implementation_authorized") is False
    )
    trace = faults["direct_trace"]
    layered_trace = faults["layered_trace"]
    implementation_trace = faults["implementation_trace"]
    functional_ledger_trace = faults["functional_ledger_trace"]
    phase_alignment = faults["phase_alignment"]
    fr_slice_authority_alignment_policy = faults["fr_slice_authority_alignment_policy"]
    test_id_authority_alignment_policy = faults["test_id_authority_alignment_policy"]
    l0_north_star_authority_normalization_policy = faults["l0_north_star_authority_normalization_policy"]
    strategy_requirement_admission_policy = faults["strategy_requirement_admission_policy"]
    agent_neo_helix_redefinition_policy = faults["agent_neo_helix_redefinition_policy"]
    agent_neo_site_build_release_policy = faults["agent_neo_site_build_release_policy"]
    agent_neo_product_evolution_release_policy = faults["agent_neo_product_evolution_release_policy"]
    fr16_notification_boundary_policy = faults["fr16_notification_boundary_policy"]
    discord_notification_rejection_policy = faults["discord_notification_rejection_policy"]
    vps_ui_primary_interface_policy = faults["vps_ui_primary_interface_policy"]
    external_browser_automation_route_policy = faults["external_browser_automation_route_policy"]
    official_api_route_authority_policy = faults["official_api_route_authority_policy"]
    genai_execution_route_policy = faults["genai_execution_route_policy"]
    automated_publishing_admission_policy = faults["automated_publishing_admission_policy"]
    content_quality_gate_learning_policy = faults["content_quality_gate_learning_policy"]
    content_risk_classification_policy = faults["content_risk_classification_policy"]
    research_led_content_growth_policy = faults["research_led_content_growth_policy"]
    discord_community_marketing_route_policy = faults["discord_community_marketing_route_policy"]
    wordpress_maintenance_boundaries_policy = faults["wordpress_maintenance_boundaries_policy"]
    resolved_subject_authority_coverage_audit = faults["resolved_subject_authority_coverage_audit"]
    ratification_dependency_audit = faults["ratification_dependency_audit"]
    vps_ui_inbox_lifecycle_policy = faults["vps_ui_inbox_lifecycle_policy"]
    vps_credential_security_boundary_policy = faults["vps_credential_security_boundary_policy"]
    media_poc_scrum_release_policy = faults["media_poc_scrum_release_policy"]
    semantic_dimensions = faults["semantic_dimensions"]
    obsolete_runtime_routes = faults["obsolete_runtime_routes"]
    wordpress_responsibility_boundary = faults["wordpress_responsibility_boundary"]
    notification_purpose_boundary = faults["notification_purpose_boundary"]
    media_route_semantics = faults["media_route_semantics"]
    connector_priority_semantics = faults["connector_priority_semantics"]
    l2_revalidation_semantics = faults["l2_revalidation_semantics"]
    vps_credential_boundary = faults["vps_credential_boundary"]
    media_requirement_admission = faults["media_requirement_admission"]
    legacy_media_trace = faults["legacy_media_trace"]
    legacy_media_trace_fault_policy = faults["legacy_media_trace_fault_policy"]
    legacy_media_inventory = faults["legacy_media_inventory"]
    trace_semantic_responsibility = faults["trace_semantic_responsibility"]
    requirement_descent_admission = faults["requirement_descent_admission"]
    vps_ui_requirement_descent = faults["vps_ui_requirement_descent"]
    human_judgement_descent = faults["human_judgement_descent"]
    nfr_requirement_authority = faults["nfr_requirement_authority"]
    strategy_test_authority = faults["strategy_test_authority"]
    provider_dependency_semantics = faults["provider_dependency_semantics"]
    provider_neutral_execution_policy = faults["provider_neutral_execution_policy"]
    legacy_requirement_consumers = faults["legacy_requirement_consumers"]
    req_authority_normalization = faults["req_authority_normalization"]
    nfr_business_authority_policy = faults["nfr_business_authority_policy"]
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
    legacy_requirement_meaning_inventory = faults["legacy_requirement_meaning_inventory"]
    legacy_strategy_quality_meaning_inventory = faults["legacy_strategy_quality_meaning_inventory"]
    legacy_mr_meaning_inventory = faults["legacy_mr_meaning_inventory"]
    legacy_fn_meaning_inventory = faults["legacy_fn_meaning_inventory"]
    legacy_ac_meaning_inventory = faults["legacy_ac_meaning_inventory"]
    legacy_tc_meaning_inventory = faults["legacy_tc_meaning_inventory"]
    legacy_media_br_dispositions = faults["legacy_media_br_dispositions"]
    legacy_fr_dispositions = faults["legacy_fr_dispositions"]
    legacy_derived_contracts = faults["legacy_derived_contracts"]
    legacy_phase_fault_dispositions = faults["legacy_phase_fault_dispositions"]
    legacy_trace_fault_policy = faults["legacy_trace_fault_policy"]
    legacy_test_authority_disposition = faults["legacy_test_authority_disposition"]
    authority_revision_candidate = faults["authority_revision_candidate"]
    objective_completion_audit = faults["objective_completion_audit"]
    refinement = faults["refinement"]
    refinement_coverage = faults["refinement_coverage"]
    open_refinements = faults["open_refinements"]
    admission = faults["approval_admission"]
    cutover = faults["authority_cutover"]
    gate(
        "G-REQ-AUTHORITY",
        not authority,
        f"9正本・非二重化・revising・frozen cutover境界を検査 (違反={authority})",
    )
    gate(
        "G-REQ-COMPATIBILITY-AUTHORITY",
        not compatibility_authority,
        f"旧requirements viewを非権威・read-onlyに固定 (違反={compatibility_authority})",
    )
    gate(
        "G-REQ-IR-PROJECTION",
        not projection_errors,
        f"決定的IR projection {len(projection['records'])}件＋HELIX-HARNESS v2 candidate 5 shard (違反={projection_errors})",
    )
    gate(
        "G-REQ-LEGACY-FAULT-STAGE-AUDIT",
        not legacy_fault_stage_audit,
        f"旧raw fault集合をsource/disposition/stageへexact固定して隔離 (違反={legacy_fault_stage_audit})",
    )
    gate("G-REQ-SEMANTIC-DRIFT", not drift or legacy_fault_quarantined, f"同一IDの意味差分を拒否又は既知旧faultとして隔離 (違反={drift[:5]})")
    gate("G-REQ-TRACE-BIDIR", not trace or legacy_fault_quarantined, f"BR→FR/SR意味traceを双方向検査又は既知旧faultとして隔離 (違反={trace[:5]})")
    gate(
        "G-REQ-TRACE-LAYERS",
        not layered_trace or legacy_fault_quarantined,
        f"BR→REQ→FR/SR/NFR隣接traceを双方向検査又は既知旧faultとして隔離 (違反={layered_trace[:5]})",
    )
    gate(
        "G-REQ-TRACE-IMPLEMENTATION",
        not implementation_trace or legacy_fault_quarantined,
        f"DU→AC/TCC参照を現行IDへ解決又は既知旧faultとして隔離 (違反={implementation_trace[:5]})",
    )
    gate(
        "G-REQ-TRACE-FUNCTION-LEDGER",
        not functional_ledger_trace or legacy_fault_quarantined,
        f"REQ→FN ledger参照を双方向検査又は既知旧faultとして隔離 (違反={functional_ledger_trace[:5]})",
    )
    gate(
        "G-REQ-PHASE-ALIGNMENT",
        not phase_alignment or legacy_fault_quarantined,
        f"FR→FN→ACの導入phaseを厳密照合又は既知旧faultとして隔離 (違反={phase_alignment[:5]})",
    )
    gate(
        "G-REQ-SEMANTIC-DIMENSIONS",
        not semantic_dimensions or legacy_fault_quarantined,
        f"BR/BRM/REQ/FR/SR/NFR/MR/FN/AC/TCの意味軸閉包を検査又は既知旧faultとして隔離 (違反={semantic_dimensions[:5]})",
    )
    gate(
        "G-REQ-OBSOLETE-RUNTIME-ROUTES",
        not obsolete_runtime_routes or legacy_fault_quarantined,
        f"VPS UI/inbox採用後のWSL cron・Discord初期固定を拒否 (違反={obsolete_runtime_routes[:5]})",
    )
    gate(
        "G-REQ-WP-RESPONSIBILITY-BOUNDARY",
        not wordpress_responsibility_boundary or legacy_fault_quarantined,
        f"WPコンテンツ運用と通常／security保守の混在を拒否 (違反={wordpress_responsibility_boundary[:5]})",
    )
    gate(
        "G-REQ-NOTIFICATION-PURPOSE-BOUNDARY",
        not notification_purpose_boundary or legacy_fault_quarantined,
        f"承認通知・運用通知・媒体投稿・開発PR通知のtransport再利用を拒否 (違反={notification_purpose_boundary[:5]})",
    )
    gate(
        "G-REQ-MEDIA-ROUTE-SEMANTICS",
        not media_route_semantics or legacy_fault_quarantined,
        f"媒体BRの許可／禁止／保留routeとMR connection/actionsを意味照合 (違反={media_route_semantics[:5]})",
    )
    gate(
        "G-REQ-CONNECTOR-PRIORITY-SEMANTICS",
        not connector_priority_semantics or legacy_fault_quarantined,
        f"BR／FR／ADR／L4／L5のconnector優先順を一意に要求 (違反={connector_priority_semantics})",
    )
    gate(
        "G-REQ-L2-REVALIDATION-SEMANTICS",
        not l2_revalidation_semantics or legacy_fault_quarantined,
        f"旧L2 prototypeの通知class・decision・trace・write・profile scopeを再検証 (違反={l2_revalidation_semantics[:5]})",
    )
    gate(
        "G-REQ-VPS-CREDENTIAL-BOUNDARY",
        not vps_credential_boundary or legacy_fault_quarantined,
        f"VPS credentialのat-rest保護・runtime注入・scope分離を一意に要求 (違反={vps_credential_boundary})",
    )
    gate(
        "G-REQ-MEDIA-ADMISSION",
        not media_requirement_admission or legacy_fault_quarantined,
        f"全MRのcapability status・execution mode・principal・effect・policy・検証降下を要求 (違反={media_requirement_admission[:5]})",
    )
    gate(
        "G-REQ-LEGACY-MEDIA-TRACE",
        not legacy_media_trace or legacy_fault_quarantined,
        f"通常BR trace圏外の旧BR-M 70件↔MR 54件を検査又は既知旧faultとして隔離 (違反={legacy_media_trace[:5]})",
    )
    gate(
        "G-REQ-LEGACY-MEDIA-TRACE-DISPOSITION",
        not legacy_media_trace_fault_policy,
        f"旧BR-M↔MR片方向edge集合をdigest固定しcapability revisionへの意味再降下へ分類 (違反={legacy_media_trace_fault_policy})",
    )
    gate(
        "G-REQ-LEGACY-MEDIA-INVENTORY",
        not legacy_media_inventory,
        f"旧MR全件を安全側deferred inventoryへ収載し旧経路の黙示採用を拒否 (違反={legacy_media_inventory})",
    )
    gate(
        "G-REQ-TRACE-SEMANTIC-RESPONSIBILITY",
        not trace_semantic_responsibility or legacy_fault_quarantined,
        f"BR／REQの責務・状態・証跡が下位FRのbehavior／ACへ実際に降下したか検査 (違反={trace_semantic_responsibility})",
    )
    gate(
        "G-REQ-DESCENT-ADMISSION",
        not requirement_descent_admission or legacy_fault_quarantined,
        f"要求定義だけのFR／SRをFN／CMP／ACへ降下又は再開条件付きdeferredへ閉じる (違反={requirement_descent_admission[:5]})",
    )
    gate(
        "G-REQ-VPS-UI-DESCENT",
        not vps_ui_requirement_descent or legacy_fault_quarantined,
        f"VPS UI主入口の状態・証跡・KPI閲覧要求と旧API-only契約を意味照合 (違反={vps_ui_requirement_descent})",
    )
    gate(
        "G-REQ-HUMAN-JUDGEMENT-DESCENT",
        not human_judgement_descent or legacy_fault_quarantined,
        f"上位BRのPO判断をFR／SR／AC／evidenceまで追跡し機械処理・agent審査による代替を拒否 (違反={human_judgement_descent})",
    )
    gate(
        "G-REQ-NFR-AUTHORITY",
        not nfr_requirement_authority or legacy_fault_quarantined,
        f"全NFRをstable REQ／BR根拠又は再開条件付きdeferredへ束縛 (違反={nfr_requirement_authority[:5]})",
    )
    gate(
        "G-REQ-STRATEGY-TEST-AUTHORITY",
        not strategy_test_authority,
        f"confirmed ACが参照するstrategy STCをPO receipt付き正本又は明示deferredへ束縛 (違反={strategy_test_authority})",
    )
    gate(
        "G-REQ-PROVIDER-DEPENDENCY",
        not provider_dependency_semantics or legacy_fault_quarantined,
        f"provider-neutral要求と旧Claude／Codex／consumer Web UI必須経路を意味照合 (違反={provider_dependency_semantics})",
    )
    gate(
        "G-REQ-PROVIDER-EXECUTION-POLICY",
        not provider_neutral_execution_policy,
        f"API/MCP優先・Playwright確認限定・consumer UI無人禁止・provider/credential/license/evidence束縛をtyped検査 (違反={provider_neutral_execution_policy})",
    )
    gate(
        "G-REQ-LEGACY-CONSUMER-ISOLATION",
        not legacy_requirement_consumers,
        f"旧REQ／requirements viewを上位・設計・検証の規範入力から隔離 (違反={legacy_requirement_consumers})",
    )
    gate(
        "G-REQ-AUTHORITY-NORMALIZATION",
        not req_authority_normalization,
        f"REQ55意味inventoryと15 ID・19 field差分を単一candidate正本の未批准cutover境界へ束縛 (違反={req_authority_normalization})",
    )
    gate(
        "G-REQ-NFR-BUSINESS-AUTHORITY-POLICY",
        not nfr_business_authority_policy,
        f"NFR11意味inventoryをstable root・actor/scope・phase・measurement authorityの未批准overlayへ束縛 (違反={nfr_business_authority_policy})",
    )
    gate(
        "G-REQ-DESIGN-NOT-STARTED",
        not design_not_started,
        f"要求freeze前のL2〜L6を再検証資料に限定し設計・実装入力化を拒否 (違反={design_not_started[:5]})",
    )
    gate(
        "G-REQ-SCOPE-ASSIGNMENT",
        not scope_assignment,
        f"旧864 IDをlegacy限定とし新refinementへ初期／後続／deferred scopeを一意に割当 (違反={scope_assignment})",
    )
    gate(
        "G-REQ-DECISION-PACKETS",
        not decision_packets,
        f"PO確認packetが全refinement subjectを順序付きexactly onceで覆い一括承認を禁止 (違反={decision_packets})",
    )
    gate(
        "G-REQ-CANDIDATE-BINDINGS",
        not candidate_requirement_bindings,
        f"候補PRCを実在refinement meaning ownerへexactlyに束縛 (違反={candidate_requirement_bindings})",
    )
    gate(
        "G-REQ-L0-CLAUSE-DISPOSITION",
        not l0_clause_dispositions,
        f"旧L0の価値／手段をclause単位で維持・置換・deferredへ明示移送 (違反={l0_clause_dispositions})",
    )
    gate(
        "G-REQ-CRITICAL-RESPONSIBILITY-DISPOSITION",
        not critical_responsibility_dispositions,
        f"旧通知・承認・自動運用・UI責務をVPS UI／inbox／activationへ明示移送 (違反={critical_responsibility_dispositions})",
    )
    gate(
        "G-REQ-SEMANTIC-DESCENT-POLICY",
        not semantic_descent_policy,
        f"BRからTCまで12意味軸を直接宣言又はdigest束縛継承し設計降下を要求freezeまで拒否 (違反={semantic_descent_policy})",
    )
    gate(
        "G-REQ-LEGACY-NFR-DISPOSITION",
        not legacy_nfr_dispositions,
        f"旧NFR-1〜11をstable業務根拠付き再降下・置換又は再開条件付きdeferredへ分類 (違反={legacy_nfr_dispositions})",
    )
    gate(
        "G-REQ-ORPHAN-REQUIREMENT-DISPOSITION",
        not orphan_requirement_groups,
        f"stable root又はFN/CMP/AC降下を欠く旧FR 11件・SR 19件を再降下・置換・deferredへ全件分類 (違反={orphan_requirement_groups})",
    )
    gate(
        "G-REQ-LEGACY-REQ-DISPOSITION",
        not legacy_req_dispositions,
        f"旧REQ 55件をMD/JSON二重意味から分離しID別に再降下・置換・deferredへ全件分類 (違反={legacy_req_dispositions})",
    )
    gate(
        "G-REQ-LEGACY-BR-DISPOSITION",
        not legacy_br_dispositions,
        f"旧BR 41件の事業価値を保持し旧runtime/provider/approval/notification手段をID別に再降下・置換 (違反={legacy_br_dispositions})",
    )
    gate(
        "G-REQ-LEGACY-MEANING-INVENTORY",
        not legacy_requirement_meaning_inventory,
        f"旧BR/REQ/FR全139 IDの意味snapshotと高risk価値・安全・人間判断の移送を固定し未分類cutoverを拒否 (違反={legacy_requirement_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-SR-NFR-MEANING-INVENTORY",
        not legacy_strategy_quality_meaning_inventory,
        f"旧SR19/NFR11全30 IDの意味snapshotと価値・安全・人間判断・旧方式非継承を固定し未分類cutoverを拒否 (違反={legacy_strategy_quality_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-MR-MEANING-INVENTORY",
        not legacy_mr_meaning_inventory,
        f"旧MR全54 IDの意味snapshotと媒体別価値・route禁止・人間判断・再開条件を固定し未分類cutoverを拒否 (違反={legacy_mr_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-FN-MEANING-INVENTORY",
        not legacy_fn_meaning_inventory,
        f"旧FN全61 IDを親semantic digest・FN固有作用・owner・evidence・旧phase処置へ束縛し未分類cutoverを拒否 (違反={legacy_fn_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-AC-MEANING-INVENTORY",
        not legacy_ac_meaning_inventory,
        f"旧AC全252 IDを親要求/FN semantic digest・oracle delta・principal/scope/HJ/effect/evidence/polarity/旧phaseへ束縛し未分類cutoverを拒否 (違反={legacy_ac_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-TC-MEANING-INVENTORY",
        not legacy_tc_meaning_inventory,
        f"旧TC全258 IDを親AC semantic digest・test oracle・critical group・旧phase/alias処置へ束縛し未分類cutoverを拒否 (違反={legacy_tc_meaning_inventory})",
    )
    gate(
        "G-REQ-LEGACY-MEDIA-BR-DISPOSITION",
        not legacy_media_br_dispositions,
        f"旧媒体BR 70件をID別semantic digest・個別処置・媒体policyへ束縛し媒体名だけの実行許可を拒否 (違反={legacy_media_br_dispositions})",
    )
    gate(
        "G-REQ-LEGACY-FR-DISPOSITION",
        not legacy_fr_dispositions,
        f"旧FR 43件を現要求へID別に再降下・置換・延期し旧runtime／provider／approval経路を拒否 (違反={legacy_fr_dispositions})",
    )
    gate(
        "G-REQ-LEGACY-DERIVED-CONTRACTS",
        not legacy_derived_contracts,
        f"旧FN 61／AC 252／TC 258を親要求の再降下までlegacy・未設計・非受入証拠へ固定 (違反={legacy_derived_contracts})",
    )
    gate(
        "G-REQ-L0-NORTH-STAR-AUTHORITY-NORMALIZATION-POLICY",
        not l0_north_star_authority_normalization_policy,
        f"旧L0 15 clauseをcharter実体・PRC・確定PO projection・新L0 cutoverへ束縛 (違反={l0_north_star_authority_normalization_policy})",
    )
    gate(
        "G-REQ-STRATEGY-REQUIREMENT-ADMISSION-POLICY",
        not strategy_requirement_admission_policy,
        f"旧SR19件をL0 north-star・意味inventory・research/risk・単一test authorityへ未批准のまま束縛 (違反={strategy_requirement_admission_policy})",
    )
    gate(
        "G-REQ-AGENT-NEO-HELIX-REDEFINITION-POLICY",
        not agent_neo_helix_redefinition_policy,
        f"AGENT NEO固定SHAについて記録済みの19観測・旧任意判断をread-only repo境界とPO未分類へ束縛 (違反={agent_neo_helix_redefinition_policy})",
    )
    gate(
        "G-REQ-AGENT-NEO-SITE-BUILD-RELEASE-POLICY",
        not agent_neo_site_build_release_policy,
        f"site-buildを親capability分類・WP三責務・対象site grantへ従属させ外部repo read-onlyを維持 (違反={agent_neo_site_build_release_policy})",
    )
    gate(
        "G-REQ-AGENT-NEO-PRODUCT-EVOLUTION-RELEASE-POLICY",
        not agent_neo_product_evolution_release_policy,
        f"product-evolutionを親capability・site-build完了へ従属させ要求cutoverと外部repo write権限を分離 (違反={agent_neo_product_evolution_release_policy})",
    )
    gate(
        "G-REQ-FR16-NOTIFICATION-BOUNDARY-POLICY",
        not fr16_notification_boundary_policy,
        f"安全停止先行・VPS UI inbox非権威・通知失敗時状態不変・旧Discord/ApprovalTransport非継承を固定 (違反={fr16_notification_boundary_policy})",
    )
    gate(
        "G-REQ-DISCORD-NOTIFICATION-REJECTION-POLICY",
        not discord_notification_rejection_policy,
        f"Discordをcommunity marketing専用に隔離し製品承認・運用・PR通知と旧ApprovalTransportへの復帰を拒否 (違反={discord_notification_rejection_policy})",
    )
    gate(
        "G-REQ-VPS-UI-PRIMARY-INTERFACE-POLICY",
        not vps_ui_primary_interface_policy,
        f"VPS Web UI＋inboxをhuman product entryとしread・notification state・decision・feedback authorityを分離 (違反={vps_ui_primary_interface_policy})",
    )
    gate(
        "G-REQ-EXTERNAL-BROWSER-AUTOMATION-ROUTE-POLICY",
        not external_browser_automation_route_policy,
        f"API/MCP優先・Playwright read確認・operation登録fallback・browser write既定禁止を分離 (違反={external_browser_automation_route_policy})",
    )
    gate(
        "G-REQ-OFFICIAL-API-ROUTE-AUTHORITY-POLICY",
        not official_api_route_authority_policy,
        f"公式route registryをaccount/operation/effect・freshness・terms・quota・credentialへ束縛 (違反={official_api_route_authority_policy})",
    )
    gate(
        "G-REQ-GENAI-EXECUTION-ROUTE-POLICY",
        not genai_execution_route_policy,
        f"生成routeをprovider-neutral登録へ束縛しconsumer UI無人操作・固定runtime・publish権威化を拒否 (違反={genai_execution_route_policy})",
    )
    gate(
        "G-REQ-AUTOMATED-PUBLISHING-ADMISSION-POLICY",
        not automated_publishing_admission_policy,
        f"初回scope activation後のgate合格自動運用・再生成・retry exhaustion inbox・明示再activationを検査 (違反={automated_publishing_admission_policy})",
    )
    gate(
        "G-REQ-CONTENT-QUALITY-GATE-LEARNING-POLICY",
        not content_quality_gate_learning_policy,
        f"content検査・人間確認前再生成・media-account scope・外部rule revision・strictness非弱化を検査 (違反={content_quality_gate_learning_policy})",
    )
    gate(
        "G-REQ-CONTENT-RISK-CLASSIFICATION-POLICY",
        not content_risk_classification_policy,
        f"claim risk/YMYL/unknown strictness/source freshness/HJ非代替をtyped検査 (違反={content_risk_classification_policy})",
    )
    gate(
        "G-REQ-RESEARCH-LED-CONTENT-GROWTH-POLICY",
        not research_led_content_growth_policy,
        f"research→仮説→媒体role→KPI観測→TLP学習とpaid超後期deferをtyped検査 (違反={research_led_content_growth_policy})",
    )
    gate(
        "G-REQ-DISCORD-COMMUNITY-MARKETING-ROUTE-POLICY",
        not discord_community_marketing_route_policy,
        f"Discord community marketingだけをBot/guild/channel/operationへ束縛し通知・承認・PR用途共有を拒否 (違反={discord_community_marketing_route_policy})",
    )
    gate(
        "G-REQ-VPS-CREDENTIAL-SECURITY-BOUNDARY-POLICY",
        not vps_credential_security_boundary_policy,
        f"VPS restart後停止・有人runtime再初期化・credential再認可・secret非永続化をtyped検査 (違反={vps_credential_security_boundary_policy})",
    )
    gate(
        "G-REQ-VPS-UI-INBOX-LIFECYCLE-POLICY",
        not vps_ui_inbox_lifecycle_policy,
        f"inboxをsource-derived lifecycle・非decision導線へ限定し失敗rollback・独自expiry・active purgeを拒否 (違反={vps_ui_inbox_lifecycle_policy})",
    )
    gate(
        "G-REQ-WORDPRESS-MAINTENANCE-BOUNDARIES-POLICY",
        not wordpress_maintenance_boundaries_policy,
        f"WordPress content/platform/security operationをexact routingしgrant・receipt・release横流用を拒否 (違反={wordpress_maintenance_boundaries_policy})",
    )
    gate(
        "G-REQ-RESOLVED-SUBJECT-AUTHORITY-COVERAGE-AUDIT",
        not resolved_subject_authority_coverage_audit,
        f"pending=[] recordを一意又は役割分離したpolicy/inventory/gateへexact対応付け (違反={resolved_subject_authority_coverage_audit})",
    )
    gate(
        "G-REQ-RATIFICATION-DEPENDENCY-AUDIT",
        not ratification_dependency_audit,
        f"未批准authorityをsemantic/core/operational-SCC/release-composite順に固定し部分ready・write権威化を拒否 (違反={ratification_dependency_audit})",
    )
    gate(
        "G-REQ-MEDIA-POC-SCRUM-RELEASE-POLICY",
        not media_poc_scrum_release_policy,
        f"媒体単位release・operation capability increment・PoC非権威・本番write個別grantを分離 (違反={media_poc_scrum_release_policy})",
    )
    gate(
        "G-REQ-TEST-ID-AUTHORITY-ALIGNMENT-POLICY",
        not test_id_authority_alignment_policy,
        f"旧TC 14 ID mappingとstrategy test ownerを分離しPO分類・candidate・cutoverへ束縛 (違反={test_id_authority_alignment_policy})",
    )
    gate(
        "G-REQ-FR-SLICE-AUTHORITY-ALIGNMENT-POLICY",
        not fr_slice_authority_alignment_policy,
        f"旧phase 30 edgeのimmutable snapshotをPO分類・candidate cutover・独立Goへ三段階で束縛 (違反={fr_slice_authority_alignment_policy})",
    )
    gate(
        "G-REQ-LEGACY-PHASE-DISPOSITION",
        not legacy_phase_fault_dispositions,
        f"旧FR→FN/AC phase逆転と包含phaseをedge別に責務分割・再降下へ固定 (違反={legacy_phase_fault_dispositions})",
    )
    gate(
        "G-REQ-LEGACY-TRACE-DISPOSITION",
        not legacy_trace_fault_policy,
        f"旧direct/layered/意味責務trace fault集合をdigest固定し種別別再降下・延期・edge廃止へ分類 (違反={legacy_trace_fault_policy})",
    )
    gate(
        "G-REQ-LEGACY-TEST-AUTHORITY-DISPOSITION",
        not legacy_test_authority_disposition,
        f"旧DU参照TC 14 IDの処遇とAC-SR二重台帳をPO cutover前のlegacy再検証資料へ固定 (違反={legacy_test_authority_disposition})",
    )
    gate(
        "G-REQ-AUTHORITY-REVISION-CANDIDATE",
        not authority_revision_candidate,
        f"新revision単一JSON正本を推奨案として保持しPO未決のまま旧ID書換え・cutover・設計開始を拒否 (違反={authority_revision_candidate})",
    )
    gate(
        "G-REQ-OBJECTIVE-COMPLETION-AUDIT",
        not objective_completion_audit,
        f"意味棚卸し・旧参照隔離・VPS UI/inbox・設計未着手・新正本freezeを目的別証拠で判定し未完の過大主張を拒否 (違反={objective_completion_audit})",
    )
    gate(
        "G-REQ-REFINEMENT",
        not refinement,
        f"refinement意味閉包・digest・受入・PO束縛を検査 (違反={refinement[:5]})",
    )
    gate(
        "G-REQ-REFINEMENT-COVERAGE",
        not refinement_coverage,
        f"全discovery候補を個別refinementへ対応 (違反={refinement_coverage[:5]})",
    )
    gate(
        "G-REQ-OPEN-REFINEMENTS",
        not open_refinements,
        f"全refinementのpending解消・PO receipt・frozenを要求 (違反={open_refinements[:5]})",
    )
    gate("G-REQ-APPROVAL-ADMISSION", not admission, f"意味閉包前の承認要求を拒否 (違反={admission})")
    gate("G-REQ-AUTHORITY-CUTOVER", not cutover, f"frozen要求だけを実装入力へ切替 (違反={cutover})")


if __name__ == "__main__":
    run(CTX)
