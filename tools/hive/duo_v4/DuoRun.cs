// Commands (both sides), the client loop and the host plan.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using AmongUs.GameOptions;
using HarmonyLib;
using InnerNet;
using TheOtherRoles;
using TheOtherRoles.Objects;
using UnityEngine;
using ForceImpostorMod;

namespace DuoTest;

internal static class DuoCommands
{
    internal static readonly HashSet<string> Acks = new();
    internal static readonly Dictionary<string, string> Done = new();

    internal static void Tick() { }

    internal static PlayerControl ById(byte id) => PlayerControl.AllPlayerControls.ToArray().FirstOrDefault(p => p && p.PlayerId == id);

    internal static void Handle(string msg, byte sender)
    {
        if (HiveV4.Handle(msg)) return;
        var a = msg.Split(' ');
        switch (a[0])
        {
            case "snap":
                DuoSnap.Write(a[2]);
                if ((a[2].StartsWith("lobby") || a[2].StartsWith("mem")) && File.Exists(Path.Combine(DuoPlugin.Root, "duo_mem_on"))) DuoMem.Write(a[2]);
                if (!DuoPlugin.IsHost) DuoPlugin.Broadcast($"ack {a[1]} {DuoPlugin.Tag}", false);
                break;
            case "ack":
                if (DuoPlugin.IsHost) Acks.Add(a[1] + "/" + a[2]);
                break;
            case "done":
                if (DuoPlugin.IsHost) Done[a[1]] = string.Join(" ", a.Skip(2));
                break;
            case "press":
                if (a[1] == DuoPlugin.Tag) DuoDriver.Start(DuoClient.PressAll(byte.Parse(a[2])));
                break;
            case "report":
                if (a[1] == DuoPlugin.Tag) { DuoPlugin.Say("reporting (emergency)"); PlayerControl.LocalPlayer.CmdReportDeadBody(null); }
                break;
            case "vote":
                if (a[1] == DuoPlugin.Tag && MeetingHud.Instance)
                {
                    DuoPlugin.Say("vote " + a[2]);
                    MeetingHud.Instance.CmdCastVote(PlayerControl.LocalPlayer.PlayerId, byte.Parse(a[2]));
                }
                break;
            case "chat":
                if (a[1] == DuoPlugin.Tag || a[1] == "*") DuoClient.Chat(string.Join(" ", a.Skip(2)));
                break;
            case "selftest":
                try
                {
                    var tr = AccessTools.TypeByName("ModSelfTest.TestRunner");
                    var res = tr.GetMethod("Run").Invoke(null, new object[] { null, false }) as IList;
                    var sum = tr.GetMethod("Summary").Invoke(null, new object[] { res }) as string;
                    DuoPlugin.Say($"selftest {a[1]}: {sum}");
                    var md = Path.Combine(BepInEx.Paths.BepInExRootPath, "SelfTest", "last-run.md");
                    if (File.Exists(md)) File.Copy(md, Path.Combine(DuoPlugin.Root, $"selftest_{a[1]}.md"), true);
                }
                catch (Exception e) { DuoPlugin.Say("selftest failed: " + (e.InnerException ?? e).Message); }
                break;
            case "proceed":
                DuoClient.Proceed();
                break;
            case "mark":
                DuoPlugin.Say("=== " + string.Join(" ", a.Skip(1)));
                break;
            case "vent":
                if (a[1] == DuoPlugin.Tag) DuoDriver.Start(DuoEdgeClient.Vent(int.Parse(a[2])));
                break;
            case "tasks":
                if (a[1] == DuoPlugin.Tag || a[1] == "*") DuoEdgeClient.CompleteTasks();
                break;
            case "sabo":
                if (a[1] == DuoPlugin.Tag) DuoEdgeClient.Sabotage(a[2]);
                break;
            case "quitme":
                if (a[1] == DuoPlugin.Tag) { DuoPlugin.Say("quit requested (single)"); DuoDriver.QuitAt = Time.realtimeSinceStartup + 1f; }
                break;
            case "quit":
                DuoPlugin.Say("quit requested");
                DuoDriver.QuitAt = Time.realtimeSinceStartup + 3f;
                break;
            default:
                DuoFeatures.Handle(a);
                break;
        }
    }
}

