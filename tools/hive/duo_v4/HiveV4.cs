using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using HarmonyLib;
using UnityEngine;
using TheOtherRoles;
using ForceImpostorMod;

namespace DuoTest;

internal static class HiveV4
{
    internal static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
    internal static object Get(object o, string f) => o == null ? null : AccessTools.Field(o.GetType(), f)?.GetValue(o);
    static readonly Dictionary<string,Type> types = new();
    internal static Type AtlasType(string name)
    {
        if(types.TryGetValue(name,out var type)) return type;
        type = AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("UnknownsAtlas."+name,false)).FirstOrDefault(t=>t!=null);
        if(type!=null) types[name]=type;
        return type;
    }
    internal static object Static(string type, string f) => AtlasType(type)?.GetField(f,BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic)?.GetValue(null);
    internal static object World => Static("AmberhiveWorld", "Current");
    internal static object Life => Get(World, "_life");
    internal static object Call(object o, string m, params object[] args) => AccessTools.Method(o.GetType(), m).Invoke(o, args);
    internal static void Set(object o, string f, object v) => AccessTools.Field(o.GetType(), f).SetValue(o, v);
    static float next;
    static Vector2 walk;
    static float walkUntil;
    static string label = "boot";
    internal static void Physics(PlayerPhysics physics)
    {
        var me=PlayerControl.LocalPlayer;
        if(Time.time>=walkUntil || !physics.AmOwner || !me || !me.CanMove) return;
        var d=walk-me.GetTruePosition();
        physics.body.velocity=d.magnitude<.06f?Vector2.zero:d.normalized*Mathf.Min(1.8f,d.magnitude/Time.fixedDeltaTime);
    }
    internal static void Tick()
    {
        try
        {
            var inbox=Path.Combine(DuoPlugin.Root,"v4_command.txt");
            if(File.Exists(inbox))
            {
                var commands=File.ReadAllLines(inbox); File.Delete(inbox);
                foreach(var command in commands)
                    if(command.StartsWith("broadcast ")) DuoPlugin.Broadcast(command.Substring(10));
                    else Handle(command);
            }
            var me = PlayerControl.LocalPlayer;
            if (Time.time < walkUntil && me && me.CanMove)
            {
                var d = walk - me.GetTruePosition();
                me.MyPhysics.body.velocity = d.magnitude < .06f ? Vector2.zero : d.normalized * Mathf.Min(1.8f, d.magnitude / Time.deltaTime);
            }
            if (Time.time < next) return;
            next = Time.time + .5f;
            State();
        }
        catch (Exception e) { DuoPlugin.Say("V4 Tick Fehler " + e); }
    }
    internal static void State()
    {
        string F(object o, string n) => Convert.ToString(Get(o, n), Inv) ?? "";
        var w = World; var l = Life; var me = PlayerControl.LocalPlayer;
        var ps = Get(l, "_prints") as IList;
        string prints = ps == null ? "" : string.Join(";", ps.Cast<object>().Select(p => F(p,"Id") + ":" + ((Vector2)Get(p,"Pos")).ToString("F3") + ":" + F(p,"Angle") + ":" + F(p,"Born")));
        var snd = Get(w, "_sound"); var voices = Get(snd, "_voices") as Array;
        string audio = voices == null ? "" : string.Join(";", voices.Cast<object>().Select(v => F(v,"Name") + ":" + ((Get(v,"Source") as AudioSource)?.volume ?? 0).ToString("F4",Inv)));
        string row = string.Join("\t", new[]{DateTime.UtcNow.ToString("O"),label, AmongUsClient.Instance?.GameState.ToString(), AmongUsClient.Instance?.AmHost.ToString(), F(w,"_two"), F(w,"_clock"),F(w,"_phase"), F(w,"_phaseT0"),F(w,"_floodZone"),F(w,"_floodT0"),w == null ? "" : Convert.ToString(Call(w,"FloodLevel"),Inv),F(w,"_chuteT0"),F(l,"_clock"),F(l,"_synced"),F(l,"_enabled"),F(l,"_generation"),F(l,"_dark"), prints, me ? me.GetTruePosition().ToString("F3") : "", me ? me.CanMove.ToString() : "", me ? me.inVent.ToString() : "", MeetingHud.Instance ? MeetingHud.Instance.state.ToString() : "", ExileController.Instance ? "exile" : "",audio});
        if(l!=null)
        {
            string eligible=string.Join(";",PlayerControl.AllPlayerControls.ToArray().Where(p=>p).Select(p=>p.PlayerId+":"+AccessTools.Method(l.GetType(),"PublicWalker").Invoke(null,new object[]{p})+":"+p.Data?.Role?.Role));
            var sun=Get(l,"_sun") as SpriteRenderer;
            var lamps=Get(l,"_lamps") as IList;
            string levels=lamps==null?"":string.Join(";",lamps.Cast<object>().Select((o,i)=>Convert.ToSingle(Call(l,"LampLevel",i)).ToString("F3",Inv)));
            File.AppendAllText(Path.Combine(DuoPlugin.Root,"v4_life.tsv"),string.Join("\t",new[]{DateTime.UtcNow.ToString("O"),label,eligible,sun?sun.transform.position.ToString("F3"):"",sun?sun.transform.eulerAngles.ToString("F3"):"",levels,((Get(l,"_honey") as IList)?.Count??0).ToString(),((Get(l,"_visibleMoving") as IList)?.Count??0).ToString()})+"\n");
        }
        File.AppendAllText(Path.Combine(DuoPlugin.Root,"v4_state.tsv"), row + "\n");
    }
    internal static bool Handle(string msg)
    {
        if (!msg.StartsWith("v4 ")) return false;
        try
        {
            var a = msg.Split(' ');
            if (a[1] == "label") { label = a[2]; State(); return true; }
            if (a[2] != "*" && a[2] != DuoPlugin.Tag) return true;
            float Num(int i) => float.Parse(a[i], Inv);
            var me = PlayerControl.LocalPlayer;
            switch(a[1])
            {
                case "shot": DuoDriver.Start(DuoFeatures.Shot(a[3] + "_" + DuoPlugin.Tag)); break;
                case "snap": me.NetTransform.RpcSnapTo(new Vector2(Num(3), Num(4)) + new Vector2(0, .3636f)); break;
                case "walk": walk = new Vector2(Num(3), Num(4)); walkUntil = Time.time + Num(5); break;
                case "flood": if (AmongUsClient.Instance.AmHost) { Set(World,"_hostFloodAt",(float)Get(World,"_clock")+3600f); Call(World,"Broadcast", (byte)1, byte.Parse(a[3])); } break;
                case "bridge": if (AmongUsClient.Instance.AmHost) Set(World,"_hostNext",Get(World,"_clock")); break;
                case "chute":
                    if (AmongUsClient.Instance.AmHost) Call(World,"HostChute",me);
                    else AccessTools.Method(AccessTools.TypeByName("UnknownsAtlas.AtlasWorld"),"Send").Invoke(null,new object[]{(byte)24,(Action<Hazel.MessageWriter>)(w=>w.Write((byte)4)),-1});
                    break;
                case "hand": ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor,(byte)(ReactorSystemType.AddUserOp | int.Parse(a[3]))); break;
                case "unhand": ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor,(byte)(ReactorSystemType.RemoveUserOp | int.Parse(a[3]))); break;
                case "audio":
                    var t = AccessTools.TypeByName("UnknownsAtlas.AtlasAmberhiveSound");
                    var entry = AccessTools.Field(t,"_volume").GetValue(null);
                    entry.GetType().GetProperty("Value").SetValue(entry,int.Parse(a[3])); break;
                case "enabled":
                    var soundType=AtlasType("AtlasAmberhiveSound");
                    var enabledEntry=AccessTools.Field(soundType,"_enabled").GetValue(null);
                    enabledEntry.GetType().GetProperty("Value").SetValue(enabledEntry,a[3]=="1"); break;
                case "invis":
                    if(a.Length>5)
                    {
                        var ninja=AccessTools.TypeByName("TheOtherRoles.TheOtherRoles+Ninja")??AccessTools.TypeByName("TheOtherRoles.Ninja");
                        AccessTools.Field(ninja,"invisibleDuration").SetValue(null,Num(5));
                    }
                    RPCProcedure.setInvisible(byte.Parse(a[4]), byte.Parse(a[3])); break;
                case "faction": RoleManager.Instance.SetRole(DuoCommands.ById(byte.Parse(a[3])), a[4]=="1"?AmongUs.GameOptions.RoleTypes.Impostor:AmongUs.GameOptions.RoleTypes.Crewmate); break;
                case "phantomrole": RoleManager.Instance.SetRole(DuoCommands.ById(byte.Parse(a[3])),AmongUs.GameOptions.RoleTypes.Phantom); break;
                case "phantom": if(a[3]=="1") me.CmdCheckVanish(0); else me.CmdCheckAppear(false); break;
                case "scout":
                    var scout=AccessTools.TypeByName("UnknownsCollection.Scout");
                    AccessTools.Method(scout,a[3]=="1"?"SendActivate":"SendDeactivate").Invoke(null,null); break;
                case "rejoin": DuoDriver.Start(Rejoin()); break;
                case "freeze": AccessTools.TypeByName("TOR_BypassTest.BypassPlugin").GetField("FreezeActive").SetValue(null,true); break;
                case "panel":
                    var def=Get(World,"_def");
                    var positions=Get(def,"Consoles") as IDictionary;
                    // AtlasMapDef benutzt Felder fuer seine Konsolenpositionen.
                    var at=(Vector2)positions[a[3]];
                    me.NetTransform.RpcSnapTo(at+new Vector2(0,-.65f+.3636f));
                    DuoDriver.Start(OpenPanel(at)); break;
                case "close": if(Minigame.Instance) Minigame.Instance.ForceClose(); break;
                case "chameleon": RoleControl.AddModifier(byte.Parse(a[3]),RoleId.Chameleon); break;
                case "attemptjoin": AmongUsClient.Instance.SetEndpoint("127.0.0.1",22023,false); AmongUsClient.Instance.Connect(InnerNet.MatchMakerModes.Client,null); break;
            }
            DuoPlugin.Say("V4 Aktion " + msg);
        }
        catch (Exception e) { DuoPlugin.Say("V4 Aktion Fehler " + msg + " " + (e.InnerException ?? e)); }
        return true;
    }
    static IEnumerator Rejoin()
    {
        AmongUsClient.Instance.ExitGame(DisconnectReasons.ExitGame);
        yield return Co.Wait(5);
        try
        {
            AmongUsClient.Instance.NetworkMode=NetworkModes.LocalGame;
            AmongUsClient.Instance.SetEndpoint("127.0.0.1",22023,false);
            AmongUsClient.Instance.Connect(InnerNet.MatchMakerModes.Client,null);
        }
        catch(Exception e) { DuoPlugin.Say("V4 spaeter Beitritt "+e); }
        yield return Co.Wait(12);
        DuoPlugin.Say("V4 spaeter Beitritt Ergebnis: "+AmongUsClient.Instance.GameState+" "+AmongUsClient.Instance.AmConnected);
    }
    static IEnumerator OpenPanel(Vector2 at)
    {
        yield return Co.Wait(1);
        var con=ShipStatus.Instance.AllConsoles.FirstOrDefault(c=>c && Vector2.Distance(c.transform.position,at)<.1f);
        if(con) con.Use();
        yield return Co.Wait(1);
        DuoPlugin.Say("V4 Konsole "+at+" Minispiel="+(Minigame.Instance?Minigame.Instance.GetType().Name:"fehlt"));
    }
}

