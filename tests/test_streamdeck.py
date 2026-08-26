import importlib.machinery
import importlib.util
import pathlib
import queue
import tempfile
import unittest
from unittest import mock


class FakeDeck:
    """Stands in for a python-elgato-streamdeck driver instance."""

    def __init__(self, name="Stream Deck XL", ident="fake:0", keys=32, rows=4,
                 columns=8, dials=0, visual=True, touch=False):
        self._name, self._id, self._keys = name, ident, keys
        self._rows, self._columns, self._dials = rows, columns, dials
        self._visual, self._touch = visual, touch

        self.opened, self.resets, self.brightness = False, 0, None
        self.key_callback = self.dial_callback = None
        self.images = {}

    def deck_type(self): return self._name
    def id(self): return self._id
    def key_count(self): return self._keys
    def key_layout(self): return (self._rows, self._columns)
    def dial_count(self): return self._dials
    def is_visual(self): return self._visual
    def is_touch(self): return self._touch
    def open(self): self.opened = True
    def close(self): self.opened = False
    def reset(self): self.resets += 1
    def get_serial_number(self): return "SN-%s" % self._id
    def set_key_callback(self, callback): self.key_callback = callback
    def set_dial_callback(self, callback): self.dial_callback = callback
    def set_brightness(self, percent): self.brightness = percent
    def set_key_image(self, index, image): self.images[index] = image
    def key_image_format(self): return {"size": (96, 96), "format": "JPEG"}


class FakeManager:
    def __init__(self, decks): self._decks = decks
    def enumerate(self): return list(self._decks)


