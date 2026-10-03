# FEATURE: NATIVE SEMANTIC BRIDGE

## Purpose
Provide per-PID read/action primitives without keeping client pointers in Python.

## Wire
- Mapping: `Local\\TLMToolClone_<PID>`
- Wake message: `WM_APP + 0x531`
- Hook: `WH_GETMESSAGE`, export `TlmGetMessageHook`
- Protocol target: `0x00020102`

## Current command surface
Core implemented: state, mount, path, NPC, Train start/stop. Remaining donor command families are tracked explicitly in T04.5/T04.6 and are not yet claimed implemented.

## Runtime status
BUILD/RUNTIME UNTESTED on Windows. Do not mark pass until CI and live client proof exist.
