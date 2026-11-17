// Snapshot: the comparable state of this client, written as TSV lines (label, key, value).
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using TheOtherRoles;
using TheOtherRoles.Objects;
using UnityEngine;

namespace DuoTest;

internal static class DuoSnap
{
    static readonly string[] Asms = {
        "TheOtherRoles", "UnknownsCollection", "UsefulTORStuff",
        "TOR-ChanceModifier", "UnknownsAtlas", "HostFixPlugin", "Nightfall", "TOR-Bypass"
    };
    static List<(string key, FieldInfo f)> fields;
    static string SnapFile => Path.Combine(DuoPlugin.Root, "duo_snap.tsv");

    static bool Supported(Type t)
    {
        if (t.IsPrimitive || t.IsEnum || t == typeof(string)) return true;
        if (t == typeof(PlayerControl) || t == typeof(NetworkedPlayerInfo) || t == typeof(Vector2) || t == typeof(Vector3)) return true;
        if (t.IsGenericType)
        {
            var d = t.GetGenericTypeDefinition();
            var a = t.GetGenericArguments();
            bool Elem(Type e) => e.IsPrimitive || e.IsEnum || e == typeof(string) || e == typeof(PlayerControl);
            if ((d == typeof(List<>) || d == typeof(HashSet<>)) && Elem(a[0])) return true;
            if (d == typeof(Dictionary<,>) && Elem(a[0])) return true;
        }
        return false;
    }

