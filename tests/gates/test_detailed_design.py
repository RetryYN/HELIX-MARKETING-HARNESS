"""detailed_design ゲートの単体テストと mutation test。"""

from tools.gates import detailed_design
from tools.gates.common import CTX, DU_SCHEMA, load, schema_check


def test_api_ut_assignment_is_complete() -> None:
    assert detailed_design.detect_api_ut_faults(CTX.duc) == []


def test_mutation_api_without_ut_is_detected() -> None:
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": []}, *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert any("UTなし" in f for f in faults)


def test_mutation_ut_pointing_at_missing_function_is_detected() -> None:
    victim = {**CTX.duc[0],
              "apis": [{**CTX.duc[0]["apis"][0], "ut": ["test_db_connect.py::test_does_not_exist"]},
                       *CTX.duc[0]["apis"][1:]]}
    faults = detailed_design.detect_api_ut_faults([victim])
    assert faults, "存在しないテスト関数への参照が検出されない"


def test_mutation_empty_precondition_violates_dbc_schema() -> None:
    schema = load(DU_SCHEMA)["properties"]["apis"]["items"]
    mutated = {**CTX.duc[0]["apis"][0], "precondition": []}
    assert schema_check(schema, mutated), "pre 空の API が schema を通ってしまう"


def test_every_api_declares_pre_and_post() -> None:
    missing = [f"{d['id']}:{a['signature'][:24]}" for d in CTX.duc for a in d["apis"]
               if not a["precondition"] or not a["postcondition"]]
    assert missing == []


def test_hollow_pattern_matches_placeholders() -> None:
    assert detailed_design.HOLLOW.search("ここは TBD")
    assert detailed_design.HOLLOW.search("仮置きの値")
    assert not detailed_design.HOLLOW.search("確定した設計")
