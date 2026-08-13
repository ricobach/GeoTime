# GeoTime

GeoTime is a custom Home Assistant integration that calculates time and sun information from the current geographic location of a `person` or `device_tracker` entity.

## Sensors

Each configured entity creates three sensors:

- **Local Time** — local clock time at the tracked location.
- **Sun Status** — whether the sun is above or below the horizon. Sunrise and sunset are exposed as attributes when available.
- **Timezone** — IANA timezone name such as `Europe/Copenhagen`.

The integration reads the latitude and longitude from the selected Home Assistant entity and resolves the timezone locally. No external geocoding or timezone API is required.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/ricobach/GeoTime` as a custom repository of type **Integration**.
3. Install **GeoTime**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **GeoTime**.
6. Select a `person` or `device_tracker` entity.

## Requirements

The source entity must expose `latitude` and `longitude` attributes.

## License

MIT
