"""Constants for Solar Hub."""
from pathlib import Path

DOMAIN = "solar_hub"
NAME = "Solar Hub"
VERSION = "0.0.4-beta.5"

CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_PORT = 8899
DEFAULT_SCAN_INTERVAL = 5

PANEL_URL = "solar-hub"
PANEL_ELEMENT = "solar-hub-panel"
STATIC_URL = "/solar_hub_static"
FRONTEND_PATH = Path(__file__).parent / "frontend"

WS_OVERVIEW = "solar_hub/overview"
WS_PREDBAT = "solar_hub/predbat"
WS_DEEP_SCAN = "solar_hub/deep_scan"
