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


@pytest.mark.parametrize("claim", ["トリガ 14 本", "トリガ 11 本", "保護トリガ 4 本",
                                   "整合トリガ 6 件", "15 本のトリガ", "トリガ 11",
                                   "トリガーは 11 本", "11 基のトリガ", "トリガー 14"])
def test_mutation_stale_trigger_count_is_detected(tmp_path, monkeypatch, claim) -> None:
    """変異: 旧いトリガ本数（11／14）や部分集合の本数を書くと検出される。"""
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


def test_section_numbers_are_not_read_as_trigger_counts(monkeypatch) -> None:
    """偽陽性回帰: 節番号（§2 の保護トリガ／3.2 トリガ 16 本）を本数の主張と読まない。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [
        ("d.md", "config への UPDATE/DELETE は §2 の保護トリガが常時拒否する"),
        ("e.md", "### 3.2 トリガ 16 本の意図"),
        ("f.md", "ツール代替（tech-stack §7 トリガー）")])
    assert architecture.detect_physical_count_faults(CTX.ddl) == []


def test_identifier_digits_are_not_read_as_counts(monkeypatch) -> None:
    """偽陽性回帰: 「S0 テーブル」「SCM-01 テーブル」の識別子を数値の主張と読まない。"""
    monkeypatch.setattr(architecture, "_texts", lambda root=None: [
        ("d.md", "S0 テーブル定義の差分なし / SCM-01 テーブルに依存 / 戦略正本 2 テーブル")])
    assert architecture.detect_physical_count_faults(CTX.ddl) == []
