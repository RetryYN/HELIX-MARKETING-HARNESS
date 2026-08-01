---
artifact_id: L6-S0-STATE-MACHINE
lifecycle_status: confirmed
slice: S0
traces: [FR-11, SR-07]
forward_refs: [SR-02, SR-03]
dus: [DU-01, DU-02, DU-03]
---

# 機能別詳細設計 — 状態機械の実装詳細

> status: **confirmed**（2026-08-01 全層再降下 §7 — AI 起草）
> 正準参照: 要求 = FR-11（ループ状態機械）。遷移表の正準は [json/s0/transitions.json](../../L3-system-requirements/canonical/schemas/s0/transitions.json) ＋
> [s0-contract_v0.1.md §3](../../L3-system-requirements/canonical/s0-contract_v0.1.md)。状態図・ガード 6 分類・発火権限・
> 競合制御の設計層は [state-machine-design_v0.1.md](../../L4-basic-design/canonical/state-machine/state-machine-design_v0.1.md)（本書の上位 —
> 本書は同書 §2〜§4 を実装レベルへ降下する）。API 署名の正本は
> [detailed-design_v0.1.md DU-01](../../L5-detailed-design/canonical/detailed-design_v0.1.md)。遷移表・状態図は再掲しない。

---

## 1. 目的

DU-01 `transition()` の内部を実装可能な粒度で確定する: 遷移解決・ガード合成・拒否理由コード・
transaction／楽観ロックの具体形・イベント発火 API。状態変更の経路をこの 1 関数に閉じる。

## 2. 契約（実装が守る事前・事後・不変条件）

- **pre**: 遷移表はパッケージデータ（transitions.json 同梱）から起動時に 1 回ロードし、
  キー `(entity_type, from_state, event)` の一意性を検証済み（重複は起動時 FatalError）。
- **post**: 許可遷移は guard → 状態 UPDATE → state_transitions INSERT（＋lower 終端では TLP INSERT）が
  単一 tx でコミット。拒否は状態・retry_count・証跡すべて不変で rejected 行のみ残る。
- **invariant**: `loop_runs.state`・`tasks.state` の UPDATE 文は本モジュール以外に存在しない
  （[db-design_v0.1.md §2](../../L4-basic-design/canonical/data/db-design_v0.1.md) 横断規則）。終端状態からの遷移要求は常に拒否。
- 検証オラクル群: TC-011・TC-GATE-05・TC-RST-06・TC-028・AC-11/13 系（末尾 trace 表）。

## 3. 遷移解決アルゴリズム

```text
transition(conn, entity_type, entity_id, event, actor, details, clock):
  1. 表ロード済み dict を (entity_type, from?, event) では引かない —
     まず BEGIN IMMEDIATE で entity 行を読む（from_state は必ず tx 内の DB 値。引数で受けない）
  2. from_state が終端 → reject(TERMINAL_STATE)
  3. key = (entity_type, from_state, event) が表に無い → reject(UNDEFINED_TRANSITION)
  4. guard チェーン評価（§4。G1..G5 の順、最初の不成立で reject(そのコード)）
  5. イベント切替判定: retryable_failure / verify_fail は G4 の境界超過時、
     retry_exhausted / verify_fail_exhausted へ切替えて表を再照合（呼出し側に再送させない）
  6. 状態 UPDATE（tasks は row_version + 1 を同文で）→ 付随更新（retry_count 等、表の定義どおり）
  7. lower 終端イベントなら TLP ビルダを同一 tx で呼ぶ（tlp.md §3）
  8. state_transitions INSERT（passed）→ COMMIT → TransitionResult
  reject(code):
     tx を rollback（状態不変）→ 別 tx で state_transitions に rejected 行
     （event・code・details を details_json へ）→ raise TransitionRejected(code)
```

- 手順 1 の「from_state を引数で受けない」が check-then-act 競合の根絶点: 先行 tx がコミット済みなら
  読み直した from_state が変わっており、手順 2〜3 で決定的に拒否される（二重発火は事故にならず
  rejected 証跡に残る）。
- 拒否記録が別 tx なのは、rejected 行自体まで rollback しないため（拒否の観測可能性 — NFR-5）。

## 4. ガード評価器の合成

guard は `register_guard(event, fn)` の登録制で、`fn(conn, entity_row) -> GuardResult(ok, code, detail)`
の純関数（DB read のみ・書込み禁止・Clock は引数注入）。実装は**分類 G1〜G5 の合成チェーン**として
組み立てる:

