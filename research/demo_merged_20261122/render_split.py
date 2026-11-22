"""Split-screen backup video for take 7: left = the Gazebo GUI window (cropped from a desktop recording, nothing else of the screen is kept),
right = the real recorded tool-call log of the same take, time-aligned by wall clock. Windows Python + Pillow + ffmpeg. Zero model calls.
Usage: python render_split.py <take folder> <desktop recording.mp4> <recording start epoch file> <crop x,y,w,h> <output.mp4>
The raw desktop recording is NOT committed (it shows the whole screen)."""
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_video import BG, DIM, FG, ACC, GOOD, WARN, LABEL, short  # noqa: E402

FPS = 5
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 17)
BIG = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 22)
SMALL = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
PW, PH = 640, 720


def events(take):
    """(wall epoch, task id, colour, text) from the recorded traces."""
    meta = json.loads((take / 'RUN_META.json').read_text())
    per_task, offset = {}, None
    for record in meta['tasks']:
        folder = next(take.glob('%s_take*' % record['task']))
        rows = [json.loads(line) for line in (folder / 'trace.jsonl').read_text().splitlines()]
        per_task[record['task']] = rows
        for r in rows:
            if offset is None and 't_wall' in r and 't_monotonic' in r:
                offset = datetime.datetime.fromisoformat(r['t_wall']).timestamp() - float(r['t_monotonic'])
    out = []
    for tid, rows in per_task.items():
        for r in rows:
            at = r['monotonic'] + offset if 'monotonic' in r else None
            k = r['kind']
            if k == 'episode_start':
                out.append((at, tid, FG, '== %s: %s' % (tid, short(r.get('request'), 90))))
            elif k == 'tool_start' and r.get('name') in ('run_skill', 'final_answer') or (k == 'tool_start' and str(r.get('name')).startswith('ros2_')):
                out.append((at, tid, GOOD if r['name'] == 'final_answer' else ACC, 'model calls %s %s' % (r['name'], short(r.get('input'), 52))))
            elif k in ('macro_internal_read', 'macro_internal_write'):
                what = 'WRITE' if k.endswith('write') else 'read'
                out.append((float(r['t_monotonic']) + offset, tid, WARN if what == 'WRITE' else DIM, '  macro %s %s' % (what, r.get('source'))))
            elif k == 'final_answer_accepted':
                out.append((at, tid, GOOD, 'ANSWER ' + short(r.get('answer'), 62)))
    return sorted((e for e in out if e[0]), key=lambda e: e[0])


def panel(log, now, rec_t):
    img = Image.new('RGB', (PW, PH), BG)
    d = ImageDraw.Draw(img)
    d.text((16, 12), 'Tool-call log (recorded, Sol)', font=BIG, fill=FG)
    d.line((16, 46, PW - 16, 46), fill=(60, 64, 76), width=2)
    shown = [e for e in log if e[0] <= now][-19:]
    for i, (_, _, colour, text) in enumerate(shown):
        d.text((16, 58 + i * 30), short(text, 58), font=FONT, fill=colour)
    d.text((16, PH - 72), 'merged method (Levinson M + Martin bounded macro),', font=SMALL, fill=WARN)
    d.text((16, PH - 50), 'demonstration only, not evaluated', font=SMALL, fill=WARN)
    d.text((16, PH - 28), 'Credit: method M components (Levinson); macro run_skill (Martin).', font=SMALL, fill=DIM)
    return img


def main():
    take, desktop, start_file, crop, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
    x, y, w, h = [int(v) for v in crop.split(',')]
    rec0 = float(start_file.read_text())
    log = events(take)
    t0, t1 = log[0][0] - 4, log[-1][0] + 5
    start, length = t0 - rec0, t1 - t0
    stage = Path(tempfile.mkdtemp())
    for i in range(int(length * FPS)):
        panel(log, t0 + i / FPS, rec0).save(stage / ('p%05d.png' % i))
    left = 'crop=%d:%d:%d:%d,scale=-2:720' % (w, h, x, y)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.2f' % start, '-t', '%.2f' % length, '-i', desktop, '-framerate', str(FPS), '-i', str(stage / 'p%05d.png'),
                    '-filter_complex', '[0:v]fps=%d,%s[l];[l][1:v]hstack=inputs=2[v]' % (FPS, left), '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(output)], check=True)
    shutil.rmtree(stage)
    print('video', output, 'seconds', round(length, 1), 'from recording second', round(start, 1))


if __name__ == '__main__':
    main()
