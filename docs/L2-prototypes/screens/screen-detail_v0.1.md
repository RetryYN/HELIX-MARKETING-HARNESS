---
artifact_id: L2-UI-SCREEN-DETAIL
lifecycle_status: draft
slice: S1
---

# UI 画面詳細 v0.1

> status: **draft**。HELIX-HARNESS の screen-detail 必須 13-field matrix を現行 12 画面へ適用した設計台帳。
> 画面単位で「何を表示するか」「何を操作できるか」「失敗時にどうなるか」「上位要求を満たすか」を確認できる。

## 必須 field

| Field | 役割 |
|---|---|
| Screen ID | screen-list の安定 ID |
| Purpose | 画面が支える user decision / review task |
| Persona | 主たる human user。AI runtime は直接操作しない |
| Route | screen-list の canonical URL |
| Inputs | path/query、local state、projection、command output |
| Display Blocks | 読み順の主要な表示領域 |
| Controls | navigation、filter、expander、manual refresh、許可済み action |
| Validation / Empty State | missing／stale／invalid／未投影データの表示 |
| Error State | fail-close、fallback、next action |
| Security / Permission | persona、scope、secret／PII の表示境界 |
| State Persistence | URL query、path、session、local state、none |
| Trace | BR／UX／FR と L2 文書への trace |
| Test / Review Hook | 実装前に必要な manual／automated check |

## 画面詳細 matrix

