"""STC-I-01/02（AC-SR-05）— 上流正本の append-only を SQLite トリガで強制する。"""

import sqlite3

import pytest

from tests.conftest import insert_tlp, seed_brief, seed_lower_run


def test_stc_i_01_brief_content_update_and_delete_rejected(conn: sqlite3.Connection) -> None:
    seed_brief(conn)
    unref = seed_brief(conn, key="SB-2", status="draft")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE strategic_briefs SET digest = ? WHERE id = 1", ("b" * 64,))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM strategic_briefs WHERE id = ?", (unref,))
    conn.execute("UPDATE strategic_briefs SET status = 'superseded' WHERE id = 1")  # status のみ遷移可


def test_stc_i_02_tlp_update_and_delete_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    run = seed_lower_run(conn, b)
    insert_tlp(conn, run, b)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE tactical_learning_packets SET confidence = 0.9 WHERE id = 1")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM tactical_learning_packets WHERE id = 1")
