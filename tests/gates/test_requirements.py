"""requirements ゲートの単体テストと mutation test。"""

import copy

from tools.gates import requirements
from tools.gates.common import CTX


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
        "AC_CONTRACT": 237, "TCC": 243, "API": 58, "API_UT": 199}


def test_nfr_verification_chain_is_concrete_and_complete() -> None:
    assert requirements.detect_nfr_verification_faults(CTX.nfc, CTX.acc, CTX.tcc) == []


def test_mutation_nfr_prose_tc_and_pseudo_sql_are_detected() -> None:
    nfr = copy.deepcopy(CTX.nfc[0])
    nfr["trace_down"] = {"ac": [], "tc": ["拒否系 TC 群"]}
    nfr["measurement_method"] += " SELECT * FROM loop_runs/tasks WHERE state NOT IN (終端)"
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, CTX.tcc)
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
    faults = requirements.detect_nfr_verification_faults([nfr], acs, tcs)
    assert any("AC意味被覆差分" in f for f in faults)
    assert any("TCC意味被覆差分" in f for f in faults)


def test_mutation_nfr_aspect_without_executable_assertion_is_detected() -> None:
    nfr = copy.deepcopy(CTX.nfc[0])
    tcs = copy.deepcopy(CTX.tcc)
    victim = nfr["verification_aspects"][0]
    for tc in tcs:
        if tc["id"] in nfr["trace_down"]["tc"]:
            tc["aspect_assertions"].pop(victim)
    faults = requirements.detect_nfr_verification_faults([nfr], CTX.acc, tcs)
    assert any("TCC観点assert差分" in f for f in faults)


def test_media_requirements_have_no_unquantified_or_stale_limits() -> None:
    assert requirements.detect_media_semantic_faults() == []


def test_mutation_ambiguous_media_rate_is_detected(tmp_path) -> None:
    p = tmp_path / "docs/L1-business-requirements/canonical/br-media"
    p.mkdir(parents=True)
    (p / "kdp.json").write_text('{"text":"出版は月数冊とする"}', encoding="utf-8")
    faults = requirements.detect_media_semantic_faults(root=tmp_path)
    assert any("月数冊" in f for f in faults)


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
