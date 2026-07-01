"""Migration of dict-style sensor unique_ids to clean slugs.

SolisSensorGroup used to bake str(entity definition dict) into unique_ids, so
any definition tweak re-keyed the entity (orphan + twin). The migration
extracts the embedded slug and re-keys the original entry, removing any twin.
"""

from unittest.mock import MagicMock, patch

from custom_components.solis_modbus import _migrate_dict_style_unique_ids
from custom_components.solis_modbus.const import DOMAIN

OLD_UID = (
    "solis_modbus_SN123_{'name': 'PV Total Energy Generation', "
    "'unique': 'solis_modbus_inverter_pv_total_generation', "
    "'register': ['33029', '33030'], 'multiplier': 1}"
)
NEW_UID = "solis_modbus_SN123_solis_modbus_inverter_pv_total_generation"


def make_reg_entry(entity_id, unique_id, entry_id="entry1"):
    e = MagicMock()
    e.entity_id = entity_id
    e.unique_id = unique_id
    e.platform = DOMAIN
    e.config_entry_id = entry_id
    e.domain = entity_id.split(".")[0]
    return e


def make_controller():
    controller = MagicMock()
    controller.device_serial_number = "SN123"
    controller.identification = None
    return controller


def run_migration(reg_entries, twin_lookup=None):
    ent_reg = MagicMock()
    ent_reg.entities = {e.entity_id: e for e in reg_entries}
    ent_reg.async_get_entity_id.side_effect = lambda domain, dom, uid: (twin_lookup or {}).get(uid)
    entry = MagicMock()
    entry.entry_id = "entry1"
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=ent_reg):
        _migrate_dict_style_unique_ids(MagicMock(), entry, make_controller())
    return ent_reg


def test_rekeys_dict_style_unique_id():
    original = make_reg_entry("sensor.solis_inverter_pv_total_energy_generation", OLD_UID)
    ent_reg = run_migration([original])
    ent_reg.async_update_entity.assert_called_once_with("sensor.solis_inverter_pv_total_energy_generation", new_unique_id=NEW_UID)
    ent_reg.async_remove.assert_not_called()


def test_removes_twin_then_rekeys_original():
    original = make_reg_entry("sensor.solis_inverter_pv_total_energy_generation", OLD_UID)
    ent_reg = run_migration([original], twin_lookup={NEW_UID: "sensor.server_room_pv_total_energy_generation_2"})
    ent_reg.async_remove.assert_called_once_with("sensor.server_room_pv_total_energy_generation_2")
    ent_reg.async_update_entity.assert_called_once_with("sensor.solis_inverter_pv_total_energy_generation", new_unique_id=NEW_UID)


def test_clean_and_foreign_entries_untouched():
    clean = make_reg_entry("sensor.solis_inverter_battery_soc", "solis_modbus_SN123_solis_modbus_inverter_battery_soc")
    switch = make_reg_entry("switch.solis_self_use", "solis_modbus_SN123_43110_0")
    other_entry = make_reg_entry("sensor.other", OLD_UID, entry_id="entry2")
    ent_reg = run_migration([clean, switch, other_entry])
    ent_reg.async_update_entity.assert_not_called()
    ent_reg.async_remove.assert_not_called()
