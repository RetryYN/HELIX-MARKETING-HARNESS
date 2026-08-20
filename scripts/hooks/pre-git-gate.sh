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
out=$(python3 "$(dirname "$0")/../validate_requirements.py" 2>&1)
validator_rc=$?
fails=$(printf '%s\n' "$out" | grep '^FAIL' || true)
# validator 自体の異常終了（非0 かつ FAIL 行なし = クラッシュ・構文破損等）は必ず遮断する
if [ "$validator_rc" -ne 0 ] && [ -z "$fails" ]; then
  echo "pre-git-gate: validator が異常終了（FAIL 出力なし）— fail-close でブロックします。" >&2
  printf '%s\n' "$out" | tail -5 >&2
  exit 2
fi
if [ "$validator_rc" -eq 0 ]; then
  # 終了コード0でも FAIL 行があれば矛盾（validator改変等）として遮断する
  if [ -n "$fails" ]; then
    echo "pre-git-gate: validator が exit 0 なのに FAIL 行を出力 — fail-close でブロックします。" >&2
    printf '%s\n' "$fails" >&2
    exit 2
  fi
  exit 0
fi
# CLAUDE.md 鉄則5の例外: 要求cutover系ゲート（閉じた列挙）の「PO未承認・未凍結」を理由とする赤だけは
# requirements_baseline_status=revising の間 commit/push を妨げない。他ゲート・他原因へ拡張しない。
# 例外の有効化は正本 JSON の状態を読んで厳密判定する（欠落・読込失敗・別状態は fail-close）。
authority="$(dirname "$0")/../../docs/00-authority/development/requirement-engine-authority.json"
status=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['requirements_baseline_status'])" "$authority" 2>/dev/null || true)
if [ "$status" != "revising" ]; then
  echo "要件整合ゲート FAIL — commit/push をブロックしました（baseline状態=${status:-unreadable} のため例外なし）。" >&2
  printf '%s\n' "$fails" >&2
  exit 2
fi
# ゲートID閉集合 × 違反item単位の PO未承認/未凍結理由の閉集合の**両方**を要求する。
# 行内に許可理由と非許可理由が混在する場合は遮断する（item単位で全件一致が必要）。
unexpected=$(printf '%s\n' "$fails" | python3 -c "
import ast, re, sys

# ゲートごとに許可する fault 文言を anchored 完全一致で定義する（閉集合。部分一致は認めない）
ALLOWED = {
    'G-REQ-STRATEGY-TEST-AUTHORITY': [
        re.compile(r'^strategy test ledger lifecycle=draft references=\[.*\]\$'),
        re.compile(r'^strategy test ledgerにPO content receiptがない\$'),
    ],
    'G-REQ-OPEN-REFINEMENTS': [
        re.compile(r'^[^:]+: lifecycle=(draft|specified)（frozenでない）\$'),
        re.compile(r'^[^:]+: PO approval receiptがない\$'),
        re.compile(r'^[^:]+: pending_resolution=\d+\$'),
    ],
}
legacy = re.compile(r'^旧[A-Za-z0-9/]+意味分類候補がPO未承認 remaining=\d+\$')
for gate in ('G-REQ-LEGACY-MEANING-INVENTORY', 'G-REQ-LEGACY-SR-NFR-MEANING-INVENTORY',
             'G-REQ-LEGACY-MR-MEANING-INVENTORY', 'G-REQ-LEGACY-FN-MEANING-INVENTORY',
             'G-REQ-LEGACY-AC-MEANING-INVENTORY', 'G-REQ-LEGACY-TC-MEANING-INVENTORY'):
    ALLOWED[gate] = [legacy]

head = re.compile(r'^FAIL \[([A-Z0-9-]+)\]')
tail = re.compile(r'違反=(\[.*\])\)\s*\$')
for line in sys.stdin:
    line = line.rstrip('\n')
    if not line:
        continue
    m = head.match(line)
    patterns = ALLOWED.get(m.group(1)) if m else None
    if not patterns:
        print(line); continue
    t = tail.search(line)
    try:
        items = ast.literal_eval(t.group(1)) if t else None
    except (ValueError, SyntaxError):
        items = None
    # 解析失敗・空list・非文字列item・閉集合外itemはすべて遮断側へ倒す
    if (not isinstance(items, list) or not items
            or any(not isinstance(i, str) or not any(p.match(i) for p in patterns) for i in items)):
        print(line)
" || printf '%s\n' "$fails")
if [ -n "$unexpected" ]; then
  echo "要件整合ゲート FAIL — commit/push をブロックしました（意図した赤以外の違反）。" >&2
  printf '%s\n' "$unexpected" >&2
  exit 2
fi
exit 0
