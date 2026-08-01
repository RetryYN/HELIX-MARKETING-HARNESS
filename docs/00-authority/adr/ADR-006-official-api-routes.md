---
artifact_id: AUTH-ADR-ADR-006-OFFICIAL-API-ROUTES
lifecycle_status: draft
slice: cross
---

# ADR-006: 無料公式 API が存在する接続はブラウザ突破より API 経路を採用

- status: accepted
- date: 2026-07-30
- decision_authority: PO（方針「こちらで用意できる環境はすべて実装する」により br-media §99 #1〜#4 を決定）
- 関連: BR-F1、BR-M-IG/LINE/MEAS/GENAI、RSK-01/08/09、tech-stack §5、POC-03

## 決定

2026-07 の媒体構造調査（br-media）で無料の公式 API が確認された接続は、ブラウザ自動化でなく API 経路を第一経路とする:

1. **Instagram**: Graph API（プロアカウント化して利用）
2. **LINE**: Messaging API（フリープラン上限は管理画面と同一）
3. **GA4 / Search Console**: 正規 API（Data API / Search Console API）。POC-03 は経路判断でなく疎通・データ取得の検証に変更
4. **Gemini**: 自動操作対象から恒久除外。他生成 AI もアカウント分離（BR-M-GENAI-2）。静的画像生成は Codex CLI image_gen を第一経路（BR-M-GENAI-4）

## 理由

- ブラウザ突破は「API がない/貧弱な媒体のための手段」（ADR-002）であり、無料公式 API がある接続で規約・BAN リスク（RSK-01）を負う理由がない
- 特に Google 系は UI 自動化の規約違反が GA4/GSC/Gmail の連座停止（RSK-09）に波及し事業全体を止め得る
- 固定費ゼロ原則は維持される（上記 API はすべて無料枠）

## 帰結

- ADR-002 の優先順は「MCP → **無料公式 API** → ブラウザ → 有償 API」に精緻化される（接続レジストリの宣言で表現）
- charter §10 の「SNS はブラウザ突破」は「公式 API のない媒体（X 投稿・note・KDP・ASP 等）に限る」と読み替える（charter 本文は次版で追記）
- API 利用にはユーザーによる環境準備（IG プロアカウント化、LINE チャネル発行、Google Cloud プロジェクト+API 有効化+認証情報）が必要 — s0-contract の環境契約に含める
