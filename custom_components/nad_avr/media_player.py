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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CMD_POWER_ON,
    CMD_POWER_OFF,
    CMD_POWER_QUERY,
    CMD_VOLUME_UP,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_QUERY,
    CMD_VOLUME_SET,
    CMD_MUTE_ON,
    CMD_MUTE_OFF,
    CMD_MUTE_QUERY,
    CMD_SOURCE_QUERY,
    CMD_SOURCE_SET,
    SOURCES,
    SOURCE_NAMES,
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
    
    async_add_entities([NADAVRMediaPlayer(client, name, config_entry.entry_id)], True)


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

    def __init__(self, client: NADClient, name: str, entry_id: str) -> None:
        """Initialize the NAD AVR media player."""
        self._client = client
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "NAD",
            "model": "AVR",
        }
        self._attr_unique_id = f"{entry_id}_media_player"
        self._attr_available = False
        self._attr_state = MediaPlayerState.OFF
        self._attr_is_volume_muted = False
        self._attr_volume_level = 0.0
        self._attr_source = None
        self._attr_source_list = list(SOURCES.values())
        
        # Set up status callback
        client._status_callback = self._connection_status_changed

    async def _connection_status_changed(self, connected: bool) -> None:
        """Handle connection status changes."""
        self._attr_available = connected
        if not connected:
            self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

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
                    # NAD volume is typically -90 to 0 dB
                    volume_db = int(response.split("=", 1)[1].strip())
                    # Convert to 0.0-1.0 range (assuming -90 to 0 dB range)
                    self._attr_volume_level = max(0.0, min(1.0, (volume_db + 90) / 90))
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
                self._attr_source = SOURCES.get(source_id, source_id)

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
        # Convert 0.0-1.0 to -90 to 0 dB
        volume_db = int((volume * 90) - 90)
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
        source_id = SOURCE_NAMES.get(source)
        if source_id:
            await self._client.send_command(CMD_SOURCE_SET.format(source_id))
            self._attr_source = source
            self.async_write_ha_state()
