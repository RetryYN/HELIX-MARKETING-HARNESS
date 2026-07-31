"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-14: mask")
def test_secret_repr_and_exception_masked() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-14: get_credential")
def test_get_credential_unavailable_fail_close() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-14: check_endpoint")
def test_endpoint_mismatch_rejected_before_connect() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-14: scan")
def test_scan_repo_sqlite_logs_zero_plaintext() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-14: scan")
def test_scan_finding_contains_no_plaintext() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-14: mask")
def test_mask_patterns_from_config() -> None:
    """du-contracts DU-14 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
