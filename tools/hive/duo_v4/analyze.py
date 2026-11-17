from pathlib import Path
import collections
import datetime
import json
import sys

HERE=Path(__file__).resolve().parent
COLUMNS='utc label game host two clock phase phaseT0 zone floodT0 level chute lifeClock synced pollen generation dark prints pos canmove vent meeting exile audio'.split()


def read(p):
    rows=[]
    for line in p.read_text(encoding='utf-8-sig').splitlines():
        a=line.split('\t')
        if len(a)!=len(COLUMNS): continue
        row=dict(zip(COLUMNS,a))
        row['time']=datetime.datetime.fromisoformat(row['utc'].replace('Z','+00:00')).timestamp()
        rows.append(row)
    return rows


def analyze(root):
    data={x:read(root/x/'v4_state.tsv') for x in 'ABC'}
    result={}
    for label in sorted(set(r['label'] for r in data['A'] if r['clock'])):
        groups={x:[r for r in rows if r['label']==label and r['clock']] for x,rows in data.items()}
        entry={'samples':{x:len(rows) for x,rows in groups.items()}}
        comparable=[]
        for a in groups['A']:
            pair=[a]
            for x in 'BC':
                if not groups[x]: break
                b=min(groups[x],key=lambda b:abs(b['time']-a['time']))
                if abs(b['time']-a['time'])>.45: break
                pair.append(b)
            if len(pair)==3: comparable.append(pair)
        entry['comparison_samples']=len(comparable)
        for name in ['two','phase','zone','pollen','generation','dark']:
            entry[name+'_mismatches']=sum(len(set(r[name] for r in pair))>1 for pair in comparable)
        for name in ['level','lifeClock']:
            deltas=[max(float(r[name]) for r in pair)-min(float(r[name]) for r in pair) for pair in comparable if all(r[name] for r in pair)]
            entry[name+'_max_difference']=round(max(deltas,default=0),3)
        entry['prints_max']={x:max((len(r['prints'].split(';')) if r['prints'] else 0 for r in rows),default=0) for x,rows in groups.items()}
        entry['prints_sets']={x:sorted(set(p for r in rows for p in r['prints'].split(';') if p)) for x,rows in groups.items()}
        entry['positions']={x:sorted(set(r['pos'] for r in rows))[-12:] for x,rows in groups.items()}
        entry['audio_max']={x:max((sum(float(v.rsplit(':',1)[1]) for v in r['audio'].split(';') if ':' in v) for r in rows),default=0) for x,rows in groups.items()}
        result[label]=entry
    errors={}
    for x in 'ABC':
        p=root/x/'LogOutput.log'
        lines=p.read_text(encoding='utf-8-sig',errors='replace').splitlines()
        errors[x]=[{'line':i+1,'text':s} for i,s in enumerate(lines) if ('[Error' in s or 'Exception:' in s or 'V4 Aktion Fehler' in s or 'V4 Tick Fehler' in s or ('[Warning' in s and ('Atlas' in s or "UNKNOWN'S ATLAS" in s)))]
    summary={'matrix':result,'errors':errors}
    (root/'analysis.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Phasen:',len(result),'Fehlerzeilen:',{x:len(v) for x,v in errors.items()})
    for label,e in result.items():
        print(label, e['samples'], 'Phasenabweichungen',e['phase_mismatches'],'Life',e['lifeClock_max_difference'],'Pollen',e['prints_max'])


if __name__=='__main__': analyze(Path(sys.argv[1]))
