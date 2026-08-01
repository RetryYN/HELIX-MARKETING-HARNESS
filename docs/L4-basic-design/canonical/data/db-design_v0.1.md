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
| external_operations | 可変 | CMP-02 WF 実行器（コネクタは行を書かない — request/response 材料の提供のみ） | status（prepared→sent→confirmed/rejected/unknown）は CMP-02 | **prepared・sent を各々単独コミット**（送信直後クラッシュの検出窓 — s0-contract §1） |
| pair_plan_quality | 可変 | CMP-03（DU-05） | status（passed/revoked）は CMP-03 のみ | 成立/revoke の各単独 tx |
| evidence | append-only | CMP-04（DU-09。型契約検証つき INSERT のみ） | — | 呼出し元 tx に参加（証跡化→遷移の順序は NFR-3） |
| kpi_nodes | 可変 | CMP-13（DU-21。登録は CMP-03 ゼロ広告費ゲート通過後のみ） | status は CMP-13 | 登録単位 tx |
| measurements | 可変 | CMP-13（DU-23） | — | **投入一括 tx**（失敗は全 rollback — s0-contract §4.3） |
| pair_kpi_measure | 可変 | CMP-03（ペア成立判定。材料は CMP-13 が供給） | status は CMP-03 | 成立単位 tx |
| learnings | 可変 | CMP-02（スプリントレビュー工程。S0 は最小） | status は CMP-02 | 単独 tx |
| playbooks | 可変 | CMP-09 の `playbooks_store` 副層のみ | status（active/broken/retired）は CMP-09 | 操作結果反映の単独 tx |
| assets | 可変 | CMP-02 WF 実行器（WF-WP-2 手順 6 の資産登録） | — | 登録単位 tx |
| approvals | 可変 | CMP-11 の `approvals_store` 副層のみ | decision は CMP-11（応答受領時） | 要求/応答の各単独 tx |
| config | append-only | CMP-06（DU-12） | — | 1 変更 = 1 INSERT tx |
| spend_ledger | 可変（追記運用） | CMP-02（有償外部操作の記帳。S0 はゼロ広告費で 0 行が正常 — CMP-03 が拒否） | — | 記帳単位 tx |

横断規則:

- 上記以外の CMP からの書込み SQL はレビュー・CI で禁止する（基本設計 §1.3 のストア層一元化）。
- `loop_runs.state`・`tasks.state` の UPDATE は DU-01 `transition()` 以外に存在してはならない
  （状態所有の一点化 — 遷移表外の状態変更をコード構造で塞ぐ）。
- コネクタ（CMP-08〜11）は業務状態テーブルに触れない。所掌はストア副層 2 表（playbooks・approvals）のみ。

## 3. append-only 群・可変群とトリガ 14 本の意図

### 3.1 群の区分

- **append-only 群（5 表）**: `config`・`evidence`・`state_transitions`・`strategic_briefs`（内容列）・
  `tactical_learning_packets`。履歴・証跡・上流正本であり、過去の書換えは監査可能性そのものを壊すため、
  アプリ層の規律ではなく **DB トリガで常時拒否**する（プロセス外からの sqlite3 直叩きにも効く）。
- **可変群（残り）**: 状態列・lease 等の UPDATE を許すが、変更経路は §2 の所有 CMP に限定する。
  可変群でも DELETE は業務上使わない（FK は全て ON DELETE RESTRICT — 暗黙カスケードなし）。

### 3.2 トリガ 14 本の意図（本文は s0-contract §2 が正準）

| # | トリガ | 意図 |
|---|---|---|
| 1–2 | config_no_update / no_delete | 設定変更の履歴化（FR-33）。「いつ誰がなぜ変えたか」を消せなくする |
| 3–4 | evidence_no_update / no_delete | 証跡の改竄不可（BR-B3/BR-I7）。done 判定の根拠を事後に書換えられない |
| 5–6 | state_transitions_no_update / no_delete | 遷移ログの不可逆性（NFR-5）。拒否記録の抹消も不可 |
| 7 | strategic_briefs_no_update（条件付き） | 上流戦略正本の**内容列凍結**。status/valid_until の運用遷移だけを許し、内容変更は supersedes_id 付き新版 INSERT に強制（下流からの直接変更不可 — AC-SR-04） |
| 8 | strategic_briefs_no_delete | 上流正本の系譜（supersedes 連鎖）を破壊させない |
| 9–10 | tactical_learning_packets_no_update / no_delete | 下流からの還流（TLP）は提出のみ・撤回不可（AC-SR-05） |
| 11 | tactical_learning_packets_integrity | INSERT 時に「lower・終端・run/brief/digest 三者一致」を DB 層でも強制（AC-SR-06）。kernel 契約（§ 終端処理）の二重防御 |

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
- **外部操作は tx 外**: `external_operations` の prepared・sent は各々単独コミットし
  （クラッシュ検出窓）、`operation_log` 証跡化 → 状態遷移の順を固定する（NFR-3）。
- 遷移 tx は `BEGIN IMMEDIATE` で開始し、書込みロックを先取して guard 評価中のロスト
  アップデートを防ぐ（設計判断 — 競合制御の詳細は
  [state-machine-design_v0.1.md §5](../state-machine/state-machine-design_v0.1.md)）。

## 6. インデックス・整合性検査方針

- **S0 は DDL の UNIQUE / PK / FK を唯一のインデックス源とする**: 決定性キー
  （idempotency_key・`(loop_run_id, step_key, attempt)`・`(brief_key, version)` 等）は正準 DDL が
  既に UNIQUE で被覆しており、S0 のデータ量（単一ブランド・記事単位）で追加 index は不要。
  性能目的の index は計測証跡（クエリ実測）を伴う **expand migration** としてのみ追加する
  （推測での index 追加禁止 — 書込みコストと引換えのため）。
- **定常整合性検査**（DU-11 `verify()` — 起動時・昇格時・LP-OPS ヘルスチェックで実行）:
  1. `PRAGMA foreign_key_check` / `PRAGMA integrity_check` 違反 0 件。
  2. 25 テーブル・トリガ 14 本の存在。
  3. TLP 孤児検査（terminal lower run で packet 0 件 → escalate）。
  4. 相互整合の追加検査（read-only SQL）: `approvals.evidence_id` ↔ approval 証跡の相互参照、
     `pair_plan_quality` passed の review 証跡実在、`measurements.evidence_id` の kind = measurement。
- 検査はすべて read-only であり何度でも安全（冪等）。違反検出は自動修復せず fail-close で
  escalate する（BR-I7 — 人の関与が必要な破損）。
