from gi.repository import Gtk, Gdk, GObject, Pango
from . import locale
from os.path import realpath
from .locale import _

ORIENTATE_HORIZONTAL = Gtk.Orientation.HORIZONTAL
ORIENTATE_VERTICAL = Gtk.Orientation.VERTICAL
ALIGN_START = Gtk.Align.START
ALIGN_END = Gtk.Align.END
RELIEF_NONE = Gtk.ReliefStyle.NONE
ELLIPSIZE_MIDDLE = Pango.EllipsizeMode.MIDDLE
SHADOW_IN = Gtk.ShadowType.IN

FOLDER_22 = "icon/folder-22.png"
WARNING_22 = "icon/warning-22.png"
CAMERA_48 = "icon/camera-48.png"
ERROR_48 = "icon/camera-error-48.png"
IMAGE_48 = "icon/image-48.png"


def is_list(object):
    """ Checks if a object is of type `list`. """

    return type(object) is list


def add_class(widget, *args):
    context = widget.get_style_context()
    if context:
        for name in args:
            context.add_class(name)


def has_class(widget, class_name):
    context = widget.get_style_context()
    if not context:
        return False
    return context.has_class(class_name)


def remove_class(widget, *args):
    context = widget.get_style_context()
    if context:
        for name in args:
            context.remove_class(name)


def show_message_dialog(text, title, icon, *args):
    dialog = Gtk.MessageDialog(
        text=text,
        title=title,
        resizable=False,
        destroy_with_parent=True,
    )
    dialog.set_icon_from_file("icon/" + icon + ".png")
    for i in range(0, len(args), 2):
        dialog.add_button(
            button_text=args[i],
            response_id=args[i + 1]
        )
    response = dialog.run()
    dialog.destroy()
    return response


def ask(text, title):
    return show_message_dialog(
        text, title, "ask",
        _("Yes"), Gtk.ResponseType.YES,
        _("No"), Gtk.ResponseType.NO
    ) == Gtk.ResponseType.YES


def info(text, title):
    show_message_dialog(
        text, title, "info",
        _("Ok"), Gtk.ResponseType.YES,
    )


def warn(text, title):
    show_message_dialog(
        text, title, "warning",
        _("Ok"), Gtk.ResponseType.YES,
    )


class UI:

    def add_class(self, *args):
        add_class(self, *args)

    def has_class(self, class_name):
        has_class(self, class_name)

    def remove_class(self, *args):
        remove_class(self, *args)


def pack_start(parent, children, expand=False, fill=True, padding=0):
    if not is_list(children):
        children = [children]
    for child in children:
        parent.pack_start(child, expand, fill, padding)


def pack_end(parent, children, expand=False, fill=True, padding=0):
    if not is_list(children):
        children = [children]
    for child in children:
        parent.pack_end(child, expand, fill, padding)


class Label(Gtk.Label, UI):
    pass


class Box(Gtk.Box, UI):

    def pack_start(self, children, expand=False, fill=True, padding=0):
        if not is_list(children):
            children = [children]
        for child in children:
            super().pack_start(child, expand, fill, padding)

    def pack_end(self, children, expand=False, fill=True, padding=0):
        if not is_list(children):
            children = [children]
        for child in children:
            super().pack_end(child, expand, fill, padding)

    def set_child_packing(self, child, pack_type=ALIGN_START, expand=False, fill=True, padding=0):
        super().set_child_packing(child, expand, fill, padding, pack_type)


class Button(Gtk.Button, UI):
    pass


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


class Grid(Gtk.Grid, UI):
    pass


class Image(Gtk.Image, UI):
    pass


