---
artifact_id: L1-PRODUCT-REQUIREMENT-BASELINE-CANDIDATE
lifecycle_status: draft
slice: cross
---

# 製品要求ベースライン候補 v0.1

## 1. 位置づけ

本書は、VPS環境と製品フロントを前提に要求を再定義するための**承認前候補**である。
旧BR／REQ／FR／NFR／MR、L2〜L6、DDL、API、画面を実装入力として再利用せず、業務価値と
安全境界だけを先に固定する。本書単独では製品runtime移行、設計、実装、外部writeを許可しない。

開発環境と製品runtimeの配置基準はVPS `helix-worker`である。XServer API/CLI PoCでは、このVPSから
外部WordPress環境の払い出し、同期、保守、破壊再構築まで実証済みである。フロントの公開方式、
認証方式、UI技術は未設計であり、実行基盤の採用と設計詳細を混同しない。

## 2. 目的・actor・価値

| 項目 | 候補 |
|---|---|
| primary business actor | PO／許可された運用者 |
| beneficiary | 複数ブランドのマーケティング運用者とコンテンツ受領者 |
| primary task | 状態・失敗・証跡・承認待ち・KPIを確認し、人間判断が必要な操作を明示決定する |
| value | チャット製品や特定開発ツールに依存せず、安全に無人処理を監督できる |
| scope in | 製品状態閲覧、通知inbox、承認、停止／再開、許可済み外部操作の証跡 |
| scope out | 開発PR通知、要求正本編集、discovery編集、個人アカウント自動操作、未許可媒体write |

## 3. 設計に依存しない要求候補

### PRC-01 人間向け主入口

製品は、認証されたフロントを状態確認、承認待ち、失敗確認、KPI、運用通知の主入口として提供する。
structured feedbackの入力と適用scope指定、blocked成果物と検査・分類証跡の診断閲覧、activation取消もこの主入口で扱う。
特定のチャットサービス、Claude Code、Codex CLIを必須runtime依存にしない。

### PRC-02 状態の正本

フロントや通知transportは状態を独自保持・確定しない。製品API／永続状態を介し、対象、版、操作、
principal、期限、bindingを再検証した結果だけを正本状態へ反映する。

### PRC-03 通知と意思決定の分離

通知は「状態変化が発生したこと」と認証済みフロントへの導線だけを伝える。通知の受信、既読、
reaction、deep-link遷移だけではapprove、reject、再開、停止、公開を成立させない。

### PRC-04 通知経路

初期通知経路はフロント内inboxとする。Web Push／PWA Push／メール等の将来外部通知は個別採用する
任意adapterであり、同じ通知IDと製品状態を参照する。Discordは通知adapter候補から除外し、PRC-31の
community marketing媒体に限定する。外部通知失敗で業務状態をrollbackしない。

### PRC-05 Discord境界

Discordを製品の承認通知、運用通知又は開発PR通知に使用しない。DiscordはPRC-31の媒体community投稿だけに使用し、
製品UI内inbox及び他の将来通知adapterとprincipal／service／operation／endpoint／account／channel／policy category／
evidenceを共有しない。self-botと個人ユーザーaccountの無人操作は禁止する。

### PRC-06 人間判断

初回の自動運用activation、scope拡張、課金、有償経路、危険設定、重大なrule境界変更及び停止後の再開は、
対象と影響を再表示したうえで許可principalが明示決定する。activation後の個別投稿は毎回の人間承認を要求せず、
scope内でPRC-33〜35の機械gateに合格した場合だけ実行できる。基準評価の機械化を初回activation又は高リスク判断の
代替にせず、初回activationを個別成果物の品質合格の代替にしない。

### PRC-07 外部write閉集合

外部writeは媒体／能力単位で`enabled`、`attended-only`、`read-only`、`deferred`を宣言する。
`enabled`だけが明示allow-listと承認条件を満たした場合に実行できる。未分類、未知tuple、credential
scope不一致、期限切れ、証跡保存不能はfail-closeで拒否する。

