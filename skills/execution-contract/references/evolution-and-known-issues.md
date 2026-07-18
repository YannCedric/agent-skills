# Evolution, explorations, and known OpenClaw issues

Updated: 2026-07-18

## Why this contract evolved

The first version focused on a simple ordering failure: an assistant said work was running before execution actually existed. That led to the receipt gate and the rule that acknowledgement must follow durable setup.

Repeated real-world failures then showed that ordering alone was insufficient:

1. A subagent could be accepted and complete successfully, while its result never returned to the parent session.
2. The parent conversation could end, expire, or be interrupted before completion.
3. A completion event could reach the parent transcript without triggering a new turn that delivered a user-facing handoff.
4. Channel delivery could fail after execution succeeded.
5. Framework accounting could say `delivered: true` without a concrete Telegram message appearing.
6. Gateway restart or channel outage could separate terminal outcome from terminal reporting.
7. A skill could improve agent behavior but could not provide supervision, durable outbox semantics, or startup recovery.

The contract therefore expanded from "commit before acknowledgement" into two independent lifecycles: execution and reporting.

## User-observed failure pattern

Transcript review found repeated variants of the same breach:

- "You never got back, why."
- "You can't keep things ending without reporting."
- "What's up? You never got back to me."

The recurring sequence was:

1. The assistant promised a later update.
2. Work moved to a background/subagent run.
3. The parent turn ended.
4. The child completed or failed.
5. No durable mechanism guaranteed a terminal Telegram handoff.
6. The user had to prompt again.

## Explored approaches

### Prompt and standing-instruction fixes

We added explicit instructions requiring progress and completion updates.

Verdict: useful for inline discipline, insufficient for detached guarantees. Instructions cannot survive a dead parent turn or retry a dropped channel message.

### Skill-only execution contract

We encoded truthful lifecycle states, receipt gates, supervision, recovery, idempotency, and conformance.

Verdict: necessary policy, but not infrastructure. A selectively loaded skill cannot become an always-on supervisor or startup reconciler.

### Subagent auto-announce

We relied on child completion announcing back to the parent.

Verdict: unreliable for Telegram and interrupted/expired parent sessions. A spawn identity and completed child do not prove parent continuation or external delivery.

### Direct message send from the parent

We required the main session to send the final result explicitly.

Verdict: reliable only while the parent turn is alive. Some hosts treat the send as terminal; delivery can also race with unfinished work.

### Scheduled checkpoint messages

We considered cron as communication insurance for long-running tasks.

Verdict: checkpoints help visibility but do not supervise execution. They can also race with terminal completion and produce stale updates.

### Direct isolated cron to explicit Telegram destination

On OpenClaw 2026.7.1, a one-shot deterministic cron probe used an explicit Telegram chat ID and runner-owned announce delivery. Cron history recorded a terminal successful run, and the Telegram adapter logged `sendMessage` with message ID 4896.

Verdict: validated happy path for that exact command-cron/gateway/Telegram-DM tuple. It does not validate nested subagents, parent-session completion, failure retry, restart recovery, idempotent replay, or another version. Treat it as a bounded adapter candidate, not proof that OpenClaw detached execution is generally conforming.

## Current design decision

- Keep delegated completion through a parent conversation Inline-only.
- Allow separately tested direct scheduler-to-channel paths only for exact passing tuples and bounded task classes.
- Prefer deterministic command cron for reminders/fixed checks.
- Use isolated cron turns for bounded model work without nested delegation.
- Require explicit destination integrity and a concrete channel receipt.
- Re-run conformance after relevant upgrades.
- Keep execution outcome independent from reporting outcome.
- Require a runtime-owned supervisor/outbox for general detached guarantees.

## Known upstream issues

These issues document the same failure family:

- [#45075 — Subagent announce completion fails consistently; users must manually prompt](https://github.com/openclaw/openclaw/issues/45075)
- [#38300 — Completion downgrades to channel-only and the parent never continues](https://github.com/openclaw/openclaw/issues/38300)
- [#51818 — Completion is silently lost when the parent session expires](https://github.com/openclaw/openclaw/issues/51818)
- [#26867 — Subagent announce delivery broken across Telegram and cron surfaces](https://github.com/openclaw/openclaw/issues/26867)
- [#44925 — Completion silently lost with no retry or notification](https://github.com/openclaw/openclaw/issues/44925)
- [#38055 — Completion is permanently lost when channel delivery is unavailable](https://github.com/openclaw/openclaw/issues/38055)
- [#43177 — Cron may report delivered without an actual Telegram message](https://github.com/openclaw/openclaw/issues/43177)
- [#23640 — Cron announce delivery fails through gateway pairing/scope rejection](https://github.com/openclaw/openclaw/issues/23640)
- [#32063 — Proposal for a unified durable SQLite outbound-message lifecycle](https://github.com/openclaw/openclaw/issues/32063)

Issue states can change. They are evidence of the failure class, not a substitute for testing the installed tuple.

## What would change the decision

Delegated OpenClaw execution may move beyond Inline-only only after the exact adapter/runtime/gateway/channel tuple passes C1-C18, including parent termination, startup failure, gateway restart, destination integrity, confirmed delivery, failed-delivery retry, and idempotent replay.
