from pathlib import Path
import collections
import json
import sys
from analyze import read

root=Path(sys.argv[1])
result={}
for letter in 'ABC':
    folder=root/letter
    rows=read(folder/'v4_state.tsv')
    lines=(folder/'LogOutput.log').read_text(encoding='utf-8-sig',errors='replace').splitlines()
    start=next((i for i,s in enumerate(lines) if '=== start game' in s),0)
    # Nur der Host schreibt die Startmarkierung, die anderen schreiben denselben Broadcast.
    runtime=lines[start:]
    errors=[{'line':start+i+1,'text':s} for i,s in enumerate(runtime) if
            ('[Error' in s or 'Exception:' in s or 'V4 Aktion Fehler' in s or 'V4 Tick Fehler' in s or '[Warning:UNKNOWN' in s)
            and 'System.TypeLoadException' not in s and 'ReflectionTypeLoadException' not in s]
    groups=collections.defaultdict(list)
    for r in rows:
        if r['clock']: groups[r['label']].append(r)
    labels={}
    for name,group in groups.items():
        prints=sorted(set(p for r in group for p in r['prints'].split(';') if p))
        allaudio=[sum(float(v.rsplit(':',1)[1]) for v in r['audio'].split(';') if ':' in v) for r in group]
        active=[sum(float(v.rsplit(':',1)[1]) for v in r['audio'].split(';') if ':' in v) for r in group if r['meeting'] or r['exile'] or r['game']!='Started']
        labels[name]={'samples':len(group),'prints':prints,'pollen':sorted(set(r['pollen'] for r in group)),'host':sorted(set(r['host'] for r in group)),
                      'phase':sorted(set(r['phase'] for r in group)),'zone':sorted(set(r['zone'] for r in group)),
                      'audio_max':round(max(allaudio,default=0),4),'audio_in_pause_max':round(max(active,default=0),4),
                      'position_first':group[0]['pos'],'position_last':group[-1]['pos'],
                      'canmove_last':group[-1]['canmove'],'clock_first':group[0]['clock'],'clock_last':group[-1]['clock']}
    result[letter]={'runtime_errors':errors,'bekannte_harmony_typwarnungen':sum('AccessTools.GetTypesFromAssembly: assembly Il2Cppmscorlib' in s for s in runtime),'wrapup_errors':sum('WrapUpPostfix' in s for s in lines), 'labels':labels}
    print(letter,'Laufzeitfehler',len(errors),'WrapUp',result[letter]['wrapup_errors'],'Phasen',len(labels))
    for name,e in labels.items():
        if any(t in name for t in ['pollen_laufen','rutsche_','reaktor_','host_verlaesst']): print(' ',name,'Abdruecke',len(e['prints']),'Position',e['position_last'],'Host',e['host'])
comparisons={}
for label in result['A']['labels']:
    entries=[result[x]['labels'].get(label,{}) for x in 'ABC']
    if not all(entries): continue
    prints=[e['prints'] for e in entries]
    if any(prints): comparisons[label]={'identische_abdruecke':prints[0]==prints[1]==prints[2],'anzahl':[len(p) for p in prints]}
result['pollenvergleich']=comparisons
(root/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print('Pollenvergleich',comparisons)
