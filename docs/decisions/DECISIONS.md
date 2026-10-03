# DECISIONS

## DEC-001 — Product surface locked to visible 2.1.2 FREE baseline
Status: ACTIVE
Decision: Do not expose recovered developer/internal tabs as normal tabs.
Reason: user requires 1:1, not an expanded tool.

## DEC-002 — Per-PID single mutable action
Status: ACTIVE
Decision: one mutable action in flight per game PID; read-only observers may run concurrently.
Evidence: DATA-2222 canonical architecture.

## DEC-003 — New clone bridge protocol
Status: ACTIVE
Decision: use a separate mapping/magic/DLL target for the clone while porting semantic behavior from the supplied donor source.
Reason: isolate the clone from the prior controller's product-specific protocol/state.