### PRC-08 外部接続経路

無人処理は利用規約に適合する公式APIまたは公式MCPを第一経路とする。公式経路で必要能力を満たせない場合の
Playwright fallback及びbrowser確認はPRC-30のoperation別許可境界に従う。公式export又はattended manualも
operation capabilityとして登録する。consumer Web UIであることだけを理由に一律許可又は一律禁止せず、規約、
principal、effect、credential及び証跡が閉じないoperationは実行しない。

### PRC-09 生成AI経路

生成AIはproviderが許可する公式API／MCPを第一経路とする。Codex image generationは候補adapterであって
製品runtimeの必須条件ではない。Playwrightを含むbrowser routeはPRC-30に従い、provider／account／operationごとに
利用規約、principal、effect、credential、quota及びevidenceが閉じた場合だけ使用する。未分類又は失敗時はfail-closeする。

### PRC-10 profile隔離

認可境界は`business_profile`のstable IDとする。表示名としてのbrand、配下のbounded domain、媒体accountを
同一IDとみなさない。横断集約は個別profile権限を満たす別capabilityとし、credential・原データ・学習状態を
越境させない。

### PRC-11 通知証跡

UI内inboxへの記録と、将来の外部adapterによる配送を別結果軸にする。初期inboxは記録attemptごとの
`recorded`／`failed`と、retryを尽くした`retry_exhausted`をdurable evidenceに残す。将来の外部adapterを
採用する場合だけ、同じ通知IDに対して`attempted`／`delivered`／`failed`／`abandoned`を別の配送証跡として
追加する。通知ID、対象状態、adapter、宛先の非secret識別子、時刻、結果を保持し、inbox記録成立、外部配送成立、
業務状態成立のいずれも相互の成立条件又はrollback条件にしない。

### PRC-12 レート・quota

ブラウザ操作の人間様待機と、公式API／MCPのquota・rate limit・retry-afterを別契約にする。
provider capやaccount capを回避せず、制限情報が不明な経路は無人writeに使わない。

### PRC-13 要求trace

実装対象の各BR／REQ／FR／NFR／MRは、business actor、受益者、workflow、scope、禁止、人間判断、
external side effect、完了証跡、phaseを持ち、AC／TCまで双方向にtraceする。未決候補はdeferred理由と
再開条件を持ち、ID集合や件数一致だけで意味完備を主張しない。旧要求系10台帳の全864 IDは、各IDごとに
12意味軸、判断を所有するrefinement subject、`redescent`／`deferred`／`superseded`の処置を一意に持つ。
横断refinementの存在だけで個別IDを再検証済みとみなさず、判断subjectへ未接続のIDをauthority cutoverしない。

### PRC-14 要求からの再設計

本ベースライン承認後にL2以降を新規に降下する。旧画面、API、DDL、状態、slice、AC／TC、実装単位は
参考資料に限り、要求との意味一致が再証明されるまで実装入力にしない。

### PRC-15 初期通知capability

安全停止、承認待ち、実行失敗をVPS UI内inboxへ記録するcapabilityは初期範囲に含める。安全停止の成立と
通知配送を別責務へ分け、通知失敗でも停止状態をrollbackしない。初期adapterはUI内inboxだけとし、
Web Pushはdeferredとする。Discordは通知adapterとして採用せず、deferred又は再開条件を持たない。Discord community投稿は
通知capabilityへ含めず、PRC-31の独立媒体として
媒体release admissionで扱う。初期source event閉集合は`approval_waiting`、
`safety_stopped`、`execution_failed`とし、purposeは`action_required`又は`operational_alert`に分ける。
community media postとdeveloper PR noticeはこのinbox要求へ含めない。inbox itemは少なくとも通知ID、purpose、
source event identity、対象profile／resource／revision、発生時刻、severity、現在の業務状態、必要な人間判断の有無を
持つ。source event identity＋対象binding＋purposeが同じ重複は一つのitemへ収束させる。