internal static class DuoClient
{
    internal static IEnumerator Run()
    {
        yield return Co.WaitEos();
        if (DuoPlugin.Plan == "menuonly") { DuoPlugin.Say("menu only: no lobby"); yield break; }   // start-time runs
        yield return Co.Wait(4f);
        for (int attempt = 1; attempt <= 20 && LobbyBehaviour.Instance == null; attempt++)
        {
            try
            {
                var c = AmongUsClient.Instance;
                if (c.AmConnected) DuoPlugin.Say("connected, waiting for the lobby scene");
                else
                {
                    DuoPlugin.Say($"join attempt {attempt}");
                    c.NetworkMode = NetworkModes.LocalGame;
                    c.OnlineScene = "OnlineGame";
                    c.SetEndpoint("127.0.0.1", 22023, false);
                    c.Connect(MatchMakerModes.Client, null);
                }
            }
            catch (Exception e) { DuoPlugin.Say("join failed: " + e.Message); }
            float t0 = Time.realtimeSinceStartup;
            while (LobbyBehaviour.Instance == null && Time.realtimeSinceStartup - t0 < 15f) yield return null;
        }
        DuoPlugin.Say(LobbyBehaviour.Instance != null ? "client in lobby" : "client could not join");
    }

    static readonly System.Reflection.FieldInfo initialClick = AccessTools.Field(typeof(CustomButton), "InitialOnClick");
    internal static Action ClickOf(CustomButton b) { try { return initialClick?.GetValue(b) as Action; } catch { return null; } }

    static bool Dangerous(CustomButton b)
    {
        try
        {
            var asm = ClickOf(b)?.Method?.DeclaringType?.Assembly.GetName().Name ?? "";
            return asm == "TOR-Bypass" || asm == "ForceImpostorMod" || asm == "HostFixPlugin";
        }
        catch { return false; }
    }

    internal static string BtnName(CustomButton b)
    {
        string n = b.buttonText;
        if (string.IsNullOrEmpty(n)) try { n = b.Sprite ? b.Sprite.name : ""; } catch { }
        if (string.IsNullOrEmpty(n)) try { n = ClickOf(b)?.Method?.DeclaringType?.Name; } catch { }
        return (n ?? "?").Replace(' ', '_');
    }

    internal static IEnumerator PressAll(byte targetId)
    {
        var me = PlayerControl.LocalPlayer;
        var target = DuoCommands.ById(targetId);
        if (target && me) { try { me.NetTransform.RpcSnapTo((Vector2)target.transform.position + new Vector2(0.3f, 0f)); } catch (Exception e) { DuoPlugin.Say("snap failed " + e.Message); } }
        yield return Co.Wait(1.2f);
        var log = new List<string>();
        try { if (me && !me.CanMove) log.Add("cannot-move-before[" + Blockers() + "]"); } catch { }
        for (int round = 1; round <= 2; round++)
        {
            foreach (var b in CustomButton.buttons.ToArray())
            {
                if (b?.actionButton == null) continue;
                bool has = false; try { has = b.HasButton(); } catch { }
                if (!has) continue;
                if (Dangerous(b)) continue;
                bool could = false;
                try
                {
                    if (!b.isEffectActive) b.Timer = -1f;
                    could = b.CouldUse();
                    b.onClickEvent();
                }
                catch (Exception e) { log.Add($"{BtnName(b)}:EXC:{e.GetType().Name}"); DuoPlugin.Say($"press {BtnName(b)} threw {e}"); continue; }
                log.Add($"{BtnName(b)}:{(could ? "use" : "nouse")}");
                yield return Co.Wait(0.7f);
            }
            try
            {
                if (me.Data?.Role != null && me.Data.Role.CanUseKillButton && !me.Data.IsDead)
                {
                    me.SetKillTimer(0f);
                    var kb = HudManager.Instance.KillButton;
                    var kt = kb.currentTarget;
                    if (kt) { byte kid = kt.PlayerId; kb.DoClick(); log.Add("vanillaKill:" + kid); }
                    else log.Add("vanillaKill:notarget");
                }
            }
            catch (Exception e) { log.Add("vanillaKill:EXC:" + e.GetType().Name); }
            yield return Co.Wait(1.5f);
        }
        CloseOverlays(log);
        DuoPlugin.Say("pressed " + string.Join(" ", log));
        DuoPlugin.Broadcast($"done {DuoPlugin.Tag} {string.Join(" ", log)}", false);
    }

