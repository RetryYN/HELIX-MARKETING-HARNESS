---
artifact_id: L4-DB-DESIGN
lifecycle_status: confirmed
slice: S0
---

# DB 設計書 v0.1（基本設計増補 — DB）

> status: **confirmed**（2026-08-01 全層再降下 §6 — AI 起草）
> 正準参照: DDL・トリガ・evidence 型契約の正準は
> [s0-contract_v0.1.md §2](../../../L3-system-requirements/canonical/s0-contract_v0.1.md)（JSON 正本 =
> [json/s0/ddl.sql](../../../L3-system-requirements/canonical/schemas/s0/ddl.sql)）。migration 規則の正準は同 §5、
> 接続規約の正準は同 §1。本書は DDL を再掲しない — 契約と矛盾したら契約を優先し本書を改訂する。
> 上位設計: [basic-design_v0.1.md](../basic-design_v0.1.md)（CMP 台帳・層分離）／
> [detailed-design_v0.1.md](../../../L5-detailed-design/canonical/detailed-design_v0.1.md)（DU-10/DU-11）
> 対応要求: FR-71（スキーマ生成）・FR-72（マイグレーション）・FR-33（config 履歴）・NFR-3・BR-I7

---

## 1. 位置づけ

s0-contract §2 が「何のテーブル・制約・トリガが存在するか」を確定済みである。本書はその上の
**設計層** — どのコンポーネントがどのテーブルを所有し、どの transaction 境界で書き、どう昇格・検証
するか — だけを確定する。列定義・CHECK・トリガ本文をここに複製することは禁止する（正本の二重化防止）。

## 2. テーブル所有マトリクス（25 テーブル）

25 テーブル = 業務 23 ＋ インフラ 2（`schema_version`・`state_transitions`）。
「書込み所有 CMP」= INSERT/UPDATE を発行してよい唯一のコンポーネント（他 CMP は read-only。
生 SQL の書込みはこの所有 CMP のストア／ストア副層に限る — 基本設計 §1.3）。
「状態所有者」= status/state 列を遷移させてよい主体。「transaction 所有者」= その書込みを含む
transaction を開閉する層。

