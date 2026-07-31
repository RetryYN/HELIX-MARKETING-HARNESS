"""レビュー束縛ゲート: レビュー成果物を対象コミット・成果物 digest・後続レビューへ束縛する。

物理移行（PO 指示 §1）後も過去のレビューを検証できるよう、旧パスは manifest の
`previous_paths` を通じて現行 canonical/view パスへ解決する。レビュー後の内容変更は
`supersedes_review` で明示的に後続 Go レビューへ引き継がれている場合のみ許容する。
"""

from __future__ import annotations

import hashlib
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
    """review_id を supersedes_review に挙げる Go レビューを推移的に集める。"""
    out: list[dict] = []
    frontier = [review_id]
    seen = {review_id}
    while frontier:
        cur = frontier.pop()
        for r in reviews.values():
            if cur in (r.get("supersedes_review") or []) and r["review_id"] not in seen:
                seen.add(r["review_id"])
                if r.get("verdict") == "Go":
                    out.append(r)
                frontier.append(r["review_id"])
    return out


def is_committed(path: Path) -> bool:
    """ファイルが HEAD に存在する（＝コミット済み）か。"""
    return git("cat-file", "-e", f"HEAD:{rel(path)}").returncode == 0


def tree_is_reachable(tree: str) -> bool:
    """ツリーがいずれかのコミットのルートツリーとして到達可能か。

    `git write-tree` が作る dangling tree は**ローカルの object store にしか存在せず**、
    push されないため clone 先（CI）で解決できない。ローカルだけ緑になる穴を塞ぐ。
    """
    out = git("log", "--all", "--format=%T")
    return out.returncode == 0 and tree in out.stdout.split()


def detect_review_faults(ctx: Ctx) -> list[str]:
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
        if r.get("target_tree"):
            if git("cat-file", "-e", f"{r['target_tree']}^{{tree}}").returncode != 0:
                bad.append(f"{p.name}: target_tree がリポジトリに存在しない")
                continue
            # 成果物自体がコミット済みなら、target_tree も**コミットから到達可能**でなければならない。
            # `git write-tree` の dangling tree はローカルにしか無く、push・clone 先で解決できない
            # （作成直後＝未コミットの間は dangling で正常なので、その間は検査しない）。
            if is_committed(p) and not tree_is_reachable(r["target_tree"]):
                bad.append(f"{p.name}: target_tree {r['target_tree'][:12]} がコミットから到達不可"
                           "（dangling tree は clone 先で解決できない — コミット済みツリーへ束縛し直す）")
                continue
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
            if not any(now in n.get("reviewed_artifact_digests", {}).values() for n in succ):
                bad.append(f"{p.name}: {art} がレビュー後に改変（{dg}→{now}）— "
                           "supersedes_review で引き継ぐ後続 Go レビューがない")
    return bad


def run(ctx: Ctx) -> None:
    bad = detect_review_faults(ctx)
    gate("G-REVIEW-BINDING", not bad,
         f"レビュー成果物が対象コミット・成果物 digest・後続レビュー（supersedes_review）へ束縛 "
         f"(欠陥={bad[:4]})")
