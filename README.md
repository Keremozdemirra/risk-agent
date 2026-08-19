# risk-agent

Point it at something you built fast, and find out what could become a legal, regulatory or financial problem — in one pass, before someone else finds it.

Software written quickly and shipped anyway carries a category of risk
that no test suite reports. The dependency whose licence forbids the way you are
shipping it. The email address collected with no lawful basis and no notice. The
chatbot that never tells anyone it is a machine. The API key on a plan with no
spending cap, behind an endpoint with no rate limit. None of these break the
build, and all of them are somebody else's leverage the moment they are noticed.

This repository is the single pass over all of it. One command, every category —
licensing, data protection, consumer terms, AI transparency, accessibility,
cross-border transfers, cost blast radius, unit economics, name collision —
ranked by what it would actually cost you, not by how easy it was to detect.

Then it fixes what can be fixed in code, drafts what has to be written, and says
plainly which findings need a lawyer rather than pretending it is one.

## What this is not

**It is not legal advice, and it is not a lawyer.** It is a way of
finding the questions worth paying a lawyer to answer, and of clearing the ones
that never needed one. Every output says so, in those words.

It does not tell you that you are compliant. Nothing here produces a clean bill
of health, because that is not a thing an automated pass can honestly give.

It is not a security audit — `pre-launch-security-audit` does that — and not an
SEO or technical audit, which is `vibecode-tech-audit`. Where a finding belongs
to one of those, it says so and points there rather than duplicating it badly.

It does not track legislative change. Every regulatory claim carries the date
the text was checked, and a check from six months ago is a check from six months
ago.

## How to use this

These are skills for Claude, not a command-line tool. There is nothing to
install and nothing to import — you describe the work and the matching skill
fires on its own.

**In Claude Code or Cowork**, once the skills are on your machine:

```bash
bash ~/Desktop/agent/_setup/sync-skills.sh
```

That clones every agent repository and links its `skills/` into `~/.claude/skills`,
so they are available in every session and every folder. Re-run it whenever the
daily loop ships something new — it pulls rather than re-clones.

Then simply ask. Each skill's `description` frontmatter is written to match how
the request actually gets phrased, in English or Turkish, so you do not name the
skill and generally should not have to think about which one applies.

**If nothing fires**, that is a defect in the skill rather than in how you
asked. The description was written for the wrong phrasing. Say what you asked
and what you expected, and it gets fixed — that feedback is more valuable than
working around it.

**What is actually built** is the Done section of [BACKLOG.md](BACKLOG.md).
Everything under Queue is planned and does not exist yet. The daily loop builds
one item a day; the table above is the intended shape, not the current state.

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

## Roadmap

See [BACKLOG.md](BACKLOG.md). The first unchecked item is the one being built.

## Planned contents

Nothing here is built yet. This table is the intended shape, and the daily loop
fills it in one item at a time.

| # | Skill | What it does |
| --- | --- | --- |
| 001 | [one-pass-sweep](skills/one-pass-sweep) | The whole point of the repository: one command over a project that reports every finding across every category below, ranked by exposure — what it would cost, how likely anyone is to notice, how long it takes to fix. |
| 002 | [licence-compliance](skills/licence-compliance) | Resolve the dependency tree and check each licence against how the product is actually shipped. |
| 003 | [personal-data-map](skills/personal-data-map) | What personal data the system touches, where it enters, where it is stored, who else receives it, and on what lawful basis each use rests. |
| 004 | [privacy-notice-from-the-map](skills/privacy-notice-from-the-map) | Generate the privacy notice from the data map rather than from a template, so it describes the system that exists. |
| 005 | [cookies-and-tracking](skills/cookies-and-tracking) | What is set before consent, what counts as strictly necessary and what people wrongly assume counts, and whether the banner does what it claims. |
| 006 | [terms-and-consumer-rights](skills/terms-and-consumer-rights) | Terms of service against consumer law where the users actually are: withdrawal rights, auto-renewal and cancellation, terms a court would strike as unfair, and the ones that are unenforceable but still signal how you treat people. |
| 007 | [ai-transparency-duties](skills/ai-transparency-duties) | When a system must disclose that a user is dealing with a machine, that content was generated, or that a decision was automated — and the practices that are simply prohibited. |
| 008 | [accessibility-obligations](skills/accessibility-obligations) | Which accessibility duties bind a digital product in the markets it serves, and the specific failures that are both most common and most cheaply fixed. |
| 009 | [cross-border-transfers](skills/cross-border-transfers) | Which processors receive data, in which countries, under what safeguard. |
| 010 | [spend-blast-radius](skills/spend-blast-radius) | The economic one. |
| 011 | [unit-economics-check](skills/unit-economics-check) | What one user costs to serve against what they pay, including the costs that scale with usage rather than with headcount. |
| 012 | [name-and-brand-collision](skills/name-and-brand-collision) | Check the product name against existing marks and live products in the markets you sell to, before it is on invoices, domains and a logo. |
| 013 | [data-provenance](skills/data-provenance) | Where training data, scraped content and seeded databases came from, and whether the use you are making of them is permitted by the source's own terms. |
| 014 | [incident-readiness](skills/incident-readiness) | What has to exist before a breach, not after: the notification clocks that apply, who decides, what gets logged, and who has to be reachable. |
| 015 | [fix-what-can-be-fixed](skills/fix-what-can-be-fixed) | Apply the fixes that are code — headers, caps, rate limits, consent gating, attribution files — and stage the ones that are documents for review. |

## Licence

MIT. See [LICENSE](LICENSE).
