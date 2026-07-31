"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_api_first_route_selected() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_browser_fallback_converges_same_evidence_contract() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_write_operation_assembly_rejected() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_property_mismatch_rejected_before_call() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_hash_fixed_and_operation_log_before_ingest() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-22: fetch")
def test_dry_run_records_fingerprint_only() -> None:
    """du-contracts DU-22 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
