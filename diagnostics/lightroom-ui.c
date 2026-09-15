/* Minimal inspection/interaction limited to Lightroom windows in this prefix. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#include <winternl.h>
#include <tlhelp32.h>
static BOOL click_signin = FALSE;
static BOOL found = FALSE;
static DWORD inspected_pid = 0;
static void inspect_environment(DWORD pid) {
    if (inspected_pid == pid) return;
    inspected_pid = pid;
    HANDLE process = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!process) { printf("PID %lu inspection unavailable: %lu\n", pid, GetLastError()); return; }
    typedef NTSTATUS (WINAPI *query_fn)(HANDLE, PROCESSINFOCLASS, PVOID, ULONG, PULONG);
    query_fn query = (query_fn)GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtQueryInformationProcess");
    PROCESS_BASIC_INFORMATION info;
    if (query && !query(process, ProcessBasicInformation, &info, sizeof(info), NULL)) {
        uintptr_t params = 0, environment = 0;
        if (ReadProcessMemory(process, (char*)info.PebBaseAddress + 0x20, &params, sizeof(params), NULL) &&
            ReadProcessMemory(process, (void*)(params + 0x80), &environment, sizeof(environment), NULL)) {
            UNICODE_STRING command;
            if (ReadProcessMemory(process, (void*)(params + 0x70), &command, sizeof(command), NULL) && command.Length < 32000) {
                wchar_t cmd[16001];
                if (ReadProcessMemory(process, command.Buffer, cmd, command.Length, NULL)) {
                    cmd[command.Length/2] = 0;
                    wprintf(L"PID %lu flags: disable-gpu=%d no-sandbox=%d swiftshader=%d in-process-gpu=%d gpu-child=%d\n", pid,
                        wcsstr(cmd,L"--disable-gpu")!=NULL, wcsstr(cmd,L"--no-sandbox")!=NULL,
                        wcsstr(cmd,L"--use-angle=swiftshader")!=NULL, wcsstr(cmd,L"--in-process-gpu")!=NULL,
                        wcsstr(cmd,L"--type=gpu-process")!=NULL);
                }
            }
            wchar_t buffer[32768]; SIZE_T read = 0, length = sizeof(buffer);
            MEMORY_BASIC_INFORMATION region;
            if (VirtualQueryEx(process, (void*)environment, &region, sizeof(region))) {
                SIZE_T available = (uintptr_t)region.BaseAddress + region.RegionSize - environment;
                if (available < length) length = available;
            }
            if (ReadProcessMemory(process, (void*)environment, buffer, length, &read) || read > 0) {
                size_t count = read / sizeof(wchar_t); buffer[count ? count-1 : 0] = 0;
                for (wchar_t *v = buffer; v < buffer + count && *v; v += wcslen(v)+1)
                    if (!wcsncmp(v, L"WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=", 37)) wprintf(L"Target environment: %ls\n", v);
            }
        }
    }
    CloseHandle(process);
}
static BOOL CALLBACK child(HWND wnd, LPARAM unused) {
    wchar_t text[256];
    GetWindowTextW(wnd, text, 256);
    if (IsWindowVisible(wnd) && !wcscmp(text, L"Sign In")) {
        RECT r; GetClientRect(wnd, &r);
        printf("Sign In control: %p\n", (void *)wnd);
        if (click_signin) {
            LPARAM point = MAKELPARAM((r.right-r.left)/2, (r.bottom-r.top)/2);
            PostMessageW(wnd, WM_LBUTTONDOWN, MK_LBUTTON, point);
            PostMessageW(wnd, WM_LBUTTONUP, 0, point);
            puts("Clicked Lightroom Sign In.");
        }
        found = TRUE;
        return FALSE;
    }
    return TRUE;
}
static BOOL CALLBACK window(HWND wnd, LPARAM unused) {
    DWORD pid; wchar_t path[4096]; DWORD length=4096;
    GetWindowThreadProcessId(wnd, &pid);
    HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!p) return TRUE;
    BOOL ok = QueryFullProcessImageNameW(p, 0, path, &length);
    CloseHandle(p);
    if (!ok) return TRUE;
    const wchar_t *name = wcsrchr(path, L'\\');
    if (!name || _wcsicmp(name+1, L"lightroom.exe")) return TRUE;
    inspect_environment(pid);
    if (IsWindowVisible(wnd)) {
        wchar_t cls[128]; RECT r; GetClassNameW(wnd, cls, 128); GetWindowRect(wnd, &r);
        wprintf(L"Window %p class %ls rect %ld,%ld %ldx%ld\n", (void*)wnd,cls,r.left,r.top,r.right-r.left,r.bottom-r.top);
        if (!found) EnumChildWindows(wnd, child, 0);
    }
    return TRUE;
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "browser")) {
        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        PROCESSENTRY32W entry = { .dwSize = sizeof(entry) };
        if (Process32FirstW(snapshot, &entry)) do {
            if (!_wcsicmp(entry.szExeFile, L"msedgewebview2.exe") ||
                !_wcsicmp(entry.szExeFile, L"adobe_licensing_wf.exe") ||
                !_wcsicmp(entry.szExeFile, L"adobe_licensing_wf_helper.exe")) {
                wprintf(L"Browser process %ls PID %lu\n", entry.szExeFile, entry.th32ProcessID);
                inspect_environment(entry.th32ProcessID);
            }
        } while (Process32NextW(snapshot, &entry));
        CloseHandle(snapshot);
        return 0;
    }
    click_signin = argc == 2 && !strcmp(argv[1], "click-sign-in");
    EnumWindows(window, 0);
    return click_signin && !found ? 1 : 0;
}
