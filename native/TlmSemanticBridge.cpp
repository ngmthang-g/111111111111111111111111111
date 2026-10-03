#include <windows.h>
#include <cstdint>
#include <cstddef>
#include <climits>
#include <cstring>
#include <string>
#include "protocol.h"

using namespace cleanroute;

namespace {
using Il2CppDomain = void;
using Il2CppAssembly = void;
using Il2CppImage = void;
using Il2CppClass = void;
using Il2CppObject = void;
using Il2CppString = void;
using Il2CppType = void;
using MethodInfo = void;
using FieldInfo = void;

HANDLE g_mapping = nullptr;
SharedBlock* g_shared = nullptr;

template <class T, size_t N> constexpr size_t ArrayCount(T (&)[N]) noexcept { return N; }

template<class T> bool Resolve(HMODULE m, const char* name, T& out) {
    FARPROC p = GetProcAddress(m, name); out = nullptr; if (!p) return false;
    static_assert(sizeof(p) == sizeof(out)); std::memcpy(&out, &p, sizeof(out)); return true;
}
void SetText(wchar_t* out, size_t cap, const wchar_t* text) {
    if (!out || !cap) return; size_t i=0; if (text) while (i+1<cap && text[i]) {out[i]=text[i]; ++i;} out[i]=0;
}
void Append(wchar_t* out,size_t cap,const wchar_t* text){if(!out||!text||!cap)return;size_t n=0;while(n+1<cap&&out[n])++n;size_t i=0;while(n+1<cap&&text[i])out[n++]=text[i++];out[n]=0;}
void AppendInt(wchar_t* out,size_t cap,int v){wchar_t b[32]{};wsprintfW(b,L"%d",v);Append(out,cap,b);}

struct Api {
    HMODULE module=nullptr;
    Il2CppDomain* (__cdecl* domain_get)()=nullptr;
    const Il2CppAssembly* (__cdecl* domain_assembly_open)(Il2CppDomain*,const char*)=nullptr;
    const Il2CppImage* (__cdecl* assembly_get_image)(const Il2CppAssembly*)=nullptr;
    Il2CppClass* (__cdecl* class_from_name)(const Il2CppImage*,const char*,const char*)=nullptr;
    const MethodInfo* (__cdecl* class_get_methods)(Il2CppClass*,void**)=nullptr;
    const char* (__cdecl* method_get_name)(const MethodInfo*)=nullptr;
    uint32_t (__cdecl* method_get_param_count)(const MethodInfo*)=nullptr;
    uint32_t (__cdecl* method_get_flags)(const MethodInfo*,uint32_t*)=nullptr;
    Il2CppObject* (__cdecl* runtime_invoke)(const MethodInfo*,void*,void**,void**)=nullptr;
    void* (__cdecl* object_unbox)(Il2CppObject*)=nullptr;
    Il2CppClass* (__cdecl* object_get_class)(Il2CppObject*)=nullptr;
    Il2CppString* (__cdecl* string_new)(const char*)=nullptr;
    int32_t (__cdecl* string_length)(Il2CppString*)=nullptr;
    const wchar_t* (__cdecl* string_chars)(Il2CppString*)=nullptr;

