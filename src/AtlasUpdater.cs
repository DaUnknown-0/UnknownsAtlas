// Unknown's Atlas - Copyright (C) 2026 DaUnknown-0
// Licensed under GPL-3.0-or-later. See LICENSE for details.

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Text.Json;
using System.Text.Json.Serialization;
using BepInEx;
using BepInEx.Unity.IL2CPP.Utils;
using Il2CppInterop.Runtime.Attributes;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using AmongUs.Data;
using Assets.InnerNet;
using Twitch;

namespace UnknownsAtlas {
    // Self-updater that checks the GitHub releases of this repo and offers an in-game update
    // button on the main menu. Mirrors TOR's own ModUpdater flow (and this project family's other
    // mods' updaters, e.g. HostFixPlugin.HostFixUpdater) but uses its own GithubRelease DTOs so
    // this plugin needs no compile-time reference to TheOtherRoles.
    public class AtlasUpdater : MonoBehaviour {
        public const string RepositoryOwner = "DaUnknown-0";
        public const string RepositoryName = "UnknownsAtlas";
        public const string PluginAssetName = "UnknownsAtlas.dll";

        public static AtlasUpdater Instance { get; private set; }

        public AtlasUpdater(IntPtr ptr) : base(ptr) { }

        private bool _busy;
        private bool _showPopUp = true;
        public List<GithubRelease> Releases;

        // Download state for the Mod Manager. 0 = idle, 1 = downloading, 2 = success (restart
        // required), 3 = error. Lives on the instance so the Mod Manager UI can poll it across
        // being closed and reopened.
        private int _updateState;
        private float _updateProgress;

        // True once the GitHub release check has finished (success or failure). Polled by the Mod
        // Manager so it only shows the collected update announcement after every mod's check.
        private bool _checkCompleted;

        public void Awake() {
            if (Instance) Destroy(Instance);
            Instance = this;
            // AUDIT-2026-08-23 (L-21): guarded. A .old left locked by a virus scanner, or a plugin
            // folder this process cannot enumerate, used to throw straight out of Awake - which
            // aborts the component's initialisation, so the updater silently did not exist for the
            // rest of the session. Cleaning up a leftover file is not worth that.
            try {
                foreach (var file in Directory.GetFiles(Paths.PluginPath, PluginAssetName + ".old")) {
                    try { File.Delete(file); } catch { }
                }
            } catch (Exception e) {
                AtlasPlugin.Logger?.LogWarning($"[Atlas] Could not clean up old plugin files: {e.Message}");
            }
        }

        private void Start() {
            if (_busy) return;
            this.StartCoroutine(CoCheckForUpdate());
            SceneManager.add_sceneLoaded((Action<Scene, LoadSceneMode>)OnSceneLoaded);
        }

        [HideFromIl2Cpp]
        public void StartDownloadRelease(GithubRelease release, bool managerMode = false) {
            if (_busy) return;
            this.StartCoroutine(CoDownloadRelease(release, managerMode));
        }

        // Re-check triggered by the Mod Manager on open (throttled to 1/minute by
        // ModManagerRegistry.MaybeCheckForUpdates).
        [HideFromIl2Cpp]
        public void TriggerCheckFromManager() {
            if (_busy) return;          // a check/download is already running - don't stack another
            _checkCompleted = false;    // lets the UI/announcement notice the re-check in flight
            this.StartCoroutine(CoCheckForUpdate());
        }

        // Reflection/direct-callable getters for the Mod Manager UI.
        [HideFromIl2Cpp]
        public int GetUpdateState() => _updateState;

        [HideFromIl2Cpp]
        public float GetUpdateProgress() => _updateProgress;

        [HideFromIl2Cpp]
        public bool GetCheckCompleted() => _checkCompleted;

        // True when the release list was successfully fetched (Mod Manager shows "check unavailable"
        // instead of a misleading "up to date" when the GitHub call failed/rate-limited).
        [HideFromIl2Cpp]
        public bool ReleasesLoaded() => Releases != null && Releases.Count > 0;

