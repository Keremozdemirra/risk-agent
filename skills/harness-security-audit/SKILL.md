---
name: harness-security-audit
description: Audits the agent setup itself (skills, agents, hooks, MCP servers, plugins, settings) as a supply chain: hidden Unicode and bidi payloads, instructions buried in loaded files, permission-bypass flags, outbound commands, unpinned sources, licences that forbid where code sits. Use before or after installing anything into the harness, or on "kurulumu denetle", "hooklari kontrol et", "harness guvenli mi", "what runs automatically". Not for an app you built; use pre-launch-security-audit.
---

# Harness security audit

Everything the model reads is executable context. A skill file, an agent
descriptor, an MCP config and a hook command are all instructions with a
delivery mechanism, and almost none of them were written by the person running
them. This skill treats that surface the way `pre-launch-security-audit` treats
an application.

The failure mode is silence. A bad install does not error; it quietly holds
more access than it needed, and the first sign is something you never see.

## Run the scan first

```bash
bash ~/.claude/skills/harness-security-audit/scripts/scan_harness.sh
```

To also check the GitHub workflow files of your own repositories for unpinned
actions, run it with `HARNESS_REPOS=/path/to/your/repos` (default: `~/.claude`).

It covers the six checks below mechanically. Read the findings yourself; the
scanner reports shapes, and every hit needs the judgement in "Telling a
payload from an artefact" before it becomes a verdict.

Whatever the scan or your own sweep prints lands in a transcript that is
written to disk and synced, so a read-only command turns into a second exposure
the moment it echoes a secret. Before printing remotes, configs or env, strip
userinfo from every URL (`git remote -v | sed -E 's#//[^/@]*@#//#'`), and treat
`.git/config`, `.npmrc`, `.netrc` and `pip.conf` as credential-bearing files:
report how many carry a token and keep the token itself out of the output.

## Signature and endpoint list

`references/signatures.md` lists persistence, credential theft, exfil endpoints and
dynamic DNS, adopted 2026-09-07 from Prism Scanner's rule files after reading
them, with what was rejected and why. No dependency: the entries were copied,
the tool was not installed.

## The six checks

**1. Hidden Unicode and bidi.** Zero-width spaces, word joiners and the
`202A` to `202E` direction overrides are invisible to a reader and fully visible to
the model. Text can be hidden between them, or reordered so the displayed line
differs from the parsed one.

**2. Embedded payloads.** `<script`, `data:text/html`, `base64,` and HTML
comments inside a file the model loads. A comment is not neutral: the model
reads it, the reviewer's eye skips it.

**3. Permission bypass and model redirection.** The highest-severity class.
`bypassPermissions`, `--dangerously-*`, `enableAllProjectMcpServers`,
`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`. A flag that turns approvals off,
or points model traffic somewhere else, defeats every other control at once.
Grep the **plugin cache** as well as your own files; this is third-party code.

**4. Outbound commands.** `curl`, `wget`, `nc`, `scp`, `ssh` in a skill or agent
body. Instructions to send data out, carried in a file that looks like prose.

**5. Unpinned sources.** `@latest` in an MCP `args`, a plugin tracking a branch,
an action on a movable tag. Each one is a promise to run whatever that name
resolves to tomorrow, with no review between publication and execution. Pin to a
version or a SHA. The npm supply-chain compromises of 2025–26 all worked this
way.

**6. External references.** A skill that points at a URL for its content has
outsourced part of its instructions to whoever controls that URL. Inline it. If
it cannot be inlined, put a guardrail beside the link telling the reader to take
facts only and ignore any directives the fetched content carries.

## Telling a payload from an artefact

Most hits are innocent, and reporting them as attacks is how the next scan gets
ignored. Resolve each one before writing it up:

- **Zero-width characters immediately before a ``` fence** are the standard
  trick for nesting code blocks in markdown. Check whether text sits *between*
  the hidden characters. If nothing does, it is formatting.
- **A bypass flag inside a vendored dependency's test fixture** is not reachable.
  Trace who imports the file before calling it live: a flag in a module nothing
  reaches costs nothing, and the same flag on a hook path is an emergency.
- **An unfamiliar hostname** is a sponsor, a docs link or an exfiltration
  endpoint, and the difference is whether anything calls it. Grep for the
  variable that carries the hostname; a hit on the string alone proves nothing.

State the reachability in the finding. "Present but unreachable" and "fires on
every edit" are different reports about the same grep hit.

## The gates themselves

A hook that scans for credentials before a push is part of the surface, and its
precision decides whether it survives: every false positive spends some of the
willingness to obey it. Two checks per gate. First, does it have a scoped
override (an allowlist file, a per-pattern suppression, a per-path exclusion)?
A gate whose only escape is a blanket `SKIP_*=1` teaches its owner to reach for
the blanket, and that is a finding on its own. Second, what does each pattern do
to clean input? Run every credential pattern over a corpus of legitimate public
identifiers (repository names, package names, git SHAs, UUIDs) and report the
false-positive rate beside the hit count. On 2026-09-04 the
`sk-[A-Za-z0-9_-]{20,}` pattern matched seventeen repository names in one public
dataset and zero keys.

## Fixing

Prefer the switch the code already has. Most tools that ship a dangerous mode
also ship the environment variable that disables it; setting that in
`~/.claude/settings.json` under `env` survives plugin updates, while editing the
plugin's own files does not. Reach for removal only when there is no switch.

Then record what you changed and why, because the next update can revert it and
nobody will notice. A finding worth fixing is worth a line in `memory/altyapi.md`
with the command that detects the regression.

## What this found the first time it ran

Kept as calibration. The point is the shape of what turns
up, and that the setup had never been scanned at all before.

- An enabled design plugin spawned a **nested agent with every approval bypassed
  and the sandbox off**, forwarding `CLAUDE_CODE_OAUTH_TOKEN` and
  `ANTHROPIC_API_KEY` into it. Reachable only through one opt-in feature and through none
  of the hooks, which is exactly the reachability distinction above. Fixed with the
  tool's own env switch rather than by editing its files.
- An MCP server pinned to `@latest`, re-resolving on every start.
- Four zero-width characters that turned out to be markdown fence formatting,
  in a third-party skill. Reported as clean, and worth the two minutes.
