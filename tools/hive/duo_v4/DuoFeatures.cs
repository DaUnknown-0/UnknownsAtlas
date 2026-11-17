// Plan "features" (2026-11-13): the new comfort features plus the meeting events, host + 2 clients (B, C).
//   lobby:   settings search (find, change a value with >, the client receives it, back with <, input lock released),
//            error toast (card + report file on host and B), Host Tools files
//   round 1: anonymous votes OFF, meeting 1 with votes -> vote history with names on every client;
//            meeting 2: Maniac defuse for C + Bug system crash for everybody -> panels open, C dies at the end
//   lobby:   change marks (an option changed after the round is marked on every client, gone when put back)
//   round 2: anonymous votes ON, meeting -> vote history with counts only
// Every client answers "probe <name> [arg]" with "pr <tag> <name> <escaped result>"; the host collects the answers.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using AmongUs.GameOptions;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;

namespace DuoTest;

internal static class DuoFeatures
{
    internal static readonly Dictionary<string, string> Answers = new();
    static ManualLogSource probeLog;

    // ---------------------------------------------------------------- every instance
    internal static void Handle(string[] a)
    {
        switch (a[0])
        {
            case "probe":
                DuoDriver.Start(Answer(a[1], a.Length > 2 ? a[2] : ""));
                break;
            case "pr":
                if (DuoPlugin.IsHost) Answers[a[1] + "/" + a[2]] = Uri.UnescapeDataString(a.Length > 3 ? a[3] : "");
                break;
        }
    }

    static void Reply(string name, string result)
    {
        string msg = $"pr {DuoPlugin.Tag} {name} {Uri.EscapeDataString(result ?? "")}";
        if (DuoPlugin.IsHost) Answers[DuoPlugin.Tag + "/" + name] = result ?? "";
        else DuoPlugin.Broadcast(msg, false);
        DuoPlugin.Say($"probe {name}: {result}");
    }

    internal static object SearchUi()
    {
        var t = AccessTools.TypeByName("UsefulTORStuff.SettingsSearchUI");
        return t == null ? null : AccessTools.Property(t, "Instance").GetValue(null);
    }

    internal static bool LockEngaged() =>
        (bool)AccessTools.Property(AccessTools.TypeByName("UsefulTORStuff.FeedbackInputLock"), "Engaged").GetValue(null);

    // the view pane: visible on the search tab, how many panels/headers it drew
    internal static string SearchViewState()
    {
        var t = AccessTools.TypeByName("UsefulTORStuff.SettingsSearchView");
        bool vis = (bool)AccessTools.Property(t, "Visible").GetValue(null);
        var pane = AccessTools.Field(t, "Pane").GetValue(null) as LobbyViewSettingsPane;
        return $"visible={vis} items={(pane != null ? pane.settingsInfo.Count : -1)}";
    }

