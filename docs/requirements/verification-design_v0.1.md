# 検証設計書 v0.1

> status: **confirmed**（2026-07-31 PO 承認 — 要件定義完遂指示。AI 起草）
> 対象設計: [requirements_v0.1.md](requirements_v0.1.md)／[s0-contract_v0.1.md](s0-contract_v0.1.md)／[br-media_v0.1.md](br-media_v0.1.md)／[loop-task-workflow_v0.1.md](loop-task-workflow_v0.1.md)／[media-requirements_v0.1.md](media-requirements_v0.1.md)
> 機械可読台帳: [json/verification.json](json/verification.json)。AC の正本は [json/ac.json](json/ac.json)。
> 上流戦略層（2026-08-01 追補）: 戦略層要件（SR）の検証は
> [strategy-loop-test-design_v0.1.md](../design/strategy-loop-test-design_v0.1.md)（STC）が対を成す。
> 本書の TC 59 の分母・対象は不変。
> 位置づけ: HELIX 流 pair gate における「要件定義 ↔ 検証設計」の検証側正本。各設計変更は本書と JSON 台帳の該当 TC を同時に更新し、pair が成立しない限り公開系を通さない。

---

## 1. ペア台帳

| 設計文書 | 検証対となる本書の節 | 逆方向の確認対象 |
|---|---|---|
| [requirements_v0.1.md](requirements_v0.1.md) | §2〜§6 | FR/NFR、S0 受入条件、AC-11〜AC-72 |
| [s0-contract_v0.1.md](s0-contract_v0.1.md) | §2〜§5 | DDL、証跡型、遷移、再開、環境、移行、更新分割 |
| [br-media_v0.1.md](br-media_v0.1.md) | §2、§3、§6 | WP/GA4 を含む媒体公開・計測の S0 境界。S1+ は N/A |
| [loop-task-workflow_v0.1.md](loop-task-workflow_v0.1.md) | §2〜§4 | LP/T/WF、T-PUB、WF-WP-1/2、WF-MEAS-1、再開規則 |
| [media-requirements_v0.1.md](media-requirements_v0.1.md) | §2、§3、§6 | WP と MEAS の S0 契約。その他媒体は deferred |

逆方向では、各 TC の `ac`、`text`、fixture、更新境界を JSON 台帳から設計文書へ追跡する。TC の追加・削除時は、設計側の対象節又は N/A を必ずペア台帳へ反映する。

## 2. AC→テストケース設計

fixture はすべて [json/s0/environment.json](json/s0/environment.json) に従う。`sqlite_seed` は一時 SQLite と seed を使う unit/integration fixture、`wp_docker` は唯一の実書込み先であるローカル Docker WP、`ga4_mock` は GA4 fixture/mock、`approval_mock` は通知 transport mock を表す。本番 WP はいずれの TC も書き込まない。

| TC | 対象 AC | 種別 | fixture | 別 | 更新 | 検証内容 |
|---|---|---|---|---|---|---|
| TC-011 | AC-11 | unit | sqlite_seed | reject | S0.1 | 未定義遷移を拒否し状態・retry_countを不変、拒否ログを残す。 |
| TC-012 | AC-12 | integration | sqlite_seed | accept | S0.1 | ループ到達で workflow・author・output kind 非NULLの task を発行する。 |
| TC-013 | AC-13 | integration | sqlite_seed | accept | S0.1 | retry_limit=3 の3回目 FAIL で escalated にする。 |
| TC-021 | AC-21 | integration | sqlite_seed | reject | S0.1 | PASS なしの公開要求を connector 呼出前に拒否する。 |
| TC-023 | AC-23 | unit | sqlite_seed | reject | S0.1 | CAC/ROAS/広告費型 kpi_node を登録拒否する。 |
| TC-027 | AC-27 | integration | sqlite_seed | reject | S0.1 | 同一 author/verifier を DB 制約と engine の双方で拒否する。 |
| TC-028 | AC-28 | integration | sqlite_seed | reject | S0.1 | required kind 欠落時の done 遷移を拒否する。 |
| TC-033 | AC-33 | integration | sqlite_seed | accept | S0.1 | config を INSERT 履歴化し旧値・理由を取得できる。 |
| TC-041 | AC-41 | integration | sqlite_seed | accept | S0.3 | レジストリ行だけの切替が選択経路に反映される。 |
| TC-042 | AC-42 | integration | sqlite_seed | accept | S0.3 | playbook 参照操作の成功後に最終成功日時を更新する。 |
| TC-044-R | AC-44 | integration | sqlite_seed, wp_docker | reject | S0.2 | 成立 pair ID なしの WP 書込みを REST 呼出前に拒否する。 |
| TC-044-A | AC-44 | e2e | sqlite_seed, wp_docker, approval_mock | accept | S0.2 | 成立 pair・束縛承認後、Docker WP で下書き→公開する。 |
| TC-046 | AC-46 | integration | sqlite_seed, approval_mock | accept | S0.2 | approvals/evidence への記録前は待機し、記録後だけ進行する。 |
| TC-047 | AC-47 | integration | sqlite_seed | accept | S0.1 | repo、SQLite、構造化ログの credential 検出件数をゼロにする。 |
| TC-051 | AC-51 | property | sqlite_seed | accept | S0.2 | 同一ソース二回の制作出力 SHA-256 を一致させる。 |
| TC-054 | AC-54 | integration | sqlite_seed | accept | S0.2 | review_pass を commit hash に束縛し source を復元する。 |
| TC-061 | AC-61 | integration | sqlite_seed, ga4_mock | accept | S0.3 | PV を node/evidence FK 付き measurements に投入する。 |
| TC-062 | AC-62 | integration | sqlite_seed, ga4_mock | accept | S0.3 | 破損行を隔離し正常行だけを投入する。 |
| TC-071 | AC-71 | integration | sqlite_seed | accept | S0.1 | S0 最小スキーマを DDL から再生成する。 |
| TC-072 | AC-72 | integration | sqlite_seed | accept | S0.1 | 旧版を前方昇格し schema_version を記録する。 |

