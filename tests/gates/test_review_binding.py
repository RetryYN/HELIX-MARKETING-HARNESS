"""review_binding ゲートの単体テストと mutation test。"""

import json

from tools.gates import review_binding
from tools.gates.common import CTX, ROOT

# 実行証跡を取得できなかった過去のレビュー（ここへ追加することは証跡強度の後退にあたる）
HISTORICAL_UNVERIFIED = ["REV-S0-DESIGN-01", "REV-S0-DESIGN-02", "REV-S0-STRUCT-01",
                         "REV-S0-STRUCT-02", "REV-S0-STRUCT-03", "REV-S0-STRUCT-04",
                         "REV-S0-STRUCT-05", "REV-S0-STRUCT-06"]


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
    w = subprocess.run(["git", "write-tree"], capture_output=True, text=True, cwd=ROOT)
    # read-only な .git（CI のキャッシュ復元等）では write-tree できない。
    # その場合は「実在するが対象コミットのルートではないツリー」で同じ分岐を検査する。
    dangling = w.stdout.strip() if w.returncode == 0 else review_binding.commit_tree("HEAD")
    assert dangling
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
    import shutil

    src = ROOT / "docs/00-authority/reviews"
    dst = tmp_path / "isolated-reviews"
    dst.mkdir()
    shutil.copy(src / "review.schema.json", dst / "review.schema.json")
    shutil.copy(src / "sol-review-s0-structure-02.json", dst / "victim.json")
    data = json.loads((dst / "victim.json").read_text(encoding="utf-8"))
    data["target_commit"] = "0" * 40
    (dst / "victim.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
    faults = _faults(monkeypatch, dst)
    assert any("target_commit がリポジトリに存在しない" in f for f in faults)


def test_historical_missing_target_is_allowed_only_with_go_successor(monkeypatch, tmp_path) -> None:
    """squash 後に旧対象が消えても、後続 Go の再レビューがあれば履歴を保てる。"""
    import shutil

    src = ROOT / "docs/00-authority/reviews"
    dst = tmp_path / "reviews"
    shutil.copytree(src, dst)
    victim = dst / "sol-review-s0-structure-02.json"
    data = json.loads(victim.read_text(encoding="utf-8"))
    data["target_commit"] = "0" * 40
    data["target_tree"] = "1" * 40
    victim.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    successor = dict(data, review_id="REV-TEST-HISTORICAL-SUCCESSOR",
                     target_commit="5846ba66dac5c43187739e43d1fc7f9d4eda48c7",
                     target_tree=review_binding.commit_tree("HEAD"),
                     supersedes_review=[data["review_id"]])
    # The successor is a gate-fixture only; its target artifacts are the current
    # tree so the test exercises the historical-object branch, not digest carryover.
    import hashlib
    successor["reviewed_artifact_digests"] = {
        a: hashlib.sha256((ROOT / a).read_bytes()).hexdigest()[:16]
        for a in data["reviewed_artifact_digests"] if (ROOT / a).exists()
    }
    (dst / "successor.json").write_text(
        json.dumps(successor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(review_binding, "REVIEWS", dst)
    faults = review_binding.detect_review_faults(CTX)
    assert not any("sol-review-s0-structure-02.json" in f
                   and ("target_commit" in f or "target_tree" in f) for f in faults), faults


def test_missing_target_without_successor_remains_fail_close(monkeypatch, tmp_path) -> None:
    """後続レビューなしの最新成果物は target object 欠落を許容しない。"""
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


# --- レビュー主体の分離を実行証跡へ束縛（PO 指示 §3）---

def _sep(tmp_path, log_text=None, tracked=None, **over):
    """self_attested なレビュー 1 件を組み立て、指定欄だけ変異させて検査する。"""
    import hashlib
    log = tmp_path / "docs/00-authority/reviews/logs/REV-TEST.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    if log_text is None:
        log_text = ('{"type":"session_meta","payload":{"id":"run-id-EXEC-REVIEWER-0001"}}\n'
                    '{"type":"turn_context","payload":{"model":"gpt-5.6-sol"}}\n')
    log.write_text(log_text, encoding="utf-8")
    r = {
        "review_id": "REV-TEST",
        "separation_status": "self_attested",
        "author_principal": "claude-code",
        "author_execution_id": "EXEC-AUTHOR-0001",
        "reviewer_principal": "codex-sol",
        "reviewer_execution_id": "run-id-EXEC-REVIEWER-0001",
        "review_run_id": "RUN-1",
        "reviewer_provider": "openai-codex-cli",
        "review_log_path": "docs/00-authority/reviews/logs/REV-TEST.jsonl",
        "review_log_digest": hashlib.sha256(log.read_bytes()).hexdigest()[:16],
        "model": "gpt-5.6-sol",
    }
    r.update(over)
    if tracked is None:
        tracked = {"docs/00-authority/reviews/logs/REV-TEST.jsonl"}
    return review_binding.detect_separation_faults([r], root=tmp_path, tracked=tracked)


def test_separation_self_attested_case_is_clean(tmp_path) -> None:
    assert _sep(tmp_path) == []


def test_mutation_same_execution_id_is_detected(tmp_path) -> None:
    """変異: 同一実行での自己レビューを『独立レビュー』と名乗れない。"""
    faults = _sep(tmp_path, author_execution_id="run-id-EXEC-REVIEWER-0001")
    assert any("同一" in f and "execution_id" in f for f in faults)


def test_mutation_same_principal_is_detected(tmp_path) -> None:
    faults = _sep(tmp_path, author_principal="codex-sol")
    assert any("principal が同一" in f for f in faults)


def test_mutation_forged_log_digest_is_detected(tmp_path) -> None:
    """変異: 実在ログと一致しない digest では self_attested を名乗れない。"""
    faults = _sep(tmp_path, review_log_digest="0" * 16)
    assert any("実在ログと不一致" in f for f in faults)


def test_mutation_missing_log_is_detected(tmp_path) -> None:
    faults = _sep(tmp_path, review_log_path="docs/00-authority/reviews/logs/ghost.jsonl")
    assert any("実在しない" in f for f in faults)


def test_mutation_log_without_execution_id_is_detected(tmp_path) -> None:
    """変異: ログがそのレビュー実行のものだと示せない（execution_id を含まない）。"""
    faults = _sep(tmp_path,
                  log_text='{"type":"session_meta","payload":{"id":"OTHER"}}\n'
                           '{"type":"turn_context","payload":{"model":"gpt-5.6-sol"}}\n')
    assert any("セッション ID として申告していない" in f for f in faults)


def test_mutation_missing_evidence_fields_are_detected(tmp_path) -> None:
    faults = _sep(tmp_path, review_run_id="")
    assert any("self_attested なのに" in f for f in faults)


def test_unverified_must_not_claim_separation_evidence(tmp_path) -> None:
    """証跡を取得できないレビューは分離を主張しない（PO 判断へ送る）。"""
    r = {"review_id": "REV-X", "separation_status": "unverified",
         "reviewer_principal": "codex-sol", "author_execution_id": "EXEC-1"}
    faults = review_binding.detect_separation_faults([r], root=tmp_path)
    assert any("分離証跡欄" in f for f in faults)
    assert review_binding.detect_separation_faults(
        [{"review_id": "REV-X", "separation_status": "unverified",
          "reviewer_principal": "codex-sol"}], root=tmp_path) == []


def test_mutation_missing_separation_status_is_detected(tmp_path) -> None:
    faults = review_binding.detect_separation_faults([{"review_id": "REV-Y"}], root=tmp_path)
    assert any("separation_status" in f for f in faults)


def test_real_reviews_declare_separation_status() -> None:
    assert review_binding.detect_separation_faults(
        [__import__("json").loads(p.read_text(encoding="utf-8"))
         for p in sorted((ROOT / "docs/00-authority/reviews").glob("*.json"))
         if p.name != "review.schema.json"]) == []


def test_log_declarations_requires_typed_records(tmp_path) -> None:
    """変異: 任意テキスト・任意の入れ子では実行証跡にならない（型付きレコードを要求）。"""
    ok = ('{"type":"session_meta","payload":{"id":"S-1"}}\n'
          '{"type":"turn_context","payload":{"model":"m-1"}}\n')
    assert review_binding.log_declarations(ok) == ({"S-1"}, {"m-1"})
    assert review_binding.log_declarations("session S-3 model m-1 のログ") == (set(), set())
    faults = _sep(tmp_path,
                  log_text="reviewer_execution_id=run-id-EXEC-REVIEWER-0001 model gpt-5.6-sol")
    assert any("セッション ID として申告していない" in f for f in faults)


def test_mutation_untyped_id_and_prose_model_forgery_is_detected(tmp_path) -> None:
    """変異: 無関係な入れ子の id と本文のモデル名で証跡を偽装できない（R2-01）。"""
    log = ('{"note":{"id":"run-id-EXEC-REVIEWER-0001"}}\n'
           '{"type":"message","text":"gpt-5.6-sol でレビューしました"}\n')
    faults = _sep(tmp_path, log_text=log)
    assert any("セッション ID として申告していない" in f for f in faults), faults
    assert any("turn_context" in f for f in faults), faults


def test_mutation_model_declared_only_in_session_record_is_detected(tmp_path) -> None:
    """変異: モデルを session_meta へ紛れ込ませても turn_context の申告としては数えない。"""
    log = ('{"type":"session_meta","payload":{"id":"run-id-EXEC-REVIEWER-0001",'
           '"model":"gpt-5.6-sol"}}\n')
    faults = _sep(tmp_path, log_text=log)
    assert any("turn_context" in f for f in faults), faults


def test_mutation_untracked_log_is_detected(tmp_path) -> None:
    """変異: git 未追跡のログでは clone 先で検証できないため self_attested を名乗れない。"""
    faults = _sep(tmp_path, tracked=set())
    assert any("git 未追跡" in f for f in faults)


def test_mutation_unverified_review_claiming_independence_is_detected(tmp_path) -> None:
    """変異: 証跡が無いレビューが散文で「独立レビュー」を名乗れない。"""
    r = {"review_id": "REV-Z", "separation_status": "unverified",
         "reviewer_principal": "codex-sol", "scope": "独立レビュー（S0 設計）"}
    faults = review_binding.detect_separation_faults([r], root=tmp_path)
    assert any("散文で独立性を主張" in f for f in faults)


def test_real_unverified_reviews_do_not_claim_independence() -> None:
    import json
    for p in sorted((ROOT / "docs/00-authority/reviews").glob("*.json")):
        if p.name == "review.schema.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("separation_status") != "unverified":
            continue
        blob = json.dumps(d, ensure_ascii=False)
        for w in review_binding.INDEPENDENCE_CLAIMS:
            assert w not in blob, f"{p.name}: {w}"


def test_mutation_top_level_declaration_without_payload_is_detected(tmp_path) -> None:
    """変異: payload を伴わないトップレベル申告を証跡として受理しない（独立レビュー R3-01）。"""
    log = ('{"type":"session_meta","id":"run-id-EXEC-REVIEWER-0001"}\n'
           '{"type":"turn_context","model":"gpt-5.6-sol"}\n')
    assert review_binding.log_declarations(log) == (set(), set())
    faults = _sep(tmp_path, log_text=log)
    assert any("セッション ID として申告していない" in f for f in faults), faults


def test_mutation_scalar_payload_does_not_fall_back(tmp_path) -> None:
    """変異: payload が辞書でないレコードでレコード全体を読ませない。"""
    log = ('{"type":"session_meta","payload":null,"id":"run-id-EXEC-REVIEWER-0001"}\n'
           '{"type":"turn_context","payload":"x","model":"gpt-5.6-sol"}\n')
    assert review_binding.log_declarations(log) == (set(), set())


# --- 証跡の出所の 3 値化（PO 指示 §5）---


def test_mutation_local_log_cannot_claim_third_party_verification(tmp_path) -> None:
    """変異: ローカル生成ログしかない self_attested が第三者検証を名乗れない。"""
    faults = _sep(tmp_path, reviewer_provider="openai-codex-cli（第三者署名あり）")
    assert any("第三者検証を主張" in f for f in faults), faults


def test_mutation_self_attested_with_ci_fields_is_detected(tmp_path) -> None:
    faults = _sep(tmp_path, ci_run_id="30707844728")
    assert any("ci_attested" in f for f in faults), faults


RUN_ID = "30707844728"
RUN_URL = f"https://github.com/RetryYN/HELIX-MARKETING-HARNESS/actions/runs/{RUN_ID}"


def _ci(tmp_path, att=None, **over):
    """ci_attested のレビュー 1 件を、リポジトリ内 CI attestation ごと組み立てる。"""
    import hashlib
    _sep(tmp_path)   # 実行ログを先に作る（attestation は**そのログ**へ束縛される）
    (tmp_path / review_binding.WORKFLOW_DIR).mkdir(parents=True, exist_ok=True)
    (tmp_path / review_binding.WORKFLOW_DIR / "python-ci.yml").write_text("name: x\n",
                                                                          encoding="utf-8")
    log = tmp_path / "docs/00-authority/reviews/logs/REV-TEST.jsonl"
    body = {"repository": "RetryYN/HELIX-MARKETING-HARNESS", "workflow": "python-ci.yml",
            "run_id": RUN_ID, "head_sha": "c" * 40, "target_tree": "d" * 40,
            "artifact_name": "review-log",
            "artifact_digest": hashlib.sha256(log.read_bytes()).hexdigest()}
    if att:
        body.update(att)
    q = tmp_path / f"{review_binding.ATTESTATIONS}/REV-TEST.json"
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    tracked = {"docs/00-authority/reviews/logs/REV-TEST.jsonl",
               f"{review_binding.ATTESTATIONS}/REV-TEST.json"}
    over.setdefault("ci_log_digest", hashlib.sha256(q.read_bytes()).hexdigest())
    over.setdefault("ci_run_url", RUN_URL)
    over.setdefault("ci_workflow", "python-ci.yml")
    over.setdefault("ci_artifact_name", "review-log")
    return _sep(tmp_path, tracked=tracked, separation_status="ci_attested",
                ci_run_id=RUN_ID, target_commit="c" * 40, target_tree="d" * 40, **over)


def test_ci_attested_requires_run_binding(tmp_path) -> None:
    assert any("ci_attested なのに" in f
               for f in _sep(tmp_path, separation_status="ci_attested")), "欄なしで通る"
    # 束縛が全部そろっていても、検証鍵が未配備なら第三者性は成立しない（fail-close）
    assert any("検証鍵" in f for f in _ci(tmp_path)), _ci(tmp_path)


def test_ci_attested_is_unreachable_without_trusted_keys(tmp_path) -> None:
    """ローカルで整合的な attestation 一式を作っても ci_attested は名乗れない。"""
    assert _ci(tmp_path) != []
    assert not (ROOT / review_binding.TRUSTED_KEYS).exists(), \
        "検証鍵を配備するなら署名検証の実装が先に要る"


def test_mutation_ci_attested_without_attestation_file_is_detected(tmp_path) -> None:
    """変異: run ID と URL の形だけでは第三者検証を名乗れない（attestation 不在）。"""
    faults = _sep(tmp_path, separation_status="ci_attested", ci_run_id=RUN_ID,
                  ci_run_url=RUN_URL, ci_log_digest="a" * 64,
                  ci_workflow="python-ci.yml", ci_artifact_name="review-log")
    assert any("attestation" in f and "が無い" in f for f in faults), faults


def test_mutation_ci_attestation_for_another_commit_is_detected(tmp_path) -> None:
    """変異: 別コミットの CI 実行を流用できない。"""
    faults = _ci(tmp_path, att={"head_sha": "f" * 40})
    assert any("head_sha" in f for f in faults), faults


def test_mutation_ci_attestation_digest_mismatch_is_detected(tmp_path) -> None:
    faults = _ci(tmp_path, ci_log_digest="a" * 64)
    assert any("ci_log_digest" in f for f in faults), faults


def test_mutation_ci_url_not_matching_run_id_is_detected(tmp_path) -> None:
    """変異: run ID と対応しない URL で ci_attested を名乗れない。"""
    url = "https://github.com/RetryYN/HELIX-MARKETING-HARNESS/actions/runs/99999999999"
    faults = _ci(tmp_path, ci_run_url=url)
    assert any("ci_run_url" in f for f in faults), faults


def test_mutation_legacy_verified_status_is_rejected(tmp_path) -> None:
    """変異: 旧語彙 verified は出所を語らないので受け付けない。"""
    faults = _sep(tmp_path, separation_status="verified")
    assert any("separation_status" in f for f in faults), faults


def test_real_reviews_use_the_three_valued_status() -> None:
    import json

    from tools.gates.common import REVIEWS
    got = {}
    for q in sorted(REVIEWS.glob("*.json")):
        if q.name == "review.schema.json":
            continue
        d = json.loads(q.read_text(encoding="utf-8"))
        got.setdefault(d["separation_status"], []).append(d["review_id"])
    assert set(got) <= set(review_binding.SEPARATION_STATUSES)
    # 期待は**構造**で書く（レビューを 1 件足すたびに固定リストを直す自己参照を避ける）。
    # ラチェット: 証跡なし（unverified）を名乗れるのは過去の 8 件だけで、新しいレビューは
    # 必ず self_attested 以上。ci_attested は検証鍵が未配備のため誰も名乗れない。
    assert sorted(got.get("unverified", [])) == HISTORICAL_UNVERIFIED
    assert set(got.get("self_attested", [])) >= {"REV-S0-STRUCT-07", "REV-S0-STRUCT-08",
                                                 "REV-S0-STRUCT-09"}
    assert "ci_attested" not in got


def test_mutation_ci_attestation_for_another_artifact_is_detected(tmp_path) -> None:
    """変異: CI が公開した artifact がレビュー実行ログでない場合を落とす。"""
    faults = _ci(tmp_path, att={"artifact_digest": "e" * 64})
    assert any("artifact_digest" in f for f in faults), faults


def test_mutation_ci_attestation_unknown_workflow_is_detected(tmp_path) -> None:
    """変異: リポジトリに実在しない workflow を名乗れない。"""
    faults = _ci(tmp_path, att={"workflow": "ghost.yml"}, ci_workflow="ghost.yml")
    assert any("実在しない" in f for f in faults), faults


def test_mutation_ci_attestation_name_mismatch_is_detected(tmp_path) -> None:
    faults = _ci(tmp_path, att={"artifact_name": "other"})
    assert any("artifact_name" in f for f in faults), faults


def test_ci_attestation_directory_is_git_tracked_in_production(monkeypatch) -> None:
    """本番配線: run() が attestations も git ls-files の収集対象に渡す（独立レビュー R2-02）。"""
    calls: list[tuple] = []
    real = review_binding.git

    def spy(*args):
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(review_binding, "git", spy)
    monkeypatch.setattr(review_binding, "gate", lambda *a, **k: None)
    monkeypatch.setattr(review_binding, "detect_review_faults", lambda ctx, notes=None: [])
    seen: dict = {}
    monkeypatch.setattr(review_binding, "detect_separation_faults",
                        lambda reviews, tracked=None, **k: seen.setdefault("tracked", tracked) and [])
    review_binding.run(CTX)
    ls = [c for c in calls if c and c[0] == "ls-files"]
    assert ls, "run() が git ls-files を呼んでいない"
    assert any(review_binding.ATTESTATIONS in a for a in ls[0]), ls[0]
    assert seen["tracked"] is not None
