---
name: pre-launch-security-audit
description: Audits an app against 51 checks in two scored sections. Section 1, the 33 that must be true before launch - leaked keys, secrets in git history, missing row-level security, client-side-only auth, CSRF, sessions that never end, reusable reset tokens, no login backoff, a superuser database key, SQL injection, XSS, unvalidated input, wildcard CORS, open uploads, leaky stack traces, unverified webhooks, vulnerable dependencies, unverified email, guessable IDs, reachable debug endpoints, hardcoded secrets, no backups, no spend alerts. Section 2, the 18 that survive a clean pass on all of it - SECURITY DEFINER functions that bypass RLS, unrevocable JWTs, a CDN caching one user's page for another, shipped sourcemaps, missing subresource integrity, CI that ignores the lockfile, GitHub Actions pinned to movable tags, dependency confusion, webhook replay, SSRF, non-timing-safe comparison, GraphQL cost, ReDoS, shared staging keys, shared logins, no audit trail. Cites a file and line for every pass and fail, marks UNKNOWN rather than guessing, then reads for the logic-level flaws grepping cannot see, attacks it the way someone hostile would, and fixes what the user approves one at a time. Use whenever the user is about to ship, deploy, launch or go live; asks "is this safe", "is this production-ready", or wants a security review, audit, score or hardening pass; says "guvenlik denetimi yap", "güvenlik denetimi yap", "yayina almadan kontrol et", "API anahtarim sizmis mi", ".env'i commit etmisim", "guvenli mi", "skor ver"; mentions exposed secrets, RLS policies, auth bugs, API abuse or a surprise cloud bill; and proactively before any AI-generated app meets real users. Not for SEO, meta tags or the technical tells that expose a site as vibecoded; use vibecode-tech-audit for that.
---

# Pre-launch security audit

AI-assisted code gets built to make the happy path work. Nothing in that loop
forces the app to be safe — the model writes what was asked for, the app runs,
the demo looks great, and every one of the 51 items below is quietly still
undone. That's the gap this skill closes.

Two rules govern how you work here. First, **be specific**: a finding is only
useful if it names the file, the line, and what an attacker does with it.
"Consider adding validation" helps no one. Second, **verify before you claim**:
read the actual code before reporting a hole, because a false alarm costs the
user trust in the whole report and a missed hole costs them their database.

## Workflow

### 1. Understand the stack before scanning

Read `package.json` / `requirements.txt` / `go.mod`, the framework config, and
the directory layout. What matters changes completely with the stack: a Supabase
app lives or dies on Row Level Security, a Next.js app on the server/client
boundary, an Express API on middleware ordering. Note which of these you're in
before you start — it determines which of the 51 items are load-bearing and
which are not applicable.

Also establish what the app actually handles. An app with no accounts, no
payments, and no user data has a much shorter real risk list than one holding
customer records, and saying so up front keeps the report honest.

### 2. Scan

Run the bundled scanner for the mechanical checks, then read code for the rest:

```bash
# $SKILL_DIR is not set in every runtime; locate the script directly.
SCAN_SECRETS="$(find "$HOME/.claude/skills" "$HOME/agents" -name scan_secrets.py -path '*pre-launch-security-audit*' -print -quit 2>/dev/null)"
python3 "$SCAN_SECRETS" <project-dir>
```

If `$SCAN_SECRETS` comes back empty the skill lives somewhere these roots do not
cover — ask the user where it is installed rather than guessing a path.

It greps for key-shaped strings, checks whether `.env` is tracked in git and
whether it appears in history, flags `dangerouslySetInnerHTML` and `eval`,
finds string-interpolated SQL, and reports dependency audit status. It is a
starting point that catches the obvious cases fast — it does not replace
reading the auth and data-access code yourself, which is where the serious
findings almost always are.

Then walk `references/checklist.md`, which has all 51 items with what to grep
for, how to tell a real finding from a false positive, and the fix per stack.
Read it — the detail there is the substance of this skill.

### 2b. Read for the four things grepping cannot see

The checklist and the scanner are both pattern work: they find a bad call, a
missing flag, a key in the wrong file. The bugs that survive a clean checklist
pass are the ones where **no single function is wrong** and the hole only exists
in how the pieces fit together. Budget real reading time for these four, tracing
the call graph rather than scanning for signatures:

