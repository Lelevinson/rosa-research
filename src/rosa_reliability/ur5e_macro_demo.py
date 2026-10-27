"""Run seven deterministic public-API checks on the installed simulated UR5e.

python -m rosa_reliability.ur5e_macro_demo --output /tmp/unique-demo-directory
No model, account or credential is used. Creates output exclusively; no overwrite.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import signal

from .bounded_macro import SkillRegistry, StateSkill
from .gazebo_demo import GazeboDemo
from .ros_arm import ArmTransport, HOME_POSE, JOINTS


def registry():
    offset = {**HOME_POSE, 'shoulder_pan_joint': 0.18, 'wrist_3_joint': 0.16}
    return (SkillRegistry()
        .register(StateSkill(skill_id='ur5e.home', targets={'/ur5e': deepcopy(HOME_POSE)}))
        .register(StateSkill(skill_id='ur5e.offset', targets={'/ur5e': offset})))


def run_checks(folder, *, tracer=None, callbacks=()):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('ROS_DOMAIN_ID', '214')
    os.environ.setdefault('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST')
    simulator = GazeboDemo(folder / 'simulator')
    controller = observer = None
    rows, cleanup = [], None
    skills = registry()
    result = {'pass': False, 'live_model_requests': 0, 'decision_actor': 'deterministic_demo', 'rows': rows}
    try:
        simulator.start()
        controller, observer = ArmTransport(), ArmTransport(read_only=True)
        cases = [
            ('already_home', 'ur5e.home', None, 'SUCCESS', 0),
            ('move_offset', 'ur5e.offset', None, 'SUCCESS', 1),
            ('already_offset', 'ur5e.offset', None, 'SUCCESS', 0),
            ('ineffective_home', 'ur5e.home', 'ineffective', 'FAILURE', 1),
            ('missing_before_home', 'ur5e.home', 'missing', 'UNKNOWN', 0),
            ('return_home', 'ur5e.home', None, 'SUCCESS', 1),
            ('partial_offset', 'ur5e.offset', 'partial', 'FAILURE', 1),
        ]
        for name, selected, fault, expected, writes in cases:
            controller.suppress_commands = fault == 'ineffective'
            controller.missing_observations = fault == 'missing'
            controller.partial_commands = fault == 'partial'
            offset = len(controller.records)
            invocation = skills.open(controller, tracer=tracer)
            config = {'callbacks': list(callbacks)} if callbacks else None
            bundle = invocation.execute(selected, config=config)
            evidence = invocation.session.observations[-1]
            values = evidence['observed_values']['/ur5e']
            target = invocation.catalogue[selected]['/ur5e']
            status = ('UNKNOWN' if any(v is None for v in values.values()) else 'SUCCESS'
                      if all(abs(values[k] - v) <= invocation.limits.tolerance for k, v in target.items()) else 'FAILURE')
            report = invocation.submit_report(status, evidence['observation_id'], config=config)
            # Separate subscription/context; never used to choose the actor report.
            actual = observer.read('/ur5e', list(JOINTS))
            reached = all(abs(actual[k] - v) <= invocation.limits.tolerance for k, v in target.items())
            records = deepcopy(controller.records[offset:])
            dispatched = sum(r['kind'] == 'trajectory_request' for r in records)
            passed = (report['report_accepted'] and status == expected and dispatched == writes and
                      (status == 'UNKNOWN' or reached == (status == 'SUCCESS')))
            row = {'case': name, 'pass': passed, 'expected': expected, 'report': report,
                   'bundle': bundle, 'dispatches': dispatched, 'independent_goal_reached': reached,
                   'independent_observation': actual, 'observer_record': deepcopy(observer.records[-1]),
                   'transport_records': records, 'snapshot': invocation.snapshot()}
            rows.append(row)
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            if not passed:
                raise RuntimeError('deterministic_gazebo_check_failed:' + name)
        # Outside-invocation demonstration cleanup, explicitly accounted separately.
        controller.suppress_commands = controller.partial_commands = controller.missing_observations = False
        controller.read('/ur5e', list(JOINTS))
        receipt = controller.write('/ur5e', HOME_POSE)
        actual = observer.read('/ur5e', list(JOINTS))
        from .gazebo_demo import require_home
        require_home(actual)
        result['outside_trial_reset'] = {'receipt': receipt, 'independent_observation': actual, 'dispatches': 1}
        result['pass'] = len(rows) == 7 and all(row['pass'] for row in rows)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        for transport in (controller, observer):
            if transport:
                transport.close()
        cleanup = simulator.close()
        result['simulator_cleanup'] = cleanup
        (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError('demonstration_external_deadline_300_seconds')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 300)
    try:
        result = run_checks(args.output)
        print(json.dumps({'pass': result['pass'], 'cases': len(result['rows']), 'live_model_requests': 0}))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    main()
