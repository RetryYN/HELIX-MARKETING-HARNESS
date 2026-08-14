<!-- GENERATED FILE — 編集禁止。正本は docs/00-authority/development/requirement-refinements.json。再生成 = python3 scripts/render_views.py -->

# 要求候補レビュー（refinement candidates）

> [!CAUTION]
> **提案専用の生成view。現行要求の正本・PO承認・設計・実装入力ではない。**  `requirements_baseline_status=revising` / `implementation_authorized=false`。
> 各候補は個別のPO receiptで承認・freezeされ、Full Vを再降下してauthority cutoverするまでcurrentにならない。本view全体を一括承認として扱わない。

> 集計: 候補 **36** 件 ／ approval receiptあり **0** 件 ／ 未承認 **36** 件。

## PO確認順（decision packets）

> packetは確認順をまとめるだけで、packet単位の一括承認は禁止。各subject revisionへ個別receiptを束縛する。

1. **RDP-REQUIREMENTS-AUTHORITY** — 新baselineの意味正本、意味軸継承、phase、NFR根拠、試験IDをどのrevisionへ凍結するか  対象: L0-NORTH-STAR-AUTHORITY-NORMALIZATION, REQ-AUTHORITY-NORMALIZATION, REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE, CONTRACT-SEMANTIC-DESCENT-V2, FR-SLICE-AUTHORITY-ALIGNMENT, NFR-BUSINESS-AUTHORITY, TEST-ID-AUTHORITY-ALIGNMENT, RATE-QUOTA-COST-AUTHORITY
2. **RDP-INITIAL-VPS-HUMAN-INTERFACE** — VPS Web UI＋UI inboxを初期主入口にし、安全停止、credential、品質、人間判断をどの要求境界で凍結するか  対象: VPS-UI-PRIMARY-HUMAN-INTERFACE, PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION, VPS-UI-AUTHENTICATION-SESSION, VPS-UI-INBOX-LIFECYCLE, FR-16-NOTIFICATION-BOUNDARY, VPS-UI-QUALITY-ATTRIBUTES, VPS-CREDENTIAL-SECURITY-BOUNDARY, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING, CONTENT-RISK-CLASSIFICATION, RESEARCH-LED-CONTENT-GROWTH
3. **RDP-WORDPRESS-PROGRAM-STAGE-1** — WordPress content operation、platform maintenance、security maintenanceをどの独立release境界と順序で凍結するか  対象: WORDPRESS-MAINTENANCE-BOUNDARIES, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE
4. **RDP-FOLLOW-ON-FULL-V** — 後続媒体、戦略、AGENT NEOのFull V releaseをどの順で再開するか  対象: OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, DISCORD-COMMUNITY-MARKETING-ROUTE, MEDIA-POC-SCRUM-RELEASE, STRATEGY-REQUIREMENT-ADMISSION, AGENT-NEO-HELIX-REDEFINITION, AGENT-NEO-SITE-BUILD-RELEASE, AGENT-NEO-PRODUCT-EVOLUTION-RELEASE
5. **RDP-DEFERRED-EXTERNAL-CAPABILITIES** — 初期scope外のDiscord、生成AI、旧媒体capabilityをdeferredのまま維持するか個別に再開するか  対象: AUTO-MODE-DECISION-AUTHORITY, DISCORD-MULTI-PURPOSE-BOUNDARIES, GENAI-EXECUTION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY

## 回答済み事項（要求へ再降下前）

> 会話から取得したPO判断の構造化snapshot。まだ個別refinement revision・approval receipt・freezeへ再降下していないため、設計・実装入力ではない。

- **POD-20260815-001** (`captured_unratified`): 外部automationは公式API又は公式MCPを第一経路とし、Playwrightをfallback及び実行結果のbrowser確認経路として使用する  既存subject=OFFICIAL-API-ROUTE-AUTHORITY, LEGACY-MEDIA-ADMISSION-INVENTORY ／ 新規要求subject=EXTERNAL-BROWSER-AUTOMATION-ROUTE ／ 未解決=媒体operationごとのPlaywright write許可範囲と利用規約境界
- **POD-20260815-002** (`captured_unratified`): Discordは製品通知経路には使用せず、コミュニティマーケティング媒体として使用する  既存subject=DISCORD-MULTI-PURPOSE-BOUNDARIES, LEGACY-MEDIA-ADMISSION-INVENTORY ／ 新規要求subject=DISCORD-COMMUNITY-MARKETING-ROUTE ／ 未解決=community operation、Bot principal、account/guild/channel、write範囲、quota、moderation、evidence
- **POD-20260815-003** (`captured_unratified`): 初期稼働はVPS UI内inboxで通知してユーザーが承認し、その後は毎回承認せず自動稼働できる  既存subject=AUTO-MODE-DECISION-AUTHORITY, VPS-UI-INBOX-LIFECYCLE, BUSINESS-PROFILE-AUTHORIZATION ／ 新規要求subject=AUTOMATED-PUBLISHING-ADMISSION ／ 未解決=activation approvalのprofile/media/account/operation scope、期限、取消、基準失効時の復帰
- **POD-20260815-004** (`captured_unratified`): 禁止語、表現、型等をHELIX型gate/lintで検査し、不合格成果物は人間確認前に自動でやり直し、合格品だけを人間確認へ送る  既存subject=CONTRACT-SEMANTIC-DESCENT-V2, AUTO-MODE-DECISION-AUTHORITY ／ 新規要求subject=CONTENT-QUALITY-GATE-LEARNING ／ 未解決=再生成上限、解消不能時の停止/通知、検査class、合格基準のauthority
- **POD-20260815-005** (`captured_unratified`): ユーザーフィードバックへ即座に対応し、構造化規則として保存する。適用範囲を明示指定でき、指定がない場合は指摘対象の媒体accountを既定scopeとする  既存subject=VPS-UI-INBOX-LIFECYCLE, PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION ／ 新規要求subject=CONTENT-QUALITY-GATE-LEARNING ／ 未解決=全体共通化の権限、規則競合、rollback、誤検知時の解除
- **POD-20260815-006** (`captured_unratified`): content check規則は運用変更を前提とし、製品コードへ埋め込まず外部化された構造化データとしてversion管理する。成果物及びclaimが扱う領域のrisk分類を上位rule setとし、YMYL等の高risk領域はより厳格な根拠・表現・更新性・安全検査を要求する。ユーザーの好みはブランドへ固定せず、案件・成果物・claimごとにcase-by-caseで指定できる。AIはrisk境界内で媒体account別及び個別scopeの下位規則を更新できる。新revisionの有効化時は対象scopeの未公開成果物を自動再検査する。公開済み成果物は媒体operationがupdate-in-placeを明示対応する場合だけ自動監査・修正・更新し、非対応時は通知を含め何もしない  既存subject=PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION, AUTO-MODE-DECISION-AUTHORITY ／ 新規要求subject=CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING ／ 未解決=risk classの分類軸と段階、YMYL境界、個別の好みが未指定の場合の継承元、AI分類の不確実時挙動、変更前検証、effective timing、競合優先順、rollback条件
- **POD-20260815-007** (`captured_unratified`): content運用は制作前のresearchを必須前提とし、市場需要、検索意図、競合、trend、媒体上の反応及び過去実績から成長仮説を作る。媒体の役割は対象商品又はofferのmarketing funnel上で担う段階と次段階への送客責務によって決まり、成長の第一基準は全媒体共通の売上ではなく、そのfunnel上の役割達成度とする。商品又はofferへの操作可能性は扱う対象ごとに異なり、アフィリエイト商材の選定又は差替え、自己商品の改善提案、変更不能な第三者商材等を同一権限として扱わない。成果物はその仮説、媒体役割、適用risk基準及びcase-by-caseのユーザー嗜好を満たすよう生成し、公開後のKPI結果を次のresearch、企画、funnel及び媒体間導線、rule及び仮説へ還流して継続的に伸ばす。有料集客はfunnel上必要になり得る将来scopeとして保持するが、初期及び中期releaseから除外し超後期までdeferredとする  既存subject=STRATEGY-REQUIREMENT-ADMISSION, PRODUCT-STATE-AUTHORITY ／ 新規要求subject=RESEARCH-LED-CONTENT-GROWTH, CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING ／ 未解決=商品又はoffer種別ごとの具体operationとauthorityは対象登録時に解決する／役割別KPIと閾値、複数役割が競合する場合の優先順位、段階間及び媒体間寄与の評価窓、research freshness、仮説の評価期間、探索と既知勝ち筋の配分、KPI悪化時の停止条件、有料集客の再開条件は超後期releaseまでdeferred

## PRC意味所有者

> baseline候補の各PRCを、意味を閉じるrefinement subjectへ束縛する。PRC本文だけを単独で承認・設計入力化しない。

- **PRC-01**: VPS-UI-PRIMARY-HUMAN-INTERFACE
- **PRC-02**: PRODUCT-STATE-AUTHORITY
- **PRC-03**: VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE
- **PRC-04**: VPS-UI-INBOX-LIFECYCLE
- **PRC-05**: DISCORD-COMMUNITY-MARKETING-ROUTE
- **PRC-06**: AUTOMATED-PUBLISHING-ADMISSION, CONTRACT-SEMANTIC-DESCENT-V2
- **PRC-07**: LEGACY-MEDIA-ADMISSION-INVENTORY, WORDPRESS-MAINTENANCE-BOUNDARIES
- **PRC-08**: OFFICIAL-API-ROUTE-AUTHORITY
- **PRC-09**: GENAI-EXECUTION-ROUTE
- **PRC-10**: BUSINESS-PROFILE-AUTHORIZATION
- **PRC-11**: VPS-UI-INBOX-LIFECYCLE
- **PRC-12**: RATE-QUOTA-COST-AUTHORITY
- **PRC-13**: CONTRACT-SEMANTIC-DESCENT-V2, REQ-AUTHORITY-NORMALIZATION
- **PRC-14**: CONTRACT-SEMANTIC-DESCENT-V2, FR-SLICE-AUTHORITY-ALIGNMENT
- **PRC-15**: FR-16-NOTIFICATION-BOUNDARY, VPS-UI-INBOX-LIFECYCLE
- **PRC-16**: VPS-UI-AUTHENTICATION-SESSION, VPS-CREDENTIAL-SECURITY-BOUNDARY
- **PRC-17**: FR-SLICE-AUTHORITY-ALIGNMENT
- **PRC-18**: OFFICIAL-API-ROUTE-AUTHORITY, GENAI-EXECUTION-ROUTE
- **PRC-19**: REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE
- **PRC-20**: RATE-QUOTA-COST-AUTHORITY
- **PRC-21**: LEGACY-MEDIA-ADMISSION-INVENTORY
- **PRC-22**: CONTRACT-SEMANTIC-DESCENT-V2, AUTOMATED-PUBLISHING-ADMISSION
- **PRC-23**: L0-NORTH-STAR-AUTHORITY-NORMALIZATION, REQ-AUTHORITY-NORMALIZATION, CONTRACT-SEMANTIC-DESCENT-V2
- **PRC-24**: AUTO-MODE-DECISION-AUTHORITY, DISCORD-MULTI-PURPOSE-BOUNDARIES, GENAI-EXECUTION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY, STRATEGY-REQUIREMENT-ADMISSION
- **PRC-25**: MEDIA-POC-SCRUM-RELEASE, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE
- **PRC-26**: AGENT-NEO-HELIX-REDEFINITION, AGENT-NEO-SITE-BUILD-RELEASE, AGENT-NEO-PRODUCT-EVOLUTION-RELEASE
- **PRC-27**: WORDPRESS-MAINTENANCE-BOUNDARIES, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE
- **PRC-28**: CONTRACT-SEMANTIC-DESCENT-V2, FR-SLICE-AUTHORITY-ALIGNMENT, TEST-ID-AUTHORITY-ALIGNMENT, STRATEGY-REQUIREMENT-ADMISSION
- **PRC-29**: NFR-BUSINESS-AUTHORITY, VPS-UI-QUALITY-ATTRIBUTES
- **PRC-30**: EXTERNAL-BROWSER-AUTOMATION-ROUTE
- **PRC-31**: DISCORD-COMMUNITY-MARKETING-ROUTE
- **PRC-32**: AUTOMATED-PUBLISHING-ADMISSION
- **PRC-33**: CONTENT-QUALITY-GATE-LEARNING
- **PRC-34**: CONTENT-RISK-CLASSIFICATION
- **PRC-35**: RESEARCH-LED-CONTENT-GROWTH

## 旧L0 clause disposition候補

> charter v0.4の旧承認履歴は変更せず、事業価値と旧実現手段を分離して新PRCへ移す候補。全行`candidate_unratified`であり、PO receiptまでは現行L0又は設計入力にならない。

| clause | 旧意味 | 処置 | 維持する価値 | replacement PRC | 再開条件 |
|---|---|---|---|---|---|
| `L0V04-PURPOSE`<br>marketing-harness-charter_v0.4 §1-2 | 一人又は小規模運用でも戦略から実行と学習まで一貫して回し事業を成長させる | `retain` | 事業成長、運用負荷低減、学習還流という目的を維持する | PRC-25, PRC-35 | — |
| `L0V04-DUAL-LOOP`<br>marketing-harness-charter_v0.4 §3 | 戦略loopと実行loopを分離し証跡を介して双方向に学習する | `retain` | 戦略正本を実行結果から直接書換えず学習packetで還流する価値を維持する | PRC-13, PRC-25, PRC-35 | — |
| `L0V04-MEDIA-PARALLEL`<br>marketing-harness-charter_v0.4 §3 媒体並走 | 媒体を独立release unitとして並走させfunnel上の役割で接続する | `replace` | 媒体ごとの独立運用は維持し、固定媒体一覧ではなくcapabilityとfunnel役割で採否する | PRC-07, PRC-13, PRC-24, PRC-25, PRC-35 | — |
| `L0V04-PWA-PLAY`<br>marketing-harness-charter_v0.4 §3 App系 | PWAを主、Google Playを従として初期媒体scopeへ固定する | `defer` | app面の価値仮説だけ保持し初期媒体採用は行わない | PRC-24, PRC-25 | funnel上のbusiness value／媒体operation capability／release受入とAC/TC |
| `L0V04-HUMAN-AI`<br>marketing-harness-charter_v0.4 §4 | 外部公開を経過措置の毎回承認から機械判定による完全自動へ移す | `replace` | 高risk判断は人間に残し通常成果物は初回scope承認とquality/risk gateで自動化する | PRC-06, PRC-22, PRC-32, PRC-33, PRC-34 | — |
| `L0V04-PILLARS`<br>marketing-harness-charter_v0.4 §5 | 戦略、制作、配信、計測、改善を横断する事業能力を柱として持つ | `retain` | 個別providerや媒体ではなくresearch、funnel、content、delivery、measurement、learningの価値として維持する | PRC-13, PRC-25, PRC-28, PRC-35 | — |
| `L0V04-CONSUMER-WEB-AUTOMATION`<br>marketing-harness-charter_v0.4 §6 制作stack | 保有accountのconsumer Web UIをbrowser自動化しAPI課金を避ける | `replace` | 必要能力を費用と規約の範囲で確保する価値は維持し、API/MCP優先とoperation別Playwright fallbackへ置換する | PRC-08, PRC-09, PRC-12, PRC-18, PRC-30 | — |
| `L0V04-CONNECTOR-PRIORITY`<br>marketing-harness-charter_v0.4 §6 外部接続 | MCPからbrowser、有償APIの固定優先順を全媒体へ適用する | `replace` | 低costで許可された経路を選ぶ価値は維持し、公式API/MCP優先とoperation別能力判定へ置換する | PRC-07, PRC-08, PRC-12, PRC-18, PRC-30 | — |
| `L0V04-CLAUDE-DESIGN`<br>marketing-harness-charter_v0.4 §6 Design System | Claude Designを全制作物の必須token正本にする | `replace` | 一貫したdesign tokenと変更証跡の価値を維持しprovider-neutral capabilityへ置換する | PRC-09, PRC-13, PRC-18 | — |
| `L0V04-BROWSER-MEASUREMENT`<br>marketing-harness-charter_v0.4 §6 計測/SNS | browser export及びbrowser突破を計測とSNSの一般経路にする | `replace` | 計測と媒体運用を自動化する価値を維持し公式route優先、Playwrightはoperation別許可へ限定する | PRC-08, PRC-12, PRC-18, PRC-30, PRC-35 | — |
| `L0V04-FULL-V`<br>marketing-harness-charter_v0.4 §7 | HELIX V-modelとsliceによって要求から受入まで閉じる | `retain` | Full Vと媒体別段階releaseを維持し、requirements_definedを設計完了又は実装許可とみなさない | PRC-13, PRC-14, PRC-25, PRC-28 | — |
| `L0V04-RUNTIME`<br>marketing-harness-charter_v0.4 §8 | 開発workspaceと製品runtimeの境界及び配置を定める | `replace` | 開発環境と製品runtimeの分離を維持し、製品runtimeとhuman interfaceをVPSへ置く | PRC-01, PRC-02, PRC-10, PRC-16, PRC-18 | — |
| `L0V04-DISCORD-APPROVAL`<br>marketing-harness-charter_v0.4 §10 Discord初期承認 | 個人Discord Appを初期の投稿可否承認入口にする | `replace` | 人間が対象を確認して高risk判断する価値を維持し、VPS UI内inboxと認証済みUI操作へ置換する | PRC-01, PRC-03, PRC-04, PRC-05, PRC-15, PRC-16, PRC-32 | — |
| `L0V04-DISCORD-COMMUNITY`<br>marketing-harness-charter_v0.4 §10 Discord媒体 | Discordを通知でなくcommunity marketing媒体として扱う | `retain` | community媒体としての価値を維持し通知用途とcredential/policy/evidenceを分離する | PRC-05, PRC-24, PRC-31, PRC-35 | — |
| `L0V04-AUTO-MODE`<br>marketing-harness-charter_v0.4 §10 auto-mode | 安定稼働証跡だけで人間承認なしの公開へ段階移行する | `replace` | 通常公開の自動化は維持し、初回scope activation、成果物gate、停止時re-activationへ置換する | PRC-06, PRC-22, PRC-32, PRC-33, PRC-34 | — |

## 旧critical responsibility disposition候補

> 旧BR／FRの通知・承認・自動運用・UI責務をそのまま再利用せず、現要求のmeaning ownerへ分割する候補。旧契約のconfirmed履歴は変更せず、全行を未承認・未設計として扱う。

