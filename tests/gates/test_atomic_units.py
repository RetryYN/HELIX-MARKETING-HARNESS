"""S0.1 原子単位（1 製品 PR）ゲートの単体テスト・負例・mutation test。"""

import copy
from types import SimpleNamespace

from tools.gates import atomic_units
from tools.gates.common import CTX


def _index() -> dict:
    """実索引を深いコピーし、合成正本の起点にする。"""
    return copy.deepcopy(atomic_units.load_index())


def _units() -> list[dict]:
    """実 AU 正本を深いコピーし、実ファイルを汚さず変異できる形で返す。"""
    return copy.deepcopy(atomic_units.load_units(atomic_units.load_index()))


def _unit(unit_id: str = "AU-DU01-01", **overrides) -> dict:
    """指定した実 AU を深いコピーして必要な項目だけ差し替える。"""
    item = next(u for u in _units() if u["atomic_unit_id"] == unit_id)
    item.update(overrides)
    return item


def _planned() -> list[dict]:
    """全単位を未着手へ戻した合成正本を返す。"""
    data = _units()
    for unit in data:
        unit["status"] = "planned"
        unit["red_receipt"] = None
        unit["green_receipt"] = None
        unit["itc_evidence"] = None
    return data


def _ctx(impl_started: bool) -> SimpleNamespace:
    """CTX を汚さず、原子単位ゲートが読む値だけを渡す。"""
    return SimpleNamespace(duc=CTX.duc, impl_started=impl_started)


def _passed_outcomes(units: list[dict]) -> dict:
    """指定単位の割当 UT をすべて passed とした outcome 正本を作る。"""
    return {"tests": [{"nodeid": nid, "outcome": "passed"}
                      for unit in units for nid in unit["ut_nodeids"]]}


def test_faults_accept_the_canonical_atomic_units(monkeypatch) -> None:
    """正例: 実正本は全ゲートの schema・依存・PR・現実・coverage 違反がゼロ。"""
    index, units = atomic_units.load_index(), atomic_units.load_units(atomic_units.load_index())
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: ([], "test"))
    assert atomic_units.schema_faults(CTX, index, units) == []
    assert atomic_units.dependency_faults(CTX, index, units) == []
    assert atomic_units.pr_scope_faults(CTX, units) == []
    assert atomic_units.test_reality_faults(CTX, units) == []
    assert atomic_units.coverage_faults(CTX, units) == []


def test_mutation_schema_rejects_duplicate_missing_low_floor_and_done_receipts() -> None:
    """変異: API 重複・欠落・低い coverage・証跡なし done を拒否する。"""
    units = _units()
    units[1]["api_ids"].append(units[0]["api_ids"][0])
    units[2]["api_ids"] = []
    units[3]["coverage_floor"] = 79
    units[4]["status"] = "done"
    faults = atomic_units.schema_faults(CTX, _index(), units)
    assert any("複数の原子単位" in fault for fault in faults)
    assert any("過不足なく覆っていない" in fault for fault in faults)
    assert any("coverage_floor=79" in fault for fault in faults)
    assert any("done だが red_receipt" in fault for fault in faults)
    assert any("done だが green_receipt" in fault for fault in faults)


def test_mutation_schema_rejects_index_mismatch_and_nonterminal_itc(monkeypatch) -> None:
    """変異: 索引漏れと非終端単位の Workset ITC 所有を拒否する。"""
    units = _units()
    units[0]["workset_itc_ids"] = ["ITC-01"]
    monkeypatch.setattr(atomic_units, "unit_files", lambda: ["AU-DU01-01.json"])
    faults = atomic_units.schema_faults(CTX, _index(), units)
    assert any("集合が不一致" in fault for fault in faults)
    assert any("workset_itc_ids が導出と不一致" in fault for fault in faults)


def test_mutation_scc_apis_cannot_be_split_across_units() -> None:
    """変異: AU-DU01-02 の SCC API を別々の原子単位へ分断して拒否する。"""
    units = _units()
    merged = next(u for u in units if u["atomic_unit_id"] == "AU-DU01-02")
    merged["api_ids"] = ["API-DU01-02"]
    split = _unit("AU-DU02-01", atomic_unit_id="AU-DU02-07", api_ids=["API-DU02-07"])
    units.append(split)
    faults = atomic_units.dependency_faults(CTX, _index(), units)
    assert any("SCC" in fault and "分断" in fault for fault in faults)


