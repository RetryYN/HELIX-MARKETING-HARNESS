"""requirements ゲートの単体テストと mutation test。"""

import copy
import json
import re
import sqlite3

import pytest

from scripts.render_views import _markdown_autolink_urls
from tools.gates import requirements
from tools.gates.common import CTX


def _measurement_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(CTX.ddl)
    con.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
                " VALUES (1,'a','p1','author','A','active','t')")
    con.execute("INSERT INTO agents (id,agent_key,principal,role,display_name,status,created_at)"
                " VALUES (2,'v','p2','verifier','V','active','t')")
    con.execute("INSERT INTO workflows (id,workflow_key,name,task_type,version,definition_json,"
                " required_evidence_json,status,created_at)"
                " VALUES (1,'wf','WF','measure',1,'{}','[]','active','t')")
    con.execute("INSERT INTO loop_runs (id,loop_kind,loop_type,state,idempotency_key,created_at)"
                " VALUES (1,'upper','LP-U','running','loop','t')")
    con.execute("INSERT INTO tasks (id,loop_run_id,workflow_id,task_type,author_agent_id,"
                " verifier_agent_id,state,step_key,idempotency_key,expected_output_kind,input_json,created_at)"
                " VALUES (1,1,1,'measure',1,2,'in_progress','measure','task','measurement','{}','t')")
    return con


def _nfr_sql(nfr_id: str, index: int = 0) -> str:
    method = next(x["measurement_method"] for x in CTX.nfc if x["id"] == nfr_id)
    return re.findall(r"SQL:`([^`]+)`", method)[index]


def _nfr_sql_containing(nfr_id: str, needle: str) -> str:
    method = next(x["measurement_method"] for x in CTX.nfc if x["id"] == nfr_id)
    return next(sql for sql in re.findall(r"SQL:`([^`]+)`", method) if needle in sql)


def _insert_approval(con: sqlite3.Connection, approval_id: int, task_id: int = 1) -> None:
    con.execute(
        "INSERT INTO approvals (id,task_id,requested_by_agent_id,channel,binding_subject,"
        "binding_operation,binding_at,decision,decided_at,created_at) "
        "VALUES (?,?,1,'discord',?,?,?,'approved',?,?)",
        (approval_id, task_id, f"subject-{approval_id}", f"operation-{approval_id}",
         f"2026-08-{approval_id:02d}T00:00:00Z", f"2026-08-{approval_id:02d}T00:00:01Z",
         f"2026-08-{approval_id:02d}T00:00:00Z"),
    )


def _insert_sent_external_operation(
        con: sqlite3.Connection, op_id: int, *, effect: str, policy_category: str,
        rate_scope: str | None, sent_at: str, operation: str | None = None) -> dict:
    request_hash = f"{op_id:064x}"
    request_sequence = 1
    idempotency_key = f"op-{op_id}" if effect == "write" else None
    correlation_key = (idempotency_key if effect == "write"
                       else f"read:1:{request_hash}:{request_sequence}")
    operation = operation or f"operation-{op_id}"
    con.execute(
        "INSERT INTO external_operations "
        "(id,task_id,service,operation,effect,policy_category,rate_scope,execution_mode,"
        "target_endpoint,idempotency_key,correlation_key,request_hash,request_sequence,status,"
        "prepared_at) VALUES (?,1,'fixture',?,?,?,?, 'actual','https://fixture.invalid',"
        "?,?,?,?, 'prepared',?)",
        (op_id, operation, effect, policy_category, rate_scope, idempotency_key,
         correlation_key, request_hash, request_sequence, sent_at),
    )
    con.execute(
        "UPDATE external_operations SET status='sent', sent_at=? WHERE id=?",
        (sent_at, op_id),
    )
    return {
        "id": op_id,
        "effect": effect,
        "policy_category": policy_category,
        "rate_scope": rate_scope,
        "service": "fixture",
        "operation": operation,
        "correlation_key": correlation_key,
        "request_hash": request_hash,
        "request_sequence": request_sequence,
    }


