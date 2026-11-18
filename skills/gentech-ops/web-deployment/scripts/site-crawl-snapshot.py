#!/usr/bin/env python3
"""site-crawl-snapshot.py — take a verifiable full snapshot of a static site before any redeploy.

WHY: a Cloudflare Pages (or any direct-upload) deploy REPLACES the entire deployment. When the
project has no git source the live edge is the only copy, so redeploying "the page I fetched"
silently deletes every file the crawler missed. This builds the complete reachable set WITH
per-file hashes, so any loss is detectable BEFORE the deploy instead of after.

It also answers a question that decides the whole workflow: **how many files does this project
actually have?**
  * crawl returns ONE file, and every other path serves the same hash  -> single-page site with a
    catch-all; redeploying that one file into the existing project is safe.
  * crawl returns many files -> the set is partial (links are not a manifest); do not deploy into
    the existing project, ship a separate project on its own subdomain instead.

Rules:
  * same-origin only (never fetch third-party CDNs we do not control)
  * record path + sha256 + content-type + byte size for every fetched file
  * follow links in HTML (href/src/action), CSS (url()) and JS string literals that look like paths
  * NEVER write outside --out
  * exit non-zero if any discovered path fails to fetch — a partial snapshot is not a snapshot

Usage:
  python3 site-crawl-snapshot.py --site https://example.com --out DIR [--max-pages 200]
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "gentech-snapshot/1.0 (+pre-deploy backup)"}
# Media/large binaries are skipped: they cannot contain further links and blow up the snapshot.
SKIP_EXT = {".zip", ".mp4", ".mp3", ".wav", ".pdf", ".gz", ".tar"}


def fetch(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), r.headers.get("content-type", ""), r.status


def extract_paths(body: bytes, ctype: str, base: str):
    out = set()
    text = body.decode("utf-8", "ignore")
    if "html" in ctype:
        pats = [r'(?:href|src|action)\s*=\s*["\']([^"\']+)["\']']
    elif "css" in ctype:
        pats = [r'url\(\s*["\']?([^"\')]+)["\']?\s*\)']
    elif "javascript" in ctype:
        pats = [r'["\'](/[A-Za-z0-9_\-./]+\.(?:html|css|js|json|png|jpg|svg|webp|ico))["\']']
    else:
        return out
    host = urllib.parse.urlsplit(base).netloc
    for p in pats:
        for m in re.findall(p, text):
            u = urllib.parse.urljoin(base, m)
            sp = urllib.parse.urlsplit(u)
            if sp.scheme not in ("http", "https") or sp.netloc != host:
                continue
            if os.path.splitext(sp.path)[1].lower() in SKIP_EXT or sp.path.startswith("/cdn-cgi/"):
                continue
            out.add(urllib.parse.urlunsplit((sp.scheme, sp.netloc, sp.path, "", "")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=200)
    a = ap.parse_args()

    site = a.site.rstrip("/")
    os.makedirs(a.out, exist_ok=True)
    seen, queue, manifest, failures = set(), [site + "/"], [], []

    while queue and len(seen) < a.max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            body, ctype, status = fetch(url)
        except Exception as e:
            failures.append({"url": url, "error": repr(e)[:160]})
            continue
        path = urllib.parse.urlsplit(url).path or "/"
        if path.endswith("/"):
            path += "index.html"
        dest = os.path.join(a.out, path.lstrip("/"))
        os.makedirs(os.path.dirname(dest) or a.out, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(body)
        manifest.append({"url": url, "path": path, "bytes": len(body),
                         "sha256": hashlib.sha256(body).hexdigest(), "content_type": ctype})
        for nxt in extract_paths(body, ctype, url):
            if nxt not in seen:
                queue.append(nxt)

    with open(os.path.join(a.out, "_manifest.json"), "w") as f:
        json.dump({"site": site, "files": manifest, "failures": failures}, f, indent=1)

    hashes = {m["sha256"] for m in manifest}
    print(f"files: {len(manifest)} | distinct bodies: {len(hashes)} | "
          f"failures: {len(failures)} | bytes: {sum(m['bytes'] for m in manifest):,}")
    for m in manifest[:40]:
        print(f"  {m['bytes']:>8,}  {m['sha256'][:12]}  {m['path']}")

    if len(manifest) == 1:
        print("\n-> SINGLE-FILE SITE. Every path serves this one file; redeploying it into the existing\n"
              "   project is safe. Confirm with a fake path before trusting that conclusion.")
    elif len(hashes) < len(manifest):
        print("\n-> Some paths share a body hash: catch-all handler present. Treat the file set as\n"
              "   partial and prefer a separate Pages project over a redeploy.")

    if failures:
        print("\nFAILED:")
        for x in failures[:10]:
            print("  ", x["url"], x["error"])
        sys.exit(2)


if __name__ == "__main__":
    main()
