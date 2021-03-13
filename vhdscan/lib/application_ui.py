from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GObject, Pango
import re
from os.path import isfile as is_file, join as join_path
from . import application, camera, settings, project, ui
from .locale import _
from .project import Project
from .camera import Camera


ZOOM_FIT = 1
ZOOM_ORIGINAL = 2
ZOOM_MANUAL = 3
ZOOM_DEFAULT = 100


class Application_UI(ui.Window):

    def init(self):
        self.project = None
        self.camera = None
        self.camera_1 = None
        self.camera_2 = None
        self._updating_ui = False
        self._autostart_feed_id = None
        self._status_messages = {}
        self._error_messages = {}

        # let's have some shortcuts
        self.set_frame = self.output_frame.set_from_pixbuf
        self.get_frame = self.output_frame.get_pixbuf
        self.set_status_text = self.status_text.set_label
        self.set_error_text = self.error_text.set_label
        self.set_status_icon = self.status_icon.set_from_file

        self.save_btn.connect("clicked", self.save_current_image)
        self.new_btn.connect("clicked", self.create_project)
        self.open_btn.connect("clicked", self.choose_project)
        self.edit_btn.connect("clicked", self.edit_project)
        self.close_btn.connect("clicked", self.close_project)
        self.camera_btn.connect("clicked", self.setup_camera)
        self.settings_btn.connect("clicked", self.show_settings)

        self.current_page_adjustment = Gtk.Adjustment(
            value=1,
            upper=1,
            lower=1,
            step_increment=1,
            page_increment=10,
            page_size=0
        )
        self.current_page_adjustment.connect("value-changed", self.current_page_changed)
        self.current_page_input.connect("changed", self.current_page_autowidth)
        self.current_page_input.set_adjustment(self.current_page_adjustment)

        self.zoom_adjustment = Gtk.Adjustment(
            value=100,
            upper=200,
            lower=10,
            step_increment=5,
            page_increment=10,
            page_size=0
        )
        self.zoom_scale.set_adjustment(self.zoom_adjustment)
        self.zoom_scale.add_mark(
            value=100,
            position=Gtk.PositionType.BOTTOM,
        )
        self.zoom_adjustment.connect("value-changed", self.update_zoom_label)

    def destroy(self):
        if self.project:
            self.camera.stop()
        super().destroy()

    def update_translation(self, *args):
        self.update_title()
        self.save_label.set_label(_("Take Image"))
        self.new_btn.set_tooltip_text(_("New Project"))
        self.open_btn.set_tooltip_text(_("Open Project"))
        self.edit_btn.set_tooltip_text(_("Edit Project"))
        self.camera_btn.set_tooltip_text(_("Setup Camera"))
        self.settings_btn.set_tooltip_text(_("Settings"))
        self.close_btn.set_tooltip_text(_("Close Project"))
        self.zoom_in_btn.set_tooltip_text(_("Zoom in"))
        self.zoom_out_btn.set_tooltip_text(_("Zoom out"))
        self.zoom_fit_btn.set_tooltip_text(_("Zoom to fit"))
        self.zoom_original_btn.set_tooltip_text(_("Zoom to original"))

        self.update_current_page_label()

        self._status_messages = {
            camera.UNSET: _("The camera is not setup."),
            camera.SETUP: _("Setting up camera..."),
            camera.IDLE: _("The camera is ready."),
            camera.INIT: _("Starting camera..."),
            camera.FEED: _("Feeding images"),
            camera.SETUP_ERROR: _("Could not setup camera."),
            camera.INIT_ERROR: _("Could not start camera feed."),
            camera.FEED_ERROR: _("Could not feed camera images."),
        }

        self._error_messages = {
            camera.E_NOT_READY: _("No camera device is set. Please select one."),
            camera.E_SET_RESOLUTION: _("Can not start camera feed because the resolution could not be set."),
            camera.E_SET_PIXELFORMAT: _("Can not start camera feed because the pixelformat could not be set."),
            camera.E_DEVICE_BUSY: _("Can not start camera feed because the camera device is already opened by another process."),
            camera.E_CAMERA_IO: _("Could not read frame from camera device. The camera might be disconnected."),
            camera.E_NO_RESOLUTION: _("Could not set camera device because the device does not provide a resolution."),
            camera.E_NO_RESOLUTIONS: _("Could not set camera device because the device does not provide any image resolutions."),
            camera.E_BANDWIDTH: _("Could not start camera feed because there is already an active feed."),
        }

    def update_ui(self, *args, **kwargs):
        if self._updating_ui:
            return
        self._updating_ui = True

        self.update_title()
        self.save_btn.set_sensitive(False)
        if self.project:
            self.edit_btn.set_sensitive(True)
            self.camera_btn.set_sensitive(True)
            self.close_btn.set_sensitive(True)
            self.current_page_adjustment.set_upper(self.project.total_pages)
            self.current_page_adjustment.set_value(self.project.current_page)
            self.bottom_toolbar.show()
            self.navigation_box.set_sensitive(False)
            self.zoom_box.set_sensitive(False)

            zoom_level = self.project.zoom_level
            if not zoom_level:
                zoom_level = ZOOM_DEFAULT
            self.zoom_adjustment.set_value(zoom_level)

        else:
            self.edit_btn.set_sensitive(False)
            self.camera_btn.set_sensitive(False)
            self.close_btn.set_sensitive(False)
            self.status_box.hide()
            self.output_scroll.hide()
            self.bottom_toolbar.hide()

        self._updating_ui = False

    def switch_camera(self, *args):
        self.camera.stop()
        self._switch_camera()
        self.camera.start()

    def _switch_camera(self):
        is_left = self.project.current_page % 2 == 1
        self.camera = self.camera_1 if is_left else self.camera_2

    # handler
    def update_zoom_label(self, *args):
        zoom = int(self.zoom_adjustment.get_value())
        self.zoom_label.set_label("{0}%".format(zoom))
        self.project.zoom_level = zoom
        self.project.save()

    # handler
    def current_page_changed(self, *args):
        if not self._updating_ui:
            page = int(self.current_page_adjustment.get_value())
            self.project.current_page = page
            self.project.save()
            self.switch_camera()

        self.update_progress_label()
        self.update_current_page_label()

    def update_progress_label(self):
        if self.project:
            total = self.project.total_pages
            current = self.project.current_page
            progress = int(100 * current / total)
            self.progress_label.set_label("{0}%".format(progress))

    def update_current_page_label(self):
        if self.project:
            is_left = self.project.current_page % 2 == 1
            text = _("Left Page") if is_left else _("Right Page")
            self.current_page_label.set_text(text)

    # handler
    def current_page_autowidth(self, *args):
        text = self.current_page_input.get_text()
        n = max(1, len(text))
        self.current_page_input.set_width_chars(n)

    def update_title(self):
        if not self.project:
            self.set_title(_("VHD Scan"))
        else:
            name = self.project.get_name()
            if not name:
                name = _("Unnamed Book")
            self.set_title(_("VHD Scan - {0}").format(name))

    # hander
    def save_current_image(self, *args):
        pixbuf = self.get_frame()
        if not pixbuf:
            return

        details = self.project.get_current_image_filename()
        path = details["path"]
        do_save = False
        if not is_file(path):
            do_save = True

        else:
            duplicate_handle = self.project.duplicate_handle
            if duplicate_handle == "ask":
                do_save = ui.ask(_("Replace image file?"))

            elif duplicate_handle == "replace":
                do_save = True

            elif duplicate_handle == "suffix":
                i = 0
                while True:
                    i += 1
                    filename = "%s (%d).%s" % (details["basename"], i, details["format"])
                    _path = join_path(details["dirname"], filename)
                    if not is_file(_path):
                        path = _path
                        do_save = True
                        break

        if do_save:
            format = details["format"]
            if format == "jpeg":
                quality = str(self.project.jpeg_quality)
                pixbuf.savev(path, "jpeg", ["quality"], [quality])
            elif format == "tiff":
                compression = str(self.project.tiff_compression)
                pixbuf.savev(path, "tiff", ["compression"], [compression])
            elif format == "png":
                compression = str(self.project.png_compression)
                pixbuf.savev(path, "png", ["compression"], [compression])

    def show_project_error(self, _noop, code):
        if code == project.E_CREATE_FILE_EXISTS:
            ui.warn(_("Can not create new project because a project already exists at the chosen destination."), _("Can not create project"))

        elif code == project.E_OPEN_EMPTY_PATH:
            ui.warn(_("Please select a path."), _("No path selected"))

        elif code == project.E_OPEN_NOT_FOUND:
            ui.warn(_("The project is gone and can not be opened."), _("Project not found"))

        elif code == project.E_OPEN_UNUSABLE:
            ui.warn(_("The project appears to be broken and can not be opened."), _("Broken project"))

    def show_camera_error(self, cam, code):
        self.set_error_text(self._error_messages[code])

    def camera_status_changed(self, cam, status):
        if cam is self.camera:
            if status == camera.FEED:
                self.status_box.hide()
                self.output_scroll.show()
            else:
                self.output_scroll.hide()
                self.status_box.show()
                self.error_text.hide()
                if status < 0:
                    self.set_status_icon(ui.ERROR_48)
                    self.error_text.show()
                    self.set_error_text(self._error_messages[cam.error])
                self.set_status_text(self._status_messages[status])

    def _init_project(self):
        project = Project()
        project.connect("error", self.show_project_error)
        return project

    def _run_project(self, p):
        self.project = p
        settings.add_recent(self.project)
        camera.set_fps(self.project.fps)
        self.update_ui()

        self.camera_1 = Camera(camera.LEFT)
        self.camera_1.connect("status", self.camera_status_changed)
        self.camera_1.connect("feed", self.render_feed)
        self.camera_2 = Camera(camera.RIGHT)
        self.camera_2.connect("status", self.camera_status_changed)
        self.camera_2.connect("feed", self.render_feed)

        self._switch_camera()
        self._autostart_feed_id = self.camera.connect("ready", self._autostart_feed)

        self.camera_1.set_setup(self.project.setup_1)
        self.camera_2.set_setup(self.project.setup_2)

    # handler: camera::ready
    def _autostart_feed(self, cam, *args):
        cam.start()
        self.navigation_box.set_sensitive(True)
        cam.disconnect(self._autostart_feed_id)
        self._autostart_feed_id = None

    # handler: new_btn::clicked
    def create_project(self, *args):
        project_data = application.project_ui.show()
        if not project_data:
            return

        self.close_project()

        project = self._init_project()
        if project.create(**project_data):
            self._run_project(project)

    # handler open_btn::clicked
    def choose_project(self, *args):
        path = application.open_dialog.show()
        if path:
            self.open_project(path)

    def maybe_open_recent(self):
        if settings.get("on-startup") == settings.STARTUP_OPEN_LAST_PROJECT:
            recent = settings.get_recent()
            if recent:
                self.open_project(recent)

    def open_project(self, path):
        self.close_project()

        project = self._init_project()
        if project.open(path):
            self._run_project(project)

    # handler: edit_btn::clicked
    def edit_project(self, *args):
        project_data = application.project_ui.show(self.project)
        if project_data:
            self.project.update(project_data)
            camera.set_fps(self.project.fps)

    # handle: close_btn::clicked
    def close_project(self, *args):
        if self.project:
            self.camera.stop()
            self.camera_1 = None
            self.camera_2 = None
            self.camera = None
            self.project = None
            self.update_ui()

    # handler: setup_btn::clicked
    def setup_camera(self, *args):
        current_setup = self.camera.get_setup()
        new_setup = application.camera_ui.show(self.camera)
        if not new_setup:
            self.camera.set_setup(current_setup)
        elif new_setup != current_setup:
            if self.camera.slot == camera.LEFT:
                self.project.setup_1 = new_setup
            else:
                self.project.setup_2 = new_setup
            self.project.save()

    # handler: settings_btn::clicked
    def show_settings(self, *args):
        application.settings_ui.show()

    # handler: camera::feed
    def render_feed(self, camera, pixbuf, *args):
        self.set_frame(pixbuf)
