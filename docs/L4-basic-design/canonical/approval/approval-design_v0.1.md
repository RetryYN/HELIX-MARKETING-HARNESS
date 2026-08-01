---
artifact_id: L4-APPROVAL-DESIGN
lifecycle_status: confirmed
slice: S0
---

# 承認設計 v0.1（②増補 — 束縛承認・オートモード）

> status: **confirmed**（2026-08-01 全層再降下 §6 — AI 起草）
> pair: [integration-test-design_v0.1.md](../../integration-tests/integration-test-design_v0.1.md)（②↔④ 文書ペアの増補側 — 承認系 ITC の設計根拠）
> 上位文書: [basic-design_v0.1.md](../basic-design_v0.1.md)（CMP-11 承認通知）／
> [s0-contract_v0.1.md](../../../L3-system-requirements/canonical/s0-contract_v0.1.md)（**approvals DDL・§3 遷移ガード・§4.2 WF-WP-2 承認ステップの正準**
> — 本書は重複記述せず参照で書く）
> 兄弟文書: [external-if-design_v0.1.md](../external-if/external-if-design_v0.1.md)（request_approval IF）／
> [error-taxonomy_v0.1.md](../../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md)（承認系例外の分類台帳）
> 位置づけ: 束縛承認の設計正準 — decision→状態遷移の写像、金銭操作の常時承認、オートモード移行基準、
> 承認の evidence 束縛を確定する。FR-26/46・BR-C4/H1/H2 と矛盾したら上位を優先し本書を改訂する。

---

## 1. 承認モデル（正準参照）

- **束縛承認**: 対象（binding_subject）・操作（binding_operation）・時点（binding_at）の 3 項目を明記した
  承認要求を人へ送り、応答が証跡化されるまで対象タスクを進めない方式（glossary 正本）。
- approvals テーブルの列・CHECK・UNIQUE は s0-contract §2 の DDL が正準。channel は `claude_code_app` のみ
  （DDL CHECK — 変更は要件改訂）。
- decision の語彙は `pending → approved / rejected / expired`。**decision の書換え・削除は不可**
  （approvals は証跡 — 変更は新規要求の別行で行う）。
- 承認が要求される箇所: WF-WP-2 ステップ 3（公開前の束縛承認 — s0-contract §4.2）と金銭操作型 task（§4）。

## 2. 承認フロー（CMP-11 の実装構造）

1. 公開系・金銭系 task が `request_approval(intent)` を発行 → approvals へ decision = pending で INSERT
   （ストア副層 `approvals_store` 経由 — 生 SQL はここだけ）→ Claude Code アプリへ binding 3 項目を明記した通知を送出。
2. pending の間、**親 loop_run を waiting** にし task は進行させない（tasks に waiting 状態はない — s0-contract §3.2。
   基本設計 CMP-11）。先行公開経路は存在しない。
3. 応答受領で decision を更新し、§3 の写像で状態遷移イベントを発火する。
4. transport は差替可能な interface（本番: アプリ通知、テスト: mock fixture で approve/reject/timeout を再現 —
   環境契約 = s0-contract §6）。transport の一時失敗は状態遷移を巻き戻さず通知のみ再送する（FR-16）。

## 3. 承認正準 — decision→分類写像

分類の例外型正規名は [error-taxonomy_v0.1.md](../../../L5-detailed-design/canonical/errors/error-taxonomy_v0.1.md) §3.2・§5。遷移の正しさは s0-contract §3 が正準。

| decision／事由 | 分類（例外正規名） | 状態機械イベント | 遷移先 |
|---|---|---|---|
| approved（binding 3 項目完全一致） | — | resume（loop）→ 後続公開へ | running 継続 |
| rejected | ApprovalRejected | **non_retryable_failure** | task = failed（局所失敗 — 代替 task の発行可。escalate に含めない） |
| expired | ApprovalExpired | なし（承認**再要求**で待機継続） | waiting 継続 |
| expired が `config.approval_retry_limit` 到達 | ApprovalRetryExhausted | **escalate** | task = escalated（無限待機しない） |
| pending | — | wait | 親 loop_run = waiting 維持 |
| binding 3 項目のいずれか不一致の応答 | ApprovalBindingMismatch | なし（応答無効） | waiting 継続（部分一致許容なし） |
| 承認なしの公開・金銭系書込み呼出し | ApprovalRequired | non_retryable_failure | 拒否（外部送信 0 回）→ failed |
| credential 再投入・設計判断待ち | —（承認の外 — escalate ガード） | **escalate** | task = escalated（s0-contract §3.2 — 承認 rejected はここに含まれない） |

