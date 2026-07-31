"""詳細設計層ゲート: DU 台帳・API 実装契約・DbC・エラー型・DB 参照・API 単位 UT・空洞禁止。"""

from __future__ import annotations

import re
from pathlib import Path

from tools.gates.architecture import detect_unknown_tables
from tools.gates.common import (
    AC_CONTRACTS,
    BR_CONTRACTS,
    CMP_CONTRACTS,
    DU_CONTRACTS,
    DU_SCHEMA,
    ERROR_TAXONOMY,
    FR_CONTRACTS,
    NFR_CONTRACTS,
    SR_CONTRACTS,
    TC_CONTRACTS,
    TESTS_UNIT,
    Ctx,
    gate,
    load,
    schema_check,
)

HOLLOW = re.compile(r"TBD|TODO|FIXME|後で書く|後で埋め|後述予定|要検討|仮置き|placeholder|XXX")


def detect_api_ut_faults(dus: list[dict], tests_dir: Path = TESTS_UNIT) -> list[str]:
    """API 単位の UT 割当・参照実在・設計リンクの欠陥を列挙する。"""
    bad: list[str] = []
    for d in dus:
        uts = set(d["trace"]["ut"])
        api_uts: set[str] = set()
        for a in d["apis"]:
            refs = a.get("ut") or []
            if not refs:
                bad.append(f"{d['id']}:{a['signature'][:28]}:UTなし")
                continue
            api_uts |= set(refs)
            if not set(refs) <= uts:
                bad.append(f"{d['id']}:{a['signature'][:28]}:trace外UT")
        if uts - api_uts:
            bad.append(f"{d['id']}:宙吊りUT{sorted(uts - api_uts)[:2]}")
        owner_apis: dict[str, set] = {}
        for a in d["apis"]:
            m0 = re.match(r"def (\w+)", a["signature"])
            if m0:
                for u in a.get("ut", []):
                    owner_apis.setdefault(u, set()).add(m0.group(1))
        for ref in sorted(uts):
            if "::" not in ref:
                bad.append(f"{d['id']}:{ref}:形式")
                continue
            fname, tname = ref.split("::", 1)
            fp = tests_dir / fname
            if not fp.exists():
                bad.append(f"{d['id']}:{ref}:ファイル不在")
                continue
            txt = fp.read_text(encoding="utf-8")
            m = re.search(rf"\ndef {re.escape(tname)}\b", txt)
            if m is None:
                bad.append(f"{d['id']}:{ref}:def 不在")
                continue
            head = txt[:m.start()]
            decos = head[head.rfind("\n\n"):]
            body = txt[m.start():][:600]
            if "skip" in decos or "NotImplementedError" in body:
                owners = owner_apis.get(ref, set())
                if d["id"] not in decos or not (owners and any(n in decos for n in owners)):
                    bad.append(f"{d['id']}:{ref}:設計リンク不備")
    return bad


def run(ctx: Ctx) -> None:
    _ledger(ctx)
    _contracts(ctx)


def _ledger(ctx: Ctx) -> None:
    dus = ctx.dus
    duids = [d["id"] for d in dus]
    cmpids = {c["id"] for c in ctx.comps}
    gate("G-DU-CNT", len(dus) == 23, f"DU=23 (実={len(dus)})")
    gate("G-DU-UNIQ", len(duids) == len(set(duids)), "DU ID 重複ゼロ")
    ducmp = {d["cmp"] for d in dus}
    dufn = [f for d in dus for f in d["fn_ids"]]
    gate("G-DU-CMP", ducmp == cmpids,
         f"DU↔CMP 双方向 (不明={sorted(ducmp - cmpids)}, 未カバー={sorted(cmpids - ducmp)})")
    gate("G-DU-FN", len(dufn) == len(set(dufn)) and set(dufn) == ctx.s0_fn,
         f"DU が S0 25 FN を重複なく完全被覆 (差分={sorted(set(dufn) ^ ctx.s0_fn)})")


def _contracts(ctx: Ctx) -> None:
    duc = ctx.duc
    schema = load(DU_SCHEMA)
    ledger = {i["id"]: i for i in ctx.dus}
    d_errs: list[str] = []
    for it in duc:
        d_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(schema, it)]
    duc_ids = {i["id"] for i in duc}
    mod_bad = [it["id"] for it in duc
               if it["id"] in ledger and ledger[it["id"]]["module"] != it["module"]]
    gate("G-DU-API", not d_errs and duc_ids == set(ledger) and not mod_bad,
         f"DU 実装契約: schema 適合＋DU23 被覆＋module 一致 "
         f"(err={d_errs[:3]}, 差={sorted(duc_ids ^ set(ledger))}, module={mod_bad})")

    dbc_bad = [f"{it['id']}:{a['signature'][:30]}" for it in duc for a in it["apis"]
               if not a["precondition"] or not a["postcondition"]]
    gate("G-DU-DBC", not dbc_bad, f"全公開 API に pre/post (欠落={dbc_bad[:3]})")

    taxonomy = ERROR_TAXONOMY.read_text(encoding="utf-8")
    unknown_err = sorted({r["type"] for it in duc for a in it["apis"] for r in a["raises"]
                          if r["type"].split("（")[0] not in taxonomy})
    gate("G-DU-ERROR", not unknown_err, f"raises 型がエラー分類正本に掲載 (未掲載={unknown_err[:5]})")

    tbl_bad = detect_unknown_tables(duc, ctx.ddl_tables)
    gate("G-DU-DATA", not tbl_bad, f"DU の DB read/write が DDL 実在テーブルのみ (未知={tbl_bad[:5]})")

    ut_faults = detect_api_ut_faults(duc)
    gate("G-API-UT", not ut_faults,
         "全 DU の API 単位 UT 割当・参照実在・設計リンク（実行検証は S0.1 で red→green） "
         f"(欠陥={ut_faults[:5]})")

    hollow_hits: list[str] = []
    for p in (BR_CONTRACTS, FR_CONTRACTS, SR_CONTRACTS, AC_CONTRACTS, NFR_CONTRACTS,
              TC_CONTRACTS, CMP_CONTRACTS, DU_CONTRACTS):
        txt = p.read_text(encoding="utf-8")
        for m in HOLLOW.finditer(txt):
            hollow_hits.append(f"{p.name}:{m.group(0)}")
    gate("G-NO-HOLLOW-DESIGN", not hollow_hits,
         f"契約正本にプレースホルダなし (検出={sorted(set(hollow_hits))[:5]})")
