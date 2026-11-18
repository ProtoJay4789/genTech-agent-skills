# Shelf-merge command batch (CORE → your seat)

Set the two roots once, then run the blocks in order. Nothing here writes to CORE except the single
`cp -p` in step 2, which is the promote-up.

```bash
CORE=/opt/data/skills
SEAT=/opt/data/profiles/<seat>/skills
P=defi/defi            # one survivor at a time
```

## 1. Three-way diff (before touching anything)

```bash
printf 'mine-only: %s | core-only: %s\n' \
  "$(diff "$SEAT/$P/SKILL.md" "$CORE/$P/SKILL.md" | grep -c '^<')" \
  "$(diff "$SEAT/$P/SKILL.md" "$CORE/$P/SKILL.md" | grep -c '^>')"

# sections CORE lacks entirely (empty output = nothing of yours to promote)
comm -23 <(grep -o '^#\+ .*' "$SEAT/$P/SKILL.md" | sort -u) \
         <(grep -o '^#\+ .*' "$CORE/$P/SKILL.md" | sort -u)

# files your seat holds that CORE does not (this is where promote-up hides)
comm -23 <(cd "$SEAT/$P" && find . -type f | sort) \
         <(cd "$CORE/$P" && find . -type f | sort)
```

**A line diff showing only path strings and a trailing-newline delta is a stale copy, not a richer one** —
check whether CORE's rows already point at the corrected paths before "promoting" them.

## 2. Promote up (only if step 1 found a seat-only file)

```bash
# does CORE's SKILL.md cite a reference that is not there?
grep -o 'references/[A-Za-z0-9._/-]*\.md' "$CORE/$P/SKILL.md" | sort -u | while read -r r; do
  [ -f "$CORE/$P/$r" ] || echo "DANGLING in CORE: $r  (seat has it: $([ -f "$SEAT/$P/$r" ] && echo yes || echo no))"
done

cp -p "$SEAT/$P/references/x.md" "$CORE/$P/references/x.md"    # mtime preserved
```

## 3. Copy the survivor down (whole directory)

```bash
cp -a "$CORE/$P/." "$SEAT/$P/"       # rsync is NOT installed on these hosts
```

## 4. Delete an absorbed skill only after proving it is a duplicate

```bash
tar czf "$SEAT/../backups/skills-merge-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" -C "$SEAT" <dirs…>

diff "$SEAT/old-skill/SKILL.md" "$CORE/$P/references/old-skill/old-skill.md" | wc -l   # want 0
rm -rf "$SEAT/old-skill"
```

## 5. Trap assertion and index reconciliation

```bash
# a preserved body left named SKILL.md inside references/ gets re-indexed as a live skill
find "$CORE" "$SEAT" -path '*/references/*' -name SKILL.md | wc -l          # want 0

hermes -p <seat> skills list > /tmp/skl 2>&1; echo rc=$?                     # capture rc, never via a pipe
grep -icE 'absorbed-name-1|absorbed-name-2' /tmp/skl                         # want 0 rows

# disk vs index: the gap should equal the platform/toolset-gated set
find "$SEAT" -name SKILL.md | wc -l
grep -E 'enabled,' /tmp/skl | tail -1
```

## 6. Fingerprint loop (CORE moves while peers apply)

```bash
fp() { ( cd "$1" && find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum | cut -d' ' -f1 ); }
for i in 1 2 3; do
  a=$(fp "$CORE/$P")
  cp -a "$CORE/$P/." "$SEAT/$P/"
  b=$(fp "$CORE/$P")
  d=$(diff -r "$SEAT/$P" "$CORE/$P" | wc -l)
  echo "attempt $i: core-stable=$([ "$a" = "$b" ] && echo yes || echo NO) diff=$d"
  [ "$a" = "$b" ] && [ "$d" = "0" ] && break
  sleep 2
done
```

Quote the final fingerprint **with a timestamp**; it is the only way the next seat can tell whether CORE
moved again or your numbers are stale.
