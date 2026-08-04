"""文書ペア・test-first 実体化ゲート: ①↔③／②↔④／⑤↔⑥ のペア、S0.1 着手の自動検出、
skip・coverage の逃げ道封じ（PO 指示 §6）。"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tools.gates.baseline import committed_baseline
from tools.gates.common import (
    BASIC_DESIGN,
    COVERAGE_FLOOR,
    DETAILED_DESIGN,
    INTEGRATION_TEST_DESIGN,
    L1,
    L3,
    L6,
    ROOT,
    S0_CONTRACT,
    S0_DU_MAX,
    TESTS_UNIT,
    UNIT_TEST_DESIGN,
    VERIFICATION_DESIGN,
    Ctx,
    gate,
    git,
    load,
    reachable_nodes,
    rel,
    ut_nodeids,
)

# ①（要件定義側）↔③（検証設計側）の対称参照対象
PAIRED_L3_DOCS = [
    L3 / "canonical/functional/requirements_v0.1.md",
    S0_CONTRACT,
    L1 / "canonical/br-media_v0.1.md",
    L1 / "canonical/loop-task-workflow_v0.1.md",
    L3 / "canonical/functional/media-requirements_v0.1.md",
]
S0_PLAN = L6 / "S0/plan-s0.1.json"
SRC_PKG = ROOT / "src/helix"
COVERAGE_STARTED_FLOOR = 80


def has_implementation_source(source: str) -> bool:
    """ソース文字列が実体（関数・クラス・lambda）を持つかを AST で判定する。

    ファイルを介さない純関数にしてあるのは、`git show <sha>:<path>` の出力を
    一時ファイルへ書かずにそのまま判定できるようにするため（独立レビュー R13-12）。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True  # 解析不能は fail-close（実装ありとみなす）
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
               for n in ast.walk(tree))


def has_reexport_source(source: str) -> bool:
    """パッケージ内シンボルの**再エクスポート**を持つかを AST で判定する。

    `def` を 1 つも書かなくても `from helix.kernel.state import transition` と
    `__init__.py` に書けば実装は外から呼べる。実体判定（`has_implementation`）だけでは
    この持ち込みが素通りするため、`helix` 由来の import／相対 import／`__all__` 宣言を
    製品コードの変更として扱う（独立レビュー R15-06）。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True  # 解析不能は fail-close
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                return True
            if str(node.module or "").split(".")[0] == "helix":
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "helix" for a in node.names):
                return True
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                return True
    return False


DYNAMIC_LOADERS = ("exec", "eval", "compile", "import_module", "__import__",
                   "load_module", "exec_module", "spec_from_file_location",
                   "run_path", "run_module", "module_from_spec", "ModuleType",
                   "loads", "load", "interact", "runcode", "runsource")


def has_dynamic_load_source(source: str) -> bool:
    """実行時にコードを持ち込む記述（exec／eval／compile／動的 import／sys.path 操作）を検出する。

    `exec("def transition(): ...")` と 1 行書けば、AST 上に `def` を一切残さずに実装を
    定義できる。静的な実体判定・再エクスポート判定だけでは素通りするため、動的ロードは
    **内容を問わず** fail-close で製品コード扱いにする（独立レビュー R15-09）。
    `src.helix` 経由の import（sys.path 操作つきの別名参照）も同様に扱う。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True
    for node in ast.walk(tree):
        # 危険 callable は「呼ばれた形」だけでなく**名前として現れた時点**で製品コード扱いにする。
        # `_x = exec` や `getattr(builtins, "exec")`、`from importlib import import_module as g`
        # のような別名束縛・間接取得で回避できてしまうためである（独立レビュー R15-12）。
        if isinstance(node, ast.Name) and node.id in DYNAMIC_LOADERS:
            return True
        if isinstance(node, ast.Attribute):
            if node.attr in DYNAMIC_LOADERS:
                return True
            if isinstance(node.value, ast.Attribute) and node.value.attr == "path":
                return True
            if isinstance(node.value, ast.Name) and node.value.id == "sys" \
                    and node.attr == "path":
                return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value in DYNAMIC_LOADERS:
            return True                      # getattr(builtins, "exec") 形
        if isinstance(node, ast.ImportFrom):
            if str(node.module or "").split(".")[:2] == ["src", "helix"]:
                return True
            if any(a.name in DYNAMIC_LOADERS for a in node.names):
                return True
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[:2] == ["src", "helix"] for a in node.names):
                return True
    return False