| テーブル | 区分 | 書込み所有 CMP | 状態所有者 | transaction 所有者・境界 |
|---|---|---|---|---|
| schema_version | インフラ | CMP-05（DU-11） | — | CMP-05（1 migration = 1 tx、適用と同一 tx で INSERT） |
| state_transitions | インフラ・append-only | CMP-01（DU-01） | — | CMP-01（遷移 tx 内。拒否も rejected で記録） |
| business_profiles | 可変 | CLI init の seed（S1: FN-306 プロファイルストア） | status は人間の意思決定＋CLI | 登録 = 単一 tx（FR-34） |
| agents | 可変 | CMP-02（seed・登録） | status（active/disabled）は CMP-02 | 登録単位 tx |
| agent_executions | 可変 | CMP-02（execution 開始・終了時） | — | 開始/終了の各単独 tx |
| brand_plans | 可変 | CMP-02（T-PLAN 出力の保存） | status は CMP-02（承認結果を反映） | task 出力保存 tx |
| action_plans | 可変 | CMP-02 | status は CMP-02 | task 出力保存 tx |
| sprints | 可変 | CMP-02 | status は CMP-02 | 遷移 tx に相乗りしない独立 tx |
| workflows | 可変 | CMP-05 seed ＋ CMP-02（版追加） | status は CMP-02 | seed = migration tx／版追加 = 単独 tx |
| strategic_briefs | append-only（内容列） | CMP-02（brief シード。新版 INSERT は上流ループ改善工程のみ） | status/valid_until のみ CMP-02 | 新版 INSERT ＋旧版 superseded 化を同一 tx |
| loop_runs | 可変 | 行生成 = CMP-02。**state 列は CMP-01 のみ** | CMP-01（DU-01） | 生成 = 単独 tx／state 更新 = 遷移 tx |
| tactical_learning_packets | append-only | CMP-02（DU-02 packet ビルダ） | — | **下位 run 終端の遷移 tx と同一 tx**（s0-contract §3） |
| tasks | 可変 | 行生成 = CMP-02。state 列は CMP-01 のみ。lease/row_version は kernel claim 経路のみ | CMP-01 | 生成 = 単独 tx／state・lease 更新 = 遷移 tx |
| external_operations | 可変 | CMP-02 `ExternalOpRecorder`（唯一の INSERT／status 更新者。コネクタは request/result 材料の提供のみ） | status（prepared→sent→confirmed/rejected/unknown）は CMP-02 | **prepared・sent を各々単独コミット**。sent 後の終端確定と operation_log 証跡（CMP-04）の row ID 束縛は同一 tx（s0-contract §1） |
| pair_plan_quality | 可変 | CMP-03（DU-05） | status（passed/revoked）は CMP-03 のみ | 成立/revoke の各単独 tx |
| evidence | append-only | CMP-04（DU-09。型契約検証つき INSERT のみ） | — | 呼出し元 tx に参加（証跡化→遷移の順序は NFR-3）。published_url は先行 confirmed write operation_log へ1:1 self-FK |
| kpi_nodes | 可変 | CMP-13（DU-21。登録は CMP-03 ゼロ広告費ゲート通過後のみ） | status は CMP-13 | 登録単位 tx |
| measurements | 可変 | CMP-13（DU-23） | — | **投入一括 tx**（失敗は全 rollback — s0-contract §4.3） |
| pair_kpi_measure | 可変 | CMP-03（ペア成立判定。材料は CMP-13 が供給） | status は CMP-03 | 成立単位 tx |
| learnings | 可変 | CMP-02（スプリントレビュー工程。S0 は最小） | status は CMP-02 | 単独 tx |
| playbooks | 版付き・内容 append-only | CMP-09 の `playbooks_store` 副層（修復workflowの編成は CMP-02） | status（active/broken/retired）は CMP-09 の CAS API | 破損時は active→broken＋repair task発行、成功時はrepair task done＋旧版retired＋新版active INSERTを、それぞれCMP-02所有の複合txで確定 |
| assets | 可変 | CMP-02 WF 実行器（WF-WP-2 手順 6 の資産登録） | — | 登録単位 tx |
| approvals | 可変 | 生 SQL は CMP-11 の `approvals_store` 副層のみ（CMP-02 承認フローから呼出し） | decision の判断材料は CMP-11、更新編成は CMP-02 | pending INSERT／応答反映の各ローカル単独 tx。transport I/O を含めない |
| config | append-only | CMP-06（DU-12） | — | 1 変更 = 1 INSERT tx |
| spend_ledger | 追記専用 | **S1 専用 component／DU 未割当（design debt）** | — | actual approved_paid_operation confirmed のみ。operation_log と同一 terminal tx での記帳 API・所有者を S1 で再降下するまで実装 confirmed 禁止 |

横断規則:

- 上記以外の CMP からの書込み SQL はレビュー・CI で禁止する（基本設計 §1.3 のストア層一元化）。
- `loop_runs.state`・`tasks.state` の UPDATE は DU-01 `transition()` 以外に存在してはならない
  （状態所有の一点化 — 遷移表外の状態変更をコード構造で塞ぐ）。
- コネクタ（CMP-08〜11）は `external_operations`／`evidence` への生 SQL を持たず、
  `ConnectorIntent`／`ConnectorResult` と request/result 材料だけを CMP-02 `ExternalOpRecorder`
  へ渡す。コネクタ所掌の永続化例外はストア副層 2 表（playbooks・approvals）に限る。
- 実 read/write はどちらも `effect` 必須で同一 lifecycle を辿る。write は決定的
  idempotency key 必須かつ correlation key と同値、read は idempotency key を持たず正整数 `request_sequence` と
  `read:<task_id>:<request_hash>:<request_sequence>` を要する。同一 logical poll の sequence は
  1, 2, ... と増やし、intent／request payload／result／operation_log まで同値で降下する。
  1 connector request = 1 行であり、Notion の read と分割 write 各要求は別行とする。
