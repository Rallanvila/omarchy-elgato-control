# Development status and handoff

Last updated: 2026-08-19  
Plugin version: 0.2.0  
Status: working prototype; not store-ready

## Goal

Build an Omarchy Shell plugin that uses a Stream Deck as a native Linux control surface, presents device status in the Oma bar, and controls Elgato Wi-Fi lights without requiring Elgato's Windows/macOS software.

## Work completed

### Omarchy integration

- Created local plugin `acp.streamdeck` with `bar-widget` and `service` entry points.
- Added a right-side bar widget using the official Elgato mark.
- Added a panel for profile, Plus, Pedal, key/dial/pedal assignments, and Key Light state.
- The service owns and restarts the Python daemon; **Edit profile** opens the user JSON.

### HID backend

- Implemented Python bindings to system `libhidapi-hidraw` using `ctypes`.
- Corrected `hid_device_info` layout for hidapi 0.15 after an initial enumeration crash exposed a pointer/bus-field ordering mismatch.
- Added reconnects, non-blocking polling, signal handling, atomic status writes, Plus key/dial parsing, Pedal parsing, brightness/fill reports, and paged JPEG key-image reports.

### Artwork and lights

- Replaced colored blocks with 120×120 JPEG pictograms and labels for all eight keys.
- Discovered two Key Light Neo devices over `_elg._tcp` mDNS.
- Added local HTTP state reads and grouped power, brightness, warmer, and cooler actions on port 9123.
- Used `.local` names so DHCP address changes do not invalidate the profile.

## Hardware observed on the development machine

| Device | Identifier | Verified result |
| --- | --- | --- |
| Stream Deck Plus | USB `0fd9:0084` | Opens through hidapi and reports connected |
| Stream Deck Pedal | USB `0fd9:0086` | Opens through hidapi and reports connected |
| Key Light Neo Left | mDNS on port 9123 | HTTP state reads succeed |
| Key Light Neo Right | mDNS on port 9123 | HTTP state reads succeed |

At the last check both lights were reachable, off, brightness 40, temperature 143 (about 7000 K). The daemon and shell had no plugin-specific warnings.

## Runtime files

| Path | Purpose |
| --- | --- |
| `~/.config/omarchy/plugins/acp.streamdeck` | Installed plugin source |
| `~/.config/omarchy-streamdeck/profile.json` | Mutable user profile |
| `~/.local/state/omarchy-streamdeck/status.json` | Daemon status read by the panel |

## Known issues and remaining work

1. **Physical action verification is incomplete.** Connections, image writes, and light reads are confirmed. Every key, dial direction/press, pedal, and light mutation needs a recorded manual test pass.
2. **No touch-strip support.** Tap, drag, flick, and touchscreen rendering are not implemented.
3. **Profile reload does not redecorate hardware.** Actions reload, but artwork, colors, and initial brightness require reconnect or daemon restart.
4. **No runtime light discovery.** Avahi discovery was manual; configured example hostnames are machine-specific.
5. **Light HTTP blocks the HID loop.** Move polling and mutations to a worker or asynchronous queue.
6. **Grouped-light behavior is simplistic.** Toggle turns all off if any is on; changes derive from the first reachable light.
7. **Errors are sticky.** Successful operations should clear transient errors and preserve per-device detail.
8. **Device coverage is narrow.** Only Plus and Pedal IDs/report shapes are supported.
9. **Pedal parsing needs real captured-report fixtures.**
10. **No automated tests.** Add parser, edge-trigger, packetization, configuration, light payload, reconnect, and recovery tests plus a non-action hardware smoke test.
11. **No profile schema/validation.** Invalid actions, colors, hosts, ports, or array lengths fail late.
12. **Actions are hard-coded.** Add a documented safe registry and optional command arrays without a shell.
13. **Icon builds are not reproducible.** JPEGs are committed, but source/build metadata is missing.
14. **Prerequisites are not checked.** Validate hidapi, hidraw permissions, Avahi, `wpctl`, `playerctl`, and Omarchy commands.
15. **Panel is read-only.** Add clickable/per-light controls, discovery, and remapping.
16. **No release process.** Add CI, screenshots, clean-machine testing, release notes, and store metadata.

## Recommended 0.3.0 milestone

1. Add tests and captured HID fixtures.
2. Make light networking asynchronous.
3. Add runtime mDNS discovery and merge it with configured names.
4. Redecorate on profile changes.
5. Add touchscreen status and controls.
6. Record the full physical control matrix.
7. Add clickable light controls to the panel.

## Validation commands used

```bash
python -m py_compile bin/omarchy-streamdeck
omarchy plugin validate ~/.config/omarchy/plugins/acp.streamdeck
bin/omarchy-streamdeck status --json
pgrep -af 'omarchy-streamdeck daemon'
journalctl --user --since '10 seconds ago' --no-pager
```

## Safety notes

- Action execution uses argument arrays and never invokes a shell.
- Key Light requests stay on the local network and require no authentication.
- Status writes are atomic.
- Do not run two daemons against the same hidraw endpoints.
