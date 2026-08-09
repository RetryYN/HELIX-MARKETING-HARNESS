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
    UPDATES,
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

    # 被覆: L6 文書が機能設計を担う DU はsliceを問わず、全 API・全 ACが責務へ接続している。
    # updates.json の更新軸と L6 のslice軸を混同し、S1責務をS0文書へ偽装配置してはならない。
    for did, du in du_by_id.items():
        if not du["trace"].get("feature_design"):
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
    api_names: dict[str, str] = {}
    for d in ctx.duc:
        for a in d["apis"]:
            if a["api_id"] in seen_api:
                bad.append(f"{a['api_id']}: api_id が重複している（安定 ID の一意性違反）")
            seen_api.add(a["api_id"])
            api_names[a["api_id"]] = api_name(a)
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
    observation_owners: dict[str, list[str]] = {}
    for ac in ctx.acc:
        refs = ac_clauses[ac["id"]]
        referenced_apis = {all_clauses[c] for c in refs if c in all_clauses}
        assertions = ac.get("api_observation_assertions") or {}
        for asserted_api, assertion in assertions.items():
            if asserted_api not in referenced_apis:
                bad.append(f"{ac['id']}: api_observation_assertions の {asserted_api} は"
                           " verifies_clause_refs で当該APIを参照していない")
                continue
            observation_owners.setdefault(asserted_api, []).append(ac["id"])
            action = assertion.get("action", "") if isinstance(assertion, dict) else ""
            function_name = api_names.get(asserted_api, "")
            if function_name and function_name not in action:
                bad.append(f"{ac['id']}:{asserted_api}: action が公開API {function_name} の"
                           "実呼出を示さない（別API assertionのコピーを拒否）")
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
            lv = a.get("verification_level")
            internal = lv in INTERNAL_LEVELS
            ut_refs = {c for u in a.get("ut", []) for c in u.get("clause_refs", [])}
            if internal:
                if len(a.get("internal_reason") or "") < 20:
                    bad.append(f"{a['api_id']}: verification_level={lv} なのに internal_reason が無い"
                               "（内部 API である理由を明示しない分類を認めない）")
                if a.get("internal_reason_code") not in INTERNAL_REASON_CODES:
                    bad.append(f"{a['api_id']}: internal_reason_code が閉じた語彙"
                               f" {INTERNAL_REASON_CODES} 外（{a.get('internal_reason_code')}）")
                # 宣言だけで検査を緩めさせない（独立レビュー R1-01）: 内部 API は**自分の振る舞い**
                # （postcondition・raises）の全節が UT／ITC へ直接接続していなければならない。
                # 呼出側義務・配線時保証で逃がせるのは precondition だけ。
                # AC 被覆で代替させない（独立レビュー R2-01）: 内部 API を名乗る以上、
                # その振る舞いは UT が直接検証していなければならない。
                own = [c["clause_id"] for c in (*a.get("postcondition", []), *a.get("raises", []))]
                loose = [c for c in own if c not in ut_refs]
                if loose:
                    bad.append(f"{a['api_id']}: 内部 API（{lv}）の post／raises {loose[:2]} が"
                               "UT の clause_refs に無い（内部分類は検証の免除ではない）")
            elif a.get("internal_reason") or a.get("internal_reason_code"):
                bad.append(f"{a['api_id']}: verification_level=acceptance なのに internal_reason 系を持つ")
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
                elif na and na.startswith(UNIT_CATEGORY) and cid not in ut_refs:
                    bad.append(f"{cid}: 『{UNIT_CATEGORY}』を名乗るのに UT の clause_refs に無い"
                               "（接続のない単体検証は主張できない）")
                elif na and na.startswith(GAP_CATEGORY):
                    if cid in ut_refs:
                        bad.append(f"{cid}: UT が本節を検証しているのに『{GAP_CATEGORY}』"
                                   f"（正しい分類は『{UNIT_CATEGORY}』）")
                    if internal:
                        bad.append(f"{a['api_id']}: 内部 API（{lv}）なのに契約節 {cid} が"
                                   f"『{GAP_CATEGORY}』（内部分類と未解決 gap は併存しない）")
    bad += detect_uncovered_api_ledger_faults(ctx, covered)
    ledger = load(UNCOVERED_APIS)
    resolved = ledger.get("resolved_items") or []
    if ledger.get("resolved_count") != len(resolved):
        bad.append("uncovered-apis.json: resolved_count がappend-only解消履歴の実数と不一致")
    resolved_ids = [it.get("api_id") for it in resolved]
    if len(resolved_ids) != len(set(resolved_ids)):
        bad.append("uncovered-apis.json: resolved_items の api_id が重複")
    for it in resolved:
        api_id = it.get("api_id")
        expected_owner = it.get("resolution_ac")
        if api_id not in api_names:
            bad.append(f"{api_id}: resolved_items が実在しないAPIを参照")
            continue
        if it.get("function") != api_names[api_id] or it.get("du_id") != du_of_api[api_id]:
            bad.append(f"{api_id}: resolved_items のdu_id/functionが現API契約と不一致")
        if expected_owner not in observation_owners.get(api_id, []):
            bad.append(f"{api_id}: resolution_ac={expected_owner} がAPI固有assertionを所有しない")
    for api_id in sorted(set(resolved_ids)):
        owners = observation_owners.get(api_id, [])
        if len(owners) != 1:
            bad.append(f"{api_id}: API固有の反証可能な api_observation_assertions が"
                       f"exactly-one ACに必要（実={owners}）")
    return bad


