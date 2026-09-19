/* Exercise Lightroom's firewall rule enumeration without changing any rules. */
#define COBJMACROS
#include <windows.h>
#include <initguid.h>
#include <ole2.h>
#include <netfw.h>
#include <stdio.h>

int main(void)
{
    INetFwPolicy2 *policy = NULL;
    INetFwRules *rules = NULL;
    IUnknown *unknown = NULL;
    IEnumVARIANT *enumerator = NULL, *clone = NULL;
    VARIANT value; ULONG fetched = 999;
    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) return 1;
    hr = CoCreateInstance(&CLSID_NetFwPolicy2, NULL, CLSCTX_INPROC_SERVER,
                          &IID_INetFwPolicy2, (void **)&policy);
    if (FAILED(hr)) return 2;
    hr = INetFwPolicy2_get_Rules(policy, &rules);
    if (FAILED(hr)) return 3;
    hr = INetFwRules_get__NewEnum(rules, &unknown);
    printf("NewEnum: %08lx; object=%s\n", hr, unknown ? "present" : "missing");
    if (FAILED(hr) || !unknown) return 4;
    hr = IUnknown_QueryInterface(unknown, &IID_IEnumVARIANT, (void **)&enumerator);
    if (FAILED(hr) || !enumerator) return 5;
    VariantInit(&value);
    hr = IEnumVARIANT_Next(enumerator, 1, &value, &fetched);
    printf("Next: %08lx; fetched=%lu\n", hr, fetched);
    if (hr != S_FALSE || fetched != 0) return 6;
    if (IEnumVARIANT_Reset(enumerator) != S_OK) return 7;
    if (IEnumVARIANT_Clone(enumerator, &clone) != S_OK || !clone) return 8;
    fetched = 999;
    if (IEnumVARIANT_Next(clone, 1, &value, &fetched) != S_FALSE || fetched) return 9;
    IEnumVARIANT_Release(clone); IEnumVARIANT_Release(enumerator);
    IUnknown_Release(unknown); INetFwRules_Release(rules); INetFwPolicy2_Release(policy);
    CoUninitialize();
    puts("Empty enumeration, reset and clone verified.");
    return 0;
}