通知記録は`recorded`又は`failed`の結果証跡を持ち、retryを尽くした場合は`retry_exhausted`を記録する。
`retry_exhausted`は通知記録の終端であり、source業務状態の解除、再開又は成功を意味しない。利用者別の
`seen`／`acknowledged`と、source業務状態に追随する
`resolved`／`expired`を別軸で扱う。`resolved`／`expired`はsource lifecycle、対象revision失効又はscope取消の正本eventだけから導出し、
未確認、時間経過、stale表示又はinbox記録失敗だけで`action_required`を失効させない。これらの通知状態をapprove／reject、停止後再開又は業務完了へ読み替えない。
inbox記録はprofile／purpose／risk class別の外部registrationへ束縛した有界retryとし、上限到達後はsource状態を維持して
`retry_exhausted`／`failed`証跡を残し、外部通知へfallbackしない。active sourceのitemは時間だけでarchive／purgeせず、
terminal後にだけretention、data classification及びlegal holdの有効revisionへ従う。policy不明時は不可逆削除をせず、
accessを制限して停止する。reminder／escalationは既定無効とし、明示登録時も同一itemの表示だけを変更してdecision、expiry、
停止解除、権限拡張又は別transportを導出しない。
inboxのlist／read／seen／acknowledgeは、principalが許可されたbusiness profile、resource及びoperation scopeへ
個別に束縛する。別profileのitem、secret、credential、個人情報又は不要なraw error payloadを表示せず、対応判断に
必要な最小情報と参照IDだけを提示する。認証済みであることだけを全inbox閲覧権限の代替にしない。
通知記録の失敗又はretryは先に成立した安全停止・実行失敗・承認待ちをrollbackしない。具体的なretry回数、
backoff、retention、resolved後の保持及び未確認itemのexpiry時間はPOの品質要求として未決のまま残し、実装者が
数値又は自動expiry可否を補完しない。FR-43又はPRC-33のquality gate blocked等の後続sourceは、そのsource要求のphase、
risk及び通知要否を個別に凍結してから閉集合へ追加する。

### PRC-16 フロントのセキュリティ要求

外部到達可能な製品フロントは通信の機密性・完全性と認証を必須とし、初期principalは明示登録されたPO／運用者に閉じる。
sessionは期限・失効・固定化及び盗用を防ぐ境界を持ち、状態変更はcross-site requestを含む不正要求の拒否と
直前の認可再検証を必須とする。attended-only operationの個別実行承認、課金、危険設定、auto-mode、停止後再開は
再認証可能な高リスク操作として扱う。具体protocol、identity provider、token保持方式、cookie属性値、timeout値、
reverse proxy製品は設計で決める。

VPSで使用するcredentialは暗号化してat-rest保護し、`0600`平文envを代替とみなさない。secret値をrepo、製品DB、log、
journal、service unit、argv、dump又はevidenceへ記録せず、契約と証跡はcredential参照IDだけを保持する。credential利用は
profile、媒体account及びoperationへ束縛し、必要な処理期間を超えて利用可能にしない。具体的な注入・保持方式は
設計へ留保する。test／productionのstore、principal及びscope tagを
分離する。credentialを製品状態backupへ含めず、喪失時は媒体側で再発行して再登録する。旧平文envに置かれたcredentialは
漏洩可能性ありとして単純移送せずrotateする。再起動後の無人unlockを許可するかが決まるまでは自動復旧を不成立として扱う。
具体secret backend、unlock方式及び注入mechanismは、この不変条件を満たす設計で選ぶ。

### PRC-17 責務とphase

`S1+`／`S3+`の包含表記を実装phaseに使わず、要求ごとに厳密な導入phaseと将来capability phaseを持つ。
安全停止／通知、媒体read／write、媒体登録／追跡などphaseが異なる責務は別IDへ分割する。単一FRへ
複数phaseを押し込まず、FN／AC／TCは対応責務と同じphaseへ接続する。

### PRC-18 生成AIと外部接続

