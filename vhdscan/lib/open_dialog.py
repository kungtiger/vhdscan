import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from . import ui, project
from .locale import _


class Open_Dialog:

    def show(self, *args, **kwargs):
        self.chooser = ui.FileChooserDialog(
            title=_("Open Project"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            local_only=False,
            modal=True,
        )
        self.chooser.set_icon_from_file(ui.FOLDER_22)
        self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        ok_btn = self.chooser.add_button(_("Open"), Gtk.ResponseType.OK)
        self.chooser.connect(
            "selection-changed",
            self.validate_folder,
            ok_btn,
        )

        path = None
        if self.chooser.run() == Gtk.ResponseType.OK:
            path = project.make_path(self.chooser.get_path())
        self.chooser.destroy()
        return path

    # handler
    @staticmethod
    def validate_folder(chooser, btn):
        btn.set_sensitive(project.is_path(chooser.get_path()))