        [HideFromIl2Cpp]
        private IEnumerator CoCheckForUpdate() {
            _busy = true;
            var www = new UnityWebRequest();
            www.SetMethod(UnityWebRequest.UnityWebRequestMethod.Get);
            www.SetUrl($"https://api.github.com/repos/{RepositoryOwner}/{RepositoryName}/releases");
            // GitHub rejects UA-less clients - set a distinct one.
            www.SetRequestHeader("User-Agent", $"UnknownsAtlas/{AtlasPlugin.VersionString}");
            www.downloadHandler = new DownloadHandlerBuffer();
            var operation = www.SendWebRequest();

            while (!operation.isDone) {
                yield return new WaitForEndOfFrame();
            }

            if (www.isNetworkError || www.isHttpError) {
                www.downloadHandler.Dispose();
                www.Dispose();
                _checkCompleted = true;
                _busy = false;
                yield break;
            }

            // GitHub returns a JSON OBJECT instead of an array on rate-limit (403) or error;
            // Deserialize/Sort must not kill the coroutine, or `_busy` would stay true for the
            // whole session and block every further check/download. try/catch is fine here since
            // this block contains no yield.
            try {
                Releases = JsonSerializer.Deserialize<List<GithubRelease>>(www.downloadHandler.text);
                if (Releases != null) Releases.Sort(SortReleases);
            } catch (Exception ex) {
                AtlasPlugin.Logger?.LogWarning($"[Atlas] update check: failed to parse GitHub releases ({ex.Message}). Treating as 'no update'.");
                // Leave Releases as-is (possibly null) - treated as "no update" everywhere.
            } finally {
                www.downloadHandler.Dispose();
                www.Dispose();
                _checkCompleted = true;
                _busy = false;
            }
        }

