"""HELIX-HARNESS 設計テンプレート適応の fail-close ゲート。"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

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
    "ci-hygiene",
    "nfr-quality-registry",
    "schema-ddl-authority",
    "atomic-change-scope",
    "developer-cross-review",
    "developer-pr-notification",
    "developer-harness-memory",
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
    ".python-version",
    ".github/workflows/docs-ci.yml",
    ".github/workflows/python-ci.yml",
    "scripts/dev.py",
    "scripts/collect_test_outcome.py",
    "pyproject.toml",
    "uv.lock",
    "tools/gates/run_all.py",
}
REQUIRED_DISCOVERY_PATHS = {
    "docs/00-authority/development/requirement-discovery-events.json",
    "docs/00-authority/development/requirement-discovery-event.schema.json",
    "tools/gates/requirement_discovery.py",
    "tests/gates/test_requirement_discovery.py",
}
TEMPLATE_SOURCE_COMMIT = "57853db413e282b050ac5f37bab7809321c67842"
TEMPLATE_LATEST_CHECKED_COMMIT = "e0073d01be1a0a4ce709a983ffde4ab1485dcb4e"
TEMPLATE_LATEST_CHECKED_AT = "2026-08-19"
PYTHON_VERSION = "3.14"
WORKFLOWS = (
    ".github/workflows/docs-ci.yml",
    ".github/workflows/python-ci.yml",
)


def _workflow_hygiene_faults(path: str, text: str) -> list[str]:
    """workflow の全 job／checkout に bounded・credential 非保持を要求する。"""
    faults: list[str] = []
    try:
        workflow = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}: workflow YAML を読めない: {exc}"]
    if not isinstance(workflow, dict):
        return [f"{path}: workflow root が object でない"]
    concurrency = workflow.get("concurrency")
    if not isinstance(concurrency, dict):
        faults.append(f"{path}: concurrency cancel 契約がない")
    else:
        if concurrency.get("cancel-in-progress") is not True:
            faults.append(f"{path}: cancel-in-progress が true でない")
        if "github.workflow" not in str(concurrency.get("group", "")):
            faults.append(f"{path}: concurrency group が workflow に束縛されていない")
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        return faults + [f"{path}: jobs が空またはobjectでない"]
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            faults.append(f"{path}: job {job_name} がobjectでない")
            continue
        timeout = job.get("timeout-minutes")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            faults.append(f"{path}: job {job_name} に正のtimeout-minutesがない")
        steps = job.get("steps")
        if not isinstance(steps, list):
            faults.append(f"{path}: job {job_name} のstepsが配列でない")
            continue
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or not str(step.get("uses", "")).startswith(
                "actions/checkout@"
            ):
                continue
            options = step.get("with")
            if not isinstance(options, dict) or options.get("persist-credentials") is not False:
                faults.append(
                    f"{path}: job {job_name} checkout[{index}] が "
                    "persist-credentials: false でない"
                )
    return faults


def detect_toolchain_faults(root: Path = ROOT) -> list[str]:
    """Python pin と CI の frozen／bounded 実行契約を検査する。"""
    faults: list[str] = []
    try:
        python_pin = (root / ".python-version").read_text(encoding="utf-8").strip()
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"toolchain pin を読めない: {exc}"]

    requires_python = pyproject.get("project", {}).get("requires-python")
    mypy_python = pyproject.get("tool", {}).get("mypy", {}).get("python_version")
    ruff_target = pyproject.get("tool", {}).get("ruff", {}).get("target-version")
    if python_pin != PYTHON_VERSION:
        faults.append(f".python-version が {PYTHON_VERSION} でない")
    if requires_python != f">={PYTHON_VERSION}":
        faults.append(f"requires-python が >={PYTHON_VERSION} でない")
    if mypy_python != PYTHON_VERSION:
        faults.append(f"mypy python_version が {PYTHON_VERSION} でない")
    if ruff_target != "py314":
        faults.append("ruff target-version が py314 でない")

    try:
        dev_entrypoint = (root / "scripts/dev.py").read_text(encoding="utf-8")
    except OSError as exc:
        faults.append(f"scripts/dev.py を読めない: {exc}")
    else:
        if '[uv, "sync", "--frozen", "--group", "dev"]' not in dev_entrypoint:
            faults.append("scripts/dev.py: setup が uv frozen sync でない")

    for path in WORKFLOWS:
        try:
            text = (root / path).read_text(encoding="utf-8")
        except OSError as exc:
            faults.append(f"{path} を読めない: {exc}")
            continue
        faults.extend(_workflow_hygiene_faults(path, text))
        if "uses: astral-sh/setup-uv@" in text:
            if f'python-version: "{PYTHON_VERSION}"' not in text:
                faults.append(f"{path}: setup-uv Python pin が一致しない")
            if "uv sync --frozen --group dev" not in text:
                faults.append(f"{path}: uv frozen sync がない")
    return faults


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
    if source["latest_checked_commit"] != TEMPLATE_LATEST_CHECKED_COMMIT:
        faults.append("source.latest_checked_commit が最新監査対象と一致しない")
    if source["latest_checked_at"] != TEMPLATE_LATEST_CHECKED_AT:
        faults.append("source.latest_checked_at が最新監査日と一致しない")
    if source["latest_checked_commit"] == source["commit"]:
        faults.append("固定採用点と latest checked point が分離されていない")
    if source["delta_disposition"] != "partially-adapted":
        faults.append("source.delta_disposition が partially-adapted でない")
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

    discovery = next((m for m in mappings if m["id"] == "discovery-lifecycle"), None)
    if discovery is None or discovery.get("status") != "adapted":
        faults.append("discovery-lifecycle は adapted でなければならない")
    elif not REQUIRED_DISCOVERY_PATHS <= set(discovery["current_paths"]):
        faults.append("discovery lifecycle の ledger/schema/gate/test current_paths が不完全")

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
    faults.extend(detect_toolchain_faults(root))
    return sorted(set(faults))


def run(ctx: Ctx) -> None:
    del ctx
    try:
        data = load(ALIGNMENT)
        faults = detect_alignment_faults(data)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        faults = [f"対応表を読み込めない: {exc}"]
    gate(
        "G-TEMPLATE-ALIGNMENT",
        not faults,
        "HELIX-HARNESS 固定コミットの read-only 対応表、Python-native 開発環境、L2 と discovery ledger が整合 "
        f"(違反={faults[:4]})",
    )
