#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hooks_path="$repo_root/.githooks"

if [[ ! -x "$hooks_path/pre-commit" || ! -x "$hooks_path/pre-push" ]]; then
  echo "FAIL: tracked public-safety hooks are missing or not executable." >&2
  exit 1
fi

install_for_repo() {
  local target="$1"
  local existing
  existing="$(git -C "$target" config --local --get core.hooksPath || true)"
  if [[ -n "$existing" && "$existing" != "$hooks_path" ]]; then
    echo "FAIL: refusing to replace existing core.hooksPath in $target: $existing" >&2
    return 1
  fi
  git -C "$target" config --local core.hooksPath "$hooks_path"
  echo "installed public-safety hooks: $target"
}

install_for_repo "$repo_root"
while IFS= read -r submodule_path; do
  [[ -n "$submodule_path" && -e "$repo_root/$submodule_path/.git" ]] || continue
  install_for_repo "$repo_root/$submodule_path"
done < <(git config --file .gitmodules --get-regexp path | awk '{print $2}')
