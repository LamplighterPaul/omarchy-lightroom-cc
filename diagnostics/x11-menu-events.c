/* Read-only MapNotify timestamps on the private X11 fixture. No screenshots.
 * Build: cc -O2 -Wall x11-menu-events.c -o x11-menu-events -lX11
 * Mapping is not proof of visible pixels or end-to-end display latency. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double seconds(clockid_t clock)
{
    struct timespec t;
    clock_gettime(clock, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

static int ignore_destroyed(Display *display, XErrorEvent *error) { return 0; }

int main(int argc, char **argv)
{
    const char *display = getenv("DISPLAY"), *wayland = getenv("WAYLAND_DISPLAY");
    int duration = argc == 2 ? atoi(argv[1]) : 0;
    if (!display || strcmp(display, ":1") || !wayland || strcmp(wayland, "lightroom-test") ||
        duration < 1 || duration > 60) return 2;
    Display *d = XOpenDisplay(":1");
    if (!d) return 3;
    XSetErrorHandler(ignore_destroyed);
    /* Observe only; never request redirect ownership from the window manager. */
    XSelectInput(d, DefaultRootWindow(d), SubstructureNotifyMask);
    XSync(d, False);
    puts("event,epoch,monotonic,window,x,y,width,height");
    puts("ready,,,,,,,"); fflush(stdout);
    double deadline = seconds(CLOCK_MONOTONIC) + duration;
    while (seconds(CLOCK_MONOTONIC) < deadline) {
        if (!XPending(d)) {
            struct pollfd fd = {ConnectionNumber(d), POLLIN, 0};
            if (poll(&fd, 1, 100) < 0) break;
            continue;
        }
        XEvent event; XNextEvent(d, &event);
        double stamp = seconds(CLOCK_MONOTONIC), epoch = seconds(CLOCK_REALTIME);
        if (event.type != MapNotify) continue;
        Window w = event.xmap.window; XWindowAttributes a; XClassHint hint = {0};
        if (!XGetWindowAttributes(d, w, &a) || !a.override_redirect || !XGetClassHint(d, w, &hint)) continue;
        if (hint.res_class && !strcmp(hint.res_class, "steam_app_lightroomomarchyproton")) {
            printf("map,%.9f,%.9f,%lx,%d,%d,%d,%d\n", epoch, stamp, w, a.x, a.y, a.width, a.height);
            fflush(stdout);
        }
        if (hint.res_class) XFree(hint.res_class);
        if (hint.res_name) XFree(hint.res_name);
    }
    XCloseDisplay(d);
    return 0;
}
