<!-- GENERATED FILE — 編集禁止。正本は docs/00-authority/development/requirement-refinements.json。再生成 = python3 scripts/render_views.py -->

# 要求候補レビュー（refinement candidates）

> [!CAUTION]
> **提案専用の生成view。現行要求の正本・PO承認・設計・実装入力ではない。**  `requirements_baseline_status=revising` / `implementation_authorized=false`。
> 各候補は個別のPO receiptで承認・freezeされ、Full Vを再降下してauthority cutoverするまでcurrentにならない。本view全体を一括承認として扱わない。
> 集計: 候補 **49** 件 ／ approval receiptあり **0** 件 ／ 未承認 **49** 件。

## PO確認順（decision packets）

> packetは確認順をまとめるだけで、packet単位の一括承認は禁止。各subject revisionへ個別receiptを束縛する。

1. **RDP-REQUIREMENTS-AUTHORITY** — 新baselineの意味正本、意味軸継承、phase、NFR根拠、試験IDをどのrevisionへ凍結するか  対象: L0-NORTH-STAR-AUTHORITY-NORMALIZATION, REQ-AUTHORITY-NORMALIZATION, CONTRACT-SEMANTIC-DESCENT-V2, FR-SLICE-AUTHORITY-ALIGNMENT, NFR-BUSINESS-AUTHORITY, TEST-ID-AUTHORITY-ALIGNMENT, RATE-QUOTA-COST-AUTHORITY, REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2
2. **RDP-INITIAL-VPS-HUMAN-INTERFACE** — VPS Web UI＋UI inboxを初期主入口にし、安全停止、credential、品質、人間判断をどの要求境界で凍結するか  対象: VPS-UI-PRIMARY-HUMAN-INTERFACE, PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION, VPS-UI-AUTHENTICATION-SESSION, VPS-UI-INBOX-LIFECYCLE, FR-16-NOTIFICATION-BOUNDARY, DISCORD-NOTIFICATION-REJECTION-BOUNDARY, VPS-UI-QUALITY-ATTRIBUTES, VPS-CREDENTIAL-SECURITY-BOUNDARY, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING, CONTENT-RISK-CLASSIFICATION, RESEARCH-LED-CONTENT-GROWTH
3. **RDP-WORDPRESS-PROGRAM-STAGE-1** — WordPress content operation、platform maintenance、security maintenanceをどの独立release境界と順序で凍結するか  対象: WORDPRESS-MAINTENANCE-BOUNDARIES, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE
4. **RDP-FOLLOW-ON-FULL-V** — 後続媒体、戦略、AGENT NEOのFull V releaseをどの順で再開するか  対象: OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, DISCORD-COMMUNITY-MARKETING-ROUTE, MEDIA-POC-SCRUM-RELEASE, STRATEGY-REQUIREMENT-ADMISSION, AGENT-NEO-HELIX-REDEFINITION, AGENT-NEO-SITE-BUILD-RELEASE, AGENT-NEO-PRODUCT-EVOLUTION-RELEASE
5. **RDP-DEFERRED-EXTERNAL-CAPABILITIES** — 初期scope外の生成AIと旧媒体capabilityをdeferredのまま維持するか個別に再開するか  対象: GENAI-EXECUTION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY
6. **RDP-MEDIA-PER-MEDIUM-HARNESS** — 各媒体を1つずつの独立ハーネスとして分離構成するか、対象媒体一覧・共通基盤範囲・分離境界をどう確定するか  対象: MEDIA-PER-MEDIUM-HARNESS
7. **RDP-MEDIA-HARNESS-WORDPRESS** — WordPressを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-WORDPRESS
8. **RDP-MEDIA-HARNESS-DISCORD-COMMUNITY** — Discord communityを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-DISCORD-COMMUNITY
9. **RDP-MEDIA-HARNESS-LINE** — LINEを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-LINE
10. **RDP-MEDIA-HARNESS-GENAI** — 生成AIを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-GENAI
11. **RDP-MEDIA-HARNESS-AFFILIATE** — アフィリエイトを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-AFFILIATE
12. **RDP-MEDIA-HARNESS-CANVA** — Canvaを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-CANVA
13. **RDP-MEDIA-HARNESS-X-TWITTER** — X（Twitter）を独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-X-TWITTER
14. **RDP-MEDIA-HARNESS-INSTAGRAM** — Instagramを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-INSTAGRAM
15. **RDP-MEDIA-HARNESS-YOUTUBE** — YouTubeを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-YOUTUBE
16. **RDP-MEDIA-HARNESS-TIKTOK** — TikTokを独立ハーネス1つとして分離構成するか、その承認境界・共有基盤分離線・リポジトリ分離条件をどう確定するか  対象: MEDIA-HARNESS-TIKTOK

## 回答済み事項（要求へ再降下前）

> 会話から取得したPO判断の構造化snapshot。まだ個別refinement revision・approval receipt・freezeへ再降下していないため、設計・実装入力ではない。

- **POD-20260815-001** (`captured_unratified`): 外部automationは公式API又は公式MCPを第一経路とし、Playwrightをfallback及び実行結果のbrowser確認経路として使用する  既存subject=OFFICIAL-API-ROUTE-AUTHORITY, LEGACY-MEDIA-ADMISSION-INVENTORY ／ 新規要求subject=EXTERNAL-BROWSER-AUTOMATION-ROUTE ／ 未解決=媒体operationごとのPlaywright write許可範囲と利用規約境界
- **POD-20260815-002** (`captured_unratified`): Discordは製品通知経路には使用せず、コミュニティマーケティング媒体として使用する  既存subject=DISCORD-MULTI-PURPOSE-BOUNDARIES, LEGACY-MEDIA-ADMISSION-INVENTORY ／ 新規要求subject=DISCORD-COMMUNITY-MARKETING-ROUTE ／ 未解決=community operation、Bot principal、account/guild/channel、write範囲、quota、moderation、evidence
- **POD-20260815-003** (`captured_unratified`): 初期稼働はVPS UI内inboxで通知してユーザーが承認し、その後は毎回承認せず自動稼働できる  既存subject=AUTO-MODE-DECISION-AUTHORITY, VPS-UI-INBOX-LIFECYCLE, BUSINESS-PROFILE-AUTHORIZATION ／ 新規要求subject=AUTOMATED-PUBLISHING-ADMISSION ／ 未解決=activation approvalのprofile/media/account/operation scope、期限、取消、基準失効時の復帰
- **POD-20260815-004** (`captured_unratified`): 禁止語、表現、型等をHELIX型gate/lintで検査し、不合格成果物は人間確認前に自動でやり直し、合格品だけを人間確認へ送る  既存subject=CONTRACT-SEMANTIC-DESCENT-V2, AUTO-MODE-DECISION-AUTHORITY ／ 新規要求subject=CONTENT-QUALITY-GATE-LEARNING ／ 未解決=再生成上限、解消不能時の停止/通知、検査class、合格基準のauthority
- **POD-20260815-005** (`captured_unratified`): ユーザーフィードバックへ即座に対応し、構造化規則として保存する。適用範囲を明示指定でき、指定がない場合は指摘対象の媒体accountを既定scopeとする  既存subject=VPS-UI-INBOX-LIFECYCLE, PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION ／ 新規要求subject=CONTENT-QUALITY-GATE-LEARNING ／ 未解決=全体共通化の権限、規則競合、rollback、誤検知時の解除
- **POD-20260815-006** (`captured_unratified`): content check規則は運用変更を前提とし、製品コードへ埋め込まず外部化された構造化データとしてversion管理する。成果物及びclaimが扱う領域のrisk分類を上位rule setとし、YMYL等の高risk領域はより厳格な根拠・表現・更新性・安全検査を要求する。ユーザーの好みはブランドへ固定せず、案件・成果物・claimごとにcase-by-caseで指定できる。AIはrisk境界内で媒体account別及び個別scopeの下位規則を更新できる。新revisionの有効化時は対象scopeの未公開成果物を自動再検査する。公開済み成果物は媒体operationがupdate-in-placeを明示対応する場合だけ自動監査・修正・更新し、非対応時は通知を含め何もしない  既存subject=PRODUCT-STATE-AUTHORITY, BUSINESS-PROFILE-AUTHORIZATION, AUTO-MODE-DECISION-AUTHORITY ／ 新規要求subject=CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING ／ 未解決=risk classの分類軸と段階、YMYL境界、個別の好みが未指定の場合の継承元、AI分類の不確実時挙動、変更前検証、effective timing、競合優先順、rollback条件
- **POD-20260815-007** (`captured_unratified`): content運用は制作前のresearchを必須前提とし、市場需要、検索意図、競合、trend、媒体上の反応及び過去実績から成長仮説を作る。媒体の役割は対象商品又はofferのmarketing funnel上で担う段階と次段階への送客責務によって決まり、成長の第一基準は全媒体共通の売上ではなく、そのfunnel上の役割達成度とする。商品又はofferへの操作可能性は扱う対象ごとに異なり、アフィリエイト商材の選定又は差替え、自己商品の改善提案、変更不能な第三者商材等を同一権限として扱わない。成果物はその仮説、媒体役割、適用risk基準及びcase-by-caseのユーザー嗜好を満たすよう生成し、公開後のKPI結果を次のresearch、企画、funnel及び媒体間導線、rule及び仮説へ還流して継続的に伸ばす。有料集客はfunnel上必要になり得る将来scopeとして保持するが、初期及び中期releaseから除外し超後期までdeferredとする  既存subject=STRATEGY-REQUIREMENT-ADMISSION, PRODUCT-STATE-AUTHORITY ／ 新規要求subject=RESEARCH-LED-CONTENT-GROWTH, CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING ／ 未解決=商品又はoffer種別ごとの具体operationとauthorityは対象登録時に解決する／役割別KPIと閾値、複数役割が競合する場合の優先順位、段階間及び媒体間寄与の評価窓、research freshness、仮説の評価期間、探索と既知勝ち筋の配分、KPI悪化時の停止条件、有料集客の再開条件は超後期releaseまでdeferred
- **POD-20260815-008** (`captured_unratified`): 現行VPS運用は再起動でエージェント実行系も停止するため、credentialだけを無人unlockして処理継続する前提を置かない。再起動後は外部操作停止を維持し、人間が実行系を再初期化するときにcredential unlock又はruntime注入も再認可する。常駐serviceと自動再起動を将来採用する場合は別要求として判断する  既存subject=VPS-CREDENTIAL-SECURITY-BOUNDARY ／ 新規要求subject=VPS-CREDENTIAL-SECURITY-BOUNDARY ／ 未解決=secret backend、unlock protocol及びruntime injection mechanismはL2以降／将来の常駐service lifecycleは採用時の別要求
- **POD-20260815-009** (`captured_unratified`): retry budgetを使い切っても合格しない成果物はblockedで停止し、VPS UI内inboxへ通知する。通常の不合格retryは通知せず自動修正又は再生成し、通知記録失敗でもblocked状態をrollbackしない。update-in-place非対応の既公開成果物は通知を含め何もしない  既存subject=CONTENT-QUALITY-GATE-LEARNING, VPS-UI-INBOX-LIFECYCLE ／ 新規要求subject=CONTENT-QUALITY-GATE-LEARNING, VPS-UI-INBOX-LIFECYCLE ／ 未解決=retry budget値及びinbox retry/retention値は外部設定又は別quality targetとして扱う

## PRC意味所有者

> baseline候補の各PRCを、意味を閉じるrefinement subjectへ束縛する。PRC本文だけを単独で承認・設計入力化しない。