def test_mutation_merge_without_reason_is_rejected() -> None:
    """変異: 結合理由の欠落・code 不正・否定 nodeid 空・不存在を拒否する。"""
    for reason, phrase in ((None, "merge_reason が無い"),
                           ({"code": "invalid", "detail": "x", "negative_test_nodeids": ["tests/gates/test_atomic_units.py::test_mutation_merge_without_reason_is_rejected"]}, "code が"),
                           ({"code": "same_scc", "detail": "x", "negative_test_nodeids": []}, "negative_test_nodeids が無い"),
                           ({"code": "same_scc", "detail": "x", "negative_test_nodeids": ["tests/gates/test_atomic_units.py::test_missing"]}, "が実在しない")):
        unit = _unit("AU-DU01-02", merge_reason=reason)
        faults = atomic_units.schema_faults(CTX, _index(), [unit])
        assert any(phrase in fault for fault in faults)


def test_mutation_dependency_rejects_derived_value_mismatch_and_bad_edges() -> None:
    """変異: API・UT・module・Workset の導出値改変と不正な依存を拒否する。"""
    units = _units()
    units[0]["api_ids"] = ["API-DU99-99"]
    units[1]["ut_nodeids"] = units[1]["ut_nodeids"][1:]
    units[2]["modules"] = ["src/helix/fake.py"]
    units[3]["workset_id"] = "WS-S0.1-A"
    units[0]["depends_on_atomic_units"] = [units[0]["atomic_unit_id"]]
    units[1]["depends_on_atomic_units"].append("AU-DU99-99")
    units[2]["depends_on_atomic_units"] = [units[3]["atomic_unit_id"]]
    units[3]["depends_on_atomic_units"] = [units[2]["atomic_unit_id"]]
    faults = atomic_units.dependency_faults(CTX, _index(), units)
    assert any("api_ids が導出と不一致" in fault for fault in faults)
    assert any("ut_nodeids が導出と不一致" in fault for fault in faults)
    assert any("modules が導出と不一致" in fault for fault in faults)
    assert any("workset_id が導出と不一致" in fault for fault in faults)
    assert any("自己参照" in fault for fault in faults)
    assert any("実在しない" in fault for fault in faults)
    assert any("循環" in fault for fault in faults)


def test_mutation_dependency_rejects_lane_contradiction() -> None:
    """変異: レーンが依存しない他レーンの単位へ依存させて拒否する。"""
    units = _units()
    a = next(u for u in units if u["workset_id"] == "WS-S0.1-A")
    c = next(u for u in units if u["workset_id"] == "WS-S0.1-C")
    a["depends_on_atomic_units"] = [c["atomic_unit_id"]]
    assert any("レーン依存と矛盾" in fault
               for fault in atomic_units.dependency_faults(CTX, _index(), units))


def test_mutation_pr_scope_rejects_multiple_active_and_outside_changes(monkeypatch) -> None:
    """変異: 複数着手、modules 外コード、割当外テストを同一 PR に混入する。"""
    units = _planned()
    units[0]["status"] = units[1]["status"] = "in_progress"
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: (
        ["src/helix/other.py", "tests/unit/test_other.py"], "test"))
    faults = atomic_units.pr_scope_faults(CTX, units)
    assert any("in_progress の原子単位が複数" in fault for fault in faults)
    assert any("modules 外" in fault for fault in faults)
    assert any("割当 UT 以外" in fault for fault in faults)


def test_mutation_pr_scope_rejects_product_change_without_active_unit(monkeypatch) -> None:
    """変異: 着手単位なしで製品コードだけを変更して拒否する。"""
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: (["src/helix/x.py"], "test"))
    assert any("in_progress の原子単位が無い" in fault
               for fault in atomic_units.pr_scope_faults(CTX, _planned()))


