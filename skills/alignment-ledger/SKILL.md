---
name: alignment-ledger
description: Maintain a lightweight evolving alignment ledger for product, UX, architecture, or strategy discussions. Use when the user asks to start or update an alignment ledger, decision log, design state, exploration log, product state, or durable planning artifact; when a discussion spans multiple turns/sessions; when decisions, assumptions, open questions, or parked ideas need tracking; or before turning exploration into a spec, epic, or implementation plan.
---

# alignment-ledger

Keep exploratory work from drifting by maintaining one compact source of truth: what is decided, what is assumed, what is open, what is parked, and whether the work is ready to build.

This skill is self-contained. Do not assume any companion skill exists. If the user asks to combine this with another workflow, follow that request at the session level.

## Default workflow

1. Find the current artifact if one exists.
2. If none exists, start with a chat-only snapshot or create a markdown file when the discussion is clearly durable.
3. Update the artifact after meaningful changes, not every message.
4. Reconcile new ideas against existing decisions before adding them.
5. Prune stale assumptions and open questions so the ledger stays small.
6. Before implementation, check whether the frame, decisions, and acceptance criteria are stable.

## Artifact location

Use the lightest durable place available. These locations are suggestions, not requirements:

- Existing project handoff/spec: update that file.
- New project artifact: create `docs/alignment-ledger.md`.
- Feature-specific artifact: create `docs/<feature>-alignment-ledger.md`.
- Early exploration: keep a chat-only snapshot until the thread becomes durable.

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