- 実外部操作は policy_category 必須。read は `external_read`、write は
  `content_publish`／`review_sync`／`approval_notification`／`approved_paid_operation` の閉集合で、
  Recorder は exact `(policy_category, service, operation, target_endpoint)` policy 合格値を lifecycle 中不変にする。
  content_publish は Docker WP のみ、review_sync は Notion の明示 config＋ApprovalPass、
  approval_notification は Claude Code アプリ＋確定済み binding、approved_paid_operation は
  PO 承認＋有償 route に限定する。write は canonical lowercase rate_scope 必須、read は NULL。
  intent／request／result／external row／operation_log で category／rate_scope を同値降下し、
  operation_log payload は read にも `rate_scope: null` を常設する。category／policy／rate_scope 欠落は行作成前拒否。
- published_url evidence は provider operation ID を必須とせず、`external_operation_row_id` 必須 FK と
  `operation_log_evidence_id` NOT NULL・UNIQUE self-FK で同一 task の external row／operation_log 1 行に束縛する。
  参照先 operation_log は `effect=write`・`policy_category=content_publish` の confirmed external row に
  `external_operation_row_id` で束縛済みであり、published_url の asset URL と task が一致しなければならない。
  provider ID は両証跡にある場合だけ一致を要する。
- `spend_ledger.external_operation_row_id` は NOT NULL・UNIQUE・`external_operations.id` FK とし、
  provider operation ID ではなく内部 row ID を記帳の正準束縛にする。対象は
  `execution_mode=actual AND effect=write AND policy_category=approved_paid_operation AND status=confirmed` だけ。
  ledger の task_id／service は外部行と一致し、provider ID は両側に存在する場合だけ一致させる。
  無料 route・手動経路・実 read・provider rejected／unknown・mock／dry-run に ledger 行を作らない。
  この不変条件は S0 schema 境界だが、記帳所有者・API・DU／UT は S1 専用 component へ再降下が必要な design debt。
  CMP-13／DU-23（計測 ingest）や CMP-02／DU-04 の既存 API に記帳責務を混在させない。

## 3. append-only 群・可変群とトリガ 37 本の意図

### 3.1 群の区分

- **append-only 保護群（6 表）**: `config`・`evidence`・`state_transitions`・`strategic_briefs`（内容列）・
  `tactical_learning_packets`・`playbooks`（版内容・系譜、および retired 版全体）。履歴・証跡・上流正本・
  攻略地図の版履歴であり、過去の書換えは監査可能性そのものを壊すため、
  アプリ層の規律ではなく **DB トリガで常時拒否**する（プロセス外からの sqlite3 直叩きにも効く）。
- **可変群（残り）**: 状態列・lease 等の UPDATE を許すが、変更経路は §2 の所有 CMP に限定する。
  可変群でも DELETE は業務上使わない（FK は全て ON DELETE RESTRICT — 暗黙カスケードなし）。

### 3.2 トリガ 37 本の意図（本文は s0-contract §2 が正準）

