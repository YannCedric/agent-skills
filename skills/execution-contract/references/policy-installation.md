# Reliable policy installation

A skill cannot reliably invoke itself. Install always-loaded policy that:

- invokes execution-contract for detached, delegated, background, long-running, or timed work;
- requires a verified adapter receipt before any accepted/queued/running claim;
- requires host/runtime reconciliation at session start and after restart;
- forbids raw turn-ending sends before detached postconditions exist;
- completes inline before final delivery when detached mode is unavailable;
- reports Not started with the exact gap when neither safe path exists.

Standing communication rules must not require an acknowledgement before safe execution ordering. Re-run C1-C18 after relevant runtime, gateway, messaging, hook, scheduler, task, or policy changes.
