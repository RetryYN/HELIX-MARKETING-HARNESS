# ADR-001: 実装言語は Python 単層

- status: accepted
- date: 2026-07-30
- decision_authority: PO（charter §10 ⑦で確定済みの判断を ADR 化）
- 関連: HELIX 本体 ADR-010（Python=semantic core, Node=commit boundary）、tech-stack §1

## 決定

ハーネス本体は Python 3.14+ の単層で実装する。TypeScript の boundary 層は設けない。

## 理由

本ハーネスはデータ処理・意味判断が中核で、HELIX 本体 ADR-010 の「Python=semantic core」と一貫する。HELIX 本体が Node を必要とした commit boundary / CLI 配布の要件が本プロジェクトにはなく、単層で足りる。

## 帰結

- uv / pytest / ruff を標準ツールチェーンとする
- Remotion（動画）等 Node 依存ツールは外部プロセスとして呼び出し、ハーネス本体の言語境界に含めない
