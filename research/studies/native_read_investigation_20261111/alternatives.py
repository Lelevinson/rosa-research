"""Offline screening of in-flight request coalescing; no freshness assumptions."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def main():
    data=json.loads((ROOT/'evidence/inventory.json').read_text())
    groups={}
    witnesses=[]
    for label,episodes in [('diagnostic_primary',[e for e in data['episodes'] if e['primary']]),
                           ('codeact_all',[e for e in data['episodes'] if e['corpus']=='codeact'])]:
        native_count=overlaps=repeats=0
        native_seconds=span=0.
        for ep in episodes:
            prior={}
            span+=ep['event_span_seconds'] or 0
            for event in ep['native_events']:
                native_count+=1
                duration=event.get('seconds')
                if duration is None:
                    continue
                native_seconds+=duration
                key=json.dumps(event.get('command'),sort_keys=True)
                end=event['monotonic']
                start=end-duration
                if key in prior:
                    repeats+=1
                    if prior[key]>start:
                        overlaps+=1
                        witnesses.append({'member':ep['member'],'command':event['command']})
                prior[key]=end
        groups[label]={'native_completions':native_count,'exact_repeats':repeats,
                       'overlapping_exact_repeats':overlaps,
                       'native_duration_sum_seconds':native_seconds,'event_span_sum_seconds':span,
                       'native_duration_fraction':native_seconds/span if span else None}
    result={'groups':groups,'overlap_witnesses':witnesses,
            'decision':'In-flight singleflight coalescing lacks activation in this sample. Sequential repeats are not cache-authorized.',
            'limits':'Timing intervals reconstructed from recorded completion monotonic minus recorded seconds. No deduplication across permissions/snapshots is authorized.'}
    (ROOT/'evidence/alternatives.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
