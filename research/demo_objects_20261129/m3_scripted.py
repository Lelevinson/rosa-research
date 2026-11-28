"""Milestone 3 scripted pick-and-place (no model). usage: m3_scripted.py <gz_partition.txt> <out.json> "x,y,yaw;x,y,yaw" [reps]
LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import objects_lib as ol
import objects_skills as sk
partition = Path(sys.argv[1]).read_text().strip()
positions = [tuple(float(v) for v in p.split(',')) for p in sys.argv[3].split(';')]
reps = int(sys.argv[4]) if len(sys.argv) > 4 else 1
arm = ol.ObjectsArm(partition)
skills = sk.Skills(arm)
rows = []
for pos in positions:
    for rep in range(reps):
        row = {'block_start': pos, 'rep': rep}
        ok, ev = sk.reset_world(arm, pos, partition)
        row['reset_ok'], row['reset'] = ok, ev
        if not ok:
            row['status'] = 'RESET_FAILED_NOT_RUN'; rows.append(row); print(row, flush=True); continue
        t0 = time.time()
        row['pick'] = skills.pick()
        row['place'] = skills.place() if row['pick']['ok'] else None
        row['success'] = bool(row['pick']['ok'] and row['place'] and row['place']['ok'] and skills.block_on_tray())
        row['seconds'] = round(time.time() - t0, 1)
        rows.append(row)
        print(pos, rep, 'success', row['success'], row['pick']['step'], row['pick']['detail'][:80], '|', (row['place'] or {}).get('detail', '')[:80], flush=True)
        Path(sys.argv[2]).write_text(json.dumps(rows, indent=1, default=str))
print('SUMMARY', sum(r.get('success', False) for r in rows), '/', len(rows))
arm.close()
