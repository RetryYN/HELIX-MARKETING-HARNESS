"""test_pairing ゲートの単体テストと mutation test（S0.1 着手検出・skip 逃げ道封じ）。"""

import json
import textwrap
from pathlib import Path

import pytest

from tools.gates import test_pairing
from tools.gates.common import CTX


def test_s0_1_not_started_on_current_tree() -> None:
    assert test_pairing.impl_start_signals(CTX) == []
    assert test_pairing.detect_impl_started(CTX) is False


def test_mutation_src_implementation_file_triggers_start_detection(tmp_path, monkeypatch) -> None:
    pkg = tmp_path / "helix"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "db.py").write_text("def connect() -> None:\n    ...\n", encoding="utf-8")
    monkeypatch.setattr(test_pairing, "SRC_PKG", pkg)
    signals = test_pairing.impl_start_signals(CTX)
    assert any(s.startswith("src-impl") for s in signals)


def test_mutation_plan_in_progress_triggers_start_detection(tmp_path, monkeypatch) -> None:
    plan = tmp_path / "plan-s0.1.json"
    plan.write_text('{"status": "in_progress", "targets": []}', encoding="utf-8")
    monkeypatch.setattr(test_pairing, "S0_PLAN", plan)
    assert "plan:in_progress" in test_pairing.impl_start_signals(CTX)


def test_ut_escape_detection_flags_skip_xfail_and_empty_assert(tmp_path) -> None:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    (tmp_path / fname).write_text(textwrap.dedent(f'''
        import pytest


        @pytest.mark.skip(reason="{du} 未実装")
        def {tname}() -> None:
            assert True
    '''), encoding="utf-8")
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any(f.endswith(":skip") for f in faults)
    assert any(f.endswith(":空 assert") for f in faults)


def test_ut_escape_detection_accepts_real_assertion(tmp_path) -> None:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    body = f"\ndef {tname}() -> None:\n    assert 1 + 1 == 2\n"
    others = {f for _, f, _ in test_pairing.s0_target_uts(CTX)}
    for f in others:
        (tmp_path / f).write_text("", encoding="utf-8")
    (tmp_path / fname).write_text(body, encoding="utf-8")
    faults = [f for f in test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
              if f.startswith(f"{du}:{fname}::{tname}")]
    assert faults == []


def test_mutation_notimplementederror_is_detected(tmp_path) -> None:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    (tmp_path / fname).write_text(
        f"\ndef {tname}() -> None:\n    raise NotImplementedError\n", encoding="utf-8")
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("NotImplementedError" in f for f in faults)


def test_coverage_floor_is_zero_before_start_and_eighty_after(monkeypatch) -> None:
    assert test_pairing.coverage_floor(CTX) == 0
    monkeypatch.setattr(test_pairing, "detect_impl_started", lambda ctx: True)
    assert test_pairing.coverage_floor(CTX) >= test_pairing.COVERAGE_STARTED_FLOOR


def test_s0_target_uts_cover_du_01_to_12() -> None:
    dus = {du for du, _, _ in test_pairing.s0_target_uts(CTX)}
    assert dus == {f"DU-{i:02d}" for i in range(1, test_pairing.S0_DU_MAX + 1)}


# --- 独立レビュー blocker 対応: 正規表現走査では素通りしていた逃げ道の mutation test ---

def _write_all_targets(tmp_path, body: str) -> None:
    """S0.1 対象 UT ファイルすべてを作り、先頭ファイルだけ body で置き換える。"""
    for _, fname, _ in test_pairing.s0_target_uts(CTX):
        (tmp_path / fname).write_text("", encoding="utf-8")
    _, first, _ = test_pairing.s0_target_uts(CTX)[0]
    (tmp_path / first).write_text(body, encoding="utf-8")


def test_mutation_module_level_skip_is_detected(tmp_path) -> None:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import pytest

        pytest.skip("{du} 未実装", allow_module_level=True)


        def {tname}() -> None:
            assert 1 + 1 == 2
    '''))
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("module-level skip" in f for f in faults)


def test_mutation_pytestmark_skip_is_detected(tmp_path) -> None:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import pytest

        pytestmark = pytest.mark.skip(reason="{du} 未実装")


        def {tname}() -> None:
            assert 1 + 1 == 2
    '''))
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("pytestmark skip" in f for f in faults)


