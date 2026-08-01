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


def test_mutation_chain_does_not_traverse_through_no_go() -> None:
    """変異: No-Go を跨いだ継承を認めない（No-Go で鎖を止める — 独立レビュー R4-05）。

    A(Go) → B(No-Go) → C(Go) の C は「No-Go を引き継いだレビュー」であって、
    A の判定を引き継ぐ鎖ではない。
    """
    reviews = {
        "REV-A": {"review_id": "REV-A", "verdict": "Go", "supersedes_review": []},
        "REV-B": {"review_id": "REV-B", "verdict": "No-Go", "supersedes_review": ["REV-A"]},
        "REV-C": {"review_id": "REV-C", "verdict": "Go", "supersedes_review": ["REV-B"]},
    }
    assert review_binding.successors(reviews, "REV-A") == []


def test_review_artifacts_are_bound() -> None:
    assert review_binding.detect_review_faults(CTX) == []


def test_commit_tree_returns_root_tree_of_commit() -> None:
    """target_tree の正解は target_commit のルートツリー（O(1) 厳密一致で検査する）。"""
    import subprocess
    head_tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], capture_output=True,
                               text=True, check=True, cwd=ROOT).stdout.strip()
    assert review_binding.commit_tree("HEAD") == head_tree


def test_mutation_unknown_commit_yields_none() -> None:
    """変異: 存在しない commit を解決したと偽ってはならない（fail-close の入口）。"""
    assert review_binding.commit_tree("0" * 40) is None


# --- target_tree 束縛の負例（detect_review_faults を直接叩く — 独立レビュー F-06） ---

def _review_dir(tmp_path, **over):
    """実レビュー成果物を複製し、1 件だけ変異させた REVIEWS ディレクトリを作る。"""
    import json
    import shutil
    src = ROOT / "docs/00-authority/reviews"
    dst = tmp_path / "reviews"
    shutil.copytree(src, dst)
    victim = dst / "sol-review-s0-structure-02.json"
    data = json.loads(victim.read_text(encoding="utf-8"))
    for k, v in over.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    victim.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dst


def _faults(monkeypatch, review_dir) -> list[str]:
    monkeypatch.setattr(review_binding, "REVIEWS", review_dir)
    return review_binding.detect_review_faults(CTX)


def test_mutation_missing_target_tree_is_detected(monkeypatch, tmp_path) -> None:
    """変異: target_tree キーごと消して厳密一致検査をスキップさせられない。"""
    faults = _faults(monkeypatch, _review_dir(tmp_path, target_tree=None))
    assert any("target_tree がない" in f or "target_tree: 必須欠落" in f for f in faults)


def test_mutation_dangling_target_tree_is_detected(monkeypatch, tmp_path) -> None:
    """変異: `git write-tree` の dangling tree（clone 先で解決できない）を束縛にできない。"""
    import subprocess
    dangling = subprocess.run(["git", "write-tree"], capture_output=True, text=True,
                              check=True, cwd=ROOT).stdout.strip()
    faults = _faults(monkeypatch, _review_dir(tmp_path, target_tree=dangling))
    assert any("target_tree" in f for f in faults), "dangling tree を素通りさせている"


def test_mutation_other_commits_tree_is_detected(monkeypatch, tmp_path) -> None:
    """変異: 別コミット（HEAD）のツリーへ掏り替えても厳密一致で落ちる。"""
    head_tree = review_binding.commit_tree("HEAD")
    faults = _faults(monkeypatch, _review_dir(tmp_path, target_tree=head_tree))
    assert any("target_commit のルートツリーと不一致" in f for f in faults)


def test_mutation_same_digest_on_another_artifact_does_not_carry_over(monkeypatch, tmp_path) -> None:
    """変異: 別 artifact に同じ digest が載っているだけで改変を引き継げない（R4-04）。

    後続 Go レビューの `reviewed_artifact_digests` を **artifact キーごと**に照合しないと、
    無関係な artifact の digest 一致で「レビュー済み」を名乗れてしまう。
    レビュー集合を victim と successor の 2 件へ**孤立**させ、他レビューの副作用に
    依存せず当該分岐だけを検査する。
    """
    import hashlib
    import json
    import shutil
    src = ROOT / "docs/00-authority/reviews"
    dst = tmp_path / "reviews"
    dst.mkdir()
    shutil.copy(src / "review.schema.json", dst / "review.schema.json")
    shutil.copy(src / "sol-review-s0-structure-02.json", dst / "victim.json")
    data = json.loads((dst / "victim.json").read_text(encoding="utf-8"))
    # 記録 digest は書き換えない。レビュー後に**実際に改変された** artifact を選ぶ
    drifted = [a for a, dg in data["reviewed_artifact_digests"].items()
               if (ROOT / a).exists()
               and hashlib.sha256((ROOT / a).read_bytes()).hexdigest()[:16] != dg]
    assert drifted, "レビュー後に改変された artifact が無く、この分岐を検査できない"
    art = drifted[0]
    now = hashlib.sha256((ROOT / art).read_bytes()).hexdigest()[:16]
    successor = dict(data, review_id="REV-TEST-SUCCESSOR", verdict="Go",
                     supersedes_review=[data["review_id"]],
                     # 現行 digest を **別の artifact キー**にだけ載せる
                     reviewed_artifact_digests={"CLAUDE.md": now})
    (dst / "successor.json").write_text(
        json.dumps(successor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(review_binding, "REVIEWS", dst)
    faults = review_binding.detect_review_faults(CTX)
    assert any("レビュー後に改変" in f and art in f for f in faults), \
        "別 artifact の digest 一致で改変が引き継がれている"


def test_mutation_unknown_target_commit_is_detected(monkeypatch, tmp_path) -> None:
    """変異: 実在しない target_commit を素通りさせない。"""
    faults = _faults(monkeypatch, _review_dir(tmp_path, target_commit="0" * 40))
    assert any("target_commit がリポジトリに存在しない" in f for f in faults)



def test_committed_review_gets_no_grace_for_target_tree() -> None:
    """コミット済みのレビュー成果物には target_tree 猶予が効かない（CI で必ず厳密検査）。"""
    for p in sorted((ROOT / "docs/00-authority/reviews").glob("*.json")):
        if p.name == "review.schema.json" or not review_binding.is_committed(p):
            continue
        import json
        r = json.loads(p.read_text(encoding="utf-8"))
        assert r["target_tree"] == review_binding.commit_tree(r["target_commit"]), p.name


def test_mutation_out_of_repo_path_is_not_granted_grace(tmp_path) -> None:
    """変異: リポジトリ外のパスを未コミット扱いにして猶予を得られない（fail-close）。"""
    assert review_binding.is_committed(tmp_path / "ghost.json") is True
    assert review_binding.is_committed(ROOT / "CLAUDE.md") is True
