---
artifact_id: AUTH-ADR-ADR-009-PRODUCT-NAMING-SHIP-BOUNDARY
lifecycle_status: draft
slice: cross
---

# ADR-009: 製品パッケージの命名・二層ゲートの区別・出荷境界の定義

- status: proposed
- date: 2026-08-12
- decision_authority: PO（未承認 — 本 ADR は提案ドラフト）
- 関連: ADR-001（python-single-layer）、ADR-007（VPS 無人車線）、ADR-008（媒体縦切り）、
  AGENTS.md §実装正本、README「HELIX-HARNESS 取込は未実施」

## 背景: 概念の層の確定

本リポジトリの位置づけを次で固定する:

- **HELIX-HARNESS** = 開発環境。「正しく作らせる」ための厳格さ（契約正本・manifest・被覆検査・
  test-first・CI）を提供する
- **HELIX-MARKETING-HARNESS** = HELIX の開発プロジェクトの一つとして走る**運用 OS**。HELIX が親の開発システム、本リポジトリはその適用プロジェクトという主従関係を固定する。「正しく動かし続ける」ための
  厳格さ（承認・状態機械・証跡・ブランド隔離・fail-close）を製品機能として持つ
- **「取込」の主語は HELIX-HARNESS**。本リポジトリが自前実装した開発時ゲート（tools/gates/）で
  実証された思想・手法を、HELIX-HARNESS 側が開発環境の機能として吸収する。
  **HELIX-HARNESS を本リポジトリに部品として内包する方向の取込は行わない**。
  HELIX は常に外部の開発環境であり、製品（MARKETING-OS）の実行時依存にならない

この確定から、現行フォルダ編成の 3 つのずれを是正する。

## 決定（提案）

### 1. 製品パッケージを `src/helix/` から `src/helix_mkt/` へ改名

製品は HELIX（開発環境）ではなくマーケティング運用 OS であり、パッケージ名 `helix` は
概念の混同をコード名に固定してしまう。現時点で中身は空の `__init__.py`（helix／gates／kernel／db）
のみ（S0.1 未着手）であり、改名コストが最小の今実施する。ADR-001 の「単一パッケージ」原則は維持
（`src/helix_mkt/` に統一）。
AGENTS.md / CLAUDE.md の該当記述を同一コミットで改訂する。

### 2. 二層ゲートの区別を作業規律に明文化

| 層 | 場所 | 役割 | 寿命 |
|---|---|---|---|
| 開発時ゲート | tools/gates/ | 契約被覆・manifest・traceability 等、開発者を縛る | HELIX-HARNESS が同等機能を提供した時点で置換・廃止し得る |
| 運用時ゲート | src/helix_mkt/gates/ | 承認・状態機械・証跡検証等、製品が実行時に自らを縛る | 製品と共に永続。出荷対象 |

CLAUDE.md / AGENTS.md に本表を追記し、「gates」への言及は必ず層を明示する。
開発時ゲートには過剰投資しない（HELIX-HARNESS 側が吸収する前提の暫定実装）。

### 3. 出荷境界（ship manifest）の新設

promote（HELIX-MARKETING-OS への昇格）時に何を送るかの正本として
`docs/00-authority/ship-manifest.json`（提案 — 最終パスは PO 承認時に確定）を新設する。原則:

- **出荷する**: src/helix_mkt/（運用時ゲート含む）、ランタイムエージェント定義（モデル・プロンプト・
  権限・予算上限の契約）、migration、運用に必要な schema／設定テンプレート
- **出荷しない**: tools/（開発時ゲート）、scripts/（開発補助）、.claude/ .codex/ .agents/
  （開発サブエージェント設定 — OS を作る作業員の編成であり製品ではない）、tests の開発専用部、
  docs の開発工程文書（運用に必要な文書のみ選別）
- promote は履歴ごと push せず、タグ時点スナップショットを ship-manifest で濾過して送る
  （構築計画の promote.sh 仕様に反映）

### 4. ランタイムエージェント定義は製品の一部

OS が実行時に用いる AI エージェント（媒体ワーカー・戦略ループ・承認待ち処理）の構成は、
開発者の個人環境（~/.claude・~/.codex）に依存してはならない。モデル選定・プロンプト・権限・
予算上限を契約正本としてリポジトリ内に定義し、ship-manifest の出荷対象に含める。

## 理由

- 概念のずれ（開発環境と運用 OS の混同）がパッケージ名・フォルダ名・出荷物に固定される前に是正する
- src が実質空の現在が、命名変更の唯一の低コスト時点
- 出荷境界の欠如は、P2（昇格路）着手時に開発道具の完成品混入として顕在化することが確実

## 帰結

- AGENTS.md「Python パッケージは src/helix/ に統一」→「src/helix_mkt/ に統一」へ改訂
- 構築計画の promote.sh 仕様に ship-manifest 濾過を組み込む
- HELIX-HARNESS 側への「取込」提案（本リポジトリの開発時ゲートの思想・手法の還流）は、
  HELIX-HARNESS 完成後に別途起票する（本リポジトリの管轄外）

## 未決事項（PO 判断）

1. パッケージ名の最終確定（本 ADR は helix_mkt を提案。marketing_os 等の代案あり）
2. docs のうち出荷対象に含める文書の範囲（運用手順・ランタイム契約のみか、設計正本も含むか）
