---
artifact_id: AUDIT-UPDATE-BOUNDARY-2026-08-02
lifecycle_status: confirmed
slice: S0
---

# 監査記録: 未被覆 API・更新境界の是正（2026-08-02）

> 対象: PR #1（`restructure/l0-l6-authority`）／PO 指示「未被覆 API／更新境界最終是正」
> 目的: 実装入力の正本数を一意化し、slice（いつ作るか）と update（S0 内のどの更新で閉じるか）を
> 分離し、S0.1 の未被覆 API を acceptance／internal のどちらかへ確定して、完了宣言を更新単位にする。
> 先行する[構造トレース是正](structural-trace-remediation-2026-08-02.md)の続き。

## 1. 正本数を 9 本へ統一（§1）

`implementation-units.json` を第 9 の契約正本として維持する判断を確定した。DU 契約と L6 文書からは
「どの責務がどの API のどの契約節を実装するか」を導出できないため、生成台帳にはできない。

| 対象 | 是正 |
|---|---|
| AGENTS.md | 「契約 JSON 正本 8 本」→ 9 本（L6 責務／API／契約節／AC／TC／UT の正本を明記） |
| requirements-gates.md | G-CANON-CONFIRMED 行を 9 本（内訳付き）へ |
| README.md ／ CLAUDE.md ／ `tools/gates/common.py` ／ artifact-manifest.json | 既に 9 本。役割記述を本監査記録の定義へ揃えた |

## 2. slice と update の分離（§2）

未被覆 API 台帳の `resolution_slice` を **`resolution_update`** へ改名し、値を手入力で決めない構造にした。
導出は **DU 台帳の `fn_ids` → `updates.json` の `fn_ids`** で、新設 `G-UNCOVERED-API-UPDATE` が
導出結果との一致を要求する（FN が複数更新に跨る／どの更新にも属さない DU も更新境界の不定として落とす）。

導出結果は DU-01〜12 = S0.1、DU-13〜20 = S0.2、DU-21〜23 = S0.3 であり、PO 指示の割当と一致した。

## 3. S0.1 の 7 API の確定（§3）

`受入基準未設定:` を N/A ではなく**未解決 gap** として扱う方針に合わせ、各 API に
`verification_level`（acceptance／unit／integration）を導入した。内部 API は `internal_reason` と
閉じた `internal_reason_code`（startup-wiring／read-only-accessor／internal-delegation）を必須とし、
**postcondition・raises の全契約節が UT の `clause_refs` へ直接接続**していることを要求する
（AC 被覆で代替できない — 独立レビュー R2-01）。未被覆 API 台帳の対象外とし、内部分類と未解決 gap は
併存させない。acceptance から内部分類への格下げは baseline のラチェットが拒否する。

| API | 関数 | 確定 | 根拠 |
|---|---|---|---|
| API-DU02-03 | `run_microloop` | acceptance | 反復・retry 消費・上限 escalate が DB で外部観測できる S0.1 中核（AC-13-7／8／9・TCC-13-7／8／9・IU-STATEMACHINE-05 を新設） |
| API-DU02-04 | `resume` | acceptance | s0-contract §3.3 の再開分岐と再送禁止が外部観測できる（AC-11-5／6・TCC-11-5／6・IU-STATEMACHINE-08 を新設） |
| API-DU04-01 | `load` | acceptance | 壊れた定義での実行開始を止める fail-close が外部観測できる（AC-12-5／6・TCC-12-5／6・IU-EXTERNALOPERATIONS-01 を新設） |
| API-DU01-02 | `register_guard` | unit | 起動時配線のみで業務状態を変えない。観測できるのは配線後の `transition()` の振る舞い |
| API-DU02-09 | `get_tactical_learning_packet` | unit | 読取専用アクセサ。還流の受入基準は TLP 生成側が観測する |
| API-DU09-02 | `for_task` | unit | 読取専用アクセサ。証跡の受入基準は記録側が観測する |
| API-DU09-03 | `exists` | unit | UNIQUE キーの存在照会のみ。冪等性の受入基準は記録側が観測する |

架空の AC は追加していない。新設した 7 AC はいずれも「外部観測点・期待 DB 差分・禁止副作用」を
持つ実測可能な振る舞いで、対応する TCC と UT を同時に新設した。

