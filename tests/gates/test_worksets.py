"""S0.1 依存 Workset（実装レーン）ゲートの単体テスト・負例・mutation test。"""

import copy
import json
from types import SimpleNamespace

from tools.gates import atomic_units, worksets
from tools.gates.common import CTX
from tools.gates.test_pairing import has_implementation_source


def _doc(*items: dict) -> dict:
    """実正本を基に、指定した Workset だけを差し替えた合成正本を返す。"""
    data = copy.deepcopy(worksets.load_worksets())
    data["worksets"] = list(items) if items else data["worksets"]
    return data


def _ws(index: int = 0, **overrides) -> dict:
    """実正本の 1 Workset を深いコピーして、必要な箇所だけ変異させる。"""
    item = copy.deepcopy(worksets.load_worksets()["worksets"][index])
    item.update(overrides)
    return item


def _all_planned() -> dict:
    data = _doc()
    for item in data["worksets"]:
        item["status"] = "planned"
    return data


def _ctx(impl_started: bool) -> SimpleNamespace:
    """CTX を汚さず、Workset が必要とする読み取り専用値だけを渡す。"""
    return SimpleNamespace(duc=CTX.duc, impl_started=impl_started)


def test_schema_faults_accepts_the_canonical_worksets() -> None:
    """正例: 実正本は schema と S0.1 全 DU の重複なき完全分割を満たす。"""
    assert worksets.schema_faults(worksets.load_worksets()) == []


def test_mutation_schema_rejects_missing_document() -> None:
    """変異: 正本を消して schema 強制そのものを外そうとする。"""
    assert worksets.schema_faults(None)


def test_mutation_schema_rejects_duplicate_du_and_missing_du07() -> None:
    """変異: DU を重複所属させ、DU-07 を分割から脱落させる。"""
    data = _doc()
    data["worksets"][1]["du_ids"].append("DU-09")
    data["worksets"][1]["du_ids"].remove("DU-07")
    faults = worksets.schema_faults(data)
    assert any("複数 Workset" in f for f in faults)
    assert any("過不足なく覆っていない" in f and "DU-07" in f for f in faults)


def test_mutation_schema_rejects_invalid_status_and_duplicate_id() -> None:
    """変異: status 語彙外と workset_id 重複を正本へ混入する。"""
    data = _doc()
    data["worksets"][0]["status"] = "finished"
    assert any("enum 外" in f for f in worksets.schema_faults(data))
    data = _doc()
    data["worksets"][1]["workset_id"] = data["worksets"][0]["workset_id"]
    assert any("workset_id 重複" in f for f in worksets.schema_faults(data))


def test_mutation_schema_rejects_low_coverage_and_derived_status_mismatch(monkeypatch) -> None:
    """変異: coverage 下限を緩め、原子単位から導出できない status を名乗る。"""
    data = _doc()
    data["worksets"][0]["coverage_floor"] = 79
    assert worksets.schema_faults(data)
    data = _doc()
    data["worksets"][0]["status"] = "in_progress"
    units = [{"atomic_unit_id": "AU-TEST", "workset_id": "WS-S0.1-A",
              "status": "planned", "workset_itc_ids": []}]
    monkeypatch.setattr(atomic_units, "load_index", lambda: {"units": []})
    monkeypatch.setattr(atomic_units, "load_units", lambda index: units)
    assert any("原子単位からの導出（planned）と不一致" in f
               for f in worksets.schema_faults(data))


def test_dependency_faults_accepts_the_canonical_worksets() -> None:
    """正例: du-contracts から導出した依存と実正本は一致する。"""
    assert worksets.dependency_faults(CTX, worksets.load_worksets()) == []


def test_mutation_dependency_rejects_missing_self_and_unknown_dependencies() -> None:
    """変異: 導出依存を消す、自身へ依存する、存在しない ID を参照する。"""
    data = _doc()
    data["worksets"][1]["depends_on"] = []
    assert any("導出と不一致" in f for f in worksets.dependency_faults(CTX, data))
    data = _doc()
    data["worksets"][1]["depends_on"] = ["WS-S0.1-B"]
    assert any("自分自身" in f for f in worksets.dependency_faults(CTX, data))
    data = _doc()
    data["worksets"][1]["depends_on"].append("WS-S0.1-Z")
    assert any("実在しない" in f for f in worksets.dependency_faults(CTX, data))


def test_mutation_po_original_partition_is_cyclic_and_justifies_moving_du04_to_b() -> None:
    """PO 原案 A=09-12/B=05-08/C=01-04 は循環する。これが DU-04 を C から B へ移した根拠。"""
    data = _doc()
    data["worksets"][0]["du_ids"] = ["DU-09", "DU-10", "DU-11", "DU-12"]
    data["worksets"][1]["du_ids"] = ["DU-05", "DU-06", "DU-07", "DU-08"]
    data["worksets"][2]["du_ids"] = ["DU-01", "DU-02", "DU-03", "DU-04"]
    faults = worksets.dependency_faults(CTX, data)
    assert any("循環している" in f for f in faults)


def test_mutation_du_scc_cannot_be_split_across_worksets() -> None:
    """変異: 相互依存する DU-01 と DU-02 を別 Workset へ分断する。"""
    data = _doc()
    data["worksets"][1]["du_ids"].append("DU-01")
    data["worksets"][2]["du_ids"].remove("DU-01")
    assert any("DU-01↔DU-02" in f for f in worksets.du_cycles_spanning(
        CTX, {du: w["workset_id"] for w in data["worksets"] for du in w["du_ids"]}))


