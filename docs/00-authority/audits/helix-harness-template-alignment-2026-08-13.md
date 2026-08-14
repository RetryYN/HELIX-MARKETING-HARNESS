---
artifact_id: AUTH-AUDIT-HELIX-HARNESS-TEMPLATE-ALIGNMENT-2026-08-13
lifecycle_status: draft
slice: cross
---

# HELIX-HARNESS 設計テンプレート適応監査（2026-08-13）

> status: **draft**。テンプレートの固定コミットを read-only 参照した構造監査であり、テンプレート側への変更や
> 本リポジトリの製品実装完了を意味しない。

## 監査対象

- repository: `RetryYN/HELIX-HARNESS`
- URL: <https://github.com/RetryYN/HELIX-HARNESS/>
- source commit: `57853db413e282b050ac5f37bab7809321c67842`
- 比較対象: 本リポジトリ `main` の現行正本、Python ゲート、L2 screen-list、開発スクリプト
- 制約: 外部リポジトリは clone して読むだけ。本リポジトリから外部へ write しない

## 判定

| テンプレートの設計要素 | 現行への対応 | 判定 | 根拠 |
|---|---|---|---|
| 現行Full V-modelとdelivery route | 旧L0〜L6は再検証資料に限定。L1〜L12 exactly once・6 V-pair、Production Scrum、V設計＋Scrum実装Hybrid、Discovery別軸、Scrum Reverse SR0〜SR4を新要求へ移植する | ブリッジ | `helix-harness-alignment.json` の `v-model`。要求freeze・route合意・pair closure前は適応完了を名乗らない |
| requirement IR の stable ID 連鎖 | 既存の 9 契約 JSON、manifest、AC↔TC、L6 implementation-units を唯一の正本として接続 | ブリッジ | `requirement-ir`。並列 `requirements-ir/` は導入しない |
| discovery event と candidate lifecycle | 導入以後の候補→質問→試作→観測→仕様化→承認を append-only ledger に記録し、既存契約へ直接 mutation しない | 適応 | `requirement-discovery-events.json`、schema、`requirement_discovery.py` |
| L2 5 点 screen 方法論 | 5点書式と補助business-flowを評価済み。内容は旧要求ベースなので新要求承認後に再作成 | ブリッジ | `docs/L2-prototypes/` |
| doctor／build／typecheck／lint／test 導線 | Python の `make setup/doctor/docs/gates/test/check` と既存全ゲートへ写像 | 適応 | `Makefile`, `scripts/dev.py` |
| toolchain pin／CI hygiene | Python 3.14、uv frozen sync、concurrency cancel、job timeout、checkout credential 非保持を対応表ゲートで固定 | 適応 | `ci-hygiene`、`G-TEMPLATE-ALIGNMENT` |
| typed NFR registry | 既存 NFR 契約の stable ID・検証方法・閾値・AC／TC traceへ写像し、並列 registry は作らない | ブリッジ | `nfr-quality-registry` |
| state DB schema／DDL authority | s0-contract と `ddl.sql` を正本に、migration checksum・空 DB 再現・等価性の設計とgateへ写像。製品migration runtimeは未実装 | ブリッジ | `schema-ddl-authority`、`G-DDL-SYNC` |
| atomic PR／変更 scope | branch 名の自己申告ではなく、plan／Workset／API／UT／module の導出一致で着手範囲を制約 | 適応済み | `atomic-change-scope`、`G-WORKSET-SCOPE` |
| cross-review | author と別 principal／execution、target commit／tree、artifact digest、後続reviewを現行レビュー成果物へ写像 | ブリッジ | `developer-cross-review`、`G-REVIEW-BINDING` |
| PR 対応依頼 | GitHub current HEAD／check／findingに束縛する開発通知。製品Discord承認へは接続しない | 保留 | `developer-pr-notification` |
| harness memory | commit済み基準点の開発継続event／projection。製品DB・要求正本・discovery・approval evidenceとは別正本 | 保留 | `developer-harness-memory` |
| Bun／Node／template runtime | 本リポジトリの Python-native 制約と衝突するため、UI ランタイムは移植しない | 保留 | ADR-012、開発環境契約 |

## 不整合と是正

1. 固定採用点の旧L0〜L14表現と最新HELIXのL1〜L12 canonical V-modelを混同しない。下流ディレクトリを
   空のまま追加するのではなく、L1↔L12、L2↔L11、L3↔L10、L4↔L9、L5↔L8、L6↔L7のpair義務、
   route選択、右腕evidenceを本製品要求へ降ろしてから物理配置を決める。
