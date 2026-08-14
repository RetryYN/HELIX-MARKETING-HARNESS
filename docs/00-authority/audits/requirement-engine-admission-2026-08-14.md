---
artifact_id: AUTH-AUDIT-REQUIREMENT-ENGINE-ADMISSION-2026-08-14
lifecycle_status: draft
slice: cross
---

# HELIX 要件確定エンジン admission 監査（2026-08-14）

## 判定

**No-Go / requirements revising**。設計・製品実装へ進めない。

HELIX-HARNESS の要件確定仕様を従来は discovery ledger、stable ID、構造ゲートまでしか適応しておらず、
requirement IR、refinement、semantic drift、approval admission、authority cutoverを移植していなかった。
この欠落により、意味齟齬を閉じる前に8 subjectを一括で承認依頼へ進めた。RDE-000065〜000072で依頼を
append-onlyにwithdrawし、承認済み又は実装入力として扱わない。

## 機械検出結果

`tools/gates/requirement_engine.py` の初回projection結果（以下は導入時snapshotで、現行値は再生成する）:

- source authority: 既存契約JSON 9本（BR／FR／SR／NFR／AC／TC／CMP／DU／L6 implementation units）
- projection records: 670（現行projectionはREQ 55件とrefinement追加を含むため、この固定値を完了分母に使わない）
- root digest: `sha256:c973d877091adacb321a4e290430aa2b27dd255e77f42a15668be3546b21b238`
- compatibility view と契約正本のsemantic drift: 128
  - upstream trace差分: 52
  - downstream trace差分: 54
  - slice差分: 22
- BR↔FR/SRの双方向trace違反: 71
- BR→REQ→FR/SR/NFRの隣接trace違反: 初回9。現行gateはstable REQ root欠落も含め38件を検出する
- active approval request: 0（8件ともwithdraw済み）

この数値は要求が誤っている件数そのものではない。一つの要求に複数の差分があり、旧viewが粗い集約を意図した
可能性もあるためである。しかし、その包含・集約規則が正本化されていない以上、同値とは判定しない。

## 既知の意味衝突

最低でも以下は個別refinementとして再質問・再降下が必要である。

1. VPS Web UI＋inboxを初期human interfaceとする決定と、旧Discord初期承認・FR-77 UI対象外の衝突。
2. FR-16安全停止、運用通知、投稿可否承認、Discord媒体投稿、開発PR通知の責務混在。
3. requirements viewとFR契約の22 slice差分、FR↔FN↔AC target updateの導入時期差分。
4. BR／REQ／FR／SR／NFRの片方向又は孤児trace。法規・復旧NFRを含む。
5. 公式API優先とMCP／browser優先、生成AI consumer Web UI自動化、媒体write許可集合の衝突。
6. XServer/VPSの実証済み能力と製品runtime実装済み主張の分離。PoC証拠は要求根拠であってruntime完成証拠ではない。
7. credentialのVPS平文env fileと暗号化store契約の衝突。
8. 媒体固有の要求はFull V-modelで閉じ、対象が概ね決まった段階incrementだけProduction Scrum又は
   V設計＋Scrum実装Hybridでdeliveryし、S4後にScrum ReverseとV-pairを閉じる。Discoveryは実現性又は
   成功条件が未知の場合だけ使う。XServer PoCは先行証跡であり、全媒体の標準工程ではない。

## 完了条件

HELIX側の完成仕様に合わせ、次をすべて満たすまで要求確定を宣言しない。

- strict IR schema、authority policy、source digest、root digest
- actor／beneficiary／value／task／workflow／scope／prohibition／human judgement／side effect／evidence／phaseの意味閉包
- refinement contract単位の質問、回答根拠、positive／negative／boundary acceptance、system test
- semantic driftと双方向traceの0件化、又は型付きprojection／包含規則による明示解消
- PO decision receiptとproposal subject/source-set digestの束縛
- frozen revisionだけを実装入力へ切り替えるauthority cutover
- generated view、mutation tests、manifest、baseline、独立cross-review

候補要求の人間向け表示は
`docs/00-authority/views/requirement-candidates_v0.1.md` として refinement 正本から決定的に生成する。
これは上記完了条件のうち generated view だけを満たしたものであり、各候補のPO receipt、freeze、Full V再降下、
manifest／baseline／独立reviewの完了を意味しない。ビュー自身にも一括承認禁止と実装入力禁止を表示する。

## 現行No-Goの処理分類