# N/A 理由の閉じた語彙。自由記述で「AC が無い」を正当化させない（独立レビュー R1-02）
UNIT_CATEGORY = "単体検証:"
# 未解決 gap。N/A ではなく「受入基準がまだ無い」という穴であり、設計クロージャーの障害になる
GAP_CATEGORY = "受入基準未設定:"
NA_CATEGORIES = ("呼出側義務:", "配線時保証:", "他 API で検証:", UNIT_CATEGORY, GAP_CATEGORY)
INTERNAL_LEVELS = ("unit", "integration")
# 内部 API の理由は閉じたコードで宣言する（自由記述で分類を正当化させない — 独立レビュー R1-01）
INTERNAL_REASON_CODES = ("startup-wiring", "read-only-accessor", "internal-delegation")
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
    # 内部 API（unit／integration）は AC を持たない設計判断が確定しているので未解決 gap ではない。
    # 台帳に載るのは「acceptance を名乗るのに AC が 1 件も無い」＝受入基準が未設定の API だけ。
    actual = {a["api_id"] for d in ctx.duc for a in d["apis"]
              if a.get("verification_level") not in INTERNAL_LEVELS
              and not (set(clause_ids(a)) & covered)}
    level = {a["api_id"]: a.get("verification_level") for d in ctx.duc for a in d["apis"]}
    for aid in sorted(k for k, v in level.items() if v in INTERNAL_LEVELS and k in declared):
        bad.append(f"{aid}: 内部 API（verification_level={level[aid]}）が未被覆 API 台帳に"
                   "登録されている（内部分類と未解決 gap は併存しない）")
    for extra in sorted(actual - set(declared)):
        bad.append(f"{extra}: AC が 1 節も検証していないのに uncovered-apis.json へ未登録")
    for stale in sorted(set(declared) - actual):
        bad.append(f"{stale}: uncovered-apis.json に登録されているが実際は AC 被覆がある")
    for aid, it in sorted(declared.items()):
        if not it.get("reason") or not it.get("resolution_update"):
            bad.append(f"{aid}: uncovered-apis.json の reason／resolution_update が空")
        # 台帳のメタデータが実契約と食い違っていないか（虚偽の DU／関数名を置けない）
        if aid in real and (it.get("du_id"), it.get("function")) != real[aid]:
            bad.append(f"{aid}: uncovered-apis.json の du_id／function が実契約 {real[aid]} と不一致")
    return bad


