---
artifact_id: AUTH-ADR-ADR-005-WP-REST-DIRECT
lifecycle_status: draft
slice: cross
---

# ADR-005: WordPress は REST 直（専用連携プラグインを開発しない）

- status: accepted
- date: 2026-07-30
- decision_authority: PO（charter §10 ①で確定済みの判断を ADR 化）
- 関連: BR-G4、FR-44、MR-WP-1..4

## 決定

WP 連携は REST API（Application Passwords）＋ WP-CLI（構築系）で行い、ハーネス専用の WP プラグインは開発しない。WP 側の拡張は既存テーマ解析＋子テーマ＋（サイト機能として必要な場合のみ）自作プラグインに限る。

## 理由

連携プラグインは WP 側にもう一つの保守対象と攻撃面を作る。REST + Application Passwords で必要な操作（投稿・メディア・下書き・公開）は全て賄え、書き込みゲート（ペア ID 必須）はハーネス側で一元実装できる（FR-44）。

## 帰結

- 公開経路はハーネス経由のみ（審査未了の直接公開経路を持たない: MR-WP-1）
- ローカル Docker（wordpress + mariadb）で構築→検証→本番反映
