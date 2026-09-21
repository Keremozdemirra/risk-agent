---
name: pre-launch-security-audit
description: Audits an app against 51 security checks in two scored sections, citing file and line for every pass or fail, then reads for logic flaws and fixes what you approve one at a time. Use before shipping or going live: "guvenlik denetimi yap", "yayina almadan kontrol et", "guvenli mi", "skor ver", "API anahtarim sizmis mi", "is this production-ready". Not for SEO tells; use vibecode-tech-audit.
---

# Pre-launch security audit

AI-assisted code gets built to make the happy path work. Nothing in that loop
forces the app to be safe: the model writes what was asked for, the app runs,
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
before you start; it determines which of the 51 items are load-bearing and
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
cover. Ask the user where it is installed.

It greps for key-shaped strings, checks whether `.env` is tracked in git and
whether it appears in history, flags `dangerouslySetInnerHTML` and `eval`,
finds string-interpolated SQL, and reports dependency audit status. It is a
starting point that catches the obvious cases fast. It does not replace
reading the auth and data-access code yourself, which is where the serious
findings almost always are.

A zero-hit grep is a hypothesis about the query. Before reporting a protection
as absent, grep for the name as it appears in code (`localStorage`, `SameSite`,
`csurf`) as well as the prose phrase ("local storage", "same site"), then read
the candidate file. The same rule holds when you check whether
`references/checklist.md` already covers a topic: read the candidate items
before reporting a gap.

**Count and hash secrets; keep their values out of the transcript.**
Investigating a leaked credential can extend the leak: the transcript persists
to disk, so every printed value is a new copy. Four rules for any sweep, by
scanner or by hand:

- Enumerate the file set with `find`, then scan each file. Recursive grep picks
  its own file set from defaults you never see: `grep` on `PATH` may be GNU
  grep, BSD grep, ugrep or ripgrep, and ugrep's recursion skips `.git` even
  with `--hidden`. Eleven `.git/config` files carrying an `x-access-token` URL
  once came back clean this way. Record `grep --version`, plant a known string
  in a `.git/config` and prove the method finds it before trusting a clean
  result. Reach `.git/config`, `.env`, `.npmrc`, `.netrc`, `pip.conf`,
  `.aws/credentials` and `.ssh/` by explicit path.
- Count with `grep -c` for lines and files, `grep -o '<pattern>' | wc -l` for
  occurrences, and name which of the two the report gives; a line holding two
  tokens makes the counts differ. Identify with a digest of the bare match, so
  the value stays out of context:
  `grep -ohE '<pattern>' <files> | sort -u | while read -r s; do printf '%s' "$s" | shasum -a 256 | cut -c1-12; done`.
  Frame both sides byte-identically. A trailing newline on one side makes one
  token look like two and manufactures a finding.
- Treat `git remote get-url`, `git remote -v`, `git config --list` and
  environment dumps as secret-printing commands. For inventory, strip userinfo
  from URLs first: `git remote -v | sed -E 's#//[^/@]*@#//#'`.
- Report distinct secrets first, occurrences second. Rotation is per secret; an
  occurrence count alone invites an incomplete rotation.

Then walk `references/checklist.md`, which has all 51 items with what to grep
for, how to tell a real finding from a false positive, and the fix per stack.
Read it; the detail there is the substance of this skill.

### 2b. Read for the five things grepping cannot see

The checklist and the scanner are both pattern work: they find a bad call, a
missing flag, a key in the wrong file. The bugs that survive a clean checklist
pass are the ones where **no single function is wrong** and the hole only exists
in how the pieces fit together. Budget real reading time for these five, and
trace the call graph for each:

**Business logic flaws.** A coupon applies twice because the check and the
deduction aren't atomic. Credits go negative because the balance is read, then
written, with an await in between. Look at every place money, quota, or
inventory changes, and ask what happens if the same request arrives twice.

**Access control that breaks across files.** The route handler authenticates and
the middleware doesn't, or the reverse, and one route was registered outside
the middleware. Check that every admin and owner-scoped route is covered by the
same guard, and that the guard is applied where routing actually resolves.

