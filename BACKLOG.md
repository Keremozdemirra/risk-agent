# Backlog

Working queue. The next unchecked item is the one being built. An item stays
unchecked and picks up a `status:` note if it spans more than one working
session — finishing something half-built takes priority over starting the next
one.

Rules of thumb applied to every item:

- one job per skill, done properly, rather than a bundle of half-features
- a skill earns its place only if it beats writing the instruction out by hand
- the `description` frontmatter is the whole trigger mechanism — write it so the
  skill fires on how the work is actually asked for, including in Turkish
- every skill carries a worked example on real input, not a toy
- no claim about a law, regulation, standard or threshold without a citation to
  the instrument itself and the date the text was checked
- findings are ranked by exposure, never by how easy they are to write up
- every output states plainly that it is not legal advice, and names the
  findings that need a lawyer rather than burying them

---

## Done

- [x] **pre-launch-security-audit** · shipped 2026-08-20. Written before this repository existed and published here as-is; no queue item.
- [x] **vibecode-tech-audit** · shipped 2026-08-20. Written before this repository existed and published here as-is; no queue item.

## Queue

- [ ] **001 — one-pass-sweep** · The whole point of the repository: one command over a project that reports every finding across every category below, ranked by exposure — what it would cost, how likely anyone is to notice, how long it takes to fix. Keeps a state file so a re-run reports what changed rather than re-listing what you already read.
- [ ] **002 — licence-compliance** · Resolve the dependency tree and check each licence against how the product is actually shipped. Copyleft in a closed distribution, attribution never rendered anywhere, a licence with no text at all. Includes the case people forget: code pasted from an answer site with a licence attached to it.
- [ ] **003 — personal-data-map** · What personal data the system touches, where it enters, where it is stored, who else receives it, and on what lawful basis each use rests. Every other data-protection item depends on this one, and almost nobody has written it down.
- [ ] **004 — privacy-notice-from-the-map** · Generate the privacy notice from the data map rather than from a template, so it describes the system that exists. A notice that does not match reality is worse than none: it is a written admission.
- [ ] **005 — cookies-and-tracking** · What is set before consent, what counts as strictly necessary and what people wrongly assume counts, and whether the banner does what it claims. Analytics and session replay are the usual findings.
- [ ] **006 — terms-and-consumer-rights** · Terms of service against consumer law where the users actually are: withdrawal rights, auto-renewal and cancellation, terms a court would strike as unfair, and the ones that are unenforceable but still signal how you treat people.
- [ ] **007 — ai-transparency-duties** · When a system must disclose that a user is dealing with a machine, that content was generated, or that a decision was automated — and the practices that are simply prohibited. Cited to the instrument, with the date checked.
- [ ] **008 — accessibility-obligations** · Which accessibility duties bind a digital product in the markets it serves, and the specific failures that are both most common and most cheaply fixed. Checked against the running page, not asserted from the framework.
- [ ] **009 — cross-border-transfers** · Which processors receive data, in which countries, under what safeguard. The finding is usually a subprocessor nobody knew was in the chain.
- [ ] **010 — spend-blast-radius** · The economic one. Every metered dependency — model APIs, cloud, email, storage — with its cap, its rate limit and its alarm, and what a single bad day or a single hostile user would cost. Absence of a cap is the finding.
- [ ] **011 — unit-economics-check** · What one user costs to serve against what they pay, including the costs that scale with usage rather than with headcount. A product that loses money per user is a business problem before it is a pricing problem.
- [ ] **012 — name-and-brand-collision** · Check the product name against existing marks and live products in the markets you sell to, before it is on invoices, domains and a logo.
- [ ] **013 — data-provenance** · Where training data, scraped content and seeded databases came from, and whether the use you are making of them is permitted by the source's own terms.
- [ ] **014 — incident-readiness** · What has to exist before a breach, not after: the notification clocks that apply, who decides, what gets logged, and who has to be reachable.
- [ ] **015 — fix-what-can-be-fixed** · Apply the fixes that are code — headers, caps, rate limits, consent gating, attribution files — and stage the ones that are documents for review. Nothing is applied without approval, and each fix says what it changed and what it did not.
