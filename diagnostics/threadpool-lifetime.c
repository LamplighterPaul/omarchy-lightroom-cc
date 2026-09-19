/* Regression probe for pool release while bound objects remain alive. */
#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static void CALLBACK timer_cb(PTP_CALLBACK_INSTANCE instance, void *context, PTP_TIMER timer)
{ SetEvent(context); }
static void CALLBACK work_cb(PTP_CALLBACK_INSTANCE instance, void *context, PTP_WORK work)
{ SetEvent(context); }
static void CALLBACK wait_cb(PTP_CALLBACK_INSTANCE instance, void *context, PTP_WAIT wait, TP_WAIT_RESULT result)
{ SetEvent(context); }
static int run_case(const char *mode)
{
    TP_CALLBACK_ENVIRON env;
    PTP_POOL pool;
    HANDLE done, trigger;
    FILETIME due = { (DWORD)-2000000, (DWORD)-1 }; /* 200 ms, relative */
    DWORD result;
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    pool = CreateThreadpool(NULL);
    if (!pool) return 2;
    if (!strcmp(mode, "empty")) { CloseThreadpool(pool); return 0; }
    done = CreateEventW(NULL, TRUE, FALSE, NULL);
    trigger = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!done || !trigger) return 3;
    InitializeThreadpoolEnvironment(&env);
    SetThreadpoolCallbackPool(&env, pool);
    if (!strcmp(mode, "work")) {
        PTP_WORK work = CreateThreadpoolWork(work_cb, done, &env);
        if (!work) return 4;
        CloseThreadpool(pool);
        Sleep(50);
        SubmitThreadpoolWork(work);
        result = WaitForSingleObject(done, 3000);
        WaitForThreadpoolWorkCallbacks(work, TRUE);
        CloseThreadpoolWork(work);
    } else if (!strcmp(mode, "wait")) {
        PTP_WAIT wait = CreateThreadpoolWait(wait_cb, done, &env);
        if (!wait) return 5;
        SetThreadpoolWait(wait, trigger, NULL);
        CloseThreadpool(pool);
        Sleep(50);
        SetEvent(trigger);
        result = WaitForSingleObject(done, 3000);
        SetThreadpoolWait(wait, NULL, NULL);
        WaitForThreadpoolWaitCallbacks(wait, TRUE);
        CloseThreadpoolWait(wait);
    } else {
        PTP_TIMER timer = CreateThreadpoolTimer(timer_cb, done, &env);
        if (!timer) return 6;
        SetThreadpoolTimer(timer, &due, 0, 0);
        if (strcmp(mode, "normal")) CloseThreadpool(pool);
        if (!strcmp(mode, "cancel")) {
            SetThreadpoolTimer(timer, NULL, 0, 0);
            result = WAIT_OBJECT_0;
        } else result = WaitForSingleObject(done, 3000);
        WaitForThreadpoolTimerCallbacks(timer, TRUE);
        CloseThreadpoolTimer(timer);
        if (!strcmp(mode, "normal")) CloseThreadpool(pool);
    }
    DestroyThreadpoolEnvironment(&env);
    CloseHandle(done); CloseHandle(trigger);
    if (result != WAIT_OBJECT_0) fprintf(stderr, "%s FAIL (%lu)\n", mode, result);
    return result == WAIT_OBJECT_0 ? 0 : 7;
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "timer";
    int count = argc > 2 ? atoi(argv[2]) : 1, i, result;
    if (strcmp(mode, "normal") && strcmp(mode, "timer") && strcmp(mode, "wait") &&
        strcmp(mode, "work") && strcmp(mode, "cancel") && strcmp(mode, "empty")) {
        fprintf(stderr, "Unknown case: %s\n", mode);
        return 8;
    }
    if (count < 1 || count > 1000) return 8;
    for (i = 0; i < count; ++i) if ((result = run_case(mode))) return result;
    Sleep(100);
    printf("%s PASS iterations=%d", mode, count);
    puts("");
    return 0;
}
