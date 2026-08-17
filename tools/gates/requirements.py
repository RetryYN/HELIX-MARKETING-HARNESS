"""要求・要件層ゲート: 分母・ID 一意性・構造化契約・AC 極性・上流戦略ループ。"""

from __future__ import annotations

import copy
import datetime
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from tools.gates.common import (
    AC_SCHEMA,
    AUTHORITY,
    BR_MEDIA_DIR,
    BR_SCHEMA,
    ENVIRONMENT,
    FIXTURES,
    FR_SCHEMA,
    HISTORICAL_COUNTS,
    L1,
    L3,
    LTW_DIR,
    MANIFEST,
    MR_DIR,
    NFR_SCHEMA,
    ROOT,
    STRATEGY_DESIGN,
    STRATEGY_DIR,
    STRATEGY_LEARNING,
    STRATEGY_REQ,
    STRATEGY_SCHEMA_DIR,
    STRATEGY_TEST_DESIGN,
    WF_CONTRACTS,
    Ctx,
    gate,
    is_frozen,
    load,
    md_count,
    rel,
    schema_check,
    ut_nodeids,
)

MANDATED_GROUPS = {
    "brand-isolation", "upstream-downstream-separation", "hypothesis-refutation-revision",
    "kpi-crossover", "multi-media-campaign", "content-value-definition", "zero-ad-spend",
    "ethics-line", "human-ai-boundary", "evidence-resume-idempotency", "external-ops-approval",
    "learning-failure-packet",
}
POLARITIES = {"normal", "reject", "boundary-recovery"}
MAX_SRC_AGE_DAYS = 90
AMBIGUOUS_MEDIA_PATTERNS = {
    "月数X": re.compile(r"月数[件冊枚通]?"),
    "数X": re.compile(r"(?<![0-9])数[件冊枚通]"),
    "十数X": re.compile(r"(?:10\s*数|十数)[件冊枚通]?"),
    "少量": re.compile(r"少量"),
    "適度": re.compile(r"適度"),
    "低頻度": re.compile(r"低頻度"),
    "目安": re.compile(r"目安"),
}
STALE_MEDIA_FACTS = ("新規タイトル 1 日 3 冊制限", "1 日 3 冊制限")

STRATEGY_SCHEMAS = [
    "market-observation", "market-model", "segment-context", "problem-model",
    "value-hypothesis", "category-definition", "positioning-hypothesis", "causal-assumption",
    "strategic-choice", "strategic-brief", "tactical-learning-packet", "strategy-revision",
    "logic-tree", "inference-analysis",
]
STRAT_GATES = ["G-STRAT-BRIEF", "G-STRAT-TRACE", "G-SEGMENT-CONTEXT", "G-OBS-INTERPRETATION",
               "G-LEARNING-TRACE", "G-NO-DIRECT-STRATEGY-MUTATION", "G-REVISION-EVIDENCE",
               "G-STRATEGY-VERSION", "G-MEDIA-ROLE", "G-CONTENT-VALUE-DEFINITION"]

AUTHORITY_POLICY = AUTHORITY / "development/requirement-engine-authority.json"
EXPECTED_ENVIRONMENT_TARGETS = {
    "ローカル WP",
    "本番 WP",
    "GA4",
    "承認通知",
    "credential 全般",
}


# ---------------------------------------------------------------- 検出関数
def detect_polarity_gaps(contracts: list[dict], acs: list[dict]) -> list[str]:
    """S0 契約で 3 極性が AC でも理由付き N/A でも満たされない箇所を列挙する。"""
    by_t: dict[str, set] = {}
    for a in acs:
        by_t.setdefault(a["target"], set()).add(a["polarity"])
    bad: list[str] = []
    for c in contracts:
        if c["slice"] != "S0":
            continue
        have = by_t.get(c["id"], set())
        na = set(c.get("ac_na", {}).keys())
        if (have | na) < POLARITIES or (have & na):
            bad.append(f"{c['id']}:{sorted(POLARITIES - have - na) or '重複NA'}")
    return bad


def detect_invariant_gaps(contracts: list[dict], acs: list[dict]) -> list[str]:
    """S0 契約の各不変条件が『固有の』負方向 AC を持たない箇所を列挙する。"""
    by_id = {a["id"]: a for a in acs}
    bad: list[str] = []
    for c in contracts:
        if c["slice"] != "S0":
            continue
        imap = c.get("invariant_ac_map")
        if not imap or len(imap) != len(c["invariants"]):
            bad.append(f"{c['id']}:map{len(imap or [])}!=inv{len(c['invariants'])}")
            continue
        used_neg: set[str] = set()
        for i, grp in enumerate(imap):
            maybe = [by_id.get(a) for a in grp]
            if any(r is None for r in maybe):
                bad.append(f"{c['id']}[{i}]:AC不在")
                continue
            refs = [r for r in maybe if r is not None]
            if any(r["target"] != c["id"] for r in refs):
                bad.append(f"{c['id']}[{i}]:target不一致")
                continue
            neg = {r["id"] for r in refs
                   if (r["polarity"] == "reject" and r["error_type"] not in ("なし", ""))
                   or r["polarity"] == "boundary-recovery"}
            if not neg:
                bad.append(f"{c['id']}[{i}]:負方向AC欠落")
            elif neg & used_neg:
                bad.append(f"{c['id']}[{i}]:負方向AC使い回し{sorted(neg & used_neg)}")
            else:
                used_neg |= neg
    return bad


