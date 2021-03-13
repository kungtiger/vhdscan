import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from . import locale, settings, udev

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
stylesheets = {}


def add_stylesheet(path):
    global stylesheets
    abspath = realpath(path)
    css_provider = Gtk.CssProvider()
    css_provider.load_from_path(abspath)
    Gtk.StyleContext.add_provider_for_screen(
        screen=Gdk.Screen.get_default(),
        provider=css_provider,
        priority=Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    stylesheets[abspath] = css_provider


def remove_stylesheet(path):
    global stylesheets
    abspath = realpath(path)
    if abspath in stylesheets:
        css_provider = stylesheets.pop(abspath)
        Gtk.StyleContext.remove_provider_for_screen(
            screen=Gdk.Screen.get_default(),
            provider=css_provider,
        )


def quit(*args):
    udev.stop()
    application_ui.destroy()
    project_ui.destroy()
    camera_ui.destroy()
    settings_ui.destroy()
    Gtk.main_quit()


def run(path):
    settings.load()

    add_stylesheet("css/vhdscan.css")

    global application_ui, project_ui, open_dialog, camera_ui, settings_ui
    application_ui = Application_UI("application", quit)
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