def test_mutation_test_reality_rejects_dependency_and_unpassed_ut(monkeypatch) -> None:
    """変異: 未完依存の着手と未実行・failed の割当 UT を拒否する。"""
    units = _planned()
    target = next(u for u in units if u["depends_on_atomic_units"])
    target["status"] = "in_progress"
    outcomes = _passed_outcomes([target])
    outcomes["tests"][0]["outcome"] = "failed"
    outcomes["tests"].pop()
    monkeypatch.setattr("tools.gates.test_reality.load_outcome", lambda: outcomes)
    faults = atomic_units.test_reality_faults(CTX, units)
    assert any("が done でない" in fault for fault in faults)
    assert any("failed" in fault for fault in faults)
    assert any("未実行" in fault for fault in faults)


def test_mutation_test_reality_rejects_receipt_order_and_terminal_itc(monkeypatch) -> None:
    """変異: done の不完全 red、逆順 green、終端 ITC 欠落・failed を拒否する。"""
    units = _planned()
    terminal_id = atomic_units.terminal_units(CTX, units)["WS-S0.1-A"]
    target = next(u for u in units if u["atomic_unit_id"] == terminal_id)
    target["status"] = "done"
    red, green = "a" * 40, "b" * 40
    target["red_receipt"] = {"red_commit": red, "nodeids": [target["ut_nodeids"][0]]}
    target["green_receipt"] = {"green_commit": green, "nodeids": list(target["ut_nodeids"])}
    monkeypatch.setattr(atomic_units, "_red_precedes_implementation", lambda *args: [])
    monkeypatch.setattr(atomic_units, "git", lambda *args: SimpleNamespace(
        returncode=1 if args[-2:] == (red, green) else 0, stdout=""))
    outcomes = _passed_outcomes([target])
    monkeypatch.setattr("tools.gates.test_reality.load_outcome", lambda: outcomes)
    faults = atomic_units.test_reality_faults(CTX, units)
    assert any("網羅していない" in fault for fault in faults)
    assert any("順序が逆" in fault for fault in faults)
    assert any("itc_evidence が無い" in fault for fault in faults)
    target["itc_evidence"] = {itc: f"tests/itest/test_x.py::test_{itc.lower()}"
                              for itc in target["workset_itc_ids"]}
    outcomes["tests"].append({"nodeid": next(iter(target["itc_evidence"].values())), "outcome": "failed"})
    assert any("failed" in fault for fault in atomic_units.test_reality_faults(CTX, units))


def test_mutation_receipt_rejects_red_not_ancestor() -> None:
    """変異: HEAD の祖先でない red_commit を done 証跡として拒否する。"""
    unit = _unit(status="done", red_receipt={"red_commit": "a" * 40, "nodeids": []},
                 green_receipt={"green_commit": "b" * 40, "nodeids": []})
    assert any("HEAD の祖先でない" in fault for fault in atomic_units._receipt_faults(unit["atomic_unit_id"], unit))


def test_mutation_coverage_rejects_low_effective_floor(monkeypatch) -> None:
    """変異: 着手済み単位があるのに有効 coverage 下限を 80 未満へ緩める。"""
    units = _planned()
    units[0]["status"] = "in_progress"
    monkeypatch.setattr("tools.gates.test_pairing.coverage_floor", lambda ctx: 79)
    assert any("79%" in fault for fault in atomic_units.coverage_faults(CTX, units))


def test_mutation_coverage_rejects_unapplied_declared_floor(monkeypatch) -> None:
    """変異: 着手単位の宣言下限が有効 coverage 下限へ配線されないことを拒否する。"""
    units = _planned()
    units[0]["status"] = "in_progress"
    units[0]["coverage_floor"] = 81
    monkeypatch.setattr("tools.gates.test_pairing.coverage_floor", lambda ctx: 80)
    assert any("宣言 coverage_floor=81" in fault
               for fault in atomic_units.coverage_faults(CTX, units))


def test_mutation_ratchet_rejects_all_regressions() -> None:
    """変異: 削除、UT 縮小、status 後退、coverage・receipt・skip の後退を拒否する。"""
    prev = _planned()
    prev[0]["status"] = "done"
    prev[0]["red_receipt"] = {"red_commit": "a" * 40, "nodeids": list(prev[0]["ut_nodeids"])}
    prev[0]["green_receipt"] = {"green_commit": "b" * 40, "nodeids": list(prev[0]["ut_nodeids"])}
    now = copy.deepcopy(prev)
    now.pop()
    now[0]["status"] = "in_progress"
    now[0]["ut_nodeids"].pop()
    now[0]["coverage_floor"] = 79
    now[0]["red_receipt"]["red_commit"] = "c" * 40
    faults = atomic_units.ratchet_faults(now, prev, "HEAD", 101, 100)
    assert any("削除" in fault for fault in faults)
    assert any("ut_nodeids が縮小" in fault for fault in faults)
    assert any("status が後退" in fault for fault in faults)
    assert any("coverage_floor が低下" in fault for fault in faults)
    assert any("red_receipt.red_commit" in fault for fault in faults)
    assert any("skip 上限が増加" in fault for fault in faults)


