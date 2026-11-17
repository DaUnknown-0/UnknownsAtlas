"""DuoTest mit V4-DLL, eigener Sicherung und begrenztem Prozessbesitz."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
WORK = Path(os.environ['LOCALAPPDATA']) / 'DuoTest'
AD = Path(os.environ['USERPROFILE']) / 'AppData/LocalLow/Innersloth/Among Us'
GAME = Path('C:/Users/moritz/Downloads/Among Us - 4.7.0/Among Us - 4.7.0')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest(paths):
    return {str(p): sha(p) for p in paths if p.is_file()}


def installed():
    return manifest([*GAME.glob('BepInEx/plugins/*.dll'), *GAME.glob('BepInEx/config/*'),
                     GAME / 'BepInEx/LogOutput.log', GAME / 'Among Us.exe',
                     GAME / 'GameAssembly.dll', GAME / 'doorstop_config.ini'])


def running():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Among Us.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True)
    return '"Among Us.exe"' in r.stdout


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'v4_multi_01'
    plan = sys.argv[2] if len(sys.argv) > 2 else 'hivev4'
    if running():
        print('Among Us laeuft bereits. Keine Aenderung, kein Teststart.', flush=True)
        return 3
    out = HERE / '_out' / tag
    out.mkdir(parents=True, exist_ok=False)
    backup = out / 'backup'
    backup.mkdir()
    adfiles = manifest(AD.glob('*'))
    real = installed()
    assets=manifest((PROJECT/'assets/amberhive').rglob('*'))
    (out/'assets_before.json').write_text(json.dumps(assets,indent=2))
    (out / 'before.json').write_text(json.dumps({'appdata':adfiles,'installation':real},indent=2))
    for p in AD.glob('*'):
        if p.is_file():
            (backup/'appdata').mkdir(exist_ok=True)
            shutil.copy2(p,backup/'appdata'/p.name)
    targets = {}
    for letter in 'ABC':
        root = WORK / letter
        files = [*root.glob('BepInEx/config/*.cfg'), root/'BepInEx/plugins/UnknownsAtlas.dll',root/'BepInEx/plugins/DuoTest.dll',root/'duo_role.txt']
        for p in files:
            rel = p.relative_to(WORK)
            targets[str(p)] = sha(p) if p.exists() else None
            if p.exists():
                (backup/rel).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,backup/rel)
    (out/'targets.json').write_text(json.dumps(targets,indent=2))
    proc = None
    try:
        for letter in 'ABC':
            root=WORK/letter
            # Plugins sind echte Kopien, niemals ueber einen bestehenden Hardlink schreiben.
            for name,src in [('UnknownsAtlas.dll',PROJECT/'bin/Release/net6.0/UnknownsAtlas.dll'),('DuoTest.dll',HERE/'bin/Release/net6.0/DuoTest.dll')]:
                dst=root/'BepInEx/plugins'/name
                dst.unlink(missing_ok=True)
                shutil.copy2(src,dst)
            cfg=root/'BepInEx/config/com.daunknown0.atlas.cfg'
            cfg.write_text('[General]\nEnabled = true\n[PoC]\nBuildPocMap = true\n[Diagnostics]\nForceMap =\nTaskTest =\nMapShot = false\nErrorStackTraces = true\nAmberhiveFloorsTest = -1\nAmberhivePollenTest = -1\nAmberhiveSunPeriodTest = 0\nAmberhiveGlowTest = false\nAmberhiveLifeLog = true\n[Amberhive Sound]\nEnabled = true\nVolume = 60\n',encoding='utf-8')
            for name in ['v4_state.tsv','v4_life.tsv']:
                (root/name).unlink(missing_ok=True)
            # Eindeutige Bildnamen je Lauf, vorhandene Aufnahmen nicht loeschen.
        (out/'deployment.json').write_text(json.dumps({x:sha(WORK/x/'BepInEx/plugins/UnknownsAtlas.dll') for x in 'ABC'},indent=2))
        ps = HERE/'run.ps1'
        text=ps.read_text(encoding='utf-8-sig')
        if 'tasklist /FI' not in text:
            text=text.replace('function Launch($x) {','function Launch($x) {\n  tasklist /FI "IMAGENAME eq Among Us.exe"\n  if (Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "$T\\*" }) { throw "Fremdes Spiel gestartet, Test angehalten" }')
        text=text.replace('"host process gone"; break','"host process gone"; Start-Sleep 35; break')
        ps.write_text(text,encoding='utf-8-sig')
        proc=subprocess.Popen(['pwsh','-NoProfile','-File',str(ps),'-Tag',tag,'-Clients','2','-Plan',plan,'-Minutes','35'],cwd=HERE,stdout=open(out/'console.log','w'),stderr=subprocess.STDOUT)
        print(f'Lauf {tag}, Steuerprozess {proc.pid}, Sicherung {backup}',flush=True)
        proc.wait()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
        # Keine vorbestehenden Prozesse moeglich: der Start wurde oben bei jedem Spiel verweigert.
        subprocess.run(['pwsh','-NoProfile','-Command', '$testRoot = $env:LOCALAPPDATA + "\\DuoTest\\"; Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path.StartsWith($testRoot) } | Stop-Process -Force'],capture_output=True)
        time.sleep(2)
        run=WORK/'runs'/tag
        if run.exists():
            shutil.copytree(run,out/'logs',dirs_exist_ok=True)
        for letter in 'ABC':
            root=WORK/letter
            dest=out/letter
            dest.mkdir(exist_ok=True)
            for name in ['v4_state.tsv','v4_life.tsv','player.log','BepInEx/LogOutput.log']:
                p=root/name
                if p.exists(): shutil.copy2(p,dest/p.name)
            if (root/'duo_shots').exists(): shutil.copytree(root/'duo_shots',dest/'shots',dirs_exist_ok=True)
        for p in AD.glob('*'):
            if p.is_file() and str(p) not in adfiles: p.unlink()
        for p in (backup/'appdata').glob('*'): shutil.copy2(p,AD/p.name)
        for name, oldsha in targets.items():
            p=Path(name)
            p.unlink(missing_ok=True)
            if oldsha is not None: shutil.copy2(backup/p.relative_to(WORK),p)
        result={'appdata_identisch':manifest(AD.glob('*'))==adfiles,'installation_identisch':installed()==real,'assets_unveraendert':manifest((PROJECT/'assets/amberhive').rglob('*'))==assets,
                'testkopien_wiederhergestellt':all((sha(Path(p)) if Path(p).exists() else None)==v for p,v in targets.items()),'spiel_laeuft':running()}
        (out/'restore.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
