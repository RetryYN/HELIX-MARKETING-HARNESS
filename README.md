# 🧬 HELIX-MARKETING-HARNESS

> TAKUMI-CMO のマーケティング頭脳を、HELIX 流「証跡と機械ゲートで品質を守るハーネス」に載せ替えるプロジェクト。

- **正本**: このリポジトリ（RetryYN/HELIX-MARKETING-HARNESS）
- **機能ソース**: [TAKUMI_CMO-Claude_Cowark](https://github.com/RetryYN/TAKUMI_CMO-Claude_Cowark)（read-only 参照）
- **北極星**: [charter v0.4](docs/L0-charter/canonical/marketing-harness-charter_v0.4.md)（status=confirmed）
- **成果物の権威正本**: [artifact-manifest.json](docs/00-authority/artifact-manifest.json)
  — 全現役成果物の artifact ID・階層・canonical／view パス・ペア・承認 digest を一意に登録する

## 現在地

- S0 設計クロージャー完了
- S1 以降は planned
- S0.1 実装未着手
- HELIX-HARNESS 取込は未実施・PO 判断待ち

判定の正本は [レビュー成果物](docs/00-authority/reviews/)（対象コミットと成果物 digest に束縛され、
G-REVIEW-BINDING が検証する）。散文で判定を宣言しない。
S0.1 の進行方法（本リポジトリ内か他経路か）は PO が決定する。

## 文書構造（L 工程）

物理構造は L0〜L6 の工程階層で分離する。`canonical/` は正本、`views/` は生成ビュー（手編集禁止）、
`docs/archive/` と `docs/00-authority/superseded/` は凍結（実装入力にできない）。

| 階層 | 内容 | 主な成果物 |
|---|---|---|
| [00-authority](docs/00-authority/) | 権威層 | artifact manifest・[承認ログ](docs/00-authority/approvals/approvals.md)・[baseline](docs/00-authority/baselines/baseline.json)・[レビュー](docs/00-authority/reviews/)・[監査](docs/00-authority/audits/)・[ゲート台帳](docs/00-authority/requirements-gates.md)・[ADR](docs/00-authority/adr/)・[リスク登録簿](docs/00-authority/risk-register_v0.1.md) |
| [L0-charter](docs/L0-charter/) | 北極星 | [charter v0.4](docs/L0-charter/canonical/marketing-harness-charter_v0.4.md) |
| [L1-business-requirements](docs/L1-business-requirements/) | 業務要求 | [BR 背骨 38](docs/L1-business-requirements/canonical/br-backbone_v0.1.md)・[媒体別業務要求 70](docs/L1-business-requirements/canonical/br-media_v0.1.md)・[要求一覧 52](docs/L1-business-requirements/canonical/requirement-list_v0.1.md)・[ループ/タスク/WF](docs/L1-business-requirements/canonical/loop-task-workflow_v0.1.md)・[用語集](docs/L1-business-requirements/canonical/glossary_v0.1.md)・[BR 契約ビュー](docs/L1-business-requirements/views/br-contracts_v0.1.md) |
| [L2-prototypes](docs/L2-prototypes/) | プロトタイプ | 未着手（workflows／screens／operating-scenarios の枠のみ） |
| [L3-system-requirements](docs/L3-system-requirements/) | システム要件 | [要件定義 FR36/NFR10](docs/L3-system-requirements/canonical/functional/requirements_v0.1.md)・[機能一覧 61](docs/L3-system-requirements/canonical/functional/function-list_v0.1.md)・[媒体別詳細要件](docs/L3-system-requirements/canonical/functional/media-requirements_v0.1.md)・[S0 契約](docs/L3-system-requirements/canonical/s0-contract_v0.1.md)・[上流戦略ループ要件](docs/L3-system-requirements/canonical/strategy/strategy-loop-requirements_v0.1.md)・[戦略学習契約](docs/L3-system-requirements/canonical/strategy/strategy-learning-contract_v0.1.md)・[検証設計](docs/L3-system-requirements/verification/verification-design_v0.1.md)・[AC カタログ](docs/L3-system-requirements/views/ac-catalog_v0.1.md)・[TC カタログ](docs/L3-system-requirements/views/tc-catalog_v0.1.md) |
| [L4-basic-design](docs/L4-basic-design/) | 基本設計 | [基本設計](docs/L4-basic-design/canonical/basic-design_v0.1.md)・[戦略ループ設計](docs/L4-basic-design/canonical/components/strategy-loop-design_v0.1.md)・独立設計書（[外部 IF](docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md)／[DB](docs/L4-basic-design/canonical/data/db-design_v0.1.md)／[状態機械](docs/L4-basic-design/canonical/state-machine/state-machine-design_v0.1.md)／[承認](docs/L4-basic-design/canonical/approval/approval-design_v0.1.md)／[ブランド隔離](docs/L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)）・[技術選定](docs/L4-basic-design/canonical/tech-stack_v0.1.md)・[総合テスト設計](docs/L4-basic-design/integration-tests/integration-test-design_v0.1.md)・[CMP 契約ビュー](docs/L4-basic-design/views/cmp-contracts_v0.1.md) |
| [L5-detailed-design](docs/L5-detailed-design/) | 詳細設計 | [詳細設計](docs/L5-detailed-design/canonical/detailed-design_v0.1.md)・[エラー分類](docs/L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md)・[migration 規則](docs/L5-detailed-design/canonical/migrations/migration-rules.json)・[単体テスト設計](docs/L5-detailed-design/unit-tests/unit-test-design_v0.1.md)・[DU 契約ビュー](docs/L5-detailed-design/views/du-contracts_v0.1.md) |
| [L6-feature-design](docs/L6-feature-design/) | 機能別設計 | [S0 の 11 本](docs/L6-feature-design/S0/)（戦略改訂・brief・TLP・証跡・migration・状態機械・ブランド隔離・KPI handoff・キャンペーン・外部操作・承認）＋[S0.1 計画](docs/L6-feature-design/S0/plan-s0.1.json)。S1／later は空 |

## 実装入力（契約正本 8 本）

実装・検証の入力は **JSON 契約正本**だけを用いる（MD は生成ビュー、または人が読む正本文書）。

| 種別 | 正本 |
|---|---|
| BR | [br-contracts.json](docs/L1-business-requirements/canonical/br/br-contracts.json) |
| FR | [fr-contracts.json](docs/L3-system-requirements/canonical/functional/fr-contracts.json) |
| SR | [sr-contracts.json](docs/L3-system-requirements/canonical/strategy/sr-contracts.json) |
| NFR | [nfr-contracts.json](docs/L3-system-requirements/canonical/nonfunctional/nfr-contracts.json) |
| AC | [ac-contracts.json](docs/L3-system-requirements/canonical/acceptance/ac-contracts.json) |
| TC | [tc-contracts.json](docs/L3-system-requirements/verification/tc-contracts.json) |
| CMP/SCM | [cmp-contracts.json](docs/L4-basic-design/canonical/components/cmp-contracts.json) |
| DU/API/UT | [du-contracts.json](docs/L5-detailed-design/canonical/apis/du-contracts.json) |

現行分母は **AC=211 ／ TCC=217 ／ API=58 ／ API_UT=189**（件数の正本は
[baseline.json](docs/00-authority/baselines/baseline.json)）。旧体系の分母は `historical_counts` にのみ保持する。

## 機械ゲート

要件整合ゲートは [tools/gates/](tools/gates/) の工程別モジュールへ分割され、
`tools/gates/run_all.py` が入口（`scripts/validate_requirements.py` は互換ラッパー）。
CI（Docs CI / Python CI）で push・PR ごとに fail-close 実行する。
台帳は [requirements-gates.md](docs/00-authority/requirements-gates.md)、件数の正本は baseline.json の `gate_count`。

```bash
python3 tools/gates/run_all.py
```

## 実装エージェント

Codex CLI を実装エージェントとして登録済み（`.claude/agents/`）: **codex-sol**（最高性能・effort low —
設計判断・レビュー）／ **codex-terra**（中位・medium — 実装主力）／ **codex-luna**（軽量・high —
定型・変換）／ **codex-imagen**（image_gen — 静的画像生成、BR-M-GENAI-4）。性能順は Sol＞Terra＞Luna。

## 次の一手

**S0.1 実装**（DB・状態機械・ゲート・証跡 — s0-contract §7 の更新分割、CMP-01〜06＝DU-01〜12 が対象）。
着手は自動検出される（`src/helix/` への実装追加・S0.1 PLAN の `in_progress` 化・DU-01〜12 の API 実装の
いずれか）。着手後は対象 UT の skip／xfail／NotImplementedError／空 assert が CI で落ち、
coverage 下限が 80% へ引き上がる。
