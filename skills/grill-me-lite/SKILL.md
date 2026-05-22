---
name: grill-me-lite
description: Use before building ambiguous product, UX, architecture, API, data-model, or task plans. Trigger on requests like "grill me", "stress test this", "think hard", "help me decide", "turn this into an epic", or "ask me questions before building". Inspect available code/docs first, then ask one sharp question at a time with a recommended default, consequence, and stopping rule. If decisions need to persist across sessions, summarize them or ask whether to use the user's preferred durable decision-log workflow.
---

# grill-me-lite

A lightweight alignment mode for avoiding wrong builds and premature planning.

Inspired by Matt Pocock's original `grill-me` skill:
https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md

Matt's skill is intentionally compact: interview the user relentlessly, walk the decision tree, ask one question at a time, provide a recommended answer, and inspect the codebase instead of asking when possible.

This variant keeps that spirit, but adds operational guardrails for product-building sessions: broader triggers, evidence-first questions, recommended defaults, a stopping rule, and an explicit output shape. It is self-contained and does not require any companion skill.

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
8. End with a compact aligned plan: decisions, assumptions, small testable tasks, quality gates, and any explicit open questions.

## Question style

Keep questions concrete and low-friction:

- Ask: "Who is the first user we are optimizing for: admin, manager, or end customer? My default: manager, because they feel the workflow pain daily and can judge usefulness quickly."
- Ask: "Should v1 optimize for speed, correctness, or learning? My default: learning, because the riskiest assumption is still whether users want this flow."
- Ask: "Is this a reversible UI change or a data-contract change? My default: data-contract change, because downstream compatibility will shape the rollout."
- Avoid: "Tell me everything about the target audience."

Prefer multiple choice when useful, but allow the user to override.

## Recommended-answer rule

Never make the user do blank-page strategy work. Each question should include:

- the question
- your recommended answer/default
- the consequence of choosing it

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
Why it matters: ...
```

## Completion shape

When aligned, produce:

- Decisions locked
- Assumptions
- Plan / tasks, small and testable
- Gates / evidence
- Open questions, if any

Then proceed with implementation only if the user asked for action or confirms the plan.
