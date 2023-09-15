"""Config flow for Kindhome Solarbeaker integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .kindhome_solarbeaker_ble import KindhomeSolarbeakerDevice
from .utils import log

_LOGGER = logging.getLogger(__name__)


class KindhomeSolarbeakerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for kindhome."""

    VERSION = 1

    def _create_config_entry(self, address, name=None):
        title = f"{name} ({address})"
        return self.async_create_entry(
            title=title, data={"address": address, "name": name}
        )

    def __init__(self) -> None:
        """Initialize the config flow."""
        log(_LOGGER, "KindhomeSolarbeakerConfigFlow.__init__", "called!")
        self._discover_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Check if discovered should be presented for user to be confirmed."""
        log(_LOGGER, "async_step_bluetooth", f"called! {discovery_info.as_dict()}")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        log(
            _LOGGER,
            "async_step_bluetooth",
            f"address: {discovery_info.address} hasn't been configured",
        )

        if not KindhomeSolarbeakerDevice.supported(discovery_info):
            return self.async_abort(reason="not_supported")

        self._discover_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm device setup."""
        log(_LOGGER, "async_step_bluetooth_confirm", "called!")
        assert self._discover_info is not None

        log(_LOGGER, "async_step_bluetooth_confirm", f"user_input = {user_input}")
        if user_input is not None:
            return self._create_config_entry(
                self._discover_info.address, self._discover_info.name
            )

        title = f"{self._discover_info.name} ({self._discover_info.address})"
        log(_LOGGER, "async_step_bluetooth_confirm", f"title = {title}")

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""

        log(_LOGGER, "async_step_user", f"called!, user_input={user_input}")

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name = self._discovered_devices[address]

            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self._create_config_entry(address, name)

        current_addresses = self._async_current_ids()

        log(_LOGGER, "async_step_user", f"current_addresses={current_addresses}")
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if KindhomeSolarbeakerDevice.supported(discovery_info):
                self._discovered_devices[address] = discovery_info.name

        if not self._discovered_devices:
            log(_LOGGER, "async_step_user", "no devices found, aborting!")
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        [
                            f"{name}: {address}"
                            for address, name in self._discovered_devices.items()
                        ]
                    )
                }
            ),
        )
