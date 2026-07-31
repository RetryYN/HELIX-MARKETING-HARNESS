"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connect_sets_foreign_keys_on() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connect_sets_wal_and_busy_timeout() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connect_configures_row_factory() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connect_missing_protection_trigger_fatal() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connect_unmigrated_db_fatal() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-10: connect")
def test_connected_db_append_only_trigger_blocks_update_delete() -> None:
    """du-contracts DU-10 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
