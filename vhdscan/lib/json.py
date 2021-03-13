import json


def read(path):
    """ Opens a `JSON` file and returns it as a python object. """

    try:
        with open(path) as file:
            return json.load(file)
    except:
        return None
    return None


def write(path, data):
    """ Saves a python object to a file in `JSON` format. """

    with open(path, "w") as file:
        json.dump(data, file, indent=2)