- **PRC-01**: VPS-UI-PRIMARY-HUMAN-INTERFACE
- **PRC-02**: PRODUCT-STATE-AUTHORITY
- **PRC-03**: VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE
- **PRC-04**: VPS-UI-INBOX-LIFECYCLE
- **PRC-05**: DISCORD-COMMUNITY-MARKETING-ROUTE, DISCORD-NOTIFICATION-REJECTION-BOUNDARY
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
- **PRC-19**: REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2
- **PRC-20**: RATE-QUOTA-COST-AUTHORITY
- **PRC-21**: LEGACY-MEDIA-ADMISSION-INVENTORY
- **PRC-22**: CONTRACT-SEMANTIC-DESCENT-V2, AUTOMATED-PUBLISHING-ADMISSION
- **PRC-23**: L0-NORTH-STAR-AUTHORITY-NORMALIZATION, REQ-AUTHORITY-NORMALIZATION, CONTRACT-SEMANTIC-DESCENT-V2
- **PRC-24**: GENAI-EXECUTION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY, STRATEGY-REQUIREMENT-ADMISSION
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
- **PRC-36**: MEDIA-PER-MEDIUM-HARNESS, MEDIA-HARNESS-WORDPRESS, MEDIA-HARNESS-DISCORD-COMMUNITY, MEDIA-HARNESS-LINE, MEDIA-HARNESS-GENAI, MEDIA-HARNESS-AFFILIATE, MEDIA-HARNESS-CANVA, MEDIA-HARNESS-X-TWITTER, MEDIA-HARNESS-INSTAGRAM, MEDIA-HARNESS-YOUTUBE, MEDIA-HARNESS-TIKTOK

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
| `NFR-5` | `redescent` | BR-H3, REQ-043 | ユーザーがVPS UIから現在状態、停止理由、影響scope及び必要な対応を把握できる | 一つのSQLという旧実装条件ではなく、権威状態から一貫したread modelを提供し、VPS UI内inboxと証跡へ目的・scope・correlationを保って表示する | freshness／保持期間／欠測表示／集約scope／可用性閾値 | NFR-BUSINESS-AUTHORITY, VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE, VPS-UI-QUALITY-ATTRIBUTES, PRODUCT-STATE-AUTHORITY |
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
| `REQG-001-010` | REQ-001=redescent, REQ-002=redescent, REQ-003=redescent, REQ-004=replace, REQ-005=redescent, REQ-006=replace, REQ-007=redescent, REQ-008=redescent, REQ-009=redescent, REQ-010=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-001: 上位ループ（戦略）をブランド成長サイクルで回せること; なし（全自動 — 異常時は BR-H3 の escalation 境界へ委譲） / REQ-002: 下位ループ（実行）を媒体単位のサイクルで回せること; なし（サイクル長の初期値設定はヒアリング/リサーチ充填） / REQ-003: 検証マイクロループをタスク内で回し PASS でのみ完了できること / REQ-004: 一年地平のブランド計画を許可principalが確定し、版付き行動計画が根拠と成果へ追跡できる; ブランド計画（1年地平）を保持し行動計画が trace できること / REQ-005: 媒体ごとにサイクル長を独立設定でき同期を強制しないこと; なし（サイクル長の初期値設定はヒアリング/リサーチ充填） / REQ-006: VPS製品runtimeの進行状態を永続化し、再起動後も一意の現在地から再開できる。保存方式は設計で決める; ループ状態が SQLite 上の状態遷移のみで表現されること; なし（全自動 — 異常時は BR-H3 の escalation 境界へ委譲） / REQ-007: タスクがワークフローとエージェントを割り当てられて実行されること / REQ-008: 企画↔品質ペア成立まで公開できないこと; なし（経過措置期間の束縛承認は BR-H2 が担う） / REQ-009: 計画↔計測ペア成立までレビュー・還流が発生しないこと; なし（全自動） / REQ-010: 完了判定は対象版に必要な証跡集合が欠落なく収束した場合だけ成立する; 完了判定が証跡の DB 収束を要件とすること; なし（全自動） / REQ-006: VPS製品状態正本 | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | — |
| `REQG-011-020` | REQ-011=redescent, REQ-012=replace, REQ-013=redescent, REQ-014=redescent, REQ-015=replace, REQ-016=redescent, REQ-017=redescent, REQ-018=redescent, REQ-019=redescent, REQ-020=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-011: 成果物のauthor principalとverifier principalを分離する; 作成者と検証者が別エージェントであること; なし（全自動） / REQ-012: 有料集客は超後期releaseまで無効とし、採用時も許可された金銭operation・予算・媒体scope以外をfail-closeする; ゼロ広告費ゲートが有料指標・広告経路を機械遮断すること; なし（例外なし — PO でも解除不可の機械的制約） / REQ-013: 広告・提携・affiliate関係を必要な媒体・offer・法域scopeで明瞭に表示し、欠落時は公開しない / REQ-014: 恐怖訴求・偽希少性・誤認表現をrisk class別に拒否し、YMYL等の高risk領域では基準を厳格化する / REQ-015: 金銭operationは対象・金額・通貨・受取人又は支払先・期限を束縛した人間承認を必要とする; 金銭operationごとの束縛承認を要求する; 金銭操作が常時人間の束縛承認を要すること; 金銭額又は対象を束縛しない承認を採用しない / REQ-016: ヒアリングエンジンが不足スロットを検出し問診・充填できること / REQ-017: リサーチエンジンが外部照合で KPI 初期形・運用詳細を起草できること / REQ-018: 運用ruleを外部化・version化し、安全側既定と変更証跡を保持する / REQ-019: ハーネスが事業非依存で複数プロファイルを共存できること / REQ-020: 媒体のfunnel上の役割と期待する認識変化を、観測可能なKPIへ接続する; KPI ツリーが露出/マイクロCV/転換/関係/収益の固定階層を持つこと | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | — |
| `REQG-021-030` | REQ-021=defer, REQ-022=replace, REQ-023=redescent, REQ-024=replace, REQ-025=defer, REQ-026=replace, REQ-027=defer, REQ-028=replace, REQ-029=replace, REQ-030=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-021: 媒体横断集計（オーガニック版 MMM）が可能なスキーマであること / REQ-022: 計測は公式API、公式MCPを優先し、必要時だけPlaywrightによる読取又は確認を行いsource evidenceを残す; 計測をブラウザエクスポート→パース→SQLite で取り込めること; なし（取得失敗の escalation は BR-H3 経由） / REQ-023: 計測値ごとに取得元・対象・時点・期間・完全性を検証できるsource evidenceを残す; hash又はスクリーンショットだけを取得証跡の必須形式に固定しない; なし（取得失敗の escalation は BR-H3 経由）; なし（全自動） / REQ-024: 許可された利用者がVPS Web UIでKPI・状態・停止理由・証跡を確認できるread modelを持つ; ダッシュボードを SQLite から HTML 自動生成できること; なし（閲覧のみ） / REQ-025: xlsx エクスポートを提供すること; なし（閲覧のみ） / REQ-026: 接続経路は利用可能な公式API、公式MCPを優先し、Playwrightは必要なfallback又は確認経路としてpolicy内で使う; 接続経路が MCP→ブラウザ→有償API の優先順で選定されること / REQ-027: 有償 API 例外の支出が台帳化され上限で停止すること / REQ-028: Playwright経路の操作知識を版付き・検証可能な形で保持し、変更検知時に旧知識を黙って使わない; ブラウザ自動化が攻略地図を蓄積・参照すること / REQ-029: Playwright経路の操作知識の陳腐化・破損を検知し、再調査結果を検証してから新版へ切り替える; 攻略地図の破損を検知し自己修復を試みること / REQ-030: 媒体又はoperation capabilityをkernelの責務分岐増殖なしに追加・停止・廃止できる; workflow追加だけで媒体追加を完了扱いしない / REQ-022: API/MCP優先 / REQ-026: 公式API/MCP / REQ-027: 超後期 | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | REQ-021: 媒体横断因果評価のbusiness valueとdata qualityが承認される／基本funnel KPI loopと高度分析境界が成立する<br>REQ-025: xlsxを必要とする利用者と業務workflowが承認される／VPS UI又はAPIでは満たせないexport要件とdata scopeが凍結される<br>REQ-027: 超後期の有料capabilityが承認される／金銭operation、ledger、予算、credential、AC/TCが凍結される |
| `REQG-031-040` | REQ-031=replace, REQ-032=redescent, REQ-033=replace, REQ-034=defer, REQ-035=replace, REQ-036=replace, REQ-037=replace, REQ-038=replace, REQ-039=replace, REQ-040=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-031: credential及びsecretをrepo・DB・logへ平文保存せず、用途・principal・環境ごとに分離する。現行runtime再起動後は外部操作停止を維持し、実行系再初期化時に人間がunlockを再認可する。credential単独auto-unlockは禁止し、将来の常駐serviceは別要求とする; 認証情報がリポジトリ・DB・ログに平文で存在しないこと / REQ-032: 制作物のsource、派生関係、検証対象版及び合格版をcontent digestで一意に追跡できる; gitだけを全制作物sourceの必須正本に固定しない; なし（審査は BR-B1/B4 経路） / REQ-033: content正本は媒体とcapabilityごとに明示し、WordPressへ一律収束させない; コンテンツ実体が WP に収束し SQLite は参照のみとすること; なし（全自動） / REQ-034: 採用済み成果物形式間の派生元・権利・変換・配布先を追跡できる; なし（全自動） / REQ-035: design tokenの意味schemaと適用証跡をprovider-neutralに保ち、単一Design providerを製品必須にしない; デザイントークンが全制作物に適用されること / REQ-036: WordPressのcontent operation、platform maintenance、security maintenanceを別authority・release単位へ分離する; WP 開発が既存テーマ解析＋子テーマ/プラグインで行われること / REQ-037: 初回のscope activation後、通常運用は品質gate合格を条件に自動化し、setup・例外・governance・外部write判断は別境界にする; 企画確定以降がヒューマンアウトオブループであること / REQ-038: profile・媒体・account・operationを束縛した初回activationを利用者が承認し、そのscope内では毎回承認なしで自動運用できる; 公開が束縛承認を経て、基準充足後オートモードへ移行できること / REQ-039: 異常・停止・対応要否をVPS UI内inboxのdurable eventとして通知し、Discordその他媒体経路を製品通知に使わない; 異常（ゲート赤・予算超過・地図破損）が検知・通知されること / REQ-040: すべてのゲートが判定不能時に通さない側へ倒れること / REQ-031: 暗号化store / REQ-033: content正本をWPへ一律固定せず / REQ-036: WP content/platform/security / REQ-037: 通常/初期setup/例外/governance/external-write / REQ-038: 初回scope activation | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | REQ-034: 対象rich-media種別とfunnel価値が承認される／provider/license/品質/配布operation/AC/TCが凍結される |
| `REQG-041-050` | REQ-041=redescent, REQ-042=replace, REQ-043=replace, REQ-044=replace, REQ-045=defer, REQ-046=redescent, REQ-047=redescent, REQ-048=redescent, REQ-049=redescent, REQ-050=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-041: 制作・集計が同一入力→同一出力の決定性を持つこと / REQ-042: 永続化した製品状態・証跡・冪等性契約から安全に再開できる。SQLiteを要求として固定しない; プロセス強制終了後も SQLite 状態から再開できること; なし（全自動） / REQ-043: 許可された利用者がVPS UI read modelで滞留・停止理由・対応要否を把握できる; 滞留状況が 1 クエリで把握できる可観測性を持つこと / REQ-044: route・媒体・accountごとの公式quota及びpolicyを守り、不明時は停止する。Playwrightは人間相当乱数を全媒体共通要件にしない; 全媒体でブラウザ操作が人間相当のランダム化レート節度を守ること / REQ-045: 媒体の役割とoperationごとにactor・effect・policy・credential・quota・evidence・受入条件が閉じたcapabilityだけを稼働する / REQ-046: ブランド・事業間でデータ・資産・認証・学習が相互隔離され越境できないこと / REQ-047: 下流が有効 brief なしに開始できず、上流正本を直接更新できないこと / REQ-048: 戦略更新が根拠・反証つき revision と append-only 版管理でのみ行われること / REQ-049: 全終端下流 run が learning/failure packet をちょうど 1 件還流すること; 観測時点より前のfailureへ因果説明を遡及付与しない; 証跡のない因果関係を確定事実として扱わない; なし（全自動生成 — 内容の評価は上流工程） / REQ-050: 複数媒体の役割分担キャンペーンを計画・評価単位として扱えること / REQ-042: VPS製品状態 / REQ-044: API/MCP quota / REQ-044: Playwright節度 / REQ-045: 個別capability admission | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | REQ-045: 媒体/operationごとのbusiness valueとcapability statusが承認される／principal/effect/policy/credential/quota/evidence/AC/TCが凍結される |
| `REQG-051-055` | REQ-051=redescent, REQ-052=redescent, REQ-053=redescent, REQ-054=redescent, REQ-055=redescent | 旧confirmed MDとdraft JSONの同一ID意味差及び旧runtime・provider・phaseを現要求へ自動継承できない | REQ-051: 主要コンテンツ企画は問題・対象者・期待する認識変化・比較軸・提供価値・戦略根拠を明示してから確定する; 固定5 fieldの存在だけで企画品質を合格扱いしない / REQ-052: 全工程が証跡・再開・冪等性の横断契約を満たすこと; 証跡・再開条件・冪等性を一組の復旧要件として保持する; ログ存在だけを復旧成立の証拠にしない; なし（全自動） / REQ-053: 下流戦術 OS が pull・WIP 制限・blocked 管理・flow 指標を持つ Kanban として連続運転し、Scrum は補充・レビュー・振り返りの cadence に限定されること / REQ-054: business_profile 配下の複数 bounded domain が registry と安全な workspace 契約で隔離され、domain root 外への path escape と暗黙共有が拒否されること / REQ-055: 上流戦略 OS の版付き判断により domain ごとの実媒体 binding を追加・一時停止・廃止・差替えでき、下流結果が TLP として上流へ還流すること | 各IDのsource rootとmeaning ownerを新単一JSON正本へ再降下し旧MD/JSONをroot代替にしない | — |

## 旧BR 41件 disposition候補

