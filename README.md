# NAD AVR Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration for controlling NAD Audio/Video Receivers via TCP/IP.

## Features

- **Media Player Entity**: Full control of your NAD AVR
  - Power on/off
  - Volume control (up, down, set level)
  - Mute/unmute
  - Source selection
- **Automatic Reconnection**: TCP connection automatically reconnects if lost
- **Connection Status Tracking**: Entity availability reflects the actual connection state
- **HACS Compatible**: Easy installation and updates through HACS

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/jetsoncontrols/ha-nad-avr` as an Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/nad_avr` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "NAD AVR"
4. Enter the following information:
   - **Host**: IP address of your NAD AVR
   - **Port**: TCP port (default: 50001)
   - **Name**: Friendly name for your device (optional)

## Usage

Once configured, a media player entity will be created for your NAD AVR. You can:

- Turn the AVR on/off
- Adjust volume
- Mute/unmute
- Select input sources

The entity will show as "unavailable" when the TCP connection is lost and automatically become available again when the connection is restored.

## Supported Sources

The integration supports the following common NAD AVR sources:
- CD
- Tuner
- Video 1
- Video 2
- Disc
- Tape 1
- Aux
- TV

## Technical Details

- **Protocol**: TCP/IP command protocol
- **Default Port**: 50001
- **Reconnection**: Automatic with 5-second delay
- **Update Interval**: 30 seconds

## Troubleshooting

### Connection Issues

1. Verify your NAD AVR is connected to your network
2. Check that the IP address and port are correct
3. Ensure no firewall is blocking the connection
4. Check the Home Assistant logs for error messages

### Entity Shows as Unavailable

The entity availability directly reflects the TCP connection status. If the entity is unavailable:
- Check network connectivity
- Verify the AVR is powered on and connected to the network
- The integration will automatically attempt to reconnect

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.