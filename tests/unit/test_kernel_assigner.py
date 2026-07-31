"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-03: assign")
def test_assign_active_different_principal_pair() -> None:
    """du-contracts DU-03 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-03: assign")
def test_assign_same_agent_pair_rejected() -> None:
    """du-contracts DU-03 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-03: assign")
def test_assign_distinct_agents_same_principal_rejected() -> None:
    """du-contracts DU-03 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-03: assign")
def test_assign_review_verifier_excludes_critic() -> None:
    """du-contracts DU-03 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-03: assign")
def test_assign_inactive_agents_excluded() -> None:
    """du-contracts DU-03 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
