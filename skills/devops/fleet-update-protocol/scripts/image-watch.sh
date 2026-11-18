#!/usr/bin/env bash
# image-watch.sh — has a newer Hermes image been published?
# Silent unless the image CHANGED. Reads the IMAGE's install stamp (the only honest version source).
#
# Exit 0  = no change  -> say nothing.
# Exit 10 = CHANGE     -> report to the coordinator.
# Exit 2  = probe failed (pull failed / stamp unreadable) -> report the failure, do NOT claim a change.
#
# Run as a no-agent cron or a host action — it needs host Docker access and cannot run from inside a seat.
set -uo pipefail

IMAGE="${HERMES_IMAGE:-ghcr.io/hostinger/hvps-hermes-agent:latest}"
STATE="${HERMES_IMAGE_WATCH_STATE:-/opt/data/cache/image-watch.json}"

pull=$(timeout 120 docker pull "$IMAGE" 2>&1) || { echo "PULL FAILED: $pull"; exit 2; }

# The naive `docker run --rm IMAGE --version` starts a gateway (s6 entrypoint eats the flag).
# Read the build stamp instead — no init, no mount, no service.
stamp=$(timeout 60 docker run --rm --entrypoint /bin/cat "$IMAGE" /opt/hermes/install-stamp.json 2>/dev/null)
[ -z "$stamp" ] && { echo "STAMP UNREADABLE from $IMAGE"; exit 2; }

ver=$(printf '%s' "$stamp"    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("baseVersion",""))')
commit=$(printf '%s' "$stamp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("commit",""))')
[ -z "$ver" ] && { echo "VERSION PARSE FAILED"; exit 2; }

mkdir -p "$(dirname "$STATE")"
if [ -f "$STATE" ]; then
  old=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("commit",""))' "$STATE" 2>/dev/null || echo "")
  [ "$old" = "$commit" ] && exit 0   # unchanged -> silence
fi

python3 - "$STATE" "$ver" "$commit" <<'PY'
import json, sys, pathlib, datetime
s, v, c = sys.argv[1], sys.argv[2], sys.argv[3]
pathlib.Path(s).write_text(json.dumps(
    {"baseVersion": v, "commit": c, "checkedAt": datetime.datetime.utcnow().isoformat() + "Z"}, indent=2))
PY

echo "NEW HERMES IMAGE PUBLISHED"
echo "  image:   $IMAGE"
echo "  version: $ver"
echo "  commit:  ${commit:0:12}"
echo "  -> run the container-edition update protocol before recreating anything"
exit 10