**Multi-step data flow.** User input passes through three functions before it
reaches a query, a shell call, or a template. No single function looks unsafe.
Follow the parameter: start at the request body and walk forward to the sink.

**Context-dependent safety.** A helper is safe on the path that sanitizes first
and dangerous on the path that doesn't. When you find a function used in more
than one place, check every call site before you clear it.

**Untrusted text that a model later reads.** A scheduled script fetches
repository names and descriptions from an API and writes them verbatim into
markdown files that a coding agent loads as context. Every function is correct;
the hole exists only in the composition. The model's context window is a sink
with the same standing as a query or a shell call, so start at every network
fetch and follow the response text forward, asking whether any consumer is an
LLM. Fix at the write site by bounding: fence the field, truncate it, and mark
it as remote data. Classifying the text as malicious is unreliable and stays
out of the fix.

This is the pass that justifies a human-grade audit over a scanner. If you skip
it, say so in the report rather than implying the code was cleared.

### 3. Report before touching anything

The user needs to see the shape of the problem before code starts changing.
Group findings by how much damage they do, with the worst first.

**Open with two lines that can be screenshotted**, then the detail:

```markdown
MUST-HAVES: 19 / 24
NOT SO OBVIOUS: 3 / 16

## Security audit: <project>

**Verdict:** <not safe to ship / ship with caveats / clean>, one sentence why.

### Critical: an attacker can do this today
| # | Finding | Where | Confidence | What an attacker does |
|---|---------|-------|-----------|----------------------|
| 1 | Supabase service_role key in client bundle | `src/lib/db.ts:4` | Confirmed | Reads and deletes every row in every table, bypassing RLS |

### Should fix: real gaps, lower urgency
### Passed: one line each, no elaboration
### Unknown: what you could not determine, and what you would need to see
### Anything else: findings no item on either list covers
### Ask me: the questions in step 3b, unscored
### Fix first: the three highest-impact items, in order, each with why it ranks there
```

**Score the two sections separately.** Section 1 is items 1–33, Section 2 is
34–51. The denominator counts **applicable checks only**; an item marked N/A
leaves it. Most projects score well on the first and badly on the second; say so
when it happens, because it is normal and it is the right order to fix in.

**Four rules govern the scoring, and they are what make it worth anything:**

- **Cite a file and a line for every pass and every fail.** A pass with no
  citation is a guess wearing a tick.
- **UNKNOWN is a real answer.** If you cannot find evidence either way, mark it
  UNKNOWN and say what you would need to see. Never resolve an unknown into a
  pass to make the number look better.
- **Never assume a framework default handles it.** Verify it in this codebase.
  "Next.js does CSRF" is not a finding; the line that proves it is.
- **State the denominator beside every count.** Files matched over files
  present, depth searched, window measured, layer parsed. "Zero" means zero
  within the named scope: a `find -maxdepth 4` clone sweep missed twelve
  repositories, and a glob over `projects/*/*.jsonl` matched 41 of 181 files
  and skipped every one under `subagents/`. Prefer `find` over globs for
  recursive trees, and strip scripts, styles and comments before counting
  visible text.

A generous audit is useless. If the score is bad, report the bad score.

**Grade severity by preconditions.** Without a rule the same bug
lands in a different tier on a different day, and the user learns the tiers mean
nothing:

| Tier | Test |
|---|---|
| **Critical** | Unauthenticated remote attacker, default deployment, no preconditions, and the blast radius is the whole dataset, the money, or the account |
| **High** | Unauthenticated with no meaningful preconditions, but bounded damage; or authenticated with a single trivial precondition |
| **Medium** | Needs authentication plus 1–2 realistic preconditions: a specific role, a user action, a particular record state |
| **Low** | Needs 3+ preconditions, local-only access, or you cannot demonstrate a concrete attack path |

**Carry a confidence separately from severity.** They are different axes and
collapsing them is how a report becomes noise. Use three values. *Confirmed*:
you read the code and traced it to the outcome, or you ran the request and saw
the outcome your severity sentence asserts. *Likely*: the code reads as
vulnerable but a guard elsewhere might catch it, or your probe showed one link
of the chain and the rest is open. *Possible*: pattern-level suspicion you did
not verify. Anything below Confirmed says what would settle it. A
Critical/Possible is a request to look harder; present it as an open question.

