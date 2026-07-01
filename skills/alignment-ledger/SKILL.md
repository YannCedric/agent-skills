---
name: alignment-ledger
description: Maintain a lightweight evolving alignment ledger for product, UX, architecture, or strategy discussions. Use when a discussion spans turns/sessions, decisions need to persist, prior project state must be found, or exploration becomes a spec/epic/implementation plan. Always search for the existing ledger before creating a new one.
---

# alignment-ledger

Keep exploratory work from drifting by maintaining one compact source of truth: what is decided, what is assumed, what is open, what is parked, and whether the work is ready to build.

This skill is installable on its own. It also works as the durable-state layer for grill/planning workflows: clarify with one high-leverage question at a time, then capture confirmed decisions, assumptions, open questions, and readiness here.

## Default workflow

1. Find the current artifact if one exists; do not create a new ledger until the locator protocol below is exhausted.
2. If none exists, start with a chat-only snapshot or create a markdown file when the discussion is clearly durable.
3. Update the artifact after meaningful changes, not every message.
4. Reconcile new ideas against existing decisions before adding them.
5. Prune stale assumptions and open questions so the ledger stays small.
6. Before implementation, check whether the frame, decisions, and acceptance criteria are stable.

## Locator protocol

When resuming work, use this deterministic order:

1. Check the project root `HANDOFF.md` for a line like `Current alignment ledger: docs/<feature>-alignment-ledger.md`.
2. Check `docs/alignment-ledger.md`. If several feature ledgers exist, this file should act as the index and point to the active ledger.
3. Search likely files before creating anything new: `docs/*alignment-ledger*.md`, `docs/*decision-log*.md`, `docs/*design-state*.md`, and similar project handoff/spec files.
4. If exactly one plausible ledger exists, use it and add a pointer to `HANDOFF.md` when that file exists.
5. If multiple plausible ledgers exist and no pointer/index says which is active, ask before updating or creating.
6. Create a new ledger only after search fails or the user confirms a new scope.

Do not store mutable decision state in `AGENTS.md` unless the project already uses it that way. Instructions and project state should stay separate when possible.

## Artifact location

Use the lightest durable place available. These locations are suggestions, not requirements:

- Active project handoff/spec: update that file if it already owns design state, and add/update a `Current alignment ledger:` pointer when the actual ledger lives elsewhere.
- New project artifact: create `docs/alignment-ledger.md`.
- Feature-specific artifact: create `docs/<feature>-alignment-ledger.md`.
- Early exploration: keep a chat-only snapshot until the thread becomes durable.

For projects with multiple feature ledgers, keep `docs/alignment-ledger.md` as a short index:

```markdown
# Alignment Ledger Index

Updated: <date>

## Active
- <feature> — `docs/<feature>-alignment-ledger.md` — Status: active

## Archived
- <feature> — `docs/<feature>-alignment-ledger.md` — Archived because: <reason>
```

If the runtime cannot write files, maintain the ledger as a compact chat artifact. If the runtime uses another artifact system, use that instead.

Do not duplicate task status from issue trackers. The ledger is for rationale and alignment, not project management.

## Ledger template

```markdown
# Alignment Ledger: <feature/problem>

Updated: <date>

## Frame
- Goal:
- Primary user:
- Non-goals:
- Success signal:

## Decisions
- D1 — <confirmed choice> — Why: <rationale> — Source: <user/evidence/date>

## Assumptions
- A1 — <belief not yet proven> — Risk: H/M/L — Confidence: H/M/L — Validate by: <test/spike/interview>

## Open Questions
- Q1 — <question> — Why it matters: <what changes if answered differently>

## Parked / Rejected
- <idea> — Parked/rejected because: <reason>; revive if: <condition>

## Readiness
- Build/spec ready? No/Partial/Yes
- Missing before build:
- Acceptance criteria:
```

## When to update

Update or propose an update when:

- The user confirms, rejects, or changes direction.
- A new idea conflicts with an existing decision.
- An assumption gets evidence.
- Several substantive turns have passed and the thread is drifting.
- You are about to write an epic, spec, task breakdown, or implementation plan.
- You are about to code or delegate implementation work.
- The session is ending and the thread should survive.

## Reconcile before adding

Ask:

- Is this a decision, assumption, open question, or parked idea?
- Does it change the goal, user, scope, or success signal?
- Does it contradict a confirmed decision?
- Is the open question still plan-changing?
- Can two entries be merged or deleted?

If there is a contradiction, call it out and ask whether to supersede the old decision. Do not silently overwrite.

## Pruning rules

Keep only useful state:

- Promote validated assumptions to decisions.
- Demote weak decisions back to assumptions if confidence drops.
- Remove stale ideas unless they explain why a path was rejected.
- Keep only open questions that would change the plan.
- Mark important old decisions as superseded; delete unimportant clutter.

## Implementation gate

Do not shift from exploration to build unless:

- The frame is clear.
- The primary user is clear.
- Build-shaping decisions are confirmed.
- Plan-changing open questions are answered or explicitly deferred.
- Acceptance criteria are testable.
- The user has approved moving from exploration to spec/build.

If not ready, show the ledger snapshot and ask the single highest-leverage question with your recommended default.

## Response shape

Use this compact format when helpful:

```markdown
Alignment ledger updated:
- Decisions:
- Assumptions:
- Open:
- Parked/pruned:
- Readiness:

Next question:
Q: ...?
Default: ...
```

Keep replies short. The value of the skill is the maintained artifact, not a long explanation of the process.
