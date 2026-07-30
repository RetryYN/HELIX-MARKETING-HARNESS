# CLAUDE.md — エージェント作業規律

人間向けの概要・文書一覧は README.md。本ファイルはエージェントの作業ルールの正本。

## 正本と現在地

- 北極星: docs/L0-charter/marketing-harness-charter_v0.3.md（confirmed）。進行はスライス駆動。
- 文書ペア（HELIX 式・片肺禁止）: ①要件定義↔③検証設計（TC 59）、②基本設計↔④総合テスト設計（ITC 16）。
  DDL・状態遷移・evidence 型・WF 契約の正準は docs/requirements/s0-contract_v0.1.md。
- 現在地: 要件定義＋基本設計 完遂（全文書 confirmed）。次 = **S0.1 実装**
  （CMP-01〜06、s0-contract §7 の更新分割。src/helix/ と tests/ を新設 — 基本設計 §2）。

## 編集の鉄則（CI が fail-close で強制）

1. 要件・設計の編集は **MD＋JSON 正本＋baseline を同一コミット**で:
   `python3 scripts/validate_requirements.py --update-baseline` を実行してからコミットする。
2. ゲートの追加・変更はスクリプトと docs/governance/requirements-gates.md を同時更新（G-WIRING が検査）。
3. 分母（BR/REQ/FR/AC/FN/CMP/ITC…）の縮小・confirmed の降格・ゲート削減は禁止（ラチェット）。
4. status: confirmed を書く前に docs/governance/approvals.md に承認行を追加（G-CONFIRM）。
5. push 前に `python3 scripts/validate_requirements.py`（51 ゲート）と markdownlint を通す。

## Codex 実装エージェント（.claude/agents/）

性能順 Sol＞Terra＞Luna。割当: codex-sol=設計判断・レビュー（low）／codex-terra=実装主力（medium）／
codex-luna=定型・変換（high）／codex-imagen=画像生成。

```bash
codex exec -s workspace-write -m gpt-5.6-<sol|terra|luna> -c model_reasoning_effort="<low|medium|high>" "<task>" </dev/null
```

- バックグラウンド実行時は **必ず `</dev/null`**（stdin 待ちハング防止）。継続は `codex exec resume --last`。
- レビューは Sol に依頼し、明示的な「Go」を得てから完遂とする。

## 実装時の設計制約（基本設計 §1・§4 の要点)

- fail-close 一元化（拒否はゲート層と状態機械に集約）／単方向依存（cli→kernel→gates→基盤）。
- コネクタは業務状態を直接書かない。永続化はストア副層・kernel・evidence API 経由のみ。
- 1 状態遷移 = 1 transaction。外部操作は「operation_log 証跡化 → 状態遷移」の順。
- 時刻・乱数は Clock/Rng 注入。設定値はすべて config 行（ハードコード禁止）。
- 外部書込みは Docker WP のみ（本番 WP・実 GA4 への書込みは禁止 — 環境契約 §6）。
