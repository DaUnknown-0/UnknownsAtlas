from pathlib import Path
import datetime
import json
import math
import sys
from analyze import read

root=Path(sys.argv[1])
data={x:read(root/x/'v4_state.tsv') for x in 'ABC'}
life={}
for x in 'ABC':
    lines=(root/x/'v4_life.tsv').read_text(encoding='utf-8-sig').splitlines()
    life[x]=[dict(zip('utc label eligible sun angle lamps honey moving'.split(),line.split('\t'))) for line in lines if len(line.split('\t'))==8]
out={}
for label in ['folge_1f_pollen_laufen','folge_pollen_laufen']:
    prints={x:sorted(set(p for r in rows if r['label']==label for p in r['prints'].split(';') if p)) for x,rows in data.items()}
    out[label]={'identisch':prints['A']==prints['B']==prints['C'],'abdruecke':prints}
out['audio']={}
for x,rows in data.items():
    total=lambda r:sum(float(v.rsplit(':',1)[1]) for v in r['audio'].split(';') if ':' in v)
    audio={'maximal':max(map(total,rows),default=0),'pause_maximal':max((total(r) for r in rows if r['meeting'] or r['exile']),default=0)}
    for label in ['folge_sound_gast_aus','folge_sound_gast_an']:
        q=[r for r in rows if r['label']==label]
        if q: q=[r for r in q if r['time']>q[0]['time']+.5]
        audio[label]=[min(map(total,q),default=0),max(map(total,q),default=0)]
    out['audio'][x]=audio
out['unsichtbarkeit']={}
for role in ['Ninja','Scout','Phantom']:
    for who,pid in [('A','0'),('B','1')]:
        label='folge_unsichtbar_'+role+'_'+who
        checks={}
        for x,rows in life.items():
            q=[r for r in rows if r['label']==label]
            if q:
                first=datetime.datetime.fromisoformat(q[0]['utc'].replace('Z','+00:00')).timestamp()
                q=[r for r in q if datetime.datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp()-first<1.9]
            flags=[next((p.split(':')[1] for p in r['eligible'].split(';') if p.startswith(pid+':')),'fehlt') for r in q]
            checks[x]={'proben':len(q),'quellenfreigaben':sorted(set(flags))}
            state=[r for r in data[x] if r['label']==label]
            if state:
                first=state[0]['time']; clock=float(state[0]['lifeClock'])
                fresh=set(p for r in state if r['time']-first<1.9 for p in r['prints'].split(';') if p and float(p.rsplit(':',1)[1])>clock+.01)
                checks[x]['frische_abdruecke']=sorted(fresh)
        out['unsichtbarkeit'][label]=checks
out['honigspuren']={}
for zone in range(4):
    label='folge_honig'+str(zone)
    out['honigspuren'][label]={x:max((int(r['honey']) for r in rows if r['label']==label),default=0) for x,rows in life.items()}
out['wege']={}
for name,target in [('keeper_waggle',(16,9.4)),('queen_sun',(7,-14.55)),('west_wasp',(-12.4,-13.4))]:
    q=[r for r in data['A'] if r['label']=='folge_weg_'+name and r['pos']]
    out['wege'][name]=min((math.dist([float(v.strip()) for v in r['pos'].strip('()').split(',')],target) for r in q),default=999)
out['host_abgang']={}
for x,rows in data.items():
    q=[r for r in rows if r['label']=='folge_host_verlaesst']
    out['host_abgang'][x]={'proben':len(q),'status':sorted(set((r['game'],r['host']) for r in q)),
                              'uhr_zuerst':q[0]['clock'] if q else '', 'uhr_zuletzt':q[-1]['clock'] if q else ''}
(root/'summary.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(out,indent=2,ensure_ascii=False))
