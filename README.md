# 🧬 HELIX-MARKETING-HARNESS

> TAKUMI-CMO のマーケティング頭脳を、HELIX 流「証跡と機械ゲートで品質を守るハーネス」に載せ替えるプロジェクト。

- **正本**: このリポジトリ（RetryYN/HELIX-MARKETING-HARNESS）
- **機能ソース**: [TAKUMI_CMO-Claude_Cowark](https://github.com/RetryYN/TAKUMI_CMO-Claude_Cowark)（read-only 参照）
- **北極星**: [docs/L0-charter/marketing-harness-charter_v0.3.md](docs/L0-charter/marketing-harness-charter_v0.3.md)（status=confirmed）

## ドキュメント

- [BR 背骨](docs/requirements/br-backbone_v0.1.md) — 業務要求 31 項目（confirmed）
- [媒体別業務要求](docs/requirements/br-media_v0.1.md) — BR-M・21 媒体の構造調査値と PO 判断 8 件（confirmed）
- [要求一覧](docs/requirements/requirement-list_v0.1.md) — REQ 45 項目・優先度・対応 FR 付き（confirmed）
- [要件定義書](docs/requirements/requirements_v0.1.md) — FR 36 / NFR 10・AC・S0 受入基準・トレース（confirmed）
- [機能一覧](docs/requirements/function-list_v0.1.md) — FN 61 機能・スライス配分（confirmed）
- [媒体・手法別詳細要件](docs/requirements/media-requirements_v0.1.md) — 19 媒体を 7 観点で（confirmed）
- [ループ・タスク・ワークフロー要件](docs/requirements/loop-task-workflow_v0.1.md) — 業務全体の実行モデル 3 分解（計画/充填/制作/運用含む）＋PoC 登録簿（confirmed）
- [S0 契約書](docs/requirements/s0-contract_v0.1.md) — 正準 DDL・状態遷移表・WF 実行契約・環境契約・S0.1〜S0.3 分割（confirmed）
- [検証設計書](docs/requirements/verification-design_v0.1.md) — 要件定義との対（pair）。TC 59・全 AC カバー・拒否系 27（confirmed）
- [JSON 正本](docs/requirements/json/) — 要件エンティティの機械可読正本（実装・変換の入力。MD と同期）
- [技術・ツール選定書](docs/requirements/tech-stack_v0.1.md) — スタック集約と再検討トリガー（confirmed）
- [用語集](docs/requirements/glossary_v0.1.md) — 独自語の正本（confirmed）
- [TAKUMI 素材カタログ](docs/design/takumi-catalog_v0.1.md) — スライスが引くプル型カタログ

### ガバナンス

- [ADR](docs/governance/adr/) — 大局判断 6 本（言語・接続原則・ブラウザ三段構え・データ正本・WP REST 直・公式 API 経路）
- [リスク登録簿](docs/governance/risk-register_v0.1.md) — RSK-01〜09・緩和策・撤退条件
- [要件定義ギャップ監査](docs/governance/requirements-gap-audit-2026-07-30.md) — HELIX 品質バー突合と是正記録
- [要件整合ゲート台帳](docs/governance/requirements-gates.md) — CI で毎 push 実行される fail-close ゲート 38 本
- [承認ログ](docs/governance/approvals.md)

## 実装エージェント

Codex CLI を実装エージェントとして登録済み（`.claude/agents/`）: **codex-sol**（最高性能・effort low —
設計判断・レビュー）／ **codex-terra**（中位・medium — 実装主力）／ **codex-luna**（軽量・high —
定型・変換）／ **codex-imagen**（image_gen — 静的画像生成、BR-M-GENAI-4）。性能順は Sol＞Terra＞Luna。

## 現在地

スライス駆動で構築中（L0 charter confirmed 2026-07-30）。
**要件定義 完遂・全文書 confirmed（2026-07-31 PO 承認）** — §99 全 8 判断クローズ、
整合ゲート 38 本 CI 常時実行、対の検証設計（TC 59）成立。
次: **S0.1 実装**（DB・状態機械・ゲート・証跡 — s0-contract §7 の更新分割に従う）。