現在の失敗を既存設計へ直接patchせず、次の処理へ固定する。`再降下`はPOがrefinementを凍結した後にL0/L1から
新ID又は改訂契約を作ること、`deferred`は理由・risk・依存・再開条件を持たせて初期baselineから外すこと、
`履歴隔離`は旧receiptを保持したまま現行実装入力にしないことを表す。

| 検出群 | 処理 | 要求上の出口 |
|---|---|---|
| REQ/FR compatibility drift、BR↔REQ↔FR/SR/NFR trace | PO判断＋再降下 | `REQ-AUTHORITY-NORMALIZATION`と意味軸refinementを凍結し、単一JSON正本からviewを生成して双方向差分0 |
| DUの旧TC ID、REQ→FN、FR→FN→AC phase | 再降下 | canonical TCC/STC語彙と厳密phaseへ揃え、複合責務は別ID化 |
| 全層semantic dimensions | 再降下 | actor、beneficiary、value、workflow、scope、禁止、HJ、副作用、evidence、phaseを各契約／AC／TCへ型付け。AC targetをscopeの代用にしない |
| WSL cron、Discord初期固定、FR-77 API-only | 履歴隔離＋再降下 | VPS配置、Web UI主入口、UI内inbox要求から新しいL2以降を作る。旧DDL／UI／APIをpatch起点にしない |
| WP content／通常保守／security保守混在 | 再降下 | 3 release unitを別principal、policy、AC/TC、rollback、S4 receiptへ分割 |
| 承認／運用通知／媒体投稿／PR通知混在 | 再降下＋一部deferred | 初期はWeb UI＋UI内inboxだけ。Discord通知・媒体投稿と開発通知は別refinementでdeferred |
| LINE／GENAI／X／Play等のroute衝突、全MR admission欠落 | 媒体別deferred | capability status、execution mode、principal、effect、policy、credential、quota、evidence、AC/TCが凍結した媒体だけ再開 |
| connector priority、provider依存 | PO判断＋再降下 | 許可された公式API／MCPを無人第一経路、consumer UIをattended-only、providerを任意adapterへ正規化 |
| VPS credential二重正本 | PO判断＋security再降下 | at-rest保護、unlock、runtime注入、rotation、scope、backup/recoveryを凍結しADR-007/014を一意化 |
| HJ descent欠落、auto-mode機械代替 | 再降下 | decision対象、revision、principal、結果、期限、receiptをAC/TCまで束縛し機械判定とPO決定を分離 |
| NFR stable root欠落 | 再降下又はdeferred | stable BR→REQ→NFR、測定、閾値、failure/recovery/evidenceを持つものだけ受入対象 |
| SR17〜19／draft strategy tests | deferred又は再降下 | business valueとphaseを再確認し、SR→AC→STCをPO receiptへ束縛するまで初期scope外 |
| L2 prototypeの未定義操作 | 履歴隔離 | 書式bridgeのみ保持し、UI/inbox/profile/approval要求freeze後に新規作成 |
| open refinement | PO判断待ち | pending questionを閉じ、1 revisionずつPO receipt付きfrozenへする。一括承認禁止 |
| review／baseline binding | 最終手続 | 意味No-Go解消後にmanifest、baseline、生成view、独立Go reviewを同一targetへ束縛 |

この表は失敗を免除するwaiverではない。`deferred`へ分類した対象も、機械台帳へ理由と再開条件が降りるまで失敗を
維持する。review／baselineだけを更新してsemantic gateを緑にすること、旧confirmed文書を現要求へ昇格すること、
未決値を設計で補完することを禁止する。

## 境界

HELIX-HARNESS本体はread-onlyであり変更しない。Bun／Node製品runtimeも移植しない。ただしPython-native化を理由に
要件確定の判定意味を削らない。生成IRは既存9正本、非権威REQ trace ledger、旧BR-M／MR／FN台帳、個別refinementから決定的に再生成する
非権威projectionで、第二正本にしない。9契約JSONはrecord sourceを`canonical_contract_json`、REQ trace ledgerは
`read_only_req_revalidation_ledger`、BR-M／MR／FNは`read_only_legacy_requirement_ledger`、refinementは
`canonical_refinement_registry`として区別する。IR全体のsourceも
`mixed_revalidation_sources`であり、REQを9契約正本の一つとして誤表示しない。旧契約／REQ recordは
`revalidation_required`、refinementは`proposal_only`であり、
PO receipt付きfrozen revisionへのcutover前にconsumerが`current`へ読み替えてはならない。
