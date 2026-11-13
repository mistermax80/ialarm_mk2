"""Test zone device relationships without connecting to an alarm panel."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from custom_components.ialarm_mk2 import binary_sensor
from custom_components.ialarm_mk2.const import DOMAIN


class TestZoneDeviceRegistry(unittest.TestCase):
    """Keep device identities stable while linking zones by registry ID."""

    def setUp(self):
        """Use a mock coordinator; never instantiate the panel interface."""
        self.hass = MagicMock()
        self.coordinator = MagicMock()
        self.coordinator.config_entry.entry_id = "entry-a"
        self.coordinator.hub.username = "panel-a"
        self.entity = binary_sensor.IAlarmmkSensor(
            self.coordinator, "Kitchen", 0, "zone-a", 2
        )
        self.entity.hass = self.hass
        self.devices = {
            ("entry-a", (DOMAIN, "panel-a")): "panel-device-a",
            ("entry-a", (DOMAIN, "zone-a")): "zone-device-a",
        }

        def lookup(hass, identifier, *, config_entry_id):
            self.assertIs(hass, self.hass)
            try:
                return self.devices[(config_entry_id, identifier)]
            except KeyError as err:
                raise ValueError("Device not registered") from err

        self.lookup = self.enterContext(
            patch.object(
                binary_sensor.dr,
                "async_get_device_id_by_identifier",
                side_effect=lookup,
                create=True,
            )
        )

    def test_existing_zone_keeps_identity_and_parent(self):
        """Use the actual parent ID, preserving the existing zone identity."""
        info = self.entity.device_info
        self.assertEqual(info, {
            "identifiers": {(DOMAIN, "zone-a")},
            "name": "Kitchen",
            "serial_number": "zone-a",
            "manufacturer": "antifurto 365",
            "model": "Sensore",
            "via_device_id": "panel-device-a",
        })
        self.assertEqual(self.entity.unique_id, "zone-a")
        self.lookup.assert_has_calls([
            call(self.hass, (DOMAIN, "panel-a"), config_entry_id="entry-a"),
            call(self.hass, (DOMAIN, "zone-a"), config_entry_id="entry-a"),
        ])

    def test_new_zone_links_to_existing_panel(self):
        """A zone need not already exist in the registry."""
        del self.devices[("entry-a", (DOMAIN, "zone-a"))]
        self.assertEqual(self.entity.device_info["via_device_id"], "panel-device-a")

    def test_missing_panel_does_not_use_another_entry(self):
        """An identically identified device in another entry is not a parent."""
        del self.devices[("entry-a", (DOMAIN, "panel-a"))]
        self.devices[("entry-b", (DOMAIN, "panel-a"))] = "unrelated-panel"
        info = self.entity.device_info
        self.assertNotIn("via_device_id", info)
        self.assertNotIn("via_device", info)
        # A later evaluation can resolve a panel registered after the zone.
        self.devices[("entry-a", (DOMAIN, "panel-a"))] = "panel-device-a"
        self.assertEqual(self.entity.device_info["via_device_id"], "panel-device-a")

    def test_multiple_entries_resolve_their_own_parent(self):
        """Even shared identifiers are resolved within the selected entry."""
        self.devices[("entry-b", (DOMAIN, "panel-a"))] = "panel-device-b"
        self.devices[("entry-b", (DOMAIN, "zone-a"))] = "zone-device-b"
        self.assertEqual(self.entity.device_info["via_device_id"], "panel-device-a")
        self.coordinator.config_entry.entry_id = "entry-b"
        self.assertEqual(self.entity.device_info["via_device_id"], "panel-device-b")

    def test_matching_identifiers_do_not_link_to_self(self):
        """Identical panel and zone identifiers cannot form a parent link."""
        self.coordinator.hub.username = "zone-a"
        self.assertNotIn("via_device_id", self.entity.device_info)
        self.lookup.assert_not_called()

    def test_existing_aliases_do_not_link_to_self(self):
        """Different identifiers may already refer to the same registry device."""
        self.devices[("entry-a", (DOMAIN, "zone-a"))] = "panel-device-a"
        self.assertNotIn("via_device_id", self.entity.device_info)

    def test_older_registry_without_helper(self):
        """Fallback lookup includes only devices belonging to the config entry."""
        panel = SimpleNamespace(
            id="panel-device-a", identifiers={(DOMAIN, "panel-a")}
        )
        zone = SimpleNamespace(id="zone-device-a", identifiers={(DOMAIN, "zone-a")})
        registry = MagicMock()
        with (
            patch.object(binary_sensor.dr, "async_get_device_id_by_identifier", None),
            patch.object(binary_sensor.dr, "async_get", return_value=registry),
            patch.object(
                binary_sensor.dr, "async_entries_for_config_entry",
                return_value=[panel, zone],
            ) as entries,
        ):
            self.assertEqual(self.entity.device_info["via_device_id"], panel.id)
            entries.assert_called_once_with(registry, "entry-a")
        self.lookup.assert_not_called()

    def test_older_registry_missing_parent_and_self_reference(self):
        """Fallback also omits missing parents and existing self references."""
        with (
            patch.object(binary_sensor.dr, "async_get_device_id_by_identifier", None),
            patch.object(binary_sensor.dr, "async_get"),
            patch.object(binary_sensor.dr, "async_entries_for_config_entry") as entries,
        ):
            entries.return_value = []
            self.assertNotIn("via_device_id", self.entity.device_info)
            entries.return_value = [SimpleNamespace(
                id="shared-device", identifiers={(DOMAIN, "panel-a"), (DOMAIN, "zone-a")}
            )]
            self.assertNotIn("via_device_id", self.entity.device_info)


if __name__ == "__main__":
    unittest.main()