[HarmonyPatch(typeof(PlayerPhysics),nameof(PlayerPhysics.FixedUpdate))]
internal static class HiveV4Physics
{
    [HarmonyPostfix,HarmonyPriority(Priority.Last)]
    static void Postfix(PlayerPhysics __instance) => HiveV4.Physics(__instance);
}

internal static partial class DuoHost
{
    static void V(string s) => DuoPlugin.Broadcast("v4 " + s);
    static IEnumerator Phase(string s,float wait=2f) { V("label " + s); yield return Co.Wait(wait); }
    static void Opt(int id,int value) { var o = CustomOption.options.FirstOrDefault(x=>x.id==id); if (o==null) throw new Exception("Option fehlt " + id); o.selection=value; Changed(o); }
    static IEnumerator HiveMeeting(string label,byte vote=253)
    {
        yield return Phase(label + "_vorher");
        yield return Co.Until(()=>PlayerControl.LocalPlayer.CanMove,20f);
        PlayerControl.LocalPlayer.CmdReportDeadBody(null);
        yield return Co.Until(()=>MeetingHud.Instance && MeetingHud.Instance.state==MeetingHud.VoteStates.NotVoted,25f);
        V("label " + label + "_meeting");
        yield return Co.Wait(2);
        V("shot * " + label + "_meeting");
        if (!MeetingHud.Instance) { report.Add(label+":KEIN-MEETING"); yield break; }
        MeetingHud.Instance.CmdCastVote(HostId,vote);
        foreach(var tag in ClientTags()) DuoPlugin.Broadcast("vote " + tag + " " + vote);
        yield return Co.Until(()=>MeetingHud.Instance && MeetingHud.Instance.state==MeetingHud.VoteStates.Results,40f);
        if (!MeetingHud.Instance || MeetingHud.Instance.state!=MeetingHud.VoteStates.Results) { report.Add(label+":KEIN-ERGEBNIS"); yield break; }
        yield return Co.Wait(3);
        DuoClient.Proceed(); DuoPlugin.Broadcast("proceed",false);
        yield return Co.Wait(2);
        V("label " + label + "_kino");
        V("shot * " + label + "_kino");
        yield return Co.Until(()=>!MeetingHud.Instance && !ExileController.Instance && PlayerControl.LocalPlayer.CanMove,50f);
        yield return Phase(label + "_nachher",5);
        yield return Snap(label);
        report.Add(label+":abgeschlossen");
    }
    static IEnumerator PlanHiveV4()
    {
        // Keine zufaelligen Rollen oder Spielmodi aus alten Testeinstellungen.
        foreach(var o in CustomOption.options) if(o.id!=0 && o.selections!=null && o.selections.Length>1) { o.selection=0; Changed(o); }
        foreach(int floors in new[]{0,1})
        {
            var tag = "hive"+(floors+1)+"f";
            yield return Co.Until(()=>LobbyBehaviour.Instance && PlayerControl.AllPlayerControls.Count>=3,120);
            if(!LobbyBehaviour.Instance || PlayerControl.AllPlayerControls.Count<3) { report.Add(tag+":CLIENTS-FEHLEN"); yield break; }
            yield return Co.Wait(6);
            Opt(1729,floors); Opt(1730,floors); CustomOption.ShareOptionSelections();
            SetVanillaMap(0); AtlasSet(AtlasKeys().IndexOf("amberhive")+1);
            yield return Co.Wait(8);
            yield return StartRound();
            if (!ShipStatus.Instance || HiveV4.World==null) { report.Add(tag+":KEINE-KARTE"); yield break; }
            var bp=ClientPlayer("B"); var cp=ClientPlayer("C");
            if(!bp || !cp) { report.Add(tag+":CLIENTS-FEHLEN-IN-RUNDE"); yield break; }
            byte bid=bp.PlayerId, cid=cp.PlayerId;
            Roles(bid); yield return Co.Wait(3);
            V("snap * 0 3.4"); yield return Phase(tag+"_basis",5);
            V("shot * " + tag+"_brunnen");
            V("bridge A"); yield return Phase(tag+"_drehung",1);
            V("shot * " + tag+"_drehung"); yield return Co.Wait(3);
            for(int zone=0;zone<4;zone++)
            {
                V("flood A "+zone); yield return Phase(tag+"_flut"+zone+"_warnung",1);
                yield return Phase(tag+"_flut"+zone+"_anstieg",5);
                V("shot * "+tag+"_flut"+zone);
                if(zone==0) yield return HiveMeeting(tag+"_skip");
                else yield return Co.Wait(12);
            }
            // Echte Host-Option statt Freeplay-Schalter.
            Opt(1730,1); CustomOption.ShareOptionSelections(); yield return Co.Wait(3);
            V("snap A 17 9.6"); V("snap C 17 9.3"); V("snap B 18.6 8.15"); yield return Phase(tag+"_pollen_aufnahme",2);
            V("walk B 16.9 8.15 2"); yield return Phase(tag+"_pollen_laufen",2);
            V("shot * "+tag+"_pollen"); yield return Co.Wait(7);
            V("snap B 18.6 8.15"); yield return Co.Wait(2);
            V("walk B 17.2 8.15 1"); yield return Phase(tag+"_pollen_vent_vorher",1);
            V("snap B 18.6 8.15"); yield return Co.Wait(1);
            DuoPlugin.Broadcast("vent B 0"); yield return Phase(tag+"_vent",7);
            foreach(string who in new[]{"A","B"})
            {
                byte id=who=="A"?HostId:bid; RoleControl.SetTorRole(id,RoleId.Ninja); yield return Co.Wait(2);
                V("snap "+who+" 18.6 8.15"); yield return Co.Wait(2);
                // Der echte TOR-RPC wird auf jeder Instanz angewandt, danach echte Bewegung.
                DuoPlugin.Broadcast("v4 invis * 0 "+id);
                V("walk "+who+" 17 8.15 1.2"); yield return Phase(tag+"_ninja_"+who,2);
                DuoPlugin.Broadcast("v4 invis * 255 "+id); yield return Co.Wait(1);
                Roles(bid); yield return Co.Wait(2);
            }
            foreach(string who in new[]{"A","B"})
            {
                byte id=who=="A"?HostId:bid;
                RoleControl.SetUcRole(id,UcRole.Scout); yield return Co.Wait(2);
                V("snap "+who+" 18.6 8.15"); yield return Co.Wait(2);
                V("scout "+who+" 1"); yield return Co.Wait(.5f);
                V("walk "+who+" 17 8.15 2"); yield return Phase(tag+"_scout_"+who,3);
                V("scout "+who+" 0"); Roles(bid); yield return Co.Wait(2);
            }
            foreach(string sys in new[]{"Electrical","Comms","LifeSupp","Reactor"})
            {
                ResetSabotageTimer(); DuoPlugin.Broadcast("sabo B "+sys);
                yield return Phase(tag+"_sabotage_"+sys,5);
                report.Add(tag+":"+sys+"-aktiv="+SabotageActive(sys));
                if(sys=="Reactor")
                {
                    V("snap A -4.4 -10.65"); V("snap C 4.4 -10.65");
                    V("hand A 0"); yield return Phase(tag+"_reaktor_eine_hand",3);
                    report.Add(tag+":Reaktor-nach-einer-Hand="+SabotageActive(sys));
                    V("hand C 1"); yield return Phase(tag+"_reaktor_zwei_haende",3);
                    report.Add(tag+":Reaktor-repariert="+!SabotageActive(sys));
                    V("unhand A 0"); V("unhand C 1");
                }
                else Repair(sys);
                yield return Phase(tag+"_repariert_"+sys,5);
                if(SabotageActive(sys)) { report.Add(tag+":"+sys+"-FEHLER-REPARATUR"); Repair(sys); }
            }
            ResetSabotageTimer(); DuoPlugin.Broadcast("sabo B doors"); yield return Phase(tag+"_tueren",12);
            if(floors==1)
            {
                foreach(string who in new[]{"A","B"})
                {
                    V("snap "+who+" 18.6 8.15"); yield return Co.Wait(1);
                    V("walk "+who+" 17 8.15 1"); yield return Co.Wait(1);
                    V("snap "+who+" 3 26"); yield return Co.Wait(2);
                    V("chute "+who); yield return Phase(tag+"_rutsche_"+who,2);
                    V("shot * "+tag+"_rutsche_"+who);
                }
                V("chute B"); yield return Phase(tag+"_rutsche_unzulaessig",3);
            }
            V("snap * 0 3.4"); yield return Co.Wait(2);
            foreach(int volume in new[]{0,30,60,100}) { V("audio B "+volume); yield return Phase(tag+"_audio"+volume,2); }
            V("audio B 60");
            Opt(1730,0); CustomOption.ShareOptionSelections(); yield return Phase(tag+"_pollen_aus",3);
            yield return HiveMeeting(tag+"_skip2");
            Roles(bid); yield return Co.Wait(3);
            DuoCommands.ById(bid).RpcMurderPlayer(DuoCommands.ById(cid),true); yield return Phase(tag+"_kill",3);
            PlayerControl.LocalPlayer.CmdReportDeadBody(DuoCommands.ById(cid).Data);
            yield return Co.Until(()=>MeetingHud.Instance && MeetingHud.Instance.state==MeetingHud.VoteStates.NotVoted,25);
            if(MeetingHud.Instance)
            {
                MeetingHud.Instance.CmdCastVote(HostId,bid); DuoPlugin.Broadcast("vote B "+bid);
                yield return Co.Until(()=>MeetingHud.Instance && MeetingHud.Instance.state==MeetingHud.VoteStates.Results,35);
                yield return Co.Wait(3); DuoClient.Proceed(); DuoPlugin.Broadcast("proceed",false);
                yield return Co.Wait(2); V("shot * "+tag+"_rauswurf");
                yield return Co.Until(()=>!MeetingHud.Instance && !ExileController.Instance,45);
                yield return Phase(tag+"_rauswurf_nachher",5);
            }
            yield return EndRound(tag);
        }
        // Kontrollkarte fuer den offenen Diagnose-Skip-Fehler.
        yield return Co.Until(()=>LobbyBehaviour.Instance && PlayerControl.AllPlayerControls.Count>=3,120);
        yield return Co.Wait(6);
        SetVanillaMap(0); AtlasSet(AtlasKeys().IndexOf("museum")+1); yield return Co.Wait(6);
        yield return StartRound(); yield return HiveMeeting("museum_skip"); yield return EndRound("museum");
        yield return Co.Until(()=>LobbyBehaviour.Instance && PlayerControl.AllPlayerControls.Count>=3,120);
        yield return Co.Wait(6);
        Opt(1729,1); Opt(1730,1); CustomOption.ShareOptionSelections(); AtlasSet(AtlasKeys().IndexOf("amberhive")+1); yield return Co.Wait(6);
        yield return StartRound(); yield return Phase("hostwechsel_vorher",5);
        V("label hostwechsel");
        DuoPlugin.Say("V4 Matrix abgeschlossen " + string.Join(" ; ",report));
        // run.ps1 sammelt nach DONE noch acht Sekunden. Mehr Beobachtungszeit fuer den neuen Host.
        DuoDriver.QuitAt=Time.realtimeSinceStartup+1;
        yield return Co.Wait(60);
    }

