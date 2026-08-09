"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-15: launch")
def test_launch_failure_retryable() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: launch")
def test_storage_state_profile_scoped_cross_denied() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: launch")
def test_launch_persists_profile_state_and_scope() -> None:
    """profile別storage stateの保存再利用とScopeContext伝播を検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: screenshot")
def test_screenshot_url_reachability_and_mismatch_denied() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: screenshot")
def test_screenshot_hash_evidence_is_caller_owned() -> None:
    """captureはPathのみ返し、hash固定と証跡化が呼出側責務であることを検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: screenshot")
def test_screenshot_timeout_retryable_without_state_change() -> None:
    """timeout・描画失敗のRetryableError化と状態不変を検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_actual_read_lifecycle_and_simulation_zero_external_rows() -> None:
    """actual readの連番1対1証跡とsimulationの外部行ゼロを検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_pre_send_retryable_failure_consumes_no_idempotency_key() -> None:
    """送信前一時失敗でidempotency keyと外部操作行を消費しないことを検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_run_playbook_write_interval_uniform_and_seed_logged() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_x_write_rejected_zero_send() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_daily_cap_rejected_before_send() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_sent_reconcile_confirms_without_resend() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-15: run_playbook")
def test_sent_unverifiable_marked_unknown_no_resend() -> None:
    """du-contracts DU-15 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
