"""Image platform for GeoTime."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import logging
from math import cos, pi, sin
from urllib.parse import urljoin

from aiohttp import ClientError
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.network import get_url

from .const import CONF_TARGET_ENTITY, DEFAULT_UPDATE_INTERVAL, DOMAIN, SENSOR_SUN_STATUS
from .sensor import _async_get_data

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GeoTime image entity."""
    source_entity = entry.options.get(
        CONF_TARGET_ENTITY,
        entry.data[CONF_TARGET_ENTITY],
    )
    async_add_entities([GeoTimeDayNightImage(hass, entry, source_entity)])


class GeoTimeDayNightImage(ImageEntity):
    """Person/device image with a day/night indicator in the upper-right corner."""

    _attr_content_type = "image/png"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity: str,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)
        self._entry = entry
        self._source_entity = source_entity
        self._image_bytes: bytes | None = None
        self._last_signature: tuple[str | None, str] | None = None
        self._attr_unique_id = f"{entry.entry_id}_day_night_image"
        self._attr_name = f"{entry.title} GeoTime Image"

    async def async_added_to_hass(self) -> None:
        """Start tracking source changes and day/night transitions."""
        await super().async_added_to_hass()
        await self._async_refresh_image()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity],
                self._handle_source_change,
            )
        )
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._handle_interval,
                DEFAULT_UPDATE_INTERVAL,
                name=f"GeoTime image refresh {self._entry.entry_id}",
            )
        )

    @callback
    def _handle_source_change(self, _event) -> None:
        """Refresh when the source person/device tracker changes."""
        self.hass.async_create_task(
            self._async_refresh_image(),
            f"Refresh GeoTime image {self._entry.entry_id}",
        )

    @callback
    def _handle_interval(self, _now) -> None:
        """Check for sunrise/sunset transitions while the source is stationary."""
        self.hass.async_create_task(
            self._async_refresh_image(),
            f"Refresh GeoTime day/night status {self._entry.entry_id}",
        )

    async def _async_refresh_image(self) -> None:
        """Rebuild the image only when its source picture or sun status changed."""
        state = self.hass.states.get(self._source_entity)
        if state is None:
            return

        source_picture = state.attributes.get("entity_picture")
        geo_data = await _async_get_data(self.hass, self._entry)
        sun_status = geo_data.get(SENSOR_SUN_STATUS, "Unknown")
        signature = (source_picture, sun_status)

        if signature == self._last_signature:
            return

        if not source_picture:
            self._last_signature = signature
            if self._image_bytes is not None:
                self._image_bytes = None
                self._attr_image_last_updated = datetime.now(UTC)
                self.async_write_ha_state()
            return

        source_bytes = await self._async_fetch_source_image(source_picture)
        if source_bytes is None:
            return

        try:
            image_bytes = await self.hass.async_add_executor_job(
                _compose_day_night_image,
                source_bytes,
                sun_status,
            )
        except (OSError, UnidentifiedImageError) as err:
            _LOGGER.debug(
                "Unable to compose image for %s: %s",
                self._source_entity,
                err,
            )
            return

        self._image_bytes = image_bytes
        self._last_signature = signature
        self._attr_image_last_updated = datetime.now(UTC)
        self.async_write_ha_state()

    async def _async_fetch_source_image(self, picture_url: str) -> bytes | None:
        """Fetch the source entity picture."""
        url = picture_url
        if picture_url.startswith("/"):
            try:
                url = urljoin(get_url(self.hass, prefer_external=False), picture_url)
            except Exception as err:  # Home Assistant may not have an internal URL.
                _LOGGER.debug("Unable to resolve source image URL: %s", err)
                return None

        try:
            async with async_get_clientsession(self.hass).get(url) as response:
                if response.status != 200:
                    _LOGGER.debug(
                        "Unable to fetch %s image: HTTP %s",
                        self._source_entity,
                        response.status,
                    )
                    return None
                return await response.read()
        except ClientError as err:
            _LOGGER.debug(
                "Unable to fetch %s image: %s",
                self._source_entity,
                err,
            )
            return None

    async def async_image(self) -> bytes | None:
        """Return the cached composite image."""
        return self._image_bytes

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="GeoTime",
        )


def _compose_day_night_image(source: bytes, sun_status: str) -> bytes:
    """Overlay a sun or moon badge in the upper-right corner."""
    with Image.open(BytesIO(source)) as source_image:
        base = ImageOps.exif_transpose(source_image).convert("RGBA")

    shortest_side = min(base.size)
    badge_size = max(40, round(shortest_side * 0.24))
    badge_size = min(badge_size, shortest_side)
    margin = max(5, round(badge_size * 0.10))

    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    edge = max(1, round(badge_size * 0.035))
    draw.ellipse(
        (edge, edge, badge_size - edge, badge_size - edge),
        fill=(255, 255, 255, 225),
        outline=(255, 255, 255, 245),
        width=edge,
    )

    if sun_status == "Above":
        _draw_sun(draw, badge_size)
    else:
        _draw_moon(draw, badge_size)

    x = max(0, base.width - badge_size - margin)
    y = min(margin, max(0, base.height - badge_size))
    base.alpha_composite(badge, (x, y))

    output = BytesIO()
    base.save(output, format="PNG")
    return output.getvalue()


def _draw_sun(draw: ImageDraw.ImageDraw, size: int) -> None:
    """Draw a sun inside the badge."""
    center = size / 2
    core_radius = size * 0.19
    ray_inner = size * 0.30
    ray_outer = size * 0.39
    color = (255, 183, 0, 255)
    line_width = max(2, round(size * 0.045))

    draw.ellipse(
        (
            center - core_radius,
            center - core_radius,
            center + core_radius,
            center + core_radius,
        ),
        fill=color,
    )

    for index in range(8):
        angle = index * pi / 4
        draw.line(
            (
                center + cos(angle) * ray_inner,
                center + sin(angle) * ray_inner,
                center + cos(angle) * ray_outer,
                center + sin(angle) * ray_outer,
            ),
            fill=color,
            width=line_width,
        )


def _draw_moon(draw: ImageDraw.ImageDraw, size: int) -> None:
    """Draw a crescent moon inside the badge."""
    color = (52, 78, 112, 255)
    radius = size * 0.27
    center_x = size * 0.47
    center_y = size * 0.50

    draw.ellipse(
        (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        ),
        fill=color,
    )

    cut_radius = radius * 0.92
    cut_x = center_x + radius * 0.48
    cut_y = center_y - radius * 0.10
    draw.ellipse(
        (
            cut_x - cut_radius,
            cut_y - cut_radius,
            cut_x + cut_radius,
            cut_y + cut_radius,
        ),
        fill=(255, 255, 255, 225),
    )
