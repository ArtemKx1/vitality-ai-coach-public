#!/usr/bin/env bash
# check-secrets.sh — scan the working tree and git history for common secret patterns.
# Usage: ./scripts/check-secrets.sh
# Exits 1 if any match is found (so it can be used in CI).
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PATTERNS=(
  'rnd_[A-Za-z0-9]{20,}'          # Render API key
  'srv-[a-z0-9]{20,}'             # Render service id
  'sk-[A-Za-z0-9]{20,}'           # OpenAI-style API key
  'AIza[A-Za-z0-9_-]{30,}'        # Google API key
  'AKIA[A-Z0-9]{16}'              # AWS access key
  'ghp_[A-Za-z0-9]{30,}'          # GitHub PAT
  'eyJ[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'  # JWT (anon keys etc.)
  '-----BEGIN[ -](RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----'
)

EXCLUDES=(
  --glob '!*node_modules*'
  --glob '!frontend/dist/*'
  --glob '!mobile/dist/*'
  --glob '!*.pyc'
  --glob '!.git/*'
  --glob '!*.lock'
  --glob '!scripts/check-secrets.sh'
)

find_matches() {
  local target="$1"
  for p in "${PATTERNS[@]}"; do
    rg -l -i -n --hidden --no-messages "${EXCLUDES[@]}" -e "$p" "$target"
  done
}

failed=0

echo "Scanning working tree..."
hits="$(find_matches . | sort -u)"
if [ -n "$hits" ]; then
  echo "$hits"
  failed=1
fi

if [ "${GIT_SCAN:-1}" = "1" ] && command -v git >/dev/null 2>&1; then
  echo "Scanning git history..."
  for c in $(git rev-list --all 2>/dev/null); do
    ghits="$(for p in "${PATTERNS[@]}"; do git grep -l -i -E -e "$p" "$c" -- . 2>/dev/null; done | sort -u)"
    if [ -n "$ghits" ]; then
      while IFS= read -r f; do
        echo "GIT HISTORY ($c): $f"
      done <<< "$ghits"
      failed=1
    fi
  done
fi

if [ "$failed" = "1" ]; then
  echo ""
  echo "Potential secrets found. Review and remove them before publishing."
  exit 1
fi

echo "OK — no secrets found."
exit 0