def _finalize_external_operation(
        con: sqlite3.Connection, op: dict, *, result: str, created_at: str,
        paid: dict | None = None) -> None:
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
        "provider_operation_id": None,
    }
    if paid:
        payload.update(paid)
    con.execute(
        "INSERT INTO evidence "
        "(id,task_id,kind,value,payload_json,external_operation_row_id,created_at) "
        "VALUES (?,1,'operation_log',?,?,?,?)",
        (1000 + op["id"], f"external-operation:{op['id']}",
         json.dumps(payload, separators=(",", ":")), op["id"], created_at),
    )


def test_polarity_gaps_clean_on_real_contracts() -> None:
    assert requirements.detect_polarity_gaps(CTX.allc, CTX.acc) == []


def test_mutation_removing_reject_ac_is_detected() -> None:
    victim = next(c for c in CTX.allc if c["slice"] == "S0"
                  and any(a["target"] == c["id"] and a["polarity"] == "reject" for a in CTX.acc))
    mutated = [a for a in CTX.acc
               if not (a["target"] == victim["id"] and a["polarity"] == "reject")]
    assert requirements.detect_polarity_gaps([victim], mutated)


def test_invariant_gaps_clean_on_real_contracts() -> None:
    assert requirements.detect_invariant_gaps(CTX.allc, CTX.acc) == []


def test_mutation_invariant_map_pointing_at_normal_ac_is_detected() -> None:
    victim = next(c for c in CTX.allc if c["slice"] == "S0" and c.get("invariant_ac_map"))
    normal = next(a["id"] for a in CTX.acc
                  if a["target"] == victim["id"] and a["polarity"] == "normal")
    mutated = copy.deepcopy(victim)
    mutated["invariant_ac_map"] = [[normal], *mutated["invariant_ac_map"][1:]]
    assert requirements.detect_invariant_gaps([mutated], CTX.acc)


def test_contract_table_faults_clean_on_real_contracts() -> None:
    assert requirements.detect_contract_table_faults(CTX.allc, CTX.ddl_tables, CTX.trn_states) == []


def test_mutation_unknown_table_reference_is_detected() -> None:
    victim = copy.deepcopy(CTX.allc[0])
    victim["tables"] = [*victim["tables"], "r: ghost_table_xyz"]
    faults = requirements.detect_contract_table_faults([victim], CTX.ddl_tables, CTX.trn_states)
    assert any("ghost_table_xyz" in f for f in faults)


def test_mutation_malformed_table_notation_is_detected() -> None:
    victim = copy.deepcopy(CTX.allc[0])
    victim["tables"] = [*victim["tables"], "loop_runs をよしなに読む"]
    assert requirements.detect_contract_table_faults([victim], CTX.ddl_tables, CTX.trn_states)


def test_current_denominators_match_declared_scope() -> None:
    assert requirements.current_denominators(CTX) == {
        "AC_CONTRACT": 237, "TCC": 243, "API": 59, "API_UT": 215}


def test_nfr_verification_chain_is_concrete_and_complete() -> None:
    assert requirements.detect_nfr_verification_faults(CTX.nfc, CTX.acc, CTX.tcc, CTX.ddl) == []


def test_mutation_nfr_prose_tc_and_pseudo_sql_are_detected() -> None:
    nfr = copy.deepcopy(CTX.nfc[0])
    nfr["trace_down"] = {"ac": [], "tc": ["拒否系 TC 群"]}
    nfr["measurement_method"] += " SELECT * FROM loop_runs/tasks WHERE state NOT IN (終端)"
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, CTX.tcc, CTX.ddl)
    assert any("AC未接続" in f for f in faults)
    assert any("未知TCC" in f for f in faults)
    assert any("実行不能な擬似SQL" in f for f in faults)


def test_mutation_nfr_aspect_missing_from_ac_and_tcc_is_detected() -> None:
    nfr = copy.deepcopy(CTX.nfc[0])
    acs = copy.deepcopy(CTX.acc)
    tcs = copy.deepcopy(CTX.tcc)
    victim = nfr["verification_aspects"][0]
    for ac in acs:
        if ac["id"] in nfr["trace_down"]["ac"]:
            ac["verification_aspects"].remove(victim)
    for tc in tcs:
        if tc["id"] in nfr["trace_down"]["tc"]:
            tc["verification_aspects"].remove(victim)
    faults = requirements.detect_nfr_verification_faults([nfr], acs, tcs, CTX.ddl)
    assert any("AC意味被覆差分" in f for f in faults)
    assert any("TCC意味被覆差分" in f for f in faults)


