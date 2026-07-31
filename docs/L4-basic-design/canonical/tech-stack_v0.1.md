# 技術・ツール選定書 v0.1

> status: **confirmed**（2026-07-31 PO 承認 — 要件定義完遂指示。AI 起草）
> charter §10 で確定した選定の集約正本＋実装レベルの具体化。選定理由と代替案・再検討条件を明記。

## 1. ハーネス本体

| 領域 | 選定 | 理由 | 代替（不採用理由） |
|---|---|---|---|
| 言語 | **Python 3.14+**（2026-07 現行 stable 3.14.6） | データ・意味判断の中核。HELIX 本体 ADR-010（Python=semantic core）と一貫 | TypeScript（HELIX では boundary 用。本ハーネスは単層で足りる） |
| DB | **SQLite**（標準 sqlite3） | 数値・状態限定でサーバ不要・単一ファイル・HELIX 本体と同構成 | Postgres（個人規模に過剰）、Notion（判定正本にしない方針） |
| パッケージ管理 | **uv** | 高速・lock 再現性 | pip+venv（可。uv を第一候補） |
| テスト | **pytest** | S0 受入基準の機械検証（ゲート拒否テスト等） | — |
| Lint/Format | **ruff** | 単一ツールで lint+format | — |
| スケジューラ | **cron（WSL）+ ハーネス内 heartbeat** | 定時起動は OS、回転判断はエンジン | — |

## 2. ブラウザ自動化（五役: SNS・計測・生成 AI・素材・レンダリング）

**方針判断: 無人自走の突破は Playwright を正とする。Claude Code 標準ブラウザは無人用途に使わない。**
Claude Code 内蔵ブラウザ（2026-07 実装）は「対話的・人が監視する前提／クリーンプロファイルで毎回再ログイン／
書き込みは分類器審査」という設計で、実アカウント操作の安全策としては正しいが、本ハーネスの
ヒューマンアウトオブループ・cron 無人自走・決定性（NFR-2）・再開性（NFR-3）・攻略地図（playbooks）とは
噛み合わない。繰り返し可能・セッション永続・CI 投入が要る無人突破には Playwright 系を用いる。

2026 年の標準構成に合わせ**三段構え**とする（anti-bot は TLS 指紋・挙動タイミングまで見る多次元検知が主流）:

| 段 | 選定 | 用途 |
|---|---|---|
| 1. DOM 駆動（主） | **Playwright for Python**（1.61+）+ LLM 操作判断 | 無人ループ内の 8 割の作業。headed/headless 切替（WSLg で headed 可）。persistent context でセッション永続 |
| 2. ステルス層 | **Camoufox**（C++ レベル偽装の Firefox 系 anti-detect） | 検知の堅いサイト（SNS・生成 AI UI 等）で Playwright が弾かれた場合 |
| 3. ビジョン駆動（フォールバック） | computer use 系（スクショ＋座標操作） | DOM アクセス不能・canvas UI 等の最終手段 |
| 補助（無人ループ外） | **Claude Code 標準ブラウザ** | 開発中の対話デバッグ・軽い目視確認・OAuth 初回ログイン取得など、人が見ている場面のみ |

| 項目 | 選定 | 備考 |
|---|---|---|
| 突破対象 | SNS（note/YouTube/stand.fm）、GTM、生成 AI Web UI（ChatGPT/Grok — Gemini は除外・ADR-006）、Canva（MCP フォールバック）、ASP、KDP、メルカリ等保留分。**IG・LINE・GA4/GSC は公式 API 経路のためブラウザ対象外（ADR-006）。X はブラウザ書込み prohibited（BR-M-X-4）— attended 人手投稿のみ** | 攻略地図（playbooks）を SQLite に蓄積・自己修復 1 回→エスカレーション |
| レンダリング | 同 Playwright（スクショ・PDF 出力） | 制作パイプラインと基盤共有 |
| セッション保管 | Playwright storage_state を暗号化保存 | 平文 credential 禁止（NFR-4） |

## 3. コンテンツ基盤

| 領域 | 選定 | 備考 |
|---|---|---|
| コンテンツ資産 DB | **WordPress**（REST API + Application Passwords / WP-CLI） | 重い実体はすべて WP。開発は既存テーマ解析＋子テーマ＋自作プラグイン（PHP/HTML/CSS/JS） |
| ローカル検証環境 | **Docker（wordpress + mariadb）** | 構築→検証→本番反映。テーマ解析もローカル複製上で |
| 計画・ネタ UI | **Notion**（公式 MCP） | 構築済み: 行動計画/ネタ帳/スプリント DB。低頻度同期のみ |
| 編集基盤 | **git 管理ブランドワークスペース**（別リポジトリ） | drafts/ assets-src/。審査 PASS = commit hash |
| デザイン正本 | **Claude Design（DesignSync）** | トークンを全制作物に注入 |

