"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-06）")
def test_check_publishable_all_conditions_returns_pairpass() -> None:
    """du-contracts DU-06 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-06）")
def test_check_publishable_without_pair_rejected() -> None:
    """du-contracts DU-06 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-06）")
def test_check_publishable_hash_mismatch_rejected() -> None:
    """du-contracts DU-06 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-06）")
def test_check_publishable_missing_evidence_rejected() -> None:
    """du-contracts DU-06 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-06）")
def test_check_publishable_rejection_precedes_connector_call() -> None:
    """du-contracts DU-06 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
