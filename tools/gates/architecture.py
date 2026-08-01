"""構造・DB 層ゲート: DDL 同期／適用・状態機械の決定性・戦略正本の DB 強制・CMP/ITC 台帳・設計書実体。"""

from __future__ import annotations

import re
import sqlite3
import subprocess
from pathlib import Path

from tools.gates.common import (
    BASIC_DESIGN,
    CMP_SCHEMA,
    EVIDENCE_KINDS,
    L4,
    L5,
    L6,
    MIGRATION_RULES,
    ROOT,
    S0_CONTRACT,
    TRACE,
    UPDATES,
    Ctx,
    gate,
    is_frozen,
    live_markdown,
    load,
    rel,
    schema_check,
)

EXPECTED_TABLES = 25
EXPECTED_TRIGGERS = 16  # append-only 10＋TLP 整合 3＋brief 不変 1＋brief 状態遷移 1＋valid_until 1
INITIAL = {"loop_runs": {"pending"}, "tasks": {"pending"}}
TERMINAL = {"loop_runs": {"completed", "failed", "escalated", "cancelled"},
            "tasks": {"done", "failed", "escalated"}}

BRIEF_INSERT = (
    "INSERT INTO strategic_briefs (brief_key, version, strategic_choice_id, segment_context_id,"
    " value_hypothesis_id, desired_recognition_change, tactical_objective, media_role,"
    " message_hypothesis, measurement_plan_json, valid_from, valid_until, digest, status, created_at)"
    " VALUES (?, 1, 'SC-1', 'SEG-1', 'VH-1', 'x', 'y', 'proof', 'm', '[]',"
    " '2026-08-01', ?, ?, ?, 't')"
)


def _apply(ddl: str) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(ddl)
    return con


# ---------------------------------------------------------------- 検出関数（DB 実 DML）
def strategy_mutation_rejected(ddl: str) -> tuple[bool, str]:
    """上流正本（brief／TLP）への UPDATE/DELETE が append-only トリガで ABORT されるか実証する。"""
    c = _apply(ddl)
    try:
        c.execute(BRIEF_INSERT, ("SB-G", None, "a" * 64, "active"))
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
                  " VALUES ('upper', 'LP-U', 'running', 'kg', 't')")
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
                  " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
                  " VALUES ('lower', 'LP-W', 'completed', 'kg2', 't', 1, 1, ?)", ("a" * 64,))
        c.execute(
            "INSERT INTO tactical_learning_packets (packet_key, packet_kind, loop_run_id,"
            " strategic_brief_id, strategic_brief_digest, observations_json, hypothesis_result,"
            " target_hypothesis_ids_json, assessment_reason, causal_interpretation,"
            " alternative_explanations_json, confidence,"
            " evidence_ids_json, recommended_next_action, created_at)"
            " VALUES ('TLP-G', 'learning', 2, 1, ?, '[\"OBS-1\"]', 'supported', '[]', 'r', 'c',"
            " '[\"ALT-1\"]', 0.5, '[\"EV-1\"]', 'continue', 't')", ("a" * 64,))
        c.execute(BRIEF_INSERT, ("SB-G2", None, "c" * 64, "draft"))
        for stmt in ("UPDATE strategic_briefs SET digest = ? WHERE id = 1",
                     "DELETE FROM strategic_briefs WHERE id = 2",
                     "UPDATE tactical_learning_packets SET confidence = 0.9 WHERE id = 1",
                     "DELETE FROM tactical_learning_packets WHERE id = 1"):
            try:
                c.execute(stmt, ("b" * 64,)) if "?" in stmt else c.execute(stmt)
                return False, f"変異が通過: {stmt}"
            except sqlite3.IntegrityError as ie:
                if "append-only" not in str(ie):
                    return False, f"トリガ以外の理由で拒否（トリガ欠落を偽装）: {stmt} → {ie}"
        return True, "UPDATE/DELETE 4 系すべて append-only トリガで ABORT"
    except sqlite3.Error as e:
        return False, f"検査不能: {e}"
    finally:
        c.close()


ALLOWED_BRIEF_TRANSITIONS = {("draft", "active"), ("active", "superseded"), ("active", "retired")}
DENIED_BRIEF_TRANSITIONS = [
    ("superseded", "active"), ("retired", "active"), ("superseded", "retired"),
    ("retired", "superseded"), ("active", "draft"), ("superseded", "draft"), ("retired", "draft"),
]


