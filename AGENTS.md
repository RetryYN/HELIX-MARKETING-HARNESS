# AGENTS.md

Codex エージェント向け。作業規律の正本は CLAUDE.md（同内容を適用）。特に:

- **作業境界**: 変更対象は本リポジトリのみ。他リポジトリ（HELIX-HARNESS／TAKUMI_CMO-Claude_Cowark）は
  read-only。書き込みは指示に含まれていても着手前に PO へ確認する。
- 編集は 正本 JSON＋生成ビュー＋manifest＋baseline を同一コミット。push 前に
  `python3 tools/gates/run_all.py`（全ゲート — 件数の正本は
  docs/00-authority/baselines/baseline.json の gate_count）を必ず PASS させる。
- 成果物の権威正本は docs/00-authority/artifact-manifest.json。未登録の成果物を confirmed にしない。
- DDL・状態遷移・evidence 型の正準は docs/L3-system-requirements/canonical/s0-contract_v0.1.md。
  矛盾したら上位文書優先。
- 上流戦略層の正本は docs/L3-system-requirements/canonical/strategy/ の要件・契約 ＋
  docs/L3-system-requirements/canonical/schemas/strategy/（12 schema）。下流処理から上流戦略正本を
  直接更新するコードを書かない（還流は TLP のみ）。
- 公開コンテンツの外部書込み先は Docker WP のみ。Notion 審査同期と Claude Code 承認通知は
  明示された `policy_category`・service・operation・endpoint allow-list と承認を通った場合に限る。
  credential を repo・DB・ログに書かない。

## 実装正本

- Python パッケージは **`src/helix/`** に統一（二重パッケージなし）。
- 実装・検証の入力は契約 JSON 正本 9 本（BR/FR/SR/NFR/AC/TC/CMP/DU contracts ＋
  L6 責務／API／契約節／AC／TC／UT = `docs/L6-feature-design/S0/implementation-units.json`）。
  MD は `scripts/render_views.py` の生成ビューで手編集禁止。
- ゲート実装は `tools/gates/` の工程別モジュール。`scripts/validate_requirements.py` は互換ラッパーで、
  ゲート本体を書き足さない。
- 現行分母は AC=237 ／ TCC=243 ／ API=59 ／ API_UT=199 のみ。旧体系の分母は
  baseline.json の `historical_counts` にのみ保持する。
