---
name: pre-launch-security-audit
description: Audits an app against the 23 things that must be true before it goes live - leaked keys, secrets in git history, missing authorization rules, client-side-only auth, no rate limiting, unvalidated input, open uploads, wildcard CORS, missing security headers, weak password hashing, insecure cookies, leaky errors and logs, SQL injection, XSS, unverified webhooks, unprotected admin routes, vulnerable dependencies, no backups, fake account deletion, no spend alerts - then attacks it the way someone hostile would, and fixes what the user approves, most dangerous first. Use whenever the user is about to ship, deploy, launch or go live; asks "is this safe / secure / production-ready" or wants a security review, audit, pentest or hardening pass; mentions leaked API keys, exposed secrets, a committed .env, RLS policies, auth bugs, API abuse or a surprise cloud bill; and proactively before any AI-generated or vibecoded app meets real users, since none of these happen on their own.
---

# Pre-launch security audit

AI-assisted code gets built to make the happy path work. Nothing in that loop
forces the app to be safe — the model writes what was asked for, the app runs,
the demo looks great, and every one of the 23 items below is quietly still
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
before you start — it determines which of the 23 items are load-bearing and
which are not applicable.

Also establish what the app actually handles. An app with no accounts, no
payments, and no user data has a much shorter real risk list than one holding
customer records, and saying so up front keeps the report honest.

### 2. Scan

Run the bundled scanner for the mechanical checks, then read code for the rest:

```bash
# scripts/scan_secrets.py, resolved relative to this skill's own directory
python3 "$SKILL_DIR/scripts/scan_secrets.py" <project-dir>
```

It greps for key-shaped strings, checks whether `.env` is tracked in git and
whether it appears in history, flags `dangerouslySetInnerHTML` and `eval`,
finds string-interpolated SQL, and reports dependency audit status. It is a
starting point that catches the obvious cases fast — it does not replace
reading the auth and data-access code yourself, which is where the serious
findings almost always are.

Then walk `references/checklist.md`, which has all 23 items with what to grep
for, how to tell a real finding from a false positive, and the fix per stack.
Read it — the detail there is the substance of this skill.

### 3. Report before touching anything

The user needs to see the shape of the problem before code starts changing.
Group findings by how much damage they do, not by checklist order:

```markdown
## Security audit — <project>

**Verdict:** <not safe to ship / ship with caveats / clean> — one sentence why.

### Critical — an attacker can do this today
| # | Finding | Where | What an attacker does |
|---|---------|-------|----------------------|
| 1 | Supabase service_role key in client bundle | `src/lib/db.ts:4` | Reads and deletes every row in every table, bypassing RLS |

### High — likely exploited once anyone looks
### Medium — real but bounded
### Notes — checked and fine, or not applicable here
```

That last section earns its place: telling the user "passwords are hashed with
bcrypt cost 12, cookies are httpOnly+Secure+SameSite=Lax, both fine" is how they
learn the audit was thorough rather than lucky.

Then ask which to fix. Offer the sensible default — "I'd fix all Critical and
High now; the Medium items are one-liners I can do in the same pass" — rather
than making them adjudicate 20 items one at a time.

### 4. Fix, most dangerous first

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

### 5. Attack it yourself (item 23, the one that finds what a checklist can't)

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

`references/checklist.md` — all 23 items in full: detection, false positives,
and stack-specific fixes. Load it during step 2 and keep it open through step 4.