| group | ID別処置 | 保持する価値 | 置換policy | owner |
|---|---|---|---|---|
| `BRG-A` | BR-A1=redescent, BR-A2=redescent, BR-A3=redescent, BR-A4=redescent | BR-A1: 戦略・媒体実行・task検証を接続した継続運用loopを成立させる / BR-A2: 媒体特性に応じて独立した運用cadenceを設定する / BR-A3: 事業計画を行動計画の上位根拠として保持しtraceする / BR-A4: taskを明示workflowへ割り当て検証合格時だけ完了させる | BR-A1: 旧三重loop構造と旧状態実装を継承しない / BR-A2: 固定cycle長と旧媒体一覧を継承しない / BR-A3: 一年という固定期間を無条件に継承しない / BR-A4: 旧agent割当方式と旧task状態実装を継承しない | L0-NORTH-STAR-AUTHORITY-NORMALIZATION, RESEARCH-LED-CONTENT-GROWTH, PRODUCT-STATE-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-B` | BR-B1=redescent, BR-B2=redescent, BR-B3=redescent, BR-B4=redescent | BR-B1: 企画意図と品質検査結果が対応した成果物だけを公開候補にする / BR-B2: KPI目標と計測結果を対応させreviewと学習へ利用する / BR-B3: 完了判断を検証可能な成果・計測・検査証跡へ束縛する / BR-B4: 成果物の作成責務と検証責務を独立させる | BR-B1: SQLite保存と毎回投稿承認を成立条件として継承しない / BR-B2: 旧sprint review構造を唯一の評価方式として継承しない / BR-B3: DB収束、スクリーンショット又は特定hash種別だけを完了条件に固定しない / BR-B4: 特定agent名又はagent数だけを独立性の証明にしない | CONTENT-QUALITY-GATE-LEARNING, RESEARCH-LED-CONTENT-GROWTH, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-C` | BR-C1=replace, BR-C2=redescent, BR-C3=redescent, BR-C4=replace | BR-C1: 有料集客と有料指標の採否を事業価値・risk・予算から独立判断する / BR-C2: 広告・提携関係を閲覧者へ明瞭に表示する / BR-C3: 誤認・不当な心理誘導を避けた表現を提供する / BR-C4: 金銭operationごとに許可principalの人間判断を要求する | BR-C1: 広告費ゼロを永久不変の機械定数として継承しない; 超後期承認前に有料集客を有効化しない / BR-C2: 単一の固定表示templateを全媒体へ無条件適用しない / BR-C3: 旧固定語彙だけで全riskを判定済みとみなさない / BR-C4: 包括承認又は別operationの承認を流用しない; 旧auto-mode又は旧ApprovalTransportを金銭承認へ継承しない | CONTENT-RISK-CLASSIFICATION, CONTENT-QUALITY-GATE-LEARNING, RATE-QUOTA-COST-AUTHORITY, NFR-BUSINESS-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-D` | BR-D1=redescent, BR-D2=redescent, BR-D3=redescent, BR-D4=redescent | BR-D1: 不足する事業前提と受入情報を検出し構造化質問で補完する / BR-D2: 外部source付きresearchからKPI・媒体運用候補を起草する / BR-D3: 運用ruleを外部化・version化し変更履歴を追跡する / BR-D4: 複数の事業profileを同じ製品能力で個別管理する | BR-D1: 旧固定schemaのslotだけを質問範囲にしない / BR-D2: 旧KPI tree又は業種標準値を現状確認なしに継承しない / BR-D3: SQLite保存、旧固定数値及び旧auto移行基準を継承しない / BR-D4: 型の再充填だけで新事業を自動承認しない | REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE, RESEARCH-LED-CONTENT-GROWTH, CONTENT-QUALITY-GATE-LEARNING, BUSINESS-PROFILE-AUTHORIZATION |
| `BRG-E` | BR-E1=redescent, BR-E2=replace, BR-E3=replace | BR-E1: funnel上の役割に沿ったKPIを媒体成果へ接続する / BR-E2: 媒体成果を検証可能なsourceから取得し時系列学習へ利用する / BR-E3: 状態・証跡・KPIを人が理解し判断できる形で提示する | BR-E1: 固定五階層及びオーガニック版MMMを初期必須要件として継承しない / BR-E2: browser export、SQLite、スクリーンショット又は列挙providerを一般経路として継承しない / BR-E3: HTML dashboard、xlsx及びSQLiteを必須表示方式として継承しない / BR-E3: VPS Web UI | RESEARCH-LED-CONTENT-GROWTH, OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, VPS-UI-PRIMARY-HUMAN-INTERFACE |
| `BRG-F` | BR-F1=replace, BR-F2=replace, BR-F3=redescent, BR-F4=replace, BR-F5=replace | BR-F1: 外部接続経路を能力・規約・費用・riskに基づいて選択する / BR-F2: 外部operationの実行知識をversion化し破損を検知・修復可能にする / BR-F3: 媒体・能力をkernel責務分岐の増殖なしに追加可能にする / BR-F4: credentialを安全に登録・利用・更新・失効できるようにする / BR-F5: 外部operationを媒体健全性と利用制限を守る速度で実行する | BR-F1: MCP→browser→有償APIという旧固定順を継承しない / BR-F2: browser攻略地図と単一回数の自己修復を全connectorへ継承しない / BR-F3: workflow追加だけで媒体追加完了とみなさない / BR-F4: 旧session保存、application password及び特定key分離方式を継承しない / BR-F5: 全媒体への人間相当ランダム間隔、固定rate及び自動調整を一律継承しない / BR-F1: 公式API/MCP / BR-F1: Playwright / BR-F4: 暗号化credential | OFFICIAL-API-ROUTE-AUTHORITY, EXTERNAL-BROWSER-AUTOMATION-ROUTE, LEGACY-MEDIA-ADMISSION-INVENTORY, VPS-CREDENTIAL-SECURITY-BOUNDARY, RATE-QUOTA-COST-AUTHORITY |
| `BRG-G` | BR-G1=redescent, BR-G2=replace, BR-G3=replace, BR-G4=replace | BR-G1: 成果物sourceと検査合格版を追跡可能にする / BR-G2: content資産のstable identityと派生関係を追跡する / BR-G3: version化されたdesign tokenで成果物の視覚的一貫性を管理する / BR-G4: owned platformの変更を解析・検証・rollback可能に行う | BR-G1: コード×browser renderingとgit commit hashだけを全成果物の方式に固定しない / BR-G2: 全content実体のWordPress収束、SQLite参照及び固定派生一覧を継承しない / BR-G3: Claude Design又は単一providerをtoken正本として必須化しない / BR-G4: 既存theme解析、子theme、plugin及びbrowser攻略地図を固定方式として継承しない / BR-G2: WP一律収束 / BR-G3: provider-neutral / BR-G4: content/platform/security | CONTENT-QUALITY-GATE-LEARNING, GENAI-EXECUTION-ROUTE, WORDPRESS-CONTENT-OPERATIONS-RELEASE, WORDPRESS-PLATFORM-MAINTENANCE-RELEASE, WORDPRESS-SECURITY-MAINTENANCE-RELEASE |
| `BRG-H` | BR-H1=replace, BR-H2=replace, BR-H3=replace | BR-H1: 通常運用を自動化し人間判断が必要な局面だけを明示する / BR-H2: 外部writeのactivation scopeを人間判断へ束縛し合格済み通常operationを自動化する / BR-H3: 異常を検知して影響scopeを安全停止し必要な対応情報を提示する | BR-H1: 企画確定後human-out-of-loopと旧束縛承認だけの境界を継承しない / BR-H2: Discord承認、個別投稿の毎回承認及び旧auto-mode移行を継承しない / BR-H3: Discord通知、ApprovalTransport再利用及び通知到達による状態確定を継承しない / BR-H1: phase別判断 / BR-H2: VPS UI初回activation / BR-H2: 自動運用 / BR-H3: UI内inbox | VPS-UI-PRIMARY-HUMAN-INTERFACE, VPS-UI-INBOX-LIFECYCLE, AUTOMATED-PUBLISHING-ADMISSION, CONTENT-QUALITY-GATE-LEARNING, FR-16-NOTIFICATION-BOUNDARY |
| `BRG-I` | BR-I1=redescent, BR-I2=redescent, BR-I3=redescent, BR-I4=redescent, BR-I5=redescent, BR-I6=redescent, BR-I7=redescent | BR-I1: 複数profileのdata・資産・credential・学習を相互隔離する / BR-I2: 上流戦略学習と下流実行学習を分離し明示契約で接続する / BR-I3: 戦略仮説を根拠・反証・信頼度・対象版付きで改訂する / BR-I4: 全終端実行から適合する学習又は失敗packetを還流する; 観測前failureについて未観測の因果解釈を生成しない / BR-I5: 複数媒体の役割を共通の認識変化目標へ接続して企画・評価する / BR-I6: 主要content企画へ問題・認識変化・比較軸・価値・戦略仮説を明示する / BR-I7: 証跡を保持する; 安全な再開条件を定義する; 再実行を冪等にする | BR-I1: 旧brand名又はworkspace配置を認可境界として継承しない / BR-I2: 旧S1+ phase及び旧brief/TLP schemaを無条件継承しない / BR-I3: 旧strategy_revision schemaと旧judge工程をそのまま継承しない / BR-I4: 後知恵で原因又は効果を捏造しない; 旧packet table及び固定件数制約だけを意味保証にしない / BR-I5: 固定媒体組合せ又は旧campaign schemaを継承しない / BR-I6: 旧五宣言のfield名だけで企画品質を証明済みとみなさない / BR-I7: 三要件の一部だけで復旧可能とみなさない; SQLite状態だけを唯一の再開根拠として継承しない | BUSINESS-PROFILE-AUTHORIZATION, STRATEGY-REQUIREMENT-ADMISSION, RESEARCH-LED-CONTENT-GROWTH, PRODUCT-STATE-AUTHORITY, CONTRACT-SEMANTIC-DESCENT-V2 |
| `BRG-J` | BR-J1=redescent, BR-J2=redescent, BR-J3=redescent | BR-J1: pull・WIP制限・blocked管理・flow指標で滞留と過負荷を制御する / BR-J2: profile配下のdomainごとに正本・work・evidenceを隔離する / BR-J3: version付き戦略判断を媒体・経路・workflow bindingへ変換し追加・停止・廃止・差替えできるようにする | BR-J1: 旧Kanban state、固定WIP値及びScrum cadenceを無条件継承しない / BR-J2: filesystem path又はworkspace構成だけをdomain認可として継承しない / BR-J3: workflow row追加だけで媒体bindingを有効化しない; 旧media binding schemaを現authorityとして継承しない | CONTRACT-SEMANTIC-DESCENT-V2, BUSINESS-PROFILE-AUTHORIZATION, LEGACY-MEDIA-ADMISSION-INVENTORY, STRATEGY-REQUIREMENT-ADMISSION |

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
| `OBJ-01` | 旧L0/BR/媒体BR/REQ/FR/SR/NFR/MR/FN/AC/TCを意味レベルで全件棚卸しする | `incomplete` | legacy_l0_clause_dispositions／legacy_br_disposition_groups／legacy_requirement_meaning_inventory／legacy_strategy_quality_meaning_inventory／legacy_mr_meaning_inventory／legacy_fn_meaning_inventory／legacy_ac_meaning_inventory／legacy_tc_meaning_inventory／legacy_media_br_source_digests／legacy_media_br_item_digests／legacy_media_br_item_dispositions／legacy_media_br_meaning_migrations／legacy_media_br_dispositions／legacy_media_trace_fault_policy／legacy_media_trace_fault_dispositions／legacy_req_disposition_groups／legacy_fr_disposition_groups／legacy_orphan_requirement_groups／legacy_nfr_dispositions／legacy_media_inventory／legacy_derived_contract_policy／legacy_phase_fault_dispositions／legacy_phase_fault_classifications／legacy_trace_fault_policy／legacy_trace_fault_dispositions／legacy_test_id_dispositions／provider_neutral_execution_policy／provider_policy_bindings／G-REQ-LEGACY-MEDIA-TRACE FAIL | 旧BR/REQ/FR 139 ID、SR/NFR 30 ID、MR 54 ID、FN 61 ID、AC 252 IDはsource/parent meaning snapshot、value/safety/HJ/obsolete mechanism候補、高risk境界を全件記録済み。TC 258 IDは旧test oracle全field、親AC semantic digest、critical controls、旧phase/alias処遇を全件記録し、親再降下までは全件deferとしている。いずれもPO未承認であるため、候補の独立監査とPO分類receiptを得たうえで、旧compatibility viewとのsemantic drift、BR↔FR/SR双方向trace、BR→REQ→FR/SR/NFR階層trace、REQ→FN、semantic responsibility及び全層semantic dimensionsを解消し、媒体孤立nodeと48片方向edgeを新capability traceへ再降下し、phase faultのedge別処遇をPO決定して全refinementをfreezeする |
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
- **semantic digest**: `sha256:a98d63668a6bbf93c4918ea12a062780d803e7b6633f0e808c5e65427024bf27`

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
  - `RDQ-AGENT-NEO-PRODUCT-EVOLUTION-RELEASE-01` (`release_scope`): 対象component、互換性policy、rollback outcome、回帰受入範囲及びrepo write authorityをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:9d01b9da1cb025a10c43e6be4fc791ede640b687bc48bfa7271adc27aca632ba`

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
  - `RDQ-AGENT-NEO-SITE-BUILD-RELEASE-01` (`release_scope`): site-build capability閉集合、受入順、migration admission及びrollback outcomeをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:9878b98db88c79f197240edfdca11c35e40dd265f4d8837b289ee5dac0099618`

## RRF-AUTO-MODE-DECISION-AUTHORITY — AUTO-MODE-DECISION-AUTHORITY

- **状態**: `superseded` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `historical_superseded` （PO receiptとFull V再降下までは実装不可）
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
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:32c3282dc43db8348b9114f9dc31ca8c3d1784b06a520362a2b71b8a420f9167`

## RRF-AUTOMATED-PUBLISHING-ADMISSION — AUTOMATED-PUBLISHING-ADMISSION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000138 RDE-000144 RDE-000150 RDE-000154 RDE-000155
- **主体**: ユーザー／製品runtime
- **受益者**: 毎回承認せず自動運用を監督するユーザー
- **価値**: VPS UIで初回scopeを承認した後も成果物gateを維持して自動運用する
- **task**: activation要求をinboxへ記録する／認証済みUIでscope/revisionを再表示し直前認可後に承認する／各成果物のcampaign/funnel role/content purpose/risk/quality admissionを独立検査する／attended-only operationを自動writeから分離する／取消・権限喪失・必須risk gate集合/risk境界/activation policy変更時にwriteを停止する／停止後にscopeを再表示してre-activationする
- **workflow**: activation要求→inboxへapproval_waiting記録→認証済みUIでscope/revision再表示→直前認可→明示承認→自動運用又はattended-only→成果物別purpose/risk/quality gate→停止条件成立→明示re-activation待ち
- **対象範囲**: profile/media/account/operation単位activation／campaign/funnel role/content purpose/risk binding／attended-only operation／自動公開admission／取消・停止・re-activation
- **対象外**: 全媒体一括activation／scope未指定activationの既定補完／毎回の公開承認／quality gate省略／feedback scopeによるwrite activation拡張／固定期限の全対象一律強制
- **禁止事項**: inbox item操作だけでactivationを成立させること／scope未指定のactivation／machine eligibilityだけのactivation／attended-only operationの自動write昇格／scope外write／activation passによる成果物gate省略／不合格成果物公開／媒体account別/個別feedback rule更新だけでactivationを停止すること／停止後に毎回承認modeへ暗黙復帰してwriteを続けること
- **人間判断**: 初回activation、scope拡張、attended-only個別実行、必須risk gate集合/risk境界/activation policy変更後の再開、取消、停止後re-activationはユーザー
- **副作用**: activation scope内かつ成果物gate合格時の自動媒体write／停止条件成立時の外部write停止
- **証跡**: inbox approval_waiting receipt／activation decision receipt／scope/revision/fresh authorization binding／campaign/funnel role/content purpose/risk binding／execution mode／gate pass receipt／revocation/stop/re-activation negative test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-AUTO-PUBLISH-P: approval_waitingをinboxへ記録し、認証済みUIでscope/revision再表示と直前認可後に承認されたscope内でgate合格成果物だけを毎回承認なしで実行する （RST-AUTO-PUBLISH-P）
  - `negative` RAC-AUTO-PUBLISH-N: inbox操作だけの承認、scope未指定、未承認、scope外、取消、権限喪失、必須risk gate/risk境界/activation policy変更、停止条件成立又はgate不合格の外部writeを拒否する （RST-AUTO-PUBLISH-N）
  - `boundary` RAC-AUTO-PUBLISH-B: 媒体account別又は個別feedbackの下位rule更新は再検査だけ行い、停止後は毎回承認modeへ戻さず対象scopeの明示re-activationまでwriteを停止する （RST-AUTO-PUBLISH-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:4e3df9a130b8c7b919b6eb5dafe68112d84bfc3210cc1538c991c1db24c74313`

## RRF-BUSINESS-PROFILE-AUTHORIZATION — BUSINESS-PROFILE-AUTHORIZATION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000130 RDE-000131 RDE-000174
- **主体**: PO／profile所有者／許可運用者
- **受益者**: 隔離された複数事業の所有者
- **価値**: stable profile IDでprincipal/resource/actionを隔離し越境を防ぐ
- **task**: grant ID/revision/digestとprincipal/profile/resource/operation/effect/expiryを検証して認可又は拒否する／cross-profile、高作用effect及びmulti-principal移行を明示再認可する
- **workflow**: authentication/session→explicit grant lookup→revision/expiry/scope/effect検証→operation又はdeny→profile-bound authorization receipt
- **対象範囲**: profile lifecycle／membership/role／resource/action／横断集約／移管/削除／explicit grant revision/digest/expiry／effect classes list/read/seen/ack/state_write/external_write/money/delete/transfer／deny state invariance
- **対象外**: 表示brand名を認可IDとすること／具体RBAC製品
- **禁止事項**: 暗黙共有／権限合算／cross-profile write／credential/data/evidence越境／authentication又はsession成立をauthorizationとみなす／membership又はrole名だけからpermissionを推論する／readからwrite、cross-profile aggregate又は別effectを推論する／delete/transferで暗黙cascade又は旧grant再利用を行う／将来multi-principal化で既存session/grantを自動継承する
- **人間判断**: membership、role、横断集約、移管、削除は許可principal
- **副作用**: 現段階は要求候補のみ
- **証跡**: authorization matrix／profile-bound receipt／cross-profile negative case／PO receipt／grant ID/revision/semantic digest/expiry receipt／cross-profile and effect escalation negative tests／denial state/revision invariance／transfer/delete separate transition evidence
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-PROFILE-AUTH-P: 有効なgrant ID、principal、profile、resource、operation、effect、grant revision、grant semantic digest及びexpiryへexact束縛したoperationだけを許可する （RST-PROFILE-AUTH-P）
  - `negative` RAC-PROFILE-AUTH-N: missing/unknown/stale/expired/scope mismatch、暗黙effect escalation、membership/role推論及びcross-profile without explicit grantを拒否する （RST-PROFILE-AUTH-N）
  - `boundary` RAC-PROFILE-AUTH-B: owner移管、delete/transfer、grant revision競合又はmulti-principal移行では旧session/grantを継承せず、製品state/revisionを維持して再認可までfail-closeする （RST-PROFILE-AUTH-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:ad26d3f40b9250e77f8e8be1aa3e387f294d170b05d3eef01b91e819c061b87a`