def environment_contract_faults() -> list[str]:
    """旧S0環境fixtureを現行の外部write authorityへ昇格させない。

    ``environment.json`` は旧baselineのテストfixture（Docker WPを実書込み先と
    する時代の構造資料）であり、VPS製品の現行write・通知・承認経路ではない。
    revising中はfixtureの構造だけを再検証する。approved cutover後に同じfixtureを
    成功条件として使うことは、新しい環境/admission authorityが明示されるまで
    fail-closeする。
    """
    faults: list[str] = []
    try:
        env = load(ENVIRONMENT)["items"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return ["旧S0環境fixtureを読み込めない"]
    if not isinstance(env, list):
        return ["旧S0環境fixtureのitemsが配列でない"]

    valid_targets: list[str] = []
    for index, entry in enumerate(env):
        if not isinstance(entry, dict):
            faults.append(f"旧S0環境fixtureのitems[{index}]がobjectでない")
            continue
        target = entry.get("target")
        if not isinstance(target, str) or not target.strip():
            faults.append(f"旧S0環境fixtureのitems[{index}].targetが非空文字列でない")
            continue
        if target in valid_targets:
            faults.append(f"旧S0環境fixtureのtargetが重複={target}")
            continue
        valid_targets.append(target)
    targets = set(valid_targets)
    if targets != EXPECTED_ENVIRONMENT_TARGETS:
        faults.append(
            "旧S0環境fixtureのtarget集合が正本と不一致"
            f" (actual={sorted(targets)}, expected={sorted(EXPECTED_ENVIRONMENT_TARGETS)})"
        )
    prod_rules = [
        e for e in env
        if isinstance(e, dict) and e.get("target") in ("本番 WP", "GA4")
    ]
    if "ローカル WP" not in targets:
        faults.append("旧S0環境fixtureのDocker WP構造が欠落")
    for entry in prod_rules:
        policy = str(entry.get("test_policy", ""))
        if "書込み" not in policy and "書込" not in policy:
            faults.append(f"旧S0環境fixture {entry.get('target')}:書込み禁止の宣言なし")

    try:
        authority = load(AUTHORITY_POLICY)
    except (OSError, json.JSONDecodeError):
        return [*faults, "現行要求authorityを読み込めない"]
    if (
        authority.get("requirements_baseline_status") != "revising"
        or type(authority.get("implementation_authorized")) is not bool
        or authority.get("implementation_authorized") is not False
    ):
        faults.append(
            "旧S0環境fixtureを現行write/通知authorityへ使えるstageではない（新環境admissionが未定義）"
        )

    try:
        manifest = load(MANIFEST)
        item = next(
            row for row in manifest.get("items", [])
            if isinstance(row, dict) and row.get("artifact_id") == "L3-S0-ENVIRONMENT"
        )
    except (OSError, json.JSONDecodeError, AttributeError, StopIteration):
        item = None
    if not isinstance(item, dict):
        faults.append("旧S0環境fixtureのmanifest登録がない")
    else:
        if item.get("applicability_status") != "revalidation_required":
            faults.append("旧S0環境fixtureがrevalidation_requiredへ隔離されていない")
        if item.get("implementation_input") is not False:
            faults.append("旧S0環境fixtureがimplementation inputへ流入している")
    return faults


def detect_contract_table_faults(contracts: list[dict], tables: set[str],
                                 trn_states: dict[str, set]) -> list[str]:
    """FR/SR 契約の tables 表記・state_transitions が DDL/遷移正本と食い違う箇所を列挙する。"""
    bad: list[str] = []
    for c in contracts:
        for entry in c["tables"]:
            m = re.match(r"^(?:r|w|rw)[:：]\s*([a-z_]+)", entry)
            if m:
                if m.group(1) not in tables:
                    bad.append(f"{c['id']}:未知表{m.group(1)}")
            elif not entry.startswith("参照:"):
                bad.append(f"{c['id']}:表記不正『{entry[:24]}』")
        for entry in c["state_transitions"]:
            ent = entry.split(":")[0].split("：")[0].strip()
            if ent in trn_states:
                for fr_s, to_s in re.findall(r"([a-z_]+)\s*→\s*([a-z_]+)", entry):
                    if fr_s not in trn_states[ent] or to_s not in trn_states[ent]:
                        bad.append(f"{c['id']}:未知状態{fr_s}→{to_s}")
            elif entry.startswith("テーブル列:"):
                m2 = re.match(r"テーブル列:\s*([a-z_]+)\.([a-z_]+)\s*:", entry)
                if not m2:
                    bad.append(f"{c['id']}:列寿命表記不正『{entry[:24]}』")
                elif m2.group(1) not in tables:
                    bad.append(f"{c['id']}:未知表{m2.group(1)}（列寿命）")
            elif not entry.startswith("参照:"):
                bad.append(f"{c['id']}:未知entity『{ent[:20]}』")
    return bad


# 旧体系の分母表記（historical_counts と監査記録以外に現れてはならない）
LEGACY_DENOMINATORS = ("AC 19", "TC 59", "UTC 69", "AC19", "TC59", "UTC69")
# 監査記録・承認ログ・レビュー成果物は **append-only の歴史**（過去行の書換えは改竄）なので走査対象外。
# archive/superseded は live_markdown が除外済み。
HISTORICAL_DIRS = (
    "docs/00-authority/audits/",
    "docs/00-authority/approvals/",
    "docs/00-authority/reviews/",
)


def detect_legacy_denominator_leaks(root: Path = ROOT) -> list[str]:
    """現役文書（root 3 ファイル＋L0〜L6＋権威層の非監査文書）に旧分母表記が残る箇所を列挙する。"""
    from tools.gates.common import live_markdown

    bad: list[str] = []
    targets = [root / "README.md", root / "CLAUDE.md", root / "AGENTS.md"]
    targets += [p for p in live_markdown()
                if not any(rel(p).startswith(d) for d in HISTORICAL_DIRS)]
    for p in targets:
        txt = p.read_text(encoding="utf-8")
        for legacy in LEGACY_DENOMINATORS:
            if legacy in txt:
                bad.append(f"{rel(p)}:旧分母『{legacy}』")
    return sorted(set(bad))


def current_denominators(ctx: Ctx) -> dict[str, int]:
    """現行分母（PO 指示 §3 — これ以外の AC/TC/UT 分母を現役で使わない）。"""
    return {
        "AC_CONTRACT": len(ctx.acc),
        "TCC": len(ctx.tcc),
        "API": sum(len(x["apis"]) for x in ctx.duc),
        "API_UT": len({u for x in ctx.duc for a in x["apis"] for u in ut_nodeids(a)}),
    }


def _prepare_contract_sql(ddl: str, sql: str) -> str | None:
    """DDL 正本へ SQL をprepareし、構文・表・列の不整合理由を返す。"""
    if re.search(r"<[^>]+>", sql):
        return "角括弧placeholderは実行不能"
    params = {name: "2026-08-01T00:00:00Z"
              for name in set(re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", sql))}
    if "service" in params:
        params["service"] = "fixture-service"
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(ddl)
        con.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    except sqlite3.Error as exc:
        return str(exc)
    finally:
        con.close()
    return None


def detect_nfr_verification_faults(nfrs: list[dict], acs: list[dict],
                                   tcs: list[dict], ddl: str) -> list[str]:
    """NFR→AC→TCC が実在IDで接続され、測定方法が実行可能な形か検査する。"""
    ac_by_id = {a["id"]: a for a in acs}
    tc_by_id = {t["id"]: t for t in tcs}
    bad: list[str] = []
    for nfr in nfrs:
        nid = nfr["id"]
        expected_aspects = set(nfr.get("verification_aspects", []))
        ac_refs = nfr.get("trace_down", {}).get("ac", [])
        tc_refs = nfr.get("trace_down", {}).get("tc", [])
        if not ac_refs:
            bad.append(f"{nid}:AC未接続")
        if not tc_refs:
            bad.append(f"{nid}:TCC未接続")
        for aid in ac_refs:
            ac = ac_by_id.get(aid)
            if ac is None:
                bad.append(f"{nid}:未知AC {aid}")
            elif ac.get("target") != nid:
                bad.append(f"{nid}:{aid} target={ac.get('target')}")
        for tid in tc_refs:
            tc = tc_by_id.get(tid)
            if tc is None:
                bad.append(f"{nid}:未知TCC {tid}")
            elif not set(tc.get("ac", [])) & set(ac_refs):
                bad.append(f"{nid}:{tid}がNFRのACを検証しない")
        ac_aspects = {aspect for aid in ac_refs if (ac := ac_by_id.get(aid))
                      for aspect in ac.get("verification_aspects", [])}
        tc_aspects = {aspect for tid in tc_refs if (tc := tc_by_id.get(tid))
                      for aspect in tc.get("verification_aspects", [])}
        tc_assertions = {aspect for tid in tc_refs if (tc := tc_by_id.get(tid))
                         for aspect in tc.get("aspect_assertions", {})}
        if not expected_aspects or any(not x.startswith(f"{nid}:") for x in expected_aspects):
            bad.append(f"{nid}:verification_aspects欠落またはprefix不一致")
        if ac_aspects != expected_aspects:
            bad.append(f"{nid}:AC意味被覆差分={sorted(expected_aspects ^ ac_aspects)}")
        if tc_aspects != expected_aspects:
            bad.append(f"{nid}:TCC意味被覆差分={sorted(expected_aspects ^ tc_aspects)}")
        if tc_assertions != expected_aspects:
            bad.append(f"{nid}:TCC観点assert差分={sorted(expected_aspects ^ tc_assertions)}")
        method = nfr.get("measurement_method", "")
        if "loop_runs/tasks" in method or "NOT IN (終端)" in method:
            bad.append(f"{nid}:実行不能な擬似SQL")
        sqls = re.findall(r"SQL:`([^`]+)`", method)
        if method.count("SQL:") != len(sqls):
            bad.append(f"{nid}:SQLタグは実行文をbacktickで1文ずつ束縛する")
        inline_sqls = [code for code in re.findall(r"`([^`]+)`", method)
                       if re.match(r"\s*(?:SELECT|WITH)\b", code, re.IGNORECASE)]
        if len(inline_sqls) != len(sqls):
            bad.append(f"{nid}:SELECT/WITH契約SQLは全てSQLタグへ束縛する")
        for sql in sqls:
            if reason := _prepare_contract_sql(ddl, sql):
                bad.append(f"{nid}:契約SQLをprepare不能 ({reason})")
    return bad


def detect_media_semantic_faults(root: Path = ROOT) -> list[str]:
    """媒体要求の規範 text にある曖昧量・失効仕様と媒体内structure分岐を検出する。"""
    bad: list[str] = []
    targets = sorted((root / "docs/L1-business-requirements/canonical/br-media").glob("*.json"))
    targets += sorted((root / "docs/L3-system-requirements/canonical/functional/mr").glob("*.json"))
    for p in targets:
        if not p.exists() or p.stem == "index":
            continue
        data = load(p)
        structures = {(it.get("structure") or "").strip() for it in data.get("items", [])}
        if len(structures) != 1:
            bad.append(f"{p.name}:同一媒体内のstructureが分岐({len(structures)}種)")
        for item in data.get("items", []):
            item_id = item.get("id", "?")
            normative = item.get("text", "")
            for label, pattern in AMBIGUOUS_MEDIA_PATTERNS.items():
                if pattern.search(normative):
                    bad.append(f"{p.name}:{item_id}:判定不能な規範量『{label}』")
            full_item = "\n".join(str(v) for v in item.values())
            for phrase in STALE_MEDIA_FACTS:
                if phrase in full_item:
                    bad.append(f"{p.name}:{item_id}:失効表記『{phrase}』")
    return bad


# ---------------------------------------------------------------- ゲート本体
def run(ctx: Ctx) -> None:
    _json_syntax()
    _counts(ctx)
    _uniqueness(ctx)
    _substance(ctx)
    _br_contract(ctx)
    _frsr_contracts(ctx)
    _strategy(ctx)


def _json_syntax() -> None:
    bad = []
    for f in sorted(ROOT.glob("docs/**/*.json")):
        if is_frozen(f):
            continue
        try:
            load(f)
        except Exception as e:  # noqa: BLE001
            bad.append(f"{rel(f)}: {e}")
    gate("G-JSON", not bad, f"現役階層の全 JSON 構文妥当 {bad or ''}")


def _counts(ctx: Ctx) -> None:
    md_br = md_count(L1 / "canonical/br-backbone_v0.1.md", r"\*\*(BR-[A-Z]\d)\*\*")
    md_req = md_count(L1 / "canonical/requirement-list_v0.1.md", r"(REQ-\d{3})")
    gate("G-CNT-BR", len(ctx.br) == md_br, f"BR JSON↔MD 件数一致 (JSON={len(ctx.br)}, MD={md_br})")
    gate("G-CNT-REQ", len(ctx.req) == md_req, f"REQ JSON↔MD 件数一致 (JSON={len(ctx.req)}, MD={md_req})")
    # requirements.json / requirements_v0.1.md は旧 baseline の互換・再検証 view。
    # 現行分母として読むと、同一 ID の slice/trace が異なる旧意味を混入する。
    # その差分は G-REQ-SEMANTIC-DRIFT だけが監視し、通常の件数は
    # confirmed 契約 JSON のみを正本とする。
    gate("G-CNT-FR", len(ctx.frc) == 43, f"FR contract JSON=43 (JSON={len(ctx.frc)})")
    gate("G-CNT-NFR", len(ctx.nfc) == 11, f"NFR contract JSON=11 (JSON={len(ctx.nfc)})")
    md_fn = md_count(L3 / "canonical/functional/function-list_v0.1.md", r"\| (FN-\d{3}) \|")
    gate("G-CNT-FN", len(ctx.fn) == 61 == md_fn, f"FN=61 (MD={md_fn}/JSON={len(ctx.fn)})")

    bm = sum(len(load(p)["items"]) for p in sorted(BR_MEDIA_DIR.glob("*.json")) if p.stem != "index")
    md_bm = md_count(L1 / "canonical/br-media_v0.1.md", r"\*\*(BR-M-[A-Z]+-\d+)\*\*")
    gate("G-CNT-BRM", bm == 70 == md_bm, f"BR-M=70 (MD={md_bm}/JSON={bm})")
    mr = sum(len(load(p)["items"]) for p in sorted(MR_DIR.glob("*.json")) if p.stem != "index")
    gate("G-CNT-MR", mr == 54, f"MR=54 (JSON={mr})")
    wf = load(LTW_DIR / "workflows.json")["items"]
    gate("G-CNT-WF", len(wf) == 49, f"WF=49 (JSON={len(wf)})")

    cur = current_denominators(ctx)
    base = ROOT / "docs/00-authority/baselines/baseline.json"
    approved = load(base).get("contract_counts", {}) if base.exists() else {}
    minimums = {
        "AC_CONTRACT": approved.get("AC_CONTRACT", 218),
        "TCC": approved.get("TCC", 224),
        "API": approved.get("API", 58),
        "API_UT": approved.get("API_UT", 199),
    }
    count_ok = (cur["AC_CONTRACT"] >= minimums["AC_CONTRACT"]
                and cur["TCC"] >= minimums["TCC"]
                and cur["API"] == minimums["API"]
                and cur["API_UT"] == minimums["API_UT"])
    gate("G-CNT-CONTRACT", count_ok,
         "現行契約分母は AC/TCC の増加を許し、API/API_UT は設計正本と一致する"
         f"（縮小は baseline ratchet が拒否） (最小={minimums}, 実={cur})")

    hist_bad = detect_legacy_denominator_leaks()
    if base.exists():
        recorded = load(base).get("historical_counts", {})
        if recorded != HISTORICAL_COUNTS:
            hist_bad.append(f"baseline.historical_counts 不一致 {recorded}")
        if set(load(base).get("counts", {})) & {"AC", "UTC"}:
            hist_bad.append("baseline.counts に旧 AC/UTC 分母が残存")
    gate("G-HISTORICAL-COUNTS", not hist_bad,
         f"旧 AC19／TC59／UTC69 は historical_counts のみ（現役分母・現役文書に不在） (違反={hist_bad})")


def _uniqueness(ctx: Ctx) -> None:
    # requirements.json は旧compatibility viewであり、現行分母／実体の根拠にしない。
    for name, items in [("BR", ctx.brc), ("REQ", ctx.req),
                        ("FR", [*ctx.frc, *ctx.src, *ctx.nfc]), ("FN", ctx.fn)]:
        ids = [i["id"] for i in items]
        gate(f"G-UNIQ-{name}", len(ids) == len(set(ids)), f"{name} ID 重複ゼロ")


def _substance(ctx: Ctx) -> None:
    hollow = []
    for _, items in [("BR", ctx.brc), ("REQ", ctx.req),
                     ("FR/SR/NFR", [*ctx.frc, *ctx.src, *ctx.nfc]), ("FN", ctx.fn)]:
        for i in items:
            body = " ".join(filter(None, [
                i.get("title"), i.get("summary"), i.get("text"),
                i.get("purpose"), i.get("problem"), i.get("value"),
                str(i.get("normal_behavior", "")), str(i.get("measurement_target", "")),
            ]))
            if len(body.strip()) < 8:
                hollow.append(i["id"])
    for p in sorted(BR_MEDIA_DIR.glob("*.json")) + sorted(MR_DIR.glob("*.json")):
        if p.stem == "index":
            continue
        for i in load(p)["items"]:
            if len((i.get("text") or "").strip()) < 8:
                hollow.append(i["id"])
    media_semantic = detect_media_semantic_faults()
    gate("G-SUBSTANCE", not hollow and not media_semantic,
         f"全エンティティ本文実体があり媒体要求に曖昧量・失効済み仕様がない "
         f"(空={hollow}, 媒体意味={media_semantic[:5]})")

    today = datetime.date.today()
    stale = []
    for p in sorted(BR_MEDIA_DIR.glob("*.json")):
        if p.stem == "index":
            continue
        c = load(p).get("structure_checked")
        try:
            age = (today - datetime.date.fromisoformat(c)).days
            if age > MAX_SRC_AGE_DAYS or age < 0:
                stale.append(f"{p.name}:{c}")
        except (TypeError, ValueError):
            stale.append(f"{p.name}:missing")
    gate("G-SRC-FRESH", not stale, f"媒体構造の調査日が {MAX_SRC_AGE_DAYS} 日以内 (失効={stale})")

    poc = load(LTW_DIR / "poc.json")
    es = poc.get("exit_schema", {})
    badpoc = []
    for i in poc["items"]:
        do, ps = i.get("decision_outcome", "MISSING"), i.get("promotion_strategy", "MISSING")
        if do not in (es.get("decision_outcome", []) + [None]) or ps not in (es.get("promotion_strategy", []) + [None]):
            badpoc.append(f"{i['id']}:invalid({do},{ps})")
        elif do == "confirmed" and ps is None:
            badpoc.append(f"{i['id']}:confirmed-without-strategy")
    gate("G-POC-EXIT", bool(es) and not badpoc, f"PoC 出口 2 軸 schema 適合 (違反={badpoc})")


def _br_contract(ctx: Ctx) -> None:
    schema = load(BR_SCHEMA)
    errs: list[str] = []
    for it in ctx.brc:
        errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(schema, it)]
    req_ids = {i["id"] for i in ctx.req}
    covered = {g for it in ctx.brc for g in it["mandated_groups"]}
    bad_refs = [f"{it['id']}→{r}" for it in ctx.brc for r in it["trace_down"]["req"] if r not in req_ids]
    view_sync = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "scripts/render_views.py"), "--check"],
        capture_output=True, text=True, check=False).returncode == 0
    gate("G-REQ-CONTRACT",
         not errs and {it["id"] for it in ctx.brc} == {i["id"] for i in ctx.br}
         and covered == MANDATED_GROUPS and not bad_refs and view_sync,
         "BR 契約: schema 適合＋全 BR 被覆＋12 要求群被覆＋REQ 参照実在＋ビュー同期 "
         f"(schema={errs[:3]}, 群欠落={sorted(MANDATED_GROUPS - covered)}, REQ参照={bad_refs[:3]}, view={view_sync})")


