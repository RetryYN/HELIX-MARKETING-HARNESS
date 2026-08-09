"""detailed_design ゲートの単体テストと mutation test。"""

import json

import pytest

from tools.gates import detailed_design
from tools.gates.common import CTX, DU_SCHEMA, load, schema_check, ut_nodeids


def test_api_ut_assignment_is_complete() -> None:
    assert detailed_design.detect_api_ut_faults(CTX.duc) == []


def test_mutation_api_without_ut_is_detected() -> None:
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": []}, *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert any("UTなし" in f for f in faults)


def test_mutation_ut_pointing_at_missing_function_is_detected() -> None:
    ghost = {"nodeid": "test_db_connect.py::test_does_not_exist", "clause_refs": []}
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": [ghost]}, *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert faults, "存在しないテスト関数への参照が検出されない"


def test_mutation_empty_precondition_violates_dbc_schema() -> None:
    schema = load(DU_SCHEMA)["properties"]["apis"]["items"]
    mutated = {**CTX.duc[0]["apis"][0], "precondition": []}
    assert schema_check(schema, mutated), "pre 空の API が schema を通ってしまう"


def test_every_api_declares_pre_and_post() -> None:
    missing = [f"{d['id']}:{a['api_id']}" for d in CTX.duc for a in d["apis"]
               if not a["precondition"] or not a["postcondition"]]
    assert missing == []


def test_hollow_pattern_matches_placeholders() -> None:
    assert detailed_design.HOLLOW.search("ここは TBD")
    assert detailed_design.HOLLOW.search("仮置きの値")
    assert not detailed_design.HOLLOW.search("確定した設計")


# --- API 安定 ID・契約節 ID の構造（PO 指示 §2）---

def test_every_api_and_clause_has_a_stable_id() -> None:
    """api_id・clause_id が全 API・全契約節に付与され、リポジトリ全体で一意である。"""
    api_ids = [a["api_id"] for d in CTX.duc for a in d["apis"]]
    clause_ids = [c["clause_id"] for d in CTX.duc for a in d["apis"]
                  for c in detailed_design.api_clauses(a)]
    assert len(api_ids) == len(set(api_ids)) == 59
    assert len(clause_ids) == len(set(clause_ids))
    for d in CTX.duc:
        for a in d["apis"]:
            assert a["api_id"].startswith(f"API-{d['id'].replace('-', '')}-")
            for c in detailed_design.api_clauses(a):
                assert c["clause_id"].startswith(a["api_id"] + "-")


def test_every_ut_declares_the_clauses_it_verifies() -> None:
    """UT は nodeid だけでなく、自分が検証する契約節へ接続している。"""
    for d in CTX.duc:
        for a in d["apis"]:
            own = {c["clause_id"] for c in detailed_design.api_clauses(a)}
            for u in a["ut"]:
                assert u["clause_refs"], f"{d['id']}:{u['nodeid']}"
                assert set(u["clause_refs"]) <= own, f"{d['id']}:{u['nodeid']}"


def test_ut_nodeids_accessor_matches_trace() -> None:
    for d in CTX.duc:
        assert {u for a in d["apis"] for u in ut_nodeids(a)} == set(d["trace"]["ut"])


def test_every_clause_is_covered_by_ac_or_reasoned_na() -> None:
    assert detailed_design.detect_clause_coverage_faults(CTX) == []


# --- L6 実装単位の構造接続（PO 指示 §2）の検出能力 ---

def _units(tmp_path, mutate=None):
    """実 implementation-units.json を複製し、1 件だけ変異させたファイルを返す。"""
    src = json.loads(detailed_design.IMPL_UNITS.read_text(encoding="utf-8"))
    if mutate:
        mutate(src["items"])
    p = tmp_path / "implementation-units.json"
    p.write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def test_implementation_units_are_clean_on_real_tree() -> None:
    assert detailed_design.detect_impl_unit_faults(CTX) == []