    bool load(wchar_t* detail,size_t cap){
        if(module)return true; module=GetModuleHandleW(L"GameAssembly.dll");
        if(!module){SetText(detail,cap,L"GameAssembly.dll chưa sẵn sàng");return false;}
#define NEED(x) if(!Resolve(module,"il2cpp_" #x,x)){SetText(detail,cap,L"Thiếu IL2CPP export bắt buộc");return false;}
        NEED(domain_get); NEED(domain_assembly_open); NEED(assembly_get_image); NEED(class_from_name);
        NEED(class_get_methods); NEED(method_get_name); NEED(method_get_param_count); NEED(method_get_flags);
        NEED(runtime_invoke); NEED(object_unbox); NEED(object_get_class); NEED(string_new); NEED(string_length); NEED(string_chars);
#undef NEED
        return true;
    }
} g_api;

const Il2CppImage* AssemblyImage(wchar_t* detail,size_t cap){
    if(!g_api.load(detail,cap))return nullptr; auto*d=g_api.domain_get(); if(!d)return nullptr;
    auto*a=g_api.domain_assembly_open(d,"Assembly-CSharp"); if(!a){SetText(detail,cap,L"Không mở được Assembly-CSharp");return nullptr;}
    return g_api.assembly_get_image(a);
}
const MethodInfo* FindMethod(Il2CppClass* c,const char* name,uint32_t argc,bool requireStatic=false){
    if(!c)return nullptr; void*it=nullptr; while(auto*m=g_api.class_get_methods(c,&it)){
        const char*n=g_api.method_get_name(m); if(!n||std::strcmp(n,name)!=0||g_api.method_get_param_count(m)!=argc)continue;
        if(requireStatic){uint32_t impl=0; if((g_api.method_get_flags(m,&impl)&0x10u)==0)continue;} return m;
    } return nullptr;
}
bool InvokeObj(const MethodInfo*m,void*self,void**args,Il2CppObject*&out,wchar_t*d,size_t cap){
    if(!m){SetText(d,cap,L"Method chưa resolve");return false;} void*exc=nullptr;out=g_api.runtime_invoke(m,self,args,&exc);if(exc){SetText(d,cap,L"IL2CPP invoke exception");return false;}return true;
}
bool InvokeVoid(const MethodInfo*m,void*self,void**args,wchar_t*d,size_t cap){Il2CppObject*o=nullptr;return InvokeObj(m,self,args,o,d,cap);}
bool InvokeI32(const MethodInfo*m,void*self,void**args,int32_t&out,wchar_t*d,size_t cap){Il2CppObject*o=nullptr;if(!InvokeObj(m,self,args,o,d,cap)||!o)return false;void*p=g_api.object_unbox(o);if(!p)return false;out=*reinterpret_cast<int32_t*>(p);return true;}
bool GetterI32(Il2CppClass*c,const char*name,void*self,int32_t&out,wchar_t*d,size_t cap){return InvokeI32(FindMethod(c,name,0,false),self,nullptr,out,d,cap);}

struct Classes {Il2CppClass* game=nullptr;Il2CppClass* network=nullptr;Il2CppClass* shared=nullptr;Il2CppClass* session=nullptr;Il2CppClass* autoPath=nullptr;Il2CppClass* gui=nullptr;};
bool ResolveClasses(Classes&c,wchar_t*d,size_t cap){
    auto*img=AssemblyImage(d,cap); if(!img)return false;
    c.game=g_api.class_from_name(img,"FGStudio.LuaSystem.API","LuaSystemAPI_Game");
    c.network=g_api.class_from_name(img,"FGStudio.LuaSystem.API","LuaSystemAPI_Network");
    c.gui=g_api.class_from_name(img,"FGStudio.LuaSystem.API","LuaSystemAPI_GUI");
    c.shared=g_api.class_from_name(img,"FGStudio.LuaSystem","LuaSystemSharedData");
    c.session=g_api.class_from_name(img,"FGStudio.Game.Logic","SessionData");
    c.autoPath=g_api.class_from_name(img,"FGStudio.Engine.Logic","AutoPathManager");
    if(!c.game||!c.shared||!c.session||!c.autoPath){SetText(d,cap,L"Thiếu class semantic bắt buộc");return false;} return true;
}
bool MapReady(const Classes&c,int32_t&ready,int32_t&waiting,wchar_t*d,size_t cap){
    if(!InvokeI32(FindMethod(c.game,"IsMapReady",0,true),nullptr,nullptr,ready,d,cap))return false;
    if(!InvokeI32(FindMethod(c.session,"get_WaitingChangeMap",0,true),nullptr,nullptr,waiting,d,cap))return false; return true;
}
bool Safe(const Classes&c,wchar_t*d,size_t cap){int32_t r=0,w=0;if(!MapReady(c,r,w,d,cap))return false;if(!r||w){SetText(d,cap,L"Action bị chặn: đang chuyển map");return false;}return true;}
bool Leader(const Classes&c,Il2CppObject*&obj,Il2CppClass*&klass,wchar_t*d,size_t cap){
    const MethodInfo*m=FindMethod(c.shared,"get_LeaderRoleData",0,true); if(!InvokeObj(m,nullptr,nullptr,obj,d,cap)||!obj){SetText(d,cap,L"LeaderRoleData chưa sẵn sàng");return false;} klass=g_api.object_get_class(obj);return klass!=nullptr;
}
bool ReadState(Snapshot&s,wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap))return false;s={};int32_t ready=0,waiting=0;if(!MapReady(c,ready,waiting,d,cap))return false;
    s.mapReady=ready?1:0;s.waitingChangeMap=waiting?1:0;s.validMask|=ValidMapTransition;if(!ready||waiting){SetText(d,cap,L"Đang chuyển map");return true;}
    Il2CppObject*o=nullptr;Il2CppClass*k=nullptr;if(!Leader(c,o,k,d,cap))return false;int32_t role=0,map=0,x=0,y=0,riding=0;
    if(!GetterI32(k,"get_RoleID",o,role,d,cap)||role<=0)return false;
    if(!GetterI32(k,"get_MapID",o,map,d,cap)||map<=0)return false;
    if(!GetterI32(k,"get_PosX",o,x,d,cap)||!GetterI32(k,"get_PosY",o,y,d,cap)){SetText(d,cap,L"Không đọc được PosX/PosY");return false;}
    if(!GetterI32(k,"get_IsRiding",o,riding,d,cap))riding=0;s.roleID=role;s.mapID=map;s.x=x;s.y=y;s.riding=riding?1:0;s.validMask|=ValidIdentity|ValidMap|ValidPosition|ValidRiding;
    int32_t team=0;if(GetterI32(k,"get_TeamID",o,team,d,cap)){s.teamID=team;s.validMask|=ValidTeam;}
    int32_t level=0,faction=0;if(GetterI32(k,"get_Level",o,level,d,cap)){s.level=level;s.validMask|=ValidProfile;}if(GetterI32(k,"get_FactionID",o,faction,d,cap)){s.factionID=faction;s.validMask|=ValidProfile;}
    int32_t hp=0,maxHP=0;if(GetterI32(k,"get_HP",o,hp,d,cap)&&GetterI32(k,"get_MaxHP",o,maxHP,d,cap)){s.hp=hp;s.maxHP=maxHP;s.validMask|=ValidVitals;}
    int32_t dead=0;if(GetterI32(k,"get_IsDeath",o,dead,d,cap)){s.dead=dead?1:0;s.validMask|=ValidLifeState;}
    int32_t autoFlag=1;if(InvokeI32(FindMethod(c.game,"get_EnableAutoF1",0,true),nullptr,nullptr,autoFlag,d,cap)){s.autoFight=autoFlag?0:1;s.validMask|=ValidAutoFight;}
    int32_t freeBag=-1;if(InvokeI32(FindMethod(c.game,"GetFreeBagSpace",0,true),nullptr,nullptr,freeBag,d,cap)&&freeBag>=0){s.freeBagSpace=freeBag;s.validMask|=ValidBagSpace;}
    auto*instM=FindMethod(c.autoPath,"get_Instance",0,true);Il2CppObject*ap=nullptr;if(InvokeObj(instM,nullptr,nullptr,ap,d,cap)&&ap){auto*ac=g_api.object_get_class(ap);int32_t path=0;if(GetterI32(ac,"get_IsAutoPathing",ap,path,d,cap)){s.autoPathing=path?1:0;s.validMask|=ValidAutoPath;}}
    if(auto*nm=FindMethod(k,"get_Name",0,false)){Il2CppObject*no=nullptr;if(InvokeObj(nm,o,nullptr,no,d,cap)&&no){auto*str=reinterpret_cast<Il2CppString*>(no);int n=g_api.string_length(str);const wchar_t*ch=g_api.string_chars(str);if(ch){int lim=n<63?n:63;for(int i=0;i<lim;++i)s.characterName[i]=ch[i];s.characterName[lim]=0;}}}
    SetText(d,cap,L"STATE role=");AppendInt(d,cap,s.roleID);Append(d,cap,L" team=");AppendInt(d,cap,s.teamID);Append(d,cap,L" map=");AppendInt(d,cap,s.mapID);Append(d,cap,L" pos=");AppendInt(d,cap,s.x);Append(d,cap,L",");AppendInt(d,cap,s.y);return true;
}
bool StartPath(int map,int x,int y,wchar_t*d,size_t cap){Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;Il2CppObject*ap=nullptr;if(!InvokeObj(FindMethod(c.autoPath,"get_Instance",0,true),nullptr,nullptr,ap,d,cap)||!ap)return false;auto*k=g_api.object_get_class(ap);auto*m=FindMethod(k,"StartAutoPath",3,false);int32_t a=map,b=x,cc=y;void*args[]={&a,&b,&cc};if(!InvokeVoid(m,ap,args,d,cap))return false;SetText(d,cap,L"Đã gửi AutoPath");return true;}
bool StopPath(wchar_t*d,size_t cap){Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;if(!InvokeVoid(FindMethod(c.game,"StopAutoPath",0,true),nullptr,nullptr,d,cap))return false;SetText(d,cap,L"Đã gửi StopAutoPath");return true;}
bool ClickNpc(int id,wchar_t*d,size_t cap){Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;int32_t v=id;void*args[]={&v};if(!InvokeVoid(FindMethod(c.game,"ClickNPC",1,true),nullptr,args,d,cap))return false;SetText(d,cap,L"Đã gửi ClickNPC");return true;}
bool ToggleRide(bool desired,wchar_t*d,size_t cap){Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;Il2CppObject*o=nullptr;Il2CppClass*k=nullptr;if(!Leader(c,o,k,d,cap))return false;int32_t riding=0;if(!GetterI32(k,"get_IsRiding",o,riding,d,cap))return false;if((riding!=0)==desired){SetText(d,cap,L"Ride state đã đúng");return true;}int32_t slot=0;if(!InvokeI32(FindMethod(c.game,"get_CurrentMountSlot",0,true),nullptr,nullptr,slot,d,cap))return false;void*args[]={&slot};if(!InvokeVoid(FindMethod(c.game,"SendToggleRideState",1,true),nullptr,args,d,cap))return false;SetText(d,cap,L"Đã gửi ToggleRide");return true;}
bool FindUi(const Classes&c,const char*name,Il2CppObject*&ui,wchar_t*d,size_t cap){if(!c.gui){SetText(d,cap,L"LuaSystemAPI_GUI chưa resolve");return false;}auto*m=FindMethod(c.gui,"FindUI",1,true);if(!m)m=FindMethod(c.gui,"MainFindUI",1,true);if(!m)return false;Il2CppString*s=g_api.string_new(name);void*args[]={&s};return InvokeObj(m,nullptr,args,ui,d,cap)&&ui;}
bool AutoFight(bool start,wchar_t*d,size_t cap){Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;Il2CppObject*ui=nullptr;if(!FindUi(c,"AutoFight_Main",ui,d,cap))return false;auto*k=g_api.object_get_class(ui);auto*m=FindMethod(k,"StartAutoFight",1,false);if(!m){SetText(d,cap,L"StartAutoFight không phải managed method trên UI build này");return false;}int32_t mode=start?1:0;void*args[]={&mode};if(!InvokeVoid(m,ui,args,d,cap))return false;SetText(d,cap,start?L"Đã StartAutoFight(Train)":L"Đã StopAutoFight");return true;}

