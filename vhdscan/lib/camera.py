import cv2 as opencv2
import re
import subprocess

from gi.repository import GObject, GdkPixbuf
from threading import Event, Thread
from . import setup, udev


# camera status
SETUP_ERROR = -1
INIT_ERROR = -2
FEED_ERROR = -3
UNSET = 0
SETUP = 1
IDLE = 2
INIT = 3
FEED = 4

# error codes
E_OK = 0
E_NOT_READY = -1
E_DEVICE_BUSY = -2
E_SET_RESOLUTION = -3
E_SET_PIXELFORMAT = -4
E_CAMERA_IO = -5
E_NO_RESOLUTION = -6
E_NO_RESOLUTIONS = -7
E_BANDWIDTH = -8

# slot names
LEFT = "left"
RIGHT = "right"

# control types
CONTROL_INT = 1
CONTROL_BOOL = 2
CONTROL_MENU = 3


def sh(*commands):
    try:
        lines = subprocess.run(
            commands,
            check=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
        ).stdout.split("\n")
    except subprocess.CalledProcessError:
        lines = []
    return lines


def regex(pattern, string, group=1, flags=0):
    if not type(group) is list:
        group = [group]
    match = re.search(pattern, string, flags)
    if match:
        return match.group(*group)
    return None


def set_fps(n):
    Camera.fps = n


class Resolution:
    def __init__(self, value=None, width=None, height=None, pixelformat=None):
        if "x" in str(value):
            width, height, pixelformat = str(value).split("x", 2)
        self.width = int(width)
        self.height = int(height)
        self.pixelformat = str(pixelformat)
        self.name = "[{0}] {1}x{2}".format(pixelformat, width, height)
        self.fourcode = opencv2.VideoWriter_fourcc(*pixelformat)
        self.value = self.stringify(width, height, pixelformat)

    @staticmethod
    def stringify(width, height, pixelformat):
        return "{0}x{1}x{2}".format(width, height, pixelformat)


class Control:

    def __init__(self, type, name, value, camera, min=0, max=0, step=0, default=0, inactive=False):
        self.name = name
        self.value = int(value)
        self.min = int(min)
        self.max = int(max)
        self.step = int(step)
        self.default = int(default)
        self.inactive = inactive
        self.values = []
        self.struct = None
        if self.min == 0 and self.max == 1:
            type = CONTROL_BOOL
        self.type = type

    def add_value(self, text, value):
        if not self.type == CONTROL_MENU:
            return
        self.values.append((text, value))

    def set_sensitive(self, is_sensitive):
        if self.struct:
            for input in self.struct.inputs:
                input.set_sensitive(is_sensitive)


