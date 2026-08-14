---
artifact_id: AUTH-AUDIT-REQUIREMENTS-SEMANTIC-REAUDIT-2026-08-14
lifecycle_status: draft
slice: cross
---

# 要求・要件の意味再監査（2026-08-14）

## 判定

**No-Go（要求再定義中）**。旧要求に対するconfirmed成果物と構造ゲートは履歴として存在するが、
それはVPS製品runtime、製品Web UI、承認、運用通知の新しい要求基準を証明しない。
`requirements_baseline_status=revising`、`implementation_authorized=false`の間は設計・実装完了を名乗らない。

## 監査した正本集合

| 層 | 対象 | 件数 | 意味観点 |
|---|---|---:|---|
| L0 | charter | 1 | 目的、制約、不変条件、製品／開発境界 |
| L1 | BR contracts | 41 | actor、課題、価値、scope in/out、禁止、人間判断、完了証跡 |
| L1 | REQ ledger | 55 | 本文、source、priority、BR→FR/SR/NFRトレース |
| L1/L3 | 媒体BR/MR | BRM 70／MR 54 | 経路、actor、execution mode、外部書込み、規約、quota、証跡 |
| L3 | FR/SR/NFR | 43／19／11 | 振舞、拒否、境界、再開、判断、副作用、証跡、slice |
| L3 | FN | 61 | 責務、FR/MR対応、slice、複合機能の分解 |
| L3 | AC/TC | 252／258 | normal、reject、boundary/recovery、禁止副作用、観測可能な証跡 |
| authority | ADR-006/007/010/013、manifest、discovery | — | 決定の時系列、承認、置換、未決候補 |

`REQ`のactor・価値・scope・human judgement・side effectは型付きfieldではない。`MR` 54件は
すべて`trace.downstream=[]`で、`FN` 61件も次工程の構造参照を持たない。したがってID集合の一致は
意味降下の証明に使わない。

現行`G-REQ-SEMANTIC-DIMENSIONS`の全件棚卸しは4,517違反である（BRM 770、REQ 605、FR 301、
SR 133、NFR 88、MR 486、FN 610、AC 1,008、TC 516。BR 41件は旧schema上の必須観点を充足）。
特にAC 252件は`target`／`target_update`をbusiness scope又はphaseとみなさず、全件でactor、明示scope、
human judgement、phaseを欠く。TC 258件もactor、scope、human judgement、side effectを欠く。
この件数は要求品質の分母ではなく、旧契約を新baselineへそのままcutoverできない反証である。

さらに生成IRの`revalidation_inventory`は旧要求系10台帳、BR 41／BR-M 70／REQ 55／FR 43／SR 19／
NFR 11／MR 54／FN 61／AC 252／TC 258の全864件を欠落なく列挙し、全件を
`applicability=revalidation_required`、`decision_status=unresolved`へ固定する。問題codeの重複集計は
旧baseline再検証864、意味軸欠落823、trace不整合80、phase不整合46、stable REQ root欠落29、
人間判断降下欠落25、既知runtime/policy衝突15、実装降下欠落11である。BR-M／MR／FNもIRへ
`read_only_legacy_requirement_ledger`として射影し、媒体・機能台帳を全件監査の外へ置かない。root欠落契約は
POが業務根拠を選択して再降下するか、理由・risk・依存・再開条件付きdeferredにするまで一括採用しない。
inventoryは非権威projectionであり、採否receiptの代替ではない。

## 意味の正規化原則

1. 環境事実、製品要求、設計選択を分ける。VPS `helix-worker`は開発・製品runtimeの採用基盤である。
   この決定はUI認証方式や公開構成の設計完了を意味しない。
2. 新要求はL0/L1→REQ→FR/NFRの順で降ろす。旧L2〜L6の実装都合を上位要求の根拠にしない。
3. 各要求はbusiness actor、受益者、trigger、価値、scope in/out、禁止、human judgement、
   external side effect、完了証跡、失敗影響を持つ。unknownは問いに束縛し、設計で補完しない。
4. 製品承認、製品運用通知、Discord媒体投稿、開発PR通知は別概念とする。
5. 公式API／MCPを第一経路とし、必要能力を満たせないoperation又は実行結果確認にはPlaywrightを候補経路にできる。
   browserであることだけで一律許可／禁止せず、媒体account／operationごとのprincipal、effect、規約、credential、
   quota、evidenceが閉じた経路だけを採用する。
6. 複合FRの単一slice表現で異なる時期の責務を混ぜない。責務分割または型付きphase対応を必須にする。
7. 上位BRの人間判断は下位FRの機械判定で省略しない。省略するなら先にBR改訂承認を行う。

## 未解決 finding

### F-01 VPS・Web UI・通知の時系列（基準解決／再降下待ち）

- ADR-007は実環境とXServer API/CLI PoC証跡に基づきVPS製品runtimeをacceptedとする。
- ADR-010の投入順序は2026-08-14追補でDiscord先行からWeb UI先行へ改訂した。
- ADR-013はWeb UI＋UI内inboxを初期主入口としてacceptedである。
- VPS配備、UI主入口、UI内inbox初期搭載は確定した。ただし要求完了前に実装へ進まず、Web Push、
  Discord補助通知、品質閾値の範囲を確定後、ADR-010/013と要求契約を正規化する。

解決した要求基準はVPS `helix-worker`への製品runtime配置方針、製品Web UI主入口、UI内inbox初期搭載である。
runtime、service、UIの実装・配備は未着手であり、この要求決定を稼働済み証跡にしない。未解決は
Web Push追加とDiscord補助の採否、認証・公開要件であり、L2以降はなお再降下待ちとする。

### F-02 承認と運用通知の混同（Blocker）

- FR-16/43が異常通知を投稿承認専用のFR-46 `ApprovalTransport`へ送る。
- FR-76は`operational_notification`をS1とし、FR-46との混在を禁じるがFN/API/CMPへ未接続である。
- BR-H3は通知送達記録を完了証跡に求めるが、FR-16/43のACは送達・失敗・再送receiptを要求しない。
- AC-16-1は通知mock回数を観測する一方、expected evidenceは状態遷移とfailure codeだけで、TCC-16-1は
  external callを0回とする。通知を実配送・inbox書込み・単なるmockのどれとして検証するかが閉じていない。
- Web UIの通知inboxと承認待ちを別状態とし、一方向通知からapprove/rejectを導出しない。
- 新要求候補は安全停止、承認待ち、実行失敗をS0のUI内inboxへ置き、Discordを初期範囲から外す。通知ID、
  purpose、source event、対象profile/resource/revision、severity、業務状態、人間判断要否を要求fieldとする。
  lifecycle、重複排除、retry/backoff、retention、FR-43等への適用範囲はRDE-000100/101で未決として束縛し、
  設計で推測補完しない。

### F-03 オートモードの決定主体（基準解決／再降下待ち）

BR-H2はPOを最終移行判断者とするが、FR-46と承認設計は基準充足の機械判定だけで承認を省略する。
基準評価とモード変更の決定を分け、PO最終承認を維持する。機械判定は移行候補を作るだけとし、
POのbinding承認なしにauto-modeへ移行しない。旧FR/承認設計は再降下で修正する。

### F-04 外部接続優先順（Major）