def test_mutation_unknown_api_ref_is_detected(tmp_path) -> None:
    """変異: 実在しない API 安定 ID へ責務を接続できない。"""
    def m(items):
        items[0]["api_ref"] = "API-DU99-01"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("API に存在しない" in f or "schema 違反" in f for f in faults)


def test_mutation_api_ref_as_array_is_rejected_by_schema(tmp_path) -> None:
    """変異: api_ref を配列に戻すと schema が拒否する（1 責務 1 API）。"""
    def m(items):
        items[0]["api_ref"] = [items[0]["api_ref"]]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("schema 違反" in f for f in faults)


def test_mutation_extra_property_is_rejected(tmp_path) -> None:
    """変異: 専用 schema は追加プロパティを許さない。"""
    def m(items):
        items[0]["note"] = "後から足した自由記述"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("schema 違反" in f for f in faults)


def test_mutation_clause_of_another_api_is_detected(tmp_path) -> None:
    """変異: 他 API の契約節を自分の責務として主張できない。"""
    def m(items):
        other = "API-DU01-02-POST-01" if items[0]["api_ref"] != "API-DU01-02" \
            else "API-DU01-01-POST-01"
        items[0]["clause_refs"] = [other]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("の契約節でない" in f for f in faults)


def test_mutation_ac_not_verifying_the_clause_is_detected(tmp_path) -> None:
    """変異: 同じ DU・同じ文書 trace 先の AC でも、**同じ契約節**を参照していなければ拒否。

    語彙一致ではなく構造参照で落ちることを示すため、DU の trace.ac には属する AC を選ぶ。
    """
    victim = next(u for u in CTX_UNITS if len(u["ac_refs"]) >= 1)
    du = next(d for d in CTX.duc if d["id"] == victim["du_id"])
    ac_by_id = {a["id"]: a for a in CTX.acc}
    mine = set(victim["clause_refs"])
    alt = next((a for a in du["trace"]["ac"]
                if a in ac_by_id and ac_by_id[a].get("verifies_clause_refs")
                and not (set(ac_by_id[a]["verifies_clause_refs"]) & mine)), None)
    assert alt, "検査対象に適した AC が見つからない"

    def m(items):
        u = next(x for x in items if x["unit_id"] == victim["unit_id"])
        u["ac_refs"] = [alt]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("clause_refs のどの節も検証していない" in f for f in faults), faults
    assert not any("trace.ac に無い" in f and victim["unit_id"] in f for f in faults), \
        "所属検査で落ちており構造参照検査を実証できない"


def test_mutation_ut_not_verifying_the_clause_is_detected(tmp_path) -> None:
    """変異: 同じ API の UT でも、その契約節を検証していなければ責務の根拠にならない。"""
    target = None
    for u in CTX_UNITS:
        du = next(d for d in CTX.duc if d["id"] == u["du_id"])
        api = next(a for a in du["apis"] if a["api_id"] == u["api_ref"])
        alt = [x["nodeid"] for x in api["ut"]
               if not (set(x["clause_refs"]) & set(u["clause_refs"]))]
        if alt:
            target = (u["unit_id"], alt[:1])
            break
    assert target, "同一 API 内に非該当 UT を持つ責務が無い"

    def m(items):
        x = next(y for y in items if y["unit_id"] == target[0])
        x["ut_refs"] = target[1]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("を検証する UT が ut_refs に無い" in f or
               "clause_refs のどの節も検証していない" in f for f in faults), faults


def test_mutation_trace_substitute_word_is_detected(tmp_path) -> None:
    """変異: 「準用」で trace を代替できない。"""
    def m(items):
        items[0]["responsibility"] += "（準用）"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("準用" in f for f in faults)


