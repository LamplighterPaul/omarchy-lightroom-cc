/* Synthetic menu API call cost, including the Windows/Unix boundary.
 * No Lightroom data or windows. Not an application latency benchmark. */
#include <windows.h>
#include <stdio.h>

int main(void)
{
    HMENU menu = CreatePopupMenu();
    LARGE_INTEGER frequency, start, end;
    volatile UINT sink = 0;
    const unsigned rounds = 22000, items = 458;
    if (!menu || !QueryPerformanceFrequency(&frequency)) return 1;
    for (unsigned i = 0; i < items; i++)
        if (!AppendMenuW(menu, MF_STRING, 1000 + i, L"Example menu command\tCtrl+Shift+K")) return 2;
    puts("pass,method,calls,elapsed_ms");
    for (unsigned pass = 0; pass < 5; pass++)
    {
        for (unsigned method = 0; method < 4; method++)
        {
            QueryPerformanceCounter(&start);
            for (unsigned i = 0; i < rounds; i++)
            {
                WCHAR text[128];
                MENUITEMINFOW info = { .cbSize = sizeof(info), .fMask = MIIM_STATE | MIIM_ID };
                if (method == 0) sink ^= GetMenuItemID(menu, i % items);
                else if (method == 1) sink ^= GetMenuState(menu, i % items, MF_BYPOSITION);
                else
                {
                    if (method == 3)
                    {
                        info.fMask |= MIIM_STRING;
                        info.dwTypeData = text;
                        info.cch = sizeof(text) / sizeof(text[0]);
                    }
                    if (!GetMenuItemInfoW(menu, i % items, TRUE, &info)) return 3;
                    sink ^= info.wID;
                }
            }
            QueryPerformanceCounter(&end);
            printf("%u,%u,%u,%.6f\n", pass, method, rounds,
                   1000.0 * (end.QuadPart - start.QuadPart) / frequency.QuadPart);
        }
    }
    DestroyMenu(menu);
    return sink == 0xffffffff ? 4 : 0;
}
