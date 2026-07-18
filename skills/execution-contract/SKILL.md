---
name: "execution-contract"
description: "Truthful lifecycle, supervision, checkpoints, and delivery for detached, delegated, scheduled, timed, or long-running work."
---

# Execution Contract

Turn conversational promises into observable execution. Enforce universal safety invariants while allowing each runtime adapter to choose an equivalent implementation.

## Core invariant

Never emit a user-visible claim that work is accepted, queued, running, or succeeded unless the claim is rendered from a current, inspectable adapter receipt whose required postconditions already hold.

A spawn result, task name, PID, Bead, prompt, cron declaration, message acknowledgement, or conversational intention is not sufficient evidence.

If detached postconditions cannot be proven, do not launch untracked work. Complete inline or report:

"Not started — detached execution is unavailable here: <exact capability gap>. Safe option: <inline execution|conforming runtime>."

## Separate execution from reporting

Execution states:

- requested: work was asked for; no execution exists.
- preparing: durable setup is incomplete; never acknowledge as accepted.
- accepted: the runtime accepted an execution and issued an identity.
- queued: the authoritative source says it is waiting.
- running: the authoritative source confirms activity.
- terminal: succeeded, failed, timed_out, cancelled, or lost.

Reporting states:

- report_pending
- dispatching
- reported
- report_best_effort
- report_failed

An execution ID proves acceptance only. Never rename accepted or queued as running. Reporting failure never changes the execution outcome.

## Negotiate capabilities

Before detached work, obtain a versioned capability receipt backed by current conformance evidence for the exact adapter/runtime/gateway/channel tuple.

Required detached capabilities:

- durable contract and attempt records
- inspectable execution identity and authoritative state
- supervision independent of the conversational turn
- durable idempotent acknowledgement and terminal reporting
- recovery after parent-turn termination and runtime restart
- completion verification
- destination integrity
- delivery confirmation, when the channel supports it

Classify the path:

- Full: all required capabilities and confirmed delivery pass conformance.
- Partial: lifecycle, independent supervision, durable reporting, recovery, verification, and destination integrity pass; explicitly named nonessential capability is absent.
- Inline-only: detached postconditions cannot be satisfied, but safe inline work is available.
- Unsupported: neither safe detached nor inline execution is available.

Unknown, stale, untested, or contradictory declarations downgrade to Inline-only. Never infer capability from tool names, documentation, a successful spawn, or one happy-path delivery probe.

## Begin detached work fail-closed

Use the adapter's semantic "begin detached" transaction. The adapter may implement it as one atomic broker call or as a crash-safe saga with durable intermediate states, compensation, and reconciliation. Tool shape is not prescribed; observable guarantees are.

Before returning an accepted receipt, the adapter must:

1. Persist contract ID, attempt, outcome, scope, constraints, verification plan, destination, retry policy, and any real deadline.
2. Start execution and persist its authoritative identity and state.
3. Attach runtime-owned supervision with recovery and a documented loss grace period.
4. Create durable acknowledgement and terminal report records with stable idempotency keys.
5. Persist links between contract, attempt, execution, supervisor, reports, and destination.
6. Verify every required record is inspectable and belongs to the same attempt.
7. Return a receipt only after all postconditions pass.

If any step fails, remain in preparing, compensate safely, or persist an explicit preparation failure. Never return accepted while required state is missing. A crash at any boundary must reconcile to either a valid accepted attempt or an explicit non-accepted failure—never an ambiguous promise.

## Receipt requirements and gate

An accepted receipt must contain or securely reference:

- contract_id, attempt, execution_id
- authoritative state and observed_at
- adapter, runtime, gateway, and channel versions
- conformance version, checked_at, and validity
- supervisor identity and recovery policy
- acknowledgement and terminal report identities
- destination fingerprint
- postcondition result
- integrity token or equivalent adapter-verifiable authenticity

Before acknowledgement:

1. Re-inspect the receipt through the authoritative adapter.
2. Verify contract, execution, supervisor, terminal report, and destination links.
3. Verify conformance is current for the exact runtime tuple.
4. Render only from verified receipt fields.
5. Dispatch through the durable report path, never a raw send known to terminate the turn.

Allowed form:

"Accepted — execution <id>, state <accepted|queued|running>. Supervision: <id>. Terminal report queued: <report-id>."

The adapter must issue separate authoritative lifecycle or terminal receipts. Never reuse the initial accepted receipt to claim later running or success.

## Inline fallback

When detached mode is absent, stale, or fails the receipt gate:

- do not launch untracked background work;
- do not send a progress acknowledgement through a mechanism known to end the working turn;
- complete and verify inline before the final visible send; or
- report Not started with the exact capability gap.

Expected duration, complexity, or a preference for delegation never bypasses the gate.

## Independent supervision

A runtime supervisor, scheduler, controller, durable task service, webhook consumer, or equivalent must own detached lifecycle and terminal reporting outside the parent conversation.

It must:

