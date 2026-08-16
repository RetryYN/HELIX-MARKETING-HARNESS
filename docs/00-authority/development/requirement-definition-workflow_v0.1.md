---
artifact_id: AUTH-DEVELOPMENT-REQUIREMENT-DEFINITION-WORKFLOW
lifecycle_status: draft
slice: cross
---

# 要件定義ワークフロー v0.1

> status: **draft**。現段階は refinement／要求候補と、旧要求に基づく L2 5点書式の評価用draftを扱う。
> 旧BR／REQ／FR／NFR／AC／TC契約、s0-contract、9契約JSONは再検証sourceであり、現行の要求・設計・実装正本ではない。
> 新要求からのL2画面設計・旧方式の採用は、PO freeze、L2〜L6再設計、別admissionの後に新正本から再選択する。

## 1. 入口から凍結まで

| 段階 | 記録するもの | 完了条件 | 主な正本 |
|---|---|---|---|
| intake | initiative、actor、背景、対象 domain | 対象と非対象が明示される | 旧BR／媒体要求の再検証source |
| candidate | stable ID、課題、価値、workflow、制約、未決事項 | 仮説と反証条件がある | refinement／要求候補 |
| prototype | normal／cancel／failure／timeout の流れと画面・媒体境界 | 実物または観測で不確実性を減らす | 旧L2 5点書式の評価用draft／PoC evidence |
| observed | 観測、反応、拒否理由、矛盾 | evidence と出所が束縛される | audit／媒体要求の再検証source |
| specified | BR→REQ→FR/NFR、状態、データ、権限、例外 | 受入可能な粒度で記述される | 旧9契約JSON／s0-contractの再検証source |
| verified | AC と TC を双方向接続 | normal／reject／boundary-recovery が実行可能 | 旧AC／TC contractsの再検証source |
| frozen | PO 承認、manifest、digest、baseline、レビュー | `confirmed` を名乗れる | artifact-manifest／approvals |

候補から `specified` へ降下する前に、価値・actor・task・workflow・data・permission・state・exception・
integration・security・privacy・accessibility・performance・availability・recovery・observability・cost・legal・
operation・migration・rollback の観点を質問し、未回答は未決事項として残す。承認なしに凍結しない。

`specified`へ進める単位は一括baselineではなく`requirement-refinements.json`の1 subject／1 revisionである。
人間向け確認には同正本から生成する`../views/requirement-candidates_v0.1.md`を使う。このviewは提案専用で、
一覧表示又は一括確認をPO receipt・freeze・authority cutoverの代用にしない。
各recordはsource event集合digest、actor／beneficiary／value／task／workflow／scope in-out／prohibition／human judgement／
side effect／evidence／phase、positive／negative／boundary acceptanceとsystem testを持つ。未解決が1件でもあれば
`specified`へ進めず、specifiedでないrecordの承認依頼と、frozenでないrevisionの実装入力化を拒否する。

## 2. stable ID と trace

- L1 の要求 ID（BR／REQ）は既存正本の ID を維持し、L3 FR／NFR は対応する上流 ID を `trace_up` に持つ。
- AC は検証する契約節を明示し、TC は AC と同じ契約節を観測する。名称の部分一致や画面名だけで接続しない。
- 旧L2の画面 ID は `L2-UI-*` artifact と画面 ID（AP-01 等）を分けて評価する。旧画面は業務状態を独自定義せず、
  s0-contract と L3 契約の語彙を参照する。新要求からの画面ID・状態・UI設計はPO freeze後に再降下し、現段階の評価用draftから継承しない。
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

AI は候補、質問、要約、反証、旧L2評価用の画面案、契約案を作成できる。PO は価値、範囲、リスク、採否、confirmed 化を判断する。
旧L2の画面案は URL から承認を確定させず、旧承認 API／既存 config INSERT は再検証対象であり、新要求のwrite方式として継承しない。
新L2の画面案・write操作は、要求freeze後に選択された正本と別admissionが揃うまで開始しない。
外部サービスの credential、実運用データ、秘密を候補や evidence に直接貼り付けない。

questionへのAI／resolver回答は提案根拠であってPO決定ではない。PO判断が成立するのは、対象semantic digest、source-set
digest、revisionへ束縛したapproval decision receiptだけである。複数subjectを一つのapprove操作で確定しない。

## 5. authority cutover

`requirement-engine-authority.json`が旧9契約JSONを再検証sourceとして列挙する。IRは候補・refinementから決定的に再生成する
非権威projectionであり、手編集や第二正本化を禁止する。compatibility viewとの意味差分と双方向traceが0、全refinementが
verified、PO receipt、manifest、baseline、独立Go reviewが揃ったときだけ対象revisionをfrozenにし、旧sourceから新要求・L2〜L6へ再降下する。
`requirements_baseline_status=revising`又は`implementation_authorized=false`の間、旧confirmed契約は履歴・再検証入力であり、
設計や製品実装の開始根拠にしない。

## 6. ローカル実行

```bash
make setup
make doctor
make requirements
make docs-check
make gates
make test
```

`make requirements` は discovery ledger の表示だけでなく、非権威IRの再生成、compatibility viewとの意味差分、
BR→REQ→FR/SR/NFRの双方向trace、refinementの受入極性、PO承認admission、authority cutoverまでを検査する。
未解消事項が1件でもあれば非0終了し、設計・実装へ進めない。

`requirements_baseline_status=revising`中はmanifest上のL0〜L6成果物を、`confirmed`を含め一律に
`revalidation_required`として扱う。`confirmed`は旧baselineでの成熟度とreceiptを保存する軸であり、
現baselineへの適用又は実装許可ではない。未承認candidateも実装入力ではない。

## Full Vを標準とする段階release

媒体をrelease unit、その媒体内のread／publish／measure／community等を独立incrementとして扱う。
標準工程は、現行HELIXのFull V-model（L1〜L12と正規V-pair）で要求から検証までを閉じることである。
作る対象と成功条件が確定した段階incrementだけを`Production Scrum`又は
`v_design_scrum_impl_hybrid`で実装する。Scrumは要求発見手法ではなく、確定したincrementの実装・検証cadenceである。
実現性又は成功条件が未知の場合に限り、例外的に`Discovery/PoC` S0〜S4へ入る。S3の動作証跡は
判断材料であって受入ではない。POがS4でrelease unitごとにconfirmed／rejected／pivot／stopを決定し、
採用する結果をFull Vの要求・要件・受入・設計正本へ戻す。XServer API/CLI PoCはこの条件付き経路の
先行証跡であり、他媒体の実現性や製品runtime完成を推定する根拠にはしない。

要件 JSON を変更した場合は `make docs` 後に manifest／baseline／レビュー束縛を更新し、全ゲートを再実行する。
