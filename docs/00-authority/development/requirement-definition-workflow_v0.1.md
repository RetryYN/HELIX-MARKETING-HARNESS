---
artifact_id: AUTH-DEVELOPMENT-REQUIREMENT-DEFINITION-WORKFLOW
lifecycle_status: draft
slice: cross
---

# 要件定義ワークフロー v0.1

> status: **draft**。HELIX-HARNESS の discovery／stable ID 方法論を、現行の JSON 契約正本へ適応するための手順。

## 1. 入口から凍結まで

| 段階 | 記録するもの | 完了条件 | 主な正本 |
|---|---|---|---|
| intake | initiative、actor、背景、対象 domain | 対象と非対象が明示される | BR 背骨／br-media |
| candidate | stable ID、課題、価値、workflow、制約、未決事項 | 仮説と反証条件がある | requirement-list |
| prototype | normal／cancel／failure／timeout の流れと画面・媒体境界 | 実物または観測で不確実性を減らす | L2 5 点セット／PoC evidence |
| observed | 観測、反応、拒否理由、矛盾 | evidence と出所が束縛される | audit／br-media |
| specified | BR→REQ→FR/NFR、状態、データ、権限、例外 | 受入可能な粒度で記述される | 9 契約 JSON／s0-contract |
| verified | AC と TC を双方向接続 | normal／reject／boundary-recovery が実行可能 | AC／TC contracts |
| frozen | PO 承認、manifest、digest、baseline、レビュー | `confirmed` を名乗れる | artifact-manifest／approvals |

候補から `specified` へ降下する前に、価値・actor・task・workflow・data・permission・state・exception・
integration・security・privacy・accessibility・performance・availability・recovery・observability・cost・legal・
operation・migration・rollback の観点を質問し、未回答は未決事項として残す。承認なしに凍結しない。

## 2. stable ID と trace

- L1 の要求 ID（BR／REQ）は既存正本の ID を維持し、L3 FR／NFR は対応する上流 ID を `trace_up` に持つ。
- AC は検証する契約節を明示し、TC は AC と同じ契約節を観測する。名称の部分一致や画面名だけで接続しない。
- L2 の画面 ID は `L2-UI-*` artifact と画面 ID（AP-01 等）を分ける。画面は業務状態を独自定義せず、s0-contract と
  L3 契約の語彙を参照する。
- 不確実な媒体・外部接続は、提案中の ADR-011（実装前 PoC）の採否を PO が判断した後、その採択内容に従って
  採用／不採用／条件付き保留と evidence を記録する。ADR-011 が draft の間は、本手順だけで PoC を義務化しない。

## 3. 人間の判断境界

AI は候補、質問、要約、反証、画面案、契約案を作成できる。PO は価値、範囲、リスク、採否、confirmed 化を判断する。
L2 の画面案は URL から承認を確定させず、write 操作は承認 API または既存の config INSERT の契約に限定する。
外部サービスの credential、実運用データ、秘密を候補や evidence に直接貼り付けない。

## 4. ローカル実行

```bash
make setup
make doctor
make requirements
make docs-check
make gates
make test
```

要件 JSON を変更した場合は `make docs` 後に manifest／baseline／レビュー束縛を更新し、全ゲートを再実行する。
