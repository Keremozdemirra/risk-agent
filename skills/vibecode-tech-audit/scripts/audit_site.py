#!/usr/bin/env python3
"""Automated checks for the vibecode technical audit (the 20 giveaways).

Works against a live URL or a local build directory. Uses only the standard
library so it runs anywhere.

Usage:
    python3 audit_site.py https://example.com
    python3 audit_site.py ./dist
    python3 audit_site.py https://example.com --json

Exit code 1 if any FAIL-level finding, else 0.

What this cannot do, and must be done by hand afterward:
  - console errors (item 19): needs a real browser — use Playwright
  - whether structured data is *accurate* (item 8)
  - whether the bundle size is acceptable for this audience (item 20)
"""

import argparse
import glob
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (compatible; vibecode-tech-audit/1.0)"
TIMEOUT = 20

results = []  # (level, item_no, title, detail)
LEVELS = {"FAIL": 0, "WARN": 1, "PASS": 2, "INFO": 3, "SKIP": 4}


def rec(level, item, title, detail=""):
    results.append((level, item, title, detail))


# ---------------------------------------------------------------- fetching

def fetch(url, method="GET"):
    """Returns (status, headers_dict, body_bytes). Status 0 on transport error."""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read() if method == "GET" else b""
            if r.headers.get("Content-Encoding") == "gzip":
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, dict(e.headers or {}), body
    except Exception as e:
        return 0, {"_error": str(e)}, b""


# ---------------------------------------------------------------- parsing

class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self.metas = []          # list of (name/property, content)
        self.links = []          # list of (rel, href, extra)
        self.html_lang = None
        self.h_levels = []       # ordered heading levels
        self.imgs = []           # list of alt value or None
        self.jsonld = []
        self._in_ld = False
        self._ld_buf = []
        self.scripts = []        # src values
        self.body_text_len = 0
        self._in_body = False
        self._skip_text = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property") or a.get("http-equiv")
            if key:
                self.metas.append((key.lower(), a.get("content", "")))
        elif tag == "link":
            self.links.append((a.get("rel", "").lower(), a.get("href", ""), a))
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h_levels.append(int(tag[1]))
        elif tag == "img":
            self.imgs.append(a.get("alt") if "alt" in a else None)
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_ld, self._ld_buf = True, []
            if a.get("src"):
                self.scripts.append(a["src"])
            self._skip_text += 1
        elif tag == "style":
            self._skip_text += 1
        elif tag == "body":
            self._in_body = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            if self._in_ld:
                self.jsonld.append("".join(self._ld_buf))
                self._in_ld = False
            self._skip_text = max(0, self._skip_text - 1)
        elif tag == "style":
            self._skip_text = max(0, self._skip_text - 1)

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data.strip()
        if self._in_ld:
            self._ld_buf.append(data)
        if self._in_body and not self._skip_text:
            self.body_text_len += len(data.strip())

    def meta(self, key):
        for k, v in self.metas:
            if k == key.lower():
                return v
        return None

    def link(self, rel):
        for r, href, _ in self.links:
            if rel in r.split():
                return href
        return None


# ---------------------------------------------------------------- checks

DEFAULT_TITLES = re.compile(
    r"^(vite|vite \+ react|vite app|react app|next\.?js|create next app|"
    r"nuxt app|astro|svelte ?kit|my app|untitled|document|home|app)$", re.I)


