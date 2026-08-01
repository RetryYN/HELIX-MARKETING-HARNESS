"""トレーサビリティゲート: AC↔TC の双方向、BR→…→UT の全区間突合、粒度ゲートの mutation 自己検査。"""

from __future__ import annotations

from tools.gates.architecture import detect_unknown_tables
from tools.gates.common import (
    DU_SCHEMA,
    TC_SCHEMA,
    Ctx,
    gate,
    load,
    schema_check,
    ut_nodeids,
)
from tools.gates.detailed_design import detect_api_ut_faults
from tools.gates.requirements import detect_invariant_gaps, detect_polarity_gaps


def detect_tc_bidir_faults(tcs: list[dict], acs: list[dict]) -> list[str]:
    """TC の AC 参照が実在しない箇所を列挙する。"""
    ids = {a["id"] for a in acs}
    return [f"{t['id']}→{a}" for t in tcs for a in t["ac"] if a not in ids]


def detect_chain_asymmetry(brc: list[dict], req: list[dict], allc: list[dict],
                           acc: list[dict], cmpc: list[dict], duc: list[dict],
                           tcc: list[dict] | None = None) -> list[str]:
    """BR→REQ→FR/SR→AC→TC→CMP→DU→API→UT の全区間で非対称エッジを列挙する。"""
    import re

    bad: list[str] = []
    up = {r["id"]: set(r["trace"]["upstream"]) for r in req}
    down = {r["id"]: set(r["trace"]["downstream"]) | set(r.get("related", [])) for r in req}
    for it in brc:
        for r in it["trace_down"]["req"]:
            if it["id"] not in up.get(r, set()):
                bad.append(f"BR→REQ:{it['id']}→{r}")
    br_edges = {(b["id"], r) for b in brc for r in b["trace_down"]["req"]}
    for r in req:
        for b in r["trace"]["upstream"]:
            if re.fullmatch(r"BR-[A-Z]\d", b) and (b, r["id"]) not in br_edges:
                bad.append(f"REQ→BR:{r['id']}→{b}")
    frsr_up = {c["id"]: {t for t in c["trace_up"] if t.startswith("REQ-")} for c in allc}
    for r in req:
        for f in down[r["id"]]:
            if f in frsr_up and r["id"] not in frsr_up[f]:
                bad.append(f"REQ→FRSR:{r['id']}→{f}")
    for c in allc:
        for r in frsr_up[c["id"]]:
            if c["id"] not in down.get(r, set()):
                bad.append(f"FRSR→REQ:{c['id']}→{r}")
    ac_by_t: dict[str, set] = {}
    for a in acc:
        ac_by_t.setdefault(a["target"], set()).add(a["id"])
    for c in allc:
        if set(c["trace_down"]["ac"]) != ac_by_t.get(c["id"], set()):
            bad.append(f"FRSR↔AC:{c['id']}")
    cmp_du = {c["id"]: set(c["trace"]["du"]) for c in cmpc}
    du_cmp: dict[str, set] = {}
    for d in duc:
        for cid in [d["cmp"], *d.get("also_implements", [])]:
            du_cmp.setdefault(cid, set()).add(d["id"])
    for cid in set(cmp_du) | set(du_cmp):
        if cmp_du.get(cid, set()) != du_cmp.get(cid, set()):
            diff = sorted(cmp_du.get(cid, set()) ^ du_cmp.get(cid, set()))
            bad.append(f"CMP↔DU:{cid}:{diff}")
    cmp_by_id = {c["id"]: c for c in cmpc}
    for c in allc:
        if not c["trace_down"].get("cmp"):
            bad.append(f"FRSR→CMP:{c['id']}:CMP未接続")
        for cid in c["trace_down"].get("cmp", []):
            if cid not in cmp_by_id:
                bad.append(f"FRSR→CMP:{c['id']}→{cid}:不在")
            else:
                fns = set(c["trace_down"].get("fn", []))
                if fns and not fns <= set(cmp_by_id[cid]["trace"]["fn"]):
                    bad.append(f"FRSR→CMP:{c['id']}→{cid}:FN未被覆"
                               f"{sorted(fns - set(cmp_by_id[cid]['trace']['fn']))}")
    if tcc is not None:
        tc_ids = {t["id"] for t in tcc}
        du_tcs = {t for d in duc for t in d["trace"]["tc"]}
        for d in duc:
            for t in d["trace"]["tc"]:
                if t.startswith("TCC-") and t not in tc_ids:
                    bad.append(f"DU→TC:{d['id']}→{t}:不在")
        s0_t = {c["id"] for c in allc if c["slice"] == "S0"}
        s0_ac = {a["id"] for a in acc if a["target"] in s0_t}
        for t in tcc:
            if t["slice"] == "S0" and set(t["ac"]) & s0_ac and t["id"] not in du_tcs:
                bad.append(f"TC→DU:{t['id']}:未割当")
    for d in duc:
        api_ut = {u for a in d["apis"] for u in ut_nodeids(a)}
        if api_ut != set(d["trace"]["ut"]):
            bad.append(f"DU↔API-UT:{d['id']}:{sorted(api_ut ^ set(d['trace']['ut']))[:2]}")
    return bad


def detect_orphan_s0_ac(allc: list[dict], acc: list[dict], duc: list[dict]) -> list[str]:
    """S0 対象でどの DU にも割当てられていない AC を列挙する。"""
    du_acs = {a for d in duc for a in d["trace"]["ac"]}
    s0_t = {c["id"] for c in allc if c["slice"] == "S0"}
    return sorted(a["id"] for a in acc if a["target"] in s0_t and a["id"] not in du_acs)


