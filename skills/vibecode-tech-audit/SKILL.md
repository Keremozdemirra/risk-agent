---
name: vibecode-tech-audit
description: Audits a site for the 20 technical giveaways of a vibecoded build that hurt SEO and sharing (default subdomain, leftover Vite title, missing og:image and meta, no canonical or sitemap, public source maps, bundle size), runs real checks on the live URL or build, and fixes what you approve. Use before launch or when a site is not indexed or shares blank: "sitem Googleda cikmiyor", "linki paylasinca gorsel gelmiyor", Lighthouse, Core Web Vitals. Not for visual AI tells; use de-ai-slop-ui.
---

# Vibecode technical audit

A site can look finished and still be invisible. All twenty items below are
defaults (what you get when the generator's output was never adjusted) and
they fail in ways the author can't see from their own browser: Google never
indexes the page, the link shares as a grey box, the bundle takes eight seconds
on a phone, and the source map hands over the whole codebase.

The through-line is that **the site works for the person who built it and fails
for every machine that has to read it**: crawlers, link unfurlers, screen
readers, LLMs, and slow networks. That's who you're auditing on behalf of.

## Workflow

### 1. Establish what you can actually check

Two paths, and they catch different things:

- **Live URL**: the real test. Response headers, redirects, robots.txt,
  sitemap.xml, whether the 404 route actually 404s, what unfurlers see. Nothing
  else substitutes for this.
- **Local repo / build output**: needed for bundle size, source maps, alt text
  across components, and config-level fixes.

Do both when both exist. Also note the stack (Vite SPA, Next.js App Router,
Astro, plain HTML); it decides whether item 2 is a five-minute meta fix or an
architecture conversation, which is the one genuinely large item here.

### 2. Run the checks

```bash
# $SKILL_DIR is not set in every runtime; locate the script directly.
AUDIT_SITE="$(find "$HOME/.claude/skills" "$HOME/agents" -name audit_site.py -path '*vibecode-tech-audit*' -print -quit 2>/dev/null)"
python3 "$AUDIT_SITE" https://example.com   # live site
python3 "$AUDIT_SITE" ./dist                # local build output
python3 "$AUDIT_SITE" ./dist --json         # machine-readable
```

If `$AUDIT_SITE` comes back empty the skill lives somewhere these roots do not
cover; ask the user where it is installed rather than guessing a path.

It fetches the page and checks the head tags, H1 structure, `lang`, alt text,
canonical, og/twitter tags, structured data, favicon, robots.txt, sitemap.xml,
llms.txt, the 404 behavior, whether HTML arrives pre-rendered or empty, source
maps, and bundle weight. Read `references/checks.md` for what each item means,
how to distinguish a real problem from a false alarm, and the fix per framework.

Two things the script can't do, so do them yourself:

- **Console errors (item 19).** Load the page in a real browser. Chromium and
  Playwright are already installed here; use `page.on('console')` and
  `page.on('pageerror')`, then click through the main flows. Errors that only
  fire on interaction are the ones that matter and the ones nobody notices.
- **Judgment on bundle size and structured data.** A number isn't a verdict;
  what matters is what the number costs this site's actual visitors.

When a check asks what a visitor reads (the wording of an H1, a caveat, a
disclaimer, alt text), match against the rendered text: strip `<script>`,
`<style>` and comment blocks and unescape entities before searching, and say in
the finding that you did. Raw markup over-counts, because a word inside a source
comment matches, and under-counts, because a real caveat is written in the
author's vocabulary and your pattern is a list of guessed phrasings. Where the
answer matters, read the extracted text of the passing and the failing pages;
the composition of the passing set says more than its size.

### 3. Report

Sort by consequence. Most of these items are two-minute
fixes, so lead with the ones that are actually costing something:

```markdown
## Technical audit — <url>

**Headline:** <the one-sentence version — e.g. "Google can't index any page
because the HTML ships empty and there's no sitemap.">

### Breaking discovery / sharing
| # | Issue | Evidence | Impact | Fix effort |
|---|-------|----------|--------|-----------|
| 1 | HTML body empty, all client-rendered | `<div id="root"></div>` only | Crawlers and unfurlers see nothing | Large — needs SSR/prerender |
| 2 | No og:image | absent | Links share as a grey box everywhere | 5 min |

### Cheap wins (under 10 minutes each)
### Performance
### Polish
```

Then offer to fix. The honest framing: "items 3–17 are about twenty minutes
total and I'd just do them; item 1 is an architecture change worth discussing."

### 4. Fix

Most items are config or head tags. Two need care:

**Client-side rendering (item 2)** is the expensive one. Options in ascending
order of work: prerender at build (`vite-plugin-ssr`, `react-snap`, Astro),
migrate to a framework that server-renders by default (Next.js, Remix,
SvelteKit, Nuxt), or, if the site is an app behind a login and SEO is
irrelevant, leave it and fix the public marketing page. Ask which case
they're in before proposing a migration; a dashboard nobody should index doesn't
need one.

**Bundle size (item 20)** starts with measurement, not guessing. Run the
analyzer, find what's actually large, and go after that: a date library pulling
every locale, a chart library imported whole for one sparkline, an icon set
imported as a namespace, moment/lodash where a 2 KB alternative exists.
Code-split routes. Guessing here wastes an hour and saves 40 KB.

For everything else, prefer the framework's own mechanism (Next.js `metadata`
exports, Astro layouts, Vite's `index.html`) over hand-written tags in odd
places, so it stays correct as the site grows.

### 5. Verify by re-running

Re-run the script against the deployed site; deploy config, headers, and
redirects are exactly where these regress, and the local build cannot show them. Then confirm the
three things that fail silently:

- Fetch the page with a bare `curl` (no JS) and check the title, description,
  and content are in the HTML.
- Check the og:image actually resolves and is the right size (1200×630, under
  ~1 MB, absolute URL, since a relative one breaks every unfurler).
- Request a URL you know doesn't exist and confirm a real 404 status; a 200
  with a pretty page is a soft 404, which gets junk indexed.

## Reference

`references/checks.md` holds all 20 items with detection, false positives, and
framework-specific fixes. Read it in step 2.

Related: for exposed keys and auth holes use `pre-launch-security-audit`; for
the visual side of the same launch use `de-ai-slop-ui`.