## RRF-CONTENT-QUALITY-GATE-LEARNING — CONTENT-QUALITY-GATE-LEARNING

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000139 RDE-000145 RDE-000151 RDE-000163 RDE-000164
- **主体**: ユーザー／content生成agent／quality gate
- **受益者**: 確認負荷を減らすユーザーと品質を受けるaudience
- **価値**: 不合格成果物を人間へ流さずfeedbackを再利用可能なruleへ変えて、人に有用で独自性と根拠のある品質を継続改善する
- **task**: 成果物を検査する／機械可読なverdictとreason codeを記録する／retry系列中のrule revisionを凍結する／外部設定された回数・時間・費用上限内で不合格を自動修正又は再生成する／解消不能時は正式な人間確認又は次工程へ送らずblockedで停止する／feedbackをscope付きruleへ変換する／明示scopeがないfeedbackはsource feedbackのmedia_account_idを既定scopeとして導出する／対象成果物を再検査する／独自価値とclaim-source対応を検査する／retry budgetを使い切ってblockedになった場合だけVPS UI内inboxへ通知eventを記録する
- **workflow**: 生成→gate→不合格時同一rule revisionで修正/再生成→再検査→合格時のみ次工程／上限到達時blocked＋UI inbox通知→feedback rule化→明示scope又はsource feedbackのmedia_account_idへ束縛→新gate実行→対象再検査
- **対象範囲**: 禁止語／表現／形式/型／根拠／対象audienceへの有用性／独自research/分析/経験／claim-source対応と鮮度／誇張しない見出し／structured feedback／source feedbackから導出したmedia account scope／rule revision／version付きretry budget／停止成果物と証跡の診断閲覧／未公開成果物再検査／retry exhaustion時のVPS UI内inbox通知
- **対象外**: 製品codeへのrule hard-code／非対応媒体の公開済み成果物変更／通常の不合格retryごとの通知
- **禁止事項**: 不合格成果物の人間reviewへの正式投入、次工程投入又は公開／retry中のrule自己緩和／無限再生成／retry budget未知時の実行継続／scope未指定feedbackの全体適用／feedback scopeによるwrite activation拡張／順位操作目的の大量生成／query variationごとの低価値量産／付加価値のないsource要約／retry exhaustion前の人間通知／inbox記録失敗によるblocked状態のrollback
- **人間判断**: feedback内容と明示scopeはユーザー。明示scopeがない場合はsource feedbackに束縛されたmedia_account_idだけを機械的に既定scopeとする。risk必須ruleを最優先し、媒体account rule、個別feedbackの順で合成する。risk境界内の通常rule更新はAI。ただしretry中の成果物には新ruleを遡及しない
- **副作用**: 対応媒体のgate合格済み公開成果物へのupdate-in-place／retry exhaustion時のVPS UI内inbox event記録
- **証跡**: artifact/claim-bound verdict／reason code／applied rule revision／rule revision／fixture／gate result／regeneration history／retry count/time/cost budget／retry exhaustion/stop receipt／source feedback IDとderived media_account_id scope evidence／claim-source map／originality/value assessment／scope-bound update receipt／source:<https://developers.google.com/search/docs/fundamentals/creating-helpful-content／source:https://developers.google.com/search/docs/fundamentals/ai-optimization-guide／blocked> source stateと通知IDのbinding／retry exhaustion inbox recorded/failed receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-CONTENT-GATE-P: 独自価値、claim-source対応及び対象audienceへの有用性を含むgateがartifact/claim、verdict、reason code、rule revisionを記録する。明示scopeがないfeedbackはsource feedbackのmedia_account_idだけへ束縛し、不合格を同一rule revisionで人間確認前に再生成して合格成果物だけを次工程へ進める。retry budgetを使い切っても不合格ならblocked状態とVPS UI内inbox通知を同じsource artifactへ束縛する （RST-CONTENT-GATE-P）
  - `negative` RAC-CONTENT-GATE-N: 不合格の正式review、次工程又は公開、retry中のrule自己緩和、scope外rule適用、retry budget未知時の継続、順位操作目的の低価値量産及び非対応媒体の公開済み変更を拒否する。通常retryごとの通知及び通知失敗によるblocked解除も拒否する （RST-CONTENT-GATE-N）
  - `boundary` RAC-CONTENT-GATE-B: 明示scopeがないfeedbackはsource feedbackのmedia_account_idだけをderived scopeとし、同一媒体の別account、全profile又は全媒体へ拡張しない。retry budget上限到達時は未合格成果物をblockedで停止し、VPS UI内inboxへ一件のdurable eventを記録して診断閲覧を許可する。通知記録失敗でもblockedを維持する。update-in-place能力不明又は非対応なら公開済み成果物へ通知を含め何もしない （RST-CONTENT-GATE-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:1c6e925b3a6b05f5ce4671469b53b18a6598191d550560da79df5502fbdf3721`

## RRF-CONTENT-RISK-CLASSIFICATION — CONTENT-RISK-CLASSIFICATION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000140 RDE-000146 RDE-000152
- **主体**: ユーザー／risk classification agent／quality gate
- **受益者**: 安全で信頼できる情報を受けるaudienceとユーザー
- **価値**: case-by-caseの好みを反映しつつ、人の健康、金融上の安定、安全又は社会の福祉に影響するYMYL相当contentを厳格に扱う
- **task**: content/claimをrisk分類する／risk class、確信度又は不確実性、根拠及びgate-set revisionを束縛する／健康・金融安定・安全・社会的福祉への影響を評価する／必須gateを選ぶ／個別の好みruleを合成する／分類と検査根拠を保存する
- **workflow**: content/claim抽出→影響軸別risk分類→分類完全性確認→必須gate→好みrule合成→検査→evidence
- **対象範囲**: content/claim risk／risk confidence/uncertainty／健康／金融上の安定／安全／社会の福祉/well-being／YMYL／根拠/鮮度/経験/専門性/表現/safety gate／case-by-case preference／停止成果物と分類証跡の診断閲覧／version付きconfidence rule
- **対象外**: ブランド一律risk固定／好みによる最低基準緩和／要件へ埋め込む固定confidence閾値
- **禁止事項**: feedback又は成長KPIによる必須risk gate迂回／risk class又は分類根拠欠落時の正式review、次工程又は公開／不確実時に低riskへ推測しない
- **人間判断**: ユーザーは案件、成果物又はclaimごとの好みを指定できる
- **副作用**: 適用gate集合とcontent可否の変更
- **証跡**: risk class/confidence binding／classification rationale／impact-axis assessment／gate-set revision／rule composition／risk gate result／uncertainty negative test／source:<https://developers.google.com/search/docs/fundamentals/creating-helpful-content>
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-CONTENT-RISK-P: claimへrisk class、確信度又は不確実性、根拠及びgate-set revisionを束縛し、必須gateと個別好みを合成して検査する （RST-CONTENT-RISK-P）
  - `negative` RAC-CONTENT-RISK-N: 好み、feedback又はKPIでYMYL等の必須gateを弱めること及びrisk情報欠落の成果物を正式review、次工程又は公開へ進めることを拒否する （RST-CONTENT-RISK-N）
  - `boundary` RAC-CONTENT-RISK-B: risk分類が欠落又は不確実なら全影響軸のYMYL相当を含む最高厳格度で扱い、診断閲覧だけ許可して再調査又は分類解決後の再検査まで停止する （RST-CONTENT-RISK-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:4ba4a208fcc0dcdcd551be40c81eadc31b75f311fa8274f8d8dfe66b20b88c49`

## RRF-CONTRACT-SEMANTIC-DESCENT-V2 — CONTRACT-SEMANTIC-DESCENT-V2

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000103 RDE-000104 RDE-000170
- **主体**: PO／要求分析者／AC/TC作成者
- **受益者**: 責務と権限を推測せず実装・検証する担当者
- **価値**: 要求からAC/TCまで意味軸・scope・PO判断receiptを型付きで閉じる
- **task**: 直接必須fieldを決める／継承可能/禁止fieldを決める／14 HJ経路をreceiptへ降下する／mutationで欠落を拒否する／下位契約の直接必須軸と選択句digest継承を分離する／multi-parentの選択句exact unionと競合処遇を検証する／安全/HJ/prohibitionの非弱化と旧方式非継承を検証する
- **workflow**: BR意味→REQ正規化→FR/SR/NFR/MR/FN降下→AC/TC反証→PO receipt検査
- **対象範囲**: actor／beneficiary／value／workflow／scope／prohibition／human judgement／side effect／evidence／phase／decision receipt／stable child/parent clause ID／parent semantic digest／explicit delta／conflict disposition／direct/inherited/replaced/deferred partition
- **対象外**: target IDをbusiness scopeとみなすこと／agent審査をPO判断とみなすこと
- **禁止事項**: 欠落fieldを実装者が推測しない／機械判定でPO decisionを代替しない／multi-parentを暗黙unionする／safety/prohibition/human judgementを子で削除又は弱化する／provider/runtime/route/storage/fixture/mock/固定閾値/旧phase/旧通知承認transportをpositive継承する／高作用契約のactor/scope/HJ/effect/evidence/phaseをfully inherited又は空にする
- **人間判断**: 意味fieldの継承可否と各PO判断点はPOが凍結
- **副作用**: 現段階は要求契約の候補化のみ
- **証跡**: schema／継承mapping／14 HJ経路のreceipt AC/TC／negative mutation／PO receipt／ID×clause disposition exact partition／parent clause/semantic digestとdelta／conflict/cycle/stale digest mutation／高作用direct dimension negative test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-SEMANTIC-DESCENT-P: 直接必須軸と選択親句digest、delta、owner、evidenceが閉じ、安全/HJ/prohibitionを弱化しない下位契約だけを次工程へ進める （RST-SEMANTIC-DESCENT-P）
  - `negative` RAC-SEMANTIC-DESCENT-N: stale digest、暗黙union、安全弱化、旧方式再混入、高作用の継承のみ又はcycleを拒否する （RST-SEMANTIC-DESCENT-N）
  - `boundary` RAC-SEMANTIC-DESCENT-B: 親意味が未classified、cutover blocked又は競合未処置なら子をdeferredとしclassifiedへ昇格しない （RST-SEMANTIC-DESCENT-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:b1fe074d7bbcc73d48f1d2f7e0683e4ee5b3a19a8e67ea6fbf62f864cffdd2e3`

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

- **状態**: `superseded` ／ revision 2 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `historical_superseded` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000005 RDE-000022 RDE-000023 RDE-000041 RDE-000042 RDE-000052 RDE-000060 RDE-000068
- **主体**: PO／製品通知runtime／Discord community運用者
- **受益者**: 用途混同を避けるPOとコミュニティ
- **価値**: 旧Discord複数用途候補を現要求へ継承せず、通知不採用とcommunity媒体を別の現行subjectへ移す
- **task**: 旧候補の再開導線を閉じる／通知拒否とcommunity媒体を別subjectへ引き渡す
- **workflow**: 旧候補識別→通知route拒否→DISCORD-NOTIFICATION-REJECTION-BOUNDARYへ移管→community要件はDISCORD-COMMUNITY-MARKETING-ROUTEへ移管
- **対象範囲**: 旧Discord承認通知候補／旧Discord運用通知候補／旧Discord deep-link候補／旧Discord媒体候補
- **対象外**: 現行通知要求の所有／現行community媒体要求の所有／設計又は実装
- **禁止事項**: 旧候補からDiscord通知adapterを再開しない／旧候補をcommunity媒体の実行許可にしない／個人user accountを無人操作しない
- **人間判断**: PO回答RDE-000158により通知routeは不採用。community媒体は別subjectで判断する
- **副作用**: なし。旧候補はsupersededであり外部送信を許可しない
- **証跡**: supersession evidence／通知route拒否negative test／community subject分離test
- **phase**: `requirements_history`
- **受入候補**:
  - `positive` RAC-DISCORD-BOUNDARY-P: 旧候補を現行入力から除外し、通知拒否とcommunity媒体を別subjectへ一意に引き渡す （RST-DISCORD-BOUNDARY-P）
  - `negative` RAC-DISCORD-BOUNDARY-N: 旧候補による通知route再開、community実行許可、credential共有及びself-botを拒否する （RST-DISCORD-BOUNDARY-N）
  - `boundary` RAC-DISCORD-BOUNDARY-B: 旧候補を参照した全外部送信を拒否し、再開条件を生成しない （RST-DISCORD-BOUNDARY-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:73e6cea0dff4bfd4f20372fa10ca44db500318eaa7a6dae4e69e7419763affd7`

## RRF-DISCORD-NOTIFICATION-REJECTION-BOUNDARY — DISCORD-NOTIFICATION-REJECTION-BOUNDARY

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000156 RDE-000157 RDE-000158
- **主体**: PO／製品通知runtime／Discord community運用者
- **受益者**: 通知誤送信と誤決定を避けるユーザーとcommunity
- **価値**: Discord community marketingと製品通知・開発PR通知を恒久分離する
- **task**: 通知purposeを判定する／Discord通知routeを不採用として拒否する／community capabilityとのcross-purpose利用を拒否する
- **workflow**: 通知要求→purpose判定→Discord route拒否→VPS UI inboxに限定
- **対象範囲**: 承認通知／運用通知／deep-link補助／開発PR通知との分離
- **対象外**: Discord community marketing operation
- **禁止事項**: Discord通知adapterの再開／通知routeのdeferred化／community credential/account/channel/evidenceの通知流用
- **人間判断**: Discord通知不採用はPO決定。community方針は別media capabilityで判断する
- **副作用**: Discord通知送信なし
- **証跡**: notification route rejection receipt／community/notification cross-purpose negative test／PO回答source
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-DISCORD-NOTIFICATION-REJECT-P: 製品通知をVPS UI inboxに限定しDiscordへ送信しない （RST-DISCORD-NOTIFICATION-REJECT-P）
  - `negative` RAC-DISCORD-NOTIFICATION-REJECT-N: 承認通知、運用通知、deep-link補助又は開発PR通知のDiscord routeとcommunity credential共有を拒否する （RST-DISCORD-NOTIFICATION-REJECT-N）
  - `boundary` RAC-DISCORD-NOTIFICATION-REJECT-B: 未知purpose又はDiscord通知routeが指定された場合は送信せず、再開条件を生成しない （RST-DISCORD-NOTIFICATION-REJECT-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:9eaf6bb8e88b9ef540c8e0d26ba71ecff670cb0e38f05ce74397722b0ec7d88b`

## RRF-EXTERNAL-BROWSER-AUTOMATION-ROUTE — EXTERNAL-BROWSER-AUTOMATION-ROUTE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000136 RDE-000142 RDE-000148
- **主体**: 媒体account所有者／connector管理者／製品runtime
- **受益者**: 許可経路で媒体を運用するユーザー
- **価値**: 公式経路を優先しつつ必要なPlaywright automationとbrowser確認をoperation単位で安全に使う
- **task**: 公式API/MCP能力を判定する／credential能力と製品側operation強制を判定する／許可時だけPlaywright fallback又は確認を行う
- **workflow**: operation要求→API/MCP確認→credential/operation allow-list確認→実行前plan検査→route許可判定→実行→receipt照合→browser確認
- **対象範囲**: 公式API／公式MCP／Playwright fallback／登録済みaccount/operation/resourceのbrowser結果確認／operation allow-list
- **対象外**: 他browser engine／経路不明operation
- **禁止事項**: 媒体全体へのbrowser write一括許可／allow-list外browser read／利用規約又はcredential境界の推測／製品側でoperation境界を強制できない無人browser write
- **人間判断**: write routeの採用と残余riskは対象登録時の許可主体
- **副作用**: 許可された媒体read又はwrite
- **証跡**: route decision／principal/effect binding／credential capability／execution plan／operation enforcement receipt／execution/confirmation receipt／negative route test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-BROWSER-ROUTE-P: 公式API/MCPを優先し、最小credential又はallow-list、実行前plan、実行後receiptで強制された許可operationだけPlaywright fallback又は確認を実行する （RST-BROWSER-ROUTE-P）
  - `negative` RAC-BROWSER-ROUTE-N: route、principal、effect、credential能力、read resource scope、operation強制又は規約境界が未確定のbrowser操作を拒否する （RST-BROWSER-ROUTE-N）
  - `boundary` RAC-BROWSER-ROUTE-B: 媒体credentialが広く製品側でもoperation境界を強制できないwriteは自動実行せずattended-only又はdeferredを維持する （RST-BROWSER-ROUTE-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:656e7c8cab8e861e8c0cc39f2633f2f59605471734441a9fb7f41a127d6fc5d8`

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
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-FR-16-NOTIFICATION-P: 異常時に停止を先に永続化しUI内inbox記録attemptと記録結果を別証跡化する （RST-FR-16-NOTIFICATION-P）
  - `negative` RAC-FR-16-NOTIFICATION-N: inbox書込み失敗でも停止状態をrollbackせずfailed receiptを残す （RST-FR-16-NOTIFICATION-N）
  - `boundary` RAC-FR-16-NOTIFICATION-B: 重複event・retry上限・再開判断待ちで二重通知や自動再開を起こさない （RST-FR-16-NOTIFICATION-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:fa328819de985985217c8b7268ee67b0fb1c725e7437b19c3dde8dc6498e0b2d`

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
  - `RDQ-FR-SLICE-AUTHORITY-ALIGNMENT-01` (`authority_choice`): 現行phase faultのFR↔FN/AC/TCC edge別処遇と旧IDのsupersession規則をPO確認する （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:f6b8ee938abf2391b9de7ce1729bfa7ecf1b832a7249ae334f169cb40082e4e2`

## RRF-GENAI-EXECUTION-ROUTE — GENAI-EXECUTION-ROUTE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000006 RDE-000024 RDE-000025 RDE-000043 RDE-000044
- **主体**: 製品runtime／PO／attended運用者
- **受益者**: 規約違反やvendor lock-inを避ける運用者
- **価値**: provider-neutralな許可経路で生成し、禁止されたconsumer Web UI自動化を排除する
- **task**: provider capabilityを登録する／許可API adapterで生成する／不能時に停止又はattended manualへ渡す
- **workflow**: capability/規約/quota確認→API実行→証跡→不能時fail-close/attended handoff
- **対象範囲**: provider-neutral API adapter／個別登録済みCLI adapter／attended manual fallback
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
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:37d8371bbc7053ae3168627da6c58b39cc44c9816d5bf5904fdd6bfef8e5d755`

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

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
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
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:6f8d4c56fa4d22900b6ba39d6c7392e766f8adc3ea0eb62a3f910638d888cd0e`

## RRF-MEDIA-HARNESS-AFFILIATE — MEDIA-HARNESS-AFFILIATE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000197 RDE-000198
- **主体**: PO／アフィリエイト媒体運用者／製品runtime
- **受益者**: アフィリエイトを他媒体から分離して監督したいPO／アフィリエイト媒体運用者
- **価値**: アフィリエイトを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをアフィリエイト単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: アフィリエイトハーネスの承認境界・write境界を定義する／アフィリエイトのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: アフィリエイト専用ハーネスの構成／アフィリエイトの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: アフィリエイトの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: アフィリエイトハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: アフィリエイト別refinementのPO凍結receipt／アフィリエイト承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-AFFILIATE-P: アフィリエイトの承認境界・write境界・route policyがアフィリエイト専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-AFFILIATE-P）
  - `negative` RAC-MEDIA-HARNESS-AFFILIATE-N: アフィリエイトと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-AFFILIATE-N）
  - `boundary` RAC-MEDIA-HARNESS-AFFILIATE-B: アフィリエイトハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-AFFILIATE-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-AFFILIATE-01` (`requirements_policy`): アフィリエイトハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:c441fd35643a1d5580ce750983f4e679fb3fa326769d00d8e8fd635a9a7ccb70`