- BR-F1はMCP→ブラウザ→有償API、ADR-006/FR-41はMCP→無料公式API→ブラウザ→有償API。
- BR-E2はGA4/GSCをブラウザexportに固定するが、媒体BR/MRとFR-62は正規API第一。
- 無人経路は公式API優先、API非提供・阻害時のみofficial export/attended manualとする案を候補とする。

### F-05 生成AIの規約違反fallback（Major）

confirmed BR-M-GENAIは消費者Web UI自動操作を規約違反とするが、confirmed FN-510とtech stackは
ブラウザ生成を経路/fallbackにする。provider-neutralな許可API/CLI adapterに限定し、Web UIは
attended manualのみ、自動fallbackはfail-closeで拒否する。

### F-06 FR・FN・ACのslice/更新責務（Major）

- requirements ledgerとFR contractsに22件のslice不一致がある。
- 同一IDを持つ`functional/requirements.json`はactive/draftの旧compatibility view、FR contractsは
  active/confirmedであり、現行engineは前者をread-only revalidation viewへ隔離して147件の意味差分を検出する。
- confirmed同士でFR-16 S0→FN-110 S1、FR-42 S1→FN-402/404 S0・FN-403 S3、
  FR-44 S1→FN-406 S0・FN-407 S3、FR-55 S0→FN-512 S1が衝突する。
- requirements docはFR-16/26/43/55のACをdeferredとするが、AC/TC contractsとL6割当はすでに存在する。
- `slice`、`target_update`、後続capabilityを別軸として型定義し、複合FRを責務単位へ分解する。

### F-07 媒体要求の下流未接続（Major）

MR 54件はすべてdownstreamが空である。Discord媒体投稿、LINE、生成AI、計測等の要求がFN/API/AC/TCの
どの拒否・証跡で満たされるか機械的に証明できない。実装対象は責務単位の下流traceを必須、
将来候補は`deferred`+理由+再開条件を必須にする。

### F-08 REQ/discoveryの意味field不足（Major）

REQ 55件とcandidate eventは、業務actor、scope in/out、permission、human judgement、side effects、
failure/exception、sliceをtyped fieldとして持たない。workflowは20観点の質問を求めるが、仕様化前の解決を
gateで検査できない。typed semantic observationとunknown→question参照を導入する。

### F-09 レート制御の対象集合（Major）

BR-F5は全媒体の外部writeにランダム間隔を要求するが、NFR-7と媒体MRはブラウザwriteだけを対象とし、
公式API/MCPはquota準拠で間隔N/Aとする。BR-F5の対象をbrowser automationに限定し、APIはprovider quota・
app/account cap・retry-afterの別契約にする。

### F-10 媒体追加の変更集合（Minor）

BR-F3は「workflow追加のみ」とするが、NFR-8/FR-41/48はworkflow・playbook・connector registry・
media bindingのdata rowを要求する。外殻code diff=0を不変条件とし、追加可能なdata artifact集合を一致させる。

### F-11 外部write許可集合と媒体要求（初期基準解決／再降下待ち）

confirmed external IFとS0 DDLのwrite許可閉集合はDocker WP公開、Notion review sync、Discord承認通知、
承認済み有償操作だけである。一方、媒体BR/MRはnote、YouTube、stand.fm、KDP、LINE、HubSpot、
Discord community等への投稿・出版・配信を要求する。各媒体を`enabled`、`attended-only`、`read-only`、
`deferred`のいずれかに決め、許可するwriteだけをactor、policy category、service、operation、endpoint、
credential scope、approval/evidenceとともに閉集合へ追加する。決定前は外部writeを実装しない。

新baseline候補の要求freezeと媒体release受入が済むまでは、実証済みDocker WPを含む全媒体writeをdisabledとする。
XServer PoCは実現可能性evidenceであって本番principal、credential、policy、AC/TC、release receiptの代替ではない。
媒体ごとの受入後にだけ個別capabilityを`enabled`へ昇格し、旧媒体BR/MRのwrite表現は再降下まで実装入力にしない。

### F-12 媒体別経路の正本衝突（Major）

- LINEのconfirmed BRはMessaging API第一だがMRはブラウザ配信かつMessaging API不使用とする。
- Discord媒体BRはBot only／self-bot禁止だがMRの「ブラウザ補完」はactorとattended境界がない。
- Canva BRは素材取得の自動化を禁止するがMRはMCP／ブラウザ経由の素材取得を許す読み方である。
- Notion MRはgate N/AとするがFR-45は`review_sync` write前の承認を必須にする。
- HS/LINE/Canva/生成AIのブラウザ経路は、attended manualと無人automationを区別していない。

媒体ごとに正規API、attended fallback、禁止経路、write承認、失敗時fail-closeを一意にする。

### F-13 L2 UIが未契約の操作と境界を提示する（Major）

- Discord deep-linkを用途に関係なく承認画面へ送るため、運用通知・媒体投稿を承認と混同する。
- 承認UIの`return`はapproved/rejected/expiredの状態閉集合やAPIに存在しない。
- 通知画面の購読設定は主体、設定schema、scope、FR/AC/TCを持たない。
- 全ブランド俯瞰はprofile隔離を越える集約契約を持たず、`brand`、`business_profile`、
  `bounded_domain`の関係も型定義されていない。
- KPI handoffは存在しない`FR-78`を参照する。

これは新要求から導出された設計ではないため、L2を実装入力にせず、要求確定後に画面・遷移・権限・
状態・traceを再設計する。unknown FR参照とpolicy categoryのcross-routeは機械的に拒否する。

### F-14 通知完了証跡の欠落（Major）

BR-H3は通知送達記録を完了証跡に求めるが、FR-16/43と対応AC/TCは送達、失敗、再送、未配送の
durable receiptを要求しない。初期運用通知経路はUI内inboxと確定したため、状態成立とinbox記録成立を分離し、
記録失敗でも業務状態をrollbackせず、attempt／delivered／failed／retry／abandonedの証跡を検証可能にする。
既読・確認・解決は業務状態と別lifecycleとし、語彙と保存期間はPO決定まで未確定として明示する。

### F-15 戦略要求の検証trace欠落（Major）

SR-17/18/19はS2だが`trace_down.ac=[]`である。戦略testのSTC-I-11〜13は存在してもSR契約から
逆引きできないため、要求完了や検証可能性を証明しない。S2 deferred＋再開条件を明記するか、
SR→AC/STCの双方向traceと反証条件を追加する。

### F-16 「人間接点2点」と下流判断点のscope不一致（Major）

BR-H1は通常ループの人間接点を問診とbinding承認の2点に限定するが、危険設定変更、KPI tree、
migration、媒体account、運用通知allow-list、escalationにも人間判断がある。通常ループ、setup、例外、
governance、外部writeのphaseを型で分け、どれを「2点」に数えるかをBR/FRで一致させる。

### F-17 confirmed旧要求の単独閲覧リスク（Major）

requirements、media requirements、function list、tech stack、verification/basic design等は旧基準の
confirmed表示を保持する一方、authority現在地は`requirements_baseline_status=revising`かつ
`implementation_authorized=false`である。confirmed履歴を改ざんせず、各成果物を新要求の現行入力と
誤認させない機械可読なapplicability／legacy-baseline参照を導入する。PO承認なしに内容confirmedを
書き換えたり、新要求へ適用可能とみなしたりしない。