        [HideFromIl2Cpp]
        private IEnumerator CoDownloadRelease(GithubRelease release, bool managerMode) {
            _busy = true;
            _updateState = 1;
            _updateProgress = 0f;

            // No Among Us TwitchPopup in manager mode; the Mod Manager shows progress/state itself
            // via GetUpdateState()/GetUpdateProgress(). TwitchManager.Instance or its TwitchPopup
            // can be null (main menu not fully initialised yet, or a build where the field is
            // simply not set up) - fall back to working popup-less, same as managerMode, rather
            // than NRE-ing out of the coroutine and leaving `_busy` stuck true for the session.
            GenericPopup popup = null;
            GameObject button = null;
            if (!managerMode) {
                var popupTemplate = TwitchManager.Instance != null ? TwitchManager.Instance.TwitchPopup : null;
                if (popupTemplate != null) {
                    popup = Instantiate(popupTemplate);
                    popup.TextAreaTMP.fontSize *= 0.7f;
                    popup.TextAreaTMP.enableAutoSizing = false;

                    popup.Show();

                    button = popup.transform.GetChild(2).gameObject;
                    button.SetActive(false);
                    popup.TextAreaTMP.text = "Updating Unknown's Atlas...";
                }
            }

            var asset = release.Assets.Find(FilterPluginAsset);
            if (asset == null) {
                AtlasPlugin.Logger?.LogError(
                    "[Atlas] Update failed: the release has no UnknownsAtlas.dll asset.");
                _updateState = 3;
                if (!managerMode && popup != null) {
                    popup.TextAreaTMP.text = "Update failed - no download found for this release.";
                    if (button != null) button.SetActive(true);
                }
                _busy = false;
                yield break;
            }

            var www = new UnityWebRequest();
            www.SetMethod(UnityWebRequest.UnityWebRequestMethod.Get);
            www.SetUrl(asset.DownloadUrl);
            www.downloadHandler = new DownloadHandlerBuffer();
            var operation = www.SendWebRequest();

            while (!operation.isDone) {
                _updateProgress = www.downloadProgress;
                if (!managerMode && popup != null) {
                    int stars = Mathf.CeilToInt(www.downloadProgress * 10);
                    string progress = "Downloading: " + new String((char)0x25A0, stars) + new String((char)0x25A1, 10 - stars);
                    popup.TextAreaTMP.text = progress;
                }
                yield return new WaitForEndOfFrame();
            }

            if (www.isNetworkError || www.isHttpError) {
                _updateState = 3;
                if (!managerMode && popup != null) {
                    popup.TextAreaTMP.text = "Update failed.";
                    if (button != null) button.SetActive(true);
                }
                _busy = false;
                yield break;
            }
            if (!managerMode && popup != null) {
                popup.TextAreaTMP.text = "Copying files...";
            }

            var filePath = Path.Combine(Paths.PluginPath, asset.Name);

            // Move the working DLL aside before writing the download, so a write failure below can
            // roll back to it instead of leaving the plugin folder without a usable Unknown's Atlas at all.
            // Guarded in its own try/catch: a locked .old (virus scanner, another process) must not
            // silently proceed and overwrite the still-working plugin file.
            var moved = false;
            try {
                if (File.Exists(filePath + ".old")) File.Delete(filePath + ".old");
                if (File.Exists(filePath)) File.Move(filePath, filePath + ".old");
                moved = true;
            } catch (Exception e) {
                AtlasPlugin.Logger?.LogError(
                    $"[Atlas] Update failed: could not move the old plugin file aside ({e.Message}).");
                _updateState = 3;
                if (!managerMode && popup != null) {
                    popup.TextAreaTMP.text = "Update failed - the previous version is still installed.";
                    if (button != null) button.SetActive(true);
                }
                _busy = false;
                yield break;
            }

            // Guarded like the move-aside above: a locked target file, a full disk or a permissions
            // problem must not throw straight out of the coroutine and leave `_busy` stuck true.
            Task persistTask = null;
            var hasError = false;
            try {
                persistTask = File.WriteAllBytesAsync(filePath, www.downloadHandler.data);
            } catch (Exception e) {
                AtlasPlugin.Logger?.LogError(
                    $"[Atlas] Update failed: could not write the downloaded file ({e.Message}).");
                hasError = true;
                persistTask = null;
            }
            while (persistTask != null && !persistTask.IsCompleted) {
                if (persistTask.Exception != null) {
                    hasError = true;
                    break;
                }

                yield return new WaitForEndOfFrame();
            }
            // AUDIT-2026-08-15: Task.IsCompleted is also true for Faulted/Canceled, so a task that
            // already failed by the very first check never enters the loop above and hasError stays
            // false. Re-check after the loop so a write failure is never reported as a successful
            // update.
            if (!hasError && persistTask != null && !persistTask.IsCompletedSuccessfully) hasError = true;

            www.downloadHandler.Dispose();
            www.Dispose();

            if (!hasError) {
                _updateState = 2;
                if (!managerMode && popup != null) {
                    popup.TextAreaTMP.text = "Update installed - restart Among Us to apply it.";
                }
            } else {
                // ROLL BACK (AUDIT-2026-08-23, L-24). The working DLL was moved aside to .old before
                // the download was written, so a failed write used to leave the plugin folder with
                // no usable Unknown's Atlas at all - a half-written file, or nothing - and the mod simply
                // stopped loading on the next start, with the only trace being an update popup that
                // said it had failed. Putting the old file back makes a failed update a no-op again.
                try {
                    if (moved && File.Exists(filePath + ".old")) {
                        if (File.Exists(filePath)) File.Delete(filePath);
                        File.Move(filePath + ".old", filePath);
                        AtlasPlugin.Logger?.LogWarning(
                            "[Atlas] Update failed - restored the previous plugin file.");
                    } else if (File.Exists(filePath)) {
                        // No .old to roll back to - delete the half-written new file rather than
                        // leave a corrupt/partial DLL in the plugin folder for the next launch.
                        try { File.Delete(filePath); } catch { }
                    }
                } catch (Exception e) {
                    AtlasPlugin.Logger?.LogError(
                        $"[Atlas] Update failed AND the previous plugin file could not be restored "
                        + $"({e.Message}). Reinstall Unknown's Atlas manually: the working DLL is next to it, "
                        + $"named \"{PluginAssetName}.old\".");
                }
                _updateState = 3;
                if (!managerMode && popup != null) {
                    popup.TextAreaTMP.text = "Update failed - the previous version is still installed.";
                }
            }
            if (!managerMode && button != null) button.SetActive(true);
            _busy = false;
        }