## RRF-MEDIA-HARNESS-CANVA — MEDIA-HARNESS-CANVA

- **状態**: `rejected` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000199 RDE-000200 RDE-000203
- **主体**: PO／Canva媒体運用者／製品runtime
- **受益者**: Canvaを他媒体から分離して監督したいPO／Canva媒体運用者
- **価値**: Canvaを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをCanva単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: Canvaハーネスの承認境界・write境界を定義する／Canvaのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: Canva専用ハーネスの構成／Canvaの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: Canvaの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: Canvaハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: Canva別refinementのPO凍結receipt／Canva承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-CANVA-P: Canvaの承認境界・write境界・route policyがCanva専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-CANVA-P）
  - `negative` RAC-MEDIA-HARNESS-CANVA-N: Canvaと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-CANVA-N）
  - `boundary` RAC-MEDIA-HARNESS-CANVA-B: Canvaハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-CANVA-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-CANVA-01` (`requirements_policy`): Canvaハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:a588be5196502530dae688f0c487444a81094b258f80c33b779c799b9ffa6fab`

## RRF-MEDIA-HARNESS-DISCORD-COMMUNITY — MEDIA-HARNESS-DISCORD-COMMUNITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000191 RDE-000192
- **主体**: PO／Discord community媒体運用者／製品runtime
- **受益者**: Discord communityを他媒体から分離して監督したいPO／Discord community媒体運用者
- **価値**: Discord communityを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをDiscord community単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: Discord communityハーネスの承認境界・write境界を定義する／Discord communityのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: Discord community専用ハーネスの構成／Discord communityの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: Discord communityの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: Discord communityハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: Discord community別refinementのPO凍結receipt／Discord community承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-DISCORD-COMMUNITY-P: Discord communityの承認境界・write境界・route policyがDiscord community専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-DISCORD-COMMUNITY-P）
  - `negative` RAC-MEDIA-HARNESS-DISCORD-COMMUNITY-N: Discord communityと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-DISCORD-COMMUNITY-N）
  - `boundary` RAC-MEDIA-HARNESS-DISCORD-COMMUNITY-B: Discord communityハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-DISCORD-COMMUNITY-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-DISCORD-COMMUNITY-01` (`requirements_policy`): Discord communityハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:378dc3e00a9b55a482d4f97f08d9563e4ddcc5ad58329c799991e7ba3775dc62`

## RRF-MEDIA-HARNESS-GENAI — MEDIA-HARNESS-GENAI

- **状態**: `rejected` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000195 RDE-000196 RDE-000202
- **主体**: PO／生成AI媒体運用者／製品runtime
- **受益者**: 生成AIを他媒体から分離して監督したいPO／生成AI媒体運用者
- **価値**: 生成AIを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyを生成AI単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: 生成AIハーネスの承認境界・write境界を定義する／生成AIのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: 生成AI専用ハーネスの構成／生成AIの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: 生成AIの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: 生成AIハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: 生成AI別refinementのPO凍結receipt／生成AI承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-GENAI-P: 生成AIの承認境界・write境界・route policyが生成AI専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-GENAI-P）
  - `negative` RAC-MEDIA-HARNESS-GENAI-N: 生成AIと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-GENAI-N）
  - `boundary` RAC-MEDIA-HARNESS-GENAI-B: 生成AIハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-GENAI-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-GENAI-01` (`requirements_policy`): 生成AIハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:842f5c521b450694bac59cffb3843ed34af611b543da0ec16537f63022314111`

## RRF-MEDIA-HARNESS-INSTAGRAM — MEDIA-HARNESS-INSTAGRAM

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000206 RDE-000207
- **主体**: PO／Instagram媒体運用者／製品runtime
- **受益者**: Instagramを他媒体から分離して監督したいPO／Instagram媒体運用者
- **価値**: Instagramを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをInstagram単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: Instagramハーネスの承認境界・write境界を定義する／Instagramのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: Instagram専用ハーネスの構成／Instagramの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: Instagramの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: Instagramハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: Instagram別refinementのPO凍結receipt／Instagram承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-INSTAGRAM-P: Instagramの承認境界・write境界・route policyがInstagram専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-INSTAGRAM-P）
  - `negative` RAC-MEDIA-HARNESS-INSTAGRAM-N: Instagramと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-INSTAGRAM-N）
  - `boundary` RAC-MEDIA-HARNESS-INSTAGRAM-B: Instagramハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-INSTAGRAM-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-INSTAGRAM-01` (`requirements_policy`): Instagramハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:3233ecaf073b185108c83c9a0f7a42c8e3c390a7d2bbe896cfd43711f4f217f1`

## RRF-MEDIA-HARNESS-LINE — MEDIA-HARNESS-LINE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000193 RDE-000194
- **主体**: PO／LINE媒体運用者／製品runtime
- **受益者**: LINEを他媒体から分離して監督したいPO／LINE媒体運用者
- **価値**: LINEを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをLINE単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: LINEハーネスの承認境界・write境界を定義する／LINEのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: LINE専用ハーネスの構成／LINEの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: LINEの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: LINEハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: LINE別refinementのPO凍結receipt／LINE承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-LINE-P: LINEの承認境界・write境界・route policyがLINE専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-LINE-P）
  - `negative` RAC-MEDIA-HARNESS-LINE-N: LINEと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-LINE-N）
  - `boundary` RAC-MEDIA-HARNESS-LINE-B: LINEハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-LINE-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-LINE-01` (`requirements_policy`): LINEハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:1f38341edf7eb4e2149c43b7d5e32920679036784f42ed3a3d86f069e7cdda18`

## RRF-MEDIA-HARNESS-TIKTOK — MEDIA-HARNESS-TIKTOK

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000210 RDE-000211
- **主体**: PO／TikTok媒体運用者／製品runtime
- **受益者**: TikTokを他媒体から分離して監督したいPO／TikTok媒体運用者
- **価値**: TikTokを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをTikTok単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: TikTokハーネスの承認境界・write境界を定義する／TikTokのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: TikTok専用ハーネスの構成／TikTokの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: TikTokの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: TikTokハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: TikTok別refinementのPO凍結receipt／TikTok承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-TIKTOK-P: TikTokの承認境界・write境界・route policyがTikTok専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-TIKTOK-P）
  - `negative` RAC-MEDIA-HARNESS-TIKTOK-N: TikTokと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-TIKTOK-N）
  - `boundary` RAC-MEDIA-HARNESS-TIKTOK-B: TikTokハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-TIKTOK-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-TIKTOK-01` (`requirements_policy`): TikTokハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:d1dcdd7d1937fca383b06111ae25b6c77a2c5f00407bf44456129520d99cc684`

## RRF-MEDIA-HARNESS-WORDPRESS — MEDIA-HARNESS-WORDPRESS

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000189 RDE-000190
- **主体**: PO／WordPress媒体運用者／製品runtime
- **受益者**: WordPressを他媒体から分離して監督したいPO／WordPress媒体運用者
- **価値**: WordPressを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをWordPress単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: WordPressハーネスの承認境界・write境界を定義する／WordPressのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: WordPress専用ハーネスの構成／WordPressの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: WordPressの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: WordPressハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: WordPress別refinementのPO凍結receipt／WordPress承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-WORDPRESS-P: WordPressの承認境界・write境界・route policyがWordPress専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-WORDPRESS-P）
  - `negative` RAC-MEDIA-HARNESS-WORDPRESS-N: WordPressと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-WORDPRESS-N）
  - `boundary` RAC-MEDIA-HARNESS-WORDPRESS-B: WordPressハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-WORDPRESS-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-WORDPRESS-01` (`requirements_policy`): WordPressハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:eeab02880e90fb0d7777b8dc9985dd4e7c081380ce9ce21d49bb64cfce6b92fa`

## RRF-MEDIA-HARNESS-X-TWITTER — MEDIA-HARNESS-X-TWITTER

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000204 RDE-000205
- **主体**: PO／X（Twitter）媒体運用者／製品runtime
- **受益者**: X（Twitter）を他媒体から分離して監督したいPO／X（Twitter）媒体運用者
- **価値**: X（Twitter）を1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをX（Twitter）単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: X（Twitter）ハーネスの承認境界・write境界を定義する／X（Twitter）のroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: X（Twitter）専用ハーネスの構成／X（Twitter）の承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: X（Twitter）の承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: X（Twitter）ハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: X（Twitter）別refinementのPO凍結receipt／X（Twitter）承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-X-TWITTER-P: X（Twitter）の承認境界・write境界・route policyがX（Twitter）専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-X-TWITTER-P）
  - `negative` RAC-MEDIA-HARNESS-X-TWITTER-N: X（Twitter）と他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-X-TWITTER-N）
  - `boundary` RAC-MEDIA-HARNESS-X-TWITTER-B: X（Twitter）ハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-X-TWITTER-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-X-TWITTER-01` (`requirements_policy`): X（Twitter）ハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:1ca89f4f3f2df277091a65b2773c8cbae28065110c0a80a4b3f1849cbe4d5f97`

## RRF-MEDIA-HARNESS-YOUTUBE — MEDIA-HARNESS-YOUTUBE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `deferred_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000208 RDE-000209
- **主体**: PO／YouTube媒体運用者／製品runtime
- **受益者**: YouTubeを他媒体から分離して監督したいPO／YouTube媒体運用者
- **価値**: YouTubeを1つの独立ハーネスとして分離し、承認境界・write境界・障害影響・route policyをYouTube単位で独立に凍結・運用でき、将来の独立リポジトリ分離を自己完結に行える
- **task**: YouTubeハーネスの承認境界・write境界を定義する／YouTubeのroute policy・credential scope・証跡を自媒体refinementへ束縛する／共有基盤との分離線と独立リポジトリ分離条件を確定する
- **workflow**: candidate→媒体別refinement降下→媒体別PO凍結→媒体別release受入→将来の独立リポジトリ分離
- **対象範囲**: YouTube専用ハーネスの構成／YouTubeの承認境界・write境界・route policy束縛／独立リポジトリ分離前提の自己完結設計
- **対象外**: 他媒体ハーネスの内容／共有基盤の実装方式選択（design-later）／外部リポジトリの実作成（PO明示指示まで行わない）／PO approval又は要求freeze
- **禁止事項**: YouTubeの承認・write境界を他媒体ハーネスへ混載しない／分離を理由に承認境界・禁止事項・fail-close規律を弱めない／PO指示なしに外部リポジトリを作成しない
- **人間判断**: YouTubeハーネスの境界確定・採否・freeze・リポジトリ分離時期はPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: YouTube別refinementのPO凍結receipt／YouTube承認境界のtyped contract／独立リポジトリ分離条件の記録
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-HARNESS-YOUTUBE-P: YouTubeの承認境界・write境界・route policyがYouTube専用refinementだけへ束縛された独立ハーネスとして構成される （RST-MEDIA-HARNESS-YOUTUBE-P）
  - `negative` RAC-MEDIA-HARNESS-YOUTUBE-N: YouTubeと他媒体の承認境界・write境界を単一ハーネスへ混載した構成、及びPO指示なしの外部リポジトリ作成を拒否する （RST-MEDIA-HARNESS-YOUTUBE-N）
  - `boundary` RAC-MEDIA-HARNESS-YOUTUBE-B: YouTubeハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで自媒体側だけを停止する （RST-MEDIA-HARNESS-YOUTUBE-B）
- **PO個別質問**:
  - `RDQ-MEDIA-HARNESS-YOUTUBE-01` (`requirements_policy`): YouTubeハーネスの承認境界・write境界・共有基盤との分離線、及び独立リポジトリ分離の時期・条件はどこで確定するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:ade8e528e0fc5feca7bc4b0c3ae3dc586564a2816e09716433af53c726b93b53`

## RRF-MEDIA-PER-MEDIUM-HARNESS — MEDIA-PER-MEDIUM-HARNESS

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000184 RDE-000185 RDE-000186 RDE-000187 RDE-000188 RDE-000201
- **主体**: PO／媒体運用者／製品runtime
- **受益者**: 媒体別に承認・障害影響を分離して監督したいPO／媒体運用者
- **価値**: 媒体ごとに1つの独立ハーネスへ分離し、承認境界・write境界・障害影響・route policyを媒体単位で独立に凍結・運用できる
- **task**: 対象媒体一覧を確定する／媒体別ハーネスの承認境界・write境界を定義する／共通基盤とハーネス分離の境界線を確定する／既存の共通ハーネス前提候補を媒体別refinementへ再割当する
- **workflow**: candidate→媒体一覧のPO確定→媒体別refinement降下→媒体別PO凍結→媒体別release受入
- **対象範囲**: 媒体単位のハーネス分離構成／媒体別の承認境界・write境界・route policy束縛／媒体別の障害影響分離／将来の媒体別独立リポジトリ分離前提の自己完結設計／PO改訂済み11媒体（WordPress・Discord community・LINE・アフィリエイト・X・Instagram・YouTube・TikTok・Threads・CRM(HubSpot想定)・Google Tag Manager）の媒体別分離
- **対象外**: 共通基盤の実装方式選択（design-later）／PO approval又は要求freeze／外部リポジトリの実作成（PO明示指示まで行わない）／旧媒体（LINE・生成AI・アフィリエイト・Canva）のdeferred運用の再開（分離は構成単位の分離であり運用再開を意味しない）／生成AI・Canvaの媒体ハーネス（PO改訂で撤回。生成AIはGENAI-EXECUTION-ROUTE、Canvaは制作ツールとして別扱い）
- **禁止事項**: 複数媒体の承認・write境界を単一ハーネスへ暗黙に混載しない／媒体別分離を理由に承認境界・禁止事項・fail-close規律を弱めない／媒体別ハーネス分離を根拠に旧媒体（LINE・生成AI・アフィリエイト・Canva）のdeferred運用を暗黙に再開しない
- **人間判断**: 対象媒体一覧・分離境界・共有基盤範囲・採否・freezeはPOが判断する
- **副作用**: 要求候補とrefinement構成だけ。製品runtime・媒体への外部writeを変更しない
- **証跡**: 媒体一覧のPO確定record／媒体別refinement subjectの降下／媒体別承認境界のtyped contract
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-MEDIA-PER-HARNESS-P: PO確定済み媒体一覧の各媒体が、承認境界・write境界・route policyを自媒体refinementだけへ束縛した独立ハーネスを1つ持つ （RST-MEDIA-PER-HARNESS-P）
  - `negative` RAC-MEDIA-PER-HARNESS-N: 複数媒体の承認境界・write境界を単一ハーネスへ混載した構成、及び媒体一覧未確定のままのハーネス凍結を拒否する。媒体別ハーネス分離を根拠とした旧媒体（LINE・生成AI・アフィリエイト・Canva）のdeferred運用の暗黙再開も拒否する （RST-MEDIA-PER-HARNESS-N）
  - `boundary` RAC-MEDIA-PER-HARNESS-B: 単一媒体ハーネスの失敗・停止時も他媒体ハーネスの承認・運用状態を変更せずfail-closeで維持する （RST-MEDIA-PER-HARNESS-B）
- **PO個別質問**:
  - `RDQ-MEDIA-PER-MEDIUM-HARNESS-01` (`requirements_policy`): 媒体横断で共有する共通基盤（credential store・evidence・kernel）の範囲と、ハーネス分離の境界線はどこか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
  - `RDQ-MEDIA-PER-MEDIUM-HARNESS-02` (`requirements_policy`): 既存の共通ハーネス前提の要求候補（route policy・content gate等）を媒体別refinementへどう再割当するか （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:77bbcddf90abf3d1fc4b7a8bbf04eefe6d36a5853edd5e184ad74ebcf2cd02bd`

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
  - `RDQ-MEDIA-POC-SCRUM-RELEASE-01` (`safety_policy`): PoC evidenceから本番write capabilityへ昇格するbusiness value、許容risk、release admission及びrollback outcomeをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:4cb3997604201fdd2f1cd7dd2f8eb48f1faa9c7d407f3112ca10ae0821540c6f`

## RRF-NFR-BUSINESS-AUTHORITY — NFR-BUSINESS-AUTHORITY

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000105 RDE-000106 RDE-000183
- **主体**: PO／品質責任者／運用者
- **受益者**: 法規・可用性・安全性を満たす利用者と運用者
- **価値**: NFRをstable business rootと測定・failure/recoveryへ接続する
- **task**: 既存NFR11意味inventoryを親digestとして再利用しstable root・actor/principal scope・applicability scope・phaseだけを分類する／NFRごとのretain/replace/defer/obsolete、owner及びresume conditionをPO分類する／measurement authorityと環境別measurement registrationを分離する／failure/recoveryを新AC/TCへ再降下し初期対象外を理由付きdeferredにする
- **workflow**: business risk/value→BR/REQ→NFR→measurement/threshold→failure/recovery→AC/TC
- **対象範囲**: NFR-1〜11／stable BR/REQ／measurement／threshold／failure／recovery／evidence／phase
- **対象外**: 節番号又はrisk IDだけを要求根拠とすること
- **禁止事項**: AC/TC存在だけで品質受入済みとしない／他NFR、旧MR/FR、節番号、risk ID又はdraft STCをstable business rootの代用にしない／旧phase又は未登録の測定閾値をpositive authorityへ暗黙昇格しない／root・actor・scope・phase未分類又は親digest staleのNFRを受入済みにしない
- **人間判断**: 品質閾値・残余risk・deferred範囲はPOが判断
- **副作用**: 現段階は要求再接続のみ
- **証跡**: NFR11 parent meaning digestとtyped authority overlay／BR→REQ→NFR双方向trace及びPO row-set receipt／環境別measurement registration revision/digest／failure/recovery AC/TCとdeferred再開条件
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-NFR-AUTH-P: NFR11全件が既存meaning digestへ束縛されたstable root、actor/principal scope、applicability scope、phase、処遇、measurement authority及びfailure/recoveryを持つ （RST-NFR-AUTH-P）
  - `negative` RAC-NFR-AUTH-N: root不明、親digest stale、意味軸未分類、旧NFR/phase/draft STC流用又は未登録閾値のNFRを受入済みにしない （RST-NFR-AUTH-N）
  - `boundary` RAC-NFR-AUTH-B: N/A又は将来NFRはowner・理由・risk・再開条件付きdeferredとし、部分成立を全体受入へ昇格しない （RST-NFR-AUTH-B）
- **PO個別質問**:
  - `RDQ-NFR-BUSINESS-AUTHORITY-01` (`authority_choice`): NFR-1〜11のstable root・actor・scope・phase・deferred範囲をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:f70dd7d7fcbfc46be0c34ddc379e49703ea765b6cff0e8a8fd6c308db9b52834`