旧L0、REQ一覧、requirements、L4 basic/tech-stack/approvalの冒頭にはhistorical/non-input bannerを置き、
FR/SR/NFR/AC/TC/BR/CMP/DUの生成view 8本には同じbannerを`render_views.py`から生成する。bannerの欠落、
旧viewの通常ゲート再利用、AGENTS/CLAUDEのrevising境界欠落は機械検査する。これで誤適用を防いでも、
旧内容の意味不整合が解決したことにはせず、semantic gateの赤と再降下要求を維持する。

### F-18 設定変更の人間判断範囲（Minor）

L2 BF-03はconfig INSERT全件に明示承認が必要と読めるが、FR-33は危険側変更だけを人手判断とする。
低リスク自動設定、危険設定、secret変更、外部write許可を分類し、UI操作と承認要求を同じ語彙にする。

### F-19 BR→REQ→FR/NFRの意味trace欠落（Major）

現行ゲートはID実在と集合被覆を中心に検査し、BRとREQが主張する下流責務の同値を保証しない。
例としてBR-B3→REQ-023はFR-28/62へ降りるがBR-B3の直接traceにFR-62がなく、計測取得証跡と
全完了証跡の責務が切れる。BR-B1→REQ-008、BR-B2→REQ-009、BR-F1→REQ-027にも同様の欠落がある。
BR traceを要約とするかexact chainとするかを決め、exactならBR→REQ→FR/NFRの推移閉包と意味fieldを
機械検査する。要約なら正本上で非規範と明記し、実装・検証入力にしない。

要件エンジン追加後の隣接trace検査では、REQ-027→NFR-6、REQ-030→NFR-8、REQ-031→NFR-4、
REQ-040→NFR-1、REQ-041→NFR-2、REQ-042→NFR-3、REQ-043→NFR-5、REQ-044→NFR-7、
REQ-052→NFR-3の9辺がNFR側から逆参照できないことを検出した。旧ゲートのgreenはこの欠落を証明しない。
さらにcontract側にstable REQ root自体がないものはFR-45/53/72/74〜77、SR-01〜05/12/15〜19、
NFR-1〜11である。合計38件の隣接trace違反としてfail-closeし、stable REQへ接続するか、理由・risk・依存・
再開条件付きdeferredへ分類する。特にFR-74〜77はaccount、preflight、運用通知、VPS UI閲覧の新要求中心なので、
既存BRや節番号への直接参照だけで新baselineへ昇格しない。

### F-20 VPS採用後も残るWSL cron／Discord先行設計（Major）

ADR-007/013はVPS runtimeとWeb UI＋inboxを採用したが、旧confirmed tech stack、FN-109、function list、
FR-46、S0 contract、L4〜L6にはcron(WSL)またはDiscord初期tupleが残る。これらをその場で部分修正すると
未確定要求を設計で補完するため、旧設計baselineとして実装不許可を維持する。通知、認証、scheduler、
deploymentの要求が閉じた後、FN／FR／AC／TCからL2〜L6まで同一baselineで再降下する。

### F-21 provider依存の二重正本（Major）

旧confirmed charter／BR-G3／FR-52はClaude Designを必須正本、BR-M-GENAI-4はCodex image generationを
第一経路とする。一方、再定義候補PRC-09/18は双方を任意adapterとし、製品runtimeをprovider-neutralにする。
Claude Codeという開発clientの非必須化とは別問題である。provider、capability、規約、quota、credential、
fallbackを個別refinementで決め、採用時はL0／BR／FR／MR／AC／TCを同じreceiptへ再降下する。

### F-22 DU・試験IDの二重語彙（Major）

DU-13以降の複数契約が、現行`TCC-*`と並べて不存在の旧`TC-041`、`TC-047`、`TC-GATE-*`等を参照する。
L4/L6本文にも同じ別名が残る。`G-REQ-TRACE-IMPLEMENTATION`で未知IDを拒否し、旧試験意図をどのTCCへ
統合又は廃止するかを要求traceとして決めるまで、DU/APIを実装入力にしない。

### F-23 FN・ACのphase逆転（Major）

FR→FNには26件の直接phase差分があり、FR-16(S0)→FN-110(S1)、FR-42(S1)→FN-402/404(S0)、
FR-44(S1)→FN-406(S0)/407(S3)等を含む。AC-44はFR-44(S1)に対してtarget_update=S0.2である。
`S1+`／`S3+`も実装phaseを一意にしない。責務を分割して厳密phaseへ再付番し、FN/AC/TCを同じ責務へ
付け直すまで、旧sliceをrelease順序に使わない。

### F-24 意味軸を表現できない契約schema（Major）

BRはactor/value/scopeを持つが、FR/SRはactor/beneficiary/value/workflow/scope、NFRはそれらに加えて
phase/human judgement/side effect、AC/TCはactor/scope/human judgement/phaseを直接表現できない。
上位traceから継承する型付き規則もない。`G-REQ-SEMANTIC-DIMENSIONS`で欠落を可視化し、直接field又は
一意な継承mappingが揃うまで、ID・件数・AC存在だけで意味完了を宣言しない。

### F-25 WordPress運用・保守・セキュリティ保守の責務混在（Major）

最初の媒体releaseはWordPressをコンテンツDBとして扱い、公開を含む。ここでいう運用は、コンテンツ公開、
リライト、メディアアップロード、固定ページ編集である。保守はWordPress本体のversion update、その随伴変更、
plugin導入・update、及びそれらの変更に起因する障害対応である。脆弱性、credential、権限、security patch、
監査と緊急判断はセキュリティ保守としてさらに分離する。三者を同じrelease、actor、停止条件、AC/TC又は
rollbackで受入れてはならない。`RRF-WORDPRESS-MAINTENANCE-BOUNDARIES`を閉じ、本格systemをFull V-modelで
扱うだけでは不十分なため、`RRF-WORDPRESS-CONTENT-OPERATIONS-RELEASE`、
`RRF-WORDPRESS-PLATFORM-MAINTENANCE-RELEASE`、`RRF-WORDPRESS-SECURITY-MAINTENANCE-RELEASE`を
独立candidateとして起票した。各refinementを個別に閉じ、本格systemをFull V-modelで設計し、段階releaseには
必要に応じてV設計＋Scrum実装Hybrid、S4判断、Scrum Reverse SR0〜SR4、V-pair
closureを適用するまで実装入力にしない。実現性又は成功条件が未知の対象だけをDiscoveryへ送る。

### F-26 AGENT NEOサイト構築とtheme改修の段階境界（Major）

AGENT NEO `9f5d679c0befce093ba077fcf11d514e4c75f17a` はFSE theme、Core Plugin、`agent-neo/v1` REST、
dry-run/apply/rollback、SEO、監査CPT等を既に持つが、その既存G4結果はMARKETING HARNESSの新要求を
受入れた証跡ではない。WordPress運用・保守の実証後、AGENT NEOによるサイト構築全体を新HELIX型で
Full V-modelのL1〜L12と正規V-pairで要求から再定義する。サイト構築releaseと、AGENT NEO自体の改善・
改修・update releaseを分け、後者を第三段階とする。段階incrementだけをProduction Scrum又はV設計＋Scrum
実装Hybridで回し、S4後もSR0〜SR4とV-pair closureを必須にする。ScrumをDiscovery/PoCと同一視しない。
repo authority、API、evidence、互換性、migration、rollbackを閉じるまでAGENT-NEOへ書き込まない。

### F-27 現行HELIX要件エンジンの未移植境界（Major）

