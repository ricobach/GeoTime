"""Sensor platform for GeoTime."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astral import LocationInfo
from astral.sun import sun
from timezonefinder import TimezoneFinder

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import (
    CONF_TARGET_ENTITY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SENSOR_LOCAL_TIME,
    SENSOR_SUN_STATUS,
    SENSOR_TIMEZONE,
)

_LOGGER = logging.getLogger(__name__)
_TIMEZONE_FINDER = TimezoneFinder(in_memory=True)

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key=SENSOR_LOCAL_TIME,
        translation_key="local_time",
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key=SENSOR_SUN_STATUS,
        translation_key="sun_status",
        icon="mdi:white-balance-sunny",
    ),
    SensorEntityDescription(
        key=SENSOR_TIMEZONE,
        translation_key="timezone",
        icon="mdi:earth",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GeoTime sensors from a config entry."""

    async def async_update_data() -> dict[str, Any]:
        return await _async_get_data(hass, entry)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=async_update_data,
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        GeoTimeSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


async def _async_get_data(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Calculate local time, timezone and sun status for the tracked entity."""
    entity_id = entry.options.get(
        CONF_TARGET_ENTITY,
        entry.data[CONF_TARGET_ENTITY],
    )
    state = hass.states.get(entity_id)

    if state is None:
        _LOGGER.debug("Tracked entity %s is unavailable", entity_id)
        return _default_data(entity_id)

    latitude = state.attributes.get(ATTR_LATITUDE)
    longitude = state.attributes.get(ATTR_LONGITUDE)

    if latitude is None or longitude is None:
        _LOGGER.debug("Tracked entity %s has no coordinates", entity_id)
        return _default_data(entity_id)

    timezone_name = await asyncio.to_thread(
        _TIMEZONE_FINDER.timezone_at,
        lat=float(latitude),
        lng=float(longitude),
    )
    if not timezone_name:
        return _default_data(entity_id)

    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        _LOGGER.warning("Timezone %s could not be loaded", timezone_name)
        return _default_data(entity_id)

    now = datetime.now(timezone)
    location = LocationInfo("", "", timezone_name, float(latitude), float(longitude))

    sunrise = None
    sunset = None
    try:
        solar = sun(location.observer, date=now.date(), tzinfo=timezone)
        sunrise = solar["sunrise"]
        sunset = solar["sunset"]
        sun_status = "Above" if sunrise <= now <= sunset else "Below"
    except ValueError:
        # Polar day/night can have no sunrise or sunset on a given date.
        from astral.sun import elevation

        sun_status = "Above" if elevation(location.observer, now) > 0 else "Below"

    return {
        SENSOR_LOCAL_TIME: now.strftime("%H:%M"),
        SENSOR_TIMEZONE: timezone_name,
        SENSOR_SUN_STATUS: sun_status,
        "sunrise": sunrise.strftime("%H:%M:%S %z") if sunrise else None,
        "sunset": sunset.strftime("%H:%M:%S %z") if sunset else None,
        "source_entity": entity_id,
    }


def _default_data(entity_id: str) -> dict[str, Any]:
    """Return placeholder data while source location is unavailable."""
    return {
        SENSOR_LOCAL_TIME: "Unknown",
        SENSOR_TIMEZONE: "Unknown",
        SENSOR_SUN_STATUS: "Unknown",
        "sunrise": None,
        "sunset": None,
        "source_entity": entity_id,
    }


class GeoTimeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a GeoTime sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> str:
        """Return the sensor state."""
        return self.coordinator.data.get(self.entity_description.key, "Unknown")

    @property
    def entity_picture(self) -> str | None:
        """Expose the generated GeoTime day/night image on Local Time."""
        if self.entity_description.key != SENSOR_LOCAL_TIME:
            return None

        image_entity_id = er.async_get(self.hass).async_get_entity_id(
            "image",
            DOMAIN,
            f"{self._entry.entry_id}_day_night_image",
        )
        if image_entity_id is None:
            return None

        image_state = self.hass.states.get(image_entity_id)
        if image_state is None:
            return None

        picture = image_state.attributes.get("entity_picture")
        if not picture:
            return None

        # The ImageEntity proxy URL itself can remain unchanged when the image
        # bytes are rebuilt. Add the image entity state timestamp so dashboard
        # cards receive a new URL whenever the generated image changes.
        image_version = image_state.state
        if image_version and image_version not in ("unknown", "unavailable"):
            separator = "&" if "?" in picture else "?"
            return f"{picture}{separator}v={quote(image_version, safe='')}"

        return picture

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes: dict[str, Any] = {
            "source_entity": self.coordinator.data.get("source_entity")
        }
        if self.entity_description.key == SENSOR_SUN_STATUS:
            attributes.update(
                {
                    "sunrise": self.coordinator.data.get("sunrise"),
                    "sunset": self.coordinator.data.get("sunset"),
                }
            )
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="GeoTime",
        )