## 4. 制作パイプライン

| 制作物 | ツールチェーン |
|---|---|
| 図解・OGP・バナー | HTML/SVG/CSS → Playwright スクショ |
| スライド・資料（リードマグネット） | HTML → Playwright PDF（slide-monster を素材候補に） |
| 診断ツール・シミュレータ | HTML/JS → WP 埋め込み → PWA 化（manifest+SW）→ TWA で Google Play（$25 買切） |
| 3D | three.js（軽量）/ **Blender ヘッドレス bpy**（高品質。RTX 5070 CUDA/OptiX） |
| 音声 | **VOICEVOX**（localhost API、商用可） |
| 動画 | **Remotion**（テンプレート化）+ **ffmpeg**（NVENC ハードウェアエンコード） |
| 電子書籍 | **pandoc** → EPUB → KDP（ブラウザ） |
| 生成 AI 画像（静的） | **Codex CLI 内蔵 image_gen**（`codex exec` 非対話・ChatGPT Pro 枠内で追加費用なし・動作確認済 2026-07-30）主。従: 保有アカウント Web UI（ブラウザ） |
| 生成 AI 動画 | 保有アカウント Web UI（ブラウザ）。例外: **Seedance API**（有償・台帳記録・月上限 config） |
| 素材調達 | **Canva**（MCP 優先）: ストック写真・クリップ・BGM。ライセンス紐づけを DB 管理 |

## 5. 接続レジストリ（初期）

| サービス | 第一経路 | フォールバック |
|---|---|---|
| Notion / Canva / HubSpot / Stripe | 公式 MCP | ブラウザ |
| WordPress | REST API / WP-CLI | — |
| GA4 / Search Console | 正規 API（無料。ADR-006） | ブラウザエクスポート（一時） |
| Instagram | Graph API（無料・プロアカウント。ADR-006） | —（エスカレーション） |
| LINE 公式 | Messaging API（無料枠。ADR-006） | —（エスカレーション） |
| GTM / note / YouTube / stand.fm / ASP / KDP | ブラウザ | —（エスカレーション） |
| X | attended 人手投稿（ブラウザ書込み prohibited・BR-M-X-4） | 公式 API 採用時のみ自動化を再検討 |
| Seedance | 有償 API（例外台帳） | ブラウザ生成 AI |
| Codex CLI（画像生成） | CLI 非対話実行（ChatGPT Pro サブスク枠） | ブラウザ生成 AI |
| Claude Design | DesignSync | 同期済みキャッシュ |
| 承認・通知 | Claude Code アプリ通知 | — |

## 6. マーケティングサービス選定（確定済みの再掲）

- **CRM/リード/メルマガ**: HubSpot 無料枠（自動化は買わずハーネス駆動）
- **LINE**: 公式アカウント フリープラン（セグメント配信専用）
- **コミュニティ**: Discord（媒体として運用）
- **決済**: Stripe（取引手数料のみ）／ **販売**: note・KDP・アフィリエイト（ASP）
- **音声配信**: Podcast RSS（WP 自前）主・stand.fm 従・Voicy 保留
- **分析面**: Python 生成 HTML 主・xlsx→スプシ従・Notion チャート不使用。
  **閲覧・対話分析は Claude Code 内蔵ブラウザを BI ビューアとして使う** — ローカル HTML なので
  内蔵ブラウザの制約（クリーンプロファイル・attended 前提）が問題にならず、ダッシュボードを
  Claude と一緒に見ながら SQLite へ追加クエリを投げる対話型 BI が成立する。Notion 埋め込みは共有・常設用
- **保留**: Shopify（固定費）・メルカリ（物理オペ）・iOS（$99/年）・R 言語（MMM 段階で再訪）

## 7. 再検討トリガー

| 条件 | 再検討対象 |
|---|---|
| メルマガ月 2,000 通超 | 配信専業サービスの無料枠 or HubSpot 有料化 |
| 本格 EC 化（商品数増） | Shopify |
| MMM 実装段階 | R（ベイズ回帰系ライブラリ）導入 |
| iOS 需要の証跡 | App Store（$99/年） |
| ブラウザ突破の恒常的破損 | 該当サービスのみ API 経路へ切替（例外台帳） |
| Codex CLI 画像生成が日次上限へ恒常到達 | OpenAI Images API（従量・明示レート仕様）へ切替（例外台帳） |
| Remotion のテンプレ表現力・保守性に不満 | Revideo / MotionForge（2026 時点で成熟した OSS 代替） |
| 実装着手時（全般） | 各ツールの現行版をリサーチエンジンで再確認（本書の版数は 2026-07 時点） |
