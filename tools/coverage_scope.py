#!/usr/bin/env python3
"""coverage の測定対象を出力する（CI の pytest へ `--cov=...` として渡す）。

coverage 80% は将来分を含む `helix` 全体ではなく、**着手済み（in_progress＋done）の
原子単位が持つモジュール集合**へ適用する（PO 指示 §4・§5）。未着手の空モジュールを
分母に入れると、着手済みをいくら green にしても下限に届かないためである。

対象は原子単位から解決し、原子単位正本が使えない場合はレーン（Workset）側の解決へ、
それも空なら `--cov=helix` へ倒す（範囲を**狭める**方向の fail-open を作らない）。

出力は GitHub Actions の step output 形式（`args=...`）で、CI は
`python3 tools/coverage_scope.py >> "$GITHUB_OUTPUT"` として**直接実行**する。
`echo "$(...)"` を挟まないのは、G-WORKSET-COVERAGE の配線検査が
「実行主体としてこのスクリプトが呼ばれていること」を argv 構造で確かめるためである。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.gates.atomic_units import enforced_modules as atomic_modules  # noqa: E402
from tools.gates.common import CTX  # noqa: E402
from tools.gates.worksets import enforced_modules  # noqa: E402


def dotted(module_path: str) -> str:
    """`src/helix/db/connect.py` → `helix.db.connect`。"""
    return module_path.removeprefix("src/").removesuffix(".py").replace("/", ".")


if __name__ == "__main__":
    mods = atomic_modules(CTX)
    if mods is None:            # 原子単位正本が使えない → レーン側の解決へ倒す
        mods = enforced_modules(CTX)
    args = " ".join(f"--cov={dotted(m)}" for m in mods) if mods else "--cov=helix"
    print(f"args={args}")