        [HideFromIl2Cpp]
        private static bool FilterPluginAsset(GithubAsset asset) {
            return asset.Name == PluginAssetName;
        }

        [HideFromIl2Cpp]
        private static int SortReleases(GithubRelease a, GithubRelease b) {
            if (a.IsNewer(b.Version)) return -1;
            if (b.IsNewer(a.Version)) return 1;
            return 0;
        }

        private void OnSceneLoaded(Scene scene, LoadSceneMode mode) {
            if (_busy || scene.name != "MainMenu" || Releases == null) return;

            // No own update button if the Mod Manager is enabled - it offers its own.
            if (IsModManagerEnabled()) {
                return;
            }

            var latestRelease = UpdateTarget();
            if (latestRelease == null || !IsActualUpdate(latestRelease.Version, AtlasPlugin.Version) || !latestRelease.Assets.Any(FilterPluginAsset))
                return;

            var template = GameObject.Find("ExitGameButton");
            if (!template) return;

            var button = Instantiate(template, null);
            // Stacked below this project family's other updaters' anchors to avoid overlap.
            button.GetComponent<AspectPosition>().anchorPoint = new Vector2(0.458f, 0.38f);

            PassiveButton passiveButton = button.GetComponent<PassiveButton>();
            passiveButton.OnClick = new Button.ButtonClickedEvent();
            passiveButton.OnClick.AddListener((Action)(() => {
                StartDownloadRelease(latestRelease);
                button.SetActive(false);
            }));

            var text = button.transform.GetComponentInChildren<TMPro.TMP_Text>();
            string t = "Update Unknown's Atlas";
            StartCoroutine(Effects.Lerp(0.1f, (Action<float>)(p => text.SetText(t))));
            passiveButton.OnMouseOut.AddListener((Action)(() => text.color = Color.cyan));
            passiveButton.OnMouseOver.AddListener((Action)(() => text.color = Color.white));
            text.color = Color.cyan;

            if (_showPopUp) {
                var announcement = $"Unknown's Atlas {latestRelease.Tag} is available.\n\n{latestRelease.Description}";
                var mgr = FindObjectOfType<MainMenuManager>(true);
                if (mgr != null)
                    mgr.StartCoroutine(CoShowAnnouncement(announcement, shortTitle: "Unknown's Atlas Update", date: latestRelease.PublishedAt));
            }
            _showPopUp = false;
        }

