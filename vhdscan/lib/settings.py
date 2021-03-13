from os import makedirs as mkdirs
from os.path import isdir as is_dir, join as join_path
from appdirs import user_config_dir

from . import json


CONFIG_FILE = "vhdscan.config"
CONFIG_DIR = user_config_dir(appname="vhdscan")
CONFIG_PATH = join_path(CONFIG_DIR, CONFIG_FILE)
CONFIG_RECENTS = 15

STARTUP_DO_NOTHING = "do-nothing"
STARTUP_OPEN_LAST_PROJECT = "open-last-project"


_data = {
    "locale": "de",
    "on-startup": STARTUP_DO_NOTHING,
    "recent": [],
    "window-geometry": {}
}


def load():
    data = json.read(CONFIG_PATH)
    if isinstance(data, dict):
        global _data
        _data.update(data)


def save():
    if not is_dir(CONFIG_DIR):
        mkdirs(CONFIG_DIR, mode=0o777, exist_ok=True)

    json.write(CONFIG_PATH, _data)


def get(key, fallback=None):
    return _data.get(key, fallback)


def update(data):
    global _data
    for key in _data:
        if key in data:
            _data[key] = data[key]
    save()


def set(key, value):
    _data[key] = value
    save()


def set_geometry(name, x, y, width, height, is_maximized, is_fullscreen):
    global _data
    _data["window-geometry"][name] = [x, y, width, height, is_maximized, is_fullscreen]
    save()


def get_geometry(name):
    return _data["window-geometry"].get(name, None)


def get_recent():
    if len(_data["recent"]) > 0:
        return _data["recent"][0]
    return None


def add_recent(project):
    global _data
    for path in _data["recent"]:
        if path == project.path:
            _data["recent"].remove(project.path)
            break

    _data["recent"].insert(0, project.path)
    _data["recent"] = _data["recent"][0:CONFIG_RECENTS]
    save()
