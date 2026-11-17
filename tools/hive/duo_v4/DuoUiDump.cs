// Plan "uidump" (2026-11-13): where are the game's menu graphics? Host only, in the lobby:
//   the lobby info pane, the view pane (VIEW) and the edit menu (EDIT) are written out as a tree
//   (path, active, sprite name / size / border / draw mode / colour, TMP font / size / colour) into
//   <game>/duo_shots/ui_*.tsv, every sprite met there as PNG into duo_shots/sprites, plus a screenshot each.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

namespace DuoTest;

internal static class DuoUiDump
{
    static readonly HashSet<string> saved = new();
    static string Dir => Path.Combine(DuoPlugin.Root, "duo_shots");

    internal static IEnumerator Plan(List<string> report)
    {
        Directory.CreateDirectory(Path.Combine(Dir, "sprites"));
        var info = LobbyInfoPane.Instance;
        if (info == null) { report.Add("uidump:NO-LOBBYINFO"); yield break; }
        Dump(info.transform, "ui_lobbyinfo.tsv");
        yield return DuoFeatures.Shot("ui_lobby");

        try { info.HostViewButton?.TryCast<PassiveButton>()?.OnClick?.Invoke(); } catch (Exception e) { report.Add("uidump:view " + e.Message); }
        yield return Co.Wait(2.5f);
        var pane = info.LobbyViewSettingsPane;
        if (pane != null)
        {
            Dump(pane.transform, "ui_viewpane.tsv");
            // the prefabs the pane draws its rows from
            if (pane.infoPanelOrigin != null) Dump(pane.infoPanelOrigin.transform, "ui_infopanel_prefab.tsv");
            if (pane.categoryHeaderOrigin != null) Dump(pane.categoryHeaderOrigin.transform, "ui_header_prefab.tsv");
        }
        yield return DuoFeatures.Shot("ui_viewpane");
        try { pane?.backButton?.OnClick?.Invoke(); } catch { }
        yield return Co.Wait(1.5f);

        try { info.EditButton?.TryCast<PassiveButton>()?.OnClick?.Invoke(); } catch (Exception e) { report.Add("uidump:edit " + e.Message); }
        yield return Co.Wait(3f);
        var menu = UnityEngine.Object.FindObjectOfType<GameSettingMenu>();
        if (menu != null)
        {
            Dump(menu.transform, "ui_editmenu.tsv");
            var gom = menu.GameSettingsTab;
            if (gom != null)
            {
                if (gom.stringOptionOrigin != null) Dump(gom.stringOptionOrigin.transform, "ui_stringoption_prefab.tsv");
                if (gom.numberOptionOrigin != null) Dump(gom.numberOptionOrigin.transform, "ui_numberoption_prefab.tsv");
                if (gom.checkboxOrigin != null) Dump(gom.checkboxOrigin.transform, "ui_checkbox_prefab.tsv");
            }
        }
        else report.Add("uidump:NO-EDITMENU");
        yield return DuoFeatures.Shot("ui_editmenu");
        try { menu?.Close(); } catch { }
        yield return Co.Wait(1f);
        report.Add($"uidump:ok sprites={saved.Count}");

        // Host Tools in the game look: statistics with sample rounds (memory only), then the start check tab
        var ht = HarmonyLib.AccessTools.TypeByName("HostFixPlugin.HostToolsUI");
        object inst = null;
        try { inst = HarmonyLib.AccessTools.Property(ht, "Instance").GetValue(null); HarmonyLib.AccessTools.Method(ht, "DiagStats").Invoke(inst, new object[] { true }); }
        catch (Exception e) { report.Add("uidump:hosttools " + e.Message); }
        yield return Co.Wait(2f);
        yield return DuoFeatures.Shot("hosttools_stats_game");

        // ModalGuard: the guard is on while Host Tools is open, off once it is closed, and its prefixes sit on the
        // game's button methods (a direct ReceiveClickUp call does not fire a button like a real click, 13.11.)
        var reg = HarmonyLib.AccessTools.TypeByName("UsefulTORStuff.ModalRegistry");
        bool Blocked() { try { return (bool)HarmonyLib.AccessTools.Method(reg, "ClicksBlocked").Invoke(null, null); } catch { return false; } }
        bool underHt = Blocked(), moveFrozen = false;
        try { moveFrozen = PlayerControl.LocalPlayer != null && !PlayerControl.LocalPlayer.moveable; } catch { }
        try { HarmonyLib.AccessTools.Method(ht, "Close").Invoke(inst, null); } catch { }
        yield return Co.Wait(0.8f);
        bool afterClose = Blocked(), moveBack = false;
        try { moveBack = PlayerControl.LocalPlayer != null && PlayerControl.LocalPlayer.moveable; } catch { }
        string owners = "";
        try
        {
            var pinfo = HarmonyLib.Harmony.GetPatchInfo(HarmonyLib.AccessTools.Method(typeof(PassiveButton), "ReceiveClickUp"));
            owners = pinfo == null ? "none" : string.Join(",", pinfo.Prefixes.Select(p => p.owner).Distinct());
        }
        catch (Exception e) { owners = "ERR " + e.Message; }
        report.Add($"modal:blocked-with-hosttools={underHt} frozen={moveFrozen} blocked-after-close={afterClose} moveable-again={moveBack} clickup-prefixes=[{owners}]"
                   + (underHt && !afterClose && moveFrozen && moveBack ? "" : "(MISMATCH)"));
        try { HarmonyLib.AccessTools.Method(ht, "DiagStats").Invoke(inst, new object[] { false }); } catch { }
        yield return Co.Wait(1f);
        string[] tabs = { "check", "log", "plan", "players" };
        for (int i = 0; i < tabs.Length; i++)
        {
            try { HarmonyLib.AccessTools.Method(ht, "DiagTab").Invoke(inst, new object[] { i }); } catch (Exception e) { report.Add("uidump:tab " + e.Message); }
            yield return Co.Wait(1.2f);
            yield return DuoFeatures.Shot("hosttools_" + tabs[i]);
        }
        try { HarmonyLib.AccessTools.Method(ht, "Close").Invoke(inst, null); } catch { }
        yield return Co.Wait(0.5f);

        // every Forgotten Fixes panel (UIGallery's tour), now in a real lobby with the game's sprites loaded
        if (System.IO.File.Exists(System.IO.Path.Combine(DuoPlugin.Root, "duo_tour_on")))
        {
            IEnumerator tour = null;
            try { tour = HarmonyLib.AccessTools.Method(HarmonyLib.AccessTools.TypeByName("UsefulTORStuff.UIGallery"), "Tour").Invoke(null, null) as IEnumerator; }
            catch (Exception e) { report.Add("uidump:tour " + e.Message); }
            if (tour != null) yield return tour;
            report.Add("uidump:tour done");


        }
    }

