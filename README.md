# 🧬 HELIX-MARKETING-HARNESS

> TAKUMI-CMO のマーケティング頭脳を、HELIX 流「証跡と機械ゲートで品質を守るハーネス」に載せ替えるプロジェクト。

- **正本**: このリポジトリ（RetryYN/HELIX-MARKETING-HARNESS）
- **機能ソース**: [TAKUMI_CMO-Claude_Cowark](https://github.com/RetryYN/TAKUMI_CMO-Claude_Cowark)（read-only 参照）
- **旧baselineの上位根拠**: [charter v0.4](docs/L0-charter/canonical/marketing-harness-charter_v0.4.md)（status=confirmed／新要求への適用は`revalidation_required`）
- **成果物の権威正本**: [artifact-manifest.json](docs/00-authority/artifact-manifest.json)
  — 全現役成果物の artifact ID・階層・slice・正本形式（`authority_format`）・現役位置（`authority_status`）・
  内容成熟度（`lifecycle_status`）・canonical／view パス・ペア・承認 digest を一意に登録する

## 現在地

- 旧baselineの物理配置・manifest登録・既存ゲート配線まで完了。新要求の権威cutoverは未完了
- S0.1 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
- S0.2 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
- S0.3 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
- Kanban／bounded domain／media binding は旧L3に要求記述だけ存在し、`revalidation_required`。FN／CMP降下とPO凍結は未完了
- ロジックツリー／統合因果分析（SR-17〜19）も旧L3に要求記述だけ存在し、AC／FN／CMP降下とPO凍結は未完了
- 製品runtimeの配置方針はVPS `helix-worker`を採択済み。ただし製品runtime／service／Web UIは未実装・未配備である。Web UI・承認・通知要求を再定義中で、L2以降は未設計として再降下する
- HELIX-HARNESS はread-only参照。Python-native開発loopを方法論bridgeとして部分適応済みであり、完全adoptedではない。L2は5点書式の物理templateだけを用意した`bridge`で、内容は旧要求の評価用draftである。要件確定エンジン、IR/refinement/semantic admission、新要求からのL2再作成が全て閉じるまで導入済み・要求確定・設計済みと名乗らない
- 未承認の要求候補は [要求候補レビュー](docs/00-authority/views/requirement-candidates_v0.1.md) で意味軸・三極性AC・未解決事項を確認する。これはrefinement正本からの生成viewであり、PO承認・設計・実装入力ではない

判定の正本は [レビュー成果物](docs/00-authority/reviews/)（対象コミットと成果物 digest に束縛され、
G-REVIEW-BINDING が検証する）。散文で判定を宣言しない。
S0.1 の進行方法（本リポジトリ内か他経路か）は PO が決定する。

要求再定義の入力は[意味再監査](docs/00-authority/audits/requirements-semantic-reaudit-2026-08-14.md)と
[製品要求ベースライン候補](docs/L1-business-requirements/canonical/product-requirement-baseline-candidate_v0.1.md)。
いずれもdraftであり、未決のPO判断を設計で補完しない。

## 文書構造（L 工程）

物理構造は L0〜L6 の工程階層で分離する。`canonical/` は正本、`views/` は生成ビュー（手編集禁止）、
`docs/archive/` と `docs/00-authority/superseded/` は凍結（実装入力にできない）。

| 階層 | 内容 | 主な成果物 |
|---|---|---|
| [00-authority](docs/00-authority/) | 権威層 | artifact manifest・[承認ログ](docs/00-authority/approvals/approvals.md)・[baseline](docs/00-authority/baselines/baseline.json)・[レビュー](docs/00-authority/reviews/)・[監査](docs/00-authority/audits/)・[ゲート台帳](docs/00-authority/requirements-gates.md)・[ADR](docs/00-authority/adr/)・[リスク登録簿](docs/00-authority/risk-register_v0.1.md) |
| [L0-charter](docs/L0-charter/) | 旧baselineの上位根拠・再検証対象 | [charter v0.4](docs/L0-charter/canonical/marketing-harness-charter_v0.4.md) |
| [L1-business-requirements](docs/L1-business-requirements/) | 旧baseline業務要求・新要求候補（manifest applicabilityに従う。実装入力ではない） | [BR 背骨 41](docs/L1-business-requirements/canonical/br-backbone_v0.1.md)・[媒体別業務要求 70](docs/L1-business-requirements/canonical/br-media_v0.1.md)・[要求一覧 55](docs/L1-business-requirements/canonical/requirement-list_v0.1.md)・[ループ/タスク/WF](docs/L1-business-requirements/canonical/loop-task-workflow_v0.1.md)・[用語集](docs/L1-business-requirements/canonical/glossary_v0.1.md)・[BR 契約ビュー](docs/L1-business-requirements/views/br-contracts_v0.1.md) |
| [L2-prototypes](docs/L2-prototypes/) | プロトタイプ | HELIX式5点セットの書式評価用draft。旧要求に基づくため実装入力ではなく、新要求確定後に再作成する |
| [L3-system-requirements](docs/L3-system-requirements/) | 旧システム要件・再検証資料 | [旧要件定義 FR43/NFR11](docs/L3-system-requirements/canonical/functional/requirements_v0.1.md)・[旧機能一覧 61](docs/L3-system-requirements/canonical/functional/function-list_v0.1.md)・[媒体別詳細要件](docs/L3-system-requirements/canonical/functional/media-requirements_v0.1.md)・[S0 契約](docs/L3-system-requirements/canonical/s0-contract_v0.1.md)・[上流戦略ループ要件](docs/L3-system-requirements/canonical/strategy/strategy-loop-requirements_v0.1.md)・[戦略学習契約](docs/L3-system-requirements/canonical/strategy/strategy-learning-contract_v0.1.md)・[検証設計](docs/L3-system-requirements/verification/verification-design_v0.1.md)・[AC カタログ](docs/L3-system-requirements/views/ac-catalog_v0.1.md)・[TC カタログ](docs/L3-system-requirements/views/tc-catalog_v0.1.md)。すべて新要求への適用は`revalidation_required` |
| [L4-basic-design](docs/L4-basic-design/) | 旧基本設計・再設計対象 | [基本設計](docs/L4-basic-design/canonical/basic-design_v0.1.md)・[戦略ループ設計](docs/L4-basic-design/canonical/components/strategy-loop-design_v0.1.md)・独立設計書（[外部 IF](docs/L4-basic-design/canonical/external-if/external-if-design_v0.1.md)／[DB](docs/L4-basic-design/canonical/data/db-design_v0.1.md)／[状態機械](docs/L4-basic-design/canonical/state-machine/state-machine-design_v0.1.md)／[承認](docs/L4-basic-design/canonical/approval/approval-design_v0.1.md)／[ブランド隔離](docs/L4-basic-design/canonical/brand-isolation/brand-isolation-design_v0.1.md)）・[技術選定](docs/L4-basic-design/canonical/tech-stack_v0.1.md)・[総合テスト設計](docs/L4-basic-design/integration-tests/integration-test-design_v0.1.md)・[CMP 契約ビュー](docs/L4-basic-design/views/cmp-contracts_v0.1.md)。新要求確定前の設計入力ではない |
| [L5-detailed-design](docs/L5-detailed-design/) | 旧詳細設計・再設計対象 | [詳細設計](docs/L5-detailed-design/canonical/detailed-design_v0.1.md)・[エラー分類](docs/L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md)・[migration 規則](docs/L5-detailed-design/canonical/migrations/migration-rules.json)・[単体テスト設計](docs/L5-detailed-design/unit-tests/unit-test-design_v0.1.md)・[DU 契約ビュー](docs/L5-detailed-design/views/du-contracts_v0.1.md)。新要求確定前の設計入力ではない |
| [L6-feature-design](docs/L6-feature-design/) | 旧機能別設計・再設計対象（全件`revalidation_required`／`implementation_input=false`） | [S0 の 11 本](docs/L6-feature-design/S0/)（旧要求基準のconfirmed履歴であり、新要求への再検証待ち）＋[実装単位 56 件](docs/L6-feature-design/S0/implementation-units.json)＋[未被覆 API 台帳](docs/L6-feature-design/S0/uncovered-apis.json)＋[更新別クロージャー](docs/L6-feature-design/S0/update-closure.json)＋[S0.1 計画](docs/L6-feature-design/S0/plan-s0.1.json)、[S1 の 3 本](docs/L6-feature-design/S1/)（planned）。later は空 |

## 旧設計基準の契約正本 9 本（要求改訂中は実装入力に使用不可）

下記9本は旧要求基準に対するconfirmed証跡として保持する。現在は`requirements_baseline_status=revising`かつ
`implementation_authorized=false`のため、新要求の実装入力にしない。要求承認後に全9本とL2〜L6を
再降下し、新baselineのレビューと実装許可が揃ってからのみ使用する。

| 種別 | 正本 |
|---|---|
| L6 責務/API/契約節/AC/TC/UT | [implementation-units.json](docs/L6-feature-design/S0/implementation-units.json) |
| BR | [br-contracts.json](docs/L1-business-requirements/canonical/br/br-contracts.json) |
| FR | [fr-contracts.json](docs/L3-system-requirements/canonical/functional/fr-contracts.json) |
| SR | [sr-contracts.json](docs/L3-system-requirements/canonical/strategy/sr-contracts.json) |
| NFR | [nfr-contracts.json](docs/L3-system-requirements/canonical/nonfunctional/nfr-contracts.json) |
| AC | [ac-contracts.json](docs/L3-system-requirements/canonical/acceptance/ac-contracts.json) |
| TC | [tc-contracts.json](docs/L3-system-requirements/verification/tc-contracts.json) |
| CMP/SCM | [cmp-contracts.json](docs/L4-basic-design/canonical/components/cmp-contracts.json) |
| DU/API/UT | [du-contracts.json](docs/L5-detailed-design/canonical/apis/du-contracts.json) |

現行分母は **AC=252 ／ TCC=258 ／ API=59 ／ API_UT=218**（件数の正本は
[baseline.json](docs/00-authority/baselines/baseline.json)）。旧体系の分母は `historical_counts` にのみ保持する。

第 9 正本の implementation-units.json は **手編集の confirmed 正本**であり、DU 契約や L6 文書からの
生成物ではない。責務は `api_ref`（API の安定 ID 1 件）と `clause_refs`（その API の契約節 ID）で
接続し、`ac_refs` の AC と `ut_refs` の UT が**同じ契約節**を参照していることを
G-L6-IMPLEMENTATION-TRACE が検査する（API 名・テスト名・語彙の部分一致は接続の根拠にしない）。
API の安定 ID は `API-DU01-01`、契約節は `API-DU01-01-POST-01` の形式で du-contracts.json が持つ。
API は `verification_level` で **acceptance 55 本／内部（unit）4 本**に分かれ、内部 API は
`internal_reason` を持ち UT が契約節を直接検証する。接続の実数は 責務 48 ／ 契約節 356（AC 被覆 133・
単体検証 69・呼出側義務 101・配線時保証 14・他 API で検証 1・**受入基準未設定 38**）／
UT→契約節 308 件。受入基準未設定は N/A ではなく**未解決 gap**であり、AC が 1 節も検証していない
acceptance API 6 本は [uncovered-apis.json](docs/L6-feature-design/S0/uncovered-apis.json) に
`resolution_update`（DU→FN→updates.json から機械導出）付きで登録される。経緯は
[構造トレース是正](docs/00-authority/audits/structural-trace-remediation-2026-08-02.md)と
[更新境界是正](docs/00-authority/audits/update-boundary-remediation-2026-08-02.md)が正本。

レビュー成果物の主体分離は `separation_status`（`unverified`／`self_attested`／`ci_attested`）で表す。
**過去 8 件は実行証跡を取得できないため `unverified`**、REV-S0-STRUCT-07／08 は別 principal・別 execution の
実行ログへ digest 束縛された **`self_attested`** である。そのログはレビュー実行者自身が生成したローカル成果物で
あり第三者署名ではないため、`ci_attested`（GitHub Actions の run ID・ログ URL・artifact digest へ束縛）だけが
第三者検証を名乗れる（G-REVIEW-SEPARATION）。

## 機械ゲート

要件整合ゲートは [tools/gates/](tools/gates/) の工程別モジュールへ分割され、
`tools/gates/run_all.py` が入口（`scripts/validate_requirements.py` は互換ラッパー）。
CI（Docs CI / Python CI）で push・PR ごとに fail-close 実行する。
台帳は [requirements-gates.md](docs/00-authority/requirements-gates.md)、件数の正本は baseline.json の `gate_count`。

```bash
python3 tools/gates/run_all.py
```

## HELIX-HARNESS 適応と開発環境

設計テンプレートは [固定コミットの対応表](docs/00-authority/template/helix-harness-alignment.json) と
[適応監査](docs/00-authority/audits/helix-harness-template-alignment-2026-08-13.md) で read-only 参照する。
テンプレートの方法論（要件発見、stable ID、L2 画面 5 点セット）は採用するが、旧baselineの契約 JSON 9 本
（`revalidation_required`／`implementation_input=false`）、artifact-manifest、Python ゲートを並列正本にはしない。
判断記録は [ADR-012](docs/00-authority/adr/ADR-012-helix-harness-template-adoption.md) を参照。
導入以後の発見過程は [append-only ledger](docs/00-authority/development/requirement-discovery-events.json) に記録するが、
既存契約や製品 runtime を直接更新せず、導入前の履歴は backfill しない。

HELIX-HARNESS の cross-review／PR対応依頼／harness memory は開発環境の別機構として扱う。現行レビュー成果物は
cross-reviewの基礎を提供するが、GitHub PR通知とrepository-local memoryは未実装である。旧ADR-010のDiscord
束縛承認経路は`revalidation_required`で、新要求候補の初期経路ではない。初期要求候補はVPS Web UI＋UI内inboxで、
Discordは製品通知・承認・deep-link補助・開発PR通知の経路として採用せず、community marketing投稿だけを別用途の候補として扱う。

VPS とローカルの要件定義環境は同じ入口で整える。

```bash
make setup       # uv.lock から開発依存を同期
make doctor      # Python／正本パス／生成ビュー／全ゲートを検査
make requirements
make docs-check
make lint
make typecheck
make imports
make build
make gates
make test        # pytest → outcome 正規化 → 全ゲート
make check       # lint/typecheck/imports/docs/build/test の一括検査
```

`make requirements` は単なる一覧表示ではない。HELIX由来の要件確定エンジンをPython-nativeで実行し、意味差分、
双方向trace、未完のrefinement又は不正な承認入口があれば非0で終了する。現行は要求基準を再定義中なので、赤は
実装開始を止める意図した状態であり、未解消事項を一括承認して緑へ変えてはならない。

環境の境界と要件定義の完了条件は [開発環境契約](docs/00-authority/development/development-environment_v0.1.md) と
[要件定義ワークフロー](docs/00-authority/development/requirement-definition-workflow_v0.1.md) に固定する。

## 実装エージェント

Codex CLI の振り分けは `.claude/agents/` に互換入口として残す。**codex-luna**（通常タスクの既定・effort max —
定型実装、変換、lint、テスト）を主力にし、**codex-sol**（effort low — 選択肢分岐、高リスク、最終レビュー）へ
必要な場合だけエスカレーションする。**codex-terra**（medium）は Luna が利用できない場合の互換 adapter とし、
設計判断の正本にはしない。画像は **codex-imagen**（image_gen）へ分離する。

## 次の一手

**要求基準の再定義とPO決定**。VPS製品Web UI・承認・通知を含むBR〜NFRの意味衝突を閉じ、
L2以降を新要求から再降下する。`requirements_baseline_status=approved`、
`implementation_authorized=true`、新baselineの独立Goレビューが揃うまでS0.1実装は開始しない。
