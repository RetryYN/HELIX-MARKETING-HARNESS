---
artifact_id: AUTH-ADR-ADR-008-MEDIA-VERTICAL-SLICING
lifecycle_status: draft
slice: cross
---

# ADR-008: スライスを「共通カーネル最小 + 媒体縦切り」に再編する

- status: proposed
- date: 2026-08-12（v0.2 改訂: 2026-08-13 — 媒体順序を文化圏駆動へ更新）
- decision_authority: PO（未承認 — 本 ADR は提案ドラフト）
- 関連: implementation-units.json（S0 実装単位 49）、s0-contract、br-media（媒体別業務要求 70）、
  SR-17〜19（統合因果分析）、ADR-005（WP REST 直）、ADR-006（公式 API 経路）、ADR-007（VPS 無人車線）

## 背景

現行スライスは横切り構成: S0 = 全媒体共通の土台（証跡・状態機械・承認・ブランド隔離基盤・
KPI handoff・外部操作・設定管理 等、実装単位 49 / API 59）を先に完成させ、その後に媒体運用が乗る。

この構成には段階導入上のリスクがある:

1. 土台 49 単位が完成するまで、どの媒体も 1 投稿も実行できない（価値の初回到達が遠い）
2. 全 59 API の契約を机上で固めてから実装するため、契約の欠陥が実運用でなく後工程で露見する
3. 進行が止まった場合に「動く成果物ゼロ」で停止する（サンクコスト化）

## 決定（提案）

スライスを「共通カーネル最小 + 媒体縦切り」に再編する:

| スライス | 内容 | 完了の定義 |
|---|---|---|
| S0-kernel | 証跡書込・状態機械・承認の 3 機能のみ（現 S0 のサブセット） | 3 機能の AC/UT が PASS |
| V1 帯: テキスト文化圏 | V1.0 WordPress を先頭に、企画→生成→ゲート→承認→投稿→KPI 回収→証跡 を 1 媒体ずつ貫通。以降 HubSpot メール／note／X／LINE／Discord／Amazon KDP を帯内で追加 | 媒体ごとに実運用 1 サイクル完走 + 証跡がゲート検証可能 |
| V2 帯: 画像文化圏 | Instagram（Graph API — PO-1 裁定）+ 既存媒体の画像リッチ化（アダプタ拡張） | 同上 |
| V3 帯: 音声→動画文化圏 | Podcast（RSS）→ stand.fm → YouTube | 同上 |
| cross-cutting: 横断能力 | 配信帯に属さない共通基盤（下表）。V1 から漸次整備 | 各チャネルの BR-M 要求の AC/TC 被覆 |
| S-integrate（旧 S2 相当） | 統合戦略ループ（SR-17〜19）。各媒体の共通契約証跡に横串 | 統合因果分析が複数媒体の実証跡で動作 |

**スライス正準語彙**: `S0-kernel / V1 / V2 / V3 / S-integrate / cross-cutting`。

**帯（文化圏）の順序原理**: 攻略しやすいのはテキスト文化圏、次に画像文化圏、最後に動画文化圏。
これは**コンテンツ資産の再利用性と生成複雑度を主軸とする既定順序**であり（前段の資産 —
コンテンツ正本・kernel・アダプタ契約 — が次段の入力になる）、媒体固有の規約・停止リスクは
帯内順位と参入ゲートで別評価する（帯順序の根拠に含めない）。

**21 チャネル完全対応表**（br-media 正本の全チャネル — 発明も欠落もなし）:

| 区分 | チャネル | 割当 |
|---|---|---|
| 配信（テキスト） | WP / HS / NOTE / X / LINE / DC / KDP | V1 帯 |
| 配信（画像） | IG | V2 帯 |
| 配信（音声→動画） | PC / STFM / YT | V3 帯 |
| 横断: 制作・生成 | CANVA / GENAI / SEED / DS | cross-cutting（SEED は V3 帯の前提） |
| 横断: 収益 | STRIPE / AFF | cross-cutting（V1 から接続） |
| 横断: 計測 | MEAS | cross-cutting（V1 から接続・KPI handoff の受け皿） |
| 横断: 運用連携 | NOTION | cross-cutting |
| 横断: 自前アプリ面 | PWA / PLAY | cross-cutting（事業判断で随時。PLAY は PO-7 で保留中） |

**将来候補（uncommitted）**: TikTok（TT）。BR-M 未起票のため本 ADR では段階配置しない。
採用の前提 = BR-M-TT 起票・調査・PO 裁定済み接続経路・allow-list・AC/TC 完備。調査が
公開投稿自動化の API 制約（audit 要件等）を実証した場合、その解消を blocker として確定する。
配置先候補は V3 帯末尾。

V1.0 に WordPress を選ぶ理由: ADR-005 により REST 直の公式経路で、anti-bot・BAN リスクが最小。
パイプライン全体の貫通検証を媒体側の不確実性と切り離せる（PoC 全 PASS — 実証済み）。

（非規範資料: 帯内の詳細検討は helix-worker ローカルの運用メモ
`~/ops/staged-release-strategy.md` v0.1（本リポ外・manifest 未登録）で行った。規範は本 ADR のみ。）

## 不変条件（縦切りしても割らないもの）

1. **証跡スキーマと状態機械は媒体共通**（s0-contract が正準のまま）。媒体別に分岐させない。
   媒体固有の差（payload・品質ゲート・policy・evidence 要件・quota・外部操作 — 例: IG の
   design-evidence ゲート、KDP の AI 申告、HS の法定表示検証、LINE の通数予算）は
   **契約された拡張点（extension point）に閉じ込める**（kernel 本体へ漏らさない）
2. 機械ゲート・manifest・契約正本 9 本の規律は全スライスに同一適用（縦切りは品質基準の緩和ではない）
3. ブランド隔離は V1 時点から適用（後付けにしない）
4. 統合戦略（総合的なマーケティング戦略）が最終ゴールであることは不変。縦切りは到達手段の再編であり、
   ゴールの放棄ではない

## 理由

- 価値の初回到達を「土台 49 単位完成後」から「V1 貫通時」へ前倒しできる
- 契約の欠陥が V1 の実運用で早期露見し、V2 以降の媒体に反映される（机上検証より精度が上がる）
- 媒体ごとの失敗が分離される（X の承認済み接続経路が成立しなくても WP 運用は回り続ける。
  自動貫通が成立しない媒体は attended 運用への降格または帯内順位の後送で扱う）
- 各縦切りが「実運用 1 サイクル完走」という検証可能な完了定義を持ち、進捗が散文でなく実物で示される

## 帰結

- implementation-units.json の 49 単位を正準語彙 `S0-kernel / V1 / V2 / V3 / S-integrate /
  cross-cutting` で再割当する（units 自体の契約は不変、スライス割当のみ変更。
  G-SLICE-PLACEMENT の 4 点一致に従い manifest・frontmatter・traces を同時更新）
- uncovered-apis / update-closure の管理単位を縦切りスライスに合わせて再編する
- L2-prototypes は V1（WordPress）の運用シナリオから着手する
- ADR-007（VPS 無人車線）承認済みの場合、V1 の実行環境は helix-worker とする

## 未決事項（PO 判断）

1. V1 帯の内部順序（特に メール先行 vs X 先行）と Discord／KDP の実施要否
2. S0-kernel の 3 機能への絞り込みの妥当性（設定管理・KPI handoff を kernel に含めるか）
3. TikTok（将来候補・uncommitted）の採用可否と配置（BR-M-TT 起票・調査・PO 裁定を経て確定）
4. X Premium・LINE 追加通数など有償枠の扱い（NFR-6 月上限との整合）
