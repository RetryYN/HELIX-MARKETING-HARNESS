"""baseline ゲートの単体テストと mutation test。"""

import re

import pytest

from tools.gates import baseline
from tools.gates.common import BASELINE, GATE_MODULES, GATE_PKG, HISTORICAL_COUNTS, ROOT, load


def test_all_gate_modules_exist() -> None:
    missing = [m for m in GATE_MODULES if not (GATE_PKG / f"{m}.py").exists()]
    assert missing == []


def test_validator_is_a_thin_wrapper() -> None:
    text = (ROOT / "scripts/validate_requirements.py").read_text(encoding="utf-8")
    assert "run_all" in text
    assert text.count("\n") <= 40
    assert 'gate("G-' not in text, "互換ラッパーにゲート本体が書かれている"


def test_gate_ids_are_all_listed_in_the_ledger() -> None:
    ledger = (ROOT / "docs/00-authority/requirements-gates.md").read_text(encoding="utf-8")
    ledger_ids: set[str] = set()
    for m in re.findall(r"G-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:/[A-Z0-9]+)*", ledger):
        parts = m.split("/")
        ledger_ids.add(parts[0])
        prefix = parts[0].rsplit("-", 1)[0]
        ledger_ids.update(f"{prefix}-{s}" for s in parts[1:])
    unwired = sorted(g for g in baseline.script_gate_ids()
                     if not (g in ledger_ids or g.rstrip("-") in ledger_ids
                             or (g.endswith("-") and any(x.startswith(g) for x in ledger_ids))))
    assert unwired == []


def test_gate_count_is_not_below_recorded_baseline() -> None:
    assert baseline.gate_count() >= load(BASELINE)["gate_count"]


def test_historical_counts_are_kept_out_of_live_denominators() -> None:
    base = load(BASELINE)
    assert base["historical_counts"] == HISTORICAL_COUNTS
    assert not set(base["counts"]) & {"AC", "UTC"}


PREV = {
    "counts": {"BR": 38, "REQ": 52, "AC": 19},
    "contract_counts": {"AC_CONTRACT": 211, "TCC": 217},
    "gate_count": 118,
    "max_skipped": 194,
}
CUR_COUNTS = {"BR": 38, "REQ": 52}
CUR_CC = {"AC_CONTRACT": 211, "TCC": 217}


def test_ratchet_passes_when_nothing_regresses() -> None:
    assert baseline.detect_ratchet_faults(PREV, CUR_COUNTS, CUR_CC, 118, 194, False) == []


def test_mutation_shrinking_a_denominator_is_detected() -> None:
    faults = baseline.detect_ratchet_faults(
        PREV, {**CUR_COUNTS, "BR": 37}, CUR_CC, 118, 194, False)
    assert any("分母縮小:BR" in f for f in faults)


def test_mutation_dropping_a_denominator_key_is_detected() -> None:
    faults = baseline.detect_ratchet_faults(
        PREV, {"BR": 38}, CUR_CC, 118, 194, False)
    assert any("分母キー消失:REQ" in f for f in faults)


def test_retired_keys_are_allowed_to_disappear() -> None:
    """AC/UTC は historical_counts へ退避済み — 消失は許可（それ以外は許可しない）。"""
    assert not any("AC" == f.split(":")[-1] for f in
                   baseline.detect_ratchet_faults(PREV, CUR_COUNTS, CUR_CC, 118, 194, False))


def test_mutation_gate_removal_is_detected() -> None:
    faults = baseline.detect_ratchet_faults(PREV, CUR_COUNTS, CUR_CC, 117, 194, False)
    assert any("ゲート削減" in f for f in faults)


def test_mutation_unapproved_skip_raise_is_detected() -> None:
    faults = baseline.detect_ratchet_faults(PREV, CUR_COUNTS, CUR_CC, 118, 200, False)
    assert any("skip 上限の未承認引き上げ" in f for f in faults)
    assert baseline.detect_ratchet_faults(PREV, CUR_COUNTS, CUR_CC, 118, 200, True) == []


def test_mutation_contract_denominator_shrink_is_detected() -> None:
    faults = baseline.detect_ratchet_faults(
        PREV, CUR_COUNTS, {**CUR_CC, "TCC": 216}, 118, 194, False)
    assert any("契約分母縮小:TCC" in f for f in faults)