def _frsr_contracts(ctx: Ctx) -> None:
    frc_schema = load(FR_SCHEMA)
    c_errs: list[str] = []
    for it in ctx.allc:
        c_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(frc_schema, it)]
    fr_ids = {i["id"] for i in ctx.frc}
    sr_ids = {i["id"] for i in ctx.src}
    cov_ok = len(fr_ids) == len(ctx.frc) and len(sr_ids) == len(ctx.src)
    tbl_faults = detect_contract_table_faults(ctx.allc, ctx.ddl_tables, ctx.trn_states)
    gate("G-FRSR-CONTRACT", not c_errs and cov_ok and not tbl_faults,
         f"FR/SR 契約正本: schema 適合＋ID一意＋DDL/遷移正本と突合（旧requirements viewを分母にしない） "
         f"(err={c_errs[:3]}, cov={cov_ok}, 突合={sorted(set(tbl_faults))[:5]})")

    n_errs: list[str] = []
    nfc_schema = load(NFR_SCHEMA)
    for it in ctx.nfc:
        n_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(nfc_schema, it)]
    nfr_ids = {i["id"] for i in ctx.nfc}
    nfr_verify_faults = detect_nfr_verification_faults(ctx.nfc, ctx.acc, ctx.tcc, ctx.ddl)
    gate("G-NFR-MEASURABLE",
         not n_errs and len(nfr_ids) == len(ctx.nfc) and not nfr_verify_faults,
         "NFR 契約正本: schema 適合＋ID一意＋NFR→AC→TCC実在ID接続＋実行可能な測定方法（旧requirements viewを分母にしない） "
         f"(err={n_errs[:3]}, 検証接続={nfr_verify_faults[:5]})")

    acc_schema = load(AC_SCHEMA)
    a_errs: list[str] = []
    for it in ctx.acc:
        a_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(acc_schema, it)]
    ac_ids = [a["id"] for a in ctx.acc]
    dup_ac = len(ac_ids) != len(set(ac_ids))
    valid_targets = fr_ids | sr_ids | nfr_ids | {i["id"] for i in ctx.nfc}
    orphan = [a["id"] for a in ctx.acc if a["target"] not in valid_targets]
    by_tgt: dict[str, list] = {}
    for a in ctx.acc:
        by_tgt.setdefault(a["target"], []).append(a)
    s0_no_ac = [c["id"] for c in ctx.allc if c["slice"] == "S0" and not by_tgt.get(c["id"])]
    gate("G-AC-COVERAGE", not a_errs and not dup_ac and not orphan and not s0_no_ac,
         f"AC 検証契約: schema 適合＋ID 一意＋target 実在＋S0 要件の AC 実在 "
         f"(err={a_errs[:3]}, dup={dup_ac}, orphan={orphan[:3]}, S0欠落={s0_no_ac})")

    pol_bad = detect_polarity_gaps(ctx.allc, ctx.acc)
    gate("G-AC-POLARITY", not pol_bad, f"S0 要件の 3 極性被覆（AC or 理由付き N/A） (欠落={pol_bad[:5]})")

    hj_bad = [c["id"] for c in ctx.allc
              if not (c["human_judgement"].startswith("なし")
                      or any(k in c["human_judgement"] for k in ("PO", "人間", "運用者", "承認")))]
    gate("G-HUMAN-JUDGE", not hj_bad, f"人間判断点の明示（なし宣言 or 主体特定） (不明={hj_bad[:5]})")

    inv_bad = detect_invariant_gaps(ctx.allc, ctx.acc)
    gate("G-INVARIANT-TRACE", not inv_bad,
         f"S0 の各不変条件に固有の負方向 AC（invariant_ac_map 個別対応） (欠落={inv_bad[:5]})")

    nogwt = [a["id"] for a in ctx.acc if not (a.get("given") and a.get("when") and a.get("then"))]
    gate("G-GWT", not nogwt, f"AC 契約全件に非空 Given/When/Then (欠落={nogwt[:5]})")

    rej = [t for t in ctx.tcc if t.get("kind") == "reject"]
    gate("G-TC-REJECT", len(rej) >= 7,
         f"fail-close 拒否系 TC >=7（拒否経路の検証が実在する） (実={len(rej)})")

    slices = {"S0", "S1", "S2", "S3+"}
    badslice = [t["id"] for t in ctx.tcc if t.get("slice") not in slices]
    s0_tc = [t for t in ctx.tcc if t.get("slice") == "S0"]
    noac = [t["id"] for t in s0_tc if not t.get("ac")]
    gate("G-TC-SLICE", not badslice and bool(s0_tc) and not noac,
         f"全 TC が既知スライス語彙に属し S0 の TC が実在して AC を参照する "
         f"(不明slice={badslice[:3]}, S0={len(s0_tc)}, AC無={noac[:3]})")

    wf_ids = {w["id"] for w in load(LTW_DIR / "workflows.json")["items"]}
    wfc = load(WF_CONTRACTS)["items"]
    unknown_wf = sorted({w["workflow"] for w in wfc if w["workflow"] not in wf_ids})
    nostep = [w["workflow"] for w in wfc if not w.get("steps")]
    gate("G-WF-CONTRACT", not unknown_wf and not nostep,
         f"WF 実行契約の対象が WF 台帳に実在し全件に step 定義がある "
         f"(不明WF={unknown_wf[:5]}, step欠={nostep[:3]})")

    env_faults = environment_contract_faults()
    gate(
        "G-ENV-CONTRACT",
        not env_faults,
        "旧S0環境fixtureをrevalidation_required・implementation_input=falseへ隔離し、"
        "Docker WP/Discord旧tupleを現行write・通知authorityとして扱わない"
        f" (違反={env_faults})",
    )