SCRIPT = pathlib.Path(__file__).parents[1] / "bin" / "elgato-control"
loader = importlib.machinery.SourceFileLoader("elgato_control", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class DeviceModelTests(unittest.TestCase):
    def test_xl_reports_its_own_geometry(self):
        info = module.deck_capabilities(FakeDeck())
        self.assertEqual(32, info["keyCount"])
        self.assertEqual((4, 8), (info["keyRows"], info["keyColumns"]))
        self.assertEqual("streamdeck", info["kind"])
        self.assertIn("keys", info["capabilities"])
        self.assertIn("brightness", info["capabilities"])
        for absent in ("pedals", "dials", "lcd"):
            self.assertNotIn(absent, info["capabilities"])

    def test_plus_capabilities_are_optional_and_explicit(self):
        deck = FakeDeck(name="Stream Deck +", keys=8, rows=2, columns=4, dials=4, touch=True)
        caps = module.deck_capabilities(deck)["capabilities"]
        self.assertIn("lcd", caps)
        self.assertIn("dials", caps)
        self.assertIn("dialPress", caps)
        self.assertNotIn("pedals", caps)

    def test_pedal_capabilities_do_not_assume_lcd(self):
        deck = FakeDeck(name="Stream Deck Pedal", keys=3, rows=1, columns=3, visual=False)
        info = module.deck_capabilities(deck)
        self.assertEqual(["pedals"], info["capabilities"])
        self.assertEqual("pedal", info["kind"])

    def test_fit_profile_grows_and_trims_to_the_deck(self):
        profile = {"keys": [{"label": "Terminal", "action": "terminal"}]}
        grown = module.fit_profile(profile, 32)
        self.assertEqual(32, len(grown["keys"]))
        self.assertEqual("terminal", grown["keys"][0]["action"])
        self.assertEqual("", grown["keys"][31]["action"])
        self.assertEqual(6, len(module.fit_profile(grown, 6)["keys"]))
        self.assertEqual(1, len(profile["keys"]), "fit_profile must not mutate its input")

    def test_lcd_svg_has_required_dimensions_and_labels(self):
        profile = {"dials": [{"label": "Volume"}, {"label": "Microphone"}]}
        svg = module.lcd_svg(profile, 55, [])
        self.assertIn('width="800" height="100"', svg)
        self.assertIn("Volume", svg)
        self.assertIn("Microphone", svg)

    def test_wave_actions_target_detected_source(self):
        command = module.command_for("mic_mute", {"sourceId": 89})
        self.assertEqual(["wpctl", "set-mute", "89", "toggle"], command)

    def test_mic_actions_fall_back_to_default_source(self):
        command = module.command_for("mic_up")
        self.assertIn("@DEFAULT_AUDIO_SOURCE@", command)

    def test_media_action_uses_native_omarchy_service(self):
        self.assertEqual(["omarchy-shell", "media", "playPause"], module.command_for("media_play_pause"))

    def test_home_key_action_uses_wtype_without_a_shell(self):
        self.assertEqual(["wtype", "-k", "Home"], module.command_for("key_home"))

    def test_voxtype_push_to_talk_has_press_and_release_commands(self):
        self.assertEqual(["voxtype", "record", "start"], module.command_for("voxtype_push_to_talk"))
        self.assertEqual(["voxtype", "record", "stop"], module.release_command_for("voxtype_push_to_talk"))

    def test_terminal_action_defers_to_the_configured_terminal(self):
        command = module.command_for("terminal")
        self.assertEqual(["omarchy", "launch", "terminal"], command)
        for emulator in ("kitty", "alacritty", "ghostty", "foot"):
            self.assertNotIn(emulator, command,
                             "the terminal action must not hardcode one emulator")

    def test_desktop_application_launch_is_validated_and_uses_argv(self):
        with mock.patch.object(module, "desktop_file_exists", return_value=True):
            self.assertEqual(["uwsm-app", "--", "gtk-launch", "example.App"],
                             module.command_for("app:example.App"))

    def test_dotted_desktop_icon_name_is_not_treated_as_file_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            icon = root / ".local/share/icons/128x128/apps/com.example.App.png"
            icon.parent.mkdir(parents=True); icon.write_bytes(b"png")
            with mock.patch.object(module.pathlib.Path, "home", return_value=root):
                resolved = module.resolve_icon("com.example.App")
            self.assertEqual(str(icon), resolved)

    def test_set_key_persists_selected_action(self):
        with tempfile.TemporaryDirectory() as directory:
            config = pathlib.Path(directory)
            profile_path = config / "profile.json"
            profile_path.write_text('{"keys":[{"label":"Old","action":"terminal"}]}')
            with mock.patch.object(module, "CONFIG", config), mock.patch.object(module, "PROFILE", profile_path):
                module.set_control_action("keys", 0, "action", "lock")
                saved = module.json.loads(profile_path.read_text())
            self.assertEqual("lock", saved["keys"][0]["action"])

    def test_legacy_profile_is_migrated_to_elgato_control_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            config = root / "elgato-control"
            state = root / "state"
            legacy = root / "omarchy-streamdeck"
            legacy.mkdir()
            (legacy / "profile.json").write_text('{"name":"Migrated","keys":[]}')
            with mock.patch.object(module, "CONFIG", config), mock.patch.object(module, "STATE", state), \
                 mock.patch.object(module, "PROFILE", config / "profile.json"), \
                 mock.patch.object(module, "LEGACY_CONFIG", legacy):
                module.ensure_profile()
                self.assertEqual("Migrated", module.load_profile()["name"])

    def test_wave_gain_action_changes_hardware_control_without_shell(self):
        wave = {"card": 2, "gainRaw": 40, "sourceId": 89}
        with mock.patch.object(module, "set_alsa_control") as setter:
            module.perform_wave_action(wave, "wave_gain_up")
        setter.assert_called_once_with(2, "Mic Capture Volume", 42)

    def test_wave_push_to_default_uses_detected_source(self):
        wave = {"card": 2, "gainRaw": 40, "sourceId": 89}
        with mock.patch.object(module, "set_default_wave_source") as setter:
            module.perform_wave_action(wave, "wave_default")
        setter.assert_called_once_with(89)

    def test_avahi_discovery_keeps_resolved_ipv4_only(self):
        output = "\n".join([
            "=;eth0;IPv4;Key\\032Light\\032Left;_elg._tcp;local;left.local;192.0.2.2;9123;",
            "=;eth0;IPv6;Key Light Left;_elg._tcp;local;left.local;fe80::1;9123;",
            "+;eth0;IPv4;Unresolved;_elg._tcp;local",
        ])
        self.assertEqual([{"name": "Key Light Left", "host": "192.0.2.2", "port": 9123}],
                         module.parse_avahi_lights(output))

    def test_key_light_names_cannot_carry_rich_text_markup(self):
        output = "=;eth0;IPv4;<img\\032src=\"https://evil.example/x\">;_elg._tcp;local;left.local;192.0.2.2;9123;"
        lights = module.parse_avahi_lights(output)
        self.assertEqual("‹img src=\"https://evil.example/x\"›", lights[0]["name"])
        self.assertNotIn("<", lights[0]["name"])
        self.assertNotIn(">", lights[0]["name"])

    def test_http_status_cannot_overwrite_key_light_name_with_markup(self):
        light = {"name": "Desk", "host": "192.168.1.20"}
        with mock.patch.object(module, "light_request", return_value={
            "on": 1, "brightness": 40, "temperature": 200, "name": "<b>hijack</b>",
        }):
            state = module.light_states([light])[0]
        self.assertEqual("Desk", state["name"])

    def test_key_light_hosts_are_local_only(self):
        self.assertEqual("key-light.local", module.validate_light_host("key-light.local."))
        self.assertEqual("192.168.1.20", module.validate_light_host("192.168.1.20"))
        with self.assertRaises(ValueError): module.validate_light_host("example.com")
        with self.assertRaises(ValueError): module.validate_light_host("8.8.8.8")

    def test_key_light_resolution_rejects_public_and_loopback_addresses(self):
        public = [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 9123))]
        loopback = [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 9123))]
        private = [(module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("192.168.1.20", 9123))]
        with mock.patch.object(module.socket, "getaddrinfo", return_value=public):
            with self.assertRaises(ValueError): module.validate_light_resolution("key-light.local", 9123)
        with mock.patch.object(module.socket, "getaddrinfo", return_value=loopback):
            with self.assertRaises(ValueError): module.validate_light_resolution("key-light.local", 9123)
        with mock.patch.object(module.socket, "getaddrinfo", return_value=private):
            self.assertEqual({"192.168.1.20"}, module.validate_light_resolution("key-light.local", 9123))

    def test_key_light_http_redirects_are_rejected(self):
        handler = module.NoRedirectHandler()
        request = module.urllib.request.Request("http://192.168.1.20:9123/elgato/lights")
        with self.assertRaises(module.urllib.error.HTTPError) as caught:
            handler.redirect_request(request, None, 302, "Found", {}, "http://example.com/")
        caught.exception.close()

    def test_individual_key_light_brightness_targets_only_selected_light(self):
        lights = [{"host": "left.local"}, {"host": "right.local"}]
        states = [{"reachable": True, "brightness": 40}, {"reachable": True, "brightness": 50}]
        with mock.patch.object(module, "available_lights", return_value=lights), \
             mock.patch.object(module, "light_states", side_effect=[states, states]), \
             mock.patch.object(module, "light_request") as request:
            module.control_lights("1", "brightness", 72)
        request.assert_called_once_with(lights[1], {"brightness": 72, "on": 1})

    def test_key_light_temperature_converts_kelvin_to_device_mireds(self):
        lights = [{"host": "left.local"}]
        states = [{"reachable": True, "temperature": 200}]
        with mock.patch.object(module, "available_lights", return_value=lights), \
             mock.patch.object(module, "light_states", side_effect=[states, states]), \
             mock.patch.object(module, "light_request") as request:
            module.control_lights("all", "temperature", 5000)
        request.assert_called_once_with(lights[0], {"temperature": 200, "on": 1})


