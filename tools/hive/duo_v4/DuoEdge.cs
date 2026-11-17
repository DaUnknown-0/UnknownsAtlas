// Edge-case plan: kill + body report + exile, sabotages/doors/vent + tie vote, task win, impostor win,
// a client leaving mid-round, the host leaving mid-round. Needs host + 2 clients (B, C).
using System;
using System.Collections;
using System.Linq;
using HarmonyLib;
using UnityEngine;
using ForceImpostorMod;

namespace DuoTest;

internal static partial class DuoHost
{
    static void AllowEnd()
    {
        var t = AccessTools.TypeByName("TOR_BypassTest.BypassPlugin");
        t?.GetField("FreezeActive")?.SetValue(null, false);
        t?.GetField("AllowOneEnd")?.SetValue(null, true);
    }

    static string LastReason()
    {
        try { return EndGameResult.CachedGameOverReason.ToString(); } catch (Exception e) { return "?" + e.GetType().Name; }
    }

    static IEnumerator WaitEnd(string label, string expect)
    {
        yield return Co.Until(() => ShipStatus.Instance == null, 45f);
        string r = ShipStatus.Instance == null ? LastReason() : "NO-END";
        report.Add($"{label}:end={r}{(r.Contains(expect) ? "" : "(expected " + expect + ")")}");
        DuoPlugin.Say($"{label}: game over {r}");
        if (ShipStatus.Instance != null)
        {
            // force the round to end so the plan can go on
            try { SetBypassFreeze(false); GameManager.Instance.RpcEndGame(GameOverReason.HumansByVote, false); } catch { }
            yield return Co.Until(() => ShipStatus.Instance == null, 30f);
        }
        yield return Co.Until(() => LobbyBehaviour.Instance != null, 90f);
        report.Add($"{label}:{(LobbyBehaviour.Instance != null ? "back-in-lobby" : "NO-LOBBY")}");
    }

    static IEnumerator NextRound(string label)
    {
        Mark("edge " + label);
        yield return Co.Until(() => LobbyBehaviour.Instance != null && PlayerControl.AllPlayerControls.Count >= 2, 120f);
        yield return Co.Wait(6f);
        yield return Snap("lobby:" + label);
        yield return StartRound();
    }

    static void Roles(byte impostorId)
    {
        foreach (var p in PlayerControl.AllPlayerControls.ToArray())
        {
            if (!p) continue;
            try { DuoPlugin.Say($"role {p.PlayerId}: {RoleControl.SetPlain(p.PlayerId, p.PlayerId == impostorId)}"); }
            catch (Exception e) { DuoPlugin.Say("role: " + e.Message); }
            DuoPlugin.Broadcast("v4 faction * " + p.PlayerId + " " + (p.PlayerId==impostorId?"1":"0"));
        }
    }

