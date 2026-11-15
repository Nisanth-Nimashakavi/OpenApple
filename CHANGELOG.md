# Changelog

## 0.4.0 — unreleased

- Explicit human approval, rejection, cancellation, and expiry with a bounded desktop queue.
- Transactional SQLite history and retry-safe request IDs; validated, backed-up legacy migration.
- Authenticated local bridge and private decision channel; named-recipient chat delivery on Hyprland, with MCP replies returned to their originating conversation.
- Restored cursor-following apple, click-to-feed crunch and particle burst, original canvas-only surface, three crunch sounds, automatic targeting and original tray menu.
- Scoped config updates with backups, dry-run, uninstall, precise interpreter registration, and diagnostics.
- Separated desktop/backend executable ownership and isolated Python bootstrap.
- Existing Python launchers load setup dependencies only when needed and provide an exact-interpreter repair command if a runtime dependency is missing.
- Legacy migration accepts older `task_summary`/`operator_feedback` records and numeric epoch timestamps alongside newer ledger formats, preserving historical text and original JSON backups.
- Desktop startup errors include the Python backend's actual diagnostic and are reported once.
- Separated lifecycle, automatic targeting, feed coordination, and platform delivery; stale/concurrent decisions are rejected before changing focus.
- Supported Electron release, pinned dependency resolution, real integration tests, CI, and artifact checks.

Breaking changes: Python exposes `openapple-cli`; npm owns `openapple`. Manual typing now targets an explicitly identified agent terminal; MCP returns gifts directly with an invitation for the agent to react. X11, macOS, and Windows delivery adapters are implemented with native acceptance pending. `feed` submits a review instead of immediately awarding an apple. Setup no longer installs global agent instruction files. Malformed/inconsistent legacy data must be reconciled before migration.
