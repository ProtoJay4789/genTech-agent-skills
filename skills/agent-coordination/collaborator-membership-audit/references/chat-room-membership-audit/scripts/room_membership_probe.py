#!/usr/bin/env python3
"""Read-only chat-room membership probe (Telegram Bot API).

Usage:
  python3 room_membership_probe.py --chat-id <telegram-group-id> \
      --registry /path/to/mapping.json [--env /path/to/profile/.env]

Prints the room identity, member count, admin list, one line per registry person, and the count
reconciliation. Calls ONLY getMe / getChat / getChatMemberCount / getChatAdministrators / getChatMember.
The token is read from .env and never printed.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

PRESENT = {"creator", "administrator", "member"}


def load_token(env_path):
    try:
        txt = open(env_path, encoding="utf-8").read()
    except OSError as exc:
        sys.exit(f"cannot read {env_path}: {exc}")
    m = re.search(r"^TELEGRAM_BOT_TOKEN\s*=\s*(.+)$", txt, re.M)
    if not m:
        sys.exit(f"TELEGRAM_BOT_TOKEN not found in {env_path}")
    return m.group(1).strip().strip('"').strip("'")


def api(token, method, **params):
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=25) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode())
    except Exception as exc:  # network, DNS, timeout
        return {"ok": False, "description": f"{type(exc).__name__}: {exc}"}


def to_membership(payload):
    """(membership, raw) — never guess; anything unclassified is UNKNOWN."""
    if not payload.get("ok"):
        desc = payload.get("description", "") or "call failed"
        if "member not found" in desc:
            return "never", desc
        return "UNKNOWN", desc
    status = payload["result"].get("status", "")
    if status in PRESENT:
        return "present", status
    if status in ("left", "kicked"):
        return status, status
    return "UNKNOWN", status or "no status field"


def authority_of(entry):
    perms = entry.get("permissions") or []
    if "all" in perms:
        return "act"
    if "recommend" in perms:
        return "recommend"
    return "UNKNOWN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--env", default=os.path.expanduser("~/.hermes/.env"))
    ap.add_argument("--registry", help="mapping.json holding collaborators{name:{telegram_id,...}}")
    args = ap.parse_args()

    token = load_token(args.env)

    me = api(token, "getMe")
    if me.get("ok"):
        r = me["result"]
        print(f"bot: {r.get('id')} @{r.get('username')} ({r.get('first_name')})")
    else:
        print(f"getMe failed: {me.get('description')}")

    chat = api(token, "getChat", chat_id=args.chat_id)
    if not chat.get("ok"):
        sys.exit(
            f"getChat failed: {chat.get('description')}\n"
            "-> wrong chat id, or THIS bot is not a member of that room."
        )
    c = chat["result"]
    print(f"room: {c.get('title')} | type={c.get('type')} | id={c.get('id')} | username={c.get('username')}")

    admins_resp = api(token, "getChatAdministrators", chat_id=args.chat_id)
    admin_ids, bot_count = set(), 0
    if admins_resp.get("ok"):
        for adm in admins_resp["result"]:
            u = adm.get("user", {})
            admin_ids.add(u.get("id"))
            if u.get("is_bot"):
                bot_count += 1
            print(
                f"  admin: {adm.get('status'):14s} {u.get('id')} "
                f"{u.get('first_name')} @{u.get('username')} bot={u.get('is_bot')}"
            )
    else:
        print(f"getChatAdministrators failed: {admins_resp.get('description')}")

    people = []
    if args.registry and os.path.isfile(args.registry):
        data = json.load(open(args.registry, encoding="utf-8"))
        for name, entry in (data.get("collaborators") or {}).items():
            if entry.get("telegram_id"):
                people.append((name, str(entry["telegram_id"]), entry))
    else:
        print("no --registry given: cannot enumerate people (getChatMember needs known ids)")

    present = 0
    for name, tid, entry in people:
        resp = api(token, "getChatMember", chat_id=args.chat_id, user_id=tid)
        membership, raw = to_membership(resp)
        if membership == "present":
            present += 1
        note = ""
        reg_status = entry.get("status", "<none>")
        if reg_status == "active" and membership != "present":
            note = "  <-- REGISTRY SAYS active"
        if membership == "present" and tid in admin_ids:
            note += "  (admin)"
        print(
            f"{name:14s} {tid:14s} membership={membership:8s} raw={raw!r} "
            f"registry_status={reg_status} scope={','.join(entry.get('topics') or [])} "
            f"authority={authority_of(entry)}{note}"
        )

    count = api(token, "getChatMemberCount", chat_id=args.chat_id)
    if count.get("ok"):
        total = count["result"]
        unlisted = total - bot_count - present
        print(
            f"RECONCILE: count={total} - bot_accounts={bot_count} - enumerated_present={present} "
            f"= {unlisted} unaccounted"
        )
        if unlisted == 0:
            print("  -> roster reconciles: no unlisted human member")
        else:
            print("  -> NOT reconciled: someone in the room is not in the registry (or a bot was missed)")
    else:
        print(f"getChatMemberCount failed: {count.get('description')}")


if __name__ == "__main__":
    main()
