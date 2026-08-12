---
artifact_id: L2-BUSINESS-FLOW
lifecycle_status: draft
slice: S1
---

# L2 業務 flow v0.1

> status: **draft**。screen-flow の遷移を actor lane と判断点へ展開する。製品 runtime の実装や外部 write の許可を意味しない。

## Actor lane

```text
PO / approver       Operator / analyst       Product runtime       Read models / evidence       External channel
    |                       |                       |                       |                         |
    | scope・価値を承認     |                       |                       |                         |
    |---------------------->|                       |                       |                         |
    |                       | 画面を閲覧・filter    |                       |                         |
    |                       |---------------------->| read projection       |                         |
    |                       |<----------------------|                       |                         |
    | explicit action       |                       | policy / scope check  |                         |
    |---------------------->|---------------------->|---------------------->|                         |
    |                       |                       | evidence を記録       |                         |
    |                       |                       |-----------------------------------------------> notification (allow-list only)
```

## シナリオと判断点

| Flow ID | Actor / trigger | Screen edge | system decision | human decision | evidence |
|---|---|---|---|---|---|
| BF-01 approval | PO が AP-01 の行を選択 | AP-01 → AP-02 | principal／brand／policy／期限を検査 | approve／reject／return | approval、evidence、request id |
| BF-02 brand scope | operator が BR-01 で profile を選択 | BR-01 → BR-02／各 route | CrossProfileAccessDenied を fail-close | 利用 profile を選ぶ | scope decision |
| BF-03 config | operator が ST-01 を入力 | ST-01 → ST-02 | schema、secret mask、version conflict を検査 | config INSERT を明示承認 | config row、digest、history |
| BF-04 KPI | analyst が BI-01 の異常を選択 | BI-01 → EV-01 | measurement と evidence の対応を確認 | 原因・次の調査を判断 | KPI、evidence、source |
| BF-05 operation failure | operator が RN-01 の失敗を選択 | RN-01 → EV-02 | operation／evidence／request を 1:1 突合 | 再実行は UI で行わず運用手順へ送る | external_operations、operation log |
| BF-06 notification | Discord の deep-link を開く | NT-01 → AP-02／EV-01 | 認証後に対象と操作を再表示 | explicit action を行う | delivery／request／target |

## 境界と禁止事項

- `screens/` は read-only を既定とし、write は現行契約が明示する承認 API／config INSERT／許可済み通知だけに限定する。
- `media_accounts` は FR-74 の S1 projection／migration であり、S0 DDL の現行 table として読み替えない。
- Discord は通知・deep-link の入口であり、URL だけで承認や状態遷移を確定しない。allow-list と principal を再検査する。
- timeout／unknown／stale は成功として扱わず、error／empty と next action を表示して evidence を残す。

## 対応関係

- screen edge: [screen-flow](../screens/screen-flow_v0.1.md)
- element／write boundary: [ui-element](../screens/ui-element_v0.1.md)
- detail／trace／test hook: [screen-detail](../screens/screen-detail_v0.1.md)
- 実運用の観測計画は `operating-scenarios/` に次の S1 設計で追加する。