`TC-044-R` と `TC-044-A` は一つの AC の拒否系・成功系を分離したものであり、他の AC は少なくとも一つの TC に 1:1 で対応する。

## 3. ゲート拒否系テスト設計

各ケースは NFR-1 の fail-close を確認する。拒否時は副作用を発生させず、状態又は DB 行を不正に更新しない。外部呼出しを伴うケースは mock または Docker WP の呼出し回数もゼロと確認する。

| TC | 対象 | 種別 | fixture | 更新 | 拒否の観測点 |
|---|---|---|---|---|---|
| TC-GATE-01 | ペア未成立公開 | integration | sqlite_seed, wp_docker | S0.1 | public/draft API を呼ばず公開を拒否する。 |
| TC-GATE-02 | 自己審査 | integration | sqlite_seed | S0.1 | DB CHECK と engine validation の双方で拒否する。 |
| TC-GATE-03 | 必須証跡欠落 | integration | sqlite_seed | S0.1 | done を拒否し evidence・状態を補完しない。 |
| TC-GATE-04 | 有料指標 | unit | sqlite_seed | S0.1 | CAC、ROAS、広告費型を deny-by-default で拒否する。 |
| TC-GATE-05 | 未定義遷移 | unit | sqlite_seed | S0.1 | 状態不変かつ rejected transition を記録する。 |
| TC-GATE-06 | 承認 binding 不一致 | integration | sqlite_seed, approval_mock | S0.2 | subject/operation/at の一つでも不一致なら公開しない。 |
| TC-GATE-07 | 外部照合不能 | integration | sqlite_seed, wp_docker | S0.2 | operation ID/URL を照合できなければ再送せず escalated にする。 |

## 4. 決定性・再開性テスト設計

NFR-2 は同一入力を二回実行してファイルハッシュ、DB 出力、記録済み非決定出力が一致することを property test で確認する。NFR-3 は強制終了を transaction 境界ごとに注入し、再起動後に SQLite 正本のみから復元する。

| TC | 対象規則 | 種別 | fixture | 更新 | 期待結果 |
|---|---|---|---|---|---|
| TC-NFR-02 | NFR-2／AC-51 | property | sqlite_seed | S0.2 | 同一入力二回の出力 SHA-256 と固定済み evidence が一致する。 |
| TC-RST-01 | pending | integration | sqlite_seed | S0.1 | idempotency key を保持し再 claim できる。 |
| TC-RST-02 | in_progress（外部操作前） | integration | sqlite_seed | S0.1 | 入力・workspace・既存証跡を再読込し同 author で再開する。 |
| TC-RST-03 | in_progress（外部操作中/後） | integration | sqlite_seed, wp_docker | S0.2 | operation_log を先に照合し、成功済みを補完して verifying へ進める。 |
| TC-RST-04 | verifying | integration | sqlite_seed | S0.1 | 既存 PASS/FAIL を再利用し retry を二重加算しない。 |
| TC-RST-05 | waiting | integration | sqlite_seed, approval_mock | S0.2 | binding 完全一致なら resume、未充足なら waiting を維持する。 |
| TC-RST-06 | 終端状態 | unit | sqlite_seed | S0.1 | done/failed/escalated/completed/cancelled は明示発行まで遷移不可。 |

