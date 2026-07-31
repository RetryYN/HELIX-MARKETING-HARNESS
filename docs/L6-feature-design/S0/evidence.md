# 機能別詳細設計 — 証跡（evidence）

> status: **draft（再降下中）**（2026-08-01 全層再降下 §7 — AI 起草）
> 正準参照: evidence 型契約（kind 10 種・必須キー・列整合）の正準は
> [s0-contract_v0.1.md §2.1](../../L3-system-requirements/canonical/s0-contract_v0.1.md)、外部操作の順序契約は同 §1（NFR-3）、
> テーブル所有・append-only トリガは [db-design_v0.1.md §2〜3](../../L4-basic-design/canonical/data/db-design_v0.1.md)。
> API 署名の正本は [detailed-design_v0.1.md DU-08/DU-09](../../L5-detailed-design/canonical/detailed-design_v0.1.md)。
> 本書は kind 別必須キー表を再掲しない — 検証器の実装構成と done 遷移・順序規律だけを確定する。

---

## 1. 目的

「証跡がなければ done にならない・証跡は書換えられない・外部操作は証跡化してから状態を進める」の
3 規律を、証跡ストア（DU-09）と完備ゲート（DU-08）の 2 モジュールで実装する。

## 2. 契約（実装が守る事前・事後・不変条件）

- **pre**: INSERT 前に kind 別 validator が payload 必須キー・列整合・追加検証をすべて通過している。
- **post**: evidence 行は task・kind・value で一意に固定され、以後不変（UPDATE/DELETE API は存在せず、
  DB トリガも常時拒否）。
- **invariant**: done 遷移は現 workflow の必須 kind 全存在＋各 kind 規則の**再検証**を通過した場合のみ。
  外部操作は operation_log 証跡化 → 状態遷移の順（逆順の実装経路を作らない）。
- 検証オラクル群: TC-EVD-01〜10（A/R 20 件）・TC-SCH-05・TC-GATE-03・AC-28 系（末尾 trace 表）。

## 3. kind 10 種の検証器構成（DU-09）

kind は 10 種（plan_record／commit_hash／review_pass／published_url／measurement／screenshot／
file_hash／approval／operation_log／dashboard — 必須キー・列対応の正準は s0-contract §2.1 の表）。
実装は **kind → validator の登録制ディスパッチ**とし、共通検証 → kind 固有検証の 2 段で行う。

1. **共通検証**（全 kind）: payload の JSON object 性・必須キーの存在と非空・
   credential/secret パターン（DU-14 と共有する正規表現集合、config 拡張可）の不在・
   `UNIQUE(task_id, kind, value)` の事前照合。
2. **kind 固有検証**: 値の意味検査（例: review_pass は `result = PASS` かつ reviewer ≠ author、
   commit_hash は 40/64 桁かつ列と payload の同値、published_url は `assets.canonical_url` との整合、
   approval は `approvals.evidence_id` との相互整合、operation_log は secret・本文の不在）。
3. 未登録 kind の INSERT 要求・検証器欠落は `GateRejected`（判定不能を通さない）。
   違反時は DB に行を作らない（fail-close — INSERT 前拒否なので rollback も不要）。

`value` は kind 内の安定同一性キーであり、再実行時の重複投入は UNIQUE で既存行に収束する（冪等）。

## 4. タスク種別ごとの必須証跡セット

必須 kind の宣言正本は `workflows.required_evidence_json`（DDL）であり、S0 seed の基準は
s0-contract §2.1: **T-PLAN = plan_record／T-PROD = commit_hash／T-REVIEW = review_pass／
T-PUB = published_url・screenshot・approval／T-MEAS = measurement・file_hash・screenshot**。

実装上の要点:

- 完備ゲート（DU-08 `check_complete`）は task の現 workflow から required kind を読み、
  ハードコードしない（workflow 版追加で宣言だけ変えられる）。
- 宣言に**未定義 kind が含まれる場合は判定不能として done を拒否**する（AC-28-3 — 宣言ミスを
  黙って無視して done を許さない）。
- required にない kind の追加証跡は許容する（append-only の追記は自由、完備判定は required のみ）。

## 5. done 遷移の完備検証シーケンス

```mermaid
sequenceDiagram
    participant V as verifier（verify_pass 要求）
    participant SM as DU-01 transition()
    participant G as DU-08 check_complete()
    participant S as DU-09 store（validator）
    V->>SM: transition(task, verify_pass)
    SM->>G: guard G5: check_complete(task_id)
    G->>G: workflow.required_evidence_json 読込
    G->>S: kind ごとに存在照合＋kind 規則の再検証
    alt 欠落・規則違反・未定義 kind
        G-->>SM: GateRejected（EvidenceIncomplete）
        SM->>SM: rejected 行を記録（task は verifying のまま）
    else 完備
        SM->>SM: state → done ＋ state_transitions passed（単一 tx）
    end
```

再検証（INSERT 時に通った規則を done 時にもう一度）を省略しない — 証跡投入後に参照先
（assets・approvals・pair）が変わった場合の不整合を done の直前で検出するため。

## 6. append-only と順序規律（NFR-3）

- **append-only**: evidence への UPDATE/DELETE は DB トリガが常時拒否
  （[db-design_v0.1.md §3.2](../../L4-basic-design/canonical/data/db-design_v0.1.md) トリガ 3–4）。DU-09 は read/INSERT API のみを公開し、
  訂正は新しい value での追記＋参照側の付替えで表現する（過去の done 判定根拠を消さない）。
- **operation_log 証跡化 → 状態遷移の順**: 外部操作は `external_operations` が confirmed/rejected に
  確定した後、まず operation_log 証跡を派生記録し、**その後に**状態遷移を発火する。
  遷移 tx の中に外部 I/O を入れない・証跡未記録のまま状態だけ進める経路を作らない
  （順序はワークフロー実行器 DU-04/DU-02 が固定し、operation_log は状態遷移の記録には使わない）。
- 証跡 INSERT は呼出し元 tx に参加できる（例: TLP 生成 tx）が、単独でも意味が完結する行のみ書く。

## 7. trace 表

| 設計要素 | DU | AC | TCC |
|---|---|---|---|
| kind 10 種の型契約検証（受理／拒否） | DU-09 | AC-28-1（ほか kind 別 AC-EVD 系） | TC-EVD-01〜10 A/R, TC-SCH-05 |
| done 遷移の完備検証 | DU-08, DU-01 | AC-28-1, AC-28-2 | TCC-28-1, TCC-28-2, TC-GATE-03 |
| 未定義 kind 宣言の fail-close | DU-08 | AC-28-3 | TCC-28-3 |
| append-only（トリガ＋API 非公開） | DU-09, DU-10 | AC-71-3 | TCC-71-3 |
| 証跡化→状態遷移の順序（NFR-3） | DU-02, DU-04 | AC-44-1, AC-26-1 | TCC-44-1, TCC-26-1 |
| credential 混入拒否 | DU-09, DU-14 | AC-47 系 | TCC-47（TC-047） |
