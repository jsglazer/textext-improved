"""
Bring the TexText dialog to the front on macOS (textext-improved addition).

Inkscape runs the extension as a separate Python process. macOS does not make
that process the active application, so the dialog opens behind Inkscape and
the user has to Cmd-Tab to it. Here we ask AppKit, through ctypes (no PyObjC
needed, no Accessibility/Automation permission), to activate our own process.

Every call is best-effort: on any failure it silently does nothing, and it
never writes to stderr (Inkscape would show that in a popup).
"""

import ctypes
import ctypes.util
import sys

# NSApplicationActivateIgnoringOtherApps = 1 << 1
_ACTIVATE_IGNORING_OTHER_APPS = 2


def _objc():
    path = ctypes.util.find_library("objc")
    if not path:
        return None
    lib = ctypes.cdll.LoadLibrary(path)
    lib.objc_getClass.restype = ctypes.c_void_p
    lib.objc_getClass.argtypes = [ctypes.c_char_p]
    lib.sel_registerName.restype = ctypes.c_void_p
    lib.sel_registerName.argtypes = [ctypes.c_char_p]
    # AppKit must be loaded for NSApplication / NSRunningApplication to exist
    appkit = ctypes.util.find_library("AppKit")
    if appkit:
        ctypes.cdll.LoadLibrary(appkit)
    return lib


def _send(lib, receiver, selector, *args, restype=ctypes.c_void_p, argtypes=()):
    # objc_msgSend must be cast to the exact signature on arm64
    fn_type = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)
    fn = fn_type(ctypes.cast(lib.objc_msgSend, ctypes.c_void_p).value)
    return fn(receiver, lib.sel_registerName(selector), *args)


def activate_current_process():
    """Make this process the frontmost application. Returns True if the calls ran."""
    if sys.platform != "darwin":
        return False
    try:
        lib = _objc()
        if lib is None:
            return False
        # [[NSRunningApplication currentApplication] activateWithOptions:IgnoringOtherApps]
        running_cls = lib.objc_getClass(b"NSRunningApplication")
        if running_cls:
            current = _send(lib, running_cls, b"currentApplication")
            if current:
                _send(lib, current, b"activateWithOptions:", _ACTIVATE_IGNORING_OTHER_APPS,
                      restype=ctypes.c_bool, argtypes=(ctypes.c_ulong,))
        # [[NSApplication sharedApplication] activateIgnoringOtherApps:YES]
        app_cls = lib.objc_getClass(b"NSApplication")
        if app_cls:
            app = _send(lib, app_cls, b"sharedApplication")
            if app:
                _send(lib, app, b"activateIgnoringOtherApps:", True,
                      restype=None, argtypes=(ctypes.c_bool,))
        return True
    except Exception:
        return False
