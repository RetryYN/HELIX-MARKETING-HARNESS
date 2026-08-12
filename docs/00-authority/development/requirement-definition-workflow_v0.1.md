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

## 3. 前向き discovery ledger

`requirement-discovery-events.json` は `coverage_start_commit` 以後の候補・質問・試作・観測・仕様化・承認を
append-only で記録する前段監査証跡である。既存 BR／REQ／FR／NFR／AC／TC 契約 JSON の履歴を推測して backfill せず、
これらの契約正本や製品 runtime を直接更新しない。status は `adapted` とし、空の台帳を adopted と称しない。

- 親コミットの events は完全 prefix として保持する。`schema_version`、authority、lifecycle status、historical policy、
  `coverage_start_commit` は導入後最初の ledger root から固定し、開始点を前方へ付け替えて既存契約変更を逃がせない。
  参照は過去 event、source ID、manifest artifact ID に限り、reference の値も secret/PII 検査対象とする。
- `approval_decided` は event actor、proposal author、approver を分離し、accepted 時点の artifact commit／manifest／
  receipt snapshot を束縛する。artifact ごとの最新 accepted だけを現行 manifest／canonical digest と照合し、履歴 accepted を
  後年の現行 digest で失効扱いにしない。rejected は契約変更を成立させず、保留は `deferred:` 理由付き withdrawal として残す。
- payload の型別厳格性（accepted の `artifact_snapshot` を含む）は schema と gate 実装の両方で定義する。内側の条件分岐は
  最小 schema 実装器の表現域を超えるため、gate が追加属性・型・相互参照を fail-close で検査する。
- 契約正本を変更するときは対象 artifact の `specification_proposed` と `approval_decided`、又は
  `reason: deferred: ...` を持つ `withdrawn` を残す。
- credential、secret、PII、raw 外部本文は payload に置かず、参照 ID と要約だけを記録する。secret scanner は代表的な
  token／email／電話番号／住所表記を fail-close で検出するが、難読化・画像・暗号化済み本文を完全検出する保証ではない。

`tools/gates/requirement_discovery.py` が schema、immutable root＋prefix、BR／REQ／FR／SR／NFR／AC／TC coverage、参照、lifecycle、
承認分離・snapshot、secret、正本への自動 mutation を fail-close で検査する。AST の alias 追跡は静的な Python 経路を
対象とする。`Path("…")`、`ROOT / "…"`、module alias の静的 Python 経路も拒否する。動的 import／eval／反射は
完全列挙できないため実行権限を与えない運用・CI・コードレビューを別の防壁として残す。

## 4. 人間の判断境界

AI は候補、質問、要約、反証、画面案、契約案を作成できる。PO は価値、範囲、リスク、採否、confirmed 化を判断する。
L2 の画面案は URL から承認を確定させず、write 操作は承認 API または既存の config INSERT の契約に限定する。
外部サービスの credential、実運用データ、秘密を候補や evidence に直接貼り付けない。

## 5. ローカル実行

```bash
make setup
make doctor
make requirements
make docs-check
make gates
make test
```

要件 JSON を変更した場合は `make docs` 後に manifest／baseline／レビュー束縛を更新し、全ゲートを再実行する。
