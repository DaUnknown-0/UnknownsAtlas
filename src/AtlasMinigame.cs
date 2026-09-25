// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.
//
// AtlasMinigame - die eigenen Minispiele der Atlas-Karten (docs/TASK_KONZEPT.md, Stufe B).
//
// Eine per ClassInjector eingeschleuste Unterklasse von Minigame. Sie ueberschreibt NICHTS:
// Console.Use instanziiert das Prefab unter der Kamera und ruft das vanilla Minigame.Begin
// (setzt Instance, MyTask, MyNormTask, Oeffnungsanimation). Die eigene Logik laeuft in Unitys
// Start/Update. Abschluss wie ein vanilla Minispiel: MyNormTask.NextStep(), dann CoStartClose.
//
// Welcher Baustein drinsteckt, steht im GameObject-Namen ("AtlasTask_dust"): verwaltete Felder
// einer eingeschleusten Klasse werden beim Instantiate NICHT mitkopiert.
//
// Jede Mechanik bekommt pro Frame nur (Mausposition im Lokalraum, Taste gehalten, gerade
// gedrueckt) und kann sich selbst spielen (Simulate) - fuer den Autotest und spaeter AutoPilot.

using System;
using System.Collections.Generic;
using Il2CppInterop.Runtime.Attributes;
using UnityEngine;
using Object = UnityEngine.Object;

namespace UnknownsAtlas;

public class AtlasMinigame : Minigame
{
    public AtlasMinigame(IntPtr ptr) : base(ptr) { }

    /// <summary>Autotest: die Mechanik spielt sich selbst (Diagnostics.TaskTest).</summary>
    internal static bool DiagAuto;
    internal static float DiagProgress;
    /// <summary>Autotest ohne passenden Task: nichts abhaken (sonst traefe es einen fremden Task).</summary>
    internal static bool DiagNoComplete;
    /// <summary>Autotest: diesen Schritt zeigen statt des echten (Diagnostics.TaskTest "fuse@1").</summary>
    internal static int DiagStep = -1;

    private IAtlasMechanic _mech;
    private SpriteRenderer _close;
    private bool _done;
    private float _opened;
    private bool _wasDown;

