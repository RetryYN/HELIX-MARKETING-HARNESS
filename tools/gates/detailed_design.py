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
    api_clauses,
    api_name,
    gate,
    load,
    schema_check,
    split_frontmatter,
    ut_nodeids,
)

IMPL_UNITS = L6 / "S0/implementation-units.json"
IMPL_UNIT_SCHEMA = L6 / "S0/implementation-unit.schema.json"
# trace を「借りて」済ませる言い回し。ID の代わりにこれらが立つと意味接続が空洞になる
TRACE_SUBSTITUTES = ("準用", "準じる", "準ずる", "同等", "相当をもって", "に倣う", "に習う",
                     "同様に扱う", "踏襲", "流用", "借用", "代用")


def api_index(du: dict) -> dict[str, dict]:
    return {a["api_id"]: a for a in du["apis"]}


def clause_ids(api: dict) -> list[str]:
    return [c["clause_id"] for c in api_clauses(api)]


def ac_clause_map(acs: list[dict]) -> dict[str, set[str]]:
    """AC → その AC が検証すると宣言した API 契約節。"""
    return {a["id"]: set(a.get("verifies_clause_refs") or []) for a in acs}


def ut_clause_map(du: dict) -> dict[tuple[str, str], set[str]]:
    """(api_id, nodeid) → その UT が検証すると宣言した契約節。"""
    return {(a["api_id"], u["nodeid"]): set(u.get("clause_refs") or [])
            for a in du["apis"] for u in a.get("ut", [])}


