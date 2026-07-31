# 戦略ループ設計 v0.1

> status: **confirmed**（2026-08-01 PO 承認 — 上流戦略インフィニティループ再強化指示。AI 起草）
> pair: [strategy-loop-test-design_v0.1.md](strategy-loop-test-design_v0.1.md)（戦略層テスト設計 — HELIX 式文書ペア）
> 上位文書: [strategy-loop-requirements_v0.1.md](../requirements/strategy-loop-requirements_v0.1.md)（SR）／
> [strategy-learning-contract_v0.1.md](../requirements/strategy-learning-contract_v0.1.md)（契約 3 本）
> 機械可読正本: [json/strategy-components.json](json/strategy-components.json)（SCM 台帳）
> 位置づけ: 上流戦略ループの実装コンポーネント分解。**基本設計②の CMP 13・S0 25 FN は変更しない** —
> S0 分は既存 CMP（DB 基盤・kernel・証跡）への最小拡張として実装し、上流の生成系（SCM-05〜10）は
> S1 以降の上流戦略スライスで実装する（SR-15）。

---

## 1. 層の位置づけ

```text
上流戦略ループ（LP-U: リサーチ → 市場分析 → マーケティング戦略 → 行動計画 → 改善）
  出力 = 意味モデル正本（json/strategy/ schema 準拠、append-only 版管理）
  下り = strategic_brief（SCM-02/03）
  上り = tactical_learning_packet（SCM-04）→ 改善工程の revision（SCM-08）
下流戦術ループ（LP-D/W/M/E: 媒体別の非同期回転 — 既存設計のまま）
背骨 = KPI ツリー（観測のみ。戦略正本ではない — SR-12）
```

## 2. コンポーネント台帳（SCM）

| SCM | 名称 | 責務 | 実装先 | S |
|---|---|---|---|---|
| SCM-01 | strategy-store | strategic_briefs／tactical_learning_packets の永続化（append-only。ストア副層） | 既存 CMP-05（DB 基盤）拡張 — DU-10/11（FN-701/702）の DDL・migration 範囲 | S0 |
| SCM-02 | brief-issuer | brief の版発行・digest 計算・supersedes 連鎖（S0 はシードコマンド） | 既存 CMP-02（オーケストレータ）拡張 — DU-02（FN-102） | S0 |
| SCM-03 | brief-gate | 下流 loop_run 開始時の有効 brief 検証（active・digest 一致・期間内。fail-close） | 既存 CMP-01（状態機械カーネル）拡張 — DU-01（FN-101）の start ガード | S0 |
| SCM-04 | tlp-generator | 下流終端到達時の TLP 生成（観測/解釈/因果/判定/推奨の分離充填） | 既存 CMP-02（オーケストレータ）拡張 — DU-02（FN-102） | S0 |
| SCM-05 | observation-store | market_observation の取込・鮮度管理（expires_at） | 新規（上流戦略スライス） | S1 |
| SCM-06 | market-analyzer | market_model／segment_context／problem_model の生成・版管理 | 新規 | S1 |
| SCM-07 | strategy-composer | value_hypothesis〜strategic_choice の生成（棄却案保持・反証条件必須） | 新規 | S1 |
| SCM-08 | revision-engine | TLP 集約 → strategy_revision 提案 → 複数根拠・反証・時間差の評価（自動 accept 制限） | 新規 | S1 |
| SCM-09 | media-role-ledger | 媒体役割語彙台帳の管理（config 経由の追加・変更） | 新規 | S1 |
| SCM-10 | recognition-content-gate | コンテンツ企画の 5 宣言（content-plan-contract）検証の実行時強制 | 新規（ゲート層） | S1 |

依存方向は既存の単方向依存（cli→kernel→gates→基盤）に従う。SCM-05〜10 は既存外殻（ループ状態機械）に
触らず追加できる — strategic_briefs／TLP テーブルと schema が S0 で先行確定しているため（SR-15）。

## 3. S0 に入れる最小変更（それ以外は S1）

1. DDL: strategic_briefs／tactical_learning_packets テーブル＋保護トリガ 4 本＋
   loop_runs.strategic_brief_id/digest 列と lower CHECK（s0-contract §2 が正準・適用検証済み）。
2. 状態機械: loop_runs `pending → start` ガードへの brief 検証の追加（s0-contract §3.1）。
3. シード: versioned brief の投入コマンド（S0 受入基準 5 の「シードコマンド経由」に従う）。
4. TLP 生成: WP 週次回転の終端で 1 件生成（観測=計測 evidence 参照、解釈・判定は分離フィールド）。
5. 上流モデル 12 schema・媒体役割台帳・コンテンツ企画契約の JSON 正本確定（本コミット）。

S0 の FN 数（25）・CMP 数（13）・DU 数（23）は不変。上記 1〜4 は CMP-05／DU-10/11（FN-701/702 —
DDL・migration）、CMP-01／DU-01（FN-101 — start ガード）、CMP-02／DU-02（FN-102 — 発行・生成）の
実装範囲内の拡張であり、各正本（fn.json／components.json／detailed.json）の該当 ID に戦略層責務を
追記済み。対応する検証は戦略層テスト設計（STC — STC-I-01〜06 が該当 DU のテストファイルに載る）が持つ。

## 4. 不変条件（実装時に型・トリガ・経路で強制）

- 下流→上流の書込みは TLP INSERT のみ（上流正本テーブルへの書込み API をコネクタ層・下流 kernel に公開しない）。
- 上流正本の変更 = supersedes_id 付き新版 INSERT のみ（UPDATE/DELETE はトリガ拒否）。
- brief digest は発行時に内容から決定的に計算し、run 保持値と照合する。
- revision accepted は支持根拠 2 件以上（単一 KPI 変動の自動反映禁止）。
- 時刻・乱数は Clock/Rng 注入、値はすべて config 行（既存設計制約を継承）。
