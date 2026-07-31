"""STC-I-03（AC-SR-02）— 有効 brief なしの下位 loop_run 開始拒否。

DDL 層（brief 列 NULL の拒否）は常設。digest 不一致・失効・superseded の拒否は
kernel の validate_strategic_brief（DU-02）実装と同時に赤→緑（S0.1）。
"""

import sqlite3

import pytest

from tests.conftest import seed_brief


def test_lower_run_without_brief_rejected_by_ddl(conn: sqlite3.Connection) -> None:
    seed_brief(conn)
    conn.execute(
        "INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
        " VALUES ('upper', 'LP-U', 'running', 'k0', 't')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
            " parent_loop_run_id) VALUES ('lower', 'LP-W', 'pending', 'k1', 't', 1)")


@pytest.mark.skip(reason="S0.1 test-first: validate_strategic_brief 実装と同時に赤→緑")
def test_stale_or_mismatched_brief_rejected_by_kernel() -> None:
    # 設計リンク: du-contracts DU-02（S0.1 test-first で red 化）
    raise NotImplementedError
