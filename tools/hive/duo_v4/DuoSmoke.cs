// Plan "smokescreen" (2026-11-13): Unknown's Smokescreen on clients B and C (setup.sh writes their config with
// OnlyInStreamerMode=false), host A unprotected as the reference.
//   1. B Morphling (impostor), C Sheriff   -> probe + screenshots on every instance
//   2. B uses its buttons on the host        -> recap entries
//   3. B Sheriff, C Morphling                -> probe again (button layout impostor vs crew)
//   4. C kills B                             -> B is a ghost, probe (ghost info shuffled)
//   5. meeting, C votes the host             -> probe in the meeting (vote icons, info lines)
//   6. end of the round                      -> every instance screenshots its end screen (recap)
using System;
using System.Collections;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using HarmonyLib;
using TheOtherRoles;
using TheOtherRoles.Objects;
using UnityEngine;

namespace DuoTest;

internal static class DuoSmoke
{
    static string Strip(string s) => s == null ? "<null>" : Regex.Replace(s, "<[^>]*>", "").Replace("\n", " / ").Trim();

    static bool AnyRendererOn(GameObject go)
    {
        foreach (var r in go.GetComponentsInChildren<Renderer>())
            if (r != null && r.enabled) return true;
        return false;
    }

    static string Vis(Component c) =>
        c == null ? "none" : !c.gameObject.activeInHierarchy ? "off" : AnyRendererOn(c.gameObject) ? "VISIBLE" : "hidden";

    static string Pos(Component c) => c == null ? "-" : $"{c.transform.localPosition.x:F2},{c.transform.localPosition.y:F2}";

    internal static string Probe()
    {
        var sb = new StringBuilder();
        try
        {
            var shield = AccessTools.TypeByName("UnknownsSmokescreen.Shield");
            sb.Append("active=" + (shield == null ? "NO-MOD" : AccessTools.Property(shield, "Active").GetValue(null)));
            var local = PlayerControl.LocalPlayer;
            sb.Append($" real='{RoleInfo.GetRolesString(local, false, false, true)}' dead={local.Data.IsDead}");
            var info = local.cosmetics.nameText.transform.parent.FindChild("Info");
            sb.Append($" info='{Strip(info != null ? info.GetComponent<TMPro.TMP_Text>()?.text : "<none>")}'");

            int colored = 0, infos = 0;
            foreach (var p in PlayerControl.AllPlayerControls)
            {
                if (p == null || p == local) continue;
                var c = p.cosmetics.nameText.color;
                if (c.r < 0.99f || c.g < 0.99f || c.b < 0.99f) colored++;
                var i = p.cosmetics.nameText.transform.parent.FindChild("Info");
                var t = i != null ? i.GetComponent<TMPro.TMP_Text>() : null;
                if (t != null && !string.IsNullOrEmpty(t.text)) { infos++; sb.Append($" other{p.PlayerId}='{Strip(t.text)}'"); }
            }
            sb.Append($" colouredNames={colored} otherInfos={infos}");

            var hud = HudManager.Instance;
            sb.Append($" kill={Vis(hud.KillButton)} sabo={Vis(hud.SabotageButton)} vent={Vis(hud.ImpostorVentButton)}");
            int on = 0, seen = 0;
            foreach (var b in CustomButton.buttons)
                if (b != null && b.actionButton != null && b.actionButton.gameObject.activeInHierarchy) { on++; if (AnyRendererOn(b.actionButton.gameObject)) seen++; }
            sb.Append($" customVisible={seen}/{on}");
            sb.Append($" use={Pos(hud.UseButton)} report={Pos(hud.ReportButton)} pet={Pos(hud.PetButton)}");

            var tab = hud.TaskPanel != null ? hud.TaskPanel.tab.transform.FindChild("TabText_TMP") : null;
            sb.Append($" tab='{Strip(tab != null ? tab.GetComponent<TMPro.TMP_Text>().text : "<none>")}'");
            string tasks = hud.TaskPanel != null && hud.TaskPanel.taskText != null ? hud.TaskPanel.taskText.text : "";
            sb.Append($" task1='{Strip((tasks ?? "").Split('\n').FirstOrDefault())}'");

            if (MeetingHud.Instance != null)
            {
                int mi = 0, grey = 0, colour = 0;
                foreach (var a in MeetingHud.Instance.playerStates)
                {
                    var i = a.NameText.transform.parent.FindChild("Info");
                    var t = i != null ? i.GetComponent<TMPro.TMP_Text>() : null;
                    if (t != null && !string.IsNullOrEmpty(t.text)) { mi++; sb.Append($" m{a.TargetPlayerId}='{Strip(t.text)}'"); }
                    var sp = a.GetComponent<VoteSpreader>();
                    if (sp != null) foreach (var v in sp.Votes) { if (v == null) continue; var col = v.material.GetColor(PlayerMaterial.BodyColor); if (Mathf.Abs(col.r - col.g) < 0.05f && Mathf.Abs(col.g - col.b) < 0.05f) grey++; else colour++; }
                }
                sb.Append($" meetingInfos={mi} votesGrey={grey} votesColour={colour}");
            }
        }
        catch (Exception e) { sb.Append(" ERR " + e.Message); }
        return sb.ToString();
    }

