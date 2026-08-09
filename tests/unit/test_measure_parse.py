"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-23: parse")
def test_partial_corruption_quarantined_normal_rows_continue() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: parse")
def test_all_rows_corrupt_import_source_invalid() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: ingest")
def test_ingest_hash_mismatch_rejected_no_insert() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: ingest")
def test_ingest_single_transaction_full_rollback() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: ingest")
def test_ingest_rerun_idempotent_zero_delta() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: ingest")
def test_fk_missing_rejected_before_insert() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: parse")
def test_empty_export_zero_rows_evidence_only() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: parse")
def test_non_pv_and_paid_metric_columns_excluded() -> None:
    """S0で許可するPV以外の列と有料指標列が結果へ混入しないことを検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-23: ingest")
def test_imported_at_supplied_by_clock() -> None:
    """du-contracts DU-23 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
