# The 20 technical giveaways

Each: **what it is → how to check → how to fix**, with framework specifics.
Ordered by consequence rather than by the original list, since the point is to
fix what's actually costing the site something. Original numbers are noted.

---

## Discovery-breaking

### 2. Empty view-source (client-side rendering)

`curl` the page and get `<div id="root"></div>` plus a script tag. The content
exists only after JavaScript runs. Google *can* render JS, but slower, less
reliably, and with a rendering budget — while link unfurlers (WhatsApp, Slack,
X, LinkedIn, iMessage), most AI crawlers, and RSS readers execute no JS at all
and see literally nothing.

**Check.** `curl -s https://site | head -50`. Is the headline text there? Is
there a `<title>` with real content? Compare `curl` output length against what
the browser shows.

**Fix.** In ascending order of effort:

1. **Prerender at build.** For a Vite SPA: `vite-plugin-ssr`/`vike`,
   `react-snap`, or `puppeteer` in a postbuild step writing static HTML per
   route. Cheapest real fix for a marketing site with a handful of pages.
2. **Move to a server-rendering framework.** Next.js App Router, Astro (best
   fit for content sites — ships zero JS by default), Remix, SvelteKit, Nuxt.
   Right answer if the site is content-first.
3. **Leave it.** A dashboard behind a login shouldn't be indexed anyway. In that
   case, make sure the *public* marketing page is server-rendered and stop there.

Don't propose a migration before asking which case it is.

### 15. No sitemap.xml

Without one, discovery depends entirely on internal links being crawlable —
which, on a client-rendered SPA, they often aren't.

**Check.** `curl -sI https://site/sitemap.xml` → expect 200 and XML, not the
SPA's index.html with a 200 (a common false pass — check the content type and
body, not just the status).

**Fix.** Generate at build: `next-sitemap`, `@astrojs/sitemap`,
`vite-plugin-sitemap`, or a 20-line script over your route list. Include only
canonical, indexable URLs — no redirects, no 404s, no `noindex` pages, since a
dirty sitemap costs crawl trust. Reference it from robots.txt
(`Sitemap: https://site/sitemap.xml`) and submit it in Search Console.

### 13. robots.txt blocking AI crawlers

Two distinct failures. The severe one: a wildcard `Disallow: /` — sometimes left
from a staging config — which removes the site from search entirely. The
deliberate-but-often-accidental one: blocking `GPTBot`, `ClaudeBot`,
`PerplexityBot`, `Google-Extended`, `CCBot`, usually copied from a template
without reading it. If the goal is for people to *find* this site, and people
increasingly search through assistants, that block is self-inflicted.

**Check.** `curl -s https://site/robots.txt`. Also check for a stray
`<meta name="robots" content="noindex">` in the HTML head and an
`X-Robots-Tag: noindex` response header — a leftover `noindex` is the single most
common reason a new site never appears in Google.

**Fix.** For a site that wants to be found:

```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/

Sitemap: https://site.com/sitemap.xml
```

Then decide about AI crawlers deliberately rather than by inheritance — blocking
them keeps content out of assistant answers, which for most small sites is
traffic they wanted. Verify no `noindex` survives anywhere in production.

### 11. No canonical tag

Without one, `https://site.com/page`, `http://`, `www.`, `/page/`, and
`/page?utm_source=x` can all be treated as separate URLs, splitting ranking
signals across duplicates.

**Check.** Look for `<link rel="canonical" href="...">` in the head. It must be
absolute, self-referential on the canonical version, and *different per page* —
every page pointing at the homepage is worse than having none, and is a common
copy-paste bug.

**Fix.** Emit per-page. Next.js: `metadata.alternates.canonical`. Astro: in the
layout from `Astro.url`. Also pick one host and redirect the rest (301
`www` → apex or the reverse, `http` → `https`) so the canonical and the
redirects agree.

### 12. No llms.txt

An emerging convention (`/llms.txt`) — a markdown file describing the site and
pointing to its key pages in a form assistants can consume cheaply. Not a
standard, not honored universally, and worth roughly ten minutes of effort. Treat
it as low-cost upside, not a requirement, and don't oversell it to the user.

