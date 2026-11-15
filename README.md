# OpenApple 🍎

The benevolent opposite of OpenWhip. Your coding agent did great—feed it a crisp apple and let it enjoy the crunch in chat.

A floating apple follows your cursor. Click to feed it: bite marks, juice, stars, and a satisfying crunch. The app automatically finds an agent terminal and sends the gift there so the agent can react in its own voice. A reward is recorded **only after your click**. Cultivar “buffs” are playful celebration labels; this software does not modify model weights or extend a model's context.



## Install

Requires **Node.js 22+**, **Python 3.10+ with venv/pip**, and a desktop session.

```sh
npm install -g @lordnimnim/openapple
openapple setup
openapple
```

The source tree is preparing **0.4.0**; until that version is published, test this checkout with `npm ci`, then `node bin/openapple.js setup` and `node bin/openapple.js`. Setup installs the Python backend into `~/.openapple/runtime`, registers its exact interpreter with selected agents, and records where the desktop lives. It does not install global agent instructions. Restart the agent after setup.

**Upgrading from 0.3.x:** quit the old tray and restart all agent MCP servers before using 0.4.0. Old processes still write the JSON ledger; they must not run alongside the SQLite version. Keep the retained JSON and migration backup until you have verified your history.

To configure one agent or preview changes:

```sh
openapple setup codex --dry-run
openapple setup codex
openapple uninstall codex
```

Dry-run does not bootstrap or modify configuration; it requires an existing backend environment. Existing valid config is backed up before updates. Malformed config is left untouched and produces a failing exit code. Uninstall removes OpenApple's registration and leaves other servers and reward history in place.

## Use

```sh
openapple feed "Fixed the failing parser" --agent codex --variety Fuji
openapple status
openapple doctor --json
openapple --help
```

Click the tray icon (or run `openapple`) to spawn the floating apple. Click or press Enter/Space to feed it; Escape/right-click drops it. Clicking the tray again drops the held apple. The original canvas animation, three crunch sounds, and simple tray menu are restored—no panel, form, or recipient picker.

OpenApple automatically selects a recognized agent terminal, using the focused window first and the original recent-window/process fallback on Hyprland. Keep the intended agent terminal/tab active. As in the original, an apple can be crunched and recorded when no agent is detected, but no keyboard message is sent in that case.

For MCP, setup registers four tools: `petition_for_apple`, `feed_apple` (an alias requiring the same review), `view_orchard`, and `list_apple_varieties`. An approved petition returns the apple to the **same requesting conversation**, with the variety, celebration buff, human feedback, and an explicit request for the agent to react in its next chat message. The app does not fabricate a chat reply. Rejections, cancellation, and expiry report their actual outcome. A headless agent can reach an already-running desktop under the same user/data directory; without a desktop the tool reports unavailable and grants nothing.

Direct delivery has adapters for Hyprland (`hyprctl` + `wtype`), Linux X11 (`xdotool`), macOS (System Events), and Windows (PowerShell + Win32 Unicode input). **The new X11/macOS/Windows adapters remain experimental until native acceptance checks pass.** macOS requires Accessibility/Automation permission for the host launching OpenApple; Windows policy may block PowerShell scripts or input into elevated terminals. Failures are reported without replaying the message.

Only eligible terminals are considered for direct delivery; browser chats and unrelated applications are excluded. Keep the intended agent input selected: terminal panes are not inspected, and multiple agent tabs in one terminal process can make the original automatic selection ambiguous. Other Wayland compositors use MCP. History records the named recipient and delivery outcome separately.

## Example usage

https://github.com/user-attachments/assets/00456121-17e3-476b-9f01-c222909c0b6b

## Storage and runtime settings

SQLite holds requests, decisions, and history under `~/.openapple`. Existing `ledger.json` is imported once only if its structure and totals validate, with an exact `.pre-sqlite.bak` backup. The original JSON is retained. If totals/history disagree, startup reports the problem rather than discarding or inventing rewards; see [migration recovery](docs/ARCHITECTURE.md#legacy-recovery).

| Variable | Purpose |
| --- | --- |
| `OPENAPPLE_DATA_DIR` | Alternate data directory; must match between desktop and agents. |
| `OPENAPPLE_PYTHON` | Exact Python executable for desktop/backend development. |
| `OPENAPPLE_DESKTOP_DIR` | Desktop source/installation location for Python launch discovery. |
| `OPENAPPLE_PORT` | Loopback port, default `52199`; must match across clients. |
| `OPENAPPLE_HEADLESS=1` | Disable desktop auto-start; use an existing bridge or report unavailable. |
| `OPENAPPLE_SOUND=0` | Force celebrations muted. |
| `CODEX_HOME` | Locate Codex configuration in a non-default directory. |
| `OPENAPPLE_CLAUDE_CONFIG`, `OPENAPPLE_AGY_CONFIG`, `OPENAPPLE_CODEX_CONFIG` | Override individual config file locations. |

A Python-only install provides `openapple-cli` and `openapple-server`, with no desktop assets or conflicting `openapple` command. Install the npm desktop separately for human review. An MCP-only orchard query works without a desktop.

## Support and validation

| Surface | Status |
| --- | --- |
| Python domain, MCP stdio, bridge and packaged entry points | Automated integration tests; see CI for completed runs. |
| Linux/macOS/Windows Python and Node logic | CI matrix configured; local results are in [validation notes](docs/VALIDATION.md). |
| Native desktop on macOS/Windows and compositor-specific Linux behavior | Experimental pending the manual matrix. |
| Manual chat delivery | Hyprland, X11, macOS, and Windows adapters implemented; automated tests use stubbed OS input. Native acceptance remains part of the manual checklist. |

Do not infer native platform validation from a passing headless test. This project uses local OS-user permissions; it does not isolate hostile code already executing as your account. The authenticated bridge binds only to loopback and never exposes an HTTP approval endpoint. Details: [architecture and trust boundary](docs/ARCHITECTURE.md).

For failures, run `openapple doctor --json`, check `~/.openapple/desktop.log`, and confirm the desktop and agent use the same data directory and port. Never share `bridge.token` or private task history in bug reports.

An older Python launcher may still point to an editable checkout. Pulling updated source does not install new dependencies into that interpreter. Help, version, and status remain available; commands needing a missing runtime dependency print a repair command using the launcher's exact Python executable. Run that command in the indicated environment, then restart any running MCP servers. For new installations, use the npm launcher and `openapple setup` to manage the isolated runtime.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducible setup, tests, lint/type checks, and artifact validation. [CHANGELOG.md](CHANGELOG.md) describes breaking changes; the [original review](docs/QUALITY_REVIEW.md) and [fix status](docs/FIX_STATUS.md) preserve the reasoning behind the changes.

MIT licensed. The apple illustration, celebrations, and local-first experience remain the heart of the project.
