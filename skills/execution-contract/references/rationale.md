# Design rationales

## Preserve broad triggering

The description retains detached, delegated, background, long-running, scheduled, and timed work because metadata is the discovery surface. Broker terminology alone would fail to trigger on ordinary user requests and recreate acknowledgement without execution.

## Enforce receipts, not prose

The original incident class allowed acknowledgement to escape before execution existed. Requiring an adapter-verifiable receipt turns ordering from advice into a gate. Raw spawn, cron, PID, and task identities remain insufficient because they do not prove supervision or reporting survived.

## Separate execution from reporting

A job may succeed while its user-facing report fails. Keeping these lifecycles independent prevents a delivery failure from erasing successful work and prevents framework-level success from masquerading as confirmed channel delivery.

## Specify semantics, not one API shape

Portability requires shared postconditions, not identical tool signatures. A runtime may use an atomic broker call, transactional database, or crash-safe saga. Every implementation must reconcile partial failure to valid acceptance or explicit non-acceptance.

## Keep supervision and reporting outside the turn

A parent conversation can end immediately after a channel send or before a child completes. Therefore neither the acknowledgement nor the conversation may own the work, supervision, or terminal report.

## Treat scheduled work as a separate adapter

Direct scheduler-to-channel delivery and child-to-parent completion have different failure boundaries. A passing cron probe cannot authorize delegated completion. Conformance attaches to an exact path and bounded task class.

## Require the strongest available delivery receipt

Framework-level delivered flags can be optimistic. When the channel exposes a concrete receipt, such as a Telegram message ID, the contract requires it before reporting confirmed delivery.

## Put startup recovery where it can run

A skill cannot invoke itself on every session. Mandatory reconciliation belongs in always-loaded host/bootstrap policy. Skill-time reconciliation remains defense in depth.

## Fail closed

Inline-only is a valid capability class, not a degraded promise. When durability is absent, completing inline or saying Not started is safer than inventing background guarantees.

## Version the conformance tuple

Runtime, gateway, hook, scheduler, and channel behavior can change independently. A previous pass must not authorize detached guarantees after a relevant upgrade.

See evolution-and-known-issues.md for the incident history, explored approaches, local probe, and upstream links.