    // An ability can open a minigame or the map (Hacker admin, Security Guard cams, Trap Log...). Left open,
    // it freezes the player for every later step.
    internal static void CloseOverlays(List<string> log)
    {
        try { if (Minigame.Instance) { log.Add("closed:" + Minigame.Instance.GetType().Name); Minigame.Instance.Close(); } } catch (Exception e) { log.Add("close-mg:EXC:" + e.GetType().Name); }
        try { if (MapBehaviour.Instance && MapBehaviour.Instance.IsOpen) { log.Add("closed:map"); MapBehaviour.Instance.Close(); } } catch (Exception e) { log.Add("close-map:EXC:" + e.GetType().Name); }
        try
        {
            var me = PlayerControl.LocalPlayer;
            if (me && !me.CanMove)
            {
                var why = Blockers();
                log.Add("STILL-CANNOT-MOVE[" + why + "]");
                // a programmatically opened UI that a player would close with Esc: give the player back
                if (why == "moveable=False") { me.moveable = true; log.Add("forced-moveable"); }
            }
        }
        catch { }
    }

    internal static string Blockers()
    {
        var me = PlayerControl.LocalPlayer;
        var l = new List<string>();
        try { if (!me.moveable) l.Add("moveable=False"); } catch { }
        try { if (Minigame.Instance) l.Add("minigame=" + Minigame.Instance.GetType().Name); } catch { }
        try { if (MapBehaviour.Instance && MapBehaviour.Instance.IsOpen) l.Add("map"); } catch { }
        try { if (MeetingHud.Instance) l.Add("meeting"); } catch { }
        try { if (ExileController.Instance) l.Add("exile"); } catch { }
        try { if (IntroCutscene.Instance) l.Add("intro"); } catch { }
        try { if (HudManager.Instance.Chat.IsOpenOrOpening) l.Add("chat"); } catch { }
        try { if (me.inVent) l.Add("vent"); if (me.onLadder) l.Add("ladder"); if (me.inMovingPlat) l.Add("platform"); } catch { }
        try { if (me.Data.IsDead) l.Add("dead"); } catch { }
        try { if (HudManager.Instance.PlayerCam.Target != me) l.Add("cam-target"); } catch { }
        try { if (HudManager.Instance.IsIntroDisplayed) l.Add("introDisplayed"); } catch { }
        try { if (HudManager.Instance.shhhEmblem.isActiveAndEnabled) l.Add("shhh"); } catch { }
        return string.Join(",", l);
    }

    // the meeting's Proceed button, pressed like a player would (only when it is actually shown)
    internal static string Proceed()
    {
        try
        {
            var m = MeetingHud.Instance;
            if (!m) return "no-meeting";
            bool shown = m.ProceedButton && m.ProceedButton.gameObject.activeInHierarchy;
            DuoPlugin.Say($"proceed button shown={shown} state={m.state}");
            if (shown) { m.ProceedButton.OnClick.Invoke(); return "clicked"; }
            return "not-shown";
        }
        catch (Exception e) { DuoPlugin.Say("proceed threw " + e.Message); return "EXC"; }
    }

    internal static void Chat(string text)
    {
        try
        {
            var hud = HudManager.Instance;
            var cc = hud.Chat;
            cc.freeChatField.textArea.SetText(text);
            cc.SendChat();
            DuoPlugin.Say("chat sent: " + text);
        }
        catch (Exception e) { DuoPlugin.Say("chat failed: " + e.Message); }
    }
}

internal static partial class DuoHost
{
    static int seq;
    static readonly List<string> report = new();

    internal static IEnumerator Snap(string label, float timeout = 15f)
    {
        int s = ++seq;
        DuoPlugin.Broadcast($"snap {s} {label}");
        var want = PlayerControl.AllPlayerControls.ToArray().Count(p => p && p != PlayerControl.LocalPlayer && !p.notRealPlayer);
        yield return Co.Until(() => DuoCommands.Acks.Count(x => x.StartsWith(s + "/")) >= Math.Min(want, DuoPlugin.ExpectedClients), timeout);
        int got = DuoCommands.Acks.Count(x => x.StartsWith(s + "/"));
        if (got < DuoPlugin.ExpectedClients) DuoPlugin.Say($"snap {label}: only {got}/{DuoPlugin.ExpectedClients} acks");
    }

    static void Mark(string m) => DuoPlugin.Broadcast("mark " + m);

