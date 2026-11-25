#!/usr/bin/env python3
"""Read-only Telegram room membership probe (stdlib only).

Calls ONLY: getMe, getChat, getChatMemberCount, getChatAdministrators, getChatMember.
No write/admin method exists in this file - that is the point: an audit must not
change what it measures.

Never prints the bot token (any accidental echo is masked).

Usage:
  python3 room-membership-probe.py --chat <telegram-group-id> \
      --person 7105876857=jordan --person 8722596779=josephine

  # token comes from --env (default: $HERMES_HOME/.env, else --profile's .env)
  python3 room-membership-probe.py --profile /opt/data/profiles/<seat> \
      --chat <chat_id> --person <id>=<label>

Always probes two controls (the bot's own id and user_id=1) so the ambiguity of
PARTICIPANT_ID_INVALID is visible in the output instead of being guessed at.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def find_env(profile, env_arg):
    if env_arg:
        return env_arg
    if profile:
        return os.path.join(profile, ".env")
    home = os.environ.get("HERMES_HOME")
    if home and os.path.isfile(os.path.join(home, ".env")):
        return os.path.join(home, ".env")
    for cand in ("/opt/data/profiles/protojay/.env", os.path.expanduser("~/.hermes/.env")):
        if os.path.isfile(cand):
            return cand
    sys.exit("no .env found - pass --env or --profile")


def load_token(env_path):
    for line in open(env_path, encoding="utf-8", errors="replace"):
        m = re.match(r"^\s*TELEGRAM_BOT_TOKEN\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    sys.exit("TELEGRAM_BOT_TOKEN not found in %s" % env_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="append", required=True, help="chat id to probe (repeatable)")
    ap.add_argument("--person", action="append", default=[], help="user_id=label (repeatable)")
    ap.add_argument("--profile", help="profile dir containing .env")
    ap.add_argument("--env", help="explicit .env path")
    args = ap.parse_args()

    env_path = find_env(args.profile, args.env)
    tok = load_token(env_path)

    def call(method, **params):
        url = "https://api.telegram.org/bot%s/%s" % (tok, method)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                out = json.load(r)
        except urllib.error.HTTPError as e:
            try:
                out = json.load(e)
            except Exception:
                out = {"ok": False, "error_code": e.code, "description": str(e)}
        except Exception as e:
            out = {"ok": False, "description": "%s: %s" % (type(e).__name__, e)}
        return json.loads(json.dumps(out).replace(tok, "TOKEN_REDACTED"))

    people = []
    for spec in args.person:
        if "=" in spec:
            uid, label = spec.split("=", 1)
        else:
            uid, label = spec, spec
        people.append((label, uid))

    me = call("getMe")
    bot_id = None
    print("== getMe ==")
    if me.get("ok"):
        u = me["result"]
        bot_id = str(u.get("id"))
        print("  id=%s username=@%s name=%s  (token from %s)" % (
            bot_id, u.get("username"), u.get("first_name"), env_path))
    else:
        print("  FAILED:", me.get("error_code"), me.get("description"))

    for cid in args.chat:
        print("\n== chat %s ==" % cid)
        c = call("getChat", chat_id=cid)
        if not c.get("ok"):
            print("  getChat: NOT VISIBLE -> %s %s" % (c.get("error_code"), c.get("description")))
            print("  NOTE: 'chat not found' from a bot that is not a member says nothing about the room.")
            continue
        r = c["result"]
        print("  getChat OK: id=%s type=%s title=%r username=%s" % (
            r.get("id"), r.get("type"), r.get("title"), r.get("username")))
        n = call("getChatMemberCount", chat_id=cid)
        count = n.get("result") if n.get("ok") else None
        print("  getChatMemberCount: %s" % (count if n.get("ok") else "FAILED %s %s" % (
            n.get("error_code"), n.get("description"))))
        a = call("getChatAdministrators", chat_id=cid)
        admins = a.get("result", []) if a.get("ok") else []
        if a.get("ok"):
            print("  getChatAdministrators: %d admin(s)" % len(admins))
            for adm in admins:
                u = adm.get("user", {})
                print("    - id=%s status=%s name=%s%s" % (
                    u.get("id"), adm.get("status"), u.get("first_name"),
                    " @" + u["username"] if u.get("username") else ""))
            if count is not None:
                if count == len(admins):
                    print("    COMPLETENESS: count == admins -> every member is enumerated above")
                else:
                    print("    COMPLETENESS: count(%s) > admins(%d) -> roster NOT fully enumerated; "
                          "say which members you cannot list" % (count, len(admins)))
        else:
            print("  getChatAdministrators: FAILED", a.get("error_code"), a.get("description"))

        print("  -- per-person getChatMember --")
        for label, uid in people:
            m = call("getChatMember", chat_id=cid, user_id=uid)
            if m.get("ok"):
                print("    %-24s id=%-12s status=%s" % (label, uid, m["result"].get("status")))
            else:
                print("    %-24s id=%-12s UNRESOLVED (%s %s) -> UNKNOWN unless the controls differ"
                      % (label, uid, m.get("error_code"), m.get("description")))

        print("  -- controls (run these BEFORE interpreting anything above) --")
        if bot_id:
            known = call("getChatMember", chat_id=cid, user_id=bot_id)
            print("    control/known-member bot %s -> %s" % (bot_id, json.dumps(
                known.get("result") or {"error": known.get("description")})[:200]))
        ctl = call("getChatMember", chat_id=cid, user_id="1")
        print("    control/nonsense id 1 -> %s" % json.dumps(
            ctl.get("result") if ctl.get("ok") else
            {"error_code": ctl.get("error_code"), "description": ctl.get("description")})[:200])
        print("    If the nonsense id returns the SAME error as a colleague's id, that error cannot")
        print("    distinguish non-member from non-user: report UNKNOWN, not left/kicked/never.")

    print("\nNo write, admin, invite, restrict or ban method was called.")


if __name__ == "__main__":
    main()