| legacy ID | 旧意味 | 処置 | 維持する責務 | 置換責務 | meaning owner | 継承禁止 |
|---|---|---|---|---|---|---|
| `BR-H2`<br>br-contracts.json BR-H2 | 初期Discordで全公開を束縛承認し、安定後のauto-mode移行をPOが最終承認する | `split` | 外部write開始scopeと停止後再開はユーザーが明示判断し、通常運用は合格済み成果物だけ自動化する | VPS UIで媒体account・operation・scopeを初回activationする／content gate合格済み成果物だけ毎回承認なしで自動公開する／取消・権限喪失・scope外・重大rule変更・停止条件では停止し明示re-activationを要求する | VPS-UI-PRIMARY-HUMAN-INTERFACE, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING | Discordを通知又は承認transportにする／機械criteriaだけでactivation又はre-activationを確定する／通常投稿を毎回人間承認へ戻す |
| `BR-H3`<br>br-contracts.json BR-H3 | 異常・停止・失敗を即時通知する | `replace` | ユーザーが対応すべき状態変化を製品内で確認でき、原因・影響scope・現在状態・可能な操作を追跡できる | VPS UI内inboxへ目的付きoperational eventを記録する／通知表示と意思決定操作を別責務にする／community媒体及び開発PR通知と資格情報・policy・evidenceを共有しない | VPS-UI-INBOX-LIFECYCLE, FR-16-NOTIFICATION-BOUNDARY | Discord通知／ApprovalTransport再利用／通知到達を状態変更又は承認決定とみなす |
| `FR-16`<br>fr-contracts.json FR-16 | 監視異常を停止しFR-46の承認通知経路へ送る | `split` | 異常をfail-closeで検出し影響scopeを安全停止して証跡化する | safety-stopとdurable failure evidenceを生成する／binding subjectを要求しないoperational inbox eventを別途生成する／解消不能又は人間判断が必要な場合だけUI上の許可操作を提示する | FR-16-NOTIFICATION-BOUNDARY, VPS-UI-INBOX-LIFECYCLE | FR-46 ApprovalTransport呼出／Discord channel固定／通知失敗を安全停止失敗へ結合する |
| `FR-43`<br>fr-contracts.json FR-43 | repair失敗をFR-46経路で通知する | `split` | repair試行・結果・停止理由を証跡化し安全側状態を維持する | repair lifecycleとfailure evidenceを保持する／対応が必要なfailureだけoperational inbox eventへ射影する／再試行・停止継続・明示再開の許可境界を分ける | FR-16-NOTIFICATION-BOUNDARY, VPS-UI-INBOX-LIFECYCLE, AUTOMATED-PUBLISHING-ADMISSION | FR-46 ApprovalTransport呼出／Discord通知／repair失敗から暗黙に外部writeを再開する |
| `FR-46`<br>fr-contracts.json FR-46 | Discord App interactionで投稿可否を束縛承認し、auto-modeでは機械criteriaで承認を省略する | `replace` | 外部writeの許可scopeと対象operationを誤結合せず、ユーザー判断と機械gateを証跡化する | VPS UIで初回activation・scope拡張・高risk例外・停止後再開を判断する／機械gateは成果物合格と停止条件を判定しユーザーactivationを代替しない／通常投稿はactivation scope内かつgate合格時だけ毎回承認なしで進める | VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-AUTHENTICATION-SESSION, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING | channel=discord固定／Discord interactionによるapprove/reject／個別投稿の毎回承認／機械criteriaだけのauto-mode移行 |
| `FR-75`<br>fr-contracts.json FR-75 | brand・media・account台帳から誤投稿をpreflightで自動拒否する | `split` | profile・媒体account・operation・成果物のbinding不一致を外部write前に機械拒否する | business profileと媒体accountの登録・変更・廃止をユーザーauthorityへ束縛する／activation scope内のbindingをpreflightで検査する／不一致時は停止し別profile又は別accountへ自動付替えしない | BUSINESS-PROFILE-AUTHORIZATION, AUTOMATED-PUBLISHING-ADMISSION, PRODUCT-STATE-AUTHORITY | preflight成功をprofile追加・廃止又はactivationの承認とみなす／不一致対象への自動付替え／停止後の暗黙再開 |
| `FR-76`<br>fr-contracts.json FR-76 | ApprovalTransport同型のDiscord経路でoperational notificationを配送する | `replace` | 運用上対応すべきeventを目的・対象scope・状態・証跡へ束縛してユーザーへ提示する | 初期capabilityはVPS UI内inboxのdurable operational eventとする／read・acknowledge・resolve又は必要な許可操作を別状態として追跡する／将来の外部通知adapterは個別refinementが承認されるまでdeferredとする | VPS-UI-INBOX-LIFECYCLE, FR-16-NOTIFICATION-BOUNDARY | Discord transport／ApprovalTransport同型tuple／community投稿又は開発PR通知とのcredential・policy共有 |
| `FR-77`<br>fr-contracts.json FR-77 | evidenceと状態をread-only APIだけで提供しWeb UIを対象外とする | `split` | 状態・停止理由・証跡・KPIを権限境界内で改変せず閲覧可能にする | read model又はAPIの改変禁止・profile隔離責務を維持する／VPS Web UIを人間向け主入口として同じ権威データを表示する／UIの認証・session・再認証・scopeを別要求で閉じる | VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-AUTHENTICATION-SESSION, PRODUCT-STATE-AUTHORITY | Web UI対象外／APIの存在をUI認証・認可の代替とみなす／表示用read modelから正本状態を直接更新する |

## 意味降下policy候補

> BRからTCまで意味fieldを散文から推測せず、直接宣言又はsource revision/digest付き継承で閉じる。FN→CMP→DUは要求freezeまでblockedであり、この表は設計成果物ではない。

| 意味軸 | mode | 規則 |
|---|---|---|
| `actors` | `direct_required` | 各責務の実行principal、判断principal及び状態ownerを対象層で直接宣言する |
| `beneficiaries` | `explicit_inheritance_or_direct` | 上位受益者を維持する場合もsource digestへ束縛し、対象層で変化する受益者を追加する |
| `value` | `explicit_inheritance_or_direct` | 下位責務が上位価値へどう寄与するかを明示し、技術手段を価値の代用にしない |
| `tasks` | `direct_required` | 対象層が責任を持つtaskと持たないtaskを直接宣言する |
| `workflow` | `direct_required` | 入力、判断、状態遷移、外部作用及び失敗経路を対象層で直接宣言する |
| `scope_in` | `direct_required` | profile、媒体account、operation、resource及びphaseの対象範囲を直接宣言する |
| `scope_out` | `direct_required` | 隣接責務、将来capability及び禁止対象を直接除外する |
| `prohibitions` | `inherit_plus_local` | 上位禁止を弱めず全て継承し、対象層固有の禁止を追加する |
| `human_judgement` | `direct_required` | 判断principal、対象、選択肢、scope、失効、receipt及び機械判定との境界を直接宣言する |
| `side_effects` | `direct_required` | DB状態、外部write、金銭、credential、通知及び証跡への作用を直接宣言する |
| `evidence` | `direct_required` | 成功、拒否、境界、判断receipt、外部作用receipt及びfailure evidenceを直接宣言する |
| `phase` | `direct_required` | 導入phaseを一意に宣言し、inclusive slice又はtarget_updateで代用しない |

| edge | source → target | admission | 規則 |
|---|---|---|---|
| `SED-BR-REQ` | BR → REQ | `requirements_candidate` | REQはBRの要約行ではなく、業務価値と境界を保持したstable requirementとして再構成する |
| `SED-BRM-MR` | BRM → MR | `requirements_candidate` | 媒体routeはcapability、execution mode、principal、effect、policy、credential、quota及びadmissionを明示し、旧connection proseから許可を推測しない |
| `SED-REQ-FR` | REQ → FR | `requirements_candidate` | 機能責務は一つの業務目的とphaseへ分割し、上位判断を機械処理へ置換しない |
| `SED-REQ-SR` | REQ → SR | `requirements_candidate` | 戦略責務はstable REQ rootと判断principalを持ち、別agent審査を人間判断の代替にしない |
| `SED-REQ-NFR` | REQ → NFR | `requirements_candidate` | 品質要求はstable業務根拠、測定、閾値、failure、recovery、残余risk及びdeferred条件を持つ |
| `SED-REQUIREMENT-FN` | FR, SR, NFR, MR → FN | `requirements_candidate` | FNは実現責務を一意phaseへ分割し、複数上位責務又は複数phaseを暗黙に束ねない |
| `SED-REQUIREMENT-AC` | FR, SR, NFR, MR → AC | `requirements_candidate` | ACはpositive、negative、boundaryでprincipal、scope、判断receipt、許可作用及び禁止作用を反証可能にする |
| `SED-AC-TC` | AC → TC | `requirements_candidate` | TCはACの意味digestと同じscope、principal、side effect、evidence及びphaseを検証し、旧ID又はdraft oracleを参照しない |
| `SED-FN-CMP` | FN → CMP | `blocked_until_frozen_requirements` | 要求freeze後にだけcomponent責務へ降下し、要求未確定fieldを設計者が補完しない |
| `SED-CMP-DU` | CMP → DU | `blocked_until_frozen_requirements` | 要求及び基本設計freeze後にだけ詳細設計へ降下し、旧DU/API/TCを新要求の完了証拠へ流用しない |

## 旧NFR disposition候補

> 旧測定文やAC/TCの存在だけでは現baselineの品質要求にならない。業務根拠、actor、scope、置換意味及び再開条件をNFRごとに記録する。

| NFR | 処置 | stable root | 業務価値 | 置換後の意味 | 未決／再開条件 | owner |
|---|---|---|---|---|---|---|
| `NFR-1` | `redescent` | BR-B4, REQ-040 | 判定不能又は未分類の操作を安全側で拒否し、禁止経路から利用者と事業を守る | 各gate classでunknown、invalid、unclassified及び検査不能を拒否し、無効化経路を持たない。具体fixtureと閾値は対象gate要求へ降下する | 対象gate class一覧／停止後の回復principal／残余risk | NFR-BUSINESS-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `NFR-2` | `redescent` | BR-B3, REQ-041 | 同じ承認済み入力と規則revisionから再現可能な判断・証跡を得る | 決定的にすべきkernel判断と非決定なresearch/生成結果を分離し、後者はsource、時点、provider、input/output digestへ固定する | 決定性を要求するoperation一覧／許容する非決定入力／再実行比較窓 | NFR-BUSINESS-AUTHORITY, CONTENT-QUALITY-GATE-LEARNING, RESEARCH-LED-CONTENT-GROWTH |
| `NFR-3` | `redescent` | BR-A1, BR-I7, REQ-042, REQ-052 | 停止や再起動があっても業務状態と外部作用を失わず二重実行を避ける | SQLiteという旧手段ではなくVPS製品状態正本からの再開性を要求し、外部作用ごとに証跡先行、照合、未知時停止及び再開principalを持つ | 状態種別／RPO/RTO／operation別idempotency／未知結果の解消authority | NFR-BUSINESS-AUTHORITY, PRODUCT-STATE-AUTHORITY, AUTOMATED-PUBLISHING-ADMISSION |
| `NFR-4` | `redescent` | BR-F4, REQ-031 | 媒体及び外部serviceの資格情報漏洩と越境利用を防ぐ | 平文env fileを許可せず、暗号化store又は有人一時注入、最小scope、runtime限定復号、非記録、rotation、失効及び監査を要求する | credential class／保管principal／rotation周期／break-glass／復旧方法 | NFR-BUSINESS-AUTHORITY, VPS-CREDENTIAL-SECURITY-BOUNDARY, BUSINESS-PROFILE-AUTHORIZATION |
| `NFR-5` | `redescent` | BR-H3, REQ-043 | ユーザーがVPS UIから現在状態、停止理由、影響scope及び必要な対応を把握できる | 一つのSQLという旧実装条件ではなく、権威状態から一貫したread modelを提供し、VPS UI内inboxと証跡へ目的・scope・correlationを保って表示する | freshness／保持期間／欠測表示／集約scope／可用性閾値 | NFR-BUSINESS-AUTHORITY, VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE, PRODUCT-STATE-AUTHORITY |
| `NFR-6` | `defer` | BR-F1, REQ-027 | 有料経路の支出をユーザーの許可予算内へ限定する | 有料集客を含む金銭operationは超後期capabilityとし、顧客入金と事業支出を別台帳・別policy・別approvalへ分離する | 対象operation／通貨／月次/案件別cap／返金／税／予算超過時挙動<br>再開: 超後期releaseのbusiness valueが承認される／金銭operation種別とledgerが分離される／予算principal、cap、credential、AC/TC及び停止条件が凍結される | NFR-BUSINESS-AUTHORITY, RATE-QUOTA-COST-AUTHORITY |
| `NFR-7` | `replace` | BR-F5, REQ-044 | 外部serviceの利用規約、rate limit及びaccount健全性を守り、過剰操作を防ぐ | 旧1〜5秒一様乱数を全経路へ強制せず、公式API/MCPのprovider quotaとPlaywrightの媒体別操作節度を別ruleとして外部化する | service/account/operation別rate／provider retry-after／browser pace／停止/再開条件 | NFR-BUSINESS-AUTHORITY, RATE-QUOTA-COST-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, OFFICIAL-API-ROUTE-AUTHORITY |
| `NFR-8` | `redescent` | BR-F3, REQ-030 | 媒体追加をkernel分岐の増殖ではなく検証可能なcapability登録として安全に行う | 単なるデータ行追加ではなく、必要な意味fieldと検証を閉じたcapability追加だけを外殻変更なしで受入れる | capability schema／connector plugin境界／互換性／rollback／release acceptance | NFR-BUSINESS-AUTHORITY, LEGACY-MEDIA-ADMISSION-INVENTORY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `NFR-9` | `defer` | 未確定 | 広告表示、配信同意、privacy及び個人情報処理を適用法と媒体policyへ適合させる | MRや旧節を根拠にせず、採用する事業・地域・媒体operation・データcategoryごとに法的根拠と責任主体を新BR/REQへ定義する | 事業主体とjurisdiction／採用operation／取得データ／保持/削除／同意/表示／専門家確認要否<br>再開: stable BR/REQの法令・privacy業務根拠が承認される／対象jurisdiction、operation、data category、保持及び同意境界が凍結される／positive/negative/boundary AC/TCが成立する | NFR-BUSINESS-AUTHORITY, CONTENT-RISK-CLASSIFICATION, LEGACY-MEDIA-ADMISSION-INVENTORY |
| `NFR-10` | `defer` | 未確定 | 障害又は誤操作から権威状態と必要な業務証跡を許容時間内に復旧する | 旧SQLite日次14世代、browser session及びDocker WP一括要件を採用せず、権威データ分類とriskごとにbackup、restore、reconciliation及び復旧試験を定義する | 権威データ分類／RPO/RTO／保持世代／暗号化／offsite／restore principal／外部媒体reconciliation<br>再開: VPS製品状態とデータ分類が要求として凍結される／RPO/RTO、保持、暗号化、restore principal及び復旧試験が承認される／credentialをbackup対象へ混入しない境界が成立する | NFR-BUSINESS-AUTHORITY, PRODUCT-STATE-AUTHORITY, VPS-CREDENTIAL-SECURITY-BOUNDARY |
| `NFR-11` | `defer` | BR-F5 | 媒体account単位の月次quota超過とpolicy違反を防ぐ | FR-74や別NFRを根拠にせず、採用capabilityごとにprovider quota、内部安全cap、集計窓、unknown時拒否及び再開条件を定義する | stable REQ root／採用service/account/operation／provider window／安全cap／再開条件<br>再開: 対象媒体capabilityがenabled又はattended-only候補になる／stable REQ rootとservice/account/operation別quotaが承認される／provider quota、内部cap、evidence及びAC/TCが凍結される | NFR-BUSINESS-AUTHORITY, RATE-QUOTA-COST-AUTHORITY, LEGACY-MEDIA-ADMISSION-INVENTORY |

## 旧orphan FR/SR disposition候補

> stable REQ root又はFN/CMP/AC降下を欠く旧FR/SRを、意味の近い責務単位で分類する。stable IDは全件exact coverageし、group化を理由に個別IDを黙示採用しない。

| group | IDs | 処置 | 旧問題 | 置換後の意味 | root／降下 | 再開条件 |
|---|---|---|---|---|---|---|
| `ORG-FR-WORK-MODEL` | FR-17, FR-35, FR-48 | `redescent` | Kanban、bounded domain、media bindingはstable REQとACだけを持ちFN/CMPへ未降下で、旧S1をimplementation-readyと誤読できる | 各責務をactor、scope、state、human judgement、side effect、evidence、phase付き要求へ再降下し、対象releaseが決まるまで実装順を確定しない | 既存REQ-053/054/055を新REQ正本へ意味再構成しBR-J1/J2/J3と双方向に束縛する<br>新FRごとにFN/CMP候補とpositive/negative/boundary AC/TCを作るが、要求freeze前はL2以降へ進めない | — |
| `ORG-FR-NOTION` | FR-45 | `defer` | Notion同期は媒体BR直結でstable REQ rootがなく、同期方向・正本・credential・write policy・AC/TCの現要求がない | Notionを必須経路にせず、採用時にread/write、正本方向、principal、workspace、credential、conflict、quota、evidenceを独立要求化する | 採用business valueが生じた時点で新BR/REQを起票し、旧媒体BRから許可を推測しない<br>媒体capability admissionと外部write policy、AC/TCが閉じるまでFR/FN/CMPへ再降下しない | Notion連携のbusiness valueと正本方向が承認される／workspace/account/principal/operation/credential/policy/evidenceが凍結される／positive/negative/boundary AC/TCが成立する |
| `ORG-FR-RICH-MEDIA` | FR-53 | `defer` | 音声・動画・EPUBを一つのS3+包括責務へ束ね、stable REQ root、媒体別価値、provider、license、品質、配布経路がない | 音声、動画、EPUBを成果物種別・媒体operation・provider capabilityごとに分け、S3+の曖昧な包括phaseを廃止する | 採用する成果物種別ごとにbusiness value、audience、funnel role、license及び新REQを起票する<br>provider、principal、credential、source/license evidence、quality gate、媒体AC/TCが閉じた種別だけ個別再降下する | 対象成果物種別とfunnel上の価値が承認される／provider/license/credential/品質/配布operationが凍結される／種別別AC/TCとrelease phaseが成立する |
| `ORG-FR-MIGRATION` | FR-72 | `replace` | migration昇格はcharter節とNFR-3だけをrootにし、対象data、owner、compatibility、rollback、RPO/RTO及び新VPS状態正本が未定義 | migrationをVPS製品状態、data classification、version、compatibility、backup/restore、dry-run、rollback及びPO release判断へ束縛する | PRODUCT-STATE-AUTHORITYとNFR business rootから新BR/REQを作り、charter節だけをrootにしない<br>対象migration classとriskごとのAC/TCを要求として閉じ、要求freeze後にだけDDL/L4/L5へ降下する | — |
| `ORG-FR-PAID` | FR-73 | `defer` | 旧spend_ledgerはFN/CMP未降下で、事業支出と顧客入金、operation種別、通貨、返金、税及び超後期有料集客を分離しない | 顧客charge、事業支出、返金/reversal、広告予算を別policy・ledger・approvalへ分離し、有料集客は超後期までdisabledにする | REQ-027を金銭operation種別ごとの業務価値とprincipalへ再構成する<br>個別金銭capability、予算、credential、tax、failure/recovery、AC/TCが承認されるまで再降下しない | 超後期releaseの金銭capabilityが承認される／顧客入金と事業支出のledger/policy/approvalが分離される／予算・通貨・返金・税・credential・AC/TCが凍結される |
| `ORG-FR-PROFILE-ACCOUNT` | FR-74, FR-75 | `replace` | brand×media×account台帳と誤投稿preflightはstable REQ/FN/CMPがなく、profile lifecycleの人間判断と機械判定を混在する | profile/account登録・変更・廃止・activationを許可principal判断へ、binding preflightを機械gateへ分離し、不一致時は停止して自動付替えしない | BUSINESS-PROFILE-AUTHORIZATIONからprofile/account/operation authorityの新BR/REQを作る<br>lifecycle判断receipt、binding schema、preflight拒否、停止/re-activationを新FR/AC/TCへ再降下する | — |
| `ORG-FR-INBOX-READ` | FR-76, FR-77 | `replace` | Discord operational notificationとWeb UI禁止のAPI-only閲覧はVPS UI＋UI内inboxの主入口要求に逆行しstable REQ/FN/CMPもない | 初期通知をVPS UI内inboxのdurable eventへ、閲覧を権威read model＋Web UIへ置換し、通知状態と業務判断を分ける | VPS UI primary、inbox lifecycle、authentication/session及びproduct stateから新BR/REQを作る<br>inbox purpose/state/evidence、read model、認証・認可、人間判断receiptを新FR/AC/TCへ再降下し外部通知adapterはdeferredにする | — |
| `ORG-SR-CORE-MODEL` | SR-01, SR-02, SR-03, SR-04, SR-05, SR-12, SR-16 | `redescent` | 戦略coreはBR/charter直結でstable REQ rootがなく、複数modelや旧語彙を現要求のresearch/funnel loopへ意味接続していない | research evidence、商品/offer capability、marketing funnel、媒体役割、仮説、KPI還流及び人間の戦略判断を一つの意味loopへ再構成する | RESEARCH-LED-CONTENT-GROWTHと旧BR-A/Eの価値からstable REQを新設し、charter節をroot代用にしない<br>戦略責務ごとのactor/scope/HJ/evidence/phaseとAC/TCを再降下し、旧3モデル等の具体方式は再評価する | — |
| `ORG-SR-LOOP-GOVERNANCE` | SR-06, SR-07, SR-08, SR-09, SR-10, SR-11, SR-13, SR-14 | `redescent` | brief/TLP/revision/content/media-role責務はREQとCMP/ACを持つがFN層がなく、PO企画確定を機械又は別agent審査へ置換する箇所がある | 構文・存在の機械検査と企画内容・改訂・有効化の人間判断を分け、research/funnel/content gateへ意味接続する | REQ-047〜051を新REQ正本へ再構成し、BR-I2/I3/I5/I6等の判断principalと双方向に束縛する<br>各SRへFN又は明示N/A責務、判断receipt付きAC、authority付きTCを降下し、draft STCを受入oracleにしない | — |
| `ORG-SR-SCOPE` | SR-15 | `replace` | 旧charterだけをrootにS0最小集合を固定し、新VPS UI、inbox、activation、content gate及びresearch要求を含まない | 新baselineのinitial/follow-on/deferred scope assignmentと依存順から最小releaseを再定義し、旧S0番号を意味根拠にしない | 候補PRCと個別refinementのPO receiptから新release-scope REQを作る<br>要求freeze後にのみ新SRとrelease acceptanceへ降下し、旧S0 L2〜L6を流用しない | — |
| `ORG-SR-ADVANCED-ANALYSIS` | SR-17, SR-18, SR-19 | `defer` | logic treeと統合分析はstable REQ、FN、CMP、ACがなくdraft strategy testだけが存在し、要求定義済みと誤読できる | research-led growth loopの基本KPI還流が成立した後の高度分析capabilityとして分離し、手法・data・判断principalを先に要求化する | 基本growth loopの実績と追加business valueが確認された時点で新BR/REQを起票する<br>data quality、因果主張の限界、human judgement、AC/TC、test authority及びphaseが閉じるまで再降下しない | 基本research/funnel/KPI loopが要求・受入とも成立する／高度分析のbusiness value、data、手法境界、判断principalが承認される／stable REQ、FN/CMP、positive/negative/boundary AC/TCが成立する |

