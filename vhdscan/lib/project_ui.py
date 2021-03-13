from gi.repository import Gtk, GdkPixbuf
from os.path import basename
from .locale import _
from . import application, project, ui


def get_image_formats():
    """ Returns available image formats for `GdkPixbuf`. """

    formats = []
    for format in GdkPixbuf.Pixbuf.get_formats():
        name = format.get_name()
        if name in project.FORMATS and format.is_writable():
            formats.append({
                "text": format.get_description(),
                "value": name,
            })
    return formats


class Project_UI(ui.Dialog):

    def init(self):
        self.project = None

        ui.add_class(self.basename_label, "vhd-label")
        ui.add_class(self.path_status, "vhd-status")

        self.total_pages_adjustment = Gtk.Adjustment(
            value=1,
            upper=10000,
            lower=1,
            step_increment=1,
            page_increment=10,
            page_size=0,
        )
        self.total_pages_input.set_adjustment(self.total_pages_adjustment)

        self.image_format_select = ui.Selectbox()
        for format in get_image_formats():
            self.image_format_select.append(**format)
        self.image_format_box.add(self.image_format_select)
        self.image_format_select.connect("notify::active", self.toggle_image_format_options)

        self.jpeg_quality_adjustment = Gtk.Adjustment(
            value=project.DEFAULT_JPEG_QUALITY,
            lower=0,
            upper=100,
            step_increment=1,
            page_increment=10,
            page_size=0,
        )
        self.jpeg_quality_input.set_adjustment(self.jpeg_quality_adjustment)

        self.png_compression_adjustment = Gtk.Adjustment(
            value=project.DEFAULT_PNG_COMPRESSION,
            lower=0,
            upper=9,
            step_increment=1,
            page_increment=5,
            page_size=0,
        )
        self.png_compression_input.set_adjustment(self.png_compression_adjustment)

        self.tiff_compression_select = ui.Selectbox()
        for compression in project.TIFF_COMPRESSIONS:
            self.tiff_compression_select.append(*compression)
        self.tiff_box.add(self.tiff_compression_select)
        self.tiff_compression_select.set_value(project.DEFAULT_TIFF_COMPRESSION)

        self.duplicate_radiogroup = ui.Radiogroup(self.duplicate_overwrite_radio)

        self.fps_select = ui.Selectbox()
        for n in project.FPS:
            self.fps_select.append(n)
        self.fps_box.add(self.fps_select)

        self.path_btn.connect("clicked", self.choose_path)

        self.form_box.show_all()

    def update_ui(self, show_project=None):
        self.project = show_project
        self.update_translation()
        if self.project:
            self.path_box.hide()
            self.ok_btn.set_sensitive(True)
            self.name_input.set_text(self.project.get_name())
            self.total_pages_input.set_value(self.project.total_pages)
            self.image_format_select.set_value(self.project.format)
            self.jpeg_quality_input.set_value(self.project.jpeg_quality)
            self.png_compression_input.set_value(self.project.png_compression)
            self.tiff_compression_select.set_value(self.project.tiff_compression)
            self.duplicate_radiogroup.set_value(self.project.duplicate_handle)
            self.fps_select.set_value(self.project.fps)

        else:
            self.path_box.show()
            self.chooser = ui.FileChooserDialog(
                title=_("Select Project Folder"),
                action=Gtk.FileChooserAction.SELECT_FOLDER,
                local_only=False,
                modal=True,
                create_folders=True,
            )
            self.chooser.set_icon_from_file(ui.FOLDER_22)
            self.chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            self.chooser.add_button(_("Choose"), Gtk.ResponseType.OK)

            self.name_input.set_text("")
            self.image_format_select.set_active(0)
            self.total_pages_input.set_value(1)
            self.jpeg_quality_input.set_value(project.DEFAULT_JPEG_QUALITY)
            self.png_compression_input.set_value(project.DEFAULT_PNG_COMPRESSION)
            self.tiff_compression_select.set_value(project.DEFAULT_TIFF_COMPRESSION)
            self.duplicate_radiogroup.set_value(project.DEFAULT_DUPLICATE_HANDLE)
            self.fps_select.set_value(project.DEFAULT_FPS)
            self.ok_btn.set_sensitive(False)

        self.toggle_image_format_options()
        self.reset_path_ui()

    # handler
    def toggle_image_format_options(self, *args):
        format = self.image_format_select.get_value()
        self.jpeg_box.hide()
        self.tiff_box.hide()
        self.png_box.hide()
        if format == project.FORMAT_JPEG:
            self.jpeg_box.show()
        elif format == project.FORMAT_PNG:
            self.png_box.show()
        elif format == project.FORMAT_TIFF:
            self.tiff_box.show()

    def update_translation(self, *args):
        if self.project:
            self.set_title(_("Edit Project"))
            self.ok_btn.set_label(_("Save"))
        else:
            self.set_title(_("Create New Project"))
            self.ok_btn.set_label(_("Create"))

        self.name_label.set_label(_("Book Title"))
        self.name_input.set_placeholder_text(_("Unnamed Book"))
        self.path_label.set_label(_("Project Folder"))
        self.total_pages_label.set_label(_("How many pages does the book have?"))
        self.image_format_label.set_label(_("Image Format"))
        self.jpeg_quality_label.set_label(_("JPEG Quality"))
        self.png_compression_label.set_label(_("PNG Compression"))
        self.tiff_compression_label.set_label(_("TIFF Compression"))
        self.cancel_btn.set_label(_("Cancel"))
        self.duplicate_label.set_label(_("How to handle existing photos"))
        self.duplicate_overwrite_radio.set_label(_("Overwrite"))
        self.duplicate_ask_radio.set_label(_("Ask"))
        self.duplicate_suffix_radio.set_label(_("Append increasing number"))
        self.fps_label.set_label(_("FPS"))

        self.tiff_compression_select.update_translation()

    def result(self, *args):
        data = {
            "name": self.name_input.get_text(),
            "format": self.image_format_select.get_value(),
            "total-pages": int(self.total_pages_adjustment.get_value()),
            "jpeg-quality": int(self.jpeg_quality_input.get_value()),
            "png-compression": int(self.png_compression_input.get_value()),
            "tiff-compression": self.tiff_compression_select.get_value(),
            "duplicate-handle": self.duplicate_radiogroup.get_value(),
            "fps": int(self.fps_select.get_value()),
        }
        if self.project:
            return data

        return {
            "path": project.make_path(self.chooser.get_path()),
            "data": data
        }

    def reset_path_ui(self):
        self.path_status.hide()
        self.basename_icon.set_from_file(ui.WARNING_22)
        self.basename_label.set_label(_("No project folder selected"))
        ui.add_class(self.path_box, "vhd-invalid")

    # handler
    def choose_path(self, *args):
        response = self.chooser.run()
        self.chooser.hide()
        if response == Gtk.ResponseType.OK:
            self.ok_btn.set_sensitive(self.check_path())

    def check_path(self):
        path = self.chooser.get_path()
        if not path:
            self.reset_path_ui()
            return False

        self.basename_label.set_label(basename(path))

        if project.is_path(path):
            self.basename_icon.set_from_file(ui.WARNING_22)
            ui.add_class(self.path_box, "vhd-invalid")
            self.path_status.show()
            self.path_status.set_label(_("There is already a project inside this folder.\nPlease choose another."))
            return False

        if not project.is_empty_path(path):
            self.basename_icon.set_from_file(ui.WARNING_22)
            ui.add_class(self.path_box, "vhd-invalid")
            self.path_status.show()
            self.path_status.set_label(_("This folder is not empty.\nPlease choose another."))
            return False

        ui.remove_class(self.path_box, "vhd-invalid")
        self.basename_icon.set_from_file(ui.FOLDER_22)
        self.basename_label.set_tooltip_text(path)
        self.path_status.hide()
        return True
