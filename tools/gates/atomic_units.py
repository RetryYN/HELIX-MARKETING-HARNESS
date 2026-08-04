"""S0.1 原子単位（1 製品 PR の単位）ゲート。

依存 Workset（実装レーン A←B←C）は**実装順・依存閉包・統合完了**を管理する上位レーンであり、
PR の単位ではない。PR の単位は本モジュールが扱う**原子単位**である（PO 指示 §2〜§4）。

原則は「公開 API 1 本＝1 原子単位」。複数 API の結合は `depends_on_apis` から独立導出した
API 依存グラフの SCC に限る。例外には構造化 `merge_reason`
（code=`same_scc`／detail／negative_test_nodeids）を要し、negative test が実在しなければ
結合を認めない。原子単位自身の宣言を導出入力へ戻す自己参照は行わない。

Workset の status は原子単位から**導出**する（全 planned → planned／1 件以上 in_progress か
done → in_progress／全 done かつ Workset ITC green → done）。red→green 証跡は Workset ではなく
原子単位が持ち、Workset ITC は必要 API がすべて done になる**最後の原子単位**で green を要求する。

fail-close の方針は Workset ゲートと同じである。正本が**無い・壊れている・S0.1 の API を
過不足なく覆っていない**なら、強制範囲を S0.1 全 API へ倒す（正本を消せば強制が消える
fail-open を作らない）。
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from tools.gates import worksets as ws
from tools.gates.common import (
    IMPL_UNITS_CONTRACTS,
    L6,
    ROOT,
    Ctx,
    gate,
    git,
    load,
    reachable_nodes,
    schema_check,
)

ATOMIC_DIR = L6 / "S0/atomic-units"
ATOMIC_INDEX = ATOMIC_DIR / "index.json"
ATOMIC_SCHEMA = ATOMIC_DIR / "atomic-unit.schema.json"
INDEX_SCHEMA = ATOMIC_DIR / "index.schema.json"
ATOMIC_DIR_REL = "docs/L6-feature-design/S0/atomic-units"

STARTED_STATUS = ("in_progress", "done")
ATOMIC_FLOOR = 80
MERGE_CODES = ("same_scc",)
RANK = {"planned": 0, "in_progress": 1, "done": 2}

TESTS_UNIT_REL = "tests/unit"
SRC_PKG_REL = "src/helix"


# ---------------------------------------------------------------- 正本の読み取り

def load_index(path: Path = ATOMIC_INDEX) -> dict | None:
    """原子単位の索引を読む。壊れていれば None（呼出側が fail-close する）。"""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_units(index: dict | None, root: Path = ATOMIC_DIR) -> list[dict] | None:
    """索引が指す AU-*.json を索引順に読む。1 件でも壊れていれば None。"""
    if not index or not isinstance(index.get("units"), list):
        return None
    out: list[dict] = []
    for entry in index["units"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            return None
        name = entry["file"]
        if "/" in name or ".." in name or not name.startswith("AU-"):
            return None
        p = root / name
        if not p.is_file():
            return None
        try:
            unit = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(unit, dict):
            return None
        out.append(unit)
    return out


def unit_files(root: Path = ATOMIC_DIR) -> list[str]:
    """ディレクトリ上に実在する AU-*.json（索引漏れ・野良ファイルの検出に使う）。"""
    return sorted(p.name for p in root.glob("AU-*.json")) if root.is_dir() else []


# ------------------------------------------------------------------ 機械導出

def s0_apis(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """S0.1（DU-01〜12）の全 API のメタ情報を api_id で引ける形にする。"""
    out: dict[str, dict[str, Any]] = {}
    s0 = set(ws.s0_du_ids())
    for du in ctx.duc:
        if du["id"] not in s0:
            continue
        for api in du.get("apis", []):
            clauses = [c["clause_id"]
                       for key in ("precondition", "postcondition", "raises")
                       for c in api.get(key, []) if c.get("clause_id")]
            out[api["api_id"]] = {
                "du_id": du["id"],
                "fn": api["signature"].split("(")[0].replace("def ", "").strip(),
                "module": f"{SRC_PKG_REL}/{du['module']}",
                "clause_ids": clauses,
                "ut_nodeids": [f"{TESTS_UNIT_REL}/{u['nodeid']}" for u in api.get("ut", [])],
            }
    return out


def _clause_text(api: dict) -> str:
    parts = []
    for key in ("precondition", "postcondition", "raises"):
        for c in api.get(key, []):
            parts += [str(c.get("text", "")), str(c.get("when", "")), str(c.get("type", ""))]
    return " ".join(parts)


def api_edges(ctx: Ctx) -> dict[str, set[str]]:
    """API 依存グラフを `depends_on_apis` から機械導出する。

    `depends_on_apis` は DU 単位の宣言（例 `"DU-10: connect()"`）なので、被参照側は
    関数名で API へ解決できる。参照側は、その関数名を**契約節本文で名指ししている API**
    へ帰属させる。名指しが無い場合だけ、その DU の全 API へ倒す（fail-close の過大近似 —
    依存を落として着手順を緩めるより、余分な依存で厳しくする側へ倒す）。
    """
    apis = s0_apis(ctx)
    by_du_fn = {(m["du_id"], m["fn"]): aid for aid, m in apis.items()}
    edges: dict[str, set[str]] = {aid: set() for aid in apis}
    s0 = set(ws.s0_du_ids())
    for du in ctx.duc:
        if du["id"] not in s0:
            continue
        own = [a["api_id"] for a in du.get("apis", [])]
        for dep in du.get("depends_on_apis", []):
            m = re.match(r"\s*(DU-\d\d)\s*:\s*(.*)", str(dep))
            if not m:
                continue
            target_du, rest = m.group(1), m.group(2)
            for fn in re.findall(r"([a-z_][a-z0-9_]*)\(\)", rest):
                target = by_du_fn.get((target_du, fn))
                if target is None:          # S0.1 外の DU への依存は対象外
                    continue
                named = [a["api_id"] for a in du.get("apis", [])
                         if re.search(rf"\b{re.escape(fn)}\b", _clause_text(a))]
                for src in (named or own):
                    if src != target:
                        edges[src].add(target)
    return edges


def sccs(edges: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan の SCC（明示スタック版）。決定的な順序で返す。"""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on: dict[str, bool] = {}
    stack: list[str] = []
    out: list[list[str]] = []
    counter = 0
    for root in sorted(edges):
        if root in index:
            continue
        work: list[list[Any]] = [[root, 0]]
        while work:
            frame = work[-1]
            v, pi = frame[0], frame[1]
            if pi == 0:
                index[v] = low[v] = counter
                counter += 1
                stack.append(v)
                on[v] = True
            succ = sorted(edges.get(v, ()))
            if pi < len(succ):
                frame[1] = pi + 1
                w = succ[pi]
                if w not in index:
                    work.append([w, 0])
                elif on.get(w):
                    low[v] = min(low[v], index[w])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on[w] = False
                    comp.append(w)
                    if w == v:
                        break
                out.append(sorted(comp))
    return sorted(out)