Confirmed is tied to the asserted outcome, and a probe can show less than it
feels like it showed. Markup reaching a sink confirms the sink; whether an
executing payload survives the trip is a separate link. In one audit the probe
showed markup arriving, the finding went out as Confirmed, and the fixing
lead's re-measurement found the runtime truncates the echo to about ten
characters, too short for any event handler. The defect was real; the rating
was one tier high. Before writing Confirmed, ask: what exactly did my probe
show, and is that the same thing my severity sentence asserts? When the answer
is a link short of the chain, rate it Likely and name the open question.

**Record the decision, not just the finding.** When the user declines to fix
something, write the reason down in the report ("accepted: internal tool, no
public signup") and keep the report in the repo. Six months later that line is
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
  controls the app, the email and the ability to issue certificates, a bigger
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
default: "I'd fix all Critical and High now; the Medium items are one-liners I
can do in the same pass". That spares them adjudicating 20 items one at a
time.

### 4. Fix, most dangerous first, one at a time

**One item per turn.** Show the change, explain what it does, wait for approval,
then move to the next. Never batch fixes together: a batch cannot be reviewed,
and when something breaks nobody knows which change did it.

Work in the order you reported. Some things to keep in mind while fixing:

**A rotated key is the only fixed key.** Removing a secret from source does
nothing: it's in the git history, in a bundle someone downloaded, in a CI log.
Anything that has ever been committed or shipped to a browser must be rotated at
the provider. Say this explicitly and, when you can, tell the user exactly where
to click.

**Server-side is the only side.** Hiding an admin button is not access control.
When you fix an authorization gap, the check has to land where the request is
handled (the API route, the middleware, the RLS policy) and the client-side
version stays only as UX.

**Deny by default.** New RLS policies, new CORS origins, new upload types: start
from nothing allowed and add what the app demonstrably needs. The reverse order
is how holes get left open.

**Don't break the app to secure it.** After each fix, make sure the flow it
touches still works: run the build, run tests if they exist, exercise the
route. A locked-down app that 500s on login is not an improvement, and the user
will roll back the whole audit to get moving again.

**Someone else's fix is a claim under audit.** Its test was written while
looking at the instances being fixed, so the matching predicate tends to match
those instances and miss the class. Re-derive the property from the source by
your own route before you read the test: enumerate the whole sink family
yourself (`innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`,
`eval`, template-string `href` and `src`), grep for all of it, then read the
test to see which members it covers. One fix shipped fifteen green tests
filtered on the substring `innerHTML`; two live `insertAdjacentHTML` sinks
survived, one of them interpolating a caught exception's message, and V8
echoes a fragment of the offending input in a `JSON.parse` error. A passing
test whose matching rule is narrower than the vulnerability class is a finding
in its own right, because it turns an open question into a settled one.

### 5. Attack it yourself (item 25, the one that finds what a checklist can't)

Once the fixes are in, stop thinking like the author and start thinking like
someone trying to get in. Checklists find known categories; adversarial probing
finds the specific mistake in *this* app. Concretely:

- Call every mutating endpoint with `curl`, no auth header. What comes back?
- Call it as user A with user B's resource ID in the path or body. This is IDOR,
  the single most common real hole in AI-generated CRUD apps, because the
  handler was written to fetch by ID and nobody added "…and check it's yours".
- Send the wrong types, negative numbers, a 10 MB string, `null`, arrays where
  objects go. Look for stack traces, hangs, and 500s that leak internals.
- Try to move price, role, `is_admin`, `user_id`, or quantity from the client.
- Hammer login, signup, and password-reset in a loop. Is there a limit?
- If files upload: upload a `.html`, a `.svg` with a script tag, something huge,
  something with `../` in the name.

Report what actually happened, with the command and the response. A working
exploit is worth more than a paragraph of concern, and if none of these work,
that's the most reassuring line in the whole report.

## Reference

`references/checklist.md` holds all 51 items in full: detection, false positives,
and stack-specific fixes. Load it during step 2 and keep it open through step 4.
