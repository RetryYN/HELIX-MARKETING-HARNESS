---
artifact_id: AUTH-ADR-ADR-003-BROWSER-THREE-TIER
lifecycle_status: draft
slice: cross
---

# ADR-003: ブラウザ自動化は三段構え（Playwright → Camoufox → ビジョン）

- status: accepted
- date: 2026-07-30
- decision_authority: PO（tech-stack §2 の判断を ADR 化）
- 関連: FR-42/43、NFR-2/3/7、risk-register RSK-01/02

## 決定

無人自走のブラウザ操作は (1) Playwright for Python（DOM 駆動・主）、(2) Camoufox（検知の堅いサイトのステルス層）、(3) computer use 系ビジョン駆動（最終手段）の三段構えとする。Claude Code 内蔵ブラウザは無人ループに使わない（対話デバッグ・OAuth 初回取得など attended 用途のみ）。

## 理由

2026 年時点の anti-bot は TLS 指紋・挙動タイミングまで見る多次元検知が主流で、単段では突破率と保守性が両立しない。内蔵ブラウザはクリーンプロファイル・attended 前提の設計で、セッション永続・決定性・cron 無人自走（NFR-2/3）と噛み合わない。

## 帰結

- セッションは storage_state を暗号化保存（FR-47）
- 攻略地図（playbooks）を SQLite に蓄積し、自己修復 1 回→エスカレーション（FR-43）
