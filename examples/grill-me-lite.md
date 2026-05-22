# Grill Me Lite Usage Examples

These examples are synthetic patterns, not chat history.

## Good Trigger Prompts

- "Grill me before we redesign this dashboard."
- "Stress test this API migration plan."
- "Think hard before turning this idea into tickets."
- "Ask me questions before you implement the pricing page."
- "Help me decide the MVP for this editor."

## Example Questions

Use one question at a time. Include a default and the consequence.

### Product Scope

Q: Who is v1 for: admin, manager, or end customer?

Default: manager.

Consequence: choosing manager keeps the workflow focused on daily operational pain instead of broad account-level reporting.

### UX Direction

Q: Should the first screen optimize for creation, review, or monitoring?

Default: review.

Consequence: review-first makes the product useful even when automation is imperfect.

### Architecture

Q: Is this a reversible UI change or a data-contract change?

Default: data-contract change.

Consequence: if downstream consumers depend on it, the rollout needs compatibility and migration gates.

### Task Planning

Q: Should we split this by user journey, technical layer, or risk?

Default: risk.

Consequence: risk-first lets us validate the riskiest assumption before polishing low-risk UI.

## Output Shape

```markdown
Decisions locked:
- ...

Assumptions:
- ...

Plan:
- ...

Gates:
- ...

Open questions:
- ...
```