現行HELIXの要求確定は、Full V-model L1〜L12の6 V-pair、`requirements`、`system_contracts`、
`acceptance_cases`、`system_tests`、`refinement_contracts`の5 IR区画、delivery route admission、
Production Scrum後のScrum Reverse SR0〜SR4及びV-pair closureを一体で扱う。本リポジトリにはstable ID、
semantic projection、個別refinement、PO admission、authority cutoverのbridgeはあるが、この全体は未移植である。
したがってDiscovery ledgerだけを「要求エンジン導入済み」と数えず、`helix_engine_adoption.status=bridge`と
未移植5項目を機械固定する。5 IR区画とFull V／route／reverse closureをPython-nativeで再現し、生成要求view、
negative test、PO receipt、独立reviewまで揃う前に`adapted`又は要求完了を宣言しない。

### F-28 charter v0.4と新要求候補の上位意味衝突（Blocker）

charter v0.4は旧baselineのconfirmed上位根拠としてDiscord初期承認、Web UI将来、消費者Web UI自動化、
MCP→browser→paid、Claude Design必須等を保持する。一方、ADR-013及び新候補はVPS Web UI＋UI内inbox初期、
Discord deferred、公式API／attended-only、provider-neutralを要求する。内容を部分修正して承認履歴を偽装せず、
manifestのtop-level applicabilityでL0〜L6全体を`revalidation_required`、実装入力false、例外ゼロに固定する。
POが新baselineを個別refinementで凍結し、L0から再降下するまではcharterを「現行北極星」として実装へ使わない。

### F-29 MR-WPのコンテンツ運用・通常保守・security保守混在（Major）

MR-WP-1〜5は同じ`connection`と`actions`へ、RESTによる記事作成・更新・下書き・公開・media操作と、
WP-CLIによる子theme／plugin配備、permalink／SEO設定を反復記載し、FR-44/CMP-10は全writeを
`content_publish`として扱う。これでは投稿承認でcore/theme/plugin変更が通り、公開rollbackと変更保守rollback、
security緊急判断を区別できない。content operation、通常保守、security保守を別stable ID、operation、connection、
policy category、principal、再認証、maintenance window、evidence、AC／TC、release receiptへ分割するまで実装入力にしない。

### F-30 媒体BRとMRの接続経路逆転（Major）

LINEはBRでMessaging API第一・管理画面attended限定だがMRはAPI不使用browser、生成AIはBRでconsumer Web UI
自動化を規約違反とするがMRは保有account Web UI操作、XはBRでbrowser write禁止だがMR connection/actionsは
Playwright／Camoufoxと投稿操作、PlayはBRでon-holdだがMRはbrowser公開routeを保持する。説明文の`safety`だけで
相殺しない。PO回答は公式API／MCP優先、Playwright fallback及びbrowser確認を許容する方向でcapture済みであり、
`EXTERNAL-BROWSER-AUTOMATION-ROUTE`へmaterializeした。MRへexecution mode、principal、effect、policy、statusを
型付けし、媒体operation別refinement、AC／TC、PO receiptが閉じるまで実装入力にしない。

### F-31 旧L2 prototypeの未定義意味（Major）

旧L2はDiscord deep-linkをnotification classなしでAP-02／EV-01へ接続し、canonical decisionにない
`return/差戻し`、存在しないFR-78、要求契約のない通知subscription write、cross-profile authority未定義の
全ブランドBIを含む。書式だけを移植済みとし、画面・flow・write semanticsは新要求の根拠にしない。
VPS UI／inbox、approval、profile scopeのrefinement凍結後にL2を新規再作成し、unknown IDとcross-routeを
negative gateで拒否するまで実装入力にしない。

### F-32 VPS credential保存境界の二重正本（Security Blocker）

accepted ADR-007はVPS上の`0600`環境fileをcredential保存先とするが、旧S0契約／external-if／CMP-07は
暗号化storeからのruntime注入、env横流し禁止、test/prod物理分離を要求する。file modeは平文at-rest、service unit、
journal、argv、dumpへの漏えいを防がない。ADR-014は暗号化store又は有人一時注入への改訂候補だが未承認である。
具体backendを設計で先取りせず、at-rest保護、unlock、runtime注入、rotation、backup/recovery、scope分離を要求として
凍結し、ADR-007/014、FR-47、NFR-4、CMP-07、DU-14を同一receiptへ再降下するまでVPS credential実装を禁止する。

### F-33 要求定義済みと実装降下済みの混同（Major）

FR-17／35／48／73〜77は`design_status=requirements_defined`でACを持つ一方、FN／CMPへ降下していない。
SR-17〜19は同じstatusだがACも空で、別のdraft strategy test台帳が存在するだけである。これは「要求として記述した」
ことと「実装責務・受入・system testまで閉じた」ことの混同である。`G-REQ-DESCENT-ADMISSION`により、FN・CMP・ACへ
降下済みか、`admission_status=deferred`と再開条件を持つかの二択に閉じる。どちらでもない契約をconfirmed件数やAC件数で
implementation-readyと数えない。

### F-34 VPS UI主入口とFR-77 API-only閲覧の衝突（Major）

ADR-013及びPRC-01／15はVPS Web UI＋UI内inboxを、状態・失敗・KPI・承認待ち・証跡の初期主入口とする。
一方、旧FR-77はprecondition、invariant、normal behaviorでWeb UIを明示的に対象外／提供禁止とする。旧契約の
read-only、profile scope、masking要求を維持するだけではUI閲覧capabilityへ降下しない。FR-77を再分割又は
UI閲覧要求を別ID化し、認証・認可・masking・監査・AC／TCへ降下するまで、UIを設計入力にしない。

### F-35 上位人間判断の下流消失（Major）

BR-D2のdraft採否、BR-D3の危険側config変更、BR-D4／I1のprofile内容確定・追加廃止、BR-E1のKPI tree初期承認、
BR-F1の有償API例外追加、BR-F3の媒体追加、BR-G3のDesign System改訂、BR-I5のcampaign brief／語彙確定は、
対応するFR-32／33／34／61／41／52、SR-06／14のACで登録・取得・cache等の機械正常系だけになり、approver、
approval ID、decision receiptを検証しない。BR-I6の企画確定はSR-13で「なし」とされ、別agent審査へ置換されている。
BR-A3のbrand計画確定はDDL生成FR-71へ誤接続され、BR-H2／F5／I1の公開・auto-mode・警告後再開・profile追加判断は
FR-75のpreflight自動判定へ混載されている。`auto_eligible`又は台帳整合はPOのenable／resume／profile decisionを
代替しない。
AI／agent判定をPO判断に読み替えず、decision対象、revision、principal、時点、結果、evidenceを対応AC／TCまで降下する。

### F-36 NFRのstable要求根拠欠落（Major）

NFR-1〜11は全件、`trace_up`にstable REQ IDを持たない。REQ台帳側はNFR-1〜8等をdownstream宣言するため片方向で、
actor・価値・scopeへ戻れない。NFR-9はMR-HS／LINE、NFR-10はrisk register、NFR-11はFR-74／NFR-7を主根拠とし、
法規、backup／recovery、月次account quotaの業務根拠とPO scopeがない。stable BR→REQ→NFRへ再接続するか、
再開条件付きdeferredへ閉じるまで、AC／TCCが存在しても品質要求の受入完了と数えない。

### F-37 confirmed ACとdraft戦略test正本の混在（Major）

