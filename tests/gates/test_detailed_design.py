"""detailed_design ゲートの単体テストと mutation test。"""

import pytest

from tools.gates import detailed_design
from tools.gates.common import CTX, DU_SCHEMA, load, schema_check


def test_api_ut_assignment_is_complete() -> None:
    assert detailed_design.detect_api_ut_faults(CTX.duc) == []


def test_mutation_api_without_ut_is_detected() -> None:
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": []}, *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert any("UTなし" in f for f in faults)


def test_mutation_ut_pointing_at_missing_function_is_detected() -> None:
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": ["test_db_connect.py::test_does_not_exist"]},
                       *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert faults, "存在しないテスト関数への参照が検出されない"


def test_mutation_empty_precondition_violates_dbc_schema() -> None:
    schema = load(DU_SCHEMA)["properties"]["apis"]["items"]
    mutated = {**CTX.duc[0]["apis"][0], "precondition": []}
    assert schema_check(schema, mutated), "pre 空の API が schema を通ってしまう"


def test_every_api_declares_pre_and_post() -> None:
    missing = [f"{d['id']}:{a['signature'][:24]}" for d in CTX.duc for a in d["apis"]
               if not a["precondition"] or not a["postcondition"]]
    assert missing == []


def test_hollow_pattern_matches_placeholders() -> None:
    assert detailed_design.HOLLOW.search("ここは TBD")
    assert detailed_design.HOLLOW.search("仮置きの値")
    assert not detailed_design.HOLLOW.search("確定した設計")


# --- L6 実装単位の意味接続（PO 指示 §1）の検出能力 ---

def _units(tmp_path, mutate=None):
    """実 implementation-units.json を複製し、1 件だけ変異させたファイルを返す。"""
    import json
    src = json.loads(detailed_design.IMPL_UNITS.read_text(encoding="utf-8"))
    if mutate:
        mutate(src["items"])
    p = tmp_path / "implementation-units.json"
    p.write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def test_implementation_units_are_clean_on_real_tree() -> None:
    assert detailed_design.detect_impl_unit_faults(CTX) == []


def test_mutation_unknown_api_ref_is_detected(tmp_path) -> None:
    """変異: 実在しない API 名へ責務を接続できない。"""
    def m(items): items[0]["api_refs"] = ["no_such_api"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("API に存在しない" in f for f in faults)


def test_mutation_du_only_reference_is_detected(tmp_path) -> None:
    """変異: API を挙げず DU を指すだけでは責務の接続と認めない。"""
    def m(items): items[0]["api_refs"] = []
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("api_refs が空" in f for f in faults)


def test_mutation_responsibility_not_in_api_contract_is_detected(tmp_path) -> None:
    """変異: API の pre/post に無い語で責務を書くと検出される（契約に明記されていない責務）。"""
    def m(items): items[0]["responsibility"] = "`ghost_symbol`・`another_ghost`: それらしい説明"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("pre/post に現れない" in f for f in faults)


def test_mutation_bare_responsibility_without_identifiers_is_detected(tmp_path) -> None:
    def m(items): items[0]["responsibility"] = "承認まわりをよしなに処理する"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("識別子" in f for f in faults)


def test_mutation_trace_substitute_word_is_detected(tmp_path) -> None:
    """変異: 「準用」で trace を代替できない。"""
    def m(items):
        items[0]["responsibility"] += "（準用）"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("準用" in f for f in faults)


def test_mutation_ac_outside_du_trace_is_detected(tmp_path) -> None:
    def m(items): items[0]["ac_refs"] = ["AC-71-1"] if "AC-71-1" not in items[0]["ac_refs"] else ["AC-33-1"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("trace.ac に無い" in f or "を担う責務が無い" in f for f in faults)


def test_mutation_tc_not_verifying_the_ac_is_detected(tmp_path) -> None:
    """変異: 当該 AC を検証しない TC を貼っても接続とみなさない。"""
    def m(items): items[0]["tc_refs"] = ["TCC-71-1"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("検証していない" in f or "検証する TC が tc_refs に無い" in f for f in faults)


def test_mutation_ut_outside_api_assignment_is_detected(tmp_path) -> None:
    def m(items): items[0]["ut_refs"] = ["test_db_connect.py::test_connect_sets_foreign_keys_on"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("UT 割当に無い" in f for f in faults)


def test_mutation_uncovered_api_is_detected(tmp_path) -> None:
    """変異: どの責務も担わない API が残ると検出される（被覆の穴）。"""
    def m(items):
        victim = next(u for u in items if u["du_id"] == "DU-12")
        items.remove(victim)
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("を担う責務が無い" in f for f in faults)


def test_mutation_duplicate_responsibility_on_same_api_is_detected(tmp_path) -> None:
    """変異: 同じ API に重なる AC を主張する責務を 2 本置けない（水増しの禁止）。"""
    def m(items):
        clone = dict(items[0], unit_id="IU-DUPLICATE-99")
        items.append(clone)
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("責務の重複" in f or "unit_id が規約外か重複" in f for f in faults)


def test_mutation_missing_unit_id_in_document_is_detected(tmp_path) -> None:
    """変異: JSON にだけ責務を足して文書へ書かない、を許さない。"""
    def m(items):
        items.append(dict(items[0], unit_id="IU-GHOSTUNIT-01"))
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("unit_id が現れない" in f for f in faults)


def test_mutation_ac_without_domain_link_is_detected(tmp_path) -> None:
    """変異: **DU の trace.ac には属する**が、API 契約の語も文書の trace 先要求も共有しない AC。

    独立レビュー R1-04／R2-02: ID グラフの所属だけでは「その振る舞いを検証している」ことに
    ならない。既存の所属検査では落ちない AC を選び、意味検査**固有**のメッセージだけを assert する。
    """
    def m(items):
        u = next(x for x in items if x["unit_id"] == "IU-EVIDENCE-02")   # DU-09 exists
        u["ac_refs"] = ["AC-47-1"]      # DU-09 の trace.ac には属する（所属検査は通る）
        u["tc_refs"] = ["TCC-47-1"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("も共有しない" in f for f in faults), faults
    assert not any("trace.ac に無い" in f for f in faults), "所属検査で落ちており意味検査を実証できない"


@pytest.mark.parametrize("word", ["準用", "準じる", "踏襲", "流用", "借用", "同様に扱う"])
def test_mutation_trace_substitute_synonyms_are_detected(tmp_path, word) -> None:
    """変異: 「準用」以外の借用表現でも trace を代替できない（独立レビュー R2-04）。"""
    def m(items):
        items[0]["responsibility"] += f"（{word}）"
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any(word in f for f in faults), word


def test_mutation_ut_not_naming_the_api_is_detected(tmp_path) -> None:
    """変異: 別 API のテストを ut_refs に置いて「検証済み」を名乗れない。"""
    def m(items):
        u = next(x for x in items if x["unit_id"] == "IU-MIGRATION-02")   # apply_all
        u["ut_refs"] = ["test_db_migrate.py::test_verify_complete_schema_passes"]
    faults = detailed_design.detect_impl_unit_faults(CTX, _units(tmp_path, m))
    assert any("API 名" in f and "含まない" in f for f in faults)


def test_trace_substitute_scan_covers_s1_documents() -> None:
    """S1 の機能設計にも trace 代替表現を許さない（S0 だけの走査にしない）。"""
    import pathlib
    for p in sorted(detailed_design.L6.rglob("*.md")):
        assert "準用" not in p.read_text(encoding="utf-8"), p.name
    assert isinstance(pathlib.Path(detailed_design.IMPL_UNITS), pathlib.Path)
