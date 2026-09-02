# 役割分担: HELIX-WP-THEME と GRAPHIX-NEO（2026-08-28）

status: draft（PO 判断待ち）

統合層には「どちらに何を置くか」だけを置く。各製品のコンセプト・方針・順序は各リポが正本。

| | HELIX-WP-THEME（`base/wp-theme`） | GRAPHIX-NEO（`base/graphix-neo`、submodule 結合済み・Phase 0） |
|---|---|---|
| 役割 | 構造自由なテーマ。運用知見・開発知見をためる | 実証済みパターンだけを取り込み、AIO/LLMO に最適化する製品 |
| 正本 | `docs/planning/L0-agent-controlled-variety.md`（L0 企画: JSON 制御維持 × テーマA/B 水準の取り込み × エージェント制御のバリエーション）と `docs/requirements/authority.md`（#73 / PR #77 で 0 から作り直し、PO 採否待ち 15 件） | `docs/planning/Graphix_NEO_Project_Proposal_v0.2.md`（企画書 v0.2、L0 入力。intake policy は未作成） |
| 流れ | 出口: 使われたパターン・崩れなかった規約 | 入口: WP-THEME からの一方向取り込み |

共通前提: 4 層モデル（トークン → 骨格 → パーツ → 内容）。両者とも**破壊的な値は止める**。cross-repo 編集禁止（取り込みは PR 単位で参照元 commit を記録）。

PO 判断: この分担でよいか。各リポの Draft PR は本ファイルの正本欄を参照。
