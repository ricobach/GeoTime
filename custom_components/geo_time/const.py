"""Constants for the GeoTime integration."""

from datetime import timedelta

DOMAIN = "geo_time"
PLATFORMS = ["sensor"]

CONF_TARGET_ENTITY = "target_entity"

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=30)

SENSOR_LOCAL_TIME = "local_time"
SENSOR_SUN_STATUS = "sun_status"
SENSOR_TIMEZONE = "timezone"
