"""共通 fixture: 正準 DDL を空 SQLite へ適用した接続を提供する。"""

import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DDL = (ROOT / "docs/L3-system-requirements/canonical/schemas/s0/ddl.sql").read_text(encoding="utf-8")
DG = "a" * 64


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(DDL)
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


def seed_brief(c: sqlite3.Connection, key: str = "SB-1", digest: str = DG, status: str = "active") -> int:
    c.execute(
        "INSERT INTO strategic_briefs (brief_key, version, strategic_choice_id, segment_context_id,"
        " value_hypothesis_id, desired_recognition_change, tactical_objective, media_role,"
        " message_hypothesis, measurement_plan_json, valid_from, digest, status, created_at)"
        " VALUES (?, 1, 'SC-1', 'SEG-1', 'VH-1', 'x', 'y', 'proof', 'm', '[]', '2026-08-01', ?, ?, 't')",
        (key, digest, status),
    )
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def seed_lower_run(c: sqlite3.Connection, brief_id: int, state: str = "completed",
                   digest: str = DG, key: str = "k-lower") -> int:
    c.execute(
        "INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
        " VALUES ('upper', 'LP-U', 'running', ?, 't')", (key + "-parent",))
    parent = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute(
        "INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
        " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
        " VALUES ('lower', 'LP-W', ?, ?, 't', ?, ?, ?)", (state, key, parent, brief_id, digest))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def insert_tlp(c: sqlite3.Connection, run_id: int, brief_id: int, kind: str = "learning",
               digest: str = DG, key: str | None = None, **extra: str) -> None:
    cols: dict[str, object] = {
        "packet_key": key or f"TLP-{run_id}-{kind}", "packet_kind": kind, "loop_run_id": run_id,
        "strategic_brief_id": brief_id, "strategic_brief_digest": digest,
        "observations_json": "[]", "confidence": 0.5, "evidence_ids_json": '["EV-1"]',
        "recommended_next_action": "continue", "created_at": "t",
    }
    if kind == "learning":
        # learning は観測・仮説判定・因果解釈・対立説明が必須（DDL: tlp_kind_field_rules）
        cols.update(observations_json='["OBS-1"]', hypothesis_result="supported",
                    assessment_reason="r", causal_interpretation="c",
                    alternative_explanations_json='["ALT-1"]')
    else:
        cols.update(failure_fact="f", reproduction_conditions="rc", recovery_conditions="rv")
    cols.update(extra)
    keys = ", ".join(cols)
    qs = ", ".join("?" * len(cols))
    c.execute(f"INSERT INTO tactical_learning_packets ({keys}) VALUES ({qs})", list(cols.values()))  # noqa: S608
