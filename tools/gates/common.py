"""ゲート共通基盤: パス正本・結果レジストリ・最小 JSON Schema 検証器・遅延ロード context。

分割方針（PO 指示 §7）: 巨大 validator を工程別モジュールへ割り、`run_all` が順に呼ぶ。
各モジュールは `gate()` で結果を登録するだけで、終了コード判定は `run_all` が行う。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- 階層パス正本
AUTHORITY = ROOT / "docs/00-authority"
MANIFEST = AUTHORITY / "artifact-manifest.json"
MANIFEST_SCHEMA = AUTHORITY / "artifact-manifest.schema.json"
APPROVALS = AUTHORITY / "approvals/approvals.md"
BASELINE = AUTHORITY / "baselines/baseline.json"
REVIEWS = AUTHORITY / "reviews"
GATE_LEDGER = AUTHORITY / "requirements-gates.md"
SUPERSEDED = AUTHORITY / "superseded"
ARCHIVE = ROOT / "docs/archive"

L0 = ROOT / "docs/L0-charter"
L1 = ROOT / "docs/L1-business-requirements"
L2 = ROOT / "docs/L2-prototypes"
L3 = ROOT / "docs/L3-system-requirements"
L4 = ROOT / "docs/L4-basic-design"
L5 = ROOT / "docs/L5-detailed-design"
L6 = ROOT / "docs/L6-feature-design"

LAYER_DIRS = [AUTHORITY, L0, L1, L2, L3, L4, L5, L6, ARCHIVE]

# 実装入力（契約正本 9 本 — PO 指示 §3・構造的意味トレース是正 §1）
BR_CONTRACTS = L1 / "canonical/br/br-contracts.json"
FR_CONTRACTS = L3 / "canonical/functional/fr-contracts.json"
SR_CONTRACTS = L3 / "canonical/strategy/sr-contracts.json"
NFR_CONTRACTS = L3 / "canonical/nonfunctional/nfr-contracts.json"
AC_CONTRACTS = L3 / "canonical/acceptance/ac-contracts.json"
TC_CONTRACTS = L3 / "verification/tc-contracts.json"
CMP_CONTRACTS = L4 / "canonical/components/cmp-contracts.json"
DU_CONTRACTS = L5 / "canonical/apis/du-contracts.json"
# 第 9 正本: L6 責務／API／契約節／AC／TC／UT の接続台帳（手編集の confirmed 正本）
IMPL_UNITS_CONTRACTS = L6 / "S0/implementation-units.json"
CANON_CONTRACTS = [BR_CONTRACTS, FR_CONTRACTS, SR_CONTRACTS, NFR_CONTRACTS,
                   AC_CONTRACTS, TC_CONTRACTS, CMP_CONTRACTS, DU_CONTRACTS,
                   IMPL_UNITS_CONTRACTS]

# 台帳・schema
BR_LEDGER = L1 / "canonical/br/br.json"
BR_SCHEMA = L1 / "canonical/br/br-contract.schema.json"
REQ_LEDGER = L1 / "canonical/req/req.json"
BR_MEDIA_DIR = L1 / "canonical/br-media"
LTW_DIR = L1 / "canonical/ltw"
REQUIREMENTS_LEDGER = L3 / "canonical/functional/requirements.json"
FN_LEDGER = L3 / "canonical/functional/fn.json"
FR_SCHEMA = L3 / "canonical/functional/fr-contract.schema.json"
MR_DIR = L3 / "canonical/functional/mr"
NFR_SCHEMA = L3 / "canonical/nonfunctional/nfr-contract.schema.json"
AC_SCHEMA = L3 / "canonical/acceptance/ac-contract.schema.json"
TC_SCHEMA = L3 / "verification/tc-contract.schema.json"
STRATEGY_DIR = L3 / "canonical/strategy"
STRATEGY_SCHEMA_DIR = L3 / "canonical/schemas/strategy"
S0_DIR = L3 / "canonical/schemas/s0"
DDL = S0_DIR / "ddl.sql"
TRANSITIONS = S0_DIR / "transitions.json"
EVIDENCE_KINDS = S0_DIR / "evidence-kinds.json"
TRACE = S0_DIR / "trace.json"
UPDATES = S0_DIR / "updates.json"
WF_CONTRACTS = L3 / "canonical/workflows/wf-contracts.json"
ENVIRONMENT = S0_DIR / "environment.json"
MIGRATION_RULES = L5 / "canonical/migrations/migration-rules.json"
FIXTURES = L3 / "verification/fixtures"
CMP_LEDGER = L4 / "canonical/components/components.json"
SCM_LEDGER = L4 / "canonical/components/strategy-components.json"
CMP_SCHEMA = L4 / "canonical/components/cmp-contract.schema.json"
ITC_LEDGER = L4 / "integration-tests/itest.json"
STC_LEDGER = L4 / "integration-tests/strategy-tests.json"
DU_LEDGER = L5 / "canonical/modules/detailed.json"
DU_SCHEMA = L5 / "canonical/apis/du-contract.schema.json"
ERROR_TAXONOMY = L5 / "canonical/errors/error-taxonomy_v0.1.md"

# 文書正本
CHARTER = L0 / "canonical/marketing-harness-charter_v0.4.md"
S0_CONTRACT = L3 / "canonical/s0-contract_v0.1.md"
VERIFICATION_DESIGN = L3 / "verification/verification-design_v0.1.md"
BASIC_DESIGN = L4 / "canonical/basic-design_v0.1.md"
INTEGRATION_TEST_DESIGN = L4 / "integration-tests/integration-test-design_v0.1.md"
DETAILED_DESIGN = L5 / "canonical/detailed-design_v0.1.md"
UNIT_TEST_DESIGN = L5 / "unit-tests/unit-test-design_v0.1.md"
STRATEGY_REQ = L3 / "canonical/strategy/strategy-loop-requirements_v0.1.md"
STRATEGY_LEARNING = L3 / "canonical/strategy/strategy-learning-contract_v0.1.md"
STRATEGY_DESIGN = L4 / "canonical/components/strategy-loop-design_v0.1.md"
STRATEGY_TEST_DESIGN = L4 / "integration-tests/strategy-loop-test-design_v0.1.md"
REQUIREMENTS_DOC = L3 / "canonical/functional/requirements_v0.1.md"

TESTS_UNIT = ROOT / "tests/unit"
SKIP_BUDGET = ROOT / "tests/skip-budget.json"
COVERAGE_FLOOR = ROOT / "tests/coverage-floor.json"
GATE_PKG = ROOT / "tools/gates"
GATE_MODULES = ["authority", "requirements", "traceability", "architecture", "detailed_design",
                "test_pairing", "semantic_refs", "review_binding", "baseline", "run_all"]

# 旧体系（archive — 実装入力にしない）
LEGACY_ARCHIVED = {
    "ac.json": ARCHIVE / "pre-structure-migration-2026-08-01/ac.json",
    "verification.json": ARCHIVE / "pre-structure-migration-2026-08-01/verification.json",
    "utest.json": ARCHIVE / "pre-structure-migration-2026-08-01/utest.json",
}

# S0.1 の対象詳細設計単位（DU-01〜12）。スライス判定の共有定数
S0_DU_MAX = 12

# 現行分母（PO 指示 §3 — 旧 AC19／TC59／UTC69 は historical_counts のみ）
HISTORICAL_COUNTS = {"AC_LEGACY": 19, "AC_DEFERRED_LEGACY": 17, "TC_LEGACY": 59, "UTC_LEGACY": 69}


# ---------------------------------------------------------------- レジストリ
_results: list[tuple[str, bool, str]] = []


def gate(gate_id: str, cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"{status} [{gate_id}] {msg}")
    _results.append((gate_id, bool(cond), msg))


def failures() -> list[str]:
    return [f"{g}: {m}" for g, ok, m in _results if not ok]


def results() -> list[tuple[str, bool, str]]:
    return list(_results)


def reset() -> None:
    _results.clear()


# ---------------------------------------------------------------- ユーティリティ
def load(p: Path) -> Any:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------- API 契約節アクセサ
# du-contracts の pre/post/raises・ut は **構造化**（clause_id / nodeid）である。
# 文字列としての読み出しはここに集約し、各ゲートが形を仮定しないようにする。
def api_name(api: dict) -> str:
    m = re.match(r"def (\w+)", api["signature"])
    return m.group(1) if m else ""


def ut_nodeids(api: dict) -> list[str]:
    return [u["nodeid"] for u in api.get("ut", [])]


def api_clauses(api: dict) -> list[dict]:
    """API の全契約節（pre／post／raises）を宣言順に返す。"""
    return [*api.get("precondition", []), *api.get("postcondition", []), *api.get("raises", [])]


def clause_text(clause: dict) -> str:
    return clause.get("text") or f"{clause.get('type', '')} {clause.get('when', '')}"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha12(p: Path) -> str:
    return sha256_file(p)[:12]


def canonical_json_digest(data: dict, exclude: str = "approval_digest") -> str:
    """契約 JSON の内容 digest（approval_digest 列を除いた正準化 JSON の sha256[:12]）。"""
    body = json.dumps({k: v for k, v in data.items() if k != exclude},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- frontmatter
# 終端 `---` の直後の空行 1 行までを frontmatter の一部として食う
# （本文 digest が frontmatter の書式差で動かないようにするため）
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n\n?", re.S)


def parse_frontmatter(block: str) -> dict[str, Any]:
    """`key: value` と `key: [a, b]` だけを解する最小 YAML パーサ（外部依存なし）。

    権威メタデータ（artifact_id・lifecycle_status・slice・traces）はこの平坦形で書く。
    入れ子を許すと「どこが正本か」が曖昧になるため、意図的に平坦形しか受け付けない。
    """
    out: dict[str, Any] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line or line.startswith((" ", "\t")):
            out.setdefault("__malformed__", []).append(line)
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            out[key.strip()] = [x.strip() for x in inner.split(",") if x.strip()]
        else:
            out[key.strip()] = val
    return out


def split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """先頭 YAML frontmatter と本文を分離する（無ければ `(None, 全文)`）。"""
    m = FRONTMATTER.match(text)
    if not m:
        return None, text
    return parse_frontmatter(m.group(1)), text[m.end():]


def frontmatter_of(p: Path) -> dict[str, Any] | None:
    return split_frontmatter(p.read_text(encoding="utf-8"))[0]


def doc_body_digest(p: Path) -> str:
    """承認・digest 束縛の対象となる内容の digest（**frontmatter を含む全文**）。

    frontmatter には `slice`／`traces`／`forward_refs` のように**ゲートが正本として読む**
    意味情報が入る。これを digest から外すと「承認された trace」を承認束縛の外で
    書き換えられるため、承認対象は常に全文とする（独立レビュー F-03）。
    """
    return sha12(p)


def md_count(path: Path, pattern: str) -> int:
    return len(set(re.findall(pattern, path.read_text(encoding="utf-8"))))


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True,  # noqa: S603, S607
                          check=False, cwd=ROOT)


def git_bytes(*args: str) -> subprocess.CompletedProcess:
    """バイト列のまま取得する（digest 計算は再エンコードを挟まない）。"""
    return subprocess.run(["git", *args], capture_output=True,  # noqa: S603, S607
                          check=False, cwd=ROOT)


def live_markdown() -> list[Path]:
    """現役階層（archive・superseded を除く）の Markdown 一覧。"""
    out = []
    for p in sorted(ROOT.glob("docs/**/*.md")):
        if is_frozen(p):
            continue
        out.append(p)
    return out


def is_frozen(p: Path) -> bool:
    """archive／superseded 配下 = 凍結（実装入力・現役導線にできない）。"""
    rel = str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
    return rel.startswith("docs/archive/") or rel.startswith("docs/00-authority/superseded/")


NESTED_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
TERMINATORS = (ast.Return, ast.Raise, ast.Continue, ast.Break)
STMT_LIST_FIELDS = ("body", "orelse", "finalbody")


def live_statements(stmts: list) -> list:
    """文の並びから、`return`／`raise`／`continue`／`break` 以降の死コードを落とす。"""
    out = []
    for s in stmts:
        out.append(s)
        if isinstance(s, TERMINATORS):
            break
    return out


def _reachable_children(node: ast.AST) -> list:
    """定数条件の分岐・ループは到達する側だけを、文の並びは死コードを除いて返す。"""
    if isinstance(node, ast.If) and isinstance(node.test, ast.Constant):
        return [node.test, *live_statements(node.body if node.test.value else node.orelse)]
    if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and not node.test.value:
        return [node.test, *live_statements(node.orelse)]  # while False: 本体は実行されない
    out: list = []
    for name, value in ast.iter_fields(node):
        if isinstance(value, list):
            items = [v for v in value if isinstance(v, ast.AST)]
            if name in STMT_LIST_FIELDS and items and isinstance(items[0], ast.stmt):
                items = live_statements(items)
            out.extend(items)
        elif isinstance(value, ast.AST):
            out.append(value)
    return out


def reachable_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """到達しうるノードのみを走査する（入れ子定義・定数偽の分岐／ループ・死コードを刈る）。

    `ast.walk` は入れ子関数の中身も `if False:` 配下も `return` 後も数えてしまうため、
    **検証行為の計上**には使えない（実行されないコードで「空 assert」を回避できてしまう）。
    逃げ道の検出側は fail-close を優先して `ast.walk`（全走査）のままにする。
    """
    stack: list[tuple[ast.AST, bool]] = [(node, True)]
    while stack:
        cur, is_root = stack.pop()
        yield cur
        if not is_root and isinstance(cur, NESTED_DEFS):
            continue  # 入れ子定義は「この関数が実行する処理」ではない
        stack.extend((child, False) for child in _reachable_children(cur))


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# ---------------------------------------------------------------- schema 検証器
TMAP: dict[str, Any] = {"string": str, "integer": int, "number": (int, float), "array": list,
                        "object": dict, "null": type(None), "boolean": bool}


def schema_check(schema: dict, doc: Any, path: str = "$") -> list[str]:
    """最小 JSON Schema 検証器（外部依存なし）。"""
    errs: list[str] = []
    if schema.get("type") == "object" or "properties" in schema or "required" in schema:
        if not isinstance(doc, dict):
            return [f"{path}: object でない"]
        errs += [f"{path}.{k}: 必須欠落" for k in schema.get("required", []) if k not in doc]
        if schema.get("additionalProperties") is False:
            errs += [f"{path}.{k}: 未定義フィールド" for k in doc if k not in schema.get("properties", {})]
        for k, sub in schema.get("properties", {}).items():
            if k in doc:
                errs += schema_check(sub, doc[k], f"{path}.{k}")
        return errs
    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    if types and not any(isinstance(doc, TMAP[x]) for x in types):
        errs.append(f"{path}: 型不一致 {types}")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: enum 外 ({doc})")
    if isinstance(doc, str):
        if len(doc) < schema.get("minLength", 0):
            errs.append(f"{path}: minLength")
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            errs.append(f"{path}: pattern")
    if isinstance(doc, list):
        if len(doc) < schema.get("minItems", 0):
            errs.append(f"{path}: minItems")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in doc]
            if len(seen) != len(set(seen)):
                errs.append(f"{path}: uniqueItems 違反")
        if "items" in schema:
            for i, item in enumerate(doc):
                errs += schema_check(schema["items"], item, f"{path}[{i}]")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            errs.append(f"{path}: minimum")
        if "maximum" in schema and doc > schema["maximum"]:
            errs.append(f"{path}: maximum")
    return errs


# ---------------------------------------------------------------- context
@dataclass
class Ctx:
    """正本の遅延ロード。全ゲートモジュールが同一インスタンスを共有する。"""

    _cache: dict = field(default_factory=dict)

    @cached_property
    def ddl(self) -> str:
        return DDL.read_text(encoding="utf-8")

    @cached_property
    def approvals(self) -> str:
        return APPROVALS.read_text(encoding="utf-8")

    @cached_property
    def br(self) -> list[dict]:
        return load(BR_LEDGER)["items"]

    @cached_property
    def req(self) -> list[dict]:
        return load(REQ_LEDGER)["items"]

    @cached_property
    def requirements(self) -> list[dict]:
        return load(REQUIREMENTS_LEDGER)["items"]

    @cached_property
    def fr(self) -> list[dict]:
        return [i for i in self.requirements if i["kind"] == "FR"]

    @cached_property
    def nfr(self) -> list[dict]:
        return [i for i in self.requirements if i["kind"] == "NFR"]

    @cached_property
    def fn(self) -> list[dict]:
        return load(FN_LEDGER)["items"]

    @cached_property
    def s0_fn(self) -> set[str]:
        return {i["id"] for i in self.fn if str(i.get("slice")) == "S0"}

    @cached_property
    def brc(self) -> list[dict]:
        return load(BR_CONTRACTS)["items"]

    @cached_property
    def frc(self) -> list[dict]:
        return load(FR_CONTRACTS)["items"]

    @cached_property
    def src(self) -> list[dict]:
        return load(SR_CONTRACTS)["items"]

    @cached_property
    def allc(self) -> list[dict]:
        return self.frc + self.src

    @cached_property
    def acc(self) -> list[dict]:
        return load(AC_CONTRACTS)["items"]

    @cached_property
    def nfc(self) -> list[dict]:
        return load(NFR_CONTRACTS)["items"]

    @cached_property
    def tcc(self) -> list[dict]:
        return load(TC_CONTRACTS)["items"]

    @cached_property
    def cmpc(self) -> list[dict]:
        return load(CMP_CONTRACTS)["items"]

    @cached_property
    def duc(self) -> list[dict]:
        return load(DU_CONTRACTS)["items"]

    @cached_property
    def comps(self) -> list[dict]:
        return load(CMP_LEDGER)["items"]

    @cached_property
    def scm(self) -> list[dict]:
        return load(SCM_LEDGER)["items"]

    @cached_property
    def itcs(self) -> list[dict]:
        return load(ITC_LEDGER)["items"]

    @cached_property
    def stc(self) -> dict:
        return load(STC_LEDGER)

    @cached_property
    def dus(self) -> list[dict]:
        return load(DU_LEDGER)["items"]

    @cached_property
    def sr(self) -> list[dict]:
        return load(STRATEGY_DIR / "sr.json")["items"]

    @cached_property
    def transitions(self) -> list[dict]:
        return load(TRANSITIONS)["items"]

    @cached_property
    def ddl_tables(self) -> set[str]:
        return set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", self.ddl))

    @cached_property
    def ddl_columns(self) -> dict[str, set[str]]:
        tbl: dict[str, set[str]] = {}
        for m in re.finditer(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\);", self.ddl, re.S):
            tbl[m.group(1)] = set(re.findall(r"^\s{2}(\w+)\s+[A-Z]", m.group(2), re.M))
        return tbl

    @cached_property
    def trn_states(self) -> dict[str, set[str]]:
        st: dict[str, set[str]] = {}
        for t in self.transitions:
            st.setdefault(t["entity"], set()).update({t["from"], t["to"]})
        return st

    @cached_property
    def manifest(self) -> dict:
        return load(MANIFEST)

    @cached_property
    def manifest_items(self) -> list[dict]:
        return self.manifest["items"]

    @cached_property
    def impl_started(self) -> bool:
        from tools.gates.test_pairing import detect_impl_started
        return detect_impl_started(self)

    @cached_property
    def skip_budget(self) -> dict:
        return load(SKIP_BUDGET)


CTX = Ctx()