        [HideFromIl2Cpp]
        public IEnumerator CoShowAnnouncement(string announcement, bool show = true, string shortTitle = "Unknown's Atlas Update", string title = "", string date = "") {
            // Stagger behind this project family's other announcement popups.
            yield return new WaitForSeconds(1.8f);
            // Wait until no announcement popup is currently visible (up to 30 s).
            for (float t = 30f; t > 0f; t -= 0.25f) {
                if (UnityEngine.Object.FindObjectOfType<AnnouncementPopUp>() == null) break;
                yield return new WaitForSeconds(0.25f);
            }
            yield return new WaitForSeconds(0.2f);

            var mgr = FindObjectOfType<MainMenuManager>(true);
            var popUpTemplate = UnityEngine.Object.FindObjectOfType<AnnouncementPopUp>(true);
            // Without a template, Instantiate(null) would throw immediately; without a manager,
            // mgr.StartCoroutine(...) below would NRE.
            if (popUpTemplate == null || mgr == null) {
                yield break;
            }
            var popUp = UnityEngine.Object.Instantiate(popUpTemplate);

            popUp.gameObject.SetActive(true);

            Announcement nightfallAnnouncement = new() {
                Id = "nightfallAnnouncement",
                Language = 0,
                Number = 6972,
                Title = title == "" ? "Unknown's Atlas Update" : title,
                ShortTitle = shortTitle,
                SubTitle = "",
                PinState = false,
                Date = date == "" ? DateTime.Now.Date.ToString() : date,
                Text = announcement,
            };
            mgr.StartCoroutine(Effects.Lerp(0.1f, new Action<float>((p) => {
                if (p == 1) {
                    var backup = DataManager.Player.Announcements.allAnnouncements;
                    DataManager.Player.Announcements.allAnnouncements = new();
                    popUp.Init(false);
                    DataManager.Player.Announcements.SetAnnouncements(new Announcement[] { nightfallAnnouncement });
                    popUp.CreateAnnouncementList();
                    popUp.UpdateAnnouncementText(nightfallAnnouncement.Number);
                    popUp.visibleAnnouncements[0].PassiveButton.OnClick.RemoveAllListeners();
                    DataManager.Player.Announcements.allAnnouncements = backup;
                }
            })));
        }

        // Order of the tags as they are really cut: a test version vX.Y.Z.W FOLLOWS the stable vX.Y.Z
        // it builds on and comes before vX.Y.(Z+1), e.g. 1.4.9 < 1.4.9.1 < 1.4.9.2 < 1.4.10 (checked
        // against all tags of the six mods on 2026-09-25: never a test version before its stable). A
        // missing 4th part counts as 0. >0 means a is newer than b. Until 2026-09-25 a stable was taken
        // to supersede its test versions, which made "test versions ON" downgrade every mod whose newest
        // release was a stable (UC 1.2.7 -> 1.2.6.3) and hid 1.4.11.1 from a user on 1.4.11.
        [HideFromIl2Cpp]
        public static int SemCompare(Version a, Version b) {
            int c = new Version(a.Major, System.Math.Max(0, a.Minor), System.Math.Max(0, a.Build)).CompareTo(new Version(b.Major, System.Math.Max(0, b.Minor), System.Math.Max(0, b.Build)));
            if (c != 0) return c;
            return System.Math.Max(0, a.Revision).CompareTo(System.Math.Max(0, b.Revision));
        }

        // True when `target` is newer than the running build (see SemCompare for the order).
        [HideFromIl2Cpp]
        private static bool IsActualUpdate(Version target, Version current) => SemCompare(target, current) > 0;

        // Channel from the TAG FORMAT: stable = vX.Y.Z (Version.Revision <= 0), test = vX.Y.Z.W (>0).
        [HideFromIl2Cpp]
        public GithubRelease LatestInChannel(bool stable) {
            if (Releases == null) return null;
            foreach (var r in Releases) {
                if (r == null || r.Draft) continue;
                int rev;
                try { rev = r.Version.Revision; } catch { continue; }
                bool isTest = rev > 0;
                if (stable == isTest) continue;
                if (r.Assets != null && r.Assets.Any(FilterPluginAsset)) return r;
            }
            return null;
        }

        // True when switching to this channel would install a DIFFERENT version than the running one. The
        // Mod Manager counts and switches only these mods, so a mod that is already on its channel target
        // neither shows up in the confirmation nor holds up the switch.
        [HideFromIl2Cpp]
        public bool HasChannelRelease(bool stable) {
            var r = ChannelTarget(stable);
            return r != null && SemCompare(r.Version, AtlasPlugin.Version) != 0;
        }

        // The update target follows the shared "show test versions" toggle. OFF -> newest STABLE only.
        // ON -> the newest release of both channels (a stable newer than every test version wins).
        [HideFromIl2Cpp]
        public GithubRelease UpdateTarget() => ChannelTarget(!VersionDisplay.ShowTestVersions());