## 旧REQ 55件 disposition候補

> confirmed Markdownとdraft JSONのどちらも現要求正本として採用せず、stable IDごとの処置を明示する。groupはレビュー単位であり、item dispositionとdeferred再開条件はID単位で保持する。

| group | ID別処置 | 旧問題 | 置換policy | root action | deferred再開条件 |
|---|---|---|---|---|---|
| `REQG-LOOPS-STATE` | REQ-001=redescent, REQ-002=redescent, REQ-003=redescent, REQ-004=replace, REQ-005=redescent, REQ-006=replace, REQ-007=redescent | 上位/下位loop、計画、状態、taskを一群に置き、REQ-004をDDL責務へ誤接続しREQ-006はSQLiteを業務要求として固定する | 戦略loop、実行loop、検証loop、brand/action plan、cycle、製品状態、task assignmentを別責務にし、REQ-004は計画内容とPO判断へ、REQ-006はVPS製品状態正本へ置換する | BR-A1〜A4のactor/value/HJを各新REQへ直接降下し、旧MD/JSONのtrace差を採用しない | — |
| `REQG-PAIR-EVIDENCE` | REQ-008=redescent, REQ-009=redescent, REQ-010=redescent, REQ-011=redescent | 企画/品質、計画/計測、証跡収束、作成/検証分離の価値はあるが旧MD/JSONで下流traceが異なる | 成立pair、完了evidence及び独立検証をactor、scope、反例、phase付きで再定義し、ID対応ではなく意味digestで降下する | BR-B1〜B4から新REQを再生成し、旧related差分をPO選択なしにmergeしない | — |
| `REQG-ETHICS-MONEY` | REQ-012=replace, REQ-013=redescent, REQ-014=redescent, REQ-015=replace | ゼロ広告費、PR表示、禁止訴求及び金銭承認を一律ruleにし、対象risk、商品/offer、金銭operation種別及び超後期有料集客を分けない | 有料集客は超後期disabled、PR/広告表示と誇張表現はrisk/offer/媒体別content gateへ、顧客入金・事業支出・返金等は別policy/ledger/approvalへ分ける | BR-C1〜C4を現商品/offer capability、risk class及び金銭operation authorityから新REQへ再構成する | — |
| `REQG-DISCOVERY-PROFILE` | REQ-016=redescent, REQ-017=redescent, REQ-018=redescent, REQ-019=redescent | 不足slot、research draft、config変更及び複数profileを持つが、現在のresearch/funnel、case-by-case rule、profile authority及び変更receiptへ未接続 | 未知情報を質問へ回す境界、source付きresearch、外部化rule revision及びstable profile authorizationへ意味再降下する | BR-D1〜D4からactor、scope、user judgement、rule/profile lifecycleを新REQへ直接宣言する | — |
| `REQG-MEASUREMENT-REPORTING` | REQ-020=redescent, REQ-021=defer, REQ-022=replace, REQ-023=redescent, REQ-024=replace, REQ-025=defer | KPI tree、MMM、browser export→SQLite、hash/screenshot、HTML dashboard、xlsxという分析価値と取得/保存/表示手段を混在する | funnel role KPIとsource evidenceを中心にし、取得はAPI/MCP優先＋必要時Playwright、表示はVPS Web UI、保存方式は設計へ留保する。MMMとxlsxは価値・利用者が確定するまでdeferredにする | BR-E1〜E3をresearch/funnel/KPI/UI価値へ再接続し、SQLite/HTML/xlsxをstable requirementにしない | REQ-021: 媒体横断因果評価のbusiness valueとdata qualityが承認される／基本funnel KPI loopと高度分析境界が成立する<br>REQ-025: xlsxを必要とする利用者と業務workflowが承認される／VPS UI又はAPIでは満たせないexport要件とdata scopeが凍結される |
| `REQG-CONNECTOR-CREDENTIAL` | REQ-026=replace, REQ-027=defer, REQ-028=replace, REQ-029=replace, REQ-030=redescent, REQ-031=replace | MCP→browser→paid順、browser攻略地図、自己修復、行追加、平文なしを旧runtime前提で固定し、公式API優先、Playwright、capability admission、暗号化credentialを反映しない | 公式API/MCPを優先しPlaywrightをfallback/確認へ限定する。操作知識はversion付き外部rule/evidence、repairは安全停止、媒体追加はtyped capability、credentialは暗号化store又は有人一時注入とする | BR-F1〜F4からoperation別business value、principal、effect、policy、credential、quota、failure/recoveryを新REQへ再構成する | REQ-027: 超後期の有料capabilityが承認される／金銭operation、ledger、予算、credential、AC/TCが凍結される |
| `REQG-CONTENT-WORDPRESS` | REQ-032=redescent, REQ-033=replace, REQ-034=defer, REQ-035=replace, REQ-036=replace | source hash、WP収束、rich-media repurpose、Claude Design token、子theme/pluginを一群にし、content authority、provider-neutral及びWP保守分離を欠く | source/evidence traceは維持するが、content正本をWPへ一律固定せず媒体operationごとに定義する。rich mediaはdeferred、design tokenはprovider-neutral、WP content/platform/securityを別releaseにする | BR-G1〜G4を成果物価値、媒体operation、provider capability及び保守authorityごとの新REQへ分割する | REQ-034: 対象rich-media種別とfunnel価値が承認される／provider/license/品質/配布operation/AC/TCが凍結される |
| `REQG-HUMAN-NOTIFICATION` | REQ-037=replace, REQ-038=replace, REQ-039=replace | 企画確定後human-out-of-loop、Discord個別投稿承認、旧auto-mode及び異常通知を固定し、phase別人間判断、初回activation、content gate、VPS inboxを反映しない | 通常/初期setup/例外/governance/external-writeを分け、VPS UIで初回scope activation後は合格済み通常投稿を毎回承認なしで自動化する。異常は安全停止＋VPS UI内inboxへ記録する | BR-H1〜H3を人間判断phase、activation scope、停止/re-activation及びoperational eventの新REQへ分割する | — |
| `REQG-CROSSCUT-QUALITY-MEDIA` | REQ-040=redescent, REQ-041=redescent, REQ-042=replace, REQ-043=replace, REQ-044=replace, REQ-045=defer | NFR自身をsourceにする循環、SQLite復旧、SQL一発可観測性、全媒体browser乱数、sourceなし媒体一括稼働を含む | 品質要求をstable BR rootへ戻し、再開はVPS製品状態、可観測性はVPS UI read model、rateはAPI/MCP quotaとPlaywright節度へ分離する。媒体は個別capability admissionまでdeferredにする | NFR dispositionのbusiness value/actor/scopeから新BR/REQを作り、NFRや旧節を自己根拠にしない | REQ-045: 媒体/operationごとのbusiness valueとcapability statusが承認される／principal/effect/policy/credential/quota/evidence/AC/TCが凍結される |
| `REQG-PROFILE-STRATEGY` | REQ-046=redescent, REQ-047=redescent, REQ-048=redescent, REQ-049=redescent, REQ-050=redescent, REQ-051=redescent, REQ-052=redescent | profile隔離、brief/TLP/revision/campaign/content宣言、横断evidenceは価値を持つが、旧MD/JSON trace差と人間判断receipt欠落がある | profile authorizationとresearch/funnel strategy loopへ接続し、企画・revision・有効化の人間判断、evidence、phaseを直接型付けする | BR-I1〜I7から新REQを再生成し、旧related差分を自動unionせずmeaning ownerとPO receiptで選ぶ | — |
| `REQG-WORK-MODEL` | REQ-053=redescent, REQ-054=redescent, REQ-055=redescent | 旧MD/JSONで本文とfill表現が異なり、Kanban、domain隔離、media binding/TLPの新FRはFN/CMP未降下 | pull/WIP/blocked、safe workspace、profile/domain/media binding lifecycleを意味軸付き新REQへ再構成し、Scrum cadenceやTLP還流の境界を明示する | BR-J1〜J3からactor/value/scope/HJ/evidenceを直接降下し、JSONを唯一正本としてviewを生成する | — |

## 旧BR 41件 disposition候補

