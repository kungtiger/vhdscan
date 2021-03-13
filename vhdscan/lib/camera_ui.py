from gi.repository import Gtk
from . import setup, camera, locale, udev, ui
from .locale import _


class Control:
    pass


class Camera_UI(ui.Dialog):
    def init(self):
        self.camera = None
        self.controls = []
        self._is_init = False
        self._ready_camera_id = None

        self.control_creator = {
            camera.CONTROL_INT: self.create_control_int,
            camera.CONTROL_BOOL: self.create_control_bool,
            camera.CONTROL_MENU: self.create_control_menu,
        }

        self.main_box = ui.Box(
            orientation=ui.ORIENTATE_VERTICAL,
            spacing=0,
        )
        self.main_scroll.add(self.main_box)

        self.device_label = ui.Label(halign=ui.ALIGN_START)
        self.device_select = ui.Selectbox()
        self.device_select.connect("change", self.camera_device_selected)
        self.device_box = ui.Box(orientation=ui.ORIENTATE_VERTICAL, spacing=4)
        self.device_box.pack_start([self.device_label, self.device_select])
        self.device_box.add_class("vhd-control")
        self.main_box.pack_start(self.device_box)

        self.resolution_label = ui.Label(halign=ui.ALIGN_START)
        self.resolution_select = ui.Selectbox()
        self.resolution_select.connect("change", self.resolution_selected)
        self.resolution_box = ui.Box(orientation=ui.ORIENTATE_VERTICAL, spacing=4)
        self.resolution_box.pack_start([self.resolution_label, self.resolution_select])
        self.resolution_box.add_class("vhd-control")
        self.main_box.pack_start(self.resolution_box)
        self.main_box.show_all()

    def update_ui(self, cam):
        self._is_init = True
        self.camera = cam
        self._ready_camera_id = cam.connect("ready", self.update_selectbox_ui)
        self.update_title()

        # clear and hide all
        self.device_box.set_sensitive(False)
        self.device_select.clear()
        self.resolution_box.set_sensitive(False)
        self.resolution_select.clear()
        self.destroy_controls()

        if len(udev.devices) == 0:
            self.add_message_box(_("There are no cameras connected."))
        else:
            self.fill_device_select()
        self._is_init = False

    def fill_device_select(self):
        selected = False
        current_name = self.camera.get_device_name()
        self.device_box.set_sensitive(True)
        self.device_select.append(_("No Camera"), "")
        for device in udev.devices:
            iter = self.device_select.append(
                text=self.get_device_name(device),
                value=device.name,
            )
            is_current = device.name == current_name
            if device.in_use and not is_current:
                self.device_select.set_sensitive(iter, False)
            if is_current:
                self.device_select.set_active_iter(iter)
                selected = True

        if not selected:
            self.device_select.set_active(0)

    @staticmethod
    def get_device_name(device):
        model = device.model
        if not model:
            model = _("Unknown Model")
        return "{0} ({1})".format(model, device.name)

    # handle: camera::ready
    def update_selectbox_ui(self, cam):
        self.device_box.set_sensitive(True)
        self.fill_resolution_select()

    # handle: device_select::change
    def camera_device_selected(self, *args):
        if not self._is_init:
            # the user selected a device; is reverted in `camera::ready`
            self.device_box.set_sensitive(False)
        self.resolution_select.clear()
        self.resolution_box.set_sensitive(False)
        self.destroy_controls()

        if self._is_init:
            # we update the ui, simply fill the resolution selectbox
            self.fill_resolution_select()
        else:
            # the user selected a device; set it, wait for `camera::ready`
            selected_device_name = self.device_select.get_value()
            self.camera.set_device_by_name(selected_device_name)

    def fill_resolution_select(self):
        if len(self.camera.resolutions) == 0:
            self.resolution_box.set_sensitive(False)
            return

        self.resolution_box.set_sensitive(True)
        for resolution_value in self.camera.resolutions:
            resolution = self.camera.resolutions[resolution_value]
            self.resolution_select.append(
                text=resolution.name,
                value=resolution.value,
            )

        current_resolution = self.camera.resolution
        self.resolution_select.set_value(current_resolution.value)

    # handle: resolution_select::change
    def resolution_selected(self, *args):
        if not self._is_init:
            # the user selected a resolution, set it, wait for `camera::ready`
            selected_resolution = self.resolution_select.get_value()
            self.camera.set_resolution(selected_resolution)
        self.create_controls()

    def create_controls(self):
        self.destroy_controls()
        for name in self.camera.controls:
            control = self.camera.controls[name]
            struct = self.create_control_struct(control)
            self.controls.append(struct)
            self.camera.update_sensitivity()

    def create_control_struct(self, control):
        struct = {}
        label = ui.Label(halign=ui.ALIGN_START)
        label.set_label(_(control.name))

        box = ui.Box(orientation=ui.ORIENTATE_VERTICAL, spacing=4)
        box.pack_start(label)
        box.add_class("vhd-control")

        creator = self.control_creator[control.type]
        struct["label"] = label
        struct["box"] = box
        struct["inputs"] = creator(control, box)

        control.struct = struct
        self.main_box.pack_start(box)
        box.show_all()
        return struct

    def create_control_int(self, control, box):
        adjustment = Gtk.Adjustment(
            value=control.value,
            lower=control.min,
            upper=control.max,
            step_increment=control.step,
            page_increment=5,
            page_size=0,
        )
        adjustment.connect("value-changed", self.control_int_changed, control.name)
        scale = ui.Scale(
            orientation=ui.ORIENTATE_HORIZONTAL,
            adjustment=adjustment,
            digits=0,
            draw_value=False,
            value_pos=Gtk.PositionType.RIGHT,
        )
        scale.add_mark(
            value=control.default,
            position=Gtk.PositionType.BOTTOM,
            markup=str(control.default),
        )
        scale.add_mark(
            value=control.min,
            position=Gtk.PositionType.TOP,
            markup=str(control.min),
        )
        scale.add_mark(
            value=control.max,
            position=Gtk.PositionType.TOP,
            markup=str(control.max),
        )
        spinbox = ui.SpinButton(
            adjustment=adjustment,
            digits=0,
            climb_rate=0,
            halign=Gtk.Align.END,
            valign=Gtk.Align.CENTER,
        )
        inner_box = ui.Box(
            orientation=ui.ORIENTATE_HORIZONTAL,
            spacing=8,
        )
        inner_box.pack_start(scale, expand=True)
        inner_box.pack_start(spinbox)
        box.pack_start(inner_box, expand=True)
        return [scale, spinbox]

    def create_control_bool(self, control, box):
        switch = ui.Switch(
            halign=Gtk.Align.START,
            hexpand=False,
            vexpand=False,
            active=control.value == 1,
        )
        switch.connect("notify::active", self.control_bool_changed, control.name)
        box.pack_start(switch)
        return [switch]

    def create_control_menu(self, control, box):
        selectbox = ui.Selectbox()
        list = selectbox.get_model()
        i = 0
        for text, value in control.values:
            selectbox.append(text, value)
            if int(value) == self.value:
                selectbox.set_active(i)
            i += 1
        selectbox.connect("change", self.control_menu_changed, control.name)
        box.pack_start(selectbox, expand=True)
        return [selectbox]

    # control-hander: adjustment::value-changed
    def control_int_changed(self, adjustment, name):
        i = int(adjustment.get_value())
        self.camera.set_control(name, i)

    # control-hander: switch::value-changed
    def control_bool_changed(self, switch, state, name):
        state = 1 if switch.get_active() else 0
        self.camera.set_control(name, state)
        self.camera.update_sensitivity(self)

    # control-hander: selectbox::value-changed
    def control_menu_changed(self, selectbox, name):
        value = selectbox.get_value()
        self.camera.set_control(name, value)
        self.camera.update_sensitivity(self)

    def destroy_controls(self):
        for control in self.controls:
            control.box.destroy()
        self.controls = []

    def add_message_box(self, message):
        box = ui.Box()
        box.add(ui.Label(label=message))
        box.show_all()
        self.main_box.pack_start(box)
        self.control_boxes.append(box)

    def update_translation(self, *args):
        self.update_title()
        self.device_label.set_label(_("Camera Device"))
        self.resolution_label.set_label(_("Image Resolution"))
        self.cancel_btn.set_label(_("Cancel"))
        self.ok_btn.set_label(_("Save"))
        for control in self.controls:
            control.set_label(_(control.name))

    def update_title(self):
        if self.camera:
            if self.camera.slot == camera.LEFT:
                title = _("Setup Left Camera")
            else:
                title = _("Setup Right Camera")
        else:
            title = _("Setup Camera")
        self.set_title(title)

    def result(self, *args):
        self.camera.disconnect(self._ready_camera_id)
        self._ready_camera_id = None
        return self.camera.get_setup()