def detect_impl_unit_faults(ctx: Ctx, units_path: Path = IMPL_UNITS) -> list[str]:
    """L6 の責務が API 契約節まで**構造参照**で接続されているかを検査する（PO 指示 §2）。

    接続の根拠は ID だけである: 責務は `api_ref`（1 件）と `clause_refs`（当該 API の契約節）を
    持ち、`ac_refs` の AC と `ut_refs` の UT が**同じ契約節**を参照していなければならない。
    API 名・テスト名・日本語語彙の部分一致は根拠にしない（語彙一致検査は廃止した）。
    全 API 契約節は AC 被覆か理由付き `na_reason` のいずれかを持つ。
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

    schema = load(IMPL_UNIT_SCHEMA)
    du_by_id = {d["id"]: d for d in ctx.duc}
    ac_by_id = {a["id"]: a for a in ctx.acc}
    ac_clauses = ac_clause_map(ctx.acc)
    tc_by_id = {t["id"]: t for t in ctx.tcc}
    seen_ids: set[str] = set()
    owned: dict[str, list[str]] = {}
    doc_dus: dict[str, set[str]] = {}
    doc_bodies: dict[str, str] = {}

    for i, u in enumerate(items):
        if not isinstance(u, dict):
            bad.append(f"items[{i}] が object でない")
            continue
        uid = u.get("unit_id", f"items[{i}]")
        errs = schema_check(schema, u)
        if errs:
            bad.append(f"{uid}: schema 違反 {errs[:2]}")
            continue
        if u["unit_id"] in seen_ids:
            bad.append(f"{uid}: unit_id が重複")
        seen_ids.add(u["unit_id"])
        doc = u["doc"]
        p = ctx_root(doc)
        if not p.exists():
            bad.append(f"{uid}: doc {doc} が S0 の L6 機能設計として実在しない")
            continue
        if doc not in doc_bodies:
            fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
            doc_bodies[doc] = body
            doc_dus[doc] = set((fm or {}).get("dus") or [])
        du = du_by_id.get(u["du_id"])
        if du is None:
            bad.append(f"{uid}: du_id {u['du_id']} が DU 契約に存在しない")
            continue
        if doc not in du["trace"].get("feature_design", []):
            bad.append(f"{uid}: {u['du_id']} の feature_design に {doc} が無い（DU↔文書の対応が非対称）")
        if u["du_id"] not in doc_dus[doc]:
            bad.append(f"{uid}: {doc} の frontmatter.dus に {u['du_id']} が無い")
        api = api_index(du).get(u["api_ref"])
        if api is None:
            bad.append(f"{uid}: api_ref {u['api_ref']} が {u['du_id']} の API に存在しない")
            continue
        mine = set(clause_ids(api))
        cls = list(u["clause_refs"])
        stray_c = [c for c in cls if c not in mine]
        if stray_c:
            bad.append(f"{uid}: clause_refs {stray_c[:2]} が {u['api_ref']} の契約節でない")
            continue
        for w in TRACE_SUBSTITUTES:
            if w in u["responsibility"]:
                bad.append(f"{uid}: responsibility に trace 代替表現『{w}』")
        acs = list(u["ac_refs"])
        for a in acs:
            if a not in ac_by_id:
                bad.append(f"{uid}: ac_refs の {a} が AC 契約に存在しない")
            elif a not in du["trace"].get("ac", []):
                bad.append(f"{uid}: ac_refs の {a} が {u['du_id']} の trace.ac に無い")
        uts = list(u["ut_refs"])
        umap = ut_clause_map(du)
        stray_u = [t for t in uts if (u["api_ref"], t) not in umap]
        if stray_u:
            bad.append(f"{uid}: ut_refs {stray_u[:2]} が {u['api_ref']} の UT 割当に無い")
        # 文書の trace 先が同じ・DU が同じ、では PASS にしない。**同じ契約節**を指していること
        for c in cls:
            if not any(c in ac_clauses.get(a, set()) for a in acs):
                bad.append(f"{uid}: clause {c} を検証する AC が ac_refs に無い"
                           "（AC が同じ契約節を参照していない）")
            if not any(c in umap.get((u["api_ref"], t), set()) for t in uts):
                bad.append(f"{uid}: clause {c} を検証する UT が ut_refs に無い"
                           "（UT が同じ契約節を参照していない）")
        for a in acs:
            if a in ac_by_id and not (ac_clauses.get(a, set()) & set(cls)):
                bad.append(f"{uid}: ac_refs の {a} が clause_refs のどの節も検証していない"
                           "（AC の所属だけで接続を名乗っている）")
        for t in uts:
            if (u["api_ref"], t) in umap and not (umap[(u["api_ref"], t)] & set(cls)):
                bad.append(f"{uid}: ut_refs の {t} が clause_refs のどの節も検証していない")
        tcs = list(u["tc_refs"])
        for t in tcs:
            if t not in tc_by_id:
                bad.append(f"{uid}: tc_refs の {t} が TC 契約に存在しない")
            elif not set(tc_by_id[t].get("ac", [])) & set(acs):
                bad.append(f"{uid}: tc_refs の {t} が ac_refs のどれも検証していない")
        for a in acs:
            if a in ac_by_id and not any(a in tc_by_id.get(t, {}).get("ac", []) for t in tcs):
                bad.append(f"{uid}: ac_refs の {a} を検証する TC が tc_refs に無い")
        if u["unit_id"] not in doc_bodies[doc]:
            bad.append(f"{uid}: 文書 {doc} に unit_id が現れない（JSON と文書が接続していない）")
        for prev in owned.get(u["api_ref"], []):
            pu = next(x for x in items if x["unit_id"] == prev)
            dup = set(pu["clause_refs"]) & set(cls)
            if dup:
                bad.append(f"{uid}: {prev} と同じ API の契約節 {sorted(dup)[:2]} を重複して主張している")
        owned.setdefault(u["api_ref"], []).append(u["unit_id"])

    # 被覆: S0 文書が機能設計を担う DU は、全 API・全 AC がどれかの責務へ接続している
    for did, du in du_by_id.items():
        if not any("/S0/" in f for f in du["trace"].get("feature_design", [])):
            continue
        mine_u = [u for u in items if isinstance(u, dict) and u.get("du_id") == did]
        covered_api = {u["api_ref"] for u in mine_u if isinstance(u.get("api_ref"), str)}
        ac_clauses_all = {c for a in ctx.acc for c in (a.get("verifies_clause_refs") or [])}
        for a in du["apis"]:
            # AC が 1 節も検証していない API は、全契約節が理由付き N/A である（別途検査）。
            # 実装責務として主張できる振る舞いが無いので、責務の欠落として扱わない。
            if not (set(clause_ids(a)) & ac_clauses_all):
                continue
            if a["api_id"] not in covered_api:
                bad.append(f"{did}: API {a['api_id']} を担う責務が無い")
        covered_ac = {a for u in mine_u for a in u.get("ac_refs", [])}
        # 契約節を検証する AC（＝実装責務に落ちる AC）だけを被覆対象にする。
        # CI・ratchet・DDL を観測する AC は clause_na_reason 付きで責務の外に置く。
        ac_by_id_all = {a["id"]: a for a in ctx.acc}
        own_clauses = {c for x in du["apis"] for c in clause_ids(x)}
        for a in du["trace"].get("ac", []):
            # この DU の API 契約節を検証している AC だけが、この DU の責務へ落ちる。
            # 他 DU の節だけを検証する AC は、その DU 側の責務が担う。
            if not (set(ac_by_id_all.get(a, {}).get("verifies_clause_refs") or []) & own_clauses):
                continue
            if a not in covered_ac:
                bad.append(f"{did}: AC {a} を担う責務が無い")
    for doc, dus in doc_dus.items():
        got = {u["du_id"] for u in items if isinstance(u, dict) and u.get("doc") == doc}
        if got != dus:
            bad.append(f"{doc}: 責務の DU 集合 {sorted(got)} が frontmatter.dus {sorted(dus)} と不一致")
    bad += detect_clause_coverage_faults(ctx)
    for p in sorted(L6.rglob("*.md")):   # S0 だけでなく L6 全体（S1 の trace 代替も拒否する）
        body = p.read_text(encoding="utf-8")
        for w in TRACE_SUBSTITUTES:
            if w in body:
                bad.append(f"{p.name}: trace 代替表現『{w}』が本文にある")
    return bad


def detect_clause_coverage_faults(ctx: Ctx) -> list[str]:
    """全 API 契約節が AC 被覆か理由付き N/A のいずれかを持つことを検査する（PO 指示 §2）。

    AC・UT の clause 参照は**自分が属する API の節**に限る（他 API の節を指して被覆を装えない）。
    AC 被覆と `na_reason` は排他である（検証されているのに『AC 無し』の理由を書けない）。

    N/A を自由記述の免罪符にしない（独立レビュー R1-02）: 理由は**閉じた語彙**の分類で始まり、
    AC が 1 節も検証していない API は `uncovered-apis.json` へ**明示登録**されていなければならない
    （登録集合と実際の集合が厳密一致 — 黙って API を台帳から消せない）。件数のラチェットは baseline。
    """
    bad: list[str] = []
    ac_clauses = ac_clause_map(ctx.acc)
    all_clauses: dict[str, str] = {}      # clause_id → api_id
    du_of_api: dict[str, str] = {}
    seen_api: set[str] = set()
    seen_clause: set[str] = set()
    for d in ctx.duc:
        for a in d["apis"]:
            if a["api_id"] in seen_api:
                bad.append(f"{a['api_id']}: api_id が重複している（安定 ID の一意性違反）")
            seen_api.add(a["api_id"])
            for c in clause_ids(a):
                if c in seen_clause:
                    bad.append(f"{c}: clause_id が重複している（安定 ID の一意性違反）")
                seen_clause.add(c)
            du_of_api[a["api_id"]] = d["id"]
            for c in clause_ids(a):
                all_clauses[c] = a["api_id"]
            for u in a.get("ut", []):
                stray = [c for c in u.get("clause_refs", []) if c not in set(clause_ids(a))]
                if stray:
                    bad.append(f"{d['id']}:{u['nodeid']}: clause_refs {stray[:2]} が"
                               f" {a['api_id']} の契約節でない")
    du_ac = {d["id"]: set(d["trace"].get("ac", [])) for d in ctx.duc}
    covered: set[str] = set()
    for ac in ctx.acc:
        refs = ac_clauses[ac["id"]]
        for c in refs:
            if c not in all_clauses:
                bad.append(f"{ac['id']}: verifies_clause_refs の {c} が実在しない")
                continue
            owner = du_of_api[all_clauses[c]]
            if ac["id"] not in du_ac.get(owner, set()):
                bad.append(f"{ac['id']}: {c} は {owner} の節だが {owner} の trace.ac に無い")
                continue
            covered.add(c)
        reason = ac.get("clause_na_reason")
        if refs and reason:
            bad.append(f"{ac['id']}: 契約節を検証しているのに clause_na_reason を持つ")
        if not refs and any(ac["id"] in v for v in du_ac.values()) and not reason:
            bad.append(f"{ac['id']}: DU に割当られているのに verifies_clause_refs が空"
                       "（API 契約節でないものを検証するなら clause_na_reason を書く）")
    for d in ctx.duc:
        for a in d["apis"]:
            for cl in api_clauses(a):
                cid = cl["clause_id"]
                na = cl.get("na_reason")
                if cid in covered and na:
                    bad.append(f"{cid}: AC 被覆があるのに na_reason を持つ")
                elif cid not in covered and not na:
                    bad.append(f"{cid}: 検証する AC も na_reason も無い（契約節が未被覆）")
                elif na and not na.startswith(NA_CATEGORIES):
                    bad.append(f"{cid}: na_reason が分類語彙 {NA_CATEGORIES} で始まっていない"
                               "（自由記述で被覆欠落を免除しない）")
    bad += detect_uncovered_api_ledger_faults(ctx, covered)
    return bad


# N/A 理由の閉じた語彙。自由記述で「AC が無い」を正当化させない（独立レビュー R1-02）
NA_CATEGORIES = ("呼出側義務:", "配線時保証:", "他 API で検証:", "受入基準未設定:")
UNCOVERED_APIS = L6 / "S0/uncovered-apis.json"


def detect_uncovered_api_ledger_faults(ctx: Ctx, covered: set[str],
                                       ledger_path: Path = UNCOVERED_APIS) -> list[str]:
    """AC が 1 節も検証していない API の集合が、明示台帳と**厳密一致**しているかを検査する。

    この集合は G-L6-IMPLEMENTATION-TRACE の責務被覆から除外される唯一の経路であり、
    「na_reason を書けば API ごと消える」抜け道になり得る。台帳への登録（＝承認対象の変更）を
    必須にして、追加・削除が必ず差分として見えるようにする。
    """
    if not ledger_path.exists():
        return [f"{ledger_path.name} が無い（AC 未被覆 API の明示台帳が存在しない）"]
    ledger = load(ledger_path)
    items = ledger.get("items", [])
    bad: list[str] = []
    seen: set[str] = set()
    for it in items:
        if it.get("api_id") in seen:
            bad.append(f"{it.get('api_id')}: uncovered-apis.json に重複登録がある")
        seen.add(it.get("api_id"))
    declared = {i["api_id"]: i for i in items}
    real = {a["api_id"]: (d["id"], api_name(a)) for d in ctx.duc for a in d["apis"]}
    actual = {a["api_id"] for d in ctx.duc for a in d["apis"]
              if not (set(clause_ids(a)) & covered)}
    for extra in sorted(actual - set(declared)):
        bad.append(f"{extra}: AC が 1 節も検証していないのに uncovered-apis.json へ未登録")
    for stale in sorted(set(declared) - actual):
        bad.append(f"{stale}: uncovered-apis.json に登録されているが実際は AC 被覆がある")
    for aid, it in sorted(declared.items()):
        if not it.get("reason") or not it.get("resolution_slice"):
            bad.append(f"{aid}: uncovered-apis.json の reason／resolution_slice が空")
        elif it["resolution_slice"] not in RESOLUTION_SLICES:
            bad.append(f"{aid}: resolution_slice が語彙 {RESOLUTION_SLICES} 外")
        # 台帳のメタデータが実契約と食い違っていないか（虚偽の DU／関数名を置けない）
        if aid in real and (it.get("du_id"), it.get("function")) != real[aid]:
            bad.append(f"{aid}: uncovered-apis.json の du_id／function が実契約 {real[aid]} と不一致")
    return bad


RESOLUTION_SLICES = ("S0.1", "S1", "later")


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
            refs = ut_nodeids(a)
            if not refs:
                bad.append(f"{d['id']}:{a['api_id']}:UTなし")
                continue
            api_uts |= set(refs)
            if not set(refs) <= uts:
                bad.append(f"{d['id']}:{a['api_id']}:trace外UT")
        if uts - api_uts:
            bad.append(f"{d['id']}:宙吊りUT{sorted(uts - api_uts)[:2]}")
        owner_apis: dict[str, set] = {}
        for a in d["apis"]:
            m0 = re.match(r"def (\w+)", a["signature"])
            if m0:
                for u in ut_nodeids(a):
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
         "L6 の責務が api_ref 1 件＋契約節（clause_id）へ構造接続し、AC／UT が同じ節を参照し、"
         "全契約節が AC 被覆か理由付き N/A を持つ（語彙一致・借用表現での代替を拒否） "
         f"(違反={iu[:3]})")


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

    dbc_bad = [f"{it['id']}:{a['api_id']}" for it in duc for a in it["apis"]
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
