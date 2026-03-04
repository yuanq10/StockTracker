import json
import os
import sys
from datetime import datetime

# When frozen by PyInstaller, place data/ next to the .exe.
# When running from source, place data/ at the project root.
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(_BASE, "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")

DEFAULT_SETTINGS = {
    "stocks": [],
    "indicators": [
        {"type": "CCI", "enabled": True, "period": 20, "buy_threshold": -100, "sell_threshold": 100},
        {"type": "MACD", "enabled": True, "fast": 12, "slow": 26, "signal": 9},
        {"type": "KDJ", "enabled": True, "period": 9, "k_smooth": 3, "d_smooth": 3, "buy_threshold": 20, "sell_threshold": 80}
    ]
}

DEFAULT_ALERTS = {
    "last_updated": "",
    "alerts": {},
    "stats": {}
}


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_settings() -> dict:
    _ensure_data_dir()
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)
    # Ensure all indicator defaults are present
    saved_types = {ind["type"] for ind in data.get("indicators", [])}
    for default_ind in DEFAULT_SETTINGS["indicators"]:
        if default_ind["type"] not in saved_types:
            data.setdefault("indicators", []).append(default_ind.copy())
    return data


def save_settings(data: dict):
    _ensure_data_dir()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_alerts() -> dict:
    _ensure_data_dir()
    if not os.path.exists(ALERTS_FILE):
        save_alerts(DEFAULT_ALERTS)
        return DEFAULT_ALERTS.copy()
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)


def save_alerts(data: dict):
    _ensure_data_dir()
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f, indent=2)