AC-SR-01〜06の一部はTCCと同時に`STC-I-01`〜`STC-I-06`を参照するが、その実体
`strategy-tests.json`はmanifest上active／draftでapproval digestを持たない。confirmed ACの反証oracleをdraft台帳へ
依存させると、TCC正本とSTC台帳のどちらがrelease判断を拘束するか決まらない。STCをPO receipt付き正本へ確定するか、
対応SR／ACを再開条件付きdeferredへ分離する。

### F-38 実行契約本文の未定義wildcard ID（Major）

FR-21のinputは公開系connectorを`FR-4x`経由と記すが、これは実在stable IDではなく、実際のWordPress write契約
FR-44等へ機械traceできない。CMP-10のsecurity boundaryもレート節度の根拠として存在しない`BR-31`を参照する。
分類見出しの略記を実行契約の依存参照に使わず、正規IDと責務へ置換する。自由文内IDもsemantic reference検査の
対象にし、存在しない契約を実装者が推測で選ばないようにする。

### F-39 provider-neutral要求と旧provider必須経路（Major）

旧L0／BRはClaude Design／DesignSyncを必須正本、媒体BRは個人Codex CLIと`~/.codex/generated_images`を第一経路、
旧L4はconsumer Web UIをfallbackとする。一方、新要求候補はClaude／Codexを任意adapter、公式API／MCPを第一経路、
必要なoperationにPlaywright fallbackを許容する。Claude Codeという開発clientの非必須化だけではこの製品依存を
解消しない。capability、execution mode、principal、credential、evidence、fallbackをprovider-neutralかつ
operation別の契約へ再降下するかdeferredにする。

### F-40 オートモード適格判定とPO移行承認の混同（Safety Blocker）

BR-H2は、安定稼働基準の証跡判定に加え、公開時の束縛承認を省略するオートモードへの移行をPOが最終承認する
ことを要求する。一方、旧FR-46とapproval-designはcriteriaと実績証跡の機械判定だけで承認を省略でき、移行を
決めたprincipal、対象媒体、revision、時点、decision receiptをAC／TCで検証しない。`auto_eligible`という機械判定と、
POの`auto_mode_enable`決定を別状態・別証跡にし、未承認・期限切れ・基準失効時は常時承認へfail-closeで戻すまで、
外部公開の承認省略を有効化しない。

### F-41 L1 REQ JSONと確認済みREQ Markdownの同一ID異義（Major）

機械REQ ledgerと確認済みの要求一覧Markdownを意味比較すると、15件のREQで合計19 fieldが一致しない。
REQ-001は出典と下流、REQ-008／009は下流、REQ-023／037／045は出典又は下流、REQ-047／048／050は下流、
REQ-053〜055は本文が異なる。`—`とnull相当は同じ「充填なし」と正規化し、表記差を意味違反へ数えない。
件数とID集合が同じでも、BR→REQ→FR/NFRの根拠と責務は一意にならない。
両方を実装入力から外した`revalidation_required`資料として保持し、POが意味を選択した後に一つのJSON正本から
Markdownを生成する。`G-REQ-SEMANTIC-DRIFT`はFR/NFR一覧だけでなくこのREQ差分もfail-closeに含める。

### F-42 historical requirementsを規範入力にするconsumer導線（解消済み）

旧`requirements_v0.1.md`と`requirements.json`をhistorical／read-only revalidationへ隔離した後も、L0 charter、
S0 contract、verification design、basic design、S0 trace台帳の5箇所が旧Markdownを規範参照していた。
これらを旧契約JSONの履歴参照又はnon-normative snapshot表示へ変更し、旧一覧への規範導線を除去した。
`G-REQ-LEGACY-CONSUMER-ISOLATION`は現在PASSし、完全な旧ファイル名だけを検出して
`media-requirements_v0.1.md`のような別文書を部分一致で誤検出しない。旧viewは引き続き意味差分監査専用であり、
新要求がPO receipt付きでfrozenになるまでは設計・検証・traceの規範入力へ戻さない。

### F-43 旧MRの黙示採用を防ぐ全件deferred inventory（Major）

旧MR 54件はconnection、actions、safety proseを持つが、capability status、execution mode、principal、effect、
policy category、credential scope、quota、evidence、AC／TC descentを閉じていない。LINE、X、Play、生成AI等には
上位BRとの直接経路衝突もある。旧文章から新baselineのroute又は許可を推測せず、全54件を安全側`deferred`とする
inventoryへ収載した。`G-REQ-LEGACY-MEDIA-INVENTORY`は全件収載と再開必須fieldを検査する。一方、旧MR正本自身は
未降下なので`G-REQ-MEDIA-ADMISSION`を意図的にredのまま維持する。媒体・operation単位で業務価値と全意味field、
三極性AC／TC、PO receiptを凍結したcapabilityだけを`enabled`、`attended-only`又は`read-only`へ昇格できる。

### F-44 全864 IDの再降下判断owner（解消済みの構造境界）

旧要求系10台帳のBR 41、媒体BR 70、REQ 55、FR 43、SR 19、NFR 11、MR 54、FN 61、AC 252、TC 258の
全864 IDをrevalidation inventoryへ収載した。各itemは12意味軸、実在するrefinement subject、許可処置
`redescent`／`deferred`／`superseded`を持つ。これにより、横断候補だけ作って個別IDを取り残すこと、又は
旧IDを黙ってcurrentへ戻すことをIR projection gateが拒否する。inventoryは判断の代替ではなく、全itemの
`decision_status=unresolved`を維持し、個別subjectのPO receipt後にだけ処置を確定する。

### F-45 会話回答を要求候補へmaterializeする境界（構造解消、承認未完）

POとの要求確認で、(1)公式API／MCP優先＋Playwright fallback／browser確認、(2)Discordは通知に使わずcommunity
marketing媒体として使う、(3)VPS UI内inboxで初回scope承認後は毎回承認なしで自動運用、(4)不合格contentは
人間確認前に自動再生成・再検査、(5)feedbackをscope付き外部ruleへ追加、(6)YMYL等のrisk別厳格性とcase-by-caseの
好み、(7)research→marketing funnel→媒体役割→KPI還流、(8)商品／offerごとの変更capability、(9)有料集客は超後期
deferred、が回答された。これらを`captured_po_decisions`だけに残さず、RDE-000136〜147、PRC-30〜35及び6件の
意味軸付きrefinementへmaterializeした。`G-REQ-DECISION-PACKETS`は回答が要求subjectへmaterializeされない状態を拒否する。

content gateとgrowth要求は、禁止語だけでなくpeople-firstの有用性、独自research／分析、claim-source対応、鮮度、経験／
専門性、誇張抑制を含む。YMYL相当のrisk軸は健康、金融上の安定、安全、社会の福祉／well-beingとし、検索順位操作を
主目的にした大量生成、query variation別の低価値量産、付加価値のないsource要約をnegative acceptanceに追加した。
根拠はGoogle Search Centralのpeople-first／YMYL及びgenerative AI search guidanceをrefinement evidenceへ束縛した。

各refinementはdraft又はspecifiedであり、PO approval receipt、frozen cutover、L2以降の設計はまだ存在しない。
旧BR／FR／MR／ADRを直接書き換えて採用済みにせず、個別のpending（媒体operation、risk分類、KPI閾値、activation失効等）を
閉じた後に同一cutoverで再降下する。

