# HELIX-HARNESS への Reverse 取込（2026-08-01）— **未実施**

> status: **not-started（PO 判断待ち）**
> クロージャー §9 の HELIX 取込は **実施していない**。取込先リポジトリへの書き込みは、
> PO の明示的な指示があるまで行わない。

---

## 経緯（撤回記録）

2026-08-01、クロージャー §9 に従い HELIX-HARNESS へ Reverse 取込を試み、
ブランチ `intake/marketing-harness` にコミット `ff835a21`（PLAN-REVERSE-459 と R0-R4 成果物の 2 ファイル）を作成した。
しかし **取込先リポジトリへの書き込みを事前確認なしに行ったこと**が誤りであり、PO の指摘を受けて撤回した。

| 項目 | 撤回後の状態 |
|---|---|
| `intake/marketing-harness` ブランチ | 削除（`ff835a21` は破棄） |
| HELIX-HARNESS の `main` | `0d3a58bd` のまま（一度も変更していない） |
| リモートへの push | 未実施（一度も行っていない） |
| HELIX-HARNESS の作業ツリー | 別作業の cherry-pick（527c815a）解決途中のまま。私の変更なし |
| 作成した worktree | 削除・prune 済み |

**反省点**: 取込先が cherry-pick 競合の解決途中であることを、書き込みを試みる前に確認していなかった。
別リポジトリへの書き込みは、指示に含まれていても着手前に PO へ確認する。

## 取込の内容（実施する場合の案 — 未承認）

| 役割 | 実体 |
|---|---|
| マーケティング思想 | TAKUMI-CMO（read-only 参照） |
| プロダクト北極星 | [charter v0.4](../L0-charter/marketing-harness-charter_v0.4.md) |
| Forward 実装入力 | 契約 JSON 群（BR/FR/SR/NFR/AC/TC/CMP/DU contracts — すべて confirmed・内容束縛 receipt つき） |
| 工程・PR・CI・収束管理 | HELIX-HARNESS（取込後） |

起草済みの取込成果物（PLAN-REVERSE-459 と R0-R4 文書）は、セッションのスクラッチパッドに退避してある。
実施する場合は、以下を PO が判断したうえで行う。

1. 取込先ブランチ（main 直か feature ブランチか）と、PR 経由にするか
2. 取込タイミング（HELIX 側の cherry-pick 競合が解決した後か）
3. forward_routing（案: L5）と promotion_strategy（案: reuse-as-is）の妥当性

## 現時点の進行

**S0.1 以降の進行方法は未確定**。HELIX 取込が完了するまでは、本リポジトリ内での進行か HELIX 経路かを
PO が決める。設計成果物（S0 スコープ）は凍結済みで、独立レビュー
[REV-S0-DESIGN-02](reviews/sol-review-s0-design-02.json)（verdict=Go・target_commit `ef4207d`）を得ている。
