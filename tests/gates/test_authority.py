"""authority ゲートの単体テストと mutation test（検出能力の証明）。"""

import pytest

from tools.gates import authority
from tools.gates.common import CTX, MANIFEST, ROOT


def _items() -> list[dict]:
    return [dict(i) for i in CTX.manifest_items]


def test_manifest_is_clean_on_real_tree() -> None:
    items = _items()
    assert authority.detect_manifest_duplicates(items) == []
    assert authority.detect_manifest_path_faults(items) == []
    assert authority.detect_manifest_pair_faults(items) == []
    assert authority.detect_unregistered(items) == []


def test_mutation_duplicate_artifact_id_is_detected() -> None:
    items = _items()
    items.append(dict(items[0]))
    assert any("artifact_id 重複" in b for b in authority.detect_manifest_duplicates(items))


def test_mutation_duplicate_canonical_claim_is_detected() -> None:
    items = _items()
    victim = next(i for i in items if i["lifecycle_status"] == "confirmed")
    clone = dict(victim, artifact_id=victim["artifact_id"] + "-CLONE")
    items.append(clone)
    assert any("canonical 重複主張" in b for b in authority.detect_manifest_duplicates(items))


def test_mutation_missing_canonical_path_is_detected() -> None:
    items = _items()
    items[0]["canonical_path"] = "docs/L3-system-requirements/canonical/ghost.json"
    assert any("canonical 不在" in b for b in authority.detect_manifest_path_faults(items))


def test_mutation_view_outside_views_dir_is_detected() -> None:
    items = _items()
    victim = next(i for i in items if i["view_path"])
    victim["view_path"] = "docs/L3-system-requirements/canonical/functional/requirements_v0.1.md"
    assert any("views/ 外" in b for b in authority.detect_manifest_path_faults(items))


def test_mutation_asymmetric_pair_is_detected() -> None:
    items = _items()
    victim = next(i for i in items if i["pair_artifact_id"])
    victim["pair_artifact_id"] = "L9-NOT-A-REAL-ARTIFACT"
    assert any("pair 不在" in b for b in authority.detect_manifest_pair_faults(items))


def test_mutation_unregistered_artifact_is_detected() -> None:
    items = [i for i in _items() if not i["canonical_path"].endswith("s0-contract_v0.1.md")]
    assert any("s0-contract" in b for b in authority.detect_unregistered(items))


def test_frozen_reference_mutation_is_detected() -> None:
    assert authority.detect_frozen_references(targets=["README.md"]) == []
    # 変異: 凍結領域を入力として参照する CI 断片を与えると検出される
    bad = authority._frozen_hits_in_code("      run: python3 docs/archive/pre-structure-migration-2026-08-01/ac.json\n")
    assert bad, "archive を入力として扱う行を検出できていない"
    # 除外指示（lychee/markdownlint）は検出しない
    assert authority._frozen_hits_in_code("            --exclude-path docs/archive\n") == []


def test_artifact_content_digest_matches_manifest() -> None:
    for it in CTX.manifest_items:
        if it["lifecycle_status"] != "confirmed":
            continue
        assert it["approval_digest"] == authority.artifact_content_digest(ROOT / it["canonical_path"])


def test_manifest_file_is_registered_authority() -> None:
    assert MANIFEST.exists()
    assert CTX.manifest["status"] == "active"


# --- 現在地の一意化（PO 指示 §3）の検出能力 ---

def _state_tree(tmp_path, monkeypatch, owners: dict[str, str], live: dict[str, str]) -> None:
    """ROOT を差し替えた疑似リポジトリを作る（README／CLAUDE／AGENTS＋現役 docs）。"""
    for name, text in owners.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(owners.get("AGENTS.md", "作業規律のみ。\n"), encoding="utf-8")
    paths = []
    for relpath, text in live.items():
        p = tmp_path / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    monkeypatch.setattr("tools.gates.common.ROOT", tmp_path)
    monkeypatch.setattr("tools.gates.authority.live_markdown", lambda: paths)