    internal static IEnumerator Run()
    {
        yield return Co.WaitEos();
        yield return Co.Wait(2f);
        try
        {
            var host = UnityEngine.Object.FindObjectOfType<HostLocalGameButton>(true);
            for (var tr = host.transform; tr != null; tr = tr.parent) if (!tr.gameObject.activeSelf) tr.gameObject.SetActive(true);
            host.NetworkMode = NetworkModes.LocalGame;
            host.OnClick();
            DuoPlugin.Say("hosting local lobby");
        }
        catch (Exception e) { DuoPlugin.Say("host failed: " + e); yield break; }
        yield return Co.Until(() => LobbyBehaviour.Instance != null && PlayerControl.LocalPlayer != null, 60f);
        if (LobbyBehaviour.Instance == null) { DuoPlugin.Say("no lobby"); yield break; }
        DuoPlugin.Say("lobby up, waiting for clients");
        yield return Co.Until(() => PlayerControl.AllPlayerControls.Count >= 1 + DuoPlugin.ExpectedClients, 300f);
        if (PlayerControl.AllPlayerControls.Count < 1 + DuoPlugin.ExpectedClients) { DuoPlugin.Say("clients never came"); yield break; }
        DuoPlugin.Say("all clients joined, settling");
        yield return Co.Wait(12f);

        IEnumerator plan = DuoPlugin.Plan switch
        {
            "hivev4" => PlanHiveV4(),
            "hivefollow" => PlanHiveFollowup(),
            "hiveninja" => PlanHiveNinja(),
            "roles" => PlanRoles(),
            "maps" => PlanMaps(),
            "rounds" => PlanRounds(),
            "edge" => PlanEdge(),
            "features" => PlanFeatures(),
            "uidump" => DuoUiDump.Plan(report),
            "smokescreen" => PlanSmokescreen(),
            _ => PlanSmoke(),
        };
        yield return plan;

        DuoPlugin.Say("DONE " + string.Join(" ; ", report));
        DuoPlugin.Broadcast("quit");
    }

    // ---------------------------------------------------------------- plans

    static IEnumerator PlanSmoke()
    {
        Mark("lobby");
        yield return Snap("lobby");
        yield return OptionsRoundTrip();
        yield return StartRound();
        if (ShipStatus.Instance == null) yield break;
        yield return RoleSweep(new[] { "tor:Sheriff", "tor:Morphling", "tor:Medic", "uc:Werewolf", "uc:Tesla" });
        yield return MeetingTest();
    }

    // Every TOR role (Jackal/Sidekick last: TOR's erase lock keeps them), every UC role, then modifiers.
    internal static readonly string[] TorRoles = {
        "Jester","Mayor","Portalmaker","Engineer","Sheriff","Deputy","Lighter","Godfather","Mafioso","Janitor","Detective",
        "TimeMaster","Medic","Swapper","Seer","Morphling","Camouflager","Hacker","Tracker","Vampire","Snitch","Eraser","Spy",
        "Trickster","Cleaner","Warlock","SecurityGuard","Arsonist","EvilGuesser","NiceGuesser","BountyHunter","Vulture","Medium",
        "Trapper","Lawyer","Prosecutor","Pursuer","Witch","Ninja","Thief","Bomber","Yoyo" };
    internal static readonly string[] Modifiers = {
        "Bait","Bloody","AntiTeleport","Tiebreaker","Sunglasses","Mini","Vip","Invert","Chameleon","Armored","Shifter" };

    static IEnumerator PlanRoles()
    {
        var only = ReadArg("roles.txt");   // optional: one "tor:X" / "uc:X" / "mod:X" per line
        var list = only ?? TorRoles.Select(r => "tor:" + r)
            .Concat(Enum.GetNames(typeof(UcRole)).Where(n => n != "None").Select(n => "uc:" + n))
            .Concat(ForceImpostorMod_Api.ModifierNames().Select(m => "mod:" + m.Replace(' ', '_')))
            .Concat(new[] { "tor:Jackal", "tor:Sidekick" }).ToList();
        Mark("lobby");
        // spawn/newcomer/early-death shields make the host untargetable: off for the ability sweep
        foreach (var id in new[] { 1380, 1383, 1390 })
        {
            var o = CustomOption.options.FirstOrDefault(x => x.id == id);
            if (o != null && o.selection != 0) { o.selection = 0; Changed(o); DuoPlugin.Say($"option {id} off"); }
        }
        CustomOption.ShareOptionSelections();
        yield return Co.Wait(6f);
        yield return Snap("lobby");
        yield return StartRound();
        if (ShipStatus.Instance == null) yield break;
        yield return MeetingTest();   // a meeting ends the spawn shields (Anti Start Kill, newcomer, early death)
        yield return RoleSweep(list);
        yield return MeetingTest();
    }