2. テンプレートの `requirements-ir/` を追加すると契約 JSON との二重正本になる。stable ID の考え方だけを既存の
   契約・manifest・traceability へ写像した。
3. テンプレートの Bun コマンドをそのまま実行すると Python 単一パッケージ規律に反する。`scripts/dev.py` と
   `Makefile` は依存を増やさず、`uv.lock` と既存ゲートを呼び出す。
4. 現行 L2 は screen-list だけだったため、残る 4 文書を追加し、入口・状態・失敗・戻る操作・read/write 境界を
   画面単位で記録できるようにした。
5. discovery ledger は導入前の要求履歴を推測生成せず、`coverage_start_commit` 以後の監査証跡だけを保持する。契約 JSON
   の変更には proposal と decision、又は `deferred:` 理由付き withdrawal を機械的に要求する。

## Latest upstream verification

- checked_at: `2026-08-14`
- upstream_checked_commit: `b19647a742a7511603940772b1afcf265abf6e3f`（`main`、read-only `git ls-remote`実測）
- adoption baseline: `57853db413e282b050ac5f37bab7809321c67842`（変更しない）
- latest delta range: `fe6ffe6cfa0e11bd054dbc67e4278f0d3bd1234d..b19647a742a7511603940772b1afcf265abf6e3f`
- latest delta: GitHub Issue metadata labelの監査と更新lifecycleを追加した15ファイル（+275/-36）。これは
  upstreamのGitHub運用／TypeScript CLI境界であり、本repoが進めている製品要求、VPS UI／inbox、Full Vの
  delivery route、Python-native runtimeの意味を変更しない。Issue metadata enforcementは現適応範囲外とし、
  将来GitHub開発adapterを採用する場合に別途再監査する。
- baseline以後の累積差分: typed NFR registry、state DB schema／DDL authority、toolchain pin、provider大容量出力、
  cross-review admission、inbox lifecycle、Node/Bun保守を含む。
- observed difference: typed NFR registry、state DB schema／DDL authority、toolchain pin、provider 大容量出力、
  Kimi／Claude review admission、one-shot inbox lifecycle、および Node/Bun runtime の保守が追加された。
- adoption disposition: **partially-adapted**（adoption baseline unchanged）
- adapted now: toolchain pin と CI hygiene を Python-native workflow・`G-TEMPLATE-ALIGNMENT`へ追加。typed NFR と
  schema／DDL authority は既存の NFR 契約、s0-contract、migration／DDL gate へ対応づけた。
- deferred development adaptation: cross-review／GitHub PR対応依頼／harness memory は製品runtimeへ入れず、
  開発環境としてPython-nativeに再設計する。現行review bindingはcross-reviewの基礎として利用できるが、PR通知と
  memory event／projectionは未実装である。
- non-applicable: Node provider spawn buffer と Bun／Node package 更新は Python-native 制約により移植しない。
- rationale: 固定採用点は再現可能な方法論 baseline として維持し、最新版確認点と差分処置を対応表の別 field へ
  機械記録する。上流 TypeScript 実装を複製せず、現行 Python 正本へ意味だけを適応する。

## 意味境界の再監査

### 現在の要求基準

VPS常駐化後の人間向け入口は、Discord先行の旧設計を前提にせず再要求化した。ADR-007は
VPS `helix-worker`を製品runtimeの配置方針としてaccepted（runtime／service／Web UIは未実装・未配備）、ADR-013はVPS上の製品Web UI＋UI内inboxを
初期主入口としてacceptedである。ADR-010もこの投入順序へ追補済みである。ただし認証・公開・追加通知adapterの
要求は未確定なので、`update-closure.json` は要求基準を`revising`、旧S0.1〜S0.3のconfirmed設計を
`revalidation_required`、新要求の実装許可をfalseとする。旧正本のconfirmed履歴は取り消さず、
要求決定後にL2以降を再降下した新baselineとの差分を再検証する。

旧tech stack／FN／FR／L2以降に残るWSL cron・Discord初期tupleは、新要求の設計入力にせず再降下で置換する。

