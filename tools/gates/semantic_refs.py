"""意味整合ゲート: 構造化参照と状態遷移4タプルの正準・層間被覆検査。"""

from __future__ import annotations

import re

from tools.gates.common import (
    ERROR_TAXONOMY,
    L3,
    L4,
    L5,
    L6,
    ROOT,
    Ctx,
    gate,
)

# operation_log は execution_mode=actual で sent に到達した外部 I/O 専用。
# 単語の blacklist ではなく、正の生成主張と構造化参照の双方を検査する。
NO_EXTERNAL_EFFECT = (
    "外部操作差分なし", "外部呼出0", "外部呼出 0", "外部操作を生成せず",
    "operation_log は使用しない", "operation_log kind）の対象外",
)
OPERATION_LOG_REQUIRED_TABLES = {"evidence", "external_operations"}
OPERATION_LOG_REQUIRED_COLUMNS = {
    "evidence.external_operation_row_id",
    "external_operations.correlation_key",
    "external_operations.effect",
    "external_operations.execution_mode",
    "external_operations.policy_category",
    "external_operations.rate_scope",
    "external_operations.request_hash",
    "external_operations.request_sequence",
    "external_operations.status",
}
INTERNAL_REJECTION_TERMS = (
    "PairNotEstablished", "UrlDenied", "ApprovalRequired", "RouteNotRegistered",
    "SecretUnavailable", "CredentialLeakDetected", "ProductionWriteDenied",
    "PaidRouteDenied", "PlaybookMissing", "PlaybookBroken", "preflight", "dry-run",
    "mock", "fixture", "事前拒否", "接続前拒否", "送信前拒否", "上限超過",
    "内部拒否", "内部ゲート拒否", "内部状態遷移", "内部判定拒否",
)
CONTRACT_ACTUAL_TERMS = (
    "execution_mode=actual", "execution_mode='actual'", 'execution_mode="actual"',
    "実外部", "実 request", "実request",
)
ERROR_TYPE_RE = re.compile(
    r"[A-Z][A-Za-z]{3,}(?:Error|Rejected|Denied|Missing|Mismatch|Detected|Incomplete|"
    r"Immutable|Violation|Required|Exhausted)")
TRANSITION_REF_KEYS = ("entity", "from", "event", "to")
OPERATION_LOG_NEGATIVE_RE = re.compile(
    r"(?:external_operations\s*[／/・と＋+]+\s*)?operation_log"
    r".{0,36}?(?:[=＋+]?\s*0\s*(?:行|件|回)?|なし|不変|対象外|禁止|"
    r"使用しない|使わない|生成しない|生成せず|作らない|作らず|作成せず|"
    r"記録しない|記録せず|残さない|残さず|記録先にしない|増分なし)",
    re.IGNORECASE,
)
OPERATION_LOG_NEUTRAL_RE = re.compile(
    r"operation_log\s*(?:の)?(?:件数|SELECT|照会|検索|検査対象)", re.IGNORECASE,
)
OPERATION_LOG_GENERATION_RE = re.compile(
    r"(?:operation_log.{0,100}?(?:INSERT\b|[+＋]\s*[1-9]\d*|"
    r"(?:生成|作成|記録)(?:する|した|し(?!ない)|される)|作る|残す|追加する|増分する)"
    r"|(?:INSERT\b|(?:生成|作成|記録)(?:する|した|し(?!ない)|される)|"
    r"作る|残す|追加する|増分する).{0,100}?operation_log)",
    re.IGNORECASE,
)
OPERATION_LOG_POSITIVE_TAIL_RE = re.compile(
    r"(?:[+＋]\s*[1-9]\d*|[1-9]\d*\s*(?:行|件|回)|INSERT\b|"
    r"(?:生成|作成|記録)(?:する|した|し(?!ない)|される)|作る|残す|追加する|増分する)",
    re.IGNORECASE,
)
OBSERVATION_FIELD_PARTS = (
    "fixture", "given", "precondition", "input", "observation_point", "forbidden",
)