**Business logic flaws.** A coupon applies twice because the check and the
deduction aren't atomic. Credits go negative because the balance is read, then
written, with an await in between. Look at every place money, quota, or
inventory changes, and ask what happens if the same request arrives twice.

**Access control that breaks across files.** The route handler authenticates and
the middleware doesn't — or the reverse, and one route was registered outside
the middleware. Check that every admin and owner-scoped route is covered by the
same guard, and that the guard is applied where routing actually resolves.

**Multi-step data flow.** User input passes through three functions before it
reaches a query, a shell call, or a template. No single function looks unsafe.
Follow the parameter, not the sink: start at the request body and walk forward.

**Context-dependent safety.** A helper is safe on the path that sanitizes first
and dangerous on the path that doesn't. When you find a function used in more
than one place, check every call site, not the one you happened to read.

This is the pass that justifies a human-grade audit over a scanner. If you skip
it, say so in the report rather than implying the code was cleared.

### 3. Report before touching anything

The user needs to see the shape of the problem before code starts changing.
Group findings by how much damage they do, not by checklist order.

**Open with two lines that can be screenshotted**, then the detail:

```markdown
MUST-HAVES: 19 / 24
NOT SO OBVIOUS: 3 / 16

## Security audit — <project>

**Verdict:** <not safe to ship / ship with caveats / clean> — one sentence why.

### Critical — an attacker can do this today
| # | Finding | Where | Confidence | What an attacker does |
|---|---------|-------|-----------|----------------------|
| 1 | Supabase service_role key in client bundle | `src/lib/db.ts:4` | Confirmed | Reads and deletes every row in every table, bypassing RLS |

### Should fix — real gaps, not urgent
### Passed — one line each, no elaboration
### Unknown — what you could not determine, and what you would need to see
### Anything else — findings no item on either list covers
### Ask me — the questions in step 3b, unscored
### Fix first — the three highest-impact items, in order, each with why it ranks there
```

**Score the two sections separately.** Section 1 is items 1–33, Section 2 is
34–51. The denominator counts **applicable checks only** — an item marked N/A
leaves it. Most projects score well on the first and badly on the second; say so
when it happens, because it is normal and it is the right order to fix in.

**Three rules govern the scoring, and they are what make it worth anything:**

- **Cite a file and a line for every pass and every fail.** A pass with no
  citation is a guess wearing a tick.
- **UNKNOWN is a real answer.** If you cannot find evidence either way, mark it
  UNKNOWN and say what you would need to see. Never resolve an unknown into a
  pass to make the number look better.
- **Never assume a framework default handles it.** Verify it in this codebase.
  "Next.js does CSRF" is not a finding; the line that proves it is.

A generous audit is useless. If the score is bad, report the bad score.

**Grade severity by preconditions, not by feel.** Without a rule the same bug
lands in a different tier on a different day, and the user learns the tiers mean
nothing:

| Tier | Test |
|---|---|
| **Critical** | Unauthenticated remote attacker, default deployment, no preconditions — and the blast radius is the whole dataset, the money, or the account |
| **High** | Unauthenticated with no meaningful preconditions, but bounded damage; or authenticated with a single trivial precondition |
| **Medium** | Needs authentication plus 1–2 realistic preconditions — a specific role, a user action, a particular record state |
| **Low** | Needs 3+ preconditions, local-only access, or you cannot demonstrate a concrete attack path |

**Carry a confidence separately from severity.** They are different axes and
collapsing them is how a report becomes noise. Use three values: *Confirmed* —
you read the code and traced it, or you ran the request and saw it work.
*Likely* — the code reads as vulnerable but a guard elsewhere might catch it.
*Possible* — pattern-level suspicion you did not verify. Anything below
Confirmed says what would settle it. A Critical/Possible is a request to look
harder, not a claim; never present one as fact.

**Record the decision, not just the finding.** When the user declines to fix
something, write the reason down in the report — "accepted: internal tool, no
public signup" — and keep the report in the repo. Six months later that line is
the difference between a considered risk and a hole nobody noticed, and it is
the only thing that survives to the next audit or to anyone asking why.

