#!/usr/bin/env python3
"""JSON 内容正本 → Markdown 生成ビュー レンダラ。

全層再降下（2026-08-01 PO 指示 §9）: JSON を内容正本、Markdown を生成ビューへ段階移行する。
生成された MD は手編集禁止（ヘッダに GENERATED 宣言、G-REQ-CONTRACT 等が同期を fail-close 検査）。

使い方:
    python3 scripts/render_views.py            # 全ビューを再生成
    python3 scripts/render_views.py --check    # 生成結果と現ファイルの一致を検査（差分あり = exit 1）
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
L1 = ROOT / "docs" / "L1-business-requirements"
L3 = ROOT / "docs" / "L3-system-requirements"
L4 = ROOT / "docs" / "L4-basic-design"
L5 = ROOT / "docs" / "L5-detailed-design"
AUTHORITY = ROOT / "docs" / "00-authority"

GENERATED_HEADER = (
    "<!-- GENERATED FILE — 編集禁止。正本は {src}。再生成 = python3 scripts/render_views.py -->\n\n"
)

STATUS_LABEL = {"confirmed": "confirmed", "draft": "draft（再降下中）", "superseded": "superseded"}
REVALIDATION_BANNER = (
    "> [!WARNING]\n"
    "> **旧baselineの生成view。現行要求の正本・設計・実装入力ではない。**  "
    "`requirements_baseline_status=revising` / `implementation_authorized=false`。\n"
    "> 下記status/receiptは旧baselineの成熟度と承認履歴だけを示す。PO receipt付きfrozen refinementから"
    "Full Vを再降下しauthority cutoverするまで、本viewの内容をcurrentへ読み替えない。\n\n"
)


def _markdown_autolink_urls(value: str) -> str:
    """正本の bare URL を変更せず、生成 Markdown でだけ autolink 化する。"""
    trailing = ".,;:!?)]}）］】」』"

    def autolink(match: re.Match[str]) -> str:
        candidate = match.group(0)
        url = candidate.rstrip(trailing)
        return f"<{url}>{candidate[len(url):]}"

    def render_prose(part: str) -> str:
        # 既存 autolink・code span・Markdown link destination は二重加工しない。
        return re.sub(r"(?<![<`(])(https?://[^\s<>`、。）」』】]+)", autolink, part)

    # fenced code は表示内容そのものなので変更せず、prose 部分だけを変換する。
    parts = re.split(r"(^```[^\n]*\n.*?^```[ \t]*$)", value, flags=re.MULTILINE | re.DOTALL)
    return "".join(part if part.startswith("```") else render_prose(part) for part in parts)


def status_line(data: dict, note: str) -> str:
    """JSON 正本の status／承認 receipt からビューの status 行を生成する（固定文字列を持たない）。"""
    st = STATUS_LABEL.get(data.get("status", "draft"), data.get("status", "draft"))
    when = (data.get("approved_at") or "")[:10]
    who = data.get("authority", "")
    receipt = data.get("approval_digest", "")
    tail = f"（{when} {who} 承認 — receipt {receipt}）" if receipt else ""
    return REVALIDATION_BANNER + f"> status: **{st}**{tail}。{note}\n"


def render_br_contracts() -> tuple[Path, str]:
    src = L1 / "canonical" / "br" / "br-contracts.json"
    data = json.loads(src.read_text())
    out = []
    out.append(GENERATED_HEADER.format(src="docs/L1-business-requirements/canonical/br/br-contracts.json"))
    out.append("# 業務要求 構造化契約（BR contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §2）"))
    out.append("> 位置づけ: [br-backbone_v0.1.md](../canonical/br-backbone_v0.1.md) の全 BR を 12 観点の構造化契約へ展開した正本ビュー。\n")
    out.append("> 1 行要求文の禁止（G-REQ-CONTRACT が schema 適合・全 BR 被覆・12 要求群被覆・本ビュー同期を fail-close 検査）。\n\n")

    groups: dict[str, list] = {}
    for it in data["items"]:
        groups.setdefault(it["group"], []).append(it)

    for group, items in groups.items():
        out.append(f"## {group}\n\n")
        for it in items:
            out.append(f"### {it['id']} {it['title']}\n\n")
            out.append(f"- **目的**: {it['purpose']}\n")
            out.append(f"- **主体・利用者**: {it['actor']}\n")
            out.append(f"- **発生状況・トリガー**: {it['trigger']}\n")
            out.append(f"- **現在の問題**: {it['problem']}\n")
            out.append(f"- **期待する価値・成果**: {it['value']}\n")
            out.append(f"- **対象範囲**: {'／'.join(it['scope_in'])}\n")
            out.append(f"- **非対象範囲**: {'／'.join(it['scope_out'])}\n")
            out.append(f"- **制約**: {'／'.join(it['constraints'])}\n")
            out.append(f"- **禁止事項**: {'／'.join(it['prohibitions'])}\n")
            out.append(f"- **人間判断点**: {it['human_judgement']}\n")
            out.append(f"- **失敗時の影響**: {it['failure_impact']}\n")
            out.append(f"- **完了を証明する証跡**: {'／'.join(it['completion_evidence'])}\n")
            td = it["trace_down"]
            down = "、".join(
                部 for 部 in (
                    " ".join(td.get("req", [])),
                    " ".join(td.get("fr", [])),
                    " ".join(td.get("sr", [])),
                    " ".join(td.get("nfr", [])),
                ) if 部
            )
            out.append(f"- **上流 trace**: {'／'.join(it['trace_up'])}\n")
            out.append(f"- **下流 trace**: {down}\n")
            if it["mandated_groups"]:
                out.append(f"- **担当する独立要求群**: {'、'.join(it['mandated_groups'])}\n")
            out.append(f"- **充填経路**: {it['fill']}\n\n")
    return L1 / "views" / "br-contracts_v0.1.md", "".join(out)


def render_requirement_candidates() -> tuple[Path, str]:
    """未承認 refinement を、人間が意味単位で確認するための候補 view にする。"""
    src_rel = "docs/00-authority/development/requirement-refinements.json"
    data = json.loads((ROOT / src_rel).read_text())
    records = sorted(data["records"], key=lambda item: item["refinement_id"])
    scope_assignments = data["scope_assignments"]
    approved = sum(item["approval"] is not None for item in records)
    out = [GENERATED_HEADER.format(src=src_rel)]
    out.append("# 要求候補レビュー（refinement candidates）\n\n")
    out.append(
        "> [!CAUTION]\n"
        "> **提案専用の生成view。現行要求の正本・PO承認・設計・実装入力ではない。**  "
        "`requirements_baseline_status=revising` / `implementation_authorized=false`。\n"
        "> 各候補は個別のPO receiptで承認・freezeされ、Full Vを再降下してauthority cutoverするまでcurrentにならない。"
        "本view全体を一括承認として扱わない。\n\n"
    )
    out.append(
        f"> 集計: 候補 **{len(records)}** 件 ／ approval receiptあり **{approved}** 件 ／ "
        f"未承認 **{len(records) - approved}** 件。\n\n"
    )
    out.append("## PO確認順（decision packets）\n\n")
    out.append("> packetは確認順をまとめるだけで、packet単位の一括承認は禁止。各subject revisionへ個別receiptを束縛する。\n\n")
    for packet in sorted(data["decision_packets"], key=lambda item: item["decision_order"]):
        out.append(
            f"{packet['decision_order']}. **{packet['packet_id']}** — {packet['decision_question']}  "
            f"対象: {', '.join(packet['subject_ids'])}\n"
        )
    out.append("\n")
    out.append("## 回答済み事項（要求へ再降下前）\n\n")
    out.append(
        "> 会話から取得したPO判断の構造化snapshot。まだ個別refinement revision・approval receipt・freezeへ"
        "再降下していないため、設計・実装入力ではない。\n\n"
    )
    for decision in data["captured_po_decisions"]:
        out.append(
            f"- **{decision['decision_id']}** (`{decision['status']}`): {decision['statement']}  "
            f"既存subject={', '.join(decision['affected_subject_ids'])} ／ "
            f"新規要求subject={', '.join(decision['required_new_subject_ids'])} ／ "
            f"未解決={'／'.join(decision['unresolved']) if decision['unresolved'] else 'なし'}\n"
        )
    out.append("\n")
    out.append("## PRC意味所有者\n\n")
    out.append(
        "> baseline候補の各PRCを、意味を閉じるrefinement subjectへ束縛する。"
        "PRC本文だけを単独で承認・設計入力化しない。\n\n"
    )
    for prc_id, owners in sorted(data["candidate_requirement_bindings"].items()):
        out.append(f"- **{prc_id}**: {', '.join(owners)}\n")
    out.append("\n")
    out.append("## 旧L0 clause disposition候補\n\n")
    out.append(
        "> charter v0.4の旧承認履歴は変更せず、事業価値と旧実現手段を分離して新PRCへ移す候補。"
        "全行`candidate_unratified`であり、PO receiptまでは現行L0又は設計入力にならない。\n\n"
    )
    out.append("| clause | 旧意味 | 処置 | 維持する価値 | replacement PRC | 再開条件 |\n")
    out.append("|---|---|---|---|---|---|\n")
    for row in data["legacy_l0_clause_dispositions"]:
        out.append(
            f"| `{row['clause_id']}`<br>{row['source_ref']} | {row['meaning']} | "
            f"`{row['disposition']}` | {row['retained_value']} | "
            f"{', '.join(row['replacement_prc_ids'])} | "
            f"{'／'.join(row['resume_conditions']) if row['resume_conditions'] else '—'} |\n"
        )
    out.append("\n")
    out.append("## 旧critical responsibility disposition候補\n\n")
    out.append(
        "> 旧BR／FRの通知・承認・自動運用・UI責務をそのまま再利用せず、現要求のmeaning ownerへ分割する候補。"
        "旧契約のconfirmed履歴は変更せず、全行を未承認・未設計として扱う。\n\n"
    )
    out.append("| legacy ID | 旧意味 | 処置 | 維持する責務 | 置換責務 | meaning owner | 継承禁止 |\n")
    out.append("|---|---|---|---|---|---|---|\n")
    for row in data["legacy_critical_responsibility_dispositions"]:
        out.append(
            f"| `{row['legacy_id']}`<br>{row['source_ref']} | {row['legacy_meaning']} | "
            f"`{row['disposition']}` | {row['retained_responsibility']} | "
            f"{'／'.join(row['replacement_responsibilities'])} | "
            f"{', '.join(row['owner_subject_ids'])} | "
            f"{'／'.join(row['prohibited_inheritance'])} |\n"
        )
    out.append("\n")
    descent = data["semantic_descent_policy"]
    out.append("## 意味降下policy候補\n\n")
    out.append(
        "> BRからTCまで意味fieldを散文から推測せず、直接宣言又はsource revision/digest付き継承で閉じる。"
        "FN→CMP→DUは要求freezeまでblockedであり、この表は設計成果物ではない。\n\n"
    )
    out.append("| 意味軸 | mode | 規則 |\n")
    out.append("|---|---|---|\n")
    for dimension, rule in descent["dimensions"].items():
        out.append(f"| `{dimension}` | `{rule['mode']}` | {rule['rule']} |\n")
    out.append("\n| edge | source → target | admission | 規則 |\n")
    out.append("|---|---|---|---|\n")
    for edge in descent["edge_contracts"]:
        out.append(
            f"| `{edge['edge_id']}` | {', '.join(edge['source_kinds'])} → {edge['target_kind']} | "
            f"`{edge['admission']}` | {edge['rule']} |\n"
        )
    out.append("\n")
    out.append("## 旧NFR disposition候補\n\n")
    out.append(
        "> 旧測定文やAC/TCの存在だけでは現baselineの品質要求にならない。"
        "業務根拠、actor、scope、置換意味及び再開条件をNFRごとに記録する。\n\n"
    )
    out.append("| NFR | 処置 | stable root | 業務価値 | 置換後の意味 | 未決／再開条件 | owner |\n")
    out.append("|---|---|---|---|---|---|---|\n")
    for row in data["legacy_nfr_dispositions"]:
        roots = ", ".join(row["stable_br_refs"] + row["stable_req_refs"]) or "未確定"
        unresolved = "／".join(row["missing_decisions"])
        if row["resume_conditions"]:
            unresolved += "<br>再開: " + "／".join(row["resume_conditions"])
        out.append(
            f"| `{row['nfr_id']}` | `{row['disposition']}` | {roots} | {row['business_value']} | "
            f"{row['replacement_meaning']} | {unresolved} | {', '.join(row['owner_subject_ids'])} |\n"
        )
    out.append("\n")
    out.append("## 旧orphan FR/SR disposition候補\n\n")
    out.append(
        "> stable REQ root又はFN/CMP/AC降下を欠く旧FR/SRを、意味の近い責務単位で分類する。"
        "stable IDは全件exact coverageし、group化を理由に個別IDを黙示採用しない。\n\n"
    )
    out.append("| group | IDs | 処置 | 旧問題 | 置換後の意味 | root／降下 | 再開条件 |\n")
    out.append("|---|---|---|---|---|---|---|\n")
    for group in data["legacy_orphan_requirement_groups"]:
        out.append(
            f"| `{group['group_id']}` | {', '.join(group['stable_ids'])} | `{group['disposition']}` | "
            f"{group['legacy_problem']} | {group['replacement_meaning']} | "
            f"{group['stable_root_action']}<br>{group['descent_action']} | "
            f"{'／'.join(group['resume_conditions']) if group['resume_conditions'] else '—'} |\n"
        )
    out.append("\n")
    out.append("## 旧REQ 55件 disposition候補\n\n")
    out.append(
        "> confirmed Markdownとdraft JSONのどちらも現要求正本として採用せず、stable IDごとの処置を明示する。"
        "groupはレビュー単位であり、item dispositionとdeferred再開条件はID単位で保持する。\n\n"
    )
    out.append("| group | ID別処置 | 旧問題 | 置換policy | root action | deferred再開条件 |\n")
    out.append("|---|---|---|---|---|---|\n")
    for group in data["legacy_req_disposition_groups"]:
        dispositions = ", ".join(
            f"{stable_id}={disposition}" for stable_id, disposition in group["item_dispositions"].items()
        )
        resumes = "<br>".join(
            f"{stable_id}: {'／'.join(conditions)}"
            for stable_id, conditions in group["deferred_resume_by_id"].items()
        ) or "—"
        out.append(
            f"| `{group['group_id']}` | {dispositions} | {group['legacy_problem']} | "
            f"{group['replacement_policy']} | {group['stable_root_action']} | {resumes} |\n"
        )
    out.append("\n")
    out.append("## 旧BR 41件 disposition候補\n\n")
    out.append("| group | ID別処置 | 保持する価値 | 置換policy | owner |\n")
    out.append("|---|---|---|---|---|\n")
    for group in data["legacy_br_disposition_groups"]:
        dispositions = ", ".join(f"{key}={value}" for key, value in group["item_dispositions"].items())
        out.append(
            f"| `{group['group_id']}` | {dispositions} | {group['retained_value']} | "
            f"{group['replacement_policy']} | {', '.join(group['owner_subject_ids'])} |\n"
        )
    out.append("\n## 旧媒体BR 70件 disposition候補\n\n")
    out.append(
        "> 媒体名又は旧BRの存在は実行許可ではない。全媒体は個別capabilityのPO receiptとAC/TCまで未承認・未設計である。\n\n"
    )
    out.append("| media | IDs | 処置 | 現候補での役割 | route policy | 再開条件 |\n")
    out.append("|---|---|---|---|---|---|\n")
    for row in data["legacy_media_br_dispositions"]:
        out.append(
            f"| `{row['media_id']}` | {', '.join(row['stable_ids'])} | `{row['disposition']}` | "
            f"{row['current_role']} | {row['route_policy']} | {'／'.join(row['resume_conditions'])} |\n"
        )
    out.append("\n")
    out.append("## 旧FR 43件 disposition候補\n\n")
    out.append("> 旧FRのconfirmedは旧baselineの履歴であり、下表は現要求への未承認・未設計の移送候補である。\n\n")
    out.append("| group | ID別処置 | 置換policy | owner | deferred再開条件 |\n")
    out.append("|---|---|---|---|---|\n")
    for group in data["legacy_fr_disposition_groups"]:
        dispositions = ", ".join(f"{key}={value}" for key, value in group["item_dispositions"].items())
        resumes = "<br>".join(
            f"{stable_id}: {'／'.join(conditions)}"
            for stable_id, conditions in group["deferred_resume_by_id"].items()
        ) or "—"
        out.append(
            f"| `{group['group_id']}` | {dispositions} | {group['replacement_policy']} | "
            f"{', '.join(group['owner_subject_ids'])} | {resumes} |\n"
        )
    out.append("\n")
    out.append("## 旧FN／AC／TC派生契約の扱い\n\n")
    out.append("| kind | count | ID digest | 処置 | 再利用条件 | 禁止claim |\n")
    out.append("|---|---:|---|---|---|---|\n")
    for row in data["legacy_derived_contract_policy"]:
        out.append(
            f"| `{row['kind']}` | {row['stable_id_count']} | `{row['stable_id_digest']}` | "
            f"`{row['disposition']}` | {'／'.join(row['reuse_requirements'])} | "
            f"{'／'.join(row['prohibited_claims'])} |\n"
        )
    out.append("\n")
    revision = data["authority_revision_candidate"]
    out.append("## 要求authority revision選択（PO未決）\n\n")
    out.append(f"- 問い: {revision['question']}\n")
    out.append(f"- 推奨: `{revision['recommended_strategy']}`\n")
    out.append(f"- 選択肢: {', '.join(revision['alternatives'])}\n")
    out.append(f"- 推奨規則: {'／'.join(revision['recommended_rules'])}\n")
    out.append(f"- 旧consumer処置: {'／'.join(revision['legacy_consumer_action'])}\n")
    out.append("- PO decision: **未回答**。要求正本cutover及び設計開始はしない。\n\n")
    out.append("## 目的別完了証拠\n\n")
    out.append("| ID | 要求 | 状態 | evidence | 残条件 |\n")
    out.append("|---|---|---|---|---|\n")
    for row in data["objective_completion_audit"]:
        out.append(
            f"| `{row['objective_id']}` | {row['requirement']} | `{row['status']}` | "
            f"{'／'.join(row['evidence'])} | {row['remaining_condition'] or '—'} |\n"
        )
    out.append("\n")
    response_contract = data["decision_response_contract"]
    out.append("## PO回答契約\n\n")
    out.append(
        f"- **回答値**: `{'` / `'.join(response_contract['allowed_responses'])}`\n"
        f"- **未回答の安全側既定**: `{response_contract['unanswered_default']}`\n"
        f"- **必須束縛**: `{'` / `'.join(response_contract['required_bindings'])}`\n"
        f"- **回答の効力**: {response_contract['approval_effect']}\n"
        f"- **revisionの効力**: {response_contract['revision_effect']}\n\n"
    )
    question_boundary = data["question_boundary"]
    out.append(
        f"- **POが決めるもの**: {'／'.join(question_boundary['po_decides'])}\n"
        f"- **L2以降で決めるもの**: {'／'.join(question_boundary['design_later'])}\n"
        f"- **要求／設計境界**: {question_boundary['rule']}\n\n"
    )
    out.append("- **回答classごとの必須項目**:\n")
    for class_id, required_fields in data["decision_class_contracts"].items():
        out.append(f"  - `{class_id}`: `{'` / `'.join(required_fields)}`\n")
    out.append("\n")
    for item in records:
        dims = item["semantic_dimensions"]
        approval = item["approval"]
        approval_label = (
            f"{approval['authority']} / {approval['approver_principal']} / "
            f"revision {approval['approved_revision']} / {approval['decision_receipt_digest']}"
            if approval else "未承認（approval receiptなし）"
        )
        out.append(f"## {item['refinement_id']} — {item['subject_id']}\n\n")
        out.append(
            f"- **状態**: `{item['lifecycle_status']}` ／ revision {item['revision']} ／ "
            f"**承認**: {approval_label}\n"
        )
        out.append(
            f"- **scope候補**: `{scope_assignments[item['subject_id']]}` "
            "（PO receiptとFull V再降下までは実装不可）\n"
        )
        out.append(f"- **source events**: {' '.join(item['source_event_ids'])}\n")
        out.append(f"- **主体**: {'／'.join(dims['actors'])}\n")
        out.append(f"- **受益者**: {'／'.join(dims['beneficiaries'])}\n")
        out.append(f"- **価値**: {dims['value']}\n")
        out.append(f"- **task**: {'／'.join(dims['tasks'])}\n")
        out.append(f"- **workflow**: {' → '.join(dims['workflow'])}\n")
        out.append(f"- **対象範囲**: {'／'.join(dims['scope_in'])}\n")
        out.append(f"- **対象外**: {'／'.join(dims['scope_out'])}\n")
        out.append(f"- **禁止事項**: {'／'.join(dims['prohibitions'])}\n")
        out.append(f"- **人間判断**: {'／'.join(dims['human_judgement'])}\n")
        out.append(f"- **副作用**: {'／'.join(dims['side_effects'])}\n")
        out.append(f"- **証跡**: {'／'.join(dims['evidence'])}\n")
        out.append(f"- **phase**: `{dims['phase']}`\n")
        admission = item.get("delivery_admission")
        if admission:
            predecessors = admission["predecessor_subject_ids"]
            out.append(
                f"- **delivery admission**: standard=`{admission['standard_model']}` ／ "
                f"program-stage={admission['program_stage']} ／ sequence={admission['sequence']} ／ "
                f"increment={'／'.join(admission['increment_routes'])} ／ "
                f"Discovery=`{admission['discovery_condition']}` ／ "
                f"predecessor={'／'.join(predecessors) if predecessors else 'なし'} ／ "
                f"completion=`{admission['completion_boundary']}`\n"
            )
        media_admission = item.get("legacy_media_admission")
        if media_admission:
            out.append(
                f"- **legacy media admission**: {len(media_admission['covered_legacy_mr_ids'])} MR ／ "
                f"default=`{media_admission['default_status']}` ／ "
                f"unresolved={'／'.join(media_admission['unresolved_fields'])} ／ "
                f"reason={media_admission['reason']}\n"
            )
        out.append("- **受入候補**:\n")
        for case in item["acceptance_cases"]:
            out.append(
                f"  - `{case['polarity']}` {case['acceptance_id']}: {case['statement']} "
                f"（{case['system_test_id']}）\n"
            )
        pending = item["pending_resolution"]
        if pending:
            out.append("- **PO個別質問**:\n")
            for question_index, question in enumerate(pending, start=1):
                question_id = f"RDQ-{item['refinement_id'][4:]}-{question_index:02d}"
                out.append(
                    f"  - `{question_id}` (`{data['question_classifications'][question_id]}`): {question} "
                    f"（未回答=`{response_contract['unanswered_default']}`。回答はsubject revisionとsemantic digestへ束縛）\n"
                )
        else:
            out.append("- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）\n")
        out.append(f"- **semantic digest**: `{item['semantic_digest']}`\n\n")
    return AUTHORITY / "views" / "requirement-candidates_v0.1.md", "".join(out)


def _contract_md(it: dict) -> str:
    o = []
    o.append(f"## {it['id']} {it['title']}\n\n")
    o.append(f"- **入力**: {'／'.join(it['input'])}\n")
    o.append(f"- **出力**: {'／'.join(it['output'])}\n")
    o.append(f"- **事前条件**: {'／'.join(it['precondition'])}\n")
    o.append(f"- **事後条件**: {'／'.join(it['postcondition'])}\n")
    o.append(f"- **不変条件**: {'／'.join(it['invariants'])}\n")
    o.append(f"- **状態遷移**: {'／'.join(it['state_transitions']) or 'なし'}\n")
    o.append(f"- **正常動作**: {it['normal_behavior']}\n")
    o.append(f"- **拒否・異常動作**: {it['rejection_behavior']}\n")
    o.append(f"- **境界動作**: {it['boundary_behavior']}\n")
    o.append(f"- **再試行・再開・復旧**: {it['retry_resume_recovery']}\n")
    o.append(f"- **人間判断／escalation**: {it['human_judgement']}\n")
    o.append(f"- **副作用**: {'／'.join(it['side_effects'])}\n")
    o.append(f"- **冪等性**: {it['idempotency']}\n")
    o.append(f"- **証跡**: {'／'.join(it['evidence'])}\n")
    o.append(f"- **使用テーブル・正本**: {'／'.join(it['tables']) or 'なし'}\n")
    o.append(f"- **外部依存**: {'／'.join(it['external_deps']) or 'なし'}\n")
    o.append(f"- **設定値**: {'／'.join(it['config_values']) or 'なし'} ／ **固定値**: {'／'.join(it['fixed_values']) or 'なし'}\n")
    td = it["trace_down"]
    down = " ".join(td.get("ac", []) + td.get("fn", []) + td.get("cmp", [])) or "（AC 割当待ち）"
    o.append(f"- **trace**: 上流 = {' '.join(it['trace_up'])} ／ 下流 = {down} ／ スライス = {it['slice']}\n")
    if it.get("ac_na"):
        nas = "、".join(f"{k}: {v}" for k, v in it["ac_na"].items())
        o.append(f"- **AC 極性 N/A**: {nas}\n")
    o.append("\n")
    return "".join(o)


def _make_contract_renderer(src_rel: str, out_name: str, title: str, pair_note: str):
    def render() -> tuple[Path, str]:
        src = ROOT / src_rel
        data = json.loads(src.read_text())
        out = [GENERATED_HEADER.format(src=src_rel)]
        out.append(f"# {title} v{data['version']}\n\n")
        out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §3）"))
        out.append(f"> {pair_note}\n\n")
        for it in data["items"]:
            out.append(_contract_md(it))
        return L3 / "views" / out_name, "".join(out)
    return render


def render_nfr_contracts() -> tuple[Path, str]:
    src = L3 / "canonical" / "nonfunctional" / "nfr-contracts.json"
    data = json.loads(src.read_text())
    out = [GENERATED_HEADER.format(src="docs/L3-system-requirements/canonical/nonfunctional/nfr-contracts.json")]
    out.append("# 非機能要件 計測契約（NFR contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §3）"))
    out.append("> 各 NFR に測定対象・測定方法・閾値・測定環境・違反時動作・証跡を必須化（G-NFR-MEASURABLE）。\n\n")
    for it in data["items"]:
        out.append(f"## {it['id']} {it['title']}\n\n")
        out.append(f"- **測定対象**: {it['measurement_target']}\n")
        out.append(f"- **測定方法**: {it['measurement_method']}\n")
        out.append(f"- **閾値**: {it['threshold']}\n")
        out.append(f"- **測定環境**: {it['measurement_env']}\n")
        out.append(f"- **違反時の動作**: {it['violation_behavior']}\n")
        out.append(f"- **証跡**: {'／'.join(it['evidence'])}\n")
        out.append(f"- **検証観点**: {' '.join(it['verification_aspects'])}\n")
        td = it["trace_down"]
        out.append(f"- **trace**: 上流 = {' '.join(it['trace_up'])} ／ 下流 = {' '.join(td.get('ac', []) + td.get('tc', [])) or '（割当待ち）'}\n\n")
    return L3 / "views" / "nfr-contracts_v0.1.md", "".join(out)


def render_ac_catalog() -> tuple[Path, str]:
    src = L3 / "canonical" / "acceptance" / "ac-contracts.json"
    data = json.loads(src.read_text())
    out = [GENERATED_HEADER.format(src="docs/L3-system-requirements/canonical/acceptance/ac-contracts.json")]
    out.append("# 受入条件 検証契約カタログ（AC contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §4）"))
    out.append("> 各 AC に GWT＋fixture・観測点・期待状態・DB 差分・証跡・禁止副作用・エラー型・対象更新を必須化\n")
    out.append("> （G-AC-COVERAGE／G-AC-POLARITY）。旧体系の受入条件は historical 記録のみ（現行分母は本カタログ）。\n\n")
    pol = {"normal": "正常", "reject": "拒否", "boundary-recovery": "境界・復旧"}
    cur = None
    for it in data["items"]:
        if it["target"] != cur:
            cur = it["target"]
            out.append(f"## {cur}\n\n")
        out.append(f"### {it['id']}（{pol[it['polarity']]}）\n\n")
        out.append(f"- **Given**: {it['given']} ／ **When**: {it['when']} ／ **Then**: {it['then']}\n")
        out.append(f"- **fixture**: {it['fixture']}\n")
        out.append(f"- **観測点**: {it['observation_point']} ／ **期待状態**: {it['expected_state']}\n")
        out.append(f"- **期待 DB 差分**: {it['expected_db_delta']} ／ **期待証跡**: {it['expected_evidence']}\n")
        out.append(f"- **禁止副作用**: {it['forbidden_side_effects']} ／ **エラー型**: {it['error_type']}\n")
        if it.get("verification_aspects"):
            out.append(f"- **NFR 検証観点**: {' '.join(it['verification_aspects'])}\n")
        out.append(f"- **対象更新**: {it['target_update']} ／ **TC**: {' '.join(it['tc']) or '（割当待ち）'}\n\n")
    return L3 / "views" / "ac-catalog_v0.1.md", "".join(out)


def render_tc_catalog() -> tuple[Path, str]:
    src = L3 / "verification" / "tc-contracts.json"
    data = json.loads(src.read_text())
    out = [GENERATED_HEADER.format(src="docs/L3-system-requirements/verification/tc-contracts.json")]
    out.append("# テストケース 検証契約カタログ（TC contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §5）"))
    out.append("> 全 AC 検証契約と双方向接続（G-TRACE-BIDIR）。状態・DB 差分・証跡・禁止副作用・外部呼出回数を検証。\n")
    out.append("> 旧体系のテストケースは historical 記録のみ（現行分母は本カタログ）。\n\n")
    out.append("| TC | kind | AC | NFR 検証観点 | 検証する状態 | DB 差分 | 証跡 | 禁止副作用の不在 | 外部呼出 | slice |\n")
    out.append("|---|---|---|---|---|---|---|---|---|---|\n")
    for it in data["items"]:
        aspects = ' '.join(it.get('verification_aspects', [])) or '—'
        out.append(f"| {it['id']} | {it['kind']} | {' '.join(it['ac'])} | {aspects} | {it['verifies_state']} | "
                   f"{it['verifies_db_delta']} | {it['verifies_evidence']} | {it['verifies_forbidden']} | "
                   f"{it['external_calls']} | {it['slice']} |\n")
    out.append("\n## NFR 観点別 assert\n\n")
    for it in data["items"]:
        if it.get("aspect_assertions"):
            out.append(f"- **{it['id']}**: " + " ／ ".join(
                f"`{k}` → {v}" for k, v in it["aspect_assertions"].items()) + "\n")
    out.append("\n検証手段（method）の全文は JSON 正本を参照。\n")
    return L3 / "views" / "tc-catalog_v0.1.md", "".join(out)


def render_cmp_contracts() -> tuple[Path, str]:
    src = L4 / "canonical" / "components" / "cmp-contracts.json"
    data = json.loads(src.read_text())
    out = [GENERATED_HEADER.format(src="docs/L4-basic-design/canonical/components/cmp-contracts.json")]
    out.append("# コンポーネント設計契約（CMP/SCM contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §6）"))
    out.append("> 各 CMP/SCM に 11 観点の設計契約を必須化（G-CMP-INTERFACE）。独立設計書とペアで読む。\n\n")
    for it in data["items"]:
        out.append(f"## {it['id']} {it['title']}\n\n")
        out.append(f"- **提供 interface**: {'／'.join(it['provided_interfaces'])}\n")
        out.append(f"- **要求 interface**: {'／'.join(it['required_interfaces']) or 'なし'}\n")
        out.append(f"- **責務境界**: {it['responsibility_boundary']}\n")
        out.append(f"- **依存方向**: {it['dependency_direction']}\n")
        out.append(f"- **データフロー**: {it['data_flow']}\n")
        out.append(f"- **状態所有者**: {it['state_owner']} ／ **transaction 所有者**: {it['transaction_owner']}\n")
        out.append(f"- **エラー分類**: {'／'.join(it['error_classes'])}\n")
        out.append(f"- **degradation／復旧**: {it['degradation_recovery']}\n")
        out.append(f"- **セキュリティ境界**: {it['security_boundary']}\n")
        out.append(f"- **人間判断点**: {it['human_judgement']}\n")
        tr = it["trace"]
        dd = "、".join(tr.get("design_doc", [])) or "—"
        out.append(f"- **trace**: FN = {' '.join(tr['fn']) or '—'} ／ DU = {' '.join(tr['du']) or '—'} ／ 独立設計書 = {dd}\n\n")
    return L4 / "views" / "cmp-contracts_v0.1.md", "".join(out)


def render_du_contracts() -> tuple[Path, str]:
    src = L5 / "canonical" / "apis" / "du-contracts.json"
    data = json.loads(src.read_text())
    out = [GENERATED_HEADER.format(src="docs/L5-detailed-design/canonical/apis/du-contracts.json")]
    out.append("# 詳細設計 実装契約（DU contracts）v" + data["version"] + "\n\n")
    out.append(status_line(data, "JSON 内容正本の生成ビュー（全層再降下 §7）"))
    out.append("> 各 DU に公開 API 署名・DbC・例外・tx 境界・冪等性・競合制御・AC/TC/UT 対応を必須化\n")
    out.append("> （G-DU-API／G-DU-DBC／G-DU-ERROR／G-DU-DATA／G-API-UT）。\n\n")
    for it in data["items"]:
        out.append(f"## {it['id']} `{it['module']}`（{it['cmp']}）\n\n")
        for api in it["apis"]:
            out.append(f"### {api['api_id']} `{api['signature']}`\n\n")
            pre = "／".join(f"[{c['clause_id']}] {c['text']}" for c in api["precondition"])
            post = "／".join(f"[{c['clause_id']}] {c['text']}" for c in api["postcondition"])
            out.append(f"- **pre**: {pre}\n")
            out.append(f"- **post**: {post}\n")
            raises = "／".join(f"[{r['clause_id']}] `{r['type']}`（{r['when']}）"
                              for r in api["raises"]) or "なし"
            out.append(f"- **raises**: {raises} ／ **pure**: {'yes' if api['pure'] else 'no'}\n")
            uts = "／".join(f"{u['nodeid']}→{'・'.join(u['clause_refs'])}" for u in api["ut"])
            out.append(f"- **UT→契約節**: {uts}\n\n")
        out.append(f"- **DTO・値オブジェクト**: {'／'.join(it['dtos']) or 'なし'}\n")
        out.append(f"- **状態遷移**: {'／'.join(it['state_transitions']) or 'なし'}\n")
        out.append(f"- **DB read**: {'／'.join(it['db_read']) or 'なし'} ／ **DB write**: {'／'.join(it['db_write']) or 'なし'}\n")
        out.append(f"- **tx 境界**: {it['transaction_boundary']}\n")
        out.append(f"- **pure／副作用端点**: {it['purity']}\n")
        out.append(f"- **冪等性**: {it['idempotency']} ／ **retry/resume**: {it['retry_resume']}\n")
        out.append(f"- **競合制御**: {it['concurrency']}\n")
        out.append(f"- **ログ・証跡**: {it['logging_evidence']}\n")
        out.append(f"- **依存 API**: {'／'.join(it['depends_on_apis']) or 'なし'}\n")
        tr = it["trace"]
        fd = "、".join(tr.get("feature_design", [])) or "—"
        out.append(f"- **trace**: AC = {' '.join(tr['ac']) or '—'} ／ TC = {' '.join(tr['tc']) or '—'} ／ "
                   f"UT = {' '.join(tr['ut']) or '—'} ／ 機能別設計 = {fd}\n\n")
    return L5 / "views" / "du-contracts_v0.1.md", "".join(out)


RENDERERS = [
    render_requirement_candidates,
    render_br_contracts,
    render_tc_catalog,
    render_cmp_contracts,
    render_du_contracts,
    _make_contract_renderer("docs/L3-system-requirements/canonical/functional/fr-contracts.json", "fr-contracts_v0.1.md",
                            "機能要件 実行契約（FR contracts）",
                            "各 FR に 18 観点の実行・検証・拒否・復旧契約を必須化（G-REQ-CONTRACT／G-INVARIANT-TRACE）。"),
    _make_contract_renderer("docs/L3-system-requirements/canonical/strategy/sr-contracts.json", "sr-contracts_v0.1.md",
                            "戦略要件 実行契約（SR contracts）",
                            "各 SR に 18 観点の実行契約を必須化。brief／TLP／revision の正準は strategy-learning-contract。"),
    render_nfr_contracts,
    render_ac_catalog,
]


def main() -> int:
    check = "--check" in sys.argv
    dirty = []
    for fn in RENDERERS:
        # 正本の欠落は fail-close（黙殺 skip は同期成功と区別できないため禁止 — Sol major 対応）
        path, content = fn()
        current = path.read_text() if path.exists() else None
        content = _markdown_autolink_urls(content.rstrip("\n")) + "\n"
        if current != content:
            if check:
                dirty.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(content)
                print(f"rendered: {path.relative_to(ROOT)}")
        else:
            print(f"up-to-date: {path.relative_to(ROOT)}")
    if check and dirty:
        print(f"STALE VIEWS (re-run render_views.py): {dirty}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
