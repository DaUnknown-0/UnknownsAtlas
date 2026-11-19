"""Freeplay-Test mit normalem Spielstart und Wiederherstellung im finally-Block."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import maptest_cfg

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
GAME = Path("C:/Users/moritz/Downloads/Among Us - 4.7.0/Among Us - 4.7.0")


def running():
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=True)
    return any(row and row[0].lower() == "among us.exe" for row in csv.reader(io.StringIO(result.stdout)))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main(args):
    mp, task, wait = args[0], args[1] if len(args) > 1 else "colliders", float(args[2]) if len(args) > 2 else 80
    if running():
        print("Among Us laeuft schon. Abbruch ohne Aenderungen.", flush=True)
        return 3
    out = Path(os.environ.get("OUTDIR", HERE / "_out" / "maptest")).resolve()
    audit = PROJECT.parent / "Audits/2026-11-17/atlas_merge"
    if not (out.is_relative_to(PROJECT) or out.is_relative_to(audit.resolve())):
        raise ValueError("OUTDIR muss im Projekt oder im freigegebenen Auditordner liegen")
    out.mkdir(parents=True, exist_ok=True)
    backup = out / f"_backup_{os.getpid()}"
    backup.mkdir()
    plugins, config = GAME / "BepInEx/plugins", GAME / "BepInEx/config"
    sources = {
        plugins / "UnknownsAtlas.dll": PROJECT / "bin/Release/net6.0/UnknownsAtlas.dll",
    }
    config_before = {p.relative_to(config).as_posix(): digest(p) for p in config.rglob("*") if p.is_file()}
    shutil.copytree(config, backup / "config")
    configs = []
    log = GAME / "BepInEx/LogOutput.log"
    originals = {path: digest(path) for path in [*sources, *configs, log]}
    for path, sha in originals.items():
        if sha is not None:
            shutil.copy2(path, backup / path.name)
    shots = GAME / "AtlasShots"
    asset_cache = GAME / "BepInEx/atlas-assets"
    appdata = Path(os.environ["USERPROFILE"]) / "AppData/LocalLow/Innersloth/Among Us"
    app_before = {p.name: digest(p) for p in appdata.iterdir() if p.is_file()}
    (backup / "appdata").mkdir()
    for name in app_before:
        shutil.copy2(appdata / name, backup / "appdata" / name)
    # Der lokale Download soll mit leerem Cache erfolgen; Nutzerdaten bleiben separat gesichert.
    cache_before = {p.relative_to(asset_cache).as_posix(): digest(p) for p in asset_cache.rglob("*") if p.is_file()}
    shots_before = {p.relative_to(shots).as_posix(): digest(p) for p in shots.rglob("*") if p.is_file()}
    moved_cache = False
    process = None
    moved_shots = False
    modified = False
    status = 1
    try:
        for source in sources.values():
            if not source.is_file():
                raise FileNotFoundError(source)
        if running():
            return 3
        modified = True
        if asset_cache.exists():
            shutil.move(str(asset_cache), str(backup / "atlas-assets_user"))
            moved_cache = True
        if os.environ.get("PREFILL_CACHE"):
            # Optional: Cache vorab aus einem Ordner fuellen (z. B. UnknownsAtlas-Assets/files), damit grosse Pakete
            # wie der Vorspann beim Test schon da sind; der Store prueft sie trotzdem gegen den Katalog.
            shutil.copytree(os.environ["PREFILL_CACHE"], asset_cache)
        if shots.exists():
            # Spiel und Arbeitskopie liegen auf verschiedenen Laufwerken.
            shutil.move(str(shots), str(backup / "AtlasShots_user"))
            moved_shots = True
        for target, source in sources.items():
            shutil.copy2(source, target)
        overrides = os.environ.get("EXTRA", "").split()
        if os.environ.get("ASSET_SOURCE"):
            overrides.append("Assets.Download source=" + os.environ["ASSET_SOURCE"])
        maptest_cfg.main([str(config), mp, task, *overrides])
        log.unlink(missing_ok=True)
        if running():
            raise RuntimeError("Among Us wurde inzwischen extern gestartet; kein eigener Start")
        # Normaler Start ohne Parameter oder veraenderte Prozessumgebung.
        (out / "tasklist_before_start.txt").write_text(subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True), encoding="utf-8")
        process = subprocess.Popen([str(GAME / "Among Us.exe")], cwd=GAME)
        print(f"Test gestartet: PID {process.pid}, DLL aus {PROJECT}", flush=True)
        deadline = time.monotonic() + 260
        built = False
        while process.poll() is None and time.monotonic() < deadline:
            if log.exists() and "BUILD DONE" in log.read_text(encoding="utf-8", errors="replace"):
                built = True
                break
            time.sleep(1)
        if not built:
            raise RuntimeError("Kein BUILD DONE im Testlauf")
        deadline = time.monotonic() + wait
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.5)
        status = 0 if process.poll() is None else 1
    finally:
        errors = []
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
            if modified:
                if log.exists():
                    shutil.copy2(log, out / f"{mp}_full.log")
                    maptest_cfg.main(["--log", str(log), str(out / f"{mp}.log")])
                if shots.exists():
                    result_shots = out / f"{mp}_shots"
                    result_shots.mkdir(exist_ok=True)
                    shutil.copytree(shots, result_shots, dirs_exist_ok=True)
                    shutil.rmtree(shots)
        except Exception as error:
            errors.append(str(error))
        finally:
            # Nur der eigene Prozess wird beendet. Bei fremden Starts auf deren Ende warten.
            while running():
                print("Fremder Spielprozess aktiv. Wiederherstellung wartet auf dessen Ende.", flush=True)
                time.sleep(5)
            if moved_cache or asset_cache.exists():
                try:
                    downloads = {p.relative_to(asset_cache).as_posix(): digest(p) for p in asset_cache.rglob("*") if p.is_file()}
                    (out / "downloaded_assets.json").write_text(json.dumps(downloads, indent=2), encoding="utf-8")
                    if asset_cache.exists():
                        shutil.rmtree(asset_cache)
                    if moved_cache:
                        shutil.move(str(backup / "atlas-assets_user"), str(asset_cache))
                except Exception as error:
                    errors.append(str(error))
            if modified:
                try:
                    for p in appdata.iterdir():
                        if p.is_file() and p.name not in app_before:
                            p.unlink()
                    for name in app_before:
                        shutil.copy2(backup / "appdata" / name, appdata / name)
                except Exception as error:
                    errors.append(str(error))
            if moved_shots:
                try:
                    shutil.move(str(backup / "AtlasShots_user"), str(shots))
                except Exception as error:
                    errors.append(str(error))
            if modified:
                try:
                    for path in config.rglob("*"):
                        if path.is_file() and path.relative_to(config).as_posix() not in config_before:
                            path.unlink()
                    shutil.copytree(backup / "config", config, dirs_exist_ok=True)
                except Exception as error:
                    errors.append(str(error))
                for path, sha in originals.items():
                    try:
                        if sha is None:
                            path.unlink(missing_ok=True)
                        else:
                            shutil.copy2(backup / path.name, path)
                    except Exception as error:
                        errors.append(str(error))
        checks = {str(path): {"before": sha, "after": digest(path)} for path, sha in originals.items()}
        (out / "restore.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
        if any(row["before"] != row["after"] for row in checks.values()):
            raise RuntimeError(f"RESTORE FEHLER. Sicherung bleibt unter {backup}")
        extra_checks = {
            "configs_identisch": config_before == {p.relative_to(config).as_posix(): digest(p) for p in config.rglob("*") if p.is_file()},
            "appdata_identisch": app_before == {p.name: digest(p) for p in appdata.iterdir() if p.is_file()},
            "asset_cache_identisch": cache_before == {p.relative_to(asset_cache).as_posix(): digest(p) for p in asset_cache.rglob("*") if p.is_file()},
            "shots_identisch": shots_before == {p.relative_to(shots).as_posix(): digest(p) for p in shots.rglob("*") if p.is_file()},
            "spiel_laeuft": running(),
        }
        (out / "outer_restore.json").write_text(json.dumps(extra_checks, indent=2), encoding="utf-8")
        if not all(v for k, v in extra_checks.items() if k != "spiel_laeuft") or extra_checks["spiel_laeuft"]:
            errors.append("Aeusserer Wiederherstellungsvergleich fehlgeschlagen")
        if errors:
            raise RuntimeError(f"Test/Nachbereitung fehlgeschlagen: {errors}. Sicherung: {backup}")
        shutil.rmtree(backup)
        print("DLL, Config, Log, Asset-Cache, Bilder und AppData zurueckgelegt und per SHA256 geprueft", flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
