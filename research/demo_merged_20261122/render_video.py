"""Render a backup video of one take from its recorded trace.jsonl files (Windows Python + Pillow + ffmpeg). Zero model calls.
The Gazebo run was headless (the launch used gazebo_gui:=false), so NO Gazebo screen exists: the video shows the real recorded tool-call log of each task.
Usage: python render_video.py <take folder> <output.mp4>"""
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABEL = 'merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated'
W, H = 1280, 720
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 20)
BIG = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 24)
SMALL = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
BG, FG, DIM, ACC, GOOD, WARN = (18, 20, 26), (230, 232, 238), (140, 146, 160), (110, 170, 255), (120, 220, 150), (255, 190, 90)


def short(value, n=96):
    text = str(value).replace('\n', ' ')
    return text if len(text) <= n else text[:n - 1] + '...'


def lines_for(task_id, trace):
    """(colour, text) log lines in order, from the recorded rows."""
    out = []
    for r in trace:
        k = r['kind']
        if k == 'tool_start' and r.get('name') in ('run_skill', 'ros2_topic_info', 'ros2_topic_echo', 'ros2_topic_list', 'ros2_node_list', 'ros2_node_info', 'final_answer'):
            out.append((ACC if r['name'] != 'final_answer' else GOOD, 'model calls  %s  %s' % (r['name'], short(r.get('input'), 70))))
        elif k in ('macro_internal_read', 'macro_internal_write'):
            what = 'WRITE' if k.endswith('write') else 'read '
            out.append((WARN if what == 'WRITE' else DIM, '  macro %s  %s  %s' % (what, r.get('source'), r.get('status'))))
        elif k == 'macro_skill_call_end':
            out.append((DIM, '  macro skill end  %s  %s' % (r.get('skill_id'), r.get('outcome'))))
        elif k == 'final_answer_accepted':
            out.append((GOOD, 'ANSWER  ' + short(r.get('answer'), 100)))
    return out


def frame(task_id, text, log, shown, final=False):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((24, 14), 'Demo %s  (Sol, take recorded log)' % task_id, font=BIG, fill=FG)
    d.text((24, 48), text[:105], font=FONT, fill=DIM)
    d.text((24, 72), text[105:210], font=FONT, fill=DIM)
    d.line((24, 102, W - 24, 102), fill=(60, 64, 76), width=2)
    visible = log[:shown][-16:]
    for i, (colour, line) in enumerate(visible):
        d.text((24, 114 + i * 30), short(line, 112), font=FONT, fill=colour)
    d.text((24, H - 54), LABEL, font=SMALL, fill=WARN)
    d.text((24, H - 30), 'Credit: method M components (Levinson); bounded macro run_skill (Martin). Headless run: log shown, no Gazebo picture.', font=SMALL, fill=DIM)
    return img


def main():
    take, output = Path(sys.argv[1]), Path(sys.argv[2])
    meta = json.loads((take / 'RUN_META.json').read_text())
    stage = Path(tempfile.mkdtemp())
    n = 0

    def save(img, repeats):
        nonlocal n
        for _ in range(repeats):
            img.save(stage / ('f%05d.png' % n))
            n += 1
    for record in meta['tasks']:
        tid = record['task']
        folder = next(take.glob('%s_take*' % tid))
        trace = [json.loads(line) for line in (folder / 'trace.jsonl').read_text().splitlines()]
        request = next(r for r in trace if r['kind'] == 'episode_start')['request']
        log = lines_for(tid, trace)
        save(frame(tid, request, log, 0), 6)
        for i in range(1, len(log) + 1):
            save(frame(tid, request, log, i), 3)
        save(frame(tid, request, log, len(log), True), 8)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '4', '-i', str(stage / 'f%05d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(output)], check=True)
    shutil.rmtree(stage)
    print('frames', n, 'video', output)


if __name__ == '__main__':
    main()
