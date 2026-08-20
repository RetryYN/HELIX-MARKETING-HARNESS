# CLAUDE.md — エージェント作業規律

人間向けの概要・文書一覧は README.md。本ファイルはエージェントの作業ルールの正本である。
ファイル名は既存運用との互換性のため維持しており、Claude Code の導入・実行を前提にしない。
Codex／CI／人間作業者も本規約を共通入力として適用する。

## 作業境界（最優先）

- 変更対象は **本リポジトリのみ**。`RetryYN/HELIX-HARNESS`、`RetryYN/TAKUMI_CMO-Claude_Cowark`、
  `RetryYN/AGENT-NEO` は
  **read-only 参照**。worktree 作成・branch・commit・push・PR／Issue・PLAN／Reverse 成果物を含む
  一切の書き込みを禁止する。**他リポジトリへの書き込みは、指示に含まれていても着手前に PO へ確認する**
  （撤回記録: docs/00-authority/audits/cross-repository-write-incident-2026-08-01.md）。

## 正本と現在地

- 旧baselineの上位根拠: docs/L0-charter/canonical/marketing-harness-charter_v0.4.md（confirmed）。新要求への適用は
  manifestの`applicability_policy`により`revalidation_required`であり、要求cutover前の実装入力にしない。
- **成果物の権威正本 = docs/00-authority/artifact-manifest.json**。全現役成果物の artifact ID・階層・
  slice・domain（業務領域のみ — slice 名・階層名の混同は G-MANIFEST-DOMAIN が拒否）・canonical／view
  パス・ペア・継承関係・承認 digest をここで一意化する（G-AUTHORITY-MANIFEST 系が fail-close 検査）。
  manifest に未登録の成果物を confirmed にできない。**置換は `supersedes`（対象は superseded／archived
  でなければならない）、拡張は `extends_artifact_ids`、依存は `depends_on_artifact_ids`** と分け、
  実在 ID・自己参照なし・循環なしを G-MANIFEST-RELATION が検査する。
- 物理構造は L 工程で分離する: `docs/00-authority/`／`docs/L0-charter/`〜`docs/L6-feature-design/`／
  `docs/archive/`。`docs/archive/` と `docs/00-authority/superseded/` は**凍結**
  （実装入力・現役導線にできない）。
- **正本の形式は `authority_format` が決める**（G-CANONICAL-FORMAT）: 機械実装入力・台帳・schema・
  DDL は `canonical/` の JSON／SQL、自動生成された人間向け表現は `views/` の Markdown（**手編集禁止**）。
  canonical Markdown は**人間承認そのものが正本の文書**（charter／policy／adr／audit-record／
  design-doc／requirement-doc／test-design）に限る。FR／SR／NFR／AC／TC／CMP／DU など JSON 正本を
  持つ成果物の Markdown は必ず `views/` に置く。
- **status は 2 軸**（G-STATUS-CONSISTENCY）: `authority_status`（active／superseded／archived＝現役
  導線上の位置だけ）と `lifecycle_status`（draft／confirmed／planned／in_progress／completed＝内容
  成熟度だけ）。markdown 正本は YAML frontmatter に `artifact_id`／`lifecycle_status`／`slice` を持ち、
  manifest と一致させる（生成ビューは frontmatter を持たない）。承認 digest は frontmatter を**含む
  全文**に対して計算する（ゲートが正本として読む slice／traces を承認束縛の外へ出さない）。
- 旧baseline L6のslice 4点一致（G-SLICE-PLACEMENT）は構造再検証専用の資料であり、現行のslice・
  強制実装正本ではない。旧baselineでは物理ディレクトリ（S0／S1／later）、`manifest.slice`、frontmatterの
  `slice`、frontmatter `traces` のFR／SR sliceを照合し、後続要求の言及を `forward_refs` へ記録していた。
  新要求のslice・forward_refs・実装降下先はPO freeze後に新正本から再選択する。
- 旧baselineの文書ペア（HELIX 式・再検証資料。現行要求・設計・実装入力ではない）3 層: ①要件定義↔③検証設計、
  ②基本設計↔④総合テスト設計（ITC 16）、⑤詳細設計↔⑥単体テスト設計（DU 23）。旧baselineの
  pair_artifact_id は manifest の構造整合を再検証するためだけに読む。新要求のペアはfreeze後に新正本から再降下する。