bool SendNetworkPacket(const Classes&c,int32_t packetID,const std::string&payload,wchar_t*d,size_t cap){
    if(!c.network){SetText(d,cap,L"Thiếu LuaSystemAPI_Network");return false;}
    auto*m=FindMethod(c.network,"SendPacket",2,true);if(!m){SetText(d,cap,L"Không resolve Network.SendPacket(Int32,String)");return false;}
    Il2CppString*s=g_api.string_new(payload.c_str());if(!s){SetText(d,cap,L"Không tạo được packet payload");return false;}
    void*args[]={&packetID,&s};return InvokeVoid(m,nullptr,args,d,cap);
}
bool PartyCreate(wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;
    Il2CppObject*o=nullptr;Il2CppClass*k=nullptr;if(!Leader(c,o,k,d,cap))return false;
    int32_t team=0;if(GetterI32(k,"get_TeamID",o,team,d,cap)&&team>0&&team!=-1){SetText(d,cap,L"Đã có tổ đội");return true;}
    if(!SendNetworkPacket(c,200057,"0",d,cap))return false;
    SetText(d,cap,L"Đã gửi tạo đội action=0");return true;
}
bool PartyLeave(wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;
    Il2CppObject*o=nullptr;Il2CppClass*k=nullptr;if(!Leader(c,o,k,d,cap))return false;
    int32_t role=0,team=0;if(!GetterI32(k,"get_RoleID",o,role,d,cap)||role<=0)return false;
    if(GetterI32(k,"get_TeamID",o,team,d,cap)&&team<=0){SetText(d,cap,L"Không ở trong tổ đội");return true;}
    if(!SendNetworkPacket(c,200057,std::string("4:")+std::to_string(role),d,cap))return false;
    SetText(d,cap,L"Đã gửi rời đội 4:selfRoleID");return true;
}
bool PartyInvite(int32_t targetRoleID,wchar_t*d,size_t cap){
    if(targetRoleID<=0){SetText(d,cap,L"RoleID mời không hợp lệ");return false;}
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;
    if(!SendNetworkPacket(c,200051,std::string("5:")+std::to_string(targetRoleID),d,cap))return false;
    SetText(d,cap,L"Đã gửi mời đội 5:targetRoleID");return true;
}
bool PartyJoin(int32_t targetRoleID,wchar_t*d,size_t cap){
    if(targetRoleID<=0){SetText(d,cap,L"RoleID trưởng nhóm không hợp lệ");return false;}
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;
    if(!SendNetworkPacket(c,200051,std::string("9:")+std::to_string(targetRoleID),d,cap))return false;
    SetText(d,cap,L"Đã gửi xin vào đội 9:targetRoleID");return true;
}
bool ReviveNormal(wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;
    Il2CppObject*o=nullptr;Il2CppClass*k=nullptr;if(!Leader(c,o,k,d,cap))return false;
    int32_t dead=0;if(!GetterI32(k,"get_IsDeath",o,dead,d,cap)||!dead){SetText(d,cap,L"Không Đầu thai vì nhân vật chưa chết");return false;}
    if(!SendNetworkPacket(c,200063,"1",d,cap))return false;
    SetText(d,cap,L"Đã gửi Đầu thai type=1");return true;
}

