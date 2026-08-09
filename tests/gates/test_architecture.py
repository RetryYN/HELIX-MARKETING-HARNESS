"""architecture ゲートの単体テストと mutation test（DDL は実 DML で検証する）。"""

import sqlite3

import pytest

from tools.gates import architecture
from tools.gates.common import CTX


def test_ddl_applies_with_expected_tables_and_triggers() -> None:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(CTX.ddl)
        tables = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        triggers = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
        assert tables == architecture.EXPECTED_TABLES
        assert triggers == architecture.EXPECTED_TRIGGERS
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        con.close()


def test_primary_ddl_extraction_ignores_later_sql_examples() -> None:
    contract = """# contract
```sql
CREATE TABLE example(id INTEGER);
```
## measurement
```sql
SELECT count(*) FROM example;
```
"""
    assert architecture.extract_primary_ddl(contract) == "CREATE TABLE example(id INTEGER);\n"


def test_brief_transitions_are_enforced_by_ddl() -> None:
    assert architecture.detect_brief_transition_faults(CTX.ddl) == []


def test_mutation_dropping_status_trigger_reopens_backward_transitions() -> None:
    mutated = _drop_trigger(CTX.ddl, "strategic_briefs_status_transition")
    faults = architecture.detect_brief_transition_faults(mutated)
    assert any("逆行が通過" in f for f in faults), "遷移トリガを外しても検出されない"


def test_valid_until_extension_is_rejected() -> None:
    assert architecture.detect_valid_until_faults(CTX.ddl) == []


def test_mutation_dropping_valid_until_trigger_allows_extension() -> None:
    mutated = _drop_trigger(CTX.ddl, "strategic_briefs_valid_until_no_extend")
    faults = architecture.detect_valid_until_faults(mutated)
    assert any("通過" in f for f in faults), "valid_until トリガを外しても検出されない"


def test_tlp_uses_json_array_length_not_string_comparison() -> None:
    assert architecture.detect_tlp_json_predicate_faults(CTX.ddl) == []


def test_mutation_string_comparison_predicate_is_detected() -> None:
    mutated = CTX.ddl.replace(
        "json_array_length(NEW.alternative_explanations_json) != 0",
        "NEW.alternative_explanations_json IS NOT '[]'").replace(
        "json_array_length(NEW.proposed_revision_targets_json) != 0",
        "NEW.proposed_revision_targets_json IS NOT '[]'")
    faults = architecture.detect_tlp_json_predicate_faults(mutated)
    assert any("文字列比較" in f for f in faults)


def test_playbook_versions_and_repair_episode_are_enforced_by_ddl() -> None:
    assert architecture.detect_playbook_version_faults(CTX.ddl) == []


def test_internal_task_types_are_registered_in_l1_canonical_vocabulary() -> None:
    items = architecture.load(architecture.LTW_DIR / "task-types.json")["items"]
    assert architecture.detect_internal_task_type_registry_faults(CTX.ddl, items) == []


def test_mutation_unregistered_internal_task_type_is_detected() -> None:
    items = architecture.load(architecture.LTW_DIR / "task-types.json")["items"]
    mutated = [item for item in items if item["id"] != "spend_correction"]
    faults = architecture.detect_internal_task_type_registry_faults(CTX.ddl, mutated)
    assert any("spend_correction" in fault for fault in faults)


def test_mutation_registry_id_rejected_by_ddl_character_contract_is_detected() -> None:
    items = architecture.load(architecture.LTW_DIR / "task-types.json")["items"]
    mutated = [*items, {"id": "bad task type", "internal": False}]
    faults = architecture.detect_internal_task_type_registry_faults(CTX.ddl, mutated)
    assert any("格納不能" in fault for fault in faults)


def test_canonical_business_task_type_is_accepted_by_workflow_and_task_ddl() -> None:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(CTX.ddl)
        con.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at) "
                    "VALUES (1,'a','p1','author','A','active','t'),"
                    "(2,'v','p2','verifier','V','active','t')")
        con.execute("INSERT INTO workflows (id,workflow_key,name,task_type,version,definition_json,"
                    "required_evidence_json,status,created_at) "
                    "VALUES (1,'WF-WP-1','Plan','T-PLAN',1,'{}','[]','active','t')")
        con.execute("INSERT INTO loop_runs "
                    "(id,loop_kind,loop_type,state,idempotency_key,created_at) "
                    "VALUES (1,'upper','LP-U','running','loop','t')")
        con.execute("INSERT INTO tasks (id,loop_run_id,workflow_id,task_type,author_agent_id,"
                    "verifier_agent_id,state,step_key,idempotency_key,expected_output_kind,"
                    "input_json,created_at) VALUES "
                    "(1,1,1,'T-PLAN',1,2,'pending','plan','task','plan_record','{}','t')")
    finally:
        con.close()