製品runtimeはprovider-neutralな許可API adapterを第一経路とする。Codex image generation、Claude Design、
その他CLI／MCPは製品の必須依存にせず、採用時にprovider、能力、利用規約、quota、credential scopeを
登録したadapterとして扱う。公式API／MCP以外のrouteはPRC-30のoperation別Playwright fallback又は
attended manualとして明示登録し、未登録browser routeを拒否する。

### PRC-19 仕様化前の意味閉包

candidate時点ではunknownを許すが、各unknownは同一subjectのquestion eventを持たなければならない。
仕様化前に全questionを回答し、業務actor、受益者、workflow、scope in/out、permission、禁止、
human judgement、状態、例外、external side effect、通知class、完了証跡、security/privacy、accessibility、
performance、availability、recovery、observability、cost、legal、operation、migration、rollbackを
値または理由付きN/Aとして閉じる。

### PRC-20 rate／quota分類

ブラウザwriteの操作間隔、公式APIのprovider quota、read安全上限、課金上限、retry/backoffを別の型として
扱う。read操作にwrite用`rate_scope`を流用せず、必要なら`read_safety_cap`として根拠・期間・単位を持つ。
制限値不明、分類不明、retry-after無視、複数accountによるcap回避を拒否する。

### PRC-21 媒体追加契約

媒体追加はworkflowだけでなく、media binding、connector capability registry、playbook、policy tuple、
credential scope、quota、evidence、AC/TCのdata row追加で完了する。kernel codeの媒体分岐追加を禁止し、
不足artifactがある媒体をenabledにしない。

### PRC-22 人間判断のphase

通常ループ、初期setup、例外/escalation、governance、外部writeを別phaseとして数える。「通常ループの
人間接点2点」は他phaseの危険設定、migration、allow-list、停止後再開を省略しない。config変更は
低リスク自動、危険設定、secret、外部write許可に分類し、後3者は許可principalの明示判断を必須とする。

### PRC-23 traceと適用可能性

BR→REQ→FR/SR/NFR→AC→TCのtraceは要約ではなく、責務・phase・意味fieldの推移閉包として検査する。
同一IDの別台帳を並行正本にしない。旧confirmed成果物は承認履歴として保持しても、現要求baselineへの
`applicability=blocked/revalidation-required`を機械可読にし、単独閲覧・ゲート・agent導線から実装入力に
できないようにする。

### PRC-24 deferred capability

初期baseline外の媒体write、Web Push、横断BI、S2戦略分析、将来生成adapterは、理由、business
value、依存、risk、再開条件、必要な要求／AC／TCを持つdeferred itemとする。下流traceが空のまま
confirmed／enabled／implementation-readyを名乗らない。

### PRC-25 Full V-modelと媒体別段階release

本格system全体は現行HELIXのFull V-model（L1〜L12と正規V-pair）で要求から検証まで閉じる。媒体を
release unitとしてbacklog化し、その媒体内のread／publish／measure／community等を段階releaseする場合は、
作るものが概ね決定済みならProduction Scrum、Vモデルで設計を閉じて実装を反復するなら
`v_design_scrum_impl_hybrid`を使う。実現性又は成功条件が未知の場合だけDiscoveryを使い、Scrumと
Discovery/PoCを同義にしない。Scrum incrementは1 PLAN単位とし、S3の動作確認だけでは完了にしない。
POのS4判断後もScrum Reverse SR0〜SR4でFull V-modelへ戻し、release candidateのV-pairが閉じて初めて
完了とする。PoCと本番のaccount、
domain、data、credential、write policyを分離し、未検証経路を他媒体へ暗黙継承しない。

最初のrelease unitはWordPressを**コンテンツデータベースとして扱い、公開する能力**とする。登録・取得・
更新・stable識別・公開・公開証跡を含め、日常のコンテンツ運用を段階incrementで広げる。

