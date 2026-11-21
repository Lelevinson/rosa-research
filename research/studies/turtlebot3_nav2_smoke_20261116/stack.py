#!/usr/bin/env python3
"""Own one headless TurtleBot3/Nav2 stack; signal only processes carrying its run marker."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path('/tmp/rosa-tb3-nav2-owned')
STATE = ROOT / 'state.json'
SCRIPT = Path(__file__).resolve()
DOMAIN = '219'


def process_marker(pid, marker):
    try:
        env = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return f'ROSA_TB3_RUN_ID={marker}'.encode() in env and stat[0] != 'Z'
    except (OSError, ProcessLookupError):
        return False


def owned(marker, exclude=()):
    result = []
    for p in Path('/proc').iterdir():
        if p.name.isdigit() and int(p.name) not in exclude and process_marker(int(p.name), marker):
            result.append(int(p.name))
    return sorted(result)


def terminate_owned(marker, exclude=(), graceful_pids=()):
    # Let ros2 launch coordinate lifecycle shutdown before escalating to children.
    for pid in graceful_pids:
        try:
            if process_marker(pid, marker): os.kill(pid, signal.SIGINT)
        except ProcessLookupError:
            pass
    if graceful_pids:
        until = time.monotonic() + 8
        while time.monotonic() < until and owned(marker, exclude): time.sleep(.2)
    # Re-scan on each phase so children created during shutdown are included.
    for sig, seconds in ((signal.SIGTERM, 4), (signal.SIGKILL, 4)):
        pids = owned(marker, exclude)
        if not pids:
            return True
        print(f'cleanup {sig.name}: {pids}', flush=True)
        for pid in pids:
            try:
                if process_marker(pid, marker): os.kill(pid, sig)
            except ProcessLookupError:
                pass
        until = time.monotonic() + seconds
        while time.monotonic() < until and owned(marker, exclude): time.sleep(.2)
    left = owned(marker, exclude)
    if left: print(f'cleanup FAILED, processes remain: {left}', flush=True)
    return not left


def environment(marker):
    env = os.environ.copy()
    env.update(ROS_DOMAIN_ID=DOMAIN, ROS_LOCALHOST_ONLY='1', TURTLEBOT3_MODEL='burger',
               LIBGL_ALWAYS_SOFTWARE='1', GZ_PARTITION='rosa_tb3_' + marker,
               ROS_HOME=str(ROOT/'ros'), ROS_LOG_DIR=str(ROOT/'log'), ROSA_TB3_RUN_ID=marker)
    return env


def shell(command, env, out):
    return subprocess.Popen(['/bin/bash', '-c', 'source /opt/ros/jazzy/setup.bash && exec ' + command],
                            env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)


def prepare_launch():
    source = Path('/opt/ros/jazzy/share/turtlebot3_gazebo/launch/turtlebot3_world.launch.py').read_text()
    assert source.count('ld.add_action(gzclient_cmd)') == 1 and source.count('-r -s -v2 ') == 1
    source = source.replace('ld.add_action(gzclient_cmd)', '# no GUI')
    source = source.replace('-r -s -v2 ', '-r -s --headless-rendering -v2 ')
    path = ROOT/'headless.launch.py'; path.write_text(source); return path


def supervise(marker):
    stop_requested = False
    def stop(_sig, _frame):
        nonlocal stop_requested
        stop_requested = True
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    os.environ['ROSA_TB3_RUN_ID'] = marker
    env = environment(marker)
    with (ROOT/'supervisor.log').open('a', buffering=1) as out:
        sys.stdout = out; sys.stderr = out
        world = nav = None
        try:
            launch = prepare_launch()
            world = shell(f'ros2 launch {launch}', env, out)
            # Allow the world to start before Nav2, but fail if the launcher exits.
            for _ in range(20):
                if stop_requested or world.poll() is not None: raise RuntimeError('world stopped during startup')
                time.sleep(.5)
            nav = shell('ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True autostart:=True map:=/opt/ros/jazzy/share/turtlebot3_navigation2/map/map.yaml params_file:=/opt/ros/jazzy/share/turtlebot3_navigation2/param/burger.yaml', env, out)
            print(f'world launcher={world.pid} nav launcher={nav.pid}', flush=True)
            while not stop_requested:
                if world.poll() is not None or nav.poll() is not None:
                    print('A launch process exited; stopping the owned stack.', flush=True); break
                time.sleep(.5)
        except Exception as exc:
            print(f'supervisor error: {exc}', flush=True)
        finally:
            ok = terminate_owned(marker, exclude=(os.getpid(),), graceful_pids=tuple(p.pid for p in (nav, world) if p is not None))
            (ROOT/'cleanup.json').write_text(json.dumps({'marker':marker, 'clean':ok, 'remaining':owned(marker, (os.getpid(),))})+'\n')
            if not ok: sys.exit(1)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command', choices=('start','stop','status','supervise')); parser.add_argument('--marker'); a=parser.parse_args()
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    if a.command=='supervise': supervise(a.marker); return
    with (ROOT/'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(STATE.read_text()) if STATE.exists() else None
        if a.command=='start':
            if state and owned(state['marker']): raise SystemExit('Owned processes still exist; stop them first.')
            env=environment('precheck')
            check=subprocess.run(['/bin/bash','-c','source /opt/ros/jazzy/setup.bash && exec ros2 node list --no-daemon'],env=env,capture_output=True,text=True,timeout=12)
            if check.returncode != 0 or check.stdout.strip(): raise SystemExit('ROS domain 219 is not confirmed empty; refusing to start: '+check.stdout+check.stderr)
            marker=uuid.uuid4().hex
            if (ROOT/'cleanup.json').exists(): (ROOT/'cleanup.json').unlink()
            p=subprocess.Popen([sys.executable,str(SCRIPT),'supervise','--marker',marker],env=environment(marker),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            STATE.write_text(json.dumps({'marker':marker,'supervisor':p.pid})+'\n')
            print(f'Started supervisor {p.pid}; log {ROOT}/supervisor.log; marker {marker}')
        elif a.command=='status':
            if not state: print('No recorded stack.'); return
            print(json.dumps({'state':state,'processes':owned(state['marker'])}))
        elif a.command=='stop':
            if not state: print('No recorded stack.'); return
            marker=state['marker']; pid=state['supervisor']
            if process_marker(pid,marker):
                os.kill(pid,signal.SIGTERM)
                until=time.monotonic()+25
                while time.monotonic()<until and process_marker(pid,marker): time.sleep(.2)
            ok=terminate_owned(marker,exclude=(os.getpid(),))
            remain=owned(marker,exclude=(os.getpid(),))
            print('STOP', 'PASS' if ok and not remain else 'FAIL', 'remaining',remain)
            if not ok or remain: sys.exit(1)
            STATE.unlink(missing_ok=True)

if __name__=='__main__': main()
