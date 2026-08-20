"""pre-git-gate.sh の例外分岐の負例テスト。

CLAUDE.md 鉄則5の例外（要求cutover系ゲートの PO未承認による意図した赤）が、
(1) validator クラッシュ、(2) 列挙ゲートの非PO原因、(3) baseline が revising 以外、
のどれでも fail-close に倒れることを固定する。
"""

import json
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts/hooks/pre-git-gate.sh"

COMMIT_INPUT = json.dumps({"tool_input": {"command": "git commit -m x"}})


def _setup(tmp_path: Path, validator_body: str, status: str | None) -> Path:
    """hook を隔離環境へ複製し、validator stub と authority 正本を差し込む。"""
    hooks = tmp_path / "scripts/hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre-git-gate.sh"
    shutil.copy(HOOK, hook)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    stub = tmp_path / "scripts/validate_requirements.py"
    stub.write_text(validator_body, encoding="utf-8")
    auth_dir = tmp_path / "docs/00-authority/development"
    auth_dir.mkdir(parents=True)
    if status is not None:
        (auth_dir / "requirement-engine-authority.json").write_text(
            json.dumps({"requirements_baseline_status": status}), encoding="utf-8"
        )
    return hook


def _run(hook: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(hook)], input=COMMIT_INPUT,
                          capture_output=True, text=True)


def test_mutation_validator_crash_is_blocked(tmp_path) -> None:
    """変異: validator が FAIL 出力なしで異常終了しても素通りさせない。"""
    hook = _setup(tmp_path, "import sys; sys.exit(1)\n", "revising")
    r = _run(hook)
    assert r.returncode == 2
    assert "異常終了" in r.stderr


def test_mutation_non_po_reason_on_listed_gate_is_blocked(tmp_path) -> None:
    """変異: 列挙ゲートIDでも PO未承認以外の原因（digest不整合等）は遮断する。"""
    body = (
        "import sys\n"
        "print('FAIL [G-REQ-OPEN-REFINEMENTS] 検査 (違反=[\\'schema digest不整合\\'])')\n"
        "sys.exit(1)\n"
    )
    hook = _setup(tmp_path, body, "revising")
    r = _run(hook)
    assert r.returncode == 2
    assert "意図した赤以外" in r.stderr


def test_mutation_non_revising_status_disables_exception(tmp_path) -> None:
    """変異: baseline が revising 以外（approved・欠落）なら PO未承認理由でも遮断する。"""
    body = (
        "import sys\n"
        "print('FAIL [G-REQ-LEGACY-MEANING-INVENTORY] 検査 (違反=[\\'旧BR意味分類候補がPO未承認 remaining=0\\'])')\n"
        "sys.exit(1)\n"
    )
    for status in ("approved", None):
        hook = _setup(tmp_path / (status or "missing"), body, status)
        r = _run(hook)
        assert r.returncode == 2, status
        assert "例外なし" in r.stderr


def test_intended_red_with_po_reason_passes_while_revising(tmp_path) -> None:
    """正例: revising 中の列挙ゲート×PO未承認理由だけの赤は commit を許可する。"""
    body = (
        "import sys\n"
        "print('FAIL [G-REQ-LEGACY-MEANING-INVENTORY] 検査 (違反=[\\'旧BR意味分類候補がPO未承認 remaining=0\\'])')\n"
        "print('FAIL [G-REQ-OPEN-REFINEMENTS] 検査 (違反=[\\'X: lifecycle=draft（frozenでない）\\', \\'X: PO approval receiptがない\\'])')\n"
        "sys.exit(1)\n"
    )
    hook = _setup(tmp_path, body, "revising")
    r = _run(hook)
    assert r.returncode == 0, r.stderr


def test_mutation_mixed_reasons_in_one_line_are_blocked(tmp_path) -> None:
    """変異: 同一FAIL行に許可理由と非許可理由が混在しても素通りさせない（item単位照合）。"""
    body = (
        "import sys\n"
        "print(\"FAIL [G-REQ-OPEN-REFINEMENTS] 検査 (違反=['X: PO approval receiptがない', 'schema digest不整合'])\")\n"
        "sys.exit(1)\n"
    )
    hook = _setup(tmp_path, body, "revising")
    r = _run(hook)
    assert r.returncode == 2
    assert "意図した赤以外" in r.stderr


def test_mutation_rc_zero_with_fail_lines_is_blocked(tmp_path) -> None:
    """変異: validator が exit 0 なのに FAIL 行を出す矛盾状態を素通りさせない。"""
    body = (
        "print('FAIL [G-REQ-REFINEMENT] schema破損')\n"
    )
    hook = _setup(tmp_path, body, "revising")
    r = _run(hook)
    assert r.returncode == 2
    assert "exit 0" in r.stderr


def test_mutation_partial_match_reason_is_blocked(tmp_path) -> None:
    """変異: 許可語彙を部分に含む複合文言（例: PO receiptがない又はdigest不一致）を許可しない。"""
    body = (
        "import sys\n"
        "print(\"FAIL [G-REQ-LEGACY-TC-MEANING-INVENTORY] 検査 (違反=['旧TC分類にPO receiptがない又は親AC digest不一致'])\")\n"
        "sys.exit(1)\n"
    )
    hook = _setup(tmp_path, body, "revising")
    r = _run(hook)
    assert r.returncode == 2
    assert "意図した赤以外" in r.stderr


def test_green_validator_passes(tmp_path) -> None:
    hook = _setup(tmp_path, "import sys; sys.exit(0)\n", "revising")
    assert _run(hook).returncode == 0
