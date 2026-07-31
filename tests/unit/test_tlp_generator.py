"""STC-I-05（AC-SR-03/06）— TLP 不変条件。DDL 層（UNIQUE・整合トリガ・packet_kind CHECK）は常設。"""

import sqlite3

import pytest

from tests.conftest import insert_tlp, seed_brief, seed_lower_run


def test_duplicate_packet_per_run_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    run = seed_lower_run(conn, b)
    insert_tlp(conn, run, b)
    # 2 件目は種別一致（completed=learning）でも UNIQUE(loop_run_id) で拒否される
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        insert_tlp(conn, run, b, key="TLP-dup")


def test_non_terminal_or_upper_run_rejected(conn: sqlite3.Connection) -> None:
    b = seed_brief(conn)
    running = seed_lower_run(conn, b, state="running", key="k-run")
    with pytest.raises(sqlite3.IntegrityError, match="tlp integrity|kind must match"):
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


def test_kind_must_match_terminal_state(conn: sqlite3.Connection) -> None:
    """completed→learning のみ／failed・escalated・cancelled→failure のみ（DDL 強制）。"""
    b = seed_brief(conn)
    completed = seed_lower_run(conn, b, state="completed", key="k-c")
    with pytest.raises(sqlite3.IntegrityError, match="kind must match"):
        insert_tlp(conn, completed, b, kind="failure")
    for st, key in (("failed", "k-f"), ("escalated", "k-e"), ("cancelled", "k-x")):
        run = seed_lower_run(conn, b, state=st, key=key)
        with pytest.raises(sqlite3.IntegrityError, match="kind must match"):
            insert_tlp(conn, run, b, kind="learning")
        insert_tlp(conn, run, b, kind="failure")  # 正しい組合せは受理


def test_failure_packet_cannot_carry_any_interpretation_field(conn: sqlite3.Connection) -> None:
    """failure は解釈系 5 フィールドをすべて持てない（DDL: tlp_kind_field_rules）。"""
    b = seed_brief(conn)
    for i, extra in enumerate((
        {"causal_interpretation": "捏造"},
        {"hypothesis_result": "supported"},
        {"assessment_reason": "理由"},
        {"alternative_explanations_json": '["ALT"]'},
        {"proposed_revision_targets_json": '["VH-1"]'},
    )):
        run = seed_lower_run(conn, b, state="failed", key=f"k-fi{i}")
        with pytest.raises(sqlite3.IntegrityError, match="field rules"):
            insert_tlp(conn, run, b, kind="failure", **extra)


def test_learning_packet_requires_observation_and_interpretation(conn: sqlite3.Connection) -> None:
    """learning は観測・仮説判定・因果解釈・対立説明が必須（DDL: tlp_kind_field_rules）。"""
    b = seed_brief(conn)
    for i, extra in enumerate((
        {"observations_json": "[]"},
        {"alternative_explanations_json": "[]"},
    )):
        run = seed_lower_run(conn, b, state="completed", key=f"k-li{i}")
        with pytest.raises(sqlite3.IntegrityError, match="field rules"):
            insert_tlp(conn, run, b, kind="learning", **extra)


def test_loop_run_brief_binding_is_immutable(conn: sqlite3.Connection) -> None:
    """loop_runs の brief id/digest は INSERT 後に変更できない（DDL: loop_runs_brief_immutable）。"""
    b = seed_brief(conn)
    run = seed_lower_run(conn, b, key="k-imm")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute("UPDATE loop_runs SET strategic_brief_digest = ? WHERE id = ?", ("b" * 64, run))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute("UPDATE loop_runs SET strategic_brief_id = 999 WHERE id = ?", (run,))


@pytest.mark.skip(reason="test-first DU-02: generate_tactical_learning_packet")
def test_kernel_generates_packet_at_terminal() -> None:
    # 設計リンク: du-contracts DU-02（S0.1 test-first で red 化）
    raise NotImplementedError
