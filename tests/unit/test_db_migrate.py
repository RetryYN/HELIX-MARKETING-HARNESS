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