WordPress運用、WordPress保守、セキュリティ保守は互いに分離したrelease unitとする。運用はコンテンツ公開、
リライト、メディアupload、固定ページ編集を含む。WordPress保守はWordPress本体のversion updateと随伴変更、
plugin導入・update、及びそれらの変更に起因する障害対応を含む。backup、smoke、互換性確認、rollbackは保守変更を
安全に行う検証・回復手段であり、コンテンツ運用へ分類しない。脆弱性、credential、権限、security patch、監査、
緊急判断はセキュリティ保守としてさらに分離する。それぞれactor、risk、停止条件、AC/TC、rollbackを個別に閉じる。
XServer PoCで実証済みの操作も、本要求の受入条件と本番principal／credential境界を満たすまでは自動的にenabledにしない。

### PRC-26 AGENT NEOのFull V再定義と第三段階

WordPress運用・保守の段階が閉じた後、固定したAGENT NEO sourceを入力に、AGENT NEOテーマを使うサイト構築全体を
現行HELIXのFull V-modelで要求から再定義する。既存theme、Core Plugin、REST操作、dry-run/apply/rollback、SEO、
監査機能の現在値はReverseのas-is evidenceであり、新要求の受入又は実装許可ではない。

サイト構築releaseと、AGENT NEO自体の改善・改修・version update releaseを分離し、後者を第三段階とする。
段階incrementを使う場合だけProduction Scrum又はV設計＋Scrum実装Hybridを用い、S4後にScrum Reverse SR0〜SR4と
V-pair closureを必須とする。MARKETING HARNESSとAGENT NEOはrepo、authority、credential、API contract、evidence、
review、release receiptを共有せず、別媒体の開発と並行しても一方のgreenを他方の受入に流用しない。

サイト構築releaseのcapability候補は、固定sourceの実装棚卸しから、(1) site identity／profile／対象package境界、
(2) FSE global styles・design token・theme設定、(3) template・template part・navigation、(4) pattern・block・section・
CTA・media、(5) page・post・taxonomy・menuのstable ID付き操作、(6) preview・dry-run・diff・apply・version・rollback、
(7) SEO metadata・schema・OGP・indexing、(8) consentを伴うmeasurement／tracking／export、(9) migration・import・
export、(10) accessibility・performance・i18n・privacy・security、(11) health・status・log・audit、(12) MARKETING
HARNESSが判断しAGENT NEOが検証済み決定論操作だけを実行するintegration境界、に分類してFull Vの要求候補へ
展開する。この一覧はas-is能力の棚卸しであり、個人／法人package、license／課金、Automation SEO、CRM、SNS、
外部API又は旧AI機能を新baselineへ採用する決定ではない。各分類の業務価値、actor、対象サイト、書込みprincipal、
失敗影響、受入順をPOが凍結するまでcapabilityをenabledにしない。

### PRC-27 WordPress責務の閉集合

WordPressの日常コンテンツ運用は、content stable IDを基準にした登録・取得・下書き・リライト・media upload・
固定ページ編集・preview・公開・公開済み更新・各操作証跡に限定する。削除、非公開化、履歴保持期間、版競合時の
解決は未決事項として別途閉じ、初期要求へ暗黙追加しない。

通常保守はWordPress coreのversion変更、pluginの導入／有効化／無効化／update、これらに伴うschema・設定・
互換性変更及び変更起因障害の調査・復旧とする。content operationの投稿承認、quota、credential又は
`content_publish` policyで保守変更を許可しない。変更前inventory・backup／restore proof・maintenance window・
互換性／smoke／regression・rollback判断・変更後inventoryを一つの保守receiptへ束縛する。

security保守は脆弱性評価、security patch、credential rotation、権限変更、監査、侵害疑い時の隔離・緊急停止／
復旧判断とし、通常保守の成功又はPOのcontent公開承認をsecurity承認の代替にしない。三領域はstable ID、actor、
principal、operation class、policy、再認証、停止条件、evidence、AC／TC、S4 receiptを共有しない。theme／Core Plugin
そのものの改善・改修・version updateはAGENT NEO第三段階へ送り、WordPress通常保守へ暗黙包含しない。

