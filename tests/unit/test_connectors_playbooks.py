"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-16: get")
def test_get_active_playbook_validated() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-16: get")
def test_get_missing_broken_and_retired_rejected() -> None:
    """missing／broken／retired の fail-close を同じ取得境界で検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-16: record_failure")
def test_record_failure_increments_and_demotes_at_threshold() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-16: record_success")
def test_record_success_resets_failures_and_verifier() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-16: get")
def test_broken_schema_json_fatal() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-16: install_repaired_version")
def test_install_repaired_version_atomic_lineage() -> None:
    """repair 版切替の原子性・系譜・同task再呼出しの冪等性を検証する。"""
    raise NotImplementedError
