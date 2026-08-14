---
artifact_id: L2-UI-ELEMENT
lifecycle_status: draft
slice: S1
---

# UI 要素定義 v0.1

> status: **draft**。要素 ID、意味、データ、状態、操作境界を定義する。実装コンポーネントの完了宣言ではない。
> 要求再定義中の旧要求ベース参考資料であり、新要求の設計・実装入力ではない。

## 共通要素契約

| 要素 ID | 意味 | 入力／データ | 状態 | 操作境界 |
|---|---|---|---|---|
| G-BRAND-SCOPE | 現在のブランド scope | `business_profiles` | loading／ok／empty／error | 切替は query 更新。越境は拒否 |
| G-STATUS-BADGE | 業務状態の 3 重符号化 | state enum | ok／warn／error／empty／loading | 色だけで意味を伝えない |
| G-EVIDENCE-LINK | evidence の出所を開く | evidence id／kind | ok／empty／error | read-only。source と digest を表示 |
| G-APPROVAL-ACTION | 承認・拒否・差戻し | approval id、principal | loading／ok／error | 承認 API の明示操作のみ |
| G-SECRET-VALUE | 秘匿値の表示 | config masking pattern | masked／empty／error | plaintext を DOM・ログへ出さない |
| G-REFRESH | 表示データの手動再取得 | query／projection cursor | disabled／ready／error | read-only。request id と取得時刻を表示 |

## 画面別要素台帳

| 画面 | 必須要素 | 読み取りデータ | write 要素 |
|---|---|---|---|
| AP-01 | G-BRAND-SCOPE、G-STATUS-BADGE、filter、table、G-EVIDENCE-LINK | approvals | なし |
| AP-02 | approval summary、preview、G-EVIDENCE-LINK、G-APPROVAL-ACTION | approvals／evidence | 承認 API の action |
| BR-01 | G-BRAND-SCOPE、profile table、status | business_profiles | なし |
| BR-02 | profile header、media/account table、G-STATUS-BADGE | FR-74 S1 projection（media_accounts） | なし |
| ST-01 | schema form、G-SECRET-VALUE、validation、G-REFRESH | config | config INSERT |
| ST-02 | version chain、diff、G-EVIDENCE-LINK | config | なし |
| BI-01／BI-02 | period／medium filter、KPI cards、G-STATUS-BADGE | kpi_nodes／measurements | なし |
| EV-01／EV-02 | kind filter、record table、source、digest | evidence／external_operations | なし |
| NT-01 | delivery history、subscription form、G-STATUS-BADGE | external_operations／config | subscription config のみ |
| RN-01 | run/task table、failure detail、G-EVIDENCE-LINK、G-REFRESH | loop_runs／tasks | read-only。EV-02 へ遷移 |

## 状態・アクセシビリティ

- loading は skeleton と `aria-busy`、empty は理由と次の行動、error は原因・request id・再取得可否を表示する。
- status は `role="status"` または適切な live region とし、表の行選択はキーボードで再現できる。
- disabled は権限不足・状態不一致・再送中を区別し、tooltip だけに理由を隠さない。
- secret はマスク済み表示だけを許し、copy／download／screen reader の出力にも plaintext を含めない。

## 設計上の不変条件

1. 要素 ID は画面間で再利用する場合も意味を変えない。
2. write 要素には対象契約、principal、scope、evidence、明示操作条件を割り当てる。
3. UI の状態名は DDL／transitions.json／L3 契約から導出し、画面専用 enum を作らない。
4. 未契約の retry API、外部操作の自動再送、UI からの CLI 自動実行は要素台帳に登録しない。