## RRF-OFFICIAL-API-ROUTE-AUTHORITY — OFFICIAL-API-ROUTE-AUTHORITY

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
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
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:a2614cd4a2b2ea8347e9f9f04e8378303628965d9e81909643a0fb9c208b9e7d`

## RRF-PRODUCT-STATE-AUTHORITY — PRODUCT-STATE-AUTHORITY

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000128 RDE-000129 RDE-000172 RDE-000173 RDE-000175
- **主体**: PO／運用者／製品runtime
- **受益者**: 一貫した状態を確認するPOと運用者
- **価値**: UI、worker、通知の状態確定を一つのrevision付き正本へ集約する
- **task**: 状態を読み、対象とrevisionを再検証し、許可更新とreceiptを残す／stable transition IDとexpected prior revisionで状態変更を検証する／通知/seen/ack/adapter/retry signalを非authorityとして分類する／復旧を新しい認可transitionとして記録する／source/target stateと結果revisionをreceiptへ記録し成功又は不変outcomeを検証する／transitionをauthorization grant ID/revision/semantic digestへ束縛する／recovery actor identityとrecovery authorization grant permissionを分離する
- **workflow**: 状態読取→対象/revision再検証→許可更新→receipt→全consumerから再読取
- **対象範囲**: 製品状態／revisionと版一致条件付き更新／owner／更新principal／保持/競合/復旧/監査／typed transition binding／非authority signal分類／append-only transition history／recovery transition receipt／source state/target state/resulting revision／success/rejected/persistence-failure typed outcome
- **対象外**: 具体DB/API設計／UI又は通知のlocal stateを正本とすること
- **禁止事項**: stale write／複数正本／UI/worker/通知による独自確定／通知配送、seen、acknowledged、外部adapter結果又はretry失敗から業務状態を暗黙変更する／通知又はretry失敗で既確定状態をrollbackする／復旧時に履歴又はprior revisionを書き換える／unknown transition、stale revision、競合又はunknown ownerで推測更新する／成功transitionでresulting revisionを進めない／拒否又は永続化失敗時にcurrent state又はrevisionを変更する／PRODUCT-STATE内でprincipal permissionを二重正本化する／recovery actor identityだけをpermission根拠にする
- **人間判断**: 状態分類、保持、競合解決、復旧riskはPO
- **副作用**: 現段階は要求候補のみ
- **証跡**: state authority map／stale revision negative case／recovery/receipt／PO receipt／transition ID/subject/prior revision/owner/authorization grant ID/revision/semantic digest/effect/result receipt／signal non-authority negative test／conflict/stale/unknown owner rejection receipt／recovery transition and immutable history evidence／source/target state and resulting revision receipt／success revision progression and failure invariance mutation／authorization grant ID/revision/semantic digest in transition receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-PRODUCT-STATE-P: stable transition ID、subject、source state、target state、expected prior revision、expected priorより大きいresulting revision、単一owner、有効なauthorization grant ID/revision/semantic digest、effect、result及びreceiptが閉じた更新だけを唯一正本へ反映する （RST-PRODUCT-STATE-P）
  - `negative` RAC-PRODUCT-STATE-N: unknown transition、stale revision、競合、unknown owner、missing/stale/expired authorization grant及び通知/seen/ack/adapter/retry signalからの暗黙更新又はrollbackを拒否する （RST-PRODUCT-STATE-N）
  - `boundary` RAC-PRODUCT-STATE-B: 拒否、競合、保存不能又は復旧時はcurrent state、current revision及び履歴を維持し、復旧を新しい認可transitionとして記録するまでfail-closeする （RST-PRODUCT-STATE-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:634bd6202e1a5d464d9696ce4f698cc5d5eb40907eea96e198cc5d885e2b9878`

## RRF-RATE-QUOTA-COST-AUTHORITY — RATE-QUOTA-COST-AUTHORITY

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000134 RDE-000135 RDE-000171
- **主体**: PO／account所有者／connector管理者
- **受益者**: 費用とaccount安全性を管理するPO
- **価値**: rate、quota、read cap、cost、retryを別型で管理しcap回避と予期せぬ課金を防ぐ
- **task**: 制限sourceを取得しscope/window/valueを評価して実行又は拒否する／effect別に未知limit時の開始可否を判定する／具体値をprofile/account/operation/risk別registration revisionへ束縛する
- **workflow**: 制限取得→分類→予算/上限評価→実行又は拒否→receipt→再評価
- **対象範囲**: provider quota／account cap／read safety cap／cost ceiling／retry/backoff/retry-after／external write/publish/money/additional retryの開始拒否／read-only残量取得の別effect分類／configuration/limit failure receipt
- **対象外**: ブラウザ人間様待機をAPI quotaとみなすこと
- **禁止事項**: 複数accountによるcap回避／retry-after無視／費用上限なし有償経路／未知・未登録・失効又は測定不能なlimitで外部作用を開始する／limit失敗を理由に既確定blocked/failed/safety-stopped状態をrollbackする／別profile/account/operationのlimit値を流用する
- **人間判断**: cost ceiling、有償例外、未知値の再開はPO
- **副作用**: 現段階は要求候補のみ
- **証跡**: typed limit registry／source/window/scope／boundary tests／PO receipt／limit registration revision／effect classification／configuration/limit failure receipt／unknown/expired/scope mismatch mutation
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-RATE-QUOTA-P: 有効なprofile/account/operation/risk別registrationとeffect分類があり、上限内のoperationだけを開始する。read-only残量取得は権限・quota・証跡が閉じる場合だけ別effectとして扱う （RST-RATE-QUOTA-P）
  - `negative` RAC-RATE-QUOTA-N: 未知、未登録、失効、測定不能、scope不一致、retry-after違反又はcost ceiling欠落時にexternal write/publish/money/additional retryを拒否する （RST-RATE-QUOTA-N）
  - `boundary` RAC-RATE-QUOTA-B: 上限到達又は分類不明では対象effectだけをblocked/deferredとし、既確定状態をrollbackせずfailure receiptを残す （RST-RATE-QUOTA-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:4d1941c135f4100df4286135bf534b7058473abaef0396495778df0fcccdcf41`

## RRF-REQ-AUTHORITY-NORMALIZATION — REQ-AUTHORITY-NORMALIZATION

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000097 RDE-000098 RDE-000124 RDE-000127 RDE-000182
- **主体**: PO／要求分析者／要件エンジン
- **受益者**: 一意な要求根拠を使う設計者と実装者
- **価値**: REQ本文・出典・下流・充填を一つのJSON正本へ凍結しBRから下流への意味根拠を一意にする
- **task**: 既存REQ55意味inventoryを再利用し、ledgerとMarkdownの15 ID・19 field差分だけをsource value digest付きdelta overlayへ固定する／各差分をretain/replace/defer/obsoleteとしてPO分類し、単一candidate JSONを凍結する／Markdownをcandidate JSONから決定的に生成するviewへ限定する／traceを再生成し差分0、manifest/baseline同一commit及び独立Goを検証する
- **workflow**: 両source snapshot→19 field delta exact partition→PO意味選択→単一candidate JSON→Markdown生成→trace再生成→manifest/baseline束縛→独立Go
- **対象範囲**: REQ本文／source／downstream trace／fill route／JSON/Markdown authority
- **対象外**: 旧Markdownの手編集／FR/NFRの自動採用／製品runtime変更
- **禁止事項**: 同一ID又は件数だけで意味同値としない／JSONとMarkdownを並行正本にしない／未分類、source stale、複数candidate、defer owner/resume欠落又はtrace差分残存でcutoverしない／旧REQ資料又は未批准candidateを実装入力にしない
- **人間判断**: 正規意味とauthority cutoverはPOが決定
- **副作用**: 要求authorityの変更だけ。現段階でruntime変更なし
- **証跡**: 既存REQ55 subset ID/meaning digestと両source artifact/content digest／15 ID・19 field delta overlay及びPO row-set receipt／単一candidate JSON、生成Markdown及びtrace digest／trace差分0、旧consumer隔離、manifest/baseline同一commit及び独立Go receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-REQ-AUTH-P: 既存REQ55意味inventoryと15 ID・19 field delta overlayをPO row-set receiptへ束縛し、単一candidate JSONからMarkdownとtraceを生成して差分0、旧consumer隔離、manifest/baseline同一commit及び独立Goを満たす （RST-REQ-AUTH-P）
  - `negative` RAC-REQ-AUTH-N: 未分類又は重複差分、source digest stale、複数selected candidate、defer owner/resume欠落、独立手編集view、旧REQ再混入、trace差分又はPO row-set digest不一致を拒否する （RST-REQ-AUTH-N）
  - `boundary` RAC-REQ-AUTH-B: 表記同値は正規化するが本文・source・downstreamの実質差を消さず、全条件成立前は旧資料とcandidateの双方をrevalidation-onlyに保つ （RST-REQ-AUTH-B）
- **PO個別質問**:
  - `RDQ-REQ-AUTHORITY-NORMALIZATION-01` (`authority_choice`): REQの本文・出典・下流・充填を正規化し、唯一のJSON正本と生成Markdown境界をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:3b83b3e1af295d0e0152cce199a294f6591dccc61ac33067926b64aa3ea5ee80`

## RRF-REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE — REQUIREMENT-DISCOVERY-SEMANTIC-COVERAGE

- **状態**: `superseded` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `historical_superseded` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000009 RDE-000014 RDE-000028 RDE-000029 RDE-000047 RDE-000048 RDE-000072
- **主体**: PO／要求分析者／要件エンジン
- **受益者**: 意味欠落のない要求を承認するPOと実装者
- **価値**: 候補から仕様化までのunknownと意味軸を機械追跡し、要約又は同一IDの二重意味による承認を防ぐ
- **task**: candidateを記録する／unknownへquestionを束縛する／12意味軸と品質観点を閉じる／同一IDの本文・出典・trace・充填を一意化する／反例/境界を定義する／各意味軸をdirect/digest_inherited/not_applicable/deferredへexactly onceで分類する／品質閾値をsubject/risk/scope/revision付きregistrationへ分離する
- **workflow**: candidate→question/observation/prototype→refinement→正本選択/生成view化→admission→PO decision→freeze
- **対象範囲**: actor/value/workflow/scope/prohibition/HJ/side-effect/evidence/phase／security/privacy/accessibility/performance/availability/recovery/operation/migration/rollback／REQ JSON/Markdown authorityとsemantic drift
- **対象外**: AI回答だけによるPO決定／一括承認／正本の自動mutation／意味未確認の文字列同期
- **禁止事項**: 未回答unknownをspecifiedにしない／positive caseだけで承認しない／同一ID・件数一致だけで意味同値とみなさない／JSONとMarkdownを独立正本として並立させない／core意味軸へnot_applicableを使う／空、unknown又は汎用的な該当なしをspecified又はfreezeへ昇格する／親semantic digest不一致又は循環を継承として認める／必要な品質閾値registrationが未登録、失効又は測定不能のまま承認する
- **人間判断**: 価値・範囲・risk・正本意味・採否・freezeはPO
- **副作用**: 要求authority cutoverだけ。製品runtimeを直接変更しない
- **証跡**: event prefix／source-set digest／semantic digest／REQ field差分0／単一JSON正本からの生成view／三極性AC／PO receipt／ID×dimension exact partition digest／parent/delta digest及びcycle-free evidence／N/A applicability receipt／quality threshold registration revision／unknown/N/A/stale parent/missing threshold mutation results
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-DISCOVERY-P: 全core軸がdirect又はdigest付き継承で閉じ、品質軸が同様に閉じるか証拠付きN/Aとなり、必要な閾値registrationが有効な対象だけを次工程へ進める （RST-DISCOVERY-P）
  - `negative` RAC-DISCOVERY-N: unknown、空、汎用N/A、親digest不一致、継承循環又は必要な閾値registration欠落をfail-closeで拒否する （RST-DISCOVERY-N）
  - `boundary` RAC-DISCOVERY-B: 一部だけ成立する場合は責務を分割又はdeferredとし、品質軸の一括N/Aや全体成立へ昇格しない （RST-DISCOVERY-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:ae73eac1dcff87687fb07345f4b59a072a33259bf7da9039fefe39e24378647f`

## RRF-REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2 — REQUIREMENT-SEMANTIC-COVERAGE-POLICY-V2

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `requirements_governance` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000169
- **主体**: PO／要求分析者／要件エンジン
- **受益者**: 意味欠落のない要求を承認するPOと実装者
- **価値**: 候補から仕様化までのunknownと意味軸を機械追跡し、要約又は同一IDの二重意味による承認を防ぐ
- **task**: candidateを記録する／unknownへquestionを束縛する／12意味軸と品質観点を閉じる／同一IDの本文・出典・trace・充填を一意化する／反例/境界を定義する／各意味軸をdirect/digest_inherited/not_applicable/deferredへexactly onceで分類する／品質閾値をsubject/risk/scope/revision付きregistrationへ分離する
- **workflow**: candidate→question/observation/prototype→refinement→正本選択/生成view化→admission→PO decision→freeze
- **対象範囲**: actor/value/workflow/scope/prohibition/HJ/side-effect/evidence/phase／security/privacy/accessibility/performance/availability/recovery/operation/migration/rollback／REQ JSON/Markdown authorityとsemantic drift
- **対象外**: AI回答だけによるPO決定／一括承認／正本の自動mutation／意味未確認の文字列同期
- **禁止事項**: 未回答unknownをspecifiedにしない／positive caseだけで承認しない／同一ID・件数一致だけで意味同値とみなさない／JSONとMarkdownを独立正本として並立させない／core意味軸へnot_applicableを使う／空、unknown又は汎用的な該当なしをspecified又はfreezeへ昇格する／親semantic digest不一致又は循環を継承として認める／必要な品質閾値registrationが未登録、失効又は測定不能のまま承認する
- **人間判断**: 価値・範囲・risk・正本意味・採否・freezeはPO
- **副作用**: 要求authority cutoverだけ。製品runtimeを直接変更しない
- **証跡**: event prefix／source-set digest／semantic digest／REQ field差分0／単一JSON正本からの生成view／三極性AC／PO receipt／ID×dimension exact partition digest／parent/delta digest及びcycle-free evidence／N/A applicability receipt／quality threshold registration revision／unknown/N/A/stale parent/missing threshold mutation results
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-DISCOVERY-P: 全core軸がdirect又はdigest付き継承で閉じ、品質軸が同様に閉じるか証拠付きN/Aとなり、必要な閾値registrationが有効な対象だけを次工程へ進める （RST-DISCOVERY-P）
  - `negative` RAC-DISCOVERY-N: unknown、空、汎用N/A、親digest不一致、継承循環又は必要な閾値registration欠落をfail-closeで拒否する （RST-DISCOVERY-N）
  - `boundary` RAC-DISCOVERY-B: 一部だけ成立する場合は責務を分割又はdeferredとし、品質軸の一括N/Aや全体成立へ昇格しない （RST-DISCOVERY-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:68ce8384a857fac070f2394e20e6188358cae6fae262ea6f2c18b5f03a9ed403`

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
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000107 RDE-000108 RDE-000161
- **主体**: PO／戦略責任者／検証責任者
- **受益者**: 戦略判断の根拠を追跡するPO
- **価値**: 旧SR-01〜16の戦略価値をresearch-led growthへ再接続し、高度分析SR-17〜19をdeferredに分離した上で要求admissionとtest authorityを一意にする
- **task**: SR価値とphaseを再確認する／初期/deferredを分ける／SR→AC→STCを束縛する／test ledger authorityを一つにする
- **workflow**: 戦略価値確認→phase/admission→SR→AC→STC→S4判断
- **対象範囲**: SR-01〜16のcore model、loop governance及び初期scope責務の再降下／research evidence、商品/offer authority、marketing funnel、媒体役割、仮説及びKPI還流との接続／企画内容、改訂及び有効化の人間判断receipt／SR-17〜19／AC-SR／TCC/STC authority／FN/CMP descent／deferred resume
- **対象外**: draft testをconfirmed oracleとすること
- **禁止事項**: 要求記述だけを検証完了としない／TCC/STCを暗黙併用しない
- **人間判断**: 戦略capabilityの価値・phase・admission、企画内容、改訂、有効化及び高度分析の再開はPOが判断
- **副作用**: 現段階は要求とtest authorityの候補化のみ
- **証跡**: SR→AC→STC双方向trace／test ledger digest／deferred再開条件／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-STRATEGY-ADMISSION-P: 採用SRがFN/CMP/ACとPO receipt付きの単一current test authorityへ降下し、旧draft STC又は旧TCCを自動流用しない （RST-STRATEGY-ADMISSION-P）
  - `negative` RAC-STRATEGY-ADMISSION-N: draft STC又はACなしSRをimplementation-readyにしない （RST-STRATEGY-ADMISSION-N）
  - `boundary` RAC-STRATEGY-ADMISSION-B: 初期外SRは価値・依存・risk・再開条件付きdeferredとする （RST-STRATEGY-ADMISSION-B）
- **PO個別質問**:
  - `RDQ-STRATEGY-REQUIREMENT-ADMISSION-01` (`release_scope`): SR-01〜16をresearch/funnel/media roleへ再降下する範囲と企画・改訂・有効化の判断receiptをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
  - `RDQ-STRATEGY-REQUIREMENT-ADMISSION-02` (`authority_choice`): SR-17〜19と既存AC-SR/STCのdeferred範囲及び唯一のcurrent test authorityをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:52f381f8b7c12da197f61fe39dd1e79474d5aabc8c97c70a8f97d423d115b2b8`

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

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000109 RDE-000110 RDE-000159 RDE-000162
- **主体**: PO／security運用者／製品runtime
- **受益者**: credential漏洩と越境を防ぐ運用者と外部account所有者
- **価値**: 具体backendを先取りせずVPS credentialの保存・解除・注入・rotationを安全に閉じる
- **task**: 暗号化at-rest境界を検証する／unlockとscope付きruntime注入を検証する／rotation/recoveryと旧平文credential再発行を検証する／test/prod分離、間接参照及びredactionを検証する
- **workflow**: credential登録→暗号化at-rest保護→実行系初期化時のunlock再認可→profile/account/operation束縛runtime注入→使用→破棄→rotation/recovery → VPS再起動→エージェント実行系停止→外部操作停止維持→人間による実行系再初期化→credential unlock/runtime注入再認可
- **対象範囲**: at-rest protection／unlock／runtime injection／rotation／backup/recovery／test/prod scope／redaction／credential参照ID
- **対象外**: 具体secret backend製品／unlockとruntime注入の具体mechanism／平文envを暗号化storeと同一視すること
- **禁止事項**: 0600だけをat-rest保護の十分条件にしない／secret値をrepo/製品DB/log/journal/service unit/argv/dump/evidenceへ記録しない／credentialを製品状態backupへ含めない／test credentialをproductionへ注入しない／旧平文credentialをrotateせず新storeへ移送しない／現行runtime lifecycleでの無人unlock又は自動復旧／資格情報だけを復旧して停止中のエージェントが継続すると仮定すること
- **人間判断**: VPS再起動後の実行系再初期化とcredential unlock/runtime注入は人間が再認可する／将来の常駐service、自動再起動及び無人unlockは別要求としてPO/security運用者が判断する
- **副作用**: 現段階は要求候補のみ。credential移動やrotationを行わない
- **証跡**: threat model／credential参照IDだけを持つoperation/evidence receipt／profile/account/operation scope negative test／test/prod tag mismatch negative test／positive/negative/boundary AC／leakage test／旧credential rotation receipt／rotation/recovery receipt／PO receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-CREDENTIAL-P: 暗号化at-rest保護とprofile/account/operation束縛一時注入を満たし、証跡は参照IDだけを保持して使用後にsecretを残さない （RST-VPS-CREDENTIAL-P）
  - `negative` RAC-VPS-CREDENTIAL-N: 平文env、repo/製品DB/log/journal/service unit/argv/dump/evidence漏洩、scope越境、test/prod混用及びsecret backupを拒否する （RST-VPS-CREDENTIAL-N）
  - `boundary` RAC-VPS-CREDENTIAL-B: VPS再起動又はunlock失敗時は外部操作停止を維持し、人間が実行系とcredential注入を再認可するまで自動復旧せず、旧平文credentialも再発行前に移送しない （RST-VPS-CREDENTIAL-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:16f222c23f0071263f5b28fc09a62e23c50719dbff0f9c4747d8de00bcb014df`

## RRF-VPS-UI-AUTHENTICATION-SESSION — VPS-UI-AUTHENTICATION-SESSION

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000132 RDE-000133 RDE-000176 RDE-000177
- **主体**: PO／許可運用者／security責任者
- **受益者**: 不正操作を防ぐPOと運用者
- **価値**: 高リスク判断を本人性とfresh sessionへ束縛する
- **task**: identity/session revision、authentication event、strength、expiry、revocation及びreauth freshnessを検証する／operationごとにauthorization grant ID/revision/digestを別検証する／VPS再起動後のruntime/credential/grant再認可を検証する
- **workflow**: identity登録→authentication event→session発行→session/CSRF/strength/freshness検証→authorization grant検証→operation又はdeny→失効/recovery監査
- **対象範囲**: identity lifecycle／session／CSRF／再認証／recovery／lockout／audit/emergency access／session binding and identity revision／authentication strength and reauth freshness／authorization grant reference／VPS restart credential/grant boundary／有人再認可後のbounded process-memory credential injection候補／non-secret session identifier又はone-way digest候補／secret-free authentication event canonical projection
- **対象外**: IdP/protocol/proxy/framework選定／専用secret authority方式の先決め
- **禁止事項**: 通知deep-linkを認証とみなさない／共有account／失効session利用／authentication又はsession成立からauthorizationを推論する／deep-linkをauthenticationとみなす／session fixation又はreplay／VPS再起動後に既存Web sessionからcredential又はgrant authorityを復元する／recovery又はbreak-glassでauthorization grantを迂回する／raw secret、raw bearer token又はcredential materialをrepo、製品DB、log又はinboxへ永続化又は露出する／authentication event digestへsecret又はcredential materialを混入する
- **人間判断**: principal登録、recovery、emergency access、残余riskはPO/security authority
- **副作用**: 現段階は要求候補のみ
- **証跡**: identity/session lifecycle／negative auth cases／recovery/audit receipt／PO receipt／session/identity/authentication event revision receipt／expired/revoked/stale/CSRF/strength/freshness negative tests／authorization grant separation receipt／post-reboot credential/grant reauthorization evidence／secret storage negative test／raw secret/bearer/credential material storage negative tests／secret-free authentication event digest projection／bounded process-memory injection receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-UI-AUTH-P: 有効なidentity revision、authentication event/digest、session expiry/revocation、必要strength/freshness及びoperation別authorization grant ID/revision/digestを満たすprincipalだけ操作できる （RST-UI-AUTH-P）
  - `negative` RAC-UI-AUTH-N: unknown/stale identity、expired/revoked/fixed/replayed session、CSRF不成立、strength/freshness不足、deep-linkのみ、grant欠落、raw secret/raw bearer token/credential materialのrepo・製品DB・log・inboxへの永続化又は露出、及びcredentialを含むauthentication event digestを拒否する （RST-UI-AUTH-N）
  - `boundary` RAC-UI-AUTH-B: lockout/recovery/break-glass又はVPS再起動時もstate/revisionを維持し、runtime/credential再認可とfresh grantまで外部作用を停止する （RST-UI-AUTH-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:59583ac23bfdef85aafee36c120abced6cf938c25b6c905bf7bf364890468d04`

## RRF-VPS-UI-INBOX-LIFECYCLE — VPS-UI-INBOX-LIFECYCLE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000100 RDE-000101 RDE-000102 RDE-000119 RDE-000165 RDE-000166 RDE-000167 RDE-000168
- **主体**: PO／許可された運用者／製品runtime
- **受益者**: 異常と承認待ちを安全に監督するPO
- **価値**: 通知lifecycleと業務状態を分離して通知失敗や重複による誤決定を防ぐ
- **task**: 初期source eventをinboxへ記録する／利用者ごとのseen/acknowledgedを管理する／source状態に追随してresolved/expiredを管理する／重複を一itemへ収束する／記録失敗を業務状態と独立にretryする／content quality retry exhaustionを一意なoperational alertとして記録する／source lifecycle、revision失効又はscope取消の正本eventだけからresolved/expiredを導出する／purpose/risk class/profile別の有効なretry budget registrationを検証する／retry上限到達時にretry_exhausted/failed receiptを残して通知処理だけを停止する／source terminal後にretention/legal hold/data classification policyへ従ってarchive/redact/purgeする／明示registrationがある場合だけactive未確認itemへ同一item内reminder又はurgency変更を行う
- **workflow**: source event→業務状態を先に確定→inbox記録attempt→recorded/failed/retry_exhausted receipt→利用者seen/acknowledged→source状態に追随したresolved/expired→source terminal後のみretention policyに従うarchive/redact/purge。reminder policyは既定disabled
- **対象範囲**: VPS UI内inbox／purpose=action_required又はoperational_alert／source=approval_waiting/safety_stopped/execution_failed／recorded/failed/retry_exhausted evidence／per-principal seen/acknowledged／source-linked resolved/expired／profile/resource/operation別list/read/seen/acknowledge認可／secret/credential/PII/raw errorの最小開示／deduplication／retry／retention／source=content_quality_retry_exhausted（通常retryを除外）／artifact/rule revision/retry exhaustion source identityによる一件dedupe／旧FR-43 repair failureを再降下したexecution_failed（旧ApprovalTransportを除外）／source-derived resolved/expired（inbox独自expiryなし）／有界inbox記録retry／terminal後retention/legal hold/data classification／同一item内reminder/urgency（明示登録時のみ）／secret/PIIを含まない最小tombstoneとpurge receipt
- **対象外**: 外部adapter配送結果／Discord／Web Push／community media post／developer PR notice／具体DB/API/UI設計／通知操作による業務decision／inbox独自時刻によるaction_required expiry／inbox失敗時の外部通知fallback／active source itemのarchive/purge／既定有効のreminder/escalation
- **禁止事項**: 承認待ちと運用alertを同じpurposeにしない／seen/acknowledgedをapprove/reject又は再開とみなさない／通知記録失敗又はretry_exhaustedで先行する安全停止・失敗・承認待ち状態をrollbackしない／inbox記録と外部配送を同じ結果軸にしない／同一source eventから複数の現役itemを作らない／認証済みであることだけで全profileのinboxを閲覧又は更新させない／secret、credential、個人情報又は不要なraw error payloadをinboxへ表示しない／未決の時間・回数を設計者が補完しない／通常のcontent quality retryをinbox itemにする／旧FR-43又はApprovalTransportを新inbox source authorityとして直接採用する／未確認、時間経過、stale表示又は記録失敗だけでaction_requiredをexpiredにする／reminder又はescalation表示からapprove/reject、停止解除又はsource expiryを導出する／無限retry／retry budget未登録・失効・不正時の自動運用開始又は追加retry／retry exhaustionから外部通知transportへfallbackする／active source itemを未確認期間だけでarchive又はpurgeする／retention policy不明又はlegal hold中の不可逆purge／reminder/escalationで別itemを量産する
- **人間判断**: approve/reject、停止後再開、中止はinbox lifecycleと別の許可principal判断／retention、availability及びreminderの方針採用は要求authorityがratifyする。実値はprofile/purpose/risk class別registration revisionへ束縛し、未登録時は安全側停止とする
- **副作用**: 現段階は要求候補の記録のみ。将来はinbox itemと利用者別確認状態を記録する／terminal itemのarchive/redact/purge候補／明示登録時の同一item内reminder又はurgency変更
- **証跡**: source event identityと対象profile/resource/revision/purpose／recorded/failed/retry/retry_exhausted receipt／per-principal seen/acknowledged receipt／profile/resource/operation scopeに対するlist/read/seen/acknowledge認可receipt／cross-profile拒否及びsecret/PII最小開示negative test／source-linked resolved/expired receipt／dedupe negative test／業務状態不変negative test／PO receipt／content quality blocked source identity、artifact、rule revision及びretry exhaustion receipt／FR-43 replacement source identity、phase、risk及びfailure evidence／source lifecycle/revision/scope eventからのresolved/expired derivation receipt／inbox独自時間経過でactive itemが失効しないnegative test／retry budget registration revision、attempt履歴及びconfiguration-fault receipt／terminal source event、retention policy revision、data classification及びlegal-hold判定／archive/redact/purge receiptと非secret最小tombstone／reminder policy revisionと同一item dedupe negative test
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-UI-INBOX-P: approval_waiting/safety_stoppedと外部operation・公開・保守のexecution_failedを先に確定し、purposeと対象bindingを持つ一意なitemをrecordedとして残し、seen/acknowledgedを利用者別に記録する。content_quality_retry_exhaustedは対象artifact、rule revision及びexhaustion source identityへ束縛したoperational alertを一件だけ記録する。resolved/expiredはsource lifecycle、revision失効又はscope取消の正本eventだけへ追随する。登録済み有界retry内で記録し、terminal後だけ登録済みretention policyに従って処理する （RST-UI-INBOX-P）
  - `negative` RAC-UI-INBOX-N: 通知失敗・重複・seen・acknowledged・resolved・expiredから業務状態、approve/reject又は停止後再開を変更せず、scope外profileのitemとsecret/PII/raw errorを表示しない。通常のcontent quality retryを通知せず、retry exhaustion itemの記録失敗でもblocked状態を変更しない。旧FR-43又はApprovalTransportをinbox source authorityとして直接採用しない。未確認、時間経過、stale表示又は記録失敗だけでaction_requiredをexpiredにしない。無限retry、外部通知fallback、active itemの時間archive/purge、policy不明時purge、reminderからのdecision又は別item生成を拒否する （RST-UI-INBOX-N）
  - `boundary` RAC-UI-INBOX-B: 未知source/purpose、同一identity再送、記録失敗、保持境界ではfail-closeし、業務状態を維持したまま一意なattempt/failed/expiry証跡を残す。content quality exhaustionの再送は同一source identityへdedupeし、別itemを作らない。長期未確認表示又はreminder候補からapprove/reject、停止解除又はsource expiryを導出しない。retry exhaustionではblockedを維持してfailed receiptを残し、retention不明又はlegal hold中はaccess制限して不可逆削除を停止し、reminder未登録時は無表示のままsource状態を維持する （RST-UI-INBOX-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:8e7014577d4ad96f3ded703a42f97f618cf2b56f3c89866d948fa7b9d1ed1fad`

## RRF-VPS-UI-PRIMARY-HUMAN-INTERFACE — VPS-UI-PRIMARY-HUMAN-INTERFACE

- **状態**: `specified` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000007 RDE-000010 RDE-000011 RDE-000012 RDE-000013 RDE-000030 RDE-000031 RDE-000032 RDE-000035
- **主体**: PO／許可された運用者／製品runtime
- **受益者**: 無人処理を監督するPO
- **価値**: チャット製品に依存せずVPS上で状態・承認・通知を一体監督できる
- **task**: 状態・失敗・KPI・承認待ちを確認する／初回activation・scope拡張・高リスク例外・停止後再開を明示決定する／structured feedbackと適用scopeを入力する／blocked成果物と検査・分類証跡を診断閲覧する／activationを取消す
- **workflow**: 認証→対象表示→通知/承認待ち確認→直前認可→明示操作→証跡保存
- **対象範囲**: VPS製品Web UI／UI内inbox／状態/証跡閲覧／blocked成果物と検査・分類証跡の診断閲覧／structured feedback入力とscope指定／activation取消／初回自動運用activationと例外判断
- **対象外**: 認証protocol/IdP選定／session timeout数値／reverse proxy製品／公開URL／UI framework選定／Web Push／Discord補助／開発PR通知
- **禁止事項**: 通知受信だけで意思決定を成立させない／要求正本をUIから更新しない／VPS-UI-AUTHENTICATION-SESSION、VPS-UI-INBOX-LIFECYCLE、VPS-UI-QUALITY-ATTRIBUTES又はPRODUCT-STATE-AUTHORITYが未凍結のまま主入口を完了扱いしない
- **人間判断**: 初回activation・scope拡張・課金・危険設定・重大rule変更・再開は許可principalが判断し、activation後の個別投稿は品質gate合格時に毎回承認を要求しない
- **副作用**: 認可済みUI操作による製品状態変更
- **証跡**: principal・対象・revision・binding・decision・状態遷移receipt／authentication/session、inbox、quality及びproduct-state各subjectのfrozen receipt
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-UI-P: 認証済みprincipalが対象revisionを再表示して明示操作した場合だけ状態を更新する （RST-VPS-UI-P）
  - `negative` RAC-VPS-UI-N: 未認証・CSRF不成立・stale binding・通知deep-linkだけの操作を拒否する （RST-VPS-UI-N）
  - `boundary` RAC-VPS-UI-B: session失効・同時更新・高リスク再認証要求時はfail-closeし既存状態を維持する （RST-VPS-UI-B）
- **PO個別質問**: なし（ただしsubject approval receiptとfreezeは別）
- **semantic digest**: `sha256:229880f28abe6afce7c9576079bf3844130c3f47aa8d60a42e8079439e12478f`

## RRF-VPS-UI-QUALITY-ATTRIBUTES — VPS-UI-QUALITY-ATTRIBUTES

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000094 RDE-000096 RDE-000178
- **主体**: PO／運用者／UI利用者
- **受益者**: 安定して監督できるPOと運用者
- **価値**: 設計製品を先取りせずVPS UIの品質と復旧可能性を反証可能にする
- **task**: 各品質属性をscope、journey又はoperation、metric、unit、測定環境/window、applicability、threshold registration、evidence、failure outcome及びresume conditionへ束縛する／未知・未測定・未登録又は失効閾値をdeferredとしてfail-closeする／故障と復旧を検証し、部分passを全体passへ昇格しない／migration/rollback対象の有無と受入判断を分離する
- **workflow**: 属性適用分類→閾値registration検証→測定→故障/復旧検証→属性別判定→全体受入判断
- **対象範囲**: accessibility／performance／availability／recovery／operation／migration／rollback
- **対象外**: protocol/IdP/proxy/UI framework選定／製品状態のbackup/restore/reconciliation（NFR-10及びPRODUCT-STATE-AUTHORITY所掌）／worker又は外部connector側のavailability/recovery
- **禁止事項**: 具体製品を要求で先取りしない／閾値なしで利用可能としない／generic N/Aを使用しない／部分passを全体pass又はrelease許可へ読み替えない／製品状態backup/restore又はworker/connector品質をUI品質証拠へ流用しない
- **人間判断**: 品質閾値と残余riskをPOが判断
- **副作用**: 現段階なし
- **証跡**: 測定定義／故障/復旧結果／migration/rollback receipt／属性別applicability partitionとthreshold registration revision/digest／failure outcomeとresume condition
- **phase**: `requirements`
- **受入候補**:
  - `positive` RAC-VPS-UI-QUALITY-P: 適用対象の全品質属性がscope、metric、unit、測定環境/window、有効なthreshold registration revision/digest、証跡、failure outcome及びresume conditionを持ち属性別受入条件を満たす （RST-VPS-UI-QUALITY-P）
  - `negative` RAC-VPS-UI-QUALITY-N: generic N/A、未知・未測定・未登録又は失効閾値、測定環境又は証拠欠落、対象変更があるmigration/rollbackの未検証を利用可能又はrelease可能として拒否する （RST-VPS-UI-QUALITY-N）
  - `boundary` RAC-VPS-UI-QUALITY-B: 一部品質だけ成立する場合はdeferredを維持し全体受入へ読み替えず、UI品質を製品状態backup/restore又はworker/connector品質へ拡張しない （RST-VPS-UI-QUALITY-B）
- **PO個別質問**:
  - `RDQ-VPS-UI-QUALITY-ATTRIBUTES-01` (`quality_target`): 各品質属性の測定対象・閾値・N/A条件をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:a01e41d02b365a1eccb468d3bfbff53f3339b83904551addb102e0232ff63b28`

## RRF-WORDPRESS-CONTENT-OPERATIONS-RELEASE — WORDPRESS-CONTENT-OPERATIONS-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `initial_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000113 RDE-000114 RDE-000160 RDE-000179
- **主体**: PO／コンテンツ運用者／製品runtime
- **受益者**: 公開コンテンツ利用者／日常運用を行うPO
- **価値**: WordPressをcontent databaseとして日常公開運用し基盤保守riskから分離する
- **task**: create draft、update draft、publish、update published in place、unpublish、delete及びrollbackを別operation/effectとして扱う／各attemptをtarget identity/revision、desired digest、capability/route、grant ID/revision/semantic digest、activation scope ID/revision/semantic digest、gate/idempotency及びresult receiptへ束縛する／API/MCPを優先しPlaywright確認をwrite authorityへ読み替えない／in-place非対応時は状態不変のunsupported non-action receiptを残し通知しない
- **workflow**: 対象取得→draft/preview→activation scopeと対象/revision再検証→quality/risk gate→scope内合格時は毎回承認なしで公開/更新→receipt。未activation、scope拡張又はattended-onlyは明示判断へ分岐
- **対象範囲**: content operation閉集合／stable ID/revision／公開証跡
- **対象外**: core/plugin変更／security変更／AGENT NEO改修
- **禁止事項**: content_publishでmaintenance/security変更を許可しない／PoC又は旧Docker WP成功を本番受入に流用しない／update/publish/unpublish/delete/rollbackを相互に含意しない／in-place非対応時に別記事作成、再公開又は通知へ置換しない／Playwright確認成功をwrite authorityとみなさない
- **人間判断**: 初回activation、scope拡張、attended-only operation及び未決の削除/非公開化/競合解決は許可principal。activation scope内のgate合格済み通常公開は毎回判断しない
- **副作用**: WordPress content/media/page状態変更
- **証跡**: preview diff／principal/decision／publication/update receipt／S4 receipt／capability、grant及びactivation scopeのID/revision/semantic digestとgate receipts／unsupported non-action又はoperation別result receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=1 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=なし ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-CONTENT-P: stable content ID、remote revision、desired digest、capability、API/MCP優先route、grant ID/revision/semantic digest、activation scope ID/revision/semantic digest、content/risk/quality gate及びidempotencyを再検証し、scope内合格済みoperationだけ実行してreceiptを残す （RST-WP-CONTENT-P）
  - `negative` RAC-WP-CONTENT-N: content policyによるcore/plugin/security変更、stale revision、grant又はactivation scopeの欠落/stale/digest不一致/identity不一致、gate/capability欠落、scope mismatch、unsupported operation及びrollback evidence欠落を拒否して既公開状態を維持する （RST-WP-CONTENT-N）
  - `boundary` RAC-WP-CONTENT-B: in-place非対応の既公開物は別operationへ置換せずstate不変のunsupported non-action receiptを残して通知せず、削除/非公開化/競合/保持が未決ならそのoperationだけdeferredにする （RST-WP-CONTENT-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-CONTENT-OPERATIONS-RELEASE-01` (`release_scope`): 削除/非公開化の許可、履歴保持、content release admission及びrollback outcomeをPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:ec927831a0dcf8ccdb6df150815fbad24fa40f6623c8340e60671ecb8efc33ae`

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
- **source events**: RDE-000115 RDE-000116 RDE-000181
- **主体**: PO／WordPress保守担当／製品runtime
- **受益者**: 安定稼働するWordPressを必要とする運用者と利用者
- **価値**: core/plugin変更と起因障害を日常content operationから分離してrollback可能にする
- **task**: inventory確認、backup作成、restore検証、非security core更新、plugin導入/状態変更/非security更新、schema/config変更及びrollbackを別operation/effectとして扱う／read-only確認とmutationを分け、mutationだけをplatform grant、window、backup/restore、compatibility/smoke/regression及びrollback evidenceへ束縛する／security relevanceをmaintenance_only/security_intersection/unknownへ分類しunknownをdeferredにする／API/MCPを優先しPlaywright確認をwrite authorityへ読み替えない
- **workflow**: 対象取得→read-only inventory分岐はidentity/current revision/inventory/read grant/routeを検証してreceipt→mutation分岐はsecurity relevance分類→backup/restore proof→platform grant/window→変更→検証→続行又はrollback→明示resume
- **対象範囲**: core version update／plugin導入/状態変更/update／随伴schema/config／起因障害復旧
- **対象外**: 日常content操作／security authority判断／AGENT NEO改善改修
- **禁止事項**: content承認をmaintenanceへ流用しない／security grantだけをplatform authorityへ流用しない／復旧proofなしで本番変更しない／security relevance unknown又はintersectionのsecurity decision/grant欠落で実行しない／rollback後に再検証と明示resumeなしで自動再開しない
- **人間判断**: 変更/停止/続行/rollback/残余riskはPOと保守担当
- **副作用**: core/plugin/schema/config変更／rollback
- **証跡**: before/after inventory／backup/restore proof／compatibility/smoke/regression／decision/rollback/S4 receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=2 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=WORDPRESS-CONTENT-OPERATIONS-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-MAINT-P: read-only inventoryは対象identity/current revision/inventory digest/read grant/route/assessment evidenceを満たしてresult receiptを残し、mutationは独立platform grant、activation/window、capability/route、backup freshness/restore、compatibility/smoke/regression、remote revision及びidempotencyを満たしてresult/rollback receiptを残す （RST-WP-MAINT-P）
  - `negative` RAC-WP-MAINT-N: content/security grant流用又はstale remote revisionを拒否し、mutationではbackup/restore/compatibility欠落、security relevance unknown又はrollback不能も拒否してsite stateを維持する （RST-WP-MAINT-N）
  - `boundary` RAC-WP-MAINT-B: security intersectionはplatform grantに加えて別security decision/grantへ束縛し、rollback後は再検証と明示resumeまで通常operationを自動再開しない （RST-WP-MAINT-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-PLATFORM-MAINTENANCE-RELEASE-01` (`safety_policy`): 自動/attended境界、maintenance window、backup freshness及びrollback品質閾値をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:32e41614f15f39347859b6c718d7321644bc5316a5a9daae719e3725adb346c3`

## RRF-WORDPRESS-SECURITY-MAINTENANCE-RELEASE — WORDPRESS-SECURITY-MAINTENANCE-RELEASE

- **状態**: `draft` ／ revision 1 ／ **承認**: 未承認（approval receiptなし）
- **scope候補**: `follow_on_candidate` （PO receiptとFull V再降下までは実装不可）
- **source events**: RDE-000117 RDE-000118 RDE-000180
- **主体**: PO／security責任者／security運用者
- **受益者**: サイト利用者／account所有者／安全な運用を必要とするPO
- **価値**: security判断を日常運用/通常保守から分離し別authorityと証跡で閉じる
- **task**: assess、core/plugin/theme patch、permission change、credential rotation、quarantine及びrestore/rollbackを別operation/effectとして扱う／component/version/inventory/advisory/risk、security grant、maintenance window、preflight、backup/restore evidence、credential authority参照及びresult/rollback receiptを束縛する／content grant、advisory/scanner又はPlaywright確認をsecurity write authorityへ読み替えない／emergency後も再検証まで通常operationを自動再開しない
- **workflow**: 脅威検知→影響評価→隔離/停止判断→変更→検証→復旧判断→監査receipt
- **対象範囲**: vulnerability／security patch／credential/permission／audit／isolation/stop/recovery
- **対象外**: 日常content操作／一般機能update／AGENT NEO機能改善
- **禁止事項**: 通常保守又は公開承認でsecurity判断を代替しない／認証鍵素材をrepo/product DB/log/inbox又はreceiptへ残さない／unknown component/version/sourceを自動patchしない／旧WP PoC成功をsecurity release admissionへ流用しない／emergencyでgrant/scope/期限/receiptを迂回しない
- **人間判断**: 脅威受容/隔離/break-glass/復旧/残余riskはsecurity authorityとPO
- **副作用**: credential/permission/security設定変更／隔離/停止/復旧
- **証跡**: threat/vulnerability／principal/decision／change/rotation／isolation/recovery proof／independent S4 receipt／security grantとmaintenance activation/windowのID/revision/semantic digest／preflight及びbackup/restore evidence revision/digest／operation別result/rollback receipt
- **phase**: `requirements`
- **delivery admission**: standard=`full_v_l1_l12` ／ program-stage=1 ／ sequence=2 ／ increment=production_scrum／v_design_scrum_impl_hybrid ／ Discovery=`only_when_feasibility_or_success_condition_unknown` ／ predecessor=WORDPRESS-CONTENT-OPERATIONS-RELEASE ／ completion=`po_s4_then_scrum_reverse_sr0_sr4_and_v_pair_closure`
- **受入候補**:
  - `positive` RAC-WP-SECURITY-P: 別security authorityがcomponent/version、inventory/advisory digest、risk、security grant、maintenance window、preflight、backup/restore evidence及びcredential authority参照を束縛しoperation別result/rollback receiptを残す （RST-WP-SECURITY-P）
  - `negative` RAC-WP-SECURITY-N: content又は通常保守grant、advisory/scanner/browser確認のauthority化、unknown対象、grant/window/preflight/backup/rollback欠落、認証鍵素材露出及びscope越境を拒否して現site stateを維持する （RST-WP-SECURITY-N）
  - `boundary` RAC-WP-SECURITY-B: 緊急break-glassでも別grant、scope、期限、receipt及び事後再検証を省略せず、通常operationを自動再開しない （RST-WP-SECURITY-B）
- **PO個別質問**:
  - `RDQ-WORDPRESS-SECURITY-MAINTENANCE-RELEASE-01` (`safety_policy`): 対象脅威、patch、credential/権限/監査範囲、緊急principalとbreak-glass条件をPO判断で閉じる （未回答=`defer`。回答はsubject revisionとsemantic digestへ束縛）
- **semantic digest**: `sha256:7664222be30ace640e3a9780c6dc6da1c226dfdb46556f3eba36068537bf20a3`