@pytest.mark.parametrize("misspelling", ["spend_correction2", "spend-correction", "SpendCorrection"])
def test_mutation_noncanonical_internal_task_type_spelling_is_detected(misspelling: str) -> None:
    items = architecture.load(architecture.LTW_DIR / "task-types.json")["items"]
    mutated = CTX.ddl.replace("task_type = 'spend_correction'",
                              f"task_type = '{misspelling}'")
    faults = architecture.detect_internal_task_type_registry_faults(mutated, items)
    assert any(misspelling in fault for fault in faults)


def test_external_operation_evidence_one_to_one_is_enforced_by_ddl() -> None:
    """実 DML で actual-only、状態機械、原子finalize、read反復、1:1、不変性を実証する。"""
    assert architecture.detect_external_operation_evidence_faults(CTX.ddl) == []


@pytest.mark.parametrize("trigger", [
    "external_operations_insert_prepared",
    "external_operations_binding_immutable",
    "external_operations_result_sent_only",
    "external_operations_lifecycle",
    "external_operations_final_immutable",
    "external_operations_no_delete",
    "evidence_operation_log_insert",
    "evidence_published_url_insert",
    "spend_ledger_binding_insert",
    "spend_ledger_no_update",
    "spend_ledger_no_delete",
])
def test_mutation_dropping_external_operation_guard_is_detected(trigger: str) -> None:
    mutated = _drop_trigger(CTX.ddl, trigger)
    assert architecture.detect_external_operation_evidence_faults(mutated), trigger


