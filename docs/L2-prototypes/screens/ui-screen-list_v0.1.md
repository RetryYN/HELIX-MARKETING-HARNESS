---
artifact_id: L2-UI-SCREEN-LIST
lifecycle_status: draft
slice: S1
---

# UI 画面一覧 v0.1（運用 UI — 設定・BI・通知・ブランド/アカウント統合）

- status: draft（PO 未承認。要求再定義中の旧要求ベース参考資料であり、新要求の設計・実装入力ではない）
- SSoT 参照: 本文書は表示の構造のみを定義し、業務語彙・状態遷移・データを独自定義しない。
  値の正本 = s0-contract の DDL（business_profiles／approvals／evidence／external_operations／
  kpi_nodes／config）と L3 契約（FR-74〜77・NFR-11、および規範利用する FR-33 設定履歴／
  FR-34 profile スコープ／FR-46 承認チャネル・Web UI 解禁条件／FR-47 秘匿情報／NFR-5 滞留 SQL）。
  承認の意味論 = ADR-010（confirmed）。スライス帯の語彙 = ADR-008 v0.2。
- 実装状態: 全画面未実装。Web UI channel は FR-46 の認証・CSRF・再認証・principal 束縛の
  AC/TC を追加する契約が confirmed になるまで不許可（本文書だけで実装着手・完了を主張しない）。
- 書式出典: RetryYN/HELIX-HARNESS の L2-screen 方法論（screen-list／screen-flow／ui-element／
  wireframe／screen-detail の 5 点セット）。本文書はその 1 点目で、残 4 点は同じ S1 draft として追補済み。

## 0. 設計制約（上位で確定済みの継承事項）

1. 全画面 read-only を既定とし、write は承認 API（ADR-010 不変条件 1 — 入口は状態を直接
   確定しない）と config INSERT（FR-33）だけに限る
2. ブランド切替が全画面の第一軸（`?brand=` query string — 共有と browser back を成立させる）。
   スコープは FR-34（CrossProfileAccessDenied・deny-by-default）を UI にも同一適用
3. 状態表示は 5 値 ok／warn／error／empty／loading を全画面で網羅し、
   色+アイコン+ラベルの 3 重符号化（色のみ非依存）
4. secret は FR-47 の config.secret.masking_patterns で必ず redact（FR-77）
5. 通知 deep-link は認証後に対象と操作を再表示して明示操作を要求（URL だけで確定しない — ADR-010）
6. 画面に出る「エージェント」は常に製品ランタイム側（s0-contract の agents）を指す。
   開発用エージェント（codex 等）は UI に現れない

## 1. 画面一覧（Bounded Context 接頭辞採番・ID↔URL 1:1・状態は query string）

| 画面 ID | 画面名 | BC | URL | 主参照（読取り） | write |
|---|---|---|---|---|---|
| AP-01 | 承認待ち一覧 | Approval | /ap/pending | approvals | なし |
| AP-02 | 承認詳細（プレビュー+承認/拒否/差戻し） | Approval | /ap/{approval_id} | approvals, evidence | 承認 API のみ |
| BR-01 | ブランド一覧/切替 | Brand | /br | business_profiles | なし |
| BR-02 | ブランド詳細（media × account 台帳 — FR-74） | Brand | /br/{profile_key} | FR-74 S1 projection（media_accounts） | なし |
| ST-01 | 設定一覧（config 行のスキーマ駆動フォーム） | Settings | /st?brand={key} | config | config INSERT のみ |
| ST-02 | 設定変更履歴（supersedes 連鎖） | Settings | /st/history?key={config_key} | config | なし |
| BI-01 | KPI ダッシュボード（layer×medium×期間） | BI | /bi?brand={key}&period={p} | kpi_nodes, measurements | なし |
| BI-02 | 横断 BI（全ブランド俯瞰 — S-integrate 接続） | BI | /bi/all?period={p} | 同上（全 profile） | なし |
| EV-01 | 証跡ブラウザ（FR-77 read-only API の画面） | Evidence | /ev?brand={key}&kind={k} | evidence | なし |
| EV-02 | 外部操作ログ | Evidence | /ev/ops?brand={key} | external_operations | なし |
| NT-01 | 通知履歴/購読設定（FR-76） | Notify | /nt?brand={key} | external_operations | 購読 config のみ |
| RN-01 | 実行状況/失敗履歴（NFR-5 の滞留 SQL） | Run | /rn?brand={key} | loop_runs, tasks | なし |

## 2. 遷移の骨格（詳細エッジ表は screen-flow で追補）

- 第一軸: BR-01 でブランド選択 → 以降全画面 `?brand=` を保持
- 主動線: AP-01→AP-02（承認）／BI-01→EV-01（KPI 異常→証跡確認）／
  RN-01→EV-02（失敗→操作ログ）／ST-01→ST-02（変更→履歴）
- 通知 deep-link: Discord 通知 → AP-02／EV-01（§0-5 の再表示原則に従う）

## 3. 段階出荷（ADR-008 の媒体縦切りとの対応）

- V1.0（WP 貫通）と同時: AP-01/02・ST-01・EV-01・RN-01 の最小 5 画面
- 媒体追加ごと: BR-02 の台帳行・BI-01 の medium 軸・NT-01 のイベント種が
  スキーマ駆動で増える（画面の新設は不要）
- S-integrate: BI-02 解禁

## 4. 未決事項（PO 判断・S1 設計で確定）

1. 認証方式（FR-46 解禁条件の具体 AC/TC — 別契約で起票）
2. ホスティング位置（helix-worker の VPS approval API と同居か分離か）
3. 認証方式（FR-46 解禁条件）と screen-detail の PO 承認順序