def check_html(head, html_text, base_url):
    # 4. leftover defaults
    t = (head.title or "").strip()
    if not t:
        rec("FAIL", 5, "No <title>", "search results and tabs have nothing to show")
    elif DEFAULT_TITLES.match(t):
        rec("FAIL", 4, "Default template title", f"title is {t!r}")
    else:
        rec("PASS", 5, "Title present", t[:80])
        if len(t) > 65:
            rec("WARN", 5, "Title likely truncated in search results", f"{len(t)} chars")

    fav = head.link("icon") or head.link("shortcut")
    if fav and re.search(r"(vite|astro|next|nuxt|svelte|react)\.svg$", fav, re.I):
        rec("FAIL", 4, "Default framework favicon", fav)

    # 6. meta description
    desc = head.meta("description")
    if not desc:
        rec("FAIL", 6, "No meta description",
            "Google will invent a snippet, often from your nav")
    elif len(desc) < 50:
        rec("WARN", 6, "Meta description very short", f"{len(desc)} chars")
    else:
        rec("PASS", 6, "Meta description present", f"{len(desc)} chars")

    # 7. open graph
    og_img = head.meta("og:image")
    missing_og = [k for k in ("og:title", "og:description", "og:image", "og:url")
                  if not head.meta(k)]
    if not og_img:
        rec("FAIL", 7, "No og:image",
            "links share as a blank grey box on WhatsApp, X, Slack, LinkedIn")
    else:
        if not og_img.startswith(("http://", "https://")):
            rec("FAIL", 7, "og:image is a relative URL",
                f"{og_img} — unfurlers do not resolve relative paths")
        else:
            st, hdrs, _ = fetch(og_img, "HEAD")
            ctype = hdrs.get("Content-Type", "")
            if st != 200:
                rec("FAIL", 7, "og:image does not resolve", f"{st} {og_img}")
            elif "svg" in ctype:
                rec("WARN", 7, "og:image is SVG", "poorly supported by unfurlers")
            else:
                rec("PASS", 7, "og:image resolves", f"{ctype} {og_img}")
    if missing_og and og_img:
        rec("WARN", 7, "Incomplete Open Graph tags", "missing " + ", ".join(missing_og))
    if not head.meta("twitter:card"):
        rec("WARN", 7, "No twitter:card", "use summary_large_image")

    # 8. structured data
    if not head.jsonld:
        rec("WARN", 8, "No JSON-LD structured data", "no eligibility for rich results")
    else:
        types = []
        for blob in head.jsonld:
            try:
                data = json.loads(blob)
                for obj in (data if isinstance(data, list) else [data]):
                    if isinstance(obj, dict):
                        types.append(str(obj.get("@type", "?")))
            except ValueError:
                rec("FAIL", 8, "JSON-LD is invalid JSON", blob.strip()[:80])
        if types:
            rec("PASS", 8, "Structured data present", ", ".join(types)
                + " — verify it matches visible content and contains no invented ratings")

    # 9 / 10. headings
    h1s = [l for l in head.h_levels if l == 1]
    if not h1s:
        rec("FAIL", 10, "No <h1> on the page",
            "the hero headline is probably a styled div")
    elif len(h1s) > 1:
        rec("FAIL", 9, f"{len(h1s)} <h1> elements", "flattens the heading hierarchy")
    else:
        rec("PASS", 9, "Exactly one <h1>")
    prev = 0
    for lvl in head.h_levels:
        if prev and lvl > prev + 1:
            rec("WARN", 9, "Heading level skipped", f"h{prev} followed by h{lvl}")
            break
        prev = lvl

    # 11. canonical
    canon = head.link("canonical")
    if not canon:
        rec("FAIL", 11, "No canonical tag", "www/http/trailing-slash variants compete")
    elif not canon.startswith(("http://", "https://")):
        rec("WARN", 11, "Canonical is relative", canon)
    else:
        rec("PASS", 11, "Canonical present", canon)

    # 14. favicon declared
    if not fav:
        rec("WARN", 14, "No favicon declared in HTML", "generic globe in tab and bookmarks")
    if not any("apple-touch-icon" in r for r, _, _ in head.links):
        rec("WARN", 14, "No apple-touch-icon", "180x180 png")

    # 16. lang
    if not head.html_lang:
        rec("FAIL", 16, "No lang attribute on <html>",
            "screen readers guess pronunciation; WCAG failure")
    else:
        rec("PASS", 16, "html lang set", head.html_lang)

    # 17. alt text
    total = len(head.imgs)
    if total:
        missing = sum(1 for a in head.imgs if a is None)
        lazy = sum(1 for a in head.imgs if a and
                   re.fullmatch(r"(image|img|photo|picture|icon|logo|screenshot|"
                                r"[\w-]+\.(png|jpe?g|svg|webp))", a.strip(), re.I))
        if missing:
            rec("FAIL", 17, f"{missing}/{total} images have no alt attribute")
        if lazy:
            rec("WARN", 17, f"{lazy}/{total} images have placeholder alt text")
        if not missing and not lazy:
            rec("PASS", 17, f"All {total} images have alt text")

    # 2. rendered vs empty
    shell = re.search(r'<div\s+id=["\'](?:root|app|__next|__nuxt)["\']\s*>\s*</div>',
                      html_text, re.I)
    if shell or head.body_text_len < 200:
        rec("FAIL", 2, "HTML arrives essentially empty",
            f"~{head.body_text_len} chars of text without JS"
            + (" and an empty mount div" if shell else "")
            + " — crawlers and link unfurlers see nothing")
    elif head.body_text_len < 600:
        rec("WARN", 2, "Very little text in the server HTML",
            f"~{head.body_text_len} chars — fine for a genuinely short page, but "
            "compare against what the browser renders to rule out client-side rendering")
    else:
        rec("PASS", 2, "Content present in server HTML",
            f"~{head.body_text_len} chars of text")

    # 13. meta robots noindex
    robots_meta = head.meta("robots") or ""
    if "noindex" in robots_meta.lower():
        rec("FAIL", 13, "meta robots contains noindex",
            f"{robots_meta!r} — the page is excluded from search entirely")

    # 18. source maps referenced
    if re.search(r"sourceMappingURL", html_text):
        rec("WARN", 18, "sourceMappingURL referenced in HTML")