    public void Awake()
    {
        // Das Il2Cpp-Konstruktor-Initialisierungsfeld laeuft fuer eingeschleuste Klassen nicht;
        // Minigame.Begin loggt aber ueber logger.
        try { if (logger == null) logger = new Logger("AtlasMinigame", (Logger.Level)1, (Logger.Category)0); }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Task] logger: {e.Message}"); }
    }

    // ---- Logger-Pin (Absturz 24.09.) ----
    // Vanilla Minigame.Close() loggt ueber das private Feld Minigame.logger. Bei diesem
    // eingeschleusten Minispiel war der Logger beim Schliessen schon eingesammelt und sein Speicher
    // neu belegt: Close -> Logger.Info -> FormatMessageForConsole -> string.IsNullOrEmpty(Muell) ->
    // Zugriffsverletzung (4 Abstuerze, immer "step 0 -> 1 of 2", Dumps: GameAssembly+0x10AC24E,
    // Aufrufer Minigame.Close+0x2B8). Der il2cpp-GC verfolgt das Basisklassen-Feld in der
    // eingeschleusten Klasse offenbar nicht; ein GC-Handle haelt den Logger fest, solange das
    // Minispiel lebt. Feld per Name und Laufzeit-Offset, nicht fest verdrahtet.
    private nint _loggerHandle;
    private static IntPtr _loggerField;
    /// <summary>Autotest-Kontrolle (TaskTest "stepmgnopin:"): Logger NICHT festhalten.</summary>
    internal static bool DiagNoPin;

    private void PinLogger()
    {
        try
        {
            if (_loggerField == IntPtr.Zero)
                _loggerField = Il2CppInterop.Runtime.IL2CPP.il2cpp_class_get_field_from_name(
                    Il2CppInterop.Runtime.Il2CppClassPointerStore<Minigame>.NativeClassPtr, "logger");
            if (_loggerField == IntPtr.Zero || _loggerHandle != 0 || DiagNoPin) return;
            uint off = Il2CppInterop.Runtime.IL2CPP.il2cpp_field_get_offset(_loggerField);
            IntPtr logger = System.Runtime.InteropServices.Marshal.ReadIntPtr(Pointer + (int)off);
            if (logger != IntPtr.Zero) _loggerHandle = Il2CppInterop.Runtime.IL2CPP.il2cpp_gchandle_new(logger, false);
        }
        catch (Exception e) { AtlasPlugin.Logger.LogWarning($"[Atlas/Task] logger pin failed: {e.Message}"); }
    }

    public void Start()
    {
        PinLogger();
        try
        {
            string kind = name.Replace("(Clone)", "").Replace("AtlasTask_", "");
            var ctx = new AtlasTaskCtx
            {
                Task = MyNormTask,
                Step = DiagStep >= 0 ? DiagStep : (MyNormTask != null ? MyNormTask.taskStep : 0),
                Map = AtlasMuseumBuilder.D.Key,
            };
            ctx.AnyTask = MyTask;
            try { ctx.ConsoleId = Console != null ? Console.ConsoleId : 0; } catch { ctx.ConsoleId = 0; }
            var divert = MyTask != null ? MyTask.TryCast<DivertPowerTask>() : null;
            if (divert != null) ctx.Target = divert.TargetSystem;
            AtlasTaskKit.Kind = kind;                                   // fuer "art:datei" in TaskArt/TaskText
            _mech = Create(kind, ctx.Step);
            if (_mech == null) { AtlasPlugin.Logger.LogError($"[Atlas/Task] unknown kind '{kind}'"); Close(); return; }
            gameObject.layer = 5;
            _mech.Build(transform, ctx);
            _close = AtlasTaskKit.Sprite(transform, "task_close.png", 100f, new Vector2(-3.3f, 2.3f), 20);
            _opened = Time.realtimeSinceStartup;
            AtlasPlugin.Logger.LogInfo($"[Atlas/Task] {kind} opened (step {(MyNormTask != null ? MyNormTask.taskStep : -1)})");
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Task] start failed: {e}"); }
    }

    /// <summary>Baustein je Task-Art und Schritt (mehrstufige Tasks zeigen je Schritt ein anderes Minispiel).</summary>
    private static IAtlasMechanic Create(string kind, int step) => kind switch
    {
        "dust" => new DustMechanic(),
        "pump" => new PumpMechanic(),
        "till" => new TillMechanic(),
        "bins" => step == 0 ? new SortMechanic(false) : new HoldLeverMechanic(false),
        "compost" => step == 0 ? new SortMechanic(true) : new HoldLeverMechanic(true),
        "fuse" => step == 0 ? new FuseMechanic() : new SwitchMechanic(false),
        "route" => step == 0 ? new RouteMechanic() : new SwitchMechanic(true),
        "light" => new LightMechanic(),
        "tomb" => new TombMechanic(),
        "projector" => new ProjectorMechanic(),
        "hiero" => new HieroMechanic(),
        "vault" => new VaultMechanic(),
        "valves" => new ValvesMechanic(),
        "splice" => new SpliceMechanic(),
        "binoculars" => new BinocularsMechanic(),
        "climate" => new ClimateMechanic(),
        "flywheel" => new AlignMechanic("task_steel_panel.png", "task_flywheel.png", "FLYWHEEL"),
        "saw" => step == 0 ? new AlignMechanic("task_wald_panel.png", "task_sawblade.png", "SAW BLADE")
                           : new AlignMechanic("task_wald_panel.png", "task_propeller.png", "OUTBOARD"),
        "generator" => new GeneratorMechanic(),
        "steam" => new FillMechanic(step % 2 == 1, false),
        "refuel" => new FillMechanic(step % 2 == 1, true),
        "constellation" => new ConstellationMechanic(),
        "patrol" => new PatrolMechanic(),
        "moths" => new TargetsMechanic(false),
        "census" => new TargetsMechanic(true),
        "pigment" => new SampleMechanic(false),
        "water" => new SampleMechanic(true),
        "audio" => new TransferMechanic(false),
        "trailcam" => new TransferMechanic(true),
        "timecard" => new TimecardMechanic(),
        "lanterns" => new LanternsMechanic(),
        "grate" => new SortMechanic(true, grate: true),
        "alarm" => new HoldTrackMechanic(false),
        "fire" => new HoldTrackMechanic(true),
        "climatefail" => new KeypadMechanic(),
        "waterworks" => new ValvePlanMechanic(),
        "fusebox" => new SwitchesMechanic(false),
        "breakers" => new SwitchesMechanic(true),
        "cctv" => new TuneMechanic(false),
        "antenna" => new TuneMechanic(true),
        "sawlog" => new SawMechanic(),
        "rexmusic" => new MusicBoxMechanic(),
        "rexlight" => new NightLightMechanic(),
        // Moonlight Carnival: bekannte Bausteine, eigene Grafik und Texte ueber AtlasMapDef.TaskArt/TaskText
        "lightstring" => new SpliceMechanic(),
        "motors" => new ClimateMechanic(),
        "parade" => new PatrolMechanic(),
        "candy" => new DustMechanic(),
        "ridepower" => step == 0 ? new RouteMechanic() : new SwitchMechanic(false),
        "spotlights" => new VaultMechanic(),
        "balloon" => new BinocularsMechanic(),
        "ridekeys" => new HieroMechanic(),
        "photos" => new TransferMechanic(true),
        "ridemotors" => step == 0 ? new AlignMechanic("task_park_panel.png", "task_park_gear.png", "CAROUSEL")
                                  : new AlignMechanic("task_park_panel.png", "task_park_bumper.png", "BUMPER CARS"),
        "gallery" => new TargetsMechanic(true),
        "popcorn" => step == 0 ? new SortMechanic(false, park: true) : new HoldLeverMechanic(false),
        "ridefuel" => new FillMechanic(step % 2 == 1, true),
        "allergen" => new SampleMechanic(false),
        "brakes" => new PumpMechanic(),
        "brakefail" => new HoldTrackMechanic(false),
        "ammonia" => new ValvePlanMechanic(),
        "blackout" => new SwitchesMechanic(false),
        "feedback" => new TuneMechanic(true),
        _ => null,
    };

    private Vector2 _lastMouse;

    public void Update()
    {
        if (_mech == null || amClosing != CloseState.None) return;
        if (_done)
        {
            // Nach "fertig" bis zum Schliessen weiterlaufen lassen, ohne Eingabe: sonst froren
            // laufende Schlussanimationen ein (User 24.09.: "die letzte Animation wird nicht
            // abgespielt", z. B. die letzte Motte auf dem Weg ins Glas).
            try { _mech.Tick(Time.deltaTime, _lastMouse, false, false); } catch { }
            return;
        }
        try
        {
            float dt = Time.deltaTime;
            Vector2 mouse; bool down;
            if (DiagAuto) _mech.Simulate(dt, out mouse, out down);
            else
            {
                var cam = Camera.main;
                var wp = cam != null ? cam.ScreenToWorldPoint(Input.mousePosition) : Vector3.zero;
                mouse = transform.InverseTransformPoint(wp);
                down = Input.GetMouseButton(0);
            }
            bool pressed = down && !_wasDown;
            _wasDown = down;
            _lastMouse = mouse;

            if (pressed && _close != null && Vector2.Distance(mouse, _close.transform.localPosition) < 0.35f)
            {
                Close();
                return;
            }
            _mech.Tick(dt, mouse, down, pressed);
            DiagProgress = _mech.Progress;
            if (_mech.Leave)
            {
                _done = true;
                AtlasPlugin.Logger.LogInfo($"[Atlas/Task] {_mech.Name} left without a step ({Time.realtimeSinceStartup - _opened:F1}s)");
                StartCoroutine(CoStartClose(0.6f));
                return;
            }
            if (_mech.Done)
            {
                _done = true;
                AtlasPlugin.Logger.LogInfo($"[Atlas/Task] {_mech.Name} step {(MyNormTask != null ? MyNormTask.taskStep : -1)} {Time.realtimeSinceStartup - _opened:F1}s");
                if (AtlasWorld.IsWorldRepair(_mech.Name)) AtlasWorld.RepairDone(_mech.Name);
                else if (DiagNoComplete) AtlasPlugin.Logger.LogInfo("[Atlas/Task] diag: no matching task, nothing completed");
                else if (MyNormTask != null) CompleteStep(MyNormTask);
                StartCoroutine(CoStartClose(0.9f));
            }
        }
        catch (Exception e) { AtlasPlugin.Logger.LogError($"[Atlas/Task] update failed: {e}"); _done = true; }
    }

    /// <summary>
    /// Ein Konsolen-Schritt. Manche Skeld-Tasks zaehlen intern Unterschritte, die der Spieler nie
    /// sieht (Clean O2 Filter: ein Schritt pro Blatt; Test 23.09.: das Minispiel schloss, der Task
    /// blieb bei 1/2/3 stehen). Ohne sichtbaren Zaehler (ShowTaskStep = false) schliesst das eigene
    /// Minispiel deshalb alle Reststufen ab; mit Zaehler ("Divert Power (0/2)") genau eine.
    /// </summary>
    // Tasks, deren sichtbarer Zaehler Treffer IM Minispiel zaehlt statt Konsolenbesuche: Clear
    // Asteroids ist im Original "(0/20)", ein Schritt pro Asteroid. Das eigene Minispiel ist der ganze
    // Task (User 24.09.: Motten zum fuenften Mal, Log "ClearAsteroids: step 0 -> 1 of 20").
    private static readonly HashSet<TaskTypes> WholeTaskInOneGame = new() { TaskTypes.ClearAsteroids };

    private static void CompleteStep(NormalPlayerTask task)
    {
        int before = task.taskStep, max = task.MaxStep;
        if (task.ShowTaskStep && !WholeTaskInOneGame.Contains(task.TaskType)) task.NextStep();
        else for (int guard = 0; guard < 64 && !task.IsComplete; guard++) task.NextStep();
        AtlasPlugin.Logger.LogInfo($"[Atlas/Task] {task.TaskType}: step {before} -> {task.taskStep} of {max} (showStep={task.ShowTaskStep}, complete={task.IsComplete})");
    }

    public void OnDestroy()
    {
        _mech?.Dispose();
        AtlasTaskKit.Kind = null;
        if (_loggerHandle != 0)
        {
            try { Il2CppInterop.Runtime.IL2CPP.il2cpp_gchandle_free(_loggerHandle); } catch { }
            _loggerHandle = 0;
        }
    }
}

