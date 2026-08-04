#!/usr/bin/env python3
"""有効な coverage 下限を出力する（CI の --cov-fail-under に渡す）。

S0.1 未着手のあいだは宣言値（tests/coverage-floor.json の fail_under）、
着手が自動検出されたら 80% 以上へ自動的に引き上がる（PO 指示 §6）。

出力は GitHub Actions の step output 形式（`floor=...`）で、CI は
`python3 tools/coverage_floor.py >> "$GITHUB_OUTPUT"` として**直接実行**する
（`echo "$(...)"` を挟むと G-WORKSET-COVERAGE の配線検査が実行主体を特定できない）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.gates.common import CTX  # noqa: E402
from tools.gates.test_pairing import coverage_floor  # noqa: E402

if __name__ == "__main__":
    print(f"floor={coverage_floor(CTX)}")