def unit_id_of(api_ids: list[str]) -> str:
    """原子単位 ID は構成 API の最小 ID から決まる（位相順に振らない＝並べ替えで ID が動かない）。"""
    return "AU-" + sorted(api_ids)[0].replace("API-", "")


def derive_units(ctx: Ctx) -> dict[str, dict[str, Any]]:
    """S0.1 の全 API を上流依存グラフの SCC だけから機械導出する。"""
    apis = s0_apis(ctx)
    edges = api_edges(ctx)
    comps = sccs(edges)
    lead_of = {aid: unit_id_of(comp) for comp in comps for aid in comp}
    du2ws = {du: w["workset_id"]
             for w in ws.worksets_of(ws.load_worksets()) for du in w["du_ids"]}
    iu_by_api: dict[str, list[str]] = {}
    for item in (load(IMPL_UNITS_CONTRACTS).get("items", [])
                 if IMPL_UNITS_CONTRACTS.is_file() else []):
        iu_by_api.setdefault(str(item.get("api_ref")), []).append(str(item.get("unit_id")))

    out: dict[str, dict[str, Any]] = {}
    for comp in comps:
        uid = unit_id_of(comp)
        members = [apis[a] for a in comp]
        deps = sorted({lead_of[t] for a in comp for t in edges[a] if lead_of[t] != uid})
        lanes = sorted({du2ws.get(m["du_id"], "?") for m in members})
        out[uid] = {
            "atomic_unit_id": uid,
            "workset_id": lanes[0] if len(lanes) == 1 else "|".join(lanes),
            "api_ids": sorted(comp),
            "clause_ids": sorted({c for m in members for c in m["clause_ids"]}),
            "implementation_unit_ids": sorted({u for a in comp for u in iu_by_api.get(a, [])}),
            "ut_nodeids": sorted({u for m in members for u in m["ut_nodeids"]}),
            "modules": sorted({m["module"] for m in members}),
            "depends_on_atomic_units": deps,
            "is_scc": len(comp) > 1,
        }
    return out


def terminal_units(ctx: Ctx, units: list[dict] | None) -> dict[str, str]:
    """レーンごとの「最後の原子単位」（Workset ITC の green を要求する単位）を求める。

    そのレーンの全原子単位を依存の位相順に並べ、最後に来る単位が終端である。
    """
    if not units:
        return {}
    order = _topo_order(units)
    last: dict[str, str] = {}
    for uid in order:
        unit = next((u for u in units if str(u.get("atomic_unit_id")) == uid), None)
        if unit:
            last[str(unit.get("workset_id"))] = uid
    return last


def _topo_order(units: list[dict]) -> list[str]:
    """原子単位を依存の位相順（決定的）に並べる。循環があれば残りを ID 順で後置する。"""
    edges = {str(u.get("atomic_unit_id")): {str(d) for d in (u.get("depends_on_atomic_units") or [])}
             for u in units}
    done: list[str] = []
    seen: set[str] = set()
    while True:
        ready = sorted(u for u, deps in edges.items() if u not in seen and deps <= seen)
        if not ready:
            break
        done += ready
        seen |= set(ready)
    return done + sorted(set(edges) - seen)


# ------------------------------------------------------------ 状態と強制範囲

def started_units(units: list[dict] | None) -> list[dict]:
    return [u for u in (units or []) if u.get("status") in STARTED_STATUS]


def canonical_broken(ctx: Ctx, index: dict | None, units: list[dict] | None) -> str | None:
    """正本が強制の土台として使えるかを判定し、使えない理由（＝全 API へ倒す理由）を返す。"""
    if index is None or units is None:
        return "原子単位正本が無い／壊れている"
    if sorted(str(e.get("file")) for e in index.get("units", [])) != unit_files():
        return "index.json と AU-*.json の集合が一致しない"
    covered = [str(a) for u in units for a in (u.get("api_ids") or [])]
    if len(covered) != len(set(covered)):
        return "同一 API が複数の原子単位に属する"
    if sorted(set(covered)) != sorted(s0_apis(ctx)):
        return "S0.1 の API を過不足なく覆っていない"
    if any(u.get("status") not in (*STARTED_STATUS, "planned") for u in units):
        return "status が planned／in_progress／done 以外"
    if ctx.impl_started and not started_units(units):
        return "実装着手が検出されたのに in_progress／done の原子単位が 0 件"
    return None


def enforced_units(ctx: Ctx, index: dict | None = None,
                   units: list[dict] | None = None) -> list[dict] | None:
    """強制対象の原子単位。正本が使えなければ None（呼出側が S0.1 全体へ倒す）。"""
    if index is None and units is None:
        index = load_index()
        units = load_units(index)
    return None if canonical_broken(ctx, index, units) else started_units(units)


def enforced_nodeids(ctx: Ctx) -> list[str] | None:
    units = enforced_units(ctx)
    return None if units is None else sorted({str(n) for u in units for n in u["ut_nodeids"]})


def enforced_modules(ctx: Ctx) -> list[str] | None:
    units = enforced_units(ctx)
    return None if units is None else sorted({str(m) for u in units for m in u["modules"]})


def derived_workset_status(units: list[dict] | None, workset_id: str,
                           itc_green: bool = False) -> str:
    """Workset（実装レーン）の status を所属原子単位から導出する（PO 指示 §3）。"""
    mine = [u for u in (units or []) if str(u.get("workset_id")) == workset_id]
    if not mine:
        return "planned"
    if all(u.get("status") == "done" for u in mine):
        return "done" if itc_green else "in_progress"
    if any(u.get("status") in STARTED_STATUS for u in mine):
        return "in_progress"
    return "planned"