追加の再監査で、`RRF-VPS-UI-PRIMARY-HUMAN-INTERFACE`に旧意味の「投稿承認」が残り、PRC-04／05が旧
`DISCORD-MULTI-PURPOSE-BOUNDARIES`をmeaning ownerとしていた点を検出した。VPS UIは初回activation・scope拡張・
高リスク例外・停止後再開の判断へ限定し、activation後の個別投稿は毎回承認しない。PRC-04はUI inbox lifecycleだけ、
PRC-05／31は`DISCORD-COMMUNITY-MARKETING-ROUTE`だけへ束縛し、gate mutationで旧個別投稿承認又は旧Discord通知の
再混入を拒否する。

RDE-000142〜147の6質問は、会話上すでに回答済み又は対象登録時のcapabilityから決まる内容だったため、未回答の
PO質問として残さない。RDE-000148〜153へ回答をappendし、Playwright route、Discord community、初回activation後
自動運用、quality learning、risk classification、research-led growthの6 refinementを`specified`へ進めた。これは
質問解消の証跡であり、subject全体のPO approval又はfrozen cutoverではない。operation別account情報や数値設定は
媒体／campaign登録時に束縛し、全媒体共通の抽象質問としてPOへ再質問しない。

旧`AUTO-MODE-DECISION-AUTHORITY`は過去にwithdrawn済みで、期限切れ時に毎回承認へ戻す旧意味を持つため履歴のまま変更しない。
RDE-000154／155は新`AUTOMATED-PUBLISHING-ADMISSION`へ束縛し、固定期限を全対象へ強制せず、取消・権限喪失・scope外・
重大rule変更又は停止条件成立時は外部writeを停止する要求へ置換した。停止後は個別承認modeへ暗黙復帰せず、対象scopeを
再表示した明示re-activationまで停止を維持する。これにより機械criteriaは成果物gate又はactivation候補評価に限定され、
activationそのものの代替にならない。

### F-46 旧L0の事業価値と実現手段のclause別移送（構造解消、承認未完）

旧charterは、保持すべき事業価値と、VPS移行・通知用途分離・provider-neutral化・媒体別capability化によって置換又は延期する
実現手段を同じ本文に混在させていた。旧L0を全文採用又は全文破棄せず、`legacy_l0_clause_dispositions`へ15 clauseを収載し、
各clauseを`retain`／`replace`／`defer`のいずれかへ一意に分類した。保持するのは事業目的、dual-loop、媒体並列運用、
人間とAIの責務分離、柱体系及びDiscord community marketingである。consumer Web UIの無人操作はAPI／MCP優先＋Playwright、
Claude Design必須はprovider-neutral capability、WSL runtimeはVPS runtime、Discord投稿承認はVPS Web UI内inbox、旧auto-modeは
初回scope activation＋content gate＋停止後の明示re-activationへ置換した。PWA／Playの初期採用は再開条件付きでdeferredとした。

商品又はofferについても旧文面から一律の変更権限を推測しない。対象ごとにowner、選定可能性、差替え可能性、内容変更可能性、
許可principal及び許可operationを登録する。アフィリエイト等の選定可能な商材は許可scope内で探索・比較・採用・差替えできるが、
固定商品又は変更不能な第三者商材には変更操作を生成せず、権限不明時は既存対象を前提にresearchとcontentを最適化する。

`G-REQ-L0-CLAUSE-DISPOSITION`は15 clauseの過不足、置換先PRC、deferred再開条件、Discord用途、runtime、browser route及び
auto-operationの意味をfail-closeで検査する。この表は旧L0から新要求候補への移送判断を欠落させないための構造であり、全行
`candidate_unratified`かつ`design_not_started=true`である。PO approval、frozen cutover又はL2以降の設計完了を表さない。

### F-47 旧通知・承認・自動運用・UI責務の移送（構造解消、承認未完）

旧BR-H2/H3及びFR-16/43/46/75/76/77は、投稿可否の承認、異常通知、repair、profile binding、auto-mode、証跡閲覧を
Discord／ApprovalTransport又はAPI-only契約へ結合していた。これらを`legacy_critical_responsibility_dispositions`へ収載し、
旧IDごとに維持する業務責務、置換後の責務、meaning owner及び継承禁止事項を固定した。

FR-16/43はsafety-stop又はrepair lifecycleとdurable evidenceを第一責務とし、人間対応が必要なeventだけをbinding不要の
VPS UI内operational inboxへ射影する。FR-46は旧Discord interactionと個別投稿承認を置換し、VPS UIでの初回activation、
scope拡張、高risk例外及び停止後re-activationと、activation scope内でcontent gateに合格した通常投稿の自動公開へ分ける。
機械criteriaはactivationの代替にならない。FR-75はprofile/account bindingの機械preflightを維持するが、profile追加・廃止・
activationの人間判断とは分離する。FR-76は初期VPS UI内inboxへ置換し、外部通知adapterは個別承認までdeferredとする。
FR-77は改変禁止のread model/API責務を維持しつつ、VPS Web UI主入口及び認証・session要求へ分割する。

`G-REQ-CRITICAL-RESPONSIBILITY-DISPOSITION`は8旧IDのexact coverage、実在meaning owner、未承認・未設計境界に加え、
Discord通知、ApprovalTransport再利用、通常投稿の毎回承認、機械criteriaだけのactivation、FR-77のWeb UI禁止が再混入
しないことを検査する。これは旧契約の置換候補を明示しただけであり、新BR/REQ/FR/AC/TC又はL2設計への再降下は未実施である。
全864 IDのrevalidation inventoryでもBR-H2/H3及びFR-16/43/46/75/76/77の判断ownerを新subjectへ差し替え、MR-DC-1〜3は
Discord community専用subjectへ束縛した。旧`AUTO-MODE-DECISION-AUTHORITY`及び`DISCORD-MULTI-PURPOSE-BOUNDARIES`は
履歴deferred packetへ隔離し、PRC-06／22の意味ownerは`AUTOMATED-PUBLISHING-ADMISSION`へ置換した。

### F-48 全要求層の意味降下policy（構造解消、個別再降下未完）

旧契約はBR以外の多くでactor、value、scope、human judgement、side effect、evidence又はphaseを直接型付けせず、trace先の
散文又はtarget IDから推測する余地があった。`semantic_descent_policy`は12意味軸と10 edgeを定義し、BR→REQ、媒体BR→MR、
REQ→FR/SR/NFR、FR/SR/NFR/MR→FN/AC、AC→TCを要求候補内の降下経路として固定した。actor、task、workflow、scope、
human judgement、side effect、evidence及びphaseは対象層で直接宣言する。beneficiary及びvalueを継承する場合もsource kind、
stable ID、revision、semantic digest、dimension、scope transform及びrationaleへ束縛する。prohibitionは上位禁止を弱めず、
対象層固有の禁止だけを追加する。未知fieldは実装者が補完せず`question_then_deferred`とする。

ACはpositive／negative／boundaryでprincipal、scope、decision receipt、許可作用及び禁止作用を反証可能にし、TCは同じ意味digest、
scope、principal、side effect、evidence及びphaseを検証する。FN→CMP及びCMP→DUは
`blocked_until_frozen_requirements`であり、このpolicy自体も`candidate_unratified`かつ`design_not_started=true`である。
`G-REQ-SEMANTIC-DESCENT-POLICY`は12意味軸、全edge、継承binding及び設計開始禁止を検査する。ただし旧864 IDのfield欠落を
修正したわけではないため、`G-REQ-SEMANTIC-DIMENSIONS`は個別再降下完了までredを維持する。