def check_live(url):
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # 1. default platform subdomain
    host = parsed.netloc.lower()
    if re.match(r"(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?$", host):
        rec("INFO", 1, "Local server — domain check not applicable", host)
    elif re.search(r"\.(vercel\.app|netlify\.app|pages\.dev|github\.io|"
                   r"onrender\.com|railway\.app|fly\.dev|surge\.sh|web\.app|"
                   r"firebaseapp\.com|replit\.app|streamlit\.app)$", host):
        rec("FAIL", 1, "Default platform subdomain", host +
            " — reads as a hobby deploy; a custom domain is the cheapest trust win")
    else:
        rec("PASS", 1, "Custom domain", host)

    status, hdrs, body = fetch(url)
    if status == 0:
        rec("FAIL", 0, "Could not fetch the URL", hdrs.get("_error", ""))
        return
    if status >= 400:
        rec("FAIL", 0, f"Homepage returned {status}")
        return

    if hdrs.get("X-Robots-Tag", "").lower().find("noindex") >= 0:
        rec("FAIL", 13, "X-Robots-Tag: noindex response header",
            hdrs["X-Robots-Tag"])

    html_text = body.decode("utf-8", "ignore")
    head = Head()
    head.feed(html_text)
    check_html(head, html_text, url)

    # 10b. http -> https
    if parsed.scheme == "https":
        st, h2, _ = fetch("http://" + parsed.netloc + (parsed.path or "/"), "HEAD")
        if st in (301, 302, 307, 308):
            rec("PASS", 0, "HTTP redirects to HTTPS", str(st))
        elif st == 200:
            rec("WARN", 0, "HTTP serves 200 without redirecting to HTTPS")

    # 3. 404 handling
    st, _, b404 = fetch(urljoin(origin, "/definitely-not-a-real-page-9f8a7b6c"))
    if st == 404:
        rec("PASS", 3, "Unknown URL returns 404")
        if len(b404) < 200:
            rec("WARN", 3, "404 response is nearly empty", "no way back for the visitor")
    elif st == 200:
        rec("FAIL", 3, "Unknown URL returns 200 (soft 404)",
            "crawlers will index infinite junk URLs as real pages")
    else:
        rec("WARN", 3, f"Unknown URL returned {st}", "expected 404")

    # 13. robots.txt
    st, _, rb = fetch(urljoin(origin, "/robots.txt"))
    if st != 200 or not rb:
        rec("WARN", 13, "No robots.txt")
    else:
        txt = rb.decode("utf-8", "ignore")
        if re.search(r"^\s*User-agent:\s*\*\s*$\s*^\s*Disallow:\s*/\s*$", txt,
                     re.M | re.I):
            rec("FAIL", 13, "robots.txt blocks the entire site",
                "Disallow: / for User-agent: * — nothing will be indexed")
        blocked = [b for b in ("GPTBot", "ClaudeBot", "Claude-Web", "PerplexityBot",
                               "CCBot", "Google-Extended", "anthropic-ai")
                   if re.search(rf"User-agent:\s*{b}", txt, re.I)
                   and re.search(rf"User-agent:\s*{b}[\s\S]{{0,120}}?Disallow:\s*/",
                                 txt, re.I)]
        if blocked:
            rec("WARN", 13, "robots.txt blocks AI crawlers",
                ", ".join(blocked) + " — deliberate, or copied from a template?")
        if "sitemap:" not in txt.lower():
            rec("WARN", 15, "robots.txt does not reference a sitemap")
        if st == 200 and not blocked:
            rec("PASS", 13, "robots.txt present")

    # 15. sitemap
    st, h, sb = fetch(urljoin(origin, "/sitemap.xml"))
    body_head = sb[:400].decode("utf-8", "ignore").lower()
    if st != 200:
        rec("FAIL", 15, "No sitemap.xml", f"returned {st}")
    elif "<urlset" not in body_head and "<sitemapindex" not in body_head:
        rec("FAIL", 15, "sitemap.xml is not a sitemap",
            "the SPA fallback is being served with a 200")
    else:
        n = sb.count(b"<loc>")
        rec("PASS", 15, "sitemap.xml present", f"{n} URLs")

    # 12. llms.txt
    st, _, lb = fetch(urljoin(origin, "/llms.txt"))
    if st == 200 and lb.strip():
        rec("PASS", 12, "llms.txt present", f"{len(lb)} bytes")
    else:
        rec("WARN", 12, "No llms.txt", "low-cost upside for assistant traffic")

    # 14b. favicon actually served
    st, h, _ = fetch(urljoin(origin, "/favicon.ico"), "HEAD")
    fav_svg = fetch(urljoin(origin, "/favicon.svg"), "HEAD")[0]
    if st != 200 and fav_svg != 200:
        rec("WARN", 14, "No favicon served at /favicon.ico or /favicon.svg")

    # 18 / 20. scripts
    total_js = 0
    maps = []
    for src in head.scripts[:25]:
        full = urljoin(url, src)
        st, h, b = fetch(full)
        if st == 200:
            total_js += len(b)
            if b"sourceMappingURL" in b[-2000:]:
                m = re.search(rb"sourceMappingURL=([^\s*]+)", b[-2000:])
                if m:
                    maps.append(urljoin(full, m.group(1).decode("utf-8", "ignore")))
    if total_js:
        kb = total_js / 1024
        detail = f"{kb:.0f} KB across {len(head.scripts)} script(s), as transferred"
        if kb > 500:
            rec("FAIL", 20, "Very large JS payload", detail)
        elif kb > 250:
            rec("WARN", 20, "Large JS payload", detail)
        else:
            rec("PASS", 20, "JS payload reasonable", detail)
    for mp in maps[:5]:
        st, _, _ = fetch(mp, "HEAD")
        if st == 200:
            rec("FAIL", 18, "Source map publicly reachable",
                mp + " — original source is downloadable")

    rec("INFO", 19, "Console errors not checked",
        "load the page in Chromium via Playwright and click through the main flows")


