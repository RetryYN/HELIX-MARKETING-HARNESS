---
artifact_id: AUTH-DEVELOPMENT-ENVIRONMENT
lifecycle_status: draft
slice: cross
---

# 開発環境契約 v0.1

> status: **draft**。要件定義〜L3 要求確定と L2 プロトタイプ設計を行うための環境を定義する。

## 目的と境界

この環境は、HELIX-HARNESS の開発ループ（doctor／docs／gates／test）を、本リポジトリの Python-native な
正本・ゲート体系へ適応したものである。対象は要件定義、契約 JSON の更新、生成ビュー、L2 画面設計、検証であり、
製品ランタイムの実装や外部媒体への書き込みを開始するものではない。

- Python 3.14 以上、`uv.lock` を依存解決の固定点とする
- パッケージは `src/helix/` の一層だけを使用する
- 正本は契約 JSON／DDL／状態遷移／evidence schema と artifact-manifest。MD は生成ビューまたは人間承認の正本文書
- credential は repository、DB、ログ、成果物に保存しない。外部書き込みは既存の allow-list と承認境界に従う
- VPS（現在の `helix-worker`）とローカルは同じコマンド列を実行し、VPS 固有の秘密や経路を文書に書かない

## コマンド契約

| コマンド | 目的 | 変更の有無 |
|---|---|---|
| `make setup` | `uv sync --group dev` で依存と `.venv` を整える | `.venv` のみ |
| `make doctor` | Python、uv、正本パス、テンプレート適応、生成ビュー、全ゲートを検査 | なし |
| `make docs` | 契約 JSON から生成ビューを再生成 | 生成ビュー |
| `make docs-check` | 生成ビューが正本と一致するか検査 | なし |
| `make lint` | ruff による静的検査 | なし |
| `make typecheck` | pyproject.toml で定義した mypy 対象を検査 | なし |
| `make imports` | import-linter で単方向依存を検査 | なし |
| `make build` | hatchling で source distribution と wheel を生成 | `dist/`（gitignore） |
| `make gates` | `tools/gates/run_all.py` を実行 | なし |
| `make test` | pytest → `collect_test_outcome.py` → 全ゲートを同一 uv 環境で実行 | レポートはローカル一時 |
| `make requirements` | 要件定義ワークフロー、テンプレート対応、prospective discovery ledger を表示・検査 | なし |
| `make check` | lint → typecheck → imports → docs-check → build → test（pytest → outcome → gates）の順に実行 | `dist/` とローカルレポート |

`uv` が無い環境では `make setup` は fail-close で停止し、`uv` の導入を促す。システム Python やグローバル
パッケージを暗黙に変更しない。

## 要件定義の完了条件

1. 要件候補に stable ID、actor／task／workflow、価値、制約、未決事項がある。
2. 候補はプロトタイプまたは反証可能な観測を経て、BR／REQ／FR／NFR の正本へ降下する。
3. 各 FR／NFR は AC と TC へ双方向に接続し、拒否・境界・復旧を含む。
4. L2 の画面は 5 点セットで入口・状態・失敗・戻る操作・アクセシビリティを記録する。
5. PO の承認前は `draft` のままとし、confirmed 化には manifest、承認 digest、baseline、レビューを同一変更で更新する。
6. discovery ledger は `coverage_start_commit` 以後だけを append-only に記録する監査証跡であり、既存契約 JSON の
   代替や製品 runtime への自動 mutation ではない。契約変更は proposal と decision、または `deferred:` 理由付き withdrawal を要する。

## 参照

- [HELIX-HARNESS 適応 ADR](../adr/ADR-012-helix-harness-template-adoption.md)
- [テンプレート対応表](../template/helix-harness-alignment.json)
- [要件定義ワークフロー](requirement-definition-workflow_v0.1.md)
- [discovery event ledger](requirement-discovery-events.json) と [strict schema](requirement-discovery-event.schema.json)