    static List<string> ReadArg(string file)
    {
        var p = Path.Combine(DuoPlugin.Root, file);
        if (!File.Exists(p)) return null;
        var l = File.ReadAllLines(p).Select(x => x.Trim()).Where(x => x.Length > 0 && !x.StartsWith("#")).ToList();
        return l.Count > 0 ? l : null;
    }

    // Atlas keeps the map list private; index 0 = vanilla, 1.. = Atlas + registered external maps.
    static Type AtlasSel => AccessTools.TypeByName("UnknownsAtlas.AtlasSelection");
    static List<string> AtlasKeys()
    {
        var keys = new List<string>();
        try
        {
            var maps = AtlasSel.GetField("Maps", BindingFlags.NonPublic | BindingFlags.Static).GetValue(null) as IList;
            foreach (var m in maps) keys.Add((string)m.GetType().GetField("Key").GetValue(m));
        }
        catch (Exception e) { DuoPlugin.Say("atlas keys: " + e.Message); }
        return keys;
    }
    static void AtlasSet(int idx) => AccessTools.Method(AtlasSel, "Set").Invoke(null, new object[] { idx, true });

    static void SetVanillaMap(byte id)
    {
        var o = GameOptionsManager.Instance.CurrentGameOptions;
        o.SetByte(ByteOptionNames.MapId, id);
        GameOptionsManager.Instance.GameHostOptions = o;
        PlayerControl.LocalPlayer.RpcSyncSettings(GameOptionsManager.Instance.gameOptionsFactory.ToBytes(o, false));
    }

    static IEnumerator PlanMaps()
    {
        var keys = AtlasKeys();
        DuoPlugin.Say("atlas maps: " + string.Join(",", keys));
        var runs = new List<(string label, byte vanilla, int atlas)>();
        foreach (var v in new byte[] { 0, 1, 2, 4, 5 }) runs.Add(("vanilla" + v, v, 0));
        for (int i = 0; i < keys.Count; i++) runs.Add(("atlas-" + keys[i], 0, i + 1));
        var only = ReadArg("maps.txt");
        if (only != null) runs = runs.Where(r => only.Contains(r.label)).ToList();
        foreach (var r in runs)
        {
            Mark("map " + r.label);
            yield return Co.Until(() => LobbyBehaviour.Instance != null && PlayerControl.AllPlayerControls.Count >= 1 + DuoPlugin.ExpectedClients, 120f);
            if (LobbyBehaviour.Instance == null) { report.Add($"{r.label}:NO-LOBBY"); yield break; }
            yield return Co.Wait(6f);
            try { SetVanillaMap(r.vanilla); AtlasSet(r.atlas); } catch (Exception e) { DuoPlugin.Say("map select: " + e); }
            yield return Co.Wait(6f);
            yield return Snap("lobby:" + r.label);
            yield return StartRound();
            if (ShipStatus.Instance == null) { report.Add($"{r.label}:NO-SHIP"); yield break; }
            yield return Snap("map:" + r.label);
            yield return MeetingTest();
            yield return EndRound(r.label);
        }
    }

    // Lets one game end go through Bypass, then everybody presses "play again".
    static IEnumerator EndRound(string label)
    {
        Mark("end " + label);
        try
        {
            var t = AccessTools.TypeByName("TOR_BypassTest.BypassPlugin");
            t?.GetField("FreezeActive")?.SetValue(null, false);
            t?.GetField("AllowOneEnd")?.SetValue(null, true);
            GameManager.Instance.RpcEndGame(GameOverReason.HumansByVote, false);
        }
        catch (Exception e) { DuoPlugin.Say("end failed: " + e.Message); }
        yield return Co.Until(() => ShipStatus.Instance == null, 30f);
        report.Add($"{label}:{(ShipStatus.Instance == null ? "ended" : "END-FAILED")}");
        yield return Co.Until(() => LobbyBehaviour.Instance != null, 90f);
        report.Add($"{label}:{(LobbyBehaviour.Instance != null ? "back-in-lobby" : "NO-LOBBY-AFTER-END")}");
    }