**Check.** `curl -s https://site/llms.txt`.

**Fix.**

```markdown
# Product Name

> One-sentence description of what this actually does.

## Docs
- [Getting started](https://site.com/docs/start): install and first run
- [API reference](https://site.com/docs/api): endpoints and auth

## About
- [Pricing](https://site.com/pricing): plans and limits
```

Keep it factual and current. A stale llms.txt is worse than none.

---

## Sharing-breaking

### 7. No og:image

The highest-visible-impact item on the list. Without it, every share on
WhatsApp, X, LinkedIn, Slack, iMessage, Discord, and Facebook renders as a grey
box — and that's usually the first impression, at the exact moment someone is
recommending the site to someone else.

**Check.** Look for `og:image`, `og:title`, `og:description`, `og:url`,
`twitter:card`. Then confirm the image URL actually loads
(`curl -sI <og:image>`) — a relative path is the classic bug, since unfurlers
don't resolve it.

**Fix.** Absolute URL, 1200×630, under ~1 MB, PNG or JPG (not SVG — poorly
supported by unfurlers), with the product name legible at thumbnail size.

```html
<meta property="og:title" content="Page-specific title">
<meta property="og:description" content="One clear sentence.">
<meta property="og:image" content="https://site.com/og.png">
<meta property="og:url" content="https://site.com/page">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
```

Next.js can generate these per page with `opengraph-image.tsx` (ImageResponse),
which is the nice version: real per-page images with no design work per page.

### 5. Identical page titles

Every route shows the same `<title>`. Search results become an unreadable list
of duplicates, browser tabs are indistinguishable, and Google may rewrite the
title itself.

**Check.** Fetch several routes and compare `<title>`. On an SPA, check whether
titles update on client navigation at all.

**Fix.** Per-page titles, most specific part first, ~50–60 characters:
`"Pricing — Product"`, not `"Product — the best tool for everything"`. Next.js:
`export const metadata = { title: ... }` per route, with a
`title.template` in the root layout. Vite SPA: `react-helmet-async` or
`@unhead/vue`, but note that client-set titles are invisible to non-JS
consumers — which is item 2 again, and the reason it ranks first.

### 4. Leftover "Vite + React" title and default favicon

The literal default: `<title>Vite + React</title>`, `vite.svg` favicon, and
sometimes the starter's `<h1>` still in place. It signals "unfinished" to every
visitor, and it's the fastest tell on the list.

**Check.** Grep `index.html` for `Vite`, `Create React App`, `Next.js App`,
`Nuxt`, `Astro`, `vite.svg`, `favicon.ico` pointing at the default asset.

**Fix.** Real title, real description, real favicon, real `<html lang>`. Also
check `manifest.json`/`site.webmanifest` for the same leftovers — commonly
missed, and it's what shows when someone installs the PWA.

### 6. No meta description

Google may generate a snippet from page text, and it's often a nav menu or a
cookie banner. You get one sentence of control over what appears under your
result; skipping it wastes it.

**Check.** `<meta name="description">` present, per-page, 140–160 characters.

**Fix.** Write it as ad copy, not as a summary: what the page offers and why
click. Per page — a site-wide description is barely better than none.

### 8. No structured data

No JSON-LD, so no rich results — no FAQ accordions, no product price and rating,
no article byline, no breadcrumbs.

**Check.** Look for `<script type="application/ld+json">`. Validate at
validator.schema.org / Google's Rich Results Test.

**Fix.** Add only the types that genuinely match the page — `Organization` or
`WebSite` sitewide, then `Product`, `SoftwareApplication`, `Article`, `FAQPage`,
or `BreadcrumbList` as applicable. Two rules: the markup must describe content
actually visible on the page (invisible-only markup is a spam signal and can
earn a manual action), and prices/ratings must be real. Don't invent
`aggregateRating` — that's a policy violation, not a growth hack.

---

## Structure and accessibility

### 9 & 10. Multiple H1s, or none

