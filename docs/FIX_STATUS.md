# Review remediation status — 0.4.0

This maps the historical [quality review](QUALITY_REVIEW.md), written against 0.3.2, to the current implementation. Original review links/line numbers refer to that old source revision. “Implemented” describes source and local checks, not an unperformed release or native platform certification.

| Finding | Resolution |
| --- | --- |
| F01 False approval | Implemented: pending requests remain unawarded until a committed UI decision; unavailable, rejected, cancelled and expired are distinct outcomes. |
| F02 Destructive config writes | Implemented: parse/type checks, scoped writer locks, content-addressed backups, atomic replacement, dry-run, and uninstall. Failure tests preserve original bytes. |
| F03 Incompatible MCP dependency | Implemented: tested MCP 1.30.x-compatible requirement `<2`, locked development resolution, real stdio-client test. v2 migration is deferred rather than falsely claimed. |
| F04 Lost/corrupt ledger | Implemented: transactional SQLite, schema versioning, fresh reads, validated all-or-nothing JSON migration with original retained. Multi-process tests pass. |
| F05 Duplicate rewards | Implemented: unique request IDs and idempotent terminal transitions. MCP/CLI never increment a second counter. |
| F06 Unsafe targeting | Replaced: named-recipient Hyprland delivery with window/focus checks, plus MCP gifts returned to the requesting conversation. Original automatic recipient selection is restored; the canvas has no picker or panel. |
| F07 Broken platform injection | Shared delivery checks now wrap separate Hyprland, X11, macOS, and Windows adapters. Native platform acceptance is still pending. Tests stub OS input; native acceptance is explicitly tracked. |
| F08 Unauthenticated bridge | Implemented: bearer token, restrictive token file, loopback binding, Host/Origin/method/content checks, bounded payload, minimal health, no HTTP approval operation. |
| F09 Concurrent petitions | Implemented: persistent FIFO pending queue, UUID receipts, separate outcomes, expiry, cancellation, and a completion hold before advancing. |
| F10 Incomplete distribution | Implemented: npm owns desktop command/resources; Python owns separate CLI/MCP entry points; setup bootstraps an isolated runtime. Built artifacts inspected and executed outside checkout. |
| F11 Cold launch | Implemented: authenticated readiness before submission, full metadata retained, bounded waits, visible errors and local log. Native cold-launch acceptance remains in the manual matrix. |
| F12 Tests/automation | Implemented: isolated domain/config/protocol regressions, Node bridge/backend integration, lint/format/types, dependency locks, CI matrix, artifact checks. Remote CI results require running the workflows. |
| F13 Unsupported Electron | Implemented: registry-available supported major 45, locked at 45.3.2. The web release index advertised 45.3.3 before it was available in the environment's npm registry. |
| F14 MCP protocol streams | Implemented: no terminal prompts or stray stdout, async review and cancellation cleanup; real MCP client test passes. |
| F15 Schema/statistics | Implemented: UTC timestamps, variety/source/receipt, bounded history, consistent streak rules, transaction-assigned decision ordering (including identical timestamps). |
| F16 Setup scope/merge | Implemented: parsed JSON/TOML, preserved TOML comments, exact interpreter registration, selected targets only, directory overrides, no automatic global rules. |
| F17 Diagnostics | Implemented: registration content/interpreter checks and authenticated live bridge check; no fake Python koffi probe or inferred OS permission success. Native capabilities are not claimed. |
| F18 Instance race | Implemented: early Electron lock, isolated userData directory, no stale-lock deletion, fatal bridge-bind/backend errors. Native simultaneous-launch check remains manual. |
| F19 CLI contract | Implemented: one desktop command, explicit backend command, shared Python routing, independent help/version, meaningful error/decision exits, signal propagation. |
| F20 Stale renderer state | Implemented: whole request replaced on each review, reset controls, variety comes from the current request. |
| F21 Privileged IPC | Implemented: main-frame/sender validation, current-ID checks, allowed outcomes, no renderer-owned OS target, sandbox/isolation/CSP/navigation restrictions. Actual preload/decision path exercised in headless Electron. |
| F22 Accessibility/context | Implemented: original canvas-only experience and keyboard cancellation restored at user request. Review panels and selection controls removed. Screenshot inspected; screen-reader session remains manual. |
| F23 Display/motion | Implemented: DPR-aware drawing, fixed simulation steps, stop on hidden/idle, cursor-display bounds and display-change handling. Native multi-display and timing measurements remain manual. |
| F24 Audio | Implemented by simplification: removed generated/threaded audio pipeline; shipped renderer audio plays only after committed approval. Force-mute environment setting; no global RNG mutation or concurrent WAV writes. |
| F25 Installer scripts | Implemented: scripts delegate to shared bootstrap, check native command failures, use venv's exact interpreter, avoid PATH shims and mismatched pip. Native Windows installer run remains manual. |
| F26 Repository/release hygiene | Implemented: generated files/machine symlink/old archive untracked without deleting local originals; license, changelog, contribution guide, issue/PR templates, version consistency, package checks and reviewable artifact workflow. |
| F27 Documentation/story | Implemented: truthful mechanics/trust boundary, install/development/troubleshooting docs, support matrix, architecture, review screenshot and demonstration procedure. No invented performance/adoption claims. |
| F28 Cleanup | Implemented: removed dead audio/config/OS code, optional koffi/rich/typer dependencies and unused engine parameter, formatted/linted/typed boundaries. |

## Remaining release work

- Run the configured CI matrix on macOS/Windows and minimum Python; local Linux checks do not substitute for those runs.
- Complete the native desktop, screen-reader, monitor/refresh-rate and installer checklist in [VALIDATION.md](VALIDATION.md).
- Record the short demonstration and, if distributing native installers later, implement signing/notarization in a dedicated release change.
- Publish 0.4.0 only after reviewing artifacts and completing the support claims appropriate to that release. No package was published by this change.

The original minimal feeding flow is restored. Native platform checks remain release blockers; the implementation is not a claim of completed macOS/Windows validation.
