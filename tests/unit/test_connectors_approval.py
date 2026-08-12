"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import sqlite3

import pytest


def _insert_pending_approval(conn: sqlite3.Connection) -> int:
    """DDL fixture に pending approval を 1 行だけ用意する。"""
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO approvals (task_id, requested_by_agent_id, channel, binding_subject, "
        "binding_operation, binding_at, decision, created_at) "
        "VALUES (1, 1, 'discord', 'article:1', 'publish', '2026-08-12T00:00:00Z', "
        "'pending', '2026-08-12T00:00:00Z')"
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


@pytest.mark.skip(reason="test-first DU-18: request")
def test_request_inserts_pending_and_notifies_binding() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-18: request")
def test_duplicate_request_unique_idempotent() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-18: receive_interaction")
def test_receive_interaction_approved_records_evidence_atomically() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


def test_receive_interaction_replay_does_not_double_finalize(
    conn: sqlite3.Connection,
) -> None:
    """同一 interaction の再送は pending 限定 CAS で二重確定されない。"""
    approval_id = _insert_pending_approval(conn)
    before_count = conn.execute("SELECT count(*) FROM approvals").fetchone()[0]

    first = conn.execute(
        "UPDATE approvals SET decision = 'approved', decided_at = ? "
        "WHERE id = ? AND decision = 'pending'",
        ("2026-08-12T00:01:00Z", approval_id),
    )
    assert first.rowcount == 1
    decision_before_replay = conn.execute(
        "SELECT decision FROM approvals WHERE id = ?", (approval_id,)
    ).fetchone()[0]

    replay = conn.execute(
        "UPDATE approvals SET decision = 'approved', decided_at = ? "
        "WHERE id = ? AND decision = 'pending'",
        ("2026-08-12T00:01:00Z", approval_id),
    )

    assert replay.rowcount == 0
    assert conn.execute(
        "SELECT decision FROM approvals WHERE id = ?", (approval_id,)
    ).fetchone()[0] == decision_before_replay == "approved"
    assert conn.execute("SELECT count(*) FROM approvals").fetchone()[0] == before_count


def test_receive_interaction_competing_decisions_only_one_cas_succeeds(
    conn: sqlite3.Connection,
) -> None:
    """競合する確定要求は先勝ちの pending 限定 CAS 1 件だけを許可する。"""
    approval_id = _insert_pending_approval(conn)
    before_count = conn.execute("SELECT count(*) FROM approvals").fetchone()[0]

    approved = conn.execute(
        "UPDATE approvals SET decision = 'approved', decided_at = ? "
        "WHERE id = ? AND decision = 'pending'",
        ("2026-08-12T00:01:00Z", approval_id),
    )
    rejected = conn.execute(
        "UPDATE approvals SET decision = 'rejected', decided_at = ? "
        "WHERE id = ? AND decision = 'pending'",
        ("2026-08-12T00:01:01Z", approval_id),
    )

    assert (approved.rowcount, rejected.rowcount) == (1, 0)
    assert sum(cursor.rowcount for cursor in (approved, rejected)) == 1
    assert conn.execute(
        "SELECT decision FROM approvals WHERE id = ?", (approval_id,)
    ).fetchone()[0] == "approved"
    assert conn.execute("SELECT count(*) FROM approvals").fetchone()[0] == before_count


def test_finalized_approval_rejects_direct_update_and_delete(
    conn: sqlite3.Connection,
) -> None:
    """pending 以外の approval は直接 SQL でも更新・削除できない。"""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO approvals (task_id, requested_by_agent_id, channel, binding_subject, "
        "binding_operation, binding_at, decision, created_at) "
        "VALUES (1, 1, 'discord', 'article:1', 'publish', '2026-08-12T00:00:00Z', "
        "'approved', '2026-08-12T00:00:00Z')"
    )
    for statement in (
        "UPDATE approvals SET decision = 'rejected' WHERE id = 1",
        "DELETE FROM approvals WHERE id = 1",
    ):
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            conn.execute(statement)
        assert exc_info.value.sqlite_errorcode & 0xFF == sqlite3.SQLITE_CONSTRAINT
    row = conn.execute("SELECT decision FROM approvals WHERE id = 1").fetchone()
    assert row == ("approved",)


@pytest.mark.skip(reason="test-first DU-18: receive_interaction")
def test_invalid_interaction_keeps_waiting() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-18: receive_interaction")
def test_rejected_classified_non_retryable_failure() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-18: rerequest_on_expired")
def test_rerequest_on_expired_new_row_series() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-18: rerequest_on_expired")
def test_rerequest_limit_reached_escalates() -> None:
    """du-contracts DU-18 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError
