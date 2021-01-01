#!/usr/bin/env python3

import gi
import cv2
import os
import re
import json
import subprocess

from appdirs import *
from os.path import basename, dirname, isdir as is_dir, isfile as is_file, join as join_path
from os import makedirs as mkdirs

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GObject, Pango

# ____________________________________________________________________________ #


def _debug_(ctx, *args):
    if Application.debug:
        if type(ctx) == str:
            output = ctx
        else:
            output = ctx.__class__.__name__ + '::'

        for arg in args:
            try:
                bit = str(arg)
                output += ' ' + bit
            except:
                pass

        print(output)


def _(text):
    return Locale.translate(text)


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


class Selectbox(Gtk.ComboBox, UI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__model = Gtk.ListStore(str, str)
        self.set_model(self.__model)

        self.__cell = Gtk.CellRendererText()
        self.pack_start(self.__cell, 25)
        self.add_attribute(self.__cell, "text", 0)

    def get_value(self, fallback=None):
        index = self.get_active()
        if index < 0:
            return fallback
        model = self.get_model()
        return model[index][1]

    def set_value(self, value):
        index = 0
        for row in self.__model:
            if row[1] == value:
                self.set_active(index)
                return True
            index += 1
        return False

    def append(self, text, value=None):
        if value is None:
            value = text
        self.__model.append([text, value])

    def clear(self):
        self.__model.clear()


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

    instance = None

    @classmethod
    def glade(self, *args):
        self.instance = self(*args)

    @classmethod
    def show(self, *args, **kwargs):
        self.instance.update_ui(*args, **kwargs)
        self.instance.root.show()

    @classmethod
    def hide(self):
        self.instance.root.hide()
        self.instance.tidy()

    def __init__(self, glade_file, stylesheet_file=None):
        self.__builder = Gtk.Builder()
        self.__builder.add_from_file(glade_file)
        self.__builder.connect_signals(self)

        if stylesheet_file:
            Application.add_stylesheet(stylesheet_file)

        self.init()

    # Routes unset instance attribute access to Glade and returns a Gtk object
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

    def update_ui(self, *args, **kwargs):
        pass

    def tidy(self):
        pass

    def result(self):
        return None

    # handler
    def quit(self, *args):
        Application.quit()


# ____________________________________________________________________________ #


class Dialog(Window):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root.set_modal(True)

    @classmethod
    def show(self, *args, **kwargs):
        self.instance.update_ui(*args, **kwargs)
        result = None
        response = self.instance.root.run()
        self.instance.root.hide()
        if response == Gtk.ResponseType.OK:
            result = self.instance.result()
        self.instance.tidy()
        return result

    def respond_ok(self, *args):
        self.instance.root.response(Gtk.ResponseType.OK)

    def respond_cancel(self, *args):
        self.instance.root.response(Gtk.ResponseType.CANCEL)


# ____________________________________________________________________________ #


class Welcome(Window):

    def init(self):
        self.title = _("VHD Scan")
        self.new_label.set_label(_("New Project"))
        self.open_label.set_label(_("Open Project"))
        self.app_name.set_label(_("VHD Scan"))
        self.version.set_label(_("Version %s") % Application.version)

    def update_ui(self):
        _debug_(self, "open")
        recent_projects = Config.get_recent()
        for btn in self.recent_list.get_children():
            btn.destroy()

        if not recent_projects:
            _debug_(self, "no recent projects. Hiding the list")
            self.recent_scroll.hide()
            self.root.set_size_request(300, 260)
        else:
            for recent in recent_projects:
                name = Label(
                    label=recent.name,
                    halign=Gtk.Align.START
                )
                name.add_class("name")

                path = Label(
                    label=recent.nice_path,
                    halign=Gtk.Align.START,
                    ellipsize=Pango.EllipsizeMode.MIDDLE,
                    wrap=False
                )
                path.add_class("path")

                box = Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    spacing=2
                )
                box.add_class("box")
                box.pack_start(name, False, False, 0)
                box.pack_start(path, False, False, 0)

                btn = Button()
                btn.add_class("button")
                btn.connect("clicked", self.open_recent, recent.path)
                btn.set_relief = Gtk.ReliefStyle.NONE
                btn.add(box)

                self.recent_list.pack_start(btn, False, False, 0)
            self.recent_scroll.show_all()
            self.root.set_size_request(420, 260)
            _debug_(self, "%s recent projects. Showing the list" % len(recent_projects))
            self.recent_scroll.show()

    # handler
    def new_project(self, *args):
        self.hide()
        data = ProjectDialog.show("new")
        if data and Project.create(data):
            CaptureWindow.show()
        else:
            self.show()

    # handler
    def open_project(self, *args):
        self.hide()
        path = OpenProjectDialog.show()
        if path and Project.load(path):
            CaptureWindow.show()
        else:
            self.show()

    # hander
    def open_recent(self, btn, path):
        self.hide()
        if path and Project.load(path):
            CaptureWindow.show()
        else:
            self.show()