/// <summary>Eine Minispiel-Mechanik (Baustein).</summary>
internal interface IAtlasMechanic
{
    string Name { get; }
    /// <summary>Schliessen OHNE Schritt (z. B. Probe gestartet, Wartezeit laeuft).</summary>
    bool Leave => false;
    float Progress { get; }
    bool Done { get; }
    void Build(Transform root, AtlasTaskCtx ctx);
    void Tick(float dt, Vector2 mouse, bool down, bool pressed);
    /// <summary>Spielt sich selbst: liefert die Eingabe dieses Frames.</summary>
    void Simulate(float dt, out Vector2 mouse, out bool down);
    void Dispose();
}

internal static class AtlasTaskKit
{
    /// <summary>Baustein-Art des offenen Minispiels ("gallery"); es ist immer nur eins offen.</summary>
    internal static string Kind;

    /// <summary>Grafikdatei dieser Karte (AtlasMapDef.TaskArt): erst "art:datei", dann "datei".</summary>
    public static string Art(string file) => Lookup(AtlasMuseumBuilder.D?.TaskArt, file);

    /// <summary>Minispiel-Text dieser Karte (AtlasMapDef.TaskText), gleiche Regel wie Art.</summary>
    public static string T(string text) => Lookup(AtlasMuseumBuilder.D?.TaskText, text);

