# Alignment Ledger Usage Examples

These examples are synthetic patterns, not chat history.

## Good Trigger Prompts

- "Start an alignment ledger for this redesign."
- "Capture the decisions from this planning session."
- "Update the project decision log before we build."
- "Prune this spec so only active assumptions remain."
- "We changed direction; reconcile this with the old plan."

## Example Artifact

```markdown
# Alignment Ledger: Admin Reporting Redesign

Updated: 2026-05-19

## Frame
- Goal: Make weekly reporting faster for team leads.
- Primary user: Team lead.
- Non-goals: Full analytics builder, custom SQL, executive dashboards.
- Success signal: A lead can answer weekly status questions in under five minutes.

## Decisions
- D1 — Start with weekly team summary reports — Why: this is the repeated workflow with the clearest pain. — Source: planning discussion
- D2 — Keep custom report building out of v1 — Why: it expands scope before the core summary flow is validated. — Source: scope review

## Assumptions
- A1 — Team leads trust generated summaries if source metrics are visible — Risk: M — Confidence: M — Validate by: prototype review

## Open Questions
- Q1 — Should exports be PDF or CSV first? — Why it matters: changes formatting and sharing work.

## Parked / Rejected
- Custom query builder — Parked because it turns v1 into an analytics platform; revive if three pilot users ask for it.

## Readiness
- Build/spec ready? Partial
- Missing before build: export format decision, source metric list
- Acceptance criteria:
  - User can generate a weekly summary.
  - Source metrics are visible.
  - Export path is clear.
```

## Example Update

User:

> We decided CSV is enough for v1.

Assistant:

```markdown
Alignment ledger updated:
- Decisions:
  - D3 — CSV export first — Why: fastest path for spreadsheet review and lower formatting risk.
- Open:
  - Removed Q1 because export format is now decided.
- Readiness:
  - Still partial; source metric list remains open.

Next question:
Q: Which source metrics are required for the weekly summary?
Default: completed work, blocked work, overdue work, and owner.
```
