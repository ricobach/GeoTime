# GeoTime

GeoTime is a custom Home Assistant integration that calculates local time, timezone, sun status, and a day/night person image from the current geographic location of a `person` or `device_tracker` entity.

The integration works from the latitude and longitude already provided by Home Assistant. Timezone lookup and sun calculations are performed locally; no external geocoding or timezone API is required.

## Features

For each configured `person` or `device_tracker`, GeoTime creates three sensors and one image entity:

- **Local Time** — the local clock time at the tracked entity's current location.
- **Sun Status** — `Above` or `Below`, based on whether the sun is above the horizon at that location. Sunrise and sunset are exposed as attributes when available.
- **Timezone** — the IANA timezone name, for example `Europe/Copenhagen`.
- **GeoTime Image** — the source entity's picture with a day/night indicator in the upper-right corner.

## Day/night image

The GeoTime image entity uses the `entity_picture` from the selected `person` or `device_tracker` as its base image.

A small indicator is added in the **upper-right corner**:

- ☀️ **Sun** when the sun is above the horizon at the tracked location.
- 🌙 **Moon** when the sun is below the horizon at the tracked location.

GeoTime rebuilds the image when either of these changes:

- the source entity's `entity_picture` changes;
- the calculated sun status changes between `Above` and `Below`.

The integration also checks the sun state periodically so the image can change at sunrise or sunset even when the tracked entity remains stationary.

The image is exposed as a real Home Assistant `image` entity. Home Assistant automatically gives image entities an `entity_picture` URL, so the generated image can be used by dashboard cards that support entity pictures.

A generated entity will typically look similar to:

```text
image.rico_geotime_image
```

The exact entity ID depends on the name of the configured entry and can be changed in Home Assistant's entity settings.

### Dashboard example

A standard Picture Entity card can display the generated image directly:

```yaml
type: picture-entity
entity: image.rico_geotime_image
show_name: true
show_state: false
```

A Tile card can also use the image entity:

```yaml
type: tile
entity: image.rico_geotime_image
show_entity_picture: true
```

Because this is an actual Home Assistant image entity, custom dashboard cards can also use its `entity_picture` in the same way as other entities.

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
   https://github.com/ricobach/GeoTime
   ```

   and select **Integration** as the repository type.
5. Install **GeoTime**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **GeoTime**.
9. Select the `person` or `device_tracker` entity you want GeoTime to follow.

## Configuration

GeoTime is configured entirely through the Home Assistant UI.

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

and the GeoTime image entity will show Rico's source picture with a sun badge in the upper-right corner. After sunset, the same image automatically changes to a moon badge.

## Notes

GeoTime uses `timezonefinder` for offline coordinate-to-timezone lookup and Astral for sunrise, sunset, and sun-position calculations.

For polar regions where sunrise or sunset may not occur on a particular date, GeoTime falls back to solar elevation to determine whether the sun is above or below the horizon.

## Issues

Please report bugs or feature requests through the GitHub issue tracker:

```text
https://github.com/ricobach/GeoTime/issues
```

## License

GeoTime is released under the MIT License.