# ____________________________________________________________________________ #


class ProjectDialog(Dialog):
    def init(self):
        self.cancel_btn.set_label(_("Cancel"))

        self.name_box = Box(orientation=Gtk.Orientation.VERTICAL)
        self.name_label = Label(label=_("Project Name"), halign=Gtk.Align.START)
        self.name_input = Gtk.Entry(
            placeholder_text=_("Unnamed Project"),
            width_request=300
        )
        self.name_box.pack_start(self.name_label, False, True, 0)
        self.name_box.pack_start(self.name_input, False, True, 0)

        self.path_box = Box(orientation=Gtk.Orientation.VERTICAL)
        self.basename_label = Label()
        self.basename_label.add_class("label")
        self.basename_icon = Gtk.Image()
        self.basename_box = Box()
        self.path_label = Label(label=_("Project Folder"), halign=Gtk.Align.START)
        self.path_status = Label(halign=Gtk.Align.START)
        self.path_status.add_class("status")
        self.path_btn = Button()
        self.path_btn.connect("clicked", self.choose_path)

        self.basename_box.pack_start(self.basename_icon, False, False, 0)
        self.basename_box.pack_start(self.basename_label, False, False, 8)
        self.path_btn.add(self.basename_box)
        self.path_box.pack_start(self.path_label, False, True, 0)
        self.path_box.pack_start(self.path_btn, False, False, 0)
        self.path_box.pack_start(self.path_status, False, False, 0)

        self.format_box = Box(orientation=Gtk.Orientation.VERTICAL)
        self.format_label = Label(label=_("Image Format"), halign=Gtk.Align.START)
        self.format_select = Selectbox()
        for format in Camera.get_image_formats():
            self.format_select.append(format)
        self.format_select.show()
        self.format_box.pack_start(self.format_label, False, True, 0)
        self.format_box.pack_start(self.format_select, False, True, 0)

        self.form_box.pack_start(self.name_box, False, True, 0)
        self.form_box.pack_start(self.path_box, False, True, 0)
        self.form_box.pack_start(self.format_box, False, True, 0)
        self.form_box.show_all()

    def update_ui(self, mode):
        _debug_(self, "open. In mode '%s'" % mode)
        self.__mode = mode
        if mode == "new":
            self.title = _("Create New Project")
            self.chooser = FileChooserDialog(
                title=_("Select Project Folder"),
                action=Gtk.FileChooserAction.SELECT_FOLDER,
            )
            self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            self.chooser.add_button(_("Choose"), Gtk.ResponseType.OK)
            self.chooser.props.icon_name = "folder"
            self.chooser.set_local_only(False)
            self.chooser.set_modal(True)
            self.chooser.set_create_folders(True)

            self.name_input.set_text("")
            self.format_select.set_active(0)
            self.path_box.show()
            self.ok_btn.set_sensitive(False)
            self.ok_btn.set_label(_("Create"))
        else:
            self.title = _("Edit Project")
            self.name_input.set_text(Project.name)
            self.format_select.set_value(Project.format)
            self.path_box.hide()
            self.ok_btn.set_sensitive(True)
            self.ok_btn.set_label(_("Save"))

        self.reset_path()

    def result(self):
        _debug_(self, "closed")
        data = {
            "name": self.name_input.get_text(),
            "format": self.format_select.get_value(),
        }
        if self.__mode == "new":
            data["path"] = Project.make_path(self.chooser.get_path())
        return data

    def reset_path(self):
        self.path_status.hide()
        self.basename_icon.set_from_icon_name("dialog-warning", Gtk.IconSize.BUTTON)
        self.basename_label.set_label(_("No project folder selected"))
        self.path_box.add_class("invalid")

    # handler
    def choose_path(self, *args):
        response = self.chooser.run()
        self.chooser.hide()
        if response == Gtk.ResponseType.OK:
            self.ok_btn.set_sensitive(self.check_path())

    def check_path(self):
        path = self.chooser.get_path()
        _debug_(self, "Checking path", path)
        if not path:
            self.reset_path()
            return False

        name = basename(path)
        self.basename_label.set_label(name)

        if Project.is_path(path):
            _debug_(self, "Destination has project.")
            self.basename_icon.props.icon_name = "dialog-warning"
            self.path_box.add_class("invalid")
            self.path_status.show()
            self.path_status.set_label(_("There is already a project inside this folder.\nPlease choose another."))
            return False

        if not Project.is_empty(path):
            _debug_(self, "Destination is not empty")
            self.basename_icon.props.icon_name = "dialog-warning"
            self.path_box.add_class("invalid")
            self.path_status.show()
            self.path_status.set_label(_("This folder is not empty.\nPlease choose another."))
            return False

        self.path_box.remove_class("invalid")
        self.basename_icon.props.icon_name = "folder"
        self.basename_label.set_tooltip_text(path)
        self.path_status.hide()
        return True


