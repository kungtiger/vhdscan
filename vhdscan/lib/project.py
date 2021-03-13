import unicodedata
from gi.repository import GObject
from os import listdir as ls
from os.path import isdir as is_dir, isfile as is_file, dirname as dirname
from os.path import basename, join as join_path
from . import json, setup

FILE_NAME = "project.vhdscan"

DUPLICATE_ASK = "ask"
DUPLICATE_SUFFIX = "suffix"
DUPLICATE_OVERWRITE = "overwrite"

FORMAT_PNG = "png"
FORMAT_JPEG = "jpeg"
FORMAT_TIFF = "tiff"
FORMATS = [FORMAT_JPEG, FORMAT_PNG, FORMAT_TIFF]

TIFF_COMPRESSION_RAW = "1"
TIFF_COMPRESSION_HUFFMAN = "2"
TIFF_COMPRESSION_LZW = "5"
TIFF_COMPRESSION_JPEG = "7"
TIFF_COMPRESSION_ZLIB = "8"

TIFF_COMPRESSIONS = [
    ("Raw (lossless)", TIFF_COMPRESSION_RAW),
    ("Huffman (lossless)", TIFF_COMPRESSION_HUFFMAN),
    ("Lempel-Ziv-Welch (lossless)", TIFF_COMPRESSION_LZW),
    ("JPEG (lossy)", TIFF_COMPRESSION_JPEG),
    ("zlib (lossless)", TIFF_COMPRESSION_ZLIB),
]

FPS = [1, 5, 10, 15, 20, 25, 30]

DEFAULT_FORMAT = FORMAT_JPEG
DEFAULT_JPEG_QUALITY = 80
DEFAULT_PNG_COMPRESSION = 7
DEFAULT_TIFF_COMPRESSION = TIFF_COMPRESSION_LZW
DEFAULT_DUPLICATE_HANDLE = DUPLICATE_OVERWRITE
DEFAULT_FPS = FPS[3]

E_CREATE_FILE_EXISTS = -1
E_OPEN_EMPTY_PATH = -2
E_OPEN_NOT_FOUND = -3
E_OPEN_UNUSABLE = -4


def make_path(path):
    """ Returns a path that ends in `project.vhdscan`. """

    if not path:
        return None
    if basename(path) == FILE_NAME:
        return path
    return join_path(path, FILE_NAME)


def is_path(path):
    """ Checks if a path exists. """

    if not path:
        return False
    path = make_path(path)
    return is_file(path)


def is_empty_path(path):
    """ Checks if a path is empty """

    return is_dir(path) and not ls(path)


def sanitize_filename(filename):
    """ Strips invalid characters from a string. """

    blacklist = ["\\", "/", ":", "*", "?", "\"", "<", ">", "|", "\0"]
    reserved = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9",
    ]  # Reserved words on Windows
    filename = "".join(c for c in filename if c not in blacklist)
    # Remove all charcters below code point 32
    filename = "".join(c for c in filename if 31 < ord(c))
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.rstrip(". ")  # Windows does not allow these at end
    filename = filename.strip()
    if all([x == "." for x in filename]):
        filename = "__" + filename
    if filename in reserved:
        filename = "__" + filename
    if len(filename) == 0:
        filename = "__"
    if len(filename) > 255:
        parts = re.split(r"/|\\", filename)[-1].split(".")
        if len(parts) > 1:
            ext = "." + parts.pop()
            filename = filename[:-len(ext)]
        else:
            ext = ""
        if filename == "":
            filename = "__"
        if len(ext) > 254:
            ext = ext[254:]
        maxl = 255 - len(ext)
        filename = filename[:maxl]
        filename = filename + ext
        # Re-check last character (if there was no extension)
        filename = filename.rstrip(". ")
        if len(filename) == 0:
            filename = "__"
    return filename


class Project(GObject.Object):

    __gsignals__ = {
        "error": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)

        self.path = None
        self.dirname = None
        self.name = ""
        self.current_page = None
        self.total_pages = None
        self.format = None
        self.jpeg_quality = None
        self.png_compression = None
        self.tiff_compression = None
        self.duplicate_handle = None
        self.fps = None
        self.setup_1 = None
        self.setup_2 = None
        self.zoom_level = 100
        self.zoom_mode = None

    def create(self, path, data):
        path = make_path(path)
        if is_file(path):
            self.emit("error", E_CREATE_FILE_EXISTS)
            return False

        self.current_page = 1
        self.path = path
        self.dirname = dirname(path)
        self.set(data)
        return self.save()

    def open(self, path):
        if not path:
            self.emit("error", E_OPEN_EMPTY_PATH)
            return False

        path = make_path(path)

        if not is_file(path):
            self.emit("error", E_OPEN_NOT_FOUND)
            return False

        data = json.read(path)
        if not isinstance(data, dict):
            self.emit("error", E_OPEN_UNUSABLE)
            return False

        self.path = path
        self.dirname = dirname(path)
        self.name = data.get("name", "")
        self.current_page = int(data.get("current-page", 1))
        self.total_pages = int(data.get("total-pages", 1))
        self.format = data.get("format", DEFAULT_FORMAT)
        self.jpeg_quality = data.get("jpeg-quality", DEFAULT_JPEG_QUALITY)
        self.png_compression = data.get("png-compression", DEFAULT_PNG_COMPRESSION)
        self.tiff_compression = str(data.get("tiff-compression", DEFAULT_TIFF_COMPRESSION))
        self.duplicate_handle = data.get("duplicate-handle", DEFAULT_DUPLICATE_HANDLE)
        self.fps = data.get("fps", DEFAULT_FPS)

        self.setup_1 = setup.new_from_data(data.get("camera-1", {}))
        self.setup_2 = setup.new_from_data(data.get("camera-2", {}))

        self.zoom_level = data.get("zoom-level", None)
        self.zoom_mode = data.get("zoom-mode", None)

        return True

    def update(self, data):
        self.set(data)
        self.current_page = min(self.current_page, self.total_pages)
        return self.save()

    def set(self, data):
        self.name = data["name"].strip()
        self.total_pages = data["total-pages"]
        self.format = data["format"]
        self.jpeg_quality = data["jpeg-quality"]
        self.png_compression = data["png-compression"]
        self.tiff_compression = data["tiff-compression"]
        self.fps = data["fps"]
        self.duplicate_handle = data["duplicate-handle"]

    def save(self):
        if not self.path:
            return False

        json.write(self.path, {
            "name": self.name,
            "format": self.format,
            "jpeg-quality": self.jpeg_quality,
            "png-compression": self.png_compression,
            "tiff-compression": int(self.tiff_compression),
            "current-page": self.current_page,
            "total-pages": self.total_pages,
            "duplicate-handle": self.duplicate_handle,
            "fps": self.fps,
            "zoom-level": self.zoom_level,
            "zoom-mode": self.zoom_mode,
            "camera-1": self.setup_1.save(),
            "camera-2": self.setup_2.save(),
        })
        return True

    def get_name(self):
        if not self.path or not self.name:
            return ""
        return self.name

    def get_current_image_filename(self):
        # TODO: custom filename patterns

        n = len(str(self.pages))
        page = str(self.page).zfill(n)

        # 0 ext | 1 name | 2 page
        pattern = '{1}_{0}'
        basename = pattern.format(
            sanitize_filename(self.name),
            page
        )
        filename = basename + '.' + self.format
        path = join_path(self.dirname, filename)
        return {
            "path": path,
            "dirname": self.dirname,
            "filename": filename,
            "basename": basename,
            "format": self.format
        }
