#!/usr/bin/env python3
"""Read Lightroom's X11 image without changing focus; report sampled luminance."""
import ctypes as c
import hashlib
import json
import statistics
import sys
import time


class XImage(c.Structure):
    _fields_ = [(n, c.c_int) for n in ('width', 'height', 'xoffset', 'format')]
    _fields_ += [('data', c.c_void_p)]
    _fields_ += [(n, c.c_int) for n in ('byte_order', 'bitmap_unit', 'bitmap_bit_order',
                                      'bitmap_pad', 'depth', 'bytes_per_line', 'bits_per_pixel')]


x = c.CDLL('libX11.so.6')
x.XOpenDisplay.argtypes = [c.c_char_p]
x.XOpenDisplay.restype = c.c_void_p
x.XDefaultRootWindow.argtypes = [c.c_void_p]
x.XDefaultRootWindow.restype = c.c_ulong
x.XQueryTree.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_ulong),
                        c.POINTER(c.POINTER(c.c_ulong)), c.POINTER(c.c_uint)]
x.XFetchName.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_char_p)]
x.XGetImage.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_int, c.c_uint,
                       c.c_uint, c.c_ulong, c.c_int]
x.XGetImage.restype = c.POINTER(XImage)
x.XDestroyImage.argtypes = [c.POINTER(XImage)]
x.XFree.argtypes = [c.c_void_p]
x.XCloseDisplay.argtypes = [c.c_void_p]
display = x.XOpenDisplay(None)
if not display:
    raise SystemExit('X11 display unavailable')
windows = []


def walk(window, depth=0):
    name = c.c_char_p()
    x.XFetchName(display, window, c.byref(name))
    if name.value == b'Lightroom':
        windows.append(window)
    if name:
        x.XFree(name)
    if depth > 3:
        return
    root, parent, count = c.c_ulong(), c.c_ulong(), c.c_uint()
    children = c.POINTER(c.c_ulong)()
    if x.XQueryTree(display, window, c.byref(root), c.byref(parent), c.byref(children), c.byref(count)):
        for i in range(count.value):
            walk(children[i], depth + 1)
        if children:
            x.XFree(children)


walk(x.XDefaultRootWindow(display))
if len(windows) != 1:
    raise SystemExit(f'Expected exactly one Lightroom window, found {len(windows)}')
# A fixed photo-only region at 2x; never capture or expose the rest of the desktop.
frames = []
started = time.monotonic()
duration = float(sys.argv[1]) if len(sys.argv) > 1 else 8
while time.monotonic() - started < duration:
    stamp = time.monotonic()
    img = x.XGetImage(display, windows[0], 400, 200, 1200, 900, c.c_ulong(-1), 2)
    if not img:
        raise SystemExit('XGetImage failed')
    info = img.contents
    if info.bits_per_pixel != 32:
        x.XDestroyImage(img)
        raise SystemExit('Expected 32-bit X11 image')
    data = (c.c_ubyte * (info.bytes_per_line * info.height)).from_address(info.data)
    pixels = bytes(data[row * info.bytes_per_line + col * 4 + channel]
                   for row in range(0, 900, 24) for col in range(0, 1200, 24) for channel in range(3))
    frames.append(dict(t=round(stamp-started, 3), mean=round(statistics.mean(pixels), 2),
                       digest=hashlib.sha256(pixels).hexdigest()[:16]))
    x.XDestroyImage(img)
    time.sleep(max(0, 0.05 - (time.monotonic() - stamp)))
x.XCloseDisplay(display)
print(json.dumps(dict(frames=frames, unique_samples=len({f['digest'] for f in frames}),
    minimum_mean=min(f['mean'] for f in frames), maximum_mean=max(f['mean'] for f in frames),
    note='20 Hz X11 pixel samples, not a frame-rate or color-accuracy benchmark.'), indent=2))
