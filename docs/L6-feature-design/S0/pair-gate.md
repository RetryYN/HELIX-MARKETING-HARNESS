---
artifact_id: L6-S0-PAIR-GATE
lifecycle_status: confirmed
slice: S0
traces: [FR-21]
forward_refs: []
dus: [DU-05, DU-06]
---

# 機能設計: 企画↔品質ペア判定（PairPass の成立・失効・バイパス不在）

> status: **confirmed**（2026-08-01 構造分類是正で新設 — DU-05／AC-21-1〜5 の機能設計が不在だったため）
> 正準参照: 要求 = FR-21（企画↔品質ペア判定）。DDL（`pair_plan_quality`）と evidence 型
> （`review_pass`）の正準は [s0-contract_v0.1.md §2・§2.1](../../L3-system-requirements/canonical/s0-contract_v0.1.md)。
> API 署名の正本は [detailed-design_v0.1.md DU-05](../../L5-detailed-design/canonical/detailed-design_v0.1.md)
> （`docs/L5-detailed-design/canonical/apis/du-contracts.json` の DU-05）。
> 兄弟文書: [approval.md](approval.md)（承認の束縛）／[external-operations.md](external-operations.md)（公開の外部操作）／
> [evidence.md](evidence.md)（review_pass 証跡の記録側）
> 位置づけ: 「企画と品質レビューが対になって初めて公開できる」規律を、型・関数分解・
> 失効経路・バイパス不在の検査点まで降下させる。DDL・evidence 必須キーは再掲しない。

---

## §0 位置づけ・動機

公開の可否を「レビューしたつもり」で越えられないようにする。ペア成立の証明は
**型（PairPass）でしか運べない**ようにし、config・引数・呼出順のいずれでも迂回できない構造にする。
DU-05（`gates/pair.py`）が状態所有者（CMP-03）であり、公開系（DU-06）は PairPass を要求するだけで
自前の判定を持たない。

## §1 実装単位と責務

| 実装単位 | 責務 | 失敗方針 |
|---|---|---|
| `PairPass`（frozen dataclass＋sentinel） | 検証済みペア通過の唯一の運搬型。`__init__` はモジュール内部 sentinel token を要求 | token 不一致は `FatalError`（偽造は即停止・拒否ではない） |
| `establish(conn, plan_id, review_task_id, review_evidence_id, clock)` | commit hash 一致時のみ `pair_plan_quality(status=passed)` を INSERT し PairPass を返す | hash 不一致 = `CommitHashMismatch`／証跡不在・result 非 PASS・重複 = `GateRejected`（DB 不変） |
| `revoke_if_changed(conn, plan_id, current_commit_hash)` | 企画又は commit の変更検知で該当 pair を `revoked` へ UPDATE し True | 変更なしは False・DB 不変（例外を投げない） |
| `require_pair(conn, plan_id)` | `passed` 行が存在する場合のみ PairPass を返す read-only 検査 | 不在・`revoked` のみ = `PairNotEstablished`（公開系はコネクタに到達しない） |

## §2 検査順序と不変条件

1. `establish` の検査順は **証跡 → hash → 一意性**: (a) `review_evidence_id` が
   `kind=review_pass`・`result=PASS` であること、(b) その `commit_hash` が制作側 commit hash 証跡と
   一致すること、(c) `UNIQUE(plan_id, review_evidence_id)` に反しないこと。いずれも先に評価が終わる
   まで INSERT しない（1 成立 = 1 transaction）。
2. reviewer ≠ author（別 principal）は evidence 側（DU-09）で検証済みであることを前提とし、
   本モジュールで二重実装しない（証跡が正本）。
3. **バイパス経路を持たない**（AC-21-4）: `establish`／`require_pair` は config を一切読まない。
   「pair 判定を無効化する設定値」は存在せず、追加もできない（config 参照が入った時点で
   FR-21 の不変条件違反）。
4. **復旧経路は再審査のみ**（AC-21-3）: `revoked` から `passed` へ戻す UPDATE を持たない。
   新しい `review_pass` 証跡で新しい pair 行を `establish` することだけが復旧である。

## §3 公開系との接続

- DU-06（`gates/publish.py`）は `require_pair` の戻り値 PairPass を引数に取る。PairPass を
  受け取れないコード経路から外部書込みへ進めない（型で強制）。
- 拒否は task 文脈で `non_retryable_failure`（failed）へ写像する。外部 API は 1 度も呼ばれない
  （拒否がコネクタ呼出しに先行する — [external-operations.md](external-operations.md) §1 の順序契約）。
- 拒否の証跡は `operation_log` と `state_transitions`（guard_result = rejected）に残す。

## §4 テスト実装方針

⑥の割当（`du-contracts.json` の DU-05 `apis[].ut`）が正本。実装は test-first で赤→緑にする。

| # | テスト | 方針 |
|---|---|---|
| 1 | 成立 | hash 一致 fixture で `passed` 行 1 件と PairPass 返却を assert |
| 2 | hash 不一致 | `CommitHashMismatch`＋`SELECT COUNT` 前後不変 |
| 3 | 重複成立 | 同一 (plan_id, review_evidence_id) の再要求が `GateRejected`（冪等拒否） |
| 4 | 失効 | 再 commit で `revoke_if_changed` が True・status=revoked |
| 5 | 未成立・失効での要求 | `PairNotEstablished`（AC-21-2／AC-21-3） |
| 6 | 偽造 | sentinel なしの `PairPass(...)` 構築が `FatalError`（AC-21-5） |

## §5 trace 表

| 実装単位 | DU | AC | TCC | 備考 |
|---|---|---|---|---|
| `establish`（成立・hash 一致・重複拒否） | DU-05 | AC-21-1 | TCC-21-1 | 成立時のみ公開前検証を通す |
| 未成立での公開拒否 | DU-05・DU-06 | AC-21-2 | TCC-21-2 | WP API 未呼出・T-PUB failed |
| 失効と再審査による復旧 | DU-05 | AC-21-3 | TCC-21-3 | revoked→passed の直接遷移なし |
| バイパス不在（config 無効） | DU-05 | AC-21-4 | TCC-21-4 | config を読まない実装で構造的に保証 |
| 不変条件の負方向 | DU-05 | AC-21-5 | TCC-21-5 | PairPass 偽造の FatalError |