# ____________________________________________________________________________ #


class OpenProjectDialog:
    @classmethod
    def show(self, *args, **kwargs):
        _debug_(self, "open")
        self.chooser = FileChooserDialog(
            title=_("Open Project"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            local_only=False,
            modal=True
        )
        self.chooser.props.icon_name = "folder"
        self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        ok_btn = self.chooser.add_button(_("Open"), Gtk.ResponseType.OK)
        self.chooser.connect(
            "selection-changed",
            self.validate_folder,
            ok_btn
        )

        path = None
        if self.chooser.run() == Gtk.ResponseType.OK:
            path = Project.make_path(self.chooser.get_path())
        self.chooser.destroy()
        return path

    # handler
    @staticmethod
    def validate_folder(chooser, btn):
        btn.set_sensitive(Project.is_path(chooser.get_path()))


# ____________________________________________________________________________ #


class SetupDialog(Dialog):
    def init(self):
        self.__camera = None
        self.close_btn.set_label(_("Close"))

        self.device_select = Selectbox()
        self.device_select.connect("notify::active", self.select_device)
        self.device_box.pack_start(self.device_select, True, True, 0)
        self.device_select.show()

        self.resolution_select = Selectbox()
        self.resolution_select.connect("notify::active", self.select_resolution)
        self.resolution_box.pack_start(self.resolution_select, True, True, 0)
        self.resolution_select.show()

    def update_ui(self, camera, slot):
        _debug_(self, "open")

        if slot == "left":
            self.title = _("Setup Left Camera")
        else:
            self.title = _("Setup Right Camera")

        self.clear_controls()
        self.__camera = camera
        self.__camera.stop_feed()
        _debug_(self, "camera path:'%s'" % camera.path)

        self.resolution_select.clear()
        self.resolution_box.hide()

        self.device_select.clear()
        self.device_select.append(_("Keine Kamera"), "")
        i = 0
        camera_set = False
        devices = DeviceManager.get_all(
            only_free=True,
            include=self.__camera.path
        )
        _debug_(self, "DeviceManager yielts %s devices" % len(devices))
        for device in devices:
            i += 1
            self.device_select.append(device.name, device.path)
            if device.path == camera.path:
                self.device_select.set_active(i)
                camera_set = True
        if not camera_set:
            _debug_(self, "setup: selected no device")
            self.device_select.set_active(0)

    def tidy(self):
        self.__camera.stop_feed()
        _debug_(self, "closed")

    def clear_controls(self):
        # TODO: Clear output image
        for box in self.controls.get_children():
            box.destroy()
        self.__controls = {}

    # handler for device_select notify::active signal
    def select_device(self, *args):
        self.clear_controls()
        self.__camera.stop_feed()
        self.resolution_select.clear()

        path = self.device_select.get_value()
        if not path:
            self.__camera.free_device()

        _debug_(self, "Selectbox: selected device '%s'" % path)
        self.__camera.set_device(path=path)
        if self.__camera.is_ready:
            for control in self.__camera.controls.values():
                box = control.create_ui()
                self.controls.pack_start(box, False, False, 0)
                self.controls.show_all()
            self.__camera._update_sensitivity()

            for resolution in self.__camera.resolutions:
                self.resolution_select.append(resolution.name, resolution.value)

            current_resolution = self.__camera.get_resolution()
            if current_resolution:
                self.resolution_select.set_value(current_resolution.value)

            self.resolution_box.show()

    # handler for resolution_select notify::active signal
    def select_resolution(self, *args):
        self.__camera.stop_feed()
        key = self.resolution_select.get_value()
        _debug_(self, "Selected resolution '%s'" % key)
        if self.__camera.set_resolution(key):
            self.__camera.start_feed(self.feed_output)


# ____________________________________________________________________________ #


class CaptureWindow(Window):

    def init(self):
        self.camera_1_btn.set_tooltip_text(_("Setup left camera"))
        self.camera_2_btn.set_tooltip_text(_("Setup right camera"))

        self.menu_project.set_label(_("Project"))
        self.menu_project_new.set_label(_("New Project"))
        self.menu_project_open.set_label(_("Open Project"))
        self.menu_project_edit.set_label(_("Edit Project"))
        self.menu_project_statistic.set_label(_("Project Statistic"))
        self.menu_project_close.set_label(_("Close Project"))
        self.menu_quit.set_label(_("Quit"))

        self.menu_camera.set_label(_("Camera"))
        self.menu_camera_capture.set_label(_("Take Photos"))
        self.menu_camera_swap.set_label(_("Swap Cameras"))
        self.menu_camera_1.set_label(_("Setup Left Camera"))
        self.menu_camera_2.set_label(_("Setup Right Camera"))

        self.menu_view.set_label(_("View"))
        self.menu_view_vertical.set_label(_("Vertical"))
        self.menu_view_horizontal.set_label(_("Horizontal"))

        self.menu_view_vertical.connect("toggled", self.change_view, "vertical")
        self.menu_view_horizontal.connect("toggled", self.change_view, "horizontal")

    def update_ui(self, *args, **kwargs):
        _debug_(self, 'open')
        self.title = _("VHD Scan - %s") % Project.get_name()
        # self.swap_btn.set_sensitive(Project.camera_1.is_ready or Project.camera_2.is_ready)
        self.update_camera_buttons()

        if Config.get("view") == "vertical":
            self.menu_view_vertical.set_active(True)
        elif Config.get("view") == "horizontal":
            self.menu_view_horizontal.set_active(True)

    def update_camera_buttons(self):
        self.camera_1_label.set_label(Project.camera_1.name)
        self.camera_2_label.set_label(Project.camera_2.name)

    # hander
    def new_project(self, *args):
        # self.hide()
        data = ProjectDialog.show("new")
        if data:
            Project.create(data)
            self.update_ui()
        # self.show()

    # hander
    def open_project(self, *args):
        self.hide()
        path = OpenProjectDialog.show()
        if path:
            Project.load(path)
        self.show()

    # handler
    def edit_project(self, *args):
        # self.hide()
        data = ProjectDialog.show("edit")
        if data:
            Project.update(data)
            Project.save()
            self.update_ui()
        # self.show()

    # handler
    def capture(self, *args):
        pass

    def show_statistic(self, *args):
        StatisticDialog.show()

    # handler
    def swap_cameras(self, *args):
        Project.camera_1, Project.camera_2 = Project.camera_2, Project.camera_1
        Project.save()
        self.update_camera_buttons()

    # handler
    def setup_camera_1(self, *args):
        self.hide()
        SetupDialog.show(Project.camera_1, "left")
        Project.save()
        self.show()

    # hander
    def setup_camera_2(self, *args):
        self.hide()
        SetupDialog.show(Project.camera_2, "right")
        Project.save()
        self.show()

    # handler
    def close_project(self, *args):
        Project.close()
        self.hide()
        Welcome.show()

    # handler
    def change_view(self, radio, view):
        if view == "horizontal" and self.menu_view_horizontal.get_active():
            _debug_(self, "setting view to '%s'" % view)
            self.camera_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            Config.set("view", view)

        elif view == "vertical" and self.menu_view_vertical.get_active():
            _debug_(self, "setting view to '%s'" % view)
            self.camera_box.set_orientation(Gtk.Orientation.VERTICAL)
            Config.set("view", view)


# ____________________________________________________________________________ #


class StatisticDialog(Dialog):
    def init(self):
        self.title = _("Project Statistic")
        self.close_btn.set_label(_("Close"))

    def update_ui(self):
        pass


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
            _debug_("Project:: saving to '%s'" % self.path)
            json_save(self.path, {
                "name": self.name,
                "format": self.format,
                "camera_1": self.camera_1.get_config(),
                "camera_2": self.camera_2.get_config(),
            })

    @classmethod
    def create(self, data):
        _debug_('Project: create')
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
        _debug_("Project:: '%s': loading data" % path)
        self.close()
        data = json_load(path)
        if not data:
            _debug_("Project:: '%s': empty data" % path)
            return False
        if not self.validate_data(data):
            _debug_("Project:: '%s': no valid data" % path)
            return False

        self.path = path
        self.update(data)
        self.name = data["name"]
        self.format = data["format"]
        self.camera_1 = Camera(**data["camera_1"])
        self.camera_2 = Camera(**data["camera_2"])
        Config.add_recent(self.path)
        _debug_("Project:: '%s': loaded project data" % path)
        return True

    @classmethod
    def update(self, data):
        _debug_("Project:: '%s': setting project data" % self.path)
        for key in data:
            setattr(self, key, data[key])

    @classmethod
    def validate_data(self, data):
        return True

    @classmethod
    def close(self):
        if self.path:
            self.save()
            self.reset()
            _debug_('Project:: closed')

    @classmethod
    def reset(self):
        self.path = None
        self.name = ""
        self.format = None
        self.camera_1 = None
        self.camera_2 = None
        _debug_('Project:: reset')

    @classmethod
    def get_name(self):
        if not self.path or not self.name:
            return _("Unnamed Project")
        return self.name

    @staticmethod
    def make_path(path):
        if not path:
            return None
        if basename(path) == "vhdscan.json":
            return path
        return join_path(path, "vhdscan.json")

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
        self.__zoom = 100
        self.__capture = None
        self.__device = None
        self.__path = None
        self.__resolution = None
        self.__resolutions = None
        self.__controls = []

        if not self.set_device(id=id):
            return

        self.set_config(config)

    def __getattr__(self, name):
        if name == "is_ready":
            return self.__device is not None
        if name == "path":
            return self.__path
        if name == "name":
            return self.__device.name if self.is_ready else _("No Camera")
        if name == "controls":
            return self.__controls
        if name == "resolutions":
            return self.__resolutions
        raise AttributeError(name)

    def set_device(self, path=None, id=None, device=None):
        if not device:
            device = DeviceManager.assign(path=path, id=id)

        if device:
            self.free_device()
            self.__device = device
            self.__path = device.path
            self._init_resolutions()
            self._init_resolution()
            self._init_controls()
            return True
        return False

    def free_device(self):
        if self.__device:
            self.stop_feed()
            DeviceManager.free(path=self.__device.path)
            self.__device = None
            self.__path = None
            self.__resolutions = None
            self.__resolution = None
            self.__controls = []

    def set_config(self, config):
        if not self.is_ready or not config:
            return False

        for property in config:
            self.set(property, config[property])

        return True

    def get_config(self):
        if not self.is_ready:
            return {"id": "", "config": None}

        config = {
            "zoom": self.__zoom,
        }

        if self.__resolution:
            config["resolution"] = self.__resolution.value

        for name, control in self.__controls.items():
            config[name] = control.value

        return {
            "id": self.__device.id,
            "config": config
        }

    def set(self, property, value):
        if not self.is_ready:
            return False

        if property == "resolution":
            return self.set_resolution(resolution=value)

        if property == "zoom":
            return self.set_zoom(value)

        if property not in self.__controls:
            return False

        if value == self.__controls[property].value:
            return False

        ctrl = "{0}={1}".format(property, value)
        result = exec("v4l2-ctl", "--device", self.__path, "--set-ctrl", ctrl)
        if result:
            self.__controls[property].value = value

        return result

    def set_zoom(self, percent=100):
        self.__zoom = percent

    def set_resolution(self, resolution):
        if not self.is_ready:
            return False

        if not isinstance(resolution, Resolution):
            resolution = self.__resolutions[resolution]

        if not resolution:
            return False

        fmt = "height={0},width={1},pixelformat={2}".format(
            resolution.height,
            resolution.width,
            resolution.pixelformat
        )
        if exec("v4l2-ctl", "--device", self.__path, "--set-fmt-video", fmt):
            self.__resolution = resolution
            _debug_(self, "set resolution '%s' on '%s'" % (resolution.value, self.__path))
            return True
        return False

    def get_resolution(self):
        return self.__resolution

    def _init_resolution(self):
        self.__resolution = None
        if not self.__resolutions:
            return False

        width = 0
        height = 0
        pixelformat = ""
        for line in cmd("v4l2-ctl", "--device", self.__path, "--get-fmt-video"):
            if "Width/Height" in line:
                width, height = regex(r"(\d+)/(\d+)", line, [1, 2])
            elif "Pixel Format" in line:
                pixelformat = regex(r"'([^']+)'", line)
        current = Resolution.stringify(width, height, pixelformat)
        self.__resolution = self.__resolutions[current]
        _debug_(self, "loaded resolution '%s' from '%s'" % (current, self.__path))
        return False

    def _init_resolutions(self):
        self.__resolutions = ResolutionList()
        for line in cmd("v4l2-ctl", "--device", self.__path, "--list-formats-ext"):
            if "]: '" in line:
                pixelformat = regex(r"'([^']+)'", line)
            elif "Size:" in line:
                width, height = regex(r"(\d+)x(\d+)", line, [1, 2])
                resolution = Resolution(width, height, pixelformat)
                self.__resolutions.append(resolution)
        _debug_(self, "gathered resolutions from '%s'. %s in total" % (self.__path, len(self.__resolutions)))

    def _init_controls(self):
        self.__controls = {}
        in_menu = False
        for line in cmd("v4l2-ctl", "--device", self.__path, "--list-ctrls-menus"):
            line = line.strip()
            if " 0x" in line:
                in_menu = False
                name = line.split("0x", 1)[0].strip()
                value = int(regex(r"value=(-?\d+)", line))
                inactive = "flags=inactive" in line
                if " (int)" in line:
                    control = Control(
                        type=Control.INT,
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
                        type=Control.BOOL,
                        name=name,
                        value=value,
                        inactive=inactive,
                        camera=self,
                    )

                elif " (menu)" in line:
                    in_menu = True
                    control = Control(
                        type=Control.MENU,
                        name=name,
                        value=value,
                        inactive=inactive,
                        camera=self,
                    )

                else:
                    continue

                self.__controls[name] = control

            elif in_menu and line:
                menu_value, menu_text = line.split(": ", 1)
                control.add_value(menu_text, menu_value)
        _debug_(self, "gathered controls from '%s'. %s in total" % (self.__path, len(self.__controls)))

    def _update_sensitivity(self):
        if not self.is_ready:
            return

        for line in cmd("v4l2-ctl", "--device", self.__path, "--list-ctrls-menus"):
            if "0x" in line:
                is_sensitive = "flags=inactive" not in line
                name = line.split("0x", 1)[0].strip()
                self.__controls[name].set_sensitive(is_sensitive)

    def start_feed(self, output):
        if not self.is_ready or not self.__resolution:
            return False

        if self.thread is not None:
            self.stop_feed()

        self.__output = output
        self.thread = GLib.idle_add(self.__render_frame)
        _debug_(self, "started feed for '%s'" % self.__path)
        return True

    def stop_feed(self):
        if not self.is_ready:
            return False

        if self.thread is None:
            return False

        GLib.source_remove(self.thread)
        _debug_(self, "stopped feed for '%s'" % self.__path)
        self.__capture.release()
        self.__capture = None
        self.__output = None
        self.thread = None
        return True

    def __render_frame(self):
        if not self.is_ready:
            return False

        if not self.__capture:
            self.__capture = cv2.VideoCapture()
            if not self.__capture.open(
                filename=self.__path,
                apiPreference=cv2.CAP_V4L2
            ):
                self.__capture = None
                return False

            self.__capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.__resolution.width)
            self.__capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.__resolution.height)
            self.__capture.set(cv2.CAP_PROP_FOURCC, self.__resolution.fourcode)

        ok, frame = self.__capture.read()
        if not ok:
            return False

        width = int(frame.shape[1] * self.__zoom / 100)
        height = int(frame.shape[0] * self.__zoom / 100)
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
        del pixbuf
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
        if "x" in str(width):
            width, height, pixelformat = str(width).split("x", 2)
        self.width = int(width)
        self.height = int(height)
        self.pixelformat = str(pixelformat)
        self.name = "[{0}] {1}x{2}".format(pixelformat, width, height)
        self.fourcode = cv2.VideoWriter_fourcc(*pixelformat)
        self.value = self.stringify(width, height, pixelformat)

    @staticmethod
    def stringify(width, height, pixelformat):
        return "{0}x{1}x{2}".format(width, height, pixelformat)