    private static string Lookup(Dictionary<string, string> map, string key)
    {
        if (map == null || map.Count == 0 || string.IsNullOrEmpty(key) || !AtlasMuseumBuilder.Active) return key;
        if (Kind != null && map.TryGetValue(Kind + ":" + key, out var own)) return own;
        return map.TryGetValue(key, out var all) ? all : key;
    }

    public static SpriteRenderer Sprite(Transform parent, string file, float ppu, Vector2 pos, int order, Vector2? pivot = null)
    {
        var go = new GameObject(file) { layer = 5 };
        go.transform.SetParent(parent, false);
        go.transform.localPosition = new Vector3(pos.x, pos.y, -order * 0.01f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = AtlasAssets.TaskSprite(file, ppu, pivot ?? new Vector2(0.5f, 0.5f));
        sr.sortingOrder = order;
        return sr;
    }
}

// ============================================================ Rubbeln: Dust the Skeleton

internal sealed class DustMechanic : IAtlasMechanic
{
    public string Name => "dust";
    const int W = 280, H = 150;              // Staubschicht in Pixeln
    const float PPU = 50f;                   // -> 5,6 x 3,0 Einheiten
    const float Radius = 22f;                // Pinsel in Pixeln
    const float Goal = 0.95f;
    static readonly Vector2 Center = new(0f, -0.1f);

