#!/usr/bin/env python3
"""
wire-profile-bot.py — point a profile at its own Telegram bot, safely.

Usage:  wire-profile-bot.py <profile> <token_file> <home_channel> <allowed_users_csv>
Example: wire-profile-bot.py arthur /opt/data/.bot-tokens/arthur.token <telegram-group-id> 7105876857,684274559

WHY THIS EXISTS — two failures it makes impossible:
  1. A Telegram bot token INLINE in a shell command trips the parser blocklist. The token is read from a
     mode-600 file and never re-typed.
  2. A bare-substring edit can match a COMMENTED template line (`# TELEGRAM_ALLOWED_USERS=` sits far above
     the live line in these .env files) and "succeed" while wiring nothing. Every edit is anchored to a
     real `^KEY=` line.

It also proves the write: the token is reported by sha256 fingerprint and length, never by value.
"""
import hashlib, os, re, sys


def setvar(txt, key, val):
    """Replace a live `KEY=...` line, or append it. Never touches a commented `# KEY=` line."""
    pat = re.compile(rf'^{re.escape(key)}=.*$', re.M)
    if pat.search(txt):
        return pat.sub(f'{key}={val}', txt, count=1)
    return txt.rstrip("\n") + f"\n{key}={val}\n"


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    profile, tokfile, home, allowed = sys.argv[1:5]
    tok = open(tokfile).read().strip()
    envp = f"/opt/data/profiles/{profile}/.env"
    if not os.path.isfile(envp):
        sys.exit(f"no .env at {envp}")
    txt = open(envp).read()
    before = len(txt)
    txt = setvar(txt, "TELEGRAM_BOT_TOKEN", tok)
    txt = setvar(txt, "TELEGRAM_HOME_CHANNEL", home)
    txt = setvar(txt, "TELEGRAM_ALLOWED_USERS", allowed)
    open(envp, "w").write(txt)
    os.chmod(envp, 0o600)
    print(f"  wired {profile}: {before} -> {len(txt)} bytes, mode 600")
    print(f"  token fingerprint: sha256:{hashlib.sha256(tok.encode()).hexdigest()[:12]} (length {len(tok)})")
    for line in open(envp):
        if re.match(r'^(TELEGRAM_HOME_CHANNEL|TELEGRAM_ALLOWED_USERS)=', line):
            print("  " + line.rstrip())


if __name__ == "__main__":
    main()
