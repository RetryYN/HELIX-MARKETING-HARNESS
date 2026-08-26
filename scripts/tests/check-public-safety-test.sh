#!/usr/bin/env bash
set -euo pipefail

integration_root="$(git rev-parse --show-toplevel)"
guard="$integration_root/scripts/check-public-safety.sh"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

fixture="$tmp_dir/repo"
git init --quiet "$fixture"
git -C "$fixture" config user.name test
git -C "$fixture" config user.email test@example.invalid

printf 'baseline\n' >"$fixture/README.md"
git -C "$fixture" add README.md
git -C "$fixture" commit --quiet -m baseline

expect_pass() {
  local description="$1"
  if ! (cd "$fixture" && bash "$guard" --staged) >/dev/null 2>&1; then
    echo "FAIL: expected pass: $description" >&2
    exit 1
  fi
}

expect_fail() {
  local description="$1"
  if (cd "$fixture" && bash "$guard" --staged) >/dev/null 2>&1; then
    echo "FAIL: expected rejection: $description" >&2
    exit 1
  fi
}

printf 'safe public fixture\n' >"$fixture/safe.txt"
git -C "$fixture" add safe.txt
expect_pass "ordinary staged content"
git -C "$fixture" reset --quiet

printf 'pass%s = example-secret-value\n' 'word' >"$fixture/credential.txt"
git -C "$fixture" add credential.txt
expect_fail "credential-like assignment"
git -C "$fixture" reset --quiet

printf 'machine path is /%s/%s/private/project\n' 'home' 'example-user' >"$fixture/path.txt"
git -C "$fixture" add path.txt
expect_fail "personal absolute path"
git -C "$fixture" reset --quiet

mkdir -p "$fixture/docs/research"
printf 'sanitized evidence\n' >"$fixture/docs/research/report.md"
git -C "$fixture" add docs/research/report.md
expect_fail "research evidence without private mapping"
(
  cd "$fixture"
  PUBLIC_REDACTION_GUARD_RE='private-example-domain\.invalid' bash "$guard" --staged
) >/dev/null
git -C "$fixture" reset --quiet

child_source="$tmp_dir/child-source"
git init --quiet "$child_source"
git -C "$child_source" config user.name test
git -C "$child_source" config user.email test@example.invalid
printf 'safe child baseline\n' >"$child_source/README.md"
git -C "$child_source" add README.md
git -C "$child_source" commit --quiet -m baseline

git -C "$fixture" -c protocol.file.allow=always submodule add --quiet "$child_source" child
git -C "$fixture" commit --quiet -m 'add child baseline'
git -C "$fixture/child" config user.name test
git -C "$fixture/child" config user.email test@example.invalid
printf 'machine path is /%s/%s/private/child\n' 'Users' 'example-user' >"$fixture/child/path.txt"
git -C "$fixture/child" add path.txt
git -C "$fixture/child" commit --quiet -m 'unsafe child change'
git -C "$fixture" add child
expect_fail "unsafe content introduced by a submodule pin update"

echo "public safety tests: OK"
