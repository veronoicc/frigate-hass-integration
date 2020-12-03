"""Adds config flow for Frigate."""
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.typing import DiscoveryInfoType
import voluptuous as vol
import logging

from .api import FrigateApiClient
from .const import (
    DOMAIN,
    PLATFORMS,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class FrigateFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Frigate."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        # Ensure mqtt
        if not 'mqtt' in self.hass.config.components:
            return self.async_abort(reason="mqtt_required")
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._valid(user_input)
            if valid:
                return self.async_create_entry(
                    title="Frigate", data=user_input
                )

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def async_step_discovery_confirm(self, user_input=None):
        """Handle user-confirmation of discovered node."""
        self._errors = {}

        # Ensure mqtt
        if not 'mqtt' in self.hass.config.components:
            self._errors["base"] = "mqtt"

        discovery_data = {"host": f"http://{self._host}:{self._port}"}
        if user_input is not None:
            valid = await self._valid(discovery_data)
            if valid:
                return self.async_create_entry(
                    title="Frigate", data=discovery_data
                )
        return self.async_show_form(
            step_id="discovery_confirm", description_placeholders=discovery_data, errors=self._errors
        )

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf discovery."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        self._host = discovery_info[CONF_HOST]
        self._port = discovery_info[CONF_PORT]

        return await self.async_step_discovery_confirm()

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("host"): str}
            ),
            errors=self._errors,
        )

    async def _valid(self, input_data):
        valid = await self._test_credentials(
            input_data["host"]
        )
        if not 'mqtt' in self.hass.config.components:
            self._errors["base"] = "mqtt"
        elif valid:
            return True
        else:
            self._errors["base"] = "auth"

        return False

    async def _test_credentials(self, url):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = FrigateApiClient(url, session)
            await client.async_get_stats()
            return True
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error(e)
            pass
        return False