def load_canon(ctx: Ctx) -> dict:
    """意味検査の正本語彙（DDL・遷移表・evidence kind・エラー分類・API）。"""
    from tools.gates.common import EVIDENCE_KINDS, load
    ev = {t["event"] for t in ctx.transitions}
    kinds = {k["kind"] for k in load(EVIDENCE_KINDS)["items"]}
    errs = set(ERROR_TYPE_RE.findall(ERROR_TAXONOMY.read_text(encoding="utf-8")))
    apis = {m.group(1) for d in ctx.duc for a in d["apis"]
            if (m := re.match(r"def (\w+)", a["signature"]))}
    return {"tables": ctx.ddl_columns, "states": ctx.trn_states, "events": ev,
            "kinds": kinds, "errors": errs, "apis": apis}


def detect_semantic_ref_faults(items: list[dict], canon: dict) -> list[str]:
    """構造化参照が正本語彙に実在しない箇所を列挙する。"""
    bad: list[str] = []
    for it in items:
        r = it.get("semantic_refs")
        if r is None:
            bad.append(f"{it.get('id', '?')}:semantic_refs なし")
            continue
        for t in r["table_refs"]:
            if t not in canon["tables"]:
                bad.append(f"{it['id']}:table {t}")
        for c in r["column_refs"]:
            t, col = c.split(".", 1)
            if t not in canon["tables"] or col not in canon["tables"][t]:
                bad.append(f"{it['id']}:column {c}")
        for s in r["state_refs"]:
            e, name = s.split(".", 1)
            if e not in canon["states"] or name not in canon["states"][e]:
                bad.append(f"{it['id']}:state {s}")
        for e in r["event_refs"]:
            if e not in canon["events"]:
                bad.append(f"{it['id']}:event {e}")
        for k in r["evidence_kind_refs"]:
            if k not in canon["kinds"]:
                bad.append(f"{it['id']}:kind {k}")
        for x in r["error_type_refs"]:
            if x not in canon["errors"]:
                bad.append(f"{it['id']}:error {x}")
        for a in r["api_refs"]:
            if a not in canon["apis"]:
                bad.append(f"{it['id']}:api {a}")
    return bad


def _transition_ref_set(item: dict, bad: list[str]) -> set[tuple[str, str, str, str]]:
    """契約1件の transition_refs を正規化し、不正形・重複を列挙する。"""
    refs = item.get("transition_refs", [])
    item_id = item.get("id", "?")
    if not isinstance(refs, list):
        bad.append(f"{item_id}:transition_refs が配列でない")
        return set()
    normalized: list[tuple[str, str, str, str]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict) or set(ref) != set(TRANSITION_REF_KEYS) \
                or not all(isinstance(ref.get(key), str) and ref[key]
                           for key in TRANSITION_REF_KEYS):
            bad.append(f"{item_id}:transition_refs[{index}] の4要素が不正")
            continue
        normalized.append(tuple(ref[key] for key in TRANSITION_REF_KEYS))
    if len(normalized) != len(set(normalized)):
        bad.append(f"{item_id}:transition_refs が重複")
    return set(normalized)


def _format_transition(ref: tuple[str, str, str, str]) -> str:
    entity, source, event, target = ref
    return f"{entity}.{source}:{event}->{target}"


