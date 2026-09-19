#include <windows.h>
#include <stdio.h>

int main(void)
{
    HMODULE module = LoadLibraryW(L"ext-ms-win-uiacore-l1-1-2.dll");
    HRESULT (WINAPI *disconnect)(void);
    HRESULT result;
    if (!module) { printf("UIA API set load failed: %lu\n", GetLastError()); return 1; }
    disconnect = (void *)GetProcAddress(module, "UiaDisconnectAllProviders");
    if (!disconnect) { puts("UIA shutdown export missing"); return 1; }
    result = disconnect();
    printf("UIA shutdown call returned %08lx without aborting\n", result);
    FreeLibrary(module);
    return FAILED(result);
}