    // a screenshot of this instance into <game>/duo_shots (end of frame, read back at once)
    internal static IEnumerator Shot(string label)
    {
        yield return new WaitForEndOfFrame();
        try
        {
            string dir = Path.Combine(DuoPlugin.Root, "duo_shots");
            Directory.CreateDirectory(dir);
            var tex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(dir, label + ".png"), ImageConversion.EncodeToPNG(tex));
            UnityEngine.Object.Destroy(tex);
        }
        catch (Exception e) { DuoPlugin.Say("shot failed: " + e.Message); }
    }

    static object Call(string type, string method, params object[] args)
    {
        var t = AccessTools.TypeByName(type);
        var m = t == null ? null : AccessTools.Method(t, method);
        return m?.Invoke(null, args);
    }

    static IEnumerator Answer(string name, string arg)
    {
        string r;
        switch (name)
        {
            case "vh":
                try { r = Call("UsefulTORStuff.VoteHistory", "BuildText") as string ?? "<null>"; } catch (Exception e) { r = "ERR " + e.Message; }
                // plain text: the colour tags would only hide what the check looks for
                r = System.Text.RegularExpressions.Regex.Replace(r, "<[^>]*>", "").Replace("\n", " | ");
                break;
            case "smoke":
                // after LateUpdate (where the mask writes), i.e. what is really drawn
                yield return new WaitForEndOfFrame();
                r = DuoSmoke.Probe();
                yield return Shot($"smoke_{arg}_{DuoPlugin.Tag}");
                DuoSmoke.DeskShot($"smoke_{arg}_{DuoPlugin.Tag}_desk");
                break;
            case "searchview":
                {
                    string res;
                    var ui = SearchUi();
                    try { Call("UsefulTORStuff.SettingsSearchView", "Open"); ui?.GetType().GetMethod("DiagQuery").Invoke(ui, new object[] { arg }); res = "opened"; }
                    catch (Exception e) { res = "ERR " + e.Message; }
                    yield return new WaitForSeconds(2f);
                    if (!res.StartsWith("ERR")) res = SearchViewState();
                    yield return Shot("search_view_" + DuoPlugin.Tag + "_" + arg.Replace(' ', '_'));
                    try { ui?.GetType().GetMethod("DiagQuery").Invoke(ui, new object[] { "" }); ui?.GetType().GetMethod("Close").Invoke(ui, null); } catch { }
                    yield return new WaitForSeconds(0.5f);
                    r = res + " lock=" + LockEngaged();
                    break;
                }
            case "marks":
                try
                {
                    var changed = AccessTools.Method(AccessTools.TypeByName("UsefulTORStuff.SettingsChangeMarks"), "Changed");
                    int n = TheOtherRoles.CustomOption.options.Count(o => o != null && (bool)changed.Invoke(null, new object[] { o }));
                    r = n.ToString();
                }
                catch (Exception e) { r = "ERR " + e.Message; }
                break;
            case "opt":
                try { var o = TheOtherRoles.CustomOption.options.FirstOrDefault(x => x.id == int.Parse(arg)); r = o == null ? "none" : o.selection.ToString(); }
                catch (Exception e) { r = "ERR " + e.Message; }
                break;
            case "defuse":
                try { r = AccessTools.Property(AccessTools.TypeByName("UnknownsCollection.ManiacDefuse"), "IsOpen").GetValue(null).ToString(); }
                catch (Exception e) { r = "ERR " + e.Message; }
                break;
            case "crash":
                try { r = AccessTools.Property(AccessTools.TypeByName("UnknownsCollection.BugCrashScreen"), "Active").GetValue(null).ToString(); }
                catch (Exception e) { r = "ERR " + e.Message; }
                break;
            case "toast":
                {
                    string dir = Path.Combine(BepInEx.Paths.BepInExRootPath, "ErrorReports");
                    int before = Directory.Exists(dir) ? Directory.GetFiles(dir, "*.txt").Length : 0;
                    probeLog ??= BepInEx.Logging.Logger.CreateLogSource("DuoTest-ErrorProbe");
                    probeLog.LogError("DuoTest probe: a deliberate error for the error toast check");
                    yield return Co.Wait(1.5f);
                    bool shown = false;
                    try
                    {
                        var t = AccessTools.TypeByName("UsefulTORStuff.ErrorToast");
                        var inst = AccessTools.Property(t, "Instance").GetValue(null);
                        var root = AccessTools.Field(t, "root").GetValue(inst) as GameObject;
                        shown = root != null && root.activeSelf;
                        if (root != null) root.SetActive(false);
                    }
                    catch (Exception e) { DuoPlugin.Say("toast read: " + e.Message); }
                    int after = Directory.Exists(dir) ? Directory.GetFiles(dir, "*.txt").Length : 0;
                    r = $"card={shown} reports={before}->{after}";
                    break;
                }
            case "hosttools":
                {
                    string dir = Path.Combine(BepInEx.Paths.ConfigPath, "HostTools");
                    r = Directory.Exists(dir) ? string.Join(",", Directory.GetFiles(dir, "*", SearchOption.AllDirectories).Select(f => Path.GetRelativePath(dir, f)).OrderBy(x => x)) : "no-dir";
                    break;
                }
            case "anon":
                try { r = GameManager.Instance.LogicOptions.GetAnonymousVotes() + "/" + GameOptionsManager.Instance.CurrentGameOptions.GetBool(BoolOptionNames.AnonymousVotes); }
                catch (Exception e) { r = "ERR " + e.Message; }
                break;
            default:
                r = "unknown probe";
                break;
        }
        Reply(name, r);
    }

    // ---------------------------------------------------------------- host side helpers
    internal static IEnumerator Ask(string name, string arg = "", float timeout = 10f)
    {
        foreach (var k in Answers.Keys.Where(k => k.EndsWith("/" + name)).ToList()) Answers.Remove(k);
        DuoPlugin.Broadcast($"probe {name} {arg}".TrimEnd());
        int want = 1 + DuoPlugin.ExpectedClients;
        yield return Co.Until(() => Answers.Keys.Count(k => k.EndsWith("/" + name)) >= want, timeout);
    }

    internal static string Got(string tag, string name) => Answers.TryGetValue(tag + "/" + name, out var v) ? v : "<no answer>";

    internal static void SetAnonymous(bool on)
    {
        var o = GameOptionsManager.Instance.CurrentGameOptions;
        o.SetBool(BoolOptionNames.AnonymousVotes, on);
        GameOptionsManager.Instance.GameHostOptions = o;
        PlayerControl.LocalPlayer.RpcSyncSettings(GameOptionsManager.Instance.gameOptionsFactory.ToBytes(o, false));
        try { GameManager.Instance.LogicOptions.SyncOptions(); } catch (Exception e) { DuoPlugin.Say("SyncOptions: " + e.Message); }
        DuoPlugin.Say($"anonymous votes {on}");
    }
}

