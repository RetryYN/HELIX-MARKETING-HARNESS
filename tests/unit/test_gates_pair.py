"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_establish_hash_match_creates_passed_pair_and_pairpass() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_establish_hash_mismatch_rejected_no_row() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_establish_duplicate_pair_rejected() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_require_pair_missing_or_revoked_rejected() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_require_pair_passed_returns_pairpass() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_revoke_if_changed_revokes_on_commit_change() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-05）")
def test_pairpass_forgery_without_sentinel_raises_fatal() -> None:
    """du-contracts DU-05 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