def run(ctx: Ctx) -> None:
    _ac_tc(ctx)
    _chain(ctx)
    _selftest(ctx)


def _ac_tc(ctx: Ctx) -> None:
    tcc_schema = load(TC_SCHEMA)
    t_errs: list[str] = []
    for it in ctx.tcc:
        t_errs += [f"{it.get('id', '?')}: {e}" for e in schema_check(tcc_schema, it)]
    tcc_ids = {t["id"] for t in ctx.tcc}
    dangling_tc = detect_tc_bidir_faults(ctx.tcc, ctx.acc)
    tcc_by_ac: dict[str, set] = {}
    for t in ctx.tcc:
        for a in t["ac"]:
            tcc_by_ac.setdefault(a, set()).add(t["id"])
    ac_no_tc = [a["id"] for a in ctx.acc if not a["tc"]]
    bidir_bad = []
    for a in ctx.acc:
        listed = {r for r in a["tc"] if r.startswith("TCC-")}
        actual = tcc_by_ac.get(a["id"], set())
        if listed != actual:
            bidir_bad.append(f"{a['id']}:{sorted(listed ^ actual)}")
    dangling_ref = [f"{a['id']}→{r}" for a in ctx.acc for r in a["tc"]
                    if r.startswith("TCC-") and r not in tcc_ids]
    gate("G-TRACE-BIDIR",
         not t_errs and not dangling_tc and not ac_no_tc and not bidir_bad and not dangling_ref,
         f"AC↔TC 双方向接続 (schema={t_errs[:3]}, TC→AC欠={dangling_tc[:3]}, "
         f"AC無TC={ac_no_tc[:3]}, 非対称={bidir_bad[:3]}, AC→TC欠={dangling_ref[:3]})")


def _chain(ctx: Ctx) -> None:
    chain_bad = detect_chain_asymmetry(ctx.brc, ctx.req, ctx.allc, ctx.acc, ctx.cmpc, ctx.duc, ctx.tcc)
    orphan = detect_orphan_s0_ac(ctx.allc, ctx.acc, ctx.duc)
    gate("G-CHAIN-BIDIR", not chain_bad and not orphan,
         f"全層 trace の双方向突合 (非対称={sorted(set(chain_bad))[:6]}, DU未割当S0AC={orphan[:5]})")


def _selftest(ctx: Ctx) -> None:
    """本番ゲートが使う**検出関数そのもの**へ変異データを投入し、検出能力を毎回証明する。"""
    ok, msg = True, []
    duc_schema = load(DU_SCHEMA)
    try:
        victim = next(c for c in ctx.allc if c["slice"] == "S0"
                      and any(a["target"] == c["id"] and a["polarity"] == "reject" for a in ctx.acc))
        mut_acc = [a for a in ctx.acc
                   if not (a["target"] == victim["id"] and a["polarity"] == "reject")]
        if not detect_polarity_gaps([victim], mut_acc):
            ok = False
            msg.append("polarity-mutation 未検出")

        mut_api = {**ctx.duc[0]["apis"][0], "precondition": []}
        if not schema_check(duc_schema["properties"]["apis"]["items"], mut_api):
            ok = False
            msg.append("dbc-mutation 未検出")

        mut_du = {**ctx.duc[0], "db_read": [*ctx.duc[0]["db_read"], "ghost_table_xyz"]}
        if "ghost_table_xyz" not in " ".join(detect_unknown_tables([mut_du], ctx.ddl_tables)):
            ok = False
            msg.append("data-mutation 未検出")

        mut_tc = {**ctx.tcc[0], "ac": ["AC-99-9"]}
        if not detect_tc_bidir_faults([mut_tc], ctx.acc):
            ok = False
            msg.append("bidir-mutation 未検出")

        mut_br = [{**ctx.brc[0], "trace_down": {**ctx.brc[0]["trace_down"],
                                                "req": [*ctx.brc[0]["trace_down"]["req"], "REQ-052"]}},
                  *ctx.brc[1:]]
        if not detect_chain_asymmetry(mut_br, ctx.req, ctx.allc, ctx.acc, ctx.cmpc, ctx.duc, ctx.tcc):
            ok = False
            msg.append("chain-mutation 未検出")

        mut_duc = [{k: v for k, v in d.items() if k != "also_implements"} for d in ctx.duc]
        if not detect_chain_asymmetry(ctx.brc, ctx.req, ctx.allc, ctx.acc, ctx.cmpc, mut_duc, ctx.tcc):
            ok = False
            msg.append("cmp-du-mutation 未検出")

        inv_victim = next((c for c in ctx.allc if c["slice"] == "S0" and c.get("invariant_ac_map")), None)
        if inv_victim is not None:
            normal_ac = next((a["id"] for a in ctx.acc
                              if a["target"] == inv_victim["id"] and a["polarity"] == "normal"), None)
            if normal_ac:
                mut_c = {**inv_victim,
                         "invariant_ac_map": [[normal_ac], *inv_victim["invariant_ac_map"][1:]]}
                if not detect_invariant_gaps([mut_c], ctx.acc):
                    ok = False
                    msg.append("invariant-mutation 未検出")

        mut_du2 = {**ctx.duc[0], "apis": [{**ctx.duc[0]["apis"][0], "ut": []}, *ctx.duc[0]["apis"][1:]]}
        if not detect_api_ut_faults([mut_du2]):
            ok = False
            msg.append("api-ut-mutation 未検出")
    except (IndexError, StopIteration, KeyError) as e:
        ok = False
        msg.append(f"自己検査を実行できない: {e}")
    gate("G-DESCENT-SELFTEST", ok, f"再降下ゲートの mutation 自己検査 (失敗={msg})")