1. イベントごとに `[G1 権限, G2 構造, G3 brief, G4 リトライ境界, G5 証跡完備]` から該当分類の
   guard 部品を順序固定で連結する（分類と該当イベントの正準は
   [state-machine-design_v0.1.md §2](../../L4-basic-design/canonical/state-machine/state-machine-design_v0.1.md)）。
2. 各部品は単一関心（例: `guard_actor_is_author_execution`・`guard_parent_running`・
   `guard_valid_brief`＝[strategic-brief.md](strategic-brief.md) §4.3 の呼出し・
   `guard_evidence_complete`＝DU-08 委譲）。合成は短絡評価 — 最初の不成立で後続を評価しない
   （安価・決定的検査を先に、権限のない要求に内部情報を返さない）。
3. 許可遷移に guard が 1 つも登録されていない場合は `FatalError`（配線漏れの実行時 fail-close）。
4. guard 部品は details_json へ**不成立コードのみ**を残し、秘匿値・内部行の内容を書かない。

## 5. TransitionRejected の理由コード

`TransitionRejected` は `GateRejected` の kernel 具体型（[error-taxonomy_v0.1.md §3.1](../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md)）
とし、`code`（機械可読・安定）と `detail`（人間可読）を持つ。コードは state_transitions の
details_json と例外の両方に載る:

| code | 段 | 意味 |
|---|---|---|
| TERMINAL_STATE | 手順 2 | 終端状態からの遷移要求 |
| UNDEFINED_TRANSITION | 手順 3 | 遷移表に無い (entity, from, event) |
| ACTOR_NOT_PERMITTED | G1 | 発火権限外（コネクタ直発火・cancel の非人間発火等） |
| SELF_REVIEW | G1 | verifier の principal が author と同一 |
| LEASE_HELD / LEASE_NOT_OWNER | G1/G2 | 失効前の他 execution claim／author 非所属 execution の claim |
| PARENT_NOT_ACTIVE | G2 | 親 run 非 running・親 task 非 in_progress |
| INPUT_INVALID | G2 | 入力・workflow の無効、FK 不在 |
| STALE_ROW_VERSION | G2 | row_version 不一致（楽観ロック敗北） |
| BRIEF_MISSING / BRIEF_NOT_ACTIVE / BRIEF_DIGEST_MISMATCH / BRIEF_EXPIRED | G3 | lower start の brief 検証 4 事由（AC-SR-02） |
| RETRY_LIMIT | G4 | 境界超過（イベント切替後もなお表に無い場合） |
| EVIDENCE_INCOMPLETE | G5 | 必須 kind 欠落・kind 規則違反（EvidenceIncomplete） |
| PAIR_NOT_ESTABLISHED / APPROVAL_BINDING_MISMATCH | G5 | ペア不成立／binding 3 項目不一致 |

コードの追加は台帳（error-taxonomy）と同一コミットで行う（分母ラチェットと同じ規律）。

## 6. BEGIN IMMEDIATE と row_version の実装

- **BEGIN IMMEDIATE**: 遷移 tx は `BEGIN IMMEDIATE` で開始し RESERVED ロックを先取する。
  guard の read が同一ロック区間に入り、読んだ from_state・retry_count がコミットまで他 writer に
  変更されない。`SQLITE_BUSY` は `busy_timeout`（config 値 — 接続時に DU-10 が設定）内で待機し、
  超過は `RetryableError` へ正規化（retryable_failure イベントとして再入）。
- **row_version 楽観ロック**: 遷移 tx 外の lease・heartbeat 更新（claim・heartbeat）は
  `UPDATE tasks SET ..., row_version = row_version + 1 WHERE id = ? AND row_version = ?` とし、
  変更行数 0 は STALE_ROW_VERSION で拒否する。遷移 tx 内の状態 UPDATE も row_version を同時に進め、
  tx 外更新との順序逆転を検出可能にする。
- 遷移 tx に外部 I/O・通知・sleep を入れない（ロック保持時間の上限を DB 操作のみに保つ）。

## 7. イベント発火 API

発火経路は 2 本のみ（発火権限の正準は state-machine-design §3。G1 が実行時に再検査する）:

| API | 呼出し元 | 用途 |
|---|---|---|
| `transition(conn, entity_type, entity_id, event, actor_agent_id, details, clock)` | CMP-02 オーケストレータ／CLI（cancel は人間操作のみ） | すべての状態遷移の唯一の入口 |
| `register_guard(event, fn)` | 起動時配線（cli 層の composition root） | guard 部品の登録。実行中の再登録は FatalError |

- コネクタ（CMP-08〜11）は本 API を import しない（依存方向で禁止 — 例外を 3 系へ正規化して
  CMP-02 に返すのみ）。失敗イベントの**選択**（retryable／non_retryable／fatal／escalate）は
  検出層のエラー分類境界が行い、kernel は選択済みイベントを表照合するだけ。