    static IEnumerator PlanHiveFollowup()
    {
        foreach(var o in CustomOption.options) if(o.id!=0 && o.selections!=null && o.selections.Length>1) { o.selection=0; Changed(o); }
        Opt(1729,0); Opt(1730,1); CustomOption.ShareOptionSelections();
        SetVanillaMap(0); AtlasSet(AtlasKeys().IndexOf("amberhive")+1); yield return Co.Wait(8);
        yield return StartRound();
        var firstB=ClientPlayer("B");
        if(!firstB || HiveV4.World==null) { report.Add("Nachtest-1f:START-FEHLER"); yield break; }
        Roles(firstB.PlayerId); yield return Co.Wait(3);
        V("freeze *");
        V("snap A 17 9.6"); V("snap C 17 9.3"); V("snap B 18.6 8.15"); yield return Co.Wait(2);
        V("walk B 16.9 8.15 2"); yield return Phase("folge_1f_pollen_laufen",2);
        V("shot * folge_1f_pollen"); yield return Co.Wait(7);
        yield return HiveMeeting("folge_1f_skip");
        foreach(var route in new[]{("keeper_waggle",10.9f,8.05f,16f,9.4f,3f),("queen_sun",2f,-14.55f,7f,-14.55f,3f),("west_wasp",-15.2f,-13.3f,-12.4f,-13.4f,2f)})
        {
            V($"snap A {route.Item2.ToString(HiveV4.Inv)} {route.Item3.ToString(HiveV4.Inv)}"); yield return Co.Wait(.5f);
            V($"walk A {route.Item4.ToString(HiveV4.Inv)} {route.Item5.ToString(HiveV4.Inv)} {route.Item6.ToString(HiveV4.Inv)}");
            yield return Phase("folge_weg_"+route.Item1,route.Item6);
            V("shot A folge_weg_"+route.Item1);
            yield return Co.Wait(.2f);
        }
        yield return EndRound("folge_1f");
        yield return Co.Until(()=>LobbyBehaviour.Instance && PlayerControl.AllPlayerControls.Count>=3,120);
        yield return Co.Wait(6);
        Opt(1729,1); Opt(1730,1); CustomOption.ShareOptionSelections();
        SetVanillaMap(0); AtlasSet(AtlasKeys().IndexOf("amberhive")+1); yield return Co.Wait(8);
        yield return StartRound();
        var b=ClientPlayer("B"); var c=ClientPlayer("C");
        if(!b || !c || HiveV4.World==null) { report.Add("Nachtest:START-FEHLER"); yield break; }
        Roles(b.PlayerId); yield return Co.Wait(3);
        V("freeze *");
        V("snap * 0 3.4"); yield return Co.Wait(2);
        V("enabled B 0"); yield return Phase("folge_sound_gast_aus",3);
        V("enabled B 1"); yield return Phase("folge_sound_gast_an",3);
        for(int repeat=0;repeat<2;repeat++)
        {
            ResetSabotageTimer(); DuoPlugin.Broadcast("sabo B Electrical");
            yield return Phase("folge_glow_ab"+repeat,.8f);
            Repair("Electrical"); yield return Phase("folge_glow_umkehr"+repeat,3);
        }
        // Beobachter stehen neben der Laufstrecke, ohne den Pollenpunkt zu blockieren.
        V("snap A 17 9.6"); V("snap C 17 9.3"); V("snap B 18.6 8.15"); yield return Co.Wait(2);
        V("walk B 16.9 8.15 2"); yield return Phase("folge_pollen_laufen",2);
        yield return HiveMeeting("folge_pollen_meeting");
        foreach(string who in new[]{"A","B"})
        {
            byte pid=who=="A"?HostId:b.PlayerId;
            foreach(string role in new[]{"Ninja","Scout","Phantom"})
            {
                Roles(b.PlayerId); yield return Co.Wait(1);
                if(role=="Ninja") RoleControl.SetTorRole(pid,RoleId.Ninja);
                if(role=="Scout") RoleControl.SetUcRole(pid,UcRole.Scout);
                if(role=="Phantom") V("phantomrole * "+pid);
                yield return Co.Wait(1);
                V("snap "+who+" 18.6 8.15"); yield return Co.Wait(2);
                if(role=="Ninja") V("invis * 0 "+pid);
                if(role=="Scout") V("scout "+who+" 1");
                if(role=="Phantom") V("phantom "+who+" 1");
                yield return Co.Wait(1.5f);
                V("walk "+who+" 17 8.15 2"); yield return Phase("folge_unsichtbar_"+role+"_"+who,2);
                if(role=="Ninja") V("invis * 255 "+pid);
                if(role=="Scout") V("scout "+who+" 0");
                if(role=="Phantom") V("phantom "+who+" 0");
                yield return Co.Wait(2);
            }
        }
        Roles(b.PlayerId); yield return Co.Wait(2);
        // Lokale Honigspuren und Flutpegel in jeder Zone mit Bewegung.
        var hive=HiveV4.Get(HiveV4.World,"_h");
        var zones=HiveV4.Get(hive,"FloodZones") as IList;
        for(int i=0;i<zones.Count;i++)
        {
            var points=(Vector2[])zones[i]; var center=points.Aggregate(Vector2.zero,(a,p)=>a+p)/points.Length;
            V("snap * "+center.x.ToString(HiveV4.Inv)+" "+center.y.ToString(HiveV4.Inv));
            V("flood A "+i); yield return Phase("folge_flut"+i+"_warnung",1);
            yield return Phase("folge_flut"+i+"_hoch",4);
            V("walk B "+(center.x+.65f).ToString(HiveV4.Inv)+" "+center.y.ToString(HiveV4.Inv)+" 1");
            yield return Phase("folge_honig"+i,1);
            V("shot * folge_honig"+i); yield return Co.Wait(2);
        }
        V("bridge A"); yield return HiveMeeting("folge_mechanik_pause");
        // Echte Minispiele an den tatsaechlichen Reaktorpositionen oeffnen.
        ResetSabotageTimer(); DuoPlugin.Broadcast("sabo B Reactor"); yield return Co.Wait(3);
        V("panel A Reactor/UpperHandConsole/0"); V("panel C Reactor/LowerHandConsole/1");
        yield return Phase("folge_reaktor_konsolen",3);
        V("shot * folge_reaktor_konsolen");
        V("hand A 0"); yield return Phase("folge_reaktor_ein",2);
        report.Add("Nachtest:Reaktor-eine-Hand-aktiv="+SabotageActive("Reactor"));
        V("hand C 1"); yield return Phase("folge_reaktor_zwei",2);
        report.Add("Nachtest:Reaktor-zwei-Haende-repariert="+!SabotageActive("Reactor"));
        V("close *"); V("unhand A 0"); V("unhand C 1");
        V("snap B 3 26"); yield return Co.Wait(2); V("chute B");
        yield return Phase("folge_rutsche_gast_komplett",2);
        V("shot * folge_rutsche_gast");
        V("chute B"); yield return Phase("folge_rutsche_unzulaessig",2);
        V("snap B 3 26"); yield return Co.Wait(2); V("chute B");
        yield return Co.Wait(.12f);
        yield return HiveMeeting("folge_rutsche_abbruch");
        // In einer laufenden Vanilla-Runde wird ein erneuter Beitritt ueblicherweise abgewiesen.
        V("rejoin C"); yield return Phase("folge_spaeter_beitritt",20);
        V("label folge_host_verlaesst");
        DuoPlugin.Say("V4 Matrix abgeschlossen "+string.Join(" ; ",report));
        DuoDriver.QuitAt=Time.realtimeSinceStartup+1;
        yield return Co.Wait(60);
    }

