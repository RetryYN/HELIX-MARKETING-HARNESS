"""実行時テスト実体ゲート（test_reality）の単体テスト・負例・mutation test。

負例は「実際に赤くなること」を実測で示す。とくに **静的検査（AST）を素通りする skip** を
outcome 経由で捕まえられることが本モジュールの存在理由なので、動的 import で組み立てた
skip を含む合成 outcome を食わせて検出を確かめる。
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.gates import test_pairing, test_reality
from tools.gates.common import CTX, ROOT

SCHEMA = test_reality.OUTCOME_SCHEMA


JUNIT_TEMPLATE = (
    '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
    '<testcase classname="tests.unit.test_x" name="test_y" file="tests/unit/test_x.py"/>'
    "</testsuite></testsuites>"
)


def _junit(tmp_path: Path, monkeypatch, xml: str = JUNIT_TEMPLATE) -> Path:
    """生成元 junit を差し替える（本番の reports/ の有無に依存させない）。"""
    p = tmp_path / "junit.xml"
    p.write_text(xml, encoding="utf-8")
    monkeypatch.setattr(test_reality, "JUNIT_XML", p)
    monkeypatch.setattr(test_reality, "ROOT", tmp_path)
    return p


def _report(tmp_path: Path, tests: list[dict], junit: Path | None = None, **over) -> Path:
    """レポートを合成する。junit を渡した場合は totals も再導出と揃える。"""
    data = {
        "schema": SCHEMA,
        "generated_by": "scripts/collect_test_outcome.py",
        "commit": test_reality.git("rev-parse", "HEAD").stdout.strip(),
        "source": "junit.xml" if junit else "reports/junit.xml",
        "source_digest": test_reality.hashlib.sha256(junit.read_bytes()).hexdigest()
        if junit else "0" * 64,
        "totals": {k: sum(1 for t in tests if t.get("outcome") == k)
                   for k in test_reality.OUTCOME_VALUES} | {"total": len(tests)},
        "tests": tests,
    }
    data.update(over)
    p = tmp_path / "test-outcome.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def _valid(tmp_path: Path, monkeypatch, **over) -> Path:
    """再導出まで一致する**正当な**レポート（負例はここから 1 点だけ崩す）。"""
    junit = _junit(tmp_path, monkeypatch)
    return _report(tmp_path, [{"nodeid": "tests/unit/test_x.py::test_y",
                               "outcome": "passed", "reason": ""}], junit=junit, **over)


def _targets(n: int = 2) -> list[str]:
    return test_reality.s0_target_nodeids(CTX)[:n]


# ---------------------------------------------------------------- レポートの健全性
def test_target_nodeids_are_repo_relative_and_nonempty() -> None:
    targets = test_reality.s0_target_nodeids(CTX)
    assert targets, "S0.1 対象 UT が 0 件では実行時ゲートが空回りする"
    assert all(n.startswith("tests/unit/") and "::" in n for n in targets)


def test_report_faults_accepts_a_report_that_rederives_from_its_junit(tmp_path, monkeypatch) -> None:
    """正例: 収集スクリプトが junit から作ったとおりのレポートは通る。"""
    assert test_reality.report_faults(_valid(tmp_path, monkeypatch)) == []


def test_report_faults_is_empty_when_report_is_absent(tmp_path) -> None:
    """未生成のうちは形式違反ではない（存在の要否は着手状態で決める）。"""
    assert test_reality.report_faults(tmp_path / "nope.json") == []


def test_mutation_report_pointing_at_another_junit_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 生成元を任意のパスへ差し替えて digest 照合を骨抜きにする。"""
    p = _valid(tmp_path, monkeypatch, source="elsewhere/mine.xml")
    assert any("source が" in f for f in test_reality.report_faults(p))


def test_mutation_junit_without_report_regeneration_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 生成元 junit を消してレポートだけ残す。"""
    junit = _junit(tmp_path, monkeypatch)
    p = _report(tmp_path, [], junit=junit)
    junit.unlink()
    assert any("実在しない" in f for f in test_reality.report_faults(p))


def test_mutation_handwritten_tests_do_not_match_the_junit_rederivation(
        tmp_path, monkeypatch) -> None:
    """変異: junit はそのままに JSON 側だけ『対象 UT は passed』へ書き換える。

    収集スクリプトを同じ junit で走らせた結果と一致しないレポートは受け付けない。
    手書き JSON はこの再導出照合で必ず落ちる（独立レビュー R1-01）。
    """
    junit = _junit(tmp_path, monkeypatch)
    forged = [{"nodeid": n, "outcome": "passed", "reason": ""} for n in _targets(3)]
    p = _report(tmp_path, forged, junit=junit)
    assert any("再導出と不一致" in f for f in test_reality.report_faults(p))


def test_mutation_committing_the_outcome_artifact_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: reports/ を commit して「実行済み」の証跡を固定化する。"""
    p = _valid(tmp_path, monkeypatch)
    monkeypatch.setattr(test_reality, "git",
                        lambda *a: type("R", (), {"stdout": "reports/test-outcome.json\n"})())
    assert any("git 追跡下" in f for f in test_reality.report_faults(p))