- 発火結果 `TransitionResult(entity, from_state, to_state, transition_id)` は frozen であり、
  呼出し側はこれを再利用して二重発火しない（同一イベント再送は §3 手順 1〜3 で決定的に拒否される）。

## 8. trace 表

| 設計要素 | DU | AC | TCC |
|---|---|---|---|
| 遷移解決（表照合・終端拒否・rejected 記録） | DU-01 | AC-11-1, AC-11-2, AC-11-3 | TCC-11-1, TCC-11-2, TCC-11-3, TC-011, TC-GATE-05 |
| ガード合成（G1〜G5・短絡・配線漏れ fail-close） | DU-01 | AC-13-1, AC-13-2 | TCC-13-1, TCC-13-2 |
| リトライ境界のイベント切替 | DU-01 | AC-13-3 | TCC-13-3, TC-028 |
| brief ガード（G3 の 4 事由コード） | DU-01, DU-02 | AC-SR-02, AC-SR-07-1 | TCC-SR-02, TCC-SR-07-1, STC-I-03 |
| BEGIN IMMEDIATE・競合直列化 | DU-01 | AC-11-3 | TCC-CONFLICT-1, TCC-KILL-1, TC-RST-06 |
| row_version・lease 排他 | DU-01, DU-02 | AC-27-3 | TCC-27-3, UT-10 |
| lower 終端の TLP 同一 tx | DU-01, DU-02 | AC-SR-03 | TCC-SR-03, TCC-KILL-2, STC-I-05 |
| 発火権限（G1 実行時再検査） | DU-01 | AC-27-2 | TCC-27-2, TC-GATE-02 |

## 9. 実装単位（implementation_units）

責務は DU の **API 1 本**へ接続する。API・AC・TC・UT の対応の機械可読な正本は
[implementation-units.json](implementation-units.json)（`G-L6-IMPLEMENTATION-TRACE` が
DU／API の実在・pre/post への責務の明記・AC／TC／UT の実在と対応を fail-close 検査する）。

| unit_id | DU | API | 契約節 | 責務 | AC |
|---|---|---|---|---|---|
| IU-STATEMACHINE-02 | DU-01 | API-DU01-01 | POST-01・POST-02・POST-03・POST-04・RAISE-01 | `transition`・`conn`: 許可時: guard 評価→状態 UPDATE→state_transitions（g… | AC-11-1, AC-11-2, AC-11-3, AC-13-1, AC-13-2, AC-13-3, AC-13-4, AC-16-1, AC-16-2, AC-16-3, AC-SR-07-1, AC-SR-07-2 |
| IU-STATEMACHINE-03 | DU-02 | API-DU02-02 | POST-01・POST-02・PRE-01・RAISE-01 | `claim`・`task`: lease_owner_execution_id・lease_expires_at（config… | AC-27-1, AC-27-3 |
| IU-STATEMACHINE-04 | DU-02 | API-DU02-01 | POST-01・POST-02・POST-03・PRE-03・RAISE-01 | `issue_task`・`loop_run`: 同一 (loop_run_id, step_key) に非終端の既存 task… | AC-12-1, AC-12-2, AC-12-3, AC-12-4, AC-27-1 |
| IU-STATEMACHINE-06 | DU-02 | API-DU02-07 | POST-01・RAISE-01 | `validate_strategic_brief`・`held_digest`: status=active・digest 一… | AC-SR-02, AC-SR-06-3, AC-SR-07-1 |
| IU-STATEMACHINE-05 | DU-02 | API-DU02-03 | POST-01・POST-02・RAISE-01・RAISE-02 | `run_microloop`・`task`: submit→verify を反復し、FAIL ごとに verify_fail 遷移（retry_c… | AC-13-7, AC-13-8, AC-13-9 |
| IU-STATEMACHINE-08 | DU-02 | API-DU02-04 | POST-01・POST-02・RAISE-01 | `resume`・`entity`: s0-contract §3.3 の再開分岐を DB 行のみを根拠に判定し ResumeAct… | AC-11-5, AC-11-6 |
| IU-STATEMACHINE-07 | DU-03 | API-DU03-01 | RAISE-01 | `assign`・`agents`: active かつ principal の異なる agent の組（agents.prin… | AC-27-2 |

本文書が担っていた次の責務は、**API 契約節を AC と UT の双方が検証している状態**を作れないため実装単位から外した（接続の穴は[監査記録](../../00-authority/audits/structural-trace-remediation-2026-08-02.md)が正本）。

| 外した unit_id | 理由 |
|---|---|
| IU-STATEMACHINE-01 | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
