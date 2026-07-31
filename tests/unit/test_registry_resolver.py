"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_resolve_priority_order_mcp_first() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_resolve_switch_by_config_insert_only() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_unregistered_service_route_not_registered() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_paid_route_denied_without_exception() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_x_browser_write_route_prohibited() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-13）")
def test_list_declared_readonly_and_schema_failclose() -> None:
    """du-contracts DU-13 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
