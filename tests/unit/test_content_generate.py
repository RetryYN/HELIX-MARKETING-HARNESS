"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-19）")
def test_same_input_same_seed_same_sha256() -> None:
    """du-contracts DU-19 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-19）")
def test_different_seed_different_output() -> None:
    """du-contracts DU-19 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-19）")
def test_unversioned_source_rejected_no_output() -> None:
    """du-contracts DU-19 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-19）")
def test_no_external_io_and_no_db_touch() -> None:
    """du-contracts DU-19 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-19）")
def test_crash_leaves_no_partial_output() -> None:
    """du-contracts DU-19 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