def test_mutation_tracked_reports_are_rejected_even_without_a_report(monkeypatch, tmp_path) -> None:
    """変異: レポートを置かずに reports/ だけ commit する（早期 return での素通り）。"""
    monkeypatch.setattr(test_reality, "git",
                        lambda *a: type("R", (), {"stdout": "reports/junit.xml\n"})())
    assert any("git 追跡下" in f for f in test_reality.report_faults(tmp_path / "absent.json"))
    assert test_reality.tracked_reports_faults()


def test_mutation_outcome_report_from_another_commit_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 別コミットで作った outcome を貼れば『対象 UT は passed だった』と主張できる。"""
    p = _valid(tmp_path, monkeypatch, commit="0" * 40)
    assert any("HEAD" in f for f in test_reality.report_faults(p))


def test_mutation_handwritten_report_without_collector_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 収集スクリプトを通さない手書きレポートを受け付けない。"""
    p = _valid(tmp_path, monkeypatch, generated_by="me")
    assert any("generated_by" in f for f in test_reality.report_faults(p))


def test_mutation_unknown_outcome_vocabulary_is_rejected(tmp_path, monkeypatch) -> None:
    junit = _junit(tmp_path, monkeypatch)
    p = _report(tmp_path, [{"nodeid": "tests/unit/test_x.py::test_y", "outcome": "green"}],
                junit=junit)
    assert any("語彙外" in f for f in test_reality.report_faults(p))


def test_mutation_duplicate_nodeid_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 同じ nodeid を passed で二重計上して skip を薄める。"""
    junit = _junit(tmp_path, monkeypatch)
    p = _report(tmp_path, [{"nodeid": "tests/unit/test_x.py::test_y", "outcome": "skipped"},
                           {"nodeid": "tests/unit/test_x.py::test_y", "outcome": "passed"}],
                junit=junit)
    assert any("重複" in f for f in test_reality.report_faults(p))


def test_mutation_tampered_junit_digest_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: junit xml を書き換えてから JSON 側の digest を据え置く。"""
    p = _valid(tmp_path, monkeypatch, source_digest="f" * 64)
    assert any("source_digest" in f for f in test_reality.report_faults(p))


# ---------------------------------------------------------------- 実行時 skip の検出
def test_runtime_skip_of_target_ut_is_detected(tmp_path) -> None:
    target = _targets(1)[0]
    data = json.loads(_report(tmp_path, [{"nodeid": target, "outcome": "skipped"}]).read_text())
    assert test_reality.runtime_skips(CTX, data) == [target]


def test_parametrized_nodeid_folds_to_the_declared_nodeid(tmp_path) -> None:
    """パラメータ化（`::test_x[case]`）でも宣言 nodeid として突合できる。"""
    target = _targets(1)[0]
    data = json.loads(_report(tmp_path, [{"nodeid": f"{target}[case-1]", "outcome": "passed"},
                                         {"nodeid": f"{target}[case-2]", "outcome": "skipped"}]
                              ).read_text())
    # 1 件でも passed でなければ passed を名乗れない（最悪値優先）
    assert test_reality.outcome_index(data)[target] == "skipped"


def _run_pytest_and_collect(tmp_path: Path, source: str) -> tuple[dict, str]:
    """一時テストを **実際に pytest で実行**し、収集スクリプトの実出力を返す。

    合成 outcome ではなく本番経路（pytest → junit xml → collect）を通すことで、
    「動的 skip が実行結果に skipped として現れる」ことそのものを実測する。
    """
    tf = tmp_path / "test_dynamic_stub.py"
    tf.write_text(source, encoding="utf-8")
    junit = tmp_path / "junit.xml"
    subprocess.run([sys.executable, "-m", "pytest", str(tf), f"--junitxml={junit}",
                    "-p", "no:cacheprovider", "-q"],
                   cwd=tmp_path, capture_output=True, check=False)
    mod = test_reality._collector()
    data = mod.collect(junit)
    nodeid = next(t["nodeid"] for t in data["tests"])
    return data, nodeid