    private Texture2D _tex;
    private Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<Color32> _pix;
    private int _dusty, _total;
    private bool _dirty;
    private Vector2? _last;
    private SpriteRenderer _dino, _brush;
    public float Progress => _total == 0 ? 1f : 1f - (float)_dusty / _total;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_museum_panel.png", 100f, Vector2.zero, 0);
        _dino = AtlasTaskKit.Sprite(root, "task_museum_dino.png", 100f, Center, 1);
        _dino.color = new Color(0.86f, 0.86f, 0.86f);
        _tex = AtlasAssets.TaskTextureCopy("task_museum_dust.png");
        _tex.filterMode = FilterMode.Bilinear;
        _tex.wrapMode = TextureWrapMode.Clamp;
        _pix = _tex.GetPixels32();
        for (int i = 0; i < _pix.Length; i++) if (_pix[i].a > 60) _total++;
        _dusty = _total;
        var go = new GameObject("dust") { layer = 5 };
        go.transform.SetParent(root, false);
        go.transform.localPosition = new Vector3(Center.x, Center.y, -0.02f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = Sprite.Create(_tex, new Rect(0, 0, W, H), new Vector2(0.5f, 0.5f), PPU);
        sr.sortingOrder = 2;
        _brush = AtlasTaskKit.Sprite(root, "task_brush.png", 100f, Vector2.zero, 10, new Vector2(0.3f, 0.27f));
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        var bt = _brush.transform;
        bt.localPosition = new Vector3(mouse.x, mouse.y, bt.localPosition.z);
        bt.localEulerAngles = new Vector3(0, 0, down ? -12f + Mathf.Sin(Time.time * 30f) * 6f : 0f);
        if (Done) return;
        if (down)
        {
            // Lokal -> Pixel der Staubschicht (Pixel 0,0 = links unten)
            var p = new Vector2((mouse.x - Center.x) * PPU + W / 2f, (mouse.y - Center.y) * PPU + H / 2f);
            if (_last.HasValue)
            {
                var a = _last.Value;
                float len = Vector2.Distance(a, p);
                int n = Mathf.Max(1, Mathf.CeilToInt(len / (Radius * 0.4f)));
                for (int i = 1; i <= n; i++) Stamp(Vector2.Lerp(a, p, i / (float)n));
            }
            else Stamp(p);
            _last = p;
        }
        else _last = null;
        if (_dirty) { _tex.SetPixels32(_pix); _tex.Apply(false); _dirty = false; }
        if (Progress >= Goal)
        {
            Done = true;
            _dino.color = Color.white;                                  // die Knochen glaenzen auf
            _dino.transform.localScale = Vector3.one * 1.03f;
        }
    }

