# 基本設計書 v0.1（②）

> status: **confirmed**（2026-07-31 PO 承認 — 基本設計完遂指示。AI 起草）
> pair: [integration-test-design_v0.1.md](integration-test-design_v0.1.md)（総合テスト設計④ — HELIX 式 ②↔④ 文書ペア）
> 上位文書: [s0-contract_v0.1.md](../requirements/s0-contract_v0.1.md)（DDL・状態遷移・WF 契約の正準）／
> [requirements_v0.1.md](../requirements/requirements_v0.1.md)（FR/NFR/AC）／
> [function-list_v0.1.md](../requirements/function-list_v0.1.md)（FN 61・スライス配分）
> **設計契約正本（2026-08-01 全層再降下 §6）**: 各 CMP/SCM の 11 観点設計契約 =
> [json/cmp-contracts.json](json/cmp-contracts.json)（ビュー [cmp-contracts_v0.1.md](cmp-contracts_v0.1.md)）。
> 独立設計書: [外部 IF](external-if-design_v0.1.md)／[DB](db-design_v0.1.md)／
> [状態機械](state-machine-design_v0.1.md)／[エラー分類](error-taxonomy_v0.1.md)／
> [承認](approval-design_v0.1.md)／[ブランド隔離](brand-isolation-design_v0.1.md)
> （G-CMP-INTERFACE が fail-close 検査）。
> JSON 正本: [json/components.json](json/components.json)（コンポーネント台帳。本文と同期、実装入力は JSON）
> 位置づけ: S0（25 機能）の実装構造を確定する。要求内容は定義しない — 上位文書と矛盾したら上位を優先し本書を改訂する。
> 上流戦略層（2026-08-01 追補）: 戦略コンポーネント（SCM）は
> [strategy-loop-design_v0.1.md](strategy-loop-design_v0.1.md) が正本。S0 分は CMP-05（テーブル・トリガ）・
> CMP-01（start ガード）・CMP-02（brief シード・TLP 生成）への最小拡張で、CMP 13・S0 25 FN は不変（SR-15）。

---

## 1. 設計方針

1. **契約駆動**: DB スキーマ・状態遷移・evidence 型・WF 実行は [s0-contract](../requirements/s0-contract_v0.1.md) が正準。
   本書はそれを「どのコード構造で実装するか」だけを決める。契約の再定義・複製はしない。
2. **fail-close 一元化**: 拒否判定はすべてゲート層（CMP-03）と状態機械（CMP-01）に集約する。
   コネクタや制作系は自前の「例外的に通す」分岐を持たない。
3. **単方向依存**: `外殻（CLI/WF 実行）→ ドメイン（kernel/gates）→ 基盤（db/evidence/config）` の一方向。
   基盤層はドメイン層を import しない。コネクタ（外部 I/O）は業務状態（loop_runs/tasks/evidence）を
   直接書かない — 状態は kernel、証跡は evidence の API 経由のみ。コネクタ固有の所掌テーブル
   （playbooks・approvals）への永続化は、各コネクタ内の**ストア副層**（`playbooks_store` /
   `approvals_store`。生 SQL はここだけ）に限定し、外部 I/O コードと分離する。
4. **決定性と再開可能性**: すべての処理は「入力＋DB 状態」から再現できる純関数的ステップに分解し、
   プロセス内メモリのみに依存する状態を持たない（s0-contract §3.3）。
5. **薄い自作・厚い標準**: SQLite3（標準ライブラリ）、Playwright、pytest、`cryptography` 以外の
   フレームワーク導入は S0 ではしない。ORM・DI コンテナ・ジョブキューは採用しない
   （tech-stack_v0.1.md の選定に従う）。

## 2. 全体構成

実装言語は Python 3.14（技術選定書と統一）。リポジトリ直下に `src/helix/` パッケージと `tests/` を新設する（docs は現行のまま）。

