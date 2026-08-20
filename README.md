# Elgato Stream Deck for Omarchy

An experimental native Omarchy Shell plugin for controlling Elgato hardware on Linux without the Elgato desktop application.

Current version: **0.2.0**

## Supported in the current prototype

- Stream Deck Plus (`0fd9:0084`): eight keys, four dials, 120×120 JPEG artwork, and device brightness
- Stream Deck Pedal (`0fd9:0086`): three pedal events
- Elgato Key Light Neo: grouped power, brightness, temperature, and live status
- Official Elgato Oma bar icon and a JSON profile that reloads at runtime

See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for the implementation history, verified hardware, architecture, and remaining work.

## Installation

The prototype expects Arch/Omarchy, Python 3, and `libhidapi-hidraw`:

```bash
git clone https://github.com/amitcpatel/omarchy-streamdeck ~/.config/omarchy/plugins/acp.streamdeck
omarchy plugin enable acp.streamdeck right
omarchy restart shell
```

The first run creates `~/.config/omarchy-streamdeck/profile.json`. Edit it to change key, dial, pedal, and light mappings. Action changes reload automatically; restart Omarchy Shell to redraw changed key artwork.

## Default controls

| Control | Default action |
| --- | --- |
| Keys 1–8 | Terminal, Browser, Files, Mic mute, Play/Pause, Screenshot, Lights, Lock |
| Dial 1 | Output volume; press to mute |
| Dial 2 | Microphone volume; press to mute |
| Dial 3 | Key Light brightness; press to toggle |
| Dial 4 | Key Light temperature; press to toggle |
| Pedals 1–3 | Mic mute, Play/Pause, Screenshot |

## Commands

```bash
bin/omarchy-streamdeck init
bin/omarchy-streamdeck profile
bin/omarchy-streamdeck status --json
bin/omarchy-streamdeck daemon
```

## Lights

Lights use stable mDNS hostnames rather than DHCP addresses. Discover yours with `avahi-browse -rt _elg._tcp` and add them to the profile:

```json
{"lights": [{"name": "Left", "host": "elgato-key-light-neo-xxxx.local", "port": 9123}]}
```

The default profile leaves this list empty so the repository does not publish device-specific network identities.

## References and credits

- [Elgato Stream Deck HID documentation](https://docs.elgato.com/streamdeck/hid/intro/)
- [Stream Deck Plus HID documentation](https://docs.elgato.com/streamdeck/hid/stream-deck-plus/)
- [Community Key Light HTTP API documentation](https://github.com/adamesch/elgato-key-light-api)
- [Official Elgato icon resources](https://docs.elgato.com/resources/icons/)

The Elgato mark comes from the MIT-licensed official `@elgato/icons` package. Elgato, Stream Deck, and Key Light are trademarks of Elgato. This MIT-licensed project is not affiliated with or endorsed by Elgato.