def test_mutation_dynamic_import_skip_is_invisible_to_ast_but_caught_at_runtime(
        tmp_path, monkeypatch) -> None:
    """変異: `importlib` で組み立てた skip は AST 検査を素通りする → 実行結果で捕まえる。

    (1) 静的検査（`test_pairing._function_escapes`）がこの skip を**検出できない**ことを実証し、
    (2) 実際に pytest を走らせた outcome では skipped として現れ、
    (3) 本番の `runtime_skips`／`statically_invisible_skips`／`per_test_faults` が拾う
    ——という 3 点を、結果の注入なしで通す。
    """
    src = ("import importlib\n"
           "def test_dynamic_skip():\n"
           "    getattr(importlib.import_module('pytest'), 'skip')('動的 skip')\n"
           "    assert False\n")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    assert test_pairing._function_escapes(fn, test_pairing._origins(tree)) == [], \
        "この skip が静的に見えているなら、実行時ゲートの存在意義の前提が崩れる"

    data, nodeid = _run_pytest_and_collect(tmp_path, src)
    assert test_reality.outcome_index(data)[nodeid] == "skipped"

    monkeypatch.setattr(test_reality, "s0_target_nodeids", lambda ctx: [nodeid])
    assert test_reality.runtime_skips(CTX, data) == [nodeid]
    assert test_reality.statically_invisible_skips(CTX, data) == [nodeid]
    assert any(nodeid in f and "skipped" in f for f in test_reality.per_test_faults(CTX, data))


def test_dynamic_xfail_is_caught_at_runtime(tmp_path, monkeypatch) -> None:
    """動的に組み立てた xfail も実行結果（xfailed）で捕まえる。"""
    src = ("import importlib\n"
           "def test_dynamic_xfail():\n"
           "    getattr(importlib.import_module('pytest'), 'xfail')('動的 xfail')\n")
    data, nodeid = _run_pytest_and_collect(tmp_path, src)
    assert test_reality.outcome_index(data)[nodeid] == "xfailed"
    monkeypatch.setattr(test_reality, "s0_target_nodeids", lambda ctx: [nodeid])
    assert test_reality.runtime_skips(CTX, data) == [nodeid]


def test_passing_test_is_not_flagged(tmp_path, monkeypatch) -> None:
    """偽陽性: 実際に通ったテストは skip としても未成立としても報告しない。"""
    data, nodeid = _run_pytest_and_collect(tmp_path, "def test_ok():\n    assert 1 == 1\n")
    monkeypatch.setattr(test_reality, "s0_target_nodeids", lambda ctx: [nodeid])
    assert test_reality.runtime_skips(CTX, data) == []
    assert test_reality.per_test_faults(CTX, data) == []


def test_statically_visible_skip_is_not_double_counted(monkeypatch) -> None:
    """AST が既に検出している skip は『不可視』として二重に数えない。"""
    target = _targets(1)[0]
    fname = target.split("/")[-1].split("::")[0]
    tname = target.split("::")[1]
    monkeypatch.setattr(test_reality, "runtime_skips",
                        lambda ctx, data, nodeids=None: [target])
    monkeypatch.setattr(test_pairing, "detect_ut_escapes",
                        lambda ctx, du_ids=None: [f"DU-01:{fname}::{tname}:skip"])
    assert test_reality.statically_invisible_skips(CTX, {}) == []


# ---------------------------------------------------------------- nodeid 単位の突合
def test_per_test_faults_flags_missing_and_non_passed(tmp_path) -> None:
    targets = _targets(2)
    data = json.loads(_report(tmp_path, [{"nodeid": targets[0], "outcome": "failed"}]).read_text())
    faults = test_reality.per_test_faults(CTX, data)
    assert any(targets[0] in f and "failed" in f for f in faults)
    assert any(targets[1] in f and "存在しない" in f for f in faults)


def test_mutation_aggregate_pass_count_cannot_substitute_for_target_uts(tmp_path) -> None:
    """変異: 無関係なテストを大量に passed にして「全部 green」と称する。"""
    others = [{"nodeid": f"tests/unit/test_other.py::test_{i}", "outcome": "passed"}
              for i in range(500)]
    data = json.loads(_report(tmp_path, others).read_text())
    faults = test_reality.per_test_faults(CTX, data)
    assert len(faults) == len(test_reality.s0_target_nodeids(CTX))


# ---------------------------------------------------------------- 間接束縛の着手検出
def _pkg(tmp_path: Path, body: str) -> Path:
    pkg = tmp_path / "helix"
    pkg.mkdir()
    (pkg / "kernel.py").write_text(body, encoding="utf-8")
    return pkg


def _s0_api(du: str = "DU-01") -> str:
    return next(a["signature"].split("(")[0].removeprefix("def ").strip()
                for d in CTX.duc if d["id"] == du for a in d["apis"])