S0.1 の残りの `受入基準未設定:` 46 節も併せて解消した。内訳は、UT が契約節を直接検証していた 36 節を
新分類 **`単体検証:`**（UT の `clause_refs` に実在する場合だけ名乗れる）へ、AC を新設した 3 API の 9 節を
AC 被覆へ、UT を新設した 7 節（API-DU01-01-RAISE-03／API-DU02-01-RAISE-02／API-DU02-03-RAISE-01・02／
API-DU02-04-POST-02／API-DU02-06-RAISE-01・02／API-DU03-01-RAISE-02）を単体検証へ、
API-DU03-01-POST-03 を `他 API で検証:` へ、API-DU08-01-POST-02 を既存 AC-28-4 の観測対象へ移した。
内部 API の実質化（R2-01）に伴い `register_guard` の POST-02・RAISE-01 にも UT を新設した。

### 分母の変化（いずれも増加・ラチェット順方向）

| 指標 | 前 | 後 |
|---|---|---|
| AC | 211 | 218 |
| TCC | 217 | 224 |
| API 単位 UT | 189 | 199 |
| 実装単位 | 45 | 48 |
| AC 被覆契約節 | 122 | 133 |
| 未被覆 API | 13 | 6（S0.2 = 5・S0.3 = 1） |

## 4. 完了宣言の update 単位化（§4）

`docs/L6-feature-design/S0/update-closure.json` を新設し、更新ごとに `design_closure`（closed／open）と
`current_state_claim` を宣言する。新設 `G-UPDATE-DESIGN-CLOSURE` が**実態から導出した状態**
（当該更新の未被覆 API = 0 ／ `受入基準未設定:` の契約節ゼロ ／ AC を持つ API の実装単位実在）との一致と、
README.md・CLAUDE.md の現在地行との一致（未被覆 API の実数まで）を要求する。
`closed` のときだけ「設計クロージャー完了」を名乗れる。

現在地は 6 行へ更新した。PO 指示の 4 行に対し、S0.2 と S0.3 を**別行**にして各更新の未被覆 API 実数を
機械照合できるようにし、既存の未決事項（HELIX-HARNESS 取込）を落とさずに残した。
S0 全体の設計クロージャーは 3 更新すべてが closed になったときに限る（現時点では未達）。

## 5. レビュー証跡の表現の正確化（§5）

`separation_status` を 3 値へ分けた。

| 値 | 意味 |
|---|---|
| `unverified` | 実行証跡を取得できず、分離を主張する欄を空にする（PO 判断へ送る）。過去 8 件 |
| `self_attested` | 別 principal・別 execution の実行ログがリポジトリ内（git 追跡下）に存在し digest まで一致する。REV-S0-STRUCT-07／08 |
| `ci_attested` | GitHub Actions の run ID・ログ URL・artifact digest へ束縛されている場合のみ |

`self_attested` のログは**レビュー実行者自身が生成したローカル成果物**であり第三者署名ではない。
そのためゲートは `unverified` と `self_attested` に対して「第三者検証」を主張する語を拒否する。

`ci_attested` は、CI が生成してリポジトリへ commit した attestation
（`docs/00-authority/reviews/attestations/<review_id>.json`・git 追跡下）が実在し、その sha256 が
`ci_log_digest` と一致し、repository／run_id／head_sha／target_tree／workflow／artifact_name／
artifact_digest がレビュー宣言と**実行ログの実体**に一致することを要求する。ただしそれだけでは
「ローカルで整合的に自作した一式」と区別できない（独立レビュー R3-02）。したがって署名検証鍵
`trusted-keys.json` が配備されるまで `ci_attested` は**成立しない**（`self_attested` が上限）。
CI 実行＋署名 provenance の構築は PO 判断事項として残る。

## 6. 残課題（PO 判断）

1. S0.2 の未被覆 API 5 本（`list_declared`／`launch`／`screenshot`／`record_failure`／`commit_workspace`）と
   S0.3 の 1 本（`tree`）の受入基準を、それぞれの更新の設計時に新設する。
2. S0.2／S0.3 に残る `受入基準未設定:` 38 節の解消は、当該更新の設計クロージャーの条件である。
3. レビューを CI 実行へ移し `ci_attested` を取得するか、`self_attested` を許容し続けるか。
4. PR #1 のマージ可否（本是正では未マージ・S0.1 実装未着手を維持した）。

## 7. 追加したラチェット

| 保護対象 | 拒否する後退 |
|---|---|
| `api_verification_levels` | acceptance → unit／integration の格下げ（分類替えで検査を緩める経路） |
| `separation_statuses` | ci_attested → self_attested → unverified の強度後退 |
| `fn_boundary_map`（FN → 「DU と更新」の対） | DU 台帳と updates.json の**協調改変**による更新境界の移動 |
