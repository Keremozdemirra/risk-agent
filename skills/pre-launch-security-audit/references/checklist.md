# The 23 items

Each item: **what it is → how to detect it → how to fix it**, with notes on
false positives where they're common. Items 1–4 and 15–18 are where the
account-ending bugs live; do not let the length of the list flatten that.

Contents:

1. [Get the keys out of the client](#1-get-the-keys-out-of-the-client)
2. [Purge .env from git history](#2-purge-env-from-git-history)
3. [Write the authorization rules](#3-write-the-authorization-rules)
4. [Keep authorization on the server](#4-keep-authorization-on-the-server)
5. [Rate-limit the entry points](#5-rate-limit-the-entry-points)
6. [Validate every input](#6-validate-every-input)
7. [Constrain uploads](#7-constrain-uploads)
8. [Lock down CORS](#8-lock-down-cors)
9. [Set security headers](#9-set-security-headers)
10. [Force HTTPS](#10-force-https)
11. [Hash passwords properly](#11-hash-passwords-properly)
12. [Harden cookies](#12-harden-cookies)
13. [Trim error messages](#13-trim-error-messages)
14. [Clean the logs](#14-clean-the-logs)
15. [Parameterize queries](#15-parameterize-queries)
16. [Escape output against XSS](#16-escape-output-against-xss)
17. [Verify webhook signatures](#17-verify-webhook-signatures)
18. [Put a role check on admin](#18-put-a-role-check-on-admin)
19. [Audit dependencies](#19-audit-dependencies)
20. [Automate backups and test a restore](#20-automate-backups-and-test-a-restore)
21. [Make account deletion real](#21-make-account-deletion-real)
22. [Set spend alerts](#22-set-spend-alerts)
23. [Attack it yourself](#23-attack-it-yourself)

---

## 1. Get the keys out of the client

Anything reaching the browser is public. Not obscure — public. `view-source`,
the network tab, and the built JS bundle all hand it over, and bots scrape
public bundles for exactly this.

**Detect.** Grep the source *and* the build output (`dist/`, `.next/`,
`build/`) for provider-shaped strings: `sk-`, `sk_live_`, `rk_live_`,
`service_role`, `AKIA`, `AIza`, `ghp_`, `xoxb-`, `SG.`, `eyJ` (a JWT header).
In Vite anything named `VITE_*` is inlined into the bundle by design; in
Next.js, `NEXT_PUBLIC_*`; in CRA, `REACT_APP_*`. A secret behind one of those
prefixes is already published. Also check for keys pasted inline with no env
var at all — common in AI-generated code because it makes the demo work.

**Distinguish.** Supabase `anon` and Stripe `pk_` publishable keys *belong* in
the client — that's their purpose. The `service_role` key and `sk_` secret key
never do. Firebase config is also public by design; its safety comes entirely
from security rules (see item 3).

**Fix.** Move the call to a server route, API handler, or edge function, and
keep the key in a server-only env var. Then **rotate the exposed key at the
provider** — it leaked the moment it shipped, and deleting the line does not
un-leak it. Add the build output to a grep in CI so it can't come back.

## 2. Purge .env from git history

Removing a file in a later commit leaves it fully readable in every earlier
one. On a public repo, assume it was indexed.

**Detect.** `git ls-files | grep -E '\.env'` for currently tracked files, and
`git log --all --full-history --oneline -- '*.env*'` for history. Also check
whether `.gitignore` actually covers the variants in use (`.env`,
`.env.local`, `.env.production`).

**Fix.**

```bash
git rm --cached .env && echo ".env*" >> .gitignore && echo "!.env.example" >> .gitignore
```

Commit an `.env.example` with keys but no values so the next person knows what
to fill in. Then rewrite history with `git filter-repo --path .env --invert-paths`
(or the BFG) and force-push — and warn the user this rewrites shared history, so
collaborators must re-clone. **Rotate every key that was in the file**, because
history rewriting doesn't reach forks, clones, or whoever already cloned it.
Rotation is the actual fix; the rewrite is cleanup.

## 3. Write the authorization rules

A Supabase/Firebase-style app talks to the database straight from the browser.
With RLS off (or a `USING (true)` policy), every user can read and write every
row — the API key is enough. This is the single most common catastrophic hole in
vibecoded apps, and everything looks completely normal until someone opens the
network tab.

**Detect.** In Supabase, check each table in the dashboard or via
`select relname, relrowsecurity from pg_class` — RLS enabled but zero policies
means *nothing* is readable (a different bug, usually noticed fast); RLS
disabled means everything is. Grep migrations for `enable row level security`.
For Firebase, read `firestore.rules` — `allow read, write: if true` is wide
open. Look also for `.eq('user_id', someClientValue)` in queries: filtering in
the client is not a policy, since the attacker writes the client.

**Fix.** Per table, per operation, deny by default:

```sql
alter table posts enable row level security;

create policy "read own" on posts for select
  using (auth.uid() = user_id);
create policy "insert own" on posts for insert
  with check (auth.uid() = user_id);
create policy "update own" on posts for update
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "delete own" on posts for delete
  using (auth.uid() = user_id);
```

`using` governs which rows are visible; `with check` governs what may be
written — an update needs both, or a user can reassign a row to someone else.
Test each policy as a second, unrelated user before believing it.

## 4. Keep authorization on the server

`if (user.role === 'admin')` in a React component hides a button. The endpoint
behind it stays open, and the endpoint is what gets called.

**Detect.** For every role or ownership check in client code, find the
corresponding check in the handler. Missing = finding. Watch for handlers that
trust body fields (`req.body.userId`, `req.body.role`, `req.body.price`) instead
of deriving identity from the verified session or token.

**Fix.** Derive identity server-side from the session/JWT, never from the
request body. Check ownership against the database *inside* the handler before
mutating. Keep the client check for UX only. In Next.js App Router, put it in
the server component / route handler / middleware — not in a `"use client"`
file.

## 5. Rate-limit the entry points

Without a limit, login is brute-forceable, signup is spammable, password reset
is an email-bomb gun, and any endpoint calling a paid API (LLMs especially) is a
way to spend the user's money at machine speed.

**Detect.** Search for `rate-limit`, `ratelimit`, `throttle`, `slow-down`,
`limiter`. None found → nothing is limited. Pay particular attention to
`/api/*` routes that call OpenAI/Anthropic/Stripe or send mail.

**Fix.** Cheapest real option first: the platform's own limiter (Vercel
Firewall, Cloudflare Rate Limiting) needs no code. In code, `@upstash/ratelimit`
with Redis works serverlessly; `express-rate-limit` works on a long-lived
server. Key on IP *and* account for auth routes, and start strict — 5 login
attempts per 15 minutes, 3 password resets per hour. In-memory limiters are
useless on serverless (every invocation is a fresh process); say so if you find
one.

## 6. Validate every input

Unvalidated bodies produce corrupt rows, 500s that leak internals, and the
occasional crash loop. It is also the layer that makes items 7, 15, and 16
much harder to exploit.

**Detect.** Handlers that destructure `req.body` and use the values directly.
No schema library in `package.json` (`zod`, `yup`, `valibot`, `joi`,
`pydantic`) is a strong signal.

**Fix.** One schema per endpoint, parsed at the boundary, allowlist not
denylist:

```ts
const Body = z.object({
  email: z.string().email(),
  quantity: z.number().int().min(1).max(100),
  note: z.string().max(500).optional(),
});
const parsed = Body.safeParse(await req.json());
if (!parsed.success) return Response.json({ error: "Invalid input" }, { status: 400 });
```

Note what's absent from the schema: `price`, `role`, `userId`. Anything the
server can determine, the server determines — accepting it from the client is
how privilege escalation and free orders happen. Also validate URL params and
query strings, not just bodies.

## 7. Constrain uploads

An unconstrained upload endpoint is free storage for strangers, a disk-filling
DoS, and a way to serve HTML/SVG from your own origin — which turns into stored
XSS on your domain, with your cookies.

**Detect.** Look at the upload handler and the bucket policy. Missing size cap,
missing type allowlist, filename taken from the client, public bucket with
anonymous write — each is a finding.

**Fix.** Cap size at the edge and in the handler. Allowlist MIME types *and*
verify the actual bytes (magic number) rather than trusting the declared
`Content-Type` or the extension. Generate the stored filename yourself (UUID)
so `../../etc/passwd` and `evil.html` are impossible. Store outside the web
root or in a bucket that serves with `Content-Disposition: attachment` and a
non-HTML content type. For SVG specifically: either sanitize it or don't
accept it. Require auth to upload, and rate-limit it.

## 8. Lock down CORS

`Access-Control-Allow-Origin: *` combined with `credentials: true` lets any
site make authenticated requests as your logged-in user. Browsers actually
refuse that exact combination — which is why the dangerous version is the
reflected one, where the server echoes back whatever `Origin` it was sent.

**Detect.** Grep for `cors(`, `Access-Control-Allow-Origin`, `origin: true`,
`origin: '*'`, and any handler that reads `req.headers.origin` and writes it
straight back.

**Fix.** An explicit array of origins, environment-specific:

```ts
const allowed = ['https://app.example.com', 'https://example.com'];
app.use(cors({
  origin: (o, cb) => cb(null, !o || allowed.includes(o)),
  credentials: true,
}));
```

Don't leave `http://localhost:3000` in the production list. Note that CORS
protects browser callers only — it is not access control, and `curl` ignores it
entirely. Item 4 is what protects the endpoint.

## 9. Set security headers

Headers are the cheapest defense-in-depth available: a few lines that blunt
XSS, clickjacking, and MIME confusion.

**Detect.** `curl -sI https://the-site` and look for `Content-Security-Policy`,
`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` /
`frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`. Absent = finding.

**Fix.** Use the framework's mechanism — `next.config.js` `headers()`,
`vercel.json`, Netlify `_headers`, `helmet()` on Express — not hand-rolled
middleware. Minimum set:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'
```

CSP is the one that takes real work, because `'unsafe-inline'` in `script-src`
gives up most of its value and many frameworks need nonces or hashes to avoid
it. Deploy in `Content-Security-Policy-Report-Only` first, watch what breaks,
then enforce. Don't hand the user a CSP that blanks their site.

## 10. Force HTTPS

Over plain HTTP, session cookies and passwords are readable on the wire, and
any HTTP asset on an HTTPS page triggers mixed-content blocking.

**Detect.** Request `http://` and confirm a 301/308 to `https://`. Grep the
codebase for `http://` URLs that aren't localhost.

**Fix.** Most hosts (Vercel, Netlify, Cloudflare) redirect by default —
confirm rather than assume, especially with a custom domain or a custom server.
Add HSTS (item 9). Behind a proxy, set `trust proxy` so the app reads
`X-Forwarded-Proto` correctly, or the redirect loops forever.

## 11. Hash passwords properly

Plaintext or a fast hash (MD5, SHA-1, SHA-256, unsalted anything) means one
database leak equals every user's password — including the ones they reuse on
their email.

**Detect.** Find where the password is stored. `crypto.createHash('sha256')`
on a password, `md5(`, plaintext comparison with `===`, or a homemade scheme
are all findings. Also check for password logging (item 14) and for password
values in error responses.

**Fix.** Use a managed auth provider if at all possible — Supabase Auth,
Clerk, Auth0, NextAuth all handle this correctly and you inherit their
maintenance. If rolling your own: `argon2id` (preferred) or `bcrypt` with cost
≥ 12, compared in constant time via the library's `verify`. Never truncate or
pre-hash the input. Migrate existing weak hashes by re-hashing on next
successful login and force-resetting anything left over. Never email a
password; send a single-use, short-lived reset link.

## 12. Harden cookies

A session cookie readable by JavaScript turns any XSS into full account
takeover. One without `SameSite` invites CSRF.

**Detect.** Grep `res.cookie(`, `Set-Cookie`, `document.cookie`, and the auth
library's session config. A session token in `localStorage` is the same class of
problem — it's JS-readable by definition.

**Fix.**

```ts
res.cookie('session', token, {
  httpOnly: true,   // JS can't read it — kills the XSS→takeover path
  secure: true,     // HTTPS only
  sameSite: 'lax',  // 'strict' if no cross-site flows; 'none' requires secure
  path: '/',
  maxAge: 60 * 60 * 24 * 7 * 1000,
});
```

Set an expiry rather than leaving it a session cookie forever, and invalidate
server-side on logout — clearing the cookie alone leaves a stolen token valid.

## 13. Trim error messages

A stack trace tells an attacker the framework, the versions, the file paths,
and often the SQL. Verbose DB errors leak schema and column names.

**Detect.** Handlers that `return { error: err.message }` or send `err.stack`.
Framework debug mode on in production (`DEBUG=True` in Django, `NODE_ENV`
unset, Next.js dev build deployed). Trigger it: send garbage to an endpoint and
read what comes back.

**Fix.** Log the full error server-side with a correlation ID; return a generic
message plus that ID to the client. Auth errors especially must not distinguish
"no such user" from "wrong password" — that difference is a free user
enumeration oracle. Confirm production sets `NODE_ENV=production` /
`DEBUG=False`.

## 14. Clean the logs

`console.log(req.body)` in a signup handler writes passwords into a log
aggregator that a much wider set of people can read, retained for months. Same
for tokens, card data, and full webhook payloads.

**Detect.** Grep `console.log`, `console.error`, `print(`, `logger.` near auth,
payment, and webhook code. Look for whole-object logging: `log(req.body)`,
`log(user)`, `log(session)`, `log(event)`.

**Fix.** Log identifiers, not payloads — `userId`, not `user`. Add a redaction
list for `password`, `token`, `authorization`, `cookie`, `secret`, `card`,
`ssn` (most structured loggers support this natively; Pino's `redact` is the
canonical example). Strip debug logging from production paths. If secrets were
already logged, they need rotating too.

## 15. Parameterize queries

String-built SQL is SQL injection: `WHERE id = '${req.params.id}'` with
`' OR 1=1--` returns every row, and with `'; drop table users;--` does worse.

**Detect.** Grep for template literals and concatenation inside `query(`,
`execute(`, `raw(`, `$queryRawUnsafe`, `.rpc(`. In Python, `%`/`.format()`/
f-strings inside `cursor.execute`. ORMs are safe by default but every one has an
escape hatch — check the raw-SQL calls specifically.

**Fix.** Placeholders, always:

```ts
// vulnerable
db.query(`select * from users where email = '${email}'`);
// safe
db.query('select * from users where email = $1', [email]);
```

Table and column names can't be parameterized — if they come from user input,
validate against a hardcoded allowlist. Prisma/Drizzle/SQLAlchemy query
builders are fine; their `raw` variants are not. Give the app's DB user only
the privileges it needs, so an injection that slips through does less.

## 16. Escape output against XSS

User content rendered as HTML runs as JavaScript on your origin, with your
cookies. Stored XSS in a comment field hits every visitor.

**Detect.** Grep `dangerouslySetInnerHTML`, `innerHTML =`, `v-html`,
`{@html`, `|safe`, `mark_safe`, `document.write`. Also `href={userValue}`
(`javascript:` URLs) and any Markdown renderer with HTML passthrough enabled.

**Fix.** Prefer plain interpolation — React, Vue, Svelte, and Jinja all escape
by default, and that default is the whole defense. When HTML really is needed
(a rich-text editor), sanitize with DOMPurify server-side on write *and* on
render; hand-written regex sanitizers get bypassed. Validate URL schemes against
`https:`/`http:`/`mailto:` before putting them in `href` or `src`. CSP (item 9)
is the backstop, not the fix.

## 17. Verify webhook signatures

An unverified webhook endpoint is an unauthenticated write API. Anyone who
guesses the URL can POST `payment_succeeded` and get whatever paying gets.

**Detect.** Find `/webhook`, `/api/webhooks/*`, `/callback` handlers. No
signature verification before processing = critical. Also check the raw-body
problem: verification silently fails, or is skipped, when a JSON body parser has
already reparsed the payload.

**Fix.** Use the provider's verifier with the raw body and the signing secret,
before any business logic:

```ts
const event = stripe.webhooks.constructEvent(rawBody, sig, process.env.STRIPE_WEBHOOK_SECRET);
```

In Next.js App Router use `await req.text()`; in Express mount
`express.raw({type: 'application/json'})` on that route only. Also make handling
idempotent — providers retry, and a double-processed payment is its own bug.
Reject stale timestamps to blunt replay.

## 18. Put a role check on admin

An admin panel protected by an unguessable URL is protected by nothing. These
routes are often the last thing built and the least reviewed, and they usually
have the widest permissions in the app.

**Detect.** Every route under `/admin`, `/dashboard`, `/internal`, plus any
handler doing bulk deletes, refunds, user impersonation, or data export. Ask:
where is the server-side role check? A client-side redirect isn't one — the
data already loaded before it fired.

**Fix.** Store the role server-side (a DB column or a JWT claim you sign), read
it from the verified session, and check it in middleware covering the whole
route group so a newly added page is protected by default rather than by memory.
Never trust a role from a client-supplied header or body field. RLS policies
need the same treatment: `using (auth.jwt() ->> 'role' = 'admin')`, not a
client flag. Log admin actions with the acting user's ID.

## 19. Audit dependencies

Vibecoded projects accumulate packages fast, and a known-vulnerable transitive
dependency is exploitable without anyone touching your code.

**Detect.**

```bash
npm audit --omit=dev            # or: pnpm audit / yarn npm audit
pip-audit                       # Python
```

Also scan for typosquats (`react-dom` vs `reactdom`), packages with a handful of
weekly downloads doing something important, and anything imported but not in
`package.json`.

**Fix.** `npm audit fix` for the non-breaking ones; upgrade the rest
deliberately and run the app afterward. Judge severity by whether the
vulnerable path is actually reachable — a prototype-pollution CVE in a build-only
tool is not the same risk as an RCE in your HTTP layer, and saying so keeps the
report credible. Turn on Dependabot/Renovate so this stays current. Commit the
lockfile.

## 20. Automate backups and test a restore

A backup nobody has restored is a hypothesis. The failure mode here isn't
attackers, it's a bad migration or a fat-fingered `delete` at 2am.

**Detect.** Ask what the backup schedule is, where backups live, and when one
was last restored. Managed Postgres usually has PITR available — check it's
actually enabled on the current plan, since free tiers often exclude it.

**Fix.** Enable automated daily backups plus point-in-time recovery where
offered. Keep a copy outside the primary provider account — a compromised or
suspended account takes its own backups with it. Then **restore one into a
scratch database and check the row counts**; that's the step that converts a
hypothesis into a backup. Write down the restore procedure while it's fresh.

## 21. Make account deletion real

"Delete account" that flips `deleted = true` while keeping the email, the
uploads, and the Stripe customer is a false promise to the user and, under
GDPR/CCPA, a legal exposure.

**Detect.** Read the deletion handler. Follow the user's data outward: rows in
other tables, storage objects, the auth provider record, Stripe, the mailing
list, analytics, any cache.

**Fix.** Decide honestly between anonymization (keep aggregate rows, scrub
identifiers) and hard deletion, and make the UI say which one happens. Cascade
across every store the user touched, including the auth provider and third
parties — `supabase.auth.admin.deleteUser` and the equivalent Stripe call are
easy to forget. Require re-authentication, then confirm. A grace period is fine
and often kind, as long as it's disclosed. Log the deletion itself (without the
deleted data) so you can prove it happened.

## 22. Set spend alerts

The nightmare bill is usually not an attack — it's a loop calling an LLM, an
unlimited free tier someone found, or egress from a hot asset. Metered
serverless plus no ceiling means the bill grows as fast as the traffic.

**Detect.** Check each paid provider for a budget alert or hard cap: the cloud
host, the database, and every AI API. Also look for missing usage limits per
user on expensive endpoints.

**Fix.** Set a budget alert at ~50% and ~100% of what the user considers
tolerable, on every provider — most have this and it's off by default. Prefer a
hard cap where one exists (OpenAI and Anthropic both offer usage limits;
Cloudflare and Vercel have spend controls). Add a per-user quota on expensive
endpoints, and rate-limit them (item 5). Consider cost anomaly detection on the
cloud account. This item takes ten minutes and prevents the single most common
"I woke up to a $4,000 bill" story.

## 23. Attack it yourself

Everything above is a category. This item is where you find the mistake specific
to *this* app — and it's the step people skip, because it requires deliberately
trying to break something you just built.

Work through these against a staging environment (or production with test data,
never real user data), and record the exact request and response for anything
that works:

**No auth.** Hit every mutating endpoint with `curl`, no cookie, no token.
Anything that isn't 401/403 is a finding.

```bash
curl -i -X POST https://app/api/orders -H 'content-type: application/json' -d '{"quantity":1}'
```

**Wrong user (IDOR).** Log in as A, take B's resource ID, call the endpoint.
This is the most common real hole in generated CRUD code: the handler fetches by
ID and never checks ownership. Try it on read, update, and delete separately —
they're often protected inconsistently.

**Client-controlled values.** Move `price`, `role`, `is_admin`, `user_id`,
`credits`, `quantity` in the request body and see if the server accepts them.
Negative quantities and negative prices are worth a specific try.

**Malformed input.** Wrong types, `null`, empty string, a 10 MB string, deeply
nested JSON, unicode, emoji, SQL and HTML metacharacters. You're looking for
500s, hangs, and leaked internals more than for a clean exploit.

**Rate.** Loop login 100 times. Loop the expensive AI endpoint 20 times. Note
whether anything stopped you and what it cost.

**Uploads.** A `.html` file, an `.svg` containing `<script>`, a 1 GB file, a
filename with `../`, a file whose extension and real bytes disagree.

**Tokens.** Try an expired one, another user's, a tampered payload with the
signature stripped (`alg: none`), and a session after logout.

Report results plainly: what you tried, what happened, what it means. If
everything held, say that — it's the most valuable sentence in the report, and
it's only credible because you actually tried.