def detect_transition_ref_faults(nfrs: list[dict], acs: list[dict], tcs: list[dict],
                                 contracts: list[dict],
                                 transitions: list[dict]) -> list[str]:
    """transition_refs の正準実在と要求→AC→TCC の集合完全一致を検査する。"""
    bad: list[str] = []
    items = contracts + nfrs + acs + tcs
    refs_by_id = {item["id"]: _transition_ref_set(item, bad) for item in items}
    canonical = {
        (row["entity"], row["from"], row["event"], row["to"])
        for row in transitions
    }
    for item in items:
        for ref in sorted(refs_by_id[item["id"]] - canonical):
            bad.append(f"{item['id']}:非正準transition {_format_transition(ref)}")

    ac_by_id = {item["id"]: item for item in acs}
    tc_by_id = {item["id"]: item for item in tcs}
    parents = contracts + nfrs
    parent_ids = {item["id"] for item in parents}
    for parent in parents:
        linked_acs = [ac_by_id[ac_id]
                      for ac_id in parent.get("trace_down", {}).get("ac", [])
                      if ac_id in ac_by_id]
        ac_union = set().union(*(refs_by_id[ac["id"]] for ac in linked_acs)) \
            if linked_acs else set()
        parent_refs = refs_by_id[parent["id"]]
        if parent_refs != ac_union:
            missing = sorted(parent_refs - ac_union)
            extra = sorted(ac_union - parent_refs)
            edge = "NFR→AC" if parent["id"].startswith("NFR-") else "FR/SR→AC"
            bad.append(
                f"{parent['id']}:{edge} transition被覆不一致 "
                f"欠落={[_format_transition(x) for x in missing]} "
                f"過剰={[_format_transition(x) for x in extra]}"
            )

    for ac in acs:
        if ac.get("target") not in parent_ids:
            continue
        linked_tcs = [tc_by_id[tc_id] for tc_id in ac.get("tc", []) if tc_id in tc_by_id]
        tc_union = set().union(*(refs_by_id[tc["id"]] for tc in linked_tcs)) \
            if linked_tcs else set()
        ac_refs = refs_by_id[ac["id"]]
        if ac_refs != tc_union:
            missing = sorted(ac_refs - tc_union)
            extra = sorted(tc_union - ac_refs)
            bad.append(
                f"{ac['id']}:AC→TCC transition被覆不一致 "
                f"欠落={[_format_transition(x) for x in missing]} "
                f"過剰={[_format_transition(x) for x in extra]}"
            )
    return bad


