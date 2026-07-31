"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-20: commit_workspace")
def test_commit_returns_valid_40_or_64_hex_hash() -> None:
    """du-contracts DU-20 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-20: link")
def test_link_records_commit_hash_evidence() -> None:
    """du-contracts DU-20 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-20: link")
def test_link_39_digit_hash_rejected() -> None:
    """du-contracts DU-20 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-20: link")
def test_link_rerun_converges_to_single_row() -> None:
    """du-contracts DU-20 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-20: restore")
def test_restore_reproduces_reviewed_source() -> None:
    """du-contracts DU-20 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