- 旧baselineの戦略層は strategy-loop-requirements／strategy-learning-contract ↔ strategy-loop-design／
  strategy-loop-test-design の再検証用ペア（SR 19／SCM 10／STC）である。現行戦略の受入・実装正本ではない。
- 旧baselineのDDL・状態遷移・evidence型・WF契約は再検証資料であり、現行要求・設計・実装入力ではない。
  構造ゲートは旧資料の整合確認に限定し、方式はPO凍結後に新正本から選択する。
- 現在地（この 8 行が正本。他所へ現在地を書かない。完了宣言は**更新単位**で、
  docs/L6-feature-design/S0/update-closure.json の宣言と実態の一致を G-UPDATE-DESIGN-CLOSURE が検査する）:
  - 旧baselineの物理配置・manifest登録・既存ゲート配線まで完了。新要求の権威cutoverは未完了
  - S0.1 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
  - S0.2 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
  - S0.3 旧confirmed設計は再検証待ち（旧基準の未被覆 API 0・新要求の実装未承認）
  - Kanban／bounded domain／media binding は旧L3に要求記述だけ存在し、`revalidation_required`。FN／CMP降下とPO凍結は未完了
  - ロジックツリー／統合因果分析（SR-17〜19）も旧L3に要求記述だけ存在し、AC／FN／CMP降下とPO凍結は未完了
  - 製品runtimeの配置方針はVPS `helix-worker`を採択済み。ただし製品runtime／service／Web UIは未実装・未配備である。Web UI・承認・通知要求を再定義中で、L2以降は未設計として再降下する
  - HELIX-HARNESS はread-only参照。Python-native開発loopを方法論bridgeとして部分適応済みであり、完全adoptedではない。L2は5点書式の物理templateだけを用意した`bridge`で、内容は旧要求の評価用draftである。要件確定エンジン、IR/refinement/semantic admission、新要求からのL2再作成が全て閉じるまで導入済み・要求確定・設計済みと名乗らない
- **旧baselineの契約 JSON 群（再検証資料・現行実装入力ではない）**は下記9本。`requirements_baseline_status=revising`または
  `implementation_authorized=false`の間は実装入力に使用せず、新要求承認後にL2〜L6と同時に再降下する:
  BR = docs/L1-business-requirements/canonical/br/br-contracts.json ／
  FR = docs/L3-system-requirements/canonical/functional/fr-contracts.json ／
  SR = docs/L3-system-requirements/canonical/strategy/sr-contracts.json ／
  NFR = docs/L3-system-requirements/canonical/nonfunctional/nfr-contracts.json ／
  AC = docs/L3-system-requirements/canonical/acceptance/ac-contracts.json ／
  TC = docs/L3-system-requirements/verification/tc-contracts.json ／
  CMP = docs/L4-basic-design/canonical/components/cmp-contracts.json ／
  DU/API/UT = docs/L5-detailed-design/canonical/apis/du-contracts.json ／
  L6 責務/API/AC/TC/UT = docs/L6-feature-design/S0/implementation-units.json。
  生成ビューは `python3 scripts/render_views.py`（手編集禁止）。
