# TlmSemanticBridge

Native x64 bridge ported from the user-provided 12.4.2 semantic donor and rebound to the TLM 2.1.2 clone wire contract.

Key invariants:
- executes requests only on the target game's window thread via `WH_GETMESSAGE` wake-up;
- resolves IL2CPP types/methods semantically at runtime;
- blocks deep reads/mutations during map transition;
- copies values into shared memory; Python never retains live IL2CPP pointers;
- one mutable action per PID is enforced by the Python controller gate.

The bridge has its own FREE clone protocol and does not use the old product license protocol.

Current command coverage: state, movement, NPC and built-in Train start/stop. Commands not yet ported fail closed and are tracked in `TASKS.md`.
