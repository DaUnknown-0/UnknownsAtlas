// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasCinematic - gerenderter Vorspann einer Karte (Bildfolge mit Stimme, Geraeuschen und Untertiteln) vor dem
// Rollen-Intro. Eingebaut fuer die Zugkarte (Polaris Express); andere Mods melden ihre Karte ueber RegisterIntro an.
//
// Wann (User 24.10.): beim ersten Start dieser Karte durch den Host an diesem Abend (solange sein Spiel laeuft),
// fuer ALLE gleichzeitig; der Host kann ihn fuer alle ueberspringen. Host-Option 1728 "Atlas: Map Intro"
// (Once Per Evening / Every Round / Off, ohne TOR die Config [Cinematics] IntroMode).
//
// Ablauf:
//   - Host, BeginGame: Karte hat einen Vorspann, das Paket liegt bei ihm vor, Option erlaubt -> Op 21 Sub 0
//     [play][key][Dauer in Zehntelsekunden] an alle. Ohne Nachricht spielt kein Client den Vorspann.
//   - Jeder Client, IntroCutscene.CoBegin: die Intro-Koroutine wartet, bis der Vorspann fertig ist, dann laeuft das
//     Rollen-Intro unveraendert weiter.
//   - Host: Leertaste/Esc/Enter oder Klick auf den Hinweis -> Op 21 Sub 1 an alle, alle hoeren sofort auf.
//   - Fehlt einem Client das Paket, sieht er fuer dieselbe Dauer eine schwarze Flaeche (die Runde startet fuer alle
//     gleich).
//
// Paket (.cine, Format HWP1): meta.json, f0000.jpg ..., audio_de.pcm, audio_en.pcm
// (16 bit mono, Rate aus meta.json; Stimme und Geraeusche schon gemischt). Untertitel stehen in meta.json und werden
// unten im Bild eingeblendet (Spielsprache Deutsch -> deutsche Stimme und Texte, sonst Englisch). Gespeichert ist
// immer nur EIN Bild (eine Textur, per LoadImage ueberschrieben), jedes Bild wird erst geladen, wenn es dran ist.

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using HarmonyLib;
using TMPro;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

public static class AtlasCinematic
{
    private const string LogPrefix = "[Atlas/Cinematic]";
    internal const byte OpCine = 21;
    private const byte SubPlay = 0, SubSkip = 1;
    public const int OptionId = 1728;

    private static void Log(string s) => AtlasPlugin.Logger.LogInfo($"{LogPrefix} {s}");
    private static void Warn(string s) => AtlasPlugin.Logger.LogWarning($"{LogPrefix} {s}");

    // ------------------------------------------------------------------ Anmeldung

    private static readonly Dictionary<string, Func<Func<string, byte[]>>> Sources = new(StringComparer.Ordinal);

    /// <summary>Vorspann fuer eine Karte anmelden. read(name) liefert einen Eintrag des Pakets (meta.json,
    /// f0000.jpg ..., audio_de.pcm, audio_en.pcm) oder null, solange das Paket fehlt.</summary>
    public static void RegisterIntro(string mapKey, Func<string, byte[]> read)
    {
        if (string.IsNullOrEmpty(mapKey) || read == null) return;
        Sources[mapKey] = () => read;
        Log($"intro registered for map '{mapKey}'");
    }

    /// <summary>Eingebaute Vorspanne aus dem Asset-Ordner von Atlas.</summary>
    internal static void RegisterBuiltIn()
    {
        Sources["train"] = () => PackReader("UnknownsAtlas.Maps.train.train_intro.cine");
    }

    private static Func<string, byte[]> PackReader(string res)
    {
        Dictionary<string, (long Off, int Len)> index = null;
        return name =>
        {
            try
            {
                using var s = AtlasAssetStore.Open(null, res);
                if (s == null) return null;
                index ??= ReadIndex(s);
                if (index == null || !index.TryGetValue(name, out var at)) return null;
                s.Seek(at.Off, SeekOrigin.Begin);
                var data = new byte[at.Len];
                int read = 0;
                while (read < data.Length) { int n = s.Read(data, read, data.Length - read); if (n <= 0) break; read += n; }
                return read == data.Length ? data : null;
            }
            catch { return null; }
        };
    }

