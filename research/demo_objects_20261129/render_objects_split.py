"""Split-screen backup video for the objects demo: left = the Gazebo 3D view (cropped from a desktop recording, nothing else of the screen is kept),
right = the real recorded tool-call log of the same take, aligned by wall clock. Windows Python + Pillow + ffmpeg. Zero model calls.
Usage: python render_objects_split.py <session folder> <request folder name e.g. req_01> <desktop recording.mp4> <recording start epoch file> <crop x,y,w,h> <output.mp4>
The raw desktop recording is NOT committed (it shows the whole screen).
LABEL: object poses read from the simulator (ground truth); simulated gripper with grasp assist; demonstration only, not evaluated."""
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'demo_merged_20261122'))
from render_video import BG, DIM, FG, ACC, GOOD, WARN, short  # noqa: E402

FPS = 5
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 17)
BIG = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 22)
SMALL = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
PW, PH = 640, 720


def events(folder):
    rows = [json.loads(line) for line in (folder / 'trace.jsonl').read_text().splitlines()]
    offset = None
    for r in rows:
        if 't_wall' in r and 't_monotonic' in r:
            offset = datetime.datetime.fromisoformat(r['t_wall']).timestamp() - float(r['t_monotonic'])
            break
    out = []
    for r in rows:
        at = r['monotonic'] + offset if 'monotonic' in r else (float(r['t_monotonic']) + offset if 't_monotonic' in r else None)
        k = r['kind']
        if k == 'episode_start':
            out.append((at, FG, 'REQUEST: ' + short(r.get('request'), 70)))
        elif k == 'tool_start' and r.get('name') in ('get_object_pose', 'pick', 'place', 'run_skill', 'final_answer'):
            out.append((at, GOOD if r['name'] == 'final_answer' else ACC, 'model calls %s %s' % (r['name'], short(r.get('input'), 44))))
        elif k == 'macro_object_call_end':
            out.append((at, GOOD if r.get('ok') else WARN, '  [macro] %s %s' % (r.get('tool'), 'OK' if r.get('ok') else 'REFUSED/FAILED')))
        elif k == 'final_answer_accepted':
            out.append((at, GOOD, 'ANSWER ' + short(r.get('answer'), 56)))
    return sorted((e for e in out if e[0]), key=lambda e: e[0])


def panel(log, now):
    img = Image.new('RGB', (PW, PH), BG)
    d = ImageDraw.Draw(img)
    d.text((16, 12), 'Tool-call log (recorded, Sol)', font=BIG, fill=FG)
    d.line((16, 46, PW - 16, 46), fill=(60, 64, 76), width=2)
    for i, (_, colour, text) in enumerate([e for e in log if e[0] <= now][-14:]):
        d.text((16, 58 + i * 34), short(text, 58), font=FONT, fill=colour)
    d.text((16, PH - 96), 'merged method (Levinson M + Martin bounded macro) + object tools', font=SMALL, fill=WARN)
    d.text((16, PH - 74), 'object poses read from the simulator (ground truth); simulated', font=SMALL, fill=WARN)
    d.text((16, PH - 52), 'gripper with grasp assist; demonstration only, not evaluated', font=SMALL, fill=WARN)
    d.text((16, PH - 28), 'Credit: method M components (Levinson); macro (Martin).', font=SMALL, fill=DIM)
    return img


def main():
    session, req, desktop, start_file, crop, output = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5], Path(sys.argv[6])
    x, y, w, h = [int(v) for v in crop.split(',')]
    rec0 = float(start_file.read_text())
    log = events(session / req)
    t0, t1 = log[0][0] - 4, log[-1][0] + 5
    start, length = t0 - rec0, t1 - t0
    stage = Path(tempfile.mkdtemp())
    for i in range(int(length * FPS)):
        panel(log, t0 + i / FPS).save(stage / ('p%05d.png' % i))
    left = 'crop=%d:%d:%d:%d,scale=-2:720' % (w, h, x, y)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.2f' % start, '-t', '%.2f' % length, '-i', desktop, '-framerate', str(FPS), '-i', str(stage / 'p%05d.png'),
                    '-filter_complex', '[0:v]fps=%d,%s[l];[l][1:v]hstack=inputs=2[v]' % (FPS, left), '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(output)], check=True)
    shutil.rmtree(stage)
    print('video', output, 'seconds', round(length, 1), 'from recording second', round(start, 1))


if __name__ == '__main__':
    main()
