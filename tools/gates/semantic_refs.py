"""意味整合ゲート: 構造化参照（table/column/state/event/evidence_kind/error_type/api）の実在検査。"""

from __future__ import annotations

import re

from tools.gates.common import (
    ERROR_TAXONOMY,
    Ctx,
    gate,
)

# operation_log（evidence kind）を証跡にできるのは外部操作・業務操作を伴うドメインのみ
EXTERNAL_TARGET = re.compile(r"^(FR-4\d|FR-5\d|FR-6\d)$")
NO_EXTERNAL_EFFECT = ("外部操作差分なし", "外部呼出0", "外部呼出 0", "外部操作を生成せず",
                      "operation_log は使用しない", "operation_log kind）の対象外")
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
    """operation_log を正当に生成する外部操作そのものか（単なる表参照では認めない）。"""
    if any(neg in text for neg in NO_EXTERNAL_EFFECT):
        return False
    explicit = ("Web 取得" in text or "external_operation_id" in text
                or "external_operations +" in text or "external_operations 1 行" in text
                or "external_operations 2 行" in text or "external_operations遷移" in text
                or "external_operations の status" in text
                or "外部操作のマスク済み証跡" in text
                or "外部操作対応operation_log" in text or "operation_log 行（外部操作" in text
                or "operation_log 行（外部取得操作" in text
                or "Docker WP" in text)
    has_external_table = "external_operations" in refs.get("table_refs", [])
    return ("Web 取得" in text
            or (explicit and (has_external_table or bool(EXTERNAL_TARGET.match(target or "")))))


def detect_state_evidence_faults(acs: list[dict], tcs: list[dict],
                                 contracts: list[dict] | None = None) -> list[str]:
    """状態遷移・ゲート拒否の証跡を operation_log で表現している箇所を列挙する。"""
    bad: list[str] = []
    ac_by_id = {a["id"]: a for a in acs}
    for c in contracts or []:
        positive = " ".join([
            c.get("rejection_behavior", ""),
            " ".join(c.get("side_effects", [])),
            " ".join(c.get("evidence", [])),
        ])
        refs = c.get("semantic_refs", {})
        claims_operation_log = ("operation_log" in positive
                                and not any(neg in positive for neg in NO_EXTERNAL_EFFECT))
        if claims_operation_log and not _external_domain(refs, c.get("id", ""), positive):
            bad.append(f"{c['id']}:内部遷移・ゲート拒否をoperation_logで表現")
        if "DB を変更せず" in c.get("rejection_behavior", "") \
                and "state_transitions" in c.get("rejection_behavior", ""):
            bad.append(f"{c['id']}:拒否証跡INSERTとDB変更なしが矛盾")
    for a in acs:
        positive = a.get("expected_evidence", "")
        if "operation_log" not in positive or any(neg in positive for neg in NO_EXTERNAL_EFFECT):
            continue
        ev_txt = " ".join((positive, a.get("expected_db_delta", ""), a.get("then", "")))
        if not _external_domain(a.get("semantic_refs", {}), a.get("target", ""), ev_txt):
            bad.append(f"{a['id']}:内部遷移・ゲート拒否を operation_log で表現")
    for t in tcs:
        positive = t.get("verifies_evidence", "")
        if "operation_log" not in positive or any(neg in positive for neg in NO_EXTERNAL_EFFECT):
            continue
        ev_txt = " ".join((positive, t.get("verifies_db_delta", "")))
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
    se_bad = detect_state_evidence_faults(ctx.acc, ctx.tcc, ctx.allc)
    gate("G-STATE-EVIDENCE-CONSISTENCY", not se_bad,
         "状態遷移の拒否・成立は state_transitions／構造化ログで表現し operation_log は外部操作に限定 "
         f"(違反={se_bad[:5]})")