# ---------------------------------------------------------------- 上流戦略ループ
def _strategy(ctx: Ctx) -> None:
    from tools.gates.architecture import strategy_mutation_rejected

    missing = [n for n in STRATEGY_SCHEMAS if not (STRATEGY_SCHEMA_DIR / f"{n}.schema.json").exists()]
    if missing:
        for gid in STRAT_GATES + ["G-STRAT-PAIR"]:
            gate(gid, False, f"戦略 schema 欠落: {missing}")
        return

    sch = {n: load(STRATEGY_SCHEMA_DIR / f"{n}.schema.json") for n in STRATEGY_SCHEMAS}
    ddl = ctx.ddl
    s0md = (L3 / "canonical/s0-contract_v0.1.md").read_text(encoding="utf-8")

    def fx(name: str, fixture: str) -> list[str]:
        return schema_check(sch[name], load(FIXTURES / fixture))

    breq = set(sch["strategic-brief"]["required"])
    need_b = {"id", "version", "strategic_choice_id", "segment_context_id", "value_hypothesis_id",
              "desired_recognition_change", "tactical_objective", "media_role", "message_hypothesis",
              "prohibited_patterns", "measurement_plan", "valid_from", "digest"}
    tguard = next((t.get("guard", "") for t in ctx.transitions
                   if t["entity"] == "loop_runs" and t["from"] == "pending" and t["event"] == "start"), "")
    gate("G-STRAT-BRIEF",
         need_b <= breq and not fx("strategic-brief", "strategic-brief.valid.json")
         and "strategic_brief_id" in ddl and "strategic_brief_digest" in ddl
         and "loop_kind != 'lower'" in ddl and "strategic_brief" in tguard,
         f"brief 契約完全＋DDL 保持列＋下位開始ガードが brief を要求 (必須欠落={sorted(need_b - breq)})")

    def chain_check(s: dict) -> bool:
        return (
            {"strategic_choice_id", "segment_context_id", "value_hypothesis_id"} <= set(s["strategic-brief"]["required"])
            and {"selected_segment_ids", "value_hypothesis_ids", "decision_basis"} <= set(s["strategic-choice"]["required"])
            and {"segment_context_id", "problem_model_id", "evidence_ids"} <= set(s["value-hypothesis"]["required"])
            and {"market_model_id", "evidence_ids"} <= set(s["segment-context"]["required"])
            and {"loop_run_id", "strategic_brief_id"} <= set(s["tactical-learning-packet"]["required"])
        )

    mut = copy.deepcopy(sch)
    mut["strategic-brief"]["required"].remove("value_hypothesis_id")
    gate("G-STRAT-TRACE",
         chain_check(sch) and not chain_check(mut)
         and bool(fx("strategic-brief", "strategic-brief.no-trace.invalid.json")),
         "run→brief→choice→VH→SEG→evidence の trace 必須＋trace 欠落 fixture 拒否＋変異 schema の検出自己検査")

    sreq = set(sch["segment-context"]["required"])
    sprops = sch["segment-context"]["properties"]
    ctx_ok = ({"time_context", "space_context", "constraints", "progress_state",
               "alternative_behaviors", "decision_conditions"} <= sreq
              and all(sprops[k].get("minItems", 0) >= 1
                      for k in ("time_context", "space_context", "constraints", "alternative_behaviors"))
              and sprops["progress_state"].get("minLength", 0) >= 1
              and "demographic_attributes" not in sreq)
    gate("G-SEGMENT-CONTEXT",
         ctx_ok and not fx("segment-context", "segment-context.valid.json")
         and bool(fx("segment-context", "segment-context.demographic-only.invalid.json")),
         "状況ベースセグメント必須＋人口統計のみ fixture を拒否")

    oprops = sch["market-observation"]["properties"]
    treq = set(sch["tactical-learning-packet"]["required"])
    tprops = sch["tactical-learning-packet"]["properties"]

    def tlp_kind_rule(doc: dict) -> bool:
        if doc.get("packet_kind") == "learning":
            return all(k in doc for k in ("causal_interpretation", "hypothesis_assessment"))
        if doc.get("packet_kind") == "failure":
            return (all(k in doc for k in ("failure_fact", "reproduction_conditions", "recovery_conditions"))
                    and "causal_interpretation" not in doc)
        return False

    tlp_v = load(FIXTURES / "tactical-learning-packet.valid.json")
    tlp_f = load(FIXTURES / "tactical-learning-packet.failure.valid.json")
    tlp_fc = load(FIXTURES / "tactical-learning-packet.failure-with-causal.invalid.json")
    gate("G-OBS-INTERPRETATION",
         sch["market-observation"].get("additionalProperties") is False
         and "fact" in sch["market-observation"]["required"]
         and not any("interpret" in k for k in oprops)
         and {"observations", "packet_kind", "recommended_next_action"} <= treq
         and {"causal_interpretation", "hypothesis_assessment", "alternative_explanations",
              "failure_fact", "reproduction_conditions", "recovery_conditions"} <= set(tprops)
         and not fx("market-observation", "market-observation.valid.json")
         and bool(fx("market-observation", "market-observation.mixed-interpretation.invalid.json"))
         and tlp_kind_rule(tlp_v) and tlp_kind_rule(tlp_f) and not tlp_kind_rule(tlp_fc),
         "観測/解釈の分離＋learning/failure packet 二分（failure への因果解釈捏造 fixture を拒否）")

    gate("G-LEARNING-TRACE",
         {"loop_run_id", "strategic_brief_id", "strategic_brief_digest", "evidence_ids"} <= treq
         and tprops["evidence_ids"].get("minItems", 0) >= 1
         and not fx("tactical-learning-packet", "tactical-learning-packet.valid.json")
         and not fx("tactical-learning-packet", "tactical-learning-packet.failure.valid.json")
         and bool(fx("tactical-learning-packet", "tactical-learning-packet.unlinked.invalid.json"))
         and "UNIQUE" in ddl.split("CREATE TABLE tactical_learning_packets")[1].split(");")[0]
         and "tactical_learning_packets_integrity" in ddl
         and "同一 transaction で tactical_learning_packet の" in s0md
         and "packet を持たない終端 lower run = 0 件" in s0md,
         "TLP の接続＋UNIQUE＋整合トリガ＋最低 1 件の kernel 契約/孤児検査宣言＋未接続 fixture を拒否")

    mrej, mmsg = strategy_mutation_rejected(ddl)
    gate("G-NO-DIRECT-STRATEGY-MUTATION",
         mrej and "上流戦略正本" in s0md
         and "下流ループ・媒体コネクタ・計測処理は上流戦略正本へ書き込めず" in s0md,
         f"上流正本への UPDATE/DELETE を実 DML で拒否実証（{mmsg}）＋直接更新禁止宣言")

    rreq = set(sch["strategy-revision"]["required"])

    def rev_rule(doc: dict) -> bool:
        if doc.get("status") != "accepted":
            return True
        if len(set(doc.get("supporting_evidence_ids", []))) < 2:
            return False
        if doc.get("revision_type") != "maintain" and not doc.get("new_version_id"):
            return False
        return True

    vr = load(FIXTURES / "strategy-revision.valid.json")
    ir = load(FIXTURES / "strategy-revision.single-metric-accept.invalid.json")
    dr = load(FIXTURES / "strategy-revision.duplicate-evidence.invalid.json")
    gate("G-REVISION-EVIDENCE",
         {"supporting_evidence_ids", "counter_evidence_ids", "confidence", "target_version"} <= rreq
         and sch["strategy-revision"]["properties"]["supporting_evidence_ids"].get("uniqueItems") is True
         and not schema_check(sch["strategy-revision"], vr) and rev_rule(vr)
         and not rev_rule(ir) and not rev_rule(dr),
         "revision の根拠/反証/信頼度/対象版＋accepted の新版必須＋単一根拠・重複根拠 accept fixture を拒否")

    VERSIONED = ["market-model", "segment-context", "problem-model", "value-hypothesis",
                 "category-definition", "positioning-hypothesis", "causal-assumption",
                 "strategic-choice", "strategic-brief"]

    def unversioned(s: dict) -> list[str]:
        return [n for n in VERSIONED
                if "version" not in s[n]["required"] or "supersedes_id" not in s[n]["properties"]]

    mut2 = copy.deepcopy(sch)
    mut2["value-hypothesis"]["required"].remove("version")
    gate("G-STRATEGY-VERSION",
         not unversioned(sch) and bool(unversioned(mut2)) and mrej and "supersedes_id INTEGER" in ddl,
         f"全上流モデルが version 必須＋supersedes_id 定義（変異検出自己検査込み）"
         f"＋DDL append-only を実 DML で実証 (欠落={unversioned(sch)})")

    roles_doc = load(STRATEGY_DIR / "media-roles.json")
    roles = {r["role"] for r in roles_doc.get("roles", [])}
    vb = load(FIXTURES / "strategic-brief.valid.json")
    bb = load(FIXTURES / "strategic-brief.bad-media-role.invalid.json")
    gate("G-MEDIA-ROLE",
         len(roles) >= 12 and {"media_role", "desired_recognition_change"} <= breq
         and vb["media_role"] in roles and bb["media_role"] not in roles,
         f"役割台帳 >=12 語彙＋brief の役割/認識変化必須＋台帳外役割 fixture を拒否 (roles={len(roles)})")

    cpc = load(STRATEGY_DIR / "content-plan-contract.json")
    ckeys = {k["key"] for k in cpc.get("required_keys", [])}
    need_c = {"defined_problem", "recognition_change", "comparison_axes", "defined_value",
              "target_hypothesis_ids"}
    vp = load(FIXTURES / "content-plan.valid.json")
    ip = load(FIXTURES / "content-plan.missing-recognition.invalid.json")
    gate("G-CONTENT-VALUE-DEFINITION",
         ckeys == need_c and need_c <= set(vp) and not (need_c <= set(ip)),
         f"コンテンツ企画 5 宣言契約＋宣言欠落 fixture を拒否 (契約差分={sorted(ckeys ^ need_c)})")

    _strategy_pair(ctx, sch)


