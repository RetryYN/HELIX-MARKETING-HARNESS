#!/usr/bin/env python3
"""要件整合ゲートの互換ラッパー（実体は tools/gates/）。

分割後の入口は tools/gates/run_all.py。既存の呼出し（CI・hook・手順書）を壊さないため
本ファイルは薄いラッパーとして残す。ゲート本体をここへ書き足さないこと。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.gates.run_all import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