| group | ID別処置 | 保持する価値 | 置換policy | owner |
|---|---|---|---|---|
| `BRG-A` | BR-A1=redescent, BR-A2=redescent, BR-A3=redescent, BR-A4=redescent | 戦略・実行・検証loop、媒体別cadence、brand/action plan trace及びtask verificationを保持する | 旧三重loopと状態手段を価値から分離し、research/funnel/KPI loop、VPS製品状態、計画PO判断及びescalationを意味軸付き新BRへ再構成する | L0-NORTH-STAR-AUTHORITY-NORMALIZATION, RESEARCH-LED-CONTENT-GROWTH, PRODUCT-STATE-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-B` | BR-B1=redescent, BR-B2=redescent, BR-B3=redescent, BR-B4=redescent | 企画/品質、計画/計測、証跡収束及び作成/検証分離による品質保証を保持する | content gate、research evidence、funnel KPI及び独立verificationへ再接続し、毎回投稿承認やagent名の違いだけを品質証明にしない | CONTENT-QUALITY-GATE-LEARNING, RESEARCH-LED-CONTENT-GROWTH, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-C` | BR-C1=replace, BR-C2=redescent, BR-C3=redescent, BR-C4=replace | 不当な広告・表示・訴求及び無許可金銭operationから利用者と事業を守る | 有料集客は超後期deferred、表示/表現はrisk・offer・媒体別gate、金銭は顧客入金/事業支出/返金等の別policy・ledger・approvalへ置換する | CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING, RATE-QUOTA-COST-AUTHORITY, NFR-BUSINESS-AUTHORITY |
| `BRG-D` | BR-D1=redescent, BR-D2=redescent, BR-D3=redescent, BR-D4=redescent | 未知情報を人へ確認し、source付きresearch、変更可能rule及び複数事業profileを安全に管理する | case-by-case user preference、外部化rule revision、research/funnel及びstable profile authorizationへ意味再降下する | REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE, RESEARCH-LED-CONTENT-GROWTH, CONTENT-QUALITY-GATE-LEARNING, BUSINESS-PROFILE-AUTHORIZATION |
| `BRG-E` | BR-E1=redescent, BR-E2=replace, BR-E3=replace | funnel上の媒体役割をKPIで観測しsource evidenceと共に人へ提示する | browser export/SQLite/HTML/xlsxを固定せず、API/MCP優先＋必要時Playwright取得、権威read model、VPS Web UI及び役割別KPIへ置換する | RESEARCH-LED-CONTENT-GROWTH, OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, VPS-UI-PRIMARY-HUMAN-INTERFACE |
| `BRG-F` | BR-F1=replace, BR-F2=replace, BR-F3=redescent, BR-F4=replace, BR-F5=replace | 外部接続を安全に選び、媒体追加、credential及びaccount健全性を管理する | 公式API/MCP優先＋Playwright fallback、version付き操作knowledge、typed media capability、暗号化credential、route別quota/pace及び停止後明示再開へ置換する | OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY, VPS-CREDENTIAL-SECURITY-BOUNDARY, RATE-QUOTA-COST-AUTHORITY |
| `BRG-G` | BR-G1=redescent, BR-G2=replace, BR-G3=replace, BR-G4=replace | 成果物の版・source・design consistency及びWordPress資産運用を追跡可能にする | WP一律収束を媒体operation別content authorityへ、Claude Design必須をprovider-neutral token capabilityへ、WP開発をcontent/platform/securityの別releaseへ置換する | CONTENT-QUALITY-GATE-LEARNING, GENAI-EXECUTION-ROUTE, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE |
| `BRG-H` | BR-H1=replace, BR-H2=replace, BR-H3=replace | 通常運用を自動化しつつ必要な人間判断、安全停止及び対応情報を失わない | 二接点限定をphase別判断へ、Discord個別投稿承認/auto-modeをVPS UI初回activation＋gate合格後自動運用へ、異常通知を安全停止＋UI内inboxへ置換する | VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING, FR-16-NOTIFICATION-BOUNDARY |
| `BRG-I` | BR-I1=redescent, BR-I2=redescent, BR-I3=redescent, BR-I4=redescent, BR-I5=redescent, BR-I6=redescent, BR-I7=redescent | profile隔離、戦略/戦術分離、仮説改訂、学習還流、複数媒体campaign、価値定義及び再開/idempotencyを保持する | research/funnel/media role、明示的な企画/改訂判断receipt、VPS製品状態及びprofile authorizationへ意味再接続する | BUSINESS-PROFILE-AUTHORIZATION, STRATEGY-REQUIREMENT-ADMISSION, RESEARCH-LED-CONTENT-GROWTH, PRODUCT-STATE-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-J` | BR-J1=redescent, BR-J2=redescent, BR-J3=redescent | pull/WIP/blocked運用、domain隔離及び戦略判断に基づくmedia binding lifecycleを保持する | actor/scope/HJ/evidence/phase付き新REQへ再降下し、媒体bindingは個別capability admissionとTLP還流へ接続する | CONTRACT-SEMANTIC-DESCENT-V2, BUSINESS-PROFILE-AUTHORIZATION, LEGACY-MEDIA-ADMISSION-INVENTORY, STRATEGY-REQUIREMENT-ADMISSION |

## 旧媒体BR 70件 disposition候補

> 媒体名又は旧BRの存在は実行許可ではない。全媒体は個別capabilityのPO receiptとAC/TCまで未承認・未設計である。

| media | IDs | 処置 | 現候補での役割 | route policy | 再開条件 |
|---|---|---|---|---|---|
| `aff` | BR-M-AFF-1, BR-M-AFF-2, BR-M-AFF-3, BR-M-AFF-4 | `replace` | 商品/offer capabilityに応じて選定・比較・差替え可能なaffiliate monetization候補 | offerごとのowner/選定/差替え/内容変更authority、PR表示、risk、tracking、媒体operationを閉じ、権限不明なら変更しない | 対象affiliate programと商品/offer capabilityが登録される／PR/legal/policy/tracking/evidence/AC/TCが凍結される |
| `canva` | BR-M-CANVA-1, BR-M-CANVA-2, BR-M-CANVA-3 | `defer` | 将来のvisual asset制作provider候補 | provider-neutral design capabilityとして扱いconsumer Web UI無人操作を許可しない | visual assetのbusiness valueとproviderが承認される／API/MCP/attended route、license、credential、evidence、AC/TCが凍結される |
| `dc` | BR-M-DC-1, BR-M-DC-2, BR-M-DC-3, BR-M-DC-4 | `replace` | 通知ではないcommunity marketing媒体のfollow-on候補 | Bot/API principalだけを候補とし、community post/reply/moderation/measurementを別operationに分け、製品通知・承認・開発PRとcredential/policy/evidenceを共有しない | community上のfunnel roleとoperationが承認される／Bot/guild/channel/principal/policy/quota/moderation/evidence/AC/TCが凍結される |
| `ds` | BR-M-DS-1 | `replace` | provider-neutral design token source候補 | Claude Design等の単一providerを必須にせずtoken schema、source authority、fallback、credential、evidenceを分ける | design tokenのbusiness valueとsource authorityが承認される／provider adapter、schema、credential、fallback、AC/TCが凍結される |
| `genai` | BR-M-GENAI-1, BR-M-GENAI-2, BR-M-GENAI-3, BR-M-GENAI-4 | `replace` | 研究・制作を補助するprovider-neutral生成capability候補 | Codex CLI/home又はconsumer Web UIを製品必須経路にせず、公式API/MCP/許可CLI adapter、principal、credential、quota、license、input/output evidenceを閉じる | 対象生成operationとprovider classが承認される／route/credential/quota/license/risk/content gate/evidence/AC/TCが凍結される |
| `hs` | BR-M-HS-1, BR-M-HS-2, BR-M-HS-3, BR-M-HS-4 | `defer` | 将来のemail/CRM nurture候補 | 公式API/MCP、opt-in/out、個人情報、配信purpose、account、quota、evidenceを閉じるまで配信しない | funnel上のnurture roleと法的根拠が承認される／API/principal/consent/privacy/credential/quota/AC/TCが凍結される |
| `ig` | BR-M-IG-1, BR-M-IG-2, BR-M-IG-3, BR-M-IG-4 | `defer` | 将来のvisual social discovery/community媒体候補 | 公式APIを優先しconsumer browser writeを許可せず、content/license/retention/account/quotaを個別化する | funnel roleと投稿operationが承認される／API/account/license/retention/policy/quota/evidence/AC/TCが凍結される |
| `kdp` | BR-M-KDP-1, BR-M-KDP-2, BR-M-KDP-3, BR-M-KDP-4, BR-M-KDP-5 | `defer` | 将来のlong-form出版・monetization媒体候補 | 書籍生成、権利、品質、価格、出版account、更新/廃止を別operationにしconsumer browser自動writeを前提にしない | 出版物のfunnel roleとbusiness valueが承認される／権利/品質/pricing/account/route/evidence/AC/TCが凍結される |
| `line` | BR-M-LINE-1, BR-M-LINE-2, BR-M-LINE-3, BR-M-LINE-4 | `replace` | 将来のmessaging/nurture媒体候補 | Messaging API第一とし管理画面browserはattended確認に限定し、consent、配信停止、principal、quota、privacyを閉じる | funnel roleと配信purposeが承認される／Messaging API/account/consent/privacy/credential/quota/evidence/AC/TCが凍結される |
| `meas` | BR-M-MEAS-1, BR-M-MEAS-2, BR-M-MEAS-3 | `replace` | research/funnel/KPI loopの測定source候補 | API/MCP優先＋必要時Playwright read確認とし、source/freshness/profile/account/KPI role/evidenceを束縛する | KPIとsource authorityが承認される／read route/account/profile/freshness/privacy/evidence/AC/TCが凍結される |
| `note` | BR-M-NOTE-1, BR-M-NOTE-2, BR-M-NOTE-3, BR-M-NOTE-4 | `defer` | 将来のlong-form discovery/monetization媒体候補 | 投稿、課金、更新、計測を別operationにし、browser writeは利用規約とattended/unattended境界が閉じるまで禁止する | funnel roleとmonetization valueが承認される／route/account/pricing/policy/credential/quota/evidence/AC/TCが凍結される |
| `notion` | BR-M-NOTION-1, BR-M-NOTION-2 | `defer` | 将来のworkspace同期capability候補 | 製品状態やcontentの正本にせず、read/write方向、workspace、conflict、credential、evidenceを閉じる | 同期のbusiness valueとauthority方向が承認される／API/workspace/principal/conflict/credential/policy/evidence/AC/TCが凍結される |
| `pc` | BR-M-PC-1, BR-M-PC-2, BR-M-PC-3, BR-M-PC-4 | `defer` | 将来のpodcast distribution媒体候補 | 音声生成、権利、feed、公開、更新、計測を別operationにしprovider/browser経路を暗黙採用しない | podcastのfunnel roleとbusiness valueが承認される／audio/provider/license/feed/account/route/evidence/AC/TCが凍結される |
| `play` | BR-M-PLAY-1, BR-M-PLAY-2, BR-M-PLAY-3 | `defer` | 超後期のapp distribution候補 | on-holdを維持しPlay Console browser公開routeを実装入力にしない | PWA/app productのbusiness valueとreleaseが承認される／developer account/policy/credential/artifact/signing/release/rollback/AC/TCが凍結される |
| `pwa` | BR-M-PWA-1, BR-M-PWA-2 | `defer` | 超後期のowned app/PWA候補 | 初期VPS Web UIと混同せず、別product capability、distribution、security、availabilityとして扱う | PWAの独立business valueとaudienceが承認される／product scope/security/distribution/operation/evidence/AC/TCが凍結される |
| `seed` | BR-M-SEED-1, BR-M-SEED-2 | `defer` | 将来の動画生成provider候補 | consumer Web UI又は支出を暗黙許可せずprovider API、license、cost、credential、evidenceを閉じる | 動画のfunnel roleとproviderが承認される／API/license/cost/credential/quota/content gate/evidence/AC/TCが凍結される |
| `stfm` | BR-M-STFM-1, BR-M-STFM-2, BR-M-STFM-3 | `defer` | 将来のaudio distribution媒体候補 | 音声、権利、公開、更新、計測、accountを個別operationにしbrowser routeを暗黙採用しない | audio媒体のfunnel roleが承認される／provider/license/account/route/policy/evidence/AC/TCが凍結される |
| `stripe` | BR-M-STRIPE-1, BR-M-STRIPE-2, BR-M-STRIPE-3 | `defer` | 将来の顧客決済capability候補 | 顧客charge/checkout/refundを事業支出ledgerから分離し、商品/価格/customer/data/tax/refund/approval/evidenceを別契約化する | 販売商品と顧客決済business valueが承認される／money operation/policy/ledger/customer data/tax/refund/credential/AC/TCが凍結される |
| `wp` | BR-M-WP-1, BR-M-WP-2, BR-M-WP-3 | `replace` | 初期候補のowned content operationと別releaseのplatform/security maintenance | 投稿draft/publish/updateとtheme/plugin/CLI/SEO/platform/security変更を別principal/policy/credential/release/rollback/evidenceへ分ける | content operationのprofile/site/account/operationが承認される／platform/security maintenanceは別releaseでbackup/compatibility/rollback/AC/TCが凍結される |
| `x` | BR-M-X-1, BR-M-X-2, BR-M-X-3, BR-M-X-4 | `replace` | 将来のshort-form discovery/community媒体候補 | 公式APIを優先し、Playwright writeは利用規約上許可されるattended-only operation以外禁止する。read確認とwriteを分ける | funnel roleとoperationが承認される／API/attended browser/account/policy/quota/evidence/AC/TCが凍結される |
| `yt` | BR-M-YT-1, BR-M-YT-2, BR-M-YT-3, BR-M-YT-4 | `defer` | 将来のvideo discovery/education媒体候補 | 企画、動画生成、権利、upload、metadata、更新、計測を別operationにし公式API/provider routeを閉じる | videoのfunnel roleとbusiness valueが承認される／provider/license/account/API/credential/quota/content gate/evidence/AC/TCが凍結される |

## 旧FR 43件 disposition候補

> 旧FRのconfirmedは旧baselineの履歴であり、下表は現要求への未承認・未設計の移送候補である。

| group | ID別処置 | 置換policy | owner | deferred再開条件 |
|---|---|---|---|---|
| `FRG-LOOPS-WORK` | FR-11=replace, FR-12=redescent, FR-13=redescent, FR-14=redescent, FR-15=redescent, FR-17=redescent, FR-35=redescent, FR-48=redescent | 旧SQLite中心のloop状態をVPS製品状態へ置換し、task/verification/cadence/learning/Kanban/domain/media bindingを一意のactor・scope・HJ・evidence・phaseへ再降下する | PRODUCT-STATE-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2, FR-SLICE-AUTHORITY-ALIGNMENT, STRATEGY-REQUIREMENT-ADMISSION | — |
| `FRG-QUALITY-SAFETY` | FR-16=replace, FR-21=redescent, FR-22=redescent, FR-23=replace, FR-24=redescent, FR-25=redescent, FR-26=replace, FR-27=redescent, FR-28=redescent | 異常は安全停止＋durable evidence＋VPS UI内inboxへ、広告費は超後期disabledへ、金銭escalationはoperation別policy/ledger/approvalへ置換し、品質pair・risk gate・独立検証をcontent gateへ再降下する | FR-16-NOTIFICATION-BOUNDARY, VPS-UI-INBOX-LIFECYCLE, CONTENT-QUALITY-GATE-LEARNING, CONTENT-RISK-CLASSIFICATION, RATE-QUOTA-COST-AUTHORITY | — |
| `FRG-DISCOVERY-PROFILE` | FR-31=redescent, FR-32=redescent, FR-33=redescent, FR-34=redescent | 問診、source付きresearch、外部化rule revision及びstable profile authorizationへ再接続し、draft採否・危険側変更・profile lifecycleの人間判断receiptをAC/TCまで降下する | REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE, RESEARCH-LED-CONTENT-GROWTH, CONTENT-QUALITY-GATE-LEARNING, BUSINESS-PROFILE-AUTHORIZATION, CONTRACT-SEMANTIC-DESCENT-V2 | — |
| `FRG-CONNECTORS` | FR-41=replace, FR-42=replace, FR-43=replace, FR-44=replace, FR-45=defer, FR-46=replace, FR-47=replace | 公式API/MCP優先＋Playwright fallback/確認、version付き操作knowledge、repair失敗時停止、WP content/platform/security分離、VPS UI初回activation、暗号化credentialへ置換する。Notionは個別価値までdeferred | OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE, AUTOMATED-PUBLISHING-ADMISSION, VPS-CREDENTIAL-SECURITY-BOUNDARY | FR-45: Notion同期のbusiness valueと正本方向が承認される／workspace/account/principal/operation/credential/policy/evidence/AC/TCが凍結される |
| `FRG-CONTENT-ASSETS` | FR-51=redescent, FR-52=replace, FR-53=defer, FR-54=redescent, FR-55=replace | render/source/evidence traceをcontent gateへ再降下し、Claude Designをprovider-neutral token capabilityへ、WP一律資産収束を媒体operation別authorityへ置換する。rich mediaは個別価値までdeferred | CONTENT-QUALITY-GATE-LEARNING, GENAI-EXECUTION-ROUTE, RESEARCH-LED-CONTENT-GROWTH, LEGACY-MEDIA-ADMISSION-INVENTORY | FR-53: 対象rich-media種別とfunnel valueが承認される／provider/license/credential/quality/distribution/evidence/AC/TCが凍結される |
| `FRG-MEASUREMENT-UI` | FR-61=redescent, FR-62=replace, FR-63=replace | funnel role KPIと初期形のPO receiptを再降下し、取得をAPI/MCP優先＋Playwright read確認へ、表示をVPS Web UIの権威read modelへ置換する | RESEARCH-LED-CONTENT-GROWTH, OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, VPS-UI-PRIMARY-HUMAN-INTERFACE, PRODUCT-STATE-AUTHORITY | — |
| `FRG-STATE-UI-MONEY` | FR-71=replace, FR-72=replace, FR-73=defer, FR-74=replace, FR-75=replace, FR-76=replace, FR-77=replace | 汎用DDLをbrand plan approvalの代替にせず、VPS製品状態、migration/rollback、profile/account lifecycle、binding preflight、VPS UI内inbox、read model、authentication/sessionへ再構成する。支出は超後期deferred | PRODUCT-STATE-AUTHORITY, NFR-BUSINESS-AUTHORITY, RATE-QUOTA-COST-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION, AUTOMATED-PUBLISHING-ADMISSION, VPS-UI-INBOX-LIFECYCLE, VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-AUTHENTICATION-SESSION | FR-73: 超後期の金銭capabilityが承認される／顧客入金/事業支出/返金のpolicy・ledger・approvalと予算/credential/AC/TCが凍結される |

## 旧FN／AC／TC派生契約の扱い

| kind | count | ID digest | 処置 | 再利用条件 | 禁止claim |
|---|---:|---|---|---|---|
| `FN` | 61 | `sha256:b36848f24c8c8942c98224d688ef8562c7d445c6ae587cd41c5dd58cb9bc6eb4` | `defer_until_parent_redescent` | 親要求がPO receipt付きfrozen正本へ再降下される／actor/scope/HJ/side_effect/evidence/phaseを新要求から再生成する／旧phase・provider・browser・Discord・WP責務を自動継承しない | 旧FNの存在を機能設計完了とみなさない／旧trace又はsliceだけでcurrent実装入力にしない |
| `AC` | 252 | `sha256:f9a3a3a813f37a3f05e2439d8f6673506dbc766860a3c5ed90a793f508b4ab49` | `defer_until_parent_redescent` | 親要求とFN責務がPO receipt付きfrozen正本へ再降下される／principal/scope/HJ/side_effect/phaseとpositive/negative/boundary evidenceを新要求から再生成する／通知・承認・community・金銭operationをexact purpose tupleで分離する | 旧ACの存在を現要求の受入完了とみなさない／旧Discord・API-only UI・machine-only approvalを受入oracleにしない |
| `TC` | 258 | `sha256:804284aa99aeafcf0c0532e090840bc77d668f65c4e3e79380105640e8ef228b` | `defer_until_parent_redescent` | 親要求・FN・ACが同じfrozen revisionへ再降下される／principal/scope/phase/external effect/evidenceと反証条件を新ACから再生成する／旧TC aliasとdraft STCを現行TCC authorityへ混在させない | 旧TC成功を現要求の受入証拠にしない／旧ID・fixture・mock期待値から新runtime挙動を推測しない |

## 要求authority revision選択（PO未決）

- 問い: 新要求を新revisionの単一JSON正本として作り旧ID群を履歴専用に残すか、旧IDをin-placeで書き換えるか
- 推奨: `new_revision_single_json_authority`
- 選択肢: new_revision_single_json_authority, rewrite_legacy_ids_in_place
- 推奨規則: 新revisionはactor/value/scope/HJ/side effect/evidence/phaseを直接型付けする／旧IDと新IDのsupersedes mappingを持つ／Markdownは新JSONからのみ生成し手編集しない／旧confirmed receiptと現baseline applicabilityを混同しない／PO decision前は候補であり正本cutover又は設計開始をしない
- 旧consumer処置: L0 charter、s0-contract、verification、basic design及びtraceの旧requirements参照をinventory化する／PO選択後に新revision参照へ一括置換又はhistorical隔離する／旧Discord、API-only UI、WSL、provider固定、旧phaseを自動移植しない
- PO decision: **未回答**。要求正本cutover及び設計開始はしない。

## 目的別完了証拠

| ID | 要求 | 状態 | evidence | 残条件 |
|---|---|---|---|---|
| `OBJ-01` | 旧L0/BR/媒体BR/REQ/FR/SR/NFR/MR/FN/AC/TCを意味レベルで全件棚卸しする | `proven` | legacy_l0_clause_dispositions／legacy_br_disposition_groups／legacy_media_br_dispositions／legacy_req_disposition_groups／legacy_fr_disposition_groups／legacy_orphan_requirement_groups／legacy_nfr_dispositions／legacy_media_inventory／legacy_derived_contract_policy／各exact coverage/digest gate PASS | — |
| `OBJ-02` | 旧requirements viewを現要求・設計の規範参照から隔離する | `proven` | G-REQ-COMPATIBILITY-AUTHORITY PASS／G-REQ-LEGACY-CONSUMER-ISOLATION PASS／旧FN/AC/TC legacy_revalidation_only | — |
| `OBJ-03` | VPS Web UIとUI内inboxを製品状態・運用通知・人間判断の初期主入口候補にする | `incomplete` | ADR-013／PRC-01/03/04/11/15／VPS-UI-PRIMARY-HUMAN-INTERFACE／VPS-UI-INBOX-LIFECYCLE／旧FR-16/43/46/76/77 disposition | 関連refinementを1件ずつPO決定し新BR/REQ/FR/NFRへ再降下する |
| `OBJ-04` | 要求・要件を先行しL2以降の設計は未着手として扱う | `proven` | implementation_authorized=false／L2-L6 revalidation_required/implementation_input=false／G-REQ-DESIGN-NOT-STARTED PASS／旧FN/AC/TC design_not_started=true | — |
| `OBJ-05` | 意味閉包した新要求正本を凍結する | `blocked_by_po` | authority_revision_candidate status=pending_po／refinement全件approval=null／G-REQ-OPEN-REFINEMENTS FAIL／semantic/trace/phase/HJ gateは旧契約に対し意図的にFAIL | 新revision又はin-place方針をPOが選び、全refinementを個別receipt付きで凍結する |

## PO回答契約

- **回答値**: `approve_as_written` / `revise` / `defer` / `reject`
- **未回答の安全側既定**: `defer`
- **必須束縛**: `refinement_id` / `revision` / `semantic_digest` / `question_id` / `response` / `rationale` / `approver_principal` / `decided_at`
- **回答の効力**: approve_as_writtenは対象revisionのpending questionを解消するだけでrefinement全体又はpacket全体を承認しない。全question解消後も別のsubject approval receiptとfreezeが必要
- **revisionの効力**: reviseは新revisionを作り旧semantic_digestをsuperseded候補にする。defer又はrejectは設計・実装入力を許可しない

- **POが決めるもの**: business value／scope/admission／authority／allowed risk／quality target／human decision boundary／deferred resume
- **L2以降で決めるもの**: protocol／database／API shape／UI layout／framework／provider product／algorithm／deployment topology
- **要求／設計境界**: PO質問は要求上のoutcome・境界・閾値・riskだけを決める。具体的な実現方式はfrozen要求からL2以降へ降下し、この回答で設計済みにならない

- **回答classごとの必須項目**:
  - `requirements_policy`: `policy_rule` / `applicable_scope` / `exceptions` / `unknown_or_na_rule` / `completion_evidence`
  - `authority_choice`: `canonical_owner` / `retained_meaning` / `superseded_meaning` / `effective_scope` / `cutover_evidence`
  - `safety_policy`: `allowed_principal` / `allowed_effect` / `prohibited_effect` / `fail_close_behavior` / `emergency_boundary` / `evidence`
  - `quality_target`: `measurement_target` / `metric` / `threshold_or_budget` / `window` / `environment` / `failure_and_recovery` / `na_rationale`
  - `release_scope`: `business_value` / `scope_in` / `scope_out` / `predecessors` / `admission_condition` / `deferred_remainder` / `acceptance_evidence`
  - `deferred_resume`: `business_value` / `deferred_reason` / `dependencies` / `risk` / `resume_condition` / `required_authority` / `required_evidence`

## RRF-AGENT-NEO-HELIX-REDEFINITION — AGENT-NEO-HELIX-REDEFINITION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000089 RDE-000090 RDE-000091 RDE-000092 RDE-000093 RDE-000099
- **主体**: PO／サイト構築者／コンテンツ運用者／AGENT NEO保守者／MARKETING HARNESS runtime
- **受益者**: AGENT NEOサイトを段階構築・運用するPOと制作担当
- **価値**: WordPress操作の実証とAGENT NEO全体要求を対応付け、サイト構築からtheme/plugin改善まで改修箇所が追跡可能な段階releaseへする
- **task**: AGENT NEO能力を固定SHAから棚卸しする／site identity／FSE styles／templates／navigation／patterns／blocks／media／content CRUD／preview・apply・rollback／SEO／measurement／migration／quality・security／health・audit／integration境界をFull V要求候補へ分類する／旧package／license／Automation SEO／CRM／SNS／外部API／AI機能を自動採用せず採否を分離する／WP操作とtheme/plugin責務をmappingする／改善・改修・updateを第三段階releaseにする
- **workflow**: WP運用/保守実証→AGENT NEO Full V-model L1-L12＋V-pair→サイト構築release→必要な段階incrementだけV設計＋Scrum実装Hybrid→S4→SR0-SR4→AGENT NEO改善/改修/update release
- **対象範囲**: Full V-model L1-L12と正規V-pair／site identityと対象site/profile境界／FSE global styles・design token・theme設定／template・template part・navigation／pattern・block・section・CTA・media／page・post・taxonomy・menuのstable ID付き操作／preview・dry-run・diff・apply・version・rollback／SEO metadata・schema・OGP・indexing／consent付きmeasurement・tracking・export／migration・import・export／accessibility・performance・i18n・privacy・security／health・status・log・audit／MARKETING HARNESS判断とAGENT NEO決定論実行のintegration境界／theme/plugin改善・改修・update／別媒体Harness開発との並行backlog
- **対象外**: AGENT-NEO repoへの現変更からの書込み／旧G4 PASSの新要求への流用／旧package／license／課金の自動採用／Automation SEO／CRM／SNS／外部APIの自動採用／theme/plugin内AI判断／ScrumとDiscoveryの同一視
- **禁止事項**: 外部repoを無断変更しない／旧設計を無検証で移植しない／repo間で正本・credential・reviewを混在させない／S4だけでV-pair未閉鎖のincrementを完了にしない
- **人間判断**: Full V要求freezeと、サイト構築release・AGENT NEO改修releaseの各S4判断をPOが分離して行う
- **副作用**: 現段階は要求記録のみ。将来はAGENT NEOサイト構築とtheme/plugin/API変更
- **証跡**: HELIX adopted methodology SHA 57853db413e282b050ac5f37bab7809321c67842／HELIX latest verification SHA fe6ffe6cfa0e11bd054dbc67e4278f0d3bd1234d／AGENT-NEO source SHA 9f5d679c0befce093ba077fcf11d514e4c75f17a／fixed-source capability inventory in RDE-000099／L1-L12 V-pair closure／capability/repo boundary map／increment evidence／S4 receipt／SR0-SR4 closure／migration/rollback proof／各repo独立review
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-AGENT-NEO-P: 固定SHAから再定義したFull V要求・V-pair・repo境界を持ち、段階incrementはS4 receiptとSR0-SR4 closureを持つ場合だけ昇格する （RST-AGENT-NEO-P）
  - `negative` RAC-AGENT-NEO-N: 旧G4 PASS、別媒体の成功、S3 green、又はWP操作だけからAGENT NEO全体をacceptedとみなすことを拒否する （RST-AGENT-NEO-N）
  - `boundary` RAC-AGENT-NEO-B: サイト構築能力とtheme/plugin改善能力を別releaseにし、互換性又はrollback未検証のupdateはenabledにしない （RST-AGENT-NEO-B）
- **PO個別質問**:
  - `RDQ-AGENT-NEO-HELIX-REDEFINITION-01` (`release_scope`): 旧package／license／Automation SEO／CRM／SNS／外部API／AI機能の採用・deferred・廃止を個別に決める （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
  - `RDQ-AGENT-NEO-HELIX-REDEFINITION-02` (`authority_choice`): MARKETING HARNESSとAGENT NEOのrepo/authority/API/evidence境界を閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:31df6dabc8432ee171318062d8ab366e75fa596ec9b4801c0cc36d9c03b0b0ef`

