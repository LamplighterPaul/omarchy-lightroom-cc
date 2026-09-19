/* Measure Wine event round trips. This is not a Lightroom rendering benchmark. */
#include <windows.h>
#include <stdio.h>
static HANDLE request, response;
static const unsigned rounds = 20000;
static DWORD WINAPI worker(void *unused)
{
    for (unsigned i = 0; i < rounds; i++) {
        if (WaitForSingleObject(request, 5000) != WAIT_OBJECT_0) return 1;
        if (!SetEvent(response)) return 1;
    }
    return 0;
}
int main(void)
{
    LARGE_INTEGER frequency, start, end;
    QueryPerformanceFrequency(&frequency);
    for (unsigned run = 0; run < 5; run++) {
        request = CreateEventW(NULL, FALSE, FALSE, NULL);
        response = CreateEventW(NULL, FALSE, FALSE, NULL);
        HANDLE thread = CreateThread(NULL, 0, worker, NULL, 0, NULL);
        if (!request || !response || !thread) return 1;
        QueryPerformanceCounter(&start);
        for (unsigned i = 0; i < rounds; i++) {
            if (!SetEvent(request) || WaitForSingleObject(response, 5000) != WAIT_OBJECT_0) return 1;
        }
        QueryPerformanceCounter(&end);
        if (WaitForSingleObject(thread, 5000) != WAIT_OBJECT_0) return 1;
        printf("round_trips=%u elapsed_ms=%.3f\n", rounds,
               1000.0 * (end.QuadPart - start.QuadPart) / frequency.QuadPart);
        CloseHandle(request); CloseHandle(response); CloseHandle(thread);
    }
    return 0;
}
