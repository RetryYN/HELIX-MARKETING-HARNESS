"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_get_active_playbook_validated() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_get_missing_rejected() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_get_broken_and_retired_rejected() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_record_failure_increments_and_demotes_at_threshold() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_record_success_resets_failures_and_verifier() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-16）")
def test_broken_schema_json_fatal() -> None:
    """du-contracts DU-16 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
