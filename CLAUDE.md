# CLAUDE.md — エージェント作業規律

人間向けの概要・文書一覧は README.md。本ファイルはエージェントの作業ルールの正本。

## 正本と現在地

- 北極星: docs/L0-charter/marketing-harness-charter_v0.4.md（confirmed）。進行はスライス駆動。
- 文書ペア（HELIX 式・片肺禁止）3 層: ①要件定義↔③検証設計（TC 59）、②基本設計↔④総合テスト設計
  （ITC 16）、⑤詳細設計↔⑥単体テスト設計（DU 23／TC 全割当＋UT 10）。
  戦略層は strategy-loop-requirements／strategy-learning-contract ↔ strategy-loop-design／
  strategy-loop-test-design のペア（SR 16／SCM 10／STC。JSON 正本 = json/strategy/）。
  DDL・状態遷移・evidence 型・WF 契約の正準は docs/requirements/s0-contract_v0.1.md。
- 現在地: **S0 設計クロージャー完了・独立レビュー Go**（2026-08-01。判定の正本 = docs/governance/reviews/sol-review-s0-design-02.json。S0 スケルトン＋要求/要件/検証契約の再降下＋
  S0 基本・詳細・単体テスト設計。**S1 以降は planned** — AC→TC→CMP/SCM→DU→API→UT の再降下が未完）。実装・検証の入力は
  **契約正本**（JSON）を用いる: BR = json/br/br-contracts.json／FR = json/fr/fr-contracts.json／
  SR = json/strategy/sr-contracts.json／NFR = json/nfr/nfr-contracts.json／AC = json/ac/ac-contracts.json／
  TC = json/verification/tc-contracts.json／CMP = design/json/cmp-contracts.json／
  DU = design/json/du-contracts.json。MD は **生成ビュー**（`python3 scripts/render_views.py`。手編集禁止）。
  次 = **S0.1 実装**（DU-01〜12 の API 29 本を test-first。各 API の UT は du-contracts の apis[].ut が正本）。
  着手時は `tests/skip-budget.json` の `s0_impl_started` を true にする（以後 G-S0-TEST-REALITY が
  S0.1 対象 UT の skip を CI で落とす — 実 red→green を強制）。実装パッケージは **`src/helix/`**。
  進行は HELIX-HARNESS の工程・Gate・PR 経路に従う（本リポジトリ内の独自手動進行はしない）。
  S0.1 の完了条件 = 割当 UT の red→green ＋ **STC-I-01〜06**（AC-SR-01〜06）green ＋ skip 上限の引き下げ
  （tests/skip-budget.json — 引き上げには approvals.md の構造化 PO 承認行が必要）。

## 編集の鉄則（CI が fail-close で強制）

1. 要件・設計の編集は **MD＋JSON 正本＋baseline を同一コミット**で:
   `python3 scripts/validate_requirements.py --update-baseline` を実行してからコミットする。
2. ゲートの追加・変更はスクリプトと docs/governance/requirements-gates.md を同時更新（G-WIRING が検査）。
3. 分母（BR/REQ/FR/AC/FN/CMP/ITC…）の縮小・confirmed の降格・ゲート削減は禁止（ラチェット）。
4. status: confirmed を書く前に docs/governance/approvals.md に承認行を追加（G-CONFIRM）。
5. push 前に `python3 scripts/validate_requirements.py`（全ゲート — 件数の正本は
   docs/governance/baseline.json の gate_count。散文に件数をハードコードしない）と markdownlint を通す。

## Codex 実装エージェント（.claude/agents/）

性能順 Sol＞Terra＞Luna。割当: codex-sol=設計判断・レビュー（low）／codex-terra=実装主力（medium）／
codex-luna=定型・変換（high）／codex-imagen=画像生成。

```bash
codex exec -s workspace-write -m gpt-5.6-<sol|terra|luna> -c model_reasoning_effort="<low|medium|high>" "<task>" </dev/null
```

- バックグラウンド実行時は **必ず `</dev/null`**（stdin 待ちハング防止）。継続は `codex exec resume --last`。
- レビューは Sol に依頼し、明示的な「Go」を得てから完遂とする。

## 実装フェーズのペア規律（TDD × DDD）

第 3 層は文書ペア（⑤↔⑥）＋コードペア（モジュール↔pytest）の二重: ⑥が TC 59 の DU 割当と
テストファイル対応（tests/unit/test_<module>.py）の正本。

1. **test-first 必須**: 実装単位ごとに、⑥の割当テスト（TC＋UT）を pytest 化して赤を確認してから
   実装する（red→green→refactor）。テストのない実装コミットは差戻し。
2. 各 S0 更新の完了条件 = 該当 TC 全 green ＋ ④の該当 ITC green ＋ 前更新の回帰 green。
3. **DDD 規律**: ドメイン語彙は glossary が正本（ユビキタス言語）。kernel/gates/evidence の層分離、
   検証済み値オブジェクト（PairPass 等）でゲート通過を型強制、永続化はストア層のみ。
4. 実装開始時に pytest ジョブと「CMP↔テストファイル対応」のペアゲートを CI に追加する
   （テストのない CMP を fail-close で検出）。

## 実装時の設計制約（基本設計 §1・§4 の要点)

- fail-close 一元化（拒否はゲート層と状態機械に集約）／単方向依存（cli→kernel→gates→基盤）。
- コネクタは業務状態を直接書かない。永続化はストア副層・kernel・evidence API 経由のみ。
- 1 状態遷移 = 1 transaction。外部操作は「operation_log 証跡化 → 状態遷移」の順。
- 時刻・乱数は Clock/Rng 注入。設定値はすべて config 行（ハードコード禁止）。
- 外部書込みは Docker WP のみ（本番 WP・実 GA4 への書込みは禁止 — 環境契約 §6）。