def test_mutation_ratchet_requires_skip_reduction_and_fails_closed() -> None:
    """変異: done 化の skip 未削減と良性でない比較元不明を fail-close する。"""
    prev, now = _planned(), _planned()
    now[0]["status"] = "done"
    released = len(now[0]["ut_nodeids"])
    assert any("引下げが" in fault
               for fault in atomic_units.ratchet_faults(now, prev, "HEAD", 100, 100))
    assert atomic_units.ratchet_faults(now, prev, "HEAD", 100 - released, 100) == []
    assert atomic_units.ratchet_faults(now, None, "壊れた比較元", 100, 100)


def test_canonical_broken_fails_closed_and_enforced_scopes_are_none(monkeypatch) -> None:
    """変異: 正本欠落・索引不一致・API 過不足・重複・全 planned を fail-close する。"""
    assert "正本が無い" in atomic_units.canonical_broken(_ctx(False), None, None)
    units = _units()
    monkeypatch.setattr(atomic_units, "unit_files", lambda: [])
    assert "集合が一致しない" in atomic_units.canonical_broken(_ctx(False), _index(), units)
    monkeypatch.undo()
    units[0]["api_ids"] = []
    assert "過不足なく覆っていない" in atomic_units.canonical_broken(_ctx(False), _index(), units)
    units = _units()
    units[1]["api_ids"].append(units[0]["api_ids"][0])
    assert "同一 API" in atomic_units.canonical_broken(_ctx(False), _index(), units)
    assert "実装着手が検出" in atomic_units.canonical_broken(_ctx(True), _index(), _planned())
    monkeypatch.setattr(atomic_units, "load_index", lambda: None)
    assert atomic_units.enforced_nodeids(_ctx(True)) is None
    assert atomic_units.enforced_modules(_ctx(True)) is None


def test_derived_workset_status_has_all_three_branches() -> None:
    """導出 status は全 planned、着手あり、全 done＋ITC green の三分岐を満たす。"""
    units = _planned()
    lane = units[0]["workset_id"]
    assert atomic_units.derived_workset_status(units, lane) == "planned"
    units[0]["status"] = "in_progress"
    assert atomic_units.derived_workset_status(units, lane) == "in_progress"
    for unit in units:
        if unit["workset_id"] == lane:
            unit["status"] = "done"
    assert atomic_units.derived_workset_status(units, lane, False) == "in_progress"
    assert atomic_units.derived_workset_status(units, lane, True) == "done"


def test_mutation_terminal_unit_cannot_finish_before_its_lane(monkeypatch) -> None:
    """変異: レーン終端が他の単位より先に done になる（ITC 要求が空振りする）状態を拒否する。"""
    units = _planned()
    lane = "WS-S0.1-A"
    terminal_id = atomic_units.terminal_units(CTX, units)[lane]
    terminal = next(u for u in units if u["atomic_unit_id"] == terminal_id)
    terminal["status"] = "done"
    faults = atomic_units._terminal_order_faults(terminal_id, terminal, units)
    assert any("未完了の原子単位が残っている" in fault for fault in faults)
    for unit in units:
        if unit["workset_id"] == lane:
            unit["status"] = "done"
    assert atomic_units._terminal_order_faults(terminal_id, terminal, units) == []


def test_mutation_pr_scope_rejects_touching_other_atomic_units(monkeypatch) -> None:
    """変異: 着手中の単位以外の AU 正本を同じ PR で書き換えて拒否する。"""
    units = _planned()
    units[0]["status"] = "in_progress"
    other = units[1]["atomic_unit_id"]
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: (
        [f"{atomic_units.ATOMIC_DIR_REL}/{other}.json"], "test"))
    assert any("以外の原子単位正本" in fault
               for fault in atomic_units.pr_scope_faults(CTX, units))
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: (
        [f"{atomic_units.ATOMIC_DIR_REL}/{units[0]['atomic_unit_id']}.json"], "test"))
    assert atomic_units.pr_scope_faults(CTX, units) == []


