#!/usr/bin/env python3
"""要件整合ゲートの入口（fail-close）。

工程別モジュール（authority／requirements／traceability／architecture／detailed_design／
test_pairing／semantic_refs／review_binding／baseline）を順に実行し、1 件でも FAIL があれば exit 1。
ゲート一覧の正本は docs/00-authority/requirements-gates.md。

usage:
    python3 tools/gates/run_all.py                    # 全ゲート
    python3 tools/gates/run_all.py --update-baseline  # baseline を再生成（承認 receipt 必須）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):  # 直接実行時にリポジトリルートを import パスへ載せる
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.gates import (  # noqa: E402
    architecture,
    authority,
    baseline,
    detailed_design,
    requirement_discovery,
    requirements,
    review_binding,
    semantic_refs,
    template_alignment,
    test_pairing,
    test_reality,
    traceability,
    worksets,
)
from tools.gates.common import (  # noqa: E402
    APPROVALS,
    BASELINE,
    CTX,
    SKIP_BUDGET,
    doc_body_digest,
    failures,
    live_markdown,
    load,
    rel,
)

MODULES = [
    authority,
    requirements,
    requirement_discovery,
    architecture,
    detailed_design,
    traceability,
    semantic_refs,
    test_pairing,
    test_reality,
    worksets,
    review_binding,
    template_alignment,
    baseline,
]


def _receipt_index() -> dict[tuple, set]:
    idx: dict[tuple, set] = {}
    for row in APPROVALS.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 8 and re.match(r"\d{4}-\d{2}-\d{2}", cells[1]):
            if cells[4] == "confirmed" and re.fullmatch(r"[0-9a-f]{12}", cells[6]):
                idx.setdefault((cells[2], cells[3]), set()).add(cells[6])
    return idx


def update_baseline() -> int:
    idx = _receipt_index()
    no_receipt = []
    for p in live_markdown():
        if not re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", p.read_text(encoding="utf-8")[:600]):
            continue
        base = re.sub(r"_v[\d.]+$", "", p.stem)
        m = re.search(r"_v([\d.]+)$", p.stem)
        ver = f"v{m.group(1)}" if m else "-"
        if doc_body_digest(p) not in idx.get((base, ver), set()):
            no_receipt.append(rel(p))
    if no_receipt:
        print(f"REFUSED: 承認 receipt（digest 行）のない confirmed 文書があるため baseline を更新しない: {no_receipt}")
        return 1
    prev = baseline.committed_max_skipped()
    cur = load(SKIP_BUDGET)["max_skipped"]
    if prev is not None and cur > prev and not baseline.skip_raise_approved(prev, cur):
        print(f"REFUSED: skip 上限の引き上げ（{prev}→{cur}）には approvals.md の構造化 PO 承認行が必要")
        return 1
    data = baseline.build_baseline(CTX)
    BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"baseline updated: docs={len(data['confirmed_docs'])}, "
          f"artifacts={len(data['artifacts'])}, gates={data['gate_count']}, counts={data['counts']}")
    return 0


def main(argv: list[str]) -> int:
    if "--update-baseline" in argv:
        return update_baseline()
    for mod in MODULES:
        mod.run(CTX)
    print()
    bad = failures()
    if bad:
        print(f"NG: {len(bad)} 件のゲート違反")
        return 1
    print("OK: 全ゲート PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