    static IEnumerator Vote(byte hostVote, byte bVote, byte cVote, string label)
    {
        yield return Co.Until(() => MeetingHud.Instance != null, 15f);
        if (!MeetingHud.Instance) { report.Add(label + ":meeting-DID-NOT-OPEN"); yield break; }
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.NotVoted || MeetingHud.Instance.state == MeetingHud.VoteStates.Voted, 20f);
        yield return Co.Wait(2f);
        yield return Snap("meeting:" + label);
        if (MeetingHud.Instance) MeetingHud.Instance.CmdCastVote(HostId, hostVote);
        DuoPlugin.Broadcast($"vote B {bVote}");
        if (cVote != 254) DuoPlugin.Broadcast($"vote C {cVote}");
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.Results, 40f);
        yield return Co.Wait(3f);
        if (MeetingHud.Instance) { DuoClient.Proceed(); DuoPlugin.Broadcast("proceed", false); }
        yield return Co.Until(() => MeetingHud.Instance == null, 30f);
        yield return Co.Until(() => ExileController.Instance == null, 30f);
        yield return Co.Wait(6f);
        yield return Snap("after:" + label);
    }

    static IEnumerator PlanEdge()
    {
        var b = ClientPlayer("B"); var c = ClientPlayer("C");
        if (!b || !c) { report.Add("edge:needs-2-clients"); yield break; }
        byte bid = b.PlayerId, cid = c.PlayerId;

        // ---- E1 kill, body report, majority exile of the impostor -> crew win by vote
        yield return NextRound("e1-kill-report-exile");
        Roles(bid); yield return Co.Wait(3f);
        try { DuoCommands.ById(bid).RpcMurderPlayer(DuoCommands.ById(cid), true); } catch (Exception e) { DuoPlugin.Say("murder: " + e.Message); }
        yield return Co.Wait(4f);
        yield return Snap("e1-after-kill");
        report.Add($"e1:victim-dead={DuoCommands.ById(cid)?.Data?.IsDead}");
        try { PlayerControl.LocalPlayer.CmdReportDeadBody(DuoCommands.ById(cid).Data); } catch (Exception e) { DuoPlugin.Say("report body: " + e.Message); }
        // with 3 players the kill leaves 1 vs 1: the end stays frozen until the impostor is voted out
        yield return Vote(bid, bid, 254, "e1");
        report.Add($"e1:impostor-exiled={DuoCommands.ById(bid)?.Data?.IsDead}");
        AllowEnd();
        yield return WaitEnd("e1", "Vote");

        // ---- E2 sabotages, doors, vent, tie vote
        yield return NextRound("e2-sabotage-vent-tie");
        Roles(bid); yield return Co.Wait(3f);
        foreach (var sys in new[] { "Electrical", "Comms", "Reactor", "LifeSupp" })
        {
            ResetSabotageTimer();
            DuoPlugin.Broadcast($"sabo B {sys}");
            yield return Co.Wait(5f);
            yield return Snap("e2-sabo-" + sys);
            report.Add($"e2:{sys}-active={SabotageActive(sys)}");
            Repair(sys);
            yield return Co.Wait(4f);
            report.Add($"e2:{sys}-repaired={!SabotageActive(sys)}");
        }
        ResetSabotageTimer();
        DuoPlugin.Broadcast("sabo B doors");
        yield return Co.Wait(4f);
        DuoPlugin.Broadcast("vent B 0");
        yield return Co.Wait(6f);
        yield return Snap("e2-after-vent");
        DuoPlugin.Broadcast("report B");
        yield return Vote(bid, HostId, 253, "e2-tie");
        report.Add($"e2:nobody-exiled={PlayerControl.AllPlayerControls.ToArray().Count(p => p && p.Data != null && p.Data.IsDead) == 0}");
        yield return EndRound("e2");

        // ---- E3 crew task win
        yield return NextRound("e3-taskwin");
        Roles(bid); yield return Co.Wait(3f);
        AllowEnd();
        DuoPlugin.Broadcast("tasks *");
        yield return WaitEnd("e3", "Task");

        // ---- E4 impostor win by kill (1 impostor vs 1 crew left)
        yield return NextRound("e4-impwin");
        Roles(bid); yield return Co.Wait(3f);
        AllowEnd();
        try { DuoCommands.ById(bid).RpcMurderPlayer(DuoCommands.ById(cid), true); } catch (Exception e) { DuoPlugin.Say("murder: " + e.Message); }
        yield return WaitEnd("e4", "Kill");

        // ---- E5 a client leaves mid-round, the round goes on
        yield return NextRound("e5-client-leaves");
        Roles(bid); yield return Co.Wait(3f);
        DuoPlugin.Broadcast("quitme C");
        yield return Co.Wait(12f);
        yield return Snap("e5-after-leave");
        var cp = DuoCommands.ById(cid);
        report.Add($"e5:c-disconnected={cp == null || cp.Data == null || cp.Data.Disconnected}");
        DuoPlugin.Broadcast("report B");
        yield return Vote(253, 253, 254, "e5");
        yield return EndRound("e5");

        // ---- E6 the host leaves mid-round (the client gets disconnected)
        yield return NextRound("e6-host-leaves");
        yield return Co.Wait(5f);
        DuoPlugin.Say("DONE " + string.Join(" ; ", report));
        report.Clear();
        DuoDriver.QuitAt = Time.realtimeSinceStartup + 2f;
    }

    static T Sys<T>(SystemTypes s) where T : Il2CppSystem.Object
    {
        try { var sh = ShipStatus.Instance; return sh != null && sh.Systems.ContainsKey(s) ? sh.Systems[s].TryCast<T>() : null; } catch { return null; }
    }

    static void ResetSabotageTimer()
    {
        var sab = Sys<SabotageSystemType>(SystemTypes.Sabotage);
        if (sab != null) { sab.Timer = 0f; sab.IsDirty = true; }
    }

    static bool SabotageActive(string sys)
    {
        try
        {
            switch (sys)
            {
                case "Electrical": { var s = Sys<SwitchSystem>(SystemTypes.Electrical); return s != null && s.ActualSwitches != s.ExpectedSwitches; }
                case "Comms": { var s = Sys<HudOverrideSystemType>(SystemTypes.Comms); return s != null && s.IsActive; }
                case "Reactor": { var s = Sys<ReactorSystemType>(SystemTypes.Reactor); return s != null && s.IsActive; }
                case "LifeSupp": { var s = Sys<LifeSuppSystemType>(SystemTypes.LifeSupp); return s != null && s.IsActive; }
            }
        }
        catch { }
        return false;
    }

    static void Repair(string sys)
    {
        try
        {
            var sh = ShipStatus.Instance;
            switch (sys)
            {
                case "Electrical":
                    {
                        var s = Sys<SwitchSystem>(SystemTypes.Electrical);
                        if (s == null) break;
                        for (int i = 0; i < 5; i++)
                            if (((s.ActualSwitches >> i) & 1) != ((s.ExpectedSwitches >> i) & 1)) sh.RpcUpdateSystem(SystemTypes.Electrical, (byte)i);
                        break;
                    }
                case "Comms": sh.RpcUpdateSystem(SystemTypes.Comms, 0); break;
                case "Reactor": sh.RpcUpdateSystem(SystemTypes.Reactor, 16); break;
                case "LifeSupp": sh.RpcUpdateSystem(SystemTypes.LifeSupp, 16); break;
            }
        }
        catch (Exception e) { DuoPlugin.Say($"repair {sys}: {e.Message}"); }
    }
}

