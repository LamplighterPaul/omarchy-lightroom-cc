#!/usr/bin/env python3
"""Real XTest gestures for the isolated Weston fixture ONLY, never the desktop."""
import argparse
import ctypes as c
import os
import json
from pathlib import Path
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['zoom', 'pan', 'menus', 'maximize', 'record', 'menu-open', 'edit-menu-open', 'escape', 'loupe', 'close'])
args = parser.parse_args()
if os.environ.get('WAYLAND_DISPLAY') != 'lightroom-test' or os.environ.get('DISPLAY') != ':1':
    raise SystemExit('Refusing input outside the dedicated lightroom-test/:1 fixture')

# Prove the X server belongs to our headless Weston, not another desktop.
server_pid = int(Path('/tmp/.X1-lock').read_text())
server = Path('/proc') / str(server_pid)
parent = int((server / 'stat').read_text().rsplit(')', 1)[1].split()[1])
command = (server / 'cmdline').read_bytes().split(b'\0')
if b'--socket=lightroom-test' not in command:
    command = (Path('/proc') / str(parent) / 'cmdline').read_bytes().split(b'\0')
if b'--socket=lightroom-test' not in command or b'--backend=headless' not in command:
    raise SystemExit('Display :1 is not owned by the isolated headless Weston')

x = c.CDLL('libX11.so.6')
t = c.CDLL('libXtst.so.6')
x.XOpenDisplay.argtypes=[c.c_char_p]; x.XOpenDisplay.restype=c.c_void_p
x.XDefaultRootWindow.argtypes=[c.c_void_p]; x.XDefaultRootWindow.restype=c.c_ulong
x.XQueryTree.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_ulong),c.POINTER(c.POINTER(c.c_ulong)),c.POINTER(c.c_uint)]
x.XFetchName.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_char_p)]
x.XGetGeometry.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_uint),c.POINTER(c.c_uint),c.POINTER(c.c_uint),c.POINTER(c.c_uint)]
x.XTranslateCoordinates.argtypes=[c.c_void_p,c.c_ulong,c.c_ulong,c.c_int,c.c_int,c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_ulong)]
x.XSetInputFocus.argtypes=[c.c_void_p,c.c_ulong,c.c_int,c.c_ulong]
x.XMoveResizeWindow.argtypes=[c.c_void_p,c.c_ulong,c.c_int,c.c_int,c.c_uint,c.c_uint]
x.XKeysymToKeycode.argtypes=[c.c_void_p,c.c_ulong]; x.XKeysymToKeycode.restype=c.c_uint
x.XFlush.argtypes=[c.c_void_p]; x.XFree.argtypes=[c.c_void_p]
t.XTestFakeMotionEvent.argtypes=[c.c_void_p,c.c_int,c.c_int,c.c_int,c.c_ulong]
t.XTestFakeButtonEvent.argtypes=[c.c_void_p,c.c_uint,c.c_int,c.c_ulong]
t.XTestFakeKeyEvent.argtypes=[c.c_void_p,c.c_uint,c.c_int,c.c_ulong]
d=x.XOpenDisplay(b':1')
if not d: raise SystemExit('Isolated X11 display unavailable')
root=x.XDefaultRootWindow(d); windows=[]

def geometry(w):
    r=c.c_ulong();a=c.c_int();b=c.c_int();width=c.c_uint();height=c.c_uint();border=c.c_uint();depth=c.c_uint()
    x.XGetGeometry(d,w,c.byref(r),c.byref(a),c.byref(b),c.byref(width),c.byref(height),c.byref(border),c.byref(depth))
    return width.value,height.value

def walk(w,depth=0):
    name=c.c_char_p();x.XFetchName(d,w,c.byref(name))
    if name.value==b'Lightroom':
        width,height=geometry(w);windows.append((width*height,w))
    if name: x.XFree(name)
    if depth>4:return
    r=c.c_ulong();p=c.c_ulong();children=c.POINTER(c.c_ulong)();count=c.c_uint()
    if x.XQueryTree(d,w,c.byref(r),c.byref(p),c.byref(children),c.byref(count)):
        for i in range(count.value):walk(children[i],depth+1)
        if children:x.XFree(children)

walk(root)
if not windows:raise SystemExit('No Lightroom window in fixture')
w=max(windows)[1]
x.XSetInputFocus(d,w,1,0)

def key(symbol,pressed):
    t.XTestFakeKeyEvent(d,x.XKeysymToKeycode(d,symbol),pressed,0);x.XFlush(d)

phase_start = time.time()
if args.action=='maximize':
    x.XMoveResizeWindow(d,w,0,0,2832,1692);x.XFlush(d)
elif args.action=='zoom':
    key(ord(' '),1);key(ord(' '),0)
elif args.action=='loupe':
    key(ord('d'),1);key(ord('d'),0)
elif args.action=='close':
    key(0xffe3,1);key(ord('q'),1);time.sleep(.05);key(ord('q'),0);key(0xffe3,0)
elif args.action=='menu-open':
    left=c.c_int();top=c.c_int();child=c.c_ulong()
    x.XTranslateCoordinates(d,w,root,0,0,c.byref(left),c.byref(top),c.byref(child))
    width,height=geometry(w)
    print('Menu origin:',left.value,top.value)
    t.XTestFakeMotionEvent(d,-1,left.value+round(width*.432),top.value+30,0)
    t.XTestFakeButtonEvent(d,1,1,0);t.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d)
elif args.action=='edit-menu-open':
    key(0xffe9,1);key(ord('e'),1);key(ord('e'),0);key(0xffe9,0)
elif args.action=='escape':
    key(0xff1b,1);key(0xff1b,0)
elif args.action=='record':
    key(0xffe1,1);key(0xffbf,1);time.sleep(.5);key(0xffbf,0);key(0xffe1,0)
elif args.action=='menus':
    for i in range(5):
        key(0xffe9,1);key(ord('f'),1);key(ord('f'),0);key(0xffe9,0)
        time.sleep(.6);key(0xff1b,1);key(0xff1b,0);time.sleep(.4)
else:
    left=c.c_int();top=c.c_int();child=c.c_ulong()
    x.XTranslateCoordinates(d,w,root,0,0,c.byref(left),c.byref(top),c.byref(child))
    width,height=geometry(w);cx=left.value+width//2;cy=top.value+height//2
    t.XTestFakeMotionEvent(d,-1,cx,cy,0);t.XTestFakeButtonEvent(d,1,1,0);x.XFlush(d)
    for i in range(1200):
        step=i%240
        dx=(step if step<120 else 240-step)*3
        t.XTestFakeMotionEvent(d,-1,cx+dx,cy,0);x.XFlush(d);time.sleep(1/120)
    t.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d)
phase = dict(action=args.action, start_epoch=phase_start, end_epoch=time.time())
log = Path.home()/'.local/share/omarchy-lightroom-cc/measurements/isolated-input.jsonl'
with log.open('a') as stream: stream.write(json.dumps(phase)+'\n')
print(json.dumps(phase), flush=True)
