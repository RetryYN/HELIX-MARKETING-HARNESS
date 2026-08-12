"""前向きの要件発見台帳を検査する fail-close ゲート。

この台帳は既存 BR/REQ/FR/NFR/AC/TC 契約の代替ではない。coverage_start_commit
以降の発見過程だけを append-only に記録し、正本や製品 runtime への自動反映を禁止する。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.gates.common import (
    AC_CONTRACTS,
    BR_CONTRACTS,
    FR_CONTRACTS,
    NFR_CONTRACTS,
    REQ_LEDGER,
    ROOT,
    TC_CONTRACTS,
    Ctx,
    canonical_json_digest,
    gate,
    git,
    load,
    schema_check,
)

DISCOVERY_DIR = ROOT / "docs/00-authority/development"
LEDGER = DISCOVERY_DIR / "requirement-discovery-events.json"
SCHEMA = DISCOVERY_DIR / "requirement-discovery-event.schema.json"
EVENT_TYPES = {
    "candidate_recorded",
    "question_raised",
    "question_answered",
    "prototype_recorded",
    "observation_recorded",
    "specification_proposed",
    "approval_requested",
    "approval_decided",
    "withdrawn",
}
PAYLOAD_FIELDS: dict[str, set[str]] = {
    "candidate_recorded": {"title", "problem_statement", "value_hypothesis", "unresolved_questions"},
    "question_raised": {"question", "dimension"},
    "question_answered": {"question_event_id", "answer"},
    "prototype_recorded": {"prototype_ref", "flows"},
    "observation_recorded": {"observation", "evidence_ref"},
    "specification_proposed": {"proposal_summary", "target_artifact_ids", "canonical_contract_mutation"},
    "approval_requested": {"proposal_event_id", "requested_by"},
    "approval_decided": {
        "proposal_event_id",
        "proposal_author_principal",
        "approver_principal",
        "decision",
        "artifact_id",
        "artifact_digest",
    },
    "withdrawn": {"reason", "withdrawn_event_id"},
}
SECRET_KEY = re.compile(
    r"(?:secret|password|credential|api[_-]?key|access[_-]?token|authorization|private[_-]?key|"
    r"(?:email|phone|address)(?:[_-]|$)|raw(?:[_-]|$)|(?:external[_-]?)?(?:body|html|content)(?:[_-]|$))",
    re.IGNORECASE,
)
SECRET_VALUE = re.compile(
    r"(?:-----BEGIN|\bBearer\s+|\bsk-[A-Za-z0-9_-]{8,}|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)", re.I
)


def load_discovery_ledger(path: Path = LEDGER) -> dict[str, Any]:
    """台帳を object として読む。呼出側が読み込み失敗を fail-close に扱う。"""
    data = load(path)
    if not isinstance(data, dict):
        raise ValueError("requirement discovery ledger は object でなければならない")
    return data


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_index(events: list[dict[str, Any]]) -> dict[str, tuple[int, dict[str, Any]]]:
    return {
        event["event_id"]: (index, event)
        for index, event in enumerate(events)
        if isinstance(event.get("event_id"), str)
    }


def _payload_faults(event: dict[str, Any]) -> list[str]:
    event_id = event.get("event_id", "?")
    event_type = event.get("event_type")
    payload = event.get("payload")
    if event_type not in PAYLOAD_FIELDS or not isinstance(payload, dict):
        return [f"{event_id}: payload の型又は event_type が不正"]
    expected = PAYLOAD_FIELDS[event_type]
    if set(payload) != expected:
        return [f"{event_id}: {event_type} payload フィールドが厳格定義と不一致"]
    strings = {
        "candidate_recorded": ("title", "problem_statement", "value_hypothesis"),
        "question_raised": ("question", "dimension"),
        "question_answered": ("question_event_id", "answer"),
        "prototype_recorded": ("prototype_ref",),
        "observation_recorded": ("observation", "evidence_ref"),
        "specification_proposed": ("proposal_summary",),
        "approval_requested": ("proposal_event_id", "requested_by"),
        "withdrawn": ("reason", "withdrawn_event_id"),
    }
    faults: list[str] = []
    for key in strings.get(event_type, ()):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            faults.append(f"{event_id}: payload.{key} は空でない string が必要")
    if event_type == "candidate_recorded" and not all(
        isinstance(x, str)
        for x in payload["unresolved_questions"]
        if isinstance(payload["unresolved_questions"], list)
    ):
        faults.append(f"{event_id}: payload.unresolved_questions は string 配列が必要")
    if event_type == "candidate_recorded" and not isinstance(payload["unresolved_questions"], list):
        faults.append(f"{event_id}: payload.unresolved_questions は配列が必要")
    if event_type == "prototype_recorded" and not isinstance(payload["flows"], list):
        faults.append(f"{event_id}: payload.flows は配列が必要")
    if event_type == "specification_proposed":
        if not isinstance(payload["target_artifact_ids"], list) or not all(
            isinstance(x, str) for x in payload["target_artifact_ids"]
        ):
            faults.append(f"{event_id}: payload.target_artifact_ids は string 配列が必要")
        if payload["canonical_contract_mutation"] is not False:
            faults.append(f"{event_id}: canonical_contract_mutation は false 固定")
    if event_type == "approval_decided":
        for key in (
            "proposal_event_id",
            "proposal_author_principal",
            "approver_principal",
            "artifact_id",
            "artifact_digest",
        ):
            if not isinstance(payload.get(key), str) or not payload[key].strip():
                faults.append(f"{event_id}: payload.{key} は空でない string が必要")
        if payload.get("decision") not in {"accepted", "rejected"}:
            faults.append(f"{event_id}: approval decision が不正")
        if not re.fullmatch(r"[0-9a-f]{12}", str(payload.get("artifact_digest", ""))):
            faults.append(f"{event_id}: artifact_digest は12桁 sha256 prefix が必要")
    return faults


def schema_and_event_faults(data: dict[str, Any]) -> list[str]:
    """schema の形と、最小検証器では表せない値・日時・payload の厳格性を検査する。"""
    faults = schema_check(load(SCHEMA), data)
    for key, expected in {
        "schema_version": "helix-requirement-discovery-events.v1",
        "authority": "canonical",
        "lifecycle_status": "adapted",
        "historical_policy": "preexisting-not-backfilled",
    }.items():
        if data.get(key) != expected:
            faults.append(f"root.{key} が {expected!r} でない")
    events = data.get("events", [])
    if not isinstance(events, list):
        return faults
    if not events:
        faults.append("adapted discovery ledger は導入決定を表す event を少なくとも 1 件持つ")
    ids = [event.get("event_id") for event in events if isinstance(event, dict)]
    if len(ids) != len(set(ids)):
        faults.append("event_id が重複")
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id", f"index:{index}")
        if event.get("sequence") != index + 1:
            faults.append(f"{event_id}: sequence は 1 から単調増加でなければならない")
        if event.get("event_type") not in EVENT_TYPES:
            faults.append(f"{event_id}: event_type が許可語彙外")
        occurred = _parse_time(event.get("occurred_at"))
        recorded = _parse_time(event.get("recorded_at"))
        if occurred is None or recorded is None:
            faults.append(f"{event_id}: occurred_at/recorded_at が RFC3339 UTC でない")
        elif recorded < occurred:
            faults.append(f"{event_id}: recorded_at は occurred_at 以降でなければならない")
        faults.extend(_payload_faults(event))
    return faults


def prefix_faults(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    """親コミット台帳を完全 prefix として保持しているかを純粋関数で検査する。"""
    if previous is None:
        return []
    old_events = previous.get("events")
    new_events = current.get("events")
    if not isinstance(old_events, list) or not isinstance(new_events, list):
        return ["親又は現行 ledger.events が配列でない"]
    if len(new_events) < len(old_events):
        return ["親コミット event の削除を検出"]
    for index, old in enumerate(old_events):
        if new_events[index] != old:
            return [f"親コミット event[{index + 1}] の改変・並替えを検出"]
    return []


def committed_parent_ledger() -> dict[str, Any] | None:
    """現在の親コミット、なければ最後に追跡された版を読む（初回導入は None）。"""
    relative = str(LEDGER.relative_to(ROOT))
    parent = git("show", "HEAD^:" + relative)
    if parent.returncode == 0:
        try:
            import json

            return json.loads(parent.stdout)
        except ValueError:
            return {"events": None}
    history = git("rev-list", "HEAD^", "--", relative)
    commit = next((line for line in history.stdout.splitlines() if line), None)
    if commit is None:
        return None
    prior = git("show", f"{commit}:{relative}")
    if prior.returncode:
        return {"events": None}
    try:
        import json

        return json.loads(prior.stdout)
    except ValueError:
        return {"events": None}


def reference_and_lifecycle_faults(data: dict[str, Any], ctx: Ctx) -> list[str]:
    events = data.get("events", [])
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        return ["events が object 配列でない"]
    index = _event_index(events)
    artifacts = {item["artifact_id"]: item for item in ctx.manifest_items}
    faults: list[str] = []
    subject_events: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for position, event in enumerate(events):
        event_id = str(event.get("event_id", position))
        subject_events.setdefault(str(event.get("subject_id", "")), []).append((position, event))
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        event_type = event.get("event_type")
        payload_ref = {
            "question_answered": ("question_event_id", "question_raised"),
            "approval_requested": ("proposal_event_id", "specification_proposed"),
        }.get(event_type)
        if payload_ref is not None:
            ref_id, expected_type = payload_ref
            payload_ref_id = payload.get(ref_id)
            target = index.get(payload_ref_id) if isinstance(payload_ref_id, str) else None
            if target is None:
                faults.append(f"{event_id}: payload.{ref_id} が orphan event を指す")
            elif target[0] >= position or target[1].get("event_type") != expected_type:
                faults.append(f"{event_id}: payload.{ref_id} が先行 {expected_type} を指さない")
            elif target[1].get("subject_id") != event.get("subject_id"):
                faults.append(f"{event_id}: payload.{ref_id} の subject が一致しない")
        if event_type == "withdrawn":
            withdrawn_id = payload.get("withdrawn_event_id")
            target = index.get(withdrawn_id) if isinstance(withdrawn_id, str) else None
            if target is None:
                faults.append(f"{event_id}: payload.withdrawn_event_id が orphan event を指す")
            elif target[0] >= position or target[1].get("subject_id") != event.get("subject_id"):
                faults.append(
                    f"{event_id}: payload.withdrawn_event_id が同一 subject の先行 event を指さない"
                )
        if event_type == "approval_decided":
            proposal_id = payload.get("proposal_event_id")
            target = index.get(proposal_id) if isinstance(proposal_id, str) else None
            if target is None:
                faults.append(f"{event_id}: payload.proposal_event_id が orphan event を指す")
            elif target[0] >= position or target[1].get("event_type") != "specification_proposed":
                faults.append(
                    f"{event_id}: payload.proposal_event_id が先行 specification_proposed を指さない"
                )
            elif target[1].get("subject_id") != event.get("subject_id"):
                faults.append(f"{event_id}: payload.proposal_event_id の subject が一致しない")
            else:
                proposal_payload = target[1].get("payload", {})
                target_artifacts = (
                    proposal_payload.get("target_artifact_ids", [])
                    if isinstance(proposal_payload, dict)
                    else []
                )
                if payload.get("artifact_id") not in target_artifacts:
                    faults.append(
                        f"{event_id}: approval artifact_id が proposal の target_artifact_ids にない"
                    )
        if event_type == "specification_proposed":
            target_ids = payload.get("target_artifact_ids", [])
            unknown = [artifact_id for artifact_id in target_ids if artifact_id not in artifacts]
            if unknown:
                faults.append(f"{event_id}: unknown target artifact {unknown}")
        for reference in event.get("references", []):
            if not isinstance(reference, dict):
                continue
            kind, reference_id = reference.get("kind"), reference.get("id")
            if kind == "event":
                target = index.get(reference_id) if isinstance(reference_id, str) else None
                if target is None:
                    faults.append(f"{event_id}: orphan event reference {reference_id}")
                elif target[0] >= position:
                    faults.append(f"{event_id}: future event reference {reference_id}")
            elif kind == "artifact":
                if reference_id not in artifacts:
                    faults.append(f"{event_id}: unknown artifact reference {reference_id}")
            elif kind == "source":
                if not isinstance(reference_id, str) or not reference_id.startswith("source:"):
                    faults.append(f"{event_id}: source reference は source: で開始する stable ID が必要")
    for subject, history in subject_events.items():
        types = [event.get("event_type") for _, event in history]
        if subject == "DISCOVERY-LEDGER":
            if history[0][1].get("event_type") != "specification_proposed":
                faults.append("DISCOVERY-LEDGER は specification_proposed から開始する")
        elif types[0] != "candidate_recorded":
            faults.append(f"{subject}: candidate_recorded より前の lifecycle event を拒否")
        terminal = next(
            (i for i, kind in enumerate(types) if kind in {"approval_decided", "withdrawn"}), None
        )
        if terminal is not None and terminal != len(types) - 1:
            faults.append(f"{subject}: approval_decided/withdrawn 後の event を拒否")
        # 集合の存在だけでなく、同一 subject のイベント列で先行していることを要求する。
        # `candidate, question_answered, question_raised` のような順序逆転を許すと、
        # event 参照を省略した変更が lifecycle gate を迂回できる。
        prior: set[str] = set()
        for _, event in history:
            kind = event.get("event_type")
            if kind == "question_answered" and "question_raised" not in prior:
                faults.append(f"{subject}: question_answered に先行 question_raised がない")
            if kind == "approval_requested" and "specification_proposed" not in prior:
                faults.append(f"{subject}: approval_requested に先行 specification_proposed がない")
            if kind == "approval_decided" and "approval_requested" not in prior:
                faults.append(f"{subject}: approval_decided に先行 approval_requested がない")
            prior.add(str(kind))
    return faults


def _artifact_digest(item: dict[str, Any]) -> str | None:
    path = ROOT / item["canonical_path"]
    if not path.exists():
        return None
    if path.suffix == ".json":
        value = load(path)
        return canonical_json_digest(value)[:12] if isinstance(value, dict) else None
    import hashlib

    body = path.read_text(encoding="utf-8")
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def approval_faults(data: dict[str, Any], ctx: Ctx) -> list[str]:
    artifacts = {item["artifact_id"]: item for item in ctx.manifest_items}
    events = data.get("events", [])
    if not isinstance(events, list):
        return ["events が配列でない"]
    by_id = _event_index([event for event in events if isinstance(event, dict)])
    faults: list[str] = []
    for event in events:
        if not isinstance(event, dict) or event.get("event_type") != "approval_decided":
            continue
        event_id, payload = event.get("event_id", "?"), event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        proposal_id = payload.get("proposal_event_id")
        proposal = by_id.get(proposal_id) if isinstance(proposal_id, str) else None
        if proposal is None or proposal[1].get("event_type") != "specification_proposed":
            faults.append(f"{event_id}: approval proposal_event_id が先行 specification_proposed を指さない")
        elif proposal[1].get("actor_principal") != payload.get("proposal_author_principal"):
            faults.append(f"{event_id}: proposal_author_principal が proposal actor と一致しない")
        else:
            proposal_payload = proposal[1].get("payload", {})
            target_artifacts = (
                proposal_payload.get("target_artifact_ids", []) if isinstance(proposal_payload, dict) else []
            )
            if payload.get("artifact_id") not in target_artifacts:
                faults.append(f"{event_id}: approval artifact_id が proposal の target_artifact_ids にない")
        if payload.get("approver_principal") == payload.get("proposal_author_principal"):
            faults.append(f"{event_id}: proposal author による self approval を拒否")
        artifact = artifacts.get(payload.get("artifact_id"))
        if artifact is None or artifact.get("lifecycle_status") != "confirmed":
            faults.append(f"{event_id}: confirmed canonical artifact が必要")
            continue
        if artifact.get("approval_digest") != payload.get("artifact_digest"):
            faults.append(f"{event_id}: manifest approval_digest と不一致")
        if _artifact_digest(artifact) != payload.get("artifact_digest"):
            faults.append(f"{event_id}: canonical artifact digest と不一致")
        receipt = re.search(
            rf"^\|[^\n]*\|\s*{re.escape(str(payload.get('artifact_digest')))}\s*\|",
            ctx.approvals,
            re.MULTILINE,
        )
        if receipt is None:
            faults.append(f"{event_id}: approval receipt に artifact digest がない")
    return faults


def safety_faults(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    faults: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if SECRET_KEY.search(key):
                    faults.append(f"{path}.{key}: secret/PII/raw external field を拒否")
                visit(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str) and SECRET_VALUE.search(value):
            faults.append(f"{path}: secret/PII value を拒否")

    visit(data.get("events", []), "events")
    # パス定数と書込み呼出しが別行に分かれても検出する。単一行 regex だと
    # `LEDGER = "...json"` → 数行後の `LEDGER.write_text(...)` で迂回できる。
    mutation = re.compile(
        r"(?:requirement-discovery-events\.json[\s\S]{0,512}"
        r"(?:write_text|write_bytes|json\.dump|unlink|replace|rename)"
        r"|(?:write_text|write_bytes|json\.dump|unlink|replace|rename)"
        r"[\s\S]{0,512}requirement-discovery-events\.json)",
        re.IGNORECASE,
    )
    for folder in (root / "src", root / "scripts", root / "tools"):
        for path in folder.rglob("*.py"):
            if mutation.search(path.read_text(encoding="utf-8")):
                faults.append(f"{path.relative_to(root)}: ledger から正本を自動 mutation する経路を拒否")
    return faults


def coverage_faults(data: dict[str, Any]) -> list[str]:
    commit = data.get("coverage_start_commit")
    if not isinstance(commit, str) or git("rev-parse", "--verify", f"{commit}^{{commit}}").returncode:
        return ["coverage_start_commit が実在 commit でない"]
    stamp = git("show", "-s", "--format=%cI", commit)
    start = _parse_time(stamp.stdout.strip())
    faults: list[str] = []
    for event in data.get("events", []):
        if isinstance(event, dict) and start is not None:
            occurred = _parse_time(event.get("occurred_at"))
            if occurred is not None and occurred < start.astimezone(UTC):
                faults.append(
                    f"{event.get('event_id', '?')}: coverage_start_commit より前の履歴を backfill できない"
                )
    return faults


DISCOVERY_COVERAGE_PATHS = (BR_CONTRACTS, REQ_LEDGER, FR_CONTRACTS, NFR_CONTRACTS, AC_CONTRACTS, TC_CONTRACTS)


def changed_contract_paths(coverage_start: str) -> set[str]:
    """開始点から作業ツリーまでに変更された既存契約正本を返す。

    `git diff <start>` は HEAD だけでなく index と未stageの変更も含むため、commit 前に
    discovery 証跡を忘れた変更も fail-close にできる。
    """
    paths = [str(path.relative_to(ROOT)) for path in DISCOVERY_COVERAGE_PATHS]
    result = git("diff", "--name-only", coverage_start, "--", *paths)
    return {line for line in result.stdout.splitlines() if line}


def contract_coverage_faults(data: dict[str, Any], ctx: Ctx) -> list[str]:
    """契約変更ごとに proposal と決定又は明示的な保留/withdrawal を要求する。"""
    start = data.get("coverage_start_commit")
    if not isinstance(start, str):
        return ["coverage_start_commit がないため contract coverage を判定できない"]
    changed = changed_contract_paths(start)
    artifacts_by_path = {item["canonical_path"]: item["artifact_id"] for item in ctx.manifest_items}
    events = [event for event in data.get("events", []) if isinstance(event, dict)]
    proposals: dict[str, set[str]] = {}
    for event in events:
        if event.get("event_type") != "specification_proposed":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            continue
        for artifact_id in payload.get("target_artifact_ids", []):
            if isinstance(artifact_id, str):
                proposals.setdefault(artifact_id, set()).add(str(event.get("event_id")))
    faults: list[str] = []
    for path in sorted(changed):
        artifact_id = artifacts_by_path.get(path)
        if artifact_id is None:
            faults.append(f"contract coverage: manifest 未登録の変更 {path}")
            continue
        proposal_ids = proposals.get(artifact_id, set())
        if not proposal_ids:
            faults.append(f"contract coverage: {artifact_id} の specification_proposed がない")
            continue
        settled = False
        for event in events:
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if (
                event.get("event_type") == "approval_decided"
                and payload.get("proposal_event_id") in proposal_ids
            ):
                settled = True
            if event.get("event_type") == "withdrawn" and payload.get("withdrawn_event_id") in proposal_ids:
                reason = payload.get("reason")
                if isinstance(reason, str) and reason.startswith("deferred:") and reason[9:].strip():
                    settled = True
        if not settled:
            faults.append(
                f"contract coverage: {artifact_id} の proposal に approval_decided 又は withdrawn(reason=deferred を含む) がない"
            )
    return faults


def detect_discovery_faults(
    data: dict[str, Any], ctx: Ctx | None = None, *, previous: dict[str, Any] | None = None, root: Path = ROOT
) -> list[str]:
    """dev.py と unit test 用の集約検査。None の previous は親履歴を用いる。"""
    context = ctx or Ctx()
    faults = schema_and_event_faults(data)
    faults += coverage_faults(data)
    faults += contract_coverage_faults(data, context)
    faults += prefix_faults(committed_parent_ledger() if previous is None else previous, data)
    faults += reference_and_lifecycle_faults(data, context)
    faults += approval_faults(data, context)
    faults += safety_faults(data, root)
    return sorted(set(faults))


def run(ctx: Ctx) -> None:
    try:
        data = load_discovery_ledger()
        grouped = {
            "schema": schema_and_event_faults(data) + coverage_faults(data),
            "coverage": contract_coverage_faults(data, ctx),
            "prefix": prefix_faults(committed_parent_ledger(), data),
            "references": reference_and_lifecycle_faults(data, ctx),
            "approval": approval_faults(data, ctx),
            "safety": safety_faults(data),
        }
    except (OSError, ValueError, KeyError) as exc:
        grouped = {
            "schema": [f"discovery ledger を読めない: {exc}"],
            "prefix": ["schema failure"],
            "coverage": ["schema failure"],
            "references": ["schema failure"],
            "approval": ["schema failure"],
            "safety": ["schema failure"],
        }
    gate(
        "G-DISCOVERY-SCHEMA",
        not grouped["schema"],
        f"ledger schema・event・coverage が整合 (違反={grouped['schema'][:3]})",
    )
    gate(
        "G-DISCOVERY-PREFIX",
        not grouped["prefix"],
        f"親コミット event prefix を維持 (違反={grouped['prefix'][:3]})",
    )
    gate(
        "G-DISCOVERY-COVERAGE",
        not grouped["coverage"],
        f"coverage start 以後の契約変更に発見・決定証跡を要求 (違反={grouped['coverage'][:3]})",
    )
    gate(
        "G-DISCOVERY-REFERENCE",
        not grouped["references"],
        f"参照の実在・過去制約・lifecycle が整合 (違反={grouped['references'][:3]})",
    )
    gate(
        "G-DISCOVERY-LIFECYCLE",
        not grouped["references"],
        "候補から承認までの subject lifecycle を fail-close 検査",
    )
    gate(
        "G-DISCOVERY-APPROVAL",
        not grouped["approval"],
        f"approval の主体分離・receipt・digest を束縛 (違反={grouped['approval'][:3]})",
    )
    gate(
        "G-DISCOVERY-SAFETY",
        not grouped["safety"],
        f"credential/secret/PII/raw payload を拒否 (違反={grouped['safety'][:3]})",
    )
    gate(
        "G-DISCOVERY-NO-CANONICAL-MUTATION",
        not grouped["safety"],
        "ledger から契約正本・製品runtimeを自動更新する経路を拒否",
    )