bool EnsureShared(){
    if(g_shared)return true;wchar_t name[96]{};MappingName(GetCurrentProcessId(),name,ArrayCount(name));g_mapping=OpenFileMappingW(FILE_MAP_ALL_ACCESS,FALSE,name);if(!g_mapping)return false;
    g_shared=reinterpret_cast<SharedBlock*>(MapViewOfFile(g_mapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(SharedBlock)));
    if(!g_shared||g_shared->magic!=kMagic||g_shared->protocolVersion!=kProtocolVersion||g_shared->targetPid!=GetCurrentProcessId()){if(g_shared)UnmapViewOfFile(g_shared);if(g_mapping)CloseHandle(g_mapping);g_shared=nullptr;g_mapping=nullptr;return false;}
    InterlockedExchange(&g_shared->bridgeLoaded,1);return true;
}
void ProcessRequest(){
    if(!EnsureShared())return;LONG seq=g_shared->requestSeq;if(seq<=0||seq==g_shared->completedSeq)return;if(InterlockedCompareExchange(&g_shared->bridgeBusy,1,0)!=0)return;
    Response r{};wchar_t detail[512]{};bool ok=false;
    if(GetCurrentThreadId()!=g_shared->targetWindowThreadId){SetText(detail,ArrayCount(detail),L"Sai callback thread");}
    else {auto cmd=static_cast<Command>(g_shared->request.command);switch(cmd){
        case Command::ReadState: ok=ReadState(r.snapshot,detail,ArrayCount(detail));break;
        case Command::ToggleRide: ok=ToggleRide(g_shared->request.arg0!=0,detail,ArrayCount(detail));break;
        case Command::StartPath: ok=StartPath(g_shared->request.arg0,g_shared->request.arg1,g_shared->request.arg2,detail,ArrayCount(detail));break;
        case Command::StopPath: ok=StopPath(detail,ArrayCount(detail));break;
        case Command::ClickNpc: ok=ClickNpc(g_shared->request.arg0,detail,ArrayCount(detail));break;
        case Command::StartAutoFight: ok=AutoFight(true,detail,ArrayCount(detail));break;
        case Command::StopAutoFight: ok=AutoFight(false,detail,ArrayCount(detail));break;
        case Command::PartyCreate: ok=PartyCreate(detail,ArrayCount(detail));break;
        case Command::PartyLeave: ok=PartyLeave(detail,ArrayCount(detail));break;
        case Command::PartyInvite: ok=PartyInvite(g_shared->request.arg0,detail,ArrayCount(detail));break;
        case Command::PartyJoin: ok=PartyJoin(g_shared->request.arg0,detail,ArrayCount(detail));break;
        case Command::Revive:
        case Command::ReviveNormal: ok=ReviveNormal(detail,ArrayCount(detail));break;
        default: SetText(detail,ArrayCount(detail),L"Command chưa được port trong T04 core bridge");break;
    }}
    r.ok=ok?1:0;SetText(r.detail,ArrayCount(r.detail),detail);g_shared->response=r;MemoryBarrier();InterlockedExchange(&g_shared->completedSeq,seq);InterlockedExchange(&g_shared->bridgeBusy,0);
}
} // namespace

extern "C" __declspec(dllexport) LRESULT CALLBACK TlmGetMessageHook(int code,WPARAM wParam,LPARAM lParam){
    (void)wParam;if(code>=0&&lParam){const MSG*msg=reinterpret_cast<const MSG*>(lParam);if(msg->message==kWakeMessage)ProcessRequest();}return CallNextHookEx(nullptr,code,wParam,lParam);
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(instance);else if(reason==DLL_PROCESS_DETACH){if(g_shared)UnmapViewOfFile(g_shared);if(g_mapping)CloseHandle(g_mapping);g_shared=nullptr;g_mapping=nullptr;}return TRUE;}
