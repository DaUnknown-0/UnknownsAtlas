// Kleine Engine-Doubles fuer den Offline-Test des unveraenderten Sound-Quellcodes.
using UnityEngine;

namespace UnityEngine
{
    public class Object
    {
        public bool Destroyed;
        public static void Destroy(Object o) => o.Destroyed = true;
    }
    [Flags] public enum HideFlags { HideAndDontSave = 1 }
    public class AudioClip : Object
    {
        public string name;
        public HideFlags hideFlags;
        public int Frames;
        public static readonly List<AudioClip> Created = new();
        public static AudioClip Create(string name, int frames, int channels, int rate, bool stream)
        {
            var c = new AudioClip { name = name, Frames = frames };
            Created.Add(c);
            return c;
        }
    }
    public class AudioSource
    {
        public AudioClip clip;
        public float volume, spatialBlend, panStereo, dopplerLevel;
        public int priority;
        public bool isPlaying = true;
        public void Stop() => isPlaying = false;
    }
    public struct Vector2
    {
        public float x, y;
        public Vector2(float x, float y) { this.x = x; this.y = y; }
        public static Vector2 zero => new(0, 0);
        public float sqrMagnitude => x * x + y * y;
        public static float Dot(Vector2 a, Vector2 b) => a.x * b.x + a.y * b.y;
        public static float Distance(Vector2 a, Vector2 b) => MathF.Sqrt((a - b).sqrMagnitude);
        public static Vector2 operator +(Vector2 a, Vector2 b) => new(a.x + b.x, a.y + b.y);
        public static Vector2 operator -(Vector2 a, Vector2 b) => new(a.x - b.x, a.y - b.y);
        public static Vector2 operator *(Vector2 a, float b) => new(a.x * b, a.y * b);
        public static Vector2 operator /(Vector2 a, float b) => new(a.x / b, a.y / b);
    }
    public static class Mathf
    {
        public static float Min(float a, float b) => MathF.Min(a, b);
        public static float Max(float a, float b) => MathF.Max(a, b);
        public static float Clamp(float x, float lo, float hi) => Math.Clamp(x, lo, hi);
        public static float Clamp01(float x) => Clamp(x, 0, 1);
        public static float MoveTowards(float x, float y, float d) => x + Math.Clamp(y - x, -d, d);
    }
}
namespace BepInEx.Configuration
{
    public sealed class ConfigEntry<T> { public T Value; }
    public sealed class ConfigDescription { public ConfigDescription(string text, object range) { } }
    public sealed class AcceptableValueRange<T> { public AcceptableValueRange(T min, T max) { } }
    public sealed class ConfigFile
    {
        public readonly Dictionary<string, object> Entries = new();
        public ConfigEntry<T> Bind<T>(string section, string key, T value, object description)
        {
            var entry = new ConfigEntry<T> { Value = value };
            Entries[key] = entry;
            return entry;
        }
    }
}
namespace HarmonyLib
{
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public sealed class HarmonyPatch : Attribute { public HarmonyPatch() { } public HarmonyPatch(Type t, string m) { } }
    public sealed class HarmonyPrefix : Attribute { }
    public sealed class HarmonyPostfix : Attribute { }
    public sealed class HarmonyPriority : Attribute { public HarmonyPriority(int value) { } }
    public static class Priority { public const int Last = 0; }
}
namespace InnerNet { public class InnerNetClient { public enum GameStates { NotJoined, Joined, Started, Ended } } }
public enum NetworkModes { LocalGame, FreePlay }
public sealed class AmongUsClient
{
    public static AmongUsClient Instance = new();
    public NetworkModes NetworkMode;
    public InnerNet.InnerNetClient.GameStates GameState = InnerNet.InnerNetClient.GameStates.Started;
    public void OnGameEnd() { }
}
public sealed class PlayerControl
{
    public static PlayerControl LocalPlayer = new();
    public object Data = new();
    public Vector2 Position;
    public Vector2 GetTruePosition() => Position;
}
public sealed class MeetingHud { public static MeetingHud Instance; public void Start() { } }
public sealed class ExileController { public static ExileController Instance; }
public sealed class HudManager { public void Update() { } }
public sealed class SoundManager
{
    public static SoundManager Instance = new();
    public readonly object SfxChannel = new();
    public readonly Dictionary<AudioClip, AudioSource> Active = new();
    public int PeakActive, DuplicatePlays;
    public AudioSource PlaySound(AudioClip clip, bool loop, float volume, object channel)
    {
        if (Active.ContainsKey(clip)) { DuplicatePlays++; throw new Exception("Doppelter Clip"); }
        if (channel != SfxChannel) throw new Exception("Falscher Mixerkanal");
        var s = new AudioSource { clip = clip, volume = volume };
        Active[clip] = s;
        PeakActive = Math.Max(PeakActive, Active.Count);
        return s;
    }
    public void StopSound(AudioClip clip) => Active.Remove(clip);
}
namespace UnknownsAtlas
{
    public static class AtlasPlugin
    {
        public static readonly Log Logger = new();
        public class Log { public void LogInfo(string text) { } public void LogWarning(string text) => Console.WriteLine(text); }
    }
    public static class AtlasAmberhive
    {
        public const string Key = "amberhive", Ns = "UnknownsAtlas.Maps.amberhive";
    }
    public class HiveData
    {
        public Vector2 PitCenter;
        public bool HasChute;
        public List<Vector2[]> FloodZones = new();
    }
    public class AtlasMapDef
    {
        public string Key = "amberhive";
        public Vector2 EmergencyButton;
        public (string Key, Vector2[] Area)[] Rooms;
        public (string Kind, float WorldX, float BaseY, float FootX0, float FootX1)[] Props;
    }
    public static class AtlasMuseumBuilder { public static bool Active = true; public static AtlasMapDef D; }
    public static class ClipFill
    {
        public static void SetData(AudioClip clip, float[] samples, int channels)
        {
            if (samples.Length / channels != clip.Frames || samples.Any(x => !float.IsFinite(x)))
                throw new Exception("Ungueltige Clipdaten");
        }
    }
}
