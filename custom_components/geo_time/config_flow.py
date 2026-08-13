"""Config flow for GeoTime."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_TARGET_ENTITY, DOMAIN

_TARGET_DOMAINS = ["person", "device_tracker"]


class GeoTimeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GeoTime."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            entity_id = user_input[CONF_TARGET_ENTITY]
            state = self.hass.states.get(entity_id)
            title = state.name if state else entity_id

            await self.async_set_unique_id(entity_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=title,
                data={CONF_TARGET_ENTITY: entity_id},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET_ENTITY): EntitySelector(
                        EntitySelectorConfig(domain=_TARGET_DOMAINS)
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return GeoTimeOptionsFlow(config_entry)


class GeoTimeOptionsFlow(config_entries.OptionsFlow):
    """Handle GeoTime options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage GeoTime options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_entity = self.config_entry.options.get(
            CONF_TARGET_ENTITY,
            self.config_entry.data[CONF_TARGET_ENTITY],
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TARGET_ENTITY,
                        default=current_entity,
                    ): EntitySelector(EntitySelectorConfig(domain=_TARGET_DOMAINS))
                }
            ),
        )
