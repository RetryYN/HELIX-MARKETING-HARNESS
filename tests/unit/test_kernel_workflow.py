"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-04: load")
def test_load_active_definition_schema_validated() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: load")
def test_load_broken_definition_raises_fatal() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: load")
def test_load_version_pinned_lookup() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_run_step_output_saved_via_evidence_api() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_run_step_failure_normalized_to_three_kinds() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_run_step_never_transitions_task_to_done() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_external_operation_prepared_sent_confirmed_each_committed() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_external_operation_sent_crash_resume_no_resend() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_external_operation_unverifiable_marked_unknown_escalates() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-04: run_step")
def test_draft_and_publish_use_distinct_idempotency_keys() -> None:
    """du-contracts DU-04 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
