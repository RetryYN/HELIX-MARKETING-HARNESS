"""review_binding ゲートの単体テストと mutation test。"""

from tools.gates import review_binding
from tools.gates.common import CTX, ROOT


def test_path_resolver_maps_previous_paths_to_current() -> None:
    """manifest.previous_paths の解決能力を検証するため、**意図的に**旧パスを固定する。

    ここに現れる旧パスは実装入力ではなく検査対象の入力値であり、
    G-ARCHIVE-ISOLATION／旧パス残存検査の例外（requirements-gates.md に明記）。
    """
    table = review_binding.path_resolver(CTX)
    assert table["docs/requirements/json/br/br-contracts.json"] == \
        "docs/L1-business-requirements/canonical/br/br-contracts.json"
    assert table["docs/design/json/du-contracts.json"] == \
        "docs/L5-detailed-design/canonical/apis/du-contracts.json"


def test_path_resolver_is_identity_for_current_paths() -> None:
    table = review_binding.path_resolver(CTX)
    for it in CTX.manifest_items:
        assert table[it["canonical_path"]] == it["canonical_path"]


def test_successors_follow_supersedes_chain() -> None:
    reviews = {
        "REV-A": {"review_id": "REV-A", "verdict": "Go", "supersedes_review": []},
        "REV-B": {"review_id": "REV-B", "verdict": "Go", "supersedes_review": ["REV-A"]},
        "REV-C": {"review_id": "REV-C", "verdict": "Go", "supersedes_review": ["REV-B"]},
    }
    ids = {r["review_id"] for r in review_binding.successors(reviews, "REV-A")}
    assert ids == {"REV-B", "REV-C"}


def test_mutation_broken_chain_yields_no_successor() -> None:
    reviews = {
        "REV-A": {"review_id": "REV-A", "verdict": "Go", "supersedes_review": []},
        "REV-B": {"review_id": "REV-B", "verdict": "Go", "supersedes_review": []},
    }
    assert review_binding.successors(reviews, "REV-A") == []


def test_mutation_no_go_successor_is_not_counted() -> None:
    reviews = {
        "REV-A": {"review_id": "REV-A", "verdict": "Go", "supersedes_review": []},
        "REV-B": {"review_id": "REV-B", "verdict": "No-Go", "supersedes_review": ["REV-A"]},
    }
    assert review_binding.successors(reviews, "REV-A") == []


def test_review_artifacts_are_bound() -> None:
    assert review_binding.detect_review_faults(CTX) == []


def test_dangling_tree_is_not_reachable() -> None:
    """`git write-tree` の dangling tree は到達不可（push されず clone 先で解決できない）。"""
    import subprocess
    dangling = subprocess.run(["git", "write-tree"], capture_output=True, text=True,
                              check=True, cwd=ROOT).stdout.strip()
    head_tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], capture_output=True,
                               text=True, check=True, cwd=ROOT).stdout.strip()
    assert review_binding.tree_is_reachable(head_tree) is True
    if dangling != head_tree:  # 作業ツリーに未コミット差分がある場合のみ検査できる
        assert review_binding.tree_is_reachable(dangling) is False, \
            "dangling tree を到達可能と誤判定している（CI の clone 先で解決できない）"


def test_mutation_unreachable_target_tree_is_detected() -> None:
    """変異: 存在しないツリー sha を到達可能と判定してはならない。"""
    assert review_binding.tree_is_reachable("0" * 40) is False


def test_is_committed_distinguishes_tracked_files() -> None:
    assert review_binding.is_committed(ROOT / "CLAUDE.md") is True
    assert review_binding.is_committed(ROOT / "docs/does-not-exist.md") is False