def test_mutation_negative_test_must_name_the_merged_unit(tmp_path) -> None:
    """変異: 無関係な既存テスト・ID を docstring にだけ置いたテストを negative test として拒否する。

    ID の文字列包含だけでは、コメント・docstring・未使用変数に ID を書けば通ってしまう
    （独立レビュー R15-08）。値として扱い、かつ本番のゲート関数を呼ぶことを要求する。
    """
    unit = _unit("AU-DU01-02")
    unit["merge_reason"] = dict(unit["merge_reason"])
    unit["merge_reason"]["negative_test_nodeids"] = [
        "tests/gates/test_atomic_units.py::test_derived_workset_status_has_all_three_branches"]
    assert any("値として" in fault or "本番のゲート関数" in fault
               for fault in atomic_units.schema_faults(CTX, _index(), [unit]))
    fake = tmp_path / "test_fake.py"
    fake.write_text('''def test_x() -> None:
    """AU-DU01-02 を docstring にだけ書く。"""
    value = 1
    assert value
''', encoding="utf-8")
    import tools.gates.atomic_units as mod
    original = mod.ROOT
    try:
        mod.ROOT = tmp_path
        faults = mod._negative_test_faults("AU-DU01-02", "test_fake.py::test_x")
    finally:
        mod.ROOT = original
    assert any("値として" in fault for fault in faults)


def test_mutation_merge_code_is_closed_to_same_scc() -> None:
    """変異: SCC 以外の自己申告コードを結合理由として拒否する。"""
    unit = _unit("AU-DU01-02")
    tests = list(unit["merge_reason"]["negative_test_nodeids"])
    unit["merge_reason"] = {"code": "indivisible_transaction", "detail": "x",
                            "negative_test_nodeids": tests}
    assert any("same_scc" in fault
               for fault in atomic_units._merge_faults("AU-DU01-02", unit, None))
    unit["merge_reason"] = {"code": "clause_not_satisfiable_alone", "detail": "x",
                            "negative_test_nodeids": tests}
    assert any("same_scc" in fault
               for fault in atomic_units._merge_faults("AU-DU01-02", unit, None))


def test_mutation_schema_check_enforces_oneof_and_property_names() -> None:
    """変異: oneOf・propertyNames・additionalProperties スキーマ・minProperties が実効化される。"""
    from tools.gates.common import schema_check
    nullable = {"oneOf": [{"type": "null"}, {"type": "object", "required": ["a"]}]}
    assert schema_check(nullable, None) == []
    assert schema_check(nullable, {"a": 1}) == []
    assert schema_check(nullable, {"b": 1})
    mapping = {"type": "object", "minProperties": 1,
               "propertyNames": {"pattern": "^ITC-[0-9]{2}$"},
               "additionalProperties": {"type": "string", "pattern": "::"}}
    assert schema_check(mapping, {"ITC-01": "tests/x.py::test_y"}) == []
    assert any("propertyNames" in e for e in schema_check(mapping, {"ITX": "tests/x.py::test_y"}))
    assert schema_check(mapping, {"ITC-01": "no-separator"})
    assert any("minProperties" in e for e in schema_check(mapping, {}))


def test_mutation_pr_scope_rejects_implementation_hidden_in_init(tmp_path, monkeypatch) -> None:
    """変異: 着手単位の modules 外の実装を `__init__.py` に隠して混入する。"""
    root = tmp_path / "root"
    (root / "src/helix/gates").mkdir(parents=True)
    init = root / "src/helix/gates/__init__.py"
    init.write_text("def check_publishable():\n    return True\n", encoding="utf-8")
    (root / "src/helix/__init__.py").write_text('"""package."""\n', encoding="utf-8")
    monkeypatch.setattr(atomic_units, "ROOT", root)
    units = _planned()
    units[0]["status"] = "in_progress"
    monkeypatch.setattr(atomic_units, "changed_paths", lambda: (
        ["src/helix/gates/__init__.py", "src/helix/__init__.py"], "test"))
    faults = atomic_units.pr_scope_faults(CTX, units)
    assert any("modules 外" in fault and "gates/__init__.py" in fault for fault in faults)
    assert not any("src/helix/__init__.py" in fault.split("modules 外")[-1]
                   for fault in faults if "gates/__init__.py" not in fault)


