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
if ! out=$(python3 "$(dirname "$0")/../validate_requirements.py" 2>&1); then
  echo "要件整合ゲート FAIL — commit/push をブロックしました。" >&2
  echo "$out" | grep '^FAIL' >&2
  exit 2
fi
exit 0
