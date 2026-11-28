import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import objects_lib as ol
p = ol.GroundTruth(Path(sys.argv[1]).read_text().strip())
for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 1):
    b = p.pose('red_block'); print(time.strftime('%H:%M:%S'), [round(x, 4) for x in b[:3]], 'yaw %.1f deg' % (ol.yaw_of(b[3:]) * 57.3), 'qxy', round(b[3], 3), round(b[4], 3), flush=True)
    if i < (int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0): time.sleep(2)
