"""実行時テスト実体ゲート: pytest outcome の取り込み・動的 skip の検出・間接束縛による着手検出・
対象 UT の nodeid 単位 executed+passed 突合（S0.1 着手前提条件 4 件 — PO 指示 §6）。

AST 検査（`test_pairing.detect_ut_escapes`）は「書かれているか」しか見られない。
`__import__`／`importlib` で組み立てた skip、実行時条件による skip、収集からの除外は
静的検査を素通りする。本モジュールは `scripts/collect_test_outcome.py` が正規化した
**実行結果**（`reports/test-outcome.json`）を入力にして、静的検査の穴を実測で塞ぐ。

fail-close の方針:

- レポートが**存在する**なら、常に schema・HEAD 束縛・source digest を検査する（偽の成果物を拒否）
- S0.1 着手後はレポートの**存在自体**を必須にする（レポートを消せば検査を消せる、を塞ぐ）
- 未着手のうちは skip の存在を違反にしない（test-first の stub は正当）。ただし実測値は
  ゲートのメッセージに出し、着手と同時に何件が赤化するかを常に見えるようにする
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import shlex
from pathlib import Path
from typing import Any

from tools.gates.common import (
    ROOT,
    S0_DU_MAX,
    Ctx,
    api_name,
    gate,
    git,
    rel,
    ut_nodeids,
)

REPORTS_DIR = ROOT / "reports"
OUTCOME_REPORT = REPORTS_DIR / "test-outcome.json"
JUNIT_XML = REPORTS_DIR / "junit.xml"
COLLECTOR = ROOT / "scripts/collect_test_outcome.py"
SRC_PKG = ROOT / "src/helix"
TESTS_UNIT_REL = "tests/unit"

OUTCOME_SCHEMA = "helix.test-outcome/v1"
OUTCOME_VALUES = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
# 「実行されなかった」と等価に扱う outcome（passed 以外はすべて対象 UT の green を主張できない）
NOT_EXECUTED = ("skipped",)
NOT_PASSED = ("failed", "error", "skipped", "xfailed", "xpassed")

# CI 配線（両ワークフローが outcome を生成してからゲートを走らせること）。
# 「同一 job の中で pytest --junitxml → 収集 → ゲート」の**順序**まで構造で検査する。
CI_WORKFLOWS = (".github/workflows/python-ci.yml", ".github/workflows/docs-ci.yml")
CI_STEP_ORDER = ("--junitxml", "scripts/collect_test_outcome.py", "tools/gates/run_all.py")
# コマンドの**実行主体**として認める先頭語（`false ... --junitxml ...` のような偽装を弾く）
RUNNERS = ("python", "python3", "uv", "poetry", "pipx")
# 実行ではなく「別のことをする」フラグ（これが挟まれば実行形と認めない）
NON_EXEC_FLAGS = ("-c", "-h", "--help", "--version", "--dry-run")
# 語を書くだけ／必ず失敗させるだけのコマンド（配線とみなさない）
#（`tee` は出力を写すだけで junit を作り替えないため、配線でも介在でもない）
NOOP_HEADS = ("echo", ":", "true", "printf", "cat", "ls", "tee")
GUARD_HEADS = ("false", "exit", "test", "[")
# ランナの前置語として素通りさせてよいトークン（これ以外のフラグが挟まれば実行形と認めない）
RUNNER_PREFIXES = ("run", "exec", "-m")
UPLOAD_WORKFLOW = ".github/workflows/python-ci.yml"
PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------- outcome レポート
def load_outcome(path: Path = OUTCOME_REPORT) -> dict | None:
    """outcome レポートを読む（存在しない・壊れている場合は None）。"""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _collector() -> Any:
    """収集スクリプトをモジュールとして読み込む（再導出照合に使う）。"""
    spec = importlib.util.spec_from_file_location("helix_collect_test_outcome", COLLECTOR)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rederivation_faults(data: dict, junit: Path) -> list[str]:
    """レポートが **junit xml から機械的に再導出できる**ことを確かめる（手書き JSON を拒否）。

    `generated_by` や `commit` は既知の文字列なので、それだけを見ていれば
    「対象 UT を passed にした JSON」を手で書けてしまう（独立レビュー R1-01）。
    そこで収集スクリプトを同じ入力で走らせ、nodeid→outcome の写像が完全一致することを要求する。
    junit xml 自体は git 追跡下に置かず（`reports/` は .gitignore）CI が同一ジョブで生成するため、
    偽造には「ジョブ内で pytest の実出力を差し替える」ことが必要になる。
    """
    mod = _collector()
    if mod is None:
        return ["収集スクリプトを読み込めない（再導出照合ができない）"]
    try:
        expected = mod.collect(junit)
    except Exception as e:  # noqa: BLE001 — 壊れた junit は fail-close
        return [f"junit xml から再導出できない:{type(e).__name__}:{e}"]
    got = {str(t.get("nodeid")): str(t.get("outcome")) for t in data.get("tests") or []
           if isinstance(t, dict)}
    want = {str(t["nodeid"]): str(t["outcome"]) for t in expected["tests"]}
    if got != want:
        only_report = sorted(set(got) - set(want))[:3]
        differs = sorted(n for n in set(got) & set(want) if got[n] != want[n])[:3]
        return [f"tests が junit xml の再導出と不一致（レポート固有={only_report}, "
                f"outcome 相違={differs}） — 手書き・改変されたレポートは使わない"]
    if data.get("totals") != expected["totals"]:
        return ["totals が junit xml の再導出と不一致"]
    return []


def tracked_reports_faults() -> list[str]:
    """`reports/` が git 追跡下でないことを**レポートの有無に関係なく**検査する。

    追跡下に置ければ「実行済みの証跡」を固定化して毎ジョブの実測を迂回できる
    （独立レビュー R2-03 — レポート不在で早期 return していた穴）。
    """
    tracked = {ln for ln in git("ls-files", "reports").stdout.splitlines() if ln}
    return [f"reports/ が git 追跡下にある（成果物は毎ジョブ生成する）:{sorted(tracked)[:3]}"] \
        if tracked else []


def report_faults(path: Path = OUTCOME_REPORT) -> list[str]:
    """レポートの構造・HEAD 束縛・生成元・**junit からの再導出一致**を検査する。

    別コミットで作った古い成果物や手書きの JSON で「対象 UT は passed だった」と
    主張できないようにする。判定に使う前段の検査であり、ここが赤なら outcome は使わない。
    レポートが存在しない場合は空（存在の要否は着手状態が決める）。
    """
    bad: list[str] = tracked_reports_faults()
    if not path.is_file():
        return bad
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return [*bad, f"{rel(path)}: JSON として読めない:{e}"]
    if not isinstance(data, dict):
        return [*bad, f"{rel(path)}: object でない"]
    if data.get("schema") != OUTCOME_SCHEMA:
        bad.append(f"schema が {OUTCOME_SCHEMA} でない:{data.get('schema')!r}")
    if data.get("generated_by") != "scripts/collect_test_outcome.py":
        bad.append(f"generated_by が収集スクリプトでない:{data.get('generated_by')!r}")
    head = git("rev-parse", "HEAD").stdout.strip()
    if head and data.get("commit") != head:
        bad.append(f"commit が HEAD({head[:8]}) へ束縛されていない:{str(data.get('commit'))[:8]!r}"
                   " — 別コミットの outcome を実行結果として使わせない")
    # 生成元 junit は「リポジトリ相対の固定パス」しか認めない（任意パスの持ち込みを塞ぐ）
    src = data.get("source")
    junit_rel = str(JUNIT_XML.relative_to(ROOT))
    if src != junit_rel:
        bad.append(f"source が {junit_rel} でない:{src!r}")
    elif not JUNIT_XML.is_file():
        bad.append(f"{junit_rel} が実在しない（レポートだけを残して生成元を消せない）")
    else:
        digest = hashlib.sha256(JUNIT_XML.read_bytes()).hexdigest()
        if data.get("source_digest") != digest:
            bad.append(f"source_digest が {junit_rel} の実体と不一致（改竄または再生成漏れ）")
        else:
            bad += _rederivation_faults(data, JUNIT_XML)
    tests = data.get("tests")
    if not isinstance(tests, list):
        bad.append("tests が配列でない")
        return bad
    seen: set[str] = set()
    for i, t in enumerate(tests):
        if not isinstance(t, dict):
            bad.append(f"tests[{i}] が object でない")
            continue
        nid, outcome = t.get("nodeid"), t.get("outcome")
        if not isinstance(nid, str) or "::" not in nid:
            bad.append(f"tests[{i}]: nodeid が不正:{nid!r}")
            continue
        if outcome not in OUTCOME_VALUES:
            bad.append(f"{nid}: outcome 語彙外:{outcome!r}")
        if nid in seen:
            bad.append(f"{nid}: nodeid が重複（同一 nodeid の二重計上）")
        seen.add(nid)
    return bad


def outcome_index(data: dict | None) -> dict[str, str]:
    """nodeid → outcome。パラメータ化テストは `[...]` を除いた基底 nodeid にも畳む。

    畳み込みは「1 つでも passed でないものがあれば passed でない」（最悪値優先）。
    """
    idx: dict[str, str] = {}
    if not data:
        return idx
    for t in data.get("tests") or []:
        if not isinstance(t, dict):
            continue
        nid, outcome = t.get("nodeid"), t.get("outcome")
        if not isinstance(nid, str) or outcome not in OUTCOME_VALUES:
            continue
        base = nid.split("[", 1)[0]
        for key in {nid, base}:
            prev = idx.get(key)
            if prev is None or (prev == "passed" and outcome != "passed"):
                idx[key] = outcome
    return idx


def s0_target_nodeids(ctx: Ctx) -> list[str]:
    """S0.1 対象 UT の nodeid（リポジトリ相対）を列挙する。"""
    out: list[str] = []
    for d in ctx.duc:
        if int(d["id"][3:]) > S0_DU_MAX:
            continue
        for a in d["apis"]:
            for ref in ut_nodeids(a):
                if "::" in ref:
                    out.append(f"{TESTS_UNIT_REL}/{ref}")
    return sorted(set(out))


def runtime_skips(ctx: Ctx, data: dict | None) -> list[str]:
    """対象 UT のうち**実行時に** skip／xfail された nodeid（実測）。"""
    idx = outcome_index(data)
    return [n for n in s0_target_nodeids(ctx)
            if idx.get(n) in ("skipped", "xfailed", "xpassed")]


def statically_invisible_skips(ctx: Ctx, data: dict | None) -> list[str]:
    """静的検査（AST）では見えないのに実行時に skip／xfail された対象 UT。

    これが動的 import 経由 skip・実行時条件による skip の検出点であり、G-UT-NO-ESCAPE の
    原理的限界を埋める部分そのもの。**収集自体からの除外**（outcome に現れない）はここでは
    見えないため、`per_test_faults` の欠落判定（G-UT-PER-TEST-OUTCOME）が担当する。
    """
    from tools.gates.test_pairing import detect_ut_escapes
    flagged: set[str] = set()
    for item in detect_ut_escapes(ctx):
        # 形式: "DU-xx:<file>::<test>:<label>" / "DU-xx:<file>:<label>"
        parts = item.split(":")
        if len(parts) >= 2:
            fname = parts[1]
            tname = parts[3] if len(parts) >= 4 and parts[2] == "" else ""
            flagged.add(f"{TESTS_UNIT_REL}/{fname}::{tname}" if tname
                        else f"{TESTS_UNIT_REL}/{fname}")
    out = []
    for n in runtime_skips(ctx, data):
        if n in flagged or n.split("::", 1)[0] in flagged:
            continue
        out.append(n)
    return out


def per_test_faults(ctx: Ctx, data: dict | None) -> list[str]:
    """対象 UT が **nodeid 単位で** executed かつ passed であることを突合する。

    集計 pass 件数では「別のテストが通ったので green」を許してしまう。ここは
    du-contracts の `apis[].ut` が指す nodeid そのものの成立だけを認める。
    """
    idx = outcome_index(data)
    bad: list[str] = []
    for n in s0_target_nodeids(ctx):
        outcome = idx.get(n)
        if outcome is None:
            bad.append(f"{n}: outcome レポートに存在しない（未実行・改名・収集除外）")
        elif outcome in NOT_PASSED:
            bad.append(f"{n}: {outcome}")
    return bad


def _steps(job: dict) -> list[dict]:
    """job の steps のうち **実際に走る**もの（`if: false` 相当を除く）を返す。"""
    out = []
    for s in job.get("steps") or []:
        if not isinstance(s, dict):
            continue
        cond = s.get("if")
        if isinstance(cond, bool) and not cond:
            continue
        if isinstance(cond, str) and cond.strip().lower() in ("false", "${{ false }}"):
            continue
        out.append(s)
    return out


def _command_lines(step: dict) -> list[str]:  # noqa: C901 — 分解規則を 1 か所に集約する
    """step が**実際に実行する**コマンド行を返す（コメント・echo は除く）。

    `run` の各行からシェルコメントを剥ぎ、`&&`／`;`／`|` で分割し、`echo`・`:`・`true` の
    ように「語を書くだけ」のコマンドを落とす。これがないと `# python3 scripts/... ` や
    `echo "collect_test_outcome.py"` が配線として通ってしまう（独立レビュー R2-01）。
    """
    out: list[str] = []
    run = step.get("run")
    if isinstance(run, str):
        # シェルの行継続（末尾 `\`）は 1 コマンドとして繋ぐ
        joined = re.sub(r"\\\s*\n\s*", " ", run)
        for raw in joined.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            segments = [s.strip() for s in re.split(r"&&|\|\||;|\|", line) if s.strip()]
            # 条件付き実行の左辺に必ず失敗するコマンドを置く偽装（`false && pytest ...`）は、
            # その行全体を配線として認めない（独立レビュー R4-01）
            stripped = [_strip_env(_argv(s)) for s in segments]
            heads = [(toks or [""])[0] for toks, _ in stripped]
            # guard（必ず失敗するコマンド）を含む行、および実行対象を特定できない行は捨てる
            if any(Path(h).name in GUARD_HEADS for h in heads) or not all(ok for _, ok in stripped):
                continue
            for cmd, head in zip(segments, heads, strict=True):
                if Path(head).name in NOOP_HEADS:
                    continue
                out.append(cmd)
    uses = step.get("uses")
    if isinstance(uses, str) and uses:
        with_ = step.get("with")
        args = " ".join(f"{k}={v}" for k, v in with_.items()) if isinstance(with_, dict) else ""
        out.append(f"uses:{uses} {args}")
    return out


def ci_wiring_faults() -> list[str]:
    """CI が outcome を**成果物として生成してからゲートを走らせる**配線かを YAML 構造で検査する。

    文字列の出現有無だけを見ると、コメント・無効化された job・`if: false` の step に語だけ残して
    実体を外せる（独立レビュー R1-03）。そこで YAML を解析し、**同一 job の実行される step 群**の中で
    `pytest --junitxml` → 収集 → `run_all.py` がこの順に現れることを要求する。
    """
    bad: list[str] = []
    try:
        import yaml
    except ImportError:  # 解析器が無い環境では検査できない → fail-close
        return ["PyYAML が無く CI 配線を構造検査できない（uv sync --group dev を実行する）"]
    for wf in CI_WORKFLOWS:
        p = ROOT / wf
        if not p.is_file():
            bad.append(f"{wf}: ワークフローが存在しない")
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            bad.append(f"{wf}: YAML として読めない:{e}")
            continue
        jobs = doc.get("jobs") if isinstance(doc, dict) else None
        if not isinstance(jobs, dict):
            bad.append(f"{wf}: jobs が無い")
            continue
        wired = False
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                continue
            # step を跨いでも step 内でも「実行されるコマンド列」の順序として評価する
            cmds = [c for s in _steps(job) for c in _command_lines(s)]
            positions: list[int] = []
            after = 0  # 3 要件は**別々のコマンド**で、前段より後ろに現れること
            for needle in CI_STEP_ORDER:
                idx = next((i for i, c in enumerate(cmds[after:], start=after)
                            if _match(c, needle)), None)
                if idx is None:
                    break
                positions.append(idx)
                after = idx + 1
            # pytest と収集の間に別コマンドを挟ませない（junit を差し替える隙を作らない
            # — 独立レビュー R4-02。CI を書き換えられる主体を完全には排除できないが、
            # 「pytest の直後に収集」を構造要件にして差し替えの余地を最小化する）
            if len(positions) == len(CI_STEP_ORDER) and positions[1] != positions[0] + 1:
                bad.append(f"{wf}[{jname}]: pytest と outcome 収集の間に別コマンドがある"
                           "（生成された junit を差し替える隙になる）")
                break
            if len(positions) == len(CI_STEP_ORDER):
                wired = True
                if wf == UPLOAD_WORKFLOW:
                    bad += _upload_faults(wf, jname, cmds)
                break
        if not wired:
            bad.append(f"{wf}: 同一 job 内に「pytest --junitxml → 収集 → run_all」の実行順序が無い"
                       "（コメント・echo・無効 step は配線とみなさない）")
    if not COLLECTOR.is_file():
        bad.append("scripts/collect_test_outcome.py が存在しない")
    bad += _xfail_strict_faults()
    return bad


def _argv(cmd: str) -> list[str]:
    try:
        return shlex.split(cmd)
    except ValueError:
        return cmd.split()


def _is_runner(tok: str) -> bool:
    name = Path(tok).name
    return name in RUNNERS or (name.startswith("python")
                               and name[6:].replace(".", "").isdigit())


ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
# `env` で解析を保証できるオプションだけを許す。これ以外（-C/--chdir/-S 等、値の取り方が
# 環境依存のもの）が現れた行は「実行対象を特定できない」として配線から外す（fail-close）。
ENV_VALUE_FLAGS = ("-u", "--unset")
ENV_BOOL_FLAGS = ("-i", "--ignore-environment", "-0", "--null")


def _strip_env(tokens: list[str]) -> tuple[list[str], bool]:
    """先頭の環境変数代入と `env ...` を取り除く。

    戻り値の第 2 要素は「実行対象を確実に特定できたか」。`env` に解析対象外のオプションが
    付く形（`env -C /tmp false && pytest ...`）は False を返し、呼出側が行ごと捨てる
    （独立レビュー R6-01・R7-01 — オプションを 1 つずつ潰す追いかけっこをやめる）。
    """
    out = list(tokens)
    while out:
        if ASSIGNMENT.fullmatch(out[0]):
            out.pop(0)
        elif Path(out[0]).name == "env":
            out.pop(0)
            while out:
                if ASSIGNMENT.fullmatch(out[0]) or out[0] in ENV_BOOL_FLAGS:
                    out.pop(0)
                elif out[0] == "--":
                    out.pop(0)
                    break
                elif out[0] in ENV_VALUE_FLAGS:  # 値を取るオプションは値ごと消費する
                    out.pop(0)
                    if not out:
                        return out, False  # 値が無い形は解析できない（独立レビュー R8-01）
                    out.pop(0)
                elif out[0].startswith("-"):
                    return out, False  # 解析対象外のオプション → 実行対象を特定できない
                else:
                    break
        else:
            break
    return out, True


def _entry_point(tokens: list[str]) -> str | None:
    """ランナ列を剥がして「実行対象」の argv 位置を返す（実行形でなければ None）。

    許すのは `X`／`python3 X`／`python -m X`／`uv run [flags] X` の形だけ。
    `-c`・`--help` 等の**実行しない**フラグを含む形、ランナを二重に連ねた形
    （`python3 uv run pytest`）は認めない（独立レビュー R4-01・R5-01）。
    """
    tokens, ok = _strip_env(tokens)
    if not ok or not tokens or any(t in NON_EXEC_FLAGS for t in tokens):
        return None
    i = 0
    if _is_runner(tokens[0]):
        i = 1
        while i < len(tokens) and (tokens[i] in RUNNER_PREFIXES or tokens[i].startswith("-")):
            i += 1
        if i >= len(tokens) or _is_runner(tokens[i]):
            return None  # ランナだけ／ランナの連鎖は実行対象が定まらない
        return tokens[i]
    return None if tokens[0].startswith("-") else tokens[0]


def _runs_pytest(cmd: str) -> bool:
    """コマンドが pytest の実行かを判定する（`--junitxml` を引数に持つだけの語を弾く）。"""
    entry = _entry_point(_argv(cmd))
    return entry is not None and Path(entry).name.startswith("pytest")


def _invokes(cmd: str, script: str) -> bool:
    """コマンドがそのスクリプトを**実行**しているか（引数の中の文字列でないか）を判定する。"""
    tokens = _argv(cmd)
    if not tokens:
        return False
    if tokens[0].endswith(script) or Path(tokens[0]).name == script.rsplit("/", 1)[-1]:
        return True
    entry = _entry_point(tokens)
    return entry is not None and (entry == script or entry.endswith(script))


def _match(cmd: str, needle: str) -> bool:
    if needle == "--junitxml":
        return "--junitxml" in cmd and _runs_pytest(cmd)
    return _invokes(cmd, needle)


def _upload_faults(wf: str, jname: str, cmds: list[str]) -> list[str]:
    """outcome を CI 成果物として**両ファイルとも**残す upload step が 1 つ以上あるか検査する。

    最初の upload だけを見ると、coverage など別成果物の upload を先に置いた正当な構成を
    偽陽性で落とす（独立レビュー R3-03）。
    """
    uploads = [c for c in cmds if "uses:actions/upload-artifact" in c]
    if not uploads:
        return [f"{wf}[{jname}]: outcome を CI 成果物として upload していない"]
    faults: list[list[str]] = []
    for up in uploads:
        bad = [f"{wf}[{jname}]: upload の path に {p} が無い"
               for p in ("reports/junit.xml", "reports/test-outcome.json") if p not in up]
        if "if-no-files-found=error" not in up.replace(" ", "").replace(":", "="):
            bad.append(f"{wf}[{jname}]: upload が if-no-files-found: error でない"
                       "（成果物が無くても素通りする）")
        if not bad:
            return []
        faults.append(bad)
    return min(faults, key=len)


def _xfail_strict_faults() -> list[str]:
    """pytest の `xfail_strict` が **[tool.pytest.ini_options] で** 有効かを検査する。

    非 strict の xfail は「実際には通った」場合に junit 上でただの成功として現れ、
    xpass を passed と誤認する（独立レビュー R1-02）。全行の文字列検索では別セクションの
    同名キーで通ってしまうため、TOML として解析して真偽値まで見る（同 R2-04）。
    """
    if not PYPROJECT.is_file():
        return ["pyproject.toml が無く xfail_strict を確認できない"]
    try:
        import tomllib
        cfg = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    except (ImportError, ValueError) as e:
        return [f"pyproject.toml を TOML として解析できない:{e}"]
    value = (((cfg.get("tool") or {}).get("pytest") or {})
             .get("ini_options") or {}).get("xfail_strict")
    if value is not True:
        return ["[tool.pytest.ini_options] の xfail_strict が true（真偽値）でない:"
                f"{value!r} — xpass が passed として素通りする"]
    return []


# ---------------------------------------------------------------- 間接束縛の着手検出
# 関数本体を書かずに実装を与える束縛（`f = partial(impl, ...)` 等）。
# `has_implementation`（def／class／lambda の実体）はこれらを実装として数えない。
BINDING_FACTORIES = (
    "functools.partial", "functools.partialmethod", "functools.singledispatch",
    "functools.reduce", "types.MethodType", "types.FunctionType",
    "operator.methodcaller", "operator.attrgetter", "operator.itemgetter",
)


def _import_origins(tree: ast.Module) -> dict[str, str]:
    """ローカル名 → import 起点の完全パス（全モジュール対象の汎用版）。"""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for a in node.names:
                out[a.asname or a.name] = f"{mod}.{a.name}" if mod else a.name
    return out


def _dotted(node: ast.AST, origins: dict[str, str]) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        base = origins.get(node.id, node.id)
        return ".".join([base, *reversed(parts)])
    return None


def _binding_kind(value: ast.expr, origins: dict[str, str], local_defs: set[str]) -> str | None:
    """右辺が「実装の間接束縛」かを判定し、その種類を返す。"""
    if isinstance(value, ast.Lambda):
        return "lambda"
    if isinstance(value, ast.Call):
        dotted = _dotted(value.func, origins) or ""
        if dotted in BINDING_FACTORIES or dotted.startswith("functools.partial"):
            return "partial"
        # デコレータ適用の代入（`f = deco(impl)`）— 引数に呼出し可能な名前が渡る形だけを見る
        for arg in [*value.args, *(k.value for k in value.keywords)]:
            if isinstance(arg, ast.Lambda):
                return "decorator(lambda)"
            if isinstance(arg, (ast.Name, ast.Attribute)):
                name = arg.id if isinstance(arg, ast.Name) else arg.attr
                if name in local_defs or (isinstance(arg, ast.Name) and arg.id in origins):
                    return "decorator"
        return None
    if isinstance(value, (ast.Name, ast.Attribute)):
        name = value.id if isinstance(value, ast.Name) else value.attr
        if name in local_defs:
            return "alias"
        if isinstance(value, ast.Name) and value.id in origins:
            return "re-export"
        if isinstance(value, ast.Attribute) and _dotted(value, origins):
            dotted = _dotted(value, origins) or ""
            if dotted.split(".")[0] in origins.values() or dotted.split(".")[0] in origins:
                return "re-export"
        return None
    # 上記に当てはまらない式（Subscript・IfExp・BoolOp・内包表記…）でも、実装名や import 由来の
    # 名前を運んでいれば束縛とみなす（`API = REGISTRY["real"]` のような迂回 — 独立レビュー R4-03）。
    # 純粋なリテラル・定数は名前を含まないためここに落ちない。
    for sub in ast.walk(value):
        if isinstance(sub, ast.Name) and (sub.id in local_defs or sub.id in origins):
            return "expr"
        if isinstance(sub, ast.Attribute) and sub.attr in local_defs:
            return "expr"
    return None


def _target_name(tgt: ast.expr) -> str | None:
    """代入先から**束縛される名前**を取り出す。

    `run_microloop = ...`（Name）だけでなく、`obj.run_microloop = ...`（Attribute）、
    `registry["run_microloop"] = ...`（Subscript の定数キー）、
    `globals()["run_microloop"] = ...` も同じ「名前への束縛」として扱う（独立レビュー R1-04）。
    """
    if isinstance(tgt, ast.Name):
        return tgt.id
    if isinstance(tgt, ast.Attribute):
        return tgt.attr
    if isinstance(tgt, ast.Subscript):
        key = tgt.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            return key.value
    return None


def _assign_targets(node: ast.AST) -> list[tuple[str, ast.expr]]:
    """`対象 = 式` を (束縛名, 右辺) で列挙する（タプル代入・注釈付き・属性・添字を含む）。"""
    out: list[tuple[str, ast.expr]] = []
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, (ast.Tuple, ast.List)) and isinstance(node.value, (ast.Tuple, ast.List)) \
                    and len(tgt.elts) == len(node.value.elts):
                out += [(n, v) for t, v in zip(tgt.elts, node.value.elts, strict=True)
                        if (n := _target_name(t))]
            elif (name := _target_name(tgt)):
                out.append((name, node.value))
    elif isinstance(node, ast.AnnAssign) and node.value is not None \
            and (name := _target_name(node.target)):
        out.append((name, node.value))
    return out


def _call_bindings(tree: ast.Module, origins: dict[str, str],
                   local_defs: set[str]) -> list[tuple[str, str]]:
    """呼出しによる束縛を (名前, 種類) で列挙する。

    - `setattr(obj, "name", impl)`
    - `registry.update({"name": impl})` / `dict(name=impl)` 形式の一括登録
    - `registry.register("name", impl)` のような 2 引数登録（第 1 引数が定数文字列）
    """
    out: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if fname == "setattr" and len(node.args) >= 3:
            key = node.args[1]
            kind = _binding_kind(node.args[2], origins, local_defs)
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and kind:
                out.append((key.value, f"setattr({kind})"))
            continue
        # 辞書リテラル経由の登録（update / dict / 直接の Dict 実引数）
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            if isinstance(arg, ast.Dict):
                for k, v in zip(arg.keys, arg.values, strict=True):
                    kind = _binding_kind(v, origins, local_defs)
                    if isinstance(k, ast.Constant) and isinstance(k.value, str) and kind:
                        out.append((k.value, f"{fname or 'call'}({kind})"))
        for kw in node.keywords:
            kind = _binding_kind(kw.value, origins, local_defs)
            if kw.arg and kind:
                out.append((kw.arg, f"{fname or 'call'}(kwarg:{kind})"))
        if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            kind = _binding_kind(node.args[1], origins, local_defs)
            if kind:
                out.append((node.args[0].value, f"{fname or 'call'}({kind})"))
    return out


MAX_BINDING_PASSES = 200  # 収束の保険（実際の上限は「代入名の個数」— 下の while で自然に止まる）


def file_bindings(path: Path) -> list[tuple[str, str]]:
    """1 ファイル内の間接束縛を (束縛名, 種類) で列挙する（構文エラーは fail-close）。

    実装を指す名前は**固定点で伝播**する。`tmp = functools.partial(real)` の `tmp` を
    実装名として覚え、`<API 名> = tmp` も束縛として検出する（独立レビュー R2-02）。
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return [("<parse-error>", "syntax")]
    origins = _import_origins(tree)
    impl_names = {n.name for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    found: dict[str, str] = {}
    grew, passes = True, 0
    while grew and passes < MAX_BINDING_PASSES:  # impl_names が増えなくなるまで収束させる
        passes += 1
        grew = False
        pairs: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                for name, value in _assign_targets(node):
                    if name.startswith("__") and name.endswith("__"):
                        continue
                    kind = _binding_kind(value, origins, impl_names)
                    if kind:
                        pairs.append((name, kind))
        pairs += _call_bindings(tree, origins, impl_names)
        for name, kind in pairs:
            if found.get(name) != kind:
                found[name] = kind
            if name not in impl_names:  # 束縛された名前自身が次段の実装名になる
                impl_names.add(name)
                grew = True
    return sorted(found.items())


def _display(p: Path) -> str:
    """リポジトリ相対パスで表示する（検査対象を差し替えた場合は絶対パスのまま）。"""
    try:
        return rel(p)
    except ValueError:
        return str(p)


def binding_signals(ctx: Ctx, pkg: Path | None = None) -> list[str]:
    """`src/helix` の間接束縛による実装着手シグナルを列挙する。

    `def` を書かずに `run_microloop = functools.partial(_impl, ...)` と置くだけで、
    `has_implementation`（def／class／lambda）と `detect_du_api_implementations`
    （`def <api>` の正規表現）の両方を回避できてしまう（独立レビュー R7-03 の deferred）。

    シグナルにするのは **DU-01〜12 の API 名への束縛**に限る。無関係な内部ヘルパの別名や
    再エクスポートまで着手扱いにすると、S0.2 以降の正当な基盤コードを止める偽陽性になる
    （独立レビュー R1-04）。構文エラーだけは解析不能として fail-close で報告する。
    """
    api_names = {api_name(a) for d in ctx.duc if int(d["id"][3:]) <= S0_DU_MAX
                 for a in d["apis"]} - {""}
    du_of = {api_name(a): d["id"] for d in ctx.duc if int(d["id"][3:]) <= S0_DU_MAX
             for a in d["apis"]}
    sig: list[str] = []
    pkg = pkg or SRC_PKG  # 既定値を呼出し時に解決する（検査対象の差替えを効かせる）
    if not pkg.exists():
        return sig
    for p in sorted(pkg.rglob("*.py")):
        for name, kind in file_bindings(p):
            label = f"{_display(p)}:{name}={kind}"
            if name in api_names:
                sig.append(f"du-api-bind:{du_of.get(name)}:{label}")
            elif kind == "syntax":
                sig.append(f"parse-error:{_display(p)}")
    return sorted(set(sig))


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    started = ctx.impl_started
    faults = report_faults()
    data = load_outcome() if not faults else None
    present = OUTCOME_REPORT.is_file()

    missing = started and not present
    wiring = ci_wiring_faults()
    gate("G-UT-RUNTIME-OUTCOME", not faults and not missing and not wiring,
         "pytest の実行結果（junit xml → reports/test-outcome.json）が CI 成果物として生成され、"
         "HEAD へ束縛された正しい形式で、着手後は存在が必須 "
         f"(配線={wiring}, 形式違反={faults[:3]}, レポート={'あり' if present else 'なし'}, "
         f"着手={started})")

    skips = runtime_skips(ctx, data)
    invisible = statically_invisible_skips(ctx, data)
    gate("G-UT-DYNAMIC-SKIP", not (started and skips) and not (started and invisible),
         "対象 UT の skip／xfail を**実行結果**で検出する（動的 import・条件付き skip を含む。"
         "収集除外は G-UT-PER-TEST-OUTCOME が担当）。"
         "着手後は 1 件も残せない（未着手は猶予） "
         f"(着手={started}, 実行時 skip={len(skips)} 件, うち AST 不可視={len(invisible)} 件"
         f"{'' if not invisible else f':{invisible[:3]}'})")

    auto = binding_signals(ctx)
    declared = bool(ctx.skip_budget.get("s0_impl_started"))
    gate("G-IMPL-START-BINDING", not (auto and not declared),
         "`def` を書かない間接束縛（partial・デコレータ適用・別名／再エクスポート・属性代入・"
         "レジストリ登録・globals 注入・setattr、多段束縛は固定点で追跡）による S0.1 実装着手を"
         "検出し、宣言と一致させる "
         f"(束縛={auto[:3]}, 宣言={declared})")

    per = per_test_faults(ctx, data) if present else []
    unresolved = started and not present
    gate("G-UT-PER-TEST-OUTCOME", not (started and (per or unresolved)),
         "du-contracts の apis[].ut が指す対象 UT が **nodeid 単位で** executed かつ passed "
         "（集計 pass 件数では代替できない・着手後に強制） "
         f"(着手={started}, 対象={len(s0_target_nodeids(ctx))} 件, 未成立={len(per)} 件"
         f"{'' if not per else f':{per[:3]}'})")
