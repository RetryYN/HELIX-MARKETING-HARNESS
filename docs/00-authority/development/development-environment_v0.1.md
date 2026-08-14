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

- Python 3.14、`uv.lock` を依存解決の固定点とし、setup／CI は `uv sync --frozen` で lock 外の解決を拒否する
- パッケージは `src/helix/` の一層だけを使用する
- 正本は契約 JSON／DDL／状態遷移／evidence schema と artifact-manifest。MD は生成ビューまたは人間承認の正本文書
- credential は repository、DB、ログ、成果物に保存しない。本書の開発コマンドは外部媒体、製品runtime、
  Discord、GitHubへwriteしない。既存allow-listは旧baselineの再検証資料であり、開発コマンドのwrite許可ではない
- VPS（現在の `helix-worker`）とローカルは同じコマンド列を実行し、VPS 固有の秘密や経路を文書に書かない

## 製品 runtime との意味境界

> 旧L3〜L6文書中の「環境契約 §6」は、本書の節番号ではなく
> `docs/L3-system-requirements/canonical/s0-contract_v0.1.md` の「§6 環境契約（S0）」を指す。
> 本書は開発環境の契約であり、製品の外部write許可、credential保存方式、runtime配置を新たに承認しない。

| 概念 | 開発環境での意味 | 製品 runtime との関係 |
|---|---|---|
| cross-review | author と別 principal／execution が commit・tree・artifact digest を read-only で検査する | 投稿可否や業務承認を行わない |
| PR 対応依頼 | GitHub PR の current HEAD、check、未解決 finding を開発者へ知らせる | Discord `approval_request` を使わず、`ApprovalTransport`／`approvals`へ接続しない |
| harness memory | commit 済み基準点に束縛した開発継続状態、判断根拠、次アクション | 製品DB、要求正本、discovery ledger、approval evidence の代替にしない |
| Discord 承認補助通知 | 開発環境の機能ではない | ADR-013で初期範囲外。将来採用時も認証済みWeb UIへのdeep-linkだけを送り、Discord単体でapprove／rejectを確定しない |
| Discord 運用通知 | 開発環境の機能ではない | 一方向の運用通知候補。投稿可否の判断を要求せず、承認補助・媒体投稿とは別policy／principal／receiptにする |
| Discord 媒体投稿 | 開発環境の機能ではない | BR-M-DC／MR-DCの再検証対象。将来採用時も承認補助とは別のBot principal・policy・account・workflowを要求する |

現行のレビュー JSON／ログと `G-REVIEW-BINDING` は cross-review の基礎を提供するが、GitHub からのPR対応依頼と
repository-local harness memory はまだ実装されていない。HELIX-HARNESS の仕組みは移植可能だが、現在は
`deferred` とし、次の条件を満たす別変更まで有効化・完了宣言しない。

- PR 対応依頼は GitHub PR／check／review の read または明示許可された comment／review request に限定し、
  current HEAD と finding ID に冪等束縛する。Discord、会社 Slack、製品通知 transport へ送らない。
- memory は append-only event と導出 projection を分離し、commit／tree／artifact digest、actor、occurred_at、
  next action、supersession を schema で必須化する。stale な projection を再開根拠にしない。
- credential、token、PII、外部本文、未承認の要求本文を memory に保存しない。要求変更は discovery ledger と
  PO 承認工程へ戻し、memory から正本を直接変更しない。
- schema、保存先、compaction／保持、foreign edit、mutation test、doctor／CI gate が揃って初めて `adapted` とする。

## コマンド契約

| コマンド | 目的 | 変更の有無 |
|---|---|---|
| `make setup` | `uv sync --frozen --group dev` で固定済み依存と `.venv` を整える | `.venv` のみ |
| `make doctor` | Python、uv、正本パス、テンプレート適応、生成ビュー、全ゲートを検査 | なし |
| `make docs` | 契約 JSON から生成ビューを再生成 | 生成ビュー |
| `make docs-check` | 生成ビューが正本と一致するか検査 | なし |
| `make lint` | ruff による静的検査 | なし |
| `make typecheck` | pyproject.toml で定義した mypy 対象を検査 | なし |
| `make imports` | import-linter で単方向依存を検査 | なし |
| `make build` | hatchling で source distribution と wheel を生成 | `dist/`（gitignore） |
| `make gates` | `tools/gates/run_all.py` を実行 | なし |
| `make test` | pytest → `collect_test_outcome.py` → 全ゲートを同一 uv 環境で実行 | レポートはローカル一時 |
| `make requirements` | テンプレート、discovery、IR、意味差分、双方向trace、refinement、PO承認 admission／authority cutover を検査。未確定なら非0終了 | なし |
| `make check` | lint → typecheck → imports → docs-check → build → test（pytest → outcome → gates）の順に実行 | `dist/` とローカルレポート |

`uv` が無い環境では `make setup` は fail-close で停止し、`uv` の導入を促す。システム Python やグローバル
パッケージを暗黙に変更しない。

CI は同一 ref の古い実行を cancel し、全 job に timeout を設ける。checkout は
`persist-credentials: false` とし、検証 job に push credential を残さない。`.python-version`、pyproject、setup-uv、
ruff、mypy の Python 3.14 pin とこれらの CI 境界は `G-TEMPLATE-ALIGNMENT` が fail-close で検査する。

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