TC-RST-03 の照合不能分岐は TC-GATE-07 を回帰実行して確認する。これにより再開規則の「照合不能なら再送せず escalated」を成功経路と拒否経路の両方から検証する。

## 5. スキーマ・マイグレーションテスト設計

| TC | 対象 | 種別 | fixture | 別 | 更新 | 検証内容 |
|---|---|---|---|---|---|---|
| TC-SCH-01 | DDL 適用 | integration | sqlite_seed | accept | S0.1 | 空 DB に DDL/migration を適用し integrity_check を成功させる。 |
| TC-SCH-02 | FK | integration | sqlite_seed | reject | S0.1 | FK 違反 DML を拒否し foreign_key_check を成功させる。 |
| TC-SCH-03 | multi-version workflows | integration | sqlite_seed | accept | S0.1 | 同一 workflow_key の異なる version を共存させ、重複 version を拒否する。 |
| TC-SCH-04 | config append-only | integration | sqlite_seed | reject | S0.1 | UPDATE/DELETE を拒否し supersedes 付き INSERT だけを受理する。 |

evidence は `UNIQUE(task_id, kind, value)` を TC-SCH-05 で拒否確認する。型契約は下表の各 valid/invalid payload を parameterize し、valid は受理、invalid は INSERT 前に拒否する。

| kind | valid TC | invalid TC | 型契約の拒否条件 |
|---|---|---|---|
| plan_record | TC-EVD-01-A | TC-EVD-01-R | plan_id/appeal/target/intent の欠落又は plan 不整合。 |
| commit_hash | TC-EVD-02-A | TC-EVD-02-R | repository/commit_hash/paths 欠落、列不一致、hash 桁数不正。 |
| review_pass | TC-EVD-03-A | TC-EVD-03-R | PASS 以外、hash 欠落、author と同一 reviewer。 |
| published_url | TC-EVD-04-A | TC-EVD-04-R | URL、asset_id、operation ID 欠落又は assets URL 不整合。 |
| measurement | TC-EVD-05-A | TC-EVD-05-R | source/file_hash/期間/row_count 欠落又は evidence 参照不能。 |
| screenshot | TC-EVD-06-A | TC-EVD-06-R | file_path/file_hash/captured_at の欠落。 |
| file_hash | TC-EVD-07-A | TC-EVD-07-R | path/hash 欠落又は algorithm が SHA-256 以外。 |
| approval | TC-EVD-08-A | TC-EVD-08-R | approved 以外、binding 三項目欠落又は approvals 不整合。 |
| operation_log | TC-EVD-09-A | TC-EVD-09-R | 必須キー・operation ID 欠落又は secret/本文/credential 混入。 |
| dashboard | TC-EVD-10-A | TC-EVD-10-R | file_path/file_hash/period_end の欠落。 |

`TC-SCH-05` は S0.1、種別 integration、fixture は `sqlite_seed`、polarity は reject とし、同一 `(task_id, kind, value)` の二回目 INSERT を拒否する。各 TC-EVD は S0.1、種別 unit、fixture は `sqlite_seed` とする。

## 6. 検証しないもの

- `json/ac.json` の deferred 17 件（FR-14、FR-15、FR-16、FR-22、FR-24〜26、FR-31〜32、FR-34、FR-43、FR-45、FR-52〜53、FR-55、FR-63、FR-73）は S1+ の実装スライスと PoC/要件 freeze 後に AC と TC を起票する。S0 の未実装を成功として扱わない。
- 本番 WordPress への書込み、公開、削除、媒体アカウント操作は対象外である。環境契約により自動 E2E の書込み先はローカル Docker WP のみとする。
- 実 GA4 property の書込みは存在しない。計測の自動検証は `ga4_mock` 又は read-only/dry-run に限定する。
- 実 credential、実承認通知先、決済・返金・価格変更、PII を含む配信は対象外である。承認通知は `approval_mock`、credential は検出ゼロの安全な fixture だけを使う。

## 7. 実行・完了判定

- pytest は TC ID を marker 又は nodeid に保持し、S0.1→S0.2→S0.3 の順で前更新の拒否系を回帰実行する。
- JSON 台帳は `python3 -m json.tool docs/requirements/json/verification.json` で検証する。
- Markdown は MD013 を無効化した markdownlint で 0 issue を完了条件とする。
- AC 19 件の全 ID が §2 と `verification.json` の少なくとも一つの `items[].ac` に存在することを機械照合する。
