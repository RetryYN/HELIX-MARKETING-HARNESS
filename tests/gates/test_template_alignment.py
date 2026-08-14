"""HELIX-HARNESS 適応ゲートの単体・mutation test。"""

from copy import deepcopy
from pathlib import Path

from tools.gates import template_alignment
from tools.gates.common import load


def test_alignment_contract_passes() -> None:
    data = load(template_alignment.ALIGNMENT)
    assert template_alignment.detect_alignment_faults(data) == []


def test_mutation_template_source_commit_is_rejected() -> None:
    data = deepcopy(load(template_alignment.ALIGNMENT))
    data["source"]["commit"] = "0" * 40
    faults = template_alignment.detect_alignment_faults(data)
    assert any("source" in fault or "固定" in fault for fault in faults)


def test_mutation_latest_checked_commit_is_rejected() -> None:
    data = deepcopy(load(template_alignment.ALIGNMENT))
    data["source"]["latest_checked_commit"] = "0" * 40
    faults = template_alignment.detect_alignment_faults(data)
    assert any("latest_checked_commit" in fault for fault in faults)


def test_mutation_latest_checked_at_is_rejected() -> None:
    data = deepcopy(load(template_alignment.ALIGNMENT))
    data["source"]["latest_checked_at"] = "2026-08-13"
    faults = template_alignment.detect_alignment_faults(data)
    assert any("latest_checked_at" in fault for fault in faults)


def test_toolchain_pin_drift_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.13\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """[project]
requires-python = \">=3.14\"
[tool.mypy]
python_version = \"3.14\"
[tool.ruff]
target-version = \"py314\"
""",
        encoding="utf-8",
    )
    faults = template_alignment.detect_toolchain_faults(tmp_path)
    assert any(".python-version" in fault for fault in faults)


def test_checkout_credential_persistence_is_rejected() -> None:
    faults = template_alignment._workflow_hygiene_faults(
        ".github/workflows/example.yml",
        """concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - run: true
""",
    )
    assert any("persist-credentials" in fault for fault in faults)


def test_every_workflow_job_requires_timeout() -> None:
    faults = template_alignment._workflow_hygiene_faults(
        ".github/workflows/example.yml",
        """concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  bounded:
    timeout-minutes: 10
    steps: []
  unbounded:
    steps: []
""",
    )
    assert any("job unbounded" in fault and "timeout" in fault for fault in faults)
