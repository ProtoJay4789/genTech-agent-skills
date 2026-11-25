#!/bin/sh
# dept-reflect.sh — cron wrapper for dept-reflect.py. Copy to profiles/<seat>/scripts/ on every seat.
#
# Two bugs this file exists to prevent, both measured:
#   1 · A wrapper that hardcodes ONE seat's .py path makes every seat grade that seat. Four seats, one subject.
#       Resolve the seat from THIS file's own location, at the last layer before execution.
#   2 · dept-reflect.py exits 2 for "measured, found something". A no_agent cron job records any non-zero
#       exit as last_status: error, so every run that found anything looked like a crash. The cron health
#       signal must mean "the measurement ran", never "the department has work to do".
#
# The wrapper therefore swallows 2 and keeps 3 (could not measure) loud. Because it swallows the code,
# dept-reflect.py MUST print its findings to stdout before returning 2 — otherwise this wrapper would build
# a monitor that cannot go red.
set -u

SEAT=$(basename "$(dirname "$(dirname "$0")")")
SCRIPT="/opt/data/profiles/$SEAT/scripts/dept-reflect.py"

if [ ! -f "$SCRIPT" ]; then
  echo "dept-reflect: cannot measure — no $SCRIPT" >&2
  exit 3
fi

OUT=$(python3 "$SCRIPT" "$@" 2>&1)
RC=$?
printf '%s\n' "$OUT"

[ "$RC" -eq 2 ] && exit 0
[ "$RC" -eq 3 ] && exit 3
exit "$RC"