# ____________________________________________________________________________ #


class ResolutionList:
    def __init__(self):
        self.__list = []
        self.__keys = []

    def append(self, resolution):
        if type(resolution) == str:
            resolution = Resolution(resolution)
        if not self.__contains__(resolution):
            self.__list.append(resolution)
            self.__keys.append(resolution.value)

    def keys(self):
        return self.__keys.copy()

    def values(self):
        return self.__list.copy()

    def __len__(self):
        return len(self.__list)

    def __iter__(self):
        return iter(self.__list)

    def __contains__(self, resolution):
        if not isinstance(resolution, Resolution):
            return False
        return resolution.value in self.__keys

    def __getitem__(self, key):
        if key in self.__keys:
            index = self.__keys.index(key)
            return self.__list[index]
        return None


# ____________________________________________________________________________ #


class Control:
    INT = 0
    BOOL = 1
    MENU = 2

    def __init__(self, type, name, value, camera, min=0, max=0, step=0, default=0, inactive=False):
        self.name = name
        self.value = int(value)
        self.min = int(min)
        self.max = int(max)
        self.step = int(step)
        self.default = int(default)
        self.inactive = inactive
        self.values = []
        self.__inputs = []
        self.__camera = camera
        if self.min == 0 and self.max == 1:
            type = self.BOOL
        self.type = type

    def add_value(self, text, value):
        if not self.type == self.MENU:
            return
        self.values.append((text, value))

    def create_ui(self):
        box = Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )
        label = Label(
            label=_(self.name),
            halign=Gtk.Align.START
        )
        box.pack_start(label, False, False, 0)

        if self.type == self.INT:
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
                adjustment=adjustment,
                digits=0,
                draw_value=False,
                value_pos=Gtk.PositionType.RIGHT
            )
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
            scale_box = Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=8
            )
            scale_box.pack_start(scale, True, True, 0)
            scale_box.pack_start(spinbox, False, True, 0)
            box.pack_start(scale_box, True, True, 0)
            self.__inputs = [scale, spinbox]

        elif self.type == self.BOOL:
            switch = Switch(
                halign=Gtk.Align.START,
                hexpand=False,
                vexpand=False,
                active=self.value == 1
            )
            switch.connect("notify::active", self.update_bool)
            box.pack_start(switch, False, False, 0)
            self.__inputs = [switch]

        elif self.type == self.MENU:
            selectbox = Selectbox()
            list = selectbox.get_model()
            i = 0
            for _text, _value in self.values:
                selectbox.append(_text, _value)
                if int(_value) == self.value:
                    selectbox.set_active(i)
                i += 1
            selectbox.connect("notify::active", self.update_menu)
            box.pack_start(selectbox, True, True, 0)
            self.__inputs = [selectbox]

        return box

    def update_int(self, scale):
        i = int(scale.get_value())
        _debug_(self, self.name + "(int) setting to " + str(i))
        self.__camera.set(self.name, i)

    def update_bool(self, switch, *args):
        state = 1 if switch.get_active() else 0
        _debug_(self, self.name + "(bool) setting to " + str(state))
        self.__camera.set(self.name, state)
        self.__camera._update_sensitivity()

    def update_menu(self, selectbox, *args):
        value = selectbox.get_value()
        _debug_(self, self.name + "(menu) setting to " + str(value))
        self.__camera.set(self.name, value)
        self.__camera._update_sensitivity()

    def set_sensitive(self, is_sensitive):
        for input in self.__inputs:
            input.set_sensitive(is_sensitive)