def check_local(path):
    idx = None
    for cand in ("index.html", "200.html"):
        p = os.path.join(path, cand)
        if os.path.exists(p):
            idx = p
            break
    if not idx:
        hits = glob.glob(os.path.join(path, "**", "index.html"), recursive=True)
        idx = hits[0] if hits else None

    if idx:
        html_text = open(idx, encoding="utf-8", errors="ignore").read()
        head = Head()
        head.feed(html_text)
        check_html(head, html_text, "file://" + idx)
    else:
        rec("WARN", 0, "No index.html found", f"looked under {path}")

    # 18. source maps on disk
    maps = glob.glob(os.path.join(path, "**", "*.map"), recursive=True)
    if maps:
        rec("FAIL", 18, f"{len(maps)} source map(s) in build output",
            ", ".join(os.path.basename(m) for m in maps[:5]) +
            " — original source is downloadable from production")
    else:
        rec("PASS", 18, "No source maps in build output")

    # 20. bundle weight
    js = [f for f in glob.glob(os.path.join(path, "**", "*.js"), recursive=True)]
    if js:
        raw = sum(os.path.getsize(f) for f in js)
        gz = 0
        for f in js:
            try:
                with open(f, "rb") as fh:
                    gz += len(gzip.compress(fh.read(), 6))
            except OSError:
                pass
        detail = (f"{raw/1024:.0f} KB raw / ~{gz/1024:.0f} KB gzipped "
                  f"across {len(js)} file(s)")
        kb = gz / 1024
        if kb > 500:
            rec("FAIL", 20, "Very large JS bundle", detail)
        elif kb > 250:
            rec("WARN", 20, "Large JS bundle", detail)
        else:
            rec("PASS", 20, "JS bundle reasonable", detail)
        biggest = sorted(js, key=os.path.getsize, reverse=True)[:3]
        rec("INFO", 20, "Largest JS files",
            ", ".join(f"{os.path.basename(f)} ({os.path.getsize(f)/1024:.0f}K)"
                      for f in biggest))

    # 15 / 13 / 12 / 3 as files
    for fname, item, label in (("sitemap.xml", 15, "sitemap.xml"),
                               ("robots.txt", 13, "robots.txt"),
                               ("llms.txt", 12, "llms.txt"),
                               ("404.html", 3, "404 page")):
        if os.path.exists(os.path.join(path, fname)):
            rec("PASS", item, f"{label} present in build")
        else:
            rec("WARN", item, f"No {label} in build output",
                "may still be generated at the platform level — verify on the live URL")

    rec("INFO", 0, "Local scan is partial",
        "status codes, redirects, headers and the live 404 need the deployed URL")


# ---------------------------------------------------------------- output

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="https://site.com or ./dist")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = args.target
    if target.startswith(("http://", "https://")):
        check_live(target)
    elif os.path.isdir(target):
        check_local(os.path.abspath(target))
    else:
        print(f"not a URL or directory: {target}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([{"level": l, "item": i, "title": t, "detail": d}
                          for l, i, t, d in results], indent=2))
    else:
        print(f"\n=== Technical audit: {target} ===")
        for level in ("FAIL", "WARN", "PASS", "INFO"):
            rows = [r for r in results if r[0] == level]
            if not rows:
                continue
            print(f"\n-- {level} ({len(rows)}) --")
            for _, item, title, detail in sorted(rows, key=lambda r: r[1]):
                tag = f"#{item}" if item else "  "
                print(f"  {tag:>4} {title}")
                if detail:
                    print(f"       {detail}")
        fails = sum(1 for r in results if r[0] == "FAIL")
        warns = sum(1 for r in results if r[0] == "WARN")
        print(f"\n{fails} failing, {warns} worth fixing.")
        print("Still to do by hand: console errors in a real browser (item 19), "
              "and judgment on whether the bundle size is acceptable here (item 20).")

    return 1 if any(r[0] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