    static void Dump(Transform root, string file)
    {
        var sb = new StringBuilder("path\tactive\tpos\tscale\tkind\tdetail\n");
        Walk(root, root.name, sb);
        File.WriteAllText(Path.Combine(Dir, file), sb.ToString());
    }

    static string V(Vector3 v) => string.Format(CultureInfo.InvariantCulture, "{0:0.###},{1:0.###},{2:0.###}", v.x, v.y, v.z);
    static string C(Color c) => "#" + ColorUtility.ToHtmlStringRGBA(c);

    static void Walk(Transform t, string path, StringBuilder sb)
    {
        string head = $"{path}\t{(t.gameObject.activeSelf ? 1 : 0)}\t{V(t.localPosition)}\t{V(t.localScale)}";
        bool any = false;
        foreach (var sr in t.GetComponents<SpriteRenderer>())
        {
            any = true;
            var s = sr.sprite;
            string sd = s == null ? "<none>" : string.Format(CultureInfo.InvariantCulture,
                "{0} rect={1}x{2} ppu={3} border={4} mode={5} size={6} color={7} mat={8} order={9}",
                s.name, s.rect.width, s.rect.height, s.pixelsPerUnit, s.border, sr.drawMode, sr.size, C(sr.color),
                sr.sharedMaterial != null ? sr.sharedMaterial.name : "-", sr.sortingOrder);
            sb.Append(head).Append("\tSprite\t").Append(sd).Append('\n');
            Save(s);
        }
        foreach (var tmp in t.GetComponents<TMPro.TextMeshPro>())
        {
            any = true;
            string txt = (tmp.text ?? "").Replace('\n', ' ').Replace('\t', ' ');
            if (txt.Length > 50) txt = txt.Substring(0, 50);
            sb.Append(head).Append("\tTMP\t").Append(string.Format(CultureInfo.InvariantCulture,
                "font={0} size={1} auto={2} color={3} outline={4}/{5} style={6} align={7} text=\"{8}\"",
                tmp.font != null ? tmp.font.name : "-", tmp.fontSize, tmp.enableAutoSizing, C(tmp.color), C(tmp.outlineColor),
                tmp.outlineWidth, tmp.fontStyle, tmp.alignment, txt)).Append('\n');
        }
        var comps = string.Join(",", t.GetComponents<Component>().Select(c => c.GetIl2CppType().Name).Where(n => n != "Transform" && n != "SpriteRenderer" && n != "TextMeshPro"));
        if (!any || comps.Length > 0) sb.Append(head).Append("\tGO\t").Append(comps).Append('\n');
        for (int i = 0; i < t.childCount; i++) { var c = t.GetChild(i); Walk(c, path + "/" + c.name, sb); }
    }

    // a sprite as PNG: the texture is GPU-only, so it goes through a render texture
    static void Save(Sprite s)
    {
        if (s == null || saved.Contains(s.name) || saved.Count > 120) return;
        saved.Add(s.name);
        try
        {
            var tex = s.texture;
            var rt = RenderTexture.GetTemporary(tex.width, tex.height, 0, RenderTextureFormat.ARGB32);
            Graphics.Blit(tex, rt);
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var r = s.textureRect;
            var outTex = new Texture2D((int)r.width, (int)r.height, TextureFormat.RGBA32, false);
            outTex.ReadPixels(new Rect(r.x, r.y, r.width, r.height), 0, 0);
            outTex.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            string name = string.Join("_", s.name.Split(Path.GetInvalidFileNameChars()));
            File.WriteAllBytes(Path.Combine(Dir, "sprites", name + ".png"), ImageConversion.EncodeToPNG(outTex));
            UnityEngine.Object.Destroy(outTex);
        }
        catch (Exception e) { DuoPlugin.Say($"sprite {s.name}: {e.Message}"); }
    }
}