## RRF-AGENT-NEO-PRODUCT-EVOLUTION-RELEASE — AGENT-NEO-PRODUCT-EVOLUTION-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000122 RDE-000123
- **主体**: PO／AGENT NEO保守者／theme/plugin開発者／site運用者
- **受益者**: AGENT NEO利用siteの所有者と利用者
- **価値**: AGENT NEO自体の改善・改修・更新をサイト構築と別の影響・互換性・rollback判断で受入する
- **task**: 改善要求、影響分析、versioning、compatibility、migration、rollback、既存site regressionをFull Vへ降下する
- **workflow**: site-build closure→改善要求→影響分析→L1-L12/V-pair→変更increment→互換性/migration/rollback検証→独立S4
- **対象範囲**: theme/plugin改善／bug fix／version update／compatibility／migration／rollback／既存site regression／release notes
- **対象外**: 日常content operation／WordPress通常保守／WordPress security保守／site-build承認の流用
- **禁止事項**: site-build成功を製品update互換性の証明にしない／migration/rollbackなしで破壊的変更を昇格しない／PO権限なしに外部repoへwriteしない
- **人間判断**: 変更価値、互換性破壊、migration、rollback、repo write、release S4はPO
- **副作用**: 現段階は要求記録のみ。将来は別権限下のAGENT-NEO repo変更
- **証跡**: change impact map／L1-L12 V-pair／compatibility matrix／migration/rollback proof／既存site regression／独立review／S4 receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=3 ／ sequence=4 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=AGENT-NEO-SITE-BUILD-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-AGENT-NEO-EVOLUTION-P: site-build closure後に影響、互換性、migration、rollback、回帰、独立S4を閉じた製品変更だけを昇格する （RST-AGENT-NEO-EVOLUTION-P）
  - `negative` RAC-AGENT-NEO-EVOLUTION-N: site-build承認、単一site成功又は旧releaseを製品変更の互換性証明として拒否する （RST-AGENT-NEO-EVOLUTION-N）
  - `boundary` RAC-AGENT-NEO-EVOLUTION-B: 一部componentだけ成立する場合は変更unitを分割し未検証componentをdeferredにする （RST-AGENT-NEO-EVOLUTION-B）
- **PO個別質問**:
  - `RDQ-AGENT-NEO-PRODUCT-EVOLUTION-RELEASE-01` (`release_scope`): 対象component、互換性policy、versioning、migration、rollback、回帰範囲、repo write権限をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:821262ece1bf0a5a9c116222672e25552cab9eeae038350aa226cf984ea21d0a`

## RRF-AGENT-NEO-SITE-BUILD-RELEASE — AGENT-NEO-SITE-BUILD-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000120 RDE-000121
- **主体**: PO／サイト構築者／コンテンツ運用者／MARKETING HARNESS runtime
- **受益者**: AGENT NEOサイトを構築・運用するPOと制作担当
- **価値**: AGENT NEOを使うサイト構築をtheme製品改善から分離して再現可能に受入する
- **task**: 固定SHA能力を棚卸しし、site identity/FSE/template/navigation/pattern/content/SEO/measurement/migrationをFull Vへ降下する
- **workflow**: 固定SHA棚卸し→L1-L12/V-pair→対象確定increment→S4→SR0-SR4→site-build closure
- **対象範囲**: site identity／FSE styles／template/navigation/pattern/block／content/media／preview/apply/rollback／SEO/measurement／migration／health/audit
- **対象外**: theme/plugin code改善／外部repo write／旧G4 PASSの流用
- **禁止事項**: サイト構築受入をAGENT NEO製品改善の受入に読み替えない／未知capabilityを実装者が補完しない
- **人間判断**: capability閉集合、対象site、公開、migration、rollback、S4はPO
- **副作用**: 現段階は要求記録のみ
- **証跡**: fixed SHA inventory／L1-L12 V-pair／site/revision/principal trace／migration/rollback proof／S4 receipt／SR0-SR4 closure
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=2 ／ sequence=3 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=WORDPRESS-PLATFORM-MAINTENANCE-RELEASE／WORDPRESS-SECURITY-MAINTENANCE-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-AGENT-NEO-SITE-P: 固定SHA能力、Full V closure、対象site trace、migration/rollback、S4 receiptを持つsite-buildだけを昇格する （RST-AGENT-NEO-SITE-P）
  - `negative` RAC-AGENT-NEO-SITE-N: 旧G4、WP操作成功、別site成功又はtheme変更をsite-build受入へ流用することを拒否する （RST-AGENT-NEO-SITE-N）
  - `boundary` RAC-AGENT-NEO-SITE-B: 成立capabilityだけをreleaseし未閉capabilityはdeferredにする （RST-AGENT-NEO-SITE-B）
- **PO個別質問**:
  - `RDQ-AGENT-NEO-SITE-BUILD-RELEASE-01` (`release_scope`): site-build capability閉集合、対象site/profile、受入順、migration/rollback境界をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:6dd0e5f127c02913784bfb1847bf46e8ca0d62169881fb4c7e9cbca0b14a6b07`

## RRF-AUTO-MODE-DECISION-AUTHORITY — AUTO-MODE-DECISION-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000003 RDE-000017 RDE-000018 RDE-000033 RDE-000034
- **主体**: PO／自動判定器／媒体運用者／製品runtime
- **受益者**: 未承認公開を防ぎつつauto-mode移行を監督するPO
- **価値**: 基準評価を自動化しつつ公開承認省略の有効化・継続・解除判断をPOに残す
- **task**: 移行基準を評価する／移行候補を提示する／POがscopeと期限を指定して移行を決定する／基準を継続監視する／失効時に常時承認へ戻す
- **workflow**: criteria評価→auto_eligible→対象/影響/binding再表示→PO enable decision→期限付きauto mode→継続監視→失効時常時承認へ復帰
- **対象範囲**: auto-mode候補／媒体・operation binding／enable/disable decision／期限・再承認／criteria失効／mode遷移証跡
- **対象外**: 機械判定だけのmode移行／具体UI設計／通知transport選定／金銭操作の承認省略
- **禁止事項**: 基準充足を承認とみなさない／PO receiptなしでauto-modeへ移行しない／別媒体又は別operationへ承認を流用しない／期限切れ又は基準失効後に公開しない
- **人間判断**: 有効化・scope・期限・継続・解除の最終判断はPO
- **副作用**: 承認されたscopeと期間だけ個別公開承認を省略する／失効時に常時承認へ復帰する
- **証跡**: eligibility評価結果／候補digest／PO decision receipt／scope/expiry binding／失効検知／mode transitionと復帰証跡
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-AUTO-MODE-P: 適格性証跡とscope/期限へ束縛したPO enable receiptが両方有効な対象だけ個別承認を省略する （RST-AUTO-MODE-P）
  - `negative` RAC-AUTO-MODE-N: 機械適格判定だけ、PO receipt欠落、scope不一致、期限切れ、基準失効、金銭操作では常時承認を要求する （RST-AUTO-MODE-N）
  - `boundary` RAC-AUTO-MODE-B: 一媒体又は一operationだけのenableを他へ伝播せず、失効検知後の次操作から常時承認へ戻す （RST-AUTO-MODE-B）
- **PO個別質問**:
  - `RDQ-AUTO-MODE-DECISION-AUTHORITY-01` (`safety_policy`): resolver回答をPOが再確認し、有効化・継続・解除principal、scope、期限、再承認、基準失効時の復帰条件を閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:ba7eee51dc0305ecfa9a84cdb30970cbad985ebbc38556f479e09c17ddef39dd`

## RRF-AUTOMATED-PUBLISHING-ADMISSION — AUTOMATED-PUBLISHING-ADMISSION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000138 RDE-000144 RDE-000150 RDE-000154 RDE-000155
- **主体**: ユーザー／製品runtime
- **受益者**: 毎回承認せず自動運用を監督するユーザー
- **価値**: VPS UIで初回scopeを承認した後も成果物gateを維持して自動運用する
- **task**: activation scopeを確認し承認する／各成果物のquality/risk admissionを検査する／取消・権限喪失・重大rule変更又は停止条件成立時にwriteを停止する／停止後にscopeを再表示してre-activationする
- **workflow**: VPS inbox→scope確認→初回承認→自動運用→成果物gate→停止条件成立→明示re-activation待ち
- **対象範囲**: profile/media/account/operation単位activation／scope未指定時の対象媒体account既定／自動公開admission／取消・停止・re-activation
- **対象外**: 全媒体一括activation／毎回の公開承認／quality gate省略／固定期限の全対象一律強制
- **禁止事項**: machine eligibilityだけのactivation／scope外write／不合格成果物公開／停止後に毎回承認modeへ暗黙復帰してwriteを続けること
- **人間判断**: 初回activation、scope拡張、重大rule変更、取消、停止後re-activationはユーザー
- **副作用**: activation scope内の自動媒体write／停止条件成立時の外部write停止
- **証跡**: activation receipt／scope/revision binding／gate pass receipt／revocation/stop/re-activation negative test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-AUTO-PUBLISH-P: 初回承認scope内でgate合格成果物だけを毎回承認なしで実行する （RST-AUTO-PUBLISH-P）
  - `negative` RAC-AUTO-PUBLISH-N: 未承認、scope外、取消、権限喪失、重大rule変更、停止条件成立又はgate不合格の外部writeを拒否する （RST-AUTO-PUBLISH-N）
  - `boundary` RAC-AUTO-PUBLISH-B: 停止後は毎回承認modeへ戻さず対象scopeの明示re-activationまでwriteを停止する （RST-AUTO-PUBLISH-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:301b801a5a2ba20d718ac93ccdc67eb9b169df53a05cb7d148ac8f6a033e6981`

## RRF-BUSINESS-PROFILE-AUTHORIZATION — BUSINESS-PROFILE-AUTHORIZATION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000130 RDE-000131
- **主体**: PO／profile所有者／許可運用者
- **受益者**: 隔離された複数事業の所有者
- **価値**: stable profile IDでprincipal/resource/actionを隔離し越境を防ぐ
- **task**: profile membership/roleを確認しresource/actionを認可する
- **workflow**: profile選択→membership/role→resource/action認可→操作→profile束縛receipt
- **対象範囲**: profile lifecycle／membership/role／resource/action／横断集約／移管/削除
- **対象外**: 表示brand名を認可IDとすること／具体RBAC製品
- **禁止事項**: 暗黙共有／権限合算／cross-profile write／credential/data/evidence越境
- **人間判断**: membership、role、横断集約、移管、削除は許可principal
- **副作用**: 現段階は要求候補のみ
- **証跡**: authorization matrix／profile-bound receipt／cross-profile negative case／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-PROFILE-AUTH-P: stable profile IDとprincipal/resource/actionへ束縛した操作だけを許可する （RST-PROFILE-AUTH-P）
  - `negative` RAC-PROFILE-AUTH-N: 表示名一致、暗黙共有、権限合算、越境writeを拒否する （RST-PROFILE-AUTH-N）
  - `boundary` RAC-PROFILE-AUTH-B: 横断集約は各profileのread権限を満たしwriteへ昇格しない （RST-PROFILE-AUTH-B）
- **PO個別質問**:
  - `RDQ-BUSINESS-PROFILE-AUTHORIZATION-01` (`safety_policy`): profile lifecycle、membership/role、resource/action認可、横断集約、削除/移管、越境監査をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:05788e01eefe7d8a8eb91fc94e4d783f71fba6feb2f7067cd08908f42b0cf885`

## RRF-CONTENT-QUALITY-GATE-LEARNING — CONTENT-QUALITY-GATE-LEARNING

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000139 RDE-000145 RDE-000151
- **主体**: ユーザー／content生成agent／quality gate
- **受益者**: 確認負荷を減らすユーザーと品質を受けるaudience
- **価値**: 不合格成果物を人間へ流さずfeedbackを再利用可能なruleへ変えて、人に有用で独自性と根拠のある品質を継続改善する
- **task**: 成果物を検査する／不合格を有界回数で自動修正又は再生成する／解消不能時は公開せず停止する／feedbackをscope付きruleへ変換する／対象成果物を再検査する／独自価値とclaim-source対応を検査する
- **workflow**: 生成→gate→不合格時修正/再生成→再検査→合格時のみ次工程→feedback rule化→対象再検査
- **対象範囲**: 禁止語／表現／形式/型／根拠／対象audienceへの有用性／独自research/分析/経験／claim-source対応と鮮度／誇張しない見出し／structured feedback／rule revision／未公開成果物再検査
- **対象外**: 製品codeへのrule hard-code／非対応媒体の公開済み成果物変更
- **禁止事項**: 不合格成果物の人間review投入又は公開／無限再生成／scope未指定feedbackの全体適用／順位操作目的の大量生成／query variationごとの低価値量産／付加価値のないsource要約
- **人間判断**: feedback内容と明示scopeはユーザー。risk必須ruleを最優先し、媒体account rule、個別feedbackの順で合成する。risk境界内の通常rule更新はAI
- **副作用**: 対応媒体のgate合格済み公開成果物へのupdate-in-place
- **証跡**: rule revision／fixture／gate result／regeneration history／retry exhaustion/stop receipt／claim-source map／originality/value assessment／scope-bound update receipt／source:<https://developers.google.com/search/docs/fundamentals/creating-helpful-content／source:https://developers.google.com/search/docs/fundamentals/ai-optimization-guide>
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-CONTENT-GATE-P: 独自価値、claim-source対応及び対象audienceへの有用性を含むgateで不合格を人間確認前に再生成し、合格成果物だけを次工程へ進める （RST-CONTENT-GATE-P）
  - `negative` RAC-CONTENT-GATE-N: 不合格公開、scope外rule適用、順位操作目的の低価値量産及び非対応媒体の公開済み変更を拒否する （RST-CONTENT-GATE-N）
  - `boundary` RAC-CONTENT-GATE-B: update-in-place能力不明又は非対応なら公開済み成果物へ通知を含め何もしない （RST-CONTENT-GATE-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:dd4a62c3fca042428bd43ac22f65cda29a1b0f7a8a8c5f6bd2bd202590a2a7ec`

## RRF-CONTENT-RISK-CLASSIFICATION — CONTENT-RISK-CLASSIFICATION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000140 RDE-000146 RDE-000152
- **主体**: ユーザー／risk classification agent／quality gate
- **受益者**: 安全で信頼できる情報を受けるaudienceとユーザー
- **価値**: case-by-caseの好みを反映しつつ、人の健康、金融上の安定、安全又は社会の福祉に影響するYMYL相当contentを厳格に扱う
- **task**: content/claimをrisk分類する／健康・金融安定・安全・社会的福祉への影響を評価する／必須gateを選ぶ／個別の好みruleを合成する／分類と検査根拠を保存する
- **workflow**: content/claim抽出→影響軸別risk分類→必須gate→好みrule合成→検査→evidence
- **対象範囲**: content/claim risk／健康／金融上の安定／安全／社会の福祉/well-being／YMYL／根拠/鮮度/経験/専門性/表現/safety gate／case-by-case preference
- **対象外**: ブランド一律risk固定／好みによる最低基準緩和
- **禁止事項**: feedback又は成長KPIによる必須risk gate迂回／不確実時に低riskへ推測しない
- **人間判断**: ユーザーは案件、成果物又はclaimごとの好みを指定できる
- **副作用**: 適用gate集合とcontent可否の変更
- **証跡**: classification rationale／impact-axis assessment／rule composition／risk gate result／uncertainty negative test／source:<https://developers.google.com/search/docs/fundamentals/creating-helpful-content>
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-CONTENT-RISK-P: claim riskに応じた必須gateと個別好みを合成して検査する （RST-CONTENT-RISK-P）
  - `negative` RAC-CONTENT-RISK-N: 好み、feedback又はKPIでYMYL等の必須gateを弱めることを拒否する （RST-CONTENT-RISK-N）
  - `boundary` RAC-CONTENT-RISK-B: risk分類が不確実なら低riskへ推測せず安全側の再調査又は停止にする （RST-CONTENT-RISK-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:9eb249e88e6fa2e2cd469a0ace6b26608fb4596b1c35843c5b7ad6fede6bd65e`

## RRF-CONTRACT-SEMANTIC-DESCENT-V2 — CONTRACT-SEMANTIC-DESCENT-V2

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000103 RDE-000104
- **主体**: PO／要求分析者／AC/TC作成者
- **受益者**: 責務と権限を推測せず実装・検証する担当者
- **価値**: 要求からAC/TCまで意味軸・scope・PO判断receiptを型付きで閉じる
- **task**: 直接必須fieldを決める／継承可能/禁止fieldを決める／14 HJ経路をreceiptへ降下する／mutationで欠落を拒否する
- **workflow**: BR意味→REQ正規化→FR/SR/NFR/MR/FN降下→AC/TC反証→PO receipt検査
- **対象範囲**: actor／beneficiary／value／workflow／scope／prohibition／human judgement／side effect／evidence／phase／decision receipt
- **対象外**: target IDをbusiness scopeとみなすこと／agent審査をPO判断とみなすこと
- **禁止事項**: 欠落fieldを実装者が推測しない／機械判定でPO decisionを代替しない
- **人間判断**: 意味fieldの継承可否と各PO判断点はPOが凍結
- **副作用**: 現段階は要求契約の候補化のみ
- **証跡**: schema／継承mapping／14 HJ経路のreceipt AC/TC／negative mutation／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-SEMANTIC-DESCENT-P: 全要求層が直接field又は明示継承を持ちPO判断がreceiptまで追跡できる （RST-SEMANTIC-DESCENT-P）
  - `negative` RAC-SEMANTIC-DESCENT-N: 意味欠落、target-as-scope、agent-as-POを拒否する （RST-SEMANTIC-DESCENT-N）
  - `boundary` RAC-SEMANTIC-DESCENT-B: 一部継承可能でもscope/HJ/side-effect/phaseの暗黙継承を許さない （RST-SEMANTIC-DESCENT-B）
- **PO個別質問**:
  - `RDQ-CONTRACT-SEMANTIC-DESCENT-V2-01` (`requirements_policy`): 直接必須fieldと継承可能/禁止fieldをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:148b0213b223e62c82cafb565ae86c8cc1c452a282a3bd6d1f3c7a5f65ed8680`

