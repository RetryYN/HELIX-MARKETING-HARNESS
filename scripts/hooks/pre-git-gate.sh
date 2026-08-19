#!/usr/bin/env bash
# PreToolUse(Bash) hook: git commit/push の前に要件整合ゲートを強制する（fail-close）。
# stdin: Claude Code の hook JSON。解析不能な入力はブロック（exit 2）。
# 注意: 本 hook は Claude Code 経由の操作にしか効かない補助線であり、
# 実際の停止境界は GitHub 側の branch protection / required status（Docs CI）に置く。
set -u
input=$(cat)
if ! cmd=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null); then
  echo "pre-git-gate: hook 入力の JSON 解析に失敗 — fail-close でブロックします。" >&2
  exit 2
fi
# git のサブコマンド commit/push を、-C <dir> や -c k=v 等のグローバルオプション越しでも検出する
if ! printf '%s' "$cmd" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]+-[-[:alnum:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+(commit|push)([[:space:]]|$)'; then
  exit 0
fi
out=$(python3 "$(dirname "$0")/../validate_requirements.py" 2>&1) || true
# CLAUDE.md 鉄則5の例外: 要求cutover系ゲートの「PO未承認・未凍結による意図した赤」だけは
# requirements_baseline_status=revising の間 commit/push を妨げない（閉じた列挙。他ゲートへ拡張しない）。
intended_red='G-REQ-STRATEGY-TEST-AUTHORITY|G-REQ-LEGACY-MEANING-INVENTORY|G-REQ-LEGACY-SR-NFR-MEANING-INVENTORY|G-REQ-LEGACY-MR-MEANING-INVENTORY|G-REQ-LEGACY-FN-MEANING-INVENTORY|G-REQ-LEGACY-AC-MEANING-INVENTORY|G-REQ-LEGACY-TC-MEANING-INVENTORY|G-REQ-OPEN-REFINEMENTS'
unexpected=$(printf '%s\n' "$out" | grep '^FAIL' | grep -Ev "^FAIL \[($intended_red)\]" || true)
if [ -n "$unexpected" ]; then
  echo "要件整合ゲート FAIL — commit/push をブロックしました（意図した赤以外の違反）。" >&2
  printf '%s\n' "$unexpected" >&2
  exit 2
fi
exit 0
