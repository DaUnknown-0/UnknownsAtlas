// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasEject - eigene Rauswurf-Szenen der Atlas-Karten, pro Rauswurf zufaellig gewaehlt.
//
// Museum: Sarkophag, Falltuer ins Depot, T-Rex, Hinausgeworfen (Waechter, Regennacht).
// Wald:   Wildwasser (Kanu ueber den Wasserfall), In den Wald gezerrt (rote Augen),
//         Vom Hochsitz (in den Talnebel).
//
// Die Karten sind technisch die Skeld, also laeuft ein SkeldExileController. Ein Postfix auf
// ExileController.Begin stoppt dessen Animate-Koroutine und startet die eigene Szene; Text,
// Tipp-Geraeusch (HandleText), Impostor-Zeile und WrapUp bleiben die des Spiels, damit TOR/UC-
// Patches (Texte, Void-Styling, WrapUp-Logik) unveraendert greifen.
//
// Die Wahl ist auf allen Clients gleich: Seed aus der ausgeworfenen PlayerId und der Zahl der Toten.
// Eine Szene = Build() + Step(t) ueber eine feste Laenge, keine verschachtelten Koroutinen.

using System;
using System.Collections;
using System.Collections.Generic;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

[HarmonyPatch]
internal static class AtlasEject
{
    private const string LogPrefix = "[Atlas/Eject]";
    public static readonly string[] MuseumScenes = { "tomb", "trapdoor", "trex", "thrown" };
    public static readonly string[] WaldScenes = { "rapids", "dragged", "stand" };
    /// <summary>Diagnose: Szene erzwingen (Index in der Kartenliste), -1 = zufaellig.</summary>
    internal static int ForceScene = -1;

