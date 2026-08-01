---
artifact_id: AUDIT-STRUCTURAL-TRACE-2026-08-02
lifecycle_status: confirmed
slice: S0
---

# 監査記録: 構造的意味トレース是正（2026-08-02）

> 対象: PR #1（`restructure/l0-l6-authority`）／PO 指示「構造的意味トレース最終是正」
> 目的: 語彙一致で成立していた L6 責務→API→AC→TC→UT の接続を、**安定 ID による構造参照**へ置換し、
> 接続できていない箇所を隠さず台帳化する。

## 1. 何を変えたか

| 対象 | 変更 |
|---|---|
| API 契約 | 全 58 API に `api_id`、全 356 契約節に `clause_id`（`API-DU01-01-POST-01` 形式）を付与 |
| AC 契約 | `verifies_clause_refs`（検証する契約節）と、契約節を検証しない AC の `clause_na_reason` を追加 |
| UT 割当 | `apis[].ut` を nodeid の配列から `{nodeid, clause_refs}` の構造へ変更（193 件） |
| 実装単位 | `api_refs`（配列）を `api_ref`（1 件）へ、`clause_refs` を追加。専用 schema を新設し追加プロパティを禁止 |
| ゲート | G-L6-IMPLEMENTATION-TRACE から**語彙一致検査を全廃**し、構造参照の突合のみに置換 |

## 2. 接続の実数

| 指標 | 値 |
|---|---|
| API 契約節 | 356（うち AC 被覆 122 ／ 理由付き N/A 234） |
| AC | 211（うち API 契約節を検証 86 ／ `clause_na_reason` 125） |
| UT→契約節の接続 | 193 件すべて |
| 実装単位 | 45（是正前 65 — 20 件を除外。内訳は §3） |
| API 契約節を 1 つも AC が検証していない API | 13（§4） |

## 3. 実装単位から外した 20 件

「同じ契約節を AC と UT の双方が検証している」という構造条件を満たせない責務は、実装単位として維持しない
（語彙が似ているという理由での接続を作らない）。文書側にも同じ表を残している。

| unit_id | 文書 | API | 除外理由 |
|---|---|---|---|
| IU-EVIDENCE-02 | evidence.md | exists | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EVIDENCE-03 | evidence.md | for_task | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EVIDENCE-05 | evidence.md | commit_workspace | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EXTERNALOPERATIONS-01 | external-operations.md | load | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EXTERNALOPERATIONS-03 | external-operations.md | list_declared | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EXTERNALOPERATIONS-09 | external-operations.md | launch | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EXTERNALOPERATIONS-11 | external-operations.md | screenshot | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-EXTERNALOPERATIONS-13 | external-operations.md | record_failure | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-KPIHANDOFF-05 | kpi-handoff.md | tree | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-STATEMACHINE-01 | state-machine.md | register_guard | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-STATEMACHINE-05 | state-machine.md | run_microloop | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-STRATEGICBRIEF-01 | strategic-brief.md | generate_tactical_learning_packet | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-STRATEGICBRIEF-03 | strategic-brief.md | issue_task | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-STRATEGICBRIEF-04 | strategic-brief.md | resume | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-STRATEGICBRIEF-06 | strategic-brief.md | validate_strategic_brief | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-STRATEGICBRIEF-08 | strategic-brief.md | verify | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-TLP-02 | tlp.md | get_tactical_learning_packet | この API の契約節を AC と UT の双方で検証している節が無い（全節が理由付き N/A） |
| IU-TLP-03 | tlp.md | issue_task | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-TLP-04 | tlp.md | supersede_strategic_brief | 同 API の他責務が全契約節を正当に所有（重複責務） |
| IU-TLP-05 | tlp.md | validate_strategic_brief | 同 API の他責務が全契約節を正当に所有（重複責務） |

「重複責務」は、同じ API の同じ契約節を複数文書の責務が主張していたもので、契約節を正当に所有する 1 本へ統合した。

## 4. AC が 1 節も検証していない API（13 本）

これらは**設計の穴**であり、隠さず記録する。全契約節に理由付き `na_reason` が付いており、
G-L6-IMPLEMENTATION-TRACE は「AC 被覆か理由付き N/A のいずれか」を要求してこの状態を可視化する。
受入基準の新設は S0.1 実装着手時／S1 の課題として PO 判断へ送る（本是正では AC を捏造しない）。

| DU | api_id | 関数 |
|---|---|---|
| DU-01 | API-DU01-02 | `register_guard` |
| DU-02 | API-DU02-03 | `run_microloop` |
| DU-02 | API-DU02-04 | `resume` |
| DU-02 | API-DU02-09 | `get_tactical_learning_packet` |
| DU-04 | API-DU04-01 | `load` |
| DU-09 | API-DU09-02 | `for_task` |
| DU-09 | API-DU09-03 | `exists` |
| DU-13 | API-DU13-02 | `list_declared` |
| DU-15 | API-DU15-01 | `launch` |
| DU-15 | API-DU15-02 | `screenshot` |
| DU-16 | API-DU16-03 | `record_failure` |
| DU-20 | API-DU20-01 | `commit_workspace` |
| DU-21 | API-DU21-02 | `tree` |

## 5. レビュー主体の分離

`review.schema.json` に `author_principal`／`author_execution_id`／`reviewer_execution_id`／
`review_run_id`／`reviewer_provider`／`review_log_path`／`review_log_digest`／`separation_status` を追加し、
G-REVIEW-SEPARATION を新設した。**過去 8 件のレビューは実行証跡を後から取得できない**ため
`separation_status: unverified` とし、「独立レビュー済み」を宣言しない（PO 判断へ送る）。

## 6. N/A を免罪符にしない仕掛け（独立レビュー R1-02 対応）

「`na_reason` を書けば API ごと責務台帳から消せる」経路を塞ぐため、次の 3 段で拘束する。

1. `na_reason` は閉じた分類語彙で始まる（`呼出側義務:`／`配線時保証:`／`他 API で検証:`／`受入基準未設定:`）
2. AC が 1 節も検証していない API は [uncovered-apis.json](../../L6-feature-design/S0/uncovered-apis.json)
   へ明示登録し、**登録集合と実態が厳密一致**していなければならない（黙って増やせない）
3. baseline のラチェットが `clause_ac_covered`（AC 被覆済み契約節）・`implementation_units`（責務数）の
   縮小と `uncovered_apis` の増加を拒否する

## 7. 実行証跡の限界（PO 判断事項）

`review_log_path` のログは**レビュー実行者自身が生成するローカル成果物**である。G-REVIEW-SEPARATION が
保証するのは構造的整合（別実行 ID・別 principal・git 追跡下のログとの digest 一致・ログの `session_meta`／`turn_context`
レコードがセッション ID とモデルを型付きで申告）までであり、第三者による署名や
改竄検知は本リポジトリの範囲外である。より強い保証が必要なら、CI 側でレビューを実行して
GitHub Actions の run ID・ログ URL を証跡にする方式へ移す必要がある（PO 判断）。

## 8. 残課題（PO 判断）

1. §4 の 13 API に対する受入基準の新設（AC／TC の追加は分母の増加であり ratchet に反しない）
2. §3 で外した 20 責務のうち、AC 新設によって復活させるものの選定
3. 過去レビュー 8 件の `unverified` 扱いを許容するか、再レビューで verified を取り直すか
4. §7 の実行証跡を CI 実行（Actions run ID）へ移すかどうか
