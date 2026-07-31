#!/usr/bin/env python3
"""JSON 内容正本 → Markdown 生成ビュー レンダラ。

全層再降下（2026-08-01 PO 指示 §9）: JSON を内容正本、Markdown を生成ビューへ段階移行する。
生成された MD は手編集禁止（ヘッダに GENERATED 宣言、G-REQ-CONTRACT 等が同期を fail-close 検査）。

使い方:
    python3 scripts/render_views.py            # 全ビューを再生成
    python3 scripts/render_views.py --check    # 生成結果と現ファイルの一致を検査（差分あり = exit 1）
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "docs" / "requirements"

GENERATED_HEADER = (
    "<!-- GENERATED FILE — 編集禁止。正本は {src}。再生成 = python3 scripts/render_views.py -->\n\n"
)


def render_br_contracts() -> tuple[Path, str]:
    src = REQ / "json" / "br" / "br-contracts.json"
    data = json.loads(src.read_text())
    out = []
    out.append(GENERATED_HEADER.format(src="docs/requirements/json/br/br-contracts.json"))
    out.append("# 業務要求 構造化契約（BR contracts）v" + data["version"] + "\n\n")
    out.append("> status: **draft（再降下中）**（2026-08-01 全層再降下 §2 — JSON 内容正本の生成ビュー）\n")
    out.append("> 位置づけ: [br-backbone_v0.1.md](br-backbone_v0.1.md) の全 BR を 12 観点の構造化契約へ展開した正本ビュー。\n")
    out.append("> 1 行要求文の禁止（G-REQ-CONTRACT が schema 適合・全 BR 被覆・12 要求群被覆・本ビュー同期を fail-close 検査）。\n\n")

    groups: dict[str, list] = {}
    for it in data["items"]:
        groups.setdefault(it["group"], []).append(it)

    for group, items in groups.items():
        out.append(f"## {group}\n\n")
        for it in items:
            out.append(f"### {it['id']} {it['title']}\n\n")
            out.append(f"- **目的**: {it['purpose']}\n")
            out.append(f"- **主体・利用者**: {it['actor']}\n")
            out.append(f"- **発生状況・トリガー**: {it['trigger']}\n")
            out.append(f"- **現在の問題**: {it['problem']}\n")
            out.append(f"- **期待する価値・成果**: {it['value']}\n")
            out.append(f"- **対象範囲**: {'／'.join(it['scope_in'])}\n")
            out.append(f"- **非対象範囲**: {'／'.join(it['scope_out'])}\n")
            out.append(f"- **制約**: {'／'.join(it['constraints'])}\n")
            out.append(f"- **禁止事項**: {'／'.join(it['prohibitions'])}\n")
            out.append(f"- **人間判断点**: {it['human_judgement']}\n")
            out.append(f"- **失敗時の影響**: {it['failure_impact']}\n")
            out.append(f"- **完了を証明する証跡**: {'／'.join(it['completion_evidence'])}\n")
            td = it["trace_down"]
            down = "、".join(
                部 for 部 in (
                    " ".join(td.get("req", [])),
                    " ".join(td.get("fr", [])),
                    " ".join(td.get("sr", [])),
                    " ".join(td.get("nfr", [])),
                ) if 部
            )
            out.append(f"- **上流 trace**: {'／'.join(it['trace_up'])}\n")
            out.append(f"- **下流 trace**: {down}\n")
            if it["mandated_groups"]:
                out.append(f"- **担当する独立要求群**: {'、'.join(it['mandated_groups'])}\n")
            out.append(f"- **充填経路**: {it['fill']}\n\n")
    return REQ / "br-contracts_v0.1.md", "".join(out)


RENDERERS = [render_br_contracts]


def main() -> int:
    check = "--check" in sys.argv
    dirty = []
    for fn in RENDERERS:
        path, content = fn()
        current = path.read_text() if path.exists() else None
        content = content.rstrip("\n") + "\n"
        if current != content:
            if check:
                dirty.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(content)
                print(f"rendered: {path.relative_to(ROOT)}")
        else:
            print(f"up-to-date: {path.relative_to(ROOT)}")
    if check and dirty:
        print(f"STALE VIEWS (re-run render_views.py): {dirty}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
