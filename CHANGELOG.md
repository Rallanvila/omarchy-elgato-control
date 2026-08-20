# Changelog

## 0.3.0 — 2026-08-20

- Rename the application to Elgato Control for its multi-device scope.
- Adopt the permanent plugin ID `io.github.amitcpatel.elgato-control`, normalized helper and data paths, and automatic migration of existing profiles.
- Add capability-based discovery for Stream Deck Plus, Pedal, Wave:3, and Key Lights.
- Add Stream Deck Plus key artwork, four-dial LCD rendering, and dial controls.
- Add visual key, dial, and Pedal remapping with installed application discovery.
- Add VOXtype push-to-talk Pedal support.
- Add native Wave:3 gain, mute, headphone, preset, and default-source controls.
- Add automatic Key Light discovery and grouped light actions.
- Add grouped and per-light power, brightness, temperature, refresh, and reachability controls to the Key Lights page.
- Restrict Key Light HTTP traffic to resolved local addresses, reject redirects, and bound response sizes.
- Add generated application artwork with safe non-blank fallbacks.
- Add regression tests for device capabilities, input parsing, discovery, application actions, and Wave controls.
- Add screenshots for each supported product view.

## 0.2.0

- Initial working Stream Deck Plus, Pedal, and Key Light prototype.