def test_find_cycle_returns_a_cycle_or_empty_list() -> None:
    """循環検出器は 2 項循環を返し、DAG には空を返す。"""
    assert worksets.find_cycle({"X": {"Y"}, "Y": {"X"}})
    assert worksets.find_cycle({"X": {"Y"}, "Y": set()}) == []


def test_scope_faults_accepts_the_canonical_worksets() -> None:
    """正例: 実正本の API・UT・ITC・module 導出は全て一致する。"""
    assert worksets.scope_faults(CTX, worksets.load_worksets()) == []


def test_mutation_scope_rejects_forged_api_missing_ut_itc_and_module() -> None:
    """変異: 導出結果の各スコープ列を一つずつ崩す。"""
    for key, value, expected in (("api_ids", _ws()["api_ids"] + ["API-DU99-01"],
                                  "が正本からの導出と不一致"),
                                 ("ut_nodeids", _ws()["ut_nodeids"][1:],
                                  "が正本からの導出と不一致"),
                                 ("itc_ids", [], "が itest.json からの導出と不一致"),
                                 ("modules", ["src/helix/fake.py"],
                                  "が正本からの導出と不一致")):
        data = _doc()
        data["worksets"][0][key] = value
        assert any(f".{key} {expected}" in f
                   for f in worksets.scope_faults(CTX, data))


def test_mutation_scope_rejects_implementation_outside_started_workset(monkeypatch) -> None:
    """変異: 未着手 Workset の module に実装を紛れ込ませる。"""
    monkeypatch.setattr(worksets, "implemented_modules", lambda ctx: [_ws(1)["modules"][0]])
    assert any("着手済み Workset に属さないモジュールへ実装がある" in f
               for f in worksets.scope_faults(CTX, _all_planned()))


def test_test_reality_all_planned_defers_unstarted_stubs() -> None:
    """全 planned なら未着手のスタブは猶予される。これが Workset 単位化の核心である。"""
    assert worksets.test_reality_faults(CTX, _all_planned()) == []


