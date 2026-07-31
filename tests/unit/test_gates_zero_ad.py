"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-07: check_metric_type")
def test_check_metric_type_free_metric_passes() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-07: check_metric_type")
def test_check_metric_type_deny_types_rejected() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-07: check_metric_type")
def test_check_metric_type_case_variant_rejected() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-07: check_domain")
def test_check_domain_denylist_hit_rejected() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-07: check_domain")
def test_check_domain_clean_domain_passes() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-07: check_domain")
def test_check_domain_empty_allowlist_fail_close() -> None:
    """du-contracts DU-07 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