    private void Stamp(Vector2 c)
    {
        int x0 = Mathf.Max(0, (int)(c.x - Radius)), x1 = Mathf.Min(W - 1, (int)(c.x + Radius));
        int y0 = Mathf.Max(0, (int)(c.y - Radius)), y1 = Mathf.Min(H - 1, (int)(c.y + Radius));
        float r2 = Radius * Radius;
        for (int y = y0; y <= y1; y++)
            for (int x = x0; x <= x1; x++)
            {
                float dx = x - c.x, dy = y - c.y, d2 = dx * dx + dy * dy;
                if (d2 > r2) continue;
                int i = y * W + x;
                var px = _pix[i];
                if (px.a == 0) continue;
                float f = Mathf.Sqrt(d2) / Radius;                      // weicher Rand
                byte na = f < 0.65f ? (byte)0 : (byte)Mathf.Min(px.a, px.a * (f - 0.65f) / 0.35f);
                if (na == px.a) continue;
                if (px.a > 60 && na <= 60) _dusty--;
                px.a = na;
                _pix[i] = px;
                _dirty = true;
            }
    }

    // Autotest: Zickzack ueber die Schicht, wie ein Spieler, der Bahn um Bahn wischt
    private float _st;
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float w = W / PPU, h = H / PPU;
        float lanes = 6f, speed = 1.25f;                       // Bahnen pro Durchgang, Bahnen pro Sekunde
        float t = _st * speed;
        int lane = (int)t % (int)lanes;
        float u = t - Mathf.Floor(t);
        float x = (lane % 2 == 0 ? u : 1f - u) * (w + 0.4f) - (w + 0.4f) / 2f;
        float y = h / 2f - (lane + 0.5f) * h / lanes + ((int)(t / lanes) % 2) * h / (lanes * 2f);
        mouse = new Vector2(x, y) + Center;
        down = true;
    }

    public void Dispose()
    {
        if (_tex != null) Object.Destroy(_tex);
    }
}

// ============================================================ Takt: Prime the Pump

internal sealed class PumpMechanic : IAtlasMechanic
{
    public string Name => "pump";
    const int Stages = 3;
    const float Gain = 1f / 6f;                 // sechs saubere Zuege pro Stufe
    const float TooFast = 0.42f, TooSlow = 1.05f, Beat = 0.7f;
    const float Up = 22f, DownA = -28f;
    static readonly Vector2 Pivot = new(-1.4f, 1.42f);
    static readonly Vector2 GaugeC = new(2.3f, 1.1f);
    const float Lever = 2.66f;

    private Transform _handle, _needle;
    private SpriteRenderer _gauge, _water, _beat;
    private readonly List<SpriteRenderer> _lamps = new();
    private Sprite _lampOn;
    private float _angle = Up, _p, _shownP, _sinceStroke = 99f, _red, _waterA, _beatT;
    private bool _grab, _armed = true, _first = true;
    private int _stage;
    public float Progress => (_stage + _p) / Stages;
    public bool Done { get; private set; }

    public void Build(Transform root, AtlasTaskCtx ctx)
    {
        AtlasTaskKit.Sprite(root, "task_wald_panel.png", 100f, Vector2.zero, 0);
        AtlasTaskKit.Sprite(root, "task_pump_body.png", 100f, new Vector2(-1.4f, -0.1f), 2);
        _water = AtlasTaskKit.Sprite(root, "task_water.png", 100f, new Vector2(-0.24f, 0.05f), 1, new Vector2(10f / 140f, 1f - 12f / 180f));
        _water.color = new Color(1, 1, 1, 0);
        _handle = AtlasTaskKit.Sprite(root, "task_pump_handle.png", 100f, Pivot, 3, new Vector2(24f / 320f, 0.5f)).transform;
        _gauge = AtlasTaskKit.Sprite(root, "task_gauge.png", 100f, GaugeC, 2);
        _gauge.transform.localScale = Vector3.one * 0.82f;              // frei vom Hebel im tiefsten Punkt
        _needle = AtlasTaskKit.Sprite(root, "task_needle.png", 100f, GaugeC, 3, new Vector2(8f / 120f, 0.5f)).transform;
        _needle.localScale = Vector3.one * 0.82f;
        _lampOn = AtlasAssets.TaskSprite("task_lamp_on.png", 100f, new Vector2(0.5f, 0.5f));
        for (int i = 0; i < Stages; i++)
            _lamps.Add(AtlasTaskKit.Sprite(root, "task_lamp_off.png", 100f, new Vector2(1.0f + i * 0.8f, -1.65f), 2));
        _beat = AtlasTaskKit.Sprite(root, "task_lamp_on.png", 100f, new Vector2(0.2f, -1.65f), 2);
        _beat.transform.localScale = Vector3.one * 0.7f;
        Apply();
    }

