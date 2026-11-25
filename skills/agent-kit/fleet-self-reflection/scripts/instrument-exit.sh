#!/bin/sh
# instrument-exit.sh — THE CONTRACT, in one place.
#
# WHY THIS FILE EXISTS. The same failure was found five times in five different cron wrappers in one pass:
#
#   memory-metrics.sh     printed "INSTRUMENT FAILED"        ->  exit 0
#   quota-ledger.sh       printed "INSTRUMENT FAILED"        ->  exit 0
#   cron-conformance.sh   printed "TOOL failure, not compliant" ->  exit 0
#   x402-trends.sh        printed "ABSENCE OF DATA"          ->  exit 0
#   lang-rule-check.py    could not read its input            ->  exit 0  ("can't read it" = "it passes")
#
# A monitor that prints a warning and exits 0 makes its warning the ONLY signal. These jobs deliver to
# `local`, so the warning lands in a file nobody reads, the cron health column reads "ok", and the
# instrument is blind while looking clean.
#
# THE CONTRACT — one meaning per code, for every instrument in the fleet:
#
#   0  CLEAN      the measurement ran and found nothing. Say NOTHING.
#   2  FINDINGS   the measurement ran and found something you must see. Print it, exit 0 to cron.
#   3  BLIND      the instrument could not measure. THIS IS NOT CLEAN and must never look clean.
#
# Usage (call it as the LAST statement of the wrapper):
#
#   . /opt/data/profiles/gentech/scripts/instrument-exit.sh
#   out="$(python3 /opt/data/scripts/thing.py 2>&1)"; rc=$?
#   instrument_report "THING" "$rc" "$out"
#
# ⚠️ WHAT THIS CANNOT DO: it cannot make a wrapper that swallows its failure observable. "Silent + exit 0"
# is identical whether the tool found nothing or never ran. Converting a silent wrapper to this contract is
# a CODE change (capture `rc`, then pass it here). A fault-injection harness can prove a wrapper SPEAKS
# about a fault; it can never prove the wrapper would NOTICE one. See `falsifiable-tests`.

instrument_report() {
  tag="$1"; rc="$2"; out="$3"
  case "$rc" in
    0)  return 0 ;;                                  # clean — silence is the correct output
    2)  [ -n "$out" ] && printf '%s\n' "$out"
        return 0 ;;                                  # findings are a SUCCESSFUL measurement
    3)  printf '%s — INSTRUMENT COULD NOT MEASURE  %s\n' "$tag" "$(date -u '+%Y-%m-%d %H:%MZ')"
        [ -n "$out" ] && printf '%s\n' "$out"
        printf 'This is a MEASUREMENT FAILURE, not a clean result. Do not read it as zero.\n'
        exit 3 ;;                                    # blind must be visible in cron health
    *)  printf '%s — INSTRUMENT FAILED (exit %s)  %s\n' "$tag" "$rc" "$(date -u '+%Y-%m-%d %H:%MZ')"
        [ -n "$out" ] && printf '%s\n' "$out"
        printf 'Unexpected exit status: treat as BLIND, not as clean.\n'
        exit 3 ;;
  esac
}