def test_mutation_ratchet_fails_closed_outside_git_but_keeps_skip_duty() -> None:
    """変異: 比較元不明（非 git）でも fail-close し、新設 done の skip 引下げ要求も残る。"""
    units = _planned()
    units[0]["status"] = "done"
    hostile = atomic_units.ratchet_faults(
        units, None, "git リポジトリではない（比較元を解決できない — fail-close）", 999, 204)
    assert any("比較元を解決できない" in fault for fault in hostile)
    assert any("引下げが" in fault or "skip 上限が増加" in fault for fault in hostile)
    benign = atomic_units.ratchet_faults(units, None, "履歴に一度も存在しない（新設）", 204, 204)
    assert any("引下げが" in fault for fault in benign)


def test_mutation_non_scc_merge_cannot_rewrite_derivation() -> None:
    """変異: 同一 DU の非 SCC API を自己申告で結合しても独立導出は変わらない。"""
    units = [u for u in _planned()
             if u["atomic_unit_id"] not in ("AU-DU11-01", "AU-DU11-02")]
    first = _unit("AU-DU11-01")
    second = _unit("AU-DU11-02")
    merged = dict(first)
    merged.update({
        "api_ids": sorted(first["api_ids"] + second["api_ids"]),
        "clause_ids": sorted(set(first["clause_ids"] + second["clause_ids"])),
        "implementation_unit_ids": sorted(set(first["implementation_unit_ids"]
                                              + second["implementation_unit_ids"])),
        "ut_nodeids": sorted(set(first["ut_nodeids"] + second["ut_nodeids"])),
        "modules": sorted(set(first["modules"] + second["modules"])),
        "depends_on_atomic_units": sorted(set(first["depends_on_atomic_units"]
                                              + second["depends_on_atomic_units"])),
        "status": "planned", "red_receipt": None, "green_receipt": None,
        "merge_reason": {
            "code": "indivisible_transaction",
            "detail": "1 migration = 1 transaction。適用と schema_version INSERT を分離できない。",
            "negative_test_nodeids": [
                "tests/gates/test_atomic_units.py::test_mutation_non_scc_merge_cannot_rewrite_derivation"],
        },
    })
    units.append(merged)
    faults = atomic_units.dependency_faults(CTX, _index(), units)
    assert any("導出結果に存在しない" in fault or "導出された原子単位が正本に無い" in fault
               for fault in faults)


def test_mutation_dynamic_loading_counts_as_product_code(tmp_path) -> None:
    """変異: exec／動的 import／sys.path 操作で製品コードを静的検査から隠す。"""
    from tools.gates.test_pairing import carries_product_code
    init = tmp_path / "__init__.py"
    for source in ('exec("def transition(): return 1")\n',
                   'CODE = "def t(): return 1"\nexec(CODE)\n',
                   'import importlib\nt = importlib.import_module("helix.kernel.state").transition\n',
                   't = __import__("helix.kernel.state", fromlist=["t"]).transition\n',
                   'import sys\nsys.path.append("src")\nimport src.helix.kernel.state\n'):
        init.write_text(source, encoding="utf-8")
        assert carries_product_code(init), source
    for benign in ('"""package."""\n', "", "pass\n"):
        init.write_text(benign, encoding="utf-8")
        assert not carries_product_code(init), benign