| 利用者の問い | 正本 | 許可される外部作用 | 禁止する混同 |
|---|---|---|---|
| 「このコンテンツを投稿してよいか」 | ADR-013、新要求候補、将来のVPS approval state | 認証済みWeb UIで対象revisionを再表示して明示決定する要求候補。製品runtime/UIは未実装で、旧個人Discord tupleとDocker WP writeはいずれも新baselineでは無効・再検証待ち | 通知受信だけの決定、PRレビュー依頼、一般チャット投稿、Discord自体へのコンテンツ公開 |
| 「このPRの指摘へ対応してほしい」 | GitHub PR current HEAD／review finding（将来の開発アダプター） | 未実装。導入時もGitHubの明示許可operationだけ | ApprovalTransport、approvals、製品の公開許可、会社Slack／個人Discordへの暗黙送信 |
| 「次セッションへ何を引き継ぐか」 | 将来のrepository-local memory event／projection | repository内の秘密を含まない開発証跡だけ | 製品DB、要求正本、discovery ledger、approval evidenceの代替・直接mutation |
| 「投稿成功・ゲート拒否・KPI異常を知らせる」 | 新要求候補のVPS UI内inbox。旧FR-76は再検証待ち | 初期はUI内inboxだけ。外部運用通知adapterはdeferred | approve／rejectの要求、公開許可の成立 |
| 「Discordコミュニティへ告知を投稿する」 | 将来の媒体別refinement。旧BR-M-DC／MR-DCは再検証待ち | 初期はdisabled/deferred。別principal・policy・account・AC/TCをPOが凍結した場合だけ再開候補 | 個人承認server／channel、開発PR通知との宛先共有 |

この分離により、初期製品承認と運用通知はVPS Web UI／UI内inbox要求へ置き、Discord承認補助、Discord媒体投稿、
GitHub開発通知はそれぞれ未採用又はdeferredの別capabilityとする。memoryも未実装の開発継続候補であり、同じ
`notification`／`approval`／`memory`という語だけで相互接続しない。

### 未解消 finding: FR-16 の通知経路

`FR-16` はS0のエスカレーション通知を `FR-46`／`ApprovalTransport`へ送ると記述し、`FR-43` も
攻略地図修復失敗通知を同じ経路へ送る。一方、`FR-46` は
投稿可否の束縛承認専用であり、`FR-76` は `approval_notification` と `operational_notification` の混在を禁止し、
S1 expand migration後だけ運用通知を許可する。このため現行confirmed契約には次の意味矛盾が残る。

- 異常通知は質問へのapprove／rejectではないのに、投稿可否承認transportへ流入する。
- S0 DDLが拒否する `operational_notification` を、S0のFR-16が送達済みとして要求する。
- BR-H3の通知送達証跡と、S1まで運用通知を無効とする実装境界が同時には成立しない。
- draftの `functional/requirements.json` はFR-16を`S1+`、confirmedの `fr-contracts.json` は同じFR-16を`S0`とし、
  slice表現も一致していない。
- confirmedのtech-stackは「承認・通知」を一行のApprovalTransportとしてまとめ、両policyの分離を表現できていない。

是正案は、S0のFR-16を「安全停止＋永続的な未通知escalation evidence」までに閉じ、S1のFR-76を
BR-H3／FR-43の通知送達担当として明示接続すること。S0で即時通知が必須なら、代わりに
`operational_notification`をS0へ前倒ししてDDL／FR／AC／TC／CMP／DUを再降下する。どちらの場合もFR-46へは
接続しない。confirmed契約の変更はdiscovery event、PO decision、承認digest、生成view、manifest、baseline、
独立reviewを同一変更で更新するまで行わない。

### 未解消 finding: オートモード移行の判断主体

上位の `BR-H2` はactorを「PO（承認者・移行判断者）」、human judgementを「オートモード移行の最終承認」とする。
一方、`FR-46` は基準充足後の機械判定で承認を省略し、confirmedのapproval designは「人手の主観判定を挟まない」とする。
基準を機械評価することと、移行を誰が確定するかが混同されている。

上位BRを優先した是正は、`config.auto_mode_criteria`と実績証跡による基準充足判定を機械化し、その結果に束縛した
POの最終承認で媒体単位のモードを切り替えること。基準未達への自動復帰は安全側なので人の承認を待たない。
FR／AC／TC／approval design／状態・config履歴／UIをこの二段階へ再降下し、基準判定だけで自動移行する経路を拒否する。
もしPOの最終承認を廃止するなら、先にBR-H2自体の改訂承認が必要である。

