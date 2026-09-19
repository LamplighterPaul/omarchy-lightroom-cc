/* Diagnostic screenshots from the PRIVATE Weston fixture, not host desktop.
 * Build with generated weston-output-capture protocol and wayland-client/libpng.
 * Readback perturbs rendering: this is appearance evidence, never an FPS test. */
#define _GNU_SOURCE
#include <wayland-client.h>
#include <png.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "weston-output-capture-client-protocol.h"
static struct wl_shm *shm;
static struct wl_output *output;
static struct weston_capture_v1 *factory;
static int width, height, format_ok, completed, failed;
static void global(void *data, struct wl_registry *registry, uint32_t id, const char *name, uint32_t version)
{
    if (!strcmp(name, "wl_shm")) shm = wl_registry_bind(registry, id, &wl_shm_interface, 1);
    else if (!strcmp(name, "wl_output") && !output) output = wl_registry_bind(registry, id, &wl_output_interface, 1);
    else if (!strcmp(name, "weston_capture_v1")) factory = wl_registry_bind(registry, id, &weston_capture_v1_interface, 1);
}
static void removed(void *data, struct wl_registry *registry, uint32_t id) {}
static const struct wl_registry_listener registry_listener = { global, removed };
static void format(void *data, struct weston_capture_source_v1 *source, uint32_t value)
{ if (value == 0x34325241) format_ok = 1; } /* DRM_FORMAT_ARGB8888 */
static void size(void *data, struct weston_capture_source_v1 *source, int32_t w, int32_t h)
{ width = w; height = h; }
static void complete(void *data, struct weston_capture_source_v1 *source) { completed = 1; }
static void retry(void *data, struct weston_capture_source_v1 *source)
{ fprintf(stderr, "Capture size/format changed; restart capture.\n"); failed = 1; }
static void failure(void *data, struct weston_capture_source_v1 *source, const char *message)
{ fprintf(stderr, "Capture failed: %s\n", message ? message : "unknown"); failed = 1; }
static const struct weston_capture_source_v1_listener capture_listener = {
    .format = format, .size = size, .complete = complete, .retry = retry, .failed = failure
};
static double seconds(clockid_t clock)
{ struct timespec t; clock_gettime(clock, &t); return t.tv_sec + t.tv_nsec / 1e9; }
static int save_png(const char *path, const uint32_t *pixels, int w, int h)
{
    FILE *file = fopen(path, "wx");
    if (!file) return 0;
    png_structp png = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    png_infop info = png ? png_create_info_struct(png) : NULL;
    if (!png || !info) { fclose(file); return 0; }
    if (setjmp(png_jmpbuf(png))) { png_destroy_write_struct(&png, &info); fclose(file); return 0; }
    png_init_io(png, file); png_set_compression_level(png, 1);
    int ow = w / 4, oh = h / 4;
    png_set_IHDR(png, info, ow, oh, 8, PNG_COLOR_TYPE_RGB, PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
    png_write_info(png, info);
    unsigned char *row = malloc(ow * 3);
    if (!row) { png_destroy_write_struct(&png, &info); fclose(file); return 0; }
    for (int y = 0; y < oh; y++) {
        for (int x = 0; x < ow; x++) {
            uint32_t pixel = pixels[y * 4 * w + x * 4];
            row[x*3] = pixel >> 16; row[x*3+1] = pixel >> 8; row[x*3+2] = pixel;
        }
        png_write_row(png, row);
    }
    free(row); png_write_end(png, NULL); png_destroy_write_struct(&png, &info); fclose(file); return 1;
}
int main(int argc, char **argv)
{
    if (argc != 4 || !getenv("WAYLAND_DISPLAY") || strcmp(getenv("WAYLAND_DISPLAY"), "lightroom-test")) {
        fprintf(stderr, "Only WAYLAND_DISPLAY=lightroom-test is allowed. Usage: capture EXISTING_DIR FRAMES FPS\n"); return 2;
    }
    int frames = atoi(argv[2]), fps = atoi(argv[3]); struct stat st;
    if (frames < 1 || frames > 600 || fps < 1 || fps > 30 || frames > fps * 60 || stat(argv[1], &st) || !S_ISDIR(st.st_mode)) return 2;
    alarm(90);
    struct wl_display *display = wl_display_connect("lightroom-test");
    if (!display) return 3;
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !shm || !output || !factory) return 3;
    struct weston_capture_source_v1 *source = weston_capture_v1_create(factory, output, WESTON_CAPTURE_V1_SOURCE_FRAMEBUFFER);
    weston_capture_source_v1_add_listener(source, &capture_listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !format_ok || width < 4 || height < 4 || width > 8192 || height > 8192) return 3;
    int w = width, h = height; size_t length = (size_t)w * h * 4;
    int fd = memfd_create("lightroom-capture", MFD_CLOEXEC);
    if (fd < 0 || ftruncate(fd, length)) return 4;
    uint32_t *pixels = mmap(NULL, length, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (pixels == MAP_FAILED) return 4;
    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, length);
    struct wl_buffer *buffer = wl_shm_pool_create_buffer(pool, 0, w, h, w * 4, WL_SHM_FORMAT_ARGB8888);
    wl_shm_pool_destroy(pool); close(fd);
    puts("frame,epoch,capture_ms,mean_luma,dark_fraction");
    for (int i = 0; i < frames; i++) {
        double start = seconds(CLOCK_MONOTONIC); completed = 0;
        weston_capture_source_v1_capture(source, buffer);
        while (!completed && !failed) if (wl_display_dispatch(display) < 0) failed = 1;
        if (failed || width != w || height != h) return 5;
        double end = seconds(CLOCK_MONOTONIC), epoch = seconds(CLOCK_REALTIME), total = 0;
        unsigned count = 0, dark = 0;
        for (int y = h / 5; y < h * 3 / 4; y += 8) for (int x = w / 3; x < w * 2 / 3; x += 8) {
            uint32_t p = pixels[y * w + x];
            double luma = .2126 * ((p >> 16) & 255) + .7152 * ((p >> 8) & 255) + .0722 * (p & 255);
            total += luma; dark += luma < 16; count++;
        }
        char path[4096];
        if (snprintf(path, sizeof(path), "%s/frame-%04d.png", argv[1], i) >= sizeof(path) || !save_png(path, pixels, w, h)) return 6;
        printf("%d,%.6f,%.3f,%.3f,%.6f\n", i, epoch, (end-start)*1000, total/count, (double)dark/count); fflush(stdout);
        double delay = 1.0/fps - (seconds(CLOCK_MONOTONIC) - start);
        if (delay > 0) { struct timespec t = {(time_t)delay, (long)((delay-(time_t)delay)*1e9)}; nanosleep(&t, NULL); }
    }
    wl_buffer_destroy(buffer); weston_capture_source_v1_destroy(source); weston_capture_v1_destroy(factory);
    wl_registry_destroy(registry); wl_display_disconnect(display); munmap(pixels, length); return 0;
}
