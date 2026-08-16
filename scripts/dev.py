#!/usr/bin/env python3
"""Python-native 開発環境の薄い入口。

HELIX-HARNESS の setup／doctor／docs／gates／test 導線を、uv・既存ゲート・pytestへ
写像する。ここには要件ゲート本体を書かず、tools/gates/run_all.pyを唯一の入口にする。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT = ROOT / "docs/00-authority/template/helix-harness-alignment.json"


def command(argv: list[str], *, check: bool = True) -> int:
    """リポジトリルートでコマンドを実行し、終了コードを返す。"""
    proc = subprocess.run(argv, cwd=ROOT, check=False)
    if check and proc.returncode:
        raise SystemExit(proc.returncode)
    return proc.returncode


def require_uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        print(
            "uv が見つかりません。https://docs.astral.sh/uv/ の手順で導入してから再実行してください。",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return uv


def check_python() -> None:
    if tuple(sys.version_info[:2]) < (3, 14):
        print(f"Python 3.14 以上が必要です: {sys.version.split()[0]}", file=sys.stderr)
        raise SystemExit(2)


def setup() -> int:
    check_python()
    uv = require_uv()
    return command([uv, "sync", "--frozen", "--group", "dev"])


def uv_python(*args: str) -> int:
    """同期済みの uv 環境で、リポジトリ内の Python ツールを実行する。"""
    return command([require_uv(), "run", "python", *args])


def docs(check: bool = False) -> int:
    args = ["scripts/render_views.py"]
    if check:
        args.append("--check")
    return uv_python(*args)


def gates() -> int:
    return uv_python("tools/gates/run_all.py")


def tests(scope: str | None = None) -> int:
    """pytest→JUnit→outcome→全ゲートを同じ uv 環境で実行する。"""
    uv = require_uv()
    args = [uv, "run", "pytest"]
    if scope is not None:
        args.append(scope)
    test_rc = command([*args, "--junitxml=reports/junit.xml"], check=False)
    outcome_rc = uv_python("scripts/collect_test_outcome.py")
    gate_rc = gates()
    return test_rc or outcome_rc or gate_rc


def lint() -> int:
    """Ruff による静的検査を実行する。"""
    uv = require_uv()
    return command([uv, "run", "ruff", "check", "."])


def typecheck() -> int:
    """プロジェクトで定義した mypy 対象を検査する。"""
    uv = require_uv()
    return command([uv, "run", "mypy"])


def imports() -> int:
    """import-linter による単方向依存の検査を実行する。"""
    uv = require_uv()
    return command([uv, "run", "lint-imports"])


def build() -> int:
    """pyproject.toml の hatchling 設定から配布物を生成する。"""
    uv = require_uv()
    return command([uv, "build"])


def requirements() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.gates.common import CTX
    from tools.gates.requirement_discovery import detect_discovery_faults, load_discovery_ledger
    from tools.gates.requirement_engine import actionable_engine_faults, engine_report
    from tools.gates.template_alignment import detect_alignment_faults

    data = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
    print(f"template: {data['source']['repository']} @ {data['source']['commit']}")
    print(f"runtime: {data['adoption']['runtime']}; scope: {data['adoption']['requirements_scope']}")
    for mapping in data["mappings"]:
        print(f"- {mapping['id']}: {mapping['status']}")
    faults = detect_alignment_faults(data)
    if faults:
        print(f"NG: template alignment ({faults[:4]})", file=sys.stderr)
        return 1
    ledger = load_discovery_ledger()
    print(
        "discovery: "
        f"{ledger['lifecycle_status']}; events: {len(ledger['events'])}; "
        f"coverage: {ledger['coverage_start_commit'][:12]}"
    )
    discovery_faults = detect_discovery_faults(ledger)
    if discovery_faults:
        print(f"NG: requirement discovery ({discovery_faults[:4]})", file=sys.stderr)
        return 1
    state, engine_faults = engine_report(CTX)
    policy = state["policy"]
    projection = state["projection"]
    refinements = state["refinements"].get("records", [])
    print(
        "requirement-engine: "
        f"baseline={policy.get('requirements_baseline_status')}; "
        f"implementation_authorized={policy.get('implementation_authorized')}; "
        f"IR={len(projection.get('records', []))}; refinements={len(refinements)}"
    )
    failed = actionable_engine_faults(state, engine_faults)
    quarantined_count = sum(
        bool(values) and name not in failed for name, values in engine_faults.items()
    )
    if quarantined_count:
        print(f"legacy quarantine: {quarantined_count} fault groups (stage audit PASS)")
    for name, faults in failed.items():
        print(f"NG: {name} ({len(faults)}件; {faults[:3]})", file=sys.stderr)
    if failed:
        print(
            "要件は未確定です。未解消の意味差分をrefinementで閉じ、PO承認後にのみ実装入力へ切り替えてください。",
            file=sys.stderr,
        )
        return 1
    print("requirement-engine: PASS (PO承認済みfrozen要求だけが実装入力です)")
    return 0


def doctor() -> int:
    check_python()
    require_uv()
    required = [
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        "src/helix",
        "docs/00-authority/artifact-manifest.json",
        "docs/00-authority/baselines/baseline.json",
        "docs/00-authority/template/helix-harness-alignment.json",
        "docs/00-authority/development/requirement-discovery-events.json",
        "docs/00-authority/development/requirement-discovery-event.schema.json",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        print(f"開発環境の必須パスがありません: {missing}", file=sys.stderr)
        return 1
    print(f"python: {sys.version.split()[0]}")
    print(f"uv: {shutil.which('uv')}")
    print("repository: HELIX-MARKETING-HARNESS")
    # requirements() is a diagnostic summary.  The authoritative exit decision
    # belongs to run_all; do not stop before it can classify every gate.
    requirements()
    docs(check=True)
    return gates()


def check() -> int:
    lint()
    typecheck()
    imports()
    docs(check=True)
    build()
    return tests()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "setup",
            "doctor",
            "requirements",
            "docs",
            "docs-check",
            "gates",
            "test",
            "test-gates",
            "lint",
            "typecheck",
            "imports",
            "build",
            "check",
        ],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    name = build_parser().parse_args(argv).command
    if name == "setup":
        return setup()
    if name == "doctor":
        return doctor()
    if name == "requirements":
        return requirements()
    if name == "docs":
        return docs()
    if name == "docs-check":
        return docs(check=True)
    if name == "gates":
        return gates()
    if name == "test":
        return tests()
    if name == "test-gates":
        return tests("tests/gates")
    if name == "lint":
        return lint()
    if name == "typecheck":
        return typecheck()
    if name == "imports":
        return imports()
    if name == "build":
        return build()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
