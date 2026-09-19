/* Check the Windows scale API used by Lightroom, without creating a window. */
#include <windows.h>
#include <shellscalingapi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    HMONITOR monitor = MonitorFromPoint((POINT){0, 0}, MONITOR_DEFAULTTOPRIMARY);
    DPI_AWARENESS_CONTEXT contexts[] = { DPI_AWARENESS_CONTEXT_UNAWARE,
        DPI_AWARENESS_CONTEXT_SYSTEM_AWARE, DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE };
    unsigned int expected = argc == 2 ? atoi(argv[1]) : 0;
    int failures = 0;
    for (unsigned int i = 0; i < 3; i++) {
        DPI_AWARENESS_CONTEXT old = SetThreadDpiAwarenessContext(contexts[i]);
        DEVICE_SCALE_FACTOR scale = 0;
        UINT x = 0, y = 0;
        HRESULT hr = GetScaleFactorForMonitor(monitor, &scale);
        GetDpiForMonitor(monitor, MDT_EFFECTIVE_DPI, &x, &y);
        BOOL unchanged = AreDpiAwarenessContextsEqual(GetThreadDpiAwarenessContext(), contexts[i]);
        printf("awareness=%u result=%08lx scale=%u dpi=%ux%u context_preserved=%d\n",
               i, hr, scale, x, y, unchanged);
        if (FAILED(hr) || !unchanged || (expected && scale != expected)) failures++;
        SetThreadDpiAwarenessContext(old);
    }
    return failures ? 1 : 0;
}
