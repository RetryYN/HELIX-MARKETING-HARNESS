# AGENTS.md

Codex エージェント向け。作業規律の正本は CLAUDE.md（同内容を適用）。特に:

- 編集は MD＋JSON 正本＋baseline を同一コミット。push 前に `python3 scripts/validate_requirements.py`（全ゲート — 件数の正本は docs/governance/baseline.json の gate_count）を必ず PASS させる。
- DDL・状態遷移・evidence 型の正準は docs/requirements/s0-contract_v0.1.md。矛盾したら上位文書優先。
- 上流戦略層の正本は docs/requirements/strategy-loop-requirements_v0.1.md／strategy-learning-contract_v0.1.md
  ＋ json/strategy/（12 schema）。下流処理から上流戦略正本を直接更新するコードを書かない（還流は TLP のみ）。
- 外部書込みは Docker WP のみ。credential を repo・DB・ログに書かない。

## 実装正本（2026-08-01 クロージャー）

- Python パッケージは **`src/helix/`** に統一（旧 `harness/` は廃止・二重パッケージなし）。
- 実装・検証の入力は契約 JSON 正本（`docs/requirements/json/**/*-contracts.json`、
  `docs/design/json/{cmp,du}-contracts.json`）。MD は `scripts/render_views.py` の生成ビューで手編集禁止。