## RRF-DISCORD-COMMUNITY-MARKETING-ROUTE — DISCORD-COMMUNITY-MARKETING-ROUTE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000137 RDE-000143 RDE-000149
- **主体**: 媒体account所有者／Discord community運用者／Discord Bot
- **受益者**: Discord communityとmarketing運用者
- **価値**: Discordを製品通知から分離したcommunity marketing媒体として利用する
- **task**: community contentを投稿する／応答とmoderationを行う／反応を計測する
- **workflow**: community企画→quality/risk gate→Bot operation→反応取得→KPI還流
- **対象範囲**: community投稿／応答／moderation／計測
- **対象外**: 製品承認通知／運用通知／開発PR通知
- **禁止事項**: self-bot／個人user account無人操作／通知credential又はchannel共有
- **人間判断**: community方針とmoderation境界は媒体account所有者
- **副作用**: Discord communityへの許可投稿又は応答
- **証跡**: purpose-specific route／Bot/account/guild/channel binding／operation receipt／cross-purpose negative test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-DISCORD-COMMUNITY-P: Botと許可guild/channel/operationを束縛してcommunity operationを記録する （RST-DISCORD-COMMUNITY-P）
  - `negative` RAC-DISCORD-COMMUNITY-N: 通知用途への送信、self-bot、個人account操作及び用途間credential共有を拒否する （RST-DISCORD-COMMUNITY-N）
  - `boundary` RAC-DISCORD-COMMUNITY-B: guild/channel/operation又はmoderation境界が不明なら当該operationを実行しない （RST-DISCORD-COMMUNITY-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:70c0b5ab8cf5b8a163454726f2b18a0e4d4db23eeff4974409ae260358d81134`

## RRF-DISCORD-MULTI-PURPOSE-BOUNDARIES — DISCORD-MULTI-PURPOSE-BOUNDARIES

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000005 RDE-000022 RDE-000023 RDE-000041 RDE-000042
- **主体**: PO／将来のDiscord通知adapter／将来のDiscord媒体Bot
- **受益者**: 用途混同を避けるPOとコミュニティ
- **価値**: 承認・運用通知・媒体投稿・PR通知の誤送信と誤決定を防ぐ
- **task**: 用途別policyとprincipalを登録する／別channel/accountへ用途別送信する
- **workflow**: 将来要求承認→用途別allow-list→送信→用途別receipt
- **対象範囲**: 将来Discord deep-link通知／将来Discord媒体投稿の分離境界
- **対象外**: 初期baseline／Discord interactionによる承認／self-bot／開発PR通知の製品接続
- **禁止事項**: 用途間でservice/operation/account/channel/evidenceを共有しない／個人user accountを無人操作しない
- **人間判断**: 将来adapterと媒体capabilityの採用は別々にPO判断
- **副作用**: 現時点なし。将来のDiscord送信はdeferred
- **証跡**: deferred理由／再開条件／用途別negative route test
- **phase**: `deferred`
- **受入候補**:
  - `positive` RAC-DISCORD-BOUNDARY-P: 将来採用時に用途別tuple・principal・channel・receiptだけを許可する （RST-DISCORD-BOUNDARY-P）
  - `negative` RAC-DISCORD-BOUNDARY-N: 承認channel・媒体channel・PR通知channelの共有とself-botを拒否する （RST-DISCORD-BOUNDARY-N）
  - `boundary` RAC-DISCORD-BOUNDARY-B: 未採用・未知tuple・allow-list外・用途不一致は送信せずdeferredを維持する （RST-DISCORD-BOUNDARY-B）
- **PO個別質問**:
  - `RDQ-DISCORD-MULTI-PURPOSE-BOUNDARIES-01` (`deferred_resume`): 初期baseline外のため採用時期・business value・account/channel tupleは未決 （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:d965a769ec3df01c423adc54ec410586a2069e5b2a03aedb496b31cf905f1840`

## RRF-EXTERNAL-BROWSER-AUTOMATION-ROUTE — EXTERNAL-BROWSER-AUTOMATION-ROUTE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000136 RDE-000142 RDE-000148
- **主体**: 媒体account所有者／connector管理者／製品runtime
- **受益者**: 許可経路で媒体を運用するユーザー
- **価値**: 公式経路を優先しつつ必要なPlaywright automationとbrowser確認をoperation単位で安全に使う
- **task**: 公式API/MCP能力を判定する／許可時だけPlaywright fallback又は確認を行う
- **workflow**: operation要求→API/MCP確認→route許可判定→実行→browser確認→receipt
- **対象範囲**: 公式API／公式MCP／Playwright fallback／browser結果確認
- **対象外**: 他browser engine／経路不明operation
- **禁止事項**: 媒体全体へのbrowser write一括許可／利用規約又はcredential境界の推測
- **人間判断**: write routeの採用と残余riskは対象登録時の許可主体
- **副作用**: 許可された媒体read又はwrite
- **証跡**: route decision／principal/effect binding／execution/confirmation receipt／negative route test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-BROWSER-ROUTE-P: 公式API/MCPを優先し許可operationだけPlaywright fallback又は確認を実行する （RST-BROWSER-ROUTE-P）
  - `negative` RAC-BROWSER-ROUTE-N: route、principal、effect又は規約境界が未確定のbrowser writeを拒否する （RST-BROWSER-ROUTE-N）
  - `boundary` RAC-BROWSER-ROUTE-B: 公式routeの能力不足時もfallback未許可なら実行せずdeferredを維持する （RST-BROWSER-ROUTE-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:ff2a436b7c1d9c68a76a21184a0edf19021cde12208b3c98d1ced474c97868a5`

## RRF-FR-16-NOTIFICATION-BOUNDARY — FR-16-NOTIFICATION-BOUNDARY

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000002 RDE-000015 RDE-000016 RDE-000036 RDE-000037
- **主体**: 製品kernel／PO
- **受益者**: 異常を安全に監督するPO
- **価値**: 安全停止を通知障害から独立させつつUI内で異常を見逃さない
- **task**: 異常時に安全停止する／通知attemptをinboxへ記録する／再開/中止を判断する
- **workflow**: 異常検知→安全停止永続化→inbox記録attempt→recorded/failed/retry_exhausted永続化→PO判断
- **対象範囲**: 安全停止／UI内operational inbox／記録成功/失敗/retry exhaustion receipt
- **対象外**: 投稿可否承認／外部通知adapter配送／Discord送信／媒体投稿／開発PR通知
- **禁止事項**: 通知記録失敗で停止をrollbackしない／通知からapprove/rejectを導出しない／inbox記録と外部配送を同じ結果軸にしない
- **人間判断**: 停止後の再開又は中止はPO
- **副作用**: 製品状態の停止／UI内通知行の追加
- **証跡**: 停止遷移／inbox記録attempt/recorded/failed/retry/retry_exhausted receipt
- **phase**: `S0`
- **受入候補**:
  - `positive` RAC-FR-16-NOTIFICATION-P: 異常時に停止を先に永続化しUI内inbox記録attemptと記録結果を別証跡化する （RST-FR-16-NOTIFICATION-P）
  - `negative` RAC-FR-16-NOTIFICATION-N: inbox書込み失敗でも停止状態をrollbackせずfailed receiptを残す （RST-FR-16-NOTIFICATION-N）
  - `boundary` RAC-FR-16-NOTIFICATION-B: 重複event・retry上限・再開判断待ちで二重通知や自動再開を起こさない （RST-FR-16-NOTIFICATION-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:6fa17dcd5642c0490e57a47ad1268d0bdfc2913ec0720cfe9542e75f64204c3a`

## RRF-FR-SLICE-AUTHORITY-ALIGNMENT — FR-SLICE-AUTHORITY-ALIGNMENT

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000004 RDE-000019 RDE-000020 RDE-000021 RDE-000038 RDE-000039 RDE-000040
- **主体**: 要求管理者／PO／実装計画者
- **受益者**: 正しい導入順でreleaseするPOと開発者
- **価値**: 複合責務を厳密phaseへ分割し、FR/FN/AC/TCの実装順逆転を防ぐ
- **task**: 複合FRを責務分割する／各責務へ厳密phaseを付ける／FN/AC/TCを付け直す
- **workflow**: 意味差分検出→責務分割→phase決定→trace再降下→境界test
- **対象範囲**: FR-16/42/44/55と同型の複合責務／FR/FN/AC/TC phase
- **対象外**: S1+/S3+を実装phaseとして使うこと
- **禁止事項**: 単一FRに異なるphaseの責務を混在させない／ID維持だけで意味同値とみなさない
- **人間判断**: 責務境界とrelease phaseはPOが要求価値から確認
- **副作用**: 旧IDの分割・supersessionとtrace再構成
- **証跡**: 責務別semantic digest／phase整合／bidirectional trace／境界test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-SLICE-P: 意味軸・根拠・許可境界を満たす対象だけを次工程へ進める （RST-SLICE-P）
  - `negative` RAC-SLICE-N: 未回答・未許可・意味trace欠落又は証跡不足をfail-closeで拒否する （RST-SLICE-N）
  - `boundary` RAC-SLICE-B: 一部だけ成立する場合は責務を分割又はdeferred/pivotし全体成立に読み替えない （RST-SLICE-B）
- **PO個別質問**:
  - `RDQ-FR-SLICE-AUTHORITY-ALIGNMENT-01` (`authority_choice`): 現行32 fault（17 FR）のFR↔FN/AC phase差分を責務分割表へ落とし、旧IDのsupersession規則をPO確認する （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:e4aa50d8443c6e460e4eb338bea2b419ed3ac00614188bce871177e94f6e162b`

## RRF-GENAI-EXECUTION-ROUTE — GENAI-EXECUTION-ROUTE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000006 RDE-000024 RDE-000025 RDE-000043 RDE-000044
- **主体**: 製品runtime／PO／attended運用者
- **受益者**: 規約違反やvendor lock-inを避ける運用者
- **価値**: provider-neutralな許可経路で生成し、禁止されたconsumer Web UI自動化を排除する
- **task**: provider capabilityを登録する／許可API adapterで生成する／不能時に停止又はattended manualへ渡す
- **workflow**: capability/規約/quota確認→API実行→証跡→不能時fail-close/attended handoff
- **対象範囲**: provider-neutral API adapter／任意CLI adapter／attended manual fallback
- **対象外**: Codex/Claudeの必須runtime依存／consumer Web UI無人操作
- **禁止事項**: 非許可Web UI自動化へfallbackしない／credential/quotaを迂回しない
- **人間判断**: adapter採用とattended生成物の採否はPO/運用者
- **副作用**: 許可providerへの生成request／attended handoff
- **証跡**: provider/version/terms check／request/response digest／quota／human handoff receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-GENAI-P: 意味軸・根拠・許可境界を満たす対象だけを次工程へ進める （RST-GENAI-P）
  - `negative` RAC-GENAI-N: 未回答・未許可・意味trace欠落又は証跡不足をfail-closeで拒否する （RST-GENAI-N）
  - `boundary` RAC-GENAI-B: 一部だけ成立する場合は責務を分割又はdeferred/pivotし全体成立に読み替えない （RST-GENAI-B）
- **PO個別質問**:
  - `RDQ-GENAI-EXECUTION-ROUTE-01` (`deferred_resume`): resolver回答をPOが再確認し、初期provider/capabilityとcost上限を媒体PoCで決める （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:9787cd7d0013c25bd58822f097ac75c243984c2f612e45f4ccd609e5d29d53d4`

## RRF-L0-NORTH-STAR-AUTHORITY-NORMALIZATION — L0-NORTH-STAR-AUTHORITY-NORMALIZATION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000111 RDE-000112
- **主体**: PO／事業責任者／要求分析者
- **受益者**: 一意なnorth-starから要求を導出する全担当者
- **価値**: 旧L0の事業価値と旧手段を分離しVPS/UI/API/provider-neutralな新baselineへ一方向再降下する
- **task**: 旧L0 clauseを棚卸しする／価値と手段を分離する／維持/置換/deferredを決める／scope別supersessionとL1 traceを作る
- **workflow**: 旧L0 clause棚卸し→価値/手段分離→維持/置換/deferred決定→新L0 freeze→L1以降再降下
- **対象範囲**: 事業目的／価値／human interface／external route／provider dependency／auto-mode／media scope／runtime placement
- **対象外**: 旧L0の無承認手編集／L2以降の設計選択
- **禁止事項**: 下位ADRだけでL0全体を暗黙上書きしない／旧手段を事業価値と同一視しない
- **人間判断**: 維持・置換・deferred・supersessionはPOが決定
- **副作用**: 現段階はnorth-star要求候補のみ
- **証跡**: clause disposition map／新L0 digest／scope別supersession／L1 trace／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-L0-AUTH-P: 全旧clauseが維持・置換・deferredの一つにPO決定され新L0からL1へtraceする （RST-L0-AUTH-P）
  - `negative` RAC-L0-AUTH-N: 旧Discord/browser/provider等を下位ADRだけで暗黙置換又はcurrent利用することを拒否する （RST-L0-AUTH-N）
  - `boundary` RAC-L0-AUTH-B: 事業価値を維持しても実現手段は独立に再決定し未決手段をdeferredとする （RST-L0-AUTH-B）
- **PO個別質問**:
  - `RDQ-L0-NORTH-STAR-AUTHORITY-NORMALIZATION-01` (`authority_choice`): charter v0.4 clauseごとの維持・置換・deferredとscope別supersessionをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:d15ab07c6a88ca37e654d8277b009e02ebcec425b310d6b27bd438e67b2024ce`

## RRF-LEGACY-MEDIA-ADMISSION-INVENTORY — LEGACY-MEDIA-ADMISSION-INVENTORY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000125 RDE-000126
- **主体**: PO／媒体運用者／connector管理者
- **受益者**: 未承認の外部writeを避けるPOと媒体account所有者
- **価値**: 旧MRを一旦全件deferredへ閉じ、新baselineの意味と受入を凍結したoperationだけ再開する
- **task**: 旧MRを全件棚卸しする／安全側deferredへ隔離する／operation単位で意味fieldとAC/TCを閉じる
- **workflow**: 旧MR棚卸し→全件deferred→媒体operation別意味確認→PO freeze→個別再開
- **対象範囲**: 旧MR 54件／capability status／execution mode／principal／effect／policy／credential／quota／evidence／AC/TC
- **対象外**: 旧connection/actionsからの実行許可推測／一括媒体有効化
- **禁止事項**: 旧MR本文だけでenabledにしない／一媒体のgreenを別媒体へ流用しない
- **人間判断**: 業務価値、route、status、risk、再開はPO
- **副作用**: 現段階は要求inventoryのみ
- **証跡**: 全54件収載／operation別意味field／三極性AC/TC／PO receipt
- **phase**: `requirements`
- **legacy media admission**: 54 MR ／ default=`deferred` ／ unresolved=business_value／execution_mode／principal／effect／policy_category／credential_scope／quota／evidence／acceptance_trace ／ reason=旧MRは全件revalidation対象であり、旧connection/actions/safety本文から新baselineの実行許可を推測しない
- **受入候補**:
  - `positive` RAC-LEGACY-MEDIA-P: 全旧MRをdeferredとして収載し意味とAC/TCを凍結したoperationだけ再開する （RST-LEGACY-MEDIA-P）
  - `negative` RAC-LEGACY-MEDIA-N: 棚卸し漏れ、旧本文からのenabled推測又は意味field未閉包の再開を拒否する （RST-LEGACY-MEDIA-N）
  - `boundary` RAC-LEGACY-MEDIA-B: 一部operationだけ成立する場合はそのoperationだけ再開し媒体全体をenabledにしない （RST-LEGACY-MEDIA-B）
- **PO個別質問**:
  - `RDQ-LEGACY-MEDIA-ADMISSION-INVENTORY-01` (`release_scope`): 各媒体operationのstatus、公式route、principal、effect、policy、credential、quota、evidence、AC/TCをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:bfdc75e655885849c275411a34b6eee6c1dc81c0abc14926b1496ec465816a58`

## RRF-MEDIA-POC-SCRUM-RELEASE — MEDIA-POC-SCRUM-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000073 RDE-000074 RDE-000075 RDE-000076 RDE-000077 RDE-000078 RDE-000079 RDE-000082 RDE-000095
- **主体**: PO／媒体運用者／Full V delivery team／製品runtime
- **受益者**: 媒体ごとの危険を隔離して段階導入するPO／マーケティング運用者
- **価値**: 媒体ごとの要求をFull Vで閉じ、受入済みcapabilityだけを段階releaseする
- **task**: 媒体/capability要求をFull Vへ降下する／WordPressをコンテンツDBとして登録・取得・更新・公開する／対象が概ね決まった段階incrementだけScrum deliveryする／S4で受入・却下・pivot・停止を判断する
- **workflow**: Full V-model要求/設計→WordPress content DB/publication release→V設計＋Scrum実装Hybrid increment→S4→Scrum Reverse SR0-SR4→V-pair closure→別の保守/security release
- **対象範囲**: Full V-model／WordPress content database/publication release unit／content CRUD/stable ID/publication/evidence increment／対象確定後のV設計＋Scrum実装Hybrid／S4 decision／Scrum Reverse SR0-SR4
- **対象外**: 全媒体一括承認／Discovery/PoCの標準工程化／PoC成功だけによる本番有効化／未検証経路の横展開／基盤・運用保守／セキュリティ保守
- **禁止事項**: ScrumをDiscovery/PoCと同一視しない／PoCと本番のcredential/data/write policyを共有しない／S3 greenをPO判断の代替にしない／未検証capabilityをenabledにしない
- **人間判断**: POがrelease unitごとにconfirmed/rejected/pivot/stopを決定する
- **副作用**: 要求で許可された検証環境への操作／承認済みrelease unitだけの本番有効化
- **証跡**: source freshness／V-pair closure／increment verification／positive/negative/boundary結果／acceptance gap／residual risk／PO S4 receipt／Scrum Reverse SR0-SR4 trace
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=1 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=なし ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-MEDIA-POC-SCRUM-P: Full V設計、increment検証、PO S4 receipt、Scrum Reverse SR0-SR4、release candidate V-pair closureを持つrelease unitだけを正本へ昇格する （RST-MEDIA-POC-SCRUM-P）
  - `negative` RAC-MEDIA-POC-SCRUM-N: Full V closure不足、必要と判定したDiscovery未実施、証跡不足、PO未決、又は別媒体から推測したcapabilityを本番enabledとして拒否する （RST-MEDIA-POC-SCRUM-N）
  - `boundary` RAC-MEDIA-POC-SCRUM-B: 一部capabilityだけが成立する場合はrelease unitを分割又はpivotし、媒体全体を一括acceptedにしない （RST-MEDIA-POC-SCRUM-B）
