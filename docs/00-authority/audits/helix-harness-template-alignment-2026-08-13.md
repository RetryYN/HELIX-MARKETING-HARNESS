---
artifact_id: AUTH-AUDIT-HELIX-HARNESS-TEMPLATE-ALIGNMENT-2026-08-13
lifecycle_status: draft
slice: cross
---

# HELIX-HARNESS 設計テンプレート適応監査（2026-08-13）

> status: **draft**。テンプレートの固定コミットを read-only 参照した構造監査であり、テンプレート側への変更や
> 本リポジトリの製品実装完了を意味しない。

## 監査対象

- repository: `RetryYN/HELIX-HARNESS`
- URL: <https://github.com/RetryYN/HELIX-HARNESS/>
- source commit: `57853db413e282b050ac5f37bab7809321c67842`
- 比較対象: 本リポジトリ `main` の現行正本、Python ゲート、L2 screen-list、開発スクリプト
- 制約: 外部リポジトリは clone して読むだけ。本リポジトリから外部へ write しない

## 判定

| テンプレートの設計要素 | 現行への対応 | 判定 | 根拠 |
|---|---|---|---|
| L0〜L14 V-model と人間境界 | L0〜L6 の現行工程を維持し、L0/L1/L2 の PO 境界と L3 以降のゲートを適応 | 適応 | `helix-harness-alignment.json` の `v-model` |
| requirement IR の stable ID 連鎖 | 既存の 9 契約 JSON、manifest、AC↔TC、L6 implementation-units を唯一の正本として接続 | ブリッジ | `requirement-ir`。並列 `requirements-ir/` は導入しない |
| discovery event と candidate lifecycle | 導入以後の候補→質問→試作→観測→仕様化→承認を append-only ledger に記録し、既存契約へ直接 mutation しない | 適応 | `requirement-discovery-events.json`、schema、`requirement_discovery.py` |
| L2 5 点 screen 方法論 | screen-list に加え screen-flow／ui-element／wireframe／screen-detail を S1 draft で追加。補助 business-flow と index でフォルダ責務を固定 | 採用 | `docs/L2-prototypes/` |
| doctor／build／typecheck／lint／test 導線 | Python の `make setup/doctor/docs/gates/test/check` と既存全ゲートへ写像 | 適応 | `Makefile`, `scripts/dev.py` |
| Bun／Node／template runtime | 本リポジトリの Python-native 制約と衝突するため、UI ランタイムは移植しない | 保留 | ADR-012、開発環境契約 |

## 不整合と是正

1. テンプレートの L0〜L14 と本リポジトリの L0〜L6 は同一の物理工程ではない。下流 L7〜L14 を空のまま追加せず、
   要件定義〜L3 の利用範囲を明示した。
2. テンプレートの `requirements-ir/` を追加すると契約 JSON との二重正本になる。stable ID の考え方だけを既存の
   契約・manifest・traceability へ写像した。
3. テンプレートの Bun コマンドをそのまま実行すると Python 単一パッケージ規律に反する。`scripts/dev.py` と
   `Makefile` は依存を増やさず、`uv.lock` と既存ゲートを呼び出す。
4. 現行 L2 は screen-list だけだったため、残る 4 文書を追加し、入口・状態・失敗・戻る操作・read/write 境界を
   画面単位で記録できるようにした。
5. discovery ledger は導入前の要求履歴を推測生成せず、`coverage_start_commit` 以後の監査証跡だけを保持する。契約 JSON
   の変更には proposal と decision、又は `deferred:` 理由付き withdrawal を機械的に要求する。

## Latest upstream verification

- checked_at: `2026-08-13`
- upstream_checked_commit: `e5dd2c6d3843a300d2daba64fdc9d07445f7e7ed`（`main`）
- adoption baseline: `57853db413e282b050ac5f37bab7809321c67842`（変更しない）
- checked range: `57853db413e282b050ac5f37bab7809321c67842..e5dd2c6d3843a300d2daba64fdc9d07445f7e7ed`
- observed difference: `package.json` の `esbuild` が `^0.28.1` から `^0.28.2`、
  `.github/workflows/harness-check.yml` の `upload-artifact` が `v4` から `v7` への更新のみ
- adoption disposition: **non-applicable**（adoption baseline unchanged）
- rationale: 本リポジトリは Bun／Node 依存と upstream workflow を実行入力として移植しない。Python-native の
  `uv.lock`、Makefile、CI、既存全ゲートが開発環境の正本であり、上記の upstream runtime／workflow 保守は
  適応範囲に意味差分を作らない。

## 検証方法

対応表は `G-TEMPLATE-ALIGNMENT` で schema、固定 source commit、必須 mapping、現行パス実在、Python-native
開発コマンド、L2 5 点セットを fail-close 検査する。テンプレートの最新版を追随する場合は source commit を更新し、
この監査と対応表を再生成してから gate とレビューをやり直す。追随しない場合も latest upstream verification に
checked SHA・差分・非適用理由を記録する。
