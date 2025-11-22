"""Constants for the NAD AVR integration."""

DOMAIN = "nad_avr"

# Defaults
DEFAULT_PORT = 23
DEFAULT_NAME = "NAD AVR"

# Update interval
SCAN_INTERVAL = 30

# NAD Commands
CMD_POWER_ON = "Main.Power=On\r\n"
CMD_POWER_OFF = "Main.Power=Standby\r\n"
CMD_POWER_QUERY = "Main.Power?\r\n"
CMD_VOLUME_UP = "Main.Volume+\r\n"
CMD_VOLUME_DOWN = "Main.Volume-\r\n"
CMD_VOLUME_QUERY = "Main.Volume?\r\n"
CMD_VOLUME_SET = "Main.Volume={}\r\n"
CMD_MUTE_ON = "Main.Mute=On\r\n"
CMD_MUTE_OFF = "Main.Mute=Off\r\n"
CMD_MUTE_QUERY = "Main.Mute?\r\n"
CMD_SOURCE_QUERY = "Main.Source?\r\n"
CMD_SOURCE_SET = "Main.Source={}\r\n"

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

# Volume range (NAD uses -90 to 0 dB)
VOLUME_MIN_DB = -90
VOLUME_MAX_DB = 0
VOLUME_RANGE_DB = VOLUME_MAX_DB - VOLUME_MIN_DB  # 90