    /// <summary>HWP1: 'HWP1', uint32 Anzahl, je Eintrag uint16 Namenslaenge, Name, uint64 Offset, uint32 Laenge.</summary>
    private static Dictionary<string, (long, int)> ReadIndex(Stream s)
    {
        s.Seek(0, SeekOrigin.Begin);
        var br = new BinaryReader(s, Encoding.UTF8, true);
        if (Encoding.ASCII.GetString(br.ReadBytes(4)) != "HWP1") return null;
        int count = br.ReadInt32();
        var map = new Dictionary<string, (long, int)>(count, StringComparer.Ordinal);
        for (int i = 0; i < count; i++)
        {
            int nl = br.ReadUInt16();
            string n = Encoding.UTF8.GetString(br.ReadBytes(nl));
            long off = br.ReadInt64();
            int len = br.ReadInt32();
            map[n] = (off, len);
        }
        return map;
    }

    // ------------------------------------------------------------------ Option (wie AtlasVanillaOptions per Reflection)

    private static ConfigEntry<int> _localMode;
    private static object _option;

    internal static void Bind(ConfigFile cfg)
    {
        _localMode = cfg.Bind("Cinematics", "IntroMode", 0,
            "Map intro before the role reveal: 0 = once per evening, 1 = every round, 2 = off. With The Other Roles "
            + "installed this is a HOST setting ('Atlas: Map Intro' in the General tab); this entry is only the fallback.");
    }

    /// <summary>Aus AtlasVanillaOptions.TryRegister (gleiche Factory), damit beide am Ende von TORs Liste stehen.</summary>
    internal static void SetOption(object option) => _option = option;

    private static int Mode
    {
        get
        {
            try
            {
                if (_option != null)
                {
                    var f = _option.GetType().GetField("selection");
                    if (f != null) return (int)f.GetValue(_option);
                }
            }
            catch { }
            return _localMode?.Value ?? 0;
        }
    }

    // ------------------------------------------------------------------ Host-Entscheidung

    private static readonly HashSet<string> ShownThisEvening = new(StringComparer.Ordinal);   // nur beim Host
    private static string _nextKey;                 // vom Host angesagt: Vorspann dieser Karte vor dem naechsten Intro
    private static float _nextSeconds;
    private static bool _skip;

    [HarmonyPatch(typeof(GameStartManager), nameof(GameStartManager.BeginGame))]
    internal static class BeginGamePatch
    {
        public static void Prefix()
        {
            try
            {
                var ac = AmongUsClient.Instance;
                if (ac == null || !ac.AmHost || PlayerControl.LocalPlayer == null) return;
                string key = AtlasMaps.SelectedKey;
                bool play = false;
                float secs = 0f;
                if (key != null && Sources.TryGetValue(key, out var src))
                {
                    int mode = Mode;
                    var meta = Meta.Load(src());
                    play = meta != null && (mode == 1 || (mode == 0 && !ShownThisEvening.Contains(key)));
                    secs = meta?.Seconds ?? 0f;
                    Log($"host: intro of '{key}' {(play ? "on" : "off")} for this round (mode {mode}, pack {(meta != null ? "ready" : "missing")})");
                }
                _nextKey = play ? key : null;
                _nextSeconds = secs;
                AtlasWorld.Send(OpCine, w =>
                {
                    w.Write(SubPlay);
                    w.Write(play);
                    w.Write(key ?? "");
                    w.Write((ushort)Mathf.Clamp(Mathf.RoundToInt(secs * 10f), 0, 65535));
                });
            }
            catch (Exception e) { Warn($"host decision failed: {e.Message}"); }
        }
    }

