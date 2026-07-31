"""DU-11（migration/DDL 試験）— 正準 DDL の適用検証。ITC-01 の前提部を常設 CI で実行する。

kernel の migration ランナー（schema_version 記録・次版昇格）は S0.1 test-first で追補する。
"""

import sqlite3

import pytest

from tests.conftest import DDL


def test_ddl_applies_to_empty_db_with_25_tables_11_triggers(conn: sqlite3.Connection) -> None:
    assert conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 25
    assert conn.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0] == 11
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

def test_reapply_without_migration_versioning_fails(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.OperationalError):
        conn.executescript(DDL)

@pytest.mark.skip(reason="S0.1 test-first: schema_version 記録と次版昇格は DU-11 実装と同時に赤→緑")
def test_schema_version_recorded_and_upgrades() -> None:
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_empty_db_creates_25_tables_and_11_triggers() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_records_version_checksum_applied_at_by() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_skips_applied_versions_idempotent() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_duplicate_version_stops_fatal() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_checksum_mismatch_stops_before_apply() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_apply_all_crash_mid_migration_rolls_back_whole_version() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: verify")
def test_verify_complete_schema_passes() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: verify")
def test_verify_missing_table_or_trigger_fails() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: verify")
def test_verify_foreign_key_violation_fails() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: verify")
def test_verify_tlp_orphan_detected_fatal() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_append_only_triggers_reject_update_and_delete() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_strategic_briefs_content_update_rejected_status_transition_allowed() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-11: apply_all")
def test_tlp_integrity_trigger_rejects_mismatched_insert() -> None:
    """du-contracts DU-11 の契約観点を検証する（実装スライスで red→green）。"""
    raise NotImplementedError
