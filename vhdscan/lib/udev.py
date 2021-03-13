from gi.repository import GObject
from pyudev import Context, Monitor, MonitorObserver


SUBSYSTEM = "video4linux"


class Device:

    def __init__(self, udev_device):
        p = udev_device.properties
        self._udev_device = udev_device
        self.in_use = False
        self.model = p.get("ID_MODEL", "").replace("_", " ")
        self.vendor = p.get("ID_VENDOR", "").replace("_", " ")
        self.vendor_id = p.get("ID_VENDOR_ID", "0000").upper()
        self.model_id = p.get("ID_MODEL_ID", "0000").upper()
        self.revision = p.get("ID_REVISION", "0000").upper()
        self.name = p.get("DEVNAME")
        self.id = "{0}:{1}:{2}".format(self.vendor_id, self.model_id, self.revision)
        self.display_name = "{0} ({1})".format(self.model, self.name)

    def equals(self, udev_device):
        return self._udev_device == udev_device


class _Signal(GObject.Object):

    __gsignals__ = {
        "change": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)


_signal = _Signal()


def _observe(udev_device):
    global devices

    if udev_device.action == "add":
        if not _can_capture(udev_device):
            return

        device = Device(udev_device)
        devices.append(device)
        _signal.emit("change", "add")

    elif udev_device.action == "remove":
        for device in devices:
            if not device.equals(udev_device):
                return

            devices.remove(device)
            _signal.emit("change", "remove")
            return


def _can_capture(udev_device):
    return "capture" in udev_device.properties.get("ID_V4L_CAPABILITIES", "")


def get_device(id, name):
    if id and name:
        for device in devices:
            if device.in_use:
                continue

            if device.id == id and device.name == name:
                return device
    return None


def get_device_by_id(id):
    if id:
        for device in devices:
            if device.in_use:
                continue
            if device.id == id:
                return device
    return None


def get_device_by_name(name):
    if name:
        for device in devices:
            if device.in_use:
                continue
            if device.name == name:
                return device
    return None


def connect(signal, callback, *args):
    return _signal.connect(signal, callback, *args)


def disconnect(handler_id):
    _signal.disconnect(handler_id)


def stop():
    _observer.stop()


devices = []
_context = Context()
for udev_device in _context.list_devices(subsystem=SUBSYSTEM):
    if not _can_capture(udev_device):
        continue

    devices.append(Device(udev_device))

_monitor = Monitor.from_netlink(_context)
_monitor.filter_by(subsystem=SUBSYSTEM)
_observer = MonitorObserver(
    monitor=_monitor,
    callback=_observe,
)
_observer.start()