```text
src/helix/
  db/          # CMP-05: スキーマ・マイグレーション・接続管理
  kernel/      # CMP-01/02: 状態機械・タスク発行・マイクロループ・WF 実行・割当
  gates/       # CMP-03: ペア判定・公開ゲート・ゼロ広告費・証跡完備
  evidence/    # CMP-04: 証跡ストア（型契約検証つき INSERT）
  config/      # CMP-06: 履歴保持 config
  registry/    # CMP-07: 接続レジストリ・秘匿情報ストア
  connectors/  # CMP-08/09/10/11: ブラウザ基盤・攻略地図・WP REST・承認通知
  content/     # CMP-12: 原稿生成・版管理連携
  measure/     # CMP-13: KPI ツリー・計測取得・パーサ群
  cli.py       # `helix` コマンド（init / run / migrate / status）
tests/
  unit/        # ③TC 59 のうち unit/component 粒度を pytest 化
  integration/ # ③TC の integration/e2e 粒度と ④ITC 16 を pytest 化。④は ③該当 TC を
               # ステップとして再利用し、結合観測点（assertions）を追加する（二重実装しない）
```

依存方向: `cli → kernel → gates → evidence/db/config`、`kernel → connectors/content/measure`（呼ぶだけ）。
逆方向 import はレビュー・CI（import-linter は S1、S0 はレビュー規律）で禁止する。

## 3. コンポーネント設計（CMP 台帳）

S0 の 25 機能（FN）を 13 コンポーネントに割り当てる。**割当は全 25 FN を重複なく被覆する**
（ゲート G-CMP-FN が機械検証）。各 CMP の正本レコードは [json/components.json](json/components.json)。

| CMP | 名称 | 担当 FN | 更新 |
|---|---|---|---|
| CMP-01 | 状態機械カーネル | FN-101, FN-704 | S0.1 |
| CMP-02 | オーケストレータ | FN-102, FN-103, FN-104, FN-105 | S0.1 |
| CMP-03 | ゲートエンジン | FN-201, FN-202, FN-204, FN-208 | S0.1 |
| CMP-04 | 証跡ストア | FN-703 | S0.1 |
| CMP-05 | DB 基盤 | FN-701, FN-702 | S0.1 |
| CMP-06 | config 管理 | FN-305 | S0.1 |
| CMP-07 | 接続レジストリ・秘匿ストア | FN-401, FN-411 | S0.2 |
| CMP-08 | ブラウザ基盤 | FN-402 | S0.2 |
| CMP-09 | 攻略地図ストア | FN-404 | S0.2 |
| CMP-10 | WP REST コネクタ | FN-406 | S0.2 |
| CMP-11 | 承認通知 | FN-409 | S0.2 |
| CMP-12 | 制作・版管理 | FN-501, FN-511 | S0.2 |
| CMP-13 | 計測 | FN-601, FN-602, FN-603 | S0.3 |

### CMP-01 状態機械カーネル（kernel/state.py）

- 遷移表（docs/requirements/json/s0/transitions.json（リポジトリ相対）をビルド時に埋め込み）を照合し、未定義の (entity, from, event) は
  guard 評価前に拒否する。許可・拒否とも `state_transitions` へ単一 transaction で記録（FN-704 を内包）。
- 公開 IF: `transition(conn, entity_type, entity_id, event, actor_agent_id, details) -> TransitionResult`。
  guard は event ごとの純関数 `guard_<event>(conn, row) -> GuardResult` として登録制。
- retry_count の増加は `verify_fail` guard 内のみ。終端状態からの遷移要求は常に拒否。

### CMP-02 オーケストレータ（kernel/orchestrator.py, assigner.py, workflow.py）

- タスク発行（FN-102）: ループステップ到達時に workflow 定義から tasks 行を生成。idempotency_key は
  `"{loop_run_id}:{step}:{attempt}"` 形で決定的に構成。
- 割当（FN-105）: `assign(author_role, verifier_role)` は active な別 agent の組のみ返す。
  同一 agent しか居ない場合は発行自体を拒否（DB CHECK と二重の fail-close）。