def _owner_text() -> str:
    return "# 現在地\n\n" + "".join(f"- {line}\n" for line in authority.CURRENT_STATE_LINES)


def test_current_state_is_single_sourced_on_the_real_tree() -> None:
    assert authority.detect_current_state_faults() == []


def test_mutation_restating_the_current_state_elsewhere_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 現在地を README／CLAUDE.md 以外の現役文書へ再掲したら検出されなければならない。"""
    _state_tree(tmp_path, monkeypatch,
                {"README.md": _owner_text(), "CLAUDE.md": _owner_text()},
                {"docs/L4-basic-design/canonical/basic-design.md":
                 f"## 前提\n\n{authority.CURRENT_STATE_LINES[0]}\n"})
    faults = authority.detect_current_state_faults(root=tmp_path)
    assert any("現在地の再掲" in f for f in faults)


def test_mutation_forbidden_route_phrase_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 未決の HELIX 取込を確定表現で書いたら検出されなければならない。"""
    phrase = authority.FORBIDDEN_STATE_PHRASES[0]
    _state_tree(tmp_path, monkeypatch,
                {"README.md": _owner_text() + f"\n{phrase}\n", "CLAUDE.md": _owner_text()},
                {})
    faults = authority.detect_current_state_faults(root=tmp_path)
    assert any("確定表現" in f for f in faults)


def test_mutation_duplicated_state_line_inside_an_owner_is_detected(tmp_path, monkeypatch) -> None:
    """変異: 正本ファイル内で現在地を 2 回書いたら（＝食い違いの余地）検出される。"""
    _state_tree(tmp_path, monkeypatch,
                {"README.md": _owner_text() + _owner_text(), "CLAUDE.md": _owner_text()},
                {})
    faults = authority.detect_current_state_faults(root=tmp_path)
    assert any("×2" in f for f in faults)


# --- canonical／view の形式規律（PO 指示 §1）の検出能力 ---

def test_format_discipline_is_clean_on_real_tree() -> None:
    assert authority.detect_format_faults(_items()) == []


def test_mutation_json_ledger_claiming_markdown_authority_is_detected() -> None:
    """変異: JSON 正本を持つ型が canonical Markdown を名乗ったら落ちる。"""
    items = _items()
    victim = next(i for i in items if i["artifact_type"] == "requirement-contract")
    victim["authority_format"] = "markdown"
    assert any("canonical Markdown を持てない" in b for b in authority.detect_format_faults(items))


def test_mutation_format_mismatch_with_extension_is_detected() -> None:
    """変異: authority_format を拡張子と食い違わせて形式規律を迂回できない。"""
    items = _items()
    victim = next(i for i in items if i["authority_format"] == "markdown")
    victim["authority_format"] = "json"
    assert any("と不一致" in b or "非 markdown 正本" in b
               for b in authority.detect_format_faults(items))


def test_mutation_generated_view_registered_as_canonical_is_detected() -> None:
    """変異: 生成 MD を canonical として登録し直すことを許さない。"""
    items = _items()
    view = next(i for i in items if i["view_generation"] == "generated")
    items.append(dict(view, artifact_id="FAKE-CANONICAL", canonical_path=view["view_path"],
                      authority_format="markdown", artifact_type="design-doc",
                      view_path=None, view_generation="none"))
    faults = authority.detect_format_faults(items)
    assert any("生成 MD を canonical に登録" in b for b in faults)
    assert any("二枚看板" in b for b in faults)


def test_mutation_view_generation_flag_desync_is_detected() -> None:
    """変異: view_path を持ちながら view_generation を none に偽れない。"""
    items = _items()
    victim = next(i for i in items if i["view_generation"] == "generated")
    victim["view_generation"] = "none"
    assert any("view_generation" in b for b in authority.detect_format_faults(items))


# --- status の意味分離（PO 指示 §3）の検出能力 ---

