"""traceability ゲートの単体テストと mutation test。"""

from tools.gates import traceability
from tools.gates.common import CTX


def test_chain_is_bidirectional_on_real_contracts() -> None:
    assert traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, CTX.allc, CTX.acc, CTX.cmpc, CTX.duc, CTX.tcc) == []
    assert traceability.detect_orphan_s0_ac(CTX.allc, CTX.acc, CTX.duc) == []


def test_requirements_defined_s1_may_defer_cmp_but_s0_may_not() -> None:
    deferred = next(c for c in CTX.allc if c["id"] == "FR-17")
    assert deferred["slice"] == "S1" and deferred["design_status"] == "requirements_defined"
    assert not deferred["trace_down"].get("cmp")
    promoted = [{**c, "slice": "S0"} if c["id"] == "FR-17" else c for c in CTX.allc]
    faults = traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, promoted, CTX.acc, CTX.cmpc, CTX.duc, CTX.tcc)
    assert "FRSR-DESIGN-STATUS:FR-17:requirements_defined宣言不整合" in faults


def test_mutation_removing_cmp_from_existing_s1_is_detected() -> None:
    victim = next(c for c in CTX.allc if c["slice"] == "S1" and c["trace_down"].get("cmp"))
    mutated = [
        {**c, "trace_down": {**c["trace_down"], "fn": [], "cmp": []}}
        if c["id"] == victim["id"] else c
        for c in CTX.allc
    ]
    faults = traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, mutated, CTX.acc, CTX.cmpc, CTX.duc, CTX.tcc)
    assert f"FRSR→CMP:{victim['id']}:CMP未接続" in faults


def test_mutation_one_way_br_req_edge_is_detected() -> None:
    mutated = [{**CTX.brc[0],
                "trace_down": {**CTX.brc[0]["trace_down"],
                               "req": [*CTX.brc[0]["trace_down"]["req"], "REQ-052"]}},
               *CTX.brc[1:]]
    assert traceability.detect_chain_asymmetry(
        mutated, CTX.req, CTX.allc, CTX.acc, CTX.cmpc, CTX.duc, CTX.tcc)


def test_mutation_stripping_also_implements_breaks_cmp_du_equality() -> None:
    mutated = [{k: v for k, v in d.items() if k != "also_implements"} for d in CTX.duc]
    faults = traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, CTX.allc, CTX.acc, CTX.cmpc, mutated, CTX.tcc)
    assert any(f.startswith("CMP↔DU") for f in faults)


def test_mutation_api_ut_divergence_is_detected() -> None:
    victim = {**CTX.duc[0], "trace": {**CTX.duc[0]["trace"], "ut": []}}
    faults = traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, CTX.allc, CTX.acc, CTX.cmpc, [victim, *CTX.duc[1:]], CTX.tcc)
    assert any("DU↔API-UT" in f for f in faults)


def test_tc_ac_references_all_resolve() -> None:
    assert traceability.detect_tc_bidir_faults(CTX.tcc, CTX.acc) == []


def test_mutation_dangling_ac_reference_is_detected() -> None:
    victim = {**CTX.tcc[0], "ac": ["AC-99-9"]}
    assert traceability.detect_tc_bidir_faults([victim], CTX.acc)


def test_mutation_orphan_s0_ac_is_detected() -> None:
    stripped = [{**d, "trace": {**d["trace"], "ac": []}} for d in CTX.duc]
    assert traceability.detect_orphan_s0_ac(CTX.allc, CTX.acc, stripped)