def update_of_du(ctx: Ctx) -> tuple[dict[str, str], list[str]]:
    """DU → 更新（S0.1／S0.2／S0.3）を DU 台帳の `fn_ids` と updates.json から**機械導出**する。

    slice（S0／S1／later ＝ いつ作るか）と update（S0 内の実装順序）は別軸である。
    台帳へ手入力された update 値は、この導出結果と一致しなければ受け付けない。
    """
    bad: list[str] = []
    fn_update: dict[str, str] = {}
    for u in load(UPDATES)["items"]:
        for f in u["fn_ids"]:
            if f in fn_update:
                bad.append(f"{f}: updates.json で複数更新に属している（{fn_update[f]}／{u['update']}）")
            fn_update[f] = u["update"]
    derived: dict[str, str] = {}
    for d in ctx.dus:
        miss = [f for f in d["fn_ids"] if f not in fn_update]
        got = sorted({fn_update[f] for f in d["fn_ids"] if f in fn_update})
        if miss:
            bad.append(f"{d['id']}: FN {miss[:2]} が updates.json のどの更新にも属さない")
        elif len(got) != 1:
            bad.append(f"{d['id']}: FN が複数更新に跨る {got}（更新境界が一意に決まらない）")
        else:
            derived[d["id"]] = got[0]
    return derived, bad


def detect_uncovered_update_faults(ctx: Ctx,
                                   ledger_path: Path = UNCOVERED_APIS) -> list[str]:
    """未被覆 API 台帳の解消先が update 軸で宣言され、DU→FN→updates.json の導出と一致するか。

    slice を解消先に書くと「いつ作るか」と「どの更新で閉じるか」が 1 欄に潰れる（PO 指示 §2）。
    """
    derived, bad = update_of_du(ctx)
    vocab = [u["update"] for u in load(UPDATES)["items"]]
    if not ledger_path.exists():
        return bad + [f"{ledger_path.name} が無い"]
    if "resolution_slice" in ledger_path.read_text(encoding="utf-8"):
        bad.append(f"{ledger_path.name}: resolution_slice が残存（slice と update の混同）")
    for it in load(ledger_path).get("items", []):
        aid = it.get("api_id")
        got = it.get("resolution_update")
        if not got:
            bad.append(f"{aid}: resolution_update が無い")
            continue
        if got not in vocab:
            bad.append(f"{aid}: resolution_update {got} が updates.json の更新語彙 {vocab} 外")
            continue
        want = derived.get(it.get("du_id", ""))
        if want is None:
            bad.append(f"{aid}: du_id {it.get('du_id')} の更新を DU 台帳から導出できない")
        elif got != want:
            bad.append(f"{aid}: resolution_update {got} が DU→FN→updates.json の導出 {want} と不一致")
    return bad


UPDATE_CLOSURE = L6 / "S0/update-closure.json"
CLOSURE_OWNERS = ("README.md", "CLAUDE.md")
CLOSED_PHRASE = "設計クロージャー完了"


def compute_update_closure(ctx: Ctx) -> tuple[dict[str, str], dict[str, int], list[str]]:
    """更新ごとの設計クロージャー状態を**実態から導出**する（宣言は参照しない）。

    closed の条件（PO 指示 §4）: 当該更新の未被覆 API = 0 ／ 全 API 契約節が AC・UT・ITC か
    正当な internal 分類（`受入基準未設定:` が残っていない）／AC を持つ API が実装単位を持つ。
    """
    derived, bad = update_of_du(ctx)
    ledger = load(UNCOVERED_APIS).get("items", []) if UNCOVERED_APIS.exists() else []
    units = load(IMPL_UNITS).get("items", []) if IMPL_UNITS.exists() else []
    unit_apis = {u.get("api_ref") for u in units if isinstance(u, dict)}
    ac_clauses_all = {c for a in ctx.acc for c in (a.get("verifies_clause_refs") or [])}
    uncovered: dict[str, int] = {}
    open_reasons: dict[str, list[str]] = {}
    for it in ledger:
        up = it.get("resolution_update")
        uncovered[up] = uncovered.get(up, 0) + 1
        open_reasons.setdefault(up, []).append(f"{it.get('api_id')}: 未被覆 API")
    for d in ctx.duc:
        up = derived.get(d["id"])
        if up is None:
            continue
        for a in d["apis"]:
            for cl in api_clauses(a):
                if (cl.get("na_reason") or "").startswith(GAP_CATEGORY):
                    open_reasons.setdefault(up, []).append(f"{cl['clause_id']}: {GAP_CATEGORY}")
            if (set(clause_ids(a)) & ac_clauses_all) and a["api_id"] not in unit_apis:
                open_reasons.setdefault(up, []).append(f"{a['api_id']}: 実装単位が無い")
    computed = {u["update"]: ("open" if open_reasons.get(u["update"]) else "closed")
                for u in load(UPDATES)["items"]}
    for up in sorted(open_reasons):
        if up not in computed:
            bad.append(f"{up}: updates.json に存在しない更新が解消先に宣言されている")
    return computed, {u: uncovered.get(u, 0) for u in computed}, bad


