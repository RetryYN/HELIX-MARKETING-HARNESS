#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

failures=0

require_text() {
  local file="$1"
  local pattern="$2"
  local description="$3"

  if [[ ! -f "$file" ]] || ! grep -Eq "$pattern" "$file"; then
    echo "FAIL: $description ($file)" >&2
    failures=$((failures + 1))
  fi
}

require_text "AGENTS.md" 'CLAUDE\.md.*正本|正本.*CLAUDE\.md' \
  "Codex 入口が統合層 CLAUDE.md を正本として参照していない"
require_text "README.md" 'media/wp/' \
  "統合層 README に WordPress 媒体が登録されていない"

if [[ -d "media/wp" ]] && [[ -f "media/wp/AGENTS.md" ]]; then
  require_text "media/wp/AGENTS.md" '統合層規律の継承' \
    "media/wp の Codex adapter に統合層規律の継承がない"
  require_text "media/wp/CLAUDE.md" '統合層規律の継承' \
    "media/wp の Claude adapter に統合層規律の継承がない"
fi

if [[ -d "base/wp-theme" ]]; then
  require_text "base/wp-theme/AGENTS.md" 'media/wp/.*現行プロジェクト進捗ではない' \
    "base/wp-theme の Codex 指示に開発ベース境界がない"
  require_text "base/wp-theme/CLAUDE.md" 'media/wp/.*現行プロジェクト進捗ではない' \
    "base/wp-theme の Claude 指示に開発ベース境界がない"
fi

if (( failures > 0 )); then
  echo "structure check: $failures failure(s)" >&2
  exit 1
fi

echo "structure check: OK"