def test_committed_baseline_resolves_previous_path() -> None:
    """物理移行で baseline が移動しても親コミットから解決できる（解決不能は fail-close）。"""
    prev, source = baseline.committed_baseline()
    assert prev is not None, f"親コミットの baseline を解決できない: {source}"
    assert "baseline.json" in source


# --- メタゲート（G-GATE-UNITTEST）自体の検出能力 ---

def _fake_gate_tests(tmp_path, monkeypatch, body: str) -> tuple[list[str], list[str], list[str]]:
    """全ゲートモジュール分の疑似テストファイルを body で生成し、検出結果を返す。

    生成物は `detect_gate_test_faults` が **AST 解析するだけ**で実行はしない
    （メタゲートの判定基準そのものを検査する）。
    """
    for m in GATE_MODULES:
        (tmp_path / f"test_{m}.py").write_text(body.format(mod=m), encoding="utf-8")
    monkeypatch.setattr(baseline, "TEST_DIR", tmp_path)
    return baseline.detect_gate_test_faults()


REAL_MUTATION = (
    "from tools.gates import {mod}\n\n\n"
    "def test_mutation_injected() -> None:\n"
    "    assert {mod}.detect_faults(MUTATED) != []\n"
)


def test_real_mutation_tests_satisfy_the_meta_gate(tmp_path, monkeypatch) -> None:
    assert _fake_gate_tests(tmp_path, monkeypatch, REAL_MUTATION) == ([], [], [])


def test_mutation_hollow_mutation_test_does_not_satisfy_the_meta_gate(tmp_path, monkeypatch) -> None:
    """変異: `def test_mutation_x(): pass` ＋無関係な属性参照では充足させない。"""
    hollow = (
        "from tools.gates import {mod}\n\n\n"
        "def test_something() -> None:\n"
        "    assert {mod}.__name__\n\n\n"
        "def test_mutation_placeholder() -> None:\n"
        "    pass\n"
    )
    no_test, no_mut, no_link = _fake_gate_tests(tmp_path, monkeypatch, hollow)
    assert no_test == []
    assert sorted(no_mut) == sorted(GATE_MODULES), "形骸の mutation 関数を素通りさせている"


def test_mutation_comment_only_mutation_marker_is_detected(tmp_path, monkeypatch) -> None:
    """変異: `# mutation` コメントだけでは mutation test とみなさない。"""
    comment = (
        "from tools.gates import {mod}\n\n\n"
        "# mutation test はここに書く予定\n"
        "def test_smoke() -> None:\n"
        "    assert {mod}.__name__\n"
    )
    _, no_mut, _ = _fake_gate_tests(tmp_path, monkeypatch, comment)
    assert sorted(no_mut) == sorted(GATE_MODULES)


def test_mutation_missing_import_is_reported_as_unlinked(tmp_path, monkeypatch) -> None:
    """変異: 本番モジュールを import せず呼ばないテストは『本番未参照』として落ちる。"""
    detached = (
        "def test_mutation_injected() -> None:\n"
        "    assert 1 + 1 == 2  # {mod} に触れていない\n"
    )
    _, no_mut, no_link = _fake_gate_tests(tmp_path, monkeypatch, detached)
    assert sorted(no_link) == sorted(GATE_MODULES)
    assert sorted(no_mut) == sorted(GATE_MODULES)


