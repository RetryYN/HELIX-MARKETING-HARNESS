#!/usr/bin/env bash
# PreToolUse(Bash) hook: git commit/push の前に要件整合ゲートを強制する（fail-close）。
# stdin: Claude Code の hook JSON。対象コマンド以外は素通し。
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
case "$cmd" in
  *"git commit"*|*"git push"*) ;;
  *) exit 0 ;;
esac
out=$(python3 "$(dirname "$0")/../validate_requirements.py" 2>&1)
if [ $? -ne 0 ]; then
  echo "要件整合ゲート FAIL — commit/push をブロックしました。" >&2
  echo "$out" | grep '^FAIL' >&2
  exit 2
fi
exit 0