        // The release a channel points at. Stable: the newest stable. Test: the newest release of BOTH
        // channels, because a test channel must never fall back behind a newer stable.
        [HideFromIl2Cpp]
        public GithubRelease ChannelTarget(bool stable) {
            if (Releases == null) return null;
            var st = LatestInChannel(true);
            if (stable) return st;
            var pre = LatestInChannel(false);
            if (pre == null) return st;
            if (st == null) return pre;
            return SemCompare(pre.Version, st.Version) > 0 ? pre : st;
        }

        // Callback methods for ModManagerRegistry: checks whether an update is available.
        [HideFromIl2Cpp]
        public bool HasUpdate() {
            var t = UpdateTarget();
            return t != null && t.Assets.Any(FilterPluginAsset)
                && IsActualUpdate(t.Version, AtlasPlugin.Version);
        }

        // Raw release notes (GitHub `body`) of the target version (from the already-loaded JSON).
        [HideFromIl2Cpp]
        public string GetReleaseNotes() => UpdateTarget()?.Description ?? "";

        // Callback method for ModManagerRegistry: starts the update download.
        [HideFromIl2Cpp]
        public void TriggerUpdateFromManager() {
            var t = UpdateTarget();
            if (t != null && t.Assets.Any(FilterPluginAsset)
                && IsActualUpdate(t.Version, AtlasPlugin.Version))
                StartDownloadRelease(t, managerMode: true);
        }

        // Install the channel's target (see ChannelTarget), deliberately also as a downgrade (test -> stable).
        // Only downloads when it is REALLY a different version than the running build.
        [HideFromIl2Cpp]
        public void TriggerChannelSwitch(bool stable) {
            var r = ChannelTarget(stable);
            if (r != null && SemCompare(r.Version, AtlasPlugin.Version) != 0)
                StartDownloadRelease(r, managerMode: true);
        }

        // Checks via AppDomain whether the Mod Manager is enabled (no compile-time reference).
        private static bool IsModManagerEnabled() {
            try {
                var data = AppDomain.CurrentDomain.GetData("ModManager.IsEnabled");
                return data is bool b && b;
            } catch {
                return false;
            }
        }
    }

    // Minimal DTOs matching the GitHub Releases API JSON. Kept local so this plugin needs no
    // compile-time reference to TheOtherRoles.
    public class GithubRelease {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("tag_name")]
        public string Tag { get; set; }

        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("draft")]
        public bool Draft { get; set; }

        [JsonPropertyName("prerelease")]
        public bool Prerelease { get; set; }

        [JsonPropertyName("created_at")]
        public string CreatedAt { get; set; }

        [JsonPropertyName("published_at")]
        public string PublishedAt { get; set; }

        [JsonPropertyName("body")]
        public string Description { get; set; }

        [JsonPropertyName("assets")]
        public List<GithubAsset> Assets { get; set; }

        // TryParse, not Parse (AUDIT-2026-08-23, L-22). Tag is whatever text the GitHub API
        // returned, and a release tagged anything that is not "vX.Y[.Z[.W]]" - a name, a date, a
        // typo - made this property THROW. The sort comparison reads it for every pair, so one bad
        // tag anywhere in the feed took down the whole comparison and left the release list in
        // arbitrary order, from which "the newest release" is then picked. A tag that cannot be
        // read is treated as version zero instead: it sorts last, IsNewer is false for it, and it
        // is simply never offered as an update.
        public Version Version =>
            Version.TryParse((Tag ?? string.Empty).Replace("v", string.Empty), out var v) ? v : new Version(0, 0, 0, 0);

        public bool IsNewer(Version version) {
            return Version > version;
        }
    }

    public class GithubAsset {
        [JsonPropertyName("url")]
        public string Url { get; set; }

        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }

        [JsonPropertyName("browser_download_url")]
        public string DownloadUrl { get; set; }
    }
}
