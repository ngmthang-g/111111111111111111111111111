#pragma once
#include <windows.h>
#include <cstdint>
#include <cstddef>

namespace cleanroute {

// Wire contract for the new TLMTool compatibility bridge. The numeric command
// family intentionally follows the already-tested 12.4.2 semantic donor so the
// behavior can be ported without changing action meaning.
constexpr std::uint32_t kMagic = 0x324D4C54u; // TLM2
constexpr std::uint32_t kProtocolVersion = 0x00020102u; // TLM 2.1.2 target
constexpr UINT kWakeMessage = WM_APP + 0x531;
constexpr wchar_t kMappingPrefix[] = L"Local\\TLMToolClone_";

enum class Command : std::uint32_t {
    None = 0, ReadState = 1, ToggleRide = 2, StartPath = 3, StopPath = 4,
    ClickNpc = 5, ConfirmMap = 6, Revive = 7, StartAutoFight = 8,
    StopAutoFight = 9, BeginBackgroundSell = 10, AdvanceBackgroundSell = 11,
    SellNextBagItem = 12, CloseBackgroundSell = 13, ClickInternalPoint = 14,
    BeginBackgroundTreatment = 15, AdvanceBackgroundTreatment = 16,
    CloseBackgroundTreatment = 17, ReadCurrency = 18, ReadBagPage = 19,
    DropBagItem = 20, SellBagItem = 21, SelectTargetByRoleID = 22,
    ClickTravelSemantic = 23, ConfirmTravelSemantic = 24, TestOpenBag = 25,
    ClickInternalPointRawTest = 26, DragInternalPoint = 27,
    ProbeNearbyLoot = 28, PickNearestLoot = 29, ProbeUiDirect = 32,
    InvokeUiDirect = 33, PartyLeave = 34, PartyInvite = 35,
    PartyJoin = 36, ReviveNormal = 37, PartyCreate = 38,
};

enum class UiDirectTarget : std::int32_t {
    None = 0, CloseItemPopup = 1, CloseBag = 2, CloseTrade = 3,
    TradeConfirm = 4, TradeTabEquip = 5, TradeLock = 6, TradeSubmit = 7,
    OpenBag = 8, TradeRequestCancel = 9,
};

enum class TravelSemantic : std::int32_t {
    None = 0, KunLunSon = 1, TinhTucHai = 2, DenCacMonPhai = 3, Trade = 4,
    InviteParty = 5, ThienSon = 6, SellPopup = 7, DiscardPopup = 8,
    DiscardConfirm = 10, PutUpPopup = 9, NamHai = 11, MieuCuong = 12,
    HoangLongPhu = 13, ThachLam = 14, DaiLy = 15, RequestJoinParty = 16,
    LacDuongLienMayChu = 17, ReturnNormalServer = 18,
};

enum class ActionResult : std::int32_t { None=0, ActionInvoked=1, StageReady=2, NoCandidate=3, UiClosed=4, NothingToClose=5 };

enum SnapshotValid : std::uint32_t {
    ValidMapTransition=1u<<0, ValidIdentity=1u<<1, ValidMap=1u<<2,
    ValidPosition=1u<<3, ValidRiding=1u<<4, ValidAutoPath=1u<<5,
    ValidLifeState=1u<<6, ValidAutoFight=1u<<7, ValidBagSpace=1u<<8,
    ValidTeam=1u<<9, ValidVitals=1u<<10, ValidProfile=1u<<11,
};

struct Snapshot {
    std::uint32_t validMask=0;
    std::int32_t roleID=0,teamID=0,level=0,factionID=0;
    std::int32_t hp=0,maxHP=0,mapID=0,x=0,y=0;
    std::int32_t riding=0,autoPathing=0,mapReady=0,waitingChangeMap=0;
    std::int32_t dead=0,autoFight=0,freeBagSpace=-1;
    wchar_t characterName[64]{};
};
struct Request { std::uint32_t command=0; std::int32_t arg0=0,arg1=0,arg2=0; };
struct BagItemSnapshot {
    std::int64_t instanceID=0; std::int32_t itemID=0,site=0,position=-1,quantity=0,bound=0,throwable=0,sellable=0,isEquip=0,isWeapon=0,itemTypeCode=0,equipTypeCode=0;
    wchar_t name[96]{},itemType[32]{},equipType[32]{};
};
constexpr std::size_t kBagPageCapacity=20;
struct BagPageSnapshot { std::int32_t totalCount=0,pageStart=0,pageCount=0,freeBagSpace=-1; BagItemSnapshot items[kBagPageCapacity]{}; };
struct Response {
    std::int32_t ok=0,resultCode=0,value0=0,value1=0; std::int64_t value64_0=0,value64_1=0;
    Snapshot snapshot{}; BagPageSnapshot bagPage{}; wchar_t detail[512]{};
};
struct SharedBlock {
    std::uint32_t magic=kMagic,protocolVersion=kProtocolVersion,targetPid=0,targetWindowThreadId=0;
    volatile LONG requestSeq=0,completedSeq=0,bridgeLoaded=0,bridgeBusy=0;
    Request request{}; Response response{};
};
inline void MappingName(DWORD pid,wchar_t* output,std::size_t count){ if(!output||!count)return; wsprintfW(output,L"%s%lu",kMappingPrefix,static_cast<unsigned long>(pid)); }
} // namespace cleanroute