    private Vector2 Tip(float angle)
    {
        float a = angle * Mathf.Deg2Rad;
        return Pivot + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Lever;
    }

    public void Tick(float dt, Vector2 mouse, bool down, bool pressed)
    {
        _sinceStroke += dt;
        if (pressed)
        {
            // den Hebel irgendwo zwischen Mitte und Griff fassen
            var tip = Tip(_angle);
            var mid = Vector2.Lerp(Pivot, tip, 0.35f);
            _grab = DistToSegment(mouse, mid, tip) < 0.45f;
        }
        if (!down) _grab = false;

        if (_grab)
        {
            var d = mouse - Pivot;
            float target = Mathf.Clamp(Mathf.Atan2(d.y, Mathf.Max(0.3f, d.x)) * Mathf.Rad2Deg, DownA, Up);
            _angle = Mathf.MoveTowards(_angle, target, 600f * dt);
        }
        else _angle = Mathf.MoveTowards(_angle, Up, 160f * dt);          // Feder zieht hoch

        if (_angle >= Up - 6f) _armed = true;
        if (_armed && _angle <= DownA + 3f) { _armed = false; Stroke(); }

        // ohne Zuege faellt der Druck langsam
        if (_sinceStroke > 1.3f) _p = Mathf.Max(0f, _p - 0.1f * dt);
        _red = Mathf.Max(0f, _red - dt * 2.5f);
        _waterA = Mathf.Max(0f, _waterA - dt * 2.2f);
        _beatT += dt;
        _shownP = Mathf.MoveTowards(_shownP, _p, dt * 1.6f);
        Apply();
    }

    private void Stroke()
    {
        float iv = _sinceStroke;
        _sinceStroke = 0f;
        _beatT = 0f;                                                     // Taktlampe folgt dem Spieler
        if (_first || iv > TooSlow) { _first = false; _p += Gain * 0.5f; _waterA = 0.35f; }
        else if (iv < TooFast) { _p = Mathf.Max(0f, _p - 0.18f); _red = 1f; }   // Ueberdruck
        else { _p += Gain; _waterA = 0.8f; }
        if (_p >= 1f)
        {
            _lamps[_stage].sprite = _lampOn;
            _stage++;
            _p = 0f; _shownP = 0f; _first = true; _waterA = 1.4f;
            if (_stage >= Stages) Done = true;
        }
    }

    private void Apply()
    {
        _handle.localEulerAngles = new Vector3(0, 0, _angle);
        float shake = _red > 0f ? Mathf.Sin(Time.time * 70f) * 6f * _red : 0f;
        _needle.localEulerAngles = new Vector3(0, 0, 210f - _shownP * 240f + shake);
        _gauge.color = Color.Lerp(Color.white, new Color(1f, 0.55f, 0.5f), _red);
        _water.color = new Color(1, 1, 1, Mathf.Clamp01(_waterA));
        // Taktlampe: blinkt im idealen Takt nach dem letzten Zug
        float ph = (_beatT % Beat) / Beat;
        _beat.color = new Color(1f, 0.75f, 0.3f, ph < 0.18f ? 1f : 0.25f);
    }

    private static float DistToSegment(Vector2 p, Vector2 a, Vector2 b)
    {
        var ab = b - a;
        float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-5f, ab.sqrMagnitude));
        return Vector2.Distance(p, a + ab * t);
    }

    // Autotest: Griff fassen, in 0,25 s runter, loslassen, im Takt von 0,7 s wiederholen
    private float _st;
    public void Simulate(float dt, out Vector2 mouse, out bool down)
    {
        _st += dt;
        float ph = _st % Beat;
        var grip = Tip(Up);
        if (ph < 0.3f)
        {
            float k = Mathf.Clamp01(ph / 0.25f);
            float a = Mathf.Lerp(Up, DownA - 8f, k);
            mouse = Tip(a) - (Tip(a) - Pivot).normalized * 0.2f;
            down = ph > 0.02f;
        }
        else { mouse = grip; down = false; }
    }

    public void Dispose() { }
}
