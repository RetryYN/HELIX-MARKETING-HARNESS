"""traceability ゲートの単体テストと mutation test。"""

from tools.gates import traceability
from tools.gates.common import CTX


def test_chain_is_bidirectional_on_real_contracts() -> None:
    assert traceability.detect_chain_asymmetry(
        CTX.brc, CTX.req, CTX.allc, CTX.acc, CTX.cmpc, CTX.duc, CTX.tcc) == []
    assert traceability.detect_orphan_s0_ac(CTX.allc, CTX.acc, CTX.duc) == []


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
