#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char *action;
static int x,y;
static void menu(HWND w, HMENU m){
 for(int i=0;i<GetMenuItemCount(m);i++){wchar_t t[256];GetMenuStringW(m,i,t,256,MF_BYPOSITION);HMENU sub=GetSubMenu(m,i);UINT id=GetMenuItemID(m,i);wprintf(L"Menu %u %ls\n",id,t);if(sub)menu(w,sub);else if(!strcmp(action,"preferences") && wcsstr(t,L"Preferences")){wprintf(L"Preferences command %u\n",id);PostMessageW(w,WM_COMMAND,id,0);}}
}
static BOOL CALLBACK visit(HWND w, LPARAM unused){
 wchar_t cls[128]; GetClassNameW(w,cls,128);
 if(wcscmp(cls,L"Lightroom CC Main Window"))return TRUE;
 RECT r;GetClientRect(w,&r);printf("Client %ld x %ld\n",r.right,r.bottom);
 if(!strcmp(action,"click-relative")){x=x*r.right/10000;y=y*r.bottom/10000;action="click";}
 if(!strcmp(action,"preferences")||!strcmp(action,"list-menu")){menu(w,GetMenu(w));}
 else if(!strcmp(action,"menu-open")){PostMessageW(w,WM_SYSCOMMAND,SC_KEYMENU,'f');}
 else if(!strcmp(action,"menu-close")){PostMessageW(w,WM_CANCELMODE,0,0);PostMessageW(w,WM_KEYDOWN,VK_ESCAPE,0);PostMessageW(w,WM_KEYUP,VK_ESCAPE,0);}
 else if(!strcmp(action,"zoom")){PostMessageW(w,WM_KEYDOWN,VK_SPACE,0x00390001);PostMessageW(w,WM_CHAR,0x20,0x00390001);PostMessageW(w,WM_KEYUP,VK_SPACE,0xc0390001);}
 else if(!strcmp(action,"pan")){
 SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);
 GetClientRect(w,&r); POINT pt={r.right*4/10,r.bottom*4/10};
 for(int i=0;i<20;i++){ HWND child=ChildWindowFromPointEx(w,pt,CWP_SKIPINVISIBLE|CWP_SKIPDISABLED|CWP_SKIPTRANSPARENT);if(!child||child==w)break;MapWindowPoints(w,child,&pt,1);w=child;}
 PostMessageW(w,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(pt.x,pt.y));
 for(int i=0;i<120;i++){int dx=(i<60?i:120-i)*3; PostMessageW(w,WM_MOUSEMOVE,MK_LBUTTON,MAKELPARAM(pt.x+dx,pt.y));Sleep(16);}
 PostMessageW(w,WM_LBUTTONUP,0,MAKELPARAM(pt.x,pt.y));
 puts("Pan messages delivered; no global pointer movement.");
 }
 else if(!strcmp(action,"close")){PostMessageW(w,WM_CLOSE,0,0);puts("Requested Lightroom close.");}
 else if(!strcmp(action,"double-click")){
 LPARAM xy=MAKELPARAM(x,y);
 PostMessageW(w,WM_LBUTTONDOWN,MK_LBUTTON,xy);PostMessageW(w,WM_LBUTTONUP,0,xy);
 PostMessageW(w,WM_LBUTTONDBLCLK,MK_LBUTTON,xy);PostMessageW(w,WM_LBUTTONUP,0,xy);
 puts("Sent double-click to Lightroom.");
 }
 else if(!strcmp(action,"click")){
 POINT pt={x,y};for(int i=0;i<20;i++){HWND child=ChildWindowFromPointEx(w,pt,CWP_SKIPINVISIBLE|CWP_SKIPDISABLED|CWP_SKIPTRANSPARENT);if(!child||child==w)break;MapWindowPoints(w,child,&pt,1);w=child;}x=pt.x;y=pt.y;GetClassNameW(w,cls,128);wprintf(L"Target class %ls at %d,%d\n",cls,x,y);
 LPARAM xy=MAKELPARAM(x,y);PostMessageW(w,WM_LBUTTONDOWN,MK_LBUTTON,xy);PostMessageW(w,WM_LBUTTONUP,0,xy);puts("Sent click to Lightroom.");
 }
 return FALSE;
}
int main(int argc,char**argv){if(argc<2)return 2;SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE);action=argv[1];if(argc==4){x=atoi(argv[2]);y=atoi(argv[3]);}EnumWindows(visit,0);return 0;}
