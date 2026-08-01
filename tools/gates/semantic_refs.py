"""意味整合ゲート: 構造化参照（table/column/state/event/evidence_kind/error_type/api）の実在検査。"""

from __future__ import annotations

import re

from tools.gates.common import (
    ERROR_TAXONOMY,
    Ctx,
    gate,
)

# operation_log（evidence kind）を証跡にできるのは外部操作・業務操作を伴うドメインのみ
EXTERNAL_TABLES = {"external_operations", "playbooks", "approvals", "assets",
                   "measurements", "spend_ledger"}
EXTERNAL_TARGET = re.compile(r"^(FR-4\d|FR-5\d|FR-6\d)$")
ERROR_TYPE_RE = re.compile(
    r"[A-Z][A-Za-z]{3,}(?:Error|Rejected|Denied|Missing|Mismatch|Detected|Incomplete|"
    r"Immutable|Violation|Required|Exhausted)")


def load_canon(ctx: Ctx) -> dict:
    """意味検査の正本語彙（DDL・遷移表・evidence kind・エラー分類・API）。"""
    from tools.gates.common import EVIDENCE_KINDS, load
    ev = {t["event"] for t in ctx.transitions}
    kinds = {k["kind"] for k in load(EVIDENCE_KINDS)["items"]}
    errs = set(ERROR_TYPE_RE.findall(ERROR_TAXONOMY.read_text(encoding="utf-8")))
    apis = {m.group(1) for d in ctx.duc for a in d["apis"]
            if (m := re.match(r"def (\w+)", a["signature"]))}
    return {"tables": ctx.ddl_columns, "states": ctx.trn_states, "events": ev,
            "kinds": kinds, "errors": errs, "apis": apis}


def detect_semantic_ref_faults(items: list[dict], canon: dict) -> list[str]:
    """構造化参照が正本語彙に実在しない箇所を列挙する。"""
    bad: list[str] = []
    for it in items:
        r = it.get("semantic_refs")
        if r is None:
            bad.append(f"{it.get('id', '?')}:semantic_refs なし")
            continue
        for t in r["table_refs"]:
            if t not in canon["tables"]:
                bad.append(f"{it['id']}:table {t}")
        for c in r["column_refs"]:
            t, col = c.split(".", 1)
            if t not in canon["tables"] or col not in canon["tables"][t]:
                bad.append(f"{it['id']}:column {c}")
        for s in r["state_refs"]:
            e, name = s.split(".", 1)
            if e not in canon["states"] or name not in canon["states"][e]:
                bad.append(f"{it['id']}:state {s}")
        for e in r["event_refs"]:
            if e not in canon["events"]:
                bad.append(f"{it['id']}:event {e}")
        for k in r["evidence_kind_refs"]:
            if k not in canon["kinds"]:
                bad.append(f"{it['id']}:kind {k}")
        for x in r["error_type_refs"]:
            if x not in canon["errors"]:
                bad.append(f"{it['id']}:error {x}")
        for a in r["api_refs"]:
            if a not in canon["apis"]:
                bad.append(f"{it['id']}:api {a}")
    return bad


def _external_domain(refs: dict, target: str, text: str) -> bool:
    return (bool(set(refs.get("table_refs", [])) & EXTERNAL_TABLES)
            or bool(EXTERNAL_TARGET.match(target or ""))
            or "外部操作" in text)


def detect_state_evidence_faults(acs: list[dict], tcs: list[dict]) -> list[str]:
    """状態遷移・ゲート拒否の証跡を operation_log で表現している箇所を列挙する。"""
    bad: list[str] = []
    ac_by_id = {a["id"]: a for a in acs}
    for a in acs:
        ev_txt = a.get("expected_evidence", "")
        if "operation_log" not in ev_txt:
            continue
        if not _external_domain(a.get("semantic_refs", {}), a.get("target", ""), ev_txt):
            bad.append(f"{a['id']}:内部遷移・ゲート拒否を operation_log で表現")
    for t in tcs:
        ev_txt = t.get("verifies_evidence", "")
        if "operation_log" not in ev_txt:
            continue
        tgt = next((ac_by_id[x]["target"] for x in t.get("ac", []) if x in ac_by_id), "")
        if not _external_domain(t.get("semantic_refs", {}), tgt, ev_txt):
            bad.append(f"{t['id']}:内部遷移・ゲート拒否を operation_log で表現")
    return bad


def run(ctx: Ctx) -> None:
    canon = load_canon(ctx)
    items = ctx.frc + ctx.src + ctx.acc + ctx.tcc + ctx.cmpc + ctx.duc
    sem_bad = detect_semantic_ref_faults(items, canon)
    col_bad = [b for b in sem_bad if ":column " in b or ":table " in b]
    gate("G-SEMANTIC-REF", not sem_bad,
         f"構造化参照が正本語彙に実在（table/column/state/event/kind/error/api） (不正={sem_bad[:5]})")
    gate("G-COLUMN-REF", not col_bad, f"table/column 参照が ddl.sql に実在 (不正={col_bad[:5]})")
    se_bad = detect_state_evidence_faults(ctx.acc, ctx.tcc)
    gate("G-STATE-EVIDENCE-CONSISTENCY", not se_bad,
         "状態遷移の拒否・成立は state_transitions／構造化ログで表現し operation_log は外部操作に限定 "
         f"(違反={se_bad[:5]})")
