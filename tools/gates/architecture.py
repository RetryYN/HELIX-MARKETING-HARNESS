"""構造・DB 層ゲート: DDL 同期／適用・状態機械の決定性・戦略正本の DB 強制・CMP/ITC 台帳・設計書実体。"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from tools.gates.common import (
    BASIC_DESIGN,
    CMP_SCHEMA,
    EVIDENCE_KINDS,
    L4,
    L5,
    L6,
    MIGRATION_RULES,
    ROOT,
    S0_CONTRACT,
    TRACE,
    UPDATES,
    Ctx,
    gate,
    is_frozen,
    live_markdown,
    load,
    rel,
    schema_check,
)

EXPECTED_TABLES = 25
EXPECTED_TRIGGERS = 37  # 既存16＋playbook10＋外部I/O7＋published_url1＋spend_ledger3
INITIAL = {"loop_runs": {"pending"}, "tasks": {"pending"}}
TERMINAL = {"loop_runs": {"completed", "failed", "escalated", "cancelled"},
            "tasks": {"done", "failed", "escalated"}}

BRIEF_INSERT = (
    "INSERT INTO strategic_briefs (brief_key, version, strategic_choice_id, segment_context_id,"
    " value_hypothesis_id, desired_recognition_change, tactical_objective, media_role,"
    " message_hypothesis, measurement_plan_json, valid_from, valid_until, digest, status, created_at)"
    " VALUES (?, 1, 'SC-1', 'SEG-1', 'VH-1', 'x', 'y', 'proof', 'm', '[]',"
    " '2026-08-01', ?, ?, ?, 't')"
)


def _apply(ddl: str) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(ddl)
    return con


# ---------------------------------------------------------------- 検出関数（DB 実 DML）
def strategy_mutation_rejected(ddl: str) -> tuple[bool, str]:
    """上流正本（brief／TLP）への UPDATE/DELETE が append-only トリガで ABORT されるか実証する。"""
    c = _apply(ddl)
    try:
        c.execute(BRIEF_INSERT, ("SB-G", None, "a" * 64, "active"))
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
                  " VALUES ('upper', 'LP-U', 'running', 'kg', 't')")
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
                  " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
                  " VALUES ('lower', 'LP-W', 'completed', 'kg2', 't', 1, 1, ?)", ("a" * 64,))
        c.execute(
            "INSERT INTO tactical_learning_packets (packet_key, packet_kind, loop_run_id,"
            " strategic_brief_id, strategic_brief_digest, observations_json, hypothesis_result,"
            " target_hypothesis_ids_json, assessment_reason, causal_interpretation,"
            " alternative_explanations_json, confidence,"
            " evidence_ids_json, recommended_next_action, created_at)"
            " VALUES ('TLP-G', 'learning', 2, 1, ?, '[\"OBS-1\"]', 'supported', '[]', 'r', 'c',"
            " '[\"ALT-1\"]', 0.5, '[\"EV-1\"]', 'continue', 't')", ("a" * 64,))
        c.execute(BRIEF_INSERT, ("SB-G2", None, "c" * 64, "draft"))
        for stmt in ("UPDATE strategic_briefs SET digest = ? WHERE id = 1",
                     "DELETE FROM strategic_briefs WHERE id = 2",
                     "UPDATE tactical_learning_packets SET confidence = 0.9 WHERE id = 1",
                     "DELETE FROM tactical_learning_packets WHERE id = 1"):
            try:
                c.execute(stmt, ("b" * 64,)) if "?" in stmt else c.execute(stmt)
                return False, f"変異が通過: {stmt}"
            except sqlite3.IntegrityError as ie:
                if "append-only" not in str(ie):
                    return False, f"トリガ以外の理由で拒否（トリガ欠落を偽装）: {stmt} → {ie}"
        return True, "UPDATE/DELETE 4 系すべて append-only トリガで ABORT"
    except sqlite3.Error as e:
        return False, f"検査不能: {e}"
    finally:
        c.close()


ALLOWED_BRIEF_TRANSITIONS = {("draft", "active"), ("active", "superseded"), ("active", "retired")}
DENIED_BRIEF_TRANSITIONS = [
    ("superseded", "active"), ("retired", "active"), ("superseded", "retired"),
    ("retired", "superseded"), ("active", "draft"), ("superseded", "draft"), ("retired", "draft"),
]


def detect_brief_transition_faults(ddl: str) -> list[str]:
    """brief の status 遷移を実 DML で検査する（許可の通過・逆行の拒否の両方）。"""
    bad: list[str] = []
    for src, dst in sorted(ALLOWED_BRIEF_TRANSITIONS):
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, (f"SB-{src}-{dst}", None, "a" * 64, src))
            c.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = ?",
                      (dst, f"SB-{src}-{dst}"))
        except sqlite3.Error as e:
            bad.append(f"許可遷移が拒否された {src}→{dst}: {e}")
        finally:
            c.close()
    for src, dst in DENIED_BRIEF_TRANSITIONS:
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, (f"SB-{src}-{dst}", None, "a" * 64, src))
            c.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = ?",
                      (dst, f"SB-{src}-{dst}"))
            bad.append(f"逆行が通過 {src}→{dst}")
        except sqlite3.IntegrityError as e:
            if "status transition" not in str(e):
                bad.append(f"別理由で拒否（遷移トリガ欠落の偽装） {src}→{dst}: {e}")
        except sqlite3.Error as e:
            bad.append(f"検査不能 {src}→{dst}: {e}")
        finally:
            c.close()
    return bad


def detect_valid_until_faults(ddl: str) -> list[str]:
    """valid_until の延長（後ろ倒し・NULL 化）が拒否され、短縮のみ通ることを実 DML で検査する。"""
    bad: list[str] = []
    cases = [
        ("2026-09-01", "2026-12-01", True, "後ろ倒し"),
        ("2026-09-01", None, True, "NULL 化（無期限延長）"),
        ("2026-09-01", "2026-08-15", False, "短縮"),
        (None, "2026-08-15", False, "無期限→期限設定"),
    ]
    for before, after, should_reject, label in cases:
        c = _apply(ddl)
        try:
            c.execute(BRIEF_INSERT, ("SB-VU", before, "a" * 64, "active"))
            c.execute("UPDATE strategic_briefs SET valid_until = ? WHERE brief_key = 'SB-VU'", (after,))
            if should_reject:
                bad.append(f"valid_until の{label}が通過")
        except sqlite3.IntegrityError as e:
            if not should_reject:
                bad.append(f"valid_until の{label}が拒否された: {e}")
            elif "valid_until" not in str(e):
                bad.append(f"別理由で拒否（トリガ欠落の偽装）{label}: {e}")
        except sqlite3.Error as e:
            bad.append(f"検査不能 {label}: {e}")
        finally:
            c.close()
    return bad


def detect_tlp_json_predicate_faults(ddl: str) -> list[str]:
    """TLP の空配列判定が文字列比較でなく json_array_length であることを検査する。"""
    bad: list[str] = []
    body = ddl.split("CREATE TRIGGER tlp_kind_field_rules")[1].split("END;")[0] if \
        "tlp_kind_field_rules" in ddl else ""
    if not body:
        return ["tlp_kind_field_rules トリガが存在しない"]
    for m in re.finditer(r"(\w+_json)\s+IS\s+NOT\s+'\[\]'", body):
        bad.append(f"文字列比較が残存: {m.group(0)}")
    for col in ("alternative_explanations_json", "proposed_revision_targets_json"):
        if f"json_array_length(NEW.{col})" not in body:
            bad.append(f"{col} が json_array_length 判定でない")
    # 実 DML: 空白入り '[ ]' は文字列比較では非空と誤判定されるが json_array_length では 0 件
    c = _apply(ddl)
    try:
        c.execute(BRIEF_INSERT, ("SB-TLP", None, "a" * 64, "active"))
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at)"
                  " VALUES ('upper', 'LP-U', 'running', 'k1', 't')")
        c.execute("INSERT INTO loop_runs (loop_kind, loop_type, state, idempotency_key, created_at,"
                  " parent_loop_run_id, strategic_brief_id, strategic_brief_digest)"
                  " VALUES ('lower', 'LP-W', 'failed', 'k2', 't', 1, 1, ?)", ("a" * 64,))
        try:
            c.execute(
                "INSERT INTO tactical_learning_packets (packet_key, packet_kind, loop_run_id,"
                " strategic_brief_id, strategic_brief_digest, observations_json, failure_fact,"
                " reproduction_conditions, recovery_conditions, alternative_explanations_json,"
                " confidence, evidence_ids_json, recommended_next_action, created_at)"
                " VALUES ('TLP-SP', 'failure', 2, 1, ?, '[\"OBS-1\"]', 'f', 'rc', 'rv', '[ ]',"
                " 0.5, '[\"EV-1\"]', 'stop', 't')", ("a" * 64,))
        except sqlite3.IntegrityError as e:
            bad.append(f"空白入り空配列 '[ ]' を非空と誤判定して拒否した（文字列比較の残存）: {e}")
    except sqlite3.Error as e:
        bad.append(f"検査不能: {e}")
    finally:
        c.close()
    return bad


def _detect_published_spend_faults(ddl: str) -> list[str]:
    """published_url と paid spend の物理 1:1・原子性を実 DML で検査する。"""
    bad: list[str] = []

    # published_url は provider ID ではなく local external row + operation_log へ 1:1 束縛。
    def _prepare_publish(c: sqlite3.Connection, *, policy: str = "content_publish",
                         result: str = "confirmed") -> None:
        _insert_external_operation(c, policy_category=policy, rate_scope=policy)
        _send_external_operation(c)
        c.execute("UPDATE external_operations SET external_operation_id='provider-1',"
                  " remote_object_id='post-1', response_hash=? WHERE id=1", ("c" * 64,))
        _insert_operation_log(c, provider_id="provider-1", result=result)
        c.execute("INSERT INTO assets "
                  "(id,source_task_id,asset_type,name,canonical_url,metadata_json,created_at) "
                  "VALUES (1,1,'article','Post','https://example.test/post','{}',?)",
                  (_IO_CONFIRMED_AT,))

    c = _external_io_fixture(ddl)
    try:
        _prepare_publish(c)
        _insert_published_url(c)  # provider ID は外部行に存在しても published_url では省略可。
        row = c.execute(
            "SELECT external_operation_row_id,operation_log_evidence_id,external_operation_id "
            "FROM evidence WHERE id=2").fetchone()
        if tuple(row or ()) != (1, 1, None):
            bad.append(f"published_url local 1:1不成立:{tuple(row or ())}")
        try:
            _insert_published_url(c, evidence_id=3)
            bad.append("同一publish operationへのpublished_url重複が通過")
        except sqlite3.IntegrityError:
            pass
    except sqlite3.Error as e:
        bad.append(f"published_url正常束縛が拒否:{e}")
    finally:
        c.close()

    published_mismatches: list[tuple[str, dict]] = [
        ("task不一致", {"task_id": 2}),
        ("operation_log ID不一致", {"operation_log_evidence_id": 99}),
        ("provider ID不一致", {"provider_id": "provider-2"}),
        ("payload external row不一致",
         {"payload_overrides": {"external_operation_row_id": 99}}),
        ("payload operation_log不一致",
         {"payload_overrides": {"operation_log_evidence_id": 99}}),
        ("payload URL不一致", {"payload_overrides": {"url": "https://invalid.test"}}),
        ("payload WP post不一致", {"payload_overrides": {"wp_post_id": "post-2"}}),
        ("payload asset不一致", {"payload_overrides": {"asset_id": 99}}),
    ]
    for label, kwargs in published_mismatches:
        c = _external_io_fixture(ddl)
        try:
            _prepare_publish(c)
            try:
                _insert_published_url(c, **kwargs)
                bad.append(f"published_url {label}が通過")
            except sqlite3.IntegrityError:
                pass
            if c.execute("SELECT count(*) FROM evidence WHERE kind='published_url'").fetchone()[0]:
                bad.append(f"published_url {label}拒否後に行が残存")
        finally:
            c.close()

    for policy, result, label in [
        ("review_sync", "confirmed", "非content_publish"),
        ("content_publish", "rejected", "非confirmed"),
    ]:
        c = _external_io_fixture(ddl)
        try:
            _prepare_publish(c, policy=policy, result=result)
            try:
                _insert_published_url(c)
                bad.append(f"published_url {label}が通過")
            except sqlite3.IntegrityError:
                pass
        finally:
            c.close()

    c = _external_io_fixture(ddl)
    try:
        _prepare_publish(c)
        try:
            c.execute("INSERT INTO evidence "
                      "(id,task_id,kind,value,payload_json,operation_log_evidence_id,created_at) "
                      "VALUES (2,1,'file_hash','x','{}',1,?)", (_IO_CONFIRMED_AT,))
            bad.append("published_url以外がoperation_log_evidence_idを占有")
        except sqlite3.IntegrityError:
            pass
    finally:
        c.close()

    # paid+confirmed は operation_log INSERT の同じ statement で charge まで原子的に作る。
    paid_payload = {
        "approval_id": 1,
        "amount_minor": 100,
        "currency": "JPY",
        "purpose": "approved generation",
        "occurred_at": _IO_CONFIRMED_AT,
    }
    c = _external_io_fixture(ddl)
    try:
        _insert_approved_approval(c)
        _insert_external_operation(c, policy_category="approved_paid_operation",
                                   rate_scope="approved_paid_operation")
        _send_external_operation(c)
        c.execute("UPDATE external_operations SET external_operation_id='paid-provider-1' WHERE id=1")
        _insert_operation_log(c, provider_id="paid-provider-1", payload_overrides=paid_payload)
        atomic = c.execute(
            "SELECT op.status,op.evidence_id,ev.id,sl.entry_type,sl.amount_minor,sl.currency,"
            " sl.external_operation_row_id FROM external_operations AS op "
            "JOIN evidence AS ev ON ev.id=op.evidence_id "
            "JOIN spend_ledger AS sl ON sl.external_operation_row_id=op.id WHERE op.id=1"
        ).fetchone()
        if tuple(atomic or ()) != ("confirmed", 1, 1, "charge", 100, "JPY", 1):
            bad.append(f"paid operation原子3者束縛不成立:{tuple(atomic or ())}")
        _insert_approved_approval(c, approval_id=2, task_id=2)
        _insert_reversal(c)
        net = c.execute("SELECT COALESCE(SUM(CASE entry_type WHEN 'charge' THEN amount_minor "
                        "WHEN 'reversal' THEN -amount_minor END),0) FROM spend_ledger "
                        "WHERE currency='JPY'").fetchone()[0]
        if net != 0:
            bad.append(f"charge/reversal符号付き集計不成立:{net}")
        for label, action in [
            ("charge二重化", lambda: c.execute(
                "INSERT INTO spend_ledger (task_id,entry_type,approval_id,service,amount_minor,"
                "currency,purpose,external_operation_row_id,external_operation_id,occurred_at,created_at) "
                "VALUES (1,'charge',1,'provider',100,'JPY','duplicate',1,'paid-provider-1',?,?)",
                (_IO_CONFIRMED_AT, _IO_CONFIRMED_AT))),
            ("reversal二重化", lambda: _insert_reversal(c, ledger_id=3)),
            ("spend更新", lambda: c.execute(
                "UPDATE spend_ledger SET amount_minor=101 WHERE id=1")),
            ("spend削除", lambda: c.execute("DELETE FROM spend_ledger WHERE id=1")),
        ]:
            try:
                action()
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
    except sqlite3.Error as e:
        bad.append(f"paid/reversal正常系検査不能:{e}")
    finally:
        c.close()

    # ledger制約違反なら operation_log INSERT・final更新・charge の3者がすべてrollback。
    for label, payload_update, seed_approval, omit_keys, created_at in [
        ("approval孤児", {"approval_id": 999}, False, (), _IO_CONFIRMED_AT),
        ("amount 0", {"amount_minor": 0}, True, (), _IO_CONFIRMED_AT),
        ("外貨", {"currency": "USD"}, True, (), _IO_CONFIRMED_AT),
        ("purpose空", {"purpose": ""}, True, (), _IO_CONFIRMED_AT),
        ("occurred_at欠落", {}, True, ("occurred_at",), _IO_CONFIRMED_AT),
        ("occurred_at暦時刻不正", {"occurred_at": "2026-08-10T24:00:00Z"}, True, (),
         _IO_CONFIRMED_AT),
        ("created_at暦日不正", {}, True, (), "2026-08-32T00:00:03Z"),
    ]:
        c = _external_io_fixture(ddl)
        try:
            if seed_approval:
                _insert_approved_approval(c)
            _insert_external_operation(c, policy_category="approved_paid_operation",
                                       rate_scope="approved_paid_operation")
            _send_external_operation(c)
            payload = {**paid_payload, **payload_update}
            try:
                _insert_operation_log(c, payload_overrides=payload,
                                      omit_payload_keys=omit_keys, created_at=created_at)
                bad.append(f"paid {label}が通過")
            except sqlite3.IntegrityError:
                pass
            state = tuple(c.execute(
                "SELECT status,evidence_id FROM external_operations WHERE id=1").fetchone())
            counts = tuple(c.execute(
                "SELECT (SELECT count(*) FROM evidence),"
                " (SELECT count(*) FROM spend_ledger)").fetchone())
            if state != ("sent", None) or counts != (0, 0):
                bad.append(f"paid {label}拒否が非原子的:{state}/{counts}")
        finally:
            c.close()

    # reversal は元chargeの完全反転、approved、非空目的、canonical UTC時刻だけを受理する。
    reversal_faults: list[tuple[str, dict, str]] = [
        ("部分取消", {"amount_minor": 99}, "approved"),
        ("service不一致", {"service": "other-provider"}, "approved"),
        ("外貨", {"currency": "USD"}, "approved"),
        ("purpose空", {"purpose": ""}, "approved"),
        ("occurred_at暦時刻不正", {"occurred_at": "2026-08-10T24:00:00Z"}, "approved"),
        ("created_at非canonical", {"created_at": "2026-08-10 00:00:03"}, "approved"),
        ("未承認", {}, "rejected"),
    ]
    for label, reversal_kwargs, decision in reversal_faults:
        c = _external_io_fixture(ddl)
        try:
            _insert_approved_approval(c)
            _insert_external_operation(c, policy_category="approved_paid_operation",
                                       rate_scope="approved_paid_operation")
            _send_external_operation(c)
            _insert_operation_log(c, payload_overrides=paid_payload)
            _insert_approved_approval(c, approval_id=2, task_id=2, decision=decision)
            try:
                _insert_reversal(c, **reversal_kwargs)
                bad.append(f"reversal {label}が通過")
            except sqlite3.IntegrityError:
                pass
            if c.execute("SELECT count(*) FROM spend_ledger").fetchone()[0] != 1:
                bad.append(f"reversal {label}拒否後に台帳行が変化")
        finally:
            c.close()

    c = _external_io_fixture(ddl)
    try:
        _insert_approved_approval(c)
        _insert_external_operation(c, policy_category="approved_paid_operation",
                                   rate_scope="approved_paid_operation")
        _send_external_operation(c)
        _insert_operation_log(c, payload_overrides=paid_payload)
        _insert_approved_approval(c, approval_id=2, task_id=2)
        _insert_reversal(c)
        try:
            _insert_reversal(c, ledger_id=3, original_id=2)
            bad.append("reversalのreversalが通過")
        except sqlite3.IntegrityError:
            pass
    finally:
        c.close()

    # paid rejected/unknown とfree policyはchargeを作らない。
    for policy, result in [
        ("approved_paid_operation", "rejected"),
        ("approved_paid_operation", "unknown"),
        ("content_publish", "confirmed"),
    ]:
        c = _external_io_fixture(ddl)
        try:
            _insert_approved_approval(c)
            _insert_external_operation(c, policy_category=policy, rate_scope=policy)
            _send_external_operation(c)
            payload = paid_payload if policy == "approved_paid_operation" else {}
            _insert_operation_log(c, result=result, payload_overrides=payload)
            if c.execute("SELECT count(*) FROM spend_ledger").fetchone()[0] != 0:
                bad.append(f"非課金結果にcharge発生:{policy}/{result}")
        except sqlite3.Error as e:
            bad.append(f"非課金結果が拒否:{policy}/{result}:{e}")
        finally:
            c.close()

    # 手入力・無料分類・0円chargeと不正reversalは直接INSERTでも拒否。
    for label, setup, statement, params in [
        ("manual charge", lambda c: _insert_approved_approval(c),
         "INSERT INTO spend_ledger (task_id,entry_type,approval_id,service,amount_minor,currency,"
         "purpose,occurred_at,created_at) VALUES (1,'charge',1,'provider',100,'JPY','manual',?,?)",
         (_IO_CONFIRMED_AT, _IO_CONFIRMED_AT)),
        ("amount 0 charge", lambda c: _insert_approved_approval(c),
         "INSERT INTO spend_ledger (task_id,entry_type,approval_id,service,amount_minor,currency,"
         "purpose,external_operation_row_id,occurred_at,created_at) "
         "VALUES (1,'charge',1,'provider',0,'JPY','zero',999,?,?)",
         (_IO_CONFIRMED_AT, _IO_CONFIRMED_AT)),
    ]:
        c = _external_io_fixture(ddl)
        try:
            setup(c)
            try:
                c.execute(statement, params)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
        finally:
            c.close()

    c = _external_io_fixture(ddl)
    try:
        _insert_approved_approval(c)
        _insert_external_operation(c)
        _send_external_operation(c)
        _insert_operation_log(c)
        try:
            c.execute("INSERT INTO spend_ledger (task_id,entry_type,approval_id,service,amount_minor,"
                      "currency,purpose,external_operation_row_id,occurred_at,created_at) "
                      "VALUES (1,'charge',1,'provider',100,'JPY','free',1,?,?)",
                      (_IO_CONFIRMED_AT, _IO_CONFIRMED_AT))
            bad.append("free policy chargeが通過")
        except sqlite3.IntegrityError:
            pass
    finally:
        c.close()
    return bad


def _playbook_fixture(ddl: str) -> sqlite3.Connection:
    """playbook 版・修復episode検査用の最小実DBを返す。"""
    c = _apply(ddl)
    c.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
              " VALUES (1,'author','p1','author','Author','active','t')")
    c.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
              " VALUES (2,'verifier','p2','verifier','Verifier','active','t')")
    c.execute("INSERT INTO workflows (id,workflow_key,name,task_type,version,definition_json,"
              " required_evidence_json,status,created_at)"
              " VALUES (1,'wf','Workflow','source',1,'{}','[]','active','t')")
    c.execute("INSERT INTO loop_runs (id,loop_kind,loop_type,state,idempotency_key,created_at)"
              " VALUES (1,'upper','LP-U','running','loop-1','t')")
    c.execute("INSERT INTO tasks (id,loop_run_id,workflow_id,task_type,author_agent_id,"
              " verifier_agent_id,state,step_key,attempt,retry_count,idempotency_key,"
              " expected_output_kind,input_json,created_at)"
              " VALUES (1,1,1,'source',1,2,'in_progress','source',1,0,'source-1','source','{}','t')")
    c.execute("INSERT INTO playbooks (id,service,operation,route_type,version,created_by_task_id,"
              " procedure_json,selector_json,status,created_at)"
              " VALUES (1,'svc','publish','browser',1,1,'{}','{}','active','t')")
    c.execute("UPDATE playbooks SET status='broken', consecutive_failures=1,last_failure_at='t1'"
              " WHERE id=1")
    c.commit()
    return c


def _insert_repair(c: sqlite3.Connection, *, task_id: int = 2,
                   fingerprint: str = "a" * 64, state: str = "pending",
                   output_kind: str = "playbook_version") -> None:
    input_json = (f'{{"playbook_id":1,"source_task_id":1,'
                  f'"failure_fingerprint":"{fingerprint}"}}')
    c.execute("INSERT INTO tasks (id,loop_run_id,parent_task_id,workflow_id,task_type,"
              " author_agent_id,verifier_agent_id,state,step_key,attempt,retry_count,"
              " idempotency_key,expected_output_kind,input_json,created_at)"
              " VALUES (?,1,1,1,'playbook_repair',1,2,?,'playbook_repair:1',1,0,"
              " 'playbook-repair:1',?,?, 't')", (task_id, state, output_kind, input_json))


def detect_playbook_version_faults(ddl: str) -> list[str]:
    """修復1回・版連鎖・atomic rollback・不変性を実DMLで検証する。"""
    bad: list[str] = []
    required_triggers = {
        "playbook_repair_task_insert", "playbook_repair_task_no_retry",
        "playbook_repair_no_verify_retry", "playbooks_initial_insert",
        "playbooks_version_insert", "playbooks_content_no_update",
        "playbooks_status_transition", "playbooks_health_active_only",
        "playbooks_retired_no_update", "playbooks_no_delete",
    }
    required_indexes = {"playbooks_one_current", "playbook_repair_one_per_episode"}
    schema = _apply(ddl)
    try:
        triggers = {row[0] for row in schema.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        indexes = {row[0] for row in schema.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        if missing := sorted(required_triggers - triggers):
            bad.append(f"playbook保護trigger欠落:{missing}")
        if missing := sorted(required_indexes - indexes):
            bad.append(f"playbook一意index欠落:{missing}")
    finally:
        schema.close()

    c = _playbook_fixture(ddl)
    try:
        _insert_repair(c)
        for label, statement, params in [
            ("同一episodeへの二重repair", None, ()),
            ("repair束縛の変更", "UPDATE tasks SET retry_count=1 WHERE id=2", ()),
            ("repairのverify retry", "INSERT INTO state_transitions "
             "(entity_type,entity_id,from_state,event,to_state,guard_result,details_json,created_at) "
             "VALUES ('task',2,'verifying','verify_fail','in_progress','passed','{}','t')", ()),
        ]:
            try:
                if statement is None:
                    _insert_repair(c, task_id=3, fingerprint="b" * 64)
                else:
                    c.execute(statement, params)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
        c.rollback()
    finally:
        c.close()

    for label, kwargs in [
        ("非pending repair", {"state": "done"}),
        ("出力型不一致repair", {"output_kind": "other"}),
        ("fingerprint不正repair", {"fingerprint": "xyz"}),
    ]:
        c = _playbook_fixture(ddl)
        try:
            try:
                _insert_repair(c, **kwargs)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
        finally:
            c.close()

    c = _playbook_fixture(ddl)
    try:
        _insert_repair(c)
        c.commit()
        c.execute("BEGIN")
        c.execute("UPDATE tasks SET state='done' WHERE id=2")
        c.execute("UPDATE playbooks SET status='retired' WHERE id=1")
        try:
            c.execute("INSERT INTO playbooks (id,service,operation,route_type,version,"
                      " supersedes_playbook_id,created_by_task_id,procedure_json,selector_json,"
                      " status,created_at) VALUES (2,'svc','publish','browser',3,1,2,'{}','{}',"
                      " 'active','t2')")
            bad.append("不連続versionが通過")
        except sqlite3.IntegrityError:
            pass
        c.rollback()
        current = c.execute("SELECT status FROM playbooks WHERE id=1").fetchone()[0]
        repair = c.execute("SELECT state FROM tasks WHERE id=2").fetchone()[0]
        if (current, repair) != ("broken", "pending"):
            bad.append(f"successor失敗時rollback不成立:{current}/{repair}")

        c.execute("BEGIN")
        c.execute("UPDATE tasks SET state='done' WHERE id=2")
        c.execute("UPDATE playbooks SET status='retired' WHERE id=1")
        c.execute("INSERT INTO playbooks (id,service,operation,route_type,version,"
                  " supersedes_playbook_id,created_by_task_id,procedure_json,selector_json,"
                  " status,created_at) VALUES (2,'svc','publish','browser',2,1,2,'{}','{}',"
                  " 'active','t2')")
        c.commit()
        rows = c.execute("SELECT version,status,supersedes_playbook_id FROM playbooks ORDER BY version").fetchall()
        if rows != [(1, "retired", None), (2, "active", 1)]:
            bad.append(f"版連鎖不成立:{rows}")
        for label, statement in [
            ("retired版内容更新", "UPDATE playbooks SET procedure_json='{\"x\":1}' WHERE id=1"),
            ("playbook版削除", "DELETE FROM playbooks WHERE id=2"),
        ]:
            try:
                c.execute(statement)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
    finally:
        c.close()

    c = _playbook_fixture(ddl)
    try:
        try:
            c.execute("UPDATE playbooks SET procedure_json='{\"x\":1}' WHERE id=1")
            bad.append("broken版内容更新が通過")
        except sqlite3.IntegrityError:
            pass
        try:
            c.execute("UPDATE playbooks SET consecutive_failures=2 WHERE id=1")
            bad.append("broken版のhealth更新が通過")
        except sqlite3.IntegrityError:
            pass
        try:
            c.execute("INSERT INTO playbooks (id,service,operation,route_type,version,"
                      " created_by_task_id,procedure_json,status,created_at)"
                      " VALUES (2,'other','read','api',1,1,'{}','broken','t')")
            bad.append("初版brokenが通過")
        except sqlite3.IntegrityError:
            pass
    finally:
        c.close()
    return bad


_IO_REQUEST_HASH = "b" * 64
_IO_PREPARED_AT = "2026-08-10T00:00:01Z"
_IO_SENT_AT = "2026-08-10T00:00:02Z"
_IO_CONFIRMED_AT = "2026-08-10T00:00:03Z"
_MISSING = object()


def _external_io_fixture(ddl: str) -> sqlite3.Connection:
    """外部 I/O 台帳と operation_log の DML 検査用最小 DB を返す。"""
    c = _apply(ddl)
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    c.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
              " VALUES (1,'io-author','p1','author','I/O Author','active','t')")
    c.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
              " VALUES (2,'io-verifier','p2','verifier','I/O Verifier','active','t')")
    c.execute("INSERT INTO workflows (id,workflow_key,name,task_type,version,definition_json,"
              " required_evidence_json,status,created_at)"
              " VALUES (1,'io-wf','External I/O','external_io',1,'{}','[]','active','t')")
    c.execute("INSERT INTO loop_runs (id,loop_kind,loop_type,state,idempotency_key,created_at)"
              " VALUES (1,'upper','LP-U','running','io-loop','t')")
    for task_id in (1, 2):
        c.execute("INSERT INTO tasks (id,loop_run_id,workflow_id,task_type,author_agent_id,"
                  " verifier_agent_id,state,step_key,attempt,retry_count,idempotency_key,"
                  " expected_output_kind,input_json,created_at)"
                  " VALUES (?,1,1,'external_io',1,2,'in_progress',?,1,0,?,'operation_log','{}','t')",
                  (task_id, f"io-{task_id}", f"io-task-{task_id}"))
    c.execute("INSERT INTO config (id,key,value_json,value_type,changed_at,reason)"
              " VALUES (1,'external_operation.sent_recovery_timeout_sec','300','integer',"
              " '2026-08-10T00:00:00Z','required recovery timeout')")
    c.commit()
    return c


def _insert_external_operation(
        c: sqlite3.Connection, *, operation_id: int = 1, task_id: int = 1,
        effect: str = "write", execution_mode: str = "actual", request_sequence: int = 1,
        correlation_key: str | None = None, idempotency_key: object = _MISSING,
        status: str = "prepared", operation: str | None = None,
        policy_category: str | None = None, rate_scope: object = _MISSING,
        service: str = "provider", request_hash: str = _IO_REQUEST_HASH,
        prepared_at: str = _IO_PREPARED_AT) -> None:
    """prepared external row を追加する。拒否 DML 用に制約違反値も受け取る。"""
    op_name = operation or ("publish" if effect == "write" else "poll")
    policy = policy_category or ("external_read" if effect == "read" else "content_publish")
    if rate_scope is _MISSING:
        rate_scope = None if effect == "read" else policy
    if idempotency_key is _MISSING:
        idempotency_key = f"write-key-{operation_id}" if effect == "write" else None
    if correlation_key is None:
        correlation_key = (str(idempotency_key) if effect == "write" else
                           f"read:{task_id}:{request_hash}:{request_sequence}")
    c.execute(
        "INSERT INTO external_operations "
        "(id,task_id,service,operation,effect,policy_category,rate_scope,execution_mode,"
        " target_endpoint,idempotency_key,correlation_key,request_hash,request_sequence,status,"
        " prepared_at) VALUES (?,?,?,?,?,?,?,?, '/endpoint',?,?,?,?,?,?)",
        (operation_id, task_id, service, op_name, effect, policy, rate_scope, execution_mode,
         idempotency_key, correlation_key, request_hash, request_sequence, status, prepared_at))


def _send_external_operation(c: sqlite3.Connection, operation_id: int = 1,
                             sent_at: str = _IO_SENT_AT) -> None:
    c.execute("UPDATE external_operations SET status='sent', sent_at=? WHERE id=?",
              (sent_at, operation_id))


def _insert_operation_log(
        c: sqlite3.Connection, *, evidence_id: int = 1, operation_id: int = 1,
        task_id: int | None = None, value: str | None = None,
        external_operation_row_id: int | None = None, provider_id: object = _MISSING,
        result: str = "confirmed", payload_overrides: dict | None = None,
        omit_payload_keys: tuple[str, ...] = (),
        created_at: str = _IO_CONFIRMED_AT) -> None:
    """sent row に対応する operation_log を追加する（AFTER trigger が同じ文で final 化）。"""
    op = c.execute("SELECT * FROM external_operations WHERE id=?", (operation_id,)).fetchone()
    if op is None:
        raise ValueError(f"external operation {operation_id} does not exist")
    if provider_id is _MISSING:
        provider_id = op["external_operation_id"]
    payload = {
        "external_operation_row_id": op["id"],
        "effect": op["effect"],
        "policy_category": op["policy_category"],
        "rate_scope": op["rate_scope"],
        "service": op["service"],
        "operation": op["operation"],
        "correlation_key": op["correlation_key"],
        "request_hash": op["request_hash"],
        "request_sequence": op["request_sequence"],
        "result": result,
    }
    if provider_id is not None:
        payload["provider_operation_id"] = provider_id
    payload.update(payload_overrides or {})
    for key in omit_payload_keys:
        payload.pop(key, None)
    row_id = op["id"] if external_operation_row_id is None else external_operation_row_id
    c.execute(
        "INSERT INTO evidence "
        "(id,task_id,kind,value,payload_json,external_operation_row_id,external_operation_id,created_at) "
        "VALUES (?,?,'operation_log',?,?,?,?, ?)",
        (evidence_id, op["task_id"] if task_id is None else task_id,
         value or f"external-operation:{op['id']}",
         json.dumps(payload, sort_keys=True, separators=(",", ":")), row_id, provider_id,
         created_at))


def _insert_approved_approval(c: sqlite3.Connection, *, approval_id: int = 1,
                              task_id: int = 1, decision: str = "approved") -> None:
    c.execute(
        "INSERT INTO approvals (id,task_id,requested_by_agent_id,channel,binding_subject,"
        " binding_operation,binding_at,decision,decided_at,created_at) "
        "VALUES (?, ?, 1, 'claude_code_app', 'external-operation', 'charge', ?, ?, ?, ?)",
        (approval_id, task_id, _IO_PREPARED_AT, decision, _IO_PREPARED_AT, _IO_PREPARED_AT))


def _insert_published_url(
        c: sqlite3.Connection, *, evidence_id: int = 2, operation_id: int = 1,
        operation_log_evidence_id: int = 1, task_id: int = 1, asset_id: int = 1,
        url: str = "https://example.test/post", provider_id: object = _MISSING,
        payload_overrides: dict | None = None) -> None:
    op = c.execute("SELECT * FROM external_operations WHERE id=?", (operation_id,)).fetchone()
    if op is None:
        raise ValueError(f"external operation {operation_id} does not exist")
    if provider_id is _MISSING:
        provider_id = None
    payload = {
        "url": url,
        "wp_post_id": op["remote_object_id"],
        "external_operation_row_id": operation_id,
        "operation_log_evidence_id": operation_log_evidence_id,
        "asset_id": asset_id,
    }
    if provider_id is not None:
        payload["provider_operation_id"] = provider_id
    payload.update(payload_overrides or {})
    c.execute(
        "INSERT INTO evidence (id,task_id,kind,value,payload_json,asset_id,"
        " external_operation_row_id,operation_log_evidence_id,external_operation_id,created_at) "
        "VALUES (?,?,'published_url',?,?,?,?,?,?,?)",
        (evidence_id, task_id, url,
         json.dumps(payload, sort_keys=True, separators=(",", ":")), asset_id, operation_id,
         operation_log_evidence_id, provider_id, _IO_CONFIRMED_AT))


def _insert_reversal(c: sqlite3.Connection, *, ledger_id: int = 2, task_id: int = 2,
                     approval_id: int = 2, original_id: int = 1,
                     service: str = "provider", amount_minor: int = 100,
                     currency: str = "JPY", purpose: str = "approved reversal",
                     occurred_at: str = _IO_CONFIRMED_AT,
                     created_at: str = _IO_CONFIRMED_AT) -> None:
    c.execute(
        "INSERT INTO spend_ledger (id,task_id,entry_type,approval_id,service,amount_minor,"
        " currency,purpose,reverses_spend_ledger_id,occurred_at,created_at) "
        "VALUES (?,?,'reversal',?,?,?,?, ?,?,?,?)",
        (ledger_id, task_id, approval_id, service, amount_minor, currency, purpose, original_id,
         occurred_at, created_at))


def _unique_column_sets(c: sqlite3.Connection, table: str) -> set[tuple[str, ...]]:
    """SQLite の自動 index を含む UNIQUE 列集合を返す。"""
    result: set[tuple[str, ...]] = set()
    for idx in c.execute(f"PRAGMA index_list('{table}')"):
        if idx[2]:
            cols = tuple(row[2] for row in c.execute(f"PRAGMA index_info('{idx[1]}')"))
            if cols and all(cols):
                result.add(cols)
    return result


def detect_operation_log_kind_faults(items: list[dict]) -> list[str]:
    """operation_log／published_url のローカル束縛と原子的 final 化を検査する。"""
    bad: list[str] = []
    logs = [item for item in items if item.get("kind") == "operation_log"]
    if len(logs) != 1:
        return [f"operation_log kind件数={len(logs)}"]
    item = logs[0]
    expected = {
        "external_operation_row_id", "effect", "policy_category", "rate_scope", "service",
        "operation", "correlation_key", "request_hash", "request_sequence", "result",
    }
    actual = set(item.get("required_payload_keys", []))
    if actual != expected:
        bad.append(f"operation_log必須payload差分={sorted(actual ^ expected)}")
    semantics = item.get("value_semantics", "")
    if "external-operation:<external_operations.id>" not in semantics:
        bad.append("operation_log valueがローカルexternal_operations.id形式でない")
    rules = item.get("column_rules", "")
    for token in ("external_operation_row_id", "external_operations.id", "UNIQUE",
                  "external_operations.evidence_id", "provider", "final"):
        if token not in rules:
            bad.append(f"operation_log column_rules欠落:{token}")
    if "external_operation_id" in actual or "provider_operation_id" in actual:
        bad.append("provider IDが必須payloadになっている")
    paid_expected = {"approval_id", "amount_minor", "currency", "purpose", "occurred_at"}
    paid_actual = set(item.get("conditional_payload_keys", {}).get(
        "approved_paid_operation", []))
    if paid_actual != paid_expected:
        bad.append(f"paid operation_log条件payload差分={sorted(paid_actual ^ paid_expected)}")

    published = [candidate for candidate in items if candidate.get("kind") == "published_url"]
    if len(published) != 1:
        bad.append(f"published_url kind件数={len(published)}")
        return bad
    published_item = published[0]
    published_expected = {
        "url", "wp_post_id", "external_operation_row_id", "operation_log_evidence_id", "asset_id",
    }
    published_actual = set(published_item.get("required_payload_keys", []))
    if published_actual != published_expected:
        bad.append(f"published_url必須payload差分={sorted(published_actual ^ published_expected)}")
    if {"external_operation_id", "provider_operation_id"} & published_actual:
        bad.append("published_urlでprovider IDが必須payloadになっている")
    published_rules = published_item.get("column_rules", "")
    for token in ("external_operation_row_id", "operation_log_evidence_id", "UNIQUE",
                  "confirmed", "content_publish", "provider"):
        if token not in published_rules:
            bad.append(f"published_url column_rules欠落:{token}")
    return bad


def detect_external_operation_evidence_faults(ddl: str) -> list[str]:
    """外部 I/O と operation_log の双方向 1:1・原子化・状態機械を実 DML で検証する。"""
    bad: list[str] = []
    required_triggers = {
        "external_operations_insert_prepared", "external_operations_binding_immutable",
        "external_operations_result_sent_only", "external_operations_lifecycle",
        "external_operations_final_immutable", "external_operations_no_delete",
        "evidence_operation_log_insert", "evidence_published_url_insert",
        "spend_ledger_binding_insert", "spend_ledger_no_update", "spend_ledger_no_delete",
    }
    try:
        schema = _apply(ddl)
    except sqlite3.Error as e:
        return [f"外部I/O schema検査不能:{e}"]
    try:
        triggers = {row[0] for row in schema.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        if missing := sorted(required_triggers - triggers):
            bad.append(f"外部I/O保護trigger欠落:{missing}")
        indexes = {row[0] for row in schema.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        required_indexes = {
            "evidence_operation_log_external_row_one",
            "evidence_published_url_external_row_one",
        }
        if missing := sorted(required_indexes - indexes):
            bad.append(f"外部証跡一意index欠落:{missing}")
        ext_unique = _unique_column_sets(schema, "external_operations")
        ev_unique = _unique_column_sets(schema, "evidence")
        spend_unique = _unique_column_sets(schema, "spend_ledger")
        for columns, uniques, label in [
            (("evidence_id",), ext_unique, "external_operations.evidence_id"),
            (("correlation_key",), ext_unique, "external_operations.correlation_key"),
            (("task_id", "effect", "operation", "request_hash", "request_sequence"),
             ext_unique, "external_operations.read request sequence"),
            (("external_operation_row_id",), ev_unique, "evidence.external_operation_row_id"),
            (("operation_log_evidence_id",), ev_unique, "evidence.operation_log_evidence_id"),
            (("external_operation_row_id",), spend_unique,
             "spend_ledger.external_operation_row_id"),
            (("reverses_spend_ledger_id",), spend_unique,
             "spend_ledger.reverses_spend_ledger_id"),
        ]:
            if columns not in uniques:
                bad.append(f"UNIQUE欠落:{label}")
        ext_fks = {(row[3], row[2], row[4]) for row in schema.execute(
            "PRAGMA foreign_key_list('external_operations')")}
        ev_fks = {(row[3], row[2], row[4]) for row in schema.execute(
            "PRAGMA foreign_key_list('evidence')")}
        spend_fks = {(row[3], row[2], row[4]) for row in schema.execute(
            "PRAGMA foreign_key_list('spend_ledger')")}
        if ("evidence_id", "evidence", "id") not in ext_fks:
            bad.append("FK欠落:external_operations.evidence_id->evidence.id")
        if ("external_operation_row_id", "external_operations", "id") not in ev_fks:
            bad.append("FK欠落:evidence.external_operation_row_id->external_operations.id")
        if ("operation_log_evidence_id", "evidence", "id") not in ev_fks:
            bad.append("FK欠落:evidence.operation_log_evidence_id->evidence.id")
        if ("external_operation_row_id", "external_operations", "id") not in spend_fks:
            bad.append("FK欠落:spend_ledger.external_operation_row_id->external_operations.id")
        if ("reverses_spend_ledger_id", "spend_ledger", "id") not in spend_fks:
            bad.append("FK欠落:spend_ledger.reverses_spend_ledger_id->spend_ledger.id")
        if ("approval_id", "approvals", "id") not in spend_fks:
            bad.append("FK欠落:spend_ledger.approval_id->approvals.id")
        if ("task_id", "tasks", "id") not in spend_fks:
            bad.append("FK欠落:spend_ledger.task_id->tasks.id")
        columns = {row[1]: row for row in schema.execute(
            "PRAGMA table_info('external_operations')")}
        for column in ("effect", "policy_category", "execution_mode", "correlation_key",
                       "request_sequence"):
            if column not in columns or columns[column][3] != 1:
                bad.append(f"外部I/O必須列欠落/nullable:{column}")
        trigger_sql = schema.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='evidence_operation_log_insert'"
        ).fetchone()
        if trigger_sql and "AFTER INSERT" not in trigger_sql[0].upper():
            bad.append("operation_log triggerがAFTER INSERT原子finalizeでない")
    finally:
        schema.close()
    # 物理保護が欠落した mutation はここで十分検出済み。壊れた schema 上の後続DMLで
    # 無関係な例外を漏らさず、gate fault として安定して返す。
    if bad:
        return bad

    # confirmed/rejected/unknown、provider ID 有無、read/write の正常系。
    for effect, result, provider_id, sequence in [
        ("write", "confirmed", "provider-1", 1),
        ("write", "rejected", None, 1),
        ("read", "unknown", None, 1),
    ]:
        c = _external_io_fixture(ddl)
        try:
            _insert_external_operation(c, effect=effect, request_sequence=sequence)
            c.commit()
            _send_external_operation(c)
            c.commit()
            if provider_id is not None:
                c.execute("UPDATE external_operations SET external_operation_id=?,"
                          " remote_object_id='remote-1', response_hash=? WHERE id=1",
                          (provider_id, "c" * 64))
            _insert_operation_log(c, provider_id=provider_id, result=result)
            c.commit()
            state = c.execute(
                "SELECT status,evidence_id,confirmed_at FROM external_operations WHERE id=1"
            ).fetchone()
            links = c.execute(
                "SELECT count(*) FROM external_operations AS op JOIN evidence AS ev "
                "ON op.evidence_id=ev.id AND ev.external_operation_row_id=op.id WHERE op.id=1"
            ).fetchone()[0]
            if tuple(state) != (result, 1, _IO_CONFIRMED_AT) or links != 1:
                bad.append(f"原子finalize不成立:{effect}/{result}/{tuple(state)}/{links}")
        except sqlite3.Error as e:
            bad.append(f"正常外部I/Oが拒否:{effect}/{result}:{e}")
        finally:
            c.close()

    # provider ID は外部行に存在しても evidence/payload では任意。記録した場合だけ一致させる。
    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c)
        _send_external_operation(c)
        c.execute("UPDATE external_operations SET external_operation_id='provider-1' WHERE id=1")
        _insert_operation_log(c, provider_id=None)
        state = tuple(c.execute(
            "SELECT status,evidence_id FROM external_operations WHERE id=1").fetchone())
        evidence = tuple(c.execute(
            "SELECT external_operation_id,json_type(payload_json,'$.provider_operation_id') "
            "FROM evidence WHERE id=1").fetchone())
        if state != ("confirmed", 1) or evidence != (None, None):
            bad.append(f"provider ID省略のfinal束縛不成立:{state}/{evidence}")
    except sqlite3.Error as e:
        bad.append(f"provider ID任意の正常系が拒否:{e}")
    finally:
        c.close()

    # 全write policy分類（paidは後段の原子charge検査）が同じwrite状態機械を共有する。
    for policy in ("review_sync", "approval_notification"):
        c = _external_io_fixture(ddl)
        try:
            _insert_external_operation(c, policy_category=policy, rate_scope=policy)
            _send_external_operation(c)
            _insert_operation_log(c)
        except sqlite3.Error as e:
            bad.append(f"write policy正常系が拒否:{policy}:{e}")
        finally:
            c.close()

    # 同一 task/request の反復 read は1始まり、直前final後だけMAX+1。gap/reuse/sent迂回を拒否。
    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c, operation_id=1, effect="read", request_sequence=1)
        _send_external_operation(c, 1)
        _insert_operation_log(c, evidence_id=1, operation_id=1, result="confirmed")
        _insert_external_operation(c, operation_id=2, effect="read", request_sequence=2)
        keys = [row[0] for row in c.execute(
            "SELECT correlation_key FROM external_operations ORDER BY request_sequence")]
        expected_keys = [f"read:1:{_IO_REQUEST_HASH}:1", f"read:1:{_IO_REQUEST_HASH}:2"]
        if keys != expected_keys:
            bad.append(f"read correlation key非決定的:{keys}")
        try:
            _insert_external_operation(c, operation_id=3, effect="read", request_sequence=1)
            bad.append("同一read request_sequence重複が通過")
        except sqlite3.IntegrityError:
            pass
    except sqlite3.Error as e:
        bad.append(f"read sequence 1/2が拒否:{e}")
    finally:
        c.close()

    for label, action in [
        ("read初回sequence 2",
         lambda c: _insert_external_operation(c, effect="read", request_sequence=2)),
        ("read未確定前回からsequence前進",
         lambda c: (_insert_external_operation(c, effect="read", request_sequence=1),
                    _insert_external_operation(c, operation_id=2, effect="read",
                                               request_sequence=2))),
        ("read sent timeoutから別rowへ前進",
         lambda c: (_insert_external_operation(
             c, effect="read", request_sequence=1, prepared_at="2026-08-09T00:00:00Z"),
                    _send_external_operation(c, sent_at="2026-08-09T00:00:01Z"),
                    _insert_external_operation(c, operation_id=2, effect="read",
                                               request_sequence=2))),
        ("write sequence 2",
         lambda c: _insert_external_operation(c, request_sequence=2)),
    ]:
        c = _external_io_fixture(ddl)
        try:
            try:
                action(c)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
        finally:
            c.close()

    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c, effect="read", request_sequence=1)
        _send_external_operation(c)
        _insert_operation_log(c)
        try:
            _insert_external_operation(c, operation_id=2, effect="read", request_sequence=3)
            bad.append("read sequence gapが通過")
        except sqlite3.IntegrityError:
            pass
    finally:
        c.close()

    # mock/dry-run/pre-call 拒否は業務 DB に一切残さない。
    for mode in ("mock", "dry_run", "pre_call_rejected"):
        c = _external_io_fixture(ddl)
        try:
            try:
                _insert_external_operation(c, execution_mode=mode)
                bad.append(f"非actual外部行が通過:{mode}")
            except sqlite3.IntegrityError:
                pass
            counts = tuple(c.execute(
                "SELECT (SELECT count(*) FROM external_operations),"
                " (SELECT count(*) FROM evidence WHERE kind='operation_log')").fetchone())
            if counts != (0, 0):
                bad.append(f"{mode}がDB証跡を残した:{counts}")
        finally:
            c.close()

    rejection_cases = [
        ("write idempotency欠落",
         lambda c: _insert_external_operation(c, idempotency_key=None,
                                               correlation_key="not-idempotent")),
        ("read correlation不正",
         lambda c: _insert_external_operation(c, effect="read", correlation_key="random")),
        ("read idempotency混入",
         lambda c: _insert_external_operation(c, effect="read", idempotency_key="bad")),
        ("effect不正",
         lambda c: _insert_external_operation(c, effect="network")),
        ("policy閉集合外",
         lambda c: _insert_external_operation(c, policy_category="paid")),
        ("policy/effect不一致",
         lambda c: _insert_external_operation(c, effect="read",
                                              policy_category="content_publish")),
        ("write rate_scope NULL",
         lambda c: _insert_external_operation(c, rate_scope=None)),
        ("read rate_scope非NULL",
         lambda c: _insert_external_operation(c, effect="read", rate_scope="external_read")),
        ("rate_scope大文字",
         lambda c: _insert_external_operation(c, rate_scope="Content_Publish")),
        ("rate_scope alias",
         lambda c: _insert_external_operation(c, rate_scope="content-publish")),
        ("rate_scope空",
         lambda c: _insert_external_operation(c, rate_scope="")),
        ("request hash大文字",
         lambda c: _insert_external_operation(c, request_hash="B" * 64)),
        ("request hash非hex",
         lambda c: _insert_external_operation(c, request_hash="z" * 64)),
        ("prepared_at非canonical",
         lambda c: _insert_external_operation(c, prepared_at="2026-08-10 00:00:01")),
        ("prepared_at暦時刻不正",
         lambda c: _insert_external_operation(c, prepared_at="2026-01-01T24:00:00Z")),
        ("prepared以外の直接INSERT",
         lambda c: _insert_external_operation(c, status="confirmed")),
        ("束縛列変更",
         lambda c: (_insert_external_operation(c),
                    c.execute("UPDATE external_operations SET request_sequence=2 WHERE id=1"))),
        ("policy束縛変更",
         lambda c: (_insert_external_operation(c), c.execute(
             "UPDATE external_operations SET policy_category='review_sync' WHERE id=1"))),
        ("rate_scope束縛変更",
         lambda c: (_insert_external_operation(c), c.execute(
             "UPDATE external_operations SET rate_scope='review_sync' WHERE id=1"))),
        ("prepared中のresult metadata記録",
         lambda c: (_insert_external_operation(c), c.execute(
             "UPDATE external_operations SET external_operation_id='provider-1' WHERE id=1"))),
        ("preparedからfinalへ直行",
         lambda c: (_insert_external_operation(c), c.execute(
             "UPDATE external_operations SET status='confirmed',confirmed_at='t3' WHERE id=1"))),
        ("sentからpreparedへ逆行",
         lambda c: (_insert_external_operation(c), _send_external_operation(c), c.execute(
             "UPDATE external_operations SET status='prepared',sent_at=NULL WHERE id=1"))),
        ("sent_at非canonical",
         lambda c: (_insert_external_operation(c),
                    _send_external_operation(c, sent_at="2026-08-10 00:00:02"))),
        ("sent_at暦日不正",
         lambda c: (_insert_external_operation(c),
                    _send_external_operation(c, sent_at="2026-08-32T00:00:02Z"))),
        ("sent_at時系列逆行",
         lambda c: (_insert_external_operation(c),
                    _send_external_operation(c, sent_at="2026-08-09T23:59:59Z"))),
        ("sent_at cap窓付替え",
         lambda c: (_insert_external_operation(c), _send_external_operation(c), c.execute(
             "UPDATE external_operations SET sent_at='2026-08-09T00:00:00Z' WHERE id=1"))),
        ("confirmed_at非canonical",
         lambda c: (_insert_external_operation(c), _send_external_operation(c),
                    _insert_operation_log(c, created_at="2026-08-10 00:00:03"))),
        ("operation_log created_at暦時刻不正",
         lambda c: (_insert_external_operation(c), _send_external_operation(c),
                    _insert_operation_log(c, created_at="2026-08-10T24:00:00Z"))),
        ("response hash大文字",
         lambda c: (_insert_external_operation(c), _send_external_operation(c), c.execute(
             "UPDATE external_operations SET response_hash=? WHERE id=1", ("C" * 64,)))),
        ("response hash非hex",
         lambda c: (_insert_external_operation(c), _send_external_operation(c), c.execute(
             "UPDATE external_operations SET response_hash=? WHERE id=1", ("z" * 64,)))),
        ("sent writeの別idempotency再送",
         lambda c: (_insert_external_operation(c), _send_external_operation(c),
                    _insert_external_operation(c, operation_id=2, idempotency_key="write-key-2"))),
        ("証跡なしfinal",
         lambda c: (_insert_external_operation(c), _send_external_operation(c), c.execute(
             "UPDATE external_operations SET status='unknown',confirmed_at='t3' WHERE id=1"))),
        ("sent前operation_log",
         lambda c: (_insert_external_operation(c), _insert_operation_log(c))),
    ]
    for label, action in rejection_cases:
        c = _external_io_fixture(ddl)
        try:
            try:
                action(c)
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
            except sqlite3.Error as e:
                bad.append(f"{label}検査不能:{e}")
        finally:
            c.close()

    # sent 中の各結果メタデータは NULL→値の一度だけ。上書きも NULL 戻しも不可。
    for column, initial, replacement in [
        ("external_operation_id", "provider-1", "provider-2"),
        ("external_operation_id", "provider-1", None),
        ("remote_object_id", "remote-1", "remote-2"),
        ("remote_object_id", "remote-1", None),
        ("response_hash", "c" * 64, "d" * 64),
        ("response_hash", "c" * 64, None),
    ]:
        c = _external_io_fixture(ddl)
        try:
            _insert_external_operation(c)
            _send_external_operation(c)
            c.execute(f"UPDATE external_operations SET {column}=? WHERE id=1", (initial,))
            try:
                c.execute(f"UPDATE external_operations SET {column}=? WHERE id=1", (replacement,))
                bad.append(f"sent metadata再変更が通過:{column}/{replacement}")
            except sqlite3.IntegrityError:
                pass
            current = c.execute(f"SELECT {column} FROM external_operations WHERE id=1").fetchone()[0]
            if current != initial:
                bad.append(f"sent metadata拒否後に値が変化:{column}/{current}")
        except sqlite3.Error as e:
            bad.append(f"sent metadata write-once検査不能:{e}")
        finally:
            c.close()

    # operation_log の孤児・全束縛不一致・不正 result は INSERT 文全体を rollback する。
    mismatch_cases: list[tuple[str, dict]] = [
        ("task不一致", {"task_id": 2}),
        ("value不一致", {"value": "external-operation:999"}),
        ("effect不一致", {"payload_overrides": {"effect": "read"}}),
        ("policy不一致", {"payload_overrides": {"policy_category": "review_sync"}}),
        ("rate_scope不一致", {"payload_overrides": {"rate_scope": "other_scope"}}),
        ("rate_scope key欠落", {"omit_payload_keys": ("rate_scope",)}),
        ("service不一致", {"payload_overrides": {"service": "other"}}),
        ("operation不一致", {"payload_overrides": {"operation": "other"}}),
        ("correlation不一致", {"payload_overrides": {"correlation_key": "other"}}),
        ("request hash不一致", {"payload_overrides": {"request_hash": "d" * 64}}),
        ("request sequence不一致", {"payload_overrides": {"request_sequence": 2}}),
        ("result不正", {"result": "success"}),
    ]
    for label, kwargs in mismatch_cases:
        c = _external_io_fixture(ddl)
        try:
            _insert_external_operation(c)
            _send_external_operation(c)
            c.commit()
            try:
                _insert_operation_log(c, **kwargs)
                bad.append(f"operation_log {label}が通過")
            except sqlite3.IntegrityError:
                pass
            op = tuple(c.execute(
                "SELECT status,evidence_id FROM external_operations WHERE id=1").fetchone())
            ev_count = c.execute("SELECT count(*) FROM evidence").fetchone()[0]
            if op != ("sent", None) or ev_count != 0:
                bad.append(f"operation_log {label}拒否が非原子的:{op}/{ev_count}")
        finally:
            c.close()

    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c)
        _send_external_operation(c)
        c.execute("UPDATE external_operations SET external_operation_id='provider-1' WHERE id=1")
        c.commit()
        try:
            _insert_operation_log(c, provider_id="provider-2")
            bad.append("operation_log provider ID不一致が通過")
        except sqlite3.IntegrityError:
            pass
        op = tuple(c.execute(
            "SELECT status,evidence_id FROM external_operations WHERE id=1").fetchone())
        if op != ("sent", None) or c.execute("SELECT count(*) FROM evidence").fetchone()[0]:
            bad.append("provider ID不一致拒否が非原子的")
    finally:
        c.close()

    c = _external_io_fixture(ddl)
    try:
        payload = json.dumps({
            "external_operation_row_id": 999, "effect": "read",
            "policy_category": "external_read", "rate_scope": None, "service": "provider",
            "operation": "poll", "correlation_key": "read:1:x:1", "request_hash": "b" * 64,
            "request_sequence": 1, "result": "unknown",
        })
        try:
            c.execute("INSERT INTO evidence "
                      "(id,task_id,kind,value,payload_json,external_operation_row_id,created_at) "
                      "VALUES (1,1,'operation_log','external-operation:999',?,999,?)",
                      (payload, _IO_CONFIRMED_AT))
            bad.append("孤児operation_logが通過")
        except sqlite3.IntegrityError:
            pass
        if c.execute("SELECT count(*) FROM evidence").fetchone()[0] != 0:
            bad.append("孤児operation_log拒否後にevidenceが残存")
    finally:
        c.close()

    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c)
        try:
            c.execute("INSERT INTO evidence "
                      "(id,task_id,kind,value,payload_json,external_operation_row_id,created_at) "
                      "VALUES (1,1,'file_hash','hash','{}',1,?)", (_IO_CONFIRMED_AT,))
            bad.append("operation_log以外がexternal_operation_row_idを占有")
        except sqlite3.IntegrityError:
            pass
        if c.execute("SELECT count(*) FROM evidence").fetchone()[0] != 0:
            bad.append("非operation_logの外部行束縛拒否後にevidenceが残存")
    finally:
        c.close()

    # 成功 INSERT は即 final。重複、final 後の更新・削除は拒否し初回束縛を保持する。
    c = _external_io_fixture(ddl)
    try:
        _insert_external_operation(c)
        _send_external_operation(c)
        _insert_operation_log(c)
        c.commit()
        for label, action in [
            ("同一外部行への重複operation_log",
             lambda: _insert_operation_log(c, evidence_id=2)),
            ("final外部行更新",
             lambda: c.execute(
                 "UPDATE external_operations SET confirmed_at='2026-08-10T00:00:04Z' WHERE id=1")),
            ("final外部行削除",
             lambda: c.execute("DELETE FROM external_operations WHERE id=1")),
            ("operation_log更新",
             lambda: c.execute("UPDATE evidence SET payload_json='{}' WHERE id=1")),
            ("operation_log削除",
             lambda: c.execute("DELETE FROM evidence WHERE id=1")),
        ]:
            try:
                action()
                bad.append(f"{label}が通過")
            except sqlite3.IntegrityError:
                pass
        state = tuple(c.execute(
            "SELECT status,evidence_id,confirmed_at FROM external_operations WHERE id=1").fetchone())
        evidence = c.execute(
            "SELECT external_operation_row_id,json_extract(payload_json,'$.result') "
            "FROM evidence WHERE id=1").fetchone()
        if state != ("confirmed", 1, _IO_CONFIRMED_AT) or tuple(evidence or ()) != (1, "confirmed"):
            bad.append(f"final束縛が拒否後に変化:{state}")
    except sqlite3.Error as e:
        bad.append(f"final不変/重複検査不能:{e}")
    finally:
        c.close()

    # operation_log は相互 FK でも DELETE を防げるが、未参照 evidence も append-only である。
    c = _external_io_fixture(ddl)
    try:
        c.execute("INSERT INTO evidence "
                  "(id,task_id,kind,value,payload_json,file_path,file_hash,created_at) "
                  "VALUES (99,1,'file_hash','file','{}','artifact','" + "f" * 64 + "','t')")
        c.commit()
        try:
            c.execute("DELETE FROM evidence WHERE id=99")
            bad.append("evidence削除が通過")
        except sqlite3.IntegrityError:
            pass
        if c.execute("SELECT count(*) FROM evidence WHERE id=99").fetchone()[0] != 1:
            bad.append("evidence削除拒否後に行が消失")
    finally:
        c.close()
    bad.extend(_detect_published_spend_faults(ddl))
    return bad


# ---------------------------------------------------------------- 物理数の主張（PO 指示 §3）
# 「25 テーブル」「保護トリガ 37 本」のような**物理数の主張**は、散文の記憶ではなく実 DDL から
# 導出した数と突合する。部分集合を語る主張（特定テーブルに限定した本数）は、その文脈に現れる
# テーブル名から**期待値を計算**して突合する（総数へ丸めない — 部分集合の主張も検証対象）。
# 「トリガ 11」「トリガーは 11 本」「11 基のトリガ」のような表記ゆれも物理数の主張として拾う
# （単位語・助詞の有無や語順に依らない — 独立レビュー R2-03）
TRIGGER_CLAIM = re.compile(r"トリガー?\s*(?:は|が|を|の|＝|=|:|：)?\s*(\d+)")
# 前置形は**単位語を必須**にする（`§2 の保護トリガ`・`3.2 トリガ` のような節番号を数と読まない）
TRIGGER_CLAIM_PRE = re.compile(
    r"(?<![A-Za-z0-9-.§])(\d+)\s*(?:本|件|個|基)\s*(?:の|もの)?\s*(?:保護|整合|append-only)?トリガー?")
# 「S0 テーブル」「SCM-01 テーブル」のような識別子の一部を数値と読まない
TABLE_CLAIM = re.compile(r"(?<![A-Za-z0-9-])(\d+)\s*テーブル")
# 部分集合の記述（「戦略正本 2 テーブル」等）と総数の主張を混同しないための閾値。
# 総数（25）は 2 桁であり、1 桁の主張は総数を名乗っていない
TABLE_TOTAL_MIN = 10
# 監査記録・承認ログは「その時点の事実」を保存する履歴であり、現在の物理数へ追随させない
HISTORICAL_PREFIXES = ("docs/00-authority/audits/", "docs/00-authority/approvals/",
                       "docs/00-authority/superseded/")
SEGMENT_SPLIT = re.compile(r"[。\n]|(?<=\|)")


def ddl_physical(ddl: str) -> tuple[set[str], dict[str, str]]:
    """実 DDL のテーブル集合と、トリガ名 → 対象テーブル名の写像を返す。"""
    con = _apply(ddl)
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    trg = {r[0]: r[1] for r in con.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='trigger'")}
    con.close()
    return tables, trg


def _texts(root: Path = ROOT) -> list[tuple[str, str]]:
    """検査対象の (出所, テキスト) を集める（現役 MD・契約 JSON・テスト関数名）。"""
    out: list[tuple[str, str]] = []
    for p in live_markdown():
        out.append((rel(p), p.read_text(encoding="utf-8")))
    for p in sorted(root.glob("docs/L*/**/*.json")):
        if is_frozen(p):
            continue
        text = p.read_text(encoding="utf-8")
        if p.name == "s0.1-worksets.json":
            # ut_nodeid_renames[].from は、親commitの旧nodeidを失わず監査するための
            # append-only履歴であり「現行物理数の主張」ではない。rename自体の妥当性・
            # 1対1・数値以外同一・親実在は G-WORKSET-RATCHET が別に強制する。
            try:
                worksets = json.loads(text)
                for rename in worksets.get("ut_nodeid_renames", []):
                    if isinstance(rename, dict):
                        rename.pop("from", None)
                text = json.dumps(worksets, ensure_ascii=False)
            except (json.JSONDecodeError, AttributeError):
                pass  # 壊れたJSONはG-JSON/G-WORKSET-SCHEMAがfail-closeする
        out.append((rel(p), text))
    for p in sorted(root.glob("tests/**/*.py")):
        for m in re.finditer(r"^def (test_\w+)", p.read_text(encoding="utf-8"), re.M):
            out.append((f"{rel(p)}::{m.group(1)}", m.group(1)))
    return out


TEST_NAME_CLAIM = re.compile(r"_(\d+)_tables?_(?:and_)?(\d+)_triggers?")


def detect_physical_count_faults(ddl: str, root: Path = ROOT) -> list[str]:
    """散文・契約・テスト名の物理数（テーブル数・トリガ数）を実 DDL と突合する。

    期待値は定数ではなく**実 DDL から導出**する。数値で書いてよいのは**総数**だけとし、
    部分集合（特定テーブルに限った本数）は数値で書かない — 長い文の中の数値がどの範囲を
    指すのかは機械にも人にも決まらず、実物との乖離が検出できないまま残るため。
    """
    tables, trg_table = ddl_physical(ddl)
    n_tab, n_trg = len(tables), len(trg_table)
    bad: list[str] = []
    for origin, text in _texts(root):
        if origin.startswith(HISTORICAL_PREFIXES):
            continue
        for m in TEST_NAME_CLAIM.finditer(text):
            if (int(m.group(1)), int(m.group(2))) != (n_tab, n_trg):
                bad.append(f"{origin}: テスト名の物理数 {m.group(1)}テーブル/{m.group(2)}トリガ "
                           f"が実 DDL（{n_tab}/{n_trg}）と不一致")
        for seg in SEGMENT_SPLIT.split(text):
            if not seg or ("トリガ" not in seg and "テーブル" not in seg):
                continue
            for pat in (TRIGGER_CLAIM, TRIGGER_CLAIM_PRE):
                for m in pat.finditer(seg):
                    if int(m.group(1)) != n_trg:
                        bad.append(f"{origin}: トリガ数の主張 {m.group(1)} が実 DDL の {n_trg} と不一致"
                                   f"（部分集合は数値で書かない — 総数だけを数値で持つ）: "
                                   f"{seg.strip()[:70]}")
            for m in TABLE_CLAIM.finditer(seg):
                n = int(m.group(1))
                if n >= TABLE_TOTAL_MIN and n != n_tab:
                    bad.append(f"{origin}: テーブル総数の主張 {n} が実 DDL の {n_tab} と不一致: "
                               f"{seg.strip()[:70]}")
    return sorted(set(bad))


def detect_unknown_tables(dus: list[dict], tables: set[str]) -> list[str]:
    """DU の db_read/db_write に DDL 非実在テーブルが含まれる箇所を列挙する。"""
    return sorted({f"{d['id']}:{t}" for d in dus for t in d["db_read"] + d["db_write"]
                   if t.split("（")[0] not in tables})


def extract_primary_ddl(contract_text: str) -> str:
    """s0-contract の最初の SQL fence（DDL 正本ブロック）だけを抽出する。

    後続節の計測 SQL 例まで連結すると、DDL が同一でも G-DDL-SYNC が偽陽性になる。
    """
    match = re.search(r"^```sql[ \t]*\n(.*?)^```[ \t]*$", contract_text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _ddl(ctx)
    _transitions(ctx)
    _brief_db(ctx)
    _components(ctx)
    _design_substance(ctx)


def _ddl(ctx: Ctx) -> None:
    md_sql = extract_primary_ddl(S0_CONTRACT.read_text(encoding="utf-8"))

    def norm(s: str) -> list[str]:
        return [ln.rstrip() for ln in s.splitlines() if ln.rstrip() and not ln.startswith("```")]

    gate("G-DDL-SYNC", norm(md_sql) == norm(ctx.ddl), "ddl.sql == s0-contract の DDL ブロック")

    external_faults = detect_external_operation_evidence_faults(ctx.ddl)
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(ctx.ddl)
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        integ = con.execute("PRAGMA integrity_check").fetchone()[0]
        ntab = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        ntrg = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
        gate("G-DDL-APPLY",
             not fk and integ == "ok" and ntab == EXPECTED_TABLES and
             ntrg == EXPECTED_TRIGGERS and not external_faults,
             f"DDL 適用 (fk={fk}, integrity={integ}, tables={ntab}/{EXPECTED_TABLES}, "
             f"triggers={ntrg}/{EXPECTED_TRIGGERS}, external_io={external_faults[:3]})")
    except sqlite3.Error as e:
        gate("G-DDL-APPLY", False, f"DDL 適用失敗: {e}")
    finally:
        con.close()

    phys = detect_physical_count_faults(ctx.ddl)
    gate("G-DESIGN-PHYSICAL-COUNT", not phys,
         "現役文書・契約 JSON・テスト名の物理数（テーブル数・トリガ数）が**実 DDL から導出した数**と"
         f"一致（部分集合の本数を数値で書かない） (違反={phys[:3]})")

    playbook_faults = detect_playbook_version_faults(ctx.ddl)
    gate("G-PLAYBOOK-VERSION", not playbook_faults,
         "playbook修復はbroken版ごとに1 task、版連鎖・atomic rollback・旧版不変をDBで強制 "
         f"(違反={playbook_faults[:3]})")

    kind_items = load(EVIDENCE_KINDS)["items"]
    kinds = {k["kind"] for k in kind_items}
    operation_log_faults = detect_operation_log_kind_faults(kind_items)
    m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)", ctx.ddl)
    dk = set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()
    gate("G-EVK", kinds == dk and len(kinds) == 10 and not operation_log_faults,
         f"evidence kind 10 種一致・operation_log双方向束縛契約 "
         f"(差分={sorted(kinds ^ dk)}, 違反={operation_log_faults[:3]})")


def _transitions(ctx: Ctx) -> None:
    titems = ctx.transitions
    ents = {t["entity"] for t in titems}
    gate("G-TRN-ENT", ents == {"loop_runs", "tasks"}, f"遷移 entity = loop_runs/tasks ({ents})")
    def _states(pattern: str) -> set[str]:
        """DDL の CHECK 句から状態語彙を抜く（見つからなければ空集合 = fail-close 側）。"""
        m = re.search(pattern, ctx.ddl)
        return set(re.findall(r"'(\w+)'", m.group(1))) if m else set()

    enum = {
        "loop_runs": _states(
            r"loop_runs[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)"),
        "tasks": _states(
            r"CREATE TABLE tasks[\s\S]*?state TEXT NOT NULL CHECK \(state IN \(([^)]*)\)"),
    }
    badst = [f"{t['entity']}:{s}" for t in titems for s in (t.get("from"), t.get("to"))
             if s and s not in enum[t["entity"]]]
    gate("G-TRN-ST", not badst, f"遷移状態が DDL enum 内・複合表記なし (不明={badst})")

    keys = [(t["entity"], t["from"], t["event"]) for t in titems]
    dupkeys = sorted({k for k in keys if keys.count(k) > 1})
    gate("G-TRN-UNIQ", not dupkeys, f"(entity, from, event) が一意 (重複={dupkeys})")

    unreach = []
    for e, states in enum.items():
        edges: dict[str, set] = {}
        for t in titems:
            if t["entity"] == e:
                edges.setdefault(t["from"], set()).add(t["to"])
        seen = set(INITIAL[e])
        stack = list(INITIAL[e])
        while stack:
            for nxt in edges.get(stack.pop(), set()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        unreach += [f"{e}:{s}" for s in sorted(states - seen)]
    gate("G-TRN-REACH", not unreach, f"enum の全状態が初期状態から BFS 到達可能 (到達不能={unreach})")
    fromterm = [f"{t['entity']}:{t['from']}" for t in titems if t["from"] in TERMINAL[t["entity"]]]
    gate("G-TRN-TERM", not fromterm, f"終端状態からの遷移なし (違反={fromterm})")
    noguard = [f"{t['entity']}:{t['from']}:{t['event']}" for t in titems
               if not (t.get("guard") or "").strip()]
    gate("G-TRN-GUARD", not noguard, f"全遷移に非空ガード (欠落={noguard})")

    up = load(UPDATES)
    uitems = up.get("items") or up.get("updates")
    fnids = [f for u in uitems for f in u["fn_ids"]]
    gate("G-S0-CNT", len(fnids) == 25 and len(set(fnids)) == 25, "S0 fn_ids=25・重複なし")
    gate("G-S0-SET", set(fnids) == ctx.s0_fn,
         f"fn_ids == slice S0 集合 (差分={sorted(set(fnids) ^ ctx.s0_fn)})")

    tr = load(TRACE)
    rows = tr.get("items") or tr.get("rows")
    allbr = {i["id"] for i in ctx.br}
    trbr = {x.get("br") or x.get("BR") for x in rows}
    gate("G-TRC-BR", trbr == allbr,
         f"trace が現役 BR 全件をカバー (行={len(rows)}, 欠落={sorted(allbr - trbr)})")


def _brief_db(ctx: Ctx) -> None:
    """PO 指示 §5: brief 状態遷移・valid_until・TLP 空配列判定を DB で強制する。"""
    tf = detect_brief_transition_faults(ctx.ddl)
    gate("G-BRIEF-TRANSITION", not tf,
         "brief 状態遷移を DDL トリガで固定（draft→active／active→superseded|retired のみ通過、"
         f"superseded/retired からの復帰・draft 逆行は実 DML で ABORT） (違反={tf[:4]})")

    vf = detect_valid_until_faults(ctx.ddl)
    gate("G-BRIEF-VALID-UNTIL", not vf,
         f"valid_until の延長（後ろ倒し・NULL 化）を拒否し短縮のみ許可（延長は新版発行） (違反={vf[:4]})")

    jf = detect_tlp_json_predicate_faults(ctx.ddl)
    gate("G-TLP-JSON-PREDICATE", not jf,
         f"TLP の空配列判定が json_array_length（文字列比較 IS NOT '[]' の不在＋実 DML 実証） (違反={jf[:4]})")


def _components(ctx: Ctx) -> None:
    comps, itcs = ctx.comps, ctx.itcs
    cmpids = [c["id"] for c in comps]
    itcids = [t["id"] for t in itcs]
    gate("G-CMP-CNT", len(comps) == 13, f"CMP=13 (実={len(comps)})")
    gate("G-CMP-UNIQ", len(cmpids) == len(set(cmpids)), "CMP ID 重複ゼロ")
    cfn = [f for c in comps for f in c["fn_ids"]]
    gate("G-CMP-FN", len(cfn) == len(set(cfn)) and set(cfn) == ctx.s0_fn,
         f"CMP が S0 25 FN を重複なく完全被覆 (差分={sorted(set(cfn) ^ ctx.s0_fn)})")
    gate("G-ITC-CNT", len(itcs) == 16, f"ITC=16 (実={len(itcs)})")
    gate("G-ITC-UNIQ", len(itcids) == len(set(itcids)), "ITC ID 重複ゼロ")
    refcmp = {c for t in itcs for c in t["cmp"]}
    gate("G-ITC-CMP", refcmp == set(cmpids),
         f"ITC↔CMP 双方向カバー (不明={sorted(refcmp - set(cmpids))}, 未カバー={sorted(set(cmpids) - refcmp)})")
    rej = [t for t in itcs if t.get("polarity") == "reject"]
    gate("G-ITC-REJ", len(rej) >= 7, f"総合テストの fail-close 拒否系 >=7 (実={len(rej)})")
    badup = [t["id"] for t in itcs if t.get("update") not in ("S0.1", "S0.2", "S0.3")]
    gate("G-ITC-UPD", not badup, f"全 ITC が S0.1〜S0.3 に割当 (未割当={badup})")

    cmpc_schema = load(CMP_SCHEMA)
    m_errs: list[str] = []
    for it in ctx.cmpc:
        m_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(cmpc_schema, it)]
    cmp_ids = {i["id"] for i in comps} | {i["id"] for i in ctx.scm}
    cmpc_ids = {i["id"] for i in ctx.cmpc}
    design_index = {p.name for p in sorted(ROOT.glob("docs/L*/**/*.md"))}
    missing_dd = sorted({dd for it in ctx.cmpc for dd in it["trace"].get("design_doc", [])
                         if Path(dd).name not in design_index})
    gate("G-CMP-INTERFACE", not m_errs and cmpc_ids == cmp_ids and not missing_dd,
         f"CMP/SCM 設計契約: schema 適合＋23 件完全被覆＋独立設計書実在 "
         f"(err={m_errs[:3]}, 差={sorted(cmpc_ids ^ cmp_ids)}, 設計書欠={missing_dd})")


def _design_substance(ctx: Ctx) -> None:
    thin: list[str] = []
    design_docs = [
        L4 / "canonical/external-if/external-if-design_v0.1.md",
        L4 / "canonical/data/db-design_v0.1.md",
        L4 / "canonical/state-machine/state-machine-design_v0.1.md",
        L4 / "canonical/approval/approval-design_v0.1.md",
        L4 / "canonical/brand-isolation/brand-isolation-design_v0.1.md",
        L5 / "canonical/errors/error-taxonomy_v0.1.md",
    ]
    # スライス横断で数える（S0 → S1 への再配置が「分母の縮小」に見えないようにする — ラチェット）。
    # スライス単位の下限も併せて持つ（総数だけだと S0 の設計が消えても通ってしまう）。
    feature_docs = sorted(L6.rglob("*.md"))
    if len(feature_docs) < 14:
        thin.append(f"features 不足:{len(feature_docs)}<14")
    s0_docs = sorted((L6 / "S0").glob("*.md"))
    if len(s0_docs) < 11:
        thin.append(f"S0 features 不足:{len(s0_docs)}<11")
    for p in design_docs + feature_docs:
        txt = p.read_text(encoding="utf-8")
        if txt.count("\n") < 50 or txt.count("## ") < 3:
            thin.append(f"{p.name}:{txt.count(chr(10))}行/{txt.count('## ')}節")
        if p in feature_docs and "trace" not in txt.lower():
            thin.append(f"{p.name}:trace表なし")
    gate("G-DESIGN-SUBSTANCE", not thin, f"設計書の実体（≥50 行・≥3 節・trace） (薄い={thin[:5]})")
    gate("G-BASIC-DESIGN-EXIST", BASIC_DESIGN.exists() and "pair:" in
         BASIC_DESIGN.read_text(encoding="utf-8")[:800],
         "基本設計②がヘッダに pair 宣言を持つ")

    mig = load(MIGRATION_RULES)
    need = {"基本規律", "expand", "backfill", "contract", "rename禁止"}
    names = {r["name"] for r in mig.get("rules", [])}
    thin_rules = [r["name"] for r in mig.get("rules", []) if len(r.get("text", "").strip()) < 30]
    gate("G-MIGRATION-RULES", need <= names and not thin_rules and bool(mig.get("promotion_steps")),
         f"migration 規則が expand/backfill/contract/rename 禁止を実体つきで定義し昇格手順を持つ "
         f"(欠落={sorted(need - names)}, 空={thin_rules})")
