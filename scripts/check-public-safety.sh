#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

usage() {
  echo "usage: $0 --staged | --base-ref <git-ref>" >&2
  exit 2
}

mode=""
base_ref=""
case "${1:-}" in
  --staged)
    mode="staged"
    [[ $# -eq 1 ]] || usage
    ;;
  --base-ref)
    mode="range"
    base_ref="${2:-}"
    [[ $# -eq 2 && -n "$base_ref" ]] || usage
    git rev-parse --verify "${base_ref}^{commit}" >/dev/null
    ;;
  *) usage ;;
esac

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
records="$tmp_dir/added-lines.tsv"
: >"$records"

append_diff() {
  local repo="$1"
  local prefix="$2"
  shift 2

  git -C "$repo" diff --no-ext-diff --unified=0 "$@" -- \
    ':(exclude)scripts/check-public-safety.sh' |
    awk -v prefix="$prefix" '
      /^\+\+\+ b\// { file = substr($0, 7); next }
      /^\+\+\+ \/dev\/null/ { file = ""; next }
      /^\+[^+]/ && file != "" {
        line = substr($0, 2)
        gsub(/\t/, "    ", line)
        print prefix file "\t" line
      }
    ' >>"$records"
}

if [[ "$mode" == "staged" ]]; then
  append_diff . "" --cached
  raw_args=(--cached --raw --no-abbrev)
else
  append_diff . "" "$base_ref" HEAD
  raw_args=(--raw --no-abbrev "$base_ref" HEAD)
fi

# A gitlink diff contains only the pointer at the integration layer. Inspect the
# actual old..new commit range inside every changed, initialized submodule.
while IFS=$'\t' read -r path old_sha new_sha; do
  [[ -n "$path" && -d "$path/.git" || -f "$path/.git" ]] || {
    echo "FAIL: changed submodule is not initialized: $path" >&2
    exit 1
  }
  for sha in "$old_sha" "$new_sha"; do
    git -C "$path" cat-file -e "${sha}^{commit}" 2>/dev/null || {
      echo "FAIL: submodule commit unavailable for inspection: $path@$sha" >&2
      exit 1
    }
  done
  append_diff "$path" "$path/" "$old_sha" "$new_sha"
done < <(
  git diff "${raw_args[@]}" | awk '
    $1 ~ /^:160000/ || $2 == "160000" {
      old = $3; new = $4; path = $6
      if (path != "") print path "\t" old "\t" new
    }
  '
)

failures=0
check_pattern() {
  local description="$1"
  local pattern="$2"
  local flags="${3:--E}"
  local found="$tmp_dir/found"
  if grep $flags -n -- "$pattern" "$records" >"$found"; then
    echo "FAIL: $description" >&2
    sed 's/^/  /' "$found" >&2
    failures=$((failures + 1))
  fi
}

# Split well-known token prefixes so this guard does not flag its own source.
check_pattern "private key material" 'BEGIN [A-Z0-9 ]*PRIVATE KEY' '-E'
check_pattern "well-known access token format" '(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})' '-E'
check_pattern "credential-like assignment" '(password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[[:punct:]]?[[:space:]]*[A-Za-z0-9+/=_-]{12,}' '-Ei'
check_pattern "personal absolute filesystem path" '(/home/[^/<[:space:]]+/|/Users/[^/<[:space:]]+/|[A-Za-z]:[/\\]Users[/\\][^/\\<[:space:]]+[/\\])' '-E'
check_pattern "affiliate or click-tracking URL" 'https?://[^[:space:]]*(a8mat=|/svt/|/0\.gif\?)' '-Ei'

custom_regex="${PUBLIC_REDACTION_GUARD_RE:-}"
local_regex_file="${PUBLIC_SAFETY_REGEX_FILE:-.public-safety.local.regex}"
if [[ -f "$local_regex_file" ]]; then
  file_regex="$(grep -Ev '^[[:space:]]*(#|$)' "$local_regex_file" | paste -sd '|' - || true)"
  if [[ -n "$file_regex" ]]; then
    custom_regex="${custom_regex:+${custom_regex}|}${file_regex}"
  fi
fi
if [[ -n "$custom_regex" ]]; then
  check_pattern "private name/domain mapping" "$custom_regex" '-Ei'
fi

if cut -f1 "$records" | grep -Eq '(^|/)(research|evidence|artifacts?/poc|raw|captures?)(/|$)' &&
   [[ -z "$custom_regex" ]]; then
  echo "FAIL: research/evidence/PoC content changed without a private redaction mapping." >&2
  echo "  Set PUBLIC_REDACTION_GUARD_RE or create .public-safety.local.regex." >&2
  failures=$((failures + 1))
fi

if (( failures > 0 )); then
  echo "public safety check: $failures failure(s)" >&2
  exit 1
fi

echo "public safety check: OK ($(wc -l <"$records" | tr -d ' ') added line(s) inspected)"