### PRC-28 要求定義から実装降下へのadmission

`requirements_defined`は要求の記述が存在することだけを表し、実装可能又は受入完了を表さない。各FR／SRは、
actor・価値・scope・禁止・人間判断・副作用・証跡・厳密phaseを凍結した後、FN・CMP・AC・system testへ双方向に
降下した場合だけimplementation candidateになれる。降下しない将来要求は`deferred`、理由、依存、risk、再開条件、
再検証するV-pairを持つ。ACだけ、又はdraft testだけが存在する状態をimplementation-readyと数えない。

旧9契約から生成するIR recordはすべて`revalidation_required`、未承認refinementは`proposal_only`としてconsumerへ渡す。
PO receipt付きfrozen revisionへauthority cutoverする前に、consumerがこれらを`current`へ読み替えることを禁止する。

### PRC-29 品質要求の業務根拠

各NFRはstable REQとBRへ逆traceし、守るactor／beneficiary、価値、scope、測定対象、閾値、phase、failure impact、
recovery、evidenceを持つ。要求文書の節、risk、MR、FR又は別NFRだけを根拠にconfirmedとしない。法規・privacy、
backup／recovery、account quotaのように業務根拠又は閾値が未確定の品質要求は、理由、依存、再開条件を持つ
`deferred`として扱い、AC／TCの存在だけで受入済みにしない。

### PRC-30 外部automationの実行経路

媒体operationは公式API又は公式MCPを第一経路とする。公式経路で必要な能力を満たせない場合に限り、
Playwrightをfallbackとして使用できる。また、公式経路で実行した結果を人間向け画面で確認するread経路にも
Playwrightを使用できる。許可は媒体全体ではなくaccount／operation単位とし、principal、read／write effect、
credential scope、利用規約、rate／quota、証跡、停止条件を持つ。credentialは可能な限りoperationに必要な最小権限とする。
媒体側credentialがより広い場合も製品側のoperation allow-list、実行前plan検査及び実行後receipt照合で権限を狭める。
browser readも登録済みaccount／operation／resource scopeに限定する。これらの強制を保証できないwriteは自動実行せず
`attended-only`又は`deferred`とする。経路又は権限が未知のoperationは実行しない。

### PRC-31 Discord community marketing

Discordは製品の承認通知、運用通知又は開発PR通知には使用しない。Discordを使用する場合はcommunity marketingの
独立媒体として扱い、Bot principal、guild／channel、投稿・応答・moderation等のoperation、policy、quota、
credential及び証跡を他用途と共有しない。self-bot又は個人user accountの無人操作を禁止する。旧FR-46／FR-76の
Discord通知tupleをcommunity投稿許可へ流用しない。

### PRC-32 初回承認後の自動運用

初期稼働時、activation要求はUI内inboxへ`approval_waiting`として記録する。承認操作自体はinbox itemでは成立させず、
認証済みUIで対象scopeとrevisionを再表示し、直前認可を再検証したうえでユーザーが明示決定する。承認後は毎回の公開承認を
要求しない。scope未指定のactivation要求は既定補完せず拒否する。activationはprofile、媒体account、operation、
activation policy revision、risk class体系及び必須risk gate集合へ束縛し、scope外、
失効、停止、重大な基準変更又は権限喪失時は自動運用を止める。個別成果物は人間承認の代わりにPRC-33〜35の
機械gateを通過しなければならず、activationを品質合格と読み替えない。campaign、funnel role、content purpose及び
risk classの適合はactivationとは独立して毎成果物でfail-close判定する。feedbackの適用scopeをprofile又は媒体へ広げても、
外部writeのactivation scopeは自動拡張しない。`attended-only` operationはactivation scope内でも個別実行承認を要し、
自動運用のwrite許可へ昇格しない。必須risk gate集合、risk境界又はactivation policyの変更は停止条件として機械判定し、
媒体account別又は個別feedbackの下位rule更新は停止条件にせず自動再検査だけをtriggerする。

