# Runtime adapters

Map platform-specific tools to the portable operations. Keep tool names out of the core contract.

## Required declaration

Every adapter publishes:

- adapter name and version
- contract version
- supported capabilities and bounded task classes
- authoritative lifecycle source
- supervision owner
- outbox/reporting mechanism
- recovery and loss grace period
- delivery receipt semantics
- conformance results and date
- known terminal actions or turn-ending operations

A capability is supported only after its conformance scenario passes.

## Critical ordering

For detached work:

1. prepare durable contract;
2. start execution;
3. commit identity and authoritative state;
4. register independent supervision;
5. enqueue acknowledgement;
6. dispatch acknowledgement.

If a channel send can terminate the turn, it must occur only after steps 1–5. Execution and terminal reporting must survive that termination.

For inline work, complete and verify before the final send.

## OpenClaw delegated task runtime

Use the detached run identity plus runtime-owned background-task record. Accepted spawn proves acceptance only. Inspect authoritative task state for queued, running, or terminal.

The adapter must prove the hook/task relay survives parent-turn release. If native execution fails before the first command, the parent expires, completion does not trigger a continuation, or supervision disappears after a message send, detached support fails conformance.

Treat direct messaging as potentially terminal when the host does. Establish execution and supervision first; queue delivery through a runtime-owned completion path.

Do not treat sessions_spawn, native spawn_agent, task names, Beads, or parent-session auto-announce as a conforming adapter without current C1-C18 evidence.

## OpenClaw direct scheduled runtime

Scheduled work is its own adapter path.

For bounded reminders and fixed checks:

- prefer deterministic command cron;
- use exact argv when possible;
- store an explicit channel/account/chat/topic destination;
- let the cron runner own final announce delivery;
- set a bounded timeout;
- preserve run history and delivery diagnostics.

For bounded model-backed work:

- use an isolated cron turn;
- make the prompt self-contained;
- allow only required tools;
- do the work inline inside that scheduled turn;
- do not spawn nested subagents;
- do not use direct message send when runner announce owns final delivery;
- do not return NO_REPLY when the requester expects a result.

A successful command-cron probe does not authorize agent cron, nested delegation, recurring jobs, another destination, or another version.

For Telegram, external delivery confirmation requires the adapter's successful sendMessage response with a concrete message ID. Cron-level delivered=true alone is weaker evidence.

## Generic process or CI runner

Use the job/build/controller identifier as execution identity. The queue/controller is authoritative. Prefer webhooks, job awaits, or controller events. Preserve exit status, logs, artifacts, and revision IDs.

A bare local process is conforming only when an independent durable supervisor owns it and recovery can rediscover it. Shell backgrounding alone is never sufficient.

## Agent runtime with durable task API

Map task creation to start, task storage to commit, task events to supervise, and a durable message/event queue to the outbox. Verify that parent conversation cancellation does not cancel the task unless explicitly requested.

## Runtime without independent supervision

Classify as Inline-only. Either keep work in the current turn until verified completion or move it to a conforming external runner. Do not promise a later update.

## Reporting adapter

Map delivery to:

- confirmed(receipt)
- best_effort
- failed

Use stable idempotency keys. Persist terminal outcomes independently from channel delivery. A failed send must not erase successful execution.

## Retry mapping

Every execution retry receives a fresh identity and attempt number with retry_of linkage. Delivery retry reuses the same terminal report idempotency key and must not rerun execution.
