"""レビュー束縛ゲート: レビュー成果物を対象コミット・成果物 digest・後続レビューへ束縛する。

物理移行（PO 指示 §1）後も過去のレビューを検証できるよう、旧パスは manifest の
`previous_paths` を通じて現行 canonical/view パスへ解決する。レビュー後の内容変更は
`supersedes_review` で明示的に後続 Go レビューへ引き継がれている場合のみ許容する。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.gates.common import (
    REVIEWS,
    ROOT,
    Ctx,
    gate,
    git,
    git_bytes,
    load,
    rel,
    schema_check,
)


def path_resolver(ctx: Ctx) -> dict[str, str]:
    """旧パス → 現行パスの解決表（manifest の previous_paths / canonical / view から構築）。"""
    table: dict[str, str] = {}
    for it in ctx.manifest_items:
        for old in it.get("previous_paths", []):
            table[old] = it["canonical_path"]
        for old in it.get("previous_view_paths", []) or []:
            if it.get("view_path"):
                table[old] = it["view_path"]
        table[it["canonical_path"]] = it["canonical_path"]
        if it.get("view_path"):
            table[it["view_path"]] = it["view_path"]
    # ゲート実装自身の移動（validator → tools/gates）もレビュー対象になり得る
    table.setdefault("scripts/validate_requirements.py", "scripts/validate_requirements.py")
    return table


def successors(reviews: dict[str, dict], review_id: str) -> list[dict]:
    """review_id を supersedes_review に挙げる **Go レビュー**を推移的に集める。

    No-Go を跨いだ継承は認めない（No-Go で止める）。No-Go の先の Go は「No-Go を引き継いだ
    レビュー」であって、元レビューの判定を引き継ぐ鎖ではない（独立レビュー R4-05）。
    """
    out: list[dict] = []
    frontier = [review_id]
    seen = {review_id}
    while frontier:
        cur = frontier.pop()
        for r in reviews.values():
            if cur in (r.get("supersedes_review") or []) and r["review_id"] not in seen:
                seen.add(r["review_id"])
                if r.get("verdict") != "Go":
                    continue  # No-Go で鎖を止める
                out.append(r)
                frontier.append(r["review_id"])
    return out


def commit_tree(commit: str) -> str | None:
    """コミットのルートツリー sha を返す（解決できなければ None）。

    `git log --all` による到達可能性の走査は使わない。`--all` は ref から辿れる範囲しか
    見ないため detached HEAD や shallow clone で結果が変わり、CI の checkout 深度に暗黙依存する。
    target_commit のルートツリーとの **O(1) 厳密一致** はこの依存を持たず、
    「dangling tree（push されず clone 先で解決できない）」と「別コミットのツリーへの掏替え」を
    同時に落とす（独立レビュー REV-S0-STRUCT-02 の deferred 対応）。
    """
    out = git("rev-parse", "--verify", "--quiet", f"{commit}^{{tree}}")
    tree = out.stdout.strip()
    return tree if out.returncode == 0 and tree else None


def is_committed(path: Path) -> bool:
    """レビュー成果物が HEAD に存在する（＝コミット済み）か。

    リポジトリ外のパス（検査用の複製）は「猶予しない」側へ倒す（fail-close）。
    """
    try:
        r = rel(path)
    except ValueError:
        return True
    return git("cat-file", "-e", f"HEAD:{r}").returncode == 0


def detect_review_faults(ctx: Ctx, notes: list[str] | None = None) -> list[str]:
    """レビュー成果物の束縛欠陥を列挙する。

    唯一の猶予は**未コミットのレビュー成果物**に対する `target_tree` 一致検査である。
    レビューはそれ自身を含むコミットを対象にするため、作成時点では対象コミットの sha が
    決まらない（自己参照）。作成直後は `git write-tree` のツリーへ暫定束縛し、
    対象コミットの確定後にコミット済みツリーへ再束縛する 2 段構成を取る。
    猶予は `notes` へ記録され、ゲート出力に「CIで未検証」として必ず現れる。
    CI は当該コミットを checkout するためレビュー成果物は常にコミット済みで、猶予は効かない。
    """
    schema = load(REVIEWS / "review.schema.json")
    paths = sorted(p for p in REVIEWS.glob("*.json") if p.name != "review.schema.json")
    bad: list[str] = []
    if not paths:
        return ["レビュー成果物が 1 件もない（Go をコミットメッセージだけで記録しない）"]
    reviews = {load(p)["review_id"]: load(p) for p in paths}
    resolver = path_resolver(ctx)
    for p in paths:
        r = load(p)
        bad += [f"{p.name}: {e}" for e in schema_check(schema, r)]
        if any(f.get("status") == "resolved" for f in r.get("findings", [])) \
                and not r.get("resolution_commits"):
            bad.append(f"{p.name}: resolved な finding があるのに resolution_commits が空")
        for sid in r.get("supersedes_review") or []:
            if sid not in reviews:
                bad.append(f"{p.name}: supersedes_review の {sid} が存在しない")
        is_go = r.get("verdict") == "Go"
        if git("cat-file", "-e", f"{r['target_commit']}^{{commit}}").returncode != 0:
            bad.append(f"{p.name}: target_commit がリポジトリに存在しない")
            continue
        if not r.get("target_tree"):
            # キー欠落で厳密一致検査ごとスキップさせない（束縛が amend 可能な commit 側へ退化する）
            bad.append(f"{p.name}: target_tree がない（レビュー対象ツリーへ束縛されていない）")
            continue
        if git("cat-file", "-e", f"{r['target_tree']}^{{tree}}").returncode != 0:
            bad.append(f"{p.name}: target_tree がリポジトリに存在しない")
            continue
        # target_tree は target_commit のルートツリーと**厳密一致**でなければならない。
        # `git write-tree` の dangling tree はローカルにしか無く push・clone 先で解決できない。
        # 別コミットのツリーへの掏替えも同じ検査で落ちる。
        # 唯一の例外は**未コミットのレビュー成果物**（docstring 参照 — 自己参照のブートストラップ）で、
        # 猶予は notes に記録されゲート出力へ「CIで未検証」として必ず現れる。
        want = commit_tree(r["target_commit"])
        if r["target_tree"] != want:
            if is_committed(p):
                bad.append(f"{p.name}: target_tree が target_commit のルートツリーと不一致"
                           f"（記録 {r['target_tree'][:12]} / 実 {(want or '解決不能')[:12]}）")
                continue
            if notes is not None:
                notes.append(f"{p.name}: 未コミットのため target_tree 一致検査を猶予")
        succ = successors(reviews, r["review_id"])
        # 凍結対象: target_tree があればツリー（amend で動かせない）、無ければ target_commit
        frozen = r.get("target_tree") or r["target_commit"]
        where = "target_tree" if r.get("target_tree") else "target_commit"
        for art, dg in r["reviewed_artifact_digests"].items():
            blob = git_bytes("show", f"{frozen}:{art}")
            if blob.returncode != 0:
                bad.append(f"{p.name}: {art} が {where} に存在しない")
                continue
            at_commit = hashlib.sha256(blob.stdout).hexdigest()[:16]
            if at_commit != dg:
                bad.append(f"{p.name}: {art} の digest が {where} の内容と不一致"
                           f"（記録 {dg} / 実 {at_commit}）")
                continue
            if not is_go:
                continue
            current = resolver.get(art, art)
            fp = ROOT / current
            if not fp.exists():
                bad.append(f"{p.name}: {art}（現行 {current}）不在")
                continue
            now = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
            if now == dg:
                continue
            # digest 値の集合ではなく **artifact キーに束縛**して照合する
            # （別 artifact に同一 digest があるだけで通る偽陰性を塞ぐ — 独立レビュー R4-04）
            if not any(n.get("reviewed_artifact_digests", {}).get(art) == now
                       or n.get("reviewed_artifact_digests", {}).get(current) == now
                       for n in succ):
                bad.append(f"{p.name}: {art} がレビュー後に改変（{dg}→{now}）— "
                           "supersedes_review で引き継ぐ後続 Go レビューがない")
    return bad


SEPARATION_FIELDS = ("author_principal", "author_execution_id", "reviewer_principal",
                     "reviewer_execution_id", "review_run_id", "reviewer_provider",
                     "review_log_path", "review_log_digest")
# unverified のレビューが散文で分離を主張していないか（値のどこにも現れてはならない語）
INDEPENDENCE_CLAIMS = ("独立レビュー", "独立ブラインド", "別 principal", "別principal")


ID_KEYS = ("id", "session_id", "conversation_id")
MODEL_KEYS = ("model", "model_slug", "model_id")
SESSION_TYPES = ("session_meta", "session_start", "session")
TURN_TYPES = ("turn_context", "turn_start", "turn")


def _payload(rec: dict) -> dict:
    """レコードの payload。**辞書でなければ空**（レコード全体へ退避しない — 独立レビュー R3-01）。

    退避を許すと `{"type":"session_meta","id":"..."}` のようなトップレベル申告が通り、
    「型付きレコードの payload から読む」という強度が失われる。
    """
    p = rec.get("payload")
    return p if isinstance(p, dict) else {}


def log_declarations(text: str) -> tuple[set[str], set[str]]:
    """実行ログ（JSONL）が**型付きレコード**として申告するセッション ID とモデルを返す。

    部分文字列一致にしない（独立レビュー R1-03／R2-01）: セッション ID は `session_meta` 系、
    モデルは `turn_context` 系レコードの payload フィールドから読む。本文へ ID やモデル名を
    書いただけ・無関係な入れ子に `id` を置いただけでは申告として数えない。
    """
    ids: set[str] = set()
    models: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        kind = rec.get("type")
        body = _payload(rec)
        if kind in SESSION_TYPES:
            ids |= {v for k, v in body.items() if k in ID_KEYS and isinstance(v, str)}
        if kind in TURN_TYPES:
            models |= {v for k, v in body.items() if k in MODEL_KEYS and isinstance(v, str)}
    return ids, models


def detect_separation_faults(reviews: list[dict], root: Path = ROOT,
                             tracked: set[str] | None = None) -> list[str]:
    """レビュー主体の分離が**実行証跡**で確認できるかを検査する（PO 指示 §3）。

    `separation_status: verified` を名乗るには、作成側とレビュー側の principal・execution_id が
    **別**であり、`review_log_digest` がリポジトリ内の実在ログ（git 追跡下）と一致し、そのログが
    JSON レコードのフィールドとして `reviewer_execution_id` を申告し、レビュー成果物が記録する
    `model` をも含んでいなければならない。証跡を取得できないレビューは `unverified` として宣言し、
    分離を主張する欄を空にし、散文でも独立性を主張しない。

    限界（PO 判断事項）: 実行ログはレビュー実行者自身が生成するローカル成果物であり、
    本ゲートが保証するのは**構造的整合**（別実行・別 principal・ログとレビューの対応）までである。
    第三者による署名・改竄検知は本リポジトリの範囲外であり、監査記録に明示する。
    """
    bad: list[str] = []
    for r in reviews:
        rid = r.get("review_id", "?")
        status = r.get("separation_status")
        if status not in ("verified", "unverified"):
            bad.append(f"{rid}: separation_status が verified／unverified でない")
            continue
        if status == "unverified":
            claimed = [f for f in SEPARATION_FIELDS
                       if f != "reviewer_principal" and r.get(f)]
            if claimed:
                bad.append(f"{rid}: unverified なのに分離証跡欄 {claimed} を主張している")
            blob = json.dumps(r, ensure_ascii=False)
            said = [w for w in INDEPENDENCE_CLAIMS if w in blob]
            if said:
                bad.append(f"{rid}: 証跡が無いのに散文で独立性を主張している{said}")
            continue
        miss = [f for f in SEPARATION_FIELDS if not r.get(f)]
        if miss:
            bad.append(f"{rid}: verified なのに {miss} が無い")
            continue
        if r["author_execution_id"] == r["reviewer_execution_id"]:
            bad.append(f"{rid}: author_execution_id と reviewer_execution_id が同一"
                       "（同一実行での自己レビュー）")
        if r["author_principal"] == r["reviewer_principal"]:
            bad.append(f"{rid}: author_principal と reviewer_principal が同一")
        rel_log = r["review_log_path"]
        log = root / rel_log
        if not log.exists():
            bad.append(f"{rid}: review_log_path {rel_log} が実在しない")
            continue
        if tracked is not None and rel_log not in tracked:
            bad.append(f"{rid}: 実行ログ {rel_log} が git 未追跡（clone 先で検証できない）")
            continue
        got = hashlib.sha256(log.read_bytes()).hexdigest()[:16]
        if got != r["review_log_digest"]:
            bad.append(f"{rid}: review_log_digest が実在ログと不一致（記録 {r['review_log_digest']}"
                       f" / 実 {got}）")
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        ids, models = log_declarations(text)
        if r["reviewer_execution_id"] not in ids:
            bad.append(f"{rid}: 実行ログの session_meta が reviewer_execution_id を"
                       "セッション ID として申告していない（ログとレビュー実行が非束縛）")
        if r.get("model") and r["model"] not in models:
            bad.append(f"{rid}: 実行ログの turn_context がレビューモデル {r['model']} を"
                       "申告していない")
    return bad


def run(ctx: Ctx) -> None:
    notes: list[str] = []
    bad = detect_review_faults(ctx, notes)
    deferred = f" ※CIで未検証（未コミット猶予）: {notes}" if notes else ""
    gate("G-REVIEW-BINDING", not bad,
         f"レビュー成果物が対象コミット・そのルートツリー・成果物 digest・後続レビュー"
         f"（supersedes_review）へ束縛 (欠陥 {len(bad)} 件={bad[:4]}){deferred}")

    reviews = [load(p) for p in sorted(REVIEWS.glob("*.json")) if p.name != "review.schema.json"]
    listed = git("ls-files", "docs/00-authority/reviews/logs")
    tracked = {ln for ln in listed.stdout.splitlines() if ln}
    sep = detect_separation_faults(reviews, tracked=tracked)
    unverified = sorted(r["review_id"] for r in reviews
                        if r.get("separation_status") == "unverified")
    gate("G-REVIEW-SEPARATION", not sep,
         "レビュー主体の分離が実行証跡へ束縛（author≠reviewer の principal／execution_id・"
         f"実在ログとの digest 一致）(欠陥={sep[:3]}) ※証跡なし＝unverified: {unverified}")
