/* Private Weston crash-recovery probe. See docs/randr-recovery-2026-09-20.md. */
#include <windows.h>
#include <stdio.h>
int main(void)
{
    HMODULE user;
    int (WINAPI *metrics)(int);
    HWND (WINAPI *create)(DWORD,LPCWSTR,LPCWSTR,DWORD,int,int,int,int,HWND,HMENU,HINSTANCE,LPVOID);
    HWND window;
    printf("ready %lu\n", GetCurrentProcessId()); fflush(stdout);
    Sleep(12000);
    user = LoadLibraryW(L"user32.dll");
    if (!user) return 2;
    metrics = (void *)GetProcAddress(user,"GetSystemMetrics");
    if (!metrics) return 3;
    create = (void *)GetProcAddress(user,"CreateWindowExW");
    if (!create) return 4;
    window = create(0,L"STATIC",L"Private RandR probe",WS_OVERLAPPEDWINDOW,0,0,300,150,0,0,0,0);
    if (!window) return 4;
    printf("display %d x %d\n",metrics(SM_CXSCREEN),metrics(SM_CYSCREEN));fflush(stdout);
    Sleep(12000);
    return 0;
}