- **PO個別質問**:
  - `RDQ-MEDIA-POC-SCRUM-RELEASE-01` (`safety_policy`): Discoveryを使用する場合の検証環境と本番account/domain/data/credential/write昇格境界を閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:fb3b0cad4ecc4a915e10753a4d2305008083cfd10671671b8333f5655eac3dc2`

## RRF-NFR-BUSINESS-AUTHORITY — NFR-BUSINESS-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000105 RDE-000106
- **主体**: PO／品質責任者／運用者
- **受益者**: 法規・可用性・安全性を満たす利用者と運用者
- **価値**: NFRをstable business rootと測定・failure/recoveryへ接続する
- **task**: NFRごとのBR/REQ rootを決める／測定/閾値/phaseを決める／failure/recoveryをAC/TC化する／初期対象外をdeferred化する
- **workflow**: business risk/value→BR/REQ→NFR→measurement/threshold→failure/recovery→AC/TC
- **対象範囲**: NFR-1〜11／stable BR/REQ／measurement／threshold／failure／recovery／evidence／phase
- **対象外**: 節番号又はrisk IDだけを要求根拠とすること
- **禁止事項**: AC/TC存在だけで品質受入済みとしない／他NFRをstable business rootの代用にしない
- **人間判断**: 品質閾値・残余risk・deferred範囲はPOが判断
- **副作用**: 現段階は要求再接続のみ
- **証跡**: BR→REQ→NFR双方向trace／測定と閾値／recovery AC/TC／deferred再開条件／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-NFR-AUTH-P: 各NFRがstable BR/REQ、測定、閾値、phase、failure/recoveryを持つ （RST-NFR-AUTH-P）
  - `negative` RAC-NFR-AUTH-N: root不明又は測定不能NFRを受入済みにしない （RST-NFR-AUTH-N）
  - `boundary` RAC-NFR-AUTH-B: N/A又は将来NFRは理由・risk・再開条件付きdeferredとする （RST-NFR-AUTH-B）
- **PO個別質問**:
  - `RDQ-NFR-BUSINESS-AUTHORITY-01` (`authority_choice`): NFR-1〜11のstable root・actor・scope・phase・deferred範囲をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:74ce0caacb64c40ad8e91c353209904ec6a3f01cc0b254006ab754a101ec31b9`

## RRF-OFFICIAL-API-ROUTE-AUTHORITY — OFFICIAL-API-ROUTE-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000008 RDE-000026 RDE-000027 RDE-000045 RDE-000046
- **主体**: 製品runtime／connector管理者／PO
- **受益者**: 規約適合した安定経路を使う媒体運用者
- **価値**: 媒体ごとの公式automation interfaceを安全性・証跡・quotaで選び、危険なbrowser fallbackを防ぐ
- **task**: capability routeを登録する／source freshnessを検査する／許可routeを選ぶ／不能時に停止/attendedへ渡す
- **workflow**: 媒体/capability→公式source検証→allow-list route→実行→evidence→fallback判定
- **対象範囲**: 公式API／公式MCP／official export／attended manual
- **対象外**: 一律MCP-first／無人consumer browser／有償経路の暗黙選択
- **禁止事項**: 未知routeを実行しない／credential/rate/cost制約を迂回しない
- **人間判断**: 有償経路・attended fallback・新route採用はPO/許可運用者
- **副作用**: 公式外部serviceへのread/write／attended handoff
- **証跡**: source/version/terms freshness／policy tuple／quota／operation receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-ROUTE-P: 意味軸・根拠・許可境界を満たす対象だけを次工程へ進める （RST-ROUTE-P）
  - `negative` RAC-ROUTE-N: 未回答・未許可・意味trace欠落又は証跡不足をfail-closeで拒否する （RST-ROUTE-N）
  - `boundary` RAC-ROUTE-B: 一部だけ成立する場合は責務を分割又はdeferred/pivotし全体成立に読み替えない （RST-ROUTE-B）
- **PO個別質問**:
  - `RDQ-OFFICIAL-API-ROUTE-AUTHORITY-01` (`release_scope`): resolver回答をPOが再確認し、媒体別PoCで初期route registryを作る （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:f451dc479d0974fac560a2606fe6574b5765d058cfaff9c5f34058380f08cd73`

## RRF-PRODUCT-STATE-AUTHORITY — PRODUCT-STATE-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000128 RDE-000129
- **主体**: PO／運用者／製品runtime
- **受益者**: 一貫した状態を確認するPOと運用者
- **価値**: UI、worker、通知の状態確定を一つのrevision付き正本へ集約する
- **task**: 状態を読み、対象とrevisionを再検証し、許可更新とreceiptを残す
- **workflow**: 状態読取→対象/revision再検証→許可更新→receipt→全consumerから再読取
- **対象範囲**: 製品状態／revision/CAS／owner／更新principal／保持/競合/復旧/監査
- **対象外**: 具体DB/API設計／UI又は通知のlocal stateを正本とすること
- **禁止事項**: stale write／複数正本／UI/worker/通知による独自確定
- **人間判断**: 状態分類、保持、競合解決、復旧riskはPO
- **副作用**: 現段階は要求候補のみ
- **証跡**: state authority map／CAS negative case／recovery/receipt／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-PRODUCT-STATE-P: 現revisionと許可principalへ束縛した更新だけを唯一正本へ反映する （RST-PRODUCT-STATE-P）
  - `negative` RAC-PRODUCT-STATE-N: stale revision、未知owner、UI/通知local stateからの確定を拒否する （RST-PRODUCT-STATE-N）
  - `boundary` RAC-PRODUCT-STATE-B: 競合、保存不能、復旧不成立では既存正本を維持してfail-closeする （RST-PRODUCT-STATE-B）
- **PO個別質問**:
  - `RDQ-PRODUCT-STATE-AUTHORITY-01` (`authority_choice`): 製品状態の種類、owner、revision/CAS、更新principal、保持、競合、復旧、監査境界をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:aaf345a856ee3ae219d0764d888f9ac43b239ea16fb959e5264531785c5d53c9`

## RRF-RATE-QUOTA-COST-AUTHORITY — RATE-QUOTA-COST-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000134 RDE-000135
- **主体**: PO／account所有者／connector管理者
- **受益者**: 費用とaccount安全性を管理するPO
- **価値**: rate、quota、read cap、cost、retryを別型で管理しcap回避と予期せぬ課金を防ぐ
- **task**: 制限sourceを取得しscope/window/valueを評価して実行又は拒否する
- **workflow**: 制限取得→分類→予算/上限評価→実行又は拒否→receipt→再評価
- **対象範囲**: provider quota／account cap／read safety cap／cost ceiling／retry/backoff/retry-after
- **対象外**: ブラウザ人間様待機をAPI quotaとみなすこと
- **禁止事項**: 複数accountによるcap回避／retry-after無視／費用上限なし有償経路
- **人間判断**: cost ceiling、有償例外、未知値の再開はPO
- **副作用**: 現段階は要求候補のみ
- **証跡**: typed limit registry／source/window/scope／boundary tests／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-RATE-QUOTA-P: 根拠、scope、window、値、費用上限が有効なoperationだけ実行する （RST-RATE-QUOTA-P）
  - `negative` RAC-RATE-QUOTA-N: 未知値、cap回避、retry-after無視、上限なし有償経路を拒否する （RST-RATE-QUOTA-N）
  - `boundary` RAC-RATE-QUOTA-B: 上限到達又は分類不明では対象operationだけ停止し他scopeへ値を流用しない （RST-RATE-QUOTA-B）
- **PO個別質問**:
  - `RDQ-RATE-QUOTA-COST-AUTHORITY-01` (`quality_target`): rate/quota/read cap/cost/retryの分類、値source、window、scope、更新、超過時挙動、未知値のdeferred条件をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:6500b2100a24a610c879a85c736029e95f29834234f239502d95be1db9e80c3c`

## RRF-REQ-AUTHORITY-NORMALIZATION — REQ-AUTHORITY-NORMALIZATION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000097 RDE-000098 RDE-000124 RDE-000127
- **主体**: PO／要求分析者／要件エンジン
- **受益者**: 一意な要求根拠を使う設計者と実装者
- **価値**: REQ本文・出典・下流・充填を一つのJSON正本へ凍結しBRから下流への意味根拠を一意にする
- **task**: 15 REQ・19 fieldの差分を意味選択する／JSON正本を凍結する／Markdownを生成view化する／traceを再検証する
- **workflow**: 差分検出→意味選択→JSON正本freeze→Markdown生成→trace再検証
- **対象範囲**: REQ本文／source／downstream trace／fill route／JSON/Markdown authority
- **対象外**: 旧Markdownの手編集／FR/NFRの自動採用／製品runtime変更
- **禁止事項**: 同一ID又は件数だけで意味同値としない／JSONとMarkdownを並行正本にしない
- **人間判断**: 正規意味とauthority cutoverはPOが決定
- **副作用**: 要求authorityの変更だけ。現段階でruntime変更なし
- **証跡**: 19 fieldのPO決定／単一JSON digest／生成Markdown／trace差分0／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-REQ-AUTH-P: POが全実質差分を決定し単一JSONからMarkdownを生成してtrace差分0となる （RST-REQ-AUTH-P）
  - `negative` RAC-REQ-AUTH-N: 未決差分、独立手編集view、又はID件数一致だけのcutoverを拒否する （RST-REQ-AUTH-N）
  - `boundary` RAC-REQ-AUTH-B: 表記同値は正規化するが本文・source・downstreamの実質差を消さない （RST-REQ-AUTH-B）
- **PO個別質問**:
  - `RDQ-REQ-AUTHORITY-NORMALIZATION-01` (`authority_choice`): REQの本文・出典・下流・充填を正規化し、唯一のJSON正本と生成Markdown境界をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:508921e634a6aad46f9f3b3a35bc48083ed85f03f9394b212bd2f5aa30dc7e05`

## RRF-REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE — REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000009 RDE-000014 RDE-000028 RDE-000029 RDE-000047 RDE-000048
- **主体**: PO／要求分析者／要件エンジン
- **受益者**: 意味欠落のない要求を承認するPOと実装者
- **価値**: 候補から仕様化までのunknownと意味軸を機械追跡し、要約又は同一IDの二重意味による承認を防ぐ
- **task**: candidateを記録する／unknownへquestionを束縛する／12意味軸と品質観点を閉じる／同一IDの本文・出典・trace・充填を一意化する／反例/境界を定義する
- **workflow**: candidate→question/observation/prototype→refinement→正本選択/生成view化→admission→PO decision→freeze
- **対象範囲**: actor/value/workflow/scope/prohibition/HJ/side-effect/evidence/phase／security/privacy/accessibility/performance/availability/recovery/operation/migration/rollback／REQ JSON/Markdown authorityとsemantic drift
- **対象外**: AI回答だけによるPO決定／一括承認／正本の自動mutation／意味未確認の文字列同期
- **禁止事項**: 未回答unknownをspecifiedにしない／positive caseだけで承認しない／同一ID・件数一致だけで意味同値とみなさない／JSONとMarkdownを独立正本として並立させない
- **人間判断**: 価値・範囲・risk・正本意味・採否・freezeはPO
- **副作用**: 要求authority cutoverだけ。製品runtimeを直接変更しない
- **証跡**: event prefix／source-set digest／semantic digest／REQ field差分0／単一JSON正本からの生成view／三極性AC／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-DISCOVERY-P: 意味軸・根拠・許可境界を満たす対象だけを次工程へ進める （RST-DISCOVERY-P）
  - `negative` RAC-DISCOVERY-N: 未回答・未許可・意味trace欠落又は証跡不足をfail-closeで拒否する （RST-DISCOVERY-N）
  - `boundary` RAC-DISCOVERY-B: 一部だけ成立する場合は責務を分割又はdeferred/pivotし全体成立に読み替えない （RST-DISCOVERY-B）
- **PO個別質問**:
  - `RDQ-REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE-01` (`requirements_policy`): resolver回答をPOが再確認し、品質閾値とN/A許容規則を閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:18f1a8f4bdc73401ea669fa633b4f9bf40cfc7f0c36f8c524a66cdeaa78b351b`

## RRF-RESEARCH-LED-CONTENT-GROWTH — RESEARCH-LED-CONTENT-GROWTH

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000141 RDE-000147 RDE-000153
- **主体**: ユーザー／research agent／strategy agent／媒体運用agent
- **受益者**: 成長する事業と各媒体のaudience
- **価値**: researchとmarketing funnelに基づき媒体の役割を決め、人に有用な独自価値を保ちながらKPIから継続的に成長する
- **task**: 市場と競合をresearchする／source/取得時点/claim/鮮度を記録する／既存情報へ追加する独自価値を定義する／成長仮説とfunnelを作る／媒体/成果物へ役割を割り当てる／KPIを仮説へ還流する
- **workflow**: source付きresearch→独自価値と成長仮説→商品/offer別funnel→媒体/成果物役割→制作/公開→KPI→仮説更新
- **対象範囲**: 市場/検索/競合/trend research／source provenance/freshness／独自経験/比較/検証/分析／marketing funnel／媒体複数役割／商品/offer capability／KPI feedback
- **対象外**: 全媒体一律売上KPI／初期/中期の有料集客
- **禁止事項**: 権限不明な商品/offer変更／成長を理由にrisk/legal/media policyを迂回／検索順位操作だけを目的にした量産／既存sourceの付加価値なき言い換え
- **人間判断**: 商品/offer登録時の変更authorityと超後期有料集客再開はユーザー
- **副作用**: 許可対象の商材選定/差替えと媒体operation
- **証跡**: source/claim/freshness付きresearch evidence／original value statement／hypothesis／funnel/role binding／KPI result／learning revision／source:<https://developers.google.com/search/docs/fundamentals/creating-helpful-content／source:https://developers.google.com/search/docs/fundamentals/ai-optimization-guide>
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-RESEARCH-GROWTH-P: source/claim/freshnessと独自価値を持つresearch仮説から媒体役割と成果物を作り、役割KPIを次の仮説へ還流する （RST-RESEARCH-GROWTH-P）
  - `negative` RAC-RESEARCH-GROWTH-N: research根拠なし制作、付加価値なきsource言い換え、順位操作目的の量産、全媒体一律KPI及び権限不明な商品変更を拒否する （RST-RESEARCH-GROWTH-N）
  - `boundary` RAC-RESEARCH-GROWTH-B: 有料集客は超後期の個別要求が承認されるまでdisabledを維持する （RST-RESEARCH-GROWTH-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:ea8db288dc6dd44db103766832cb6d8f73862e5de15c21c18fa0b43087e50b9e`

## RRF-STRATEGY-REQUIREMENT-ADMISSION — STRATEGY-REQUIREMENT-ADMISSION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000107 RDE-000108
- **主体**: PO／戦略責任者／検証責任者
- **受益者**: 戦略判断の根拠を追跡するPO
- **価値**: 戦略要求の記述・実装admission・test oracleを一意にする
- **task**: SR価値とphaseを再確認する／初期/deferredを分ける／SR→AC→STCを束縛する／test ledger authorityを一つにする
- **workflow**: 戦略価値確認→phase/admission→SR→AC→STC→S4判断
- **対象範囲**: SR-17〜19／AC-SR／TCC/STC authority／FN/CMP descent／deferred resume
- **対象外**: draft testをconfirmed oracleとすること
- **禁止事項**: 要求記述だけを検証完了としない／TCC/STCを暗黙併用しない
- **人間判断**: 戦略capabilityの価値・phase・admissionはPOが判断
- **副作用**: 現段階は要求とtest authorityの候補化のみ
- **証跡**: SR→AC→STC双方向trace／test ledger digest／deferred再開条件／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-STRATEGY-ADMISSION-P: 採用SRがFN/CMP/ACとPO receipt付き単一STC oracleへ降下する （RST-STRATEGY-ADMISSION-P）
  - `negative` RAC-STRATEGY-ADMISSION-N: draft STC又はACなしSRをimplementation-readyにしない （RST-STRATEGY-ADMISSION-N）
  - `boundary` RAC-STRATEGY-ADMISSION-B: 初期外SRは価値・依存・risk・再開条件付きdeferredとする （RST-STRATEGY-ADMISSION-B）
- **PO個別質問**:
  - `RDQ-STRATEGY-REQUIREMENT-ADMISSION-01` (`release_scope`): SR-17〜19と既存AC-SR/STCの初期/deferred及び唯一oracleをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:4739de984abd793c928d5fc98516a44cbe86fe90703d830ba6fe992b280d7565`

## RRF-TEST-ID-AUTHORITY-ALIGNMENT — TEST-ID-AUTHORITY-ALIGNMENT

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000080 RDE-000081
- **主体**: PO／要求管理者／検証責任者／実装者
- **受益者**: 正しい試験でrelease判断するPOと開発者
- **価値**: DUから検証正本への参照を一意にし、不存在の旧TC IDによる偽の完了判定を防ぐ
- **task**: 旧TC参照を抽出する／試験意図を比較する／TCC/STCへ統合・新設又は廃止する／全traceを検証する
- **workflow**: 旧参照抽出→試験意図比較→PO mapping判断→DU/AC/TC再trace→negative gate
- **対象範囲**: DU trace.tc／TCC契約／STC台帳／L4/L6試験参照
- **対象外**: 製品実装／意味確認なしの文字列置換
- **禁止事項**: 不存在IDを完了証跡に使わない／試験意図を失ったまま旧IDを削除しない
- **人間判断**: 統合・新設・廃止はPOが要求責務と反証条件から決定する
- **副作用**: 要求・検証traceの変更のみ
- **証跡**: 旧新ID mapping／試験意図digest／全参照解決／negative mutation test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-TEST-ID-P: 全DU試験参照が実在TCC/STCへ一意に解決し試験意図が保存される （RST-TEST-ID-P）
  - `negative` RAC-TEST-ID-N: 不存在又は旧TC-*参照と意味未確認の置換を拒否する （RST-TEST-ID-N）
  - `boundary` RAC-TEST-ID-B: 同値でない試験は統合せず新ID化又は明示廃止を要求する （RST-TEST-ID-B）
- **PO個別質問**:
  - `RDQ-TEST-ID-AUTHORITY-ALIGNMENT-01` (`authority_choice`): 各旧TC-*の統合・新設・廃止mappingをPO確認する （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:5df8bc9cff5ace92a0fe0e070ccc34b217cbe6b0a3af4770598c1932dcf6ace3`