def test_mutation_test_reality_rejects_skipped_ut_for_started_a(tmp_path, monkeypatch) -> None:
    """変異: A 着手後も outcome 上 skip の UT を残す。

    強制範囲は**原子単位**まで絞られるので、レーンを in_progress にするだけでなく
    当該 UT を持つ原子単位も着手済みにする（原子単位がどれも未着手なら、その UT は
    まだ誰も書くと宣言していない＝猶予対象である）。
    """
    root = tmp_path / "root"
    (root / "reports").mkdir(parents=True)
    (root / "reports/test-outcome.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(worksets, "ROOT", root)
    target = _ws()["ut_nodeids"][0]
    monkeypatch.setattr(atomic_units, "enforced_nodeids", lambda ctx: [target])
    monkeypatch.setattr("tools.gates.test_reality.load_outcome",
                        lambda: {"tests": [{"nodeid": target, "outcome": "skipped"}]})
    from tools.gates import atomic_units as au
    units = au.load_units(au.load_index())
    for unit in units:
        if target in unit["ut_nodeids"]:
            unit["status"] = "in_progress"
    monkeypatch.setattr(au, "load_units", lambda index=None: units)
    data = _all_planned()
    data["worksets"][0]["status"] = "in_progress"
    assert any(target in f and "skipped" in f for f in worksets.test_reality_faults(CTX, data))


def test_mutation_test_reality_requires_done_dependencies() -> None:
    """変異: 依存 A が planned のまま B だけを着手する。"""
    data = _all_planned()
    data["worksets"][1]["status"] = "in_progress"
    assert any("依存 Workset WS-S0.1-A が done でない" in f
               for f in worksets.test_reality_faults(CTX, data))


def test_mutation_skip_ceiling_rejects_growth_and_missing_current() -> None:
    """変異: 全体 skip 上限の増加と現在値を読めない状態を許さない。"""
    assert any("skip 上限が増加" in f
               for f in worksets._skip_ceiling_faults(101, 100, "skip-budget: HEAD^"))
    assert any("skip 上限を読めない" in f
               for f in worksets._skip_ceiling_faults(None, 100, "skip-budget: HEAD^"))


def test_coverage_faults_and_ci_wiring_accept_current_repository() -> None:
    """正例: 現行 CI は coverage scope と floor を pytest へ配線している。"""
    assert worksets.coverage_faults(CTX, worksets.load_worksets()) == []
    assert worksets._ci_coverage_wiring() == []


def test_mutation_coverage_fails_closed_when_ci_file_is_missing(monkeypatch, tmp_path) -> None:
    """変異: Python CI を存在しないパスへ差し替える。"""
    monkeypatch.setattr(worksets, "PYTHON_CI", tmp_path / "missing.yml")
    assert any("構造として読めない" in fault for fault in worksets._ci_coverage_wiring())
    assert any(
        "構造として読めない" in fault
        for fault in worksets.coverage_faults(CTX, worksets.load_worksets())
    )


def test_mutation_ci_wiring_rejects_pytest_without_scope_or_floor(tmp_path, monkeypatch) -> None:
    """変異: coverage pytest 行から scope/floor の受け渡しを外す。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        """jobs:
  python:
    steps:
      - run: python3 tools/coverage_scope.py
      - run: uv run pytest --cov-report=term --cov-fail-under=80
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert any("受け取っていない" in f for f in worksets._ci_coverage_wiring())


def test_ratchet_faults_accept_identical_parent() -> None:
    """親正本と同一で skip 上限も不変ならラチェット違反はない。"""
    data = worksets.load_worksets()
    assert worksets.ratchet_faults(data, copy.deepcopy(data), "HEAD", 100, 100,
                                  "skip-budget: HEAD^") == []


def test_mutation_ratchet_rejects_removal_all_scope_shrinks_and_regressions() -> None:
    """変異: Workset と全スコープ列を縮小し、status・coverage を後退させる。"""
    prev = _doc()
    prev["worksets"][0]["status"] = "done"
    prev["worksets"][1]["depends_on"] = ["WS-S0.1-A"]
    now = copy.deepcopy(prev)
    now["worksets"].pop()
    now["worksets"][0]["du_ids"].pop()
    now["worksets"][0]["api_ids"].pop()
    now["worksets"][0]["ut_nodeids"].pop()
    now["worksets"][0]["itc_ids"].pop()
    now["worksets"][1]["depends_on"] = []
    now["worksets"][0]["status"] = "in_progress"
    now["worksets"][0]["coverage_floor"] = 70
    faults = worksets.ratchet_faults(now, prev, "HEAD", 100, 100,
                                     "skip-budget: HEAD^")
    assert any("Workset が削除" in f for f in faults)
    assert any("du_ids が縮小" in f for f in faults)
    assert any("api_ids が縮小" in f for f in faults)
    assert any("ut_nodeids が縮小" in f for f in faults)
    assert any("itc_ids が縮小" in f for f in faults)
    assert any("depends_on が縮小" in f for f in faults)
    assert any("status が後退" in f for f in faults)
    assert any("coverage_floor が低下" in f for f in faults)


def test_mutation_skip_ceiling_rejects_unresolved_previous_unless_benign() -> None:
    """変異: skip 上限の比較元不在を、良性 source 以外では fail-close にする。"""
    assert any("比較元を解決できない" in f
               for f in worksets._skip_ceiling_faults(100, None, "skip-budget: 壊れた親"))
    assert worksets._skip_ceiling_faults(
        100, None, "skip-budget: 親コミットなし（初回コミット）") == []
    assert worksets._skip_ceiling_faults(
        100, None, "skip-budget: 履歴に一度も存在しない（新設）") == []


def test_ratchet_fail_closed_only_for_broken_parent() -> None:
    """親正本が壊れた場合だけ fail-close、初回コミットは比較対象なしとして通す。"""
    data = _doc()
    assert worksets.ratchet_faults(data, None, "HEAD の Workset 正本が壊れている")
    assert worksets.ratchet_faults(
        data, None, "worksets: 親コミットなし（初回コミット）", 100, 100,
        "skip-budget: 親コミットなし（初回コミット）") == []


def test_enforced_scopes_follow_started_worksets_and_fail_closed(monkeypatch) -> None:
    """強制範囲は started A のみ、正本不全かつ実装開始後は S0.1 全 DU へ倒れる。"""
    planned = _all_planned()
    assert worksets.enforced_du_ids(_ctx(False), planned) == []
    assert worksets.enforced_nodeids(_ctx(False), planned) == []
    assert worksets.enforced_modules(_ctx(False), planned) == []
    started = _all_planned()
    started["worksets"][0]["status"] = "in_progress"
    assert worksets.enforced_du_ids(_ctx(True), started) == _ws()["du_ids"]
    started_scope = worksets.derive_scope(CTX, _ws()["du_ids"])
    assert worksets.enforced_nodeids(_ctx(True), started) == started_scope["ut_nodeids"]
    assert worksets.enforced_modules(_ctx(True), started) == _ws()["modules"]
    incomplete = _doc()
    incomplete["worksets"][0]["du_ids"].pop()
    assert worksets.enforced_du_ids(_ctx(True), incomplete) == worksets.s0_du_ids()
    monkeypatch.setattr(worksets, "load_worksets", lambda: None)
    all_du_ids = worksets.s0_du_ids()
    all_scope = worksets.derive_scope(CTX, all_du_ids)
    assert worksets.enforced_du_ids(_ctx(True), None) == all_du_ids
    assert worksets.enforced_nodeids(_ctx(True), None) == all_scope["ut_nodeids"]
    assert worksets.enforced_modules(_ctx(True), None) == all_scope["modules"]


def test_mutation_committed_worksets_reads_parent_commit_not_head(monkeypatch) -> None:
    """変異: HEAD 自己比較ではなく HEAD^ を比較元に固定する。"""
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str) -> SimpleNamespace:
        calls.append(args)
        if args[:2] == ("rev-parse", "--is-inside-work-tree"):
            return SimpleNamespace(returncode=0, stdout="true")
        if args[:2] == ("rev-parse", "--verify"):
            return SimpleNamespace(returncode=0, stdout="parent")
        return SimpleNamespace(returncode=0, stdout='{"worksets": []}')

    monkeypatch.setattr(worksets, "git", fake_git)
    prev, _ = worksets.committed_worksets()
    skip_prev, _ = worksets.committed_skip_budget()
    assert prev == {"worksets": []}
    assert skip_prev is None
    assert ("rev-parse", "--verify", "HEAD^") in calls
    shown = [args[1] for args in calls if args[0] == "show"]
    assert shown and all(arg.startswith("HEAD^:") for arg in shown)
    assert all(not arg.startswith("HEAD:") for arg in shown)