Two failures of the same thing. Zero H1 (common when the hero headline is a
styled `<div>` or `<p>`) leaves the page's topic unstated. Multiple H1s (common
when every section heading got `text-4xl font-bold` as an `<h1>`) flatten the
hierarchy. Screen-reader users navigate by heading level, so this is an
accessibility issue as much as an SEO one.

**Check.** Count `<h1>` — expect exactly one. Then check the levels descend
without skipping (`h1 → h2 → h3`, never `h1 → h4`).

**Fix.** One `<h1>` per page carrying the actual topic; sections get `<h2>`,
subsections `<h3>`. Heading level is semantics; size is CSS. A visually small
`<h2>` and a huge `<h2>` are both fine — decouple the two.

### 16. Missing html lang

`<html>` with no `lang`. Screen readers then guess the pronunciation language,
browsers mis-apply translation and hyphenation, and search engines lose a
targeting signal. It is a one-attribute fix and a WCAG requirement.

**Check.** `<html lang="...">` present and correct — `tr` for Turkish, `en` for
English, regional variants (`en-GB`, `pt-BR`) where meaningful. Watch for a
template default that doesn't match the content's actual language, which is
worse than absence because it's confidently wrong.

**Fix.** Set it. On multilingual sites, set it per rendered locale and add
`hreflang` alternates linking the versions.

### 17. Missing alt text

Images with no `alt`. Screen readers announce the filename or skip it, and image
search has nothing to index. Generated markup usually omits it entirely.

**Check.** Count `<img>` without an `alt` attribute. Also flag lazy alt text —
`alt="image"`, `alt="photo"`, the filename — which is present-but-useless.

