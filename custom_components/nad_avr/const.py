"""Constants for the NAD AVR integration."""

DOMAIN = "nad_avr"

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"

# Defaults
DEFAULT_PORT = 50001
DEFAULT_NAME = "NAD AVR"

# Update interval
SCAN_INTERVAL = 30

# NAD Commands
CMD_POWER_ON = "Main.Power=On\r"
CMD_POWER_OFF = "Main.Power=Standby\r"
CMD_POWER_QUERY = "Main.Power?\r"
CMD_VOLUME_UP = "Main.Volume+\r"
CMD_VOLUME_DOWN = "Main.Volume-\r"
CMD_VOLUME_QUERY = "Main.Volume?\r"
CMD_VOLUME_SET = "Main.Volume={}\r"
CMD_MUTE_ON = "Main.Mute=On\r"
CMD_MUTE_OFF = "Main.Mute=Off\r"
CMD_MUTE_QUERY = "Main.Mute?\r"
CMD_SOURCE_QUERY = "Main.Source?\r"
CMD_SOURCE_SET = "Main.Source={}\r"

# NAD Sources - Common inputs for NAD AVRs
SOURCES = {
    "1": "CD",
    "2": "Tuner",
    "3": "Video 1",
    "4": "Video 2",
    "5": "Disc",
    "6": "Tape 1",
    "7": "Aux",
    "8": "TV",
}

# Reverse mapping
SOURCE_NAMES = {v: k for k, v in SOURCES.items()}
