#!/usr/bin/env python3
"""pytest skip 件数ラチェット（全層再降下 — green の誤読防止）。

tests/skip-budget.json の `max_skipped` を上限とし、実測 skipped がそれを超えたら fail-close。
上限は減らす方向にのみ更新する（スライス完了 = 該当 skip の解消とセットで budget を下げる）。
usage: pytest 実行後に `python3 scripts/check_skip_budget.py <skipped数>`、
または引数なしで pytest を自身で実行して判定。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "tests" / "skip-budget.json"


def measured_skipped() -> int:
    if len(sys.argv) > 1:
        return int(sys.argv[1])
    proc = subprocess.run(  # noqa: S603
        ["uv", "run", "pytest"],  # noqa: S607
        capture_output=True, text=True, check=False, cwd=ROOT,
    )
    m = re.search(r"(\d+) skipped", proc.stdout + proc.stderr)
    if m is None:
        # 集計行が取れない = 判定不能 → fail-close
        print("FAIL [SKIP-BUDGET] pytest 集計行を解析できない")
        sys.exit(1)
    return int(m.group(1))


def main() -> int:
    budget = json.loads(BUDGET.read_text())
    limit = budget["max_skipped"]
    # ラチェット: 上限は baseline に記録した値を超えて増やせない（減少方向のみ許可）
    # 比較対象は git HEAD にコミット済みの baseline（作業ツリーの同時改変では回避できない）
    proc = subprocess.run(  # noqa: S603
        ["git", "show", "HEAD:docs/governance/baseline.json"],  # noqa: S607
        capture_output=True, text=True, check=False, cwd=ROOT)
    recorded = json.loads(proc.stdout).get("max_skipped") if proc.returncode == 0 else None
    approvals = (ROOT / "docs/governance/approvals.md").read_text()
    approved = recorded is not None and f"skip-budget {recorded}→{limit}" in approvals
    if recorded is not None and limit > recorded and not approved:
        print(f"FAIL [SKIP-BUDGET] 上限を {recorded} → {limit} へ引き上げている（ラチェット違反）。"
              "スタブ増加は設計追加（du-contracts の UT 追補）と同一コミットで、"
              "PO 承認 receipt を添えて baseline を更新すること")
        return 1
    skipped = measured_skipped()
    if skipped > limit:
        print(f"FAIL [SKIP-BUDGET] skipped {skipped} > 上限 {limit} — "
              "スタブ追加は budget 更新（理由付き）と同一コミットで行うこと")
        return 1
    print(f"PASS [SKIP-BUDGET] skipped {skipped} <= 上限 {limit}（baseline 記録 {recorded}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
