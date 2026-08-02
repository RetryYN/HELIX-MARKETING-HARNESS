#!/usr/bin/env python3
"""pytest の junit xml を **ゲートが読める outcome レポート**へ正規化する（S0.1 着手前提条件 §1）。

AST 検査は「そのテストが実行されたか」を原理的に判定できない。動的 import で組み立てた
skip／xfail、条件付き skip、収集自体からの除外は、静的検査を素通りする。そのため
`pytest --junitxml` の実行結果を CI 成果物として取り込み、
`tools/gates/test_reality.py` の実行時ゲート（G-UT-RUNTIME-OUTCOME／G-UT-DYNAMIC-SKIP／
G-UT-PER-TEST-OUTCOME）の入力にする。

usage:
    pytest --junitxml=reports/junit.xml
    python3 scripts/collect_test_outcome.py            # → reports/test-outcome.json
    python3 scripts/collect_test_outcome.py --junit <path> --out <path>

レポートは **HEAD へ束縛**する（`commit`）。別コミットで作った古い成果物を貼り付けて
「対象 UT は passed だった」と主張できないようにするため、ゲート側が HEAD と照合する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JUNIT = ROOT / "reports/junit.xml"
DEFAULT_OUT = ROOT / "reports/test-outcome.json"
SCHEMA_ID = "helix.test-outcome/v1"

# junit の 1 testcase から導く outcome。xfail は skipped 要素の type で見分ける
OUTCOMES = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")


def head_commit() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def nodeid_of(case: ET.Element) -> str:
    """junit の testcase 属性から pytest の nodeid を復元する。

    `file` 属性（相対パス）を起点に、`classname` の残余をクラス階層として繋ぐ。
    `file` が無い（収集エラー等）場合は classname をドットからパスへ戻して代用する。
    """
    name = case.get("name", "")
    classname = case.get("classname", "")
    path = case.get("file")
    if not path:
        # 収集段階の skip／error は file を持たず、モジュールのドット表記だけが入る
        dotted = classname or name
        if not dotted:
            return name
        path = dotted.replace(".", "/") + ".py"
        return f"{path}::{name}" if classname and name else f"{path}::<module>"
    module = path[:-3].replace("/", ".") if path.endswith(".py") else path.replace("/", ".")
    rest = classname[len(module):].strip(".") if classname.startswith(module) else ""
    parts = [p for p in rest.split(".") if p]
    return "::".join([path, *parts, name])


def outcome_of(case: ET.Element) -> tuple[str, str]:
    """(outcome, reason) を返す。xfail／xpass は skipped 要素の type と message で判別する。"""
    for tag, value in (("failure", "failed"), ("error", "error")):
        el = case.find(tag)
        if el is not None:
            msg = (el.get("message") or "").strip()
            if value == "failed" and "XPASS" in msg.upper():
                return "xpassed", msg
            return value, msg
    el = case.find("skipped")
    if el is not None:
        typ = (el.get("type") or "").lower()
        msg = (el.get("message") or "").strip()
        return ("xfailed" if "xfail" in typ or "xfail" in msg.lower() else "skipped"), msg
    return "passed", ""


def collect(junit: Path) -> dict:
    # 入力は同一ジョブ内の pytest が直前に生成した junit xml（外部から取得しない）。
    # ゲート側（G-UT-RUNTIME-OUTCOME）が sha256 と HEAD 束縛で出所を再検査する。
    tree = ET.parse(junit)  # noqa: S314 — 自ジョブ生成の成果物のみを対象にする
    tests: list[dict] = []
    for case in tree.getroot().iter("testcase"):
        outcome, reason = outcome_of(case)
        tests.append({"nodeid": nodeid_of(case), "outcome": outcome, "reason": reason[:200]})
    totals = {k: sum(1 for t in tests if t["outcome"] == k) for k in OUTCOMES}
    totals["total"] = len(tests)
    return {
        "schema": SCHEMA_ID,
        "generated_by": "scripts/collect_test_outcome.py",
        "commit": head_commit(),
        "source": str(junit.relative_to(ROOT)) if junit.is_relative_to(ROOT) else str(junit),
        "source_digest": hashlib.sha256(junit.read_bytes()).hexdigest(),
        "totals": totals,
        "tests": sorted(tests, key=lambda t: (t["nodeid"], t["outcome"])),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", type=Path, default=DEFAULT_JUNIT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    if not args.junit.is_file():
        print(f"NG: junit xml がない: {args.junit}（pytest --junitxml=... を先に実行する）")
        return 1
    data = collect(args.junit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"test outcome: {args.out} ({data['totals']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
