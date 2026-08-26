# Changelog

## 0.4.0

- Replace the hand-rolled `ctypes` hidapi layer, key-image packetization, and
  per-model report parsers with `python-elgato-streamdeck`, which supplies
  maintained drivers for every Stream Deck model.
- Add Stream Deck XL support (32 keys, 8×4, 96×96 artwork), along with MK.2,
  Original, Original V2, Mini, Neo, and Studio.
- Derive device capabilities, key count, grid shape, and artwork size from the
  driver instead of a two-entry product ID table.
- Render key artwork at the size the connected deck reports rather than a fixed
  120×120, reusing the built-in pictograms at any scale.
- Grow the stored profile to the connected deck's key count so every physical
  key is addressable from the panel.
- Move control input onto driver callbacks, queued and dispatched on the daemon
  thread so action handling stays single-threaded.
- Drive the panel's key grid from the connected device's column count.

## 0.3.1 — 2026-08-20

- Force `Text.PlainText` for Key Light names and other externally supplied panel strings so QML AutoText cannot load markup or remote resources.
- Sanitize mDNS Key Light names before they enter status JSON, and keep HTTP light payloads from overwriting the advertised name.

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