That last section earns its place: telling the user "passwords are hashed with
bcrypt cost 12, cookies are httpOnly+Secure+SameSite=Lax, both fine" is how they
learn the audit was thorough rather than lucky.

### 3b. Ask about what the repository cannot show

Some of the things most likely to end a project leave no trace in the code.
List these as questions, do not score them, and do not guess at the answers:

- Are automated backups running, and has a restore actually been tested? An
  untested backup is a guess; people find out theirs were empty when they need
  them.
- Are billing and spend alerts on? For a solo app the first sign of abuse is
  usually financial, and a scraped key can cost thousands before anyone opens
  the dashboard.
- Do the registrar and DNS have 2FA and a transfer lock? Whoever controls DNS
  controls the app, the email and the ability to issue certificates — a bigger
  prize than the app login.
- Are CAA records set, and is there any dangling DNS? A subdomain still pointing
  at a service nobody owns any more can be claimed by someone else.
- Is there a WAF in front of it?
- Is the admin panel IP-allowlisted or behind a VPN? If it is only used from a
  few places, the rest of the internet has no reason to reach the login page.
- Are there canary tokens planted? Real breaches are quiet; a fake credential
  nobody has a legitimate reason to touch turns a maybe into a signal.
- Has there been a pen test or external review in the last 12 months? You cannot
  audit your own blind spots, and enterprise customers eventually ask.

### 3c. Report what is not on either list

Anything you found that no item covers goes here, and it matters most. The
checklist encodes what has already gone wrong for other people; this section is
where the thing specific to *this* codebase shows up. Never skip it because the
lists came back clean.

Then **stop and ask** whether to fix anything. Steps 1–3 are read-only: nothing
is changed, fixed or refactored until the user says so. Offer the sensible
default — "I'd fix all Critical and High now; the Medium items are one-liners I
can do in the same pass" — rather than making them adjudicate 20 items one at a
time.

### 4. Fix, most dangerous first, one at a time

**One item per turn.** Show the change, explain what it does, wait for approval,
then move to the next. Never batch fixes together: a batch cannot be reviewed,
and when something breaks nobody knows which change did it.

Work in the order you reported. Some things to keep in mind while fixing:

**A rotated key is the only fixed key.** Removing a secret from source does
nothing — it's in the git history, in a bundle someone downloaded, in a CI log.
Anything that has ever been committed or shipped to a browser must be rotated at
the provider. Say this explicitly and, when you can, tell the user exactly where
to click.

**Server-side is the only side.** Hiding an admin button is not access control.
When you fix an authorization gap, the check has to land where the request is
actually handled — the API route, the middleware, the RLS policy — and the
client-side version stays only as UX.

**Deny by default.** New RLS policies, new CORS origins, new upload types: start
from nothing allowed and add what the app demonstrably needs. The reverse order
is how holes get left open.

**Don't break the app to secure it.** After each fix, make sure the flow it
touches still works — run the build, run tests if they exist, exercise the
route. A locked-down app that 500s on login is not an improvement, and the user
will roll back the whole audit to get moving again.

### 5. Attack it yourself (item 25, the one that finds what a checklist can't)

Once the fixes are in, stop thinking like the author and start thinking like
someone trying to get in. Checklists find known categories; adversarial probing
finds the specific mistake in *this* app. Concretely:

- Call every mutating endpoint with `curl`, no auth header. What comes back?
- Call it as user A with user B's resource ID in the path or body. This — IDOR —
  is the single most common real hole in AI-generated CRUD apps, because the
  handler was written to fetch by ID and nobody added "…and check it's yours".
- Send the wrong types, negative numbers, a 10 MB string, `null`, arrays where
  objects go. Look for stack traces, hangs, and 500s that leak internals.
- Try to move price, role, `is_admin`, `user_id`, or quantity from the client.
- Hammer login, signup, and password-reset in a loop. Is there a limit?
- If files upload: upload a `.html`, a `.svg` with a script tag, something huge,
  something with `../` in the name.

Report what actually happened, with the command and the response. A working
exploit is worth more than a paragraph of concern — and if none of these work,
that's the most reassuring line in the whole report.

## Reference

`references/checklist.md` — all 51 items in full: detection, false positives,
and stack-specific fixes. Load it during step 2 and keep it open through step 4.
