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
- **L6 のスライスは 4 点一致**（G-SLICE-PLACEMENT）: 物理ディレクトリ（S0／S1／later）＝
  `manifest.slice` ＝ frontmatter の `slice` ＝ frontmatter `traces` の FR／SR のスライス。
  後続スライスの要求への言及は `forward_refs` に過不足なく宣言する（S0 文書は将来拡張点だけを
  持ち、強制実装は S1 側の文書が正本）。
- 文書ペア（HELIX 式・片肺禁止）3 層: ①要件定義↔③検証設計、②基本設計↔④総合テスト設計（ITC 16）、
  ⑤詳細設計↔⑥単体テスト設計（DU 23）。ペアの正本は manifest の `pair_artifact_id`。
  戦略層は strategy-loop-requirements／strategy-learning-contract ↔ strategy-loop-design／
  strategy-loop-test-design のペア（SR 19／SCM 10／STC）。
  DDL・状態遷移・evidence 型・WF 契約の正準は docs/L3-system-requirements/canonical/s0-contract_v0.1.md。
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
- 旧設計基準の契約正本は下記9本。`requirements_baseline_status=revising`または
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
- **第 9 正本 implementation-units.json は手編集の confirmed 正本**（生成物ではない。schema =
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
  その後の条件付き実装候補は`src/helix/`のDU-01〜12だが、旧契約のUT・skip budget・closureを
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
   markdownlint・pytest を通す。

6. 要件定義〜L3 と L2 画面設計の開発入口は `make setup`／`make doctor`／`make requirements`／
   `make docs-check`／`make lint`／`make typecheck`／`make imports`／`make build`／`make gates`／`make test`／`make check`。
   Python 3.14 と `uv.lock` を固定点にし、credential を repository・DB・ログへ書かない。`make test` は
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

## 実装フェーズのペア規律（TDD × DDD）

第 3 層は文書ペア（⑤↔⑥）＋コードペア（モジュール↔pytest）の二重: du-contracts の `apis[].ut` が
テストファイル対応（tests/unit/test_<module>.py）の正本。

1. **test-first 必須**: 実装単位ごとに、割当テスト（TC＋UT）を pytest 化して赤を確認してから
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
- 旧baselineで外部writeを許可していたのは Docker WP のみだが、これも`revalidation_required`である。新baselineは
  個別refinementのPO凍結とrelease受入まで全媒体writeを無効とする。Web UI内inboxは初期要求候補だが
  refinement凍結まで実装しない。Notion審査同期と旧Discord承認tupleは
  `revalidation_required`であり、新baselineの許可ではない。通知・媒体投稿・開発PR通知を相互流用しない。
- 上流戦略正本は DB で保護する: brief の状態遷移は draft→active／active→superseded|retired のみ、
  valid_until の延長は禁止（新版発行）、TLP の空配列判定は `json_array_length()` を使う。