def test_mutation_committed_sources_fail_closed_and_skip_budget_is_typed(monkeypatch) -> None:
    """変異: 比較元の不全、親の壊れた JSON、欠損 skip 上限を fail-close にする。"""
    def check(response: SimpleNamespace, phrase: str, benign: bool) -> str:
        monkeypatch.setattr(worksets, "git", lambda *args: response)
        _, source = worksets._committed(worksets.WORKSETS, "worksets")
        assert phrase in source
        assert worksets._benign(source) is benign
        return source

    check(SimpleNamespace(returncode=1, stdout=""), "git リポジトリではない", False)

    def no_parent(*args: str) -> SimpleNamespace:
        return SimpleNamespace(returncode=0 if args[1] == "--is-inside-work-tree" else 1, stdout="")

    monkeypatch.setattr(worksets, "git", no_parent)
    _, source = worksets._committed(worksets.WORKSETS, "worksets")
    assert "初回コミット" in source and worksets._benign(source)

    def new_file(*args: str) -> SimpleNamespace:
        code = 0 if args[0] == "rev-parse" else 1
        return SimpleNamespace(returncode=code, stdout="")

    monkeypatch.setattr(worksets, "git", new_file)
    _, source = worksets._committed(worksets.WORKSETS, "worksets")
    assert "新設" in source and worksets._benign(source)

    def broken_json(*args: str) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="{")

    monkeypatch.setattr(worksets, "git", broken_json)
    _, source = worksets._committed(worksets.WORKSETS, "worksets")
    assert "壊れている" in source and not worksets._benign(source)
    assert worksets.ratchet_faults(_doc(), None, source)

    for payload in ('{}', '{"max_skipped": "not-a-number"}'):
        monkeypatch.setattr(worksets, "git", lambda *args, payload=payload:
                            SimpleNamespace(returncode=0, stdout=payload))
        value, reason = worksets.committed_skip_budget()
        assert value is None and "max_skipped" in reason

    prev, now = _doc(), _doc()
    now["worksets"][0]["status"] = "done"
    assert any("比較元を解決できない" in f
               for f in worksets.ratchet_faults(now, prev, "HEAD", 1, None, "max_skipped 不在"))
    assert any("比較元を解決できない" in f
               for f in worksets.ratchet_faults(prev, prev, "HEAD", 1, None, "max_skipped 不在"))


