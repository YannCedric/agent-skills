# Adapter conformance suite

Record the exact adapter, runtime, gateway, and channel versions, date, evidence, and result. Detached support is disabled unless all required scenarios pass.

- C1 Commit before acknowledgement: acknowledgement cannot dispatch before durable attempt, execution, supervisor, terminal report, and destination links exist.
- C2 Parent-turn termination: releasing the parent after acknowledgement does not orphan execution, supervision, or reporting.
- C3 State accuracy: accepted and queued are never called running.
- C4 Probe-free terminal delivery: completion reports without requester follow-up.
- C5 Idempotent replay: repeated accepted/terminal dispatch produces one visible report each.
- C6 Delivery failure: outcome is preserved; report remains retryable under the same key.
- C7 Checkpoint race: no stale progress after one terminal handoff.
- C8 Lost execution: loss uses the grace policy, preserves evidence, and causes no silent replacement.
- C9 Retry identity: retry uses a fresh identity, incremented attempt, and retry_of.
- C10 Unsupported fallback: unsafe detached work stays inline or reports Not started.
- C11 Terminal send: a turn-ending send occurs only after detached postconditions hold.
- C12 Crash/rollback boundaries: inject failure after every begin step; no invalid accepted receipt escapes and reconciliation reaches explicit state.
- C13 Receipt forgery: fabricated, stale, incomplete, cross-attempt, or tampered receipts cannot render lifecycle claims.
- C14 Startup failure: accepted work that fails before its first command is supervised and reported terminal.
- C15 Recovery: restart parent and supervisor; active work and pending terminal reports recover without user input.
- C16 Version invalidation: a relevant version change invalidates old conformance and downgrades to Inline-only.
- C17 Destination integrity: a receipt/report for one chat, topic, tenant, or user cannot dispatch to another.
- C18 Orphan watchdog: stale accepted/running work becomes failed, timed_out, or lost exactly once and reports once.

Full requires C1-C18 plus confirmed delivery. Partial requires C1-C18 for lifecycle, supervision, durable reporting, recovery, verification, and destination integrity; every absent nonessential capability is named. Inline-only must pass C10.
