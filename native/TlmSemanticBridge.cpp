#include <windows.h>
#include <cstdint>
#include <cstddef>
#include <climits>
#include <cstring>
#include <string>
#include <algorithm>
#include <vector>
#include <cwchar>
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
    const Il2CppImage* (__cdecl* get_corlib)()=nullptr;
    Il2CppObject* (__cdecl* array_new)(Il2CppClass*,std::uintptr_t)=nullptr;
    Il2CppClass* (__cdecl* class_get_parent)(Il2CppClass*)=nullptr;
    FieldInfo* (__cdecl* class_get_field_from_name)(Il2CppClass*,const char*)=nullptr;
    const Il2CppType* (__cdecl* field_get_type)(FieldInfo*)=nullptr;
    void (__cdecl* field_get_value)(Il2CppObject*,FieldInfo*,void*)=nullptr;
    const Il2CppType* (__cdecl* method_get_return_type)(const MethodInfo*)=nullptr;
    char* (__cdecl* type_get_name)(const Il2CppType*)=nullptr;
    void (__cdecl* free_fn)(void*)=nullptr;

    bool load(wchar_t* detail,size_t cap){
        if(module)return true; module=GetModuleHandleW(L"GameAssembly.dll");
        if(!module){SetText(detail,cap,L"GameAssembly.dll chưa sẵn sàng");return false;}
#define NEED(x) if(!Resolve(module,"il2cpp_" #x,x)){SetText(detail,cap,L"Thiếu IL2CPP export bắt buộc");return false;}
        NEED(domain_get); NEED(domain_assembly_open); NEED(assembly_get_image); NEED(class_from_name);
        NEED(class_get_methods); NEED(method_get_name); NEED(method_get_param_count); NEED(method_get_flags);
        NEED(runtime_invoke); NEED(object_unbox); NEED(object_get_class); NEED(string_new); NEED(string_length); NEED(string_chars);
        NEED(get_corlib); NEED(array_new); NEED(class_get_parent); NEED(class_get_field_from_name);
        NEED(field_get_type); NEED(field_get_value); NEED(method_get_return_type); NEED(type_get_name);
#undef NEED
        if(!Resolve(module,"il2cpp_free",free_fn)){SetText(detail,cap,L"Thiếu IL2CPP export bắt buộc");return false;}
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

bool Eq(const char*a,const char*b){return a&&b&&std::strcmp(a,b)==0;}
bool CopyManagedString(Il2CppString*value,wchar_t*out,size_t cap){
    if(!value||!out||!cap)return false;int32_t len=g_api.string_length(value);const wchar_t*chars=g_api.string_chars(value);
    if(len<0||len>4096||!chars)return false;size_t n=static_cast<size_t>(len);if(n+1>cap)n=cap-1;
    for(size_t i=0;i<n;++i)out[i]=chars[i];out[n]=0;return true;
}
bool InvokeScalar64(const MethodInfo*m,void*self,void**args,std::int64_t&out,wchar_t*d,size_t cap){
    out=0;if(!m){SetText(d,cap,L"Scalar method chưa resolve");return false;}
    const Il2CppType*rt=g_api.method_get_return_type(m);char*tn=rt?g_api.type_get_name(rt):nullptr;
    if(!tn){SetText(d,cap,L"Không đọc được return type");return false;}
    void*exc=nullptr;Il2CppObject*boxed=g_api.runtime_invoke(m,self,args,&exc);
    if(exc||!boxed){g_api.free_fn(tn);SetText(d,cap,L"Scalar getter lỗi/null");return false;}
    void*raw=g_api.object_unbox(boxed);if(!raw){g_api.free_fn(tn);SetText(d,cap,L"Không unbox scalar");return false;}
    bool ok=true;
    if(Eq(tn,"System.Boolean"))out=*reinterpret_cast<const std::uint8_t*>(raw)?1:0;
    else if(Eq(tn,"System.Int32"))out=*reinterpret_cast<const std::int32_t*>(raw);
    else if(Eq(tn,"System.UInt32"))out=*reinterpret_cast<const std::uint32_t*>(raw);
    else if(Eq(tn,"System.Int64"))out=*reinterpret_cast<const std::int64_t*>(raw);
    else if(Eq(tn,"System.UInt64")){auto v=*reinterpret_cast<const std::uint64_t*>(raw);if(v>static_cast<std::uint64_t>(INT64_MAX))ok=false;else out=static_cast<std::int64_t>(v);}
    else ok=false;
    g_api.free_fn(tn);if(!ok)SetText(d,cap,L"Return type scalar chưa hỗ trợ");return ok;
}
FieldInfo* FindField(Il2CppClass*klass,const char*name){
    for(Il2CppClass*c=klass;c;c=g_api.class_get_parent(c)){if(auto*f=g_api.class_get_field_from_name(c,name))return f;}return nullptr;
}
bool ObjectMember(Il2CppObject*object,const char*name,Il2CppObject*&out,wchar_t*d,size_t cap){
    out=nullptr;if(!object||!name)return false;Il2CppClass*k=g_api.object_get_class(object);if(!k)return false;
    std::string getter=std::string("get_")+name;if(auto*m=FindMethod(k,getter.c_str(),0,false)){wchar_t ignored[96]{};if(InvokeObj(m,object,nullptr,out,ignored,ArrayCount(ignored))&&out)return true;}
    if(auto*f=FindField(k,name)){g_api.field_get_value(object,f,&out);if(out)return true;}
    SetText(d,cap,L"Không đọc được member UI ");return false;
}
bool ReadScalarField64(Il2CppObject*object,Il2CppClass*klass,const char*name,std::int64_t&out){
    out=0;FieldInfo*f=FindField(klass,name);if(!f)return false;const Il2CppType*t=g_api.field_get_type(f);char*tn=t?g_api.type_get_name(t):nullptr;if(!tn)return false;
    bool ok=true;
    if(Eq(tn,"System.Boolean")){std::uint8_t v=0;g_api.field_get_value(object,f,&v);out=v?1:0;}
    else if(Eq(tn,"System.Int32")){std::int32_t v=0;g_api.field_get_value(object,f,&v);out=v;}
    else if(Eq(tn,"System.UInt32")){std::uint32_t v=0;g_api.field_get_value(object,f,&v);out=v;}
    else if(Eq(tn,"System.Int64")){std::int64_t v=0;g_api.field_get_value(object,f,&v);out=v;}
    else if(Eq(tn,"System.UInt64")){std::uint64_t v=0;g_api.field_get_value(object,f,&v);if(v>static_cast<std::uint64_t>(INT64_MAX))ok=false;else out=static_cast<std::int64_t>(v);}
    else ok=false;g_api.free_fn(tn);return ok;
}
bool ReadScalarMember64(Il2CppObject*object,Il2CppClass*klass,const char*name,std::int64_t&out){
    std::string getter=std::string("get_")+name;wchar_t ignored[96]{};
    if(InvokeScalar64(FindMethod(klass,getter.c_str(),0,false),object,nullptr,out,ignored,ArrayCount(ignored)))return true;
    return ReadScalarField64(object,klass,name,out);
}
bool InvokeEnum32Name(const MethodInfo*m,void*self,void**args,std::int32_t&value,wchar_t*name,size_t nameCap,wchar_t*d,size_t cap){
    value=0;if(name&&nameCap)name[0]=0;if(!m){SetText(d,cap,L"Enum method chưa resolve");return false;}
    void*exc=nullptr;Il2CppObject*boxed=g_api.runtime_invoke(m,self,args,&exc);if(exc||!boxed){SetText(d,cap,L"Enum getter lỗi/null");return false;}
    void*raw=g_api.object_unbox(boxed);if(!raw){SetText(d,cap,L"Không unbox enum");return false;}value=*reinterpret_cast<const std::int32_t*>(raw);
    if(name&&nameCap){Il2CppClass*k=g_api.object_get_class(boxed);const MethodInfo*toString=k?FindMethod(k,"ToString",0,false):nullptr;Il2CppObject*str=nullptr;wchar_t ignored[96]{};
        if(toString&&InvokeObj(toString,boxed,nullptr,str,ignored,ArrayCount(ignored))&&str)CopyManagedString(reinterpret_cast<Il2CppString*>(str),name,nameCap);}
    return true;
}
template<class T> bool WriteLocal(void*base,size_t offset,const T&value){
    if(!base)return false;SIZE_T done=0;auto*address=reinterpret_cast<unsigned char*>(base)+offset;
    return WriteProcessMemory(GetCurrentProcess(),address,&value,sizeof(value),&done)!=FALSE&&done==sizeof(value);
}

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
    wchar_t optional[160]{};
    int32_t team=0;if(GetterI32(k,"get_TeamID",o,team,optional,ArrayCount(optional))){s.teamID=team;s.validMask|=ValidTeam;}optional[0]=0;
    int32_t level=0,faction=0;if(GetterI32(k,"get_Level",o,level,optional,ArrayCount(optional))){s.level=level;s.validMask|=ValidProfile;}optional[0]=0;if(GetterI32(k,"get_FactionID",o,faction,optional,ArrayCount(optional))){s.factionID=faction;s.validMask|=ValidProfile;}optional[0]=0;
    int32_t hp=0,maxHP=0;if(GetterI32(k,"get_HP",o,hp,optional,ArrayCount(optional))){optional[0]=0;if(GetterI32(k,"get_MaxHP",o,maxHP,optional,ArrayCount(optional))){s.hp=hp;s.maxHP=maxHP;s.validMask|=ValidVitals;}}optional[0]=0;
    int32_t dead=0;if(GetterI32(k,"get_IsDeath",o,dead,optional,ArrayCount(optional))){s.dead=dead?1:0;s.validMask|=ValidLifeState;}
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

const MethodInfo* BagListMethod(const Classes&c){
    auto*m=FindMethod(c.game,"GetItemsAtSite",1,true);if(m)return m;
    return FindMethod(c.shared,"GetItemsAtSite",1,true);
}
const MethodInfo* BagItemAtSiteMethod(const Classes&c){
    auto*m=FindMethod(c.game,"GetItemAtSite",2,true);if(m)return m;
    return FindMethod(c.shared,"GetItemAtSite",2,true);
}
bool LooksLikeBagItemObject(Il2CppObject*object){
    if(!object)return false;Il2CppClass*k=g_api.object_get_class(object);if(!k)return false;
    return FindField(k,"ID")||FindMethod(k,"get_ID",0,false)
        ? (FindField(k,"ItemID")||FindMethod(k,"get_ItemID",0,false))!=nullptr
        : false;
}
bool TryUnwrapBagEnumeratorCurrent(Il2CppObject*current,Il2CppObject*&item){
    item=nullptr;if(!current)return true;if(LooksLikeBagItemObject(current)){item=current;return true;}
    Il2CppClass*k=g_api.object_get_class(current);auto*m=k?FindMethod(k,"get_Value",0,false):nullptr;if(!m)return false;
    wchar_t ignored[96]{};Il2CppObject*value=nullptr;if(!InvokeObj(m,current,nullptr,value,ignored,ArrayCount(ignored)))return false;
    if(!value||!LooksLikeBagItemObject(value))return false;item=value;return true;
}
bool TryReadBagIndexed(Il2CppObject*collection,Il2CppClass*cc,std::vector<Il2CppObject*>&items){
    items.clear();int32_t count=0;wchar_t ignored[128]{};
    if(!GetterI32(cc,"get_Count",collection,count,ignored,ArrayCount(ignored))||count<0||count>1000)return false;
    auto*getItem=FindMethod(cc,"get_Item",1,false);if(!getItem)return false;
    std::vector<Il2CppObject*>candidate;candidate.reserve(static_cast<size_t>(count));
    for(int32_t i=0;i<count;++i){int32_t index=i;void*args[]={&index};Il2CppObject*item=nullptr;wchar_t itemError[96]{};
        if(!InvokeObj(getItem,collection,args,item,itemError,ArrayCount(itemError)))return false;if(item)candidate.push_back(item);}
    items.swap(candidate);return true;
}
bool TryReadBagEnumerator(Il2CppObject*collection,Il2CppClass*cc,std::vector<Il2CppObject*>&items){
    items.clear();auto*getEnumerator=FindMethod(cc,"GetEnumerator",0,false);if(!getEnumerator)return false;
    Il2CppObject*enumerator=nullptr;wchar_t ignored[128]{};
    if(!InvokeObj(getEnumerator,collection,nullptr,enumerator,ignored,ArrayCount(ignored))||!enumerator)return false;
    Il2CppClass*ec=g_api.object_get_class(enumerator);if(!ec)return false;
    auto*moveNext=FindMethod(ec,"MoveNext",0,false);auto*getCurrent=FindMethod(ec,"get_Current",0,false);if(!moveNext||!getCurrent)return false;
    std::vector<Il2CppObject*>candidate;candidate.reserve(100);
    for(int guard=0;guard<1000;++guard){std::int64_t moved=0;wchar_t stepError[96]{};
        if(!InvokeScalar64(moveNext,enumerator,nullptr,moved,stepError,ArrayCount(stepError)))return false;
        if(!moved){items.swap(candidate);return true;}
        Il2CppObject*current=nullptr;if(!InvokeObj(getCurrent,enumerator,nullptr,current,stepError,ArrayCount(stepError)))return false;
        Il2CppObject*item=nullptr;if(!TryUnwrapBagEnumeratorCurrent(current,item))return false;if(item)candidate.push_back(item);}
    return false;
}
bool TryReadBagByPosition(const Classes&c,std::vector<Il2CppObject*>&items){
    items.clear();auto*m=BagItemAtSiteMethod(c);if(!m)return false;
    std::vector<Il2CppObject*>candidate;candidate.reserve(100);int successful=0;int32_t site=10;
    for(int32_t pos=0;pos<=100;++pos){void*args[]={&site,&pos};Il2CppObject*item=nullptr;wchar_t ignored[96]{};
        if(!InvokeObj(m,nullptr,args,item,ignored,ArrayCount(ignored)))continue;++successful;if(!item)continue;
        if(std::find(candidate.begin(),candidate.end(),item)==candidate.end())candidate.push_back(item);}
    if(successful==0)return false;items.swap(candidate);return true;
}
bool ReadBagObjects(const Classes&c,std::vector<Il2CppObject*>&items,int&freeSpace,wchar_t*d,size_t cap){
    items.clear();freeSpace=-1;bool readOk=false;
    if(auto*list=BagListMethod(c)){int32_t site=10;void*args[]={&site};Il2CppObject*collection=nullptr;
        if(InvokeObj(list,nullptr,args,collection,d,cap)&&collection){Il2CppClass*cc=g_api.object_get_class(collection);
            if(cc){readOk=TryReadBagIndexed(collection,cc,items);if(!readOk)readOk=TryReadBagEnumerator(collection,cc,items);}}}
    if(!readOk)readOk=TryReadBagByPosition(c,items);
    if(!readOk){SetText(d,cap,L"Không enumerate được tay nải qua GetItemsAtSite/GetItemAtSite");return false;}
    wchar_t ignored[96]{};int32_t freeBag=-1;if(InvokeI32(FindMethod(c.game,"GetFreeBagSpace",0,true),nullptr,nullptr,freeBag,ignored,ArrayCount(ignored))&&freeBag>=0)freeSpace=freeBag;
    return true;
}
bool StaticBoolByItemID(Il2CppClass*game,const char*methodName,std::int32_t itemID,bool&out){
    out=false;auto*m=FindMethod(game,methodName,1,true);if(!m)return false;void*args[]={&itemID};std::int64_t v=0;wchar_t ignored[96]{};
    if(!InvokeScalar64(m,nullptr,args,v,ignored,ArrayCount(ignored)))return false;out=v!=0;return true;
}
bool FillBagItemSnapshot(const Classes&c,Il2CppObject*object,BagItemSnapshot&out,wchar_t*d,size_t cap){
    out={};if(!object)return false;Il2CppClass*k=g_api.object_get_class(object);if(!k)return false;std::int64_t v=0;
    if(!ReadScalarMember64(object,k,"ID",v)||v<=0){SetText(d,cap,L"Bag item thiếu ID");return false;}out.instanceID=v;
    if(!ReadScalarMember64(object,k,"ItemID",v)||v<=0||v>INT32_MAX){SetText(d,cap,L"Bag item thiếu ItemID");return false;}out.itemID=static_cast<std::int32_t>(v);
    if(ReadScalarMember64(object,k,"Site",v)&&v>=INT32_MIN&&v<=INT32_MAX)out.site=static_cast<std::int32_t>(v);
    if(ReadScalarMember64(object,k,"Position",v)&&v>=INT32_MIN&&v<=INT32_MAX)out.position=static_cast<std::int32_t>(v);
    if(ReadScalarMember64(object,k,"Quantity",v)&&v>=0&&v<=INT32_MAX)out.quantity=static_cast<std::int32_t>(v);
    if(ReadScalarMember64(object,k,"Bound",v))out.bound=v?1:0;
    if(auto*m=FindMethod(c.game,"GetItemName",1,true)){std::int32_t id=out.itemID;void*args[]={&id};Il2CppObject*str=nullptr;wchar_t ignored[96]{};
        if(InvokeObj(m,nullptr,args,str,ignored,ArrayCount(ignored))&&str)CopyManagedString(reinterpret_cast<Il2CppString*>(str),out.name,ArrayCount(out.name));}
    if(auto*m=FindMethod(c.game,"GetItemType",1,true)){std::int32_t id=out.itemID;void*args[]={&id};(void)InvokeEnum32Name(m,nullptr,args,out.itemTypeCode,out.itemType,ArrayCount(out.itemType),d,cap);}
    out.isEquip=_wcsicmp(out.itemType,L"Equip")==0?1:0;
    if(out.isEquip){if(auto*m=FindMethod(c.game,"GetEquipType",1,true)){std::int32_t id=out.itemID;void*args[]={&id};(void)InvokeEnum32Name(m,nullptr,args,out.equipTypeCode,out.equipType,ArrayCount(out.equipType),d,cap);}out.isWeapon=_wcsicmp(out.equipType,L"Weapon")==0?1:0;}
    bool flag=false;if(StaticBoolByItemID(c.game,"IsItemThrowable",out.itemID,flag))out.throwable=flag?1:0;
    if(StaticBoolByItemID(c.game,"IsItemSellable",out.itemID,flag))out.sellable=flag?1:0;return true;
}
bool ReadBagPage(int start,Response&response,wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap))return false;std::vector<Il2CppObject*>items;int freeSpace=-1;if(!ReadBagObjects(c,items,freeSpace,d,cap))return false;
    start=std::clamp(start,0,static_cast<int>(items.size()));response.bagPage.totalCount=static_cast<std::int32_t>(items.size());response.bagPage.pageStart=start;response.bagPage.freeBagSpace=freeSpace;
    int count=std::min<int>(static_cast<int>(kBagPageCapacity),static_cast<int>(items.size())-start);
    for(int i=0;i<count;++i)if(!FillBagItemSnapshot(c,items[static_cast<size_t>(start+i)],response.bagPage.items[i],d,cap))return false;
    response.bagPage.pageCount=count;response.value0=response.bagPage.totalCount;response.value1=freeSpace;SetText(d,cap,L"Bag semantic page ");AppendInt(d,cap,start);Append(d,cap,L"+");AppendInt(d,cap,count);return true;
}
bool FindFreshBagItem(const Classes&c,std::int64_t instanceID,std::int32_t expectedItemID,Il2CppObject*&object,BagItemSnapshot&item,wchar_t*d,size_t cap){
    object=nullptr;item={};std::vector<Il2CppObject*>items;int freeSpace=-1;if(!ReadBagObjects(c,items,freeSpace,d,cap))return false;
    for(auto*candidate:items){BagItemSnapshot current{};wchar_t ignored[160]{};if(!FillBagItemSnapshot(c,candidate,current,ignored,ArrayCount(ignored)))continue;
        if(current.instanceID==instanceID&&current.itemID==expectedItemID&&current.site==10){object=candidate;item=current;return true;}}
    SetText(d,cap,L"Item instance đã đổi/mất; yêu cầu re-scan");return false;
}
std::int64_t RequestInstanceID(std::int32_t low,std::int32_t high){
    auto lo=static_cast<std::uint64_t>(static_cast<std::uint32_t>(low));auto hi=static_cast<std::uint64_t>(static_cast<std::uint32_t>(high));return static_cast<std::int64_t>((hi<<32)|lo);
}
Il2CppClass* FindExecutorClass(wchar_t*d,size_t cap){
    auto*img=AssemblyImage(d,cap);if(!img)return nullptr;const char*spaces[]={"FGStudio.LuaSystem","FGStudio.LuaSystem.Base","FGStudio.LuaSystem.GUI","FGStudio.Engine.Utilities",""};
    for(const char*ns:spaces){auto*k=g_api.class_from_name(img,ns,"MonoBehaviourExecutor");if(k&&FindMethod(k,"get_Instance",0,true)&&FindMethod(k,"ExecuteScriptFunction",3,false))return k;}
    SetText(d,cap,L"Không resolve MonoBehaviourExecutor");return nullptr;
}
bool ExecuteLuaOnObject(Il2CppObject*uiObject,Il2CppString*function,Il2CppObject*argsArray,wchar_t*d,size_t cap){
    if(!uiObject||!function||!argsArray)return false;Il2CppClass*executorClass=FindExecutorClass(d,cap);if(!executorClass)return false;Il2CppObject*executor=nullptr;
    if(!InvokeObj(FindMethod(executorClass,"get_Instance",0,true),nullptr,nullptr,executor,d,cap)||!executor){SetText(d,cap,L"MonoBehaviourExecutor.Instance chưa sẵn sàng");return false;}
    auto*execute=FindMethod(executorClass,"ExecuteScriptFunction",3,false);void*args[]={&uiObject,&function,&argsArray};return InvokeVoid(execute,executor,args,d,cap);
}
bool SellBagItem(std::int64_t instanceID,std::int32_t expectedItemID,Response&response,wchar_t*d,size_t cap){
    Classes c{};if(!ResolveClasses(c,d,cap)||!Safe(c,d,cap))return false;Il2CppObject*itemObject=nullptr;BagItemSnapshot item{};
    if(!FindFreshBagItem(c,instanceID,expectedItemID,itemObject,item,d,cap))return false;
    if(!item.sellable){SetText(d,cap,L"Item hiện tại IsItemSellable=false; chặn bán");return false;}
    if(item.itemID>=40000000&&item.itemID<50000000){SetText(d,cap,L"Item quest-family; chặn bán");return false;}
    Il2CppObject*shop=nullptr;if(!FindUi(c,"NPCShop",shop,d,cap)||!shop){SetText(d,cap,L"Chưa có NPCShop hiện hành; không bán mù");return false;}
    Il2CppObject*sellTab=nullptr;if(!ObjectMember(shop,"SellItemTab",sellTab,d,cap)||!sellTab){SetText(d,cap,L"NPCShop chưa có SellItemTab hiện hành");return false;}
    auto*corlib=g_api.get_corlib();Il2CppClass*systemObject=corlib?g_api.class_from_name(corlib,"System","Object"):nullptr;if(!systemObject){SetText(d,cap,L"Không resolve System.Object");return false;}
    Il2CppString*function=g_api.string_new("RequestSellItem");Il2CppObject*argsArray=g_api.array_new(systemObject,1);
    if(!function||!argsArray||!WriteLocal(argsArray,0x20,itemObject)){SetText(d,cap,L"Không tạo được RequestSellItem(item) args");return false;}
    if(!ExecuteLuaOnObject(sellTab,function,argsArray,d,cap))return false;response.resultCode=static_cast<std::int32_t>(ActionResult::ActionInvoked);response.value64_0=item.instanceID;response.value0=item.itemID;
    SetText(d,cap,L"Đã gọi NPCShop_SellItemTab.RequestSellItem");return true;
}

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
        case Command::ReadBagPage: ok=ReadBagPage(g_shared->request.arg0,r,detail,ArrayCount(detail));break;
        case Command::SellBagItem: ok=SellBagItem(RequestInstanceID(g_shared->request.arg0,g_shared->request.arg1),g_shared->request.arg2,r,detail,ArrayCount(detail));break;
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
