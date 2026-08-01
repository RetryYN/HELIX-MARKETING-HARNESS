"""詳細設計層ゲート: DU 台帳・API 実装契約・DbC・エラー型・DB 参照・API 単位 UT・空洞禁止。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.gates.architecture import detect_unknown_tables
from tools.gates.common import (
    AC_CONTRACTS,
    BR_CONTRACTS,
    CMP_CONTRACTS,
    DU_CONTRACTS,
    DU_SCHEMA,
    ERROR_TAXONOMY,
    FR_CONTRACTS,
    L6,
    NFR_CONTRACTS,
    SR_CONTRACTS,
    TC_CONTRACTS,
    TESTS_UNIT,
    Ctx,
    gate,
    load,
    schema_check,
    split_frontmatter,
)

IMPL_UNITS = L6 / "S0/implementation-units.json"
UNIT_FIELDS = ("unit_id", "doc", "du_id", "responsibility", "api_refs", "ac_refs", "tc_refs", "ut_refs")
UNIT_ID = re.compile(r"^IU-[A-Z0-9]+-\d{2}$")
CODE_TOKEN = re.compile(r"`([^`\n]+)`")
# 「準用」は「別の AC を借りてきて trace の代わりにする」書き方であり、意味接続の抜け穴になる
# trace を「借りて」済ませる言い回し。ID の代わりにこれらが立つと意味接続が空洞になる
TRACE_SUBSTITUTES = ("準用", "準じる", "準ずる", "同等", "相当をもって", "に倣う", "に習う",
                     "同様に扱う", "踏襲", "流用", "借用", "代用")


# どの契約にも現れる汎用語は「ドメイン語の共有」の根拠にしない（独立レビュー R2-01）
GENERIC_TERMS = frozenset({
    "raise", "raises", "return", "returns", "value", "values", "conn", "clock", "none",
    "error", "errors", "result", "check", "state", "table", "insert", "update", "select",
    "delete", "event", "entity", "input", "output", "param", "params",
})


def identifiers(s: str) -> set[str]:
    """ドメイン語（snake_case 識別子・例外型などの CamelCase）を抜き出す。

    **単語境界つき**で拾う（`GateRejected` から `ejected` のような部分文字列を作らない —
    独立レビュー R2-01）。CamelCase は語全体と構成語の両方を返し、汎用語は除く。
    """
    words = set(re.findall(r"\b[a-z][a-z_]{4,}\b", s))
    for camel in re.findall(r"\b[A-Z][a-zA-Z]{5,}\b", s):
        words.add(camel)
        words |= {w.lower() for w in re.findall(r"[A-Z][a-z]{3,}", camel)}
    return {w for w in words if w.lower() not in GENERIC_TERMS}


AC_PROSE_FIELDS = ("given", "when", "then", "expected_state", "expected_db_delta",
                   "expected_evidence", "error_type", "forbidden_side_effects")


def ac_identifiers(ac: dict) -> set[str]:
    return identifiers(" ".join(str(ac.get(k, "")) for k in AC_PROSE_FIELDS))


def api_name(api: dict) -> str:
    m = re.search(r"def (\w+)", api["signature"])
    return m.group(1) if m else ""


def api_text(api: dict) -> str:
    """API 契約の全文（署名・pre・post・raises）。責務が明記されているかの照合対象。"""
    return " ".join([api["signature"], *api.get("precondition", []), *api.get("postcondition", []),
                     *[f"{r.get('type', '')} {r.get('when', '')}" for r in api.get("raises", [])]])


def detect_impl_unit_faults(ctx: Ctx, units_path: Path = IMPL_UNITS) -> list[str]:
    """L6 の責務が API・AC・TC・UT まで意味接続されているかを検査する（PO 指示 §1）。

    「同じ DU を指しているから接続済み」を PASS にしない: 責務は **API 1 本**へ接続し、
    その API の pre／post に責務の識別子が現れ、AC／TC／UT が当該振る舞いを検証していることまでを
    要求する。「準用」のような借用表現で trace を代替できない。
    """
    bad: list[str] = []
    if not units_path.exists():
        return ["implementation-units.json が存在しない（L6 責務の API 接続が機械可読でない）"]
    doc_json = load(units_path)
    items = doc_json.get("items")
    raw_items = json.dumps(items, ensure_ascii=False)
    for w in TRACE_SUBSTITUTES:
        if w in raw_items:
            bad.append(f"implementation-units.json の items に trace 代替表現『{w}』がある")
    if not isinstance(items, list) or not items:
        return bad + ["implementation-units.json の items が空"]

    du_by_id = {d["id"]: d for d in ctx.duc}
    ac_by_id = {a["id"]: a for a in ctx.acc}
    ac_ids = set(ac_by_id)
    doc_reqs: dict[str, set[str]] = {}
    tc_by_id = {t["id"]: t for t in ctx.tcc}
    seen_ids: set[str] = set()
    owned: dict[tuple[str, str], list[str]] = {}
    doc_dus: dict[str, set[str]] = {}
    doc_bodies: dict[str, str] = {}

    for i, u in enumerate(items):
        if not isinstance(u, dict):
            bad.append(f"items[{i}] が object でない")
            continue
        uid = u.get("unit_id", f"items[{i}]")
        miss = [f for f in UNIT_FIELDS if f not in u]
        if miss:
            bad.append(f"{uid}: 必須項目の欠落 {miss}")
            continue
        if not UNIT_ID.match(u["unit_id"]) or u["unit_id"] in seen_ids:
            bad.append(f"{uid}: unit_id が規約外か重複")
        seen_ids.add(u["unit_id"])
        doc = u["doc"]
        p = ctx_root(doc)
        if not p.exists() or "/S0/" not in doc:
            bad.append(f"{uid}: doc {doc} が S0 の L6 機能設計として実在しない")
            continue
        if doc not in doc_bodies:
            fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
            doc_bodies[doc] = body
            doc_dus[doc] = set((fm or {}).get("dus") or [])
            doc_reqs[doc] = set(((fm or {}).get("traces") or [])
                                + ((fm or {}).get("forward_refs") or []))
        du = du_by_id.get(u["du_id"])
        if du is None:
            bad.append(f"{uid}: du_id {u['du_id']} が DU 契約に存在しない")
            continue
        if doc not in du["trace"].get("feature_design", []):
            bad.append(f"{uid}: {u['du_id']} の feature_design に {doc} が無い（DU↔文書の対応が非対称）")
        if u["du_id"] not in doc_dus[doc]:
            bad.append(f"{uid}: {doc} の frontmatter.dus に {u['du_id']} が無い")
        names = {api_name(a): a for a in du["apis"]}
        refs = u["api_refs"]
        if not isinstance(refs, list) or not refs:
            bad.append(f"{uid}: api_refs が空（DU 参照だけでは責務を接続したことにしない）")
            continue
        unknown = [r for r in refs if r not in names]
        if unknown:
            bad.append(f"{uid}: api_refs {unknown} が {u['du_id']} の API に存在しない")
            continue
        text = " ".join(api_text(names[r]) for r in refs)
        tokens = CODE_TOKEN.findall(u["responsibility"])
        if len(tokens) < 2:
            bad.append(f"{uid}: responsibility に識別子（`...`）が 2 個未満"
                       "（何の振る舞いかを API 契約の語で書く）")
        missing = [t for t in tokens if t not in text]
        if missing:
            bad.append(f"{uid}: responsibility の {missing} が API の pre/post に現れない"
                       "（責務が API 契約に明記されていない）")
        for w in TRACE_SUBSTITUTES:
            if w in u["responsibility"]:
                bad.append(f"{uid}: responsibility に trace 代替表現『{w}』")
        acs = u["ac_refs"]
        if not acs:
            bad.append(f"{uid}: ac_refs が空")
        for a in acs:
            if a not in ac_ids:
                bad.append(f"{uid}: ac_refs の {a} が AC 契約に存在しない")
            elif a not in du["trace"].get("ac", []):
                bad.append(f"{uid}: ac_refs の {a} が {u['du_id']} の trace.ac に無い")
        tcs = u["tc_refs"]
        if not tcs:
            bad.append(f"{uid}: tc_refs が空")
        for t in tcs:
            if t not in tc_by_id:
                bad.append(f"{uid}: tc_refs の {t} が TC 契約に存在しない")
            elif not set(tc_by_id[t].get("ac", [])) & set(acs):
                bad.append(f"{uid}: tc_refs の {t} が ac_refs のどれも検証していない")
        for a in acs:
            if a in ac_ids and not any(a in tc_by_id.get(t, {}).get("ac", []) for t in tcs):
                bad.append(f"{uid}: ac_refs の {a} を検証する TC が tc_refs に無い")
        # ID の所属だけでは「その振る舞いを検証している」ことにならない（独立レビュー R1-04）。
        # AC は (a) API 契約と**同じドメイン語**を共有するか、(b) 当該文書が trace する要求に属する。
        want = doc_reqs[doc]
        api_ids = identifiers(text)
        # **1 件でも**繋がっていれば良い、にはしない（独立レビュー R2-01）。全 ac_ref を個別に問う
        for a in acs:
            if a not in ac_by_id:
                continue
            if not (ac_identifiers(ac_by_id[a]) & api_ids) and ac_by_id[a].get("target") not in want:
                bad.append(f"{uid}: ac_refs の {a} が API 契約の語も文書の trace 先要求"
                           f"（{sorted(want)}）も共有しない（ID の所属だけで意味接続を名乗っている）")
        uts = u["ut_refs"]
        if not uts:
            bad.append(f"{uid}: ut_refs が空（API の振る舞いを検証する UT が無い）")
        allowed = {t for r in refs for t in names[r].get("ut", [])}
        stray = [t for t in uts if t not in allowed]
        if stray:
            bad.append(f"{uid}: ut_refs {stray[:2]} が api_refs の UT 割当に無い")
        # UT 名が API を名指ししていること（割当表の所属だけを根拠にしない — 独立レビュー R1-04）
        parts = {w for r in refs for w in r.split("_") if len(w) >= 4}
        if uts and parts and not any(w in u2 for u2 in uts for w in parts):
            bad.append(f"{uid}: ut_refs のどれも API 名（{sorted(parts)}）を含まない"
                       "（別 API のテストで検証済みを名乗れない）")
        if u["unit_id"] not in doc_bodies[doc]:
            bad.append(f"{uid}: 文書 {doc} に unit_id が現れない（JSON と文書が接続していない）")
        key = (u["du_id"], ",".join(sorted(refs)))
        for prev in owned.get(key, []):
            pu = next(x for x in items if x["unit_id"] == prev)
            if set(pu["ac_refs"]) & set(acs):
                bad.append(f"{uid}: {prev} と同じ API・重なる AC を主張している（責務の重複）")
        owned.setdefault(key, []).append(u["unit_id"])

    # 被覆: S0 文書が機能設計を担う DU は、全 API・全 AC がどれかの責務へ接続している
    for did, du in du_by_id.items():
        if not any("/S0/" in f for f in du["trace"].get("feature_design", [])):
            continue
        mine = [u for u in items if isinstance(u, dict) and u.get("du_id") == did]
        covered_api = {r for u in mine for r in u.get("api_refs", [])}
        for a in du["apis"]:
            if api_name(a) not in covered_api:
                bad.append(f"{did}: API {api_name(a)} を担う責務が無い")
        covered_ac = {a for u in mine for a in u.get("ac_refs", [])}
        for a in du["trace"].get("ac", []):
            if a not in covered_ac:
                bad.append(f"{did}: AC {a} を担う責務が無い")
    for doc, dus in doc_dus.items():
        got = {u["du_id"] for u in items if isinstance(u, dict) and u.get("doc") == doc}
        if got != dus:
            bad.append(f"{doc}: 責務の DU 集合 {sorted(got)} が frontmatter.dus {sorted(dus)} と不一致")
    for p in sorted(L6.rglob("*.md")):   # S0 だけでなく L6 全体（S1 の trace 代替も拒否する）
        body = p.read_text(encoding="utf-8")
        for w in TRACE_SUBSTITUTES:
            if w in body:
                bad.append(f"{p.name}: trace 代替表現『{w}』が本文にある")
    return bad


def ctx_root(rel_path: str) -> Path:
    from tools.gates.common import ROOT
    return ROOT / rel_path


HOLLOW = re.compile(r"TBD|TODO|FIXME|後で書く|後で埋め|後述予定|要検討|仮置き|placeholder|XXX")


def detect_api_ut_faults(dus: list[dict], tests_dir: Path = TESTS_UNIT) -> list[str]:
    """API 単位の UT 割当・参照実在・設計リンクの欠陥を列挙する。"""
    bad: list[str] = []
    for d in dus:
        uts = set(d["trace"]["ut"])
        api_uts: set[str] = set()
        for a in d["apis"]:
            refs = a.get("ut") or []
            if not refs:
                bad.append(f"{d['id']}:{a['signature'][:28]}:UTなし")
                continue
            api_uts |= set(refs)
            if not set(refs) <= uts:
                bad.append(f"{d['id']}:{a['signature'][:28]}:trace外UT")
        if uts - api_uts:
            bad.append(f"{d['id']}:宙吊りUT{sorted(uts - api_uts)[:2]}")
        owner_apis: dict[str, set] = {}
        for a in d["apis"]:
            m0 = re.match(r"def (\w+)", a["signature"])
            if m0:
                for u in a.get("ut", []):
                    owner_apis.setdefault(u, set()).add(m0.group(1))
        for ref in sorted(uts):
            if "::" not in ref:
                bad.append(f"{d['id']}:{ref}:形式")
                continue
            fname, tname = ref.split("::", 1)
            fp = tests_dir / fname
            if not fp.exists():
                bad.append(f"{d['id']}:{ref}:ファイル不在")
                continue
            txt = fp.read_text(encoding="utf-8")
            m = re.search(rf"\ndef {re.escape(tname)}\b", txt)
            if m is None:
                bad.append(f"{d['id']}:{ref}:def 不在")
                continue
            head = txt[:m.start()]
            decos = head[head.rfind("\n\n"):]
            body = txt[m.start():][:600]
            if "skip" in decos or "NotImplementedError" in body:
                owners = owner_apis.get(ref, set())
                if d["id"] not in decos or not (owners and any(n in decos for n in owners)):
                    bad.append(f"{d['id']}:{ref}:設計リンク不備")
    return bad


def run(ctx: Ctx) -> None:
    _ledger(ctx)
    _contracts(ctx)
    iu = detect_impl_unit_faults(ctx)
    gate("G-L6-IMPLEMENTATION-TRACE", not iu,
         "L6 の責務が API 1 本へ接続し、その pre/post に責務が明記され、AC／TC／UT が当該振る舞いを"
         f"検証している（DU 参照だけ・『準用』での代替を拒否） (違反={iu[:3]})")


def _ledger(ctx: Ctx) -> None:
    dus = ctx.dus
    duids = [d["id"] for d in dus]
    cmpids = {c["id"] for c in ctx.comps}
    gate("G-DU-CNT", len(dus) == 23, f"DU=23 (実={len(dus)})")
    gate("G-DU-UNIQ", len(duids) == len(set(duids)), "DU ID 重複ゼロ")
    ducmp = {d["cmp"] for d in dus}
    dufn = [f for d in dus for f in d["fn_ids"]]
    gate("G-DU-CMP", ducmp == cmpids,
         f"DU↔CMP 双方向 (不明={sorted(ducmp - cmpids)}, 未カバー={sorted(cmpids - ducmp)})")
    gate("G-DU-FN", len(dufn) == len(set(dufn)) and set(dufn) == ctx.s0_fn,
         f"DU が S0 25 FN を重複なく完全被覆 (差分={sorted(set(dufn) ^ ctx.s0_fn)})")


def _contracts(ctx: Ctx) -> None:
    duc = ctx.duc
    schema = load(DU_SCHEMA)
    ledger = {i["id"]: i for i in ctx.dus}
    d_errs: list[str] = []
    for it in duc:
        d_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(schema, it)]
    duc_ids = {i["id"] for i in duc}
    mod_bad = [it["id"] for it in duc
               if it["id"] in ledger and ledger[it["id"]]["module"] != it["module"]]
    gate("G-DU-API", not d_errs and duc_ids == set(ledger) and not mod_bad,
         f"DU 実装契約: schema 適合＋DU23 被覆＋module 一致 "
         f"(err={d_errs[:3]}, 差={sorted(duc_ids ^ set(ledger))}, module={mod_bad})")

    dbc_bad = [f"{it['id']}:{a['signature'][:30]}" for it in duc for a in it["apis"]
               if not a["precondition"] or not a["postcondition"]]
    gate("G-DU-DBC", not dbc_bad, f"全公開 API に pre/post (欠落={dbc_bad[:3]})")

    taxonomy = ERROR_TAXONOMY.read_text(encoding="utf-8")
    unknown_err = sorted({r["type"] for it in duc for a in it["apis"] for r in a["raises"]
                          if r["type"].split("（")[0] not in taxonomy})
    gate("G-DU-ERROR", not unknown_err, f"raises 型がエラー分類正本に掲載 (未掲載={unknown_err[:5]})")

    tbl_bad = detect_unknown_tables(duc, ctx.ddl_tables)
    gate("G-DU-DATA", not tbl_bad, f"DU の DB read/write が DDL 実在テーブルのみ (未知={tbl_bad[:5]})")

    ut_faults = detect_api_ut_faults(duc)
    gate("G-API-UT", not ut_faults,
         "全 DU の API 単位 UT 割当・参照実在・設計リンク（実行検証は S0.1 で red→green） "
         f"(欠陥={ut_faults[:5]})")

    hollow_hits: list[str] = []
    for p in (BR_CONTRACTS, FR_CONTRACTS, SR_CONTRACTS, AC_CONTRACTS, NFR_CONTRACTS,
              TC_CONTRACTS, CMP_CONTRACTS, DU_CONTRACTS):
        txt = p.read_text(encoding="utf-8")
        for m in HOLLOW.finditer(txt):
            hollow_hits.append(f"{p.name}:{m.group(0)}")
    gate("G-NO-HOLLOW-DESIGN", not hollow_hits,
         f"契約正本にプレースホルダなし (検出={sorted(set(hollow_hits))[:5]})")