| # | トリガ | 意図 |
|---|---|---|
| 1–2 | config_no_update / no_delete | 設定変更の履歴化（FR-33）。「いつ誰がなぜ変えたか」を消せなくする |
| 3–4 | evidence_no_update / no_delete | 証跡の改竄不可（BR-B3/BR-I7）。done 判定の根拠を事後に書換えられない |
| 5–6 | state_transitions_no_update / no_delete | 遷移ログの不可逆性（NFR-5）。拒否記録の抹消も不可 |
| 7 | external_operations_insert_prepared | preflight 通過後の新規行を prepared 開始に限定し、時刻・結果列の先行充填を拒否 |
| 8 | external_operations_binding_immutable | task/service/operation/effect/policy_category/rate_scope/request key/hash/sequence/target_endpoint の lifecycle 中差替えを拒否 |
| 9 | external_operations_result_sent_only | sent 到達前の provider 結果・response hash 充填を拒否 |
| 10 | external_operations_lifecycle | prepared→sent→confirmed/rejected/unknown の正準遷移・時刻・結果必須条件を強制 |
| 11–12 | external_operations_final_immutable / no_delete | terminal 行の改変と外部操作履歴の削除を拒否 |
| 13 | evidence_operation_log_insert | operation_log の内部 row ID 束縛・terminal 1:1・policy_category/rate_scope を含む対応属性一致を INSERT 時に強制 |
| 14 | evidence_published_url_insert | published_url を同 task の confirmed content_publish external row／operation_log へ2つのローカルIDで1:1束縛 |
| 15 | spend_ledger_binding_insert | approved_paid_operation confirmed の内部 external row ID 1:1、task/service/provider任意ID一致を強制 |
| 16–17 | spend_ledger_no_update / no_delete | 支出台帳の追記専用性を強制 |
| 18–20 | playbook_repair_task_insert / task_no_retry / no_verify_retry | 破損版1件につきpending修復task 1件、attempt=1・retry=0・束縛不変を強制 |
| 21–22 | playbooks_initial_insert / version_insert | 初版active、新版はdoneの修復/人手改訂taskとretired直前版へ連続束縛 |
| 23–27 | playbooks_content_no_update / status_transition / health_active_only / retired_no_update / no_delete | 版内容・系譜の上書き、状態逆行、非active健全性更新、retired改変、削除を拒否 |
| 28–29 | strategic_briefs_no_update / no_delete | 上流正本の内容列・系譜を凍結し、内容変更を supersedes_id 付き新版 INSERT に強制 |
| 30–31 | strategic_briefs_status_transition / valid_until_no_extend | brief の状態逆行と既存版の期限延長を拒否 |
| 32–33 | tactical_learning_packets_no_update / no_delete | 下流からの還流（TLP）は提出のみ・撤回不可（AC-SR-05） |
| 34 | tactical_learning_packets_integrity | INSERT 時に「lower・終端・run/brief/digest 三者一致」を DB 層でも強制（AC-SR-06） |
| 35 | loop_runs_brief_immutable | run 開始後の brief ID/digest 差替えを拒否 |
| 36–37 | tlp_kind_matches_terminal_state / tlp_kind_field_rules | 終端状態と packet 種別・必須/禁止フィールドの意味整合を強制 |

トリガは「最大 1 件・整合」を守る側であり、「終端 lower run に最低 1 件」は kernel の同一 tx 契約＋
DU-11 `verify()` の孤児検査が守る（役割分担 — s0-contract §3）。

## 4. マイグレーション方針（FR-72）

規則の正準は s0-contract §5。本書の設計判断は以下。

1. **前方参照のみ**: 全変更を expand / backfill / contract に分類して設計する。rename・意味変更は
   破壊的変更として禁止（新名を expand で追加し、旧名は deprecated read 互換）。
2. **1 版 1 transaction**: `migrations/NNNN_description.sql` を 1 ファイル = 1 tx で適用し、
   同一 tx で `schema_version` へ checksum 付き INSERT（DU-11 `apply_all`）。クラッシュは当該版ごと
   巻き戻り、schema_version 照合で冪等再開する（version = 冪等キー）。
3. **不変ファイル**: 適用済み migration の編集禁止。checksum 不一致・同 version 既存は適用前に
   `FatalError` 停止。失敗版は次 version で修正する。
4. **DU-11 `verify()` を昇格の関門**とする: `PRAGMA foreign_key_check`・`integrity_check`・
   25 テーブル存在・保護トリガ存在・**TLP 孤児検査**（packet なし終端 lower run = 0 件）。
   不合格 DB は使用開始自体を拒否する（SchemaVerificationFailed — fail-close）。
5. **backfill は migration に混ぜない**: 再開可能・冪等な明示 task/WF として実行し、
   件数・hash・失敗を evidence に残す。
6. **0001 = 正準 DDL と等価**: G-DDL-APPLY／G-DDL-SYNC が JSON 正本
   （[json/s0/ddl.sql](../../../L3-system-requirements/canonical/schemas/s0/ddl.sql)）との等価性を機械検査する。手書き同期に依存しない。

## 5. 接続・トランザクション規約

接続契約の正準は s0-contract §1。設計判断:

- **唯一の接続入口** = DU-10 `connect()`。`PRAGMA foreign_keys = ON`・`journal_mode = WAL`・
  `busy_timeout`（`config.sqlite_busy_timeout_ms`）を設定しない接続経路をコード上に存在させない。
  接続時に保護トリガの存在を確認し、欠落 DB は `FatalError`（不正な実行環境）。