### F-49 旧NFR-1〜11の業務根拠と処置（構造解消、個別承認未完）

旧NFRは詳細な測定式とAC/TCを持つ一方、全件がstable REQを逆参照せず、NFR-9/10はstable BRも持たなかった。
`legacy_nfr_dispositions`へ11件を収載し、業務価値、actor、scope、stable BR/REQ候補、置換後の意味、未決事項、
再開条件及びmeaning ownerを明示した。NFR-1〜5/8は既存業務root候補から再降下、NFR-7は旧全経路1〜5秒一様乱数を
公式API/MCPのprovider quotaとPlaywrightの媒体別操作節度へ置換する。

有料経路のNFR-6は超後期までdeferredとし、顧客入金と事業支出を別ledger／policy／approvalへ分ける。NFR-9は対象事業、
jurisdiction、媒体operation及びdata categoryのstable BR/REQが未確定、NFR-10はVPS製品状態のdata classificationとRPO/RTOが
未確定、NFR-11は対象capabilityとstable REQ rootが未確定なため、いずれも再開条件付きdeferredとした。NFR-3の旧SQLite固定は
VPS製品状態正本からの再開性へ、NFR-5の「SQL 1本」はVPS UI read modelとinboxでの可観測性へ、NFR-4の平文env許容余地は
暗号化store又は有人一時注入へ置換する。

`G-REQ-LEGACY-NFR-DISPOSITION`は11件のexact coverage、実在BR/REQ、meaning owner、処置、deferred再開条件及び旧手段の
再混入を検査する。これは新NFR正本又は閾値の承認ではない。stable rootと未決thresholdを新BR/REQ/NFR/AC/TCへ再降下するまで
旧`nfr-contracts.json`は`revalidation_required`であり、`G-REQ-NFR-AUTHORITY`をredのまま維持する。

### F-50 stable root又は実装降下を欠く旧FR/SRの処置（構造解消、個別再降下未完）

旧FRではFR-17/35/48がstable REQとACを持ちながらFN/CMP未降下、FR-45/53/72/74〜77がstable REQ rootを持たず、
FR-73〜77はFN/CMP未降下だった。旧SR 19件は全件FNを持たず、SR-01〜05/12/15〜19はstable REQ rootもなく、
SR-17〜19はCMP/ACも持たなかった。これらFR 11件・SR 19件を`legacy_orphan_requirement_groups`へexact coverageで収載した。

Kanban／bounded domain／media bindingは新REQから再降下する。Notion及び音声・動画・EPUBはbusiness value、provider、license、
媒体operationが決まるまでdeferred、migrationはVPS製品状態・data classification・compatibility・rollback要求へ置換する。
FR-73は超後期金銭capabilityまでdeferred、FR-74/75はprofile/account lifecycleの人間判断とbinding preflightへ分け、FR-76/77は
VPS UI内inbox、権威read model、authentication/sessionへ置換する。

戦略core SR-01〜05/12/16はresearch、商品/offer capability、funnel、媒体役割、仮説、KPI還流からstable REQを新設して再降下する。
SR-06〜11/13/14は構文検査と企画・改訂・有効化の人間判断を分け、FN又は明示N/A、receipt付きAC及びauthority付きTCへ再降下する。
SR-15の旧S0最小集合は新baselineのinitial/follow-on/deferred scopeから置換する。SR-17〜19の高度分析は基本growth loopが成立し、
business value、data、手法境界及び判断principalが承認されるまでdeferredとする。

`G-REQ-ORPHAN-REQUIREMENT-DISPOSITION`は30 IDの過不足・重複、実在meaning owner、処置、root/descent action、deferred再開条件、
未承認・未設計境界及び旧Discord/API-only UI・旧S0・包括S3+・有料経路・高度分析の再混入を検査する。旧FR/SR契約の
trace/phase/descent自体は未変更なので、既存trace・phase・descent gateは新正本再降下までredを維持する。

### F-51 旧REQ 55件のID別処置と実現手段分離（構造解消、新REQ正本未生成）

旧`requirement-list_v0.1.md`と`canonical/req/req.json`は同じ55 IDを持つが、本文・source・relatedに実質差分があり、
片方を正本又は両方のunionとして採用できない。`legacy_req_disposition_groups`は55 IDをexact coverageし、レビュー可能な業務群へ
まとめながら、処置とdeferred再開条件をID単位で保持する。全groupは`candidate_unratified`かつ`design_not_started=true`である。

SQLite状態REQ-006/042はVPS製品状態正本へ、browser export→SQLiteのREQ-022はAPI/MCP優先＋必要時Playwrightへ、HTML dashboardの
REQ-024と一発SQL可観測性REQ-043はVPS Web UI/read modelへ置換する。connector順REQ-026は公式API/MCP優先＋Playwright fallback、
credential REQ-031は暗号化store又は有人一時注入、WP収束REQ-033は媒体operation別content authority、Claude Design REQ-035は
provider-neutral、WP REQ-036はcontent/platform/securityの別releaseへ置換する。

人間非介在REQ-037、Discord個別投稿承認/auto-mode REQ-038、異常通知REQ-039は、phase別人間判断、VPS UI初回scope activation、
content gate合格後の毎回承認なし自動運用、安全停止＋VPS UI内inboxへ置換する。全媒体browser乱数REQ-044はAPI/MCP quotaと
Playwright節度へ分離し、媒体一括稼働REQ-045は個別capability admissionまでdeferredとする。有料REQ-027、MMM REQ-021、xlsx
REQ-025、rich-media REQ-034も個別business valueと再開条件が成立するまでdeferredである。

`G-REQ-LEGACY-REQ-DISPOSITION`は55 IDの過不足・重複、group内item処置、deferred再開条件、meaning owner及び旧手段の再混入を
検査する。これはMD又はJSONの旧本文を変更・承認したものではない。POが各意味を選択した後、一つの新JSON正本からviewを生成し、
BR→REQ→FR/SR/NFRの双方向traceと12意味軸を再降下するまでsemantic drift及びtrace gateはredを維持する。

### F-52 旧BR 41件の事業価値と実現手段分離（構造解消、新BR正本未生成）

旧BRはactor/value/scope/HJ/evidenceを比較的多く持つが、SQLite、browser、HTML/xlsx、MCP→browser→paid、WP一律収束、
Claude Design、企画後の人間接点二つ限定、Discord個別投稿承認、旧auto-mode及び旧通知方式を事業価値と同じ契約へ固定していた。
`legacy_br_disposition_groups`はA〜Jの全41 IDをexact coverageし、ID別処置、保持する価値、置換policy及びmeaning ownerを明示した。

戦略/実行/検証loop、pair/evidence、research、profile、KPI、成果物trace、戦略還流、Kanban/domain/media binding等の事業価値は
再降下候補として保持する。一方、接続は公式API/MCP優先＋Playwright fallback、状態はVPS製品状態、表示はVPS Web UI、credentialは
暗号化store又は有人一時注入、design tokenはprovider-neutral、WPはcontent/platform/security別releaseへ置換する。BR-H1〜H3は
phase別人間判断、VPS UI初回activation、gate合格後の毎回承認なし自動運用、安全停止＋UI内inboxへ置換する。

`G-REQ-LEGACY-BR-DISPOSITION`は41 ID、個別処置、meaning owner、未承認・未設計境界及び重要な価値/手段分離を検査する。
これは旧BRのconfirmed receiptを書き換えるものではなく、新BR正本への再降下前の処置候補である。

