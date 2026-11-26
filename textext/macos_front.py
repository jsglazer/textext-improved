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


# ---------------------------------------------------------------------------
# Locating Inkscape's window, so the dialog opens on top of it (and on the same
# monitor) instead of wherever the window manager puts a new process's window.
# Uses CGWindowListCopyWindowInfo, whose bounds/owner fields need no Screen
# Recording permission.

class _CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class _CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]


class _CGRect(ctypes.Structure):
    _fields_ = [("origin", _CGPoint), ("size", _CGSize)]


_ON_SCREEN_ONLY = 1          # kCGWindowListOptionOnScreenOnly
_EXCLUDE_DESKTOP = 16        # kCGWindowListExcludeDesktopElements
_CF_NUMBER_SINT64 = 4        # kCFNumberSInt64Type
_CF_UTF8 = 0x08000100        # kCFStringEncodingUTF8


def _frameworks():
    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
    cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    cg.CGRectMakeWithDictionaryRepresentation.restype = ctypes.c_bool
    cg.CGRectMakeWithDictionaryRepresentation.argtypes = [ctypes.c_void_p, ctypes.POINTER(_CGRect)]
    cg.CGGetActiveDisplayList.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
                                          ctypes.POINTER(ctypes.c_uint32)]
    cg.CGDisplayBounds.restype = _CGRect
    cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    cf.CFDictionaryGetValue.restype = ctypes.c_void_p
    cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringGetCString.restype = ctypes.c_bool
    cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    return cg, cf


def _display_origin(cg):
    """Top-left corner of the union of all displays, in CoreGraphics coordinates."""
    ids = (ctypes.c_uint32 * 16)()
    count = ctypes.c_uint32()
    if cg.CGGetActiveDisplayList(16, ids, ctypes.byref(count)) != 0 or count.value == 0:
        return 0.0, 0.0
    bounds = [cg.CGDisplayBounds(ids[i]) for i in range(count.value)]
    return min(b.origin.x for b in bounds), min(b.origin.y for b in bounds)


def find_window_bounds(pids=(), owner_substring="inkscape", min_size=300):
    """
    Bounds of the frontmost on-screen normal window owned by one of `pids`, or
    failing that by an app whose name contains `owner_substring`.

    :return: dict with "cg" = (x, y, w, h) in CoreGraphics global points (origin at the
             top-left of the main display, as Tk uses) and "gdk" = the same rectangle in
             GDK's coordinates (origin at the top-left of all displays), or None.
    """
    if sys.platform != "darwin":
        return None
    try:
        cg, cf = _frameworks()
        keys = {}
        for name in ("kCGWindowOwnerPID", "kCGWindowOwnerName", "kCGWindowLayer", "kCGWindowBounds"):
            keys[name] = cf.CFStringCreateWithCString(None, name.encode(), _CF_UTF8)
        windows = cg.CGWindowListCopyWindowInfo(_ON_SCREEN_ONLY | _EXCLUDE_DESKTOP, 0)
        if not windows:
            return None
        try:
            by_pid, by_name = None, None
            for i in range(cf.CFArrayGetCount(windows)):  # front-to-back order
                info = cf.CFArrayGetValueAtIndex(windows, i)

                def number(key):
                    value = cf.CFDictionaryGetValue(info, keys[key])
                    out = ctypes.c_int64(0)
                    if value:
                        cf.CFNumberGetValue(value, _CF_NUMBER_SINT64, ctypes.byref(out))
                    return out.value

                if number("kCGWindowLayer") != 0:
                    continue
                rect = _CGRect()
                bounds_dict = cf.CFDictionaryGetValue(info, keys["kCGWindowBounds"])
                if not bounds_dict or not cg.CGRectMakeWithDictionaryRepresentation(bounds_dict, ctypes.byref(rect)):
                    continue
                if rect.size.width < min_size or rect.size.height < min_size:
                    continue
                box = (rect.origin.x, rect.origin.y, rect.size.width, rect.size.height)
                if by_pid is None and number("kCGWindowOwnerPID") in pids:
                    by_pid = box
                    break
                if by_name is None:
                    name_ref = cf.CFDictionaryGetValue(info, keys["kCGWindowOwnerName"])
                    buf = ctypes.create_string_buffer(256)
                    if name_ref and cf.CFStringGetCString(name_ref, buf, 256, _CF_UTF8) \
                            and owner_substring.lower() in buf.value.decode("utf-8", "replace").lower():
                        by_name = box
            box = by_pid or by_name
        finally:
            cf.CFRelease(windows)
            for ref in keys.values():
                cf.CFRelease(ref)
        if box is None:
            return None
        ox, oy = _display_origin(cg)
        x, y, w, h = box
        return {"cg": box, "gdk": (x - ox, y - oy, w, h)}
    except Exception:
        return None


def centered_position(target, size, area):
    """
    Top-left position that centres a window of `size` (w, h) on `target` (x, y, w, h),
    kept inside `area` (x, y, w, h) -- the work area of the monitor under the target.
    Pure arithmetic, unit-tested.
    """
    tx, ty, tw, th = target
    w, h = size
    ax, ay, aw, ah = area
    x = tx + (tw - w) / 2.0
    y = ty + (th - h) / 2.0
    x = max(ax, min(x, ax + aw - w))
    y = max(ay, min(y, ay + ah - h))
    return int(round(x)), int(round(y))