internal static partial class DuoHost
{
    static IEnumerator FeatureMeeting(string label, byte hostVote, byte bVote, byte cVote, Func<IEnumerator> during = null)
    {
        DuoPlugin.Broadcast("report B");
        yield return Co.Until(() => MeetingHud.Instance != null, 15f);
        if (!MeetingHud.Instance) { report.Add(label + ":meeting-DID-NOT-OPEN"); yield break; }
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.NotVoted || MeetingHud.Instance.state == MeetingHud.VoteStates.Voted, 20f);
        yield return Co.Wait(2f);
        if (during != null) yield return during();
        if (MeetingHud.Instance) MeetingHud.Instance.CmdCastVote(HostId, hostVote);
        if (bVote != 254) DuoPlugin.Broadcast($"vote B {bVote}");
        if (cVote != 254) DuoPlugin.Broadcast($"vote C {cVote}");
        yield return Co.Until(() => MeetingHud.Instance == null || MeetingHud.Instance.state == MeetingHud.VoteStates.Results, 150f);
        yield return Co.Wait(3f);
        if (MeetingHud.Instance) { DuoClient.Proceed(); DuoPlugin.Broadcast("proceed", false); }
        yield return Co.Until(() => MeetingHud.Instance == null, 30f);
        yield return Co.Until(() => ExileController.Instance == null, 30f);
        yield return Co.Wait(6f);
    }

    static void AllPlainCrew()
    {
        foreach (var p in PlayerControl.AllPlayerControls.ToArray())
            if (p) try { ForceImpostorMod.RoleControl.SetPlain(p.PlayerId, false); } catch (Exception e) { DuoPlugin.Say("plain: " + e.Message); }
    }

    static IEnumerator PlanFeatures()
    {
        var b = ClientPlayer("B"); var c = ClientPlayer("C");
        if (!b || !c) { report.Add("features:needs-2-clients"); yield break; }
        byte bid = b.PlayerId, cid = c.PlayerId, hid = HostId;
        string bn = b.Data.PlayerName, cn = c.Data.PlayerName, hn = PlayerControl.LocalPlayer.Data.PlayerName;

        // ---- lobby: settings search (2nd version: tabs in the game's own menus)
        Mark("features search");
        {
            var ui = DuoFeatures.SearchUi();
            var edit = AccessTools.TypeByName("UsefulTORStuff.SettingsSearchEdit");
            var core = AccessTools.TypeByName("UsefulTORStuff.SettingsSearch");
            if (ui == null || edit == null || core == null) report.Add("search:TYPES-MISSING");
            else
            {
                void Query(string q) => ui.GetType().GetMethod("DiagQuery").Invoke(ui, new object[] { q });
                try { ui.GetType().GetMethod("Toggle").Invoke(ui, null); } catch (Exception e) { report.Add("search:OPEN-FAILED " + e.Message); }
                yield return Co.Wait(2.5f);
                bool vis = (bool)AccessTools.Property(edit, "Visible").GetValue(null);
                report.Add($"search:edit-visible={vis} lock={DuoFeatures.LockEngaged()}");
                Query("sheriff");
                yield return Co.Wait(1f);
                var gom = AccessTools.Field(edit, "Gom").GetValue(null) as GameOptionsMenu;
                report.Add($"search:sheriff-rows={(gom != null ? gom.Children.Count - 1 : -1)}");
                yield return DuoFeatures.Shot("search_edit_sheriff");

                Query("sheriff cooldown");
                yield return Co.Wait(1f);
                var args = new object[] { 0 };
                var groups = AccessTools.Method(core, "Find").Invoke(null, args) as System.Collections.IList;
                TheOtherRoles.CustomOption opt = null;
                if (groups != null && groups.Count > 0)
                {
                    var rows = AccessTools.Field(groups[0].GetType(), "Rows").GetValue(groups[0]) as List<TheOtherRoles.CustomOption>;
                    opt = rows?.FirstOrDefault();
                }
                gom = AccessTools.Field(edit, "Gom").GetValue(null) as GameOptionsMenu;
                var row = gom != null && gom.Children.Count > 1 ? gom.Children[1].TryCast<StringOption>() : null;   // [0] is the field
                if (opt == null || row == null) report.Add($"search:no-row opt={opt?.id} row={(row != null)}");
                else
                {
                    int before = opt.selection;
                    row.PlusBtn.OnClick.Invoke();           // the real button, as a click
                    yield return Co.Wait(3f);
                    yield return DuoFeatures.Ask("opt", opt.id.ToString());
                    string want = opt.selection.ToString();
                    report.Add($"search:plus {opt.id} {before}->{opt.selection} B={DuoFeatures.Got("B", "opt")} C={DuoFeatures.Got("C", "opt")}"
                               + (opt.selection != before && DuoFeatures.Got("B", "opt") == want && DuoFeatures.Got("C", "opt") == want ? "" : "(MISMATCH)"));
                    gom = AccessTools.Field(edit, "Gom").GetValue(null) as GameOptionsMenu;   // rebuilt after the change
                    row = gom != null && gom.Children.Count > 1 ? gom.Children[1].TryCast<StringOption>() : null;
                    string shown = row != null ? row.ValueText.text : "<no row>";
                    report.Add($"search:row-shows-new-value={shown == opt.selections[opt.selection].ToString()} ({shown})");
                    row?.MinusBtn.OnClick.Invoke();
                    yield return Co.Wait(2f);
                    report.Add($"search:restored={opt.selection == before}");
                }
                Query("cooldown");
                yield return Co.Wait(1f);
                yield return DuoFeatures.Shot("search_edit_cooldown");
                Query("");
                ui.GetType().GetMethod("Close").Invoke(ui, null);
                yield return Co.Wait(1f);
                report.Add($"search:input-lock-released={!DuoFeatures.LockEngaged()}");

                // the view pane: host, then the clients
                try { AccessTools.Method(AccessTools.TypeByName("UsefulTORStuff.SettingsSearchView"), "Open").Invoke(null, null); Query("sheriff"); } catch (Exception e) { report.Add("search:VIEW-FAILED " + e.Message); }
                yield return Co.Wait(2f);
                report.Add("search:host-view " + DuoFeatures.SearchViewState());
                yield return DuoFeatures.Shot("search_view_host_sheriff");
                Query("");
                ui.GetType().GetMethod("Close").Invoke(ui, null);
                yield return Co.Wait(1f);
                yield return DuoFeatures.Ask("searchview", "sheriff", 15f);
                report.Add("search:B-view " + DuoFeatures.Got("B", "searchview") + " | C " + DuoFeatures.Got("C", "searchview"));
            }
        }

        // ---- lobby: error toast everywhere
        Mark("features toast");
        yield return DuoFeatures.Ask("toast", "", 15f);
        report.Add($"toast:A[{DuoFeatures.Got("A", "toast")}] B[{DuoFeatures.Got("B", "toast")}] C[{DuoFeatures.Got("C", "toast")}]");
        yield return DuoFeatures.Ask("hosttools");
        string htBefore = DuoFeatures.Got("A", "hosttools");

        // ---- round 1: anonymous off, vote history with names; maniac defuse + bug crash
        DuoFeatures.SetAnonymous(false);
        yield return Co.Wait(2f);
        yield return NextRound("f1-votes-named");
        AllPlainCrew();
        yield return Co.Wait(3f);
        Mark("features meeting 1");
        yield return FeatureMeeting("f1m1", bid, cid, 253);
        yield return DuoFeatures.Ask("vh");
        foreach (var x in new[] { "A", "B", "C" }) report.Add($"vh-named:{x}[{DuoFeatures.Got(x, "vh")}]");
        bool named = new[] { "A", "B", "C" }.All(x => DuoFeatures.Got(x, "vh").Contains(hn) && DuoFeatures.Got(x, "vh").Contains(bn));
        report.Add($"vh-named:{(named ? "ok" : "MISSING-NAMES")}");

        Mark("features meeting 2 (defuse + crash)");
        string evDefuse = "", evCrash = "";
        yield return FeatureMeeting("f1m2", 253, 253, 254, () => Events());
        IEnumerator Events()
        {
            try { evDefuse = AccessTools.TypeByName("UnknownsCollection.UCEvents").GetMethod("ManiacDefuse").Invoke(null, new object[] { cid }) as string; } catch (Exception e) { evDefuse = "ERR " + e.Message; }
            try { evCrash = AccessTools.TypeByName("UnknownsCollection.UCEvents").GetMethod("BugCrashNow").Invoke(null, null) as string; } catch (Exception e) { evCrash = "ERR " + e.Message; }
            DuoPlugin.Say($"events: {evDefuse} / {evCrash}");
            yield return Co.Wait(6f);
            yield return DuoFeatures.Ask("defuse");
            yield return DuoFeatures.Ask("crash");
            yield return Snap("events");
            report.Add($"defuse:C={DuoFeatures.Got("C", "defuse")} B={DuoFeatures.Got("B", "defuse")}");
            // the defuse has priority: the crash must not show up in this meeting (User 2026-11-13)
            bool crashNow = new[] { "A", "B", "C" }.Any(x => DuoFeatures.Got(x, "crash") == "True");
            report.Add($"crash-postponed:{(!crashNow && (evCrash ?? "").Contains("next meeting") ? "ok" : "FAIL " + evCrash)}");
        }
        report.Add($"defuse:c-dead-after-meeting={DuoCommands.ById(cid)?.Data?.IsDead}");

        Mark("features meeting 3 (the postponed crash)");
        yield return FeatureMeeting("f1m3", 253, 253, 254, () => CrashCheck());
        IEnumerator CrashCheck()
        {
            yield return Co.Wait(12f);   // the crash fires 6-10 s into the meeting
            yield return DuoFeatures.Ask("crash");
            report.Add($"crash-next-meeting:A={DuoFeatures.Got("A", "crash")} B={DuoFeatures.Got("B", "crash")}"
                       + (DuoFeatures.Got("A", "crash") == "True" && DuoFeatures.Got("B", "crash") == "True" ? "" : " (MISSING)"));
        }
        yield return DuoFeatures.Ask("hosttools");
        report.Add($"hosttools:before[{htBefore}] after[{DuoFeatures.Got("A", "hosttools")}]");
        yield return EndRound("f1");

        // ---- lobby: change marks
        // every client back in the lobby with its player object first: an option sent while a client still sits on
        // the end screen does not reach it (known driver pitfall)
        yield return Co.Until(() => LobbyBehaviour.Instance != null && PlayerControl.AllPlayerControls.Count >= 1 + DuoPlugin.ExpectedClients, 90f);
        yield return Co.Wait(12f);

        // ---- lobby: Host Tools statistic kept round f1 (one line per player, newest round)
        Mark("features host stats");
        {
            string file = Path.Combine(BepInEx.Paths.ConfigPath, "HostTools", "stats.tsv");
            string res;
            try
            {
                var lines = File.Exists(file) ? File.ReadAllLines(file) : new string[0];
                var newest = lines.Select(l => l.Split('\t')).Where(f => f.Length >= 18).GroupBy(f => f[1]).OrderByDescending(g => g.Key).FirstOrDefault();
                long age = newest == null ? -1 : DateTimeOffset.UtcNow.ToUnixTimeSeconds() - long.Parse(newest.Key);
                res = newest == null ? "NO-FILE-OR-ROWS"
                    : $"rows={newest.Count()} map={newest.First()[4]} len={newest.First()[2]} early={newest.Count(f => f[13] == "0" && f[12] != "" && f[12] != f[6] && f[11] != "-1")} "
                      + $"first={newest.Where(f => f[17] == "1").Select(f => f[7]).FirstOrDefault() ?? "-"} age={age}s"
                      + (newest.Count() == 1 + DuoPlugin.ExpectedClients && age < 600 ? "" : "(MISMATCH)");
            }
            catch (Exception e) { res = "ERR " + e.Message; }
            report.Add("hoststats:" + res);
            try
            {
                var ht = AccessTools.TypeByName("HostFixPlugin.HostToolsUI");
                var inst = AccessTools.Property(ht, "Instance").GetValue(null);
                AccessTools.Method(ht, "DiagStats").Invoke(inst, new object[] { false });
            }
            catch (Exception e) { report.Add("hoststats:UI-FAILED " + e.Message); }
            yield return Co.Wait(1.5f);
            yield return DuoFeatures.Shot("hoststats_tab");
            try { var ht = AccessTools.TypeByName("HostFixPlugin.HostToolsUI"); AccessTools.Method(ht, "Close").Invoke(AccessTools.Property(ht, "Instance").GetValue(null), null); } catch { }
            yield return Co.Wait(1f);
        }

        Mark("features change marks");
        var vhOpt = TheOtherRoles.CustomOption.options.FirstOrDefault(o => o.id == 1352);
        if (vhOpt != null)
        {
            int keep = vhOpt.selection;
            vhOpt.updateSelection(keep == 0 ? 1 : 0);
            // the menu is closed: updateSelection does not send it then (TOR shares only with the menu open)
            TheOtherRoles.CustomOption.ShareOptionSelections();
            yield return Co.Wait(3f);
            yield return DuoFeatures.Ask("marks");
            report.Add($"marks:changed A={DuoFeatures.Got("A", "marks")} B={DuoFeatures.Got("B", "marks")} C={DuoFeatures.Got("C", "marks")}");
            vhOpt.updateSelection(keep);
            TheOtherRoles.CustomOption.ShareOptionSelections();
            yield return Co.Wait(3f);
            yield return DuoFeatures.Ask("marks");
            report.Add($"marks:restored A={DuoFeatures.Got("A", "marks")} B={DuoFeatures.Got("B", "marks")} C={DuoFeatures.Got("C", "marks")}");
        }
        else report.Add("marks:option-1352-missing");

        // ---- round 2: anonymous on, counts only
        DuoFeatures.SetAnonymous(true);
        yield return Co.Wait(2f);
        yield return NextRound("f2-votes-anonymous");
        AllPlainCrew();
        yield return Co.Wait(3f);
        b = ClientPlayer("B"); c = ClientPlayer("C");
        Mark("features meeting anonymous");
        yield return FeatureMeeting("f2m1", b.PlayerId, hid, b.PlayerId, () => AnonProbe());
        IEnumerator AnonProbe()
        {
            yield return DuoFeatures.Ask("anon");
            report.Add($"anon-in-meeting:A={DuoFeatures.Got("A", "anon")} B={DuoFeatures.Got("B", "anon")} C={DuoFeatures.Got("C", "anon")}");
        }
        yield return DuoFeatures.Ask("vh");
        foreach (var x in new[] { "A", "B", "C" }) report.Add($"vh-anon:{x}[{DuoFeatures.Got(x, "vh")}]");
        bool leak = new[] { "A", "B", "C" }.Any(x => DuoFeatures.Got(x, "vh").Contains(": " + hn) || DuoFeatures.Got(x, "vh").Contains(": " + cn));
        report.Add($"vh-anon:{(leak ? "LEAKS-NAMES" : "ok")}");
        DuoFeatures.SetAnonymous(false);
        yield return EndRound("f2");
    }
}
