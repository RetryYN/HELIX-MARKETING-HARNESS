"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_allowed_commits_state_and_passed_log() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_undefined_combination_rejected_db_unchanged() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_terminal_state_request_rejected() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_rejected_records_rejected_row_only() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_crash_mid_tx_leaves_no_partial_state() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_verify_fail_retry_boundary_switches_to_exhausted() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_double_fire_rejected_by_stale_from_state() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_begin_immediate_serializes_concurrent_write() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: register_guard")
def test_register_guard_wires_event_guard() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: register_guard")
def test_register_guard_unregistered_event_allowed_transition_fatal() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_lower_start_without_valid_brief_rejected() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_lower_terminal_transition_includes_tlp_same_tx() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: transition")
def test_transition_busy_timeout_normalized_to_retryable() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: register_guard")
def test_register_guard_is_startup_only_no_runtime_swap() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-01: register_guard")
def test_register_guard_duplicate_or_unknown_event_fatal() -> None:
    """du-contracts DU-01 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
