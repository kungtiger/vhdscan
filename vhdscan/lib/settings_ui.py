from .ui import Dialog, Radiogroup, Selectbox, pack_start
from .locale import _
from . import locale, settings


class Settings_UI(Dialog):

    def init(self):
        self.locale_select = Selectbox()
        self.locale_select.show()
        pack_start(self.locale_box, self.locale_select)

        self.startup_radiogroup = Radiogroup(self.startup_nothing_radio)

    def update_translation(self, *args):
        self.set_title(_("Settings"))
        self.startup_label.set_label(_("Program start"))
        self.startup_nothing_radio.set_label(_("Do nothing"))
        self.startup_last_radio.set_label(_("Open last project"))
        self.cancel_btn.set_label(_("Cancel"))
        self.save_btn.set_label(_("Save"))
        self.locale_label.set_label(_("Language"))

    def update_ui(self):
        self.startup_radiogroup.set_value(settings.get("on-startup"))

        current_iso = settings.get("locale")
        self.locale_select.clear()
        for iso, name in locale.get_all():
            iter = self.locale_select.append(name, iso)
            if current_iso and iso == current_iso:
                self.locale_select.set_active_iter(iter)
        if not current_iso:
            self.locale_select.set_value("en")

    def result(self):
        iso_key = self.locale_select.get_value()
        settings.update({
            "locale": iso_key,
            "on-startup": self.startup_radiogroup.get_value(),
        })
        locale.load(iso_key)
        return True
