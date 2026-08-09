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

GENERATED_HEADER = (
    "<!-- GENERATED FILE — 編集禁止。正本は {src}。再生成 = python3 scripts/render_views.py -->\n\n"
)

STATUS_LABEL = {"confirmed": "confirmed", "draft": "draft（再降下中）", "superseded": "superseded"}


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
    return f"> status: **{st}**{tail}。{note}\n"


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
