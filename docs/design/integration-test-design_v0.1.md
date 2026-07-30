# 総合テスト設計書 v0.1（④）

> status: **confirmed**（2026-07-31 PO 承認 — 基本設計完遂指示。AI 起草）
> pair: [basic-design_v0.1.md](basic-design_v0.1.md)（基本設計② — HELIX 式 ②↔④ 文書ペア）
> 対象文書: basic-design_v0.1.md の CMP-01〜CMP-13 全コンポーネント。
> 上位文書: [verification-design_v0.1.md](../requirements/verification-design_v0.1.md)（検証設計③ — TC 59 は
> ユニット/コンポーネント粒度、本書 ITC はコンポーネント結合〜E2E 粒度で階層を分担する）
> JSON 正本: [json/itest.json](json/itest.json)（ITC 台帳。本文と同期、実装入力は JSON）

---

## 1. 位置づけと合否基準

- ③（TC 59）が「各 AC を最小粒度で示す」のに対し、④（ITC 16）は「CMP を結合した実シナリオで
  s0-contract の契約が崩れないこと」を示す。**全 13 CMP は 1 件以上の ITC に登場し、全 19 AC は
  1 件以上の ITC が参照する**（ゲート G-ITC-CMP / G-ITC-AC が機械検証）。
- 拒否系（fail-close の実証）を 8 件含む。総合テストの PASS は各 S0 更新の完了条件であり、
  S0.2/S0.3 は前更新の ITC を回帰実行する（デグレ検出）。
- **③との階層分担**: 各 ITC は ③の該当 TC（同一 AC を参照するもの）をステップとして再利用し、
  ④固有の追加分は「結合観測点」（assertions — JSON 正本の `assertions` 配列）に限定する。
  同一検証の二重実装はしない。
- 実行系: pytest（`tests/integration/`）。外部実サービスへの書込みは Docker WP のみ（環境契約 §6）。

## 2. fixture（試験環境部品）

| fixture | 内容 | 使用 ITC |
|---|---|---|
| tmp_db | 空 SQLite に全 migration 適用済みの一時 DB＋seed（agents 2 体以上・WF 3 種・config） | 全件 |
| wp_docker | `wordpress`+`mariadb` コンテナ、テスト管理者、REST 有効 | ITC-08, 09, 11, 16 |
| ga4_mock | GA4 Data API/エクスポートの成功・失敗・破損行・timeout 応答 | ITC-13, 14, 16 |
| approval_mock | 承認 transport の approve / reject / expire / binding 不一致応答 | ITC-09, 10, 16 |
| secrets_tmp | テスト用暗号化ストア（テスト credential のみ。endpoint 突合検査用の偽本番値を含む） | ITC-12, 15 |

## 3. 総合テストケース（ITC 台帳）

