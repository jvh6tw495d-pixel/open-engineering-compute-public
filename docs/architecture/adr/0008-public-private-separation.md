# ADR 0008: OEC is developed as a fully independent, private-reference-free repository

- **Status:** accepted
- **Date:** 2026-07-25

## Context

OEC is developed alongside a private, commercial product, in the same
user's environment but as a separate, standalone repository. The
project's master planning document (external to this repo — see
"References" below) sets an absolute rule: nothing in this repository
may reference, directly or indirectly, any private system, client,
commercial project, proprietary formulation, or internal codename.

This rule was enforced from the very first commit (a fresh local `git
init`, no inherited history — see `docs/sprints/sprint-00-foundation.md`)
but, through Sprint 07, was never captured as an in-repo ADR — the
policy existed only in the external master document. A holistic review
at the end of Sprint 07 flagged this as a real, if low-urgency, gap:
`0008` is one of the master document's originally reserved ADR slots
(alongside `0006`/`0009`), and a hard compliance rule with real release
consequences deserves to be discoverable from inside the repository
itself, not only from a document that may not travel with it.

## Decision

1. **No private references, anywhere, ever.** This repository — source
   code, tests, documentation, comments, class/file names, commit
   messages, branch names, issues, pull requests, examples, fixtures,
   screenshots, diagrams, metadata, CI configuration, and git history —
   must never mention any private system, client, commercial project,
   internal codename, proprietary formulation, commercial rule, funding
   strategy, tariff logic, operational data, internal source code, or
   private repository name. This is not a style guideline; it is a
   hard gate checked before any public release.
2. **No remote, no push, until an explicit sanitization sprint.** During
   incubation, this repository stays local-only (`git init`, no
   `origin`, `main` branch, Conventional Commits) — verified at every
   sprint boundary that `git remote -v` is empty. Before any public
   repository is created, a dedicated sanitization sprint (candidate:
   the handbook's "Fase 9 — Hardening e Public Alpha") must: review
   architecture, review licenses and dependencies, remove any internal
   reference, and start a **new, clean git history** in the eventual
   public repository — never publish this private-incubation history
   directly, even with files removed after the fact (removed files
   remain recoverable from history).
3. **Public positioning is fixed independently of anything private**:
   "Open Engineering Compute is an open framework for executable,
   versioned and auditable engineering skills." No public-facing text
   ties OEC's identity to any specific private product or organization
   beyond its own authorship.

## Verification

Compliance is not assumed — it is checked. A holistic review at the end
of Sprint 07 grepped the full working tree, the full git history
(`git log -p` / `git rev-list --all`), commit messages, and branch
names against the master document's forbidden-term list plus a broader
proprietary-smell set, and found zero matches. This is the kind of
check every future sprint boundary (and, non-negotiably, the eventual
sanitization sprint) must repeat — not a one-time pass that's assumed
to hold forever as the codebase grows.

## Consequences

- Every skill's methodology, every example, and every fixture must be
  either standard public-domain engineering knowledge (textbook
  formulas, published algorithms) or synthetic data invented for this
  project — never derived from real private operational data.
- A contributor (human or agent) who is unsure whether something is
  "private enough" to avoid should default to leaving it out and
  flagging the uncertainty, per the master document's own instruction
  to report blockers rather than guess.
- This ADR does not itself enumerate the forbidden-term list (that list
  lives in the master document and may be extended without needing an
  ADR revision each time) — it documents the *policy*, not the list.
- No remote is configured as of this ADR; the first `git remote add`
  or `git push` in this repository's history is a decision significant
  enough to warrant explicit confirmation at the time, not something
  any future sprint should do incidentally.

## References

- OEC master planning document, section 2 ("Regra absoluta de
  separação") and section 30.2 ("Git local durante a incubação") — the
  authoritative source for this policy; kept external to this
  repository by design, since the document itself may reference the
  private context this ADR exists to keep out of OEC.