def test_status_discipline_is_clean_on_real_tree() -> None:
    assert authority.detect_status_faults(_items()) == []


def test_mutation_confirmed_without_approval_digest_is_detected() -> None:
    """変異: 承認 digest なしで confirmed を名乗れない。"""
    items = _items()
    victim = next(i for i in items if i["lifecycle_status"] == "confirmed")
    victim["approval_digest"] = None
    assert any("approval_digest" in b for b in authority.detect_status_faults(items))


def test_mutation_draft_document_promoted_in_manifest_only_is_detected() -> None:
    """変異: manifest だけ confirmed へ上げても frontmatter との不一致で落ちる。"""
    items = _items()
    victim = next(i for i in items
                  if i["authority_format"] == "markdown" and i["lifecycle_status"] == "draft")
    victim["lifecycle_status"] = "confirmed"
    faults = authority.detect_status_faults(items)
    assert any("frontmatter.lifecycle_status" in b for b in faults)


def test_mutation_authority_status_and_frozen_path_desync_is_detected() -> None:
    """変異: 凍結領域の成果物を active と主張できない。"""
    items = _items()
    victim = next(i for i in items if i["authority_status"] != "active")
    victim["authority_status"] = "active"
    assert any("凍結領域なのに" in b for b in authority.detect_status_faults(items))


# --- スライス配置（PO 指示 §2・§5）の検出能力 ---

def test_slice_placement_is_clean_on_real_tree() -> None:
    assert authority.detect_slice_faults(CTX) == []


