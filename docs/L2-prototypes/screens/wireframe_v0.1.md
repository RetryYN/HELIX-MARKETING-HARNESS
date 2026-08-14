---
artifact_id: L2-UI-WIREFRAME
lifecycle_status: draft
slice: S1
---

# UI ワイヤーフレーム v0.1

> status: **draft**。テキスト wireframe とレイアウト不変条件を定義する。CSS・コンポーネント実装は未着手。
> 要求再定義中の旧要求ベース参考資料であり、新要求の設計・実装入力ではない。

## 共通レイアウト

```text
+----------------------------------------------------------------+
| G-BRAND-SCOPE | breadcrumb | auth/principal                     |
+----------------------+-----------------------------------------+
| navigation            | page title / status / filter            |
| AP BR ST BI EV NT RN |                                         |
|                      | primary content                        |
|                      | table / detail / evidence              |
|                      |                                         |
|                      | footer: source / digest / request id   |
+----------------------+-----------------------------------------+
```

- desktop は navigation／content の 2 列、狭幅は navigation を drawer 化し content を 1 列にする。
- `brand`、principal、status、request id は content の上端または footer で常時把握できる。
- 失敗・empty・loading は同じ領域を占有し、レイアウトシフトで操作対象を取り違えない。

## 主要画面の wireframe

### AP-01 承認待ち一覧

```text
[brand] [status filter] [search]                         [refresh]
------------------------------------------------------------------
| status badge | approval title | target | age | evidence | open |
| ...                                                         AP-02|
------------------------------------------------------------------
```

### AP-02 承認詳細

```text
[back AP-01] [approval id] [status badge]
------------------------------------------------------------------
| preview (read-only)                  | evidence / source       |
| requested operation / policy         | digest / request id     |
------------------------------------------------------------------
| [reject] [return]                         [approve explicit]   |
```

### BR-01／ST-01

```text
[brand scope] [route title] [status]
------------------------------------------------------------------
| profile/config list | selected schema-driven detail/form        |
| scope/status        | masked secret | validation | [save]       |
------------------------------------------------------------------
```

### BI-01／EV-01

```text
[brand] [period] [medium] [kind]
------------------------------------------------------------------
| KPI cards / warning banner       | selected evidence detail   |
| node / measurement / status      | source + digest + links    |
------------------------------------------------------------------
```

### RN-01

```text
[brand] [run status] [time range]
------------------------------------------------------------------
| run/task table                   | failure / operation log   |
| state / age / evidence link      | request id | [view]        |
------------------------------------------------------------------
```

BR-02、ST-02、BI-02、EV-02、NT-01 は同じ header／scope／footer region を paired detail として再利用する。
新しい媒体を追加しても media/account 行を増やし、画面の意味や write 境界を変更しない。

## レビュー観点

- 全画面で 5 状態、キーボード順序、狭幅での focus、失敗時の request id が確認できる。
- 承認・設定の write は wireframe 上でも read-only 部分から視覚的に分離される。RN-01 の失敗行は EV-02 の
  evidence 閲覧へ遷移するだけで、未契約の retry API を持たない。
- Discord deep-link は AP-02／EV-01 の通常入口と同じ確認領域を通り、URL だけで確定しない。
