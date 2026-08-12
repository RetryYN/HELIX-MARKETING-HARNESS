---
artifact_id: AUTH-ADR-ADR-012-HELIX-HARNESS-TEMPLATE-ADOPTION
lifecycle_status: draft
slice: cross
---

# ADR-012: HELIX-HARNESS 設計テンプレートの適応

> status: **draft**。設計テンプレートの適応方針を記録する。テンプレートのランタイムを本リポジトリへ
> 移植する決定ではない。

- date: 2026-08-13
- decision_authority: PO 指示に基づく適応案（内容は draft。confirmed 化には承認 receipt が必要）
- source: [RetryYN/HELIX-HARNESS](https://github.com/RetryYN/HELIX-HARNESS/)
- source_commit: `57853db413e282b050ac5f37bab7809321c67842`
- source_policy: read-only。テンプレート側の branch／worktree／commit／issue／PR は変更しない

## 背景

本リポジトリは L0〜L6 の要件・契約・ゲートを Python-native に積み上げている。一方、HELIX-HARNESS は
L0〜L14 の V-model、要件発見イベント、stable ID による要件連鎖、L2 の 5 文書 screen 方法論、開発者向け
doctor／build／test の導線を設計テンプレートとして提供する。両者を無条件に統合すると、現在の JSON 正本と
Python ゲートが二重化されるため、方法論と開発環境だけを互換層として取り込む。

## 決定

1. **適応するもの**: V-model の工程語彙、要件発見→候補→試作→受入→凍結のライフサイクル、stable ID／
   要件→契約→AC→TC の連鎖、L2 screen-list／screen-flow／ui-element／wireframe／screen-detail の 5 点セット、
   doctor／docs／gates／test の開発コマンド。
2. **正本を変えないもの**: 実装入力は既存の契約 JSON 9 本、DDL・状態遷移・evidence 型は s0-contract、成果物の
   権威は artifact-manifest、検証入口は `tools/gates/run_all.py` とする。HELIX-HARNESS の `requirements-ir/` を
   並列正本として導入しない。
3. **ランタイム境界**: 本リポジトリの実装言語は Python、パッケージは `src/helix/`。テンプレートの Bun／Node
   ランタイム、`.helix` 実行系、外部サービス接続を本リポジトリの実装入力にしない。
4. **導入範囲**: 要件定義〜L3 の要求確定と L2 プロトタイプ設計までを直ちに利用可能にする。L4 以降と製品実装は
   既存スライス・PoC・承認・test-first の規律を継続する。
5. **外部参照の固定**: テンプレートの適応判断は source_commit に固定した read-only 監査で更新する。最新版を取り込む
   際は source_commit と対応表を更新し、旧テンプレート側へ書き込まない。

## 対応する成果物

- 対応表の正本: `docs/00-authority/template/helix-harness-alignment.json`
- 対応表 schema: `docs/00-authority/template/helix-harness-alignment.schema.json`
- 適応監査: `docs/00-authority/audits/helix-harness-template-alignment-2026-08-13.md`
- 要件定義手順: `docs/00-authority/development/requirement-definition-workflow_v0.1.md`
- L2 5 点セット: `docs/L2-prototypes/screens/`
- 開発環境契約: `docs/00-authority/development/development-environment_v0.1.md`

## 帰結と未決事項

- `make setup`／`make doctor`／`make docs`／`make gates`／`make test` で、VPS とローカルの同一手順を提供する。
- Bun／Node を追加しないため、テンプレートの UI ランタイムをそのまま実行することはできない。UI は L2 設計を先行し、
  認証・CSRF・再認証・principal 束縛の契約が confirmed になるまで実装を開始しない。
- テンプレートの将来更新を追随するか、別の source_commit に固定するかは、各更新時の監査で PO が判断する。