    [HarmonyPostfix]
    [HarmonyPatch(typeof(ExileController), nameof(ExileController.Begin))]
    internal static void ExileController_Begin_Postfix(ExileController __instance)
    {
        if (!AtlasMuseumBuilder.Active || __instance == null || __instance.TryCast<SkeldExileController>() == null) return;
        try
        {
            __instance.StopAllCoroutines();
            __instance.StartCoroutine(Run(__instance).WrapToIl2Cpp());
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"{LogPrefix} start failed: {e}"); }
    }

    private static string Pick(ExileController ec)
    {
        bool wald = AtlasMuseumBuilder.D.Key == "wald";
        var list = wald ? WaldScenes : MuseumScenes;
        if (ForceScene >= 0) return list[ForceScene % list.Length];
        int pid = ec.initData != null && ec.initData.networkedPlayer != null ? ec.initData.networkedPlayer.PlayerId : 255;
        int dead = 0;
        foreach (var p in GameData.Instance.AllPlayers) if (p != null && p.IsDead) dead++;
        var rng = new System.Random(pid * 7919 + dead * 104729 + (wald ? 1 : 0));
        return list[rng.Next(list.Length)];
    }

    private static IEnumerator Run(ExileController ec)
    {
        Scene scene = null;
        try
        {
            string kind = Pick(ec);
            scene = kind switch
            {
                "tomb" => new TombScene(),
                "trapdoor" => new TrapdoorScene(),
                "trex" => new TRexScene(),
                "thrown" => new ThrownScene(),
                "rapids" => new RapidsScene(),
                "dragged" => new DraggedScene(),
                _ => new StandScene(),
            };
            scene.Setup(ec);
            scene.Build();
            AtlasPlugin.Logger.LogInfo($"{LogPrefix} scene {kind} (player {(scene.P != null ? "yes" : "none")})");
        }
        catch (Exception e)
        {
            AtlasPlugin.Logger.LogError($"{LogPrefix} build failed, plain fade: {e}");
            scene = null;
        }

        var hud = HudManager.Instance;
        if (hud != null) hud.StartCoroutine(hud.CoFadeFullScreen(Color.black, Color.clear, 0.2f, false));
        if (scene != null) ec.StartCoroutine(ec.HandleText(scene.TextAt, scene.TextDur));
        else ec.StartCoroutine(ec.HandleText(0.5f, 2f));

        float len = scene?.Length ?? 3f, t = 0f;
        while (t < len)
        {
            t += Time.deltaTime;
            try { scene?.Step(Mathf.Min(t, len)); } catch (Exception e) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} step: {e.Message}"); scene = null; }
            yield return null;
        }

        // Impostor-Zeile wie im Spiel: aufploppen, kurz stehen lassen
        bool imp = false;
        try { imp = ec.initData != null && ec.initData.confirmImpostor && ec.ImpostorText != null; } catch { }
        if (imp) ec.ImpostorText.gameObject.SetActive(true);
        float extra = imp ? 1.6f : 0.6f;
        for (float u = 0f; u < extra; u += Time.deltaTime)
        {
            if (imp)
            {
                float k = Mathf.Clamp01(u / 0.3f);
                float sc = k < 1f ? Mathf.Lerp(0.2f, 1.1f, k) : Mathf.Lerp(1.1f, 1f, Mathf.Clamp01((u - 0.3f) / 0.2f));
                ec.ImpostorText.transform.localScale = Vector3.one * sc;
            }
            try { scene?.Step(len + u); } catch { scene = null; }
            yield return null;
        }

        if (hud != null) hud.StartCoroutine(hud.CoFadeFullScreen(Color.clear, Color.black, 0.2f, false));
        for (float u = 0f; u < 0.25f; u += Time.deltaTime) yield return null;
        ec.WrapUp();
    }

    // ================================================================== Grundgeruest

    internal abstract class Scene
    {
        public float Length = 6.5f, TextAt = 1.4f, TextDur = 2.6f;
        public Transform Root, P;
        protected ExileController Ec;
        protected Vector3 PScale;
        private int _layerId, _lo, _hi, _layer;
        private readonly List<(SpriteRenderer R, Vector3 V, float Life, float Age, Color C, float Grow)> _puffs = new();
        private readonly HashSet<string> _played = new();
        private Vector3 _rootHome;
        private float _shakeUntil;

        public void Setup(ExileController ec)
        {
            Ec = ec;
            _layer = ec.gameObject.layer;
            // Sortierung vom Spieler-Bild: Hintergrund darunter, Vordergrund darueber
            _lo = int.MaxValue; _hi = int.MinValue;
            try
            {
                if (ec.Player != null && ec.Player.gameObject.activeSelf && ec.initData != null && ec.initData.networkedPlayer != null)
                {
                    P = ec.Player.transform;
                    foreach (var r in ec.Player.GetComponentsInChildren<Renderer>(true))
                    {
                        _layerId = r.sortingLayerID;
                        _lo = Math.Min(_lo, r.sortingOrder); _hi = Math.Max(_hi, r.sortingOrder);
                    }
                }
            }
            catch { P = null; }
            if (_lo == int.MaxValue)
            {
                var tr = ec.Text != null ? ec.Text.GetComponent<Renderer>() : null;
                _layerId = tr != null ? tr.sortingLayerID : 0;
                _lo = _hi = tr != null ? tr.sortingOrder - 5 : 0;
            }

            // Skeld-Kulisse (Sterne, Hintergrund) ausblenden; Spieler und Texte bleiben
            foreach (var r in ec.GetComponentsInChildren<Renderer>(true))
            {
                if (r == null) continue;
                var tf = r.transform;
                if ((ec.Player != null && tf.IsChildOf(ec.Player.transform)) ||
                    (ec.Text != null && tf.IsChildOf(ec.Text.transform)) ||
                    (ec.ImpostorText != null && tf.IsChildOf(ec.ImpostorText.transform))) continue;
                r.enabled = false;
            }
            foreach (var ps in ec.GetComponentsInChildren<ParticleSystem>(true)) if (ps != null) ps.Stop();

            var go = new GameObject("Atlas_EjectScene") { layer = _layer };
            go.transform.SetParent(ec.transform, false);
            Root = go.transform;
            // Szenen-Einheiten = Hintergrund-Einheiten (11 x 6,2), auf den Bildschirm skaliert (fuellend)
            var cam = Camera.main;
            float halfH = (cam != null ? cam.orthographicSize : 3f) / Mathf.Max(0.001f, ec.transform.lossyScale.y);
            float halfW = halfH * (cam != null ? cam.aspect : 1.78f);
            float s = Mathf.Max(2f * halfW / 11f, 2f * halfH / 6.2f);
            Root.localPosition = new Vector3(0f, 0f, 1f);
            Root.localScale = new Vector3(s, s, 1f);
            _rootHome = Root.localPosition;

            if (P != null)
            {
                P.SetParent(Root, true);
                PScale = P.localScale;
                P.localRotation = Quaternion.identity;
            }

            // Text oben ueber einem dunklen Verlauf
            if (ec.Text != null)
            {
                ec.Text.transform.localPosition = new Vector3(0f, halfH - 0.55f, ec.Text.transform.localPosition.z);
                SetOrder(ec.Text.GetComponent<Renderer>(), _hi + 40);
            }
            if (ec.ImpostorText != null)
            {
                ec.ImpostorText.transform.localPosition = new Vector3(0f, halfH - 1.1f, ec.ImpostorText.transform.localPosition.z);
                SetOrder(ec.ImpostorText.GetComponent<Renderer>(), _hi + 40);
            }
            var band = Spr("task_eject_band.png", new Vector2(0f, 3.1f), 30, new Vector2(0.5f, 1f));
            band.transform.localScale = new Vector3(12f / 0.64f, 1.9f / 1.6f, 1f);
        }

        public abstract void Build();
        protected abstract void Animate(float t);

        public void Step(float t)
        {
            Animate(t);
            float dt = Time.deltaTime;
            for (int i = _puffs.Count - 1; i >= 0; i--)
            {
                var p = _puffs[i];
                p.Age += dt;
                if (p.R == null || p.Age >= p.Life) { if (p.R != null) Object.Destroy(p.R.gameObject); _puffs.RemoveAt(i); continue; }
                float k = p.Age / p.Life;
                p.R.transform.localPosition += p.V * dt;
                p.R.transform.localScale *= 1f + p.Grow * dt;
                p.R.color = new Color(p.C.r, p.C.g, p.C.b, p.C.a * (1f - k));
                _puffs[i] = p;
            }
            if (Time.time < _shakeUntil)
                Root.localPosition = _rootHome + (Vector3)(UnityEngine.Random.insideUnitCircle * 0.06f * Root.localScale.x);
            else Root.localPosition = _rootHome;
        }

        // ---- Bausteine
        /// <summary>order relativ zum Spieler: negativ = dahinter, positiv = davor.</summary>
        protected SpriteRenderer Spr(string file, Vector2 pos, int order, Vector2? pivot = null, float scale = 1f)
        {
            var go = new GameObject(file) { layer = _layer };
            go.transform.SetParent(Root, false);
            go.transform.localPosition = new Vector3(pos.x, pos.y, -order * 0.001f);
            go.transform.localScale = Vector3.one * scale;
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = AtlasAssets.TaskSprite(file, 100f, pivot ?? new Vector2(0.5f, 0.5f));
            sr.sortingLayerID = _layerId;
            sr.sortingOrder = order < 0 ? _lo + order : _hi + order;
            return sr;
        }

        protected SpriteRenderer Child(Transform parent, string file, Vector2 local, int order, Vector2? pivot = null, float scale = 1f)
        {
            var sr = Spr(file, Vector2.zero, order, pivot, scale);
            sr.transform.SetParent(parent, false);
            sr.transform.localPosition = new Vector3(local.x, local.y, 0f);
            return sr;
        }

        protected Transform Node(string name, Vector2 pos)
        {
            var go = new GameObject(name) { layer = _layer };
            go.transform.SetParent(Root, false);
            go.transform.localPosition = pos;
            return go.transform;
        }

        protected void Bg(string file) => Spr(file, Vector2.zero, -30);

        private void SetOrder(Renderer r, int order) { if (r != null) { r.sortingLayerID = _layerId; r.sortingOrder = order; } }

        /// <summary>Spieler setzen (Position in Szenen-Einheiten, Groesse relativ, Drehung in Grad).</summary>
        protected void Pl(Vector2 pos, float size = 1f, float rot = 0f, bool faceLeft = false)
        {
            if (P == null) return;
            P.localPosition = new Vector3(pos.x, pos.y, P.localPosition.z);
            P.localScale = new Vector3(Mathf.Abs(PScale.x) * size * (faceLeft ? -1f : 1f), PScale.y * size, PScale.z);
            P.localEulerAngles = new Vector3(0f, 0f, rot);
        }

        protected void PlHide() { if (P != null && P.gameObject.activeSelf) P.gameObject.SetActive(false); }

        protected void Puff(Vector2 at, Color c, float size, Vector2 vel, float life = 1.2f, float grow = 0.8f, int order = 20)
        {
            var sr = Spr("task_eject_soft.png", at, order, null, size);
            sr.color = c;
            _puffs.Add((sr, vel, life, 0f, c, grow));
        }

        /// <summary>Einmal-Ereignis zum Zeitpunkt at (Geraeusch, Staub ...).</summary>
        protected bool Once(float t, float at, string key)
        {
            if (t < at || _played.Contains(key)) return false;
            _played.Add(key);
            return true;
        }

        protected void Sound(float t, float at, string clip, float vol = 0.7f)
        {
            if (Once(t, at, "snd:" + clip + at)) AtlasWeatherFx.Sfx(clip, vol);
        }

        protected void Shake(float dur) => _shakeUntil = Time.time + dur;

        protected static float K(float t, float a, float b) => Mathf.Clamp01((t - a) / Mathf.Max(0.0001f, b - a));
        protected static float Ease(float k) => k * k * (3f - 2f * k);
        protected static float EaseIn(float k) => k * k;
        protected static float EaseOut(float k) => 1f - (1f - k) * (1f - k);
        protected static float Bob(float t, float amp = 0.06f, float f = 9f) => Mathf.Abs(Mathf.Sin(t * f)) * amp;
    }

    // ================================================================== Museum: Sarkophag

    private sealed class TombScene : Scene
    {
        private Transform _lid;
        private SpriteRenderer _base;
        public override void Build()
        {
            Bg("task_eject_tomb_bg.jpg");
            _base = Spr("task_eject_sarc_base.png", new Vector2(0.6f, -1.55f), 5, null, 0.85f);
            _lid = Spr("task_eject_sarc_lid.png", new Vector2(0.6f, 4.2f), 6, null, 0.85f).transform;
            TextAt = 1.2f; TextDur = 2.8f; Length = 6.2f;
        }

        protected override void Animate(float t)
        {
            // schwebt herein (langsam kreiselnd), sinkt in die Wanne
            float a = Ease(K(t, 0f, 3f));
            var pos = Vector2.Lerp(new Vector2(-6.4f, 0.6f), new Vector2(0.6f, -0.35f), a) + new Vector2(0f, Mathf.Sin(t * 2.2f) * 0.12f * (1f - a));
            pos.y -= Ease(K(t, 3.1f, 3.8f)) * 0.75f;
            Pl(pos, 0.9f, Mathf.Sin(t * 1.4f) * 25f * (1f - K(t, 2.4f, 3.1f)));
            // Deckel gleitet zu
            Sound(t, 3.8f, "grind", 0.6f);
            float l = EaseIn(K(t, 3.8f, 4.6f));
            _lid.localPosition = new Vector3(0.6f, Mathf.Lerp(4.2f, -0.72f, l), _lid.localPosition.z);
            _lid.localEulerAngles = new Vector3(0f, 0f, Mathf.Lerp(12f, 0f, l));
            if (Once(t, 4.6f, "shut"))
            {
                PlHide();
                AtlasWeatherFx.Sfx("thud", 0.8f);
                Shake(0.25f);
                for (int i = 0; i < 8; i++)
                    Puff(new Vector2(0.6f + UnityEngine.Random.Range(-1.8f, 1.8f), -0.8f), new Color(0.75f, 0.62f, 0.45f, 0.55f), 0.5f,
                         new Vector2(UnityEngine.Random.Range(-0.6f, 0.6f), UnityEngine.Random.Range(0.1f, 0.5f)), 1.4f);
            }
        }
    }

    // ================================================================== Museum: Falltuer ins Depot

    private sealed class TrapdoorScene : Scene
    {
        private Transform _l, _r;
        private SpriteRenderer _shade;
        public override void Build()
        {
            Bg("task_eject_depot_bg.jpg");
            _l = Spr("task_eject_trap_leaf.png", new Vector2(-1.4f, 0f), -5, new Vector2(0f, 0.5f)).transform;
            _r = Spr("task_eject_trap_leaf.png", new Vector2(1.4f, 0f), -5, new Vector2(1f, 0.5f)).transform;
            _shade = Spr("task_eject_soft.png", new Vector2(0f, 0.2f), 5, null, 1.4f);
            _shade.color = new Color(0f, 0f, 0f, 0f);
            TextAt = 1.0f; TextDur = 2.6f; Length = 6.0f;
        }

        protected override void Animate(float t)
        {
            float w = K(t, 0f, 2.2f);
            if (t < 3.1f) Pl(Vector2.Lerp(new Vector2(-6.2f, 0.4f), new Vector2(0f, 0.3f), Ease(w)) + new Vector2(0f, w < 1f ? Bob(t) : 0f), 1f, 0f);
            Sound(t, 2.4f, "creak", 0.6f);
            float open = Ease(K(t, 2.6f, 3.1f)) * (1f - Ease(K(t, 5.0f, 5.5f)));
            float sx = Mathf.Lerp(1f, 0.06f, open);
            _l.localScale = new Vector3(sx, 1f, 1f);
            _r.localScale = new Vector3(sx, 1f, 1f);
            var dim = new Color(1f - open * 0.5f, 1f - open * 0.5f, 1f - open * 0.5f);
            _l.GetComponent<SpriteRenderer>().color = dim; _r.GetComponent<SpriteRenderer>().color = dim;
            // Sturz: kleiner werden, kreiseln, ins Dunkel
            float f = EaseIn(K(t, 3.1f, 4.3f));
            if (t >= 3.1f) Pl(new Vector2(0f, 0.3f - f * 0.3f), Mathf.Lerp(1f, 0.12f, f), f * 540f);
            _shade.color = new Color(0f, 0f, 0f, Mathf.Clamp01(f * 1.3f) * (t < 4.4f ? 1f : 0f));
            if (Once(t, 4.4f, "gone")) PlHide();
            Sound(t, 4.7f, "thud", 0.25f);
            Sound(t, 5.5f, "slam", 0.6f);
        }
    }

    // ================================================================== Museum: T-Rex

    private sealed class TRexScene : Scene
    {
        private Transform _rex, _jawPivot;
        public override void Build()
        {
            Bg("task_eject_hall_bg.jpg");
            _rex = Node("trex", new Vector2(9f, -0.1f));
            _rex.localScale = Vector3.one * 0.85f;
            Child(_rex, "task_eject_trex_head.png", Vector2.zero, 8);
            _jawPivot = new GameObject("jawPivot") { layer = _rex.gameObject.layer }.transform;
            _jawPivot.SetParent(_rex, false);
            _jawPivot.localPosition = new Vector3(2.3f, -0.95f, 0f);
            Child(_jawPivot, "task_eject_trex_jaw.png", new Vector2(-2.4f, 0f), 7);
            TextAt = 1.2f; TextDur = 2.6f; Length = 6.4f;
        }

        protected override void Animate(float t)
        {
            float w = K(t, 0f, 2.4f);
            if (t < 3.5f) Pl(Vector2.Lerp(new Vector2(-6.2f, -0.75f), new Vector2(-0.5f, -0.75f), Ease(w)) + new Vector2(0f, w < 1f ? Bob(t) : 0f), 1f, 0f, faceLeft: t > 2.7f);
            if (t > 2.7f && t < 3.5f) Pl(new Vector2(-0.5f + Mathf.Sin(t * 60f) * 0.03f, -0.75f), 1f, 0f, faceLeft: true);   // zittern
            // Schaedel schnellt herein, Kiefer auf, zu, zurueck
            Sound(t, 2.8f, "roar", 0.8f);
            if (Once(t, 2.8f, "shake")) Shake(0.8f);
            float x = t < 3.9f ? Mathf.Lerp(9f, 1.6f, EaseOut(K(t, 2.8f, 3.3f))) : Mathf.Lerp(1.6f, 10f, EaseIn(K(t, 3.9f, 4.7f)));
            _rex.localPosition = new Vector3(x, -0.1f + (t > 3.3f && t < 3.9f ? Mathf.Sin(t * 30f) * 0.03f : 0f), _rex.localPosition.z);
            float jaw = t < 3.4f ? 26f * Ease(K(t, 2.9f, 3.25f)) : 26f * (1f - Ease(K(t, 3.4f, 3.55f)));
            _jawPivot.localEulerAngles = new Vector3(0f, 0f, jaw);
            if (Once(t, 3.55f, "chomp"))
            {
                PlHide();
                AtlasWeatherFx.Sfx("slam", 0.7f);
                for (int i = 0; i < 6; i++)
                    Puff(new Vector2(-0.4f, -1.2f), new Color(0.8f, 0.78f, 0.72f, 0.4f), 0.4f, new Vector2(UnityEngine.Random.Range(-0.8f, 0.8f), UnityEngine.Random.Range(0f, 0.4f)), 1.2f);
            }
        }
    }

    // ================================================================== Museum: Hinausgeworfen

    private sealed class ThrownScene : Scene
    {
        private Transform _g1, _g2, _door;
        private readonly List<Transform> _rain = new();
        public override void Build()
        {
            Bg("task_eject_night_bg.jpg");
            _door = Spr("task_eject_door.png", new Vector2(-3.95f, -1.07f), -4, new Vector2(0f, 0f), 0.95f).transform;
            _door.localScale = new Vector3(0.05f, 0.95f, 1f);
            _g1 = Spr("task_eject_guard.png", new Vector2(-3.9f, -1.25f), -2, null, 0.62f).transform;
            _g2 = Spr("task_eject_guard.png", new Vector2(-2.8f, -1.25f), 2, null, 0.62f).transform;
            _g2.localScale = new Vector3(-0.62f, 0.62f, 1f);
            for (int i = 0; i < 60; i++)
            {
                var d = Spr("task_raindrop.png", new Vector2(UnityEngine.Random.Range(-6f, 6f), UnityEngine.Random.Range(-3.2f, 3.2f)), 25, null, UnityEngine.Random.Range(0.5f, 0.9f));
                d.color = new Color(0.75f, 0.85f, 1f, 0.5f);
                d.transform.localEulerAngles = new Vector3(0f, 0f, 8f);
                _rain.Add(d.transform);
            }
            AtlasWeatherFx.Sfx("rush", 0.35f);
            TextAt = 1.6f; TextDur = 2.6f; Length = 6.6f;
        }

        protected override void Animate(float t)
        {
            float dt = Time.deltaTime;
            foreach (var d in _rain)
            {
                var p = d.localPosition + new Vector3(-1.5f * dt, -11f * dt, 0f);
                if (p.y < -3.4f) { p.y += 6.8f; p.x = UnityEngine.Random.Range(-6f, 6.5f); }
                d.localPosition = p;
            }
            // Waechter treten vor, Wurf in hohem Bogen
            float step = Ease(K(t, 0.3f, 0.8f)) * (1f - Ease(K(t, 2.8f, 3.3f)));
            _g1.localPosition = new Vector3(-3.9f + step * 0.5f, -1.25f, _g1.localPosition.z);
            _g2.localPosition = new Vector3(-2.8f + step * 0.5f, -1.25f, _g2.localPosition.z);
            if (t < 0.9f) Pl(new Vector2(-3.35f + step * 0.45f, -1.0f), 0.8f, 0f);
            Sound(t, 0.9f, "whoosh", 0.7f);
            if (t >= 0.9f && t < 2.2f)
            {
                float k = K(t, 0.9f, 2.2f);
                var p = Vector2.Lerp(new Vector2(-2.9f, -1.0f), new Vector2(0.9f, -2.25f), k) + new Vector2(0f, 4f * k * (1f - k) * 1.9f);
                Pl(p, 0.8f, -k * 720f);
            }
            if (Once(t, 2.2f, "land"))
            {
                AtlasWeatherFx.Sfx("splash", 0.8f);
                for (int i = 0; i < 9; i++)
                    Puff(new Vector2(0.9f, -2.35f), new Color(0.7f, 0.8f, 1f, 0.55f), 0.35f,
                         new Vector2(UnityEngine.Random.Range(-1.4f, 1.4f), UnityEngine.Random.Range(0.4f, 1.4f)), 0.9f, 0.4f);
            }
            if (t >= 2.2f)
            {
                float b = K(t, 2.2f, 2.6f);
                Pl(new Vector2(0.9f + b * 0.3f, -2.25f + Mathf.Sin(b * Mathf.PI) * 0.25f), 0.8f, -90f);
            }
            if (Once(t, 3.3f, "inside")) { _g1.gameObject.SetActive(false); _g2.gameObject.SetActive(false); }
            float c = Ease(K(t, 3.4f, 3.8f));
            _door.localScale = new Vector3(Mathf.Lerp(0.05f, 0.95f, c), 0.95f, 1f);
            Sound(t, 3.8f, "slam", 0.7f);
        }
    }

    // ================================================================== Wald: Wildwasser

    private sealed class RapidsScene : Scene
    {
        private Transform _boat;
        public override void Build()
        {
            Bg("task_eject_river_bg.jpg");
            _boat = Node("boat", new Vector2(-6.5f, -0.75f));
            Child(_boat, "task_eject_canoe.png", Vector2.zero, 6, null, 0.72f);
            if (P != null) { P.SetParent(_boat, true); }
            AtlasWeatherFx.Sfx("rush", 0.5f);
            TextAt = 1.4f; TextDur = 2.6f; Length = 6.4f;
        }

        protected override void Animate(float t)
        {
            // Treiben, schneller werden, ueber die Kante kippen und fallen
            float d = EaseIn(K(t, 0f, 3.8f));
            float x = Mathf.Lerp(-6.5f, 2.7f, d);
            float y = -0.75f + Mathf.Sin(t * 3f) * 0.05f;
            float rot = Mathf.Sin(t * 2.3f) * 4f;
            if (t > 3.8f)
            {
                float k = K(t, 3.8f, 4.9f);
                x += k * 1.4f;
                y -= EaseIn(k) * 4.5f;
                rot = -Mathf.Lerp(0f, 55f, EaseOut(K(t, 3.8f, 4.3f)));
            }
            _boat.localPosition = new Vector3(x, y, _boat.localPosition.z);
            _boat.localEulerAngles = new Vector3(0f, 0f, rot);
            if (P != null && P.parent == _boat)
            {
                P.localPosition = new Vector3(0.1f / 0.72f * 0.72f, 0.45f, P.localPosition.z);
                P.localEulerAngles = Vector3.zero;
                P.localScale = new Vector3(Mathf.Abs(PScale.x) * 0.62f, PScale.y * 0.62f, PScale.z);
            }
            if (Once(t, 4.8f, "splash"))
            {
                AtlasWeatherFx.Sfx("splash", 0.9f);
                for (int i = 0; i < 12; i++)
                    Puff(new Vector2(3.9f + UnityEngine.Random.Range(-0.6f, 0.6f), -2.0f), new Color(0.9f, 0.95f, 1f, 0.6f), 0.7f,
                         new Vector2(UnityEngine.Random.Range(-0.5f, 0.5f), UnityEngine.Random.Range(0.3f, 1.1f)), 1.6f, 0.9f);
            }
        }
    }

    // ================================================================== Wald: In den Wald gezerrt

    private sealed class DraggedScene : Scene
    {
        private Transform _bush;
        private readonly List<(SpriteRenderer R, float At)> _eyes = new();
        public override void Build()
        {
            Bg("task_eject_forest_bg.jpg");
            _bush = Spr("task_eject_bushes.png", new Vector2(3.4f, -1.75f), 8, new Vector2(0.5f, 0.2f), 0.95f).transform;
            var spots = new[] { (new Vector2(2.3f, 0.25f), 2.3f), (new Vector2(3.8f, 0.7f), 2.7f), (new Vector2(4.6f, -0.1f), 3.0f), (new Vector2(1.5f, 0.95f), 3.3f), (new Vector2(3.1f, 1.35f), 3.5f) };
            foreach (var (p, at) in spots)
            {
                var e = Spr("task_eject_eyes.png", p, -3, null, 0.9f);
                e.color = new Color(1f, 1f, 1f, 0f);
                _eyes.Add((e, at));
            }
            TextAt = 1.2f; TextDur = 2.6f; Length = 6.4f;
        }

        protected override void Animate(float t)
        {
            float w = K(t, 0f, 2.0f);
            if (t < 3.9f)
            {
                var p = Vector2.Lerp(new Vector2(-6.2f, -1.55f), new Vector2(-1.2f, -1.55f), Ease(w)) + new Vector2(0f, w < 1f ? Bob(t) : 0f);
                if (t > 2.8f) p.x += Mathf.Sin(t * 70f) * 0.025f;                            // zittert
                Pl(p, 1f, 0f);
            }
            Sound(t, 2.2f, "twig", 0.6f);
            foreach (var (r, at) in _eyes)
            {
                float a = K(t, at, at + 0.35f) * (1f - K(t, 4.1f, 4.3f));
                bool blink = Mathf.Repeat(t * 0.9f + at, 1.7f) < 0.08f;
                r.color = new Color(1f, 1f, 1f, blink ? 0f : a);
            }
            Sound(t, 3.6f, "growl", 0.8f);
            // Ruck: ins Gebuesch gerissen
            if (t >= 3.9f)
            {
                float k = EaseIn(K(t, 3.9f, 4.2f));
                Pl(new Vector2(Mathf.Lerp(-1.2f, 4.2f, k), -1.55f + k * 0.2f), 1f, -35f * k);
                if (t > 4.2f) PlHide();
            }
            Sound(t, 3.9f, "whoosh", 0.8f);
            float rustle = (t > 3.9f && t < 5f) ? Mathf.Sin(t * 40f) * 4f * (1f - K(t, 3.9f, 5f)) : 0f;
            _bush.localEulerAngles = new Vector3(0f, 0f, rustle);
            Sound(t, 5.2f, "owl", 0.35f);
        }
    }

    // ================================================================== Wald: Vom Hochsitz

    private sealed class StandScene : Scene
    {
        private Transform _fog;
        public override void Build()
        {
            Bg("task_eject_valley_bg.jpg");
            Spr("task_eject_stand.png", new Vector2(-3.4f, -1.2f), -4, null, 0.8f);
            _fog = Spr("task_eject_fog.png", new Vector2(0f, -2.3f), 10, null, 1.1f).transform;
            TextAt = 1.2f; TextDur = 2.6f; Length = 6.4f;
        }

        protected override void Animate(float t)
        {
            _fog.localPosition = new Vector3(Mathf.Sin(t * 0.4f) * 0.3f, -2.3f, _fog.localPosition.z);
            Sound(t, 1.6f, "creak", 0.6f);
            if (t < 2.2f)
            {
                float shove = t > 1.9f ? EaseOut(K(t, 1.9f, 2.2f)) * 0.35f : 0f;
                Pl(new Vector2(-3.3f + shove, 0.2f), 0.72f, shove * -20f);
            }
            else
            {
                float k = K(t, 2.2f, 4.3f);
                var p = new Vector2(Mathf.Lerp(-2.95f, 1.8f, k), 0.2f + 1.2f * k * (1f - k) * 1.2f - EaseIn(k) * 3.2f);
                Pl(p, Mathf.Lerp(0.72f, 0.22f, k), -k * 540f);
                if (k >= 1f) PlHide();
            }
            Sound(t, 2.2f, "whoosh", 0.7f);
            Sound(t, 4.6f, "thud", 0.2f);
        }
    }

    // ================================================================== Diagnose

    /// <summary>"eject:&lt;n&gt;" im TaskTest: Rauswurf eines Dummys (oder, ohne Dummy, von niemandem).</summary>
    internal static void Diag(int scene)
    {
        ForceScene = scene;
        var ship = ShipStatus.Instance;
        if (ship == null || ship.ExileCutscenePrefab == null) { AtlasPlugin.Logger.LogWarning($"{LogPrefix} diag: no exile prefab"); return; }
        NetworkedPlayerInfo victim = null;
        foreach (var p in GameData.Instance.AllPlayers)
            if (p != null && !p.IsDead && p.PlayerId != PlayerControl.LocalPlayer.PlayerId) { victim = p; break; }
        var ec = Object.Instantiate(ship.ExileCutscenePrefab);
        ec.transform.SetParent(HudManager.Instance.transform, false);
        ec.transform.localPosition = new Vector3(0f, 0f, -60f);
        ec.BeginForGameplay(victim, false);
        AtlasPlugin.Logger.LogInfo($"{LogPrefix} diag: eject {(victim != null ? victim.PlayerName : "nobody")}, scene index {scene}");
    }
}