def test_mutation_inline_xfail_call_is_detected(tmp_path) -> None:
    _, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import pytest


        def {tname}() -> None:
            pytest.xfail("未実装")
            assert 1 + 1 == 2
    '''))
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("xfail()" in f for f in faults)


def test_mutation_skipif_decorator_is_detected(tmp_path) -> None:
    _, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import pytest


        @pytest.mark.skipif(True, reason="未実装")
        def {tname}() -> None:
            assert 1 + 1 == 2
    '''))
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any(f.endswith(":skip") for f in faults)


def test_mutation_constant_assert_is_detected(tmp_path) -> None:
    _, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, f"\ndef {tname}() -> None:\n    assert 1\n")
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("空 assert" in f for f in faults)


def test_mutation_implementation_hidden_in_init_py_is_detected(tmp_path, monkeypatch) -> None:
    pkg = tmp_path / "helix"
    (pkg / "kernel").mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""docstring only."""\n', encoding="utf-8")
    (pkg / "kernel" / "__init__.py").write_text(
        "def start_run() -> None:\n    return None\n", encoding="utf-8")
    monkeypatch.setattr(test_pairing, "SRC_PKG", pkg)
    signals = test_pairing.impl_start_signals(CTX)
    assert any(s.startswith("src-impl") for s in signals), \
        "__init__.py に実装を隠した着手が検出されない"


def test_docstring_only_init_is_not_an_implementation(tmp_path) -> None:
    p = tmp_path / "__init__.py"
    p.write_text('"""re-export only."""\nfrom x import y  # noqa: F401\n', encoding="utf-8")
    assert test_pairing.has_implementation(p) is False


def test_mutation_conditional_def_and_lambda_are_implementations(tmp_path) -> None:
    """変異: `if` ブロック内の def や `f = lambda ...` で着手検出を迂回できてはならない。"""
    conditional = tmp_path / "conditional.py"
    conditional.write_text(
        "import os\n\nif os.name:\n    def connect() -> None:\n        return None\n",
        encoding="utf-8")
    assert test_pairing.has_implementation(conditional) is True
    lam = tmp_path / "lam.py"
    lam.write_text("transition = lambda a, b: a\n", encoding="utf-8")
    assert test_pairing.has_implementation(lam) is True


def test_mutation_bare_skip_from_pytest_import_is_detected(tmp_path) -> None:
    """変異: `from pytest import skip` 経由の裸呼出しでも skip 禁止を迂回できてはならない。"""
    _, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        from pytest import skip


        def {tname}() -> None:
            skip("未実装")
            assert 1 + 1 == 2
    '''))
    faults = test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
    assert any("skip()" in f for f in faults), "裸の skip() 呼出しが素通りしている"


# --- 偽陽性の回帰テスト: 正当なテストを違反扱いしない（独立レビュー major 対応） ---

def _first_target_faults(tmp_path) -> list[str]:
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    return [f for f in test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
            if f.startswith(f"{du}:{fname}::{tname}")]


def test_pytest_raises_only_rejection_test_is_not_a_violation(tmp_path) -> None:
    """`pytest.raises` だけの拒否テストは検証行為であり「空 assert」ではない。"""
    _, _, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import pytest


        def {tname}() -> None:
            with pytest.raises(ValueError):
                int("x")
    '''))
    assert _first_target_faults(tmp_path) == []


def test_mock_assertion_only_test_is_not_a_violation(tmp_path) -> None:
    """mock の表明（assert_called_once 等）も検証行為として認める。"""
    _, _, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        from unittest.mock import Mock


        def {tname}() -> None:
            m = Mock()
            m()
            m.assert_called_once()
    '''))
    assert _first_target_faults(tmp_path) == []


def test_non_pytest_decorator_named_skip_is_not_a_violation(tmp_path) -> None:
    """`@custom.skip` のような同名の自作 API を skip と誤検出しない（import 解決）。"""
    _, _, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import custom


        @custom.skip
        def {tname}() -> None:
            assert 1 + 1 == 2
    '''))
    assert _first_target_faults(tmp_path) == []


def test_module_level_sys_exit_is_not_a_module_skip(tmp_path) -> None:
    """`sys.exit()` を module-level skip と誤判定しない。"""
    _, _, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, textwrap.dedent(f'''
        import sys

        sys.exit


        def {tname}() -> None:
            assert 1 + 1 == 2
    '''))
    assert _first_target_faults(tmp_path) == []


def test_committed_coverage_floor_reports_its_source(monkeypatch) -> None:
    """比較元は baseline 経由に一本化され、解決できない場合は理由が返る（fail-close の入力）。"""
    value, source = test_pairing.committed_coverage_floor()
    assert isinstance(source, str) and source
    assert value is None or isinstance(value, int)
    monkeypatch.setattr(test_pairing, "committed_baseline",
                        lambda: (None, "親コミットに baseline が見つからない（旧パス含む）"))
    assert test_pairing.committed_coverage_floor() == (
        None, "親コミットに baseline が見つからない（旧パス含む）")


# --- 逃げ道の網羅表（第 3 次レビュー major 対応: 別名 import・再代入・getattr） ---

ESCAPE_MATRIX = [
    ("pytest.skip", True, "import pytest\n\ndef {t}():\n    pytest.skip('x')\n    assert 1 + 1 == 2\n"),
    ("from-import", True, "from pytest import skip\n\ndef {t}():\n    skip('x')\n    assert 1 + 1 == 2\n"),
    ("import-alias", True, "import pytest as p\n\ndef {t}():\n    p.skip('x')\n    assert 1 + 1 == 2\n"),
    ("symbol-alias", True,
     "from pytest import skip as s\n\ndef {t}():\n    s('x')\n    assert 1 + 1 == 2\n"),
    ("module-rebind", True,
     "import pytest\np = pytest\n\ndef {t}():\n    p.skip('x')\n    assert 1 + 1 == 2\n"),
    ("symbol-rebind", True,
     "from pytest import skip\ns = skip\n\ndef {t}():\n    s('x')\n    assert 1 + 1 == 2\n"),
    ("mark-rebind", True,
     "import pytest\nmark = pytest.mark\n\n@mark.skip\ndef {t}():\n    assert 1 + 1 == 2\n"),
    ("getattr", True,
     "import pytest\n\ndef {t}():\n    getattr(pytest, 'skip')('x')\n    assert 1 + 1 == 2\n"),
    ("nested-assert-only", True, "def {t}():\n    def inner():\n        assert 1 + 1 == 2\n"),
    ("unreachable-assert-only", True, "def {t}():\n    if False:\n        assert 1 + 1 == 2\n"),
    ("custom-skip-decorator", False,
     "import custom\n\n@custom.skip\ndef {t}():\n    assert 1 + 1 == 2\n"),
    ("module-level-sys-exit", False,
     "import sys\nsys.exit\n\ndef {t}():\n    assert 1 + 1 == 2\n"),
    ("unittest-assert-method", False, "def {t}(self=None):\n    (self or O()).assertEqual(1, 1)\n"),
    ("star-import", True, "from pytest import *\n\ndef {t}():\n    skip('x')\n    assert 1 + 1 == 2\n"),
    ("tuple-alias", True,
     "import pytest\ns, _ = pytest.skip, None\n\ndef {t}():\n    s('x')\n    assert 1 + 1 == 2\n"),
    ("annassign-alias", True,
     "import pytest\ns: object = pytest.skip\n\ndef {t}():\n    s('x')\n    assert 1 + 1 == 2\n"),
    ("walrus-alias", True,
     "import pytest\n\ndef {t}():\n    (s := pytest.skip)('x')\n    assert 1 + 1 == 2\n"),
    ("multi-hop-alias", True,
     "from pytest import skip as s\nu = s\n\ndef {t}():\n    u('x')\n    assert 1 + 1 == 2\n"),
    ("dead-while-false", True, "def {t}():\n    while False:\n        assert 1 + 1 == 2\n"),
    ("dead-after-return", True, "def {t}():\n    return\n    assert 1 + 1 == 2\n"),
    ("dead-after-raise", True, "def {t}():\n    raise SystemExit\n    assert 1 + 1 == 2\n"),
    ("live-try-except", False,
     "def {t}():\n    try:\n        assert 1 + 1 == 2\n    except Exception:\n        pass\n"),
    ("live-finally", False,
     "def {t}():\n    try:\n        pass\n    finally:\n        assert 1 + 1 == 2\n"),
    ("live-for-else", False,
     "def {t}():\n    for i in []:\n        pass\n    else:\n        assert 1 + 1 == 2\n"),
    ("live-while-dynamic", False,
     "def {t}():\n    while cond():\n        assert 1 + 1 == 2\n"),
    ("live-with", False, "def {t}():\n    with open('x') as f:\n        assert f\n"),
]


@pytest.mark.parametrize("label,should_flag,body", ESCAPE_MATRIX,
                         ids=[c[0] for c in ESCAPE_MATRIX])
def test_mutation_escape_matrix(tmp_path, label: str, should_flag: bool, body: str) -> None:
    """別名 import・モジュール再代入・getattr・到達不能コードまで含めた検出／非検出の網羅表。"""
    du, fname, tname = test_pairing.s0_target_uts(CTX)[0]
    _write_all_targets(tmp_path, body.format(t=tname))
    # 対象関数そのものの違反と module 単位の違反だけを見る
    # （同一ファイルに割り当てられた他の UT の「def 不在」は本テストの関心事ではない）
    faults = [f for f in test_pairing.detect_ut_escapes(CTX, tests_dir=tmp_path)
              if f.startswith(f"{du}:{fname}::{tname}:")
              or (f.startswith(f"{du}:{fname}:") and "::" not in f)]
    assert bool(faults) is should_flag, f"{label}: 期待={should_flag} 実際={faults}"


# --- 着手前提条件の機械化（REV-S0-STRUCT-01 第 5 次 minor 対応） ---

DESC = "pytest の outcome レポートで対象 UT が individually executed かつ passed であることを検査する実行時ゲートを追加する"


def _required_unmet() -> list[dict]:
    """PO 指定の S0.1 開始条件（4 件）を unmet で持つ最小の preconditions。"""
    return [{"id": pid, "status": "unmet", "description": DESC, "source": "…"}
            for pid in test_pairing.REQUIRED_PRECONDITIONS]


def _plan(tmp_path, **over) -> Path:
    data = {
        "plan_id": "PLAN-S0.1", "slice": "S0", "update": "S0.1", "status": "planned",
        "preconditions": _required_unmet(),
        "targets": [f"DU-{i:02d}" for i in range(1, test_pairing.S0_DU_MAX + 1)],
    }
    # 個別の変異は**必須 4 件に足す**形で与える（必須欠落の違反と混ざらないように）
    if "preconditions" in over and not over.pop("raw", False):
        over["preconditions"] = [*_required_unmet(), *over["preconditions"]]
    data.update(over)
    p = tmp_path / "plan-s0.1.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_plan_is_clean_on_the_real_tree() -> None:
    assert test_pairing.detect_plan_faults(started=False) == []


def test_mutation_starting_with_unmet_preconditions_is_detected(tmp_path) -> None:
    """変異: 前提条件が未充足のまま着手（自動検出）したら fail-close。"""
    faults = test_pairing.detect_plan_faults(started=True, plan_path=_plan(tmp_path))
    assert any("未充足の前提条件" in f for f in faults)


def test_mutation_flipping_status_to_in_progress_with_unmet_precondition_is_detected(
        tmp_path) -> None:
    """変異: 前提条件が未充足のまま status を in_progress にしたら fail-close。"""
    faults = test_pairing.detect_plan_faults(
        started=False, plan_path=_plan(tmp_path, status="in_progress"))
    assert any("未充足の前提条件" in f for f in faults)


def _patch_ledger(monkeypatch) -> None:
    """専用ゲートが**実装された後**の世界を模す（met を許す唯一の条件）。"""
    ids = test_pairing.ledger_gate_ids() | set(test_pairing.REQUIRED_PRECONDITIONS.values())
    monkeypatch.setattr(test_pairing, "ledger_gate_ids", lambda: ids)


def test_met_preconditions_allow_starting(tmp_path, monkeypatch) -> None:
    """4 件すべてを専用ゲートの実装で met にすれば着手できる（偽陽性回帰）。"""
    _patch_ledger(monkeypatch)
    plan = _plan(tmp_path, status="in_progress", raw=True,
                 preconditions=[{"id": pid, "status": "met", "description": DESC, "met_by": g}
                                for pid, g in test_pairing.REQUIRED_PRECONDITIONS.items()])
    assert test_pairing.detect_plan_faults(started=True, plan_path=plan) == []


def test_mutation_dropping_a_required_precondition_is_detected(tmp_path) -> None:
    """変異: PO 指定の開始条件を導入コミット内で消しても検出される（独立レビュー R1-02）。

    baseline ラチェットは**親コミット**との差分しか見ないため、初導入と同時に消す経路が残る。
    必須集合はコード側が持つ。
    """
    plan = _plan(tmp_path, raw=True,
                 preconditions=[p for p in _required_unmet()
                                if p["id"] != "per-ut-executed-and-passed"])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("開始条件が欠落" in f and "per-ut-executed-and-passed" in f for f in faults)


@pytest.mark.parametrize("bogus", ["G-UT-NO-ESCAPE", "G-BASE-HASH", "G-MANIFEST-DOMAIN"])
def test_mutation_unrelated_gate_cannot_meet_a_required_precondition(
        tmp_path, monkeypatch, bogus) -> None:
    """変異: 無関係な既存ゲート ID を貼って必須前提条件を met に偽装できない（R1-01）。"""
    _patch_ledger(monkeypatch)
    plan = _plan(tmp_path, raw=True,
                 preconditions=[{"id": "runtime-ut-outcome-gate", "status": "met",
                                 "description": DESC, "met_by": bogus},
                                *[p for p in _required_unmet()
                                  if p["id"] != "runtime-ut-outcome-gate"]])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("この前提条件専用の新設ゲート" in f for f in faults), bogus


def test_mutation_commit_sha_cannot_meet_a_required_precondition(tmp_path) -> None:
    """変異: 任意の実在 commit SHA では必須前提条件を met にできない（R1-01）。"""
    import subprocess
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True, cwd=test_pairing.ROOT).stdout.strip()
    plan = _plan(tmp_path, raw=True,
                 preconditions=[{"id": "dynamic-import-skip-detection", "status": "met",
                                 "description": DESC, "met_by": head},
                                *[p for p in _required_unmet()
                                  if p["id"] != "dynamic-import-skip-detection"]])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("この前提条件専用の新設ゲート" in f for f in faults)


def test_mutation_declaring_the_dedicated_gate_without_implementing_it_is_detected(
        tmp_path) -> None:
    """変異: 専用ゲート ID を書くだけ（本番が emit していない）では met にできない。"""
    plan = _plan(tmp_path, raw=True,
                 preconditions=[{"id": "runtime-ut-outcome-gate", "status": "met",
                                 "description": DESC, "met_by": "G-UT-RUNTIME-OUTCOME"},
                                *[p for p in _required_unmet()
                                  if p["id"] != "runtime-ut-outcome-gate"]])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("本番ゲートが emit していない" in f for f in faults)


def test_mutation_removing_preconditions_is_detected(tmp_path) -> None:
    """変異: preconditions ごと消して申し送りを散文へ戻すことを許さない。"""
    plan = _plan(tmp_path)
    data = json.loads(plan.read_text(encoding="utf-8"))
    del data["preconditions"]
    plan.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("preconditions が未定義" in f for f in faults)


# --- deferred だった fail-close 穴（PO 指示 §4-1〜4-4）の負例 ---

def test_mutation_non_dict_precondition_is_a_readable_violation(tmp_path) -> None:
    """変異: 前提条件を文字列に潰しても AttributeError で異常終了せず、違反として出る。"""
    plan = _plan(tmp_path, preconditions=["runtime-ut-outcome-gate"])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("object でない" in f for f in faults)


def test_mutation_stub_description_is_detected(tmp_path) -> None:
    """変異: description を一語に潰して前提条件を骨抜きにできない。"""
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "unmet", "description": "後で"}])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("description が" in f for f in faults)


def test_mutation_met_without_met_by_is_detected(tmp_path) -> None:
    """変異: 根拠なしに met へ書き換えて前提条件を消せない。"""
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "met", "description": DESC}])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("met_by" in f for f in faults)


@pytest.mark.parametrize("fake", ["G-DOES-NOT-EXIST", "G-BASE", "G-UNIQ", "G-UT-NO", "G-CNT"])
def test_mutation_met_by_unknown_gate_is_detected(tmp_path, fake) -> None:
    """変異: 実在しないゲート ID を met_by に書いて偽装できない。

    `G-BASE`／`G-UNIQ` は実在 ID の**接頭辞**・台帳の圧縮表記断片であり、部分文字列一致へ
    退行すると素通りする（独立レビュー F-05）。
    """
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "met", "description": DESC,
                                           "met_by": fake}])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("ゲート台帳に存在しない" in f for f in faults), fake


@pytest.mark.parametrize("real", ["G-BASE-HASH", "G-UT-NO-ESCAPE", "G-SLICE-PLACEMENT"])
def test_real_gate_ids_are_accepted_as_met_by(tmp_path, real) -> None:
    """実在ゲート ID は met_by として通る（偽陽性回帰）。"""
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "met", "description": DESC,
                                           "met_by": real}])
    assert test_pairing.detect_plan_faults(started=False, plan_path=plan) == [], real


def test_mutation_met_by_unknown_commit_is_detected(tmp_path) -> None:
    """変異: 実在しない commit SHA を met_by に書いて偽装できない。"""
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "met", "description": DESC,
                                           "met_by": "0" * 40}])
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("リポジトリに存在しない" in f for f in faults)


def test_met_by_real_commit_is_accepted(tmp_path) -> None:
    """実在 commit SHA による束縛は通る（偽陽性回帰）。"""
    import subprocess
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True, cwd=test_pairing.ROOT).stdout.strip()
    plan = _plan(tmp_path, preconditions=[{"id": "x", "status": "met", "description": DESC,
                                           "met_by": sha}])
    assert test_pairing.detect_plan_faults(started=False, plan_path=plan) == []


def test_mutation_planned_to_done_shortcut_is_detected(tmp_path) -> None:
    """変異: in_progress を飛ばして done へ直行しても前提条件検査は発火する。"""
    plan = _plan(tmp_path, status="done")
    faults = test_pairing.detect_plan_faults(started=False, plan_path=plan)
    assert any("未充足の前提条件" in f for f in faults)


def test_mutation_plan_done_triggers_start_detection(tmp_path, monkeypatch) -> None:
    """変異: status=done でも着手扱いにする（in_progress を飛ばした迂回を塞ぐ — R4-01）。"""
    plan = tmp_path / "plan-s0.1.json"
    plan.write_text('{"status": "done", "targets": []}', encoding="utf-8")
    monkeypatch.setattr(test_pairing, "S0_PLAN", plan)
    assert "plan:done" in test_pairing.impl_start_signals(CTX)


def test_mutation_done_without_implementation_is_detected(tmp_path) -> None:
    """変異: 実装ゼロのまま done を名乗って S0.1 完了を宣言できない（R4-01）。"""
    plan = _plan(tmp_path, status="done",
                 preconditions=[{"id": "x", "status": "met", "description": DESC,
                                 "met_by": "G-UT-NO-ESCAPE"}])
    faults = test_pairing.detect_plan_faults(started=True, plan_path=plan, ctx=CTX)
    assert any("API 未実装の対象がある" in f for f in faults)
