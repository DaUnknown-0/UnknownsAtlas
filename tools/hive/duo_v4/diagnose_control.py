"""Gegenprobe einer unveraenderten Atlas-Karte, echte Installation nur via maptest.sh."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from session import AD, HERE, PROJECT, installed, manifest, running

if running():
    print('Among Us laeuft. Keine Gegenprobe gestartet.')
    raise SystemExit(3)
out=HERE/'_out'/(sys.argv[1] if len(sys.argv)>1 else 'v4_control_museum')
out.mkdir(parents=True,exist_ok=False)
ad=manifest(AD.glob('*'))
real=installed()
backup=out/'appdata_backup'
backup.mkdir()
for p in AD.glob('*'):
    if p.is_file(): shutil.copy2(p,backup/p.name)
try:
    env=os.environ.copy()
    env['OUTDIR']=str(out)
    env['EXTRA']='Diagnostics.MapShot=false'
    with (out/'console.log').open('w') as log:
        rc=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(PROJECT/'tools/hive/maptest.sh'),'museum','ejectskip:0','55'],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
finally:
    for p in AD.glob('*'):
        if p.is_file() and str(p) not in ad: p.unlink()
    for p in backup.glob('*'): shutil.copy2(p,AD/p.name)
    status={'appdata_identisch':manifest(AD.glob('*'))==ad,'installation_identisch':installed()==real,'spiel_laeuft':running()}
    (out/'outer_restore.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status),flush=True)
raise SystemExit(rc)