- WF 実行器（FN-104）: `workflows.definition_json` のステップ列を順に実行し、各ステップの出力・証跡を
  kernel/evidence 経由で保存。ステップ失敗は §3 遷移（retry / failed / escalated）に還元する。
- マイクロループ（FN-103）: submit→verify の反復。`config.retry_limit` 到達で escalate。

### CMP-03 ゲートエンジン（gates/）

- ペア判定（FN-201）: `pair_plan_quality` の成立・revoke。企画/commit 変更検知で revoked へ。
- 公開ゲート（FN-202）: 公開系操作の直前に `require_pair(plan_id)` — 成立 pair がなければ
  コネクタ呼出し前に拒否（WP API を呼ばない）。
- ゼロ広告費（FN-204）: `kpi_nodes.metric_type` の deny 型（DB CHECK と二重）＋広告ドメイン denylist
  （config 値）で登録・投入の両方を拒否。
- 証跡完備（FN-208）: `required_evidence_json` の全 kind 存在＋各 kind 規則の再検証。done 遷移 guard から呼ばれる。

### CMP-04 証跡ストア（evidence/store.py)

- `record(conn, task_id, kind, value, payload, **cols) -> evidence_id`。s0-contract §2.1 の kind 別必須キー・
  列整合を INSERT 前に検証し、違反は例外（fail-close）。secret/credential 文字列パターンの混入検査を含む。
- 参照 API は read-only（`for_task(task_id)`, `latest(kind, value)`）。UPDATE/DELETE は提供しない。

### CMP-05 DB 基盤（db/）

- `migrations/NNNN_description.sql`（不変・連番）と `migrate.py`（適用・checksum 記録・§5.2 の昇格手順）。
  0001 は s0-contract §2 の正準 DDL と等価（G-DDL-SYNC が JSON 正本と突合済み）。
- `connect(path) -> Connection`: `PRAGMA foreign_keys = ON` を必ず実行して返す唯一の接続入口。
  config テーブルへの UPDATE/DELETE 拒否トリガもここで保証する。

### CMP-06 config 管理（config/store.py）

- append-only INSERT＋`supersedes_config_id` 連鎖。`get(key)` は changed_at 最大行。
  同一 key 同一時刻の INSERT 拒否。理由（reason）必須。

### CMP-07 接続レジストリ・秘匿ストア（registry/）

- レジストリ（FN-401）: サービス別に `route_type` 優先順（mcp → api → browser → 有償）を宣言 JSON で保持し、
  `resolve(service, operation) -> Route` を返す。切替はデータ変更のみ（コード変更なし — AC-41）。
- 秘匿ストア（FN-411）: `cryptography`（Fernet）で暗号化したファイルストア。復号値はメモリ内のみ、
  ログ・DB・evidence への書込み禁止（CMP-04 の混入検査と対）。テスト用/本番用は物理別ファイル＋
  endpoint 突合（テスト credential→本番 endpoint 等の組合せは接続前に拒否）。

### CMP-08 ブラウザ基盤（connectors/browser.py）

- Playwright 起動・storage_state 永続化・headed/headless 切替（WSLg）。S0 では GA4 フォールバック経路と
  スクショ取得だけが利用者。セレクタ・手順は持たない（攻略地図から供給）。

### CMP-09 攻略地図ストア（connectors/playbooks.py）

- `playbooks` 行の保存・参照・`last_success_at` 更新（AC-42）。操作失敗の連続で status = broken へ。
  永続化は §1.3 のストア副層 `playbooks_store` が担い、外部 I/O コードから分離する。

### CMP-10 WP REST コネクタ（connectors/wp.py）

