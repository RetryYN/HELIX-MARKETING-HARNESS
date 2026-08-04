"""S0.1 依存 Workset（実装レーン）ゲート: 実装単位を依存方向に沿った Workset へ分割し、
着手・完了・ラチェットを **Workset 単位**で強制する（PO 指示 §2〜§6）。

Workset A／B／C は **PR の単位ではない**。実装順・依存閉包・統合完了（Workset ITC）を
管理する上位レーンであり、1 レーンは複数の実装 PR に分かれてよい。

従来は「最初の実装追加で S0.1 対象 UT 127 件を一斉に強制」する all-or-nothing だった。
それでは最初の Workset に着手した瞬間に、まだ書きようのない後続 Workset のスタブまで赤になる。
ここでは正本 `docs/L6-feature-design/S0/s0.1-worksets.json` を軸に、

- 着手済み（in_progress／done）Workset **だけ**へ skip 解除・nodeid 単位 executed+passed・
  対象モジュール coverage 80%・依存 Workset の done を強制する
- 未着手 Workset のスタブは猶予する
- 完了した Workset の UT・API・依存・coverage・skip 上限は以後後退できない（ラチェット）

fail-close の方針: 正本が**無い・壊れている・分割が不完全**なら「全 S0.1 DU が強制範囲」に
落とす（`enforced_du_ids`）。正本を消せば強制が消える、という逃げ道を作らない。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools.gates.common import (
    ITC_LEDGER,
    L6,
    ROOT,
    S0_DU_MAX,
    SKIP_BUDGET,
    Ctx,
    gate,
    git,
    load,
    schema_check,
)

WORKSETS = L6 / "S0/s0.1-worksets.json"
WORKSET_SCHEMA = L6 / "S0/s0.1-workset.schema.json"
COVERAGE_SCOPE_TOOL = "tools/coverage_scope.py"
COVERAGE_FLOOR_TOOL = "tools/coverage_floor.py"
PYTHON_CI = ROOT / ".github/workflows/python-ci.yml"
# pytest 行が coverage 対象を受け取っていることの構造要件（step id → 出力名）
COV_SCOPE_REF = "steps.covscope.outputs.args"
COV_FLOOR_REF = "steps.cov.outputs.floor"

TESTS_UNIT_REL = "tests/unit"
SRC_PKG_REL = "src/helix"
STARTED_STATUS = ("in_progress", "done")
WORKSET_FLOOR = 80


# ---------------------------------------------------------------- 正本のロード
def load_worksets(path: Path = WORKSETS) -> dict | None:
    """Workset 正本を読む（不在・壊れている場合は None＝fail-close 側へ倒す）。"""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def worksets_of(data: dict | None) -> list[dict]:
    items = (data or {}).get("worksets")
    return [w for w in items if isinstance(w, dict)] if isinstance(items, list) else []


def s0_du_ids() -> list[str]:
    return [f"DU-{i:02d}" for i in range(1, S0_DU_MAX + 1)]


# ---------------------------------------------------------------- 依存グラフの機械導出
def du_dependencies(ctx: Ctx) -> dict[str, list[str]]:
    """DU → 依存 DU（S0.1 内）を du-contracts の `depends_on_apis` から機械導出する。

    正本は散文込みの文字列（`"DU-10: connect()"`）なので、DU 参照だけを抜く。
    S0.1 外の DU（DU-13 以降）は S0.1 の分割順序に影響しないため落とす。
    """
    s0 = set(s0_du_ids())
    out: dict[str, list[str]] = {}
    for d in ctx.duc:
        if d["id"] not in s0:
            continue
        refs = " ".join(str(x) for x in (d.get("depends_on_apis") or []))
        out[d["id"]] = sorted({m for m in re.findall(r"DU-\d\d", refs) if m in s0} - {d["id"]})
    return out


def du_module(ctx: Ctx, du_id: str) -> str:
    for d in ctx.duc:
        if d["id"] == du_id:
            return f"{SRC_PKG_REL}/{str(d['module']).strip().rstrip(':：')}"
    return ""


def derive_scope(ctx: Ctx, du_ids: list[str]) -> dict[str, list[str]]:
    """Workset の DU 集合から api_ids／ut_nodeids／modules を導出する。"""
    apis: set[str] = set()
    uts: set[str] = set()
    mods: set[str] = set()
    for d in ctx.duc:
        if d["id"] not in du_ids:
            continue
        mods.add(f"{SRC_PKG_REL}/{str(d['module']).strip().rstrip(':：')}")
        for a in d["apis"]:
            apis.add(a["api_id"])
            for u in a.get("ut", []):
                nid = u.get("nodeid")
                if isinstance(nid, str) and "::" in nid:
                    uts.add(f"{TESTS_UNIT_REL}/{nid}")
    return {"api_ids": sorted(apis), "ut_nodeids": sorted(uts), "modules": sorted(mods)}


def derive_itc(ctx: Ctx, membership: dict[str, str], order: list[str]) -> dict[str, list[str]]:
    """S0.1 の ITC を「依存順で最後に成立する Workset」へ機械的に割り当てる。

    ITC は CMP 単位で書かれている（②↔④のペア正本）。CMP→DU→Workset で写像し、
    その ITC が触れる Workset のうち依存順で最も後ろのものへ 1 回だけ割り当てる。
    こうすると各 ITC は「必要な Workset が全部 done になった時点」で初めて要求される。
    """
    cmp2ws: dict[str, set[str]] = {}
    for d in ctx.duc:
        if d["id"] in membership:
            cmp2ws.setdefault(str(d.get("cmp")), set()).add(membership[d["id"]])
    out: dict[str, list[str]] = {w: [] for w in order}
    for it in load(ITC_LEDGER)["items"]:
        if it.get("update") != "S0.1":
            continue
        ranks = [order.index(w) for c in (it.get("cmp") or []) for w in cmp2ws.get(str(c), ())
                 if w in order]
        if ranks:
            out[order[max(ranks)]].append(str(it["id"]))
    return {w: sorted(v) for w, v in out.items()}


def workset_edges(ctx: Ctx, membership: dict[str, str]) -> dict[str, set[str]]:
    """DU 依存から Workset 間の直接依存を導出する。"""
    edges: dict[str, set[str]] = {w: set() for w in set(membership.values())}
    for du, deps in du_dependencies(ctx).items():
        src = membership.get(du)
        if src is None:
            continue
        for other in deps:
            dst = membership.get(other)
            if dst is not None and dst != src:
                edges[src].add(dst)
    return edges


def find_cycle(edges: dict[str, set[str]]) -> list[str]:
    """有向グラフの循環を 1 本返す（無ければ空）。"""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str) -> list[str]:
        state[n] = 1
        stack.append(n)
        for m in sorted(edges.get(n, ())):
            if state.get(m) == 1:
                return [*stack[stack.index(m):], m]
            if state.get(m, 0) == 0:
                found = visit(m)
                if found:
                    return found
        stack.pop()
        state[n] = 2
        return []

    for n in sorted(edges):
        if state.get(n, 0) == 0:
            found = visit(n)
            if found:
                return found
    return []


def du_cycles_spanning(ctx: Ctx, membership: dict[str, str]) -> list[str]:
    """DU 単位の相互依存（SCC）が複数 Workset に跨っていないかを見る。

    跨っていれば Workset 分割は原理的に非循環にできない。単純な 2 項相互依存だけでなく
    到達可能性の相互性で見る（DU-01↔DU-02 のような契約上の SCC は同一 Workset に置く）。
    """
    deps = du_dependencies(ctx)
    reach: dict[str, set[str]] = {}
    for start in deps:
        seen: set[str] = set()
        stack = list(deps[start])
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(deps.get(n, []))
        reach[start] = seen
    bad = []
    for a in sorted(deps):
        for b in sorted(deps):
            if a < b and b in reach.get(a, ()) and a in reach.get(b, ()) \
                    and membership.get(a) != membership.get(b):
                bad.append(f"{a}↔{b} が {membership.get(a)}／{membership.get(b)} に分断")
    return bad


# ---------------------------------------------------------------- 強制範囲
def started_worksets(data: dict | None) -> list[dict]:
    return [w for w in worksets_of(data) if w.get("status") in STARTED_STATUS]


def enforced_du_ids(ctx: Ctx, data: dict | None = None) -> list[str]:
    """強制の対象になる DU（着手済み Workset のもの）。

    正本が読めない・分割が S0.1 全 DU を覆っていない場合は **全 DU** を対象にする
    （正本を消す／削るだけで強制が外れる fail-open を塞ぐ）。
    """
    data = load_worksets() if data is None else data
    items = worksets_of(data)
    covered = [du for w in items for du in (w.get("du_ids") or []) if isinstance(du, str)]
    if not items or sorted(set(covered)) != s0_du_ids() or len(covered) != len(set(covered)):
        return s0_du_ids() if ctx.impl_started else []
    started = sorted({du for w in started_worksets(data) for du in (w.get("du_ids") or [])})
    # 着手シグナルが立っているのに Workset を全部 planned に据え置けば強制範囲が空になる。
    # その状態は「どの Workset に着手したのか宣言していない着手」なので全 DU へ倒す
    # （独立レビュー R13-05 — 分割は強制の緩和ではなく分割でしかない）。
    if not started and ctx.impl_started:
        return s0_du_ids()
    return started


def enforced_nodeids(ctx: Ctx, data: dict | None = None) -> list[str]:
    """強制の対象になる UT nodeid（着手済み Workset のもの）。"""
    return derive_scope(ctx, enforced_du_ids(ctx, data))["ut_nodeids"]


def enforced_modules(ctx: Ctx, data: dict | None = None) -> list[str]:
    """coverage を強制する対象モジュール（active＋done Workset のもの）。"""
    return derive_scope(ctx, enforced_du_ids(ctx, data))["modules"]


def implemented_modules(ctx: Ctx) -> list[str]:
    """S0.1 対象モジュールのうち **実装実体を持つ**もの。

    `def`／`class`／`lambda` の実体だけでなく、**S0.1 の API 名への間接束縛**
    （再エクスポート・partial・デコレータ適用・setattr・レジストリ登録）も実装として扱う。
    これが無いと planned Workset のモジュールへ `from ._impl import f as api_f` と書くだけで
    stray 検出も強制範囲も外れる（独立レビュー R13-23）。
    """
    from tools.gates.test_pairing import has_implementation
    from tools.gates.test_reality import binding_signals
    bound = {sig.split(":")[2] for sig in binding_signals(ctx)
             if sig.startswith("du-api-bind:") and len(sig.split(":")) > 2}
    out = []
    for du in s0_du_ids():
        mod = du_module(ctx, du)
        p = ROOT / mod
        if mod and (mod in bound or (p.is_file() and has_implementation(p))):
            out.append(mod)
    return sorted(out)


# ---------------------------------------------------------------- 検査本体
def schema_faults(data: dict | None) -> list[str]:
    if data is None:
        return [f"{WORKSETS.name} が無い・壊れている（fail-close）"]
    if not WORKSET_SCHEMA.is_file():
        return [f"{WORKSET_SCHEMA.name} が無い"]
    errs = schema_check(load(WORKSET_SCHEMA), data)
    if errs:
        return errs[:5]
    items = worksets_of(data)
    ids = [str(w["workset_id"]) for w in items]
    bad = []
    if len(ids) != len(set(ids)):
        bad.append(f"workset_id 重複:{sorted({i for i in ids if ids.count(i) > 1})}")
    covered = [du for w in items for du in w["du_ids"]]
    dup = sorted({d for d in covered if covered.count(d) > 1})
    if dup:
        bad.append(f"DU が複数 Workset に属する（レーンが重複している）:{dup}")
    if sorted(set(covered)) != s0_du_ids():
        missing = sorted(set(s0_du_ids()) - set(covered))
        extra = sorted(set(covered) - set(s0_du_ids()))
        bad.append(f"S0.1 の DU を過不足なく覆っていない（欠落={missing}, 範囲外={extra}）")
    for w in items:
        if w["status"] == "done" and not w["red_receipt"]:
            bad.append(f"{w['workset_id']}: done だが red_receipt が無い（red→green 証跡なし）")
        if w["coverage_floor"] < WORKSET_FLOOR:
            bad.append(f"{w['workset_id']}: coverage_floor={w['coverage_floor']} < {WORKSET_FLOOR}")
    return bad


def dependency_faults(ctx: Ctx, data: dict | None) -> list[str]:
    items = worksets_of(data)
    if not items:
        return ["Workset 正本が読めない（依存を導出できない）"]
    membership = {du: str(w["workset_id"]) for w in items
                  for du in (w.get("du_ids") or []) if isinstance(du, str)}
    order = [str(w.get("workset_id")) for w in items]
    edges = workset_edges(ctx, membership)
    bad: list[str] = []
    for w in items:
        wid = str(w.get("workset_id"))
        declared = set(w.get("depends_on") or [])
        derived = edges.get(wid, set())
        if wid in declared:
            bad.append(f"{wid}: 自分自身に依存している")
        if declared != derived:
            bad.append(f"{wid}: depends_on が DU 依存の導出と不一致 "
                       f"(宣言={sorted(declared)}, 導出={sorted(derived)})")
        unknown = sorted(declared - set(order))
        if unknown:
            bad.append(f"{wid}: 実在しない Workset へ依存:{unknown}")
    cycle = find_cycle({k: set(v) for k, v in edges.items()})
    if cycle:
        bad.append(f"Workset 依存が循環している:{'→'.join(cycle)}")
    bad += du_cycles_spanning(ctx, membership)
    # 配列順は ITC の割当（依存順で最後の Workset）の基準になるため、位相順であることを要求する。
    # 並べ替えるだけで宣言と導出が自己一致したまま割当先を変えられる（独立レビュー R13-08）。
    for i, wid in enumerate(order):
        late = sorted(d for d in edges.get(wid, set()) if d in order and order.index(d) > i)
        if late:
            bad.append(f"{wid}: 依存先が配列上で後ろにある（位相順でない）:{late}")
    return bad


def scope_faults(ctx: Ctx, data: dict | None) -> list[str]:
    items = worksets_of(data)
    if not items:
        return ["Workset 正本が読めない（スコープを導出できない）"]
    membership = {du: str(w["workset_id"]) for w in items
                  for du in (w.get("du_ids") or []) if isinstance(du, str)}
    order = [str(w.get("workset_id")) for w in items]
    itc = derive_itc(ctx, membership, order)
    bad: list[str] = []
    for w in items:
        wid = str(w.get("workset_id"))
        derived = derive_scope(ctx, [du for du in (w.get("du_ids") or []) if isinstance(du, str)])
        for key in ("api_ids", "ut_nodeids", "modules"):
            if sorted(str(x) for x in (w.get(key) or [])) != derived[key]:
                got = sorted(str(x) for x in (w.get(key) or []))
                bad.append(f"{wid}.{key} が正本からの導出と不一致 "
                           f"(余剰={sorted(set(got) - set(derived[key]))[:3]}, "
                           f"欠落={sorted(set(derived[key]) - set(got))[:3]})")
        if sorted(str(x) for x in (w.get("itc_ids") or [])) != itc.get(wid, []):
            bad.append(f"{wid}.itc_ids が itest.json からの導出と不一致 "
                       f"(宣言={sorted(str(x) for x in (w.get('itc_ids') or []))}, "
                       f"導出={itc.get(wid, [])})")
    # 着手していない Workset の製品コードを混ぜない（PO 指示 §6）
    started = started_worksets(data)
    started_mods = {m for w in started for m in (w.get("modules") or [])}
    stray = sorted(set(implemented_modules(ctx)) - started_mods)
    if stray:
        bad.append(f"着手済み Workset に属さないモジュールへ実装がある:{stray[:5]}")
    # 着手シグナルはあるのに in_progress／done の Workset が 1 つも無い状態を許さない
    # （どの Workset に着手したのかを宣言しないまま強制範囲だけ空にできる — R13-05）
    if ctx.impl_started and not started:
        bad.append("S0.1 着手が検出されているのに in_progress／done の Workset が 0 件"
                   "（着手先の Workset を宣言していない）")
    return bad


def test_reality_faults(ctx: Ctx, data: dict | None) -> list[str]:
    """着手済み Workset に対してのみ skip 解除・nodeid 単位 green・依存 done を強制する。"""
    from tools.gates.test_pairing import detect_ut_escapes
    from tools.gates.test_reality import load_outcome, outcome_index

    items = worksets_of(data)
    by_id = {str(w.get("workset_id")): w for w in items}
    idx = outcome_index(load_outcome())
    report = (ROOT / "reports/test-outcome.json").is_file()
    bad: list[str] = []
    for w in started_worksets(data):
        wid = str(w.get("workset_id"))
        dus = [du for du in (w.get("du_ids") or []) if isinstance(du, str)]
        escapes = detect_ut_escapes(ctx, du_ids=dus)
        if escapes:
            bad.append(f"{wid}: 対象 UT に skip／xfail／NotImplementedError／空 assert "
                       f"{len(escapes)} 件:{escapes[:3]}")
        if not report:
            bad.append(f"{wid}: outcome レポートが無い（executed+passed を実測できない）")
        else:
            for nid in derive_scope(ctx, dus)["ut_nodeids"]:
                got = idx.get(nid)
                if got != "passed":
                    bad.append(f"{wid}: {nid} が {got or '未実行（レポートに無い）'}")
        for dep in sorted(str(d) for d in (w.get("depends_on") or [])):
            if str((by_id.get(dep) or {}).get("status")) != "done":
                bad.append(f"{wid}: 依存 Workset {dep} が done でない")
        if w.get("status") == "done":
            bad += _receipt_faults(wid, w)
            bad += _itc_faults(wid, w, idx)
    return bad


def _itc_faults(wid: str, w: dict, idx: dict[str, str]) -> list[str]:
    """done を名乗る Workset の ITC（②↔④の統合テスト）が実際に green かを突合する。

    ITC を Workset へ割り当てても、完了条件として突き合わせなければ飾りにしかならない
    （独立レビュー R13-03）。`itc_evidence` が ITC ID → 実 nodeid を宣言し、その nodeid が
    outcome レポート上 passed であることを要求する。
    """
    declared = {str(i) for i in (w.get("itc_ids") or [])}
    evidence = w.get("itc_evidence")
    if not declared:
        return []
    if not isinstance(evidence, dict):
        return [f"{wid}: done だが itc_evidence が無い（割当 ITC={sorted(declared)}）"]
    bad: list[str] = []
    missing = sorted(declared - set(map(str, evidence)))
    extra = sorted(set(map(str, evidence)) - declared)
    if missing:
        bad.append(f"{wid}: itc_evidence に未記載の ITC:{missing}")
    if extra:
        bad.append(f"{wid}: itc_evidence に割当外の ITC:{extra}")
    for itc, nid in sorted((str(k), str(v)) for k, v in evidence.items()):
        got = idx.get(nid)
        if got != "passed":
            bad.append(f"{wid}: {itc} の {nid} が {got or '未実行（レポートに無い）'}")
    return bad


def _receipt_faults(wid: str, w: dict) -> list[str]:
    """done を名乗る Workset の red→green 証跡を検査する。

    「祖先の SHA を 1 つと nodeid を 1 件」書けば done を名乗れる状態は証跡ではない
    （独立レビュー R13-06）。ここでは (a) 割当 UT の**全件**が red 時に列挙されている
    (b) red_commit → green_commit → HEAD の祖先順序 (c) red_commit の時点で
    当該 Workset のモジュールに**実装実体が無い**（＝実装前に赤を踏んでいる）を要求する。
    """
    receipt = w.get("red_receipt")
    if not isinstance(receipt, dict):
        return [f"{wid}: done だが red_receipt が無い"]
    bad: list[str] = []
    sha = str(receipt.get("red_commit") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        bad.append(f"{wid}: red_commit が 40 桁 SHA でない")
    elif git("merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
        bad.append(f"{wid}: red_commit {sha[:8]} が HEAD の祖先でない（実在しない red）")
    else:
        bad += _red_precedes_implementation(wid, sha, w)
    nodeids = {str(n) for n in (receipt.get("nodeids") or [])}
    assigned = {str(n) for n in (w.get("ut_nodeids") or [])}
    outside = sorted(nodeids - assigned)
    lacking = sorted(assigned - nodeids)
    if not nodeids:
        bad.append(f"{wid}: red_receipt.nodeids が空")
    if outside:
        bad.append(f"{wid}: red_receipt.nodeids に Workset 外の nodeid:{outside[:3]}")
    if lacking:
        bad.append(f"{wid}: red_receipt.nodeids が割当 UT を網羅していない"
                   f"（{len(lacking)} 件不足:{lacking[:3]}）")
    green = receipt.get("green_commit")
    if green is None:
        # done で green_commit が null なら、順序検査そのものが発動しない（R13-10）
        bad.append(f"{wid}: done だが green_commit が null（red→green の到達点が無い）")
    else:
        g = str(green)
        if not re.fullmatch(r"[0-9a-f]{40}", g):
            bad.append(f"{wid}: green_commit が 40 桁 SHA でない")
        elif git("merge-base", "--is-ancestor", g, "HEAD").returncode != 0:
            bad.append(f"{wid}: green_commit が HEAD の祖先でない")
        elif g == sha:
            bad.append(f"{wid}: red_commit と green_commit が同一（red→green になっていない）")
        elif re.fullmatch(r"[0-9a-f]{40}", sha) \
                and git("merge-base", "--is-ancestor", sha, g).returncode != 0:
            bad.append(f"{wid}: red_commit が green_commit の祖先でない（順序が逆）")
    return bad


def _red_precedes_implementation(wid: str, sha: str, w: dict) -> list[str]:
    """red_commit の時点で当該 Workset のモジュールが未実装であることを確かめる。

    実装後の任意の祖先コミットを red と称する偽装を落とす（test-first の機械的裏付け）。
    """
    from tools.gates.test_pairing import has_implementation_source
    bad = []
    for mod in sorted(str(m) for m in (w.get("modules") or [])):
        shown = git("show", f"{sha}:{mod}")
        if shown.returncode != 0:
            continue  # red 時点でファイルが無い = 未実装（正しい）
        if has_implementation_source(shown.stdout):
            bad.append(f"{wid}: red_commit {sha[:8]} の時点で {mod} が既に実装済み"
                       "（実装後のコミットを red と称している）")
    return bad


def coverage_faults(ctx: Ctx, data: dict | None) -> list[str]:
    """coverage 80% を active＋done Workset の対象モジュール集合へ適用する配線を検査する。"""
    from tools.gates.test_pairing import coverage_floor

    bad: list[str] = []
    started = started_worksets(data)
    floor = coverage_floor(ctx)
    if started and floor < WORKSET_FLOOR:
        bad.append(f"着手済み Workset があるのに有効 coverage 下限が {floor}%")
    if not (ROOT / COVERAGE_SCOPE_TOOL).is_file():
        bad.append(f"{COVERAGE_SCOPE_TOOL} が無い（対象モジュール集合を CI へ供給できない）")
    bad += _ci_coverage_wiring()
    return bad


def _disabled(node: dict) -> bool:
    """`if: false` 相当で実行されない job／step か。"""
    cond = node.get("if")
    if isinstance(cond, bool):
        return not cond
    return isinstance(cond, str) and cond.strip().lower() in ("false", "${{ false }}")


def _conditional(node: dict) -> bool:
    """常に実行され、**失敗が CI に伝播する**とは限らない job／step か。

    「push のときだけ coverage を測る」構成にすると PR 経路で下限強制が消える。
    `continue-on-error: true` は「実行はされるが落ちない」だけで結果は同じなので同列に扱う
    （独立レビュー R13-14・R13-17）。
    """
    soft = node.get("continue-on-error")
    if soft is True or (isinstance(soft, str) and soft.strip().lower() in ("true", "${{ true }}")):
        return True
    cond = node.get("if")
    if cond is None:
        return False
    if isinstance(cond, bool):
        return not cond
    return str(cond).strip().lower() not in ("true", "${{ true }}")


def _resolver_step(steps: list[dict], step_id: str, tool: str) -> int | None:
    """`id: <step_id>` を持ち、そのツールを**実際に実行する** step の位置を返す。"""
    from tools.gates.test_reality import _command_lines, _invokes
    for i, s in enumerate(steps):
        if str(s.get("id") or "") != step_id:
            continue
        if any(_invokes(c, tool) for c in _command_lines(s)):
            return i
    return None


def _ci_coverage_wiring() -> list[str]:
    """python-ci が「対象モジュールの解決 → pytest へ引き渡し」を実際に配線しているか。

    参照される step id が**実際にそのツールを走らせる step の id** であり、かつ pytest より
    **前**にあることまで要求する（id をずらせば `${{ steps.X.outputs.Y }}` は空文字に評価され、
    `--cov` 無指定・`--cov-fail-under` 無効化と同じことが起きる — 独立レビュー R13-07）。
    """
    from tools.gates.test_reality import _command_lines, _load_yaml, _steps

    doc = _load_yaml(PYTHON_CI)
    if doc is None:
        return [f"{PYTHON_CI.name} を構造として読めない（fail-close）"]
    from tools.gates.test_reality import _runs_pytest
    bad: list[str] = []
    checked = 0
    for jname, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict) or _disabled(job):
            continue
        steps = _steps(job)
        # coverage 引数を持つコマンドは **pytest の実行**でなければならない。
        # 部分文字列一致だけだと `python3 -c pass --cov-fail-under=...` のダミーで
        # 配線検査を通しつつ実計測を外せる（独立レビュー R13-13）。
        cov_at = [i for i, s in enumerate(steps)
                  if any("--cov-fail-under" in c for c in _command_lines(s))]
        if not cov_at:
            continue
        if _conditional(job):
            bad.append(f"{jname}: coverage を測る job が条件付き実行（if: {job.get('if')}）")
        # `--cov-fail-under` を持つ **全** step を検査する（2 つ目以降を無検査にしない）
        for at in cov_at:
            checked += 1
            bad += _pytest_step_faults(str(jname), steps, at, doc, job)
        if not any(any(_runs_pytest(c) and "--cov-fail-under" in c for c in _command_lines(steps[i]))
                   for i in cov_at):
            bad.append(f"{jname}: coverage 下限を渡している実行主体が pytest でない")
    if not checked:
        return [f"{PYTHON_CI.name} に「coverage 対象の解決 → pytest」の配線が無い"]
    return bad


def _pytest_step_faults(jname: str, steps: list[dict], at: int,
                        doc: dict, job: dict) -> list[str]:
    """pytest step が解決結果を受け取り、resolver が無条件かつ前段にあることを確かめる。"""
    from tools.gates.test_reality import _command_lines, _runs_pytest
    bad: list[str] = []
    lines = [c for c in _command_lines(steps[at]) if "--cov-fail-under" in c]
    missing = [c for c in lines if COV_SCOPE_REF not in c or COV_FLOOR_REF not in c]
    if missing:
        bad.append(f"{jname}: pytest が coverage 対象／下限の解決結果を受け取っていない"
                   f":{missing[0][:80]}")
    not_pytest = [c for c in lines if not _runs_pytest(c)]
    if not_pytest:
        bad.append(f"{jname}: coverage 引数を持つが pytest の実行ではない:{not_pytest[0][:80]}")
    if _conditional(steps[at]):
        bad.append(f"{jname}: coverage を測る pytest step が条件付き実行・失敗許容"
                   f"（if: {steps[at].get('if')}, continue-on-error: "
                   f"{steps[at].get('continue-on-error')}）")
    for ref, step_id, tool in ((COV_SCOPE_REF, "covscope", COVERAGE_SCOPE_TOOL),
                               (COV_FLOOR_REF, "cov", COVERAGE_FLOOR_TOOL)):
        pos = _resolver_step(steps, step_id, tool)
        if pos is None:
            bad.append(f"{jname}: {ref} が指す step（id={step_id}）が {tool} を実行していない")
            continue
        if pos >= at:
            bad.append(f"{jname}: {ref} を解決する step（id={step_id}）が pytest より後ろにある")
        # 条件付き・失敗許容で走る resolver は「走らない経路」で outputs が空になり、
        # `--cov` 無指定・`--cov-fail-under` 無効化と同じ結果になる（R13-11・R13-17）。
        if _conditional(steps[pos]):
            bad.append(f"{jname}: resolver step（id={step_id}）が条件付き実行"
                       f"（if: {steps[pos].get('if')}）で、走らない経路では解決結果が空になる")
        bad += _canonical_faults(jname, steps[pos], f"resolver step（id={step_id}）")
        bad += _shell_faults(jname, doc, job, steps[pos], f"resolver step（id={step_id}）")
    bad += _canonical_faults(jname, steps[at], "coverage を測る pytest step")
    bad += _shell_faults(jname, doc, job, steps[at], "coverage を測る pytest step")
    return bad


# coverage／resolver の step に置いてよいのは正準コマンド 1 行だけ。以下はいずれも
# 「実行はされるが exit code が伝わらない」「実行主体が実体を指さない」を作れる
NON_CANONICAL = ("|", "&", ";", "$(", "`", "&&", "||")


def _raw_lines(step: dict) -> list[str] | None:
    """step の `run` を「コメント除去・行継続結合済みの実行行」の列にする。"""
    run = step.get("run")
    if not isinstance(run, str):
        return None
    joined = re.sub(r"\\\s*\n\s*", " ", run)
    return [ln for ln in (raw.split("#", 1)[0].strip() for raw in joined.splitlines()) if ln]


# `run` を実行するシェルとして認める値。カスタム shell（`bash -c "bash {0}; exit 0"` 等）は
# run 本文を正準 1 行に保ったまま exit code を握り潰せる（独立レビュー R13-19）
ALLOWED_SHELLS = ("bash", "sh")


def _effective_shell(doc: dict, job: dict, step: dict) -> object:
    """step へ実際に適用される shell（step → job defaults → workflow defaults）。"""
    for node in (step, job.get("defaults") or {}, doc.get("defaults") or {}):
        if not isinstance(node, dict):
            continue
        shell = node.get("shell") if node is step else ((node.get("run") or {}).get("shell")
                                                        if isinstance(node.get("run"), dict)
                                                        else None)
        if shell is not None:
            return shell
    return None


def _shell_faults(jname: str, doc: dict, job: dict, step: dict, label: str) -> list[str]:
    """coverage に関わる step のシェルが正準（bash／sh）であることを要求する。"""
    shell = _effective_shell(doc, job, step)
    if shell is None or str(shell).strip() in ALLOWED_SHELLS:
        return []
    return [f"{jname}: {label} のシェルが正準でない（shell: {shell!r}） — "
            "カスタム shell は run 本文を変えずに exit code を握り潰せる"]


def _canonical_faults(jname: str, step: dict, label: str) -> list[str]:
    """coverage に関わる step が**正準コマンド 1 行**だけであることを要求する。

    `set +e` で errexit を解除する、`| tee` で exit code を捨てる、同名のシェル関数を
    定義してから呼ぶ——といった回避はいずれも「pytest の周りに任意のシェルを書ける」
    ことに由来する。個別に禁止語を潰すのではなく、書ける形そのものを 1 行へ限定する
    （独立レビュー R13-16・R13-18）。リダイレクト（`>` `>>`）だけは step output への
    書き出しに要るため許す。
    """
    lines = _raw_lines(step)
    if lines is None:
        return [f"{jname}: {label} が run コマンドを持たない"]
    if len(lines) != 1:
        return [f"{jname}: {label} は正準コマンド 1 行のみ（{len(lines)} 行ある）:{lines[:2]}"]
    line = lines[0]
    found = sorted({tok for tok in NON_CANONICAL if tok in line})
    if found:
        return [f"{jname}: {label} に連結・パイプ・コマンド置換がある{found}:{line[:80]}"]
    return []


# ---------------------------------------------------------------- ラチェット
def _committed(path: Path, label: str) -> tuple[dict | None, str]:
    """**親コミット**（`HEAD^`）の JSON を返す（作業ツリーの同時改変では回避できない比較元）。

    比較元を `HEAD` にすると、CI は checkout したコミットそのものを作業ツリーに持つため
    「親比較」が常に自己比較になり、ラチェットが丸ごと空回りする（独立レビュー R13-01）。
    解決規約は `baseline.committed_baseline()` と同じ: 非 git ツリーは fail-close、
    親コミットが無い（初回コミット）と親に当該ファイルが無い（新設）だけを正常扱いにする。
    """
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        return None, f"{label}: git リポジトリではない（比較元を解決できない — fail-close）"
    if git("rev-parse", "--verify", "HEAD^").returncode != 0:
        return None, f"{label}: 親コミットなし（初回コミット）"
    rel_path = str(path.relative_to(ROOT))
    shown = git("show", f"HEAD^:{rel_path}")
    origin = "HEAD^"
    if shown.returncode != 0:
        # 「直前コミットで正本を削除 → 次のコミットで改変版を再追加」でラチェットを丸ごと
        # 外せてしまうため、履歴を遡って**最後に存在した版**を比較元にする（R13-09）。
        found = _last_committed_blob(rel_path)
        if found is None:
            return None, f"{label}: 履歴に一度も存在しない（新設）"
        origin, shown = found
    try:
        data = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return None, f"{label}: 比較元（{origin}）の内容が壊れている"
    return (data if isinstance(data, dict) else None), f"{label}: {origin}"


def _last_committed_blob(rel_path: str) -> tuple[str, Any] | None:
    """`HEAD^` 以前で当該パスの blob が存在した**最新のコミット**を返す。"""
    listed = git("rev-list", "HEAD^", "--", rel_path)
    if listed.returncode != 0:
        return None
    for sha in listed.stdout.split():
        shown = git("show", f"{sha}:{rel_path}")
        if shown.returncode == 0:
            return f"{sha[:12]}（削除前の最新版）", shown
    return None


# ratchet を「保護すべき値がまだ無い」として正常扱いにしてよい理由（それ以外は fail-close）
BENIGN_SOURCES = ("親コミットなし（初回コミット）", "履歴に一度も存在しない（新設）")


def _benign(source: str) -> bool:
    return any(source.endswith(s) for s in BENIGN_SOURCES)


def committed_worksets() -> tuple[dict | None, str]:
    return _committed(WORKSETS, "worksets")


def committed_skip_budget() -> tuple[int | None, str]:
    """親コミットの skip 上限を `(値, 出所)` で返す（解決不能は理由付きで返す）。

    None を黙って返すと `max_skipped` を消すだけで done 化時の引下げ要求が無検査になる
    （独立レビュー R13-02）。呼び出し側は理由付き None を fault として扱う。
    """
    data, source = _committed(SKIP_BUDGET, "skip-budget")
    if data is None:
        return None, source
    try:
        return int(data["max_skipped"]), source
    except (KeyError, TypeError, ValueError):
        return None, "skip-budget: 親コミットに max_skipped が無い・数値でない"


RANK = {"planned": 0, "in_progress": 1, "done": 2}


def ratchet_faults(data: dict | None, prev: dict | None, source: str,
                   skip_now: int | None = None, skip_prev: int | None = None,
                   skip_source: str = "") -> list[str]:
    """親コミット比で縮小・後退・緩和が無いことを検査する。"""
    bad: list[str] = []
    newly_done: list[dict] = []
    if prev is None:
        # 「壊れている」「非 git」は fail-close、「新設・初回」は保護すべき値が無いので正常。
        # ただし正本ごと新設して最初から done を書く経路があるため、skip 引下げ要求だけは
        # 打ち切らずに続ける（worksets 側の比較元不在で skip ラチェットまで消さない — R13-09）。
        if not _benign(source):
            return [source]
        newly_done = [w for w in worksets_of(data) if str(w.get("status")) == "done"]
        return bad + _skip_reduction_faults(newly_done, skip_now, skip_prev, skip_source)
    now = {str(w.get("workset_id")): w for w in worksets_of(data)}
    old = {str(w.get("workset_id")): w for w in worksets_of(prev)}
    for wid, o in sorted(old.items()):
        n = now.get(wid)
        if n is None:
            bad.append(f"{wid}: Workset が削除された")
            continue
        for key in ("du_ids", "api_ids", "ut_nodeids", "itc_ids", "depends_on"):
            lost = sorted({str(x) for x in (o.get(key) or [])}
                          - {str(x) for x in (n.get(key) or [])})
            if lost:
                bad.append(f"{wid}.{key} が縮小:{lost[:3]}")
        if RANK.get(str(n.get("status")), -1) < RANK.get(str(o.get("status")), -1):
            bad.append(f"{wid}: status が後退（{o.get('status')}→{n.get('status')}）")
        try:
            if int(n.get("coverage_floor", 0)) < int(o.get("coverage_floor", 0)):
                bad.append(f"{wid}: coverage_floor が低下"
                           f"（{o.get('coverage_floor')}→{n.get('coverage_floor')}）")
        except (TypeError, ValueError):
            bad.append(f"{wid}: coverage_floor が数値でない")
        old_receipt = o.get("red_receipt")
        if isinstance(old_receipt, dict):
            new_receipt = n.get("red_receipt")
            if not isinstance(new_receipt, dict) \
                    or new_receipt.get("red_commit") != old_receipt.get("red_commit"):
                bad.append(f"{wid}: 記録済みの red_receipt.red_commit が改変・削除された")
        if str(o.get("status")) != "done" and str(n.get("status")) == "done":
            newly_done.append(n)
    return bad + _skip_reduction_faults(newly_done, skip_now, skip_prev, skip_source)


def _skip_reduction_faults(newly_done: list[dict], skip_now: int | None,
                           skip_prev: int | None, skip_source: str) -> list[str]:
    """done へ進めた Workset は、解除した skip 件数以上を上限から減らす（PO 指示 §5）。

    複数を同時に done 化した場合は**和集合**で要求する（個別比較だと片方分の引下げで
    両方の判定を満たせてしまう — 独立レビュー R13-04）。
    """
    if not newly_done:
        return []
    released = {str(x) for w in newly_done for x in (w.get("ut_nodeids") or [])}
    ids = sorted(str(w.get("workset_id")) for w in newly_done)
    if skip_now is None or skip_prev is None:
        return [f"{ids}: done 化したが skip 上限の比較元を解決できない（{skip_source}）"]
    if skip_prev - skip_now < len(released):
        return [f"{ids}: done 化に伴う skip 上限の引下げが不足"
                f"（{skip_prev}→{skip_now}, 必要={len(released)} 件以上）"]
    return []


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    data = load_worksets()
    items = worksets_of(data)
    started = started_worksets(data)

    schema = schema_faults(data)
    gate("G-WORKSET-SCHEMA", not schema,
         "S0.1 Workset 正本が schema 準拠で、DU-01〜12 を重複なく過不足なく分割し、"
         "status 語彙・coverage_floor・done の red_receipt を満たす "
         f"(Workset={len(items)} 件, 違反={schema[:3]})")

    deps = dependency_faults(ctx, data)
    gate("G-WORKSET-DEPENDENCY", not deps,
         "depends_on が du-contracts の depends_on_apis から導出した Workset 依存と一致し、"
         "Workset 依存グラフが非循環で、DU 単位の相互依存（SCC）が Workset を跨がない "
         f"(違反={deps[:3]})")

    scope = scope_faults(ctx, data)
    gate("G-WORKSET-SCOPE", not scope,
         "api_ids／ut_nodeids／itc_ids／modules が DU／API／UT／ITC 正本からの導出と完全一致し、"
         "着手済み Workset に属さないモジュールへ製品実装が無い "
         f"(違反={scope[:3]})")

    reality = test_reality_faults(ctx, data)
    gate("G-WORKSET-TEST-REALITY", not reality,
         "着手済み（in_progress／done）Workset だけに、対象 UT の skip／xfail／"
         "NotImplementedError／空 assert = 0・nodeid 単位 executed+passed・依存 Workset の done・"
         "done の red→green 証跡を強制（未着手 Workset のスタブは猶予） "
         f"(着手={[str(w.get('workset_id')) for w in started]}, 違反={len(reality)} 件"
         f"{'' if not reality else f':{reality[:3]}'})")

    cov = coverage_faults(ctx, data)
    gate("G-WORKSET-COVERAGE", not cov,
         f"coverage {WORKSET_FLOOR}% は helix 全体ではなく active＋done Workset の対象モジュール"
         "集合へ適用され、その解決結果が CI の pytest へ実際に引き渡されている "
         f"(対象={len(enforced_modules(ctx, data))} モジュール, 違反={cov[:3]})")

    prev, source = committed_worksets()
    skip_prev, skip_source = committed_skip_budget()
    ratchet = ratchet_faults(data, prev, source,
                             skip_now=int(ctx.skip_budget.get("max_skipped", 0)),
                             skip_prev=skip_prev, skip_source=skip_source)
    gate("G-WORKSET-RATCHET", not ratchet,
         "親コミット比で Workset の削除・DU／API／UT／ITC／依存の縮小・status 後退"
         "（done→in_progress 等）・coverage_floor 低下・red_receipt 改変が無く、"
         "done 化には解除 skip 件数以上の上限引下げを伴う "
         f"(比較元={source}, 違反={ratchet[:3]})")
