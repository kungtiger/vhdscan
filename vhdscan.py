#!/usr/bin/env python3

import gi
import cv2
import os
import re
import json
import subprocess

from appdirs import *
from os.path import basename, isdir as is_dir, isfile as is_file, join as join_path
from os import makedirs as mkdirs

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GObject

# ____________________________________________________________________________ #


def _(text):
    return App.translate(text)


def json_load(path):
    try:
        if os.path.isfile(path):
            with open(path) as file:
                return json.load(file)
    except json.JSONDecodeError:
        return None
    return None


def json_save(path, data):
    with open(path, "w") as file:
        json.dump(data, file, indent=2)


def cmd(*commands):
    try:
        return subprocess.run(
            commands,
            check=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
        ).stdout.split("\n")
    except subprocess.CalledProcessError:
        return None


def exec(*commands):
    try:
        subprocess.run(
            commands,
            check=True,
            universal_newlines=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def regex(pattern, string, group=1, flags=0):
    if not type(group) is list:
        group = [group]
    match = re.search(pattern, string, flags)
    if match:
        return match.group(*group)
    return None


# ____________________________________________________________________________ #


class UI:
    def add_class(self, *args):
        context = self.get_style_context()
        if context:
            for name in args:
                context.add_class(name)

    def has_class(self, class_name):
        context = self.get_style_context()
        if not context:
            return False
        return context.has_class(class_name)

    def remove_class(self, *args):
        context = self.get_style_context()
        if context:
            for name in args:
                context.remove_class(name)


# ____________________________________________________________________________ #


class Label(Gtk.Label, UI):
    pass


class Box(Gtk.Box, UI):
    pass


class Button(Gtk.Button, UI):
    pass


class ComboBox(Gtk.ComboBox, UI):

    def __init__(self, *args, **kwargs):
        types = [str]
        if "types" in kwargs:
            types = kwargs["types"]
            del kwargs["types"]
        display = 0
        if "display" in kwargs:
            display = kwargs["display"]
            del kwargs["display"]

        super().__init__(*args, **kwargs)

        self.__model = Gtk.ListStore(*types)
        self.set_model(self.__model)

        self.__cell = Gtk.CellRendererText()
        self.pack_start(self.__cell, 25)
        self.add_attribute(self.__cell, "text", display)

    def get_value(self, column=0, fallback=None):
        index = self.get_active()
        if index < 0:
            return fallback
        model = self.get_model()
        return model[index][column]

    def set_value(self, value, column=0):
        index = 0
        for row in self.__model:
            if row[column] == value:
                self.set_active(index)
                return True
            index += 1
        return False


class Scale(Gtk.Scale, UI):
    pass


class Switch(Gtk.Switch, UI):
    pass


class SpinButton(Gtk.SpinButton, UI):
    pass


class FileChooserDialog(Gtk.FileChooserDialog, UI):

    def get_path(self, fallback=None):
        file = self.get_file()
        if not file:
            return fallback
        return file.get_path()


# ____________________________________________________________________________ #


class Window(UI):
    # Scaffold for Windows

    instance = None

    @classmethod
    def glade(self, *args):
        self.instance = self(*args)

    @classmethod
    def show(self, *args, **kwargs):
        self.instance.setup(*args, **kwargs)
        self.instance.root.show()

    @classmethod
    def hide(self):
        self.instance.root.hide()
        self.instance.teardown()

    def __init__(self, glade_file, stylesheet_file=None):
        self.__builder = Gtk.Builder()
        self.__builder.add_from_file(glade_file)
        self.__builder.connect_signals(self)

        if stylesheet_file:
            App.add_stylesheet(stylesheet_file)

        self.init()

    # Routes unset instance attribute access to Glade and returns a GTK object
    def __getattr__(self, id):
        gtk_object = self.__builder.get_object(id)
        if not gtk_object:
            raise Exception('Unknown GObject with ID "{}"'.format(id))
        setattr(self, id, gtk_object)
        return gtk_object

    def __setattr__(self, attribute, value):
        if attribute == "title":
            self.root.set_title(value)
        else:
            self.__dict__[attribute] = value

    def init(self):
        pass

    def setup(self, *args, **kwargs):
        pass

    def teardown(self):
        pass

    def result(self):
        return None

    # handler
    def quit(self, *args):
        App.quit()


# ____________________________________________________________________________ #


class Dialog(Window):

    @classmethod
    def show(self, *args, **kwargs):
        self.instance.setup(*args, **kwargs)
        response = self.instance.root.run()
        self.hide()
        if response == Gtk.ResponseType.OK:
            return self.instance.result()
        return None


# ____________________________________________________________________________ #

    def respond_ok(self, *args):
        self.instance.root.response(Gtk.ResponseType.OK)

    def respond_cancel(self, *args):
        self.instance.root.response(Gtk.ResponseType.CANCEL)

    def respond_apply(self, *args):
        self.instance.root.response(Gtk.ResponseType.APPLY)

    def respond_close(self, *args):
        self.instance.root.response(Gtk.ResponseType.CLOSE)

    def respond_yes(self, *args):
        self.instance.root.response(Gtk.ResponseType.YES)

    def respond_no(self, *args):
        self.instance.root.response(Gtk.ResponseType.NO)


# ____________________________________________________________________________ #


class Welcome(Window):
    def init(self):
        self.title = _("VHD Scan")
        self.new_label.props.label = _("New Project")
        self.open_label.props.label = _("Open Project")
        self.app_name.props.label = _("VHD Scan")
        self.version.props.label = _("Version %s") % App.version

    def setup(self):
        recent_projects = Config.get_recent()
        for btn in self.recent_list.get_children():
            btn.destroy()

        if not recent_projects:
            self.recent_scroll.hide()
            self.root.resize(300, 260)
        else:
            for recent in recent_projects:
                recent_path, recent_display_path, recent_name = recent

                btn = Button()
                btn.add_class("button")
                box = Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                box.add_class("box")
                name = Label()
                path = Label()

                name.props.label = recent_name
                path.props.label = recent_display_path
                name.props.halign = Gtk.Align.START
                path.props.halign = Gtk.Align.START
                name.add_class("name")
                path.add_class("path")
                box.pack_start(name, False, False, 0)
                box.pack_start(path, False, False, 0)
                btn.connect("clicked", self.open_recent, recent_path)
                btn.props.relief = Gtk.ReliefStyle.NONE
                btn.add(box)

                self.recent_list.pack_start(btn, False, False, 0)
            self.recent_scroll.show_all()
            self.root.resize(420, 260)

    # handler
    def new_project(self, *args):
        self.hide()
        data = New_Project.show()
        if data and Project.create(data):
            Capture.show()
        else:
            self.show()

    # handler
    def open_project(self, *args):
        self.hide()
        path = Open_Project.show()
        if path and Project.load(path):
            Capture.show()
        else:
            self.show()

    # hander
    def open_recent(self, btn, path):
        self.hide()
        if path and Project.load(path):
            Capture.show()
        else:
            self.show()


# ____________________________________________________________________________ #


class New_Project(Dialog):
    def init(self):
        self.title = _("Create New Project")
        self.name_label.props.label = _("Project Name")
        self.path_label.props.label = _("Project Folder")
        self.format_label.props.label = _("Image Format")
        self.cancel_btn.props.label = _("Cancel")
        self.create_btn.props.label = _("Create")

        self.format_select = ComboBox()
        self.format_box.pack_start(self.format_select, False, True, 0)
        format_list = self.format_select.get_model()
        for format in Camera.get_image_formats():
            format_list.append([format])
        self.format_select.show()

    def result(self):
        return {
            "name": self.name_input.props.text,
            "path": Project.make_path(self.chooser.get_path()),
            "format": self.format_select.get_value(),
        }

    def setup(self, *args, **kwargs):
        self.chooser = FileChooserDialog(
            title=_("Select Project Folder"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.chooser.add_button(_("Choose"), Gtk.ResponseType.OK)
        self.chooser.props.icon_name = "folder"
        self.chooser.props.local_only = False
        self.chooser.props.modal = True
        self.chooser.props.create_folders = True

        self.name_input.props.text = ""
        self.format_select.set_active(0)
        self.create_btn.set_sensitive(False)

        self.reset_path()

    def reset_path(self):
        self.path_icon.props.icon_name = "dialog-warning"
        self.status_label.hide()
        self.basename_label.props.label = "<i>" + _("No project folder selected") + "</i>"

    # handler
    def choose_path(self, *args):
        response = self.chooser.run()
        self.chooser.hide()
        if response == Gtk.ResponseType.OK:
            self.create_btn.props.sensitive = self.check_path()

    def check_path(self):
        path = self.chooser.get_path()
        if not path:
            self.reset_path()
            return False

        name = basename(path)
        self.basename_label.set_label(name)

        if Project.is_path(path):
            self.path_icon.props.icon_name = "dialog-warning"
            self.status_label.show()
            self.status_label.props.label = _("There is already a project inside this folder. Please choose another.")
            return False

        if not Project.is_empty(path):
            self.path_icon.props.icon_name = "dialog-warning"
            self.status_label.show()
            self.status_label.props.label = _("This folder is not empty. Please choose another.")
            return False

        self.path_icon.props.icon_name = "folder"
        self.basename_label.props.tooltip_text = path
        self.status_label.hide()
        return True


# ____________________________________________________________________________ #


class Open_Project:
    @classmethod
    def show(self, *args, **kwargs):
        self.chooser = FileChooserDialog(
            title=_("Open Project"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        self.chooser.props.icon_name = "folder"
        self.chooser.props.local_only = False
        self.chooser.props.modal = True
        self.chooser.props.create_folders = True
        self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        ok_btn = self.chooser.add_button(_("Open"), Gtk.ResponseType.OK)
        self.chooser.connect(
            "selection-changed",
            self.validate_folder,
            ok_btn
        )

        path = None
        if self.chooser.run() == Gtk.ResponseType.OK:
            path = join_path(self.chooser.get_path(), ".vhdscan")
        self.chooser.destroy()
        return path

    # handler
    @staticmethod
    def validate_folder(chooser, btn):
        print(chooser.get_path())
        btn.props.sensitive = Project.is_path(chooser.get_path())


# ____________________________________________________________________________ #


class Update_Project(Dialog):
    def init(self):
        self.title = _("Edit Project")
        self.name_label.props.label = _("Project Name")
        self.format_label.props.label = _("Image Format")
        self.cancel_btn.props.label = _("Cancel")
        self.save_btn.props.label = _("Save")


# ____________________________________________________________________________ #


class Setup_Camera(Dialog):
    def init(self):
        self.__building = False
        self.__camera = None
        self.title = _("Setup Camera")
        self.close_btn.props.label = _("Close")

        # name id path
        types = [str, str, str]
        self.camera_list = ComboBox(types=types)
        self.setup_toolbar.pack_start(self.camera_list, False, True, 0)
        self.__camera_list = self.camera_list.get_model()
        self.camera_list.show()

        # index name
        types = [str, GObject.TYPE_PYOBJECT]
        self.resolution_list = ComboBox(types=types)
        self.setup_toolbar.pack_start(self.resolution_list, False, True, 0)
        self.__resolution_list = self.resolution_list.get_model()
        self.resolution_list.show()

    def setup(self, camera):
        self.clear_controls()
        self.__camera = camera

        self.__camera_list.clear()
        self.__camera_list.append(["", "", _("Keine Kamera")])
        i = 0
        for device in Device_Manager.get_all(only_free=True):
            i += 1
            self.__camera_list.append([device.name, device.id, device.path])
            if device.path == camera.path:
                self.camera_list.set_active(i)

    def result(self):
        pass

    def clear_controls(self):
        for box in self.controls.get_children():
            box.destroy()
        self.__controls = {}

    # handler for camera_list::changed
    def select_device(self, *args):
        self.clear_controls()
        path = self.camera_list.get_value()
        if not path:
            return

        self.__camera.suspend()
        if self.__camera.set_device(path=path):
            for control in self.__camera.controls:
                box = control.create_ui()
                self.controls.pack_start(box, False, False, 0)
                self.controls.show_all()

            i = 0
            self.__resolution_list.clear()
            for resolution in self.__camera.resolutions:
                self.__resolution_list.append([resolution.name, resolution])
                i += 1
        self.__camera.resume()

    # handler for resolution_list::changed
    def select_resolution(self, *args):
        resolution = self.resolution_list.get_value(1)
        self.__camera.set_resolution(resolution)
        self.__camera.start_feed()


# ____________________________________________________________________________ #


class Capture(Window):

    def init(self):
        self.new_btn.props.tooltip_text = _("New Project")
        self.open_btn.props.tooltip_text = _("Open Project")
        self.update_btn.props.tooltip_text = _("Edit Project")
        self.camera_1_btn.props.tooltip_text = _("Setup left camera")
        self.camera_2_btn.props.tooltip_text = _("Setup right camera")
        self.swap_btn.props.tooltip_text = _("Swap camera")
        self.close_btn.props.tooltip_text = _("Close project")
        self.capture_btn.props.label = _("Take pictures")
        self.capture_btn.props.tooltip_text = _("Take pictures of pages")

    def setup(self, *args, **kwargs):
        self.title = _("VHD Scan - %s") % Project.get_name()
        self.swap_btn.props.sensitive = Project.camera_1.active or Project.camera_2.active
        self.camera_1_label.props.label = Project.camera_1.name
        self.camera_2_label.props.label = Project.camera_2.name

    # hander
    def new_project(self, *args):
        self.hide()
        data = New_Project.show()
        if data:
            Project.create(data)
        self.show()

    # hander
    def open_project(self, *args):
        self.hide()
        path = Open_Project.show()
        if path:
            Project.load(path)
        self.show()

    # handler
    def update_project(self, *args):
        self.hide()
        data = Update_Project.show()
        if data:
            Project.update(data)
        self.show()

    # handler
    def capture(self, *args):
        pass

    # handler
    def swap_cameras(self, *args):
        Project.camera_1, Project.camera_2 = Project.camera_2, Project.camera_1
        Project.save()

    # handler
    def setup_camera_1(self, *args):
        self.hide()
        Setup_Camera.show(Project.camera_1)
        self.show()

    # hander
    def setup_camera_2(self, *args):
        self.hide()
        Setup_Camera.show(Project.camera_2)
        self.show()

    # handler
    def close_project(self, *args):
        Project.close()
        self.hide()
        Welcome.show()


# ____________________________________________________________________________ #


class Project:
    path = None
    name = ""
    format = None
    camera_1 = None
    camera_2 = None

    @classmethod
    def save(self):
        if self.path:
            json_save(self.path, {
                "name": self.name,
                "format": self.format,
                "camera_1": self.camera_1.get_config(),
                "camera_2": self.camera_2.get_config(),
            })

    @classmethod
    def create(self, data):
        self.close()
        self.name = data["name"]
        self.path = data["path"]
        self.format = data["format"]
        self.camera_1 = Camera()
        self.camera_2 = Camera()
        self.save()
        Config.add_recent(self.path)
        return True

    @classmethod
    def load(self, path):
        self.close()
        data = json_load(path)
        if not data:
            return False

        self.path = path
        self.name = data["name"]
        self.format = data["format"]
        self.camera_1 = Camera(**data["camera_1"])
        self.camera_2 = Camera(**data["camera_2"])
        Config.add_recent(self.path)
        return True

    @classmethod
    def close(self):
        self.save()
        self.reset()

    @classmethod
    def reset(self):
        self.path = None
        self.name = ""
        self.format = None
        self.camera_1 = None
        self.camera_2 = None

    @classmethod
    def get_name(self):
        if not self.path or not self.name:
            return _("Unnamed Project")
        return self.name

    @staticmethod
    def make_path(path):
        if not path:
            return None
        if basename(path) == ".vhdscan":
            return path
        return join_path(path, ".vhdscan")

    @classmethod
    def is_path(self, path):
        if not path:
            return False
        path = self.make_path(path)
        return is_file(path)

    @staticmethod
    def is_empty(path):
        return is_dir(path) and not os.listdir(path)


# ____________________________________________________________________________ #


class Camera:

    # This is the main capture thread
    thread = None

    def __init__(self, id=None, config=None):
        self.__output = None
        self.__zoom = 1
        self.__capture = None
        self.__device = None
        self.__resolutions = []
        self.__controls = []
        self.__suspended = False

        if not self.set_device(id=id):
            return

        self.set_config(config)

    def __getattr__(self, p):
        if p == "path":
            return self.__device.path if self.active else None
        if p == "active":
            return self.__device is not None
        if p == "name":
            return self.__device.name if self.active else _("No Camera")
        if p == "resolutions":
            return self.__resolutions
        if p == "controls":
            return self.__controls

    def suspend(self):
        self.__suspended = True

    def resume(self):
        self.__suspended = False

    def set_device(self, id=None, path=None):
        device = Device_Manager.assign(id=id, path=path)
        if device:
            Device_Manager.free(device=self.__device)
            self.__device = device
            self.__path = device.path
            self.init_resolutions()
            self.init_controls()
            return True
        return False

    def get_device(self):
        return self.__device if self.active else None

    def set_config(self, config):
        if not config:
            return

        for property in config:
            self.set(property, config[property])

    def get_config(self):
        if not self.__device:
            return {"id": "", "config": None}

        config = {
            "zoom": self.__zoom,
            "resolution": self.__resolution
        }

        for control in self.__controls:
            config[control.name] = control.value

        return {
            "id": self.__device.id,
            "config": config
        }

    def set(self, property, value):
        if not self.__device:
            return False

        if property == "resolution":
            return self.set_resolution(resolution=value)

        if property == "zoom":
            return self.set_zoom(value)

        if property not in self.__controls:
            return False

        if value == self.__controls[property].value:
            return False

        result = exec("v4l2-ctl", "--device", self.path, "--set-ctrl", "{0}={1}".format(property, value))
        if result:
            self.__controls[property].value = value

        return result

    def set_zoom(self, percent=100):
        self.__zoom = percent / 100

    def set_resolution(self, resolution=None, width=None, height=None, pixelformat=None):
        if not self.__device:
            return False

        if resolution:
            # unpack the resolution string
            width, height, pixelformat = resolution.split("x", 2)

        resolution = "height={0},width={1},pixelformat={2}".format(height, width, pixelformat)
        success = exec("v4l2-ctl", "--device", self.path, "--set-fmt-video", resolution)
        if success:
            self.__device["resolution"] = "{0}x{1}x{2}".format(width, height, pixelformat)
        return success

    def get_resolution(self):
        width = 0
        height = 0
        pixelformat = ""
        for line in cmd("v4l2-ctl", "--device", self.path, "--get-fmt-video"):
            if "Width/Height" in line:
                width, height = regex(r"(\d+/\d+)", line).split("/", 1)
            elif "Pixel Format" in line:
                pixelformat = regex(r"'([^']+)'", line)
        return "{0}x{1}x{2}".format(width, height, pixelformat)

    def init_resolutions(self):
        self.__resolutions = []
        for line in cmd("v4l2-ctl", "--device", self.path, "--list-formats-ext"):
            if "]: '" in line:
                pixelformat = regex(r"'([^']+)'", line)
            elif "Size:" in line:
                width, height = regex(r"(\d+)x(\d+)", line, [1, 2])
                self.__resolutions.append(Resolution(
                    width=width,
                    height=height,
                    pixelformat=pixelformat
                ))

    def init_controls(self):
        self.__controls = {}
        in_menu = False
        for line in cmd("v4l2-ctl", "--device", self.path, "--list-ctrls-menus"):
            line = line.strip()
            if " 0x" in line:
                in_menu = False
                name = line.split("0x", 1)[0].strip()
                value = int(regex(r"value=(-?\d+)", line))
                if " (int)" in line:
                    control = Control(
                        type=Control.INT,
                        name=name,
                        value=value,
                        min=regex(r"min=(-?\d+)", line),
                        max=regex(r"max=(-?\d+)", line),
                        step=regex(r"step=(-?\d+)", line),
                        default=regex(r"default=(-?\d+)", line),
                        camera=self,
                    )

                elif " (bool)" in line:
                    control = Control(
                        type=Control.BOOL,
                        name=name,
                        value=value,
                        camera=self,
                    )

                elif " (menu)" in line:
                    in_menu = True
                    control = Control(
                        type=self.MENU,
                        name=name,
                        value=value,
                        camera=self,
                    )

                else:
                    continue

                self.__controls[name] = control

            elif in_menu and line:
                value, text = line.split(": ", 1)
                control.add_value(int(value), text)

    def start_feed(self, output):
        if not self.__device:
            return False

        if self.thread > 0:
            return False

        self.__output = output
        self.thread = GLib.idle_add(self.__render_frame)
        return True

    def stop_feed(self):
        if not self.__device:
            return False

        if self.thread == 0:
            return False

        GLib.source_remove(self.thread)
        self.__capture.release()
        self.__capture = None
        self.__output = None
        self.thread = 0
        return True

    def __render_frame(self):
        if not self.__device:
            return False

        ok, frame = self.__capture.read()
        if not ok:
            return False

        width = int(frame.shape[1] * self.__zoom)
        height = int(frame.shape[0] * self.__zoom)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        in_height, in_width = frame.shape[0:2]
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            data=frame.tobytes(),
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=False,
            bits_per_sample=8,
            height=in_height,
            width=in_width,
            rowstride=frame.shape[2] * in_width,
        )
        self.__output.set_from_pixbuf(
            pixbuf.scale_simple(
                dest_height=height,
                dest_width=width,
                interp_type=GdkPixbuf.InterpType.NEAREST,
            ).copy()
        )
        return True

    @staticmethod
    def get_image_formats():
        formats = []
        for format in GdkPixbuf.Pixbuf.get_formats():
            if format.is_writable():
                formats.append(format.get_name())
        return formats


# ____________________________________________________________________________ #


class Resolution:
    def __init__(self, width, height, pixelformat):
        self.width = int(width)
        self.height = int(height)
        self.pixelformat = pixelformat
        self.name = "[{0}] {1}x{2}".format(pixelformat, width, height)
        self.fourcode = cv2.VideoWriter_fourcc(*pixelformat)


# ____________________________________________________________________________ #


class Control:
    INT = 0
    BOOL = 1
    MENU = 2

    def __init__(self, type, name, value, camera, min=None, max=None, step=None, default=None):
        if min == 0 and max == 1:
            type = self.BOOL
        self.type = type
        self.name = name
        self.value = value
        self.min = min
        self.max = max
        self.step = step
        self.default = default
        self.values = []
        self.__inputs = []
        self.__camera = camera

    def add_value(self, value, text):
        if not self.type == self.MENU:
            return
        self.values.append([value, text])

    def create_ui(self):
        box = Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2
        )
        label = Label()
        label.props.label = _(name)
        label.props.halign = Gtk.Align.START
        box.pack_start(label, False, False, 0)

        if self.type == self.INT:
            scale_box = Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=0
            )
            adjustment = Gtk.Adjustment(
                value=self.value,
                lower=self.min,
                upper=self.max,
                step_increment=self.step,
                page_increment=5,
                page_size=0
            )
            scale = Scale(
                orientation=Gtk.Orientation.HORIZONTAL,
                adjustment=adjustment
            )
            scale.props.digits = 0
            scale.props.draw_value = False
            scale.value_post = Gtk.PositionType.RIGHT
            scale.add_mark(
                value=self.default,
                position=Gtk.PositionType.BOTTOM,
                markup=str(self.default),
            )
            scale.add_mark(
                value=self.min,
                position=Gtk.PositionType.TOP,
                markup=str(self.min),
            )
            scale.add_mark(
                value=self.max,
                position=Gtk.PositionType.TOP,
                markup=str(self.max),
            )
            scale.connect("value-changed", self.update_int)
            spinbox = SpinButton(
                adjustment=adjustment,
                digits=0,
                climb_rate=0
            )
            spinbox.props.valign = Gtk.Align.CENTER
            spinbox.connect("value-changed", self.update_int)
            scale_box.pack_start(scale, True, True, 0)
            scale_box.pack_start(spinbox, False, True, 0)
            box.pack_start(scale_box, True, True, 0)
            self.__inputs = [scale, spinbox]

        elif self.type == self.BOOL:
            switch = Switch(
                hexpand=False,
                vexpand=False
            )
            switch.props.active = self.value == 1
            switch.props.halign = Gtk.Align.START
            switch.connect("notify::active", self.update_bool)
            box.pack_start(switch, False, False, 0)
            self.__inputs = [switch]

        elif self.type == self.MENU:
            combo = ComboBox()
            list = combo.get_model()
            i = 0
            for entry in self.values:
                list.append(entry)
                if entry[0] == self.value:
                    combo.set_active(i)
                i += 1
            combo.connect("changed", self.update_menu)
            box.pack_start(combo, True, True, 0)
            self.__inputs = [combo]

        return box

    def update_int(self, scale):
        self.__camera.set(self.name, int(scale.get_value()))

    def update_bool(self, switch, active,):
        self.__camera.set(self.name, switch.get_state())

    def update_menu(self, combobox):
        self.__camera.set(self.name, combobox.get_value(1))

    def set_sensitive(self, state):
        for input in self.__inputs:
            input.props.sensitive = state

# ____________________________________________________________________________ #


class Device_Manager:
    __devices = []

    @classmethod
    def get_all(self, only_free=True):
        self.refresh()
        devices = []
        for device in self.__devices:
            if only_free and device.in_use:
                continue
            devices.append(device)
        return devices

    @classmethod
    def get(self, id=None, path=None):
        if not id and not path:
            return None

        self.refresh()
        if id:
            for device in self.__devices:
                if device.id == id:
                    return device
        elif path:
            for device in self.__devices:
                if device.path == path:
                    return device
        return None

    @classmethod
    def free(self, id=None, path=None, device=None):
        if not id and not path and not device:
            return False

        for _device in self.__devices:
            if (device and _device == device) or (id and device.id == id) or (path and device.path == path):
                device.in_use = False
                return True
        return False

    @classmethod
    def assign(self, id=None, path=None, context=True):
        if not id and not path:
            return False

        self.refresh()
        for device in self.__devices:
            if device.in_use:
                continue
            if (id and device.id == id) or (path and device.path == path):
                device.in_use = context
                return device
        return None

    @classmethod
    def refresh(self):
        new_devices = []
        for line in cmd("v4l2-ctl", "--list-devices"):
            if "/dev/" in line:
                new_device = Device(line.strip())
                if new_device.valid and new_device.can_capture:
                    new_devices.append(new_device)

        devices = []
        for old_device in self.__devices:
            for new_device in new_devices:
                if old_device.id == new_device.id and old_device.path == new_device.path:
                    devices.append(old_device)
                    new_devices.remove(new_device)

        devices += new_devices
        self.__devices = devices

# ____________________________________________________________________________ #


class Device:

    def __init__(self, path):
        self.id = "0000:0000:0"
        self.name = ""
        self.vendor = _("Unknown Manufacturer")
        self.vendor_id = "0000"
        self.model = _("Unknown Model")
        self.model_id = "0000"
        self.revision = "0"
        self.in_use = False
        self.valid = False

        lines = cmd("udevadm", "info", "--name", path, "--query=property")
        if lines is None:
            self.path = None
            return

        for line in lines:
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            if key == "ID_VENDOR":
                self.vendor = value.replace("_", " ")
            elif key == "ID_VENDOR_ID":
                self.vendor_id = value.upper()
            elif key == "ID_MODEL":
                self.model = value.replace("_", " ")
            elif key == "ID_MODEL_ID":
                self.model_id = value.upper()
            elif key == "ID_REVISION":
                self.revision = value.upper()

        # we build an id to identify a device later on
        self.id = "{0}:{1}:{2}".format(self.vendor_id, self.model_id, self.revision)
        self.name = "{0} [{1}]".format(self.model, path)
        self.path = path
        self.valid = True

        in_caps = False
        self.can_capture = False
        for line in cmd("v4l2-ctl", "--device", self.path, "--info"):
            if re.match(r"\s*Device Caps\s*: 0x", line):
                in_caps = True
            elif in_caps and "Video Capture" in line:
                self.can_capture = True
                break

# ____________________________________________________________________________ #


class _Unused:

    @staticmethod
    def get_state(path):
        status = {}
        for line in cmd("v4l2-ctl", "--device", path, "--list-ctrl-menus"):
            if "0x" in line:
                name = line.split("0x", 1)[0].strip()
                status[name] = "flags=inactive" not in line
        return status

# ____________________________________________________________________________ #


class Config:
    @classmethod
    def load(self):
        self.__config = {
            "recent": []
        }
        self.__config_dir = user_config_dir(appname="vhdscan")
        self.__config_path = join_path(self.__config_dir, "vhdscan.config")
        config = json_load(self.__config_path)
        if config:
            self.__config.update(config)

    @classmethod
    def __save(self):
        if not is_dir(self.__config_dir):
            mkdirs(self.__config_dir, mode=0o777, exist_ok=True)

        json_save(self.__config_path, self.__config)

    @classmethod
    def __getattr__(self, key):
        if key == "__config":
            return self.__config
        return self.__config.get(key, None)

    @classmethod
    def __setattr__(self, key, value):
        self.__config[key] = value
        self.__save()

    @classmethod
    def get_recent(self):
        recents = []
        home_path = os.path.expanduser("~")
        for path in self.__config["recent"]:
            if not is_file(path):
                continue

            data = json_load(path)
            name = data.get("name", _("Unnamed Project"))
            display_path = path
            if not home_path == "~":
                display_path = path.replace(home_path, "~")
            recents.append((path, display_path, name))
        return recents

    @classmethod
    def add_recent(self, path):
        paths = self.__config["recent"]
        for _path in paths:
            if _path == path:
                paths.remove(path)
                break
        paths.insert(0, path)
        if len(paths) > 15:
            self.__config["recent"] = paths[0:15]
        self.__save()

# ____________________________________________________________________________ #


class App:

    version = "beta"

    __locale = None
    __l10n = None
    __stylesheets = {}
    __screen = None

    @classmethod
    def run(self):
        self.__screen = Gdk.Screen.get_default()

        Config.load()
        self.load_locale()

        # Init the dialogs and windows
        Welcome.glade("ui/welcome.glade", "ui/welcome.css")
        New_Project.glade("ui/new-project.glade")
        Update_Project.glade("ui/update-project.glade")
        Capture.glade("ui/capture.glade")
        Setup_Camera.glade("ui/setup-camera.glade")

        Welcome.show()
        Gtk.main()

    @classmethod
    def load_config(self):
        self.__config = {
            "recent": []
        }
        self.__config_dir = user_config_dir(appname="vhdscan")
        self.__config_path = join_path(self.__config_dir, "vhdscan.config")
        config = json_load(self.__config_path)
        if config:
            self.__config.update(config)

    @classmethod
    def load_locale(self):
        self.__locale = "de"
        l10n_file = join_path("locale", self.__locale + ".json")
        if is_file(l10n_file):
            self.__l10n = json_load(l10n_file)

    @classmethod
    def add_stylesheet(self, path):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(path)
        Gtk.StyleContext.add_provider_for_screen(
            screen=self.__screen,
            provider=css_provider,
            priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.__stylesheets[path] = css_provider

    @classmethod
    def remove_stylesheet(self, path):
        if path in self.__stylesheets:
            Gtk.StyleContext.remove_provider_for_screen(
                screen=self.__screen,
                provider=self.__stylesheets[path]
            )

    @classmethod
    def quit(self, *args):
        Gtk.main_quit()

    @classmethod
    def translate(self, text):
        return self.__l10n.get(text, text) if self.__l10n else text


if __name__ == "__main__":
    App.run()
