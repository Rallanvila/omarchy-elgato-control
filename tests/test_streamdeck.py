import importlib.machinery
import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock


SCRIPT = pathlib.Path(__file__).parents[1] / "bin" / "omarchy-streamdeck"
loader = importlib.machinery.SourceFileLoader("omarchy_streamdeck", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class DeviceModelTests(unittest.TestCase):
    def test_plus_capabilities_are_optional_and_explicit(self):
        caps = module.DEVICE_SPECS[module.PLUS]["capabilities"]
        self.assertIn("lcd", caps)
        self.assertIn("dials", caps)
        self.assertNotIn("pedals", caps)

    def test_pedal_capabilities_do_not_assume_lcd(self):
        self.assertEqual(["pedals"], module.DEVICE_SPECS[module.PEDAL]["capabilities"])

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

    def test_key_light_hosts_are_local_only(self):
        self.assertEqual("key-light.local", module.validate_light_host("key-light.local."))
        self.assertEqual("192.168.1.20", module.validate_light_host("192.168.1.20"))
        with self.assertRaises(ValueError): module.validate_light_host("example.com")
        with self.assertRaises(ValueError): module.validate_light_host("8.8.8.8")


class PedalParserTests(unittest.TestCase):
    def make_daemon(self):
        daemon = module.Daemon.__new__(module.Daemon)
        daemon.previous = {}
        daemon.profile = {"pedals": [{"action": "left"}, {"action": "middle"}, {"action": "right"}]}
        daemon.actions = []
        daemon.releases = []
        daemon.act = daemon.actions.append
        daemon.release = daemon.releases.append
        return daemon

    def test_three_byte_report_press_is_edge_triggered(self):
        daemon = self.make_daemon()
        daemon.parse_pedal(bytes([1, 0, 3, 1, 0, 0]))
        daemon.parse_pedal(bytes([1, 0, 3, 1, 0, 0]))
        daemon.parse_pedal(bytes([1, 0, 3, 0, 0, 0]))
        self.assertEqual(["left"], daemon.actions)
        self.assertEqual(["left"], daemon.releases)

    def test_legacy_padded_report_is_supported(self):
        daemon = self.make_daemon()
        daemon.parse_pedal(bytes([1, 0, 3, 0, 0, 1, 0]))
        self.assertEqual(["middle"], daemon.actions)


if __name__ == "__main__":
    unittest.main()
