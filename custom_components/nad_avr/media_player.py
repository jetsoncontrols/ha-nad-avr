"""Media player platform for NAD AVR."""

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_MUTE_OFF,
    CMD_MUTE_ON,
    CMD_MUTE_QUERY,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_POWER_QUERY,
    CMD_SOURCE_QUERY,
    CMD_SOURCE_SET,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_QUERY,
    CMD_VOLUME_SET,
    CMD_VOLUME_UP,
    DOMAIN,
    SOURCE_NAMES,
    SOURCES,
    VOLUME_MIN_DB,
    VOLUME_RANGE_DB,
)
from .nad_client import NADClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NAD AVR media player."""
    client = hass.data[DOMAIN][config_entry.entry_id]
    name = config_entry.data.get(CONF_NAME, f"NAD AVR {config_entry.data[CONF_HOST]}")
    host = config_entry.data[CONF_HOST]

    async_add_entities(
        [NADAVRMediaPlayer(client, name, host, config_entry.entry_id)], True
    )


class NADAVRMediaPlayer(MediaPlayerEntity):
    """Representation of a NAD AVR media player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, client: NADClient, name: str, host: str, entry_id: str) -> None:
        """Initialize the NAD AVR media player."""
        self._client = client
        self._host = host
        self._entry_id = entry_id
        self._device_name = name
        self._attr_unique_id = f"{entry_id}_media_player"
        self._attr_available = False
        self._attr_state = MediaPlayerState.OFF
        self._attr_is_volume_muted = False
        self._attr_volume_level = 0.0
        self._attr_source = None
        self._attr_source_list = list(SOURCES.values())

        # Set up callbacks
        client.status_callback = self._connection_status_changed
        client.update_callback = self._handle_update

    async def async_added_to_hass(self) -> None:
        """Handle entity being added to Home Assistant."""
        await super().async_added_to_hass()
        # Now that the entity is added and callbacks are set up, connect to the device
        await self._client.connect()

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        info = {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": self._device_name,
            "manufacturer": "NAD",
            "model": self._client.model or "AVR",
            "configuration_url": f"http://{self._host}/osd/",
        }

        # Add firmware version if available
        if self._client.firmware_version:
            info["sw_version"] = self._client.firmware_version

        return info

    async def _connection_status_changed(self, connected: bool) -> None:
        """Handle connection status changes."""
        self._attr_available = connected
        if not connected:
            self._attr_state = MediaPlayerState.OFF
            self.async_write_ha_state()
        else:
            # Poll device info (model and firmware version)
            await self._client.poll_device_info()

            # Update device registry with polled info
            device_reg = dr.async_get(self.hass)
            device = device_reg.async_get_device(identifiers={(DOMAIN, self._entry_id)})
            if device:
                device_reg.async_update_device(
                    device.id,
                    model=self._client.model,
                    sw_version=self._client.firmware_version,
                )

            # Poll source names from the device
            await self._client.poll_source_names()
            self._update_source_list()

            # Write state after updating source list
            self.async_write_ha_state()

            # Poll initial state (power, volume, mute, source)
            await self.async_update()

    def _update_source_list(self) -> None:
        """Update the source list with polled names, filtering out disabled sources."""
        if self._client.source_enabled:
            # Only include sources that are enabled
            enabled_sources = [
                source_id
                for source_id in sorted(self._client.source_enabled.keys())
                if self._client.source_enabled.get(source_id, False)
            ]

            # Use polled names for enabled sources
            self._attr_source_list = []
            for source_id in enabled_sources:
                # Use the polled name if available, otherwise fall back to default
                source_name = self._client.source_names.get(source_id)
                if not source_name:
                    source_name = SOURCES.get(source_id, f"Source {source_id}")
                self._attr_source_list.append(source_name)
        elif self._client.source_names:
            # If no enabled info but we have names, use all sources with names
            self._attr_source_list = list(self._client.source_names.values())
        else:
            # Use default names if polling failed
            self._attr_source_list = list(SOURCES.values())

    async def _handle_update(self, message: str) -> None:
        """Handle unsolicited updates from the device."""
        if not message or "=" not in message:
            return

        try:
            key, value = message.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Handle power state updates
            if key == "Main.Power":
                if value.lower() == "on":
                    self._attr_state = MediaPlayerState.ON
                else:
                    self._attr_state = MediaPlayerState.OFF

            # Handle volume updates
            elif key == "Main.Volume":
                try:
                    volume_db = int(value)
                    self._attr_volume_level = max(
                        0.0, min(1.0, (volume_db - VOLUME_MIN_DB) / VOLUME_RANGE_DB)
                    )
                except ValueError:
                    pass

            # Handle mute updates
            elif key == "Main.Mute":
                self._attr_is_volume_muted = value.lower() == "on"

            # Handle source updates
            elif key == "Main.Source":
                # Use polled name if available, otherwise use default
                self._attr_source = self._client.source_names.get(
                    value, SOURCES.get(value, value)
                )

            # Handle source enabled status updates
            elif key.startswith("Source") and key.endswith(".Enabled"):
                # Extract source number from key (e.g., "Source1.Enabled" -> "1")
                try:
                    source_num = key.replace("Source", "").replace(".Enabled", "")
                    is_enabled = value.lower() in ["yes", "on", "true", "1"]
                    self._client.source_enabled[source_num] = is_enabled
                    # Update the source list when enabled status changes
                    self._update_source_list()
                except (ValueError, IndexError):
                    _LOGGER.debug(
                        "Could not parse source enabled update: %s=%s", key, value
                    )

            # Handle source name updates
            elif key.startswith("Source") and key.endswith(".Name"):
                # Extract source number from key (e.g., "Source1.Name" -> "1")
                try:
                    source_num = key.replace("Source", "").replace(".Name", "")
                    if value:
                        self._client.source_names[source_num] = value
                        # Update the source list when name changes
                        self._update_source_list()
                except (ValueError, IndexError):
                    _LOGGER.debug(
                        "Could not parse source name update: %s=%s", key, value
                    )

            # Update the state in Home Assistant
            self.async_write_ha_state()

        except (ValueError, KeyError, AttributeError) as err:
            _LOGGER.debug("Error parsing update message '%s': %s", message, err)

    async def async_update(self) -> None:
        """Update the state of the media player."""
        if not self._client.connected:
            self._attr_available = False
            self._attr_state = MediaPlayerState.OFF
            return

        self._attr_available = True

        # Query power state
        response = await self._client.query(CMD_POWER_QUERY)
        if response and "=" in response:
            value = response.split("=", 1)[1].strip()
            if value.lower() == "on":
                self._attr_state = MediaPlayerState.ON
            else:
                self._attr_state = MediaPlayerState.OFF

        if self._attr_state == MediaPlayerState.ON:
            # Query volume
            response = await self._client.query(CMD_VOLUME_QUERY)
            if response and "=" in response:
                try:
                    volume_db = int(response.split("=", 1)[1].strip())
                    # Convert to 0.0-1.0 range
                    self._attr_volume_level = max(
                        0.0, min(1.0, (volume_db - VOLUME_MIN_DB) / VOLUME_RANGE_DB)
                    )
                except (ValueError, IndexError):
                    pass

            # Query mute state
            response = await self._client.query(CMD_MUTE_QUERY)
            if response and "=" in response:
                value = response.split("=", 1)[1].strip()
                self._attr_is_volume_muted = value.lower() == "on"

            # Query source
            response = await self._client.query(CMD_SOURCE_QUERY)
            if response and "=" in response:
                source_id = response.split("=", 1)[1].strip()
                # Use polled name if available, otherwise use default
                self._attr_source = self._client.source_names.get(
                    source_id, SOURCES.get(source_id, source_id)
                )

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self._client.send_command(CMD_POWER_ON)
        self._attr_state = MediaPlayerState.ON
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._client.send_command(CMD_POWER_OFF)
        self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute the volume."""
        if mute:
            await self._client.send_command(CMD_MUTE_ON)
        else:
            await self._client.send_command(CMD_MUTE_OFF)
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        # Convert 0.0-1.0 to NAD dB range
        volume_db = int((volume * VOLUME_RANGE_DB) + VOLUME_MIN_DB)
        await self._client.send_command(CMD_VOLUME_SET.format(volume_db))
        self._attr_volume_level = volume
        self.async_write_ha_state()

    async def async_volume_up(self) -> None:
        """Increase volume."""
        await self._client.send_command(CMD_VOLUME_UP)

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        await self._client.send_command(CMD_VOLUME_DOWN)

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        # Find source ID by matching against polled names or defaults
        source_id = None

        # Check polled names first
        for sid, name in self._client.source_names.items():
            if name == source:
                source_id = sid
                break

        # Fall back to default names
        if not source_id:
            source_id = SOURCE_NAMES.get(source)

        if source_id:
            await self._client.send_command(CMD_SOURCE_SET.format(source_id))
            self._attr_source = source
            self.async_write_ha_state()