- 旧baselineの L6 implementation-units.json は手編集の confirmed 再検証資料（生成物ではない。schema =
  同ディレクトリの implementation-unit.schema.json・追加プロパティ禁止）。責務は `api_ref`
  （API 安定 ID 1 件・配列禁止）と `clause_refs`（当該 API の契約節 ID）で接続し、`ac_refs` の AC
  （`verifies_clause_refs`）と `ut_refs` の UT（`apis[].ut[].clause_refs`）が**同じ契約節**を
  参照していなければならない。API 名・テスト名・日本語語彙の部分一致を接続の根拠にしない。
  全 API 契約節は AC 被覆か理由付き `na_reason`（閉じた語彙 — `呼出側義務:`／`配線時保証:`／
  `他 API で検証:`／`単体検証:`／`受入基準未設定:`）のいずれかを持つ（G-L6-IMPLEMENTATION-TRACE）。
  API は `verification_level`（acceptance／unit／integration）で分かれ、内部 API は `internal_reason` を
  持ち UT が契約節を直接検証する。`受入基準未設定:` は N/A ではなく**未解決 gap**で、AC が 1 節も
  検証していない acceptance API は docs/L6-feature-design/S0/uncovered-apis.json に
  `resolution_update`（DU の fn_ids → updates.json から機械導出 — G-UNCOVERED-API-UPDATE）付きで登録する。
  更新ごとの設計クロージャー宣言は docs/L6-feature-design/S0/update-closure.json が正本で、
  実態との一致と現在地との一致を G-UPDATE-DESIGN-CLOSURE が検査する（slice と update を混同しない）。
- 現行分母は **AC=252 ／ TCC=258 ／ API=59 ／ API_UT=218** のみ。旧体系の分母は baseline.json の
  `historical_counts` にのみ保持し、現役導線では使わない。
- 次 = **要求基準の再定義とPO決定**。VPS製品Web UI・承認・通知を含むBR〜NFRの意味衝突を閉じ、
  L2以降を新要求から再降下する。`requirements_baseline_status=approved`、
  `implementation_authorized=true`、新baselineの独立Goレビューが同時に成立するまでS0.1実装を開始しない。
  既存`src/helix/`のDU-01〜12は旧baselineの再検証対象であり、freeze・L2〜L6再設計・admission後に
  再利用又は置換を判断する。現時点の実装候補とは扱わず、旧契約のUT・skip budget・closureを
  新要求の完了条件として流用しない。

- HELIX-HARNESS 適応の正本は `docs/00-authority/template/helix-harness-alignment.json`、判断記録は
  `docs/00-authority/adr/ADR-012-helix-harness-template-adoption.md`、開発環境契約は
  `docs/00-authority/development/development-environment_v0.1.md`。外部テンプレートは固定 commit の read-only 参照とし、
  `requirements-ir/` や Bun／Node runtime を本リポジトリへ二重導入しない。
- discovery の前段監査証跡は `docs/00-authority/development/requirement-discovery-events.json`（schema は同ディレクトリ）で
  append-only に保持する。既存 BR/REQ/FR/NFR/AC/TC 契約の代替ではなく、導入前の履歴は backfill せず、契約・runtime を直接 mutation しない。

## 編集の鉄則（CI が fail-close で強制）

1. 要件・設計の編集は **正本 JSON＋生成ビュー＋manifest＋baseline を同一コミット**で:
   `python3 scripts/render_views.py` → `python3 tools/gates/run_all.py --update-baseline` の順に実行する。
2. ゲートの追加・変更は tools/gates/ のモジュールと docs/00-authority/requirements-gates.md を
   同時更新（G-WIRING が検査）。ゲート本体を scripts/validate_requirements.py に書かない（互換ラッパー）。
3. 分母（BR/REQ/FR/FN/CMP/ITC/DU…）の縮小・confirmed の降格・ゲート削減は禁止（ラチェット）。
4. `lifecycle_status: confirmed` を書く前に docs/00-authority/approvals/approvals.md に承認行を追加
   （G-CONFIRM）し、manifest の `approval_digest` を内容に一致させる（G-MANIFEST-STATUS）。
5. push 前に `python3 tools/gates/run_all.py`（全ゲート — 件数の正本は
   docs/00-authority/baselines/baseline.json の gate_count。散文に件数をハードコードしない）と
   markdownlint・pytest を通す。**例外**: 要求cutover系ゲート（G-REQ-STRATEGY-TEST-AUTHORITY／
   G-REQ-LEGACY-\*-MEANING-INVENTORY／G-REQ-OPEN-REFINEMENTS）の「PO 未承認・未凍結による赤」は
   `requirements_baseline_status=revising` の間は**意図した赤**であり push を妨げない
   （根拠: docs/00-authority/development/requirement-definition-workflow_v0.1.md）。この例外を
   他ゲートへ拡大しない。上記以外のゲートの赤、及び cutover 系でも PO 未承認以外の原因による赤は
   通常どおり修正してから push する。