def workset_itc_green(units: list[dict] | None, workset_id: str,
                      idx: dict[str, str] | None = None) -> bool:
    """レーン終端の原子単位が Workset ITC を実 nodeid で green にしているか。"""
    if idx is None:
        from tools.gates.test_reality import load_outcome, outcome_index
        idx = outcome_index(load_outcome())
    for unit in (units or []):
        if str(unit.get("workset_id")) != workset_id:
            continue
        evidence = unit.get("itc_evidence")
        if isinstance(evidence, dict) and evidence:
            return all(idx.get(str(v)) == "passed" for v in evidence.values())
    return False


# ------------------------------------------------------------------ G-ATOMIC-SCHEMA

def schema_faults(ctx: Ctx, index: dict | None, units: list[dict] | None) -> list[str]:
    """正本の構造・API の完全分割・結合例外の正当性を検査する。"""
    if index is None:
        return ["原子単位の索引 index.json が無い／壊れている"]
    bad = list(schema_check(load(INDEX_SCHEMA), index, "index.json"))
    if units is None:
        return bad + ["索引が指す AU-*.json を読めない（欠落・壊れ・索引外パス）"]
    unit_schema = load(ATOMIC_SCHEMA)
    for u in units:
        bad += schema_check(unit_schema, u, str(u.get("atomic_unit_id", "?")))

    listed = sorted(str(e.get("file")) for e in index.get("units", []))
    if listed != unit_files():
        bad.append(f"index.json と実ファイルの集合が不一致（索引={listed[:3]} / 実在={unit_files()[:3]}）")

    ids = [str(u.get("atomic_unit_id")) for u in units]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    if dup_ids:
        bad.append(f"atomic_unit_id が重複:{dup_ids}")
    for u in units:
        uid = str(u.get("atomic_unit_id"))
        if f"{uid}.json" not in unit_files():
            bad.append(f"{uid}: ファイル名が atomic_unit_id と一致しない")

    apis = s0_apis(ctx)
    covered = [str(a) for u in units for a in (u.get("api_ids") or [])]
    dup = sorted({a for a in covered if covered.count(a) > 1})
    if dup:
        bad.append(f"同一 API が複数の原子単位に属する（分割でない）:{dup}")
    if sorted(set(covered)) != sorted(apis):
        missing = sorted(set(apis) - set(covered))
        extra = sorted(set(covered) - set(apis))
        bad.append(f"S0.1 の API を過不足なく覆っていない（欠落={missing}, 範囲外={extra}）")

    derived = derive_units(ctx)
    terminals = terminal_units(ctx, units)
    for u in units:
        uid = str(u.get("atomic_unit_id"))
        if u.get("coverage_floor", 0) < ATOMIC_FLOOR:
            bad.append(f"{uid}: coverage_floor={u.get('coverage_floor')} < {ATOMIC_FLOOR}")
        if u.get("status") == "done":
            if not u.get("red_receipt"):
                bad.append(f"{uid}: done だが red_receipt が無い")
            if not u.get("green_receipt"):
                bad.append(f"{uid}: done だが green_receipt が無い")
        is_terminal = terminals.get(str(u.get("workset_id"))) == uid
        declared = [str(i) for i in (u.get("workset_itc_ids") or [])]
        want = _lane_itc(u.get("workset_id")) if is_terminal else []
        if sorted(declared) != sorted(want):
            bad.append(f"{uid}: workset_itc_ids が導出と不一致（正本={sorted(declared)} / "
                       f"導出={sorted(want)}。ITC はレーン終端の原子単位が持つ）")
        bad += _merge_faults(uid, u, derived.get(uid))
    return bad


def _lane_itc(workset_id: Any) -> list[str]:
    """レーン（Workset）へ割り当てられた ITC。Workset 正本が唯一の出所である。"""
    for w in ws.worksets_of(ws.load_worksets()):
        if w["workset_id"] == str(workset_id):
            return [str(i) for i in (w.get("itc_ids") or [])]
    return []


def _merge_faults(uid: str, unit: dict, derived: dict | None) -> list[str]:
    """複数 API の結合が独立導出した SCC であることを機械検査する。"""
    api_ids = [str(a) for a in (unit.get("api_ids") or [])]
    reason = unit.get("merge_reason")
    if len(api_ids) <= 1:
        return [f"{uid}: 単一 API なのに merge_reason を持つ"] if reason else []
    if not isinstance(reason, dict):
        return [f"{uid}: 複数 API（{api_ids}）を結合しているのに merge_reason が無い"]
    bad: list[str] = []
    code = reason.get("code")
    if code not in MERGE_CODES:
        bad.append(f"{uid}: merge_reason.code が {MERGE_CODES} 以外（{code}）")
    if not str(reason.get("detail") or "").strip():
        bad.append(f"{uid}: merge_reason.detail が空（任意結合と区別できない）")
    tests = [str(n) for n in (reason.get("negative_test_nodeids") or [])]
    if not tests:
        bad.append(f"{uid}: merge_reason に negative_test_nodeids が無い（結合の否定検査が無い）")
    for nid in tests:
        bad += _negative_test_faults(uid, nid)
    bad += _merge_code_faults(uid, unit, code, derived)
    return bad


def _negative_test_faults(uid: str, nid: str) -> list[str]:
    """negative test が実在し、**この原子単位を名指しで**検証していることを要求する。

    実在確認だけでは、結合と無関係な既存テストの nodeid を書いておけば例外を通せる
    （独立レビュー R15-03）。当該テスト関数の本体に atomic_unit_id が現れることを要求し、
    「どの結合を否定しているのか」を機械が辿れる形にする。
    """
    rel_path, _, name = nid.partition("::")
    path = ROOT / rel_path
    if not path.is_file():
        return [f"{uid}: negative test {nid} が実在しない"]
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [f"{uid}: negative test {nid} を解析できない"]
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
    if fn is None:
        return [f"{uid}: negative test {nid} が実在しない"]
    doc = ast.get_docstring(fn)
    bearers = _uid_statements(fn, uid, doc)
    if not bearers:
        return [f"{uid}: negative test {nid} が {uid} を**使われる値として**扱っていない"
                "（コメント・docstring・未使用変数に ID を書いただけでは否定検査にならない）"]
    calls = _asserted_production_calls(fn, _production_names(tree))
    if not calls:
        return [f"{uid}: negative test {nid} が本番のゲート関数（tools.gates.atomic_units）を"
                "到達可能な位置で呼び、その結果を assert していない（拒否を実測していない）"]
    if not any(_connected(stmt, call) for stmt in bearers for call in calls):
        return [f"{uid}: negative test {nid} の {uid} が、assert している本番呼出しへ"
                "つながっていない（別の単位を検査しているだけ）"]
    return []


