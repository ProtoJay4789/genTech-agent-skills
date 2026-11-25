# Recipe — applying a core consolidation to one seat

Companion to SKILL.md. Replace `<CORE>` with the shared core path, `<SEAT>` with the seat's `skills/` dir and
`<skill>` with a survivor skill's relative path (e.g. `security/key-custody-and-recovery`).

## 1. Measure direction per file (before touching anything)

```bash
C=<CORE>; S=<SEAT>
for p in <survivor skill dirs>; do
  echo "=== $p"
  echo "CORE files: $(find $C/$p -type f | wc -l) | SEAT files: $(find $S/$p -type f | wc -l)"
  echo "-- on my seat, not in CORE (promote-up candidates):"
  comm -23 <(cd $S/$p && find . -type f | sort) <(cd $C/$p && find . -type f | sort)
  echo "-- headings only I have:"
  comm -23 <(grep -o '^#\+ .*' $S/$p/SKILL.md | sort -u) <(grep -o '^#\+ .*' $C/$p/SKILL.md | sort -u)
done
```

## 2. Find the dangling references that mark a missing core file

```bash
grep -oE 'references/[A-Za-z0-9._/-]+\.md' "$C/<skill>/SKILL.md" | sort -u | while read -r r; do
  [ -f "$C/<skill>/$r" ] || echo "DANGLING in CORE: $r"
done
```

Every hit is a file the core cites and does not hold. Search all seats for the basename before concluding it is
gone for good.

## 3. Promote up (never overwrite)

```bash
cp -p "$S/<skill>/references/<file>.md" "$C/<skill>/references/<file>.md"
md5sum "$S/<skill>/references/<file>.md" "$C/<skill>/references/<file>.md"    # must match
```

## 4. Back up and delete the absorbed dirs (proof first)

```bash
B=<SEAT>/../backups/skills-merge-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$B"
tar czf "$B/before.tar.gz" -C "$S" <survivors> <absorbed dirs>

# per absorbed dir: require 0 diff lines against the preserved body
for pair in "defi-lp-monitoring:defi/defi/references/defi-lp-monitoring/defi-lp-monitoring.md" ; do
  d=${pair%%:*}; body=${pair#*:}
  echo "$d -> $(diff "$S/$d/SKILL.md" "$S/$body" | grep -c '^')"
done
```

Only after every pair reports 0, `rm -rf "$S/<absorbed dir>"`.

## 5. Copy down until the core is stable and the trees match

```bash
fp() { ( cd "$1" && find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum | cut -d' ' -f1 ); }
for attempt in 1 2 3; do
  c1=$(fp "$C/<skill>")
  cp -a "$C/<skill>/." "$S/<skill>/"
  c2=$(fp "$C/<skill>")
  d=$(diff -r "$S/<skill>" "$C/<skill>" | wc -l)
  echo "attempt $attempt: core-stable=$([ "$c1" = "$c2" ] && echo yes || echo NO) diff=$d"
  [ "$c1" = "$c2" ] && [ "$d" = 0 ] && break
  sleep 2
done
echo "frozen fingerprint: $(fp "$C/<skill>")"
```

## 6. Verify the whole apply

```bash
# 6a. re-index trap, BOTH trees — want 0
find "$S" "$C" -path '*/references/*' -name SKILL.md | wc -l

# 6b. absorbed dirs really gone
for d in <absorbed dirs>; do [ -d "$S/$d" ] && echo "STILL THERE: $d"; done

# 6c. index: -N absorbed, +M new, no absorbed row, survivors present
hermes -p <seat> skills list > /tmp/skl.txt 2>&1
grep -E 'enabled,' /tmp/skl.txt | tail -1
grep -icE '<absorbed-name-1>|<absorbed-name-2>' /tmp/skl.txt      # want 0

# 6d. frontmatter of every edited SKILL.md still parses
python3 - <<'PY'
import yaml, pathlib
for f in <edited SKILL.md paths>:
    t = pathlib.Path(f).read_text(errors='replace')
    end = t.find('\n---', 3)
    print('OK', f, yaml.safe_load(t[3:end]).get('name'))
PY
```

## 7. Close a disk-vs-index gap before filing it

`hermes skills list` rows can be fewer than `find <SEAT> -name SKILL.md | wc -l`:

- `platforms: [macos]` → skipped on a Linux host (`skill_view` returns `unsupported`);
- `requires_toolsets: [kanban]` → loads `available` via `skill_view`, may be absent from the table.

Confirm each candidate with `skill_view(name)`, then check that on-disk − rows = gated count.

## 8. ACK checklist

- per survivor: diff verdict, including "nothing unique to me" with the measurement that proves it;
- promote-ups: path, byte count, md5, and why (a dangling core reference is the usual reason);
- deletions: each with the byte-identity proof, plus backup path and size;
- index before → after, trap count, and the timestamp the numbers describe;
- pointers repointed (count + files) and each deliberate leave with its reason;
- core moves observed mid-apply, with the peer whose ACK explains them;
- gaps with no copy anywhere, named explicitly rather than filled with a guess.