def test_mutation_missing_test_file_is_detected(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(baseline, "TEST_DIR", tmp_path)
    no_test, _, _ = baseline.detect_gate_test_faults()
    assert sorted(no_test) == sorted(GATE_MODULES)


def test_real_gate_tests_pass_the_meta_gate() -> None:
    assert baseline.detect_gate_test_faults() == ([], [], [])


def test_artifact_hashes_cover_gate_modules_and_manifest() -> None:
    arts = baseline.artifact_hashes()
    assert "docs/00-authority/artifact-manifest.json" in arts
    for m in GATE_MODULES:
        assert f"tools/gates/{m}.py" in arts
    assert not any(a.startswith("docs/archive/") for a in arts)


HOLLOW_FORMS = [
    ("結果を捨てる",
     "from tools.gates import {mod}\n\n\n"
     "def test_mutation_x() -> None:\n"
     "    {mod}.detect_faults(MUTATED)\n"
     "    assert 1 == 1\n"),
    ("無関係な変数を assert",
     "from tools.gates import {mod}\n\n\n"
     "def test_mutation_x() -> None:\n"
     "    {mod}.detect_faults(MUTATED)\n"
     "    other = compute()\n"
     "    assert other == 3\n"),
    ("入れ子関数の中",
     "from tools.gates import {mod}\n\n\n"
     "def test_mutation_x() -> None:\n"
     "    def inner():\n"
     "        assert {mod}.detect_faults(MUTATED) != []\n"),
    ("if False: 配下",
     "from tools.gates import {mod}\n\n\n"
     "def test_mutation_x() -> None:\n"
     "    if False:\n"
     "        assert {mod}.detect_faults(MUTATED) != []\n"),
]


@pytest.mark.parametrize("label,body", HOLLOW_FORMS, ids=[f[0] for f in HOLLOW_FORMS])
def test_mutation_hollow_forms_do_not_satisfy_the_meta_gate(
        tmp_path, monkeypatch, label: str, body: str) -> None:
    """変異: 本番を呼んでも結果を観測しない／到達しない mutation test は充足させない。"""
    _, no_mut, _ = _fake_gate_tests(tmp_path, monkeypatch, body)
    assert sorted(no_mut) == sorted(GATE_MODULES), f"{label} が素通りしている"


def test_mutation_binding_the_call_result_satisfies_the_meta_gate(tmp_path, monkeypatch) -> None:
    """呼出し結果を変数へ束縛して assert する形は正しく充足する（偽陽性回帰）。"""
    bound = (
        "from tools.gates import {mod}\n\n\n"
        "def test_mutation_x() -> None:\n"
        "    faults = {mod}.detect_faults(MUTATED)\n"
        "    assert faults != []\n"
    )
    assert _fake_gate_tests(tmp_path, monkeypatch, bound) == ([], [], [])


def test_audit_records_are_hash_bound_in_the_baseline() -> None:
    """監査記録は append-only を掲げる以上、baseline のハッシュ束縛対象でなければならない。"""
    arts = baseline.artifact_hashes()
    audits = [a for a in arts if a.startswith("docs/00-authority/audits/")]
    assert audits, "監査記録が baseline の artifact 束縛から漏れている"


def test_mutation_tuple_disguise_does_not_satisfy_the_meta_gate(tmp_path, monkeypatch) -> None:
    """変異: `observed, junk = (0, mod.f())` + `assert observed` はタプル位置対応で落とす。"""
    disguise = (
        "from tools.gates import {mod}\n\n\n"
        "def test_mutation_x() -> None:\n"
        "    observed, junk = (0, {mod}.detect_faults(MUTATED))\n"
        "    assert observed == 0\n"
    )
    _, no_mut, _ = _fake_gate_tests(tmp_path, monkeypatch, disguise)
    assert sorted(no_mut) == sorted(GATE_MODULES), "タプルの無関係要素で観測束縛を偽装できている"


def test_name_propagation_is_not_a_false_positive(tmp_path, monkeypatch) -> None:
    """`x = mod.f(); y = x; assert y` は正当な観測 — 偽陽性で落としてはならない。"""
    propagated = (
        "from tools.gates import {mod}\n\n\n"
        "def test_mutation_x() -> None:\n"
        "    x = {mod}.detect_faults(MUTATED)\n"
        "    y = x\n"
        "    assert y != []\n"
    )
    assert _fake_gate_tests(tmp_path, monkeypatch, propagated) == ([], [], [])


def test_positional_tuple_binding_is_accepted(tmp_path, monkeypatch) -> None:
    """`a, b = mod.f(), 1` の `a` は本番結果に束縛される（位置対応の正例）。"""
    positional = (
        "from tools.gates import {mod}\n\n\n"
        "def test_mutation_x() -> None:\n"
        "    a, b = {mod}.detect_faults(MUTATED), 1\n"
        "    assert a != b\n"
    )
    assert _fake_gate_tests(tmp_path, monkeypatch, positional) == ([], [], [])