def test_mutation_negative_test_rejects_tautologies(tmp_path, monkeypatch) -> None:
    """変異: 自己呼出し・到達不能呼出し・未使用変数・別単位検査の偽 negative test を拒否する。"""
    fake = tmp_path / "test_fake.py"
    cases = {
        "self_call": '''def test_x() -> None:
    from tools.gates import atomic_units as au
    assert au._negative_test_faults("AU-DU01-02", "tests/gates/test_fake.py::test_x") == []
''',
        "unreachable": '''def test_x() -> None:
    from tools.gates import atomic_units as au
    target = "AU-DU01-02"
    if False:
        assert au.dependency_faults(None, None, [target])
''',
        "unused_variable": '''def test_x() -> None:
    from tools.gates import atomic_units as au
    unused = "AU-DU01-02"
    assert au.dependency_faults(None, None, [])
''',
        "no_assert": '''def test_x() -> None:
    from tools.gates import atomic_units as au
    au.dependency_faults(None, None, [{"atomic_unit_id": "AU-DU01-02"}])
''',
    }
    monkeypatch.setattr(atomic_units, "ROOT", tmp_path)
    for label, source in cases.items():
        fake.write_text(source, encoding="utf-8")
        assert atomic_units._negative_test_faults(
            "AU-DU01-02", "test_fake.py::test_x"), label
    fake.write_text('''def test_x() -> None:
    from tools.gates import atomic_units as au
    unit = {"atomic_unit_id": "AU-DU01-02"}
    assert au.dependency_faults(None, None, [unit])
''', encoding="utf-8")
    assert atomic_units._negative_test_faults("AU-DU01-02", "test_fake.py::test_x") == []

def test_mutation_dynamic_loader_aliases_are_product_code(tmp_path) -> None:
    """変異: 危険 callable を別名・getattr・import alias で受け取って検出を外す。"""
    from tools.gates.test_pairing import carries_product_code
    init = tmp_path / "__init__.py"
    for source in ('_x = exec\n_x("def transition(): return 1")\n',
                   'import builtins\ngetattr(builtins, "exec")("def t(): return 1")\n',
                   'from importlib import import_module as g\nt = g("helix.kernel.state")\n',
                   'import sys\nsys.path.append("src")\n'):
        init.write_text(source, encoding="utf-8")
        assert carries_product_code(init), source
    for benign in ("import json\n", "from __future__ import annotations\n", "pass\n"):
        init.write_text(benign, encoding="utf-8")
        assert not carries_product_code(init), benign


def test_mutation_pr_scope_rejects_non_python_artifacts(monkeypatch) -> None:
    """変異: `.pyc`／`.so` など `.py` 以外の実行物を原子単位外へ持ち込む。"""
    units = _planned()
    for path in ("src/helix/newpkg/payload.pyc", "src/helix/newpkg/payload.so",
                 "src/helix/newpkg/payload.bin"):
        monkeypatch.setattr(atomic_units, "changed_paths", lambda p=path: ([p], "test"))
        assert any("製品コードを変更している" in fault
                   for fault in atomic_units.pr_scope_faults(CTX, units)), path
        started = _planned()
        started[0]["status"] = "in_progress"
        assert any("modules 外" in fault
                   for fault in atomic_units.pr_scope_faults(CTX, started)), path


def test_mutation_negative_test_requires_real_origin_and_connection(tmp_path, monkeypatch) -> None:
    """変異: 同名ローカル関数・偽 receiver・別単位検査の negative test を拒否する。"""
    fake = tmp_path / "test_fake.py"
    monkeypatch.setattr(atomic_units, "ROOT", tmp_path)
    cases = {
        "local_shadow": '''def dependency_faults(*args):
    return ["x"]


def test_x() -> None:
    unit = {"atomic_unit_id": "AU-DU01-02"}
    assert dependency_faults(None, None, [unit])
''',
        "fake_receiver": '''import types
fake = types.SimpleNamespace(dependency_faults=lambda *a: ["x"])


def test_x() -> None:
    unit = {"atomic_unit_id": "AU-DU01-02"}
    assert fake.dependency_faults(None, None, [unit])
''',
        "other_unit": '''def test_x() -> None:
    from tools.gates import atomic_units as au
    print("AU-DU01-02")
    other = {"atomic_unit_id": "AU-OTHER"}
    assert au.dependency_faults(None, None, [other])
''',
    }
    for label, source in cases.items():
        fake.write_text(source, encoding="utf-8")
        assert atomic_units._negative_test_faults(
            "AU-DU01-02", "test_fake.py::test_x"), label
    fake.write_text('''def test_x() -> None:
    from tools.gates import atomic_units as au
    unit = {"atomic_unit_id": "AU-DU01-02"}
    assert au.dependency_faults(None, None, [unit])
''', encoding="utf-8")
    assert atomic_units._negative_test_faults("AU-DU01-02", "test_fake.py::test_x") == []