def detect_update_closure_faults(ctx: Ctx, closure_path: Path = UPDATE_CLOSURE) -> list[str]:
    """更新ごとの完了宣言が実態と一致し、現在地の正本行がその宣言と一致するかを検査する。"""
    computed, uncovered, bad = compute_update_closure(ctx)
    if not closure_path.exists():
        return bad + [f"{closure_path.name} が無い（更新単位の完了宣言が機械可読でない）"]
    items = load(closure_path).get("items", [])
    declared = {i.get("update"): i for i in items}
    if set(declared) != set(computed):
        bad.append(f"{closure_path.name} の更新集合 {sorted(declared)} が"
                   f" updates.json {sorted(computed)} と不一致")
    texts = {n: (ctx_root(n)).read_text(encoding="utf-8") for n in CLOSURE_OWNERS}
    for up in sorted(set(declared) & set(computed)):
        it = declared[up]
        got = it.get("design_closure")
        if got not in ("closed", "open"):
            bad.append(f"{up}: design_closure が closed／open 以外（{got}）")
            continue
        if got != computed[up]:
            bad.append(f"{up}: design_closure={got} が実態 {computed[up]} と不一致"
                       f"（未被覆 API={uncovered[up]}）")
        claim = it.get("current_state_claim") or ""
        if len(claim) < 8:
            bad.append(f"{up}: current_state_claim が無い（現在地と宣言が接続していない）")
            continue
        if (CLOSED_PHRASE in claim) != (computed[up] == "closed"):
            bad.append(f"{up}: current_state_claim『{claim}』が実態 {computed[up]} と矛盾する"
                       f"（closed のときだけ『{CLOSED_PHRASE}』を名乗れる）")
        if f"未被覆 API {uncovered[up]}" not in claim:
            bad.append(f"{up}: current_state_claim が実数『未被覆 API {uncovered[up]}』を含まない")
        for name, txt in texts.items():
            if txt.count(claim) != 1:
                bad.append(f"{name}: 現在地に『{claim}』が {txt.count(claim)} 回")
    return bad


def detect_s0_design_completion_faults(ctx: Ctx) -> list[str]:
    """S0 全更新の設計完遂を検査する。

    更新ごとの closure ゲートは、open を正直に宣言すれば PASS する状態整合検査である。
    それを S0 全体の完遂と取り違えないよう、導出状態がすべて closed であることを別に要求する。
    """
    computed, uncovered, bad = compute_update_closure(ctx)
    for update, state in sorted(computed.items()):
        if state != "closed":
            bad.append(
                f"{update}: design_closure={state}"
                f"（未被覆 API={uncovered.get(update, 0)}。S0 全体の設計完遂を名乗れない）"
            )
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
    uu = detect_uncovered_update_faults(ctx)
    gate("G-UNCOVERED-API-UPDATE", not uu,
         "未被覆 API 台帳の解消先が update 軸（updates.json の語彙）で宣言され、"
         "DU 台帳の fn_ids → updates.json から導出した更新と一致する（slice との混同・手入力の齟齬を拒否） "
         f"(違反={uu[:3]})")
    uc = detect_update_closure_faults(ctx)
    gate("G-UPDATE-DESIGN-CLOSURE", not uc,
         "更新（S0.1／S0.2／S0.3）ごとの設計クロージャー宣言が実態（未被覆 API=0・受入基準未設定の"
         "契約節ゼロ・AC を持つ API の実装単位実在）と一致し、README／CLAUDE.md の現在地が"
         "その宣言と実数まで一致する（closed のときだけ設計クロージャー完了を名乗れる） "
         f"(違反={uc[:3]})")
    complete = detect_s0_design_completion_faults(ctx)
    gate("G-S0-DESIGN-COMPLETE", not complete,
         "S0.1／S0.2／S0.3 がすべて導出上 closed で、open 更新・未被覆 API・"
         "受入基準未設定の契約節を残さない（状態整合PASSを全体完遂と取り違えない） "
         f"(違反={complete[:3]})")


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