# 自己参照（`_negative_test_faults` を呼ぶだけ）でトートロジーを作れないよう、
# 本検査そのものは根拠として認めない（独立レビュー R15-10）。
PRODUCTION_ENTRIES = ("schema_faults", "dependency_faults", "_merge_faults",
                      "_merge_code_faults", "derive_units")


def _uid_statements(fn: ast.AST, uid: str, doc: str | None) -> list[ast.stmt]:
    """uid が **到達可能な位置で使われる値**として現れる文を返す（未使用変数への代入は除く）。"""
    used_names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
                  and isinstance(n.ctx, ast.Load)}
    reachable = {id(n) for n in reachable_nodes(fn)}
    out: list[ast.stmt] = []
    for stmt in ast.walk(fn):
        if not isinstance(stmt, ast.stmt) or stmt is fn or id(stmt) not in reachable:
            continue
        if not any(isinstance(c, ast.Constant) and isinstance(c.value, str)
                   and c.value != doc and uid in c.value for c in ast.walk(stmt)):
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if names and not (names & used_names):
                continue          # 誰も読まない変数に ID を置いただけ
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue              # 文字列リテラルを置いただけ（docstring 相当）
        out.append(stmt)
    return out


def _stmt_names(stmt: ast.stmt) -> set[str]:
    """文が触れる変数名（代入先と参照名の両方）。"""
    names = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)}
    return names


def _connected(stmt: ast.stmt, call: ast.Call) -> bool:
    """uid を持つ文と、assert している本番呼出しが同じ値へつながっているか。

    同一文の場合と、文が触れる変数のいずれかが呼出しの引数に現れる場合を接続とみなす。
    これが無いと「uid は print に渡すだけ、検査対象は別単位」という偽装が通る
    （独立レビュー R15-14）。
    """
    if any(c is call for c in ast.walk(stmt)):
        return True
    arg_names = {n.id for a in [*call.args, *(k.value for k in call.keywords)]
                 for n in ast.walk(a) if isinstance(n, ast.Name)}
    return bool(_stmt_names(stmt) & arg_names)


def _production_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """`tools.gates.atomic_units` を指すモジュール別名と、直接 import された本番関数名。"""
    modules: set[str] = set()
    direct: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.endswith("tools.gates.atomic_units"):
                    modules.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            for a in node.names:
                if module == "tools.gates" and a.name == "atomic_units":
                    modules.add(a.asname or a.name)
                elif module == "tools.gates.atomic_units" and a.name in PRODUCTION_ENTRIES:
                    direct.add(a.asname or a.name)
    return modules, direct


def _asserted_production_calls(fn: ast.AST,
                               origins: tuple[set[str], set[str]]) -> list[ast.Call]:
    """本番のゲート関数を**到達可能な位置**で呼び、結果を assert している呼出しを返す。

    `assert gate(...)` の直接形と、`faults = gate(...)` → `assert any(... faults ...)` の
    代入経由の両方を認める。到達不能（`if False:` 配下）の呼出し、`_negative_test_faults`
    自身の呼出し（自己参照）、同名のローカル関数・偽 receiver（出所が
    `tools.gates.atomic_units` でない）は根拠にしない（独立レビュー R15-14）。
    """
    asserted_nodes: set[int] = set()
    asserted_names: set[str] = set()
    for node in reachable_nodes(fn):
        if isinstance(node, ast.Assert):
            for child in ast.walk(node):
                asserted_nodes.add(id(child))
                if isinstance(child, ast.Name):
                    asserted_names.add(child.id)
    out: list[ast.Call] = []
    reachable = list(reachable_nodes(fn))
    for node in reachable:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if names & asserted_names:
                out += [c for c in ast.walk(node)
                        if isinstance(c, ast.Call) and _production_call(c, origins)]
        if isinstance(node, ast.Call) and id(node) in asserted_nodes \
                and _production_call(node, origins):
            out.append(node)
    return out


def _production_call(node: ast.Call, origins: tuple[set[str], set[str]]) -> bool:
    """呼出先が **tools.gates.atomic_units の本番関数**であることを出所まで確かめる。"""
    modules, direct = origins
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in PRODUCTION_ENTRIES and isinstance(func.value, ast.Name) \
            and func.value.id in modules
    if isinstance(func, ast.Name):
        return func.id in direct
    return False


def _merge_code_faults(uid: str, unit: dict, code: Any, derived: dict | None) -> list[str]:
    """結合理由が独立導出した SCC と一致することを要求する。"""
    if code == "same_scc":
        if derived is None or not derived.get("is_scc"):
            return [f"{uid}: merge_reason.code=same_scc だが API 依存グラフ上 SCC ではない"]
        return []
    return [f"{uid}: merge_reason.code は same_scc のみ許可（{code}）"]


# -------------------------------------------------------------- G-ATOMIC-DEPENDENCY

DERIVED_KEYS = ("workset_id", "api_ids", "clause_ids", "implementation_unit_ids",
                "ut_nodeids", "modules", "depends_on_atomic_units")


