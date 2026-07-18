# OpenClaw migration plan

1. Keep current OpenClaw/Codex detached mode classified Inline-only.
2. Add capability discovery and a versioned conformance tuple.
3. Implement durable Contract, Attempt, Supervisor Lease, Report, and Evidence records.
4. Implement fail-closed begin semantics with receipt validation, crash recovery, and compensation.
5. Implement a supervisor/reconciler independent of parent conversations.
6. Implement a persistent idempotent Telegram outbox with destination fingerprints.
7. Integrate reconciliation into always-loaded session/gateway bootstrap.
8. Run C1-C18 with failure injection and parent/gateway restarts.
9. Canary one low-risk task class.
10. Enable detached mode only for the exact passing tuple.
11. Auto-downgrade to Inline-only on health or version invalidation.

Rollback forces Inline-only immediately while existing accepted attempts remain supervised and reportable.