def detect_brief_transition_faults(ddl: str) -> list[str]:
    """brief の status 遷移を実 DML で検査する（許可の通過・逆行の拒否の両方）。"""
    bad: list[str] = []
    for src, dst in sorted(ALLOWED_BRIEF_TRANSITIONS):
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, (f"SB-{src}-{dst}", None, "a" * 64, src))
            c.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = ?",
                      (dst, f"SB-{src}-{dst}"))
        except sqlite3.Error as e:
            bad.append(f"許可遷移が拒否された {src}→{dst}: {e}")
        finally:
            c.close()
    for src, dst in DENIED_BRIEF_TRANSITIONS:
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, (f"SB-{src}-{dst}", None, "a" * 64, src))
            c.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = ?",
                      (dst, f"SB-{src}-{dst}"))
            bad.append(f"逆行が通過 {src}→{dst}")
        except sqlite3.IntegrityError as e:
            if "status transition" not in str(e):
                bad.append(f"別理由で拒否（遷移トリガ欠落の偽装） {src}→{dst}: {e}")
        except sqlite3.Error as e:
            bad.append(f"検査不能 {src}→{dst}: {e}")
        finally:
            c.close()
    return bad


def detect_valid_until_faults(ddl: str) -> list[str]:
    """valid_until の延長（後ろ倒し・NULL 化）が拒否され、短縮のみ通ることを実 DML で検査する。"""
    bad: list[str] = []
    cases = [
        ("2026-09-01", "2026-12-01", True, "後ろ倒し"),
        ("2026-09-01", None, True, "NULL 化（無期限延長）"),
        ("2026-09-01", "2026-08-15", False, "短縮"),
        (None, "2026-08-15", False, "無期限→期限設定"),
    ]
    for before, after, should_reject, label in cases:
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, ("SB-VU", before, "a" * 64, "active"))
            c.execute("UPDATE strategic_briefs SET valid_until = ? WHERE brief_key = 'SB-VU'", (after,))
            if should_reject:
                bad.append(f"valid_until の{label}が通過")
        except sqlite3.IntegrityError as e:
            if not should_reject:
                bad.append(f"valid_until の{label}が拒否された: {e}")
            elif "valid_until" not in str(e):
                bad.append(f"別理由で拒否（トリガ欠落の偽装）{label}: {e}")
        except sqlite3.Error as e:
            bad.append(f"検査不能 {label}: {e}")
        finally:
            c.close()
    return bad


def detect_tlp_json_predicate_faults(ddl: str) -> list[str]:
    """TLP の空配列判定が文字列比較でなく json_array_length であることを検査する。"""
    bad: list[str] = []
    body = ddl.split("CREATE TRIGGER tlp_kind_field_rules")[1].split("END;")[0] if \
        "tlp_kind_field_rules" in ddl else ""
    if not body:
        return ["tlp_kind_field_rules トリガが存在しない"]
    for m in re.finditer(r"(\w+_json)\s+IS\s+NOT\s+'\[\]'", body):
        bad.append(f"文字列比較が残存: {m.group(0)}")
    for col in ("alternative_explanations_json", "proposed_revision_targets_json"):
        if f"json_array_length(NEW.{col})" not in body:
            bad.append(f"{col} が json_array_length 判定でない")
    # 実 DML: 空白入り '[ ]' は文字列比較では非空と誤判定されるが json_array_length では 0 件
    c = _apply(ddl)
    try:
        c.execute(BRIEF_INSERT, ("SB-TLP", None, "a" * 64, "active"))
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
                  " VALUES ('upper', 'LP-U', 'running', 'k1', 't')")
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
                  " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
                  " VALUES ('lower', 'LP-W', 'failed', 'k2', 't', 1, 1, ?)", ("a" * 64,))
        try:
            c.execute(
                "INSERT INTO tactical_learning_packets (packet_key, packet_kind, loop_run_id,"
                " strategic_brief_id, strategic_brief_digest, observations_json, failure_fact,"
                " reproduction_conditions, recovery_conditions, alternative_explanations_json,"
                " confidence, evidence_ids_json, recommended_next_action, created_at)"
                " VALUES ('TLP-SP', 'failure', 2, 1, ?, '[\"OBS-1\"]', 'f', 'rc', 'rv', '[ ]',"
                " 0.5, '[\"EV-1\"]', 'stop', 't')", ("a" * 64,))
        except sqlite3.IntegrityError as e:
            bad.append(f"空白入り空配列 '[ ]' を非空と誤判定して拒否した（文字列比較の残存）: {e}")
    except sqlite3.Error as e:
        bad.append(f"検査不能: {e}")
    finally:
        c.close()
    return bad