def test_mutation_nfr_aspect_without_executable_assertion_is_detected() -> None:
    nfr = copy.deepcopy(CTX.nfc[0])
    tcs = copy.deepcopy(CTX.tcc)
    victim = nfr["verification_aspects"][0]
    for tc in tcs:
        if tc["id"] in nfr["trace_down"]["tc"]:
            tc["aspect_assertions"].pop(victim)
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, tcs, CTX.ddl)
    assert any("TCC観点assert差分" in f for f in faults)


@pytest.mark.parametrize("bad_sql", [
    "SELECT count(*) FROM ghost_ledger",
    "SELECT ghost_column FROM spend_ledger",
    "SELECT FROM spend_ledger",
    "SELECT count(*) FROM spend_ledger WHERE occurred_at >= <当月初>",
])
def test_mutation_invalid_contract_sql_is_detected(bad_sql: str) -> None:
    nfr = copy.deepcopy(next(x for x in CTX.nfc if x["id"] == "NFR-6"))
    nfr["measurement_method"] = f"SQL:`{bad_sql}`"
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, CTX.tcc, CTX.ddl)
    assert any("契約SQLをprepare不能" in f for f in faults)


def test_mutation_unbound_sql_prose_is_detected() -> None:
    nfr = copy.deepcopy(next(x for x in CTX.nfc if x["id"] == "NFR-6"))
    nfr["measurement_method"] = "SQL: SELECT * FROM spend_ledger"
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, CTX.tcc, CTX.ddl)
    assert any("SQLタグ" in f for f in faults)


def test_mutation_backtick_select_without_sql_tag_is_detected() -> None:
    nfr = copy.deepcopy(next(x for x in CTX.nfc if x["id"] == "NFR-6"))
    nfr["measurement_method"] = "pytestで`SELECT count(*) FROM spend_ledger`を検証する"
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, CTX.tcc, CTX.ddl)
    assert any("SELECT/WITH契約SQL" in f for f in faults)


def test_generated_markdown_autolinks_bare_url_without_polluting_canonical_value() -> None:
    canonical = "config.designsync_source=http://designsync.test、次"
    assert _markdown_autolink_urls(canonical) == (
        "config.designsync_source=<http://designsync.test>、次"
    )
    assert "<" not in canonical


def test_generated_markdown_autolink_does_not_double_wrap_markup_or_code() -> None:
    assert _markdown_autolink_urls(
        "<http://a.test> `http://b.test` [link](http://c.test)"
    ) == (
        "<http://a.test> `http://b.test` [link](http://c.test)"
    )


def test_generated_markdown_autolink_keeps_sentence_punctuation_outside() -> None:
    assert _markdown_autolink_urls("（http://a.test/path）。https://b.test/x.") == (
        "（<http://a.test/path>）。<https://b.test/x>."
    )


def test_generated_markdown_autolink_leaves_fenced_code_unchanged() -> None:
    source = "before http://a.test\n```text\nhttp://code.test\n```\nafter http://b.test"
    assert _markdown_autolink_urls(source) == (
        "before <http://a.test>\n```text\nhttp://code.test\n```\nafter <http://b.test>"
    )


