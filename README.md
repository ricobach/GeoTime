# GeoTime

GeoTime is a custom Home Assistant integration that calculates local time, timezone, sun status, and a day/night person image from the current geographic location of a `person` or `device_tracker` entity.

The integration works from the latitude and longitude already provided by Home Assistant. Timezone lookup and sun calculations are performed locally; no external geocoding or timezone API is required.

## Features

For each configured `person` or `device_tracker`, GeoTime creates three sensors and one image entity:

- **Local Time** — the local clock time at the tracked entity's current location. The sensor exposes the generated GeoTime day/night image through its `entity_picture` for dashboard use.
- **Sun Status** — `Above` or `Below`, based on whether the sun is above the horizon at that location. Sunrise and sunset are exposed as attributes when available.
- **Timezone** — the IANA timezone name, for example `Europe/Copenhagen`.
- **GeoTime Image** — the source entity's picture with a day/night indicator in the upper-right corner. This image entity provides the generated image used by the Local Time sensor.

## Day/night image

The GeoTime image uses the `entity_picture` from the selected `person` or `device_tracker` as its base image.

A small indicator is added in the **upper-right corner**:

- ☀️ **Sun** when the sun is above the horizon at the tracked location.
- 🌙 **Moon** when the sun is below the horizon at the tracked location.

GeoTime updates the generated image when the source entity changes and updates the day/night indicator according to the sun status at the tracked location.

The generated image is exposed as a real Home Assistant `image` entity and is also exposed through the **Local Time sensor's `entity_picture`**, making the Local Time sensor convenient to use with dashboard cards that support entity pictures.

A generated image entity will typically look similar to:

```text
image.rico_geotime_image
```

The exact entity ID depends on the name of the configured entry and can be changed in Home Assistant's entity settings.

### Dashboard example

The generated image can be used as the background of a Picture Elements card while the Local Time sensor provides the displayed time:

```yaml
type: picture-elements
image_entity: image.rico_geotime_image
elements:
  - type: state-label
    entity: sensor.rico_local_time
    style:
      left: 50%
      bottom: 5%
      transform: translate(-50%, 0)
      color: white
      font-size: 18px
      font-weight: 500
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7)
```

Cards that support `entity_picture` can use the Local Time sensor directly.

## Requirements

The selected source entity must:

- be a `person` or `device_tracker` entity;
- expose `latitude` and `longitude` attributes.

The day/night image additionally requires the source entity to have an `entity_picture` attribute. If no source picture is available, the local-time, timezone, and sun-status sensors continue to work normally.

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Open the menu and choose **Custom repositories**.
4. Add:

   ```text
   https://github.com/ricobach/HA-GeoTime
   ```

   and select **Integration** as the repository type.
5. Install **GeoTime**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **GeoTime**.
9. Select the `person` or `device_tracker` entity you want GeoTime to follow.

## Configuration

GeoTime is configured entirely through the Home Assistant UI and appears as a regular Home Assistant integration.

To change the tracked entity later, open **Settings → Devices & services**, select GeoTime, and use the integration options.

## Example

If `person.rico` is currently in Copenhagen and has:

```yaml
latitude: 55.6761
longitude: 12.5683
entity_picture: /api/image/serve/example/512x512
```

GeoTime can expose information similar to:

```text
Local Time: 12:07
Sun Status: Above
Timezone: Europe/Copenhagen
```

The generated GeoTime image shows the source picture with a sun badge in the upper-right corner. After sunset, the indicator changes to a moon badge. The same generated picture is available from the Local Time sensor through `entity_picture` for compatible dashboard cards.

## Notes

GeoTime uses `timezonefinder` for offline coordinate-to-timezone lookup and Home Assistant's available Astral library for sunrise, sunset, and sun-position calculations.

For polar regions where sunrise or sunset may not occur on a particular date, GeoTime falls back to solar elevation to determine whether the sun is above or below the horizon.

## Issues

Please report bugs or feature requests through the GitHub issue tracker:

```text
https://github.com/ricobach/HA-GeoTime/issues
```

## License

GeoTime is released under the MIT License.