# ---------------------------------------------------------------- 物理数の主張（PO 指示 §3）
# 「25 テーブル」「保護トリガ 16 本」のような**物理数の主張**は、散文の記憶ではなく実 DDL から
# 導出した数と突合する。部分集合を語る主張（特定テーブルに限定した本数）は、その文脈に現れる
# テーブル名から**期待値を計算**して突合する（総数へ丸めない — 部分集合の主張も検証対象）。
# 「トリガ 11」「トリガーは 11 本」「11 基のトリガ」のような表記ゆれも物理数の主張として拾う
# （単位語・助詞の有無や語順に依らない — 独立レビュー R2-03）
TRIGGER_CLAIM = re.compile(r"トリガー?\s*(?:は|が|を|の|＝|=|:|：)?\s*(\d+)")
# 前置形は**単位語を必須**にする（`§2 の保護トリガ`・`3.2 トリガ` のような節番号を数と読まない）
TRIGGER_CLAIM_PRE = re.compile(
    r"(?<![A-Za-z0-9-.§])(\d+)\s*(?:本|件|個|基)\s*(?:の|もの)?\s*(?:保護|整合|append-only)?トリガー?")
# 「S0 テーブル」「SCM-01 テーブル」のような識別子の一部を数値と読まない
TABLE_CLAIM = re.compile(r"(?<![A-Za-z0-9-])(\d+)\s*テーブル")
# 部分集合の記述（「戦略正本 2 テーブル」等）と総数の主張を混同しないための閾値。
# 総数（25）は 2 桁であり、1 桁の主張は総数を名乗っていない
TABLE_TOTAL_MIN = 10
# 監査記録・承認ログは「その時点の事実」を保存する履歴であり、現在の物理数へ追随させない
HISTORICAL_PREFIXES = ("docs/00-authority/audits/", "docs/00-authority/approvals/",
                       "docs/00-authority/superseded/")
SEGMENT_SPLIT = re.compile(r"[。\n]|(?<=\|)")