def carries_product_code(path: Path) -> bool:
    """実体（def／class／lambda）・再エクスポート・間接束縛・動的ロードのいずれかを持つか。

    PR スコープ（G-ATOMIC-PR-SCOPE）と stray 検出（G-WORKSET-SCOPE）で**同じ述語**を
    使うためのもの。片方が弱い述語だと、partial 束縛やデコレータ適用による持ち込みが
    一方だけ素通りする（独立レビュー R15-06）。動的ロードも含めるのは、`exec` で実体を
    実行時に定義すれば静的判定を全部抜けられるため（同 R15-09）。
    """
    from tools.gates.test_reality import file_bindings
    source = path.read_text(encoding="utf-8")
    return (has_implementation_source(source) or has_reexport_source(source)
            or has_dynamic_load_source(source) or bool(file_bindings(path)))


def has_implementation(path: Path) -> bool:
    """再エクスポート・docstring 以外の実体（関数・クラス・lambda）を持つかを AST で判定する。

    `__init__.py` に実装を置く迂回を塞ぐ。トップレベル直下だけでなく `ast.walk` で全階層を
    見るため、`if` ブロック内の条件付き定義や `f = lambda ...` も実装として扱う。
    """
    return has_implementation_source(path.read_text(encoding="utf-8"))


def _display(p: Path) -> str:
    """リポジトリ相対パスで表示する（差替えられた検査対象は絶対パスのまま返す）。"""
    try:
        return rel(p)
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- 着手の自動検出
def impl_start_signals(ctx: Ctx) -> list[str]:
    """S0.1 着手を示す**自動**シグナルを列挙する（手動宣言は含めない）。"""
    sig: list[str] = []
    extra = sorted(_display(p) for p in SRC_PKG.rglob("*.py") if has_implementation(p))
    if extra:
        sig.append(f"src-impl:{extra[:3]}")
    if S0_PLAN.exists():
        # `done` も着手済みとして扱う。in_progress を飛ばして done を書けば
        # G-UT-NO-ESCAPE・coverage 下限・G-S0-TEST-REALITY を全部迂回できてしまう
        # （独立レビュー R4-01 の fail-open）。
        st = load(S0_PLAN).get("status")
        if st in ("in_progress", "done"):
            sig.append(f"plan:{st}")
    api_impl = detect_du_api_implementations(ctx)
    if api_impl:
        sig.append(f"du-api:{api_impl[:3]}")
    # `def` を書かない間接束縛（partial・デコレータ適用・別名・setattr）も着手として扱う。
    # ここに載せることで skip 上限・coverage 下限・G-UT-NO-ESCAPE のラチェットが同時に発火する
    # （遅延 import — test_reality は s0_target_uts のために本モジュールを参照する）。
    from tools.gates.test_reality import binding_signals
    bindings = binding_signals(ctx)
    if bindings:
        sig.append(f"bind:{bindings[:3]}")
    # 原子単位を in_progress／done にした時点で着手である。宣言だけ先に立てて
    # coverage 下限・skip ラチェットを 0 のままにしておく経路を塞ぐ（PO 指示 §4）。
    from tools.gates import atomic_units as au
    started = [str(u.get("atomic_unit_id"))
               for u in au.started_units(au.load_units(au.load_index()))]
    if started:
        sig.append(f"atomic:{sorted(started)[:3]}")
    return sig


def detect_du_api_implementations(ctx: Ctx) -> list[str]:
    """DU-01〜12 の公開 API が src/ 配下に実装（def 定義）されている箇所を列挙する。"""
    found: list[str] = []
    for d in ctx.duc:
        if int(d["id"][3:]) > S0_DU_MAX:
            continue
        module = d["module"].strip().rstrip(":：")
        base = module.replace(".", "/")
        candidates = [ROOT / "src" / f"{base}.py", ROOT / "src" / base / "__init__.py"]
        for path in candidates:
            if not path.exists():
                continue
            txt = path.read_text(encoding="utf-8")
            for a in d["apis"]:
                m = re.match(r"def (\w+)", a["signature"])
                if m and re.search(rf"^\s*(?:async )?def {re.escape(m.group(1))}\b", txt, re.M):
                    found.append(f"{d['id']}:{m.group(1)}")
    return sorted(found)


def detect_impl_started(ctx: Ctx) -> bool:
    """自動検出 or 手動宣言のいずれかが立てば着手済みとして扱う（手動宣言だけに依存しない）。"""
    return bool(impl_start_signals(ctx)) or bool(ctx.skip_budget.get("s0_impl_started"))