def test_mutation_undeclared_forward_reference_is_detected(tmp_path) -> None:
    """変異: S0 文書へ後続スライスの要求を書き足しても forward_refs 宣言漏れで落ちる。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/evidence.md"
    victim.write_text(victim.read_text(encoding="utf-8") + "\n本節は FR-34 を実装する。\n",
                      encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("forward_refs が本文の後続スライス言及と不一致" in b for b in faults)


def test_mutation_trace_from_another_slice_is_detected(tmp_path) -> None:
    """変異: S0 文書が S1 の要求を traces（根拠）に据えることを許さない。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/evidence.md"
    victim.write_text(victim.read_text(encoding="utf-8").replace(
        "traces: [FR-28, FR-54, FR-55]", "traces: [FR-34]"), encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("別スライスの要求を根拠にできない" in b for b in faults)


def test_mutation_slice_directory_mismatch_is_detected(tmp_path) -> None:
    """変異: 物理ディレクトリと frontmatter.slice の食い違いを検出する。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/evidence.md"
    victim.write_text(victim.read_text(encoding="utf-8").replace(
        "slice: S0", "slice: S1"), encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("frontmatter.slice" in b for b in faults)


def test_mutation_unknown_requirement_in_body_is_detected(tmp_path) -> None:
    """変異: 本文へ実在しない FR-99／SR-77 を書いても無視されない（独立レビュー F-04）。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/evidence.md"
    victim.write_text(victim.read_text(encoding="utf-8") + "\n本節は FR-99・SR-77 に対応する。\n",
                      encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("本文が実在しない要求 FR-99" in b for b in faults)
    assert any("本文が実在しない要求 SR-77" in b for b in faults)


def test_mutation_dus_declaration_desync_is_detected(tmp_path) -> None:
    """変異: frontmatter.dus を書き換えると du-contracts との双方向突合で落ちる（F-07）。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/pair-gate.md"
    victim.write_text(victim.read_text(encoding="utf-8").replace(
        "dus: [DU-05, DU-06]", "dus: [DU-05]"), encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("frontmatter.dus が du-contracts" in b for b in faults)


def test_mutation_feature_doc_not_covering_declared_du_is_detected(tmp_path) -> None:
    """変異: 宣言した DU も その AC も扱わない本文へ差し替えると落ちる（F-07）。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    victim = root / "docs/L6-feature-design/S0/pair-gate.md"
    fm = victim.read_text(encoding="utf-8").split("---", 2)[1]
    victim.write_text(f"---{fm}---\n\n# 中身のない機能設計\n\n## §1\n\n本文。\n",
                      encoding="utf-8")
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("本文が扱っていない" in b for b in faults)


def test_mutation_untracked_canonical_is_detected(monkeypatch) -> None:
    """変異: git 未追跡のファイルを canonical に登録すると落ちる（F-10／独立レビュー N-04）。

    偶発的に存在する成果物に頼らず、追跡集合を決定的に固定して検査する。
    """
    items = _items()
    victim = items[0]["canonical_path"]
    monkeypatch.setattr(authority, "tracked_files", lambda root=ROOT: set())
    faults = authority.detect_manifest_path_faults(items)
    assert any(f"canonical が git 未追跡 {victim}" in b for b in faults)


def test_mutation_git_listing_failure_is_fail_close(monkeypatch) -> None:
    """変異: 追跡集合を取得できない環境で検査が消える（fail-open）ことを許さない。"""
    monkeypatch.setattr(authority, "tracked_files", lambda root=ROOT: None)
    faults = authority.detect_manifest_path_faults(_items())
    assert any("git 管理下のファイル一覧を取得できない" in b for b in faults)


def test_mutation_generated_marker_outside_window_is_detected(tmp_path) -> None:
    """変異: GENERATED 宣言を先頭窓の外へ追い出して canonical 混入検査を外せない（F-09／N-05）。"""
    p = tmp_path / "sneaky.md"
    p.write_text("あ" * (authority.GENERATED_WINDOW + 50) + "\n" + authority.GENERATED_MARK + "\n",
                 encoding="utf-8")
    assert authority.is_generated_view(p) is True


def test_mutation_nonexistent_feature_design_is_detected(tmp_path, monkeypatch) -> None:
    """変異: du-contracts の feature_design に実在しないパスを書いても落ちる（N-06）。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    duc = [dict(d) for d in CTX.duc]
    duc[0] = dict(duc[0], trace=dict(duc[0]["trace"],
                                     feature_design=["docs/L6-feature-design/S0/ghost.md"]))
    monkeypatch.setattr(type(CTX), "duc", property(lambda self: duc))
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("L6 機能設計として実在しない" in b for b in faults)


def test_tracked_files_returns_none_on_git_failure(monkeypatch) -> None:
    """変異: git 一覧の取得失敗を空集合で握り潰さない（fail-open 防止 — R4-02）。"""
    class _R:
        returncode = 128
        stdout = ""

    monkeypatch.setattr(authority.subprocess, "run", lambda *a, **k: _R())
    assert authority.tracked_files() is None


def test_mutation_s1_feature_design_on_s0_du_is_detected(tmp_path, monkeypatch) -> None:
    """変異: S0 の DU に S1 の機能設計を割り当てると落ちる（R4-07）。"""
    import shutil
    from pathlib import Path
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "docs/L6-feature-design", root / "docs/L6-feature-design")
    duc = [dict(d) for d in CTX.duc]
    duc[0] = dict(duc[0], trace=dict(duc[0]["trace"],
                                     feature_design=["docs/L6-feature-design/S1/campaign.md"]))
    monkeypatch.setattr(type(CTX), "duc", property(lambda self: duc))
    faults = authority.detect_slice_faults(CTX, root=Path(root))
    assert any("後続スライスの機能設計" in b for b in faults)


# --- 継承関係（PO 指示 §3）の検出能力 ---

def test_relations_are_clean_on_real_tree() -> None:
    assert authority.detect_relation_faults(_items()) == []


def test_mutation_dangling_relation_reference_is_detected() -> None:
    """変異: 存在しない旧 artifact ID を supersedes に残せない（分割前の ID の置き去り）。"""
    items = _items()
    items[0]["supersedes"] = ["L6-S0-BRAND-ISOLATION"]
    assert any("参照先 L6-S0-BRAND-ISOLATION が manifest に存在しない" in b
               for b in authority.detect_relation_faults(items))


def test_mutation_superseding_a_live_artifact_is_detected() -> None:
    """変異: 現役成果物を supersedes に書けない（拡張を置換と偽れない）。"""
    items = _items()
    victim = next(i for i in items if i["artifact_id"] == "L6-S1-BRAND-ISOLATION-COMPLETION")
    victim["supersedes"] = ["L6-S0-BRAND-ISOLATION-FOUNDATION"]
    victim["extends_artifact_ids"] = []
    faults = authority.detect_relation_faults(items)
    assert any("現役成果物は置換対象にできない" in b for b in faults)


def test_mutation_self_reference_is_detected() -> None:
    items = _items()
    aid = items[0]["artifact_id"]
    items[0]["extends_artifact_ids"] = [aid]
    assert any("自己参照" in b for b in authority.detect_relation_faults(items))


def test_mutation_duplicate_declaration_across_fields_is_detected() -> None:
    """変異: 同じ相手を extends と depends_on の両方で宣言して関係を曖昧にできない。"""
    items = _items()
    victim = next(i for i in items if i["artifact_id"] == "L6-S1-BRAND-ISOLATION-COMPLETION")
    victim["depends_on_artifact_ids"] = list(victim["extends_artifact_ids"])
    assert any("の両方で宣言" in b for b in authority.detect_relation_faults(items))


def test_mutation_relation_cycle_is_detected() -> None:
    """変異: 拡張関係の循環（A→B→A）は検出される。"""
    items = _items()
    a = next(i for i in items if i["artifact_id"] == "L6-S1-BRAND-ISOLATION-COMPLETION")
    b = next(i for i in items if i["artifact_id"] == "L6-S0-BRAND-ISOLATION-FOUNDATION")
    b["depends_on_artifact_ids"] = [a["artifact_id"]]
    assert any("循環参照" in x for x in authority.detect_relation_faults(items))


def test_cycles_finds_longer_loops() -> None:
    assert authority._cycles({"A": {"B"}, "B": {"C"}, "C": {"A"}})
    assert authority._cycles({"A": {"B"}, "B": {"C"}}) == []


# --- domain の語彙（PO 指示 §4）の検出能力 ---

def test_domains_are_clean_on_real_tree() -> None:
    assert authority.detect_domain_faults(_items()) == []


def test_mutation_slice_name_as_domain_is_detected() -> None:
    for bogus in ("S0", "S1", "later", "cross"):
        items = _items()
        items[0]["domain"] = bogus
        faults = authority.detect_domain_faults(items)
        assert any("slice" in b for b in faults), bogus


def test_mutation_layer_name_as_domain_is_detected() -> None:
    items = _items()
    items[0]["domain"] = "l4"
    assert any("階層名" in b for b in authority.detect_domain_faults(items))


@pytest.mark.parametrize("compound", ["s0-design", "design-s1", "later-work", "cross-domain"])
def test_mutation_slice_name_inside_a_compound_domain_is_detected(compound) -> None:
    """変異: slice 名をハイフン複合語へ埋め込んでも検査を外せない（独立レビュー R1-04）。

    全体一致だけの検査へ退行すると、この 4 件が素通りする。
    """
    items = _items()
    items[0]["domain"] = compound
    faults = authority.detect_domain_faults(items)
    assert any("slice 名が含まれる" in b for b in faults), compound


@pytest.mark.parametrize("compound", ["l4-design", "design-l6", "l0-charter"])
def test_mutation_layer_name_inside_a_compound_domain_is_detected(compound) -> None:
    """変異: 階層名をハイフン複合語へ埋め込んでも検査を外せない。"""
    items = _items()
    items[0]["domain"] = compound
    faults = authority.detect_domain_faults(items)
    assert any("階層名が含まれる" in b for b in faults), compound


def test_mutation_non_kebab_domain_is_detected() -> None:
    items = _items()
    items[0]["domain"] = "Brand_Isolation"
    assert any("kebab-case" in b for b in authority.detect_domain_faults(items))
