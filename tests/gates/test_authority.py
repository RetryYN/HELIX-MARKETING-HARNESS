"""authority ゲートの単体テストと mutation test（検出能力の証明）。"""

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
    victim = next(i for i in items if i["status"] == "confirmed")
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
        if it["status"] != "confirmed":
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