def s0_target_uts(ctx: Ctx) -> list[tuple[str, str, str]]:
    """S0.1 対象 UT の (DU, ファイル名, テスト関数名) を列挙する。"""
    out: list[tuple[str, str, str]] = []
    for d in ctx.duc:
        if int(d["id"][3:]) > S0_DU_MAX:
            continue
        for a in d["apis"]:
            for ref in ut_nodeids(a):
                if "::" in ref:
                    fname, tname = ref.split("::", 1)
                    out.append((d["id"], fname, tname))
    return out


SKIP_MARKS = {"skip", "skipif", "xfail"}
SKIP_CALLS = {"skip", "xfail"}
MODULE_LEVEL_CALLS = {"skip", "xfail", "exit"}
# skip／検証 API の由来として認めるモジュール（`@custom.skip` のような同名の自作 API を誤検出しない）
TEST_FRAMEWORKS = ("pytest", "_pytest", "unittest")
# 検証行為として認める呼出し（いずれも由来がテストフレームワークであることを要求する）
VERIFY_CALLS = {"raises", "warns", "fail"}


ALIAS_PASSES = 5  # 別名の連鎖（a = pytest; b = a; b.skip()）を解くための固定点反復の上限


def _origins(tree: ast.Module) -> dict[str, str]:
    """ローカル名 → **フレームワーク起点の完全パス**を返す（pytest／unittest 系のみ）。

    局所名だけでなく元シンボル名を保持するのが要点。これがないと
    `from pytest import skip as s` の `s()` が SKIP_CALLS と照合できず素通りする。

    | 記述 | 記録される値 |
    |---|---|
    | `import pytest` | `pytest → "pytest"` |
    | `import pytest as p` | `p → "pytest"` |
    | `from pytest import skip` | `skip → "pytest.skip"` |
    | `from pytest import skip as s` | `s → "pytest.skip"` |
    | `mark = pytest.mark` | `mark → "pytest.mark"`（別名代入の固定点解決） |
    """
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in TEST_FRAMEWORKS:
                    out[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.split(".")[0] in TEST_FRAMEWORKS:
                for a in node.names:
                    # `from pytest import *` は裸名すべてを当該モジュール由来として扱う
                    out["*" if a.name == "*" else (a.asname or a.name)] = (
                        mod if a.name == "*" else f"{mod}.{a.name}")
    # 別名代入（`p = pytest` / `mark = pytest.mark` / `s = skip` / タプル / 注釈付き /
    # セイウチ）を固定点まで畳み込む
    for _ in range(ALIAS_PASSES):
        grew = False
        for tgt, value in _alias_bindings(tree):
            if tgt.id in out:
                continue
            path = _resolve(value, out)
            if path:
                out[tgt.id] = path
                grew = True
        if not grew:
            break
    return out


def _alias_bindings(tree: ast.Module) -> list[tuple[ast.Name, ast.expr]]:
    """`名前 = 式` の対応を列挙する（タプル代入は位置対応、注釈付き・セイウチも拾う）。"""
    pairs: list[tuple[ast.Name, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    pairs.append((tgt, node.value))
                elif isinstance(tgt, (ast.Tuple, ast.List)) \
                        and isinstance(node.value, (ast.Tuple, ast.List)) \
                        and len(tgt.elts) == len(node.value.elts):
                    pairs += [(t, v) for t, v in zip(tgt.elts, node.value.elts, strict=True)
                              if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.value is not None:
            pairs.append((node.target, node.value))
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            pairs.append((node.target, node.value))
    return pairs


def _resolve(node: ast.AST, origins: dict[str, str]) -> str | None:
    """式をフレームワーク起点の完全パスへ解決する（解決できなければ None）。

    `pytest.mark.skip` → `"pytest.mark.skip"`、`s`（= `skip as s`）→ `"pytest.skip"`、
    `p.skip`（= `pytest as p`）→ `"pytest.skip"`。
    """
    parts: list[str] = []
    while True:
        if isinstance(node, ast.NamedExpr):
            node = node.value  # `(s := pytest.skip)('x')` の即時呼出し
        elif isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        else:
            break
    if isinstance(node, ast.Name):
        if node.id in origins:
            return ".".join([origins[node.id], *reversed(parts)])
        if "*" in origins:  # star import 経由の裸名
            return ".".join([origins["*"], node.id, *reversed(parts)])
    return None


def _resolved_leaf(node: ast.AST, origins: dict[str, str], names: set[str]) -> str | None:
    """式が `names` のいずれかのフレームワーク API を指すなら、その末端名を返す。"""
    path = _resolve(node, origins)
    if path is None:
        return None
    leaf = path.rsplit(".", 1)[-1]
    return leaf if leaf in names else None


def _is_skip_expr(node: ast.AST, origins: dict[str, str]) -> bool:
    """pytest.mark.skip / skipif / xfail、unittest.skip 系の式かを import 解決込みで判定する。"""
    return any(_resolved_leaf(sub, origins, SKIP_MARKS)
               for sub in ast.walk(node) if isinstance(sub, (ast.Attribute, ast.Name)))


def _escape_call(call: ast.Call, origins: dict[str, str], names: set[str]) -> str | None:
    """テストフレームワーク由来の skip／xfail 呼出しなら、その名前を返す。

    `pytest.skip()` に加えて `from pytest import skip [as s]` 経由の裸呼出し、別名代入経由、
    `getattr(pytest, "skip")()` の動的取得も拾う（デコレータ側と同じ語彙・同じ解決器を共有）。
    """
    leaf = _resolved_leaf(call.func, origins, names)
    if leaf:
        return leaf
    fn = call.func
    if isinstance(fn, ast.Call) and isinstance(fn.func, ast.Name) and fn.func.id == "getattr" \
            and len(fn.args) >= 2:
        attr = fn.args[1]
        if _resolve(fn.args[0], origins) and isinstance(attr, ast.Constant) \
                and attr.value in names:
            return str(attr.value)
    return None


def _module_level_escapes(tree: ast.Module, origins: dict[str, str]) -> list[str]:
    """module 単位の skip（pytest.skip(allow_module_level=True) / pytestmark）を列挙する。

    `allow_module_level=True` の有無は問わない（引数なしの module-level skip も逃げ道であり、
    kwarg を必須にすると fail-open になる）。代わりに **呼出元が pytest／unittest** であることを
    要求し、`sys.exit()` のような無関係な呼出しを誤検出しない。
    """
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                and _escape_call(node.value, origins, MODULE_LEVEL_CALLS):
            out.append("module-level skip")
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "pytestmark" \
                        and _is_skip_expr(node.value, origins):
                    out.append("pytestmark skip")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "pytestmark" and node.value is not None \
                and _is_skip_expr(node.value, origins):
            out.append("pytestmark skip")
    return out


def _is_assert_method(name: str) -> bool:
    """`assert_called_once` / `assertEqual` / `assert_frame_equal` 等の表明メソッド名か。"""
    return name == "assert" or name.startswith("assert_") or bool(re.match(r"assert[A-Z]", name))


def _verification_actions(fn: ast.FunctionDef | ast.AsyncFunctionDef,
                          origins: dict[str, str]) -> int:
    """検証行為の数を数える（実 assert・pytest.raises/warns・assert 系メソッド・pytest.fail）。

    PO 指示 §6 の禁止対象は「**空** assert」＝ 検証行為ゼロであって、`pytest.raises` を使う
    拒否テストではない。assert 文の有無だけで判定すると、拒否系 UT（S0.1 対象 118 本中 54 本）と
    mock の表明が丸ごと偽陽性になる。

    計上は**到達しうる文**に限る（入れ子関数内・`if False:` 配下の assert は数えない）。
    `assert_*` メソッドは呼出先が静的に解決できない（mock の動的属性）ため由来束縛を課しておらず、
    ここは着手後の coverage 下限 80% を backstop とする意図的なトレードオフ。
    """
    n = 0
    for sub in reachable_nodes(fn):
        if isinstance(sub, ast.Assert):
            if not (isinstance(sub.test, ast.Constant) and bool(sub.test.value)):
                n += 1
        elif isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Attribute) and _is_assert_method(f.attr):
                n += 1
            elif _escape_call(sub, origins, VERIFY_CALLS):
                n += 1
    return n


def _function_escapes(fn: ast.FunctionDef | ast.AsyncFunctionDef,
                      origins: dict[str, str]) -> list[str]:
    """関数単位の逃げ道（デコレータ skip/xfail・本体の skip/xfail/NotImplementedError・空 assert）。"""
    out: list[str] = []
    for deco in fn.decorator_list:
        if _is_skip_expr(deco, origins):
            out.append("skip")
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Call):
            name = _escape_call(sub, origins, SKIP_CALLS)
            if name:
                out.append(f"{name}()")
        if isinstance(sub, ast.Raise):
            exc = sub.exc
            name_or_none = None
            if isinstance(exc, ast.Name):
                name_or_none = exc.id
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name_or_none = exc.func.id
            elif isinstance(exc, ast.Attribute):
                name_or_none = exc.attr
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Attribute):
                name_or_none = exc.func.attr
            if name_or_none == "NotImplementedError":
                out.append("NotImplementedError")
    if _verification_actions(fn, origins) == 0:
        out.append("空 assert")
    return out


def detect_ut_escapes(ctx: Ctx, tests_dir: Path = TESTS_UNIT,
                      du_ids: list[str] | None = None,
                      nodeids: list[str] | None = None) -> list[str]:
    """S0.1 対象 UT に残る skip／xfail／NotImplementedError／空 assert を AST で列挙する。

    module-level skip・`pytestmark`・関数内 `pytest.xfail()`・`from pytest import skip` 経由の
    裸呼出し・定数 assert まで検出する（正規表現走査では素通りしていた）。
    逆に `pytest.raises` のみの拒否テストや mock の表明は検証行為として通す。

    `du_ids` を渡すとその DU の UT だけを、`nodeids` を渡すとその nodeid だけを対象にする
    （原子単位＝1 製品 PR 単位の強制 — PO 指示 §4）。両方渡した場合は積集合になる。
    """
    bad: list[str] = []
    cache: dict[str, tuple[ast.Module | None, dict[str, str], list[str]]] = {}
    scope = None if du_ids is None else set(du_ids)
    wanted = None if nodeids is None else {str(n).split("/")[-1] for n in nodeids}
    for du, fname, tname in s0_target_uts(ctx):
        if scope is not None and du not in scope:
            continue
        if wanted is not None and f"{fname}::{tname}" not in wanted:
            continue
        fp = tests_dir / fname
        if not fp.exists():
            bad.append(f"{du}:{fname}:ファイル不在")
            continue
        if fname not in cache:
            try:
                tree = ast.parse(fp.read_text(encoding="utf-8"))
                origins = _origins(tree)
                cache[fname] = (tree, origins, _module_level_escapes(tree, origins))
            except SyntaxError as e:
                cache[fname] = (None, {}, [f"構文エラー:{e}"])
        cached, origins, mod_escapes = cache[fname]
        for label in mod_escapes:
            bad.append(f"{du}:{fname}:{label}")
        if cached is None:
            continue
        fn = next((n for n in ast.walk(cached)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == tname), None)
        if fn is None:
            bad.append(f"{du}:{fname}::{tname}:def 不在")
            continue
        for label in _function_escapes(fn, origins):
            bad.append(f"{du}:{fname}::{tname}:{label}")
    return sorted(set(bad))


PLAN_STATUSES = ("planned", "in_progress", "done")
PRECONDITION_STATUSES = ("unmet", "met")
# 前提条件が「一語の申し送り」に退化するのを防ぐ最小記述量（何を満たせば met なのかが読める長さ）
PRECONDITION_MIN_DESC = 40
# met の根拠は機械が辿れる形（ゲート ID／commit SHA）に束縛する
MET_BY_GATE = re.compile(r"^G-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
MET_BY_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")


def ledger_gate_ids() -> set[str]:
    """**実際に emit されるゲート ID** の集合（完全一致照合用）。

    台帳散文からの抽出は使わない。台帳は `G-CNT-BR/REQ/FR` のような圧縮表記や廃止 ID の
    説明行を含むため、素朴な正規表現では実在しない ID を受理し（偽陰性）、実在する
    `G-BASE-HASH` 等を拒否する（偽陽性）。本番モジュールの `gate(...)` 呼出しが正本。
    """
    from tools.gates.baseline import script_gate_ids
    return script_gate_ids()


# PO が S0.1 開始条件として残した前提条件と、それを解消する**専用ゲート**の対応（PO 指示 §6）。
# baseline のラチェットだけだと「導入コミット内で消す」抜け道が残るため、必須集合をコードで持つ
# （独立レビュー R1-02）。met_by はここに書かれたゲート ID 以外を受け付けない（R1-01）。
REQUIRED_PRECONDITIONS = {
    "runtime-ut-outcome-gate": "G-UT-RUNTIME-OUTCOME",
    "dynamic-import-skip-detection": "G-UT-DYNAMIC-SKIP",
    "impl-start-detect-indirect-binding": "G-IMPL-START-BINDING",
    "per-ut-executed-and-passed": "G-UT-PER-TEST-OUTCOME",
}


def _precondition_faults(index: int, p: object) -> list[str]:
    """preconditions の 1 要素を検査する（非 dict でも例外にせず違反として返す）。"""
    if not isinstance(p, dict):
        return [f"preconditions[{index}] が object でない:{type(p).__name__}"]
    bad: list[str] = []
    pid = p.get("id")
    label = pid if isinstance(pid, str) and pid else f"preconditions[{index}]"
    if not isinstance(pid, str) or not pid:
        bad.append(f"{label}: id が非空文字列でない")
    if p.get("status") not in PRECONDITION_STATUSES:
        bad.append(f"{label}: status 語彙外:{p.get('status')}")
    desc = p.get("description")
    if not isinstance(desc, str) or len(desc.strip()) < PRECONDITION_MIN_DESC:
        bad.append(f"{label}: description が {PRECONDITION_MIN_DESC} 文字未満"
                   "（何を満たせば met なのかを書く）")
    if p.get("status") == "met":
        bad += _met_by_faults(label, pid if isinstance(pid, str) else "", p.get("met_by"))
    return bad


def _met_by_faults(label: str, pid: str, mb: object) -> list[str]:
    """`status=met` の根拠（met_by）が**その前提条件そのもの**へ束縛されているか検査する。

    汎用の「実在するゲート ID か実在する commit SHA」だけでは、無関係な既存ゲート
    （`G-BASE-HASH` 等）や任意の過去 commit を貼るだけで全条件を met に偽装できる
    （独立レビュー R1-01）。PO が残した前提条件は、**それを解消するために新設される
    専用ゲート**の ID でしか met にできない。
    """
    required = REQUIRED_PRECONDITIONS.get(pid)
    if required is not None:
        if mb != required:
            return [f"{label}: status=met には met_by={required}（この前提条件専用の新設ゲート）が必須"
                    f"だが {mb!r} — 無関係なゲート ID・commit SHA では met にできない"]
        if required not in ledger_gate_ids():
            return [f"{label}: met_by の {required} を本番ゲートが emit していない"
                    "（前提条件の解消はゲートの実装をもって行う）"]
        return []
    if not isinstance(mb, str) or not (MET_BY_GATE.match(mb) or MET_BY_COMMIT.match(mb)):
        return [f"{label}: status=met には met_by（ゲート ID または commit SHA）が必須:{mb!r}"]
    if MET_BY_GATE.match(mb):
        # 部分文字列一致だと実在 ID の接頭辞（G-BASE 等）が素通りするため、
        # 本番モジュールが emit する ID 集合への完全一致所属を要求する
        if mb not in ledger_gate_ids():
            return [f"{label}: met_by のゲート {mb} がゲート台帳に存在しない"]
    elif git("cat-file", "-e", f"{mb}^{{commit}}").returncode != 0:
        return [f"{label}: met_by の commit {mb} がリポジトリに存在しない"]
    return []


def detect_plan_faults(started: bool, plan_path: Path = S0_PLAN,
                       ctx: Ctx | None = None) -> list[str]:
    """S0.1 PLAN の妥当性と**着手前提条件の充足**を検査する。

    前提条件を散文の申し送りで持つと、必要になる瞬間（＝着手時）にちょうど忘れられる。
    `preconditions[].status` が `met` でない限り、`planned` 以外の全 status（in_progress・done）
    と着手の自動検出を fail-close で落とす（`planned → done` 直行による迂回も塞ぐ）。
    """
    bad: list[str] = []
    if not plan_path.exists():
        return ["S0.1 PLAN が存在しない（着手自動検出の入力が欠ける）"]
    plan = load(plan_path)
    status = plan.get("status")
    if status not in PLAN_STATUSES:
        bad.append(f"status 語彙外:{status}")
    want = {f"DU-{i:02d}" for i in range(1, S0_DU_MAX + 1)}
    if set(plan.get("targets", [])) != want:
        bad.append(f"targets が DU-01〜{S0_DU_MAX:02d} と不一致")
    pres = plan.get("preconditions")
    if not isinstance(pres, list) or not pres:
        bad.append("preconditions が未定義（着手前提条件を散文に置かない）")
        return bad
    for i, p in enumerate(pres):
        bad += _precondition_faults(i, p)
    # 必須の前提条件を「導入したコミット内で消す」抜け道を塞ぐ（baseline ラチェットの前段）
    have = {p.get("id") for p in pres if isinstance(p, dict)}
    missing = sorted(set(REQUIRED_PRECONDITIONS) - have)
    if missing:
        bad.append(f"PO 指定の S0.1 開始条件が欠落:{missing}")
    unmet = [p.get("id") for p in pres
             if isinstance(p, dict) and p.get("status") != "met"]
    # `planned` 以外は「着手済み」とみなす（done への直行も前提条件検査の対象）
    if unmet and (started or status != "planned"):
        bad.append(f"未充足の前提条件があるまま着手（status={status}）:{unmet}")
    if status == "done":
        bad += _done_completion_faults(plan, ctx)
    return bad


def _done_completion_faults(plan: dict, ctx: Ctx | None) -> list[str]:
    """`done` を名乗るための完了条件（対象 DU の API が実装済み）を検査する。

    実装ゼロのまま `done` を書いて S0.1 完了を宣言できないようにする（独立レビュー R4-01）。
    """
    if ctx is None:
        return []
    implemented = {s.split(":")[0] for s in detect_du_api_implementations(ctx)}
    missing = sorted(set(plan.get("targets", [])) - implemented)
    return [f"status=done だが API 未実装の対象がある:{missing[:5]}"] if missing else []


def coverage_floor(ctx: Ctx) -> int:
    """有効な coverage 下限（着手後は 80 以上・低下禁止のラチェット）。"""
    cfg = load(COVERAGE_FLOOR)
    declared = int(cfg["fail_under"])
    return max(declared, COVERAGE_STARTED_FLOOR) if detect_impl_started(ctx) else declared


def committed_coverage_floor() -> tuple[int | None, str]:
    """親コミットに記録された coverage 下限を `(値, 出所)` で返す。

    比較元の解決は baseline 経由に一本化する（`committed_baseline()` が旧パス遡及と
    fail-close を担う）。作業ツリーの同時改変では回避できない。
    親が解決できたが `coverage_floor` キーが無い場合は「まだ保護すべき値が無い」ため
    値なしで正常扱い。親そのものが解決できない場合は理由を返し、呼び出し側が落とす。
    """
    prev, source = committed_baseline()
    if prev is None:
        return None, source
    if "coverage_floor" not in prev:
        return None, f"{source}: coverage_floor キーなし"
    try:
        return int(prev["coverage_floor"]), source
    except (TypeError, ValueError):
        return None, f"{source}: coverage_floor が数値でない"


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _pairs(ctx)
    _test_files(ctx)
    _impl_start(ctx)


def _pairs(ctx: Ctx) -> None:
    vd = VERIFICATION_DESIGN.read_text(encoding="utf-8")
    nopair: list[str] = []
    for p in PAIRED_L3_DOCS:
        head = p.read_text(encoding="utf-8")[:800]
        if "pair:" not in head or "verification-design" not in head:
            nopair.append(f"{p.name}:①側 pair 行なし")
        if p.name not in vd:
            nopair.append(f"{p.name}:③側の対象列挙なし")
    gate("G-PAIR-HDR", not nopair, f"①↔③ 対称参照 (欠落={nopair})")

    by_id = {it["artifact_id"]: it for it in ctx.manifest_items}
    expected = [
        ("L4-BASIC-DESIGN", "L4-INTEGRATION-TEST-DESIGN", BASIC_DESIGN, INTEGRATION_TEST_DESIGN,
         "integration-test-design", "basic-design"),
        ("L5-DETAILED-DESIGN", "L5-UNIT-TEST-DESIGN", DETAILED_DESIGN, UNIT_TEST_DESIGN,
         "unit-test-design", "detailed-design"),
    ]
    bad: list[str] = []
    for a_id, b_id, a_doc, b_doc, a_needle, b_needle in expected:
        a, b = by_id.get(a_id), by_id.get(b_id)
        if a is None or b is None:
            bad.append(f"manifest 未登録:{a_id}/{b_id}")
            continue
        if a.get("pair_artifact_id") != b_id or b.get("pair_artifact_id") != a_id:
            bad.append(f"manifest pair 非対称:{a_id}↔{b_id}")
        ah = a_doc.read_text(encoding="utf-8")[:800]
        bh = b_doc.read_text(encoding="utf-8")[:800]
        if "pair:" not in ah or a_needle not in ah:
            bad.append(f"{a_doc.name}:pair ヘッダ欠落")
        if "pair:" not in bh or b_needle not in bh:
            bad.append(f"{b_doc.name}:pair ヘッダ欠落")
    gate("G-PAIR-MANIFEST", not bad,
         f"②↔④・⑤↔⑥ のペアが manifest（pair_artifact_id）と文書ヘッダの両方で双方向 (欠陥={bad})")


def _test_files(ctx: Ctx) -> None:
    du2files: dict[str, set[str]] = {}
    for d in ctx.duc:
        for a in d["apis"]:
            for ref in ut_nodeids(a):
                if "::" in ref:
                    du2files.setdefault(d["id"], set()).add(ref.split("::", 1)[0])
    multi = sorted(f"{du}:{sorted(fs)}" for du, fs in du2files.items() if len(fs) != 1)
    files = [next(iter(fs)) for fs in du2files.values() if len(fs) == 1]
    shared = sorted({f for f in files if files.count(f) > 1})
    gate("G-UT-FILE-UNIQ", not multi and not shared,
         f"DU↔テストファイルが 1 対 1・衝突なし (複数={multi[:3]}, 共有={shared[:3]})")

    declared = {f for fs in du2files.values() for f in fs}
    stc_files = {it["test_file"] for it in ctx.stc["items"]
                 if it.get("kind") == "impl" and it.get("update") == "S0.1" and it.get("test_file")}
    missing = sorted({f for f in declared if not (TESTS_UNIT / f).exists()})
    missing += sorted({f for f in stc_files if not (ROOT / f).exists()})
    gate("G-UT-FILE-EXIST", not missing,
         f"du-contracts／STC-I（S0.1）が宣言する test_file が実在 (欠落={missing[:5]})")


def _impl_start(ctx: Ctx) -> None:
    auto = impl_start_signals(ctx)
    declared = bool(ctx.skip_budget.get("s0_impl_started"))
    gate("G-IMPL-START-DETECT", not (auto and not declared),
         "S0.1 着手の自動検出（src/helix の実装ファイル・S0.1 PLAN in_progress・DU-01〜12 API 実装・"
         "原子単位の in_progress／done 宣言）と "
         f"tests/skip-budget.json の宣言が一致（自動検出のみで着手扱い） (自動={auto}, 宣言={declared})")

    started = detect_impl_started(ctx)
    # 強制範囲は着手済み Workset の DU に限る（未着手 Workset のスタブは猶予 — PO 指示 §4）。
    # Workset 正本が壊れている場合は enforced_du_ids が S0.1 全 DU へ倒す（fail-close）。
    from tools.gates import atomic_units as au
    from tools.gates.worksets import enforced_du_ids
    scoped_dus = enforced_du_ids(ctx)
    # 原子単位正本が使えるなら nodeid 単位まで絞る。使えなければ Workset（さらに壊れていれば
    # S0.1 全 DU）へ倒す。範囲を**広げる**方向にしか倒さないのが fail-close の要点である。
    scoped_nodeids = au.enforced_nodeids(ctx)
    escapes = detect_ut_escapes(ctx, du_ids=scoped_dus, nodeids=scoped_nodeids) \
        if scoped_dus else []
    gate("G-UT-NO-ESCAPE", not escapes,
         "着手済み原子単位の対象 UT に skip／xfail／NotImplementedError／空 assert を残せない"
         f"（未着手は猶予） (着手={started}, 強制 DU={len(scoped_dus)} 件, "
         f"強制 UT={'全 DU 分' if scoped_nodeids is None else len(scoped_nodeids)}, "
         f"違反={escapes[:5]})")

    cfg = load(COVERAGE_FLOOR)
    declared_floor = int(cfg["fail_under"])
    required = COVERAGE_STARTED_FLOOR if started else 0
    prev, cov_source = committed_coverage_floor()
    lowered = prev is not None and declared_floor < prev
    # 親そのものを解決できない場合は fail-close（黙って None を返して素通りさせない）
    unresolved = prev is None and "キーなし" not in cov_source and "初回コミット" not in cov_source
    gate("G-COVERAGE-RATCHET", declared_floor >= required and not lowered and not unresolved,
         f"coverage 下限は着手後 {COVERAGE_STARTED_FLOOR}% 以上・以後低下禁止 "
         f"(宣言={declared_floor}, 必要={required}, 親コミット={prev}／{cov_source})")

    plan_bad = detect_plan_faults(started, ctx=ctx)
    gate("G-PLAN-S0", not plan_bad,
         f"S0.1 PLAN が実在し status 語彙・対象 DU（01〜{S0_DU_MAX:02d}）・着手前提条件が正しい "
         f"(違反={plan_bad})")

    budget = ctx.skip_budget
    gate("G-S0-TEST-REALITY", not (started and budget.get("max_skipped", 0) > 0 and escapes),
         "S0.1 着手後は skip を red と称せない（G-UT-NO-ESCAPE と連動して実 red→green を要求） "
         f"(着手={started}, skip 上限={budget.get('max_skipped')})")
