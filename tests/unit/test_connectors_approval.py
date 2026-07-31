"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_request_inserts_pending_and_notifies_binding() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_duplicate_request_unique_idempotent() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_poll_approved_records_evidence_atomically() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_binding_mismatch_response_invalid_keeps_waiting() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_rejected_classified_non_retryable_failure() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_rerequest_on_expired_new_row_series() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="S1 スライス: 実装開始時に red 化（設計 = du-contracts DU-18）")
def test_rerequest_limit_reached_escalates() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