    /// <summary>Aus AtlasWorld.PlayerControl_HandleRpc_Postfix (Kanal 237), vor dessen Karten-Pruefung.</summary>
    internal static void Receive(bool fromHost, Hazel.MessageReader reader)
    {
        if (!fromHost) return;
        byte sub = reader.ReadByte();
        if (sub == SubPlay)
        {
            bool play = reader.ReadBoolean();
            string key = reader.ReadString();
            float secs = reader.ReadUInt16() / 10f;
            _nextKey = play && key.Length > 0 ? key : null;
            _nextSeconds = secs;
        }
        else if (sub == SubSkip)
        {
            if (_playing) { _skip = true; Log("host skipped the intro"); }
        }
    }

    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.OnGameJoined))]
    internal static class JoinedPatch
    {
        public static void Postfix() { _nextKey = null; }
    }

    // ------------------------------------------------------------------ Einhaengen vor dem Rollen-Intro

    private static IntroCutscene _intro;
    private static bool _playing;
    private static float _deadline = -1f;

    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.CoBegin))]
    internal static class CoBeginPatch
    {
        public static void Postfix(IntroCutscene __instance, ref Il2CppSystem.Collections.IEnumerator __result)
        {
            try
            {
                _intro = __instance;
                string key = _nextKey;
                _nextKey = null;
                if (key == null || __result == null || AtlasMaps.ActiveKey != key) return;
                if (AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost) ShownThisEvening.Add(key);
                __result = Wrap(__result, key, _nextSeconds).WrapToIl2Cpp();
            }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} wrap failed, plain intro: {e}"); }
        }
    }

    private static IEnumerator Wrap(Il2CppSystem.Collections.IEnumerator original, string key, float seconds)
    {
        if (HudManager.InstanceExists)
        {
            _playing = true;
            HudManager.Instance.StartCoroutine(Guarded(key, seconds).WrapToIl2Cpp());
            while (_playing) yield return null;
        }
        while (original.MoveNext()) yield return original.Current;
    }

    private static IEnumerator Guarded(string key, float seconds)
    {
        var play = Play(key, seconds);
        while (true)
        {
            object step;
            try { if (!play.MoveNext()) break; step = play.Current; }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} playback failed: {e}"); break; }
            yield return step;
        }
        Cleanup();
        _playing = false;
    }

    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.OnDestroy))]
    internal static class IntroDestroyPatch
    {
        public static void Postfix()
        {
            if (_root == null) return;
            Warn("role intro ended early, overlay removed");
            Cleanup();
            _playing = false;
        }
    }

    // Waechter: bricht die Koroutine ab (Intro zerstoert, Fehler), bleibt die schwarze Flaeche sonst liegen.
    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static class WatchdogPatch
    {
        public static void Postfix()
        {
            if (_root == null || _deadline < 0f || Time.time < _deadline) return;
            Warn("intro was cut off, overlay removed by the watchdog");
            Cleanup();
            _playing = false;
        }
    }

    // ------------------------------------------------------------------ Paketdaten

    private sealed class Line
    {
        public string Speaker, SpeakerDe, En, De;
        public float SEn, EEn, SDe, EDe;
    }

    private sealed class Meta
    {
        public float Fps = 24f;
        public int Frames;
        public int AudioRate = 24000;
        public readonly List<Line> Lines = new();
        public float Seconds => Frames / Mathf.Max(1f, Fps);

        public static Meta Load(Func<string, byte[]> read)
        {
            try
            {
                var bytes = read?.Invoke("meta.json");
                if (bytes == null) return null;
                using var doc = JsonDocument.Parse(bytes);
                var r = doc.RootElement;
                var m = new Meta
                {
                    Fps = r.GetProperty("fps").GetSingle(),
                    Frames = r.GetProperty("frames").GetInt32(),
                    AudioRate = r.TryGetProperty("audio_rate", out var ar) ? ar.GetInt32() : 24000,
                };
                if (r.TryGetProperty("subs", out var subs))
                    foreach (var s in subs.EnumerateArray())
                        m.Lines.Add(new Line
                        {
                            Speaker = Str(s, "speaker"), SpeakerDe = Str(s, "speaker_de"), En = Str(s, "en"), De = Str(s, "de"),
                            SEn = s.GetProperty("s_en").GetSingle(), EEn = s.GetProperty("e_en").GetSingle(),
                            SDe = s.GetProperty("s_de").GetSingle(), EDe = s.GetProperty("e_de").GetSingle(),
                        });
                return m.Frames > 0 ? m : null;
            }
            catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} meta.json unreadable: {e.Message}"); return null; }
        }

        private static string Str(JsonElement e, string name) => e.TryGetProperty(name, out var v) ? v.GetString() ?? "" : "";
    }

    private static bool German()
    {
        try { return AmongUs.Data.DataManager.Settings.Language.CurrentLanguage == SupportedLangs.German; }
        catch { return false; }
    }

    // ------------------------------------------------------------------ Abspielen

    private static GameObject _root;
    private static Texture2D _tex;
    private static AudioSource _audio;
    private static AudioClip _clip;
    private static GameObject _camera;
    private static int _layer = 5, _sortLayer, _baseOrder = 32000;

    private static IEnumerator Play(string key, float announcedSeconds)
    {
        _skip = false;
        var read = Sources.TryGetValue(key, out var src) ? src() : null;
        var meta = Meta.Load(read);
        bool de = German();
        bool amHost = AmongUsClient.Instance != null && AmongUsClient.Instance.AmHost;
        byte[] first = meta != null ? read(Frame(0)) : null;
        var cam = Camera.main;
        if (cam == null) yield break;

        // Eigene Kamera, die als letzte zeichnet und den ganzen Bildschirm schwarz loescht: an der UI-Kamera lagen
        // Knoepfe (Use, Report, Rollen- und Mod-Knoepfe) trotz oberster Sortierschicht darueber (Freeplay-Test 24.10.).
        // Kamera und Film liegen weit abseits der Karte, keine andere Kamera sieht sie.
        _layer = 5; _sortLayer = 0; _baseOrder = 0;
        var camGo = new GameObject("Atlas_CinematicCamera");
        camGo.transform.position = new Vector3(5000f, 5000f, -10f);
        var view = camGo.AddComponent<Camera>();
        view.orthographic = true;
        view.orthographicSize = 3f;
        view.nearClipPlane = 0.1f;
        view.farClipPlane = 50f;
        view.clearFlags = CameraClearFlags.SolidColor;
        view.backgroundColor = Color.black;
        view.cullingMask = 1 << _layer;
        view.depth = 1000f;
        _camera = camGo;
        _root = new GameObject("Atlas_Cinematic") { layer = _layer };
        _root.transform.position = new Vector3(5000f, 5000f, 0f);
        HideIntro();

        var black = MakeQuad("black", Color.black, 0);
        SpriteRenderer frame = null;
        if (first != null)
        {
            _tex = new Texture2D(2, 2, TextureFormat.RGB24, false) { hideFlags = HideFlags.HideAndDontSave };
            if (ImageConversion.LoadImage(_tex, first, false))
            {
                _tex.filterMode = FilterMode.Bilinear;
                _tex.wrapMode = TextureWrapMode.Clamp;
                var go = new GameObject("frame") { layer = _layer };
                go.transform.SetParent(_root.transform, false);
                frame = go.AddComponent<SpriteRenderer>();
                frame.sprite = Sprite.Create(_tex, new Rect(0, 0, _tex.width, _tex.height), new Vector2(0.5f, 0.5f), 100f);
                frame.sortingLayerID = _sortLayer;
                frame.sortingOrder = _baseOrder + 1;
            }
        }
        var subBg = MakeQuad("subtitle_bg", new Color(0f, 0f, 0f, 0.55f), 2);
        var noteBg = MakeQuad("note_bg", new Color(0f, 0f, 0f, 0.45f), 2);
        var sub = MakeText("subtitle", 3);
        var note = MakeText("note", 3);
        note.alignment = TextAlignmentOptions.BottomRight;
        if (amHost) note.text = de ? "<b>[Leertaste]</b> Vorspann für alle überspringen" : "<b>[Space]</b> Skip the intro for everyone";
        else if (frame == null) note.text = de ? "Vorspann läuft ..." : "Intro playing ...";

        float total = meta != null ? meta.Seconds : Mathf.Max(1f, announcedSeconds);
        if (frame == null) Warn(meta == null ? $"pack for '{key}' missing here, black screen for {total:F1} s" : "first frame unreadable, black screen");

        // Ton: Stimme + Geraeusche (schon gemischt) in der Spielsprache
        if (meta != null)
        {
            var pcm = read(de ? "audio_de.pcm" : "audio_en.pcm") ?? read(de ? "audio_en.pcm" : "audio_de.pcm");
            if (pcm != null && pcm.Length >= 4)
            {
                try
                {
                    int n = pcm.Length / 2;
                    var f = new float[n];
                    for (int i = 0; i < n; i++) f[i] = (short)(pcm[2 * i] | (pcm[2 * i + 1] << 8)) / 32768f;
                    _clip = AudioClip.Create("atlas_cine_" + key, n, 1, meta.AudioRate, false);
                    _clip.hideFlags |= HideFlags.DontUnloadUnusedAsset;
                    _clip.SetData(f, 0);
                    _audio = SoundManager.Instance.PlaySound(_clip, false, 1f);
                }
                catch (Exception e) { Warn($"audio failed: {e.Message}"); }
            }
        }
        Log($"playing '{key}': {(meta != null ? meta.Frames : 0)} frames, {total:F1} s, {(de ? "de" : "en")}, camera '{view.name}'");

        float t0 = Time.time;
        _deadline = t0 + total + 2f;
        int shown = 0;
        Line current = null;
        while (true)
        {
            float t = Time.time - t0;
            try { if (_audio != null && _audio.isPlaying && Mathf.Abs(_audio.time - t) < 0.5f) t = _audio.time; } catch { }
            float ch = view.orthographicSize * 2f, cw = ch * view.aspect;
            black.transform.localScale = new Vector3(cw * 1.1f, ch * 1.1f, 1f);
            float fit = 1f;
            if (frame != null)
            {
                fit = Mathf.Min(cw / (_tex.width / 100f), ch / (_tex.height / 100f));
                frame.transform.localScale = new Vector3(fit, fit, 1f);
                int want = Mathf.Min(meta.Frames - 1, (int)(t * meta.Fps));
                if (want != shown)
                {
                    var bytes = read(Frame(want));
                    if (bytes != null) ImageConversion.LoadImage(_tex, bytes, false);
                    shown = want;
                }
            }
            // Untertitel im unteren Sechstel des Bildes
            float picH = frame != null ? _tex.height / 100f * fit : ch;
            float picW = frame != null ? _tex.width / 100f * fit : cw;
            sub.rectTransform.sizeDelta = new Vector2(picW * 0.86f, picH / 6f);
            sub.transform.localPosition = new Vector3(0f, -picH / 2f + picH / 12f, -1f);
            sub.fontSize = picH * 0.45f;
            note.rectTransform.sizeDelta = new Vector2(picW * 0.5f, picH * 0.06f);
            note.transform.localPosition = new Vector3(picW / 2f - picW * 0.26f, picH / 2f - picH * 0.04f, -1f);
            note.fontSize = picH * 0.26f;
            FitBackground(subBg, sub, picW * 0.86f, picH * 0.012f);
            FitBackground(noteBg, note, picW * 0.5f, picH * 0.008f);
            Line line = null;
            if (meta != null)
                foreach (var l in meta.Lines)
                    if (de ? (t >= l.SDe && t <= l.EDe) : (t >= l.SEn && t <= l.EEn)) { line = l; break; }
            if (line != current)
            {
                current = line;
                if (line == null) sub.text = "";
                else
                {
                    string who = de ? (line.SpeakerDe.Length > 0 ? line.SpeakerDe : line.Speaker) : line.Speaker;
                    string txt = de ? line.De : line.En;
                    sub.text = (who.Length > 0 ? $"<color=#E8B04A>{who}:</color> " : "") + txt;
                }
            }
            // Host ueberspringt fuer alle
            if (amHost && !_skip && (Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.Return)
                || (Input.GetMouseButtonDown(0) && Clicked(view, note))))
            {
                _skip = true;
                AtlasWorld.Send(OpCine, w => w.Write(SubSkip));
                Log("intro skipped by the host");
            }
            if (_skip) break;
            // die letzten 0,3 s ausblenden
            if (frame != null && t >= total - 0.3f) frame.color = new Color(1f, 1f, 1f, Mathf.Clamp01((total - t) / 0.3f));
            if (t >= total) break;
            yield return null;
        }
        Cleanup();
    }

    private static string Frame(int i) => $"f{i:0000}.jpg";

    /// <summary>Halbtransparente Flaeche genau hinter dem Text (leer: unsichtbar).</summary>
    private static void FitBackground(GameObject bg, TextMeshPro t, float maxW, float pad)
    {
        try
        {
            if (string.IsNullOrEmpty(t.text)) { if (bg.activeSelf) bg.SetActive(false); return; }
            var size = t.GetPreferredValues(t.text, maxW, 0f);
            float w = Mathf.Min(size.x, maxW) + pad * 4f, h = size.y + pad * 2f;
            var p = t.transform.localPosition;
            float x = t.alignment == TextAlignmentOptions.BottomRight ? p.x + t.rectTransform.sizeDelta.x / 2f - w / 2f + pad * 2f : p.x;
            float y = t.alignment == TextAlignmentOptions.BottomRight ? p.y - t.rectTransform.sizeDelta.y / 2f + h / 2f - pad : p.y;
            bg.transform.localPosition = new Vector3(x, y, p.z + 0.5f);
            bg.transform.localScale = new Vector3(w, h, 1f);
            if (!bg.activeSelf) bg.SetActive(true);
        }
        catch { }
    }

    private static bool Clicked(Camera view, TextMeshPro t)
    {
        try
        {
            var b = t.GetComponent<MeshRenderer>().bounds;
            var a = view.WorldToScreenPoint(b.min);
            var c = view.WorldToScreenPoint(b.max);
            var m = Input.mousePosition;
            return m.x >= Mathf.Min(a.x, c.x) - 20 && m.x <= Mathf.Max(a.x, c.x) + 20 && m.y >= Mathf.Min(a.y, c.y) - 20 && m.y <= Mathf.Max(a.y, c.y) + 20;
        }
        catch { return false; }
    }

    private static GameObject MakeQuad(string name, Color c, int order)
    {
        var go = new GameObject(name) { layer = _layer };
        go.transform.SetParent(_root.transform, false);
        var sr = go.AddComponent<SpriteRenderer>();
        var tex = new Texture2D(1, 1) { hideFlags = HideFlags.HideAndDontSave };
        tex.SetPixel(0, 0, Color.white);
        tex.Apply();
        sr.sprite = Sprite.Create(tex, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0.5f), 1f);
        sr.color = c;
        sr.sortingLayerID = _sortLayer;
        sr.sortingOrder = _baseOrder + order;
        return go;
    }

    private static TextMeshPro MakeText(string name, int order)
    {
        var go = new GameObject(name) { layer = _layer };
        go.transform.SetParent(_root.transform, false);
        var t = go.AddComponent<TextMeshPro>();
        try
        {
            var src = HudManager.Instance.GetComponentInChildren<TextMeshPro>(true);
            if (src != null) { t.font = src.font; t.fontSharedMaterial = src.fontSharedMaterial; }
        }
        catch { }
        t.alignment = TextAlignmentOptions.Center;
        t.enableWordWrapping = true;
        t.color = Color.white;
        t.text = "";
        var mr = go.GetComponent<MeshRenderer>();
        if (mr != null) { mr.sortingLayerID = _sortLayer; mr.sortingOrder = _baseOrder + order; }
        return t;
    }

    // Renderer des Rollen-Intros, die waehrend des Vorspanns ausgeblendet sind (seine schwarzen Ebenen lagen sonst
    // trotz niedrigerer Sortierung vor einem Vollbild-Overlay)
    private static readonly List<Renderer> HiddenIntro = new();

    private static void HideIntro()
    {
        HiddenIntro.Clear();
        try
        {
            if (_intro == null) return;
            foreach (var r in _intro.GetComponentsInChildren<Renderer>(true))
            {
                if (r == null || !r.enabled) continue;
                r.enabled = false;
                HiddenIntro.Add(r);
            }
        }
        catch (Exception e) { Warn($"hiding the role intro failed: {e.Message}"); }
    }

    private static void Cleanup()
    {
        foreach (var r in HiddenIntro) { try { if (r != null) r.enabled = true; } catch { } }
        HiddenIntro.Clear();
        try { if (_audio != null) _audio.Stop(); } catch { }
        try { if (_root != null) Object.Destroy(_root); } catch { }
        try { if (_tex != null) Object.Destroy(_tex); } catch { }
        try { if (_camera != null) Object.Destroy(_camera); } catch { }
        _camera = null;
        try { if (_clip != null) Object.Destroy(_clip); } catch { }
        _root = null; _tex = null; _audio = null; _clip = null;
        _deadline = -1f;
    }

    // ------------------------------------------------------------------ Diagnose (Freeplay)

    // ATLAS_CINE_DIAG=<key>[,skip]: spielt den Vorspann 2 s nach dem Kartenbau ohne Host-Entscheidung, fotografiert
    // ihn (AtlasShots/cine_<t>.png) und beendet das Spiel danach ("skip": nach 3 s ueberspringen).
    private static readonly string DiagMode = Environment.GetEnvironmentVariable("ATLAS_CINE_DIAG") ?? "";
    private static float _diagAt = -1f;
    private static bool _diagDone;

    [HarmonyPatch(typeof(HudManager), nameof(HudManager.Update))]
    internal static class DiagPatch
    {
        public static bool Prepare() => DiagMode.Length > 0;

        public static void Postfix(HudManager __instance)
        {
            try
            {
                string key = DiagMode.Split(',')[0];
                if (_diagDone || AtlasMaps.ActiveKey != key) return;
                if (_diagAt < 0f) { _diagAt = Time.time + 2f; return; }
                if (Time.time < _diagAt) return;
                _diagDone = true;
                __instance.StartCoroutine(DiagRun(key, DiagMode.Contains("skip")).WrapToIl2Cpp());
            }
            catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} diag failed: {e}"); _diagDone = true; }
        }
    }

    private static IEnumerator DiagRun(string key, bool skip)
    {
        float[] at = { 1.5f, 6.0f, 15.0f, 25.0f, 40.0f, 52.0f };
        int next = 0;
        float t0 = Time.time;
        string dir = Path.Combine(BepInEx.Paths.GameRootPath, "AtlasShots");
        Directory.CreateDirectory(dir);
        _playing = true;
        var play = Play(key, 0f);
        while (true)
        {
            bool more;
            try { more = play.MoveNext(); } catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} diag playback: {e}"); more = false; }
            if (!more) break;
            float t = Time.time - t0;
            if (skip && t >= 3f && !_skip) { _skip = true; Log("diag: skip"); }
            if (next < at.Length && t >= at[next])
            {
                ScreenCapture.CaptureScreenshot(Path.Combine(dir, FormattableString.Invariant($"cine_{key}_{at[next]:0.0}s.png")));
                next++;
            }
            yield return play.Current;
        }
        Cleanup();
        _playing = false;
        Log($"diag: done after {Time.time - t0:F1} s");
        yield return new WaitForSeconds(1f);
        Log("diag: all done");
        Application.Quit();
    }
}
