# AGENTS.md

Codex エージェント向け。作業規律の正本は CLAUDE.md（同内容を適用）。特に:

- 編集は MD＋JSON 正本＋baseline を同一コミット。push 前に `python3 scripts/validate_requirements.py`（51 ゲート）を必ず PASS させる。
- DDL・状態遷移・evidence 型の正準は docs/requirements/s0-contract_v0.1.md。矛盾したら上位文書優先。
- 外部書込みは Docker WP のみ。credential を repo・DB・ログに書かない。