def dependency_faults(ctx: Ctx, index: dict | None, units: list[dict] | None) -> list[str]:
    """導出値との完全一致・非循環・SCC 非分断・レーン依存との整合を検査する。"""
    if units is None:
        return ["原子単位正本を読めないため依存導出と突合できない"]
    derived = derive_units(ctx)
    bad: list[str] = []
    for u in units:
        uid = str(u.get("atomic_unit_id"))
        d = derived.get(uid)
        if d is None:
            bad.append(f"{uid}: 導出結果に存在しない原子単位（手書きの単位）")
            continue
        for key in DERIVED_KEYS:
            want = d[key]
            got = u.get(key)
            if isinstance(want, list):
                got = sorted(str(x) for x in (got or []))
            else:
                got = str(got)
            if got != want:
                bad.append(f"{uid}: {key} が導出と不一致"
                           f"（正本={got if not isinstance(got, list) else got[:3]} /"
                           f" 導出={want if not isinstance(want, list) else want[:3]}）")
    for uid in sorted(derived):
        if uid not in {str(u.get("atomic_unit_id")) for u in units}:
            bad.append(f"{uid}: 導出された原子単位が正本に無い（分割の欠落）")

    ids = {str(u.get("atomic_unit_id")) for u in units}
    edges = {str(u.get("atomic_unit_id")):
             {str(d) for d in (u.get("depends_on_atomic_units") or [])} for u in units}
    for uid, deps in sorted(edges.items()):
        unknown = sorted(deps - ids)
        if unknown:
            bad.append(f"{uid}: 実在しない原子単位へ依存:{unknown}")
        if uid in deps:
            bad.append(f"{uid}: 自己参照の依存")
    cycle = ws.find_cycle({k: v & ids for k, v in edges.items()})
    if cycle:
        bad.append(f"原子単位の依存が循環:{cycle}")

    api_scc = {frozenset(c) for c in sccs(api_edges(ctx)) if len(c) > 1}
    for comp in sorted(api_scc, key=sorted):
        owners = {str(u.get("atomic_unit_id")) for u in units
                  if set(map(str, u.get("api_ids") or [])) & comp}
        if len(owners) > 1:
            bad.append(f"API の相互依存（SCC）{sorted(comp)} が原子単位 {sorted(owners)} へ分断されている")

    lanes = {w["workset_id"]: {str(x) for x in (w.get("depends_on") or [])}
             for w in ws.worksets_of(ws.load_worksets())}
    lane_of = {str(u.get("atomic_unit_id")): str(u.get("workset_id")) for u in units}
    for uid, deps in sorted(edges.items()):
        mine = lane_of.get(uid)
        for dep in sorted(deps & ids):
            other = lane_of.get(dep)
            if other and mine and other != mine and other not in lanes.get(mine, set()):
                bad.append(f"{uid}（{mine}）が {dep}（{other}）へ依存するが、"
                           f"レーン {mine} は {other} に依存していない（レーン依存と矛盾）")
    return bad


# ---------------------------------------------------------------- G-ATOMIC-PR-SCOPE

def _merge_base() -> tuple[str | None, str]:
    for ref in ("origin/main", "main"):
        if git("rev-parse", "--verify", ref).returncode != 0:
            continue
        res = git("merge-base", "HEAD", ref)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), ref
    return None, "解決不能"


def changed_paths() -> tuple[list[str] | None, str]:
    """main との分岐点から HEAD まで＋作業ツリーの変更パス（＝この PR の変更範囲）。"""
    base, ref = _merge_base()
    if base is None:
        return None, "main との分岐点を解決できない"
    diff = git("diff", "--name-only", f"{base}..HEAD")
    work = git("status", "--porcelain")
    if diff.returncode != 0 or work.returncode != 0:
        return None, "git の変更一覧を取得できない"
    paths = {p for p in diff.stdout.split("\n") if p.strip()}
    for line in work.stdout.splitlines():
        if len(line) > 3:
            paths.add(line[3:].strip().strip('"').split(" -> ")[-1])
    return sorted(paths), ref


def _inert(rel_path: str) -> bool:
    """`src/helix` 配下で製品コードとして数えない変更（実体なしの純パッケージ初期化のみ）。

    拡張子で `.py` に限ると、ソースレス `.pyc` や拡張モジュール `.so` を原子単位外へ
    置くだけで実装本体を持ち込める（独立レビュー R15-13）。したがって `src/helix` 配下は
    **拡張子を問わず**製品変更として扱い、猶予するのは実体も再エクスポートも動的ロードも
    持たない `__init__.py`（および削除）だけにする。
    """
    return rel_path.endswith(".py") and _reexport_only(rel_path)


def _reexport_only(rel_path: str) -> bool:
    """`__init__.py` のうち**実体も再エクスポートも持たない**ものだけを猶予する。

    `__init__.py` を無条件に除外すると、着手単位の modules 外の実装を任意個の
    `__init__.py` へ置いて 1 製品 PR へ混入できてしまう（独立レビュー R15-01）。
    さらに `def` を書かずとも `from helix.kernel.state import transition` と 1 行書けば
    実装は外から呼べるので、パッケージ内シンボルの再エクスポートも製品コードとして扱う
    （同 R15-06）。ファイルが消えている場合（削除）だけが猶予対象である。
    """
    from tools.gates.test_pairing import carries_product_code
    if not rel_path.endswith("__init__.py"):
        return False
    path = ROOT / rel_path
    return not path.is_file() or not carries_product_code(path)


def pr_scope_faults(ctx: Ctx, units: list[dict] | None) -> list[str]:
    """1 製品 PR で in_progress にできる原子単位を 1 件に限り、変更範囲をその単位へ閉じる。"""
    if units is None:
        return ["原子単位正本を読めないため PR スコープを判定できない"]
    active = [u for u in units if u.get("status") == "in_progress"]
    bad: list[str] = []
    if len(active) > 1:
        bad.append("in_progress の原子単位が複数（1 製品 PR = 1 原子単位）:"
                   f"{sorted(str(u.get('atomic_unit_id')) for u in active)}")
    paths, source = changed_paths()
    if paths is None:
        return bad + ([f"変更範囲を判定できない（{source}）"] if (active or ctx.impl_started) else [])
    product = [p for p in paths if p.startswith(f"{SRC_PKG_REL}/") and not _inert(p)]
    unit_tests = [p for p in paths if p.startswith(f"{TESTS_UNIT_REL}/")]
    if not active:
        stray = sorted(product)
        if stray:
            bad.append(f"in_progress の原子単位が無いのに製品コードを変更している:{stray[:5]}")
        return bad
    unit = active[0]
    uid = str(unit.get("atomic_unit_id"))
    mods = {str(m) for m in (unit.get("modules") or [])}
    own_tests = {str(n).split("::")[0] for n in (unit.get("ut_nodeids") or [])}
    outside = sorted(p for p in product if p not in mods)
    if outside:
        bad.append(f"{uid} の modules 外の製品コードが同じ PR に混入:{outside[:5]}")
    stray_tests = sorted(p for p in unit_tests if p not in own_tests)
    if stray_tests:
        bad.append(f"{uid} の割当 UT 以外のテストファイルが同じ PR に混入:{stray_tests[:5]}")
    others = sorted(p for p in paths
                    if p.startswith(f"{ATOMIC_DIR_REL}/AU-") and not p.endswith(f"/{uid}.json"))
    if others:
        bad.append(f"{uid} 以外の原子単位正本が同じ PR で変更されている"
                   f"（status・receipt の巻き込み）:{[Path(p).name for p in others][:5]}")
    return bad