### PRC-33 content quality gateとfeedback learning

成果物は人間確認又は公開へ進む前に、禁止語、表現、形式、型、根拠及び適用ruleをHELIX型の機械gate／lintで検査する。
不合格成果物は人間へ渡さず、自動再生成又は修正、再検査へ戻す。合格した成果物だけを次工程へ進める。ユーザーの
指摘は構造化ruleとして外部化し、identity、revision、scope、effective period、fixture、検査結果及びrollbackを持つ。
scope指定がないfeedbackは指摘対象の媒体accountだけへ適用し、暗黙に他account、全profile又は全媒体へ拡張しない。
rule有効化時は未公開・処理待ち・承認待ち成果物を自動再検査する。gate結果は少なくともverdict、reason code、適用rule
revision及び対象artifact／claimを機械可読に束縛する。再生成の回数、時間及び費用上限はversion付き外部設定とし、未知又は
上限到達時は未合格成果物を正式な人間確認又は次工程へ送らず`blocked`で停止し、VPS UI内inboxへ一件のdurable eventを記録する。停止成果物と検査証跡は必要時の診断閲覧
だけを許可し、公開承認の代替にしない。通常の不合格retryでは通知せず、inbox記録失敗でも`blocked`状態をrollbackしない。retry系列中は適用rule revisionを凍結し、rule更新は
新しいgate実行から適用する。

品質gateは単なる禁止語一致ではなく、対象audienceへの有用性、独自の情報・research・分析、主張と出典の対応、出典鮮度、
経験又は専門性の根拠、誇張しない見出し、読み手が目的を達成できる十分性を検査対象に含める。検索又は生成AI検索での露出は
成長KPIになり得るが、順位操作を主目的にした大量生成、query variationごとの低価値な量産、他sourceの要約だけで付加価値が
ない成果物を合格させない。

公開済み成果物は媒体operationがupdate-in-placeを明示対応する場合だけ監査し、修正版がgate合格した場合だけ自動更新する。
非対応又は能力不明の場合は通知、削除、非公開化、再投稿、訂正を含め何もしない。

### PRC-34 risk別content policy

content及びclaimを扱う領域のrisk classを判定する。人の健康、金融上の安定、安全又は社会の福祉・well-beingへ重大な影響を
与え得る領域をYMYL相当の高risk候補とし、低risk領域より厳格な根拠、出典鮮度、
専門性、誇大表現、断定、免責及び安全gateを適用する。ユーザーの好みはブランドへ固定せず、案件、成果物又はclaimごとに
case-by-caseで指定できるが、risk classが要求する法令・安全上の最低基準を弱めたり迂回したりできない。AIはrisk境界内で
ruleを更新できるが、分類根拠、変更差分、scope、fixture及び検査結果を証跡化する。不確実なrisk分類は低riskへ推測しない。
各artifact／claimはrisk class、分類確信度又は不確実性、分類根拠及び適用gate-set revisionを持つ。欠落又は不確実な場合は
全影響軸のYMYL相当を含む最高厳格度として扱い、再調査又は分類解決後の再検査まで正式な人間確認、次工程又は公開へ進めない。
停止成果物と分類証跡の診断閲覧は許可する。確信度閾値は固定値を要件へ埋め込まず、version付きruleとして外部化する。

### PRC-35 research-led growth loop

content制作前に市場需要、検索意図、競合、trend、媒体反応及び過去KPIをresearchし、source、取得時点、対象claim、鮮度及び
一次／二次情報の区別を持つ成長仮説を記録する。researchは既存情報の言い換えだけで終えず、対象audienceへ追加する独自価値、
経験、比較、検証又は分析を明示する。商品又はofferごとに
marketing funnelを定義し、媒体及び成果物へ一つ以上のfunnel段階、対象audience、役割、期待する次行動、次の接点及び
役割達成KPIを束縛する。一媒体が複数段階を担うことを許可する。全媒体を一律の売上で評価せず、段階間遷移、媒体間送客、
割当役割の達成度及び最終成果への寄与を評価する。公開後KPIを仮説の支持、棄却又は要再検証として次のresearch、企画、
funnel、ruleへ還流する。

