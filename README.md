# risk-agent

Point it at something you built fast, and find out what goes wrong once it is public — before someone else finds it.

Software written quickly and shipped anyway carries a category of risk
that no test suite reports. The dependency whose licence forbids the way you are
shipping it. The email address collected with no lawful basis and no notice. The
chatbot that never tells anyone it is a machine. The API key on a plan with no
spending cap, behind an endpoint with no rate limit. None of these break the
build, and all of them are somebody else's leverage the moment they are noticed.

What exists today is two passes, both technical. One is the security pass before
launch — leaked keys, secrets in git history, missing authorisation, no rate
limiting, no spend alerts. The other is the pass over the technical and SEO tells
that keep a site out of search results. Both fix what you approve rather than
only reporting.

The legal and regulatory categories — licensing, data protection, consumer terms,
AI transparency, accessibility, cross-border transfers, cost blast radius, unit
economics, name collision — and the single command that runs all of them in one
ranked pass are the roadmap, not the current state. They are in
[BACKLOG.md](BACKLOG.md) and none of them are written yet.

## What this is not

**It is not legal advice, and it is not a lawyer.** It is a way of
finding the questions worth paying a lawyer to answer, and of clearing the ones
that never needed one. Every output says so, in those words.

It does not tell you that you are compliant. Nothing here produces a clean bill
of health, because that is not a thing an automated pass can honestly give.

It is not one skill. The security pass and the technical pass are separate
skills in this repository — `pre-launch-security-audit` and
`vibecode-tech-audit` — and where a finding belongs to the other one, it says so
and points there rather than duplicating it badly.

It does not track legislative change. Every regulatory claim carries the date
the text was checked, and a check from six months ago is a check from six months
ago.

## How to use this

These are skills for Claude, not a command-line tool. There is nothing to
build and nothing to import — you describe the work and the matching skill
fires on its own.

**In Claude Code**, clone the repository and link its skills into the
folders Claude Code reads (`~/.claude/skills/`):

```bash
git clone https://github.com/Keremozdemirra/risk-agent ~/agent-packs/risk-agent
cd ~/agent-packs/risk-agent
mkdir -p ~/.claude/skills
for s in skills/*; do ln -sfn "$PWD/$s" ~/.claude/skills/; done
```

The links point back into the clone, so `git pull` there brings in whatever
ships next. To copy the files instead of linking them, replace the
line starting with `for` with:

```bash
cp -R skills/* ~/.claude/skills/
```

Skills placed there are available in every session and every folder; start a
new session after installing.

Then simply ask. Each skill's `description` frontmatter is written to match how
the request actually gets phrased, in English or Turkish, so you do not name the
skill and generally should not have to think about which one applies.

**If nothing fires**, that is a defect in the skill rather than in how you
asked. The description was written for the wrong phrasing. Say what you asked
and what you expected, and it gets fixed — that feedback is more valuable than
working around it.

**What is actually built** is listed under Contents below and in the Done
section of [BACKLOG.md](BACKLOG.md). Everything under Queue is planned and does
not exist yet.

## Layout

```
agents/
  <name>.md           one specialist, its brief and its boundaries
skills/
  <name>/
    SKILL.md          the instruction, with triggering description frontmatter
    scripts/          only where deterministic code beats instruction
examples/
  <name>/             worked example on real input, with the output committed
```

`agents/` and `examples/` are empty so far.

## Roadmap

See [BACKLOG.md](BACKLOG.md). The first unchecked item is the one being built.

## Contents

| Skill | What it does |
| --- | --- |
| [harness-security-audit](skills/harness-security-audit) | Audit the agent setup itself (skills, agents, hooks, MCP servers, plugins, settings) as a supply chain: hidden Unicode, buried instructions, permission-bypass flags, outbound commands, unpinned sources, missing licences. Ships a read-only scanner script. |
| [pre-launch-security-audit](skills/pre-launch-security-audit) | The pass before anything goes public: secrets, permissions, exposed endpoints, dependency risk. |
| [vibecode-tech-audit](skills/vibecode-tech-audit) | Check a site against the 20 technical tells — titles, meta, og:image, canonical, sitemap, robots, 404, bundle size — that keep it out of search results and make its links unfurl as a grey box. |

These arrived already written and in daily use, rather than being built against the queue below — which is why most carry no item number. Some have Turkish bodies: they were written in the language they are used in, and translating them is a queue item rather than a blocker.

Everything still under Queue in [BACKLOG.md](BACKLOG.md) does not exist
yet.
## Licence

MIT. See [LICENSE](LICENSE).