| Screen ID | Purpose | Persona | Route | Inputs | Display Blocks | Controls | Validation / Empty State | Error State | Security / Permission | State Persistence | Trace | Test / Review Hook |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AP-01 | 承認待ちを確認し対象を選ぶ | PO／reviewer | `/ap/pending` | brand、status、cursor、approvals projection | scope header、status filter、approval table、evidence link | filter、manual refresh、AP-02 navigation | 空なら理由と対象範囲を表示 | auth／scope／timeout を red と next action で表示 | 認証済み principal と brand scope、secret 非表示 | brand／filter を query に保持 | BR-I1／FR-46、screen-list／screen-flow | table keyboard、5 状態、URL back を確認 |
| AP-02 | approval の内容と証跡を確認し明示判断する | PO／approver | `/ap/{approval_id}` | approval id、brand、approvals／evidence | preview、policy、source／digest、action region | evidence navigation、explicit approve／reject、return | 対象なし・期限切れを理由付き表示 | CSRF／policy／conflict は fail-close、request id を表示 | principal／scope／再認証を要求、secret redact | approval id と元 filter を path/query に保持 | ADR-010／FR-46/77、screen-flow／ui-element | reject／boundary AC/TC と a11y action を確認 |
| BR-01 | ブランド scope を選択する | PO／operator | `/br` | business_profiles projection、principal | profile table、scope/status badge | select、filter、manual refresh | profile が空なら setup guidance | scope denied は profile を作らず説明 | principal に許可された profile のみ | 選択 profile を次 route の `brand` query に保持 | FR-34／FR-74、screen-list／screen-flow | CrossProfileAccessDenied と back を確認 |
| BR-02 | 媒体・account 台帳の状況を確認する | PO／operator | `/br/{profile_key}` | profile key、FR-74 S1 projection（S0 DDL の現行 table ではない） | profile header、service/account table、status | filter、row detail、return | projection 未生成は planned／empty と明示 | stale／missing projection を error 表示 | profile scope 内だけ。credential_ref／secret は非表示 | profile key を path に保持 | FR-74（S1 migration）、screen-list／ui-element | projection と scope の read-only 突合 |
| ST-01 | schema 駆動の設定を確認・登録する | PO／operator | `/st?brand={key}` | brand、config schema、current version | schema form、masked value、validation、history link | validate、manual refresh、許可された config INSERT | 未設定は empty と schema guidance | validation／conflict を field 単位で表示 | masked secret、principal／brand scope、config INSERT のみ | brand／config key を query に保持 | FR-33/34/47、screen-flow／ui-element | secret redaction、CSRF、config AC/TC を確認 |
| ST-02 | 設定の supersedes 連鎖を確認する | PO／reviewer | `/st/history?key={config_key}` | config key、version、config projection | version chain、diff、source／digest | version filter、return、manual refresh | history が無い場合は empty reason | chain mismatch／scope denied を表示 | read-only、secret は diff でも redact | config key／version を query に保持 | FR-33／s0-contract、screen-flow／wireframe | chain 順序と digest を突合 |
| BI-01 | ブランド単位 KPI と異常箇所を確認する | PO／analyst | `/bi?brand={key}&period={p}` | brand、period、medium、kpi_nodes、measurements | KPI cards、warning banner、trend/table、evidence link | period／medium filter、manual refresh、EV-01 navigation | 測定不足は empty／unknown と表示 | stale／measurement error に next action | scope 内の集計だけ、write なし | brand／period／medium を query に保持 | KPI handoff／FR-78、screen-flow／wireframe | raw source と evidence の一致を確認 |
| BI-02 | 全ブランドの KPI を俯瞰する | PO／analyst | `/bi/all?period={p}` | period、all-profile projection、principal | profile summary、comparison table、scope warning | period／sort／BR-02 navigation、manual refresh | profile 未投影は gray／unknown | 越境 scope は拒否し partial green にしない | aggregate は許可 profile の範囲のみ | period／sort を query に保持 | FR-34／S-integrate、screen-list／wireframe | scope isolation と sample-size を確認 |
| EV-01 | evidence の source と digest を閲覧する | PO／reviewer | `/ev?brand={key}&kind={k}` | brand、kind、cursor、evidence | filter、record table、source、digest、detail | kind／period filter、record open、manual refresh | evidence 0 件は kind／期間を明示 | digest mismatch／not found を fail-close | read-only API scope、payload redact | brand／kind／cursor を query に保持 | FR-77／s0-contract、screen-flow／ui-element | masking、source link、read-only を確認 |
| EV-02 | external operation の実行記録を確認する | PO／operator | `/ev/ops?brand={key}` | brand、operation filter、external_operations | operation table、request／correlation、result | filter、detail、manual refresh | log なしは empty reason | request／evidence 不整合を error | profile scope、credential／payload 非表示 | brand／filter を query に保持 | FR-75/76／s0-contract、screen-flow | operation↔evidence 1:1 を確認 |
| NT-01 | 通知履歴と許可済み購読設定を確認する | PO／operator | `/nt?brand={key}` | brand、external_operations、subscription config | delivery history、status、subscription form | filter、manual refresh、許可された config INSERT | 配信なしは empty、未設定は guidance | endpoint／allow-list／delivery error を表示 | service／operation／endpoint allow-list と principal | brand／subscription key を query に保持 | FR-76／ADR-010、screen-flow | secret 非表示、allow-list boundary を確認 |
| RN-01 | 実行状況と失敗理由を閲覧する | PO／operator | `/rn?brand={key}` | brand、loop_runs、tasks、status filter | run/task table、failure detail、operation/evidence link | filter、manual refresh、EV-02 navigation | run が無ければ empty reason | timeout／fatal を request id と表示 | read-only。retry API／write control は置かない | brand／run／filter を query に保持 | s0-contract／NFR-5、screen-flow／wireframe | stale/failed 状態、operation link、no-write を確認 |

## 共通レビュー条件

- 5 状態（ok／warn／error／empty／loading）、keyboard 順序、狭幅での focus、request id を全画面で確認する。
- signed-off contract が許可しない直接 mutation、CLI 自動実行、URL だけの承認確定を含めない。
- `media_accounts` は FR-74 の S1 migration／projection であり、S0 の現行 DDL table として扱わない。
- テンプレートの 13 field を埋めた後、screen-flow の edge、ui-element の要素、wireframe の layout と相互に突合する。