6. 要件候補〜L3再検証と旧L2 5点書式の評価用draftの開発入口は `make setup`／`make doctor`／`make requirements`／
   `make docs-check`／`make lint`／`make typecheck`／`make imports`／`make build`／`make gates`／`make test`／`make check`。
   新要求からのL2画面設計はrequirements freeze後の再降下・別admissionまで開始しない。Python 3.14 と `uv.lock` を固定点にし、credential を repository・DB・ログへ書かない。`make test` は
   pytest → test outcome 正規化 → 全ゲートの順に、同期済み uv 環境で実行する。

## Codex 実装エージェント（.claude/agents/）

通常タスクは **codex-luna（effort max）** を既定にする。選択肢の分岐、高リスク変更、セキュリティ・正本境界、
最終レビューだけ **codex-sol（effort low）** へエスカレーションする。codex-terra（medium）は Luna が利用できない
場合の互換 adapter に限定し、設計判断の主力にしない。画像は codex-imagen へ分離する。

```bash
codex exec -s workspace-write -m gpt-5.6-<sol|terra|luna> -c model_reasoning_effort="<low|medium|max>" "<task>" </dev/null
```

- effort の割当は Sol=`low`／Terra=`medium`／Luna=`max`。`.claude/agents/` は互換入口であり、Claude Code の導入・実行を前提にしない。
- バックグラウンド実行時は **必ず `</dev/null`**（stdin 待ちハング防止）。継続は `codex exec resume --last`。
- レビューは Sol に依頼し、明示的な「Go」を得てから完遂とする。判定はレビュー成果物 JSON が正本。

## 旧baselineの実装フェーズ規律（再検証資料・現行実装入力ではない）

旧baselineでは、文書とコードのペア、S0の受入テスト、DDDの層分離及びテストゲートを実装フェーズの規律として
採用していた。これらは旧DU／CMP／S0の再検証資料であり、現行要求の実装単位・テスト対応・層構造を拘束しない。
新要求のfreeze後に、必要な実装単位・AC/TC/UT対応・CI gateを新しい正本から再降下する。

- 旧baselineでは、実装単位に割当テストを先に作り、red→green→refactorで進める運用だった。
- 旧baselineでは、S0更新の完了を旧TC・旧ITC・旧回帰テストのgreenで判定していた。
- 旧baselineでは、glossary、kernel、gates、evidence及びstoreの層分離と、PairPass等の値オブジェクトを採用していた。
- 旧baselineでは、実装開始時にpytestとCMP↔テストファイル対応のCI gateを追加していた。

## 旧baselineの設計制約（再検証資料・現行実装入力ではない）

以下は旧baselineの基本設計に存在した制約を、再検証資料として記録する。現行要求・設計・実装を拘束しない。
新要求のPO凍結・設計再降下後に、必要な制約だけを別途選択し、正本・manifest・baseline・独立レビューへ束縛する。

- 旧baselineでは fail-close をゲート層と状態機械へ集約し、cli→kernel→gates→基盤という単方向依存を採用していた。
- 旧baselineではコネクタから業務状態を直接書かず、ストア副層・kernel・evidence APIを経由させていた。
- 旧baselineでは1状態遷移=1 transaction、外部操作はoperation_logの証跡化後に状態遷移する方式だった。
- 旧baselineでは時刻・乱数をClock/Rngへ注入し、設定値をconfig行へ置く方式だった。
- 旧baselineでは Docker WP のみ外部writeを許可していたが、現在は`revalidation_required`であり、新baselineの許可ではない。
  現行候補では個別refinementのPO凍結とrelease受入まで全媒体writeを無効にし、Web UI内inboxも要求候補に留める。
  Notion審査同期と旧Discord承認tupleも`revalidation_required`であり、通知・媒体投稿・開発PR通知を相互流用しない。
- 旧baselineでは上流戦略正本をDBで保護し、briefの状態遷移、valid_until、TLPの空配列を特定のDDL/API方式で扱っていた。
  上流戦略正本の保護方式は現行設計では未選択であり、DB/API/DDL方式をここから継承しない。
