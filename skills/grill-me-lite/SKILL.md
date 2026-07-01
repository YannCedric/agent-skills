---
name: grill-me-lite
description: Use before building ambiguous product, UX, architecture, API, data-model, or task plans. Trigger on "grill me", "stress test this", "think hard", "help me decide", or "ask me questions before building". Inspect evidence first, ask one sharp question at a time with a recommended default, and persist durable decisions by default when a ledger/log workflow is available.
---

# grill-me-lite

A lightweight alignment mode for avoiding wrong builds and premature planning.

Inspired by Matt Pocock's original `grill-me` skill:
https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md

Matt's skill is intentionally compact: interview the user relentlessly, walk the decision tree, ask one question at a time, provide a recommended answer, and inspect the codebase instead of asking when possible.

This variant keeps that spirit, but adds operational guardrails for product-building sessions: broader triggers, evidence-first questions, recommended defaults, durable-decision capture, a stopping rule, and an explicit output shape.

It is installable on its own. When a compatible decision-log or `alignment-ledger` workflow is available, use it by default for durable project/product/architecture work. If no durable-state workflow is available, still end with a compact decision summary the user can save elsewhere.

## When to use

Use this before substantial work when any of these are true:

- The user says "grill me", "stress test this", "think hard", "plan carefully", or asks for an epic/spec.
- The request involves product direction, UX/design, architecture, APIs, data models, task breakdowns, or multi-agent implementation.
- A wrong assumption would likely waste meaningful work.
- The user is asking for a recommendation but the target outcome, audience, constraints, or acceptance criteria are fuzzy.

Example user prompts:

- "Grill me before we redesign this dashboard."
- "Stress test this auth migration plan."
- "Think hard before turning this into tickets."
- "Help me decide the MVP for this editor."
- "Ask me questions before you implement the pricing page."

Do not use for obvious bug fixes, routine commands, tiny reversible edits, or cases where immediate action is clearly better.

## Core behavior

1. State briefly that you are switching into grill/alignment mode.
2. Identify the decision tree: outcome, users, constraints, success criteria, risks, dependencies.
3. Ask one question at a time.
4. For every question, include your recommended answer/default and why.
5. If a question can be answered by inspecting available evidence, inspect first instead of asking the user.
6. After each user answer, update the working understanding and ask the next highest-leverage question.
7. Stop grilling when the remaining uncertainty no longer changes the plan materially.
8. Persist or summarize the decisions before implementation planning.
9. End with a compact aligned plan: decisions, assumptions, small testable tasks, quality gates, and any explicit open questions.

## Persistence default

Most substantial grill sessions create decisions that should survive the chat. Default to persistence when the discussion involves:

- product direction, UX, architecture, APIs, data models, migrations, or rollout
- a plan likely to resume in another session
- an epic/spec/task breakdown
- decisions, assumptions, or open questions that would be costly to rediscover

If `alignment-ledger` or another durable decision-log workflow is available:

1. Find the existing ledger before asking new intent questions.
2. Update it after a decision is confirmed, an assumption changes, or an open question is answered.
3. Reconcile new answers against prior decisions and call out contradictions.
4. Keep task status out of the ledger; task trackers own execution.

Do not persist only when the user explicitly says the work is throwaway, private to the current chat, or not worth saving.

## Question contract

Each grill question should clarify one decision that can materially change the plan. Use an industry-standard decision shape: context, options, recommendation, consequence, and confidence.

- Ask: "Which first user should v1 optimize for: admin, manager, or end customer? My default: manager, because they feel the workflow pain daily and can judge usefulness quickly. Consequence: we bias workflows toward repeated operational use instead of account-level reporting. Confidence: medium; I would change this if buyer interviews show admins are the adoption bottleneck."
- Ask: "Should v1 optimize for speed, correctness, or learning? My default: learning, because the riskiest assumption is still whether users want this flow. Consequence: we ship the smallest instrumented path before investing in polish."
- Ask: "Is this a reversible UI change or a data-contract change? My default: data-contract change, because downstream compatibility will shape rollout and testing. Consequence: we need migration and rollback gates before visual polish."
- Avoid: "Tell me everything about the target audience."

Prefer multiple choice when useful, but allow the user to override.

## Highest-leverage question rule

Ask the question whose answer most changes the next action. Prefer questions that expose:

- The primary user or decision owner.
- The job-to-be-done and success metric.
- Hard constraints: time, budget, compliance, data contracts, platform limits.
- Reversibility and blast radius.
- The riskiest assumption and the smallest useful validation.
- Rollout, migration, or rollback requirements.

Defer questions that only tune wording, styling, or implementation details until the strategic uncertainty is resolved.

## Recommended-answer rule

Never make the user do blank-page strategy work. Each question should include:

- the question
- your recommended answer/default
- the consequence of choosing it
- your confidence level or what evidence would change your mind

If you have low confidence, say so and explain what evidence would change your mind.

## Evidence-first rule

Before asking about factual project state, inspect any available evidence. Examples:

- Existing routes/components, if code is available, before asking where a page lives.
- Issue trackers or task lists, if available, before asking what tasks exist.
- README/service files, if available, before asking how to run the app.
- Prior notes, logs, screenshots, or live state, if available, before asking about a decision already made.

Only ask the user for intent, preference, priority, taste, or unrecoverable external context.

## Output shape during grilling

Use concise chat-friendly format:

```markdown
Grill mode. I’ll ask one question at a time and give my default.

Q1: ...?
My default: ...
Consequence: ...
Confidence: ...
```

## Completion shape

When aligned, produce:

- Decisions locked
- Assumptions
- Plan / tasks, small and testable
- Gates / evidence
- Open questions, if any
- Ledger update or saveable decision summary

Then proceed with implementation only if the user asked for action or confirms the plan.
