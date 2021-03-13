from gi.repository import GObject
from os.path import basename as basename, isfile as is_file
from glob import glob
from os.path import realpath
from . import json


_data = {}
_iso_key = None


class _Signal(GObject.Object):

    __gsignals__ = {
        "change": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)


_signal = _Signal()


def get_all():
    locales = [["en", "English (en)"]]
    for json in glob("locale/*.json"):
        data = json.read(json)
        if data:
            iso_key = basename(json).rsplit('.', 1)[0]
            name = "{0} ({1})".format(data["name"], iso_key)
            locales.append([iso_key, name])
    locales.sort(key=lambda locale: locale[1])
    return locales


def load(iso_key):
    global _data, _iso_key

    _data = {}
    current_iso_key = _iso_key
    if current_iso_key == iso_key:
        return

    _iso_key = iso_key
    if not iso_key or iso_key == "en":
        _signal.emit("change")
        return

    path = realpath("locale/" + iso_key + ".json")
    if is_file(path):
        _data = json.read(path)
        _signal.emit("change")


def get_name():
    return _data.name if _data else ""


def connect(signal, callback, *args):
    return _signal.connect(signal, callback, *args)


def disconnect(handler_id):
    _signal.disconnect(handler_id)


def translate(text):
    if not _data or "strings" not in _data:
        return text
    _text = _data["strings"].get(text, text)
    return text if _text == "" else _text


_ = translate