@pytest.mark.parametrize(("before", "after"), [
    ("evidence_id INTEGER UNIQUE", "evidence_id INTEGER"),
    ("operation_log_evidence_id INTEGER UNIQUE", "operation_log_evidence_id INTEGER"),
    ("external_operation_row_id INTEGER UNIQUE", "external_operation_row_id INTEGER"),
    ("reverses_spend_ledger_id INTEGER UNIQUE", "reverses_spend_ledger_id INTEGER"),
    ("  UNIQUE (task_id, effect, operation, request_hash, request_sequence),\n", ""),
])
def test_mutation_dropping_external_operation_unique_is_detected(
        before: str, after: str) -> None:
    assert before in CTX.ddl
    mutated = CTX.ddl.replace(before, after, 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("UNIQUE欠落" in fault for fault in faults), faults


@pytest.mark.parametrize("index", [
    "evidence_operation_log_external_row_one",
    "evidence_published_url_external_row_one",
])
def test_mutation_dropping_external_evidence_partial_unique_is_detected(index: str) -> None:
    marker = f"CREATE UNIQUE INDEX {index}"
    start = CTX.ddl.index(marker)
    end = CTX.ddl.index(";", start) + 2
    mutated = CTX.ddl[:start] + CTX.ddl[end:]
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("一意index欠落" in fault for fault in faults), faults


@pytest.mark.parametrize("foreign_key", [
    "  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,\n",
    "  FOREIGN KEY (external_operation_row_id) REFERENCES external_operations(id) ON DELETE RESTRICT,\n",
    "  FOREIGN KEY (operation_log_evidence_id) REFERENCES evidence(id) ON DELETE RESTRICT,\n",
    "  FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE RESTRICT,\n",
    "  FOREIGN KEY (reverses_spend_ledger_id) REFERENCES spend_ledger(id) ON DELETE RESTRICT,\n",
])
def test_mutation_dropping_external_operation_bidirectional_fk_is_detected(
        foreign_key: str) -> None:
    assert foreign_key in CTX.ddl
    mutated = CTX.ddl.replace(foreign_key, "", 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("FK欠落" in fault for fault in faults), faults


def test_mutation_operation_log_trigger_before_insert_reopens_non_atomic_window() -> None:
    mutated = CTX.ddl.replace(
        "CREATE TRIGGER evidence_operation_log_insert AFTER INSERT ON evidence",
        "CREATE TRIGGER evidence_operation_log_insert BEFORE INSERT ON evidence", 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("AFTER INSERT" in fault or "原子finalize" in fault for fault in faults), faults


@pytest.mark.parametrize("trigger", ["evidence_no_update", "evidence_no_delete"])
def test_mutation_external_operation_log_append_only_trigger_cannot_be_noop(
        trigger: str) -> None:
    """変異: evidence保護trigger名と本数だけを残し、WHEN 0で無効化できない。"""
    marker = f"CREATE TRIGGER {trigger} BEFORE "
    start = CTX.ddl.index(marker)
    begin = CTX.ddl.index("\nBEGIN", start)
    mutated = CTX.ddl[:begin] + "\nWHEN 0" + CTX.ddl[begin:]
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    expected = "operation_log更新" if trigger.endswith("update") else "evidence削除"
    assert any(expected in fault for fault in faults), faults


def test_mutation_non_operation_log_can_never_bind_external_row() -> None:
    check = ("  CHECK ((kind = 'operation_log'\n"
             "          AND external_operation_row_id IS NOT NULL\n"
             "          AND operation_log_evidence_id IS NULL)\n"
             "      OR (kind = 'published_url'\n"
             "          AND external_operation_row_id IS NOT NULL\n"
             "          AND operation_log_evidence_id IS NOT NULL\n"
             "          AND asset_id IS NOT NULL)\n"
             "      OR (kind NOT IN ('operation_log', 'published_url')\n"
             "          AND external_operation_row_id IS NULL\n"
             "          AND operation_log_evidence_id IS NULL)),\n")
    assert check in CTX.ddl
    mutated = CTX.ddl.replace(check, "", 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("operation_log以外" in fault for fault in faults), faults


def test_operation_log_evidence_kind_requires_local_row_and_sequence() -> None:
    assert architecture.detect_operation_log_kind_faults(
        architecture.load(architecture.EVIDENCE_KINDS)["items"]) == []


def test_mutation_operation_log_kind_requiring_provider_id_is_detected() -> None:
    items = architecture.load(architecture.EVIDENCE_KINDS)["items"]
    mutated = [dict(item) for item in items]
    operation_log = next(item for item in mutated if item["kind"] == "operation_log")
    operation_log["required_payload_keys"] = [
        key for key in operation_log["required_payload_keys"]
        if key != "external_operation_row_id"
    ] + ["external_operation_id"]
    faults = architecture.detect_operation_log_kind_faults(mutated)
    assert any("必須payload差分" in fault or "provider ID" in fault for fault in faults)


@pytest.mark.parametrize(("kind", "key"), [
    ("operation_log", "rate_scope"),
    ("published_url", "operation_log_evidence_id"),
    ("published_url", "external_operation_row_id"),
])
def test_mutation_evidence_kind_removing_local_binding_key_is_detected(
        kind: str, key: str) -> None:
    items = architecture.load(architecture.EVIDENCE_KINDS)["items"]
    mutated = [dict(item) for item in items]
    item = next(candidate for candidate in mutated if candidate["kind"] == kind)
    item["required_payload_keys"] = [
        candidate for candidate in item["required_payload_keys"] if candidate != key]
    faults = architecture.detect_operation_log_kind_faults(mutated)
    assert any("必須payload差分" in fault for fault in faults), faults


def test_mutation_paid_operation_kind_removing_accounting_key_is_detected() -> None:
    items = architecture.load(architecture.EVIDENCE_KINDS)["items"]
    mutated = [dict(item) for item in items]
    operation_log = next(item for item in mutated if item["kind"] == "operation_log")
    operation_log["conditional_payload_keys"] = {
        "approved_paid_operation": ["approval_id", "currency", "purpose", "occurred_at"]}
    faults = architecture.detect_operation_log_kind_faults(mutated)
    assert any("条件payload差分" in fault for fault in faults), faults


@pytest.mark.parametrize(("before", "after", "expected"), [
    ("COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', prepared_at, '+0 seconds') = prepared_at, 0)",
     "1", "prepared_at暦時刻不正"),
    ("COALESCE(strftime('%Y-%m-%dT%H:%M:%SZ', occurred_at, '+0 seconds') = occurred_at, 0)",
     "1", "occurred_at暦時刻不正"),
])
def test_mutation_weakening_canonical_utc_check_is_detected(
        before: str, after: str, expected: str) -> None:
    assert before in CTX.ddl
    mutated = CTX.ddl.replace(before, after, 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any(expected in fault for fault in faults), faults


def test_mutation_making_provider_id_mandatory_is_detected_by_dml() -> None:
    before = ("AND (NEW.external_operation_id IS NULL\n"
              "           OR NEW.external_operation_id IS op.external_operation_id)")
    after = "AND NEW.external_operation_id IS op.external_operation_id"
    assert before in CTX.ddl
    mutated = CTX.ddl.replace(before, after, 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any("provider ID任意" in fault for fault in faults), faults


@pytest.mark.parametrize(("before", "after", "expected"), [
    ("WHEN NEW.kind = 'published_url'", "WHEN 0 AND NEW.kind = 'published_url'", "published_url"),
    ("WHEN NOT EXISTS (\n    SELECT 1 FROM approvals AS approval",
     "WHEN 0 AND NOT EXISTS (\n    SELECT 1 FROM approvals AS approval",
     "未承認"),
])
def test_mutation_named_binding_trigger_cannot_be_noop(
        before: str, after: str, expected: str) -> None:
    assert before in CTX.ddl
    mutated = CTX.ddl.replace(before, after, 1)
    faults = architecture.detect_external_operation_evidence_faults(mutated)
    assert any(expected in fault for fault in faults), faults


@pytest.mark.parametrize("trigger", [
    "playbook_repair_task_insert",
    "playbook_repair_task_no_retry",
    "playbook_repair_no_verify_retry",
    "playbooks_initial_insert",
    "playbooks_version_insert",
    "playbooks_content_no_update",
    "playbooks_status_transition",
    "playbooks_health_active_only",
    "playbooks_retired_no_update",
    "playbooks_no_delete",
])
def test_mutation_dropping_playbook_guard_is_detected(trigger: str) -> None:
    mutated = _drop_trigger(CTX.ddl, trigger)
    assert architecture.detect_playbook_version_faults(mutated), trigger


@pytest.mark.parametrize("index", ["playbooks_one_current", "playbook_repair_one_per_episode"])
def test_mutation_dropping_playbook_unique_index_is_detected(index: str) -> None:
    marker = f"CREATE UNIQUE INDEX {index}"
    start = CTX.ddl.index(marker)
    end = CTX.ddl.index(";", start) + 2
    mutated = CTX.ddl[:start] + CTX.ddl[end:]
    assert architecture.detect_playbook_version_faults(mutated), index


def test_strategy_canon_is_append_only() -> None:
    ok, msg = architecture.strategy_mutation_rejected(CTX.ddl)
    assert ok, msg


def test_mutation_dropping_append_only_trigger_is_detected() -> None:
    mutated = _drop_trigger(CTX.ddl, "strategic_briefs_no_update")
    ok, msg = architecture.strategy_mutation_rejected(mutated)
    assert not ok, "append-only トリガを外しても拒否実証が通ってしまう"


def test_unknown_table_mutation_is_detected() -> None:
    victim = {**CTX.duc[0], "db_read": [*CTX.duc[0]["db_read"], "ghost_table_xyz"]}
    assert architecture.detect_unknown_tables([victim], CTX.ddl_tables)


def _drop_trigger(ddl: str, name: str) -> str:
    """指定トリガの CREATE 文だけを取り除いた DDL を返す（mutation 用）。"""
    marker = f"CREATE TRIGGER {name}"
    start = ddl.index(marker)
    end = ddl.index("END;", start) + len("END;\n")
    return ddl[:start] + ddl[end:]


def test_drop_trigger_helper_removes_exactly_one_trigger() -> None:
    mutated = _drop_trigger(CTX.ddl, "strategic_briefs_status_transition")
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(mutated)
        n = con.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
        assert n == architecture.EXPECTED_TRIGGERS - 1
    finally:
        con.close()


@pytest.mark.parametrize("src,dst", sorted(architecture.ALLOWED_BRIEF_TRANSITIONS))
def test_allowed_brief_transition_passes(src: str, dst: str) -> None:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(CTX.ddl)
        con.execute(architecture.BRIEF_INSERT, ("SB-T", None, "a" * 64, src))
        con.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = 'SB-T'", (dst,))
        after = con.execute(
            "SELECT status FROM strategic_briefs WHERE brief_key = 'SB-T'").fetchone()[0]
        assert after == dst, f"許可された遷移 {src}→{dst} が反映されていない"
    finally:
        con.close()


@pytest.mark.parametrize("src,dst", architecture.DENIED_BRIEF_TRANSITIONS)
def test_denied_brief_transition_aborts(src: str, dst: str) -> None:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(CTX.ddl)
        con.execute(architecture.BRIEF_INSERT, ("SB-T", None, "a" * 64, src))
        with pytest.raises(sqlite3.IntegrityError, match="status transition"):
            con.execute("UPDATE strategic_briefs SET status = ? WHERE brief_key = 'SB-T'", (dst,))
    finally:
        con.close()


# --- 物理数の主張（PO 指示 §3）の検出能力 ---

def test_physical_counts_are_clean_on_real_tree() -> None:
    assert architecture.detect_physical_count_faults(CTX.ddl) == []


def test_ddl_physical_is_derived_from_real_ddl() -> None:
    """期待値は定数ではなく実 DDL から導出する（定数と DDL の二重管理を作らない）。"""
    tables, trg = architecture.ddl_physical(CTX.ddl)
    assert len(tables) == architecture.EXPECTED_TABLES
    assert len(trg) == architecture.EXPECTED_TRIGGERS
    assert set(trg.values()) <= tables


@pytest.mark.parametrize("claim", ["トリガ 26 本", "トリガ 16 本", "トリガ 14 本", "トリガ 11 本", "保護トリガ 4 本",
                                   "整合トリガ 6 件", "15 本のトリガ", "トリガ 11",
                                   "トリガーは 11 本", "11 基のトリガ", "トリガー 14"])
def test_mutation_stale_trigger_count_is_detected(tmp_path, monkeypatch, claim) -> None:
    """変異: 旧いトリガ本数（11／14／16／26）や部分集合の本数を書くと検出される。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [("dummy.md", claim)])
    faults = architecture.detect_physical_count_faults(CTX.ddl)
    assert any("トリガ数の主張" in f for f in faults), claim


@pytest.mark.parametrize("claim", ["19 テーブル", "24 テーブル", "26 テーブル"])
def test_mutation_stale_table_count_is_detected(tmp_path, monkeypatch, claim) -> None:
    """変異: 総数を名乗るテーブル数が実 DDL とずれると検出される。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [("dummy.md", claim)])
    faults = architecture.detect_physical_count_faults(CTX.ddl)
    assert any("テーブル総数の主張" in f for f in faults), claim


def test_mutation_stale_test_name_count_is_detected(monkeypatch) -> None:
    """変異: テスト関数名に埋め込んだ物理数が実 DDL とずれると検出される。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [
        ("t.py::x", "test_apply_all_empty_db_creates_25_tables_and_14_triggers")])
    faults = architecture.detect_physical_count_faults(CTX.ddl)
    assert any("テスト名の物理数" in f for f in faults)


def test_workset_rename_history_is_not_a_current_physical_count_claim() -> None:
    """rename元は監査履歴であり、現行値はrename先だけを物理数として検査する。"""
    texts = dict(architecture._texts())
    worksets = texts["docs/L6-feature-design/S0/s0.1-worksets.json"]
    assert "test_apply_all_empty_db_creates_25_tables_and_16_triggers" not in worksets
    assert "test_apply_all_empty_db_creates_25_tables_and_37_triggers" in worksets


def test_section_numbers_are_not_read_as_trigger_counts(monkeypatch) -> None:
    """偽陽性回帰: 節番号を本数と誤読せず、正しい本数主張は許可する。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [
        ("d.md", "config への UPDATE/DELETE は §2 の保護トリガが常時拒否する"),
        ("e.md", "### 3.2 トリガ 37 本の意図"),
        ("f.md", "ツール代替（tech-stack §7 トリガー）")])
    assert architecture.detect_physical_count_faults(CTX.ddl) == []


def test_identifier_digits_are_not_read_as_counts(monkeypatch) -> None:
    """偽陽性回帰: 「S0 テーブル」「SCM-01 テーブル」の識別子を数値の主張と読まない。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [
        ("d.md", "S0 テーブル定義の差分なし / SCM-01 テーブルに依存 / 戦略正本 2 テーブル")])
    assert architecture.detect_physical_count_faults(CTX.ddl) == []
