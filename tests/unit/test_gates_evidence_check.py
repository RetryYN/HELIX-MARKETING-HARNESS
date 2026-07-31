"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-08）")
def test_check_complete_all_required_kinds_pass() -> None:
    """du-contracts DU-08 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-08）")
def test_check_complete_missing_kind_rejected() -> None:
    """du-contracts DU-08 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-08）")
def test_check_complete_kind_rule_violation_rejected() -> None:
    """du-contracts DU-08 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S0.1 test-first: 実装開始時に red 化（設計 = du-contracts DU-08）")
def test_check_complete_unknown_required_kind_fail_close() -> None:
    """du-contracts DU-08 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