# ------------------------------------------------------------ G-ATOMIC-TEST-REALITY

def test_reality_faults(ctx: Ctx, units: list[dict] | None) -> list[str]:
    """着手済み原子単位だけに red→green・skip 解除・nodeid 単位 PASS・契約節被覆を強制する。"""
    if units is None:
        return ["原子単位正本を読めないため着手強制を原子単位へ限定できない"]
    from tools.gates.test_reality import load_outcome, outcome_index
    idx = outcome_index(load_outcome())
    by_id = {str(u.get("atomic_unit_id")): u for u in units}
    bad: list[str] = []
    for u in units:
        uid = str(u.get("atomic_unit_id"))
        status = u.get("status")
        if status not in STARTED_STATUS:
            continue
        for dep in sorted(str(d) for d in (u.get("depends_on_atomic_units") or [])):
            if by_id.get(dep, {}).get("status") != "done":
                bad.append(f"{uid}: 依存原子単位 {dep} が done でないのに着手している")
        for nid in sorted(str(n) for n in (u.get("ut_nodeids") or [])):
            got = idx.get(nid)
            if got != "passed":
                bad.append(f"{uid}: {nid} が {got or '未実行（レポートに無い）'}")
        bad += _clause_coverage_faults(ctx, uid, u)
        if status == "done":
            bad += _receipt_faults(uid, u)
            bad += _itc_faults(uid, u, idx)
            bad += _terminal_order_faults(uid, u, units)
    return bad


def _terminal_order_faults(uid: str, unit: dict, units: list[dict]) -> list[str]:
    """レーン終端の原子単位は、そのレーンの他の単位が全て done になるまで done にできない。

    Workset ITC は「必要 API がすべて done になった最後の原子単位」で green を要求する
    （PO 指示 §4）。終端が先に done になれる状態では、ITC を要求する時点で必要 API が
    揃っていないことがあり、要求そのものが空振りになる。
    """
    if not (unit.get("workset_itc_ids") or []):
        return []
    lane = str(unit.get("workset_id"))
    rest = sorted(str(u.get("atomic_unit_id")) for u in units
                  if str(u.get("workset_id")) == lane
                  and str(u.get("atomic_unit_id")) != uid and u.get("status") != "done")
    return [f"{uid}: レーン終端が done だが {lane} に未完了の原子単位が残っている:{rest[:5]}"] \
        if rest else []


def _clause_coverage_faults(ctx: Ctx, uid: str, unit: dict) -> list[str]:
    """原子単位の全契約節が UT の clause_refs か na_reason で被覆されていることを要求する。"""
    covered: set[str] = set()
    exempt: set[str] = set()
    wanted = {str(a) for a in (unit.get("api_ids") or [])}
    for du in ctx.duc:
        for api in du.get("apis", []):
            if api["api_id"] not in wanted:
                continue
            for key in ("precondition", "postcondition", "raises"):
                for c in api.get(key, []):
                    if c.get("na_reason"):
                        exempt.add(str(c["clause_id"]))
            for ut in api.get("ut", []):
                covered |= {str(c) for c in ut.get("clause_refs", [])}
    missing = sorted({str(c) for c in (unit.get("clause_ids") or [])} - covered - exempt)
    return [f"{uid}: 契約節が UT でも na_reason でも被覆されていない:{missing[:5]}"] if missing else []


def _red_precedes_implementation(uid: str, sha: str, unit: dict) -> list[str]:
    """red_commit の時点で当該原子単位のモジュールが未実装であることを確かめる。

    実装後の任意の祖先コミットを red と称する偽装を落とす（test-first の機械的裏付け）。
    """
    from tools.gates.test_pairing import has_implementation_source
    bad = []
    for mod in sorted(str(m) for m in (unit.get("modules") or [])):
        shown = git("show", f"{sha}:{mod}")
        if shown.returncode != 0:
            continue          # red 時点でファイルが無い = 未実装（正しい）
        if has_implementation_source(shown.stdout):
            bad.append(f"{uid}: red_commit {sha[:8]} の時点で {mod} が既に実装済み"
                       "（実装後のコミットを red と称している）")
    return bad


