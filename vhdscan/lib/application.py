import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from . import locale, settings, udev, ui

from .camera_ui import Camera_UI
from .application_ui import Application_UI
from .open_dialog import Open_Dialog
from .project_ui import Project_UI
from .settings_ui import Settings_UI

version = "0.3"
application_ui = None
project_ui = None
open_dialog = None
camera_ui = None
settings_ui = None


def quit(*args):
    udev.stop()
    application_ui.destroy()
    project_ui.destroy()
    camera_ui.destroy()
    settings_ui.destroy()
    Gtk.main_quit()


def run(path):
    settings.load()

    ui.add_stylesheet("css/vhdscan.css")

    global application_ui, project_ui, open_dialog, camera_ui, settings_ui
    application_ui = Application_UI("application")
    project_ui = Project_UI("project")
    open_dialog = Open_Dialog()
    camera_ui = Camera_UI("camera")
    settings_ui = Settings_UI("settings")

    locale.load(settings.get("locale"))
    application_ui.show()
    if path:
        application_ui.open_project(path)
    else:
        application_ui.maybe_open_recent()
    Gtk.main()