def test_nfr6_spend_sql_uses_jpy_and_utc_half_open_window() -> None:
    con = _measurement_db()
    try:
        _insert_approval(con, 1)
        paid_rows = [
            (1, 100, "2026-08-01T00:00:00Z", "kept charge"),
            (2, 50, "2026-08-02T00:00:00Z", "reversed charge"),
            (3, 800, "2026-09-01T00:00:00Z", "next window"),
        ]
        for op_id, amount, occurred_at, purpose in paid_rows:
            op = _insert_sent_external_operation(
                con, op_id, effect="write", policy_category="approved_paid_operation",
                rate_scope="paid_fixture", sent_at=occurred_at,
            )
            _finalize_external_operation(
                con, op, result="confirmed", created_at=occurred_at,
                paid={"approval_id": 1, "amount_minor": amount, "currency": "JPY",
                      "purpose": purpose, "occurred_at": occurred_at},
            )
        reversed_id = con.execute(
            "SELECT id FROM spend_ledger WHERE external_operation_row_id=2"
        ).fetchone()[0]
        con.execute(
            "INSERT INTO tasks (id,loop_run_id,parent_task_id,workflow_id,task_type,"
            "author_agent_id,verifier_agent_id,state,step_key,idempotency_key,"
            "expected_output_kind,input_json,created_at) "
            "VALUES (2,1,1,1,'spend_correction',1,2,'in_progress','correct-spend',"
            "'correct-spend-1','spend_reversal',?, 't')",
            (json.dumps({"original_spend_ledger_id": reversed_id}),),
        )
        _insert_approval(con, 2, task_id=2)
        con.execute(
            "INSERT INTO spend_ledger "
            "(task_id,entry_type,approval_id,service,amount_minor,currency,purpose,"
            "reverses_spend_ledger_id,occurred_at,created_at) "
            "VALUES (2,'reversal',2,'fixture',50,'JPY','approved correction',?,?,?)",
            (reversed_id, "2026-08-03T00:00:00Z", "2026-08-03T00:00:00Z"),
        )
        total = con.execute(_nfr_sql("NFR-6"), {
            "month_start_utc": "2026-08-01T00:00:00Z",
            "next_month_start_utc": "2026-09-01T00:00:00Z",
        }).fetchone()[0]
        assert total == 100
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO spend_ledger "
                "(task_id,entry_type,approval_id,service,amount_minor,currency,purpose,"
                "reverses_spend_ledger_id,occurred_at,created_at) "
                "VALUES (1,'reversal',2,'fixture',100,'USD','invalid FX',1,?,?)",
                ("2026-08-04T00:00:00Z", "2026-08-04T00:00:00Z"),
            )
    finally:
        con.close()


def test_nfr7_daily_cap_sql_counts_writes_only_in_utc_window() -> None:
    con = _measurement_db()
    try:
        fixtures = [
            (10, "write", "review_sync", "note", "2026-08-10T12:00:00Z", "confirmed"),
            (11, "write", "review_sync", "note", "2026-08-10T13:00:00Z", "rejected"),
            (12, "write", "review_sync", "note", "2026-08-10T14:00:00Z", "unknown"),
            (13, "read", "external_read", None, "2026-08-10T15:00:00Z", "confirmed"),
            (14, "write", "review_sync", "note", "2026-08-11T00:00:00Z", "confirmed"),
        ]
        for op_id, effect, category, rate_scope, sent_at, result in fixtures:
            op = _insert_sent_external_operation(
                con, op_id, effect=effect, policy_category=category,
                rate_scope=rate_scope, sent_at=sent_at,
            )
            _finalize_external_operation(con, op, result=result, created_at=sent_at)
        count = con.execute(_nfr_sql("NFR-7"), {
            "rate_scope": "note",
            "day_start_utc": "2026-08-10T00:00:00Z",
            "next_day_start_utc": "2026-08-11T00:00:00Z",
        }).fetchone()[0]
        assert count == 3
    finally:
        con.close()


def test_nfr5_sent_recovery_timeout_uses_strict_cutoff_boundary() -> None:
    con = _measurement_db()
    try:
        for op_id, sent_at in [
            (20, "2026-08-10T11:59:59Z"),
            (21, "2026-08-10T12:00:00Z"),
            (22, "2026-08-10T12:00:01Z"),
        ]:
            _insert_sent_external_operation(
                con, op_id, effect="read", policy_category="external_read",
                rate_scope=None, sent_at=sent_at,
            )
        sql = _nfr_sql_containing("NFR-5", "status='sent'")
        rows = con.execute(sql, {"recovery_cutoff_utc": "2026-08-10T12:00:00Z"}).fetchall()
        assert rows == [(20,)]
    finally:
        con.close()


def test_media_requirements_have_no_unquantified_or_stale_limits() -> None:
    assert requirements.detect_media_semantic_faults() == []