## RRF-VPS-CREDENTIAL-SECURITY-BOUNDARY — VPS-CREDENTIAL-SECURITY-BOUNDARY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000109 RDE-000110
- **主体**: PO／security運用者／製品runtime
- **受益者**: credential漏洩と越境を防ぐ運用者と外部account所有者
- **価値**: 具体backendを先取りせずVPS credentialの保存・解除・注入・rotationを安全に閉じる
- **task**: at-rest境界を決める／unlock/runtime注入を決める／rotation/recoveryを決める／test/prodとredactionを検証する
- **workflow**: credential登録→at-rest保護→有人unlock/認可→scope付きruntime注入→使用→破棄→rotation/recovery
- **対象範囲**: at-rest protection／unlock／runtime injection／rotation／backup/recovery／test/prod scope／redaction
- **対象外**: 具体secret backend製品／平文envを暗号化storeと同一視すること
- **禁止事項**: 0600だけをat-rest保護の十分条件にしない／test credentialをproductionへ注入しない
- **人間判断**: unlock/rotation/recovery principalと残余riskはPO/security運用者が判断
- **副作用**: 現段階は要求候補のみ。credential移動やrotationを行わない
- **証跡**: threat model／positive/negative/boundary AC／leakage test／rotation/recovery receipt／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-CREDENTIAL-P: at-rest保護とscope付き一時注入を満たし使用後にsecretを残さない （RST-VPS-CREDENTIAL-P）
  - `negative` RAC-VPS-CREDENTIAL-N: 平文env、repo/DB/log/journal/argv/dump漏洩、scope越境を拒否する （RST-VPS-CREDENTIAL-N）
  - `boundary` RAC-VPS-CREDENTIAL-B: unlock失敗・rotation・recovery時は外部操作をfail-closeし旧secret再利用を防ぐ （RST-VPS-CREDENTIAL-B）
- **PO個別質問**:
  - `RDQ-VPS-CREDENTIAL-SECURITY-BOUNDARY-01` (`safety_policy`): at-rest保護、unlock principal、runtime注入、rotation、backup/recovery、test/prod分離をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:b200a95228475b76d930b3519423f587ed639c7e81794a479929b1bca4707ce0`

## RRF-VPS-UI-AUTHENTICATION-SESSION — VPS-UI-AUTHENTICATION-SESSION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000132 RDE-000133
- **主体**: PO／許可運用者／security責任者
- **受益者**: 不正操作を防ぐPOと運用者
- **価値**: 高リスク判断を本人性とfresh sessionへ束縛する
- **task**: identityを登録し認証/session/再認証/失効/recoveryを管理する
- **workflow**: identity登録→認証→session発行→認可→高リスク再認証→失効/recovery→監査
- **対象範囲**: identity lifecycle／session／CSRF／再認証／recovery／lockout／audit/emergency access
- **対象外**: IdP/protocol/proxy/framework選定
- **禁止事項**: 通知deep-linkを認証とみなさない／共有account／失効session利用
- **人間判断**: principal登録、recovery、emergency access、残余riskはPO/security authority
- **副作用**: 現段階は要求候補のみ
- **証跡**: identity/session lifecycle／negative auth cases／recovery/audit receipt／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-UI-AUTH-P: 認証済みかつ有効なsessionと必要な再認証を満たすprincipalだけ操作できる （RST-UI-AUTH-P）
  - `negative` RAC-UI-AUTH-N: 未認証、失効、CSRF不成立、共有account、deep-linkだけの操作を拒否する （RST-UI-AUTH-N）
  - `boundary` RAC-UI-AUTH-B: lockout/recovery/emergency accessでもscope、期限、監査を省略しない （RST-UI-AUTH-B）
- **PO個別質問**:
  - `RDQ-VPS-UI-AUTHENTICATION-SESSION-01` (`safety_policy`): 初期principal、identity lifecycle、session期限/失効、再認証条件、recovery、lockout、監査、emergency accessをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:57f1759d8ef5adb33f4129dddb4692d470956891f41f9fb94d68ed3e8a406758`

## RRF-VPS-UI-INBOX-LIFECYCLE — VPS-UI-INBOX-LIFECYCLE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000100 RDE-000101 RDE-000102 RDE-000119
- **主体**: PO／許可された運用者／製品runtime
- **受益者**: 異常と承認待ちを安全に監督するPO
- **価値**: 通知lifecycleと業務状態を分離して通知失敗や重複による誤決定を防ぐ
- **task**: 初期source eventをinboxへ記録する／利用者ごとのseen/acknowledgedを管理する／source状態に追随してresolved/expiredを管理する／重複を一itemへ収束する／記録失敗を業務状態と独立にretryする
- **workflow**: source event→業務状態を先に確定→inbox記録attempt→recorded/failed/retry_exhausted receipt→利用者seen/acknowledged→source状態に追随したresolved/expired
- **対象範囲**: VPS UI内inbox／purpose=action_required又はoperational_alert／source=approval_waiting/safety_stopped/execution_failed／recorded/failed/retry_exhausted evidence／per-principal seen/acknowledged／source-linked resolved/expired／deduplication／retry／retention
- **対象外**: 外部adapter配送結果／Discord／Web Push／community media post／developer PR notice／具体DB/API/UI設計／通知操作による業務decision
- **禁止事項**: 承認待ちと運用alertを同じpurposeにしない／seen/acknowledgedをapprove/reject又は再開とみなさない／通知記録失敗又はretry_exhaustedで先行する安全停止・失敗・承認待ち状態をrollbackしない／inbox記録と外部配送を同じ結果軸にしない／同一source eventから複数の現役itemを作らない／未決の時間・回数を設計者が補完しない
- **人間判断**: approve/reject、停止後再開、中止はinbox lifecycleと別の許可principal判断／retry回数・backoff・retention・expiry時間はPOが品質要求として決定
- **副作用**: 現段階は要求候補の記録のみ。将来はinbox itemと利用者別確認状態を記録する
- **証跡**: source event identityと対象profile/resource/revision/purpose／recorded/failed/retry/retry_exhausted receipt／per-principal seen/acknowledged receipt／source-linked resolved/expired receipt／dedupe negative test／業務状態不変negative test／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-UI-INBOX-P: approval_waiting/safety_stopped/execution_failedの業務状態を先に確定し、purposeと対象bindingを持つ一意なitemをrecordedとして残し、seen/acknowledgedを利用者別に記録する （RST-UI-INBOX-P）
  - `negative` RAC-UI-INBOX-N: 通知失敗・重複・seen・acknowledged・resolved・expiredから業務状態、approve/reject又は停止後再開を変更しない （RST-UI-INBOX-N）
  - `boundary` RAC-UI-INBOX-B: 未知source/purpose、同一identity再送、記録失敗、保持境界ではfail-closeし、業務状態を維持したまま一意なattempt/failed/expiry証跡を残す （RST-UI-INBOX-B）
- **PO個別質問**:
  - `RDQ-VPS-UI-INBOX-LIFECYCLE-01` (`quality_target`): inbox記録retry回数・backoff、retention、resolved後の保持、未確認itemのexpiry時間をPO品質判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
  - `RDQ-VPS-UI-INBOX-LIFECYCLE-02` (`release_scope`): FR-43等の後続source追加は各source要求のphaseとriskを凍結してから閉集合へ追加する （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:b76638e55a85db15cd03a245780aaddd46b69a1c93f2ee7a5646978db87201e8`

## RRF-VPS-UI-PRIMARY-HUMAN-INTERFACE — VPS-UI-PRIMARY-HUMAN-INTERFACE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000007 RDE-000010 RDE-000011 RDE-000012 RDE-000013 RDE-000030 RDE-000031 RDE-000032 RDE-000035
- **主体**: PO／許可された運用者／製品runtime
- **受益者**: 無人処理を監督するPO
- **価値**: チャット製品に依存せずVPS上で状態・承認・通知を一体監督できる
- **task**: 状態・失敗・KPI・承認待ちを確認する／初回activation・scope拡張・高リスク例外・停止後再開を明示決定する
- **workflow**: 認証→対象表示→通知/承認待ち確認→直前認可→明示操作→証跡保存
- **対象範囲**: VPS製品Web UI／UI内inbox／状態/証跡閲覧／初回自動運用activationと例外判断
- **対象外**: 認証protocol/IdP選定／session timeout数値／reverse proxy製品／公開URL／UI framework選定／Web Push／Discord補助／開発PR通知
- **禁止事項**: 通知受信だけで意思決定を成立させない／要求正本をUIから更新しない
- **人間判断**: 初回activation・scope拡張・課金・危険設定・重大rule変更・再開は許可principalが判断し、activation後の個別投稿は品質gate合格時に毎回承認を要求しない
- **副作用**: 認可済みUI操作による製品状態変更
- **証跡**: principal・対象・revision・binding・decision・状態遷移receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-UI-P: 認証済みprincipalが対象revisionを再表示して明示操作した場合だけ状態を更新する （RST-VPS-UI-P）
  - `negative` RAC-VPS-UI-N: 未認証・CSRF不成立・stale binding・通知deep-linkだけの操作を拒否する （RST-VPS-UI-N）
  - `boundary` RAC-VPS-UI-B: session失効・同時更新・高リスク再認証要求時はfail-closeし既存状態を維持する （RST-VPS-UI-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:7453d207a6d160ca25055edbf87eb8411593735a2b8da8043f0de2a6746edf76`

## RRF-VPS-UI-QUALITY-ATTRIBUTES — VPS-UI-QUALITY-ATTRIBUTES

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000094 RDE-000096
- **主体**: PO／運用者／UI利用者
- **受益者**: 安定して監督できるPOと運用者
- **価値**: 設計製品を先取りせずVPS UIの品質と復旧可能性を反証可能にする
- **task**: 品質目標を定義する／測定する／故障と復旧を検証する／migration/rollbackを受入判断する
- **workflow**: 品質目標定義→測定→故障注入/復旧→受入判断
- **対象範囲**: accessibility／performance／availability／recovery／operation／migration／rollback
- **対象外**: protocol/IdP/proxy/UI framework選定
- **禁止事項**: 具体製品を要求で先取りしない／閾値なしで利用可能としない
- **人間判断**: 品質閾値と残余riskをPOが判断
- **副作用**: 現段階なし
- **証跡**: 測定定義／故障/復旧結果／migration/rollback receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-UI-QUALITY-P: 全品質属性が測定方法・閾値・証跡を持ち受入条件を満たす （RST-VPS-UI-QUALITY-P）
  - `negative` RAC-VPS-UI-QUALITY-N: 未測定、閾値未定、復旧不能又はrollback不能を利用可能として拒否する （RST-VPS-UI-QUALITY-N）
  - `boundary` RAC-VPS-UI-QUALITY-B: 一部品質だけ成立する場合は制限又はdeferredとし全体受入に読み替えない （RST-VPS-UI-QUALITY-B）
- **PO個別質問**:
  - `RDQ-VPS-UI-QUALITY-ATTRIBUTES-01` (`quality_target`): 各品質属性の測定対象・閾値・N/A条件をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:c79650b7473048c20976ba0af3ce002bf8cca2c475a285488b3e38ac801c1ded`

## RRF-WORDPRESS-CONTENT-OPERATIONS-RELEASE — WORDPRESS-CONTENT-OPERATIONS-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000113 RDE-000114
- **主体**: PO／コンテンツ運用者／製品runtime
- **受益者**: 公開コンテンツ利用者／日常運用を行うPO
- **価値**: WordPressをcontent databaseとして日常公開運用し基盤保守riskから分離する
- **task**: 登録/取得/下書き/リライト/media upload/固定ページ編集/preview/公開/更新をstable IDで行う
- **workflow**: 対象取得→draft/preview→対象/revision再表示→承認→公開/更新→receipt
- **対象範囲**: content operation閉集合／stable ID/revision／公開証跡
- **対象外**: core/plugin変更／security変更／AGENT NEO改修
- **禁止事項**: content_publishでmaintenance/security変更を許可しない／PoCを本番受入に流用しない
- **人間判断**: 公開可否と未決の削除/競合解決は許可principal
- **副作用**: WordPress content/media/page状態変更
- **証跡**: preview diff／principal/decision／publication/update receipt／S4 receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=1 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=なし ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-CONTENT-P: stable IDとrevisionを再検証し承認済みcontent操作だけを実行してreceiptを残す （RST-WP-CONTENT-P）
  - `negative` RAC-WP-CONTENT-N: content policyによるcore/plugin/security変更とstale/unknown対象writeを拒否する （RST-WP-CONTENT-N）
  - `boundary` RAC-WP-CONTENT-B: 削除/非公開化/競合/保持が未決ならそのoperationだけdeferredにする （RST-WP-CONTENT-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-CONTENT-OPERATIONS-RELEASE-01` (`release_scope`): increment順序、削除/非公開化、版競合、履歴保持、media差替え、再認証境界をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:2f2ad97d5b2b234f704347aa6875a3a7823f6fc75b7d70a87b9ec588ec5b303f`

## RRF-WORDPRESS-MAINTENANCE-BOUNDARIES — WORDPRESS-MAINTENANCE-BOUNDARIES

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000083 RDE-000084 RDE-000085 RDE-000086 RDE-000087 RDE-000088
- **主体**: PO／コンテンツ運用者／WordPress保守担当／セキュリティ責任者／製品runtime
- **受益者**: 公開コンテンツ利用者／安定かつ安全なWordPress運用を必要とするPO
- **価値**: コンテンツ価値提供、変更保守、セキュリティ対応を独立releaseにして異なるrisk・停止・rollback判断を混同しない
- **task**: コンテンツを公開・リライトする／メディアをアップロードする／固定ページを編集する／WordPress本体をversion updateする／pluginを導入・updateする／変更起因障害を復旧する
- **workflow**: content operation release→独立S4 → WordPress maintenance release→変更前backup/PoC→更新→smoke→rollback判断→独立S4 → security maintenance release→別risk/authority/AC/TC
- **対象範囲**: 運用: 公開・リライト・メディアupload・固定ページ編集／保守: WordPress本体version updateと随伴変更／保守: plugin導入/updateと変更起因障害対応／security保守の独立境界
- **対象外**: 三領域の一括受入／通常運用による保守変更／通常保守判断によるsecurity停止解除
- **禁止事項**: コンテンツ操作を保守へ分類しない／core/plugin変更を日常運用へ分類しない／security保守を通常保守へ混在させない／backup/smoke/rollbackなしで更新を本番昇格しない
- **人間判断**: 各release unitをPOが個別S4判断する／version/plugin変更後の障害は保守担当が停止・rollback候補を提示する／security緊急判断は別権限境界で行う
- **副作用**: 公開コンテンツ変更／WordPress core/plugin変更／変更起因rollback／別releaseでのsecurity変更
- **証跡**: publication/edit/media receipt／version/plugin inventory before/after／backup/restore proof／smoke/regression result／incident/rollback receipt／separate security receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-WP-BOUNDARY-P: 公開・リライト・media upload・固定ページ編集は運用release、core/plugin変更と起因障害対応は保守releaseとして独立証跡を持つ （RST-WP-BOUNDARY-P）
  - `negative` RAC-WP-BOUNDARY-N: 運用操作によるcore/plugin変更、又は通常保守によるsecurity判断代替を拒否する （RST-WP-BOUNDARY-N）
  - `boundary` RAC-WP-BOUNDARY-B: plugin更新にsecurity修正が含まれても変更作業は保守、脅威受容・緊急解除・credential/権限判断はsecurity保守として別receiptへ束縛する （RST-WP-BOUNDARY-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:eafdb5ab01a64154bc42df57594ce221f4327aed4a5beb2b77ec0f80047f8201`

## RRF-WORDPRESS-PLATFORM-MAINTENANCE-RELEASE — WORDPRESS-PLATFORM-MAINTENANCE-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000115 RDE-000116
- **主体**: PO／WordPress保守担当／製品runtime
- **受益者**: 安定稼働するWordPressを必要とする運用者と利用者
- **価値**: core/plugin変更と起因障害を日常content operationから分離してrollback可能にする
- **task**: inventory/backup/互換性評価/core/plugin変更/smoke/regression/rollbackを行う
- **workflow**: inventory→評価→backup/restore proof→承認→変更→検証→続行又はrollback→receipt
- **対象範囲**: core version update／plugin導入/状態変更/update／随伴schema/config／起因障害復旧
- **対象外**: 日常content操作／security authority判断／AGENT NEO改善改修
- **禁止事項**: content承認をmaintenanceへ流用しない／復旧proofなしで本番変更しない
- **人間判断**: 変更/停止/続行/rollback/残余riskはPOと保守担当
- **副作用**: core/plugin/schema/config変更／rollback
- **証跡**: before/after inventory／backup/restore proof／compatibility/smoke/regression／decision/rollback/S4 receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=2 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=WORDPRESS-CONTENT-OPERATIONS-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-MAINT-P: 独立maintenance承認と復旧proofを持つ変更だけを実行し検証receiptを残す （RST-WP-MAINT-P）
  - `negative` RAC-WP-MAINT-N: content承認、backup不足、互換性未検証又はrollback不能な変更を拒否する （RST-WP-MAINT-N）
  - `boundary` RAC-WP-MAINT-B: plugin更新がsecurity修正を含んでも変更実施と脅威受容を別decisionへ束縛する （RST-WP-MAINT-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-PLATFORM-MAINTENANCE-RELEASE-01` (`safety_policy`): 自動/attended境界、maintenance window、backup freshness、smoke/regression、rollback閾値をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:e5e6a588ff8440f3e5e45d482dda2c9e70db23d75a5d9db1363587fbc03300a1`

## RRF-WORDPRESS-SECURITY-MAINTENANCE-RELEASE — WORDPRESS-SECURITY-MAINTENANCE-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000117 RDE-000118
- **主体**: PO／security責任者／security運用者
- **受益者**: サイト利用者／account所有者／安全な運用を必要とするPO
- **価値**: security判断を日常運用/通常保守から分離し別authorityと証跡で閉じる
- **task**: 脆弱性評価/security patch/credential rotation/権限変更/監査/隔離/停止/復旧を行う
- **workflow**: 脅威検知→影響評価→隔離/停止判断→変更→検証→復旧判断→監査receipt
- **対象範囲**: vulnerability／security patch／credential/permission／audit／isolation/stop/recovery
- **対象外**: 日常content操作／一般機能update／AGENT NEO機能改善
- **禁止事項**: 通常保守又は公開承認でsecurity判断を代替しない／secretをrepo/DB/logへ残さない
- **人間判断**: 脅威受容/隔離/break-glass/復旧/残余riskはsecurity authorityとPO
- **副作用**: credential/permission/security設定変更／隔離/停止/復旧
- **証跡**: threat/vulnerability／principal/decision／change/rotation／isolation/recovery proof／independent S4 receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=2 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=WORDPRESS-CONTENT-OPERATIONS-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-SECURITY-P: 別security authorityが脅威と対象を束縛して変更/隔離/復旧receiptを残す （RST-WP-SECURITY-P）
  - `negative` RAC-WP-SECURITY-N: content又は通常保守の承認流用、secret漏洩、権限越境を拒否する （RST-WP-SECURITY-N）
  - `boundary` RAC-WP-SECURITY-B: 緊急break-glassでもscope/期限/事後監査/復旧判断を省略しない （RST-WP-SECURITY-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-SECURITY-MAINTENANCE-RELEASE-01` (`safety_policy`): 対象脅威、patch、credential/権限/監査範囲、緊急principalとbreak-glass条件をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:fd8b1a8ceb114d1606b8224fdab9d77699956e18b94c2d79aabe792c4b021660`
