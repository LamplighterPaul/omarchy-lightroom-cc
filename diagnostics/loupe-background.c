/* Regression probe for the opt-in X11 loupeView retained-photo workaround.
 * Run ONLY in the private Weston fixture: creates temporary test windows.
 * Build with MinGW: -ld3d11 -ldxgi -ldxguid -lgdi32 -luser32 */
#define COBJMACROS
#include <windows.h>
#include <d3d11.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned failures;
static void pump(void);
struct renderer { IDXGISwapChain *swap; ID3D11Device *device; ID3D11DeviceContext *context; ID3D11RenderTargetView *target; };
/* GetPixel(child) can read stale GDI storage while its GPU surface is visible.
 * The runner validates actual private-compositor pixels and acknowledges each
 * check through an application-local file. This diagnostic intentionally waits; it is not a benchmark. */
static void check(const char *name, HWND window, int x, int y, COLORREF expected)
{
    POINT pt={x,y};char reply[32];ClientToScreen(window,&pt);
    printf("CAPTURE %s %ld %ld %u %u %u\n",name,pt.x,pt.y,
           GetRValue(expected),GetGValue(expected),GetBValue(expected));fflush(stdout);
    static unsigned sequence;char path[2048];FILE *ack=0;
    snprintf(path,sizeof(path),"%s/%u.ack",getenv("LRCC_CAPTURE_DIR"),sequence++);
    for(unsigned i=0;i<1500&&!ack;i++){MsgWaitForMultipleObjects(0,0,FALSE,10,QS_ALLINPUT);pump();ack=fopen(path,"r");}
    if(!ack){puts("FAIL capture timeout");exit(2);}
    if(!fgets(reply,sizeof(reply),ack)||strcmp(reply,"PASS\n"))failures++;
    fclose(ack);remove(path);
}
static void pump(void) { MSG m; while(PeekMessageW(&m,0,0,0,PM_REMOVE)){TranslateMessage(&m);DispatchMessageW(&m);} }
static void fill(HWND window, int width, int height)
{
    HDC dc=GetDC(window); HBRUSH brush=CreateSolidBrush(RGB(0,255,0)); HGDIOBJ old=SelectObject(dc,brush);
    if(!PatBlt(dc,0,0,width,height,PATCOPY)){puts("FAIL PatBlt");failures++;}
    SelectObject(dc,old);DeleteObject(brush);
    /* Synchronize the diagnostic GDI request before compositor sampling. */
    GetPixel(dc,5,5);ReleaseDC(window,dc);GdiFlush();
}
static void start(struct renderer *r, HWND window, UINT width, UINT height)
{
    DXGI_SWAP_CHAIN_DESC desc={0}; D3D_FEATURE_LEVEL level=D3D_FEATURE_LEVEL_11_0; ID3D11Texture2D *texture=0;
    desc.BufferDesc.Width=width;desc.BufferDesc.Height=height;desc.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.SampleDesc.Count=1;desc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;desc.BufferCount=2;desc.OutputWindow=window;
    desc.Windowed=TRUE;desc.SwapEffect=DXGI_SWAP_EFFECT_DISCARD;
    HRESULT hr=D3D11CreateDeviceAndSwapChain(0,D3D_DRIVER_TYPE_HARDWARE,0,0,&level,1,D3D11_SDK_VERSION,&desc,&r->swap,&r->device,0,&r->context);
    if(FAILED(hr)){printf("FAIL D3D11 creation %08lx\n",hr);exit(2);}
    hr=IDXGISwapChain_GetBuffer(r->swap,0,&IID_ID3D11Texture2D,(void**)&texture);
    if(SUCCEEDED(hr))hr=ID3D11Device_CreateRenderTargetView(r->device,(ID3D11Resource*)texture,0,&r->target);
    if(texture)ID3D11Texture2D_Release(texture);
    if(FAILED(hr)){printf("FAIL render target %08lx\n",hr);exit(2);}
}
static void texture_probe(struct renderer *r)
{
    ID3D11Resource *resource=0;ID3D11Texture2D *staging=0;D3D11_TEXTURE2D_DESC desc;D3D11_MAPPED_SUBRESOURCE mapped;
    ID3D11RenderTargetView_GetResource(r->target,&resource);
    ID3D11Texture2D_GetDesc((ID3D11Texture2D*)resource,&desc);
    desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;desc.MiscFlags=0;
    HRESULT hr=ID3D11Device_CreateTexture2D(r->device,&desc,0,&staging);
    if(SUCCEEDED(hr)){
        ID3D11DeviceContext_CopyResource(r->context,(ID3D11Resource*)staging,resource);
        hr=ID3D11DeviceContext_Map(r->context,(ID3D11Resource*)staging,0,D3D11_MAP_READ,0,&mapped);
        if(SUCCEEDED(hr)){
            const unsigned char *p=mapped.pData;
            printf("GPU_TEXTURE rgba=%u,%u,%u,%u dimensions=%u,%u\n",p[0],p[1],p[2],p[3],desc.Width,desc.Height);
            ID3D11DeviceContext_Unmap(r->context,(ID3D11Resource*)staging,0);
        }
        ID3D11Texture2D_Release(staging);
    }
    if(FAILED(hr))printf("GPU_TEXTURE failure=%08lx\n",hr);
    ID3D11Resource_Release(resource);
}
static void present(struct renderer *r)
{
    const float red[4]={1,0,0,1};
    for(unsigned i=0;i<4;i++){
        ID3D11DeviceContext_OMSetRenderTargets(r->context,1,&r->target,0);
        ID3D11DeviceContext_ClearRenderTargetView(r->context,r->target,red);
        ID3D11DeviceContext_Flush(r->context);
        if(i==0)texture_probe(r);
        HRESULT hr=IDXGISwapChain_Present(r->swap,0,0);
        if(hr!=S_OK){printf("FAIL Present status=%08lx\n",hr);failures++;}
        Sleep(30);pump();
    }
}
static void resize_renderer(struct renderer *r, UINT width, UINT height)
{
    ID3D11Texture2D *texture=0;
    ID3D11DeviceContext_ClearState(r->context);ID3D11DeviceContext_Flush(r->context);
    ID3D11RenderTargetView_Release(r->target);r->target=0;
    HRESULT hr=IDXGISwapChain_ResizeBuffers(r->swap,0,width,height,DXGI_FORMAT_UNKNOWN,0);
    if(SUCCEEDED(hr))hr=IDXGISwapChain_GetBuffer(r->swap,0,&IID_ID3D11Texture2D,(void**)&texture);
    if(SUCCEEDED(hr))hr=ID3D11Device_CreateRenderTargetView(r->device,(ID3D11Resource*)texture,0,&r->target);
    if(texture)ID3D11Texture2D_Release(texture);
    if(FAILED(hr)){printf("FAIL resize %08lx\n",hr);exit(2);}
}
static void stop(struct renderer *r)
{
    ID3D11DeviceContext_ClearState(r->context);ID3D11DeviceContext_Flush(r->context);
    ID3D11RenderTargetView_Release(r->target);IDXGISwapChain_Release(r->swap);
    ID3D11DeviceContext_Release(r->context);ID3D11Device_Release(r->device);Sleep(300);pump();
}
static void run_case(const char *cls, BOOL child, BOOL retained)
{
    struct renderer r={0};RECT rect; HWND parent=0,w;
    if(child)parent=CreateWindowA("probeParent","Private GPU regression",WS_OVERLAPPEDWINDOW|WS_VISIBLE|WS_CLIPCHILDREN|WS_CLIPSIBLINGS,20,20,640,480,0,0,GetModuleHandleW(0),0);
    w=CreateWindowA(cls,"Private GPU regression",(child?WS_CHILD:WS_OVERLAPPEDWINDOW)|WS_VISIBLE|WS_CLIPCHILDREN|WS_CLIPSIBLINGS,20,20,320,240,parent,0,GetModuleHandleW(0),0);
    if(!w){puts("FAIL CreateWindow");exit(2);}pump();GetClientRect(w,&rect);
    start(&r,w,rect.right,rect.bottom);
    fill(w,rect.right,rect.bottom);check("before-first-present",w,50,50,RGB(0,255,0));
    present(&r);check("GPU-red",w,50,50,RGB(255,0,0));
    fill(w,rect.right,rect.bottom);check("full-client-fill",w,50,50,retained?RGB(255,0,0):RGB(0,255,0));
    present(&r);fill(w,20,20);check("partial-fill",w,10,10,RGB(0,255,0));
    if(child&&!strcmp(cls,"loupeView")){
        present(&r);
        HWND overlay=CreateWindowA("ordinaryView","Overlap",WS_CHILD|WS_VISIBLE|WS_CLIPSIBLINGS,
                                   20,20,rect.right,rect.bottom,parent,0,GetModuleHandleW(0),0);
        if(!overlay){puts("FAIL overlap window");exit(2);}
        SetWindowPos(overlay,HWND_TOP,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);pump();
        fill(overlay,rect.right,rect.bottom);check("overlapping-owner",overlay,50,50,RGB(0,255,0));
        DestroyWindow(overlay);pump();present(&r);check("after-overlap",w,50,50,RGB(255,0,0));
        SetWindowPos(w,0,20,20,400,280,SWP_NOZORDER|SWP_NOACTIVATE);pump();GetClientRect(w,&rect);
        fill(w,rect.right,rect.bottom);check("resize-before-present",w,50,50,RGB(0,255,0));
        resize_renderer(&r,rect.right,rect.bottom);present(&r);check("resized-GPU-red",w,350,250,RGB(255,0,0));
        fill(w,rect.right,rect.bottom);check("resized-full-fill",w,350,250,retained?RGB(255,0,0):RGB(0,255,0));
    }
    stop(&r);fill(w,rect.right,rect.bottom);check("after-renderer-release",w,50,50,RGB(0,255,0));
    DestroyWindow(w);pump();
    if(child&&!strcmp(cls,"loupeView")){
        w=CreateWindowA(cls,"Recreated",WS_CHILD|WS_VISIBLE|WS_CLIPSIBLINGS,
                        20,20,320,240,parent,0,GetModuleHandleW(0),0);
        if(!w){puts("FAIL recreated window");exit(2);}
        pump();fill(w,320,240);check("recreated-no-renderer",w,50,50,RGB(0,255,0));DestroyWindow(w);
    }
    if(parent)DestroyWindow(parent);
    pump();
}
int main(int argc,char **argv)
{
    BOOL retained=argc==2&&!strcmp(argv[1],"retained");
    /* Wine intentionally omits WAYLAND_DISPLAY from the Windows environment.
     * The Python runner validates compositor ownership before setting this gate. */
    const char *display=getenv("DISPLAY"),*fixture=getenv("LRCC_PRIVATE_FIXTURE");
    if(!getenv("LRCC_CAPTURE_DIR")||!display||strcmp(display,":1")||!fixture||strcmp(fixture,"lightroom-test:1")){puts("Refusing non-fixture display");return 2;}
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);
    const char *classes[]={"probeParent","loupeView","ordinaryView"};
    for(unsigned i=0;i<3;i++){WNDCLASSA cls={0};cls.lpfnWndProc=DefWindowProcA;cls.hInstance=GetModuleHandleW(0);cls.lpszClassName=classes[i];if(!RegisterClassA(&cls))return 2;}
    puts("CASE child loupeView");run_case("loupeView",TRUE,retained);
    puts("CASE unrelated child");run_case("ordinaryView",TRUE,FALSE);
    puts("CASE top-level loupeView");run_case("loupeView",FALSE,FALSE);
    printf("Failures: %u\n",failures);return failures?1:0;
}