    static IEnumerator PlanHiveNinja()
    {
        foreach(var o in CustomOption.options) if(o.id!=0 && o.selections!=null && o.selections.Length>1) { o.selection=0; Changed(o); }
        Opt(1729,1); Opt(1730,1); CustomOption.ShareOptionSelections();
        SetVanillaMap(0); AtlasSet(AtlasKeys().IndexOf("amberhive")+1); yield return Co.Wait(8);
        yield return StartRound();
        var b=ClientPlayer("B"); if(!b || HiveV4.World==null) { report.Add("Ninja:START-FEHLER"); yield break; }
        Roles(b.PlayerId); yield return Co.Wait(2); V("freeze *");
        foreach(string who in new[]{"A","B"})
        {
            byte pid=who=="A"?HostId:b.PlayerId;
            V("snap A 17 9.6"); V("snap C 17 9.3");
            V("snap "+who+" 18.6 8.15"); yield return Co.Wait(2);
            V("walk "+who+" 17 8.15 2"); yield return Phase("ninja_sichtbar_"+who,2);
            RoleControl.SetTorRole(pid,RoleId.Ninja); yield return Co.Wait(2);
            V("snap "+who+" 18.6 8.15"); yield return Co.Wait(2);
            // Explizit zehn Sekunden, damit die ausgeschalteten Zufallsoptionen nicht vorher enttarnen.
            V("invis * 0 "+pid+" 10"); yield return Co.Wait(.5f);
            V("walk "+who+" 17 8.15 2"); yield return Phase("ninja_aktiv_"+who,2);
            V("shot * ninja_aktiv_"+who);
            V("invis * 255 "+pid); Roles(b.PlayerId); yield return Co.Wait(2);
        }
        V("snap B 3 26"); yield return Co.Wait(2);
        V("chute B"); yield return Co.Wait(.12f);
        V("label rutsche_abbruch_sofort");
        PlayerControl.LocalPlayer.CmdReportDeadBody(null);
        yield return Vote(253,253,253,"rutsche_abbruch_sofort");
        V("label rutsche_abbruch_freigegeben"); yield return Co.Wait(3);
        report.Add("Ninja-und-Rutschenabbruch:abgeschlossen");
    }
}