### F-53 旧媒体BR 70件のcapability別処置（構造解消、全媒体write無効）

旧媒体BRは21媒体70 IDを持つが、媒体名、connection又は上位価値の存在だけではaccount/operation単位の外部作用を許可できない。
`legacy_media_br_dispositions`は全70 IDを媒体別exact coverageし、現候補でのfunnel role、route policy、meaning owner及び再開条件を持つ。
全行は`candidate_unratified`かつ`design_not_started=true`であり、個別capabilityのPO receiptとrelease受入まで外部writeは無効である。

Discordは製品通知・承認・開発PRと分離したcommunity marketingだけ、affiliateは商品/offerごとのowner・選定・差替え・内容変更authority
に従い権限不明なら変更しない。LINEはMessaging API第一、measurementはAPI/MCP優先＋必要時Playwright read確認、Xは公式API優先で
Playwright writeを規約上許可されたattended-only operationへ限定する。WordPressはcontent operationとplatform/security maintenanceを
別principal/policy/releaseへ分ける。Stripeの顧客charge/checkout/refundは事業支出台帳とは別のmoney policy/ledger/approvalが閉じるまで
deferredである。Play/PWA、有料生成、rich media、各social/distribution媒体も個別business valueとAC/TCまで再開しない。

`G-REQ-LEGACY-MEDIA-BR-DISPOSITION`は70 ID、媒体別処置、route、owner、再開条件及びDiscord/affiliate/GenAI/LINE/measurement/
Play/Stripe/WP/Xの重要境界を検査する。旧MR 54件も別inventoryで全件deferredのため、BR処置だけで媒体routeを有効化できない。

### F-54 旧FR 43件の現要求への処置（構造解消、再降下未完）

旧FR 43件は旧baselineでconfirmedだが、SQLite状態、Discord通知/個別承認、Claude Design、API-only UI、媒体一律route及び
複数phaseの責務を含むため、そのまま現要求へ採用しない。`legacy_fr_disposition_groups`は全43 IDをexact coverageし、各IDを
`redescent`、`replace`又は`defer`へ分類し、meaning owner、延期対象の再開条件、`candidate_unratified`及び
`design_not_started=true`を固定した。

主要な置換は、VPS製品状態、異常時の安全停止＋durable evidence＋VPS UI内inbox、公式API/MCP優先＋Playwright fallback/確認、
WP content/platform/security分離、VPS UI初回activation、暗号化credential、provider-neutral token、funnel KPIのVPS Web UI表示、
profile/account lifecycle、binding preflight及び認証/session付きread modelである。Notion同期、rich media及び支出は個別価値と
operation権限が確定するまでdeferredとする。affiliate等の商品変更は媒体一律可否ではなく、offerごとのowner、replaceable、
allowed alternatives及びfixed constraintsに従い、権限不明なら変更しない。

`G-REQ-LEGACY-FR-DISPOSITION`は全43 ID、個別処置、owner、deferred再開条件及び重要な置換語彙を検査する。この処置表は
新FR正本又は設計ではない。旧FRのslice/trace/意味差分、phase、semantic dimensions及びAC/TC降下の既存ゲートは引き続き赤であり、
個別refinementのPO凍結後に新FRへ再降下するまで実装入力にはならない。

### F-55 旧FN／AC／TCを現設計・受入証拠へ流用する境界（構造解消、再生成未完）

旧FN 61件、AC 252件及びTC 258件は旧要求から派生しており、上位FR/SR/NFR/MRの意味、phase、通知、承認、provider及び
媒体routeが置換対象である以上、IDが存在し旧試験が成功しても現要求の設計又は受入証拠にはならない。
`legacy_derived_contract_policy`は各kindの全stable ID集合をcountとdigestで固定し、処置を
`defer_until_parent_redescent`、statusを`legacy_revalidation_only`、`design_not_started=true`とした。

再利用には、親要求のPO receipt付きfrozen正本、actor/scope/HJ/side effect/evidence/phaseの再生成、FN→AC→TCの同一revision降下、
通知/承認/community/金銭operationのpurpose分離及び旧TC alias/draft STCの解消が必要である。
`G-REQ-LEGACY-DERIVED-CONTRACTS`は集合digestとこの境界を検査する。これは新FN/AC/TCの作成又は受入完了ではなく、
要求確定前に旧下位成果物から設計を逆算しないためのfail-closeである。

### F-56 新要求revision方式のPO未決境界（候補明示、未解決）

旧REQ Markdown/JSON及び旧requirements view/contractは同一IDで別意味を持つため、in-place書換えは旧receipt、trace及び
レビュー時点を曖昧にする。`authority_revision_candidate`は、新revisionの単一JSON正本、そこからのMarkdown生成、旧IDとの
supersedes mapping及び旧consumerの一括置換/historical隔離を推奨案として明示した。旧Discord、API-only UI、WSL、provider固定及び
旧phaseは自動移植しない。

ただしこれはPO未回答の選択肢であり、`po_decision=null`、`status=pending_po`、`design_not_started=true`を維持する。
`G-REQ-AUTHORITY-REVISION-CANDIDATE`は推奨案を自己承認せず、旧IDの書換え、authority cutover又は設計開始へ進まないことを検査する。

### F-57 目的別完了証拠と非完了境界（構造解消、新要求freeze未完）

`objective_completion_audit`は、全旧要求層の意味棚卸し、旧requirements consumer隔離、VPS UI/inbox要求、設計未着手及び
新要求正本freezeを別々に評価する。全件棚卸し、旧参照隔離及び設計未着手は対応するexact coverage/digest/consumer/design gateにより
`proven`とした。VPS UI/inboxは候補とdispositionまでで新BR/REQ/FR/NFRへの再降下がないため`incomplete`、新要求正本freezeは
revision方式と全refinementのPO receiptが未決のため`blocked_by_po`である。

`G-REQ-OBJECTIVE-COMPLETION-AUDIT`は証拠と残条件を検査し、棚卸し完了を要求完了、UI候補を実装済み、又は旧設計の隔離を
新設計完了へ読み替えることを拒否する。

## 要求完了の必要条件

1. F-01〜F-57を個別に解消又は要求候補へ束縛し、未解決findingにはquestion/answerとPO選択が
   discovery ledgerにappend-onlyで存在する。F-42のように機械隔離で解消したfindingへ不要なPO判断を要求しない。
2. BR/REQ/FR/SR/NFR/MR/FNの各責務がactor・価値・scope・禁止・人間判断・副作用・証跡で一致する。
3. 実行対象の各要求がAC/TCまで反証可能に降下し、未実装将来候補はdeferredと再開条件を持つ。
4. ADR-007/010/013、BR-H2/H3、フロント要求、通知/承認契約の時系列が一意になる。
5. 要求正本のPO承認・manifest digest・baseline・独立Goレビューが揃う。
6. 上記後にだけL2〜L6を新要求から再設計し、`implementation_authorized=true`にできる。

## 現時点の非完了事項

本監査は不整合の発見と要求完了条件の固定であり、仕様決定や設計完了ではない。
UI framework、認証、配備、API、画面、通知実装は未決定である。Discord community利用、Playwright、初回承認後の
自動運用、content gate及びresearch-led growthの方向は回答capture済みだが、個別refinementのPO承認、frozen cutover、
媒体operation別境界及びL2以降の設計は未完了である。
