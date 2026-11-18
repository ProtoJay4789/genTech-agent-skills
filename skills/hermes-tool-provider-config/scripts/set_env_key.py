#!/usr/bin/env python3
"""Set or replace KEY=VALUE in a profile .env, then PROVE the line landed.

    python3 set_env_key.py /opt/data/profiles/<profile>/.env ELEVENLABS_API_KEY sk_xxx

Pass the value as an ARGUMENT. Do NOT build a writer like this from an unquoted
shell heredoc -- `python3 - <<PY` lets the shell expand `$` inside the Python
source, so a regex containing `$'` is silently rewritten, the write never lands,
and the script still prints success. argv bypasses the shell's parser entirely.

The write is atomic (temp file + os.replace) so a crash cannot leave a truncated
.env, and the key is re-read from disk afterwards to assert exactly one line.
"""
import os
import sys
import tempfile


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    env_path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()

    prefix = key + "="
    out, replaced = [], False
    for line in lines:
        if line.startswith(prefix):
            out.append(prefix + value)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(prefix + value)

    directory = os.path.dirname(os.path.abspath(env_path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".env-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, env_path)
        os.chmod(env_path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    # Independent read of the file on disk -- never trust the write we just did.
    with open(env_path, "r", encoding="utf-8") as fh:
        hits = [ln for ln in fh.read().splitlines() if ln.startswith(prefix)]
    if len(hits) != 1:
        print(f"FAIL: expected exactly 1 '{key}=' line, found {len(hits)}")
        return 1

    print(f"OK: {key} set ({len(hits[0]) - len(prefix)} chars) in {env_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