def ddl_physical(ddl: str) -> tuple[set[str], dict[str, str]]:
    """実 DDL のテーブル集合と、トリガ名 → 対象テーブル名の写像を返す。"""
    con = _apply(ddl)
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    trg = {r[0]: r[1] for r in con.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='trigger'")}
    con.close()
    return tables, trg


def _texts(root: Path = ROOT) -> list[tuple[str, str]]:
    """検査対象の (出所, テキスト) を集める（現役 MD・契約 JSON・テスト関数名）。"""
    out: list[tuple[str, str]] = []
    for p in live_markdown():
        out.append((rel(p), p.read_text(encoding="utf-8")))
    for p in sorted(root.glob("docs/L*/**/*.json")):
        if is_frozen(p):
            continue
        out.append((rel(p), p.read_text(encoding="utf-8")))
    for p in sorted(root.glob("tests/**/*.py")):
        for m in re.finditer(r"^def (test_\w+)", p.read_text(encoding="utf-8"), re.M):
            out.append((f"{rel(p)}::{m.group(1)}", m.group(1)))
    return out


TEST_NAME_CLAIM = re.compile(r"_(\d+)_tables?_(?:and_)?(\d+)_triggers?")


def detect_physical_count_faults(ddl: str, root: Path = ROOT) -> list[str]:
    """散文・契約・テスト名の物理数（テーブル数・トリガ数）を実 DDL と突合する。

    期待値は定数ではなく**実 DDL から導出**する。数値で書いてよいのは**総数**だけとし、
    部分集合（特定テーブルに限った本数）は数値で書かない — 長い文の中の数値がどの範囲を
    指すのかは機械にも人にも決まらず、実物との乖離が検出できないまま残るため。
    """
    tables, trg_table = ddl_physical(ddl)
    n_tab, n_trg = len(tables), len(trg_table)
    bad: list[str] = []
    for origin, text in _texts(root):
        if origin.startswith(HISTORICAL_PREFIXES):
            continue
        for m in TEST_NAME_CLAIM.finditer(text):
            if (int(m.group(1)), int(m.group(2))) != (n_tab, n_trg):
                bad.append(f"{origin}: テスト名の物理数 {m.group(1)}テーブル/{m.group(2)}トリガ "
                           f"が実 DDL（{n_tab}/{n_trg}）と不一致")
        for seg in SEGMENT_SPLIT.split(text):
            if not seg or ("トリガ" not in seg and "テーブル" not in seg):
                continue
            for pat in (TRIGGER_CLAIM, TRIGGER_CLAIM_PRE):
                for m in pat.finditer(seg):
                    if int(m.group(1)) != n_trg:
                        bad.append(f"{origin}: トリガ数の主張 {m.group(1)} が実 DDL の {n_trg} と不一致"
                                   f"（部分集合は数値で書かない — 総数だけを数値で持つ）: "
                                   f"{seg.strip()[:70]}")
            for m in TABLE_CLAIM.finditer(seg):
                n = int(m.group(1))
                if n >= TABLE_TOTAL_MIN and n != n_tab:
                    bad.append(f"{origin}: テーブル総数の主張 {n} が実 DDL の {n_tab} と不一致: "
                               f"{seg.strip()[:70]}")
    return sorted(set(bad))


def detect_unknown_tables(dus: list[dict], tables: set[str]) -> list[str]:
    """DU の db_read/db_write に DDL 非実在テーブルが含まれる箇所を列挙する。"""
    return sorted({f"{d['id']}:{t}" for d in dus for t in d["db_read"] + d["db_write"]
                   if t.split("（")[0] not in tables})


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _ddl(ctx)
    _transitions(ctx)
    _brief_db(ctx)
    _components(ctx)
    _design_substance(ctx)


def _ddl(ctx: Ctx) -> None:
    md_sql = subprocess.run(  # noqa: S603
        ["awk", "/^```sql$/,/^```$/", str(S0_CONTRACT)],  # noqa: S607
        capture_output=True, text=True, check=True).stdout

    def norm(s: str) -> list[str]:
        return [ln.rstrip() for ln in s.splitlines() if ln.rstrip() and not ln.startswith("```")]

    gate("G-DDL-SYNC", norm(md_sql) == norm(ctx.ddl), "ddl.sql == s0-contract の DDL ブロック")

    con = sqlite3.connect(":memory:")
    try:
        con.executescript(ctx.ddl)
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        integ = con.execute("PRAGMA integrity_check").fetchone()[0]
        ntab = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        ntrg = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
        gate("G-DDL-APPLY",
             not fk and integ == "ok" and ntab == EXPECTED_TABLES and ntrg == EXPECTED_TRIGGERS,
             f"DDL 適用 (fk={fk}, integrity={integ}, tables={ntab}/{EXPECTED_TABLES}, "
             f"triggers={ntrg}/{EXPECTED_TRIGGERS})")
    except sqlite3.Error as e:
        gate("G-DDL-APPLY", False, f"DDL 適用失敗: {e}")
    finally:
        con.close()

    phys = detect_physical_count_faults(ctx.ddl)
    gate("G-DESIGN-PHYSICAL-COUNT", not phys,
         "現役文書・契約 JSON・テスト名の物理数（テーブル数・トリガ数）が**実 DDL から導出した数**と"
         f"一致（部分集合の本数を数値で書かない） (違反={phys[:3]})")

    kinds = {k["kind"] for k in load(EVIDENCE_KINDS)["items"]}
    m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)", ctx.ddl)
    dk = set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()
    gate("G-EVK", kinds == dk and len(kinds) == 10, f"evidence kind 10 種一致 (差分={sorted(kinds ^ dk)})")


