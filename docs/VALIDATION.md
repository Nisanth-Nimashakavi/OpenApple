# Validation evidence and manual release checklist

Local validation on 2026-11-15 used Python 3.13.14, MCP 1.30.0, Node 22.23.2, and Electron 45.3.2 on Linux.

- Python: **49 passing tests**, including independent-process persistence, duplicate decisions, equal-timestamp ordering, mixed historical ledger formats, migration preservation, setup failure paths, cancellation cleanup, a real MCP stdio client, and existing Python launchers without installed setup dependencies.
- Node: **23 passing integration tests**, including actual Python child/backend calls, concurrent HTTP clients, authenticated routing/limits, cancellation, backend crash handling, startup diagnostics, named-recipient/focus-change delivery behavior, platform helper contracts, and stale/concurrent decision guards.
- Python lint, formatting, and mypy checks pass; application JS syntax checks pass.
- Built wheel/sdist and npm archive; verified version/resource/license boundaries and isolated imports/entry points outside the source checkout. Clean npm setup also created a working isolated Python environment, registered only the selected agent in temporary configuration, and queried the installed CLI successfully (`python scripts/check_installation.py`).
- Headless Electron (`npm run test:desktop`): cursor-following and click-to-feed, named-recipient manual delivery with stubbed `hyprctl`/`wtype`, and an actual MCP client receiving its apple/reaction prompt tested in an isolated orchard. Queued approval/rejection, Escape cancellation, and exact persisted totals are also verified. No OS input reaches a real chat. This used simulated clicks, not a real human award.
- Original canvas-only overlay, automatic recipient, feed/drop controls, and MCP routing verified in real Electron. Headless screenshot capture was inconsistent after viewport resizing; a native preview and screen-reader check remain pending.
- Impeccable mechanical scan ran in degraded regex mode because optional parser modules were unavailable. No clean accessibility/contrast certification is inferred from it.

The restricted execution sandbox blocked local socket binding and AnyIO thread IPC. Network/process integration suites were rerun with the required local execution permission and passed. Tests never used the user's orchard or agent configuration.

## Native checks before claiming platform support

For each claimed OS/display-server combination, record OS version, Electron/Python versions, date, result, and any limitation. Mark a platform experimental until its native run is complete.

- [ ] Clean installation from the packed npm artifact and setup in a path containing spaces.
- [ ] First startup, missing runtime, failed dependency install, stale registration, and occupied bridge port.
- [ ] Two simultaneous launches share one desktop; tray-only startup creates no review.
- [ ] Two agents submit distinct petitions; approve one and reject/cancel the other; each receives its own result.
- [ ] Close/quit while a review is pending, reconnect/restart before expiry, and restart after expiry.
- [ ] Keyboard-only review with Tab/Enter/Escape and assistive-technology announcement of the task and saved result.
- [ ] Linux Orca, macOS VoiceOver, or Windows Narrator on the corresponding platform.
- [ ] Light/dark/high-contrast modes, long task text, long agent/variety, text scaling, and smallest supported display.
- [ ] One and multiple monitors, mixed DPI, display removal, tiling compositor behavior, and 60/120 Hz motion timing.
- [ ] Reduced motion uses a quiet status change; muted and force-muted paths play no audio.
- [ ] Idle/hidden process resource use measured before making performance claims.
- [ ] Hyprland: named destination matches the intended chat; focus its message box, feed once, and confirm the agent reacts there. Switching/closing the target must abort submission. No automatic clipboard modification. Verify MCP requests reply in their originating conversation on other platforms.
- [ ] Existing config backup, repeated setup, selected-target isolation, dry-run, and uninstall verified.
- [ ] Windows PowerShell 5.1 installer, `py`-only Python environment, and macOS/Linux shell bootstrap verified natively.

## Record a short demo

Use a new `OPENAPPLE_DATA_DIR` consistently across desktop and client so no private tasks appear. Start the desktop, submit `openapple feed "Fixed the parser regression" --agent codex --variety Fuji`, show the recipient, approve once, then show `openapple status` after restart. Submit a second request and cancel it to demonstrate that the count stays unchanged. Keep the recording around 30–60 seconds and label it as a demonstration.

## Release artifact review

Run the complete commands in CONTRIBUTING.md, then inspect the CI artifacts. Verify `openapple --version`, Python package metadata, and changelog agree. The release workflow prepares artifacts for review and does not upload to npm/PyPI or create signed native applications automatically.

## Restored-flow platform acceptance

X11, macOS, and Windows adapters have contract tests with fake OS commands, not native acceptance results. Before promotion, test each adapter with Unicode gift text, a closed/renamed terminal, changed focus during input, denied permissions, missing utilities, multiple windows, and repeated clicks. Verify macOS Accessibility/Automation permissions and Windows execution policy/input integrity failures produce actionable errors. Confirm the terminal receives one message and the agent authors its own response. No browser or unrelated desktop app should receive direct input.
