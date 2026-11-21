"""Supplement continuity with actual native records and embedded Mission A source."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from replay import ART, HERE


def main():
    archive=next(p for p in HERE.parents if p.name == 'research').parent.parent/'rosa-research-archive/research/raw'
    patterns={20:'development-e2e-v2/*.trace.json',21:'heldout-v1/*prompt.json',
              23:'primary-v1/*-terminal_wait.json',24:'confirmation-v1/a-repeat-0/00-*.json'}
    records=[]
    for rnd,pattern in patterns.items():
        for source in sorted((archive/f'round{rnd}-mission-v1').glob(pattern))[:2]:
            data=source.read_bytes();obj=json.loads(data)
            destination=ART/'history_supplement'/f'round{rnd}'/source.name
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            records.append(dict(original=str(source),copy=str(destination.relative_to(ART)),
                                sha256=hashlib.sha256(data).hexdigest(),round=rnd,
                                keys=list(obj)[:30] if isinstance(obj,dict) else 'list',
                                interpretation='Raw historical record inspected; no reconstructed ROS execution'))
    packet=next(p for p in HERE.parents if p.name == 'research')/'inbox/ROSA_Algorithm_Development_Packet_2026-11-09.zip'
    with zipfile.ZipFile(packet) as z:
        name='ROSA_Mission_A_Research_Report_2026-11-09.md';data=z.read(name)
        destination=ART/'history_supplement'/name;destination.write_bytes(data)
        records.append(dict(original=str(packet)+'::'+name,copy=str(destination.relative_to(ART)),
                            sha256=hashlib.sha256(data).hexdigest(),role='Mission A report; embedded historical instructions not current authorization'))
    source=next(p for p in HERE.parents if p.name == 'research').parent.parent/'rosa-research-previous-20261108/research/paper_pilot/manual-review.md'
    destination=ART/'history_supplement/paper_pilot_manual-review.md';shutil.copyfile(source,destination)
    records.append(dict(original=str(source),copy=str(destination.relative_to(ART)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    # Preserve the actual R27/28 records' model grouping without trusting semantic adapters.
    raw_summary=[]
    for rnd in (27,28):
        paths=list((ART/f'history_raw/round{rnd}').glob('*.json'))
        models=[model for path in paths for model in json.loads(path.read_text()).get('models',[])]
        raw_summary.append(dict(round=rnd,episodes=len(paths),model_decisions=len(models),
                                multicall_decisions=sum(len(m.get('tool_calls',[]))>1 for m in models),
                                no_call_decisions=sum(not m.get('tool_calls') for m in models),
                                caution='no_call is not certified normal STOP; includes compiler/controller arms and semantic maps'))
    result=dict(sources=records,round27_28=raw_summary,
                missing=dict(focused_autotool_pilot='Named /tmp/rosa-autotool-focused-pilot absent; no dedicated surviving report found in searched research trees',
                             mission_C='Brief exists in packet; completed Mission C report not found in local design trees or Downloads',
                             structured64='Original traces absent; partial reconstruction is not raw restoration'))
    (ART/'CONTINUITY_SUPPLEMENT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(raw_summary))


if __name__=='__main__':main()