internal static class DuoEdgeClient
{
    internal static IEnumerator Vent(int id)
    {
        var me = PlayerControl.LocalPlayer;
        DuoPlugin.Say($"vent {id} enter");
        try { me.MyPhysics.RpcEnterVent(id); } catch (Exception e) { DuoPlugin.Say("enter vent: " + e.Message); }
        yield return Co.Wait(3f);
        DuoPlugin.Say($"vent {id} exit");
        try { me.MyPhysics.RpcExitVent(id); } catch (Exception e) { DuoPlugin.Say("exit vent: " + e.Message); }
    }

    internal static void CompleteTasks()
    {
        var me = PlayerControl.LocalPlayer;
        if (me == null || me.Data == null || me.Data.Role == null || me.Data.Role.IsImpostor) return;
        int n = 0;
        foreach (var t in me.myTasks.ToArray())
        {
            if (t == null || t.IsComplete) continue;
            try { me.RpcCompleteTask(t.Id); n++; } catch (Exception e) { DuoPlugin.Say("task: " + e.Message); }
        }
        DuoPlugin.Say($"completed {n} task(s)");
    }

    internal static void Sabotage(string what)
    {
        var sh = ShipStatus.Instance;
        if (sh == null) return;
        try
        {
            if (what == "doors") { sh.RpcCloseDoorsOfType(SystemTypes.Cafeteria); DuoPlugin.Say("doors closed"); return; }
            var sys = (SystemTypes)Enum.Parse(typeof(SystemTypes), what);
            sh.RpcUpdateSystem(SystemTypes.Sabotage, (byte)sys);
            DuoPlugin.Say($"sabotage {what}");
        }
        catch (Exception e) { DuoPlugin.Say($"sabotage {what}: {e.Message}"); }
    }
}
