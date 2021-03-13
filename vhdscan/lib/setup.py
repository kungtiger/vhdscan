
class Setup:

    def __init__(self):
        self.id = ""
        self.udev_name = ""
        self.resolution = ""
        self.controls = {}

    def save(self):
        return {
            "id": self.id,
            "udev_name": self.udev_name,
            "resolution": self.resolution,
            "controls": self.controls,
        }

    def __eq__(self, other):
        if not isinstance(other, Setup):
            return False
        if self.id != other.id:
            return False
        if self.udev_name != other.udev_name:
            return False
        if self.resolution != other.resolution:
            return False
        for name in self.controls:
            if name not in other.controls:
                return False
            if self.controls[name] != other.controls[name]:
                return False
        return True

    def __neq__(self, other):
        return not self.__eq__(other)


def new_from_camera(camera):
    setup = Setup()
    device = camera.device
    if device:
        setup.id = device.id
        setup.udev_name = device.name
    if camera.resolution:
        setup.resolution = camera.resolution.value
    for name in camera.controls:
        setup.controls[name] = camera.controls[name].value
    return setup


def new_from_data(data):
    setup = Setup()
    setup.id = data.get("id", "")
    setup.resolution = data.get("resolution", "")
    setup.udev_name = data.get("udev_name", "")
    setup.controls = data.get("controls", {})
    return setup