def _transitions(ctx: Ctx) -> None:
    titems = ctx.transitions
    ents = {t["entity"] for t in titems}
    gate("G-TRN-ENT", ents == {"loop_runs", "tasks"}, f"遷移 entity = loop_runs/tasks ({ents})")
    def _states(pattern: str) -> set[str]:
        """DDL の CHECK 句から状態語彙を抜く（見つからなければ空集合 = fail-close 側）。"""
        m = re.search(pattern, ctx.ddl)
        return set(re.findall(r"'(\w+)'", m.group(1))) if m else set()

    enum = {
        "loop_runs": _states(
            r"loop_runs[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)"),
        "tasks": _states(
            r"CREATE TABLE tasks[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)"),
    }
    badst = [f"{t['entity']}:{s}" for t in titems for s in (t.get("from"), t.get("to"))
             if s and s not in enum[t["entity"]]]
    gate("G-TRN-ST", not badst, f"遷移状態が DDL enum 内・複合表記なし (不明={badst})")

    keys = [(t["entity"], t["from"], t["event"]) for t in titems]
    dupkeys = sorted({k for k in keys if keys.count(k) > 1})
    gate("G-TRN-UNIQ", not dupkeys, f"(entity, from, event) が一意 (重複={dupkeys})")

    unreach = []
    for e, states in enum.items():
        edges: dict[str, set] = {}
        for t in titems:
            if t["entity"] == e:
                edges.setdefault(t["from"], set()).add(t["to"])
        seen = set(INITIAL[e])
        stack = list(INITIAL[e])
        while stack:
            for nxt in edges.get(stack.pop(), set()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        unreach += [f"{e}:{s}" for s in sorted(states - seen)]
    gate("G-TRN-REACH", not unreach, f"enum の全状態が初期状態から BFS 到達可能 (到達不能={unreach})")
    fromterm = [f"{t['entity']}:{t['from']}" for t in titems if t["from"] in TERMINAL[t["entity"]]]
    gate("G-TRN-TERM", not fromterm, f"終端状態からの遷移なし (違反={fromterm})")
    noguard = [f"{t['entity']}:{t['from']}:{t['event']}" for t in titems
               if not (t.get("guard") or "").strip()]
    gate("G-TRN-GUARD", not noguard, f"全遷移に非空ガード (欠落={noguard})")

    up = load(UPDATES)
    uitems = up.get("items") or up.get("updates")
    fnids = [f for u in uitems for f in u["fn_ids"]]
    gate("G-S0-CNT", len(fnids) == 25 and len(set(fnids)) == 25, "S0 fn_ids=25・重複なし")
    gate("G-S0-SET", set(fnids) == ctx.s0_fn,
         f"fn_ids == slice S0 集合 (差分={sorted(set(fnids) ^ ctx.s0_fn)})")

    tr = load(TRACE)
    rows = tr.get("items") or tr.get("rows")
    allbr = {i["id"] for i in ctx.br}
    trbr = {x.get("br") or x.get("BR") for x in rows}
    gate("G-TRC-BR", trbr == allbr, f"trace 38 行が全 BR をカバー (欠落={sorted(allbr - trbr)})")


def _brief_db(ctx: Ctx) -> None:
    """PO 指示 §5: brief 状態遷移・valid_until・TLP 空配列判定を DB で強制する。"""
    tf = detect_brief_transition_faults(ctx.ddl)
    gate("G-BRIEF-TRANSITION", not tf,
         "brief 状態遷移を DDL トリガで固定（draft→active／active→superseded|retired のみ通過、"
         f"superseded/retired からの復帰・draft 逆行は実 DML で ABORT） (違反={tf[:4]})")

    vf = detect_valid_until_faults(ctx.ddl)
    gate("G-BRIEF-VALID-UNTIL", not vf,
         f"valid_until の延長（後ろ倒し・NULL 化）を拒否し短縮のみ許可（延長は新版発行） (違反={vf[:4]})")

    jf = detect_tlp_json_predicate_faults(ctx.ddl)
    gate("G-TLP-JSON-PREDICATE", not jf,
         f"TLP の空配列判定が json_array_length（文字列比較 IS NOT '[]' の不在＋実 DML 実証） (違反={jf[:4]})")


def _components(ctx: Ctx) -> None:
    comps, itcs = ctx.comps, ctx.itcs
    cmpids = [c["id"] for c in comps]
    itcids = [t["id"] for t in itcs]
    gate("G-CMP-CNT", len(comps) == 13, f"CMP=13 (実={len(comps)})")
    gate("G-CMP-UNIQ", len(cmpids) == len(set(cmpids)), "CMP ID 重複ゼロ")
    cfn = [f for c in comps for f in c["fn_ids"]]
    gate("G-CMP-FN", len(cfn) == len(set(cfn)) and set(cfn) == ctx.s0_fn,
         f"CMP が S0 25 FN を重複なく完全被覆 (差分={sorted(set(cfn) ^ ctx.s0_fn)})")
    gate("G-ITC-CNT", len(itcs) == 16, f"ITC=16 (実={len(itcs)})")
    gate("G-ITC-UNIQ", len(itcids) == len(set(itcids)), "ITC ID 重複ゼロ")
    refcmp = {c for t in itcs for c in t["cmp"]}
    gate("G-ITC-CMP", refcmp == set(cmpids),
         f"ITC↔CMP 双方向カバー (不明={sorted(refcmp - set(cmpids))}, 未カバー={sorted(set(cmpids) - refcmp)})")
    rej = [t for t in itcs if t.get("polarity") == "reject"]
    gate("G-ITC-REJ", len(rej) >= 7, f"総合テストの fail-close 拒否系 >=7 (実={len(rej)})")
    badup = [t["id"] for t in itcs if t.get("update") not in ("S0.1", "S0.2", "S0.3")]
    gate("G-ITC-UPD", not badup, f"全 ITC が S0.1〜S0.3 に割当 (未割当={badup})")

    cmpc_schema = load(CMP_SCHEMA)
    m_errs: list[str] = []
    for it in ctx.cmpc:
        m_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(cmpc_schema, it)]
    cmp_ids = {i["id"] for i in comps} | {i["id"] for i in ctx.scm}
    cmpc_ids = {i["id"] for i in ctx.cmpc}
    design_index = {p.name for p in sorted(ROOT.glob("docs/L*/**/*.md"))}
    missing_dd = sorted({dd for it in ctx.cmpc for dd in it["trace"].get("design_doc", [])
                         if Path(dd).name not in design_index})
    gate("G-CMP-INTERFACE", not m_errs and cmpc_ids == cmp_ids and not missing_dd,
         f"CMP/SCM 設計契約: schema 適合＋23 件完全被覆＋独立設計書実在 "
         f"(err={m_errs[:3]}, 差={sorted(cmpc_ids ^ cmp_ids)}, 設計書欠={missing_dd})")