    // rounds.txt, one round per line:  <label> [map=<vanilla id>|atlas=<key>] [random:<seed>] [<id|name>=<selection>]...
    // Names match CustomOption.name case-insensitively (first hit). Defaults are restored after each round.
    static IEnumerator PlanRounds()
    {
        var lines = ReadArg("rounds.txt") ?? new List<string> { "default" };
        var defaults = CustomOption.options.ToDictionary(o => o, o => o.selection);
        var keys = AtlasKeys();
        foreach (var line in lines)
        {
            var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            var label = parts[0];
            Mark("round " + line);
            yield return Co.Until(() => LobbyBehaviour.Instance != null && PlayerControl.AllPlayerControls.Count >= 1 + DuoPlugin.ExpectedClients, 120f);
            if (LobbyBehaviour.Instance == null) { report.Add($"{label}:NO-LOBBY"); yield break; }
            yield return Co.Wait(6f);
            foreach (var kv in defaults) if (kv.Key.selection != kv.Value) { kv.Key.selection = kv.Value; Changed(kv.Key); }
            byte vmap = 0; int amap = 0;
            foreach (var p in parts.Skip(1))
            {
                try
                {
                    if (p == "max:" || p == "min:")
                    {
                        foreach (var o in CustomOption.options)
                        {
                            if (o.id == 0 || o.selections == null || o.selections.Length < 2) continue;
                            o.selection = p == "max:" ? o.selections.Length - 1 : 0; Changed(o);
                        }
                        continue;
                    }
                    if (p.StartsWith("random:"))
                    {
                        var rnd = new System.Random(int.Parse(p.Substring(7)));
                        foreach (var o in CustomOption.options)
                        {
                            if (o.id == 0 || o.selections == null || o.selections.Length < 2) continue;
                            o.selection = rnd.Next(o.selections.Length); Changed(o);
                        }
                        continue;
                    }
                    var kv = p.Split('=');
                    if (kv[0] == "map") { vmap = byte.Parse(kv[1]); continue; }
                    if (kv[0] == "atlas") { amap = keys.FindIndex(k => k.Equals(kv[1], StringComparison.OrdinalIgnoreCase)) + 1; continue; }
                    var name = kv[0].Replace('_', ' ');
                    var opt = int.TryParse(kv[0], out int id) ? CustomOption.options.FirstOrDefault(o => o.id == id)
                        : CustomOption.options.FirstOrDefault(o => string.Equals(StripTags(o.name), name, StringComparison.OrdinalIgnoreCase));
                    if (opt == null) { DuoPlugin.Say($"option '{kv[0]}' not found"); report.Add($"{label}:no-option-{kv[0]}"); continue; }
                    opt.selection = Mathf.Clamp(int.Parse(kv[1]), 0, opt.selections.Length - 1); Changed(opt);
                    DuoPlugin.Say($"option {opt.id} '{StripTags(opt.name)}' = {opt.selections[opt.selection]}");
                }
                catch (Exception e) { DuoPlugin.Say($"bad token '{p}': {e.Message}"); }
            }
            CustomOption.ShareOptionSelections();
            try { SetVanillaMap(vmap); AtlasSet(amap); } catch (Exception e) { DuoPlugin.Say("map select: " + e.Message); }
            yield return Co.Wait(8f);
            yield return Snap("lobby:" + label);
            yield return StartRound();
            if (ShipStatus.Instance == null) { report.Add($"{label}:NO-SHIP"); yield break; }
            yield return Co.Wait(12f);
            yield return Snap("r1:" + label);
            yield return MeetingTest();
            foreach (var c in ClientTags())
            {
                DuoCommands.Done.Remove(c);
                DuoPlugin.Broadcast($"press {c} {HostId}");
                yield return Co.Until(() => DuoCommands.Done.ContainsKey(c), 40f);
                report.Add($"{label}/{c}:{(DuoCommands.Done.TryGetValue(c, out var d) ? d : "NO-DONE")}");
            }
            yield return Co.Wait(4f);
            if (MeetingHud.Instance) { MeetingHud.Instance.RpcClose(); yield return Co.Wait(12f); }
            yield return Snap("r2:" + label);
            yield return EndRound(label);
        }
        foreach (var kv in defaults) if (kv.Key.selection != kv.Value) { kv.Key.selection = kv.Value; Changed(kv.Key); }
    }

    static IEnumerable<string> ClientTags() { for (int i = 0; i < DuoPlugin.ExpectedClients; i++) yield return ((char)('B' + i)).ToString(); }
    static string StripTags(string s) => System.Text.RegularExpressions.Regex.Replace(s ?? "", "<[^>]+>", "").Trim();