def test_mutation_ac_outside_du_trace_is_detected(tmp_path) -> None:
    def m(items):
        items[0]["ac_refs"] = ["AC-71-1"] if "AC-71-1" not in items[0]["ac_refs"] \
            else ["AC-33-1"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("trace.ac に無い" in f or "を担う責務が無い" in f for f in faults)


def test_mutation_tc_not_verifying_the_ac_is_detected(tmp_path) -> None:
    """変異: 当該 AC を検証しない TC を貼っても接続とみなさない。"""
    def m(items):
        items[0]["tc_refs"] = ["TCC-71-1"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("検証していない" in f or "検証する TC が tc_refs に無い" in f for f in faults)


def test_mutation_ut_outside_api_assignment_is_detected(tmp_path) -> None:
    def m(items):
        items[0]["ut_refs"] = ["test_db_connect.py::test_connect_sets_foreign_keys_on"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("UT 割当に無い" in f for f in faults)


def test_mutation_uncovered_api_is_detected(tmp_path) -> None:
    """変異: どの責務も担わない API が残ると検出される（被覆の穴）。"""
    def m(items):
        for victim in [u for u in items if u["du_id"] == "DU-12"]:
            items.remove(victim)
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("を担う責務が無い" in f for f in faults)


def test_mutation_duplicate_clause_claim_on_same_api_is_detected(tmp_path) -> None:
    """変異: 同じ API の同じ契約節を 2 本の責務が主張できない（水増しの禁止）。"""
    def m(items):
        items.append(dict(items[0], unit_id="IU-DUPLICATE-99"))
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("重複して主張している" in f or "unit_id が重複" in f for f in faults)


def test_mutation_missing_unit_id_in_document_is_detected(tmp_path) -> None:
    """変異: JSON にだけ責務を足して文書へ書かない、を許さない。"""
    def m(items):
        items.append(dict(items[0], unit_id="IU-GHOSTUNIT-01"))
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("unit_id が現れない" in f for f in faults)


@pytest.mark.parametrize("word", ["準用", "準じる", "踏襲", "流用", "借用", "同様に扱う"])
def test_mutation_trace_substitute_synonyms_are_detected(tmp_path, word) -> None:
    """変異: 「準用」以外の借用表現でも trace を代替できない（独立レビュー R2-04）。"""
    def m(items):
        items[0]["responsibility"] += f"（{word}）"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any(word in f for f in faults), word


def test_trace_substitute_scan_covers_s1_documents() -> None:
    """S1 の機能設計にも trace 代替表現を許さない（S0 だけの走査にしない）。"""
    for p in sorted(detailed_design.L6.rglob("*.md")):
        assert "準用" not in p.read_text(encoding="utf-8"), p.name


CTX_UNITS = json.loads(detailed_design.IMPL_UNITS.read_text(encoding="utf-8"))["items"]


# --- N/A を免罪符にしない（独立レビュー R1-02）---

def _ctx_with(tmp_path, monkeypatch, mutate_du=None, mutate_ac=None):
    """CTX の duc/acc だけを差し替えた検査用 context を返す。"""
    import copy

    from tools.gates.common import Ctx
    ctx = Ctx()
    duc = copy.deepcopy(CTX.duc)
    acc = copy.deepcopy(CTX.acc)
    if mutate_du:
        mutate_du(duc)
    if mutate_ac:
        mutate_ac(acc)
    monkeypatch.setattr(type(ctx), "duc", property(lambda self: duc))
    monkeypatch.setattr(type(ctx), "acc", property(lambda self: acc))
    return ctx


def test_mutation_free_text_na_reason_is_detected(monkeypatch, tmp_path) -> None:
    """変異: 分類語彙のない自由記述で契約節の未被覆を免除できない。"""
    def m(duc):
        for d in duc:
            for a in d["apis"]:
                for c in detailed_design.api_clauses(a):
                    if c.get("na_reason"):
                        c["na_reason"] = "とくに理由はないが受入基準は不要"
                        return
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("分類語彙" in f for f in faults), faults


def test_mutation_erasing_an_api_via_na_reason_is_detected(monkeypatch, tmp_path) -> None:
    """変異: AC の節参照を落として na_reason を付けても、未登録 API として検出される。

    「na_reason を書けば API ごと責務被覆から消せる」経路（独立レビュー R1-02）を塞ぐ検査。
    """
    victim = "API-DU05-01"
    def m_ac(acc):
        for a in acc:
            a["verifies_clause_refs"] = [c for c in a["verifies_clause_refs"]
                                         if not c.startswith(victim + "-")]
    def m_du(duc):
        for d in duc:
            for a in d["apis"]:
                if a["api_id"] != victim:
                    continue
                for c in detailed_design.api_clauses(a):
                    c["na_reason"] = "受入基準未設定: あとで書く"
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m_du, mutate_ac=m_ac)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any(victim in f and "未登録" in f for f in faults), faults


def test_mutation_stale_uncovered_api_entry_is_detected(monkeypatch, tmp_path) -> None:
    """変異: 実際は AC 被覆がある API を台帳へ残しておけない（台帳と実態の厳密一致）。"""
    import json
    p = tmp_path / "uncovered-apis.json"
    p.write_text(json.dumps({"items": [{"api_id": "API-DU05-01", "du_id": "DU-05",
                                        "function": "establish", "reason": "x",
                                        "resolution_update": "S0.1"}]}), encoding="utf-8")
    covered = {c for a in CTX.acc for c in (a.get("verifies_clause_refs") or [])}
    faults = detailed_design.detect_uncovered_api_ledger_faults(CTX, covered, p)
    assert any("実際は AC 被覆がある" in f for f in faults), faults


def test_uncovered_api_ledger_matches_reality() -> None:
    covered = {c for a in CTX.acc for c in (a.get("verifies_clause_refs") or [])}
    assert detailed_design.detect_uncovered_api_ledger_faults(CTX, covered) == []


def test_mutation_duplicate_api_id_is_detected(monkeypatch, tmp_path) -> None:
    """変異: api_id・clause_id の重複を本番ゲートが落とす（独立レビュー R1-05）。"""
    def m(duc):
        duc[1]["apis"][0]["api_id"] = duc[0]["apis"][0]["api_id"]
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("api_id が重複" in f for f in faults), faults


def test_mutation_duplicate_clause_id_is_detected(monkeypatch, tmp_path) -> None:
    def m(duc):
        a = duc[0]["apis"][0]
        a["postcondition"][0]["clause_id"] = a["precondition"][0]["clause_id"]
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("clause_id が重複" in f for f in faults), faults


def test_mutation_duplicate_ledger_entry_is_detected(tmp_path) -> None:
    """変異: uncovered-apis.json の重複登録を黙って上書きしない（独立レビュー R2-02）。"""
    src = json.loads(detailed_design.UNCOVERED_APIS.read_text(encoding="utf-8"))
    src["items"].append(dict(src["items"][0]))
    p = tmp_path / "uncovered-apis.json"
    p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    covered = {c for a in CTX.acc for c in (a.get("verifies_clause_refs") or [])}
    faults = detailed_design.detect_uncovered_api_ledger_faults(CTX, covered, p)
    assert any("重複登録" in f for f in faults), faults


def test_mutation_ledger_metadata_mismatch_is_detected(tmp_path) -> None:
    """変異: 台帳の du_id／function に虚偽を書けない。"""
    src = json.loads(detailed_design.UNCOVERED_APIS.read_text(encoding="utf-8"))
    src["items"][0]["function"] = "totally_other_function"
    p = tmp_path / "uncovered-apis.json"
    p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    covered = {c for a in CTX.acc for c in (a.get("verifies_clause_refs") or [])}
    faults = detailed_design.detect_uncovered_api_ledger_faults(CTX, covered, p)
    assert any("実契約" in f and "不一致" in f for f in faults), faults


# --- 更新境界（PO 指示 §2・§4）---


def _ledger(tmp_path, mutate):
    src = json.loads(detailed_design.UNCOVERED_APIS.read_text(encoding="utf-8"))
    mutate(src)
    p = tmp_path / "uncovered-apis.json"
    p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    return p


def test_update_is_derived_from_du_fn_ids_and_updates_json() -> None:
    """DU→FN→updates.json の導出が一意に決まり、S0.1／S0.2／S0.3 の境界を与える。"""
    derived, bad = detailed_design.update_of_du(CTX)
    assert bad == []
    assert derived["DU-01"] == "S0.1" and derived["DU-13"] == "S0.2" and derived["DU-21"] == "S0.3"
    assert set(derived) == {d["id"] for d in CTX.dus}


def test_uncovered_ledger_updates_match_derivation() -> None:
    assert detailed_design.detect_uncovered_update_faults(CTX) == []


def test_mutation_hand_written_update_that_contradicts_derivation_is_detected(tmp_path) -> None:
    """変異: 導出と食い違う update を手入力できない。"""
    p = _ledger(tmp_path, lambda s: s["items"][0].update({"resolution_update": "S0.3"}))
    faults = detailed_design.detect_uncovered_update_faults(CTX, p)
    assert any("導出" in f and "不一致" in f for f in faults), faults


def test_mutation_slice_vocabulary_as_resolution_is_detected(tmp_path) -> None:
    """変異: slice 語彙（S1／later）を解消先に書けない。"""
    p = _ledger(tmp_path, lambda s: s["items"][0].update({"resolution_update": "S1"}))
    faults = detailed_design.detect_uncovered_update_faults(CTX, p)
    assert any("更新語彙" in f for f in faults), faults


def test_mutation_legacy_resolution_slice_field_is_detected(tmp_path) -> None:
    """変異: 旧欄 resolution_slice の残存を落とす（slice と update の混同）。"""
    def m(s):
        s["items"][0]["resolution_slice"] = "S0"
    p = _ledger(tmp_path, m)
    faults = detailed_design.detect_uncovered_update_faults(CTX, p)
    assert any("resolution_slice" in f for f in faults), faults


def test_update_closure_declaration_matches_reality() -> None:
    assert detailed_design.detect_update_closure_faults(CTX) == []
    computed, uncovered, bad = detailed_design.compute_update_closure(CTX)
    assert bad == []
    assert computed["S0.1"] == "closed" and uncovered["S0.1"] == 0
    assert computed["S0.2"] == "open" and computed["S0.3"] == "open"


def test_mutation_unresolved_gap_reopens_the_update(monkeypatch, tmp_path) -> None:
    """変異: S0.1 の契約節に受入基準未設定が 1 つでも残れば closed を名乗れない。"""
    def m(duc):
        for d in duc:
            if d["id"] != "DU-01":
                continue
            detailed_design.api_clauses(d["apis"][0])[0]["na_reason"] = "受入基準未設定: あとで"
            return
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    computed, _, _ = detailed_design.compute_update_closure(ctx)
    assert computed["S0.1"] == "open"
    faults = detailed_design.detect_update_closure_faults(ctx)
    assert any("S0.1" in f and "実態" in f for f in faults), faults


def test_mutation_closed_claim_without_closure_is_detected(tmp_path) -> None:
    """変異: open の更新が現在地で『設計クロージャー完了』を名乗れない。"""
    src = json.loads(detailed_design.UPDATE_CLOSURE.read_text(encoding="utf-8"))
    for it in src["items"]:
        if it["update"] == "S0.2":
            it["design_closure"] = "closed"
            it["current_state_claim"] = "S0.2 設計クロージャー完了（未被覆 API 5）"
    p = tmp_path / "update-closure.json"
    p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    faults = detailed_design.detect_update_closure_faults(CTX, p)
    assert any("S0.2" in f and "実態 open" in f for f in faults), faults


def test_mutation_claim_absent_from_current_state_is_detected(tmp_path) -> None:
    """変異: 宣言した現在地行が README／CLAUDE.md に無ければ落とす。"""
    src = json.loads(detailed_design.UPDATE_CLOSURE.read_text(encoding="utf-8"))
    for it in src["items"]:
        if it["update"] == "S0.1":
            it["current_state_claim"] = "S0.1 設計クロージャー完了（未被覆 API 0）— 未掲載"
    p = tmp_path / "update-closure.json"
    p.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    faults = detailed_design.detect_update_closure_faults(CTX, p)
    assert any("現在地に" in f for f in faults), faults


# --- verification_level（PO 指示 §3）---


def test_every_api_declares_a_verification_level() -> None:
    levels = {a["api_id"]: a["verification_level"] for d in CTX.duc for a in d["apis"]}
    assert set(levels.values()) <= {"acceptance", "unit", "integration"}
    internal = sorted(k for k, v in levels.items() if v != "acceptance")
    assert internal == ["API-DU01-02", "API-DU02-09", "API-DU09-02", "API-DU09-03"]
    for d in CTX.duc:
        for a in d["apis"]:
            if a["verification_level"] != "acceptance":
                assert len(a["internal_reason"]) >= 20


def test_mutation_internal_level_without_reason_is_detected(monkeypatch, tmp_path) -> None:
    def m(duc):
        duc[0]["apis"][0]["verification_level"] = "unit"
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("internal_reason" in f for f in faults), faults


def test_mutation_unit_category_without_ut_link_is_detected(monkeypatch, tmp_path) -> None:
    """変異: UT 接続のない節が『単体検証』を名乗れない。"""
    def m(duc):
        for d in duc:
            for a in d["apis"]:
                for c in detailed_design.api_clauses(a):
                    if (c.get("na_reason") or "").startswith("呼出側義務:"):
                        c["na_reason"] = "単体検証: UT が検証している（と主張するだけ）"
                        return
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("単体検証" in f and "clause_refs に無い" in f for f in faults), faults


def test_mutation_gap_category_on_ut_verified_clause_is_detected(monkeypatch, tmp_path) -> None:
    """変異: UT が検証している節を『受入基準未設定』（未解決 gap）と偽れない。"""
    def m(duc):
        for d in duc:
            for a in d["apis"]:
                for c in detailed_design.api_clauses(a):
                    if (c.get("na_reason") or "").startswith("単体検証:"):
                        c["na_reason"] = "受入基準未設定: 受入基準がない"
                        return
    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any("正しい分類" in f for f in faults), faults


def test_mutation_internal_api_listed_in_uncovered_ledger_is_detected(tmp_path) -> None:
    """変異: 内部 API を未解決 gap の台帳へ載せられない（分類の二重取り）。"""
    def m(s):
        s["items"].append({"api_id": "API-DU01-02", "du_id": "DU-01",
                           "function": "register_guard", "reason": "x",
                           "resolution_update": "S0.1"})
    p = _ledger(tmp_path, m)
    covered = {c for a in CTX.acc for c in (a.get("verifies_clause_refs") or [])}
    faults = detailed_design.detect_uncovered_api_ledger_faults(CTX, covered, p)
    assert any("内部 API" in f for f in faults), faults


def test_mutation_internal_api_cannot_swap_ut_link_for_ac(monkeypatch, tmp_path) -> None:
    """変異: 内部 API の post／raises を AC 被覆へ付け替えて UT 接続を外せない（R2-01）。"""
    victim = "API-DU01-02"
    clause = "API-DU01-02-POST-01"

    def m_du(duc):
        for d in duc:
            for a in d["apis"]:
                if a["api_id"] != victim:
                    continue
                for u in a["ut"]:
                    u["clause_refs"] = [c for c in u["clause_refs"] if c != clause]
                for c in detailed_design.api_clauses(a):
                    if c["clause_id"] == clause:
                        c.pop("na_reason", None)

    def m_ac(acc):
        for a in acc:
            if a["id"] == "AC-11-1":
                a["verifies_clause_refs"] = [*a["verifies_clause_refs"], clause]

    ctx = _ctx_with(tmp_path, monkeypatch, mutate_du=m_du, mutate_ac=m_ac)
    faults = detailed_design.detect_clause_coverage_faults(ctx)
    assert any(victim in f and "UT の clause_refs に無い" in f for f in faults), faults