def _design_substance(ctx: Ctx) -> None:
    thin: list[str] = []
    design_docs = [
        L4 / "canonical/external-if/external-if-design_v0.1.md",
        L4 / "canonical/data/db-design_v0.1.md",
        L4 / "canonical/state-machine/state-machine-design_v0.1.md",
        L4 / "canonical/approval/approval-design_v0.1.md",
        L4 / "canonical/brand-isolation/brand-isolation-design_v0.1.md",
        L5 / "canonical/errors/error-taxonomy_v0.1.md",
    ]
    # スライス横断で数える（S0 → S1 への再配置が「分母の縮小」に見えないようにする — ラチェット）。
    # スライス単位の下限も併せて持つ（総数だけだと S0 の設計が消えても通ってしまう）。
    feature_docs = sorted(L6.rglob("*.md"))
    if len(feature_docs) < 14:
        thin.append(f"features 不足:{len(feature_docs)}<14")
    s0_docs = sorted((L6 / "S0").glob("*.md"))
    if len(s0_docs) < 11:
        thin.append(f"S0 features 不足:{len(s0_docs)}<11")
    for p in design_docs + feature_docs:
        txt = p.read_text(encoding="utf-8")
        if txt.count("\n") < 50 or txt.count("## ") < 3:
            thin.append(f"{p.name}:{txt.count(chr(10))}行/{txt.count('## ')}節")
        if p in feature_docs and "trace" not in txt.lower():
            thin.append(f"{p.name}:trace表なし")
    gate("G-DESIGN-SUBSTANCE", not thin, f"設計書の実体（≥50 行・≥3 節・trace） (薄い={thin[:5]})")
    gate("G-BASIC-DESIGN-EXIST", BASIC_DESIGN.exists() and "pair:" in
         BASIC_DESIGN.read_text(encoding="utf-8")[:800],
         "基本設計②がヘッダに pair 宣言を持つ")

    mig = load(MIGRATION_RULES)
    need = {"基本規律", "expand", "backfill", "contract", "rename禁止"}
    names = {r["name"] for r in mig.get("rules", [])}
    thin_rules = [r["name"] for r in mig.get("rules", []) if len(r.get("text", "").strip()) < 30]
    gate("G-MIGRATION-RULES", need <= names and not thin_rules and bool(mig.get("promotion_steps")),
         f"migration 規則が expand/backfill/contract/rename 禁止を実体つきで定義し昇格手順を持つ "
         f"(欠落={sorted(need - names)}, 空={thin_rules})")