class ControlDispatchTests(unittest.TestCase):
    def make_daemon(self, deck):
        daemon = module.Daemon.__new__(module.Daemon)
        daemon.events = queue.Queue()
        daemon.decks = {deck.id(): {"deck": deck, "info": module.deck_capabilities(deck)}}
        daemon.profile = {
            "keys": [{"action": "terminal"}, {"action": "browser"}],
            "pedals": [{"action": "left"}, {"action": "middle"}, {"action": "right"}],
            "dials": [{"left": "volume_down", "right": "volume_up", "press": "volume_mute"}],
        }
        daemon.status = {"recentReports": {}}
        daemon.actions = []
        daemon.releases = []
        daemon.act = daemon.actions.append
        daemon.release = daemon.releases.append
        return daemon

    def test_pedal_press_and_release_both_dispatch(self):
        deck = FakeDeck(name="Stream Deck Pedal", keys=3, rows=1, columns=3, visual=False)
        daemon = self.make_daemon(deck)
        daemon._on_key(deck, 0, True)
        daemon._on_key(deck, 0, False)
        daemon.drain_events()
        self.assertEqual(["left"], daemon.actions)
        self.assertEqual(["left"], daemon.releases)

    def test_visual_key_fires_on_press_only(self):
        deck = FakeDeck()
        daemon = self.make_daemon(deck)
        daemon._on_key(deck, 1, True)
        daemon._on_key(deck, 1, False)
        daemon.drain_events()
        self.assertEqual(["browser"], daemon.actions)
        self.assertEqual([], daemon.releases)

    def test_out_of_range_key_is_ignored(self):
        deck = FakeDeck()
        daemon = self.make_daemon(deck)
        daemon._on_key(deck, 31, True)
        daemon.drain_events()
        self.assertEqual([], daemon.actions)

    def test_events_from_an_unknown_deck_are_dropped(self):
        deck = FakeDeck()
        daemon = self.make_daemon(deck)
        daemon._on_key(FakeDeck(ident="ghost:1"), 0, True)
        daemon.drain_events()
        self.assertEqual([], daemon.actions)

    @unittest.skipIf(module.DialEventType is None, "python-elgato-streamdeck is not installed")
    def test_dial_turn_repeats_per_detent_and_is_capped(self):
        deck = FakeDeck(name="Stream Deck +", keys=8, rows=2, columns=4, dials=4, touch=True)
        daemon = self.make_daemon(deck)
        daemon._on_dial(deck, 0, module.DialEventType.TURN, 3)
        daemon._on_dial(deck, 0, module.DialEventType.TURN, -1)
        daemon._on_dial(deck, 0, module.DialEventType.TURN, 99)
        daemon.drain_events()
        self.assertEqual(["volume_up"] * 3 + ["volume_down"] + ["volume_up"] * 5, daemon.actions)

    @unittest.skipIf(module.DialEventType is None, "python-elgato-streamdeck is not installed")
    def test_dial_push_is_edge_triggered(self):
        deck = FakeDeck(name="Stream Deck +", keys=8, rows=2, columns=4, dials=4, touch=True)
        daemon = self.make_daemon(deck)
        daemon._on_dial(deck, 0, module.DialEventType.PUSH, True)
        daemon._on_dial(deck, 0, module.DialEventType.PUSH, False)
        daemon.drain_events()
        self.assertEqual(["volume_mute"], daemon.actions)