def test_mutation_partial_binding_is_detected_as_implementation(tmp_path) -> None:
    """変異: `def` を書かず `functools.partial` で API を束縛して着手検出を回避する。"""
    api = _s0_api()
    body = f"import functools\nfrom ._impl import real\n{api} = functools.partial(real, 1)\n"
    sig = test_reality.binding_signals(CTX, _pkg(tmp_path, body))
    assert any(s.startswith("du-api-bind:DU-01:") and api in s for s in sig)


@pytest.mark.parametrize("template", [
    "setattr(obj, '{api}', real)",          # 動的属性束縛
    "obj.{api} = real",                     # 属性代入
    "REGISTRY['{api}'] = real",             # 添字（レジストリ）登録
    "globals()['{api}'] = real",            # グローバル注入
    "REGISTRY.update({{'{api}': real}})",   # 辞書一括登録
    "register('{api}', real)",              # 2 引数の登録関数
    "{api} = decorate(real)",               # デコレータ適用の代入
    "{api}: object = real",                 # 注釈付き別名
])
def test_mutation_indirect_binding_variants_are_detected(tmp_path, template: str) -> None:
    """変異: Name 代入以外の経路で API を束縛して着手検出を回避する。"""
    api = _s0_api()
    body = ("from ._impl import real, decorate, register, obj\n"
            "REGISTRY = {}\n" + template.format(api=api) + "\n")
    sig = test_reality.binding_signals(CTX, _pkg(tmp_path, body))
    assert any(s.startswith("du-api-bind:") and api in s for s in sig), sig


@pytest.mark.parametrize("stages", [2, 6, 12])
def test_mutation_multi_stage_binding_is_detected(tmp_path, stages: int) -> None:
    """変異: 何段も別名を挟んでから API 名へ束縛する（固定点に収束するまで追う）。"""
    api = _s0_api()
    chain = "".join(f"_a{i + 1} = _a{i}\n" for i in range(stages))
    body = ("import functools\nfrom ._impl import real\n"
            "_a0 = functools.partial(real, 1)\n" + chain + f"{api} = _a{stages}\n")
    sig = test_reality.binding_signals(CTX, _pkg(tmp_path, body))
    assert any(s.startswith("du-api-bind:") and api in s for s in sig), sig


@pytest.mark.parametrize("expr", [
    "REGISTRY['real']",                 # 添字経由（独立レビュー R4-03）
    "real if FLAG else real",           # 条件式
    "(real,)[0]",                       # タプル添字
    "[real][0]",                        # リスト添字
    "getattr(mod, 'real')",             # 動的属性取得
])
def test_mutation_expression_carried_bindings_are_detected(tmp_path, expr: str) -> None:
    """変異: 単純な代入以外の式で実装を API 名へ運ぶ。"""
    api = _s0_api()
    body = ("from ._impl import real, REGISTRY, FLAG, mod\n" + f"{api} = {expr}\n")
    sig = test_reality.binding_signals(CTX, _pkg(tmp_path, body))
    assert any(s.startswith("du-api-bind:") and api in s for s in sig), sig


def test_multi_stage_binding_written_in_reverse_order_is_detected(tmp_path) -> None:
    """束縛の記述順が逆でも（前方参照）検出する。"""
    api = _s0_api()
    body = ("import functools\nfrom ._impl import real\n"
            f"{api} = _b2\n_b2 = _b1\n_b1 = functools.partial(real, 1)\n")
    sig = test_reality.binding_signals(CTX, _pkg(tmp_path, body))
    assert any(s.startswith("du-api-bind:") and api in s for s in sig), sig


def test_non_api_bindings_are_not_start_signals(tmp_path) -> None:
    """偽陽性: API 名でない内部ヘルパの別名・再エクスポート・定数は着手ではない。"""
    body = ("from ._impl import real\n"
            "__all__ = ['a']\nTIMEOUT = 30\nNAMES = {'a': 1}\n"
            "helper = real\nrows = dict(a=real)\n")
    assert test_reality.binding_signals(CTX, _pkg(tmp_path, body)) == []


def test_binding_signals_feed_impl_start_detection(tmp_path, monkeypatch) -> None:
    """間接束縛が着手シグナルへ合流し、skip・coverage のラチェットを発火させる。"""
    api = _s0_api()
    monkeypatch.setattr(test_reality, "SRC_PKG",
                        _pkg(tmp_path, f"from ._impl import real\n{api} = real\n"))
    assert any(s.startswith("bind:") for s in test_pairing.impl_start_signals(CTX))
    assert test_pairing.detect_impl_started(CTX) is True


def test_syntax_error_in_src_is_fail_close(tmp_path) -> None:
    pkg = _pkg(tmp_path, "def broken(:\n")
    assert test_reality.file_bindings(pkg / "kernel.py") == [("<parse-error>", "syntax")]
    assert any(s.startswith("parse-error:") for s in test_reality.binding_signals(CTX, pkg))