| ID | 更新 | 極性 | 対象 CMP | 参照 AC | シナリオ |
|---|---|---|---|---|---|
| ITC-01 | S0.1 | accept | CMP-05 | AC-71, AC-72 | 空 DB→全 migration 適用で 21 テーブル再現、FK/integrity PASS、schema_version に checksum 記録、次版昇格も成功 |
| ITC-02 | S0.1 | reject | CMP-01, CMP-02 | AC-11, AC-13, AC-27 | 遷移表（s0-contract §3.1/3.2）の**全許可・全拒否組合せをパラメタライズ実行**: 未定義遷移・終端からの遷移は状態/retry_count 不変＋rejected ログ、自己審査割当は DB CHECK とエンジン双方で拒否、verify_fail 反復の retry 境界（上限-1 / 上限到達→escalated） |
| ITC-03 | S0.1 | reject | CMP-03, CMP-04 | AC-28 | 必須証跡欠落時の done 遷移拒否、kind 型契約違反 payload の INSERT 拒否、credential 文字列混入の evidence 拒否 |
| ITC-04 | S0.1 | accept | CMP-06 | AC-33 | config の INSERT 履歴化・supersedes 連鎖・有効値解決、UPDATE/DELETE がトリガで拒否される |
| ITC-05 | S0.1 | reject | CMP-03, CMP-05 | AC-23 | 有料指標型（cac/roas/ad_spend）の kpi_node 登録を DB CHECK（直接 INSERT）とゲートエンジン API の双方で拒否、広告ドメイン denylist（config 値）が登録を拒否 |
| ITC-06 | S0.1 | accept | CMP-01, CMP-02, CMP-04 | AC-11 | 強制終了→再起動の再開規則を **s0-contract §3.3 の全行についてパラメタライズ実行**: pending 再 claim、外部操作前後の in_progress、verifying 再検証（二重加算なし）、loop_run waiting の再照合 resume、終端状態の遷移不可 |
| ITC-07 | S0.2 | accept | CMP-02, CMP-03, CMP-12 | AC-12, AC-51, AC-54 | WF-WP-1 一気通貫: 企画→原稿生成（同一入力→同一 hash）→commit 固定→別 agent 審査 PASS→pair_plan_quality 成立。tasks 行の WF ID・担当・期待成果物型が非 NULL |
| ITC-08 | S0.2 | reject | CMP-03, CMP-10 | AC-21, AC-44 | pair 未成立/revoked/hash 不一致での公開要求を WP API 呼出し前に拒否（HTTP リクエストが発生しないことを mock で証明） |
| ITC-09 | S0.2 | accept | CMP-10, CMP-11, CMP-03, CMP-04 | AC-44, AC-46 | WF-WP-2 一気通貫: pair 成立→Docker WP 下書き→束縛承認 approve→公開→URL/スクショ/approval 証跡が evidence に揃い T-PUB done |
| ITC-10 | S0.2 | reject | CMP-11 | AC-46 | 承認 binding 3 項目の 1 つでも不一致なら公開拒否、rejected/expired は task failed、pending 中は親 loop_run が waiting のまま task が進行しない |
| ITC-11 | S0.2 | reject | CMP-10 | AC-44 | 同一 idempotency_key の再送で二重公開なし（operation_log 照合で結果補完）、照合不能な timeout は再送せず escalated |
| ITC-12 | S0.2 | reject | CMP-07 | AC-47 | テスト credential→本番 endpoint / 本番 credential→Docker の組合せを接続前に拒否、ログ・DB・evidence 全走査で平文 credential 検出 0 件 |
| ITC-13 | S0.3 | accept | CMP-13, CMP-04 | AC-61 | WF-MEAS-1 一気通貫（ga4_mock）: 取得→SHA-256 固定→パース→measurements 投入が kpi_node と取得証跡へ FK 接続 |
| ITC-14 | S0.3 | reject | CMP-13 | AC-62 | 破損行は隔離＋証跡化し正常行のみ投入、hash 再計算不一致は投入自体を拒否、transaction 失敗は全 rollback |
| ITC-15 | S0.2 | accept | CMP-07, CMP-08, CMP-09 | AC-41, AC-42 | レジストリのデータ変更のみで api→browser 経路切替が反映、playbook 実行成功で last_success_at 更新、ブラウザ基盤の headed/headless 起動と storage_state 再利用 |
| ITC-16 | S0.3 | accept | CMP-01〜CMP-13 | AC-44, AC-46, AC-61 | ウォーキングスケルトン E2E（s0-contract §8）: 記事 1 本を企画→制作→審査→承認→Docker WP 公開→計測取込まで通し、commit_hash / review_pass / published_url / screenshot / approval / measurement が単一 DB に揃う。**全 CMP の観測点を assert**: config 値解決（CMP-06）・registry 経路選択（CMP-07）・playbook 参照と last_success_at 更新（CMP-09）・ブラウザ経由スクショ（CMP-08）・state_transitions 完全記録（CMP-01） |

## 4. 回帰・デグレ対策

- S0.2 完了条件 = S0.2 の ITC ＋ **S0.1 の全 ITC 再実行 green**。S0.3 も同様に S0.1/S0.2 を回帰する。
- ITC は CI で毎 push 実行する（wp_docker/ga4_mock はサービスコンテナ・fixture で CI 内完結。
  実 GA4・本番 WP には触れない）。
- 台帳の削除・縮小はベースラインゲート（G-BASE-RATCHET の ITC 分母）で禁止。追加のみ許す。

## 5. 対象外（S0 では実施しない）

負荷・性能試験（NFR に該当基準なし）、本番 WP への書込み試験（環境契約で禁止）、
実 GA4 property への書込み（存在しない）、UI 表示試験（S0 に UI なし。ダッシュボード HTML は S1 FN-605）。
