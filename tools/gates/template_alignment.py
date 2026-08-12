"""HELIX-HARNESS 設計テンプレート適応の fail-close ゲート。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.gates.common import ROOT, Ctx, gate, load, schema_check

ALIGNMENT = ROOT / "docs/00-authority/template/helix-harness-alignment.json"
SCHEMA = ROOT / "docs/00-authority/template/helix-harness-alignment.schema.json"
REQUIRED_MAPPINGS = {
    "v-model",
    "requirement-ir",
    "discovery-lifecycle",
    "l2-screen-template",
    "developer-loop",
    "hooks-and-authority",
}
REQUIRED_L2_PATHS = {
    "docs/L2-prototypes/screens/ui-screen-list_v0.1.md",
    "docs/L2-prototypes/screens/screen-flow_v0.1.md",
    "docs/L2-prototypes/screens/ui-element_v0.1.md",
    "docs/L2-prototypes/screens/wireframe_v0.1.md",
    "docs/L2-prototypes/screens/screen-detail_v0.1.md",
}
REQUIRED_CURRENT_PATHS = {
    "Makefile",
    "scripts/dev.py",
    "scripts/collect_test_outcome.py",
    "pyproject.toml",
    "uv.lock",
    "tools/gates/run_all.py",
}
TEMPLATE_SOURCE_COMMIT = "57853db413e282b050ac5f37bab7809321c67842"


def detect_alignment_faults(data: Any, root: Path = ROOT) -> list[str]:
    """対応表の schema、固定 source、現行パス、採用範囲を検査する。"""
    if not isinstance(data, dict):
        return ["対応表が object でない"]
    if not SCHEMA.exists():
        return [f"schema 不在: {SCHEMA}"]
    faults = schema_check(load(SCHEMA), data)
    if faults:
        return faults

    source = data["source"]
    if source["repository"] != "RetryYN/HELIX-HARNESS":
        faults.append("source.repository が RetryYN/HELIX-HARNESS でない")
    if not re.fullmatch(r"[0-9a-f]{40}", source["commit"]):
        faults.append("source.commit が 40 桁 SHA-1 でない")
    elif source["commit"] != TEMPLATE_SOURCE_COMMIT:
        faults.append("source.commit が固定監査対象と一致しない")
    if not source["url"].rstrip("/").endswith("github.com/RetryYN/HELIX-HARNESS"):
        faults.append("source.url が RetryYN/HELIX-HARNESS を指していない")
    if source["read_only"] is not True:
        faults.append("source.read_only が true でない")

    adoption = data["adoption"]
    if adoption["runtime"] != "python-native":
        faults.append("runtime が python-native でない")
    if adoption["bun_active_dependency"] is not False:
        faults.append("bun_active_dependency が false でない")
    if adoption["product_runtime_dependency"] != "none":
        faults.append("product_runtime_dependency が none でない")

    mappings = data["mappings"]
    ids = [m["id"] for m in mappings]
    missing = sorted(REQUIRED_MAPPINGS - set(ids))
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if missing:
        faults.append(f"必須 mapping 欠落: {missing}")
    if duplicates:
        faults.append(f"mapping ID 重複: {duplicates}")

    declared_paths: set[str] = set()
    for mapping in mappings:
        for path in mapping["current_paths"]:
            declared_paths.add(path)
            if not (root / path).exists():
                faults.append(f"mapping {mapping['id']}: current path 不在 {path}")
    if not REQUIRED_CURRENT_PATHS <= declared_paths:
        faults.append(f"開発環境 path の対応表欠落: {sorted(REQUIRED_CURRENT_PATHS - declared_paths)}")

    l2 = next((m for m in mappings if m["id"] == "l2-screen-template"), None)
    if l2 is None or not REQUIRED_L2_PATHS <= set(l2["current_paths"]):
        faults.append("L2 5 点セットの current_paths が不完全")

    required_checks = set(data["required_checks"])
    for check in (
        "python3 tools/gates/run_all.py",
        "make doctor",
        "make lint",
        "make typecheck",
        "make build",
        "make test",
        "make check",
    ):
        if check not in required_checks:
            faults.append(f"required_checks 欠落: {check}")
    return sorted(set(faults))


def run(ctx: Ctx) -> None:
    del ctx
    try:
        data = load(ALIGNMENT)
        faults = detect_alignment_faults(data)
    except (OSError, ValueError, KeyError) as exc:
        faults = [f"対応表を読み込めない: {exc}"]
    gate(
        "G-TEMPLATE-ALIGNMENT",
        not faults,
        "HELIX-HARNESS 固定コミットの read-only 対応表、Python-native 開発環境、L2 5 点セットが整合 "
        f"(違反={faults[:4]})",
    )
