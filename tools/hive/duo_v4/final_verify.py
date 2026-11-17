from pathlib import Path
import json
import re
from session import AD, HERE, PROJECT, installed, manifest, running, sha

latest=HERE/'_out/v4_multi_04'
before=json.loads((latest/'before.json').read_text())
targets=json.loads((latest/'targets.json').read_text())
deployment=json.loads((latest/'deployment.json').read_text())
assets=json.loads((latest/'assets_before.json').read_text())
result={
    'appdata_identisch_vor_letztem_lauf':manifest(AD.glob('*'))==before['appdata'],
    'echte_installation_identisch':installed()==before['installation'],
    'testkopien_identisch':all((sha(Path(p)) if Path(p).exists() else None)==v for p,v in targets.items()),
    'assets_identisch':manifest((PROJECT/'assets/amberhive').rglob('*'))==assets,
    'alle_instanz_dlls_aus_v4_release':all(v==sha(PROJECT/'bin/Release/net6.0/UnknownsAtlas.dll') for v in deployment.values()),
    'keine_among_us_prozesse':not running(),
    'release_sha256':sha(PROJECT/'bin/Release/net6.0/UnknownsAtlas.dll'),
    'life_source_sha256':sha(PROJECT/'src/AtlasAmberhiveLife.cs'),
    'wiederherstellung_lauefe':{},
}
for p in sorted((HERE/'_out').glob('*/restore.json')):
    if p.parent.name.startswith('v4_multi_'):
        result['wiederherstellung_lauefe'][p.parent.name]=json.loads(p.read_text())
for p in sorted((HERE/'_out').glob('*/outer_restore.json')):
    result['wiederherstellung_lauefe'][p.parent.name]=json.loads(p.read_text())
report=PROJECT/'tools/hive/V4_BERICHT_MULTI.md'
missing=[]
for link in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
    if '://' not in link and link!='duo_v4/final_verification.json' and not (report.parent/link).exists():missing.append(link)
result['bericht_fehlende_links']=missing
(HERE/'final_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if isinstance(v,bool) or k=='bericht_fehlende_links'},ensure_ascii=False))
assert all(v for v in result.values() if isinstance(v,bool))
assert not missing
