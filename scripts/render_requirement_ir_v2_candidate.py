#!/usr/bin/env python3
"""Generate the HELIX-HARNESS-shaped requirement IR candidate projection.

The upstream format uses a manifest and five stable-ID keyed JSON shards.  This
repository is still in ``requirements_baseline_status=revising`` and therefore
cannot claim the upstream ``authority=canonical``/``definition_status=frozen``
state.  The projection below keeps the upstream envelope and field vocabulary,
but explicitly marks every record as a candidate (or historical) and binds the
result to the local refinement registry.  It is generated data, never a second
source of requirement authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs/00-authority/development/requirement-refinements.json"
OUTPUT = ROOT / "docs/00-authority/development/requirements-ir"
REL_SOURCE = "docs/00-authority/development/requirement-refinements.json"
PARTITIONS = (
    "requirements",
    "system_contracts",
    "acceptance_cases",
    "system_tests",
    "refinement_contracts",
)


def _digest(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    return slug or "UNNAMED"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _join(value: Any) -> str:
    return " / ".join(_list(value))


def _kind(subject_id: str) -> str:
    upper = subject_id.upper()
    if any(word in upper for word in ("QUALITY", "RISK", "NFR", "CREDENTIAL", "AUTHENTICATION", "RATE-QUOTA")):
        return "non_functional"
    if any(word in upper for word in ("FR-", "INBOX", "ROUTE", "API", "PUBLISHING", "WORDPRESS")):
        return "functional"
    if any(word in upper for word in ("AGENT", "STRATEGY", "RESEARCH", "MEDIA", "L0-", "BUSINESS")):
        return "business"
    return "functional"


def _candidate_status(record: dict[str, Any]) -> tuple[str, str, str]:
    if record.get("lifecycle_status") == "superseded":
        return "historical_superseded", "superseded_history", "historical_refinement_registry"
    return "candidate_unratified", "unfrozen", "current_refinement_registry"


def _statement(dimensions: dict[str, Any]) -> str:
    """Keep every semantic dimension in a deterministic human-readable statement."""
    labels = (
        ("value", "value"),
        ("tasks", "tasks"),
        ("workflow", "workflow"),
        ("scope_in", "scope_in"),
        ("scope_out", "scope_out"),
        ("prohibitions", "prohibitions"),
        ("human_judgement", "human_judgement"),
        ("side_effects", "side_effects"),
        ("evidence", "evidence"),
        ("phase", "phase"),
    )
    lines: list[str] = []
    for key, label in labels:
        value = dimensions.get(key)
        rendered = value if isinstance(value, str) else _join(value)
        if rendered:
            lines.append(f"{label}: {rendered}")
    return "\n".join(lines)


def _source_pointer(refinement_id: str) -> str:
    return f"{REL_SOURCE}#/records/{refinement_id}"


def _acceptance_ids(subject: str) -> list[str]:
    slug = _slug(subject)
    return [f"MHH-AC-{slug}-{suffix}" for suffix in ("P", "N", "B")]


def _test_id(subject: str) -> str:
    return f"MHH-ST-{_slug(subject)}"


def _requirement_id(subject: str) -> str:
    return f"MHH-REQ-{_slug(subject)}"


def _contract_id(subject: str) -> str:
    return f"MHH-SC-{_slug(subject)}"


def _record_semantic_digest(record: dict[str, Any]) -> str:
    return _digest({key: value for key, value in record.items() if key != "semantic_digest"})


def build_candidate_ir() -> dict[str, Any]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("requirement refinement registry records must be an object list")
    ordered = sorted(records, key=lambda item: str(item.get("refinement_id", "")))

    requirements: dict[str, dict[str, Any]] = {}
    contracts: dict[str, dict[str, Any]] = {}
    acceptances: dict[str, dict[str, Any]] = {}
    tests: dict[str, dict[str, Any]] = {}
    refinements: dict[str, dict[str, Any]] = {}

    for source_record in ordered:
        refinement_id = source_record.get("refinement_id")
        subject_id = source_record.get("subject_id")
        dimensions = source_record.get("semantic_dimensions")
        acceptance_cases = source_record.get("acceptance_cases")
        if not all(isinstance(value, str) and value for value in (refinement_id, subject_id)):
            raise ValueError("every refinement must have a non-empty refinement_id and subject_id")
        if not isinstance(dimensions, dict) or not isinstance(acceptance_cases, list) or len(acceptance_cases) != 3:
            raise ValueError(f"{refinement_id}: exactly three typed acceptance cases are required")

        status, definition_status, evidence_origin = _candidate_status(source_record)
        req_id = _requirement_id(subject_id)
        contract_id = _contract_id(subject_id)
        test_id = _test_id(subject_id)
        acceptance_ids = _acceptance_ids(subject_id)
        text = _statement(dimensions)
        source_pointer = _source_pointer(refinement_id)
        source_digest = source_record.get("semantic_digest")
        if not isinstance(source_digest, str):
            raise ValueError(f"{refinement_id}: semantic_digest is required")
        pending = _list(source_record.get("pending_resolution"))
        if "PO receipt and requirements freeze remain pending" not in pending and status != "historical_superseded":
            pending.append("PO receipt and requirements freeze remain pending")
        if status == "historical_superseded":
            pending = ["historical refinement; no current design or implementation input"]

        requirement: dict[str, Any] = {
            "schema_version": "helix-requirement.v1",
            "requirement_id": req_id,
            "revision": int(source_record.get("revision", 1)),
            "kind": _kind(subject_id),
            "status": status,
            "definition_status": definition_status,
            "evidence_origin": evidence_origin,
            "statement": {"text": text, "semantic_digest": _digest(text)},
            "source": {
                "canonical_pointer": f"requirements-ir/requirements.json#/{req_id}",
                "migration_source_pointer": source_pointer,
                "authority_id": refinement_id,
            },
            "assertion_id": f"MHH-AS-{_slug(subject_id)}",
            "primary_system_contract_id": contract_id,
            "acceptance_ids": acceptance_ids,
            "system_test_id": test_id,
            "downstream_obligation": {
                "obligation_id": f"MHH-DOWNSTREAM-{_slug(subject_id)}",
                "owner_id": contract_id,
                "status": "pending_requirements_freeze",
                "route_issue_ids": [],
            },
            "actor_ids": _list(dimensions.get("actors")),
            "task_ids": _list(dimensions.get("tasks")),
            "surface_ids": _list(dimensions.get("scope_in")),
            "design_template_ids": [],
            "design_obligation_ids": [],
            "required_design_artifact_kinds": [],
            "pending_resolution": pending,
        }
        requirement["semantic_digest"] = _record_semantic_digest(requirement)
        requirements[req_id] = requirement

        contract: dict[str, Any] = {
            "schema_version": "helix-system-contract.v1",
            "system_contract_id": contract_id,
            "revision": int(source_record.get("revision", 1)),
            "status": status,
            "requirement_ids": [req_id],
            "behavior": f"requirements candidate only: {_join(dimensions.get('tasks'))}",
            "transition_contract": "candidate_unratified -> frozen only after individual PO receipt; no design or runtime transition is admitted",
            "failure_and_evidence": f"prohibitions: {_join(dimensions.get('prohibitions'))}; evidence: {_join(dimensions.get('evidence'))}",
            "acceptance_ids": acceptance_ids,
            "system_test_id": test_id,
        }
        contract["semantic_digest"] = _record_semantic_digest(contract)
        contracts[contract_id] = contract

        generated_acceptances: list[dict[str, Any]] = []
        for index, source_acceptance in enumerate(acceptance_cases):
            if not isinstance(source_acceptance, dict):
                raise ValueError(f"{refinement_id}: acceptance case must be an object")
            generated_id = acceptance_ids[index]
            polarity = source_acceptance.get("polarity")
            statement = source_acceptance.get("statement")
            if polarity not in {"positive", "negative", "boundary"} or not isinstance(statement, str) or not statement:
                raise ValueError(f"{refinement_id}: acceptance case polarity/statement invalid")
            acceptance: dict[str, Any] = {
                "schema_version": "helix-acceptance-case.v1",
                "acceptance_id": generated_id,
                "revision": int(source_record.get("revision", 1)),
                "status": status,
                "system_contract_id": contract_id,
                "polarity": polarity,
                "statement": statement,
                "system_test_id": test_id,
            }
            acceptance["semantic_digest"] = _record_semantic_digest(acceptance)
            acceptances[generated_id] = acceptance
            generated_acceptances.append(acceptance)

        test: dict[str, Any] = {
            "schema_version": "helix-system-test.v1",
            "system_test_id": test_id,
            "revision": int(source_record.get("revision", 1)),
            "status": "historical_superseded" if status == "historical_superseded" else "designed_not_implemented",
            "system_contract_id": contract_id,
            "acceptance_ids": acceptance_ids,
            "supporting_test_ids": [],
            "scenario": f"requirements meaning review for {subject_id}; no L2+ design or runtime execution",
            "required_evidence": _join(dimensions.get("evidence")) or "PO receipt, source digest, semantic review receipt",
            "negative_boundary": _join(dimensions.get("prohibitions")) or "unapproved or design-like input is rejected",
        }
        test["semantic_digest"] = _record_semantic_digest(test)
        tests[test_id] = test

        refinement: dict[str, Any] = {
            "schema_version": "helix-requirement-refinement.v1",
            "refinement_contract_id": refinement_id,
            "revision": int(source_record.get("revision", 1)),
            "lifecycle_status": source_record.get("lifecycle_status"),
            "primary_system_contract_id": contract_id,
            "related_system_contract_ids": [],
            "source": {
                "requirement_path": source_pointer,
                "requirement_digest": source_digest,
                "acceptance_path": f"{source_pointer}/acceptance_cases",
                "acceptance_digest": _digest(acceptance_cases),
            },
            "plan_id": "PLAN-REQUIREMENTS-FREEZE-PENDING",
            "responsibility_owner": subject_id,
            "contract_requirement": {
                "requirement_id": req_id,
                "source_projection": "local_refinement_registry",
                "statement": text,
                "acceptance_ids": acceptance_ids,
                "semantic_digest": source_digest,
            },
            "supporting_requirements": [],
            "acceptance_cases": [
                {
                    "acceptance_id": item["acceptance_id"],
                    "source_projection": "local_refinement_registry",
                    "requirement_ids": [req_id],
                    "polarity": item["polarity"],
                    "statement": item["statement"],
                    "semantic_digest": item["semantic_digest"],
                }
                for item in generated_acceptances
            ],
            "downstream_issue_ids": [],
            "acceptance_owners": [],
            "approval": None,
        }
        refinement["semantic_digest"] = _record_semantic_digest(refinement)
        refinements[refinement_id] = refinement

    shards = {
        "requirements": requirements,
        "system_contracts": contracts,
        "acceptance_cases": acceptances,
        "system_tests": tests,
        "refinement_contracts": refinements,
    }
    source_projection = [
        {
            "refinement_id": item.get("refinement_id"),
            "revision": item.get("revision"),
            "lifecycle_status": item.get("lifecycle_status"),
            "semantic_digest": item.get("semantic_digest"),
        }
        for item in ordered
    ]
    baseline_root_digest = _digest(
        {
            "source_path": REL_SOURCE,
            "source_file_digest": _file_digest(SOURCE),
            "source_projection": source_projection,
        }
    )
    shard_entries = [
        {
            "kind": kind,
            "path": f"requirements-ir/{kind}.json",
            "count": len(shards[kind]),
            "digest": _digest(shards[kind]),
        }
        for kind in PARTITIONS
    ]
    manifest_body = {
        "schema_version": "helix-requirement-ir.v2",
        "authority": "candidate_non_authoritative",
        "source_authority": "requirement_refinement_registry_projection",
        "partition": "stable_id_keyed_shards",
        "shards": shard_entries,
        "baseline_root_digest": baseline_root_digest,
    }
    manifest = {**manifest_body, "root_digest": _digest(manifest_body)}
    return {"manifest": manifest, "shards": shards}


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_candidate_ir() -> None:
    built = build_candidate_ir()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for kind, shard in built["shards"].items():
        (OUTPUT / f"{kind}.json").write_text(_json_text(shard), encoding="utf-8")
    (OUTPUT / "manifest.json").write_text(_json_text(built["manifest"]), encoding="utf-8")


def check_candidate_ir() -> list[str]:
    built = build_candidate_ir()
    faults: list[str] = []
    expected_paths = [OUTPUT / "manifest.json", *(OUTPUT / f"{kind}.json" for kind in PARTITIONS)]
    for path in expected_paths:
        if not path.is_file():
            faults.append(f"generated candidate IR missing: {path.relative_to(ROOT)}")
    if faults:
        return faults
    if json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8")) != built["manifest"]:
        faults.append("candidate IR manifest differs from deterministic projection")
    for kind, expected in built["shards"].items():
        actual = json.loads((OUTPUT / f"{kind}.json").read_text(encoding="utf-8"))
        if actual != expected:
            faults.append(f"candidate IR shard differs from deterministic projection: {kind}")
    return faults


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    if args.check:
        faults = check_candidate_ir()
        for fault in faults:
            print(f"FAIL: {fault}")
        return 1 if faults else 0
    write_candidate_ir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