商品又はofferは対象ごとにowner、選定可能性、差替え可能性、内容変更可能性及び許可operationを持つ。アフィリエイト等の
選定可能な商材は許可scope内で探索・比較・採用・差替えでき、変更不能な対象には変更操作を生成しない。権限不明時は既存対象を
変更せずcontent最適化に限定する。有料集客はfunnel上の将来候補として保持するが、初期・中期releaseでは無効とし、予算と
金銭操作境界を含む個別要求が承認される超後期releaseまでdeferredとする。

### PRC-36 媒体別ハーネス分離

各媒体は1つずつの独立したハーネスとして構成する。媒体別ハーネスは自媒体の承認境界、write境界、route policy、
credential scope及び証跡を自媒体のrefinementだけへ束縛し、複数媒体の承認・write境界を単一ハーネスへ暗黙に
混載しない。単一媒体ハーネスの失敗・停止・仕様変更は他媒体ハーネスの承認・運用状態へ波及させず、fail-closeで
自媒体側だけを停止する。対象媒体の閉じた一覧、媒体横断で共有する共通基盤（credential store・evidence・kernel等）の
範囲及びハーネス分離の境界線はPOが確定し、既存の共通ハーネス前提の要求候補は確定後に媒体別refinementへ再割当する。
媒体別分離を理由に承認境界、禁止事項又はfail-close規律を弱めない。

## 4. 決定receiptと未決中の安全側既定

この表は本書の一括承認対象ではない。`決定済み`は既存のPO receiptを参照する事実、`安全側既定`は
未承認中に外部作用を起こさない暫定挙動であり、要求採用を意味しない。各候補は対応refinement revisionを
個別にPOが承認して初めてfrozenへ進む。

| Decision ID | 問い | 状態／未決中のfail-close |
|---|---|---|
| PD-01 | 製品runtimeをVPSへ正式移行するか | **既存決定: ADR-007のPO receiptでVPS `helix-worker`を基準化。新baselineへの適用範囲は再検証中** |
| PD-02 | Web Pushを初期追加adapterに含めるか | **UI内inboxはADR-013で初期必須。安全側既定として外部Web Pushだけを無効化し、品質閾値とadapter採否はrefinement未凍結** |
| PD-03 | Discordを製品通知又はdeep-link補助に使用するか | **決定済み: 不採用。DiscordはPRC-31のcommunity marketing媒体だけに使用し、通知routeは再開条件を持たない** |
| PD-04 | 初期版でwriteを許可する媒体はどれか | **安全側既定: 新baselineでは全媒体write無効。Docker WPもPoC証跡からrelease受入へ別途昇格** |
| PD-05 | 初回activation後に毎回承認なしで自動運用するか | **回答capture済み: scope付き初回承認後は自動運用。未ratify中の安全側既定は外部write無効** |
| PD-06 | profile横断BIを初期範囲に含めるか | **安全側既定: 無効。単一profile候補もrefinement未凍結** |

安全側既定は無効化・停止のためだけに使い、採用済み機能、初期scope又は実装許可として読まない。
有効化には個別refinement、PO receipt、AC/TC、再設計を必要とする。

## 5. 本書で決めないこと

framework、component、URL、port、reverse proxy、認証protocol、session実装、CSRF方式、DB table、API、
screen ID、状態enum、retry回数、deployment topologyは設計事項である。要求承認前に選定しない。

## 6. 承認後の置換範囲

承認時はADR-007／010／013、BR／REQ／FR／SR／NFR／MR、FN、AC／TCを同一要求変更として整合させる。
その後にL2〜L6、DDL、API、test、manifest、baselineを再降下し、独立Goレビューと
`implementation_authorized=true`が揃うまで実装を開始しない。
