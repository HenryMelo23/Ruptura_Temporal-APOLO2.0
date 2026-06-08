import os
import sys


def _candidate_roots():
    roots = []
    for value in (
        getattr(sys, "_MEIPASS", None),
        os.path.dirname(sys.executable),
        os.getcwd(),
    ):
        if value and value not in roots:
            roots.append(value)
    for root in list(roots):
        internal = os.path.join(root, "_internal")
        if os.path.isdir(internal) and internal not in roots:
            roots.append(internal)
    return roots


def _configure_vlc_paths():
    if not sys.platform.startswith("win"):
        return
    if os.environ.get("PYTHON_VLC_LIB_PATH") and os.environ.get("PYTHON_VLC_MODULE_PATH"):
        return
    for root in _candidate_roots():
        dll_path = os.path.join(root, "libvlc.dll")
        plugin_path = os.path.join(root, "plugins")
        if not os.path.exists(dll_path):
            continue
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", dll_path)
        if os.path.isdir(plugin_path):
            os.environ.setdefault("PYTHON_VLC_MODULE_PATH", plugin_path)
        try:
            os.add_dll_directory(root)
        except (AttributeError, FileNotFoundError, OSError):
            pass
        break


_configure_vlc_paths()
