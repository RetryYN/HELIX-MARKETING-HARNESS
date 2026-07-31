"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-12: set")
def test_set_inserts_new_row_with_supersedes_chain() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: set")
def test_set_without_reason_rejected() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: set")
def test_set_same_key_same_changed_at_rejected() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: get")
def test_get_returns_latest_row_type_converted() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: get")
def test_get_missing_key_returns_default_when_given() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: get")
def test_get_missing_key_without_default_fail_close() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-12: set")
def test_direct_update_delete_blocked_by_trigger() -> None:
    """du-contracts DU-12 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