- survive parent-turn release, interruption, and restart;
- observe authoritative lifecycle events;
- detect accepted-but-never-started work;
- preserve logs and partial artifacts;
- verify requested outputs and quality gates;
- reconcile stale records and apply the documented loss grace period;
- persist one terminal result per attempt;
- enqueue exactly one terminal report per attempt;
- retry delivery idempotently without changing execution state;
- never silently retry execution.

A skill, prompt, agent memory, raw process, task name, or conversational promise is not a supervisor.

## Durable idempotent reporting

Use stable keys:

- <contract-id>:<attempt>:accepted
- <contract-id>:<attempt>:checkpoint:<deadline>
- <contract-id>:<attempt>:terminal

Persist outcomes independently from delivery. Replaying the same key must not duplicate a user-visible report.

Schedule checkpoints only when requested or required by an explicit SLA. A checkpoint is communication insurance, not evidence of progress. Resolve checkpoint/terminal races in favor of one terminal handoff and no stale progress message afterward.

## Scheduled and timed work

Scheduled execution and completion delivery are separate capabilities. A scheduler firing does not prove the result reached the requester.

For OpenClaw scheduled work:

- prefer a deterministic command job for reminders and fixed checks;
- use an isolated cron turn for bounded model-backed work;
- store an explicit provider/account/chat/topic destination;
- let the cron runner own terminal announce delivery;
- do not nest subagents inside isolated cron work;
- do not make delivery depend on the original parent session resuming;
- do not call a direct message tool from the scheduled turn when runner delivery owns the final reply;
- never return `NO_REPLY` when the user expects a result;
- verify both terminal run state and a concrete channel receipt.

A direct cron-to-channel path may pass its own adapter conformance while delegated completion remains Inline-only. Capabilities are per exact path, not per product.

Read references/runtime-adapters.md before scheduling. Read references/evolution-and-known-issues.md for the OpenClaw failure history, explorations, and issue links.

## Recovery

The runtime or always-loaded host bootstrap must reconcile owned contracts and pending reports on startup and after interruption. A selectively triggered skill cannot guarantee session-start recovery.

When this skill is loaded, also request reconciliation as defense in depth:

- deliver pending terminal reports before a new detached acknowledgement;
- surface failed, timed_out, cancelled, or lost attempts;
- preserve pending reports until delivered or explicitly abandoned;
- never silently replace a missing attempt.

Startup reconciliation supplements independent supervision; it does not replace it.

## Failure, loss, and retry

When backing state disappears:

1. Inspect the authoritative record.
2. Distinguish failed, timed_out, cancelled, and lost.
3. Use lost only after the adapter reports loss or its recovery grace period expires.
4. Preserve logs, partial artifacts, evidence, and report state.
5. Enqueue the terminal report promptly.

Retries require authorization or an ordinary safe retry policy. Each retry gets a new execution identity and attempt number with retry_of linkage. Final reporting lists every attempt and state.

## Verify terminal success

Before a succeeded receipt:

1. Check the requested artifact or external effect.
2. Run agreed quality gates.
3. Persist concise evidence and artifact/revision identities.
4. Let the supervisor finalize the terminal state.
5. Confirm the terminal report exists.
6. Dispatch idempotently.
7. Mark reported only with confirmed delivery; otherwise use report_best_effort or report_failed.

Allowed form:

"Succeeded — execution <id>. Verified by <evidence>. Result: <artifact/link/summary>. Delivery: <confirmed receipt|best effort|failed>."

A framework-level `delivered: true` is not sufficient when the channel supports a stronger receipt. For Telegram, require a successful `sendMessage` result with a concrete message ID.

## Portable adapter semantics

A conforming adapter provides equivalent semantics for:

- capabilities and current conformance evidence
- prepare/begin detached
- accepted receipt validation
- inspect authoritative lifecycle
- supervise and recover independently
- verify completion
- enqueue and dispatch idempotent reports
- reconcile contracts, attempts, and pending reports

Adapters may expose one broker API or several coordinated operations. Tool names and transaction mechanisms belong in adapter references, not the core contract.

Read references/runtime-adapters.md before mapping a platform. Require references/conformance.md before advertising Full or Partial. Read references/policy-installation.md for host integration. Read references/rationale.md when changing these invariants.

## Conformance gate

Detached mode is disabled by default for each exact adapter/runtime/gateway/channel version tuple. Require C1-C18, including destructive and failure-injection scenarios. Re-run after any relevant upgrade.

A static scan, successful task spawn, or happy-path channel probe is insufficient. A relevant version change invalidates prior conformance.

## OpenClaw status rule

For OpenClaw/Codex, sessions_spawn, native spawn_agent, task names, Beads, cron declarations, and message.send do not collectively prove a conforming detached adapter.

Classify delegated completion through a parent conversation as Inline-only until OpenClaw provides current conformance evidence for durable execution, independent supervision, idempotent reporting, recovery across turn/gateway restart, startup-failure reporting, destination integrity, and confirmed delivery.

A separately tested direct isolated-cron-to-channel adapter may be enabled only for the exact passing tuple and bounded task class. Do not generalize that pass to subagent completion, interactive delegation, another channel, or another version.

## Capability honesty

Portable semantics are universal; runtime guarantees are conditional. A skill cannot manufacture missing infrastructure. Fail closed instead of making a confident promise.