### 未解消 finding: 同一FR IDのslice不一致

activeなdraft `functional/requirements.json` とconfirmed `fr-contracts.json`をIDで突合すると22件のslice表現が一致しない。
`S1+`対`S1`の広義／厳密表現だけでなく、FR-16=`S1+`対`S0`、FR-42／44=`S0`対`S1`、
FR-55=`S1+`対`S0`のように実装順序を変える差がある。confirmedの`requirements_v0.1.md`にも旧表現が残る。
さらにconfirmedの`function-list_v0.1.md`と突合しても、FR-16=`S0`に対するFN-110=`S1`、
FR-42=`S1`に対するFN-402／404=`S0`とFN-403=`S3`、FR-44=`S1`に対するFN-406=`S0`と
FN-407=`S3`、FR-55=`S0`に対するFN-512=`S1`の直接衝突がある。FR-42／44は一つのFRに
S0の基盤／RESTとS3のステルス／WP-CLIを含む複合機能で、単一slice値では意味を保存できない。

実装入力の正本はconfirmed契約JSONだが、この状態でFR契約の単一sliceを一律にFNへ強制すると
S0機能を遅延させる。FR-42／44のような複合FRは、slice別FRへ分割するか、FR契約に
「導入slice」と「後続capability slice」の型付き対応を持たせる。FR-16／55も同様に、S0の停止／登録責務と
S1の通知／資産追跡責務を分離する。requirements ledger、FR、FN、AC／TC、L6／DUを同じ分解へ
再降下し、単なID一致でなく責務単位のslice対応をgateで検査する。confirmed成果物の変更は
POの仕様選択と承認後に行う。

### 未解消 finding: Discord媒体投稿と運用通知の実行境界

Discordには投稿可否承認とは別に、(a) BR-M-DC／MR-DCのコミュニティ媒体投稿、(b) FR-76の運用通知がある。
しかしMR-DCは下流FNへ未接続で、現行external IFのwrite閉集合にはDiscord媒体投稿用tupleがない。
FR-76も`ApprovalTransport同型`とのみ記述し、承認用service／operation／channelを再利用できないexact tuple、
一方向payload、approve／reject禁止を固定していない。FR-76のtrace_downもFN／CMP／APIが空である。

両機能を将来sliceとして維持する場合は、未実装・未接続であることを明記する。実装へ進める場合は、承認用個人server、
運用通知channel、コミュニティ投稿accountを別config namespaceとし、別policy category／service／operation／endpoint、
profile/account binding、AC／TC、adapterを定義する。いずれも開発PR通知とは接続しない。

### 未解消 finding: 生成AIのWeb UI操作とCodex依存

confirmedのBR-M-GENAIは生成AI Web UI自動操作を明文の規約違反とし、Codex CLI `image_gen`を
第一経路とする。一方、confirmedのFN-510は「ブラウザ経由生成」、confirmedのtech stackは
Codex CLIのフォールバックを「ブラウザ生成AI」とするため、上位BRが禁じる経路へ無人で退避できる。
MR-GENAIも保有アカウントWeb UI操作と5〜15秒のランダム間隔を要求し、actor／attended modeを
限定していないため無人自動操作と読める。さらに`~/.codex/generated_images/`を証跡元に固定するが、
Python-native VPS環境にはCodex CLIの必須導入契約、runtime-neutral adapter、利用不能時のfail-closeがない。

是正は、Web UIを明示的なattended manual補助に限定し、無人runtimeの第一経路をprovider-neutralな画像生成adapterとして
定義すること。Codex `image_gen`はその許可済みadapterの一実装または開発補助に位置づけ、CLI不在時は未証跡生成や
Web UI自動化へ暗黙fallbackしない。HS／LINE／Canvaのブラウザ補完も同じくactor、execution mode、human judgementを
明記し、公式API優先／attended-only／prohibitedのBRを機械gateで強制する。

## 検証方法

対応表は `G-TEMPLATE-ALIGNMENT` で schema、固定 source commit、latest checked commit、必須 mapping、現行パス実在、
Python pin／frozen CI／credential 非保持、Python-native 開発コマンド、L2 5 点セットを fail-close 検査する。
テンプレートの最新版を追随する場合は source commit を更新し、
この監査と対応表を再生成してから gate とレビューをやり直す。追随しない場合も latest upstream verification に
checked SHA・差分・非適用理由を記録する。