def test_mutation_lane_completion_rejects_unfinished_atomic_units(tmp_path, monkeypatch) -> None:
    """変異: done Workset に未完了の所属原子単位を残す。"""
    root = tmp_path / "root"
    (root / "reports").mkdir(parents=True)
    (root / "reports/test-outcome.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(worksets, "ROOT", root)
    monkeypatch.setattr("tools.gates.test_pairing.detect_ut_escapes", lambda *a, **k: [])
    data = _all_planned()
    w = data["worksets"][0]
    w["status"] = "done"
    outcomes = [{"nodeid": nid, "outcome": "passed"} for nid in w["ut_nodeids"]]
    monkeypatch.setattr("tools.gates.test_reality.load_outcome",
                        lambda: {"tests": outcomes})
    units = [{"atomic_unit_id": "AU-TEST", "workset_id": w["workset_id"],
              "status": "in_progress"}]
    monkeypatch.setattr(atomic_units, "load_index", lambda: {"units": []})
    monkeypatch.setattr(atomic_units, "load_units", lambda index: units)
    assert any("done だが未完了の原子単位が残っている" in f
               for f in worksets.test_reality_faults(CTX, data))


def test_mutation_lane_completion_rejects_unreadable_atomic_units(monkeypatch) -> None:
    """変異: done Workset の原子単位正本を読めない状態にする。"""
    data = _all_planned()
    wid = data["worksets"][0]["workset_id"]
    monkeypatch.setattr(atomic_units, "load_index", lambda: None)
    monkeypatch.setattr(atomic_units, "load_units", lambda index: None)
    assert any("done だが原子単位正本を読めない" in f
               for f in worksets._lane_completion_faults(wid, {"status": "done"}))


def test_mutation_skip_ceiling_accepts_a_decrease_without_double_counting() -> None:
    """変異: Workset 側の skip ceiling は上限の減少を受理し、解除件数を二重計上しない。"""
    assert worksets._skip_ceiling_faults(99, 100, "skip-budget: HEAD^") == []


def test_mutation_all_planned_after_start_forces_all_du_and_declared_workset(monkeypatch) -> None:
    """変異: 実装着手後に全 Workset を planned へ戻して強制を外せない。"""
    data = _all_planned()
    monkeypatch.setattr(worksets, "implemented_modules", lambda ctx: [])
    assert worksets.enforced_du_ids(_ctx(True), data) == worksets.s0_du_ids()
    assert worksets.enforced_du_ids(_ctx(False), data) == []
    assert any("in_progress／done の Workset が 0 件" in f
               for f in worksets.scope_faults(_ctx(True), data))
    data["worksets"][0]["status"] = "in_progress"
    assert not any("in_progress／done の Workset が 0 件" in f
                   for f in worksets.scope_faults(_ctx(True), data))


def test_mutation_derived_status_rejects_status_ahead_of_atomic_units(monkeypatch) -> None:
    """変異: 原子単位が planned のまま Workset だけを in_progress に進める。"""
    data = _doc()
    data["worksets"][0]["status"] = "in_progress"
    units = [{"atomic_unit_id": "AU-TEST", "workset_id": "WS-S0.1-A",
              "status": "planned", "workset_itc_ids": []}]
    monkeypatch.setattr(atomic_units, "load_index", lambda: {"units": []})
    monkeypatch.setattr(atomic_units, "load_units", lambda index: units)
    faults = worksets.derived_status_faults(data)
    assert any("WS-S0.1-A" in f and "status=in_progress" in f
               and "導出（planned）と不一致" in f for f in faults)


def test_mutation_ci_wiring_requires_resolver_ids_and_order(tmp_path, monkeypatch) -> None:
    """変異: resolver の id・実行順・有効 job を coverage 配線として検査する。"""
    pytest = (f"uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under="
              f"${{{{ {worksets.COV_FLOOR_REF} }}}}")

    def write(name: str, body: str) -> None:
        ci = tmp_path / name
        ci.write_text(body, encoding="utf-8")
        monkeypatch.setattr(worksets, "PYTHON_CI", ci)

    write("valid.yml", f"""jobs:\n  python:\n    steps:\n      - id: cov\n        run: python3 tools/coverage_floor.py\n      - id: covscope\n        run: python3 tools/coverage_scope.py\n      - run: {pytest}\n""")
    assert worksets._ci_coverage_wiring() == []
    write("wrong-id.yml", f"""jobs:\n  python:\n    steps:\n      - id: cov\n        run: python3 tools/coverage_floor.py\n      - id: covscope2\n        run: python3 tools/coverage_scope.py\n      - run: {pytest}\n""")
    assert any("id=covscope" in f for f in worksets._ci_coverage_wiring())
    write("late.yml", f"""jobs:\n  python:\n    steps:\n      - id: cov\n        run: python3 tools/coverage_floor.py\n      - run: {pytest}\n      - id: covscope\n        run: python3 tools/coverage_scope.py\n""")
    assert any("後ろにある" in f for f in worksets._ci_coverage_wiring())
    write("disabled.yml", f"""jobs:\n  python:\n    if: false\n    steps:\n      - id: cov\n        run: python3 tools/coverage_floor.py\n      - id: covscope\n        run: python3 tools/coverage_scope.py\n      - run: {pytest}\n""")
    assert any("配線が無い" in f for f in worksets._ci_coverage_wiring())


def test_mutation_dependency_rejects_reverse_topological_workset_order() -> None:
    """変異: C, B, A の逆順は依存宣言が正しくても位相順ではない。"""
    data = _doc(*reversed(_doc()["worksets"]))
    assert any("位相順でない" in f for f in worksets.dependency_faults(CTX, data))


def test_mutation_committed_recovers_deleted_parent_blob_for_ratchet(monkeypatch) -> None:
    """変異: 親で削除された正本も削除前の最新版から比較する。"""
    previous = _doc()
    sha = "a" * 40

    def fake_git(*args: str) -> SimpleNamespace:
        if args[:2] == ("rev-parse", "--is-inside-work-tree"):
            return SimpleNamespace(returncode=0, stdout="true")
        if args[:2] == ("rev-parse", "--verify"):
            return SimpleNamespace(returncode=0, stdout="parent")
        if args[0] == "show" and args[1].startswith("HEAD^:"):
            return SimpleNamespace(returncode=1, stdout="")
        if args[0] == "rev-list":
            return SimpleNamespace(returncode=0, stdout=f"{sha}\n")
        if args == ("show", f"{sha}:{worksets.WORKSETS.relative_to(worksets.ROOT)}"):
            return SimpleNamespace(returncode=0, stdout=json.dumps(previous))
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(worksets, "git", fake_git)
    prev, source = worksets._committed(worksets.WORKSETS, "worksets")
    assert prev == previous
    assert "削除前の最新版" in source
    assert not worksets._benign(source)

    prev["worksets"][0]["status"] = "done"
    now = copy.deepcopy(prev)
    now["worksets"].pop()
    now["worksets"][0]["ut_nodeids"].pop()
    now["worksets"][0]["status"] = "in_progress"
    faults = worksets.ratchet_faults(now, prev, source)
    assert any("Workset が削除" in fault for fault in faults)
    assert any("ut_nodeids が縮小" in fault for fault in faults)
    assert any("status が後退" in fault for fault in faults)


def test_mutation_committed_treats_never_seen_path_as_benign(monkeypatch) -> None:
    """変異: 履歴に一度も無い新設だけを benign として扱う。"""
    def fake_git(*args: str) -> SimpleNamespace:
        if args[:2] == ("rev-parse", "--is-inside-work-tree"):
            return SimpleNamespace(returncode=0, stdout="true")
        if args[:2] == ("rev-parse", "--verify"):
            return SimpleNamespace(returncode=0, stdout="parent")
        if args[0] == "rev-list":
            return SimpleNamespace(returncode=0, stdout="")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(worksets, "git", fake_git)
    _, source = worksets._committed(worksets.WORKSETS, "worksets")
    assert "履歴に一度も存在しない（新設）" in source
    assert worksets._benign(source)


def test_mutation_benign_sources_excludes_missing_parent_phrase() -> None:
    """変異: 親だけに無い経路を benign に加えてラチェットを外せない。"""
    assert "親コミットに存在しない（新設）" not in worksets.BENIGN_SOURCES
    assert worksets.BENIGN_SOURCES == (
        "親コミットなし（初回コミット）",
        "履歴に一度も存在しない（新設）",
    )


def test_mutation_new_worksets_allow_benign_missing_skip_source() -> None:
    """変異: 新設正本では比較元 skip 上限の不在に猶予を与える。"""
    source = "worksets: 履歴に一度も存在しない（新設）"
    assert worksets.ratchet_faults(_all_planned(), None, source, 100, None,
                                  "skip-budget: 履歴に一度も存在しない（新設）") == []


def test_mutation_skip_ceiling_rejects_non_benign_missing_source() -> None:
    """変異: 良性でない source の比較元不在を猶予しない。"""
    faults = worksets._skip_ceiling_faults(1, None, "skip-budget: max_skipped 不在")
    assert any("比較元を解決できない" in fault for fault in faults)


def test_mutation_ci_wiring_checks_every_coverage_job_and_step(tmp_path, monkeypatch) -> None:
    """変異: 複数 job と同一 job の全 coverage pytest step を検査する。"""
    pytest = (f"uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under="
              f"${{{{ {worksets.COV_FLOOR_REF} }}}}")
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  good:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: {pytest}
  bad:
    steps:
      - id: covscope-other
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: {pytest}
  two-pytest:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: {pytest}
      - run: uv run pytest --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    faults = worksets._ci_coverage_wiring()
    assert any("bad:" in fault and "id=covscope" in fault for fault in faults)
    assert any("two-pytest: pytest が" in fault for fault in faults)


def test_mutation_ci_wiring_requires_unconditional_resolver(tmp_path, monkeypatch) -> None:
    """変異: resolver の条件付き実行は true 以外を拒否する。"""
    pytest = (f"uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under="
              f"${{{{ {worksets.COV_FLOOR_REF} }}}}")
    ci = tmp_path / "python-ci.yml"

    def write(condition: str) -> None:
        ci.write_text(
            f"""jobs:
  python:
    steps:
      - id: covscope
        if: {condition}
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: {pytest}
""",
            encoding="utf-8",
        )

    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    write("${{ matrix.resolve }}")
    assert "if: ${{ matrix.resolve }}" in ci.read_text(encoding="utf-8")
    assert any("条件付き実行" in fault for fault in worksets._ci_coverage_wiring())
    write("true")
    assert worksets._ci_coverage_wiring() == []


def test_mutation_ci_wiring_accepts_repository_configuration() -> None:
    """正例: 実リポジトリの coverage CI 配線は全 job 検査を通る。"""
    assert worksets._ci_coverage_wiring() == []


def test_mutation_has_implementation_source_is_pure_and_fail_closed() -> None:
    """変異: 実装判定は文字列だけで行い構文エラーを実装ありと扱う。"""
    assert has_implementation_source("def f(): return 1")
    assert not has_implementation_source('\"\"\"doc\"\"\"\nfrom x import y')
    assert has_implementation_source("def (")


def test_mutation_lane_completion_rejects_workset_without_atomic_units(monkeypatch) -> None:
    """変異: done Workset に所属する原子単位を 1 件も用意しない。"""
    monkeypatch.setattr(atomic_units, "load_index", lambda: {"units": []})
    monkeypatch.setattr(atomic_units, "load_units", lambda index: [])
    assert any("done だが所属する原子単位が 1 件も無い" in fault
               for fault in worksets._lane_completion_faults(
                   "WS-S0.1-A", {"status": "done"}))


def test_mutation_ci_wiring_rejects_non_pytest_coverage_command(tmp_path, monkeypatch) -> None:
    """変異: coverage 引数だけを持つ非 pytest コマンドを配線として認めない。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: python3 -c pass --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}} ${{{{ {worksets.COV_SCOPE_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert any("pytest の実行ではない" in fault for fault in worksets._ci_coverage_wiring())


def test_mutation_ci_wiring_checks_non_pytest_coverage_step_alongside_pytest(tmp_path, monkeypatch) -> None:
    """変異: 正しい pytest step があってもダミー step を全件検査する。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
      - run: python3 -c pass --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}} ${{{{ {worksets.COV_SCOPE_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    faults = worksets._ci_coverage_wiring()
    assert any("pytest の実行ではない" in fault and "python3 -c pass" in fault
               for fault in faults)


def test_mutation_ci_wiring_reports_job_when_all_coverage_commands_are_non_pytest(
        tmp_path, monkeypatch) -> None:
    """変異: job 内に pytest 実行主体が無ければ job レベルでも拒否する。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: python3 -c pass --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}} ${{{{ {worksets.COV_SCOPE_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert any("coverage 下限を渡している実行主体が pytest でない" in fault
               for fault in worksets._ci_coverage_wiring())


def test_mutation_ci_wiring_accepts_pytest_coverage_command_with_real_resolvers(
        tmp_path, monkeypatch) -> None:
    """正例: 前段の実 resolver と pytest の coverage 配線を受理する。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-report=term --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert worksets._ci_coverage_wiring() == []


def test_mutation_ci_wiring_rejects_conditional_coverage_job(tmp_path, monkeypatch) -> None:
    """変異: coverage job を push 時だけに限定できない。"""
    from tools.gates.test_reality import _load_yaml

    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    if: "github.event_name == 'push'"
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - run: uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
""",
        encoding="utf-8",
    )
    assert _load_yaml(ci)["jobs"]["python"]["if"] == "github.event_name == 'push'"
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert any("coverage を測る job が条件付き実行" in fault
               for fault in worksets._ci_coverage_wiring())


def test_mutation_ci_wiring_rejects_conditional_coverage_pytest_step(tmp_path, monkeypatch) -> None:
    """変異: coverage pytest step を push 時だけに限定できない。"""
    from tools.gates.test_reality import _load_yaml

    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - if: "github.event_name == 'push'"
        run: uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
""",
        encoding="utf-8",
    )
    assert _load_yaml(ci)["jobs"]["python"]["steps"][2]["if"] == "github.event_name == 'push'"
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert any("coverage を測る pytest step が条件付き実行" in fault
               for fault in worksets._ci_coverage_wiring())


def test_mutation_ci_wiring_accepts_true_conditions_on_coverage_job_and_step(
        tmp_path, monkeypatch) -> None:
    """正例: true リテラルの job／pytest step は無条件実行として扱う。"""
    ci = tmp_path / "python-ci.yml"
    ci.write_text(
        f"""jobs:
  python:
    if: true
    steps:
      - id: covscope
        run: python3 tools/coverage_scope.py
      - id: cov
        run: python3 tools/coverage_floor.py
      - if: true
        run: uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} --cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    assert worksets._ci_coverage_wiring() == []


def test_mutation_conditional_recognizes_only_unconditional_true_forms() -> None:
    """変異: false・式の if を無条件実行へ緩和できない。"""
    assert worksets._conditional({}) is False
    assert worksets._conditional({"if": True}) is False
    assert worksets._conditional({"if": "true"}) is False
    assert worksets._conditional({"if": "${{ true }}"}) is False
    assert worksets._conditional({"if": False}) is True
    assert worksets._conditional({"if": "github.event_name == 'push'"}) is True


def test_mutation_ci_wiring_accepts_repository_after_conditional_checks() -> None:
    """正例: 実リポジトリの Python CI は無条件 coverage 配線を保つ。"""
    assert worksets._ci_coverage_wiring() == []


def _wiring(tmp_path, monkeypatch, name: str, body: str) -> list[str]:
    """合成ワークフローで配線検査を走らせる（実 CI を書き換えない）。"""
    ci = tmp_path / name
    ci.write_text(body, encoding="utf-8")
    monkeypatch.setattr(worksets, "PYTHON_CI", ci)
    return worksets._ci_coverage_wiring()


_PYTEST_LINE = (f"uv run pytest ${{{{ {worksets.COV_SCOPE_REF} }}}} "
                f"--cov-fail-under=${{{{ {worksets.COV_FLOOR_REF} }}}}")
_RESOLVERS = ("      - id: cov\n        run: python3 tools/coverage_floor.py\n"
              "      - id: covscope\n        run: python3 tools/coverage_scope.py\n")


def test_mutation_pytest_lookalike_binary_is_not_an_execution_subject() -> None:
    """変異: `pytest-fake` のような別名を置いて実行主体を詐称する（R13-15）。

    前方一致で判定していると、名前を `pytest*` にするだけで coverage 引数を持つ
    ダミー step が配線検査を通ってしまう。basename の完全一致だけを認める。
    """
    from tools.gates.test_reality import _runs_pytest
    assert _runs_pytest("uv run pytest --cov-fail-under=80") is True
    assert _runs_pytest("python3 -m pytest --cov-fail-under=80") is True
    assert _runs_pytest("uv run pytest-fake --cov-fail-under=80") is False
    assert _runs_pytest("uv run pytest${SUFFIX} --cov-fail-under=80") is False
    assert _runs_pytest("python3 -c pass --cov-fail-under=80") is False


def test_mutation_coverage_step_must_be_a_single_canonical_command(tmp_path, monkeypatch) -> None:
    """変異: pytest の周りに任意のシェルを書いて失敗を伝播させない（R13-16・R13-18）。

    `|| true`・`| tee`・末尾 `&`・`set +e` ＋ 後続の成功コマンド・同名シェル関数の定義は
    いずれも「実行はされるが exit code が伝わらない／実体を指さない」を作る。個別の
    禁止語ではなく **正準コマンド 1 行のみ**という構造要件で一括に塞ぐ。
    """
    def body(line: str) -> str:
        return f"jobs:\n  python:\n    steps:\n{_RESOLVERS}      - run: {line}\n"

    assert _wiring(tmp_path, monkeypatch, "ok.yml", body(_PYTEST_LINE)) == []
    for name, line in (("or.yml", f"{_PYTEST_LINE} || true"),
                       ("pipe.yml", f"{_PYTEST_LINE} | tee out.txt"),
                       ("bg.yml", f"{_PYTEST_LINE} &"),
                       ("semi.yml", f"{_PYTEST_LINE}; true"),
                       ("subst.yml", f"{_PYTEST_LINE} $(echo x)")):
        faults = _wiring(tmp_path, monkeypatch, name, body(line))
        assert any("連結・パイプ・コマンド置換" in f or "配線が無い" in f for f in faults), name
    multi = ("jobs:\n  python:\n    steps:\n" + _RESOLVERS
             + "      - run: |\n          set +e\n          " + _PYTEST_LINE + "\n          true\n")
    assert any("正準コマンド 1 行のみ" in f or "配線が無い" in f
               for f in _wiring(tmp_path, monkeypatch, "seterr.yml", multi))
    shadow = ("jobs:\n  python:\n    steps:\n" + _RESOLVERS
              + "      - run: |\n          pytest() { return 0; }\n          " + _PYTEST_LINE + "\n")
    assert _wiring(tmp_path, monkeypatch, "shadow.yml", shadow) != []


def test_mutation_continue_on_error_is_treated_as_conditional(tmp_path, monkeypatch) -> None:
    """変異: `continue-on-error: true` で失敗を伝播させない（R13-17）。"""
    assert worksets._conditional({"continue-on-error": True}) is True
    assert worksets._conditional({"continue-on-error": "true"}) is True
    assert worksets._conditional({"continue-on-error": False}) is False
    soft_step = (f"jobs:\n  python:\n    steps:\n{_RESOLVERS}"
                 f"      - continue-on-error: true\n        run: {_PYTEST_LINE}\n")
    assert any("失敗許容" in f
               for f in _wiring(tmp_path, monkeypatch, "soft-step.yml", soft_step))
    soft_job = (f"jobs:\n  python:\n    continue-on-error: true\n    steps:\n{_RESOLVERS}"
                f"      - run: {_PYTEST_LINE}\n")
    assert any("条件付き実行" in f
               for f in _wiring(tmp_path, monkeypatch, "soft-job.yml", soft_job))
    soft_resolver = ("jobs:\n  python:\n    steps:\n"
                     "      - id: cov\n        run: python3 tools/coverage_floor.py\n"
                     "      - id: covscope\n        continue-on-error: true\n"
                     "        run: python3 tools/coverage_scope.py\n"
                     f"      - run: {_PYTEST_LINE}\n")
    assert any("resolver step" in f
               for f in _wiring(tmp_path, monkeypatch, "soft-resolver.yml", soft_resolver))


def test_mutation_custom_shell_cannot_swallow_the_exit_code(tmp_path, monkeypatch) -> None:
    """変異: run 本文を正準 1 行に保ったまま custom shell で exit code を捨てる（R13-19）。"""
    evil = "bash -c \"bash {0}; exit 0\""
    step_level = (f"jobs:\n  python:\n    steps:\n{_RESOLVERS}"
                  f"      - shell: '{evil}'\n        run: {_PYTEST_LINE}\n")
    assert any("シェルが正準でない" in f
               for f in _wiring(tmp_path, monkeypatch, "shell-step.yml", step_level))
    job_level = (f"jobs:\n  python:\n    defaults:\n      run:\n        shell: '{evil}'\n"
                 f"    steps:\n{_RESOLVERS}      - run: {_PYTEST_LINE}\n")
    assert any("シェルが正準でない" in f
               for f in _wiring(tmp_path, monkeypatch, "shell-job.yml", job_level))
    wf_level = (f"defaults:\n  run:\n    shell: '{evil}'\n"
                f"jobs:\n  python:\n    steps:\n{_RESOLVERS}      - run: {_PYTEST_LINE}\n")
    assert any("シェルが正準でない" in f
               for f in _wiring(tmp_path, monkeypatch, "shell-wf.yml", wf_level))
    ok = (f"jobs:\n  python:\n    steps:\n{_RESOLVERS}"
          f"      - shell: bash\n        run: {_PYTEST_LINE}\n")
    assert _wiring(tmp_path, monkeypatch, "shell-ok.yml", ok) == []


def test_mutation_unanalyzable_step_breaks_pytest_collect_adjacency(monkeypatch) -> None:
    """変異: 解析不能 step を挟んで junit を差し替える（R13-20）。

    解析不能な run を「不可視」にすると pytest→収集の隣接判定を素通りできる。
    位置を占めるマーカーを返すことで、間に挟まれた step が必ず検出される。
    """
    from tools.gates import test_reality
    assert test_reality._command_lines({"run": "set +e\ncp fake.xml reports/junit.xml"}) == [
        test_reality.UNANALYZABLE]
    doc = test_reality._load_yaml(test_reality.ROOT / ".github/workflows/python-ci.yml")
    job = next(iter(doc["jobs"].values()))
    steps = test_reality._steps(job)
    at = next(i for i, s in enumerate(steps)
              if any("--junitxml" in c for c in test_reality._command_lines(s)))
    tampered = [*steps[:at + 1], {"run": "set +u\ncp fake.xml reports/junit.xml"}, *steps[at + 1:]]
    cmds = [c for s in tampered for c in test_reality._command_lines(s)]
    pos = [next(i for i, c in enumerate(cmds) if test_reality._match(c, n))
           for n in test_reality.CI_STEP_ORDER[:2]]
    assert pos[1] != pos[0] + 1, "解析不能 step が位置を占めず隣接判定が素通りしている"


def test_mutation_wiring_job_rejects_non_canonical_shell_on_any_step(monkeypatch) -> None:
    """変異: collector／run_all step にカスタム shell を置いて失敗を握り潰す（R13-21）。"""
    from tools.gates import test_reality
    doc = test_reality._load_yaml(test_reality.ROOT / ".github/workflows/python-ci.yml")
    job = next(iter(doc["jobs"].values()))
    assert test_reality._shell_faults("python-ci.yml", "python", doc, job) == []
    tampered = {**job, "steps": [{**s, "shell": 'bash -c "bash {0}; exit 0"'}
                                 if isinstance(s.get("run"), str) else s
                                 for s in job["steps"]]}
    assert any("非正準シェル" in f
               for f in test_reality._shell_faults("python-ci.yml", "python", doc, tampered))
    by_job = {**doc, "jobs": {}}
    assert any("非正準シェル" in f for f in test_reality._shell_faults(
        "python-ci.yml", "python", {**by_job, "defaults": {"run": {"shell": "pwsh"}}}, job))


def test_mutation_unparseable_command_occupies_a_position(monkeypatch) -> None:
    """変異: 解析不能オプションの step を挟んで junit を差し替える（R13-22）。"""
    from tools.gates import test_reality
    assert test_reality._command_lines({"run": "env -C . python3 overwrite_junit.py"}) == [
        test_reality.UNANALYZABLE]
    assert test_reality._command_lines({"run": "false && cp fake.xml reports/junit.xml"}) == [
        test_reality.UNANALYZABLE]


def test_mutation_indirect_binding_in_a_planned_workset_module_is_stray(monkeypatch) -> None:
    """変異: planned Workset のモジュールへ再エクスポートだけ置いて強制を外す（R13-23）。"""
    mod = worksets.du_module(CTX, "DU-10")
    monkeypatch.setattr(worksets, "binding_signals",
                        lambda ctx: [f"du-api-bind:DU-10:{mod}:connect=alias"], raising=False)
    import tools.gates.test_reality as tr
    monkeypatch.setattr(tr, "binding_signals",
                        lambda ctx, pkg=None: [f"du-api-bind:DU-10:{mod}:connect=alias"])
    assert mod in worksets.implemented_modules(CTX)
    assert any("着手済み Workset に属さないモジュールへ実装がある" in f
               for f in worksets.scope_faults(CTX, worksets.load_worksets()))