def test_mutation_ambiguous_media_rate_is_detected(tmp_path) -> None:
    p = tmp_path / "docs/L1-business-requirements/canonical/br-media"
    p.mkdir(parents=True)
    (p / "kdp.json").write_text(json.dumps({"items": [
        {"id": "BR-M-KDP-X", "text": "出版は月数冊とする", "structure": "外部調査"}
    ]}, ensure_ascii=False), encoding="utf-8")
    faults = requirements.detect_media_semantic_faults(root=tmp_path)
    assert any("判定不能な規範量" in f for f in faults)


@pytest.mark.parametrize("phrase", ["数件", "十数件", "少量", "適度", "低頻度", "80以上（目安）"])
def test_mutation_known_ambiguous_media_quantities_are_detected(tmp_path, phrase: str) -> None:
    p = tmp_path / "docs/L1-business-requirements/canonical/br-media"
    p.mkdir(parents=True)
    (p / "x.json").write_text(json.dumps({"items": [
        {"id": "BR-M-X-X", "text": f"処理量は{phrase}とする", "structure": "外部仕様（目安）"}
    ]}, ensure_ascii=False), encoding="utf-8")
    assert requirements.detect_media_semantic_faults(root=tmp_path)


def test_media_structure_research_wording_is_not_treated_as_normative(tmp_path) -> None:
    p = tmp_path / "docs/L1-business-requirements/canonical/br-media"
    p.mkdir(parents=True)
    (p / "x.json").write_text(json.dumps({"items": [
        {"id": "BR-M-X-X", "text": "上限は config.rate.x.daily_cap で必須化する",
         "structure": "公開情報上の上限は目安"}
    ]}, ensure_ascii=False), encoding="utf-8")
    assert requirements.detect_media_semantic_faults(root=tmp_path) == []


def test_mutation_media_structure_split_is_detected(tmp_path) -> None:
    p = tmp_path / "docs/L1-business-requirements/canonical/br-media"
    p.mkdir(parents=True)
    (p / "kdp.json").write_text(json.dumps({"items": [
        {"structure": "週次作成上限"}, {"structure": "同時実行上限"}
    ]}, ensure_ascii=False), encoding="utf-8")
    faults = requirements.detect_media_semantic_faults(root=tmp_path)
    assert any("structureが分岐" in f for f in faults)


def test_no_legacy_denominator_leaks_in_live_docs() -> None:
    assert requirements.detect_legacy_denominator_leaks() == []


def _fake_tree(tmp_path, monkeypatch, docs: dict[str, str]) -> list:
    """ROOT を差し替えた疑似リポジトリを作り、live_markdown の戻り値を固定する。"""
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        (tmp_path / name).write_text("現行分母は AC=211／TCC=217。\n", encoding="utf-8")
    live = []
    for relpath, text in docs.items():
        p = tmp_path / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        live.append(p)
    monkeypatch.setattr("tools.gates.common.ROOT", tmp_path)
    monkeypatch.setattr("tools.gates.common.live_markdown", lambda: live)
    return live


def test_mutation_legacy_denominator_in_a_live_doc_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 現役文書に旧分母（AC 19／TC 59／UTC 69）が復活したら検出されなければならない。"""
    _fake_tree(tmp_path, monkeypatch, {
        "docs/L3-system-requirements/canonical/leak.md": "受入基準は AC 19 本、検証は TC 59 本。\n",
        "docs/L3-system-requirements/canonical/clean.md": "受入基準は AC=211 本、検証は TCC=217 本。\n",
    })
    faults = requirements.detect_legacy_denominator_leaks(root=tmp_path)
    assert any("AC 19" in f for f in faults)
    assert any("TC 59" in f for f in faults)
    assert not any("clean.md" in f for f in faults), "現行分母の文書を誤検出している"


def test_historical_directories_are_exempt_from_the_legacy_scan(tmp_path, monkeypatch) -> None:
    """監査・承認・レビューは append-only の歴史なので旧分母の記録が残ってよい。"""
    _fake_tree(tmp_path, monkeypatch, {
        "docs/00-authority/audits/past.md": "当時の分母は AC 19／TC 59／UTC 69 だった。\n",
    })
    assert requirements.detect_legacy_denominator_leaks(root=tmp_path) == []
