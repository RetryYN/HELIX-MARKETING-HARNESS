"""権威層ゲート: artifact manifest・物理構造・正本確定・旧体系隔離・現在地の一意性。

PO 指示 §1〜§4 に対応する。manifest（docs/00-authority/artifact-manifest.json）を
全成果物の権威正本とし、canonical／view／pair／status／digest／archive 非参照を fail-close 検査する。
"""

from __future__ import annotations

import os
import re
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
    Ctx,
    canonical_json_digest,
    gate,
    is_frozen,
    live_markdown,
    load,
    rel,
    schema_check,
    sha12,
    sha256_file,
)

# 現在地の正本文（README.md / CLAUDE.md はこの 4 行以外の現在地表明を持たない — PO 指示 §3）
CURRENT_STATE_LINES = [
    "S0 設計クロージャー完了",
    "S1 以降は planned",
    "S0.1 実装未着手",
    "HELIX-HARNESS 取込は未実施・PO 判断待ち",
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
    """成果物の内容 digest。契約 JSON は正準化 digest、それ以外はファイル sha256[:12]。"""
    if path.suffix == ".json":
        data = load(path)
        if isinstance(data, dict) and "approval_digest" in data:
            return canonical_json_digest(data)
    return sha12(path)


# ---------------------------------------------------------------- 検出関数（mutation test が共用）
# 現役（凍結でない）status。canonical の一意性はこの全てに効かせる（active の迂回を塞ぐ）
LIVE_STATUSES = ("confirmed", "active", "draft")


def detect_manifest_duplicates(items: list[dict]) -> list[str]:
    """artifact_id の重複と、同一 canonical_path を複数 artifact が主張する箇所を列挙する。

    一意性は **全ての現役 status**（confirmed/active/draft）に効かせる。status=active を
    経由した重複主張の迂回を許さない（独立レビュー blocker 対応）。
    """
    bad: list[str] = []
    seen_ids: dict[str, int] = {}
    seen_canon: dict[str, list[str]] = {}
    for it in items:
        seen_ids[it["artifact_id"]] = seen_ids.get(it["artifact_id"], 0) + 1
        if it.get("status") in LIVE_STATUSES:
            seen_canon.setdefault(it["canonical_path"], []).append(it["artifact_id"])
    bad += [f"artifact_id 重複:{k}" for k, n in seen_ids.items() if n > 1]
    bad += [f"canonical 重複主張:{p}={sorted(ids)}" for p, ids in seen_canon.items() if len(ids) > 1]
    return bad


def detect_manifest_path_faults(items: list[dict], root: Path = ROOT) -> list[str]:
    """canonical_path／view_path／previous_paths の実在・凍結領域混入を列挙する。"""
    bad: list[str] = []
    for it in items:
        cp = it["canonical_path"]
        if not (root / cp).exists():
            bad.append(f"{it['artifact_id']}:canonical 不在 {cp}")
        elif cp.startswith(FROZEN_PREFIXES) and it.get("status") not in ("archived", "superseded"):
            bad.append(f"{it['artifact_id']}:現役 artifact の canonical が凍結領域 {cp}")
        vp = it.get("view_path")
        if vp is not None:
            if not (root / vp).exists():
                bad.append(f"{it['artifact_id']}:view 不在 {vp}")
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
         f"artifact manifest が schema 適合（必須 11 項目・追加禁止）で 1 件以上登録 (err={errs[:4]}, n={len(items)})")

    dup = detect_manifest_duplicates(items)
    gate("G-MANIFEST-UNIQUE", not dup,
         f"artifact ID 一意・同一 canonical を複数 artifact が主張しない (違反={dup[:4]})")

    pf = detect_manifest_path_faults(items)
    gate("G-MANIFEST-PATHS", not pf,
         f"canonical/view/previous_paths の実在・views 配置・旧パス不在 (違反={pf[:4]})")

    pair = detect_manifest_pair_faults(items)
    gate("G-MANIFEST-PAIR", not pair, f"pair_artifact_id の実在と対称性 (違反={pair[:4]})")

    appr = _approval_digests(ctx)
    st_bad: list[str] = []
    for it in items:
        if it["status"] == "confirmed":
            want = artifact_content_digest(ROOT / it["canonical_path"])
            if it["approval_digest"] != want:
                st_bad.append(f"{it['artifact_id']}:digest 不一致({it['approval_digest']}!={want})")
            elif it["approval_digest"] not in appr:
                st_bad.append(f"{it['artifact_id']}:approvals 行なし")
        elif it["approval_digest"] is not None:
            st_bad.append(f"{it['artifact_id']}:非 confirmed に approval_digest")
    gate("G-MANIFEST-STATUS", not st_bad,
         f"confirmed artifact は内容束縛 digest＋承認行を持つ (違反={st_bad[:4]})")

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
                    if it["status"] in ("confirmed", "draft")
                    and it["canonical_path"].startswith(FROZEN_PREFIXES)]
    gate("G-MANIFEST-ARCHIVE", not frozen_claim,
         f"archive／superseded を現役 artifact の canonical にできない (違反={frozen_claim})")


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
        elif "GENERATED FILE" not in p.read_text(encoding="utf-8")[:200]:
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
        return sha12(p) in receipt_index.get((base, ver), set())

    unbound = [f"{p.name}:{sha12(p)}" for p in live_markdown()
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
         f"契約 JSON 正本 8 本が confirmed＋内容束縛 receipt (欠陥={canon_bad[:4]})")


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
         "現在地は README／CLAUDE.md の 4 行のみ（他の現役文書に再掲・他経路の確定表現なし） "
         f"(違反={bad[:5]})")
