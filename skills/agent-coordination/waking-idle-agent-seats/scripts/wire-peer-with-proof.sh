#!/usr/bin/env bash
# wire-peer-with-proof.sh — register a peer gateway and PROVE the lane before claiming it live.
#
# WHY: "peer added" is a config fact; "peer answers" is a delivery fact. A registered-but-dark peer
# is worse than no peer — every later status report inherits the false claim. This script will not
# print LIVE until a DM comes back with the expected token.
#
# ORDER (do not reorder): measure endpoint -> validate key material -> register -> prove -> record.
#
# USAGE
#   ./wire-peer-with-proof.sh <peer-name> <base-url> <keyfile>
#   ./wire-peer-with-proof.sh --check <base-url>          # measure only, touch nothing
#   ./wire-peer-with-proof.sh --remove <peer-name>
#
# KEY HANDLING: key comes from a FILE, mode 600, never argv (argv is visible in `ps`).
#
# STATUS OF THIS SCRIPT: the guard branches and the endpoint measurement are exercised; the
# register+DM happy path follows `hermes peer add` / `hermes peer dm` documented behaviour and has
# not yet been run end to end against a live peer. Treat the first real run as a test, and read the
# output rather than the exit code.
set -uo pipefail
N=${1:?peer name}; shift || true

check() { # $1 = base url
  local h c
  h=$(curl -s -o /dev/null -w '%{http_code}' -m 8 "$1/health" || echo 000)
  c=$(curl -s -o /dev/null -w '%{http_code}' -m 8 -X POST -H 'Content-Type: application/json' \
        -d '{"model":"probe","messages":[{"role":"user","content":"probe"}]}' \
        "$1/v1/chat/completions" || echo 000)
  printf '   /health -> %s | unkeyed POST /v1/chat/completions -> %s\n' "$h" "$c"
  [ "$h" = 200 ] || { echo "🔴 not healthy — do not register a peer against it" >&2; return 1; }
  case "$c" in
    401|403) echo "   ✅ up and demanding auth";;
    200)   echo "   ⚠️ answered WITHOUT a key — open endpoint, report it, do not use it";;
    *)     echo "   ⚠️ unexpected $c — investigate before wiring";;
  esac
}

case "$N" in
  --check)   check "${1:?base url}"; exit $? ;;
  --remove)  hermes peer remove "${1:?peer name}"; exit $? ;;
esac

URL=${1:?base url}; KEYFILE=${2:?key file (mode 600)}
[ -f "$KEYFILE" ] || { echo "🔴 key file not found: $KEYFILE" >&2; exit 1; }
P=$(stat -c '%a' "$KEYFILE"); case "$P" in 600|400) ;; *) echo "🔴 key file must be mode 600 (is $P)" >&2; exit 1;; esac
KEY=$(tr -d ' \t\r\n' < "$KEYFILE"); [ -n "$KEY" ] || { echo "🔴 key file empty" >&2; exit 1; }

check "$URL" || exit 1
hermes peer add "$N" --url "$URL" --key "$KEY" --note "wired $(date -u +%Y-%m-%dT%H:%MZ)" || exit 1
hermes peer list

REPLY=$(hermes peer dm "$N" "probe $(date -u +%Y-%m-%dT%H:%MZ): reply with the single word RECEIVED." 2>&1); rc=$?
printf '%s\n' "$REPLY"
if [ $rc -ne 0 ] || ! printf '%s' "$REPLY" | grep -qi received; then
  echo "🔴 NO PROOF — peer may be registered but DARK. Report it as dark, never as live." >&2
  exit 1
fi
echo "✅ lane proven — record the reply in the vault (a session log is not evidence anyone can audit)"