- Application Password で REST（下書き・公開・メディア）。全書込みは `idempotency_key` 必須・
  事前照合（同 key の operation_log 存在時は再送せず結果補完）。公開系の唯一の公開入口は
  kernel 側 `publish(pair_pass: PairPass, ...)` とし、`PairPass` は CMP-03 の `require_pair` だけが
  生成できる検証済み値オブジェクト。低レベル WP client はモジュール非公開（`_client`）とし、
  ゲート未通過の呼出し経路をコード構造で塞ぐ。
  書込み先はローカル Docker WP のみ（環境契約 §6。base URL の allow-list 検査）。

### CMP-11 承認通知（connectors/approval.py）

- Claude Code アプリ通知で binding 3 項目（subject / operation / at）を提示し、応答を approvals
  （ストア副層 `approvals_store` 経由）＋ approval 証跡（evidence API 経由）へ記録。承認 pending 中は
  **親 loop_run を waiting** にし task は進行させない（tasks に waiting 状態はない — s0-contract §3.2）。
  rejected は non_retryable_failure で task を failed へ、expired は承認再要求で待機継続し approval_retry_limit 到達で escalated（同 §4.2）。
  transport は差替可能な interface（本番: 通知、テスト: mock fixture）。

### CMP-12 制作・版管理（content/）

- 原稿生成（FN-501）: 企画入力から git workspace へ記事ソース生成。同一入力→同一ハッシュの決定性
  （テンプレート＋乱数種固定 — AC-51）。
- 版管理連携（FN-511）: workspace の commit 実行・hash 取得・成果物/審査記録との紐づけ（AC-54）。

### CMP-13 計測（measure/）

- KPI ツリー（FN-601）: kpi_nodes CRUD（有料指標型は CMP-03 経由で拒否）。
- 取得（FN-602）: GA4 Data API 第一経路（ADR-006）、阻害時のみブラウザエクスポート。取得物は即
  SHA-256 固定＋スクショ証跡。
- パーサ群（FN-603）: schema/type 検証→正常行のみ transaction 投入、壊れた行は隔離テーブルではなく
  隔離ファイル＋evidence 記録（AC-62）。投入失敗は全 rollback。

## 4. 横断設計

- **トランザクション境界**: 「1 状態遷移 = 1 transaction」（guard・状態更新・遷移ログ）。外部操作は
  transaction 外で行い、`operation_log 証跡化 → 状態遷移` の順を固定する（NFR-3）。
- **エラー分類**: `RetryableError`（→ retryable_failure）／`FatalError`（→ fatal_failure /
  non_retryable_failure）／`GateRejected`（遷移拒否・状態不変）の 3 系に正規化し、
  コネクタ例外は境界で必ずこのいずれかに変換する。
- **構造化ログ**: FN-704 は state_transitions（DB）と JSON Lines（ファイル）の二重化。ログには
  entity/event/guard_result/duration のみで、本文・credential を含めない。
- **時間・乱数**: 現在時刻と乱数は `Clock`/`Rng` 注入で受け取り、直接呼ばない（テスト決定性、NFR-7 の
  ランダム間隔も同注入点で実装）。
- **設定値**: リトライ上限・間隔範囲・denylist 等はすべて config 行。ハードコード禁止（型×動的充填）。

## 5. 実装体制（エージェント割当）

| 工程 | 担当 | 検証 |
|---|---|---|
| S0.1〜S0.3 実装主力 | codex-terra（medium） | Claude（本セッション）＋ codex-sol レビュー |
| 定型変換（DDL→migration、TC→pytest 雛形） | codex-luna（high） | Claude |
| 設計判断・差分レビュー | codex-sol（low） | PO 承認 |

完了の定義は各更新とも「④の該当 ITC ＋ ③の該当 TC が pytest で green ＋ 要件整合ゲート全数 PASS
（件数の正本は baseline.json の gate_count）」。

## 6. S1 以降への持ち越し

FN-605（ダッシュボード HTML 生成）、import-linter による依存方向の機械検査、本番 WP 書込み、
Notion 正式連携（FN-408）は本設計の構造（レジストリ・ゲート・証跡）に追加コンポーネントとして
載せる前提であり、S0 構造の変更を要しない。