def _receipt_faults(uid: str, unit: dict) -> list[str]:
    """done を名乗る原子単位の red→green 証跡を検査する（Workset から移設）。"""
    bad: list[str] = []
    red = unit.get("red_receipt")
    green = unit.get("green_receipt")
    assigned = {str(n) for n in (unit.get("ut_nodeids") or [])}
    if not isinstance(red, dict):
        return [f"{uid}: done だが red_receipt が無い"]
    sha = str(red.get("red_commit") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        bad.append(f"{uid}: red_commit が 40 桁 SHA でない")
    elif git("merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
        bad.append(f"{uid}: red_commit {sha[:8]} が HEAD の祖先でない（実在しない red）")
    else:
        bad += _red_precedes_implementation(uid, sha, unit)
    red_ids = {str(n) for n in (red.get("nodeids") or [])}
    if not red_ids:
        bad.append(f"{uid}: red_receipt.nodeids が空")
    outside = sorted(red_ids - assigned)
    lacking = sorted(assigned - red_ids)
    if outside:
        bad.append(f"{uid}: red_receipt.nodeids に単位外の nodeid:{outside[:3]}")
    if lacking:
        bad.append(f"{uid}: red_receipt.nodeids が割当 UT を網羅していない"
                   f"（{len(lacking)} 件不足:{lacking[:3]}）")
    if not isinstance(green, dict):
        return bad + [f"{uid}: done だが green_receipt が無い"]
    g = str(green.get("green_commit") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", g):
        bad.append(f"{uid}: green_commit が 40 桁 SHA でない")
    elif git("merge-base", "--is-ancestor", g, "HEAD").returncode != 0:
        bad.append(f"{uid}: green_commit が HEAD の祖先でない")
    elif g == sha:
        bad.append(f"{uid}: red_commit と green_commit が同一（red→green になっていない）")
    elif re.fullmatch(r"[0-9a-f]{40}", sha) \
            and git("merge-base", "--is-ancestor", sha, g).returncode != 0:
        bad.append(f"{uid}: red_commit が green_commit の祖先でない（順序が逆）")
    green_ids = {str(n) for n in (green.get("nodeids") or [])}
    if green_ids != assigned:
        bad.append(f"{uid}: green_receipt.nodeids が割当 UT と一致しない"
                   f"（不足={sorted(assigned - green_ids)[:3]} 余分={sorted(green_ids - assigned)[:3]}）")
    return bad


def _itc_faults(uid: str, unit: dict, idx: dict[str, str]) -> list[str]:
    """レーン終端の原子単位が done を名乗るとき、Workset ITC の green を実 nodeid で要求する。"""
    declared = {str(i) for i in (unit.get("workset_itc_ids") or [])}
    if not declared:
        return []
    evidence = unit.get("itc_evidence")
    if not isinstance(evidence, dict):
        return [f"{uid}: done だが itc_evidence が無い（レーン ITC={sorted(declared)}）"]
    bad: list[str] = []
    missing = sorted(declared - set(map(str, evidence)))
    extra = sorted(set(map(str, evidence)) - declared)
    if missing:
        bad.append(f"{uid}: itc_evidence に未記載の ITC:{missing}")
    if extra:
        bad.append(f"{uid}: itc_evidence に割当外の ITC:{extra}")
    for itc, nid in sorted((str(k), str(v)) for k, v in evidence.items()):
        got = idx.get(nid)
        if got != "passed":
            bad.append(f"{uid}: {itc} の {nid} が {got or '未実行（レポートに無い）'}")
    return bad


# ------------------------------------------------------------- G-ATOMIC-COVERAGE

def coverage_faults(ctx: Ctx, units: list[dict] | None) -> list[str]:
    """coverage 80% を着手済み原子単位のモジュール集合へ適用する配線を検査する。"""
    from tools.gates.test_pairing import coverage_floor
    bad: list[str] = []
    if units is None:
        return ["原子単位正本を読めないため coverage 適用範囲を判定できない"]
    started = started_units(units)
    floor = coverage_floor(ctx)
    if started and floor < ATOMIC_FLOOR:
        bad.append(f"着手済み原子単位があるのに有効 coverage 下限が {floor}%")
    for u in started:
        if u.get("coverage_floor", 0) > floor:
            bad.append(f"{u.get('atomic_unit_id')}: 宣言 coverage_floor={u.get('coverage_floor')}"
                       f" が有効下限 {floor} を上回る（宣言が効いていない）")
    scope = enforced_modules(ctx)
    if started and not scope:
        bad.append("着手済み原子単位があるのに coverage 対象モジュールが空")
    bad += ws._ci_coverage_wiring()
    return bad


# -------------------------------------------------------------- G-ATOMIC-RATCHET

def committed_units() -> tuple[list[dict] | None, str]:
    """親コミット（HEAD^）時点の原子単位。取得元の説明を添えて返す。

    解決規約は Workset 側（`worksets._committed`）と揃える。非 git ツリーは
    **fail-close**（良性扱いにしない）。HEAD^ に無ければ履歴を遡り、削除される前の
    最後の版を比較元にする（「削除コミット → 改変版を再追加」でラチェットを丸ごと
    無効化できた経路を塞ぐ — 独立レビュー R15-02）。
    """
    if git("rev-parse", "--git-dir").returncode != 0:
        return None, "git リポジトリではない（比較元を解決できない — fail-close）"
    parent = git("rev-parse", "--verify", "HEAD^")
    if parent.returncode != 0:
        return None, "親コミットなし（初回コミット）"
    listing = git("ls-tree", "--name-only", "HEAD^", f"{ATOMIC_DIR_REL}/")
    names = [n for n in listing.stdout.split("\n")
             if listing.returncode == 0 and n.endswith(".json") and "/AU-" in n]
    source = "HEAD^"
    if not names:
        revived = _last_committed_units()
        if revived is None:
            return None, "履歴に一度も存在しない（新設）"
        names, source = revived
    out: list[dict] = []
    for name in sorted(names):
        blob = git("show", f"{source}:{name}")
        if blob.returncode != 0:
            return None, f"{source} の {name} を読めない（比較元が壊れている）"
        try:
            data = json.loads(blob.stdout)
        except json.JSONDecodeError:
            return None, f"{source} の {name} が壊れている"
        if not isinstance(data, dict):
            return None, f"{source} の {name} が壊れている"
        out.append(data)
    return out, source


def _last_committed_units() -> tuple[list[str], str] | None:
    """原子単位正本が**最後に存在した**コミットとそのファイル一覧を履歴から探す。"""
    log = git("log", "--format=%H", "-n", "50", "HEAD^", "--", f"{ATOMIC_DIR_REL}/")
    if log.returncode != 0:
        return None
    for sha in [c for c in log.stdout.split("\n") if c.strip()]:
        listing = git("ls-tree", "--name-only", sha, f"{ATOMIC_DIR_REL}/")
        names = [n for n in listing.stdout.split("\n")
                 if listing.returncode == 0 and n.endswith(".json") and "/AU-" in n]
        if names:
            return names, sha
    return None


SHRINK_KEYS = ("api_ids", "clause_ids", "implementation_unit_ids",
               "ut_nodeids", "modules", "depends_on_atomic_units")


def ratchet_faults(units: list[dict] | None, prev: list[dict] | None, source: str,
                   skip_now: int | None, skip_prev: int | None,
                   skip_source: str = "HEAD^") -> list[str]:
    """完了・スコープ・依存・証跡の後退を拒否する（PO 指示 §4 のラチェット）。"""
    if prev is None:
        # 比較元が無くても「正本ごと新設して最初から done を書く」経路があるため、
        # skip 引下げ要求だけは打ち切らない（Workset 側 R13-09 と同じ規律 — R15-02）。
        newly = [u for u in (units or []) if str(u.get("status")) == "done"]
        base = [] if ws._benign(source) else [f"比較元を解決できない（{source}）"]
        return base + _skip_faults(newly, skip_now, skip_prev, skip_source)
    if units is None:
        return ["現在の原子単位正本を読めない（ラチェット検査不能）"]
    now = {str(u.get("atomic_unit_id")): u for u in units}
    bad: list[str] = []
    newly_done: list[dict] = []
    for uid, old in sorted((str(p.get("atomic_unit_id")), p) for p in prev):
        cur = now.get(uid)
        if cur is None:
            bad.append(f"{uid}: 原子単位が削除されている")
            continue
        for key in SHRINK_KEYS:
            lost = sorted({str(x) for x in (old.get(key) or [])}
                          - {str(x) for x in (cur.get(key) or [])})
            if lost:
                bad.append(f"{uid}: {key} が縮小（消えた要素={lost[:3]}）")
        if RANK.get(str(cur.get("status")), -1) < RANK.get(str(old.get("status")), -1):
            bad.append(f"{uid}: status が後退（{old.get('status')} → {cur.get('status')}）")
        if (cur.get("coverage_floor") or 0) < (old.get("coverage_floor") or 0):
            bad.append(f"{uid}: coverage_floor が低下"
                       f"（{old.get('coverage_floor')} → {cur.get('coverage_floor')}）")
        for key, field in (("red_receipt", "red_commit"), ("green_receipt", "green_commit")):
            was = (old.get(key) or {}).get(field) if isinstance(old.get(key), dict) else None
            is_ = (cur.get(key) or {}).get(field) if isinstance(cur.get(key), dict) else None
            if was and is_ != was:
                bad.append(f"{uid}: 記録済み {key}.{field} が改変（{str(was)[:8]} → {str(is_)[:8]}）")
        if str(old.get("status")) != "done" and str(cur.get("status")) == "done":
            newly_done.append(cur)
    bad += _skip_faults(newly_done, skip_now, skip_prev, skip_source)
    return bad


def _skip_faults(newly_done: list[dict], skip_now: int | None, skip_prev: int | None,
                 source: str) -> list[str]:
    """done 化した原子単位で解除した skip 件数以上を、全体 skip 上限から減らす。"""
    if skip_now is None:
        return ["skip 上限を読めない（ラチェット検査不能）"]
    if skip_prev is None:
        return [] if ws._benign(source) else [f"skip 上限の比較元を解決できない（{source}）"]
    bad: list[str] = []
    if skip_now > skip_prev:
        bad.append(f"skip 上限が増加（{skip_prev} → {skip_now}）")
    released = len({str(n) for u in newly_done for n in (u.get("ut_nodeids") or [])})
    if released and skip_prev - skip_now < released:
        bad.append(f"done 化した原子単位 {sorted(str(u.get('atomic_unit_id')) for u in newly_done)} の"
                   f"解除 UT {released} 件に対し、skip 上限の引下げが {skip_prev - skip_now} 件しかない")
    return bad

# --------------------------------------------------------------------------- run

def run(ctx: Ctx) -> None:
    index = load_index()
    units = load_units(index)
    broken = canonical_broken(ctx, index, units)
    started = started_units(units)
    scope = f"S0.1 全 API へ倒す（{broken}）" if broken else \
        f"着手済み {len(started)}/{len(units or [])} 原子単位"

    schema = schema_faults(ctx, index, units)
    gate("G-ATOMIC-SCHEMA", not schema,
         "原子単位正本（index.json＋AU-*.json）が schema 準拠で、S0.1 の全 API を重複なく"
         "過不足なく分割し、複数 API の結合は独立導出した SCC に限り、"
         "merge_reason（same_scc）と実在する negative test を伴う "
         f"(原子単位={len(units or [])} 件, 違反={schema[:3]})")

    deps = dependency_faults(ctx, index, units)
    gate("G-ATOMIC-DEPENDENCY", not deps,
         "api_ids／clause_ids／implementation_unit_ids／ut_nodeids／modules／"
         "depends_on_atomic_units／workset_id が正本からの導出と完全一致し、原子単位の依存が"
         "非循環で、API の相互依存（SCC）が原子単位を跨がず、レーン依存と矛盾しない "
         f"(違反={deps[:3]})")

    pr = pr_scope_faults(ctx, units)
    gate("G-ATOMIC-PR-SCOPE", not pr,
         "1 製品 PR で in_progress にできる原子単位は 1 件だけで、製品コードとテストの変更が"
         "その単位の modules／割当 UT に閉じている（別原子単位・別レーンの混入を拒否） "
         f"(違反={pr[:3]})")

    reality = test_reality_faults(ctx, units)
    gate("G-ATOMIC-TEST-REALITY", not reality,
         "着手済み原子単位だけに、依存単位の done・割当 UT の nodeid 単位 executed+passed・"
         "契約節被覆・done の red→green 証跡・レーン終端での Workset ITC green を強制する "
         f"(強制範囲={scope}, 違反={len(reality)} 件"
         f"{'' if not reality else f':{reality[:3]}'})")

    cov = coverage_faults(ctx, units)
    gate("G-ATOMIC-COVERAGE", not cov,
         f"coverage {ATOMIC_FLOOR}% を helix 全体ではなく着手済み原子単位のモジュール集合へ適用し、"
         "その解決結果が CI の pytest へ実際に引き渡されている "
         f"(対象={len(enforced_modules(ctx) or [])} モジュール, 違反={cov[:3]})")

    prev, source = committed_units()
    skip_prev, skip_source = ws.committed_skip_budget()
    ratchet = ratchet_faults(units, prev, source,
                             skip_now=int(ctx.skip_budget.get("max_skipped", 0)),
                             skip_prev=skip_prev, skip_source=skip_source)
    gate("G-ATOMIC-RATCHET", not ratchet,
         "親コミット比で原子単位の削除・API／契約節／UT／モジュール／依存の縮小・status 後退・"
         "coverage_floor 低下・記録済み receipt の改変が無く、done 化には解除 skip 件数以上の"
         "上限引下げを伴う "
         f"(比較元={source}, 違反={ratchet[:3]})")
