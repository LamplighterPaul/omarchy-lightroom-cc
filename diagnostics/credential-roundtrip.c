/* Test Wine/Proton DPAPI migration with disposable data, never Adobe tokens. */
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    static char sample[] = "lightroom-omarchy-proton disposable migration test";
    DATA_BLOB input = {0}, output = {0};
    char user[256]; DWORD size = sizeof(user);
    FILE *file;
    if (argc != 3) return 2;
    if (!GetUserNameA(user, &size)) return 3;
    printf("Windows user: %s\n", user);
    if (!strcmp(argv[1], "protect"))
    {
        input.pbData = (BYTE *)sample; input.cbData = sizeof(sample);
        if (!CryptProtectData(&input, L"Migration test", NULL, NULL, NULL,
                              CRYPTPROTECT_UI_FORBIDDEN, &output)) return 4;
        file = fopen(argv[2], "wb");
        if (!file) return 5;
        size_t written = fwrite(output.pbData, 1, output.cbData, file);
        fclose(file); LocalFree(output.pbData);
        if (written != output.cbData) return 6;
        puts("Disposable test data protected.");
    }
    else if (!strcmp(argv[1], "unprotect"))
    {
        BYTE bytes[4096];
        file = fopen(argv[2], "rb");
        if (!file) return 7;
        input.cbData = fread(bytes, 1, sizeof(bytes), file); input.pbData = bytes;
        fclose(file);
        if (!CryptUnprotectData(&input, NULL, NULL, NULL, NULL,
                                CRYPTPROTECT_UI_FORBIDDEN, &output))
        { printf("Unprotect failed: %lu\n", GetLastError()); return 8; }
        int ok = output.cbData == sizeof(sample) && !memcmp(output.pbData, sample, sizeof(sample));
        LocalFree(output.pbData);
        puts(ok ? "Round trip verified." : "Payload mismatch.");
        return ok ? 0 : 9;
    }
    else return 2;
    return 0;
}