class Camera(GObject.Object):

    _global_thread = None
    fps = 15

    __gsignals__ = {
        "ready": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "resolution": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "start": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "stop": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "status": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "feed": (GObject.SignalFlags.RUN_FIRST, None, (object, object, object,))
    }

    _error_to_name = {
        E_OK: "ok",
        E_NOT_READY: "no-ready",
        E_DEVICE_BUSY: "device-busy",
        E_SET_RESOLUTION: "set-resolution",
        E_SET_PIXELFORMAT: "set-pixelformat",
        E_CAMERA_IO: "camera-io",
        E_NO_RESOLUTION: "no-resolution",
        E_NO_RESOLUTIONS: "no-resolutions",
        E_BANDWIDTH: "bandwidth-exceeded",
    }

    _status_to_name = {
        UNSET: "unset",
        SETUP: "setup",
        SETUP_ERROR: "setup-error",
        INIT: "starting feed",
        INIT_ERROR: "setup-error",
        FEED: "feed",
        FEED_ERROR: "feed-error",
        IDLE: "idle",
    }

    def __init__(self, slot=None):
        GObject.Object.__init__(self)
        self.slot = slot
        self.device = None
        self.status = UNSET
        self._reset()

    def _reset(self):
        self.stop()
        if self.device:
            self.device.in_use = False
        self.device = None
        self.controls = {}
        self.resolution = None
        self.resolutions = {}
        self.error = E_OK
        self._frame = None
        self._feed_interrupt = False
        self._feed_thread = False
        self._buffer_thread = False
        self._is_threading = False

    def reset(self):
        self._reset()
        self._set_status(UNSET)

    def _set_status(self, status, error_code=None):
        self.status = status
        is_error = error_code is not None
        if is_error:
            self.error = error_code
        self.emit("status", status)
        if is_error:
            self.emit("error", error_code)

    def get_setup(self):
        return setup.new_from_camera(self)

    def set_setup(self, setup):
        if self._is_threading:
            return False
        if not setup:
            return False

        device = udev.get_device(setup.id, setup.udev_name)
        if not device:
            device = udev.get_device_by_id(setup.id)
        if device:
            return self.set_device(device, setup.resolution, setup.controls)

        self.reset()
        self.emit("ready")
        return False

    def save(self):
        return self.get_setup().save()

    def open(self, data):
        return self.set_setup(setup.new_from_data(data))

    def set_device_by_id(self, id, resolution=None, controls=None):
        if self._is_threading:
            return False

        if not id:
            self.reset()
            self.emit("ready")
            return True

        device = udev.get_device_by_id(id)
        return self.set_device(device, resolution, controls)

    def set_device_by_name(self, name, resolution=None, controls=None):
        if self._is_threading:
            return False

        if not name:
            self.reset()
            self.emit("ready")
            return True

        device = udev.get_device_by_name(name)
        return self.set_device(device, resolution, controls)

    def set_device(self, device, resolution=None, controls=None):

        def set_resolution():
            if not resolution:
                return False

            res = Resolution(value=resolution)
            if res.value in self.resolutions:
                self.resolution = res
                self.emit("resolution")
                return True
            return False

        def set_controls():
            if not controls:
                return False

            for name in controls:
                if name not in self.controls:
                    continue
                if controls[name] == self.controls[name].value:
                    continue
                sh(
                    "v4l2-ctl",
                    "--device", self.device.name,
                    "--set-ctrl", "{0}={1}".format(name, controls[name]),
                )
            return True

        def abort_init(error):
            self._is_threading = False
            self._set_status(SETUP_ERROR, error)
            return False

        def init_resolutions():
            for line in sh(
                "v4l2-ctl",
                "--device", self.device.name,
                "--list-formats-ext",
            ):
                if "]: '" in line:
                    pixelformat = regex(r"'([^']+)'", line)
                elif "Size:" in line:
                    width, height = regex(r"(\d+)x(\d+)", line, [1, 2])
                    resolution = Resolution(
                        width=width,
                        height=height,
                        pixelformat=pixelformat,
                    )
                    self.resolutions[resolution.value] = resolution
            n = len(self.resolutions)
            return n > 0

        def init_resolution():
            if set_resolution():
                return True

            width = 0
            height = 0
            pixelformat = ""
            for line in sh(
                    "v4l2-ctl",
                    "--device", self.device.name,
                    "--get-fmt-video",
            ):
                if "Width/Height" in line:
                    width, height = regex(r"(\d+)/(\d+)", line, [1, 2])
                elif "Pixel Format" in line:
                    pixelformat = regex(r"'([^']+)'", line)

            if not width or not height or not pixelformat:
                return False

            self.resolution = Resolution(
                width=width,
                height=height,
                pixelformat=pixelformat,
            )
            return True

        def init_controls():
            in_menu = False
            for line in sh(
                "v4l2-ctl",
                "--device", self.device.name,
                "--list-ctrls-menus",
            ):
                line = line.strip()
                if " 0x" in line:
                    in_menu = False
                    name = line.split("0x", 1)[0].strip()
                    value = int(regex(r"value=(-?\d+)", line))
                    inactive = "flags=inactive" in line
                    if " (int)" in line:
                        control = Control(
                            type=CONTROL_INT,
                            name=name,
                            value=value,
                            min=regex(r"min=(-?\d+)", line),
                            max=regex(r"max=(-?\d+)", line),
                            step=regex(r"step=(-?\d+)", line),
                            default=regex(r"default=(-?\d+)", line),
                            inactive=inactive,
                            camera=self,
                        )

                    elif " (bool)" in line:
                        control = Control(
                            type=CONTROL_BOOL,
                            name=name,
                            value=value,
                            inactive=inactive,
                            camera=self,
                        )

                    elif " (menu)" in line:
                        in_menu = True
                        control = Control(
                            type=CONTROL_MENU,
                            name=name,
                            value=value,
                            inactive=inactive,
                            camera=self,
                        )

                    else:
                        continue

                    self.controls[name] = control

                elif in_menu and line:
                    menu_value, menu_text = line.split(": ", 1)
                    control.add_value(menu_text, menu_value)
            set_controls()
            return True

        def setup():
            self._set_status(SETUP)
            if not init_resolutions():
                return abort_init(E_NO_RESOLUTIONS)
            if not init_resolution():
                return abort_init(E_NO_RESOLUTION)
            init_controls()
            self._is_threading = False
            self._set_status(IDLE)
            self.emit("ready")
            if stopped_feed:
                self.start()

        if self._is_threading:
            return False

        if device is None:
            # device is explicitly set to `None`; reset and emit `setup`
            self.reset()
            self.emit("ready")
            return True

        stopped_feed = False
        if self.device is not device:
            # a new device is to be set; stop feed and reinitialise
            stopped_feed = self.stop()
            self._reset()
            device.in_use = True
            self.device = device
            thread = Thread(target=setup)
            self._is_threading = True
            thread.start()
            return True

        # it's the same device; just apply resolution and controls
        if set_resolution():
            stopped_feed = self.stop()
        set_controls()
        self._set_status(IDLE)
        self.emit("ready")
        if stopped_feed:
            self.start()
        return True

    def set_resolution(self, value):
        if self.status < IDLE:
            # not ready; abort
            return False

        if self.resolution.value == value:
            # same resolution; nothing to do
            return None

        if value not in self.resolutions:
            # resolution is not supported; abort
            return False

        # we need to stop any feed to apply a new resolution
        stop_feed = self._buffer_thread is not False
        if stopped_feed:
            _restart_id = self.connect("")
            self.stop()
        self.resolution = Resolution(value=value)
        self.emit("resolution")
        if stopped_feed:
            # TODO: this needs to happen asyncronously
            # we stopped a feed, let's restart it
            self.start()
        return True

    def set_control(self, name, value):
        if self.status < IDLE:
            return False
        if name not in self.controls:
            return False
        if value == self.controls[name].value:
            return None

        def set():
            sh(
                "v4l2-ctl",
                "--device", self.device.name,
                "--set-ctrl", "{0}={1}".format(name, value),
            )
        Thread(target=set).start()
        return True

    def get_device_name(self):
        if self.status < IDLE:
            return None
        return self.device.name

    def get_model_name(self, fallback=""):
        if self.status < IDLE:
            return fallback
        return self.device.model

    def update_sensitivity(self, dialog_widget):
        # TODO: this is UI stuff! move to camera_dialog.py
        if self._is_threading:
            return False

        if self.status < IDLE:
            return False

        def parse():
            for line in sh(
                "v4l2-ctl",
                "--device", self.device.name,
                "--list-ctrls-menus",
            ):
                if "0x" in line:
                    is_sensitive = "flags=inactive" not in line
                    name = line.split("0x", 1)[0].strip()
                    self.controls[name].set_sensitive(is_sensitive)
            self._is_threading = False

        self._is_threading = True
        Thread(target=parse).start()
        return True

    def start(self):
        if self._global_thread:
            if self._buffer_thread == self._global_thread:
                return True
            self._set_status(INIT_ERROR, E_BANDWIDTH)
            return False

        if self.status != IDLE:
            self._set_status(INIT_ERROR, E_NOT_READY)
            return False

        if self._is_threading:
            return False

        self._feed_interrupt = Event()
        self._buffer_thread = Thread(target=self._buffer_frame)
        self._feed_thread = Thread(target=self._feed_frame)
        self._global_thread = self._buffer_thread
        self._buffer_thread.start()
        self._feed_thread.start()

    # thread target
    def _buffer_frame(self):
        self._set_status(INIT)
        capture = opencv2.VideoCapture()
        if not capture.open(
            filename=self.device.name,
            apiPreference=opencv2.CAP_V4L2,
        ):
            self._stop_buffer(capture)
            self._set_status(INIT_ERROR, E_DEVICE_BUSY)
            return

        if not capture.set(opencv2.CAP_PROP_FRAME_WIDTH, self.resolution.width):
            self._set_status(INIT_ERROR, E_SET_RESOLUTION)
            return

        if not capture.set(opencv2.CAP_PROP_FRAME_HEIGHT, self.resolution.height):
            self._set_status(INIT_ERROR, E_SET_RESOLUTION)
            return

        if not capture.set(opencv2.CAP_PROP_FOURCC, self.resolution.fourcode):
            self._set_status(INIT_ERROR, E_SET_PIXELFORMAT)
            return

        self._set_status(FEED)
        self.emit("start")
        while True:
            buffered, frame = capture.read()
            if not buffered:
                self._stop_buffer(capture)
                self._set_status(FEED_ERROR, E_CAMERA_IO)
                return

            self._frame = frame

            if self._feed_interrupt is False or self._feed_interrupt.is_set():
                break

        self._stop_buffer(capture)
        self._set_status(IDLE)

    # thread target
    def _feed_frame(self):
        while True:
            if self._frame is not None:
                frame = opencv2.cvtColor(self._frame, opencv2.COLOR_BGR2RGB)
                height, width = frame.shape[0:2]
                pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                    data=frame.tobytes(),
                    colorspace=GdkPixbuf.Colorspace.RGB,
                    has_alpha=False,
                    bits_per_sample=8,
                    height=height,
                    width=width,
                    rowstride=frame.shape[2] * width,
                )
                self.emit("feed", pixbuf, width, height)
                del pixbuf
                del frame

            if self._feed_interrupt is False or self._feed_interrupt.wait(1/self.fps):
                break

    def _stop_buffer(self, capture):
        if capture.isOpened():
            capture.release()
        self._stop_feed()

    def _stop_feed(self):
        self._frame = None
        self._feed_thread = False
        self._global_thread = False
        if self._feed_interrupt:
            self._feed_interrupt.set()

    def stop(self):
        # make sure there is a thread
        if not self._global_thread:
            return False

        # make sure it's our thread
        if self._global_thread is not self._buffer_thread:
            return False

        self._stop_feed()
        return True