    static readonly FieldInfo onChangeF = AccessTools.Field(typeof(CustomOption), "onChange");
    static void Changed(CustomOption o) { try { (onChangeF?.GetValue(o) as Action)?.Invoke(); } catch (Exception e) { DuoPlugin.Say($"onChange {o.id} threw {e.GetType().Name}: {e.Message}"); } }

    static IEnumerator OptionsRoundTrip()
    {
        Mark("options random");
        var old = CustomOption.options.ToDictionary(o => o, o => o.selection);
        var rnd = new System.Random(4711);
        foreach (var o in CustomOption.options)
        {
            if (o.id == 0 || o.selections == null || o.selections.Length < 2) continue;
            o.selection = rnd.Next(o.selections.Length);
            Changed(o);
        }
        CustomOption.ShareOptionSelections();
        yield return Co.Wait(10f);
        yield return Snap("opt-rand");
        foreach (var kv in old) { if (kv.Key.selection != kv.Value) { kv.Key.selection = kv.Value; Changed(kv.Key); } }
        CustomOption.ShareOptionSelections();
        yield return Co.Wait(10f);
        yield return Snap("opt-restored");
    }

    static IEnumerator StartRound()
    {
        Mark("start game");
        SetBypassFreeze(true);   // before the start: with few players the end check fires during the intro
        try { AmongUsClient.Instance.StartGame(); } catch (Exception e) { DuoPlugin.Say("StartGame threw " + e); }
        yield return Co.Until(() => ShipStatus.Instance != null, 90f);
        if (ShipStatus.Instance == null) { DuoPlugin.Say("FAIL: no ShipStatus after StartGame"); report.Add("start:FAIL"); yield break; }
        // the intro is over when the local player may move again (TOR/UC/UTS stretch the intro)
        float stable = -1f, t0 = Time.realtimeSinceStartup;
        while (Time.realtimeSinceStartup - t0 < 90f)
        {
            bool ok = false;
            try { ok = IntroCutscene.Instance == null && PlayerControl.LocalPlayer && PlayerControl.LocalPlayer.CanMove && !MeetingHud.Instance; } catch { }
            if (!ok) stable = -1f;
            else if (stable < 0) stable = Time.realtimeSinceStartup;
            else if (Time.realtimeSinceStartup - stable > 2f) break;
            yield return null;
        }
        DuoPlugin.Say($"intro over after {Time.realtimeSinceStartup - t0:F1}s");
        yield return Co.Wait(8f);
        SetBypassFreeze(true);
        yield return Snap("intro");
    }

    internal static void SetBypassFreeze(bool on)
    {
        try
        {
            var t = AccessTools.TypeByName("TOR_BypassTest.BypassPlugin");
            t?.GetField("FreezeActive")?.SetValue(null, on);
            DuoPlugin.Say($"Bypass FreezeActive={on} ({(t != null ? "found" : "missing")})");
        }
        catch (Exception e) { DuoPlugin.Say("bypass: " + e.Message); }
    }

    static byte HostId => PlayerControl.LocalPlayer.PlayerId;
    static PlayerControl ClientPlayer(string tag)
    {
        // clients join in order B, C, ...: the n-th non-host player by id
        var others = PlayerControl.AllPlayerControls.ToArray().Where(p => p && p.PlayerId != HostId).OrderBy(p => p.PlayerId).ToList();
        int i = tag[0] - 'B';
        return i >= 0 && i < others.Count ? others[i] : null;
    }