    static int endShots, introShots;

    // ---- what the screen really shows over this game window (other windows, e.g. the private overlay, included)
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out RECT r);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr h);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern int ReleaseDC(IntPtr h, IntPtr dc);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern IntPtr CreateCompatibleDC(IntPtr dc);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern IntPtr CreateCompatibleBitmap(IntPtr dc, int w, int h);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern IntPtr SelectObject(IntPtr dc, IntPtr o);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern bool BitBlt(IntPtr d, int x, int y, int w, int h, IntPtr s, int sx, int sy, uint rop);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern int GetDIBits(IntPtr dc, IntPtr bmp, uint start, uint lines, byte[] bits, ref BMI bi, uint usage);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr o);
    [System.Runtime.InteropServices.DllImport("gdi32.dll")] static extern bool DeleteDC(IntPtr dc);
    struct RECT { public int l, t, r, b; }
    struct POINT { public int x, y; }
    struct BMI { public uint size; public int w, h; public ushort planes, bits; public uint comp, sizeImage; public int xppm, yppm; public uint used, important; public uint c0, c1, c2, c3; }

    internal static void DeskShot(string label)
    {
        try
        {
            IntPtr hwnd;
            using (var p = System.Diagnostics.Process.GetCurrentProcess()) hwnd = p.MainWindowHandle;
            GetClientRect(hwnd, out var rc);
            var o = new POINT();
            ClientToScreen(hwnd, ref o);
            int w = rc.r - rc.l, h = rc.b - rc.t;
            IntPtr screen = GetDC(IntPtr.Zero), mem = CreateCompatibleDC(screen), bmp = CreateCompatibleBitmap(screen, w, h);
            IntPtr old = SelectObject(mem, bmp);
            BitBlt(mem, 0, 0, w, h, screen, o.x, o.y, 0x00CC0020 | 0x40000000);   // SRCCOPY | CAPTUREBLT (layered windows too)
            SelectObject(mem, old);
            var bi = new BMI { size = 40, w = w, h = -h, planes = 1, bits = 32 };
            var px = new byte[w * h * 4];
            GetDIBits(mem, bmp, 0, (uint)h, px, ref bi, 0);
            DeleteObject(bmp); DeleteDC(mem); ReleaseDC(IntPtr.Zero, screen);
            string dir = System.IO.Path.Combine(DuoPlugin.Root, "duo_shots");
            System.IO.Directory.CreateDirectory(dir);
            using var f = System.IO.File.Create(System.IO.Path.Combine(dir, label + ".deskraw"));
            var bw = new System.IO.BinaryWriter(f);
            bw.Write(w); bw.Write(h); bw.Write(px);
        }
        catch (Exception e) { DuoPlugin.Say("desk shot failed: " + e.Message); }
    }

    // Intro: team screen and role screen, shot by every instance itself.
    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.BeginCrewmate))]
    static class IntroTeamShot
    {
        static void Postfix()
        {
            if (AccessTools.TypeByName("UnknownsSmokescreen.Shield") == null) return;
            DuoDriver.Start(Later(1.5f, "team"));
        }
    }

    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.BeginImpostor))]
    static class IntroImpShot
    {
        static void Postfix()
        {
            if (AccessTools.TypeByName("UnknownsSmokescreen.Shield") == null) return;
            DuoDriver.Start(Later(1.5f, "team"));
        }
    }

    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.ShowRole))]
    static class IntroRoleShot
    {
        static void Postfix()
        {
            if (AccessTools.TypeByName("UnknownsSmokescreen.Shield") == null) return;
            DuoDriver.Start(Later(0.6f, "role"));
            DuoDriver.Start(Later(1.4f, "role"));
            DuoDriver.Start(Later(3.0f, "role"));
        }
    }

    static IEnumerator Later(float s, string what)
    {
        yield return Co.Wait(s);
        yield return DuoFeatures.Shot($"smoke_intro_{what}_{DuoPlugin.Tag}_{++introShots}");
    }

    // End screens: the clients cannot be messaged there, so each instance shoots its own.
    [HarmonyPatch(typeof(EndGameManager), nameof(EndGameManager.SetEverythingUp))]
    static class EndShot
    {
        static void Postfix()
        {
            if (AccessTools.TypeByName("UnknownsSmokescreen.Shield") == null) return;
            DuoDriver.Start(Later());
        }

        static IEnumerator Later()
        {
            yield return Co.Wait(3f);
            yield return DuoFeatures.Shot($"smoke_end_{DuoPlugin.Tag}_{++endShots}");
        }
    }
}