    static void Index()
    {
        fields = new();
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            var n = asm.GetName().Name;
            if (!Asms.Contains(n)) continue;
            Type[] types;
            try { types = asm.GetTypes(); } catch (ReflectionTypeLoadException e) { types = e.Types.Where(x => x != null).ToArray(); }
            foreach (var t in types)
            {
                if (t.IsGenericTypeDefinition || t.IsInterface || t.Name.Contains('<')) continue;
                FieldInfo[] fs;
                try { fs = t.GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly); } catch { continue; }
                foreach (var f in fs)
                {
                    if (f.IsLiteral || f.Name.Contains('<')) continue;
                    if (!Supported(f.FieldType)) continue;
                    fields.Add(($"{n}:{t.FullName}.{f.Name}", f));
                }
            }
        }
        DuoPlugin.Say($"snapshot index: {fields.Count} static fields");
    }

    static string Fmt(object v)
    {
        if (v == null) return "null";
        switch (v)
        {
            case PlayerControl p: try { return p == null ? "pc:destroyed" : "pc:" + p.PlayerId; } catch { return "pc:err"; }
            case NetworkedPlayerInfo d: try { return d == null ? "npi:destroyed" : "npi:" + d.PlayerId; } catch { return "npi:err"; }
            case float fl: return float.IsNaN(fl) ? "NaN" : fl.ToString("0.0", CultureInfo.InvariantCulture);
            case double db: return db.ToString("0.0", CultureInfo.InvariantCulture);
            case Vector2 v2: return $"v({v2.x:0.0},{v2.y:0.0})";
            case Vector3 v3: return $"v({v3.x:0.0},{v3.y:0.0})";
            case string s: s = s.Replace('\t', ' ').Replace('\n', '|').Replace('\r', ' '); return s.Length > 120 ? s.Substring(0, 120) + "…" : s;
            case IDictionary dict:
                {
                    var keys = new List<string>();
                    foreach (DictionaryEntry e in dict) keys.Add(Fmt(e.Key) + "=" + (IsSimple(e.Value) ? Fmt(e.Value) : "*"));
                    keys.Sort(StringComparer.Ordinal);
                    return "{" + string.Join(",", keys.Take(40)) + (keys.Count > 40 ? ",…" + keys.Count : "") + "}";
                }
            case IEnumerable en:
                {
                    var items = new List<string>();
                    foreach (var o in en) items.Add(Fmt(o));
                    items.Sort(StringComparer.Ordinal);
                    return "[" + string.Join(",", items.Take(40)) + (items.Count > 40 ? ",…" + items.Count : "") + "]";
                }
        }
        return Convert.ToString(v, CultureInfo.InvariantCulture);
    }

    static bool IsSimple(object o) => o == null || o is string || o is PlayerControl || o.GetType().IsPrimitive || o.GetType().IsEnum || o is Vector2 || o is Vector3;

    internal static void Write(string label)
    {
        var sb = new StringBuilder();
        void Add(string k, string v) => sb.Append(label).Append('\t').Append(k).Append('\t').Append(v).Append('\n');
        try
        {
            if (fields == null) Index();
            var ac = AmongUsClient.Instance;
            Add("game.state", ac ? ac.GameState.ToString() : "null");
            Add("game.local", PlayerControl.LocalPlayer ? PlayerControl.LocalPlayer.PlayerId.ToString() : "null");
            Add("game.ship", ShipStatus.Instance ? ShipStatus.Instance.GetType().Name + "/" + ShipStatus.Instance.name : "none");
            Add("game.meeting", MeetingHud.Instance ? MeetingHud.Instance.state.ToString() : "none");
            try { Add("local.canmove", PlayerControl.LocalPlayer ? PlayerControl.LocalPlayer.CanMove.ToString() : "null"); } catch { }
            try { Add("game.proceed", MeetingHud.Instance && MeetingHud.Instance.ProceedButton ? MeetingHud.Instance.ProceedButton.gameObject.activeInHierarchy.ToString() : "none"); } catch { }
            try { Add("local.minigame", Minigame.Instance ? Minigame.Instance.GetType().Name : "none"); } catch { }
            try { Add("game.bodies", UnityEngine.Object.FindObjectsOfType<DeadBody>().Count.ToString()); } catch { }
            foreach (var p in PlayerControl.AllPlayerControls.ToArray())
            {
                if (!p) continue;
                var id = p.PlayerId;
                var d = p.Data;
                Add($"p{id}.name", d != null ? d.PlayerName : "nodata");
                Add($"p{id}.dead", d != null ? d.IsDead.ToString() : "?");
                Add($"p{id}.disc", d != null ? d.Disconnected.ToString() : "?");
                Add($"p{id}.vrole", d?.Role != null ? d.Role.Role.ToString() : "null");
                Add($"p{id}.color", d != null ? d.DefaultOutfit.ColorId.ToString() : "?");
                Add($"p{id}.hat", d != null ? d.DefaultOutfit.HatId : "?");
                try { Add($"p{id}.roles", string.Join("+", RoleInfo.getRoleInfoForPlayer(p, true).Select(r => r.name))); } catch (Exception e) { Add($"p{id}.roles", "ERR " + e.GetType().Name); }
                try { Add($"p{id}.tasks", d?.Tasks == null ? "null" : $"{d.Tasks.ToArray().Count(t => t.Complete)}/{d.Tasks.Count}"); } catch { }
                try { Add($"p{id}.pos", Fmt((Vector2)p.transform.position)); } catch { }
                try { Add($"p{id}.visible", p.Visible.ToString()); } catch { }
                try { Add($"p{id}.cur", d != null ? $"{p.CurrentOutfit.ColorId}/{p.CurrentOutfit.HatId}/{p.CurrentOutfitType}" : "?"); } catch { }
            }
            foreach (var o in CustomOption.options) Add("opt." + o.id, o.selection.ToString());
            int i = 0;
            foreach (var b in CustomButton.buttons)
            {
                try
                {
                    if (b?.actionButton == null) continue;
                    bool has = false; try { has = b.HasButton(); } catch { }
                    if (has) Add($"btn.{i++}", $"{b.buttonText}|{b.Sprite?.name}");
                }
                catch { }
            }
            foreach (var (key, f) in fields)
            {
                string v;
                try { v = Fmt(f.GetValue(null)); } catch (Exception e) { v = "ERR " + (e.InnerException ?? e).GetType().Name; }
                Add("s." + key, v);
            }
        }
        catch (Exception e) { Add("snap.error", e.ToString().Replace('\n', '|')); }
        File.AppendAllText(SnapFile, sb.ToString());
    }
}
