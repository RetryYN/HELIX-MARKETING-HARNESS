"""run_all（ゲート入口）の単体テストと mutation test。"""

import subprocess
import sys

from tools.gates import common, run_all
from tools.gates.common import ROOT


def test_all_modules_are_registered_in_execution_order() -> None:
    names = [m.__name__.rsplit(".", 1)[-1] for m in run_all.MODULES]
    assert names == ["authority", "requirements", "architecture", "detailed_design",
                     "traceability", "semantic_refs", "test_pairing", "test_reality",
                     "review_binding", "baseline"]
    for m in run_all.MODULES:
        assert callable(m.run)


def test_registry_collects_failures_and_resets() -> None:
    common.reset()
    common.gate("G-TEST-OK", True, "ok")
    common.gate("G-TEST-NG", False, "ng")
    assert common.failures() == ["G-TEST-NG: ng"]
    common.reset()
    assert common.failures() == []


def test_mutation_a_failing_gate_makes_the_entry_point_nonzero() -> None:
    """変異: いずれかのゲートが FAIL を登録したら exit code は非ゼロでなければならない。"""
    common.reset()
    common.gate("G-TEST-MUTATION", False, "injected failure")
    assert common.failures(), "FAIL を登録してもレジストリが空"
    common.reset()


HEADER = "| 日付 | 対象 | 版 | 判断 | 承認者 | digest | 備考 |\n|---|---|---|---|---|---|---|\n"


def test_receipt_index_collects_confirmed_rows_with_digests(tmp_path, monkeypatch) -> None:
    doc = tmp_path / "approvals.md"
    doc.write_text(
        HEADER + "| 2026-08-01 | some-doc | v0.1 | confirmed | PO | 0123456789ab | ok |\n",
        encoding="utf-8")
    monkeypatch.setattr(run_all, "APPROVALS", doc)
    assert run_all._receipt_index() == {("some-doc", "v0.1"): {"0123456789ab"}}


def test_mutation_receipt_without_a_valid_digest_is_not_indexed(tmp_path, monkeypatch) -> None:
    """変異: digest 欄が空／不正な confirmed 行を receipt として数えてはならない。

    数えてしまうと `--update-baseline` が未承認の confirmed 文書を素通しする。
    """
    doc = tmp_path / "approvals.md"
    doc.write_text(
        HEADER
        + "| 2026-08-01 | no-digest | v0.1 | confirmed | PO | — | 承認 digest なし |\n"
        + "| 2026-08-01 | short | v0.1 | confirmed | PO | abc | 桁不足 |\n"
        + "| 2026-08-01 | draft-doc | v0.1 | draft | PO | 0123456789ab | confirmed ではない |\n",
        encoding="utf-8")
    monkeypatch.setattr(run_all, "APPROVALS", doc)
    assert run_all._receipt_index() == {}


def test_wrapper_and_entry_point_agree() -> None:
    for cmd in (["tools/gates/run_all.py"], ["scripts/validate_requirements.py"]):
        proc = subprocess.run([sys.executable, *cmd], capture_output=True, text=True,
                              check=False, cwd=ROOT)
        assert "OK: 全ゲート PASS" in proc.stdout or "NG:" in proc.stdout
        assert proc.returncode in (0, 1)