**Fix.** Describe function, not appearance: `alt="Dashboard showing weekly
revenue trend"`, not `alt="screenshot"`. Purely decorative images get `alt=""`
(explicitly empty, so it's correctly skipped) — that's a real answer, not a
cop-out. Don't start with "image of"; the screen reader already says that.

### 3. No 404 page

An unknown URL either shows a blank page, a framework error, or — worse — the
homepage with a 200 status. That last one is a "soft 404": crawlers index
infinite junk URLs as real pages.

**Check.** `curl -sI https://site/definitely-not-a-real-url-12345` and read the
status code, not the body. Expect 404. A 200 is the finding.

**Fix.** A real 404 route that returns status 404 and offers a way forward — a
link home, search, the main sections. Next.js: `app/not-found.tsx`. Astro:
`src/pages/404.astro`. For an SPA with catch-all rewriting on a static host, the
rewrite makes correct status codes awkward; solve it at the host (Netlify
`_redirects` with `404`, Vercel `routes`) rather than pretending. Also confirm
`/index.html`-style duplicates and trailing-slash variants resolve consistently.

### 14. No favicon

The 404 in the network tab, and a generic globe or blank square in the tab bar
and in every bookmark.

**Check.** `curl -sI https://site/favicon.ico` plus the declared `<link
rel="icon">`.

**Fix.** Modern minimum: an SVG icon plus a PNG fallback plus
`apple-touch-icon` at 180×180.

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-96.png" sizes="96x96">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

Check it's legible at 16×16 — most logos aren't; use a mark or a single letter.

---

## Performance and hygiene

### 20. Massive JS bundle

Multi-megabyte JS on a page that shows a hero and three cards. On a mid-range
phone on cellular, a 3.5 MB bundle is several seconds of blank screen before
anything renders, and it moves every Core Web Vital in the wrong direction.

**Check.** Sum the JS in the build output, and check *transferred* size (gzip or
brotli) as well as raw — hosts compress, so raw numbers overstate the cost.
Rough guidance for a marketing site: under ~150 KB compressed JS is healthy,
~300 KB is a yellow flag, over ~500 KB needs work. Then find out *what* it is:

```bash
npx vite-bundle-visualizer          # Vite
ANALYZE=true npx next build          # with @next/bundle-analyzer
npx source-map-explorer 'dist/**/*.js'
```

**Fix.** Go after what the analyzer shows, in this order:

- **Whole-library imports.** `import * as Icons`, `import _ from 'lodash'`,
  `import { Chart } from 'chart.js'` for one sparkline. Import the members you
  use, or switch to a lighter option (`date-fns`/`dayjs` over `moment`, native
  `Intl` over both).
- **Route-level code splitting.** `React.lazy` / dynamic imports so the landing
  page doesn't ship the dashboard.
- **Locale and font data.** Full ICU locale sets and every font weight are
  frequently the largest single chunk.
- **Unused UI kits.** A whole component library imported for a button.
- **Images.** Not JS, but usually the bigger real problem — serve WebP/AVIF,
  size them for their display box, `loading="lazy"` below the fold, and always
  set dimensions (see `de-ai-slop-ui` tell 21 on layout shift).

Measure after each change; report actual numbers ("482 KB → 96 KB compressed"),
because that's what makes the work legible to the user.

### 18. Source maps in production

`.map` files deployed alongside the bundle, or an inline
`//# sourceMappingURL=data:...`. Anyone can reconstruct the original source
including comments, internal names, unshipped code paths, and occasionally a key
that was assumed minified away.

**Check.** Look for `*.map` in the build output and `sourceMappingURL` comments
in the shipped JS. Try fetching one from the live site.

**Fix.** Either turn them off (`build.sourcemap: false` in Vite,
`productionBrowserSourceMaps: false` in Next.js — the default) or, better, keep
generating them and upload them privately to your error tracker (Sentry does
this with `sourcemaps upload` then deletes the files) so stack traces stay
readable without publishing the source. If a map was already public, treat any
secret visible in it as leaked and rotate it — see `pre-launch-security-audit`.

### 19. Console errors

Red errors in the console on load or on interaction: failed fetches, hydration
mismatches, React key warnings, 404s on missing assets, uncaught promise
rejections. Each is a real bug that happened to not be visible on the developer's
machine — and hydration mismatches in particular cause content to flash or
disappear for real users.

**Check.** A real browser, not a static scan. With Playwright (Chromium is
already installed):

```js
const errors = [];
page.on('console', m => m.type() === 'error' && errors.push(m.text()));
page.on('pageerror', e => errors.push(e.message));
page.on('requestfailed', r => errors.push(`${r.failure()?.errorText} ${r.url()}`));
```

Then load the page *and click through the main flows* — the errors that only fire
on interaction are the ones nobody has noticed.

**Fix.** Fix them; don't silence them. Priority order: uncaught exceptions
(break functionality) → failed requests (break features) → hydration mismatches
(break rendering) → React warnings (usually reveal a real state bug) → deprecation
notices. Add an error boundary so a single component failure doesn't blank the
page, and wire up error tracking so you learn about production errors from data
rather than from a user email.

### 1. Default platform subdomain

`something-git-main-username.vercel.app`, `random-name.netlify.app`,
`project.pages.dev`. It works fine technically; it just tells every visitor the
site is a hobby deploy, which is fatal for anything asking for a card number.

**Check.** The hostname.

**Fix.** A domain costs about ten dollars a year and is the highest
trust-per-effort change available. After pointing it: set the canonical to the
new host, 301 the old subdomain rather than leaving both live and indexed, update
og:url and the sitemap, re-verify in Search Console, and update any OAuth
redirect URIs and webhook endpoints — those break silently on a domain change and
are the usual post-migration bug.

---

## Verification order

Re-check against the deployed site, since deploy config is where these regress:

1. `curl -s <url> | head -60` — title, description, og tags, real content in the
   HTML.
2. `curl -sI <url>/nonexistent-12345` — a real 404 status.
3. `curl -sI <og:image>` — resolves, correct type, sensible size.
4. `curl -s <url>/robots.txt` and `/sitemap.xml` — present, no stray
   `Disallow: /`, sitemap referenced.
5. Browser console, clicking through the main flows — no errors.
6. Compressed JS total, before and after.
7. Google Search Console URL Inspection on the live URL — the authoritative
   answer to "can Google actually index this", which no local check replaces.