# ____________________________________________________________________________ #


class DeviceManager:
    __devices = []

    @classmethod
    def get_all(self, only_free=True, include=[]):
        self.refresh()
        devices = []
        check_include = bool(include)
        for device in self.__devices:
            if check_include and device.path in include:
                devices.append(device)
                continue

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
    def free(self, path=None, device=None):
        if not path and not device:
            return False

        for _device in self.__devices:
            if (path and _device.path == path) or (_device and _device == device):
                _debug_("DeviceManager:: device '%s' is now free" % _device.path)
                _device.in_use = False
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
                _debug_("DeviceManager:: device '%s' is now in use" % device.path)
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


class Recent:
    def __init__(self, path):
        data = json_load(path)
        if not data:
            return

        self.path = path
        self.name = data.get("name", _("Unnamed Project"))
        nice_path = dirname(path)
        if not Application.home_path == "~":
            nice_path = nice_path.replace(Application.home_path, "~")
        self.nice_path = nice_path


# ____________________________________________________________________________ #


class Config:
    @classmethod
    def load(self):
        self.__config = {
            "locale": "de",
            "view": "vertical",
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
    def get(self, key, fallback=None):
        return self.__config.get(key, fallback)

    @classmethod
    def set(self, key, value):
        self.__config[key] = value
        self.__save()

    @classmethod
    def get_recent(self):
        recents = []
        for path in self.__config["recent"]:
            if not Project.is_path(path):
                continue
            recent = Recent(path)
            if not recent.path:
                continue
            recents.append(recent)
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


class Locale:
    __locale = None
    __l10n = None

    @classmethod
    def load(self, name):
        self.__locale = name
        l10n_file = join_path("locale", self.__locale + ".json")
        if is_file(l10n_file):
            self.__l10n = json_load(l10n_file)

    @classmethod
    def translate(self, text):
        if not self.__l10n:
            return text
        return self.__l10n.get(text, text)

# ____________________________________________________________________________ #


class Application:

    version = "beta"
    debug = True

    __stylesheets = {}
    __screen = None

    @classmethod
    def run(self):
        self.__screen = Gdk.Screen.get_default()
        self.home_path = os.path.expanduser("~")

        Config.load()
        Locale.load(Config.get("locale"))

        # Init the dialogs and windows
        Welcome.glade("ui/welcome.glade", "ui/welcome.css")
        ProjectDialog.glade("ui/project.glade")
        CaptureWindow.glade("ui/capture.glade")
        StatisticDialog.glade("ui/statistic.glade")
        SetupDialog.glade("ui/setup.glade")

        Welcome.show()
        Gtk.main()

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


if __name__ == "__main__":
    Application.run()
