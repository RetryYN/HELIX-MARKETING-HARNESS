---
artifact_id: L2-UI-SCREEN-FLOW
lifecycle_status: draft
slice: S1
---

# UI 画面フロー v0.1

> status: **draft**。screen-list の画面 ID と s0-contract／L3 契約を参照する遷移正本。画面から業務状態を直接確定しない。

## 共通フロー規則

- 入口・前提条件・保持する context（`brand`、期間、filter）・戻る操作・失敗時の出口を 1 エッジに記録する。
- URL deep-link は認証後に対象と操作を再表示し、承認・拒否・設定 INSERT を自動実行しない。
- `ok`／`warn`／`error`／`empty`／`loading` の 5 状態は、色・アイコン・ラベルの 3 要素で表現する。
- 外部操作の失敗は EV-02 または RN-01 に evidence／request／operation の束縛を表示し、再実行は明示操作とする。

## シナリオとエッジ

| ID | trigger／入口 | 前提・保持 context | 正常出口 | 拒否・失敗出口 | browser back |
|---|---|---|---|---|---|
| F-01 承認 | AP-01 の行選択 | 認証済み、`brand` と approval id を保持 | AP-02 → 明示承認 → AP-01 | 権限拒否／expired → AP-02 の evidence | AP-01 の filter を保持 |
| F-02 ブランド | BR-01 のブランド選択 | profile が存在し scope 許可 | 各画面へ `?brand=` 付きで遷移 | CrossProfileAccessDenied → BR-01 | 選択前の route と query を復元 |
| F-03 設定 | ST-01 の config 行選択 | schema／current version を取得済み | config INSERT → ST-02 | validation／conflict → ST-01 | 入力は破棄せず再表示 |
| F-04 KPI | BI-01 の異常 node | period／medium／brand を保持 | EV-01 で evidence を確認 | 測定欠落 → empty／BI-01 | filter を保持 |
| F-05 実行失敗 | RN-01 の failed task | run id と task id が存在 | EV-02 で operation log を確認 | evidence 欠落 → RN-01 error | run context を保持 |
| F-06 通知 | Discord の承認／証跡 deep-link | 認証・principal・brand scope を再確認 | AP-02 または EV-01 で明示操作 | 不正／期限切れ → AP-01 | 通知元へ戻れる |

## 画面ごとの戻りと状態保持

| 画面群 | entry context | exit context | 失敗時の再試行 |
|---|---|---|---|
| AP-01／AP-02 | `brand`、status、cursor | approval id、evidence id | 同じ approval を再読込。操作は再実行しない |
| BR-01／BR-02 | profile key | `brand` query | scope 再取得。無い profile は作らない |
| ST-01／ST-02 | config key、version | config row、history cursor | validation を修正し再送信は明示 |
| BI-01／BI-02 | period、medium、brand | node id、evidence kind | 測定を再実行せず evidence を再取得 |
| EV-01／EV-02 | evidence／operation filter | selected record | read-only 再取得 |
| NT-01／RN-01 | notification／run id | subscription／task id | history／operation evidence を明示閲覧 |

## テンプレートとの差分

HELIX-HARNESS の screen-flow が要求する trigger／conditions／state retention／back／6 シナリオを採用し、
本製品固有の承認、brand scope、evidence、Discord deep-link の fail-close 境界を追加した。