def _strategy_pair(ctx: Ctx, sch: dict) -> None:
    sr_md = md_count(STRATEGY_REQ, r"\*\*(SR-\d{2})")
    stc = ctx.stc
    sr_ids = {i["id"] for i in ctx.sr}
    cov_sr = {s for it in stc["items"] for s in it.get("sr", [])}
    cov_scm = {c for it in stc["items"] for c in it.get("scm", [])}
    neg = {it.get("gate") for it in stc["items"]
           if it.get("kind") == "gate" and it.get("polarity") == "reject"}
    heads = {p: p.read_text(encoding="utf-8")[:900]
             for p in (STRATEGY_REQ, STRATEGY_LEARNING, STRATEGY_DESIGN, STRATEGY_TEST_DESIGN)}
    pair_ok = (all("pair:" in h for h in heads.values())
               and all("strategy-loop-test-design" in heads[p]
                       for p in (STRATEGY_REQ, STRATEGY_LEARNING, STRATEGY_DESIGN))
               and "strategy-loop-design" in heads[STRATEGY_TEST_DESIGN])
    missing_fx = [it["fixture"] for it in stc["items"]
                  if it.get("fixture") and not (ROOT / it["fixture"]).exists()]
    stc_mut = [dict(it, sr=[s for s in it.get("sr", []) if s != "SR-04"]) for it in stc["items"]]
    mut_detects = sr_ids != {s for it in stc_mut for s in it.get("sr", [])}
    acsr = load(STRATEGY_DIR / "ac-sr.json")["items"]
    stc_ids = {it["id"] for it in stc["items"]}
    du_ids = {d["id"] for d in ctx.dus}
    acsr_ok = (len(acsr) == 6
               and all(a.get("given") and a.get("when") and a.get("then") for a in acsr)
               and all(set(a["sr"]) <= sr_ids and set(a["stc"]) <= stc_ids
                       and set(a["du"]) <= du_ids for a in acsr)
               and {x for a in acsr for x in a["stc"]} == {f"STC-I-0{i}" for i in range(1, 7)})
    gate("G-STRAT-PAIR",
         mut_detects and acsr_ok and len(ctx.sr) == 19 == sr_md and len(ctx.scm) == 10 and pair_ok
         and sr_ids == cov_sr and {c["id"] for c in ctx.scm} == cov_scm
         and all(g in neg for g in STRAT_GATES) and not missing_fx,
         f"旧戦略資料の構造検査のみ: SR19/SCM10/AC-SR6 双方向カバー＋4 文書相互 pair＋全戦略ゲートに拒否系 STC。"
         f"現要求の受入権威・実装可否はG-REQ-STRATEGY-TEST-AUTHORITYで別判定 "
         f"(SR差={sorted(sr_ids ^ cov_sr)}, AC-SR={acsr_ok}, negative欠={sorted(set(STRAT_GATES) - neg)}, "
         f"fixture欠={missing_fx})")