    static IEnumerator RoleSweep(IEnumerable<string> roles)
    {
        var b = ClientPlayer("B");
        if (b == null) { DuoPlugin.Say("no client player"); yield break; }
        // the host is the target of every ability: a plain crewmate (impostors cannot target each other)
        try { DuoPlugin.Say("host plain crew: " + RoleControl.SetPlain(HostId, false)); } catch (Exception e) { DuoPlugin.Say("host plain: " + e.Message); }
        foreach (var c in ClientTags().Skip(1)) { var o = ClientPlayer(c); if (o) try { RoleControl.SetPlain(o.PlayerId, false); } catch { } }
        yield return Co.Wait(3f);
        foreach (var r in roles)
        {
            if (MeetingHud.Instance) { MeetingHud.Instance.RpcClose(); }
            yield return Co.Until(() => !MeetingHud.Instance && !ExileController.Instance, 30f);
            Mark("role " + r);
            yield return EnsureAlive(HostId);
            yield return EnsureAlive(b.PlayerId);
            string res;
            try
            {
                var kind = r.Split(':')[0];
                var name = r.Split(':')[1];
                if (kind == "tor") res = ForceImpostorMod_Api.SetTor(b.PlayerId, name);
                else if (kind == "mod") res = ForceImpostorMod_Api.AddMod(b.PlayerId, name);
                else res = ForceImpostorMod_Api.SetUc(b.PlayerId, name);
            }
            catch (Exception e) { res = "EXC " + e.Message; }
            DuoPlugin.Say($"assign {r}: {res}");
            yield return Co.Wait(3f);
            yield return Snap("set:" + r);
            DuoCommands.Done.Remove("B");
            DuoPlugin.Broadcast($"press B {HostId}");
            yield return Co.Until(() => DuoCommands.Done.ContainsKey("B"), 40f);
            report.Add($"{r}=>{(DuoCommands.Done.TryGetValue("B", out var d) ? d : "NO-DONE")}");
            yield return Co.Wait(2f);
            if (MeetingHud.Instance) { yield return Snap("meeting:" + r); MeetingHud.Instance.RpcClose(); yield return Co.Wait(12f); }
            yield return Snap("used:" + r);
        }
    }

    static IEnumerator EnsureAlive(byte pid)
    {
        var p = DuoCommands.ById(pid);
        if (p && p.Data != null && p.Data.IsDead)
        {
            DuoPlugin.Say($"revive {pid}: {ForceImpostorMod_Api.Revive(pid)}");
            yield return Co.Wait(2f);
        }
    }

    static IEnumerator MeetingTest()
    {
        Mark("meeting");
        DuoPlugin.Broadcast("report B");
        yield return Co.Until(() => MeetingHud.Instance != null, 15f);
        if (!MeetingHud.Instance) { report.Add("meeting:DID-NOT-OPEN"); yield break; }
        // votes cast during the opening animation are dropped: wait for the voting phase
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.NotVoted || MeetingHud.Instance.state == MeetingHud.VoteStates.Voted, 20f);
        yield return Co.Wait(2f);
        yield return Snap("meeting-open");
        if (MeetingHud.Instance) MeetingHud.Instance.CmdCastVote(HostId, 253);
        foreach (var c in ClientTags()) DuoPlugin.Broadcast($"vote {c} 253");
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.Results, 30f);
        yield return Co.Wait(2f);
        if (MeetingHud.Instance && MeetingHud.Instance.state == MeetingHud.VoteStates.Results)
        {
            yield return Snap("meeting-results");
            yield return Co.Wait(3f);
            report.Add("proceed-host:" + DuoClient.Proceed());
            DuoPlugin.Broadcast("proceed", false);
        }
        if (MeetingHud.Instance && MeetingHud.Instance.state != MeetingHud.VoteStates.Results && MeetingHud.Instance.state != MeetingHud.VoteStates.Proceeding) { report.Add("meeting:NO-RESULTS-" + MeetingHud.Instance.state); DuoPlugin.Say("FAIL meeting did not reach results: " + MeetingHud.Instance.state); MeetingHud.Instance.RpcClose(); }
        yield return Co.Until(() => MeetingHud.Instance == null, 30f);
        yield return Co.Wait(10f);
        yield return Snap("after-meeting");
        report.Add("meeting:ok");
    }
}

// Role Control access (hard reference, the harness only runs with it installed).
internal static class ForceImpostorMod_Api
{
    internal static string SetTor(byte pid, string name) => RoleControl.SetTorRole(pid, (RoleId)Enum.Parse(typeof(RoleId), name));
    internal static string SetUc(byte pid, string name) => RoleControl.SetUcRole(pid, (UcRole)Enum.Parse(typeof(UcRole), name));
    internal static string Revive(byte pid) => RoleControl.Revive(pid);
    internal static IEnumerable<string> ModifierNames() => RoleControl.ModifierIds.Where(m => m != RoleId.Lover).Select(m => RoleControl.ModifierName(m));
    internal static string AddMod(byte pid, string name)
    {
        var m = RoleControl.ModifierIds.FirstOrDefault(x => RoleControl.ModifierName(x) == name.Replace('_', ' '));
        return RoleControl.AddModifier(pid, m);
    }
}
