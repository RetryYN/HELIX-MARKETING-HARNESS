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
require_text "CLAUDE.md" 'public-repository-safety\.md' \
  "統合層共通規律が公開リポジトリ安全規約を参照していない"
require_text "docs/governance/public-repository-safety.md" '全 submodule' \
  "公開リポジトリ安全規約の適用範囲が全 submodule になっていない"
require_text ".github/workflows/structure-check.yml" 'check-public-safety\.sh' \
  "統合層 CI が公開情報ガードを実行していない"
require_text "scripts/install-public-safety-hooks.sh" 'core\.hooksPath' \
  "公開情報ガードの Git hook installer がない"

for hook in .githooks/pre-commit .githooks/pre-push; do
  if [[ ! -x "$hook" ]]; then
    echo "FAIL: tracked Git hook が実行可能ではない ($hook)" >&2
    failures=$((failures + 1))
  fi
done

if [[ ! -x "scripts/check-public-safety.sh" ]] ||
   [[ ! -x "scripts/install-public-safety-hooks.sh" ]] ||
   [[ ! -x "scripts/tests/check-public-safety-test.sh" ]]; then
  echo "FAIL: 公開情報ガードまたはそのテストが実行可能ではない" >&2
  failures=$((failures + 1))
fi

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