def _walk_strings(value: object, path: str = "") -> list[tuple[str, str]]:
    """semantic_refs 自身を除き、契約内の任意階層にある自由文を列挙する。"""
    out: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "semantic_refs":
                continue
            child_path = f"{path}.{key}" if path else key
            out.extend(_walk_strings(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.extend(_walk_strings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        out.append((path, value))
    return out


def _operation_log_fragments(text: str, field: str = "") -> tuple[list[str], list[str]]:
    """operation_log の正生成主張と 0 行／非生成主張を節単位で分離する。"""
    positive: list[str] = []
    negative: list[str] = []
    observation_field = any(token in field for token in OBSERVATION_FIELD_PARTS)
    # 「mock は0、actual は1」のような同一フィールド混在を丸ごと skip しない。
    for fragment in re.split(r"[。；;\n、，]", text):
        if "operation_log" not in fragment:
            continue
        # 否定形を引用して覆す文と「検査対象として1行生成」は正生成を優先する。
        override_tail = ""
        for marker in ("ではなく", "禁止し", "廃止し", "検査対象として"):
            if marker in fragment:
                override_tail = fragment.rsplit(marker, 1)[1]
                break
        positive_override = bool(
            override_tail and OPERATION_LOG_POSITIVE_TAIL_RE.search(override_tail)
        )
        if positive_override:
            positive.append(fragment)
        elif OPERATION_LOG_NEGATIVE_RE.search(fragment) \
                or any(marker in fragment for marker in NO_EXTERNAL_EFFECT):
            negative.append(fragment)
        elif OPERATION_LOG_GENERATION_RE.search(fragment):
            positive.append(fragment)
        elif OPERATION_LOG_NEUTRAL_RE.search(fragment):
            continue
        elif observation_field:
            # fixture/given/input は既存行の混入・観測にも使う。正生成動詞がある時だけ主張。
            continue
        else:
            positive.append(fragment)
    return positive, negative


def _has_actual_sent_witness(text: str) -> bool:
    """同じ節で actual 外部 I/O が sent/provider 到達したことを明示しているか。"""
    actual = any(term in text for term in CONTRACT_ACTUAL_TERMS) \
        or bool(re.search(r"(?<![A-Za-z])actual(?![A-Za-z])", text, re.IGNORECASE))
    sent_or_provider_reached = "sent" in text or bool(re.search(
        r"provider.{0,24}?(?:到達|送信|応答|受信|返却|429|成功|失敗)", text,
        re.IGNORECASE,
    ))
    return actual and sent_or_provider_reached


def _active_internal_terms(text: str) -> list[str]:
    """否定された mock/dry-run を除き、正生成節内の内部/pre-call語を返す。"""
    active: list[str] = []
    for term in INTERNAL_REJECTION_TERMS:
        if term == "fixture":
            # fixture はテスト入力の意味が支配的で、拒否種別ではない。
            continue
        lowered = text.lower()
        for match in re.finditer(re.escape(term), text, re.IGNORECASE):
            term_index = match.start()
            previous_log = lowered.rfind("operation_log", 0, term_index)
            next_log = lowered.find("operation_log", match.end())
            if previous_log >= 0 and "／" in text[previous_log:term_index] \
                    and next_log < 0:
                # 「外部log／秘匿process拒否」のような後続別チャネルを同一主張にしない。
                continue
            local_tail = text[term_index:term_index + 64]
            if term in {"mock", "dry-run"} and re.search(
                    rf"{re.escape(term)}.{{0,40}}?(?:使用しない|使わない|対象外|"
                    rf"0\s*(?:行|件|回))", local_tail, re.IGNORECASE):
                continue
            active.append(term)
            break
    return active


def _operation_log_binding_faults(item: dict, positive: list[tuple[str, str]]) -> list[str]:
    """正の operation_log 主張が actual 外部行へ意味・構造とも束縛されるか検査。"""
    if not positive:
        return []
    item_id = item.get("id", "?")
    refs = item.get("semantic_refs", {})
    tables = set(refs.get("table_refs", []))
    columns = set(refs.get("column_refs", []))
    kinds = set(refs.get("evidence_kind_refs", []))
    all_text = " ".join(text for _, text in _walk_strings(item))
    faults: list[str] = []

    # refs や別フィールドへ actual 語彙をコピーしても、内部拒否の正生成節は救済しない。
    for field, fragment in positive:
        internal = _active_internal_terms(fragment)
        if internal and not _has_actual_sent_witness(fragment):
            faults.append(
                f"{item_id}:{field}:内部/pre-call operation_log正生成={internal}"
            )

    missing_tables = sorted(OPERATION_LOG_REQUIRED_TABLES - tables)
    missing_columns = sorted(OPERATION_LOG_REQUIRED_COLUMNS - columns)
    if "operation_log" not in kinds:
        faults.append(f"{item_id}:operation_log正生成主張にevidence_kind_refなし")
    if missing_tables:
        faults.append(f"{item_id}:operation_log正生成主張のtable_ref欠落={missing_tables}")
    if missing_columns:
        faults.append(f"{item_id}:operation_log正生成主張のcolumn_ref欠落={missing_columns}")

    text_requirements = {
        "actual": any(term in all_text for term in CONTRACT_ACTUAL_TERMS),
        "sent": "sent" in all_text,
        "effect": "effect" in all_text and ("read" in all_text or "write" in all_text),
        "policy_category": "policy_category" in all_text,
        "rate_scope": "rate_scope" in all_text,
        "local_row": "external_operation_row_id" in all_text,
        "correlation": "correlation_key" in all_text,
        "request_hash": "request_hash" in all_text,
        "request_sequence": "request_sequence" in all_text,
    }
    missing_meaning = sorted(name for name, present in text_requirements.items() if not present)
    if missing_meaning:
        faults.append(f"{item_id}:operation_log正生成主張の意味束縛欠落={missing_meaning}")
    return faults


def detect_state_evidence_faults(acs: list[dict], tcs: list[dict],
                                 contracts: list[dict] | None = None) -> list[str]:
    """operation_log の actual 外部 I/O 限定と全フィールドの意味束縛を検査する。"""
    bad: list[str] = []
    seen: set[str] = set()
    for item in [*(contracts or []), *acs, *tcs]:
        item_id = item.get("id", "?")
        if item_id in seen:
            continue
        seen.add(item_id)
        positive: list[tuple[str, str]] = []
        for field, text in _walk_strings(item):
            positives, _ = _operation_log_fragments(text, field)
            positive.extend((field, fragment) for fragment in positives)
        bad.extend(_operation_log_binding_faults(item, positive))

        if "DB を変更せず" in str(item.get("rejection_behavior", "")) \
                and "state_transitions" in str(item.get("rejection_behavior", "")):
            bad.append(f"{item_id}:拒否証跡INSERTとDB変更なしが矛盾")
    return bad


def _markdown_logical_blocks(text: str) -> list[tuple[int, str]]:
    """段落・table row・親子箇条書きを、折返しを含む論理ブロックへまとめる。"""
    blocks: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    bullet_indent: int | None = None

    def flush() -> None:
        nonlocal current, start, bullet_indent
        if current:
            blocks.append((start, " ".join(part.strip() for part in current)))
        current = []
        start = 0
        bullet_indent = None

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("|"):
            flush()
            blocks.append((lineno, stripped))
            continue
        if stripped.startswith("#"):
            flush()
            blocks.append((lineno, stripped))
            continue

        bullet = re.match(r"^(\s*)(?:[-*+]|\d+[.)])\s+", line)
        if bullet:
            indent = len(bullet.group(1).expandtabs(4))
            if current and bullet_indent is not None and indent <= bullet_indent:
                flush()
            if not current:
                start = lineno
                bullet_indent = indent
            current.append(stripped)
            continue

        if not current:
            start = lineno
        current.append(stripped)
    flush()
    return blocks


def detect_markdown_operation_log_faults(documents: list[tuple[str, str]]) -> list[str]:
    """設計 Markdown の内部／pre-call 拒否を operation_log 化する逆行を検出する。"""
    bad: list[str] = []
    for name, text in documents:
        for lineno, context in _markdown_logical_blocks(text):
            if "operation_log" not in context:
                continue
            positive, _ = _operation_log_fragments(context)
            invalid = [
                fragment for fragment in positive
                if _active_internal_terms(fragment)
                and not _has_actual_sent_witness(fragment)
            ]
            if not invalid:
                # 親 bullet が句点で終わり、子 bullet が証跡主張を続ける折返しも同じ文脈。
                for child in re.finditer(
                        r"。\s*(?:[-*+]|\d+[.)])\s+([^。]*operation_log[^。]*)",
                        context):
                    child_text = child.group(1)
                    child_positive, _ = _operation_log_fragments(child_text)
                    if _active_internal_terms(context[:child.start()]) and child_positive \
                            and not _has_actual_sent_witness(child_text):
                        invalid.extend(child_positive)
                        break
            if invalid:
                bad.append(f"{name}:{lineno}:内部/pre-call拒否をoperation_logで表現")
    return bad


def run(ctx: Ctx) -> None:
    canon = load_canon(ctx)
    items = ctx.frc + ctx.src + ctx.nfc + ctx.acc + ctx.tcc + ctx.cmpc + ctx.duc
    sem_bad = detect_semantic_ref_faults(items, canon)
    sem_bad += detect_transition_ref_faults(
        ctx.nfc, ctx.acc, ctx.tcc, ctx.allc, ctx.transitions)
    col_bad = [b for b in sem_bad if ":column " in b or ":table " in b]
    gate("G-SEMANTIC-REF", not sem_bad,
         "構造化参照が正本語彙に実在し、transition 4タプルが正準かつFR/SR/NFR→AC→TCCで集合一致 "
         f"(table/column/state/event/kind/error/api/transition) (不正={sem_bad[:5]})")
    gate("G-COLUMN-REF", not col_bad, f"table/column 参照が ddl.sql に実在 (不正={col_bad[:5]})")
    se_bad = detect_state_evidence_faults(
        ctx.acc, ctx.tcc, ctx.allc + ctx.nfc + ctx.cmpc + ctx.duc)
    markdown_paths = sorted({
        *L3.joinpath("canonical").rglob("*.md"),
        *L4.joinpath("canonical").rglob("*.md"),
        *L5.joinpath("canonical").rglob("*.md"),
        *L6.joinpath("S0").glob("*.md"),
    })
    se_bad += detect_markdown_operation_log_faults([
        (str(path.relative_to(ROOT)), path.read_text(encoding="utf-8"))
        for path in markdown_paths
    ])
    gate("G-STATE-EVIDENCE-CONSISTENCY", not se_bad,
         "operation_log は actual・sent 外部I/Oに限定し、全フィールド・設計Markdown・構造参照を束縛 "
         f"(違反={se_bad[:5]})")