- **単一 writer**: 書込みは kernel 経由に集約する（単一プロセス前提 — BR-I7 scope_out）。
  `SQLITE_BUSY` は busy_timeout 内待機→タイムアウトで retryable_failure に正規化する。
- **1 状態遷移 = 1 transaction**: guard 判定・状態更新・`state_transitions` INSERT・（下位 run 終端では）
  TLP INSERT を単一 tx でコミットする。遷移 tx に外部 I/O を入れない。
- **外部 I/O は tx 外、lifecycle 記録は短い tx**: route・credential・endpoint・
  PairPass・ApprovalPass・cap をすべて preflight し、合格後にだけ Recorder が prepared を
  commit → sent を commit → 実 read/write を tx 外で実行する。sent 後は provider の
  confirmed／rejected／unknown を問わず、終端結果と `external_operation_row_id` で束縛した
  operation_log を確定してから状態遷移する（NFR-3）。provider operation ID は任意である。
- **行を作らない経路**: preflight／credential／pair／approval／cap 拒否と mock／fixture／
  dry-run は `external_operations`／operation_log とも 0 行。予定 fingerprint・拒否理由・
  模擬結果は秘匿化済み process logger にだけ残す。
- 遷移 tx は `BEGIN IMMEDIATE` で開始し、書込みロックを先取して guard 評価中のロスト
  アップデートを防ぐ（設計判断 — 競合制御の詳細は
  [state-machine-design_v0.1.md §5](../state-machine/state-machine-design_v0.1.md)）。

## 6. インデックス・整合性検査方針

- **S0 は正準 DDL の UNIQUE / 部分 UNIQUE / PK / FK を唯一のインデックス源とする**: 決定性キー
  （idempotency_key・`(loop_run_id, step_key, attempt)`・`(brief_key, version)` 等）は正準 DDL が
  既に UNIQUE で被覆しており、S0 のデータ量（単一ブランド・記事単位）で追加 index は不要。
  性能目的の index は計測証跡（クエリ実測）を伴う **expand migration** としてのみ追加する
  （推測での index 追加禁止 — 書込みコストと引換えのため）。
- **定常整合性検査**（DU-11 `verify()` — 起動時・昇格時・LP-OPS ヘルスチェックで実行）:
  1. `PRAGMA foreign_key_check` / `PRAGMA integrity_check` 違反 0 件。
  2. 25 テーブル・トリガ 37 本の存在。
  3. TLP 孤児検査（terminal lower run で packet 0 件 → escalate）。
  4. 相互整合の追加検査（read-only SQL）: `approvals.evidence_id` ↔ approval 証跡の相互参照、
     `pair_plan_quality` passed の review 証跡実在、`measurements.evidence_id` の kind = measurement。
  5. status が confirmed／rejected／unknown の全 terminal `external_operations` 行に、
     `external_operation_row_id = id` の operation_log がちょうど 1 行あること。
     逆方向の orphan／重複も 0 件とし、task_id, service, operation, effect, policy_category, rate_scope,
     correlation_key, request_hash, request_sequence, result の同値を照合する。read は rate_scope IS NULL、
     operation_log JSON の rate_scope=null も必須。provider operation ID の有無は照合成否に用いない。
     status=sent は timeout 内の in-flight だけを許し、超過行は reconcile 対象として別に列挙する。
  6. published_url 全行が `external_operation_row_id` と `operation_log_evidence_id` で同 task の
     confirmed content_publish external row／operation_log ちょうど 1 組へ接続し、self-FK／UNIQUE・asset URL 一致を満たすこと。
     provider ID が NULL でも正常とし、存在時のみ双方一致を検査する。
  7. spend_ledger 全行が `external_operation_row_id` で actual・write・approved_paid_operation・confirmed の外部行ちょうど
     1 件へ接続し、task_id・service と任意 provider ID が一致すること。逆方向は検証済み有償 route の
     confirmed approved_paid_operation だけが ledger ちょうど 1 行、無料／手動 route・read・rejected／unknown は
     0 行であること。provider ID の欠落は row ID 束縛を無効にしない。
- 検査はすべて read-only であり何度でも安全（冪等）。違反検出は自動修復せず fail-close で
  escalate する（BR-I7 — 人の関与が必要な破損）。
