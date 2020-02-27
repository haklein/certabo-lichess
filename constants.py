import os
import platform
import appdirs


ENGINE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "engines")
BOOK_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "books")
BASE_PORT = 3102

if platform.system() == "Windows":
    import ctypes.wintypes

    CSIDL_PERSONAL = 5  # My Documents
    SHGFP_TYPE_CURRENT = 0  # Get current, not default value

    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(
        None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf
    )

    MY_DOCUMENTS = buf.value
else:
    MY_DOCUMENTS = os.path.expanduser("~/Documents")


CERTABO_SAVE_PATH = os.path.join(MY_DOCUMENTS, "Certabo Saved Games")
CERTABO_DATA_PATH = appdirs.user_data_dir("GUI", "Certabo")

MAX_DEPTH_DEFAULT = 20

if __name__ == "__main__":
    print("ENGINE_PATH", ENGINE_PATH)
    print("MY_DOCUMENTS", MY_DOCUMENTS)
    print("CERTABO_DATA_PATH", CERTABO_DATA_PATH)
    print("CERTABO_SAVE_PATH", CERTABO_SAVE_PATH)
