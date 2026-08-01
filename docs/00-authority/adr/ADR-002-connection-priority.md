---
artifact_id: AUTH-ADR-ADR-002-CONNECTION-PRIORITY
lifecycle_status: draft
slice: cross
---

# ADR-002: 外部接続の優先順は MCP → ブラウザ → 有償 API

- status: accepted
- date: 2026-07-30
- decision_authority: PO（charter §6/§10 で確定済みの判断を ADR 化）
- 関連: BR-F1、FR-41、tech-stack §5

## 決定

外部サービス接続は (1) 公式 MCP、(2) ブラウザ自動化、(3) 有償 API（明示的例外のみ、現状 Seedance）の優先順で選定し、接続レジストリに宣言的に保持する。

## 理由

固定費ゼロ原則（ゼロ広告費・ゼロ API 費）を守りつつ、API を持たない/貧弱な媒体（X・note・IG・KDP・ASP・LINE 等）をカバーするため。例外支出は spend_ledger で全件可視化する（FR-73）。

## 帰結

- 経路選定はコードに埋め込まずレジストリ参照（NFR-8: 媒体追加は行追加で完結）
- **精緻化（ADR-006, 2026-07-30）**: 無料公式 API が存在する接続は「MCP → 無料公式 API → ブラウザ → 有償 API」の順とする（IG・LINE・GA4/GSC が該当）
- ブラウザ経路には規約・BAN リスクが伴う → risk-register RSK-01/02 で管理、恒常破損時は当該サービスのみ API 切替（tech-stack §7）
