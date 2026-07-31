# 🧬 HELIX-MARKETING-HARNESS

> TAKUMI-CMO のマーケティング頭脳を、HELIX 流「証跡と機械ゲートで品質を守るハーネス」に載せ替えるプロジェクト。

- **正本**: このリポジトリ（RetryYN/HELIX-MARKETING-HARNESS）
- **機能ソース**: [TAKUMI_CMO-Claude_Cowark](https://github.com/RetryYN/TAKUMI_CMO-Claude_Cowark)（read-only 参照）
- **北極星**: [docs/L0-charter/marketing-harness-charter_v0.4.md](docs/L0-charter/marketing-harness-charter_v0.4.md)（status=confirmed。v0.4 = 上流戦略インフィニティループ再強化）

## ドキュメント

- [BR 背骨](docs/requirements/br-backbone_v0.1.md) — 業務要求 31 項目（confirmed）
- [媒体別業務要求](docs/requirements/br-media_v0.1.md) — BR-M・21 媒体の構造調査値と PO 判断 8 件（confirmed）
- [要求一覧](docs/requirements/requirement-list_v0.1.md) — REQ 45 項目・優先度・対応 FR 付き（confirmed）
- [要件定義書](docs/requirements/requirements_v0.1.md) — FR 36 / NFR 10・AC・S0 受入基準・トレース（confirmed）
- [機能一覧](docs/requirements/function-list_v0.1.md) — FN 61 機能・スライス配分（confirmed）
- [媒体・手法別詳細要件](docs/requirements/media-requirements_v0.1.md) — 19 媒体を 7 観点で（confirmed）
- [ループ・タスク・ワークフロー要件](docs/requirements/loop-task-workflow_v0.1.md) — 業務全体の実行モデル 3 分解（計画/充填/制作/運用含む）＋PoC 登録簿（confirmed）
- [S0 契約書](docs/requirements/s0-contract_v0.1.md) — 正準 DDL・状態遷移表・WF 実行契約・環境契約・S0.1〜S0.3 分割（confirmed）
- [上流戦略ループ要件](docs/requirements/strategy-loop-requirements_v0.1.md) — SR 16・意味モデル 12・ペルソナ禁止・S0 境界（confirmed）
- [戦略学習契約](docs/requirements/strategy-learning-contract_v0.1.md) — brief／TLP／revision の 3 契約＋コンテンツ 5 宣言（confirmed）
- [戦略層 JSON 正本](docs/requirements/json/strategy/) — 12 schema・媒体役割台帳・コンテンツ企画契約・fixture（ゲートの negative test 入力）
- [検証設計書](docs/requirements/verification-design_v0.1.md) — 要件定義との対（pair）。TC 59・全 AC カバー・拒否系 27（confirmed）
- [JSON 正本](docs/requirements/json/) — 要件エンティティの機械可読正本（実装・変換の入力。MD と同期）
- [技術・ツール選定書](docs/requirements/tech-stack_v0.1.md) — スタック集約と再検討トリガー（confirmed）
- [用語集](docs/requirements/glossary_v0.1.md) — 独自語の正本（confirmed）
- [基本設計書](docs/design/basic-design_v0.1.md) — ②。CMP 13 コンポーネント・S0 25 FN 完全被覆（confirmed）
- [総合テスト設計書](docs/design/integration-test-design_v0.1.md) — ④。基本設計との対（pair）。ITC 16・拒否系 7・E2E 含む（confirmed）
- [詳細設計書](docs/design/detailed-design_v0.1.md) — ⑤。DU 23 モジュール・公開 API 仕様（confirmed）
- [単体テスト設計書](docs/design/unit-test-design_v0.1.md) — ⑥。詳細設計との対（pair）。TC 59 全割当＋UT 10（confirmed）
- [戦略ループ設計](docs/design/strategy-loop-design_v0.1.md) — SCM 10・S0 最小変更／S1 上流スライス配分（confirmed）
- [戦略層テスト設計](docs/design/strategy-loop-test-design_v0.1.md) — STC（ゲート×fixture 常設＋S0.1/S1 pytest）（confirmed）
- [設計 JSON 正本](docs/design/json/) — CMP/ITC/DU/UTC/SCM/STC 台帳の機械可読正本（MD と同期）
- [TAKUMI 素材カタログ](docs/design/takumi-catalog_v0.1.md) — スライスが引くプル型カタログ

### ガバナンス

- [ADR](docs/governance/adr/) — 大局判断 6 本（言語・接続原則・ブラウザ三段構え・データ正本・WP REST 直・公式 API 経路）
- [リスク登録簿](docs/governance/risk-register_v0.1.md) — RSK-01〜09・緩和策・撤退条件
- [要件定義ギャップ監査](docs/governance/requirements-gap-audit-2026-07-30.md) — HELIX 品質バー突合と是正記録
- [要件整合ゲート台帳](docs/governance/requirements-gates.md) — CI で毎 push 実行される fail-close ゲート群
  （件数の正本は [baseline.json](docs/governance/baseline.json) の gate_count）
- [承認ログ](docs/governance/approvals.md)

## 実装エージェント

Codex CLI を実装エージェントとして登録済み（`.claude/agents/`）: **codex-sol**（最高性能・effort low —
設計判断・レビュー）／ **codex-terra**（中位・medium — 実装主力）／ **codex-luna**（軽量・high —
定型・変換）／ **codex-imagen**（image_gen — 静的画像生成、BR-M-GENAI-4）。性能順は Sol＞Terra＞Luna。

## 現在地

スライス駆動で構築中（L0 charter confirmed 2026-07-30）。
**要件定義＋基本設計＋詳細設計 完遂・全文書 confirmed（2026-07-31 PO 承認）** — §99 全 8 判断クローズ、
整合ゲート CI 常時実行（件数の正本 = baseline.json の gate_count）、①↔③（TC 59）・②↔④（ITC 16）・
⑤↔⑥（DU 23／UTC 69）の HELIX 式文書ペア 3 層成立。
**2026-08-01 外部レビュー対応（P0 是正）完遂** — 状態機械の決定性、DDL の lease/attempt/external_operations、
承認 digest 束縛、X ブラウザ書込みの事前禁止ほか（[是正台帳](docs/governance/review-remediation-2026-08-01.md)）。
**2026-08-01 上流戦略インフィニティループ再強化 完遂** — charter v0.4、SR 16／意味モデル 12 schema、
brief／TLP／revision の 3 契約、strategic_briefs・TLP テーブル（DDL 25 テーブル・トリガ 10）、
戦略ゲート 11 件を追加（fixture negative test 常設）。
次: **S0.1 実装**（DB・状態機械・ゲート・証跡 — s0-contract §7 の更新分割、CMP-01〜06 が対象）。
