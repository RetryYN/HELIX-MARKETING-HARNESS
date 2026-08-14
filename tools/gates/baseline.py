"""ベースライン・配線ゲート: デグレ検出（ラチェット）、件数表記の同期、ゲート配線と分割規律。"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from tools.gates.common import (
    APPROVALS,
    BASELINE,
    COVERAGE_FLOOR,
    GATE_LEDGER,
    GATE_MODULES,
    GATE_PKG,
    HISTORICAL_COUNTS,
    L1,
    L3,
    L4,
    L5,
    L6,
    REVIEWS,
    ROOT,
    SKIP_BUDGET,
    Ctx,
    gate,
    git,
    live_markdown,
    load,
    reachable_nodes,
    rel,
    sha256_file,
)
from tools.gates.requirements import current_denominators

S0_PLAN = L6 / "S0/plan-s0.1.json"

# baseline が束縛する実装入力（archive は含めない）
ARTIFACT_GLOBS = [
    "docs/00-authority/artifact-manifest.json",
    "docs/00-authority/artifact-manifest.schema.json",
    "docs/L1-business-requirements/canonical/**/*.json",
    "docs/L3-system-requirements/**/*.json",
    "docs/L3-system-requirements/**/*.sql",
    "docs/L4-basic-design/**/*.json",
    "docs/L5-detailed-design/**/*.json",
    "docs/L6-feature-design/**/*.json",
    "tools/gates/*.py",
    "tools/*.py",
    "scripts/*.py",
    "scripts/hooks/*.sh",
    ".claude/agents/*.md",
    "Makefile",
    ".python-version",
    "docs/00-authority/template/*.json",
    "docs/00-authority/development/*.json",
    ".github/workflows/*.yml",
    # secret scanner の allowlist は**セキュリティ制御の設定**であり、改変検出の対象にする
    # （範囲を緩めても baseline drift が赤化しない状態を作らない — 独立レビュー R11-01）
    ".gitleaks.toml",
    "CLAUDE.md",
    "AGENTS.md",
    # 監査記録は append-only の規律を掲げる以上、機械的にも改変検出の対象にする
    "docs/00-authority/audits/*.md",
    "pyproject.toml",
    "uv.lock",
    "tests/skip-budget.json",
    "tests/coverage-floor.json",
]

TEST_DIR = ROOT / "tests/gates"


def gate_sources() -> list[Path]:
    return sorted(p for p in GATE_PKG.glob("*.py") if p.name != "__init__.py")


def gate_count() -> int:
    """全ゲートモジュールの gate() 呼出し箇所数（ラチェットの分母）。"""
    return sum(len(re.findall(r'gate\(\s*f?"G-', p.read_text(encoding="utf-8")))
               for p in gate_sources())


def script_gate_ids() -> set[str]:
    ids: set[str] = set()
    for p in gate_sources():
        ids |= set(re.findall(r'gate\(\s*f?"(G-[A-Z0-9-]+)', p.read_text(encoding="utf-8")))
    return ids


def _is_module_call(n: ast.AST, module: str) -> bool:
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == module)


def _calls_module(node: ast.AST, module: str) -> bool:
    """**到達しうる**範囲に `<module>.<name>(...)` の呼出しがあるか（関数単位の検査用）。"""
    return any(_is_module_call(n, module) for n in reachable_nodes(node))


def _file_calls_module(tree: ast.Module, module: str) -> bool:
    """ファイル全体のどこかに `<module>.<name>(...)` の呼出しがあるか（配線の検査用）。"""
    return any(_is_module_call(n, module) for n in ast.walk(tree))


def _has_real_assert(node: ast.AST) -> bool:
    """定数（`assert True` 等）ではない実 assert を持つか。"""
    return any(isinstance(n, ast.Assert)
               and not (isinstance(n.test, ast.Constant) and bool(n.test.value))
               for n in reachable_nodes(node))


BIND_PASSES = 5  # 名前伝播（x = mod.f(); y = x; assert y）を解くための固定点反復の上限


def _bound_names(target: ast.expr, value: ast.expr, module: str, bound: set[str]) -> set[str]:
    """代入 1 件から、本番呼出しの結果に（直接または名前伝播で）束縛される名前を返す。"""
    if isinstance(target, (ast.Tuple, ast.List)):
        # タプル代入は**位置対応**で解く。要素数が合わないアンパックは fail-close（束縛としない）
        if isinstance(value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts):
            return set().union(*(_bound_names(t, v, module, bound)
                                 for t, v in zip(target.elts, value.elts, strict=True))) \
                if target.elts else set()
        return set()
    if not isinstance(target, ast.Name):
        return set()
    if _calls_module(value, module):
        return {target.id}
    names = {s.id for s in ast.walk(value) if isinstance(s, ast.Name)}
    return {target.id} if names and names <= bound else set()  # 名前伝播


def _names_bound_from(node: ast.AST, module: str) -> set[str]:
    """本番呼出しの結果に束縛された名前を集める（タプルは位置対応・名前伝播は固定点）。"""
    assigns: list[tuple[list[ast.expr], ast.expr]] = []
    for n in reachable_nodes(node):
        if isinstance(n, ast.Assign):
            assigns.append((list(n.targets), n.value))
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            assigns.append(([n.target], n.value))
        elif isinstance(n, ast.NamedExpr):
            assigns.append(([n.target], n.value))
    bound: set[str] = set()
    for _ in range(BIND_PASSES):
        grew = False
        for targets, value in assigns:
            for t in targets:
                fresh = _bound_names(t, value, module, bound) - bound
                if fresh:
                    bound |= fresh
                    grew = True
        if not grew:
            break
    return bound


def _assert_observes_module(fn: ast.AST, module: str) -> bool:
    """assert が本番呼出しの結果を実際に観測しているか（データフローの最小束縛）。

    「本番を呼ぶが結果を捨て `assert 1 == 1`」のような形骸を落とすため、
    assert 式そのものが本番呼出しを含むか、本番呼出しの結果に束縛された名前を参照することを要求する。
    """
    bound = _names_bound_from(fn, module)
    for n in reachable_nodes(fn):
        if not isinstance(n, ast.Assert):
            continue
        if isinstance(n.test, ast.Constant) and bool(n.test.value):
            continue
        if _calls_module(n.test, module):
            return True
        if any(isinstance(s, ast.Name) and s.id in bound for s in ast.walk(n.test)):
            return True
    return False


def detect_gate_test_faults() -> tuple[list[str], list[str], list[str]]:
    """各ゲートモジュールの単体テスト・mutation test・本番ロジック参照の欠落を列挙する。

    形骸を許さないため、`test_mutation_*` 関数**それ自身**が当該ゲートモジュールの関数を
    呼び、かつ実 assert を持つことまで束縛する（`def test_mutation_x(): pass` と
    無関係な属性参照 1 個では充足しない）。
    """
    no_test: list[str] = []
    no_mut: list[str] = []
    no_link: list[str] = []
    for m in GATE_MODULES:
        tp = TEST_DIR / f"test_{m}.py"
        if not tp.exists():
            no_test.append(m)
            continue
        try:
            tree = ast.parse(tp.read_text(encoding="utf-8"))
        except SyntaxError:
            no_test.append(m)
            continue
        mutations = [n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name.startswith("test_mutation_")]
        if not any(_calls_module(f, m) and _has_real_assert(f) and _assert_observes_module(f, m)
                   for f in mutations):
            no_mut.append(m)
        imported = any(
            (isinstance(n, ast.ImportFrom) and (n.module or "").startswith("tools.gates")
             and any(a.name == m for a in n.names))
            or (isinstance(n, ast.Import) and any(a.name == f"tools.gates.{m}" for a in n.names))
            for n in ast.walk(tree))
        if not (imported and _file_calls_module(tree, m)):
            no_link.append(m)
    return no_test, no_mut, no_link


def confirmed_docs() -> dict[str, str]:
    return {rel(p): sha256_file(p) for p in live_markdown()
            if re.search(r"status:\s*\*{0,2}confirmed\*{0,2}", p.read_text(encoding="utf-8")[:600])}


def detect_untracked_baseline_keys(base: dict) -> list[str]:
    """baseline の artifacts が「git 追跡下の実在パス → sha256」だけであることを検査する。

    この台帳は digest だけを持つため secret scanner の allowlist で除外している。
    除外が安全なのは**キーが実在パスに限られる**ことが機械保証されている場合だけであり、
    その保証をここで与える（`"api_key.txt": "<64 桁 hex>"` のような行は台帳に存在し得ない）。
    """
    tracked = {ln for ln in git("ls-files").stdout.splitlines() if ln}
    bad: list[str] = []
    for k, v in (base.get("artifacts") or {}).items():
        if k not in tracked:
            bad.append(f"{k}: git 追跡下に無いキー")
        elif not (ROOT / k).is_file():
            # 追跡済みでも作業ツリーから消えたパスは「実在」ではない（独立レビュー R11-02）
            bad.append(f"{k}: 追跡下だが作業ツリーに実在しない")
        elif not re.fullmatch(r"[0-9a-f]{64}", str(v)):
            bad.append(f"{k}: 値が sha256 64 桁でない")
    return bad


def artifact_hashes() -> dict[str, str]:
    files = sorted({rel(Path(f)) for g in ARTIFACT_GLOBS
                    for f in ROOT.glob(g) if Path(f).is_file()})
    return {a: sha256_file(ROOT / a) for a in files}


def current_counts(ctx: Ctx) -> dict[str, int]:
    """現行分母（旧 AC19／TC59／UTC69 は historical_counts へ退避済み）。"""
    bm = sum(len(load(p)["items"]) for p in sorted((L1 / "canonical/br-media").glob("*.json"))
             if p.stem != "index")
    mr = sum(len(load(p)["items"]) for p in sorted((L3 / "canonical/functional/mr").glob("*.json"))
             if p.stem != "index")
    counts = {
        "BR": len(ctx.br), "REQ": len(ctx.req), "FR": len(ctx.frc), "NFR": len(ctx.nfc),
        "FN": len(ctx.fn), "BRM": bm, "MR": mr,
        "WF": len(load(L1 / "canonical/ltw/workflows.json")["items"]),
        "CMP": len(ctx.comps), "SCM": len(ctx.scm), "ITC": len(ctx.itcs), "DU": len(ctx.dus),
    }
    counts.update(current_denominators(ctx))
    return counts


# baseline の旧パス（物理移行前）。親コミットとの比較はここまで遡って解決する
BASELINE_PREVIOUS_PATHS = ["docs/governance/baseline.json"]
# 現行分母から意図的に退避したキー（historical_counts へ移した — 消失を silent に許さない）
RETIRED_COUNT_KEYS = {"AC", "UTC"}


def committed_baseline() -> tuple[dict | None, str]:
    """**親コミット**の baseline を返す（作業ツリーの同時改変では回避できない比較元）。

    物理移行で baseline のパスが変わったため、旧パスまで遡って解決する。
    親コミットが存在するのに baseline がどのパスでも解決できない場合は fail-close
    （None ではなく理由を返し、呼び出し側がゲートを落とす）。
    """
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        # 非 git ツリーを「初回コミット」と混同するとラチェットが一律に素通りする（独立レビュー N-07）
        return None, "git リポジトリではない（比較元を解決できない — fail-close）"
    if git("rev-parse", "--verify", "HEAD^").returncode != 0:
        return None, "親コミットなし（初回コミット）"
    for path in [rel(BASELINE), *BASELINE_PREVIOUS_PATHS]:
        out = git("show", f"HEAD^:{path}")
        if out.returncode == 0:
            try:
                return json.loads(out.stdout), path
            except json.JSONDecodeError:
                return None, f"{path}: JSON 解析不能"
    return None, "親コミットに baseline が見つからない（旧パス含む）"


def committed_max_skipped() -> int | None:
    base, _ = committed_baseline()
    return None if base is None else base.get("max_skipped")


def detect_ratchet_faults(prev: dict, counts: dict[str, int], contract_counts: dict[str, int],
                          gates: int, skip: int, skip_approved: bool) -> list[str]:
    """親コミットの baseline に対するラチェット違反を列挙する（本番ゲートとテストが共用）。"""
    bad: list[str] = []
    for k, v in prev.get("counts", {}).items():
        if k in RETIRED_COUNT_KEYS:
            continue
        if k not in counts:
            bad.append(f"分母キー消失:{k}")
        elif counts[k] < v:
            bad.append(f"分母縮小:{k}:{v}→{counts[k]}")
    for k, v in prev.get("contract_counts", {}).items():
        if k not in contract_counts:
            bad.append(f"契約分母キー消失:{k}")
        elif contract_counts[k] < v:
            bad.append(f"契約分母縮小:{k}:{v}→{contract_counts[k]}")
    if gates < prev.get("gate_count", 0):
        bad.append(f"ゲート削減:{prev.get('gate_count')}→{gates}")
    prev_skip = prev.get("max_skipped")
    if prev_skip is not None and skip > prev_skip:
        if not skip_approved:
            bad.append(f"skip 上限の未承認引き上げ:{prev_skip}→{skip}")
        bad += skip_raise_backing_faults(prev, contract_counts, prev_skip, skip)
    prev_cov = prev.get("coverage_floor")
    cur_cov = load(COVERAGE_FLOOR)["fail_under"]
    if prev_cov is not None and cur_cov < prev_cov:
        bad.append(f"coverage 下限の引き下げ:{prev_cov}→{cur_cov}")
    # S0.1 の着手前提条件は「消して満たす」ことができない（met にして残すのが唯一の解消）
    dropped = sorted(set(prev.get("plan_preconditions", [])) - set(plan_precondition_ids()))
    if dropped:
        bad.append(f"S0.1 前提条件の削除:{dropped}")
    # 構造接続の実数は縮められない（na_reason で契約節・責務を削って通す経路を塞ぐ）
    for k, label in (("clause_ac_covered", "AC 被覆の契約節"), ("implementation_units", "実装単位")):
        p0 = prev.get(k)
        if p0 is not None and trace_counts().get(k, 0) < p0:
            bad.append(f"{label}の縮小:{p0}→{trace_counts().get(k)}")
    grown = sorted(set(uncovered_apis()) - set(prev.get("uncovered_apis", [])))
    if prev.get("uncovered_apis") is not None and grown:
        bad.append(f"AC 未被覆 API の増加:{grown}")
    # 実行証跡で分離を確認したレビューは unverified へ落とせない（主体分離のラチェット）
    lost = sorted(set(prev.get("separation_verified_reviews", [])) - set(verified_reviews()))
    if lost:
        bad.append(f"レビュー主体分離の証跡束縛（self_attested／ci_attested）取消:{lost}")
    # 証跡の**強度**も後退させられない（ci_attested → self_attested の弱体化 — 独立レビュー R1-03）
    cur_sep = separation_statuses()
    for rid, was in sorted(prev.get("separation_statuses", {}).items()):
        now = cur_sep.get(rid)
        if now is None:
            bad.append(f"レビュー成果物の消失:{rid}")
        elif SEPARATION_RANK.get(now, -1) < SEPARATION_RANK.get(was, -1):
            bad.append(f"レビュー証跡強度の後退:{rid}:{was}→{now}")
    # API の検証水準は acceptance から内部分類へ落とせない（分類替えで検査を緩める経路を塞ぐ）
    cur_lv = api_verification_levels()
    for aid, was in sorted(prev.get("api_verification_levels", {}).items()):
        now = cur_lv.get(aid)
        if now is None:
            bad.append(f"API の消失:{aid}")
        elif was == "acceptance" and now != "acceptance":
            bad.append(f"検証水準の格下げ:{aid}:{was}→{now}")
    # 更新境界の導出元（FN→DU・FN→update）を黙って動かせない（協調改変 — 独立レビュー R1-04）
    cur_fn = fn_boundary_map()
    for key, was in sorted(prev.get("fn_boundary_map", {}).items()):
        now = cur_fn.get(key)
        if now is None:
            bad.append(f"FN の消失:{key}")
        elif now != was:
            bad.append(f"更新境界の無承認変更:{key}:{was}→{now}")
    return bad


SEPARATION_RANK = {"unverified": 0, "self_attested": 1, "ci_attested": 2}


def separation_statuses() -> dict[str, str]:
    """レビュー ID → separation_status（強度ラチェットの保護対象）。"""
    out: dict[str, str] = {}
    for p in sorted(REVIEWS.glob("*.json")):
        if p.name == "review.schema.json":
            continue
        r = load(p)
        out[r["review_id"]] = r.get("separation_status", "unverified")
    return out


def api_verification_levels() -> dict[str, str]:
    """API 安定 ID → verification_level（acceptance からの格下げを拒否する）。"""
    from tools.gates.common import DU_CONTRACTS
    return {a["api_id"]: a.get("verification_level", "acceptance")
            for d in load(DU_CONTRACTS)["items"] for a in d["apis"]}


def fn_boundary_map() -> dict[str, str]:
    """FN → 『DU|更新』。resolution_update の導出元そのものをラチェットで固定する。

    DU 台帳の fn_ids と updates.json を**同時に**書き換えれば、集合の一意性を保ったまま
    任意の API の解消先を動かせてしまう（独立レビュー R1-04）。導出元の対応表を baseline へ
    保存し、承認のない移動を検出する。
    """
    from tools.gates.common import DU_LEDGER, UPDATES
    du_of = {f: d["id"] for d in load(DU_LEDGER)["items"] for f in d["fn_ids"]}
    up_of = {f: u["update"] for u in load(UPDATES)["items"] for f in u["fn_ids"]}
    return {f: f"{du_of.get(f, '-')}|{up_of.get(f, '-')}" for f in sorted(set(du_of) | set(up_of))}


def skip_raise_backing_faults(prev: dict, contract_counts: dict[str, int],
                              prev_skip: int, skip: int) -> list[str]:
    """skip 上限の引き上げが**同一変更内の設計追加**に裏打ちされているかを検査する。

    承認行の形式だけを見ると「承認行を書けば上限を上げられる」ことになり、実装の遅れを
    skip で吸収する経路が開く（独立レビュー R5-02）。上限の増分は、同じ変更で増えた
    API 単位 UT（du-contracts の `apis[].ut`）の本数以内でなければならない。
    """
    delta_cap = skip - prev_skip
    prev_ut = (prev.get("contract_counts") or {}).get("API_UT")
    if prev_ut is None:
        return [f"skip 上限の引き上げ({prev_skip}→{skip})を裏づける親コミットの API_UT が無い"]
    delta_ut = contract_counts.get("API_UT", 0) - prev_ut
    if delta_ut < delta_cap:
        return [f"skip 上限の引き上げ({prev_skip}→{skip}: +{delta_cap})が"
                f"同一変更の UT 追加(+{delta_ut})を超えている（設計追加と同一コミットで行うこと）"]
    return []


def trace_counts() -> dict[str, int]:
    """構造接続の実数（AC 被覆済み契約節・実装単位）。ラチェットの保護対象。"""
    from tools.gates.common import AC_CONTRACTS, IMPL_UNITS_CONTRACTS
    acc = load(AC_CONTRACTS)["items"]
    covered = {c for a in acc for c in (a.get("verifies_clause_refs") or [])}
    units = load(IMPL_UNITS_CONTRACTS).get("items", []) if IMPL_UNITS_CONTRACTS.exists() else []
    return {"clause_ac_covered": len(covered), "implementation_units": len(units)}


def uncovered_apis() -> list[str]:
    """AC が 1 節も検証していない API の明示台帳（増加はラチェット違反）。"""
    p = L6 / "S0/uncovered-apis.json"
    if not p.exists():
        return []
    return sorted(i["api_id"] for i in load(p).get("items", []))


def verified_reviews() -> list[str]:
    """実行証跡で主体分離を確認済みのレビュー ID（ラチェットの保護対象）。

    self_attested（ローカル実行ログ束縛）と ci_attested（Actions 束縛）の両方を含む。
    証跡付きから unverified への後退を拒否するのが目的で、出所の強度はここでは区別しない。
    """
    from tools.gates.review_binding import ATTESTED
    out = []
    for p in sorted(REVIEWS.glob("*.json")):
        if p.name == "review.schema.json":
            continue
        r = load(p)
        if r.get("separation_status") in ATTESTED:
            out.append(r["review_id"])
    return sorted(out)


def plan_precondition_ids() -> list[str]:
    """S0.1 PLAN が持つ前提条件 ID の一覧（ラチェットの保護対象）。"""
    if not S0_PLAN.exists():
        return []
    pres = load(S0_PLAN).get("preconditions", [])
    return sorted(p["id"] for p in pres if isinstance(p, dict) and "id" in p)


def skip_raise_approved(prev: int | None, new: int) -> bool:
    """skip 上限の引き上げに対する構造化 PO 承認行が approvals.md にあるか。"""
    if prev is None or new <= prev:
        return False
    pat = re.compile(
        rf"^\|[^|]*\|\s*skip-budget\s*\|[^|]*{prev}→{new}[^|]*\|\s*approved\s*\|\s*PO\s*\|",
        re.MULTILINE)
    return bool(pat.search(APPROVALS.read_text(encoding="utf-8")))


def build_baseline(ctx: Ctx) -> dict:
    return {
        "updated": "see git log",
        "counts": current_counts(ctx),
        "gate_count": gate_count(),
        "max_skipped": load(SKIP_BUDGET)["max_skipped"],
        "coverage_floor": load(COVERAGE_FLOOR)["fail_under"],
        "contract_counts": current_denominators(ctx),
        "historical_counts": HISTORICAL_COUNTS,
        "confirmed_docs": confirmed_docs(),
        "plan_preconditions": plan_precondition_ids(),
        "separation_verified_reviews": verified_reviews(),
        "separation_statuses": separation_statuses(),
        "api_verification_levels": api_verification_levels(),
        "fn_boundary_map": fn_boundary_map(),
        **trace_counts(),
        "uncovered_apis": uncovered_apis(),
        "artifacts": artifact_hashes(),
    }


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _baseline(ctx)
    _count_sync(ctx)
    _wiring(ctx)


def _baseline(ctx: Ctx) -> None:
    if not BASELINE.exists():
        gate("G-BASE-EXIST", False, "baseline.json が存在しない（--update-baseline で生成）")
        return
    base = load(BASELINE)
    cur_hashes = confirmed_docs()
    drift = [d for d, h in base["confirmed_docs"].items() if cur_hashes.get(d) != h]
    gate("G-BASE-HASH", not drift,
         f"confirmed 文書の無断改変なし (差分={drift or '[]'}; 意図的なら --update-baseline を同一コミットで)")
    demoted = [d for d in base["confirmed_docs"] if d not in cur_hashes]
    gate("G-BASE-STATUS", not demoted, f"confirmed の降格なし (降格={demoted})")

    # ラチェットの比較元は **親コミット**の baseline（同一コミットでの自己参照を排除）
    prev, source = committed_baseline()
    cur_counts = current_counts(ctx)
    cur_cc = current_denominators(ctx)
    cur_skip = load(SKIP_BUDGET)["max_skipped"]
    gc = gate_count()
    if prev is None and source == "親コミットなし（初回コミット）":
        gate("G-BASE-RATCHET", True, f"ラチェット比較元なし（{source}） — 初回コミットのため検査対象外")
    elif prev is None:
        gate("G-BASE-RATCHET", False, f"ラチェット比較元を解決できない（{source}） — fail-close")
    else:
        approved = skip_raise_approved(prev.get("max_skipped"), cur_skip)
        faults = detect_ratchet_faults(prev, cur_counts, cur_cc, gc, cur_skip, approved)
        gate("G-BASE-RATCHET", not faults,
             f"親コミット（{source}）比で分母縮小・キー消失・ゲート削減・skip 未承認引上げなし "
             f"(違反={faults}, gates={gc}>={prev.get('gate_count')}, "
             f"skip={cur_skip} vs 親={prev.get('max_skipped')})")

    cur_art = artifact_hashes()
    adrift = sorted(set([a for a, h in base.get("artifacts", {}).items() if cur_art.get(a) != h]
                        + [a for a in cur_art if a not in base.get("artifacts", {})]))
    gate("G-BASE-ART", "artifacts" in base and not adrift,
         f"実装入力 artifact の無断改変/未登録なし (差分={adrift[:5] or '[]'}; 意図的なら --update-baseline)")

    ghost = detect_untracked_baseline_keys(base)
    gate("G-BASE-ART-PATHS", not ghost,
         "baseline の artifacts キーが**git 追跡下の実在パス**のみで、値が sha256 64 桁である"
         f"（台帳へ秘密らしきキーを紛れ込ませられない） (違反={ghost[:5]})")


def _count_sync(ctx: Ctx) -> None:
    gc = gate_count()
    files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "AGENTS.md", GATE_LEDGER]
    files += sorted((L4 / "canonical").glob("*.md")) + sorted((L5 / "canonical").glob("*.md"))
    stale = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        for m in re.findall(r"整合ゲート\s*(\d+)\s*本|（(\d+)\s*ゲート）|ゲート\s*(\d+)\s*本", text):
            n = int(next(x for x in m if x))
            if n != gc:
                stale.append(f"{p.name}:{n}!={gc}")
    stale += detect_readme_count_faults(
        (ROOT / "README.md").read_text(encoding="utf-8"), current_counts(ctx))
    for p in (ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "AGENTS.md"):
        stale += detect_root_contract_count_faults(
            p.name, p.read_text(encoding="utf-8"), current_counts(ctx))
    gate("G-COUNT-SYNC", not stale,
         f"ゲート件数・README主要分母・root 3文書の契約分母が正本の実数と一致 (乖離={stale})")


def detect_readme_count_faults(text: str, counts: dict[str, int]) -> list[str]:
    """README の入口導線に掲げる主要分母が JSON 正本からドリフトしていないか検出する。"""
    claims = {
        "BR": (r"BR 背骨\s+(\d+)", counts["BR"]),
        "REQ": (r"要求一覧\s+(\d+)", counts["REQ"]),
        "FR": (r"要件定義 FR(\d+)/NFR\d+", counts["FR"]),
        "NFR": (r"要件定義 FR\d+/NFR(\d+)", counts["NFR"]),
        "FN": (r"機能一覧\s+(\d+)", counts["FN"]),
    }
    bad: list[str] = []
    for label, (pattern, expected) in claims.items():
        found = [int(x) for x in re.findall(pattern, text)]
        if found != [expected]:
            bad.append(f"README:{label}={found or '欠落'}!={expected}")
    return bad


ROOT_DENOMINATOR = re.compile(
    r"現行分母は\s+\*{0,2}AC=(\d+)\s*／\s*TCC=(\d+)\s*／\s*"
    r"API=(\d+)\s*／\s*API_UT=(\d+)\*{0,2}")


def detect_root_contract_count_faults(name: str, text: str, counts: dict[str, int]) -> list[str]:
    """README/CLAUDE/AGENTS の権威行が1行だけ存在し、4分母が正本と一致するか検査する。"""
    found = [tuple(map(int, match)) for match in ROOT_DENOMINATOR.findall(text)]
    expected = (counts["AC_CONTRACT"], counts["TCC"], counts["API"], counts["API_UT"])
    if found != [expected]:
        return [f"{name}:契約分母={found or '欠落'}!={expected}"]
    return []


def _wiring(ctx: Ctx) -> None:
    ledger = GATE_LEDGER.read_text(encoding="utf-8")
    ledger_gates: set[str] = set()
    for m in re.findall(r"G-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:/[A-Z0-9]+)*", ledger):
        parts = m.split("/")
        ledger_gates.add(parts[0])
        prefix = parts[0].rsplit("-", 1)[0]
        ledger_gates.update(f"{prefix}-{s}" for s in parts[1:])
    unwired = sorted(g for g in script_gate_ids()
                     if not (g in ledger_gates or g.rstrip("-") in ledger_gates
                             or (g.endswith("-") and any(lg.startswith(g) for lg in ledger_gates))))
    ci = (ROOT / ".github/workflows/docs-ci.yml").read_text(encoding="utf-8")
    gate("G-WIRING", "tools/gates/run_all.py" in ci and not unwired,
         f"CI 配線（run_all）＋台帳掲載 (未掲載={unwired})")

    missing_mod = [m for m in GATE_MODULES if not (GATE_PKG / f"{m}.py").exists()]
    wrapper = (ROOT / "scripts/validate_requirements.py").read_text(encoding="utf-8")
    thin = wrapper.count("\n") <= 40 and "run_all" in wrapper
    gate("G-GATE-MODULES", not missing_mod and thin,
         f"ゲートは tools/gates/ の工程別モジュールへ分割され validate_requirements.py は互換ラッパー "
         f"(欠落={missing_mod}, ラッパー行数={wrapper.count(chr(10))}, run_all 参照={'run_all' in wrapper})")

    no_test, no_mut, no_link = detect_gate_test_faults()
    gate("G-GATE-UNITTEST", not no_test and not no_mut and not no_link,
         "各ゲートモジュールに単体テストと mutation test（test_mutation_* 関数）が存在し、"
         "本番モジュールの関数を実際に呼んでいる "
         f"(テスト欠={no_test}, mutation欠={no_mut}, 本番未参照={no_link})")
