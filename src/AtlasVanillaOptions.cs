// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasVanillaOptions - Host-Einstellungen der Krisen auf den Vanilla-Karten (AtlasVanillaCrisis).
//
// Atlas bleibt ohne The Other Roles ladbar (deshalb bisher nur BepInEx-Config). Diese Einstellungen muessen aber fuer
// alle gleich sein: wer die Krise nicht kennt, kann sie nicht beheben. Wie bei Nightfall (NightfallOptions) werden sie
// deshalb per Reflection als TOR-CustomOptions angemeldet, wenn TOR da ist; TOR teilt die Auswahl des Hosts dann von
// selbst. Ohne TOR gilt der lokale Config-Wert (Freeplay, Tests).
//
// IDs aus dem Atlas-Block 1720-1739 (ID-Registry): 1720 Ueberschrift, 1721-1727 je Krise. Die Optionen wandern ans
// Ende von TORs Liste (siehe NightfallOptions.MoveToEndOfOptionList: ein Client ohne Atlas bricht sonst beim Empfang
// der Host-Auswahl an der ersten unbekannten ID ab und verliert alle folgenden Optionen).
// Auswahl je Krise: "Extra" (zusaetzlich zur Vanilla-Sabotage), "Replaces <x>" (die Vanilla-Sabotage verschwindet von
// der Sabotage-Karte und laesst sich nicht mehr ausloesen), "Off". Standard ist der erste Eintrag (TOR-Verhalten).

using System;
using System.Collections.Generic;
using System.Reflection;
using BepInEx.Configuration;
using HarmonyLib;

namespace UnknownsAtlas;

internal static class AtlasVanillaOptions
{
    private const string LogPrefix = "[Atlas/VanillaOptions]";
    public const int HeaderId = 1720;
    public enum Mode { Extra = 0, Replace = 1, Off = 2 }

    private static ConfigEntry<bool> _localOn;
    private static readonly Dictionary<byte, ConfigEntry<Mode>> Local = new();
    private static object _header;
    private static readonly Dictionary<byte, object> Opts = new();
    private static FieldInfo _fSel;
    private static bool _tried;
    private static int _attempts;

    public static void Bind(ConfigFile cfg)
    {
        _localOn = cfg.Bind("VanillaCrises", "Enabled", false,
            "Extra sabotages on the vanilla maps (Skeld, Polus, Airship). With The Other Roles installed this is a HOST "
            + "setting in the TOR settings (General tab, 'Atlas: Extra Sabotages'); this entry is only the fallback.");
        foreach (var d in AtlasVanillaCrisis.Defs)
            Local[d.Id] = cfg.Bind("VanillaCrises", d.Key, Mode.Extra, $"{d.Title} on {d.MapName}: Extra, Replace ({d.ReplacesLabel}) or Off.");
    }

    public static bool On
    {
        get
        {
            int h = Sel(_header);
            return h >= 0 ? h == 1 : _localOn?.Value ?? false;
        }
    }

    public static Mode ModeOf(byte id)
    {
        int s = Opts.TryGetValue(id, out var o) ? Sel(o) : -1;
        if (s >= 0 && s <= 2) return (Mode)s;
        return Local.TryGetValue(id, out var e) ? e.Value : Mode.Off;
    }

    private static int Sel(object option)
    {
        try { if (option != null && _fSel != null) return (int)_fSel.GetValue(option); } catch { }
        return -1;
    }

    // ------------------------------------------------------------------ Anmeldung (wie NightfallOptions)

    public static void TryRegister()
    {
        if (_tried) return;
        if (++_attempts > 120) { _tried = true; return; }
        Type co = null;
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            try { co = asm.GetType("TheOtherRoles.CustomOption", false); if (co != null) break; } catch { }
        }
        if (co == null) return;
        _tried = true;
        try
        {
            var enumType = co.GetNestedType("CustomOptionType") ?? throw new MissingMemberException("CustomOptionType");
            MethodInfo create = null;
            foreach (var m in co.GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                if (m.Name != "Create") continue;
                var p = m.GetParameters();
                if (p.Length >= 4 && p[3].ParameterType == typeof(string[])) { create = m; break; }
            }
            if (create == null) throw new MissingMethodException("CustomOption.Create(string[])");
            _fSel = co.GetField("selection", BindingFlags.Public | BindingFlags.Instance) ?? throw new MissingMemberException("selection");
            object general = Enum.Parse(enumType, "General");

            object Make(int id, string name, string[] labels, object parent, bool header)
            {
                var ps = create.GetParameters();
                var args = new object[ps.Length];
                args[0] = id; args[1] = general; args[2] = name; args[3] = labels;
                for (int i = 4; i < ps.Length; i++)
                {
                    args[i] = ps[i].HasDefaultValue ? ps[i].DefaultValue
                        : ps[i].ParameterType.IsValueType ? Activator.CreateInstance(ps[i].ParameterType) : null;
                    if (ps[i].Name == "parent") args[i] = parent;
                    if (ps[i].Name == "isHeader") args[i] = header;
                }
                return create.Invoke(null, args);
            }

            _header = Make(HeaderId, "Atlas: Extra Sabotages On Vanilla Maps", new[] { "Off", "On" }, null, true);
            foreach (var d in AtlasVanillaCrisis.Defs)
                Opts[d.Id] = Make(HeaderId + d.Id, $"{d.Title} ({d.MapName})", new[] { "Extra", "Replaces " + d.ReplacesLabel, "Off" }, _header, false);
            MoveToEnd(co);
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} registered as TOR options {HeaderId}-{HeaderId + Opts.Count} (host-synchronised)");
        }
        catch (Exception e)
        {
            _header = null; Opts.Clear();
            AtlasPlugin.Logger.LogWarning($"{LogPrefix} could not register with The Other Roles ({e.Message}); using the local config, NOT shared with the lobby");
        }
    }

    private static void MoveToEnd(Type co)
    {
        try
        {
            if (co.GetField("options", BindingFlags.Public | BindingFlags.Static)?.GetValue(null) is not System.Collections.IList list) return;
            var mine = new List<object> { _header };
            foreach (var d in AtlasVanillaCrisis.Defs) if (Opts.TryGetValue(d.Id, out var o)) mine.Add(o);
            foreach (var o in mine) { int i = list.IndexOf(o); if (i >= 0) list.RemoveAt(i); }
            foreach (var o in mine) list.Add(o);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} could not move the options to the end of TOR's list: {e.Message}"); }
    }

    [HarmonyPatch(typeof(MainMenuManager), nameof(MainMenuManager.Start))]
    internal static class RegisterPatch
    {
        public static void Postfix() { try { TryRegister(); } catch { } }
    }
}
