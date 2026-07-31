# HELIX-HARNESS への Reverse 取込 証跡（2026-08-01）

> status: **completed**（クロージャー §9）
> 以降の工程・Gate・PR・収束管理は **HELIX-HARNESS 側**で行う。
> 本リポジトリ内の独自手動進行（PO への直接報告による進行）は本証跡をもって終了する。

---

## 1. 取込の内容

| 役割 | 実体 |
|---|---|
| マーケティング思想 | TAKUMI-CMO（read-only 参照） |
| プロダクト北極星 | [charter v0.4](../L0-charter/marketing-harness-charter_v0.4.md) |
| Forward 実装入力 | 契約 JSON 群（BR/FR/SR/NFR/AC/TC/CMP/DU contracts — すべて confirmed・内容束縛 receipt つき） |
| 工程・PR・CI・収束管理 | HELIX-HARNESS |

## 2. 取込先の成果物（HELIX-HARNESS）

| 項目 | 値 |
|---|---|
| PLAN | `docs/plans/PLAN-REVERSE-459-marketing-harness-intake.md`（kind=reverse／confirmed_reverse_type=design／workflow_phase=R4） |
| R0-R4 成果物 | `docs/design/marketing-harness/reverse-intake-r0-r4.md` |
| ブランチ | `intake/marketing-harness` |
| コミット | `ff835a21f76940c1c9be115782c5ead4f78c7790` |
| forward_routing | `L5`（詳細設計の pair 凍結点から合流。Forward 側で再設計しない） |
| promotion_strategy | `reuse-as-is` |
| HELIX 側 lint | `plan lint` の plan-entry-routing / plan-descent / plan-schedule すべて OK（既存の plan-specific-vpair-binding 286 件は取込前から同数で、本 PLAN は kind=reverse のため対象外） |

> **取込先リポジトリの状態について**: HELIX-HARNESS の作業ツリーは取込作業時、別作業
> （`docs/l3-21-context-review-db-convergence` ブランチの cherry-pick 527c815a）の競合解決途中だった。
> その状態には一切触れず、`main` から切った worktree 上で `intake/marketing-harness` ブランチへ
> コミットしている。**main へのマージと push は未実施**（PO・HELIX 側の工程判断に委ねる）。

## 3. 取込時点の対象（本リポジトリ）

| 項目 | 値 |
|---|---|
| 対象コミット | `ef4207dbf2a233f148a1575d8ed95c3688a00324` |
| 独立レビュー | [REV-S0-DESIGN-02](reviews/sol-review-s0-design-02.json)（verdict=Go・rounds=2・target_commit 束縛） |
| プロダクト側ゲート | 113 / 113 PASS |
| pytest | 13 passed, 194 skipped（skip は test-first スタブ。実行検証ではない） |
| 設計スコープ | S0（ウォーキングスケルトン）— **S1 以降は planned**（AC→TC→CMP/SCM→DU→API→UT の再降下が未完） |

## 4. 以降の進め方

1. S0.1 実装は HELIX の工程・Gate・PR 経路で進める（本リポジトリ内で独自に手動進行しない）。
2. 着手時に `tests/skip-budget.json` の `s0_impl_started` を `true` にする。以後
   `G-S0-TEST-REALITY` が S0.1 対象 API の UT の skip を CI で落とし、実 red→green を強制する。
3. プロダクト側 113 ゲートは内容整合の fail-close 検査として維持し、HELIX の工程 Gate を上位に置く。
   プロダクト側ゲートが赤の状態で HELIX の Gate を通さない（二重ゲート運用）。
4. S1 以降の着手時は、AC→TC→CMP/SCM→DU→API→UT の再降下を先に行う（planned → in_progress）。