# ---------------------------------------------------------------- CI 配線
def test_ci_wiring_is_complete_in_production() -> None:
    assert test_reality.ci_wiring_faults() == []


def test_mutation_missing_ci_wiring_is_detected(monkeypatch) -> None:
    """変異: outcome の生成を CI から外して実行時ゲートを空にする。"""
    monkeypatch.setattr(test_reality, "CI_WORKFLOWS", (".github/workflows/nonexistent.yml",))
    assert any("ワークフローが存在しない" in f for f in test_reality.ci_wiring_faults())


def _wf(tmp_path: Path, steps: str) -> Path:
    p = tmp_path / "wf.yml"
    p.write_text("name: t\non: [push]\njobs:\n  j:\n    runs-on: ubuntu-latest\n"
                 "    steps:\n" + steps, encoding="utf-8")
    return p


def test_mutation_commented_out_or_disabled_steps_are_not_wiring(tmp_path, monkeypatch) -> None:
    """変異: 語だけコメント／`if: false` で残し、実体の収集ステップを外す。"""
    steps = ("      - name: pytest\n        run: pytest --junitxml=reports/junit.xml\n"
             "      # - run: python3 scripts/collect_test_outcome.py\n"
             "      - name: collect (disabled)\n        if: false\n"
             "        run: python3 scripts/collect_test_outcome.py\n"
             "      - run: python3 tools/gates/run_all.py\n")
    wf = _wf(tmp_path, steps)
    monkeypatch.setattr(test_reality, "ROOT", tmp_path)
    monkeypatch.setattr(test_reality, "CI_WORKFLOWS", (wf.name,))
    monkeypatch.setattr(test_reality, "UPLOAD_WORKFLOW", wf.name)
    assert any("順序が無い" in f for f in test_reality.ci_wiring_faults())


def test_mutation_collection_after_the_gate_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 収集をゲートの後ろへ動かし、ゲートがレポートを読めない配線にする。"""
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             "      - run: python3 tools/gates/run_all.py\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             "      - uses: actions/upload-artifact@v4\n")
    wf = _wf(tmp_path, steps)
    monkeypatch.setattr(test_reality, "ROOT", tmp_path)
    monkeypatch.setattr(test_reality, "CI_WORKFLOWS", (wf.name,))
    monkeypatch.setattr(test_reality, "UPLOAD_WORKFLOW", wf.name)
    assert any("順序が無い" in f for f in test_reality.ci_wiring_faults())


UPLOAD_STEP = ("      - uses: actions/upload-artifact@v4\n        with:\n"
               "          name: pytest-outcome\n"
               "          path: |\n"
               "            reports/junit.xml\n            reports/test-outcome.json\n"
               "          if-no-files-found: error\n")
WIRED_STEPS = ("      - run: pytest --junitxml=reports/junit.xml\n"
               "      - run: python3 scripts/collect_test_outcome.py\n"
               "      - run: python3 tools/gates/run_all.py\n")


def _wire(tmp_path: Path, monkeypatch, steps: str) -> None:
    wf = _wf(tmp_path, steps)
    monkeypatch.setattr(test_reality, "ROOT", tmp_path)
    monkeypatch.setattr(test_reality, "CI_WORKFLOWS", (wf.name,))
    monkeypatch.setattr(test_reality, "UPLOAD_WORKFLOW", wf.name)


def test_wiring_accepts_a_correctly_ordered_job(tmp_path, monkeypatch) -> None:
    _wire(tmp_path, monkeypatch, WIRED_STEPS + UPLOAD_STEP)
    assert test_reality.ci_wiring_faults() == []


def test_mutation_missing_artifact_upload_is_detected(tmp_path, monkeypatch) -> None:
    """変異: outcome を CI 成果物として残さない（PO 指示の『CI 成果物として取得』の骨抜き）。"""
    _wire(tmp_path, monkeypatch, WIRED_STEPS)
    assert any("upload していない" in f for f in test_reality.ci_wiring_faults())


def test_mutation_upload_without_the_outcome_json_is_detected(tmp_path, monkeypatch) -> None:
    """変異: junit だけ upload して正規化済み outcome を残さない。"""
    partial_upload = UPLOAD_STEP.replace("            reports/test-outcome.json\n", "")
    _wire(tmp_path, monkeypatch, WIRED_STEPS + partial_upload)
    assert any("reports/test-outcome.json が無い" in f for f in test_reality.ci_wiring_faults())


def test_mutation_upload_without_fail_on_missing_files_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 成果物が無くても素通りする upload（if-no-files-found を warn に落とす）。"""
    _wire(tmp_path, monkeypatch,
          WIRED_STEPS + UPLOAD_STEP.replace("if-no-files-found: error", "if-no-files-found: warn"))
    assert any("if-no-files-found" in f for f in test_reality.ci_wiring_faults())


