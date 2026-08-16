"""権威層ゲート: artifact manifest・物理構造・正本確定・旧体系隔離・現在地の一意性。

PO 指示 §1〜§4 に対応する。manifest（docs/00-authority/artifact-manifest.json）を
全成果物の権威正本とし、canonical／view／pair／status／digest／archive 非参照を fail-close 検査する。
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from tools.gates.common import (
    APPROVALS,
    ARCHIVE,
    AUTHORITY,
    CANON_CONTRACTS,
    LAYER_DIRS,
    LEGACY_ARCHIVED,
    MANIFEST,
    MANIFEST_SCHEMA,
    ROOT,
    S0_DU_MAX,
    Ctx,
    canonical_json_digest,
    doc_body_digest,
    gate,
    is_frozen,
    live_markdown,
    load,
    rel,
    schema_check,
    sha256_file,
    split_frontmatter,
)

# 現在地の正本文（README.md / CLAUDE.md はこの行以外の現在地表明を持たない — PO 指示 §3）
CURRENT_STATE_LINES = [
    "旧baselineの物理配置・manifest登録・既存ゲート配線まで完了。新要求の権威cutoverは未完了",
    "S0.1 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）",
    "S0.2 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）",
    "S0.3 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）",
    "Kanban／bounded domain／media binding は旧L3に要求記述だけ存在し、`revalidation_required`。FN／CMP降下とPO凍結は未完了",
    "ロジックツリー／統合因果分析（SR-17〜19）も旧L3に要求記述だけ存在し、AC／FN／CMP降下とPO凍結は未完了",
    "製品runtimeの配置方針はVPS `helix-worker`を採択済み。ただし製品runtime／service／Web UIは未実装・未配備である。Web UI・承認・通知要求を再定義中で、L2以降は未設計として再降下する",
    "HELIX-HARNESS はread-only参照。Python-native開発loopを方法論bridgeとして部分適応済みであり、完全adoptedではない。L2は5点書式の物理templateだけを用意した`bridge`で、内容は旧要求の評価用draftである。要件確定エンジン、IR/refinement/semantic admission、新要求からのL2再作成が全て閉じるまで導入済み・要求確定・設計済みと名乗らない",
]
FORBIDDEN_STATE_PHRASES = [
    "HELIX 経路で進める",
    "HELIX-HARNESS の工程で開始",
    "以降の工程は HELIX-HARNESS の Gate/PR 経路で進める",
]

# archive／superseded を参照してはならない現役導線（ゲート実装自身は隔離の検査主体なので対象外）
ISOLATION_TARGETS = [
    "README.md", "CLAUDE.md", "AGENTS.md",
    ".github/workflows/docs-ci.yml", ".github/workflows/python-ci.yml",
    "scripts/render_views.py", "scripts/validate_requirements.py",
    "scripts/check_skip_budget.py", "tests/conftest.py",
]
FROZEN_PREFIXES = ("docs/archive/", "docs/00-authority/superseded/")

# manifest に自分自身と、manifest の検証に使う台帳は登録しない（循環参照の回避）。
# これ以外の権威層成果物（ADR・リスク登録簿・ゲート台帳・監査記録）は登録対象。
SELF_REFERENTIAL = (
    "docs/00-authority/artifact-manifest.json",
    "docs/00-authority/artifact-manifest.schema.json",
    "docs/00-authority/baselines/",
    "docs/00-authority/approvals/",
    "docs/00-authority/reviews/",
)
CONTENT_BINDING_MIGRATIONS = AUTHORITY / "approvals" / "content-binding-migrations.json"
CONTENT_BINDING_ALGORITHM = "sha256_full_markdown_including_frontmatter_v1"
CONTENT_BINDING_MIGRATION_ALLOWLIST = {
    "AUTH-ADR-ADR-013-VPS-PRODUCT-UI-PRIMARY-HUMAN-INTERFACE": {
        "canonical_path": "docs/00-authority/adr/ADR-013-vps-product-ui-primary-human-interface.md",
        "approval_target": "ADR-013-vps-product-ui-primary-human-interface",
        "approval_version": "-",
        "prior_po_approval_digest": "0f523543dcec",
        "content_binding_digest": "e36352ef7e92",
        "source_commit": "7488e8516a17f2c7e20f731de66e7345578ef9fc",
    },
}


def _manifest_by_id(ctx: Ctx) -> dict[str, dict]:
    return {it["artifact_id"]: it for it in ctx.manifest_items}


def _approval_digests(ctx: Ctx) -> set[str]:
    """approvals.md の全承認行が持つ digest 集合。"""
    out: set[str] = set()
    for row in ctx.approvals.splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 8 and re.match(r"\d{4}-\d{2}-\d{2}", cells[1]):
            if re.fullmatch(r"[0-9a-f]{12}", cells[6]):
                out.add(cells[6])
    return out


def artifact_content_digest(path: Path) -> str:
    """成果物の内容 digest。

    契約 JSON は正準化 digest、それ以外は**frontmatter を含む全文**の sha256[:12]。
    frontmatter には slice／traces のようにゲートが正本として読む情報が入るため、承認束縛から外さない。
    """
    if path.suffix == ".json":
        data = load(path)
        if isinstance(data, dict) and "approval_digest" in data:
            return canonical_json_digest(data)
    return doc_body_digest(path)


def content_binding_migration_faults(ctx: Ctx, data: dict | None = None) -> list[str]:
    """既存PO承認と後発の全文digest補正を分離して検証する。"""
    if data is None:
        try:
            data = load(CONTENT_BINDING_MIGRATIONS)
        except (OSError, ValueError):
            return ["content-binding migration ledger 不在または不正"]
    faults: list[str] = []
    if not isinstance(data, dict) or set(data) != {"schema_version", "algorithm", "receipts"}:
        return ["content-binding migration ledger shape 不正"]
    if data.get("schema_version") != "1.0" or data.get("algorithm") != CONTENT_BINDING_ALGORITHM:
        faults.append("content-binding migration ledger version/algorithm 不正")
    receipts = data.get("receipts")
    if not isinstance(receipts, list):
        return faults + ["content-binding migration receipts が配列でない"]
    required = {
        "artifact_id", "canonical_path", "prior_po_approval_digest", "content_binding_digest",
        "source_commit", "migration_actor", "migration_reason", "semantic_unchanged",
        "grants_new_approval",
    }
    manifest = _manifest_by_id(ctx)
    approvals = _approval_digests(ctx)
    git_executable = shutil.which("git")
    if git_executable is None:
        return faults + ["content-binding migration検証用git executable不在"]
    seen: set[str] = set()
    for index, receipt in enumerate(receipts):
        label = f"migration[{index}]"
        if not isinstance(receipt, dict) or set(receipt) != required:
            faults.append(f"{label}:shape 不正")
            continue
        artifact_id = receipt.get("artifact_id")
        item = manifest.get(artifact_id) if isinstance(artifact_id, str) else None
        expected = (
            CONTENT_BINDING_MIGRATION_ALLOWLIST.get(artifact_id)
            if isinstance(artifact_id, str)
            else None
        )
        if artifact_id in seen:
            faults.append(f"{label}:artifact 重複")
        if isinstance(artifact_id, str):
            seen.add(artifact_id)
        if item is None or item.get("lifecycle_status") != "confirmed":
            faults.append(f"{label}:confirmed manifest artifact 不在")
            continue
        if expected is None:
            faults.append(f"{label}:code-exact migration allowlist 対象外")
            continue
        if any(receipt.get(key) != value for key, value in expected.items()
               if key not in {"approval_target", "approval_version"}):
            faults.append(f"{label}:code-exact migration allowlist 不一致")
        if receipt.get("canonical_path") != item.get("canonical_path"):
            faults.append(f"{label}:canonical path 不一致")
        prior = receipt.get("prior_po_approval_digest")
        if prior != item.get("approval_digest") or prior not in approvals:
            faults.append(f"{label}:既存PO承認digest 不一致または承認行なし")
        path = ROOT / item["canonical_path"]
        if receipt.get("content_binding_digest") != artifact_content_digest(path):
            faults.append(f"{label}:現内容digest 不一致")
        source_commit = receipt.get("source_commit")
        if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            faults.append(f"{label}:source commit 不正")
        else:
            ancestor = subprocess.run(  # noqa: S603 -- code-allowlisted commit and fixed git argv
                [git_executable, "merge-base", "--is-ancestor", source_commit, "HEAD"], cwd=ROOT,
                capture_output=True, check=False,
            )
            source_doc = subprocess.run(  # noqa: S603 -- code-allowlisted commit/path
                [git_executable, "show", f"{source_commit}:{item['canonical_path']}"], cwd=ROOT,
                capture_output=True, check=False,
            )
            approval_path = rel(APPROVALS)
            source_approvals = subprocess.run(  # noqa: S603 -- code-allowlisted commit/fixed path
                [git_executable, "show", f"{source_commit}:{approval_path}"], cwd=ROOT,
                capture_output=True, check=False,
            )
            if ancestor.returncode != 0:
                faults.append(f"{label}:source commit が実在HEAD祖先でない")
            if source_doc.returncode != 0 or hashlib.sha256(source_doc.stdout).hexdigest()[:12] != receipt.get(
                    "content_binding_digest"):
                faults.append(f"{label}:source commit blob digest 不一致")
            approval_row = (
                f"| 2026-08-14 | {expected['approval_target']} | {expected['approval_version']} | "
                f"confirmed | PO | {receipt.get('prior_po_approval_digest')} |"
            )
            if source_approvals.returncode != 0 or approval_row.encode() not in source_approvals.stdout:
                faults.append(f"{label}:source commit の対象別PO承認行不在")
        if receipt.get("migration_actor") != "tool:authority-content-binding-migration":
            faults.append(f"{label}:migration actor 不正")
        reason = receipt.get("migration_reason")
        if not isinstance(reason, str) or not reason.strip():
            faults.append(f"{label}:migration reason 欠落")
        if receipt.get("semantic_unchanged") is not True or receipt.get("grants_new_approval") is not False:
            faults.append(f"{label}:意味不変・非承認境界の違反")
    return faults


def _content_binding_migrations(ctx: Ctx, data: dict | None = None) -> dict[str, dict]:
    if content_binding_migration_faults(ctx, data):
        return {}
    ledger = data if data is not None else load(CONTENT_BINDING_MIGRATIONS)
    return {row["artifact_id"]: row for row in ledger["receipts"]}


# ---------------------------------------------------------------- 検出関数（mutation test が共用）
# 現役（凍結でない）authority_status。canonical の一意性は現役の全てに効かせる
LIVE_STATUSES = ("active",)


def detect_manifest_duplicates(items: list[dict]) -> list[str]:
    """artifact_id の重複と、同一 canonical_path を複数 artifact が主張する箇所を列挙する。

    一意性は **現役（authority_status=active）の全て**に効かせる。内容成熟度
    （lifecycle_status）による例外は設けない — draft を経由した重複主張の迂回を許さない。
    """
    bad: list[str] = []
    seen_ids: dict[str, int] = {}
    seen_canon: dict[str, list[str]] = {}
    for it in items:
        seen_ids[it["artifact_id"]] = seen_ids.get(it["artifact_id"], 0) + 1
        if it.get("authority_status") in LIVE_STATUSES:
            seen_canon.setdefault(it["canonical_path"], []).append(it["artifact_id"])
    bad += [f"artifact_id 重複:{k}" for k, n in seen_ids.items() if n > 1]
    bad += [f"canonical 重複主張:{p}={sorted(ids)}" for p, ids in seen_canon.items() if len(ids) > 1]
    return bad


def tracked_files(root: Path = ROOT) -> set[str] | None:
    """git 管理下のパス集合。取得できない場合は **None**（呼び側で違反にする）。

    空集合を返すと `elif tracked and ...` のような短絡ガードで検査そのものが消え、
    非 git ツリーや dubious ownership で fail-open になる（独立レビュー F-10）。
    """
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,  # noqa: S603, S607
                         check=False, cwd=root)
    return set(out.stdout.split("\n")) if out.returncode == 0 else None


def detect_manifest_path_faults(items: list[dict], root: Path = ROOT) -> list[str]:
    """canonical_path／view_path／previous_paths の実在・git 管理・凍結領域混入を列挙する。

    実在するだけでは足りない: untracked のまま登録された成果物は、ローカルだけ緑で
    CI の clone 先には存在しない（独立レビュー F-10）。
    """
    bad: list[str] = []
    tracked = tracked_files(root)
    if tracked is None:
        return ["git 管理下のファイル一覧を取得できない（git リポジトリでない／取得失敗 — fail-close）"]
    for it in items:
        cp = it["canonical_path"]
        if not (root / cp).exists():
            bad.append(f"{it['artifact_id']}:canonical 不在 {cp}")
        elif cp not in tracked:
            bad.append(f"{it['artifact_id']}:canonical が git 未追跡 {cp}（clone 先に存在しない）")
        elif cp.startswith(FROZEN_PREFIXES) and it.get("authority_status") == "active":
            bad.append(f"{it['artifact_id']}:現役 artifact の canonical が凍結領域 {cp}")
        vp = it.get("view_path")
        if vp is not None:
            if not (root / vp).exists():
                bad.append(f"{it['artifact_id']}:view 不在 {vp}")
            elif vp not in tracked:
                bad.append(f"{it['artifact_id']}:view が git 未追跡 {vp}（clone 先に存在しない）")
            elif "/views/" not in vp:
                bad.append(f"{it['artifact_id']}:view が views/ 外 {vp}")
        for pp in it.get("previous_paths", []):
            if (root / pp).exists():
                bad.append(f"{it['artifact_id']}:旧パスが残存 {pp}")
    return bad


def detect_manifest_pair_faults(items: list[dict]) -> list[str]:
    """pair_artifact_id の実在と対称性を列挙する。"""
    by_id = {it["artifact_id"]: it for it in items}
    bad: list[str] = []
    for it in items:
        pid = it.get("pair_artifact_id")
        if pid is None:
            continue
        other = by_id.get(pid)
        if other is None:
            bad.append(f"{it['artifact_id']}:pair 不在 {pid}")
        elif other.get("pair_artifact_id") != it["artifact_id"]:
            bad.append(f"{it['artifact_id']}↔{pid}:pair 非対称")
    return bad


def detect_unregistered(items: list[dict], root: Path = ROOT) -> list[str]:
    """現役階層にありながら manifest 未登録の成果物を列挙する（.gitkeep・README を除く）。"""
    registered = {it["canonical_path"] for it in items} | {
        it["view_path"] for it in items if it.get("view_path")}
    live: list[str] = []
    for layer in LAYER_DIRS:
        if layer in (ARCHIVE,):
            continue
        for p in sorted(layer.rglob("*")):
            if not p.is_file() or p.name == ".gitkeep" or is_frozen(p):
                continue
            if p.suffix not in (".md", ".json", ".sql"):
                continue
            r = rel(p)
            if any(r.startswith(x) for x in SELF_REFERENTIAL):
                continue  # manifest 自身と、manifest の digest 検証に使う台帳（循環回避）
            if r not in registered:
                live.append(r)
    return sorted(live)


def detect_duplicate_canonical_content(root: Path = ROOT) -> list[str]:
    """現役階層で内容が同一のファイル対を列挙する（同一正本の二重配置検出）。"""
    seen: dict[str, list[str]] = {}
    for p in sorted(root.glob("docs/**/*")):
        if not p.is_file() or p.name == ".gitkeep" or is_frozen(p):
            continue
        if p.suffix not in (".md", ".json", ".sql"):
            continue
        seen.setdefault(sha256_file(p), []).append(rel(p))
    return [f"{h[:8]}:{sorted(v)}" for h, v in seen.items() if len(v) > 1]


# ---------------------------------------------------------------- canonical／view の形式規律（§1）
# 「人間承認そのものが正本の文書」だけが canonical Markdown を名乗れる。
# JSON 正本（契約・台帳・schema・DDL）を持つ成果物の Markdown は必ず views/ の生成ビューになる。
MD_AUTHORITY_TYPES = frozenset({
    "charter",          # 憲章
    "policy",           # 方針・ゲート台帳・リスク登録簿
    "adr",              # 設計判断記録
    "audit-record",     # 監査・事故記録
    "design-doc",       # 設計判断文書
    "requirement-doc",  # 人間承認を伴う本文正本
    "test-design",      # 同上（検証設計）
})
FORMAT_BY_SUFFIX = {".md": "markdown", ".json": "json", ".sql": "sql"}
GENERATED_MARK = "GENERATED FILE"
GENERATED_WINDOW = 400  # 生成宣言はファイル先頭に置く（全ゲートで同一窓を使う）


def is_generated_view(p: Path) -> bool:
    """生成 MD か（先頭に GENERATED 宣言がある、又は本文のどこかに紛れている）。

    窓の外へ宣言を追い出して検査を外す迂回を塞ぐため、全文も見る。
    """
    txt = p.read_text(encoding="utf-8")
    return GENERATED_MARK in txt


def detect_format_faults(items: list[dict], root: Path = ROOT) -> list[str]:
    """canonical／view の形式規律違反を列挙する（PO 指示 §1）。

    (a) authority_format が canonical_path の拡張子と一致する
    (b) markdown 正本は MD_AUTHORITY_TYPES に限る（JSON 正本を持つ型の MD 登録を拒否）
    (c) view_generation と view_path の整合、view は views/ 配下の生成 MD
    (d) canonical に生成 MD（GENERATED 宣言つき）を登録しない
    (e) canonical と view の集合が交わらない（同一 MD の二枚看板を禁止）
    (f) 現役階層の生成 MD は必ずどれかの view_path として登録されている
    """
    bad: list[str] = []
    canon = {it["canonical_path"] for it in items}
    views = {it["view_path"] for it in items if it.get("view_path")}
    for it in items:
        aid, cp = it["artifact_id"], it["canonical_path"]
        want = FORMAT_BY_SUFFIX.get(Path(cp).suffix)
        fmt = it.get("authority_format")
        if want is None:
            bad.append(f"{aid}:canonical の拡張子が正本形式になりえない {cp}")
        elif fmt != want:
            bad.append(f"{aid}:authority_format={fmt} が canonical {cp} と不一致（想定 {want}）")
        if fmt == "markdown" and it["artifact_type"] not in MD_AUTHORITY_TYPES:
            bad.append(f"{aid}:artifact_type={it['artifact_type']} は canonical Markdown を持てない"
                       "（JSON 正本を持つ成果物の MD は views/ へ）")
        if fmt != "markdown" and Path(cp).suffix == ".md":
            bad.append(f"{aid}:MD を非 markdown 正本として登録 {cp}")
        if "/views/" in cp:
            bad.append(f"{aid}:canonical が views/ 配下 {cp}")
        vp = it.get("view_path")
        gen = it.get("view_generation")
        if (vp is not None) != (gen == "generated"):
            bad.append(f"{aid}:view_generation={gen} と view_path={vp} が不整合")
        p = root / cp
        if p.exists() and p.suffix == ".md" and is_generated_view(p):
            bad.append(f"{aid}:生成 MD を canonical に登録 {cp}")
    for it in items:
        vp = it.get("view_path")
        if vp and (root / vp).exists() \
                and GENERATED_MARK not in (root / vp).read_text(encoding="utf-8")[:GENERATED_WINDOW]:
            bad.append(f"{it['artifact_id']}:登録された view に GENERATED 宣言がない {vp}")
    for both in sorted(canon & views):
        bad.append(f"{both}:canonical と view の二枚看板")
    for p in sorted(root.glob("docs/**/*.md")):
        if is_frozen(p) or not is_generated_view(p):
            continue
        if rel(p) not in views:
            bad.append(f"{rel(p)}:生成 MD が view_path として未登録")
    return bad


# ---------------------------------------------------------------- status の意味分離（§3）
LIFECYCLE_PROSE = re.compile(r"^>\s*status:\s*\*{0,2}([a-z_]+)", re.M)
# 記録文書が本文で使う語 → lifecycle_status。ここに無い語は「語彙外」として落とす
# （本文で好きな status を名乗って manifest との突合を逃れることを許さない）
PROSE_TO_LIFECYCLE = {
    "draft": "draft", "confirmed": "confirmed", "planned": "planned",
    "in_progress": "in_progress", "completed": "completed",
    "active": "draft", "open": "draft", "reference": "draft",  # 進行中の記録・方針・参照表
    "closed": "completed", "withdrawn": "completed",  # 終了した記録
}


def detect_status_faults(items: list[dict], root: Path = ROOT) -> list[str]:
    """authority_status／lifecycle_status の規律と frontmatter 整合を列挙する（PO 指示 §3）。

    `authority_status` は現役導線上の位置だけを、`lifecycle_status` は内容成熟度だけを表す。
    markdown 正本は frontmatter に artifact_id／lifecycle_status を持ち、manifest と一致する。
    生成ビューは manifest 側の成熟度に従うため frontmatter を持たない。
    """
    bad: list[str] = []
    for it in items:
        aid, cp = it["artifact_id"], it["canonical_path"]
        auth, life = it.get("authority_status"), it.get("lifecycle_status")
        applicability = it.get("applicability_status")
        implementation_input = it.get("implementation_input")
        layer = it.get("layer")
        if layer in {"L0", "L1", "L2", "L3", "L4", "L5", "L6"}:
            if applicability not in {"revalidation_required", "proposal_only"}:
                bad.append(f"{aid}:requirements revising中の{layer}成果物がapplicability={applicability}")
            if implementation_input is not False:
                bad.append(f"{aid}:requirements revising中の{layer}成果物がimplementation_input=true")
        elif implementation_input is not False:
            bad.append(f"{aid}:requirements revising中にimplementation_input=true")
        if (life == "confirmed") != (it.get("approval_digest") is not None):
            bad.append(f"{aid}:lifecycle_status={life} と approval_digest={it['approval_digest']} が不整合"
                       "（confirmed のみ承認 digest を持つ）")
        frozen = cp.startswith(FROZEN_PREFIXES)
        if frozen and auth == "active":
            bad.append(f"{aid}:凍結領域なのに authority_status=active")
        if not frozen and auth != "active":
            bad.append(f"{aid}:authority_status={auth} なのに現役階層に置かれている {cp}")
        if it.get("authority_format") != "markdown":
            continue
        p = root / cp
        if not p.exists():
            continue
        fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
        if fm is None:
            bad.append(f"{aid}:markdown 正本に frontmatter がない {cp}")
            continue
        if fm.get("__malformed__"):
            bad.append(f"{aid}:frontmatter が平坦な key: value 形式でない {fm['__malformed__'][:1]}")
        if fm.get("artifact_id") != aid:
            bad.append(f"{aid}:frontmatter.artifact_id={fm.get('artifact_id')} が manifest と不一致")
        if fm.get("lifecycle_status") != life:
            bad.append(f"{aid}:frontmatter.lifecycle_status={fm.get('lifecycle_status')}"
                       f" が manifest の {life} と不一致")
        m = LIFECYCLE_PROSE.search(body)
        if m and PROSE_TO_LIFECYCLE.get(m.group(1)) != life:
            bad.append(f"{aid}:本文の status 行『{m.group(1)}』が lifecycle_status={life} と不一致"
                       "（語彙外か、manifest と食い違っている）")
    for it in items:
        vp = it.get("view_path")
        if vp and (root / vp).exists() and split_frontmatter(
                (root / vp).read_text(encoding="utf-8"))[0] is not None:
            bad.append(f"{it['artifact_id']}:生成ビューに frontmatter がある {vp}")
    return bad


# ---------------------------------------------------------------- 継承関係（§3）
RELATION_FIELDS = ("supersedes", "extends_artifact_ids", "depends_on_artifact_ids")
# supersedes は「完全置換」専用。置換された側は現役導線から降りていなければならない。
SUPERSEDED_STATUSES = frozenset({"superseded", "archived"})


def detect_relation_faults(items: list[dict]) -> list[str]:
    """artifact 間の置換・拡張・依存の参照整合を列挙する（PO 指示 §3）。

    (a) 参照先 artifact ID が manifest に実在する（存在しない旧 ID の参照を残さない）
    (b) supersedes の対象は authority_status ∈ {superseded, archived}
        — 現役成果物を supersedes に書けない（拡張は extends_artifact_ids）
    (c) 自己参照禁止（3 フィールドとも）
    (d) 同一フィールド内の重複禁止・置換と拡張の二重宣言禁止
    (e) 循環参照禁止（supersedes／extends／depends_on を辺とする有向グラフに閉路がない）
    """
    bad: list[str] = []
    by_id = {it["artifact_id"]: it for it in items}
    edges: dict[str, set[str]] = {}
    for it in items:
        aid = it["artifact_id"]
        seen_any: dict[str, str] = {}
        for f in RELATION_FIELDS:
            refs = it.get(f)
            if not isinstance(refs, list):
                bad.append(f"{aid}:{f} が配列でない")
                continue
            if len(refs) != len(set(refs)):
                bad.append(f"{aid}:{f} に重複した参照がある")
            for r in refs:
                if r == aid:
                    bad.append(f"{aid}:{f} が自己参照")
                    continue
                if r not in by_id:
                    bad.append(f"{aid}:{f} の参照先 {r} が manifest に存在しない")
                    continue
                if f == "supersedes" and by_id[r].get("authority_status") not in SUPERSEDED_STATUSES:
                    bad.append(
                        f"{aid}:supersedes の {r} は authority_status="
                        f"{by_id[r].get('authority_status')}（現役成果物は置換対象にできない"
                        "— 拡張なら extends_artifact_ids）")
                if r in seen_any:
                    bad.append(f"{aid}:{r} を {seen_any[r]} と {f} の両方で宣言している")
                else:
                    seen_any[r] = f
                edges.setdefault(aid, set()).add(r)
    bad += [f"循環参照:{c}" for c in _cycles(edges)]
    return bad


def _cycles(edges: dict[str, set[str]]) -> list[str]:
    """有向グラフの閉路を列挙する（DFS の三色塗り分け）。"""
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    found: list[str] = []

    def visit(n: str, path: list[str]) -> None:
        color[n] = GREY
        for m in sorted(edges.get(n, ())):
            c = color.get(m, WHITE)
            if c == GREY:
                found.append("→".join([*path[path.index(m):], m]) if m in path else f"{n}→{m}")
            elif c == WHITE:
                visit(m, [*path, m])
        color[n] = BLACK

    for n in sorted(edges):
        if color.get(n, WHITE) == WHITE:
            visit(n, [n])
    return sorted(set(found))


# ---------------------------------------------------------------- domain の語彙（§4）
SLICE_VOCAB = frozenset({"s0", "s1", "s2", "s3", "s3+", "later", "cross", "slice"})
SLICE_LIKE = re.compile(r"^s[0-9]+(\.[0-9]+)?\+?$", re.I)
DOMAIN_SHAPE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LAYER_VOCAB = frozenset({"00-authority", "l0", "l1", "l2", "l3", "l4", "l5", "l6"})


def detect_domain_faults(items: list[dict]) -> list[str]:
    """domain に slice 名・階層名が紛れ込んでいないかを列挙する（PO 指示 §4）。

    domain は**業務領域**だけを表す。スライス（いつ作るか）と階層（どの工程か）は
    それぞれ `slice`・`layer` が持つ軸であり、domain へ写すと分類軸が壊れる。
    """
    bad: list[str] = []
    for it in items:
        aid, d = it["artifact_id"], it.get("domain")
        if not isinstance(d, str):
            bad.append(f"{aid}:domain={d} が文字列でない")
            continue
        if not DOMAIN_SHAPE.fullmatch(d):
            # 形式違反でも語彙検査は続ける（大文字にするだけで slice 名検査を外せないように）
            bad.append(f"{aid}:domain={d} が小文字 kebab-case でない")
        low = d.lower()
        # 全体一致だけを見ると `s0-design` のような複合語で検査を外せる（独立レビュー R1-04）。
        # ハイフン単位のトークンでも語彙を拒否する。
        tokens = [low, *low.split("-")]
        if any(t in SLICE_VOCAB or SLICE_LIKE.fullmatch(t) for t in tokens):
            bad.append(f"{aid}:domain={d} に slice 名が含まれる（業務領域ではない）")
        if low == str(it.get("slice", "")).lower():
            bad.append(f"{aid}:domain={d} が slice と同値（分類軸の混同）")
        if any(t in LAYER_VOCAB for t in tokens):
            bad.append(f"{aid}:domain={d} に階層名が含まれる（layer が持つ軸）")
    return bad


# ---------------------------------------------------------------- スライス配置（§2・§5）
SLICE_ORDER = {"S0": 0, "S1": 1, "S2": 2, "S3+": 3, "later": 9}
L6_DIRS = ("S0", "S1", "later")
REQ_REF = re.compile(r"\b(FR|SR)-(\d+(?:/\d+)*)")
CODE_SPAN = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def _mentioned_requirements(body: str) -> set[str]:
    """本文（散文）が言及する FR／SR を列挙する（`FR-26/46` のような連記も展開する）。

    コードフェンス・インラインコードは走査から除く（識別子や例示コード中の ID を
    「後続スライスの実装を混ぜた」と誤検出しないため — 独立レビュー F-08）。
    """
    prose = CODE_SPAN.sub(" ", body)
    out: set[str] = set()
    for prefix, nums in REQ_REF.findall(prose):
        for n in nums.split("/"):
            out.add(f"{prefix}-{int(n):02d}")
    return out


def detect_slice_faults(ctx: Ctx, root: Path = ROOT) -> list[str]:
    """L6 機能設計の物理パス・manifest・本文・trace 先のスライス不一致を列挙する（PO 指示 §2）。

    (a) 物理ディレクトリ ＝ manifest.slice ＝ frontmatter.slice
    (b) frontmatter.traces は非空で、全て**同一スライス**の実在 FR／SR
    (c) 本文が言及する**後続スライス**の FR／SR は過不足なく forward_refs に宣言されている
        （S0 文書に S1 の強制実装を混ぜると、宣言漏れとして必ず落ちる）
    (d) DU の feature_design が実在し、S0 の DU が後続スライスの機能設計を入力にしない
    """
    bad: list[str] = []
    req_slice = {i["id"]: i["slice"] for i in ctx.allc}
    by_path = {it["canonical_path"]: it for it in ctx.manifest_items}

    l6 = root / "docs/L6-feature-design"
    stray = sorted(str(p.relative_to(root)) for p in l6.iterdir()
                   if p.name not in L6_DIRS and p.name != ".gitkeep")
    bad += [f"{s}:L6 直下は S0／S1／later のみ" for s in stray]

    doc_slice: dict[str, str] = {}
    declared_dus: dict[str, list] = {}
    bodies: dict[str, str] = {}
    for p in sorted(l6.rglob("*.md")):
        r = str(p.relative_to(root))
        phys = p.relative_to(l6).parts[0]
        doc_slice[r] = phys
        it = by_path.get(r)
        if it is None:
            bad.append(f"{r}:manifest 未登録")
            continue
        if it["slice"] != phys:
            bad.append(f"{r}:manifest.slice={it['slice']} が物理ディレクトリ {phys} と不一致")
        fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
        if fm is None:
            bad.append(f"{r}:frontmatter がない")
            continue
        if fm.get("slice") != phys:
            bad.append(f"{r}:frontmatter.slice={fm.get('slice')} が物理ディレクトリ {phys} と不一致")
        traces = fm.get("traces")
        if not isinstance(traces, list) or not traces:
            bad.append(f"{r}:traces が空（機能設計は根拠 FR／SR を持つ）")
            traces = []
        for t in traces:
            if t not in req_slice:
                bad.append(f"{r}:traces の {t} が FR／SR 契約に存在しない")
            elif req_slice[t] != phys:
                bad.append(f"{r}:traces の {t} は slice={req_slice[t]}"
                           f"（本書は {phys} — 別スライスの要求を根拠にできない）")
        declared_dus[r] = fm.get("dus") or []
        bodies[r] = body  # 突合は本文に対して行う（frontmatter の宣言自身を根拠にしない）
        declared = set(fm.get("forward_refs") or [])
        mentioned = _mentioned_requirements(body)
        # 本文の要求参照も実在性を fail-close 検査する（frontmatter だけ厳しく本文は素通り、を作らない）
        bad += [f"{r}:本文が実在しない要求 {i} を参照" for i in sorted(mentioned - set(req_slice))]
        actual = {i for i in mentioned
                  if i in req_slice and i not in traces
                  and SLICE_ORDER.get(req_slice[i], 9) > SLICE_ORDER.get(phys, 9)}
        if declared != actual:
            bad.append(f"{r}:forward_refs が本文の後続スライス言及と不一致"
                       f"（宣言={sorted(declared)} / 実際={sorted(actual)}）")
    # DU → 機能設計 の写像と、機能設計 frontmatter の `dus` 宣言を**双方向**に突き合わせる。
    # 片方向（DU 側だけ）だと、付替え先の文書が当該 DU を扱っていなくても通ってしまう。
    from_du: dict[str, set[str]] = {r: set() for r in doc_slice}
    for d in ctx.duc:
        du_slice = "S0" if int(d["id"][3:]) <= S0_DU_MAX else "S1"
        for f in d["trace"].get("feature_design", []):
            if f not in doc_slice:
                bad.append(f"{d['id']}:feature_design {f} が L6 機能設計として実在しない")
                continue
            from_du.setdefault(f, set()).add(d["id"])
            if SLICE_ORDER.get(doc_slice.get(f, ""), 9) > SLICE_ORDER.get(du_slice, 9):
                bad.append(f"{d['id']}({du_slice}):feature_design {f} が後続スライスの機能設計")
    for r, dus in sorted(from_du.items()):
        declared = set(declared_dus.get(r, []))
        if declared != dus:
            bad.append(f"{r}:frontmatter.dus が du-contracts の feature_design と不一致"
                       f"（宣言={sorted(declared)} / 実際={sorted(dus)}）")
        txt = bodies.get(r, "")
        # 内容の突合は S0 の DU に限る（test-first の対象＝実装が始まる単位）。
        # S1 以降の DU は⑤改訂で採番し直す段階にあり、機能設計側の記述粒度が揃っていない。
        for du in sorted(d for d in dus if int(d[3:]) <= S0_DU_MAX):
            acs: list[str] = next(
                (c["trace"].get("ac", []) for c in ctx.duc if c["id"] == du), [])
            if du not in txt and not any(a in txt for a in acs):
                bad.append(f"{r}:宣言した {du} も その AC も本文が扱っていない")
    return bad


MD_LINK = re.compile(r"\]\(([^)]+)\)")
EXCLUSION_HINTS = ("--exclude-path", "!docs/")


def _frozen_hits_in_code(txt: str) -> list[str]:
    """除外指示（lychee の --exclude-path・markdownlint の ! グロブ）以外での凍結領域参照。"""
    hits = []
    for line in txt.splitlines():
        if any(h in line for h in EXCLUSION_HINTS):
            continue
        for pref in FROZEN_PREFIXES:
            if pref in line:
                hits.append(pref)
    return hits


def detect_frozen_references(root: Path = ROOT, targets: list[str] | None = None) -> list[str]:
    """現役導線が archive／superseded を**入力として**参照している箇所を列挙する。

    散文での言及（規律の説明）と CI の除外指示は対象外。検出するのは
    (a) 現役 Markdown からの**リンク**、(b) 現役 JSON の**文字列値**、
    (c) スクリプト・CI が除外指示以外で凍結パスを扱う箇所。
    """
    bad: list[str] = []
    for t in (targets or ISOLATION_TARGETS):
        p = root / t
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        if p.suffix == ".md":
            for m in MD_LINK.finditer(txt):
                tgt = m.group(1).split("#")[0]
                if not tgt or tgt.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = os.path.normpath(str(p.parent / tgt))
                r = os.path.relpath(resolved, str(root)).replace("\\", "/")
                if r.startswith(FROZEN_PREFIXES):
                    bad.append(f"{t}→{r}")
        else:
            bad += [f"{t}→{h}" for h in _frozen_hits_in_code(txt)]
    for p in live_markdown():
        for m in MD_LINK.finditer(p.read_text(encoding="utf-8")):
            tgt = m.group(1).split("#")[0]
            if not tgt or tgt.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = os.path.normpath(str(p.parent / tgt))
            r = os.path.relpath(resolved, str(root)).replace("\\", "/")
            if r.startswith(FROZEN_PREFIXES):
                bad.append(f"{rel(p)}→{r}")
    for p in sorted(root.glob("docs/**/*.json")):
        # manifest は凍結成果物の登録簿そのもの（隔離の検査主体）なので対象外
        if is_frozen(p) or p == MANIFEST:
            continue
        for m in re.finditer(r'"([^"]*)"', p.read_text(encoding="utf-8")):
            if m.group(1).startswith(FROZEN_PREFIXES):
                bad.append(f"{rel(p)}→{m.group(1)}")
    return sorted(set(bad))


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _manifest(ctx)
    _structure(ctx)
    _confirmed(ctx)
    _legacy(ctx)
    _current_state(ctx)


def _manifest(ctx: Ctx) -> None:
    items = ctx.manifest_items
    schema = load(MANIFEST_SCHEMA)
    errs = schema_check(schema, ctx.manifest)
    gate("G-AUTHORITY-MANIFEST", not errs and bool(items),
         f"artifact manifest が schema 適合（必須 18 項目・追加禁止）で 1 件以上登録 (err={errs[:4]}, n={len(items)})")

    dup = detect_manifest_duplicates(items)
    gate("G-MANIFEST-UNIQUE", not dup,
         f"artifact ID 一意・同一 canonical を複数 artifact が主張しない (違反={dup[:4]})")

    pf = detect_manifest_path_faults(items)
    gate("G-MANIFEST-PATHS", not pf,
         f"canonical/view/previous_paths の実在・views 配置・旧パス不在 (違反={pf[:4]})")

    pair = detect_manifest_pair_faults(items)
    gate("G-MANIFEST-PAIR", not pair, f"pair_artifact_id の実在と対称性 (違反={pair[:4]})")

    rel_bad = detect_relation_faults(items)
    gate("G-MANIFEST-RELATION", not rel_bad,
         "supersedes（完全置換・対象は superseded／archived）と extends／depends_on（拡張・依存）が"
         f"実在 ID・自己参照なし・二重宣言なし・循環なしで整合 (違反={rel_bad[:4]})")

    dom_bad = detect_domain_faults(items)
    gate("G-MANIFEST-DOMAIN", not dom_bad,
         f"domain は業務領域のみ（slice 名・階層名の混同を拒否） (違反={dom_bad[:4]})")

    migration_bad = content_binding_migration_faults(ctx)
    migrations = _content_binding_migrations(ctx)
    appr = _approval_digests(ctx)
    st_bad: list[str] = [f"content binding:{fault}" for fault in migration_bad]
    for it in items:
        if it["lifecycle_status"] == "confirmed":
            want = artifact_content_digest(ROOT / it["canonical_path"])
            migration = migrations.get(it["artifact_id"])
            content_bound = it["approval_digest"] == want or (
                migration is not None and migration["content_binding_digest"] == want
            )
            if not content_bound:
                st_bad.append(f"{it['artifact_id']}:digest 不一致({it['approval_digest']}!={want})")
            if it["approval_digest"] not in appr:
                st_bad.append(f"{it['artifact_id']}:approvals 行なし")
        elif it["approval_digest"] is not None:
            st_bad.append(f"{it['artifact_id']}:非 confirmed に approval_digest")
    gate("G-MANIFEST-STATUS", not st_bad,
         "confirmed artifact は内容束縛 digest＋承認行を持ち、機械補正は既存PO承認へ束縛されて"
         f"意味不変かつ新規承認を付与しない (違反={st_bad[:4]})")

    rev_digests: set[str] = set()
    for p in sorted((AUTHORITY / "reviews").glob("*.json")):
        if p.name == "review.schema.json":
            continue
        rev_digests |= set(load(p).get("reviewed_artifact_digests", {}).values())
    rv_bad = [f"{it['artifact_id']}:{it['review_digest']}" for it in items
              if it.get("review_digest") is not None
              and (it["review_digest"] != sha256_file(ROOT / it["canonical_path"])[:16]
                   or it["review_digest"] not in rev_digests)]
    gate("G-MANIFEST-DIGEST", not rv_bad,
         f"review_digest が現内容とレビュー成果物の両方に一致 (違反={rv_bad[:4]})")

    unreg = detect_unregistered(items)
    gate("G-MANIFEST-COVERAGE", not unreg,
         f"現役階層の全成果物が manifest に登録（未登録の confirmed 化を禁止） (未登録={unreg[:5]})")

    frozen_claim = [it["artifact_id"] for it in items
                    if it["authority_status"] == "active"
                    and it["canonical_path"].startswith(FROZEN_PREFIXES)]
    gate("G-MANIFEST-ARCHIVE", not frozen_claim,
         f"archive／superseded を現役 artifact の canonical にできない (違反={frozen_claim})")

    fmt_bad = detect_format_faults(items)
    gate("G-CANONICAL-FORMAT", not fmt_bad,
         "canonical=正本形式（JSON／SQL／人間承認 MD のみ）・views=生成 MD で一意"
         f"（生成 MD の canonical 混入と JSON 正本を持つ MD の canonical 登録を拒否） (違反={fmt_bad[:4]})")

    slice_bad = detect_slice_faults(ctx)
    gate("G-SLICE-PLACEMENT", not slice_bad,
         "L6 機能設計の物理パス・manifest.slice・frontmatter.slice・trace 先 FR／SR のスライスが一致し、"
         f"後続スライスへの言及が forward_refs に宣言されている (違反={slice_bad[:4]})")

    st2_bad = detect_status_faults(items)
    gate("G-STATUS-CONSISTENCY", not st2_bad,
         "authority_status（現役位置）・lifecycle_status（内容成熟度）・applicability_status・"
         "implementation_inputが分離され、"
         f"markdown 正本の frontmatter・本文 status 行と manifest が一致 (違反={st2_bad[:4]})")


def _structure(ctx: Ctx) -> None:
    stray = sorted(rel(p) for p in ROOT.glob("docs/*")
                   if p.is_dir() and p not in LAYER_DIRS)
    stray += sorted(rel(p) for p in ROOT.glob("docs/*") if p.is_file())
    gate("G-LAYER-PLACEMENT", not stray,
         f"docs 直下は 00-authority／L0〜L6／archive のみ（旧階層の残存なし） (残存={stray})")

    view_bad: list[str] = []
    for p in sorted(ROOT.glob("docs/**/views/*")):
        if p.name == ".gitkeep":
            continue
        if p.suffix != ".md":
            view_bad.append(f"{rel(p)}:MD 以外")
        elif GENERATED_MARK not in p.read_text(encoding="utf-8")[:GENERATED_WINDOW]:
            view_bad.append(f"{rel(p)}:GENERATED 宣言なし")
    generated = {it["view_path"] for it in ctx.manifest_items if it.get("view_path")}
    misplaced = sorted(v for v in generated if "/views/" not in v)
    gate("G-VIEWS-GENERATED", not view_bad and not misplaced,
         f"views/ は生成 MD のみ（GENERATED 宣言必須・手編集禁止） (違反={view_bad[:4]}, 配置={misplaced})")

    dupc = detect_duplicate_canonical_content()
    gate("G-CANONICAL-UNIQUE", not dupc,
         f"同一内容の正本が現役階層に複数存在しない (重複={dupc[:4]})")

    froz = detect_frozen_references()
    gate("G-ARCHIVE-ISOLATION", not froz,
         f"現役導線（README/CLAUDE/AGENTS/CI/スクリプト/現役文書・JSON）が archive・superseded を参照しない "
         f"(参照={froz[:4]})")


def _confirmed(ctx: Ctx) -> None:
    imposters = []
    for p in live_markdown():
        if p.samefile(APPROVALS):
            continue
        head = p.read_text(encoding="utf-8")[:600]
        base = re.sub(r"_v[\d.]+$", "", p.stem)
        if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", head) and base not in ctx.approvals:
            imposters.append(p.name)
    gate("G-CONFIRM", not imposters, f"confirmed 文書は承認ログに実在 (偽装={imposters})")

    receipt_index: dict[tuple, set] = {}
    for row in ctx.approvals.splitlines():
        cells = [c.strip() for c in row.split("|")]
        if len(cells) >= 8 and re.match(r"\d{4}-\d{2}-\d{2}", cells[1]):
            if cells[4] == "confirmed" and re.fullmatch(r"[0-9a-f]{12}", cells[6]):
                receipt_index.setdefault((cells[2], cells[3]), set()).add(cells[6])

    def has_receipt(p: Path) -> bool:
        base = re.sub(r"_v[\d.]+$", "", p.stem)
        m = re.search(r"_v([\d.]+)$", p.stem)
        ver = f"v{m.group(1)}" if m else "-"
        direct = doc_body_digest(p) in receipt_index.get((base, ver), set())
        if direct:
            return True
        item = next((it for it in ctx.manifest_items if it.get("canonical_path") == rel(p)), None)
        if item is None:
            return False
        migration = _content_binding_migrations(ctx).get(item["artifact_id"])
        return bool(migration and migration["content_binding_digest"] == doc_body_digest(p))

    unbound = [f"{p.name}:{doc_body_digest(p)}" for p in live_markdown()
               if not p.samefile(APPROVALS)
               and re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", p.read_text(encoding="utf-8")[:600])
               and not has_receipt(p)]
    gate("G-CONFIRM-DIGEST", not unbound,
         f"confirmed 文書の現内容 digest が同一 (対象, 版, confirmed) の承認行に存在 (未束縛={unbound})")

    canon_bad: list[str] = []
    for p in CANON_CONTRACTS:
        d = load(p)
        if d.get("status") != "confirmed":
            canon_bad.append(f"{p.name}:status={d.get('status')}")
            continue
        for k in ("approved_at", "approval_digest", "authority"):
            if not d.get(k):
                canon_bad.append(f"{p.name}:{k} 欠落")
        want = canonical_json_digest(d)
        if d.get("approval_digest") != want:
            canon_bad.append(f"{p.name}:digest 不一致({d.get('approval_digest')}!={want})")
        elif f"| {p.name} | v0.1 | confirmed | PO | {want} |" not in ctx.approvals:
            canon_bad.append(f"{p.name}:approvals 行なし")
    gate("G-CANON-CONFIRMED", not canon_bad,
         f"契約 JSON 正本 9 本が confirmed＋内容束縛 receipt (欠陥={canon_bad[:4]})")


def _legacy(ctx: Ctx) -> None:
    misplaced = []
    for name, path in LEGACY_ARCHIVED.items():
        if not path.exists():
            misplaced.append(f"{name}:archive 不在")
        hits = [rel(p) for p in ROOT.glob(f"docs/**/{name}") if not is_frozen(p)]
        if hits:
            misplaced.append(f"{name}:現役階層に残存 {hits}")
    gate("G-LEGACY-ARCHIVED", not misplaced,
         f"旧正本（ac/verification/utest.json）が archive のみに存在し現役階層から消失 (違反={misplaced})")


CURRENT_STATE_OWNERS = ("README.md", "CLAUDE.md")


def detect_current_state_faults(root: Path = ROOT) -> list[str]:
    """現在地の表明が正本 2 ファイルに 1 回ずつだけ存在し、確定表現が現役文書に無いことを検査する。"""
    bad: list[str] = []
    for name in CURRENT_STATE_OWNERS:
        txt = (root / name).read_text(encoding="utf-8")
        for line in CURRENT_STATE_LINES:
            if txt.count(line) != 1:
                bad.append(f"{name}:『{line}』×{txt.count(line)}")
    # 正本 2 ファイル以外（AGENTS.md・現役 docs）に現在地の再掲・確定表現がない
    others = [root / "AGENTS.md", *live_markdown()]
    for p in others:
        r = rel(p)
        if r in CURRENT_STATE_OWNERS or r.startswith("docs/00-authority/audits/"):
            continue
        txt = p.read_text(encoding="utf-8")
        for line in CURRENT_STATE_LINES:
            if line in txt:
                bad.append(f"{r}:現在地の再掲『{line}』")
        for ph in FORBIDDEN_STATE_PHRASES:
            if ph in txt:
                bad.append(f"{r}:確定表現『{ph}』")
    for name in CURRENT_STATE_OWNERS:
        txt = (root / name).read_text(encoding="utf-8")
        for ph in FORBIDDEN_STATE_PHRASES:
            if ph in txt:
                bad.append(f"{name}:確定表現『{ph}』")
    return bad


def _current_state(ctx: Ctx) -> None:
    bad = detect_current_state_faults()
    gate("G-CURRENT-STATE-SINGLE", not bad,
         "現在地は README／CLAUDE.md の正本行のみ（他の現役文書に再掲・他経路の確定表現なし） "
         f"(違反={bad[:5]})")
