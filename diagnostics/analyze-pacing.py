#!/usr/bin/env python3
import argparse,csv,datetime,json,statistics,math
from pathlib import Path
parser=argparse.ArgumentParser(description='Match MangoHud CSVs to recorded gesture intervals, retaining stalls.')
parser.add_argument('measurements',type=Path)
parser.add_argument('--cases',default='pacing-comparison')
args=parser.parse_args()
base=args.measurements
files=[]
for path in sorted((base/'mangohud').glob('lightroom_*.csv')):
 if path.name.endswith('_summary.csv'):continue
 start=datetime.datetime.strptime(path.stem.removeprefix('lightroom_'),'%Y-%m-%d_%H-%M-%S').timestamp()
 try:
  rows=list(csv.DictReader(path.read_text().splitlines()[2:]));samples=[(start+float(r['elapsed'])/1e9,float(r['frametime'])) for r in rows]
 except (ValueError,KeyError):continue
 files.append((path.name,samples))
report=[]
for path in sorted((base/args.cases).glob('*-phases.json')):
 case=json.loads(path.read_text());runs=[]
 for phase in case['phases']:
  # Filename clock precision is one second. Trim both boundaries by one second,
  # then include EVERY frame interval, including stalls, inside the active span.
  data=[(name,t,dt) for name,samples in files for t,dt in samples if phase['start_epoch']+1<=t<=phase['end_epoch']-1]
  values=sorted(dt for name,t,dt in data)
  if not values:runs.append({'samples':0});continue
  percentile=lambda q:values[max(0,math.ceil(q*len(values))-1)]
  runs.append(dict(samples=len(values),p50_ms=round(statistics.median(values),3),p95_ms=round(percentile(.95),3),p99_ms=round(percentile(.99),3),max_ms=round(max(values),3),over_16_67_percent=round(100*sum(v>16.67 for v in values)/len(values),1),over_8_33_percent=round(100*sum(v>8.33 for v in values)/len(values),1),files=sorted(set(n for n,_,_ in data))))
 report.append(dict(case=case['case'],config=case['config'],runs=runs))
print(json.dumps(report,indent=2))