- 再要求は同一 binding 3 項目の**新規 approvals 行**として発行し、系列（要求・再要求・応答の全履歴）を証跡に残す。
  同一 (task_id, binding_subject, binding_operation, binding_at) の重複要求は UNIQUE 制約で既存行に照合する。
- binding_at と実公開時点の乖離は不一致として拒否する（FR-46 boundary）。

## 4. 金銭操作の常時承認（BR-C4・FR-26）

- task の操作型を金銭操作型定義リスト（価格変更・返金・決済設定に類する型 — 固定値）と照合し、
  該当時は**オートモード判定より先に**束縛承認を要求する。
- **オートモード状態に関わらず金銭操作型は束縛承認を要する**（バイパス経路なし）。承認判断の機械化はしない。
- 金銭該当か判定不能な操作型は金銭型として扱い承認を要求する（fail-close）。
- approved（binding 完全一致）の確認 → approval evidence 記録 → 外部操作（prepared→sent→confirmed）の順を固定する。
  承認なしの金銭系外部書込みは operation_log 上 0 件が不変条件。
- 有償操作は spend_ledger 記録（FR-73 — approval_id への FK）と対で行う。

## 5. オートモード移行基準（BR-H2）

- **経過措置**: 外部公開は当面すべて束縛承認（Claude Code アプリ通知）を要する。
- **移行**: 安定稼働基準の証跡が揃った媒体は、束縛承認を省略して公開まで自走するオートモードへ移行できる。
  判定は `config.auto_mode_criteria`（充填経路 C）と実績証跡から**機械判定**し、人手の主観判定を挟まない（FR-46）。
- 安定稼働証跡の基準要素（config で宣言 — 値のハードコード禁止）:
  連続成功公開数・拒否/差戻し率・escalated 発生 0 の観測期間・sent 照合不能（unknown）0 件、を媒体単位で満たすこと。
  具体閾値は config 行が正本であり本書に記述しない。
- **除外**: 金銭操作型（§4）はオートモード移行後も常時承認。基準未達へ戻った媒体（escalated・unknown の発生）は
  束縛承認へ自動で復帰する（fail-close 側へ倒す）。
- 移行・復帰は config INSERT（履歴保持 — FR-33）で記録し、切替の系譜を追跡可能にする。

## 6. 承認の evidence 束縛

- approved 時のみ evidence（kind = approval）を記録する。payload の必須キーと検証規則は s0-contract §2.1 が正準
  （`approval_id`・`decision`・binding 3 項目、decision = approved、`approvals.evidence_id` と**相互整合**）。
- 公開実行時は approval evidence ではなく **approvals 行の binding 3 項目の完全一致照合**を通過した
  検証済み値オブジェクト `ApprovalPass` を要求する（external-if-design §3 — PairPass と同じ型強制パターン。
  `ApprovalPass` は承認照合 API だけが生成できる）。
- T-PUB の done 遷移は required_evidence_json の approval kind 充足を証跡完備ゲート（FN-208）が再検証する。
- 再開規則: クラッシュ後は approvals.decision から再開する（pending = 待機継続、approved = evidence 整合を確認して公開へ、
  rejected/expired = §3 の写像を適用 — s0-contract §3.3 waiting 行）。承認は binding 3 項目の完全一致のみ有効で、
  「承認されたはず」という推測を再開根拠にしない。

## 7. 実装への持ち越し

- CMP-11（connectors/approval.py・approvals_store）と CMP-03（ApprovalPass 生成の照合 API）の関数分解は
  ⑤詳細設計の DU 割当で確定し、⑥の承認系 TC（approve/reject/expired/binding 不一致/limit 到達）を test-first で赤→実装する。
- オートモード判定（FN-410 系）は S1 以降。S0 は常時束縛承認＋mock transport の検証まで（s0-contract §7）。