class Selectbox(Gtk.ComboBox, UI):

    TEXT = 0
    VALUE = 1
    SENSITIVE = 2
    DATA = 3

    __gsignals__ = {
        # syntactic sugar for `notify::active`
        "change": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        GObject.Object.__init__(self)

        # text value sensitive data
        types = [str, str, bool, object]
        self.__model = Gtk.ListStore(*types)
        self.set_model(self.__model)

        cell = Gtk.CellRendererText()
        self.pack_start(cell, False)
        self.add_attribute(cell, "text", self.TEXT)
        self.add_attribute(cell, "sensitive", self.SENSITIVE)
        self.connect("notify::active", self.emit_change_signal)

    def emit_change_signal(self, *args):
        self.emit("change")

    def get_value(self, fallback=None):
        iter = self.get_active_iter()
        if iter is None:
            return fallback
        return self.__model.get_value(iter, self.VALUE)

    def get_data(self, fallback=None):
        iter = self.get_active_iter()
        if iter is None:
            return fallback
        return self.__model.get_value(iter, self.DATA)

    def set_value(self, value):
        value = str(value)
        iter = self.__model.get_iter_first()
        while iter is not None:
            _value = self.__model.get_value(iter, self.VALUE)
            if value == _value:
                self.set_active_iter(iter)
                return True
            iter = self.__model.iter_next(iter)

    def set_sensitive(self, value, sensitive=None):
        if type(value) == bool:
            super().set_sensitive(value)
            return

        if isinstance(value, Gtk.TreeIter):
            self.__model.set_value(value, self.SENSITIVE, bool(sensitive))
            return True

        iter = self.__model.get_iter_first()
        while iter is not None:
            _value = self.__model.get_value(iter, self.VALUE)
            if value == _value:
                self.__model.set_value(iter, self.SENSITIVE, bool(sensitive))
                return True
            iter = self.__model.iter_next(iter)

    def get_sensitive(self, value=None):
        if value is None:
            return super().get_sensitive()

        iter = self.__model.get_iter_first()
        while iter is not None:
            _value = self.__model.get_value(iter, self.VALUE)
            if value == _value:
                return self.__model.get_value(iter, self.SENSITIVE)
            iter = self.__model.iter_next(iter)

    def append(self, text, value=None, sensitive=True, data={}):
        if value is None:
            value = text
        return self.__model.append([str(text), str(value), bool(sensitive), data])

    def clear(self):
        self.__model.clear()

    def update_translation(self):
        iter = self.__model.get_iter_first()
        while iter is not None:
            text = self.__model.get_value(iter, self.TEXT)
            self.__model.set_value(iter, self.TEXT, _(text))
            iter = self.__model.iter_next(iter)


class Radiogroup(GObject.Object):

    __gsignals__ = {
        "change": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, radiobutton):
        GObject.Object.__init__(self)
        self.group = radiobutton.get_group()
        self.current = None
        self.map = {}
        for btn in self.group:
            if btn.get_active():
                self.current = btn
        if self.current:
            for btn in self.group:
                value = btn.get_label()
                self.map[value] = btn
                btn._radio_value = value
                btn.connect("toggled", self.handle_toggle)

    def handle_toggle(self, btn):
        if btn is not self.current:
            self.current = btn
            self.emit("change", btn)

    def get_value(self):
        if not self.current:
            return None
        return self.current._radio_value

    def set_value(self, value):
        if value in self.map:
            self.map[value].set_active(True)


class Window(UI):

    def __init__(self, name, quit=None):
        self._name = name
        self._builder = Gtk.Builder()
        self._builder.add_from_file("glade/" + name + ".glade")
        self._builder.connect_signals(self)

        locale.connect("change", self.update_translation)
        if quit:
            self.root.connect("destroy", quit)

        self.init()

    def destroy(self):
        self.root.destroy()

    def show(self, *args, **kwargs):
        self.update_ui(*args, **kwargs)
        self.root.show()

    def hide(self):
        self.root.hide()
        self.tidy()

    def set_title(self, title):
        self.root.set_title(title)

    # Routes unset instance attribute access to Glade and returns a Gtk object
    def __getattr__(self, id):
        instance = self._builder.get_object(id)
        if not instance:
            raise Exception('Unknown GObject with ID "{}"'.format(id))
        setattr(self, id, instance)
        return instance

    def init(self):
        pass

    def update_translation(self, *args, **kwargs):
        pass

    def update_ui(self, *args, **kwargs):
        pass

    def tidy(self):
        pass

    def result(self):
        return None


class Dialog(Window):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root.set_modal(True)

    def show(self, *args, **kwargs):
        self.update_ui(*args, **kwargs)
        result = None
        response = self.root.run()
        self.root.hide()
        if response == Gtk.ResponseType.OK:
            result = self.result(*args, **kwargs)
        self.tidy()
        return result

    def respond_ok(self, *args):
        self.root.response(Gtk.ResponseType.OK)

    def respond_cancel(self, *args):
        self.root.response(Gtk.ResponseType.CANCEL)
