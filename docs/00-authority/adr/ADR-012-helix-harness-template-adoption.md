---
artifact_id: AUTH-ADR-ADR-012-HELIX-HARNESS-TEMPLATE-ADOPTION
lifecycle_status: draft
slice: cross
---

# ADR-012: HELIX-HARNESS 設計テンプレートの適応

> status: **draft**。設計テンプレートと、要件定義から確定までの要求エンジンを適応する方針を記録する。
> 製品ランタイムを移植する決定ではない。L2は旧要求に基づく5点書式の評価用draftだけを扱い、新要求からのL2設計は要求freeze後に再降下する。

- date: 2026-08-13
- decision_authority: PO 指示に基づく適応案（内容は draft。confirmed 化には承認 receipt が必要）
- source: [RetryYN/HELIX-HARNESS](https://github.com/RetryYN/HELIX-HARNESS/)
- source_commit: `57853db413e282b050ac5f37bab7809321c67842`
- source_policy: read-only。テンプレート側の branch／worktree／commit／issue／PR は変更しない

## 背景

本リポジトリは L0〜L6 の要件・契約・ゲートを Python-native に積み上げている。一方、HELIX-HARNESS は
L0〜L14 の V-model、要件発見イベント、stable ID による要件連鎖、L2 の 5 文書 screen 方法論、開発者向け
doctor／build／test の導線を設計テンプレートとして提供する。両者を無条件に統合すると、現在の JSON 正本と
Python ゲートが二重化されないよう、既存正本を維持したまま要求エンジンの意味契約を Python-native に移植する。

## 決定

1. **適応するもの**: V-model の工程語彙、要件発見→候補→質問→試作→仕様化→個別承認→凍結のライフサイクル、
   stable ID、requirement IR、refinement contract、semantic digest／drift、authority cutover、要件→契約→AC→TC の
   意味連鎖、旧要求評価用のL2 5点書式、doctor／docs／gates／test の開発コマンド。要件定義から確定までの
   判定順序と fail-close 条件は省略しない。新要求からのL2プロトタイプ／画面設計は要求freeze・L2〜L6再設計・別admission後に開始する。
2. **再検証資料として保持するもの**: 旧baselineの契約 JSON 9 本、DDL・状態遷移・evidence 型は
   `revalidation_required` の構造資料であり、`requirements_baseline_status=revising` 又は
   `implementation_authorized=false` の間は現行要求・設計・実装入力にしない。成果物の権威は
   artifact-manifest、検証入口は `tools/gates/run_all.py` とする。既存9正本と refinement registry を source authority として読み、
   HELIX-HARNESS v2 の manifest／stable-ID keyed shard 形式へ `candidate_non_authoritative` IR を決定的に生成・検証する。
   候補IRを手編集可能な並列正本にせず、個別PO receipt・requirements freeze・authority cutoverまでは実装入力にしない。
3. **ランタイム境界**: 本リポジトリの実装言語は Python、パッケージは `src/helix/`。テンプレートの Bun／Node
   ランタイム、`.helix` 実行系、外部サービス接続を本リポジトリの実装入力にしない。
4. **導入範囲**: 要件定義〜L3 の要求候補と、旧要求に基づくL2 5点書式の評価用draftを直ちに利用可能にする。
   新要求からのL2プロトタイプ／画面設計は、要求freeze、L2〜L6再設計、別admissionの後に新正本から再降下する。
   L4 以降と製品実装は既存スライス・PoC・承認・test-first の規律を再検証資料として扱う。
5. **外部参照の固定**: テンプレートの適応判断は source_commit に固定した read-only 監査で更新する。最新版を取り込む
   際は source_commit と対応表を更新し、旧テンプレート側へ書き込まない。
6. **最新版確認の運用**: upstream `main` は read-only で最新 SHA と source_commit からの意味差分を確認する。採用範囲に
   意味差分がなければ source_commit の固定点は維持し、適応監査へ checked SHA・差分・non-applicable の理由を記録する。
   意味差分があり採用する場合だけ、PO 判断後に source_commit、対応表、監査、gate、レビューを同一変更で更新する。
7. **discovery 証跡**: 導入以後の候補・質問・試作・観測・仕様化・承認は append-only ledger で監査する。既存の
   契約 JSON 正本や製品 runtime を直接更新せず、導入前履歴を推測 backfill しない。契約変更は proposal と decision、
   又は `deferred:` 理由付き withdrawal を通じて既存承認工程へ還流する。
8. **開発環境の適応境界**: 上流の toolchain pin と CI hygiene は Python 3.14、`uv sync --frozen`、重複実行の
   cancel、job timeout、checkout credential 非保持へ写像し、対応表ゲートで検査する。Node provider 実装は移植しない。
   一方、独立 cross-review、PR 対応依頼、継続状態／memory journal は製品機能ではなく開発環境の候補として分離し、
   Python-native な契約・保存形式・gate が揃うまでは `deferred` とする。
9. **通知の非混同**: `approval_notification`／`discord_app`／`approval_request`は旧baselineの
   Discord投稿可否承認tupleであり、現在は`revalidation_required`である。現行要求候補はVPS Web UIを
   判断入口、UI内inboxを初期通知経路とし、Discordを製品通知・承認・deep-link補助・開発PR通知へ採用しない。
   Discordのcommunity marketingは別用途の候補として分離し、旧tupleを現在の製品承認へ再導入せず、開発上のPR対応依頼にも流用しない。
   PR 通知を導入する場合は GitHub の PR／check／review 状態だけを対象とする別の開発アダプターとし、製品の
   `ApprovalTransport`、`approvals`、公開許可、運用通知へ接続しない。
10. **memory の非混同**: harness memory はセッションをまたぐ開発継続・判断根拠・次アクションの記録候補であり、
    製品の SQLite 業務状態、discovery ledger、要求契約 JSON、承認 evidence の代替にしない。credential、PII、
    外部本文、未承認の要求変更を保存せず、commit／tree／artifact digest へ束縛する。
11. **承認admission**: 未回答質問、未解決semantic dimension、authority不明、意味traceの片方向欠落、同一IDの意味差分、
    acceptance／system test未束縛、根拠digest不一致、旧正本のapplicability未確定のいずれかがあれば
    `approval_requested` と authority cutover を拒否する。一括承認へ丸めず、独立したrefinement単位で閉じる。
12. **移植完了条件**: schema、authority policy、決定的IR生成、refinement検証、semantic drift検出、生成ビュー、
    gate wiring、negative mutation test、manifest、baseline、独立reviewがすべて揃うまで `requirement-ir` を
    `adapted` と表示せず、既存要求群を新しい実装入力として承認しない。

## 対応する成果物

- 対応表の正本: `docs/00-authority/template/helix-harness-alignment.json`
- 対応表 schema: `docs/00-authority/template/helix-harness-alignment.schema.json`
- 適応監査: `docs/00-authority/audits/helix-harness-template-alignment-2026-08-13.md`
- 要件定義手順: `docs/00-authority/development/requirement-definition-workflow_v0.1.md`
- HELIX-HARNESS v2 candidate IR: `docs/00-authority/development/requirements-ir/`（生成専用。source authorityではない）
- discovery ledger/schema: `docs/00-authority/development/requirement-discovery-events.json`／`requirement-discovery-event.schema.json`
- L2 5 点セット: `docs/L2-prototypes/screens/`
- 開発環境契約: `docs/00-authority/development/development-environment_v0.1.md`

## 帰結と未決事項

- `make setup`／`make doctor`／`make docs`／`make gates`／`make test` で、VPS とローカルの同一手順を提供する。
- Bun／Node を追加しないため、テンプレートの UI ランタイムをそのまま実行することはできない。現段階では旧要求評価用の
  L2 5点書式だけを検証し、新要求からのUI設計・認証・CSRF・再認証・principal束縛の方式は要求freeze後に再降下する。
  その契約がconfirmedになるまで製品UI実装を開始しない。
- テンプレートの将来更新を追随するか、別の source_commit に固定するかは、各更新時の監査で PO が判断する。
- cross-review／PR 対応依頼と harness memory は移植可能だが、現時点では要件と境界を記録した段階で未実装である。
  Discord を開発通知へ転用せず、GitHub 開発アダプターと repository-local memory の schema／保持期間／秘密検査／
  stale 判定／mutation test を別変更で確定してから有効化する。
- 2026-08-14 に作成した8件の一括 `approval_requested` は、要求エンジン未移植の状態でadmissionを通過させたため、
  append-only台帳上でwithdrawした。意味精査後に再開する場合も新revisionのrefinementとして扱う。