internal static partial class DuoHost
{
    static IEnumerator SmokeProbe(string label)
    {
        yield return DuoFeatures.Ask("smoke", label, 15f);
        foreach (var t in ClientTags().Prepend("A"))
            report.Add($"{label}/{t}: {DuoFeatures.Got(t, "smoke")}");
    }

    static IEnumerator PlanSmokescreen()
    {
        // anonymous votes on: the stream must not see vote colours, not even through a ghost
        DuoFeatures.SetAnonymous(true);
        yield return Co.Wait(3f);
        yield return StartRound();
        if (ShipStatus.Instance == null) yield break;
        var b = ClientPlayer("B"); var c = ClientPlayer("C");
        if (!b || !c) { report.Add("smokescreen:needs-2-clients"); yield break; }
        byte bid = b.PlayerId, cid = c.PlayerId;

        Mark("smoke 1 B impostor, C sheriff");
        try { ForceImpostorMod.RoleControl.SetPlain(HostId, false); } catch (Exception e) { DuoPlugin.Say("plain: " + e.Message); }
        DuoPlugin.Say("B: " + ForceImpostorMod_Api.SetTor(bid, "Morphling"));
        DuoPlugin.Say("C: " + ForceImpostorMod_Api.SetTor(cid, "Sheriff"));
        yield return Co.Wait(5f);
        yield return SmokeProbe("imp");

        Mark("smoke 2 B presses its buttons");
        DuoCommands.Done.Remove("B");
        DuoPlugin.Broadcast($"press B {HostId}");
        yield return Co.Until(() => DuoCommands.Done.ContainsKey("B"), 40f);
        report.Add("press:" + (DuoCommands.Done.TryGetValue("B", out var d) ? d : "NO-DONE"));
        yield return Co.Wait(3f);
        if (MeetingHud.Instance) { MeetingHud.Instance.RpcClose(); yield return Co.Wait(12f); }
        yield return EnsureAlive(HostId);

        Mark("smoke 3 B sheriff, C impostor");
        DuoPlugin.Say("B: " + ForceImpostorMod_Api.SetTor(bid, "Sheriff"));
        DuoPlugin.Say("C: " + ForceImpostorMod_Api.SetTor(cid, "Morphling"));
        yield return Co.Wait(5f);
        yield return SmokeProbe("crew");

        Mark("smoke 4 C kills B");
        try { DuoCommands.ById(cid).RpcMurderPlayer(DuoCommands.ById(bid), true); } catch (Exception e) { DuoPlugin.Say("murder: " + e.Message); }
        yield return Co.Wait(6f);
        yield return SmokeProbe("ghost");

        Mark("smoke 5 meeting");
        DuoPlugin.Broadcast("report C");
        yield return Co.Until(() => MeetingHud.Instance != null, 15f);
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.NotVoted || MeetingHud.Instance.state == MeetingHud.VoteStates.Voted, 20f);
        yield return Co.Wait(2f);
        if (MeetingHud.Instance) MeetingHud.Instance.CmdCastVote(HostId, 253);
        DuoPlugin.Broadcast($"vote C {HostId}");
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.Results, 150f);
        yield return Co.Wait(3f);
        yield return SmokeProbe("meeting");
        if (MeetingHud.Instance) { DuoClient.Proceed(); DuoPlugin.Broadcast("proceed", false); }
        yield return Co.Until(() => MeetingHud.Instance == null, 30f);
        yield return Co.Until(() => ExileController.Instance == null, 30f);
        yield return Co.Wait(4f);

        Mark("smoke 6 end");
        yield return EndRound("smoke-end");
    }
}