def test_mutation_echo_only_wiring_is_not_accepted(tmp_path, monkeypatch) -> None:
    """変異: 語だけ echo して実体のコマンドを外す。"""
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             '      - run: echo "python3 scripts/collect_test_outcome.py"\n'
             "      - run: python3 tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


def test_mutation_single_non_executing_command_cannot_fake_the_wiring(
        tmp_path, monkeypatch) -> None:
    """変異: 1 つの非実行コマンドの引数へ 3 語を並べて配線を偽装する（独立レビュー R3-01）。"""
    steps = ("      - run: false --junitxml scripts/collect_test_outcome.py "
             "tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


def test_mutation_reusing_one_command_for_all_three_requirements_is_detected(
        tmp_path, monkeypatch) -> None:
    """変異: 同じ 1 コマンドを 3 要件すべてに使い回す（位置の再利用）。"""
    steps = ("      - run: pytest --junitxml=reports/junit.xml "
             "scripts/collect_test_outcome.py tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


@pytest.mark.parametrize("steps", [
    # 実行しないコマンド形で語だけ置く（独立レビュー R4-01）
    ("      - run: false pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    ("      - run: pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 -c scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    ("      - run: pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: uv --help tools/gates/run_all.py\n"),
    # 条件付き実行の左辺を必ず失敗させる
    ("      - run: false && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    # 環境変数代入で guard を隠す（独立レビュー R5-01）
    ("      - run: FLAG=1 false && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    # --help を後置して実行しない形にする
    ("      - run: pytest --help --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    # env のオプション引数の陰に guard を隠す（独立レビュー R6-01・R7-01）
    ("      - run: env -u CI false && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    ("      - run: env -C /tmp false && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    ("      - run: env --chdir /tmp false && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    # 値の無い -u で解析を崩す（独立レビュー R8-01）
    ("      - run: env -u && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    ("      - run: env --unset && pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
    # ランナを二重に連ねて実行対象を曖昧にする
    ("      - run: python3 uv run pytest --junitxml=reports/junit.xml\n"
     "      - run: python3 scripts/collect_test_outcome.py\n"
     "      - run: python3 tools/gates/run_all.py\n"),
])
def test_mutation_non_executing_command_forms_are_rejected(tmp_path, monkeypatch, steps) -> None:
    """変異: コマンドを実行しない形（false／-c／--help／条件付き左辺）で配線を偽装する。"""
    _wire(tmp_path, monkeypatch, steps + UPLOAD_STEP)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


@pytest.mark.parametrize("needle", ["pytest --junitxml=reports/junit.xml",
                                   "python3 scripts/collect_test_outcome.py",
                                   "python3 tools/gates/run_all.py"])
def test_mutation_control_operators_cannot_swallow_wiring_exit_codes(
        tmp_path, monkeypatch, needle: str) -> None:
    """変異: 配線 step に `|| true`／パイプを付けて失敗を成功へ変える（独立レビュー R13-24）。

    `&&` 連結だけを配線として認め、`||`・`;`・パイプ・バックグラウンドを含む行は
    解析不能に倒す。3 つの配線コマンドのどれに付けても配線が成立しなくなる。
    """
    base = ["pytest --junitxml=reports/junit.xml",
            "python3 scripts/collect_test_outcome.py",
            "python3 tools/gates/run_all.py"]
    steps = "".join(f"      - run: {c} || true\n" if c == needle else f"      - run: {c}\n"
                    for c in base) + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f or "間に別コマンド" in f
               for f in test_reality.ci_wiring_faults())


def test_mutation_injecting_a_command_between_pytest_and_collection_is_detected(
        tmp_path, monkeypatch) -> None:
    """変異: pytest と収集の間にコマンドを挟み、生成された junit を差し替える。"""
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             "      - run: python3 tools/forge_junit.py\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             "      - run: python3 tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("間に別コマンド" in f for f in test_reality.ci_wiring_faults())


@pytest.mark.parametrize("pytest_cmd", [
    "PYTHONWARNINGS=error pytest --junitxml=reports/junit.xml",
    "env PYTHONWARNINGS=error pytest --junitxml=reports/junit.xml",
    "uv run --frozen pytest --junitxml=reports/junit.xml",
    "env -u CI pytest --junitxml=reports/junit.xml",
    "env -- pytest --junitxml=reports/junit.xml",
])
def test_legitimate_pytest_invocations_are_accepted(tmp_path, monkeypatch, pytest_cmd) -> None:
    """偽陽性: 環境変数付き・env 経由・uv のオプション付きも配線として認める。"""
    steps = (f"      - run: {pytest_cmd}\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             "      - run: python3 tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert test_reality.ci_wiring_faults() == []


def test_upload_of_other_artifacts_before_the_outcome_is_accepted(tmp_path, monkeypatch) -> None:
    """偽陽性: 先に別成果物を upload する構成でも、正しい outcome upload があれば通る。"""
    other = ("      - uses: actions/upload-artifact@v4\n        with:\n"
             "          name: coverage\n          path: coverage.xml\n")
    _wire(tmp_path, monkeypatch, WIRED_STEPS + other + UPLOAD_STEP)
    assert test_reality.ci_wiring_faults() == []


def test_mutation_out_of_order_within_one_step_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 1 つの step に押し込んで順序を入れ替える（step 単位検査の隙）。"""
    steps = ("      - run: |\n"
             "          pytest --junitxml=reports/junit.xml\n"
             "          python3 tools/gates/run_all.py\n"
             "          python3 scripts/collect_test_outcome.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


@pytest.mark.parametrize("toml_text", [
    "[tool.pytest.ini_options]\naddopts = '-q'\n",                    # キーごと削除
    "[tool.pytest.ini_options]\nxfail_strict = false\n",              # false へ反転
    "[tool.pytest.ini_options]\nxfail_strict = 'true'\n",             # 文字列で偽装
    "[tool.other]\nxfail_strict = true\n",                            # 別セクションへ移動
])
def test_mutation_disabling_xfail_strict_is_detected(tmp_path, monkeypatch, toml_text) -> None:
    """変異: xfail_strict を外して xpass を passed として素通りさせる。"""
    p = tmp_path / "pyproject.toml"
    p.write_text(toml_text, encoding="utf-8")
    monkeypatch.setattr(test_reality, "PYPROJECT", p)
    assert any("xfail_strict" in f for f in test_reality.ci_wiring_faults())


def test_collector_reconstructs_nodeids_from_junit(tmp_path) -> None:
    """収集スクリプトが junit の属性から pytest の nodeid を復元する。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "collect_test_outcome", ROOT / "scripts/collect_test_outcome.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
        '<testcase classname="tests.unit.test_x" name="test_a" file="tests/unit/test_x.py"/>'
        '<testcase classname="tests.unit.test_x.TestG" name="test_b" file="tests/unit/test_x.py">'
        '<skipped type="pytest.skip" message="stub"/></testcase>'
        '<testcase classname="tests.unit.test_x" name="test_c" file="tests/unit/test_x.py">'
        '<failure message="boom"/></testcase>'
        "</testsuite></testsuites>", encoding="utf-8")
    data = mod.collect(junit)
    by = {t["nodeid"]: t["outcome"] for t in data["tests"]}
    assert by["tests/unit/test_x.py::test_a"] == "passed"
    assert by["tests/unit/test_x.py::TestG::test_b"] == "skipped"
    assert by["tests/unit/test_x.py::test_c"] == "failed"


@pytest.mark.parametrize("gate_id", ["G-UT-RUNTIME-OUTCOME", "G-UT-DYNAMIC-SKIP",
                                     "G-IMPL-START-BINDING", "G-UT-PER-TEST-OUTCOME"])
def test_all_four_preconditions_gates_are_emitted(gate_id: str) -> None:
    """PO 指定の 4 前提条件に対応する専用ゲートが**本番で** emit されている。"""
    from tools.gates.baseline import script_gate_ids
    assert gate_id in script_gate_ids()


@pytest.mark.parametrize("suffix", ["$(python3 tools/forge.py)", "`python3 tools/forge.py`"])
def test_mutation_command_substitution_in_wiring_is_rejected(tmp_path, monkeypatch, suffix) -> None:
    """変異: 引数のコマンド置換で収集の直前に junit を差し替える（独立レビュー R13-26）。"""
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             f"      - run: python3 scripts/collect_test_outcome.py {suffix}\n"
             "      - run: python3 tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


def test_mutation_env_prefixed_set_plus_e_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: `X=1 set +e` で errexit を解除してゲート失敗を握り潰す（独立レビュー R13-27）。"""
    assert test_reality._shadowing("X=1 set +e\npython3 tools/gates/run_all.py") is True
    assert test_reality._shadowing("set -euo pipefail\npytest") is False
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             "      - run: |\n          X=1 set +e\n          python3 tools/gates/run_all.py\n"
             ) + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("実行順序が無い" in f for f in test_reality.ci_wiring_faults())


@pytest.mark.parametrize("where", ["step", "job"])
def test_mutation_continue_on_error_breaks_the_wiring(tmp_path, monkeypatch, where) -> None:
    """変異: `continue-on-error: true` でゲート失敗を CI へ伝播させない（R13-25）。"""
    soft = "        continue-on-error: true\n" if where == "step" else ""
    job_soft = "    continue-on-error: true\n" if where == "job" else ""
    steps = ("      - run: pytest --junitxml=reports/junit.xml\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             f"      - run: python3 tools/gates/run_all.py\n{soft}") + UPLOAD_STEP
    ci = tmp_path / "wf.yml"
    ci.write_text(f"jobs:\n  python:\n{job_soft}    steps:\n{steps}", encoding="utf-8")
    monkeypatch.setattr(test_reality, "CI_WORKFLOWS", (str(ci),))
    monkeypatch.setattr(test_reality, "ROOT", tmp_path)
    monkeypatch.setattr(test_reality, "UPLOAD_WORKFLOW", str(ci))
    assert any("continue-on-error" in f for f in test_reality.ci_wiring_faults())


def test_mutation_expression_forged_command_substitution_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: GHA 式で `$` を作り、展開後にコマンド置換を合成する（独立レビュー R13-28）。"""
    forged = "python3 scripts/collect_test_outcome.py ${{ '$' }}(python3 forge.py)"
    assert test_reality._command_lines({"run": forged}) == [test_reality.UNANALYZABLE]
    assert test_reality._without_expressions("a ${{ steps.cov.outputs.floor }}") == "a "
    assert test_reality._without_expressions("a ${{ '$' }}") is None


def test_mutation_heredoc_body_is_not_wiring(tmp_path, monkeypatch) -> None:
    """変異: heredoc の中に配線コマンドを並べて実行せずに配線を偽装する（R13-30）。"""
    body = ("cat <<'EOF'\\npytest --junitxml=reports/junit.xml\\n"
            "python3 scripts/collect_test_outcome.py\\npython3 tools/gates/run_all.py\\nEOF")
    assert test_reality._command_lines({"run": body.replace("\\n", "\n")}) == [
        test_reality.UNANALYZABLE]


def test_mutation_shadowing_detects_segments_and_env_prefixes() -> None:
    """変異: `&&` の右辺・env 前置に関数定義／alias を置く（独立レビュー R13-29）。"""
    assert test_reality._shadowing("true && pytest() {\n  return 0\n}") is True
    assert test_reality._shadowing("X=1 alias pytest=true") is True
    assert test_reality._shadowing("true && X=1 set +e") is True
    assert test_reality._shadowing("set -euo pipefail\nuv run pytest") is False


def test_mutation_externally_controlled_expressions_are_rejected() -> None:
    """変異: 外部制御の GHA コンテキストを配線行へ差し込む（独立レビュー R13-31）。"""
    assert test_reality._without_expressions("pytest ${{ github.event.pull_request.title }}") is None
    assert test_reality._without_expressions("pytest ${{ inputs.args }}") is None
    assert test_reality._without_expressions("pytest ${{ steps.cov.outputs.floor }}") == "pytest "
    assert test_reality._command_lines(
        {"run": "pytest --junitxml=reports/junit.xml ${{ github.event.issue.body }}"}) == [
        test_reality.UNANALYZABLE]


def test_mutation_shadowing_covers_eval_source_and_export_f() -> None:
    """変異: eval／source／export -f で偽 pytest を注入する（独立レビュー R13-32）。"""
    assert test_reality._shadowing("eval 'pytest() { return 0; }'") is True
    assert test_reality._shadowing("source ./evil.sh") is True
    assert test_reality._shadowing("export -f pytest") is True
    assert test_reality._shadowing("BASH_ENV=./evil.sh uv run pytest") is True
    # `.` は source と等価。Path 正規化で空文字に潰れて素通りしないこと（R13-33）
    assert test_reality._shadowing(". ./evil.sh\nuv run pytest -q") is True
    assert test_reality._command_lines(
        {"run": ". ./ci-helpers.sh\nuv run pytest -q --junitxml=reports/junit.xml"}) == [
        test_reality.UNANALYZABLE]
    assert test_reality._shadowing("uv run pytest --junitxml=reports/junit.xml") is False


def test_mutation_unanalyzable_before_the_wiring_is_rejected(tmp_path, monkeypatch) -> None:
    """変異: 配線の前段で実行主体を差し替える（同一 run の関数定義は後続に効く）。"""
    steps = ("      - run: |\n          eval 'pytest() { return 0; }'\n"
             "          uv run pytest --junitxml=reports/junit.xml\n"
             "      - run: python3 scripts/collect_test_outcome.py\n"
             "      - run: python3 tools/gates/run_all.py\n") + UPLOAD_STEP
    _wire(tmp_path, monkeypatch, steps)
    assert any("前段に解析不能" in f or "実行順序が無い" in f
               for f in test_reality.ci_wiring_faults())