class ConnectTests(unittest.TestCase):
    def make_daemon(self):
        daemon = module.Daemon.__new__(module.Daemon)
        daemon.decks, daemon.events, daemon.manager = {}, queue.Queue(), None
        daemon.profile = {"name": "Test", "keys": [{"label": "Terminal", "action": "terminal"}],
                          "dials": [], "pedals": []}
        daemon.mtime = 0
        daemon.brightness = 55
        daemon.light_states = []
        daemon.discovered_lights = []
        daemon.last_light_discovery = 0
        daemon.lcd_signature = None
        daemon.running = True
        daemon.status = {"plus": None, "pedal": None, "wave": None, "lights": [],
                         "devices": [], "recentReports": {}, "error": ""}
        return daemon

    def connect_with(self, decks, decorate=False):
        directory = tempfile.TemporaryDirectory()
        config = pathlib.Path(directory.name)
        patches = [
            mock.patch.object(module, "CONFIG", config),
            mock.patch.object(module, "STATE", config / "state"),
            mock.patch.object(module, "PROFILE", config / "profile.json"),
            mock.patch.object(module, "DeviceManager", lambda: FakeManager(decks)),
            mock.patch.object(module, "detect_wave", return_value=None),
        ]
        if not decorate:
            patches.append(mock.patch.object(module.Daemon, "decorate", lambda self, deck: None))
        daemon = self.make_daemon()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            if decorate:
                daemon.connect()
            else:
                with patches[5]:
                    daemon.connect()
        directory.cleanup()
        return daemon

    def test_connect_opens_the_deck_and_registers_callbacks(self):
        deck = FakeDeck()
        daemon = self.connect_with([deck])
        self.assertTrue(deck.opened)
        self.assertEqual(1, deck.resets)
        self.assertIsNotNone(deck.key_callback)
        self.assertIsNone(deck.dial_callback, "an XL has no dials to subscribe to")
        self.assertEqual("", daemon.status["error"])

    def test_connect_publishes_geometry_for_the_panel(self):
        daemon = self.connect_with([FakeDeck()])
        self.assertEqual(32, daemon.status["plus"]["keyCount"])
        self.assertEqual(8, daemon.status["plus"]["keyColumns"])
        self.assertEqual(4, daemon.status["plus"]["keyRows"])
        self.assertEqual("SN-fake:0", daemon.status["plus"]["serial"])
        self.assertIsNone(daemon.status["pedal"])
        self.assertEqual([daemon.status["plus"]], daemon.status["devices"])

    def test_connect_grows_the_stored_profile_to_the_deck(self):
        daemon = self.connect_with([FakeDeck()])
        self.assertEqual(32, len(daemon.profile["keys"]))
        self.assertEqual("terminal", daemon.profile["keys"][0]["action"])

    def test_a_pedal_fills_its_own_status_slot(self):
        pedal = FakeDeck(name="Stream Deck Pedal", ident="pedal:0", keys=3, rows=1,
                         columns=3, visual=False)
        daemon = self.connect_with([FakeDeck(), pedal])
        self.assertEqual("Stream Deck Pedal", daemon.status["pedal"]["product"])
        self.assertEqual("Stream Deck XL", daemon.status["plus"]["product"])

    def test_dials_are_subscribed_only_when_present(self):
        plus = FakeDeck(name="Stream Deck +", ident="plus:0", keys=8, rows=2,
                        columns=4, dials=4, touch=True)
        self.connect_with([plus])
        self.assertIsNotNone(plus.dial_callback)

    def test_unplugged_deck_is_closed_and_dropped(self):
        deck = FakeDeck()
        daemon = self.connect_with([deck])
        with mock.patch.object(module, "DeviceManager", lambda: FakeManager([])), \
             mock.patch.object(module, "detect_wave", return_value=None):
            daemon.manager = None
            daemon.connect()
        self.assertFalse(deck.opened)
        self.assertEqual({}, daemon.decks)
        self.assertIsNone(daemon.status["plus"])

    def test_decorate_paints_every_key_at_the_deck_size(self):
        deck = FakeDeck()
        with mock.patch.object(module, "rendered_key_image") as render, \
             mock.patch.object(module, "Image", mock.MagicMock()), \
             mock.patch.object(module, "PILHelper", mock.MagicMock()):
            render.return_value = mock.MagicMock(**{"exists.return_value": True})
            self.connect_with([deck], decorate=True)
        self.assertEqual(55, deck.brightness)
        # Only the one configured key carries an action; blanks are skipped.
        self.assertEqual([0], sorted(deck.images))
        self.assertEqual((96, 96), render.call_args[0][3])


class QmlPlainTextTests(unittest.TestCase):
    PANEL = pathlib.Path(__file__).parents[1] / "Panel.qml"

    def test_network_controlled_qml_text_forces_plain_text(self):
        """Key Light names and other external strings must not use AutoText."""
        panel = self.PANEL.read_text()
        bindings = (
            "text: modelData.name; textFormat: Text.PlainText",
            "root.selectedLightName(); textFormat: Text.PlainText",
            "root.status.wave.product : \"Wave microphone\"; textFormat: Text.PlainText",
            "root.status.profile || \"Omarchy Default\"; textFormat: Text.PlainText",
            "text: modelData.label; textFormat: Text.PlainText",
            "root.actionName(modelData.action); textFormat: Text.PlainText",
            'text: root.error || root.status.error || ""; textFormat: Text.PlainText',
        )
        for binding in bindings:
            self.assertIn(binding, panel, f"untrusted QML binding lacks PlainText: {binding}")


if __name__ == "__main__":
    unittest.main()
