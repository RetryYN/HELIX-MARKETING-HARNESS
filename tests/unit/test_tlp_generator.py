"""STC-I-05（AC-SR-03/06）— TLP 不変条件。DDL 層（UNIQUE・整合トリガ・packet_kind CHECK）は常設。"""

import sqlite3

import pytest

from tests.conftest import insert_tlp, seed_brief, seed_lower_run


def test_duplicate_packet_per_run_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    run = seed_lower_run(conn, b)
    insert_tlp(conn, run, b)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        insert_tlp(conn, run, b, kind="failure", key="TLP-dup")


def test_non_terminal_or_upper_run_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    running = seed_lower_run(conn, b, state="running", key="k-run")
    with pytest.raises(sqlite3.IntegrityError, match="tlp integrity"):
        insert_tlp(conn, running, b)


def test_digest_mismatch_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    run = seed_lower_run(conn, b)
    with pytest.raises(sqlite3.IntegrityError, match="tlp integrity"):
        insert_tlp(conn, run, b, digest="b" * 64)


def test_failure_packet_cannot_carry_causal_interpretation(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    run = seed_lower_run(conn, b, state="failed")
    with pytest.raises(sqlite3.IntegrityError):
        insert_tlp(conn, run, b, kind="failure", causal_interpretation="観測なき因果の捏造")
    insert_tlp(conn, run, b, kind="failure")  # 事実・再現・復旧のみなら受理


@pytest.mark.skip(reason="S0.1 test-first: 終端遷移と同一 transaction の TLP 生成の実装と同時に赤→緑")
def test_kernel_generates_packet_at_terminal() -> None:
    # 設計リンク: du-contracts DU-02（S0.1 test-first で red 化）
    raise NotImplementedError
