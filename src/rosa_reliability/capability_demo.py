"""Small two-capability demo. Selection may be deterministic or an actual LLM.

python -m rosa_reliability.capability_demo --mode deterministic \
  --skill ur5e.inspect_readiness --output /tmp/unique-capability-demo
"""
import argparse
import json
import os
from pathlib import Path
import signal

from .bounded_macro import StateSkill
from .capabilities import CapabilityRegistry, InspectionSkill
from .gazebo_demo import GazeboDemo
from .macro_agent import MacroROSA
from .ros_arm import ArmTransport, HOME_POSE, JOINTS
from .ros_readiness import ArmReadinessTransport

CHECKS = {'controllers': ['trajectory_controller_active', 'joint_state_broadcaster_active'],
          'joint_state': ['joint_sample_fresh']}


def registry():
    return (CapabilityRegistry()
        .register(StateSkill(skill_id='ur5e.home', targets={'/ur5e': dict(HOME_POSE)}))
        .register(StateSkill(skill_id='ur5e.offset', targets={'/ur5e':
            {**HOME_POSE, 'shoulder_pan_joint': 0.18, 'wrist_3_joint': 0.16}}))
        .register(InspectionSkill(skill_id='ur5e.inspect_readiness', subject='/ur5e_readiness', checks=CHECKS)))


def deterministic_report(invocation):
    """Explicit reference caller; never credited as an LLM classification."""
    evidence = invocation.session.observations[-1]
    values, targets = evidence['observed_values'], invocation.session.targets
    status = 'UNKNOWN' if any(v is None for group in values.values() for v in group.values()) else (
        'SUCCESS' if all(abs(values[n][k] - v) <= invocation.limits.tolerance
                         for n, group in targets.items() for k, v in group.items()) else 'FAILURE')
    return invocation.submit_report(status, evidence['observation_id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mode', choices=('deterministic', 'ollama', 'siwc'), default='deterministic')
    parser.add_argument('--skill', choices=('ur5e.home', 'ur5e.offset', 'ur5e.inspect_readiness'))
    parser.add_argument('--request')
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11434')
    args = parser.parse_args()
    if args.mode == 'deterministic' and not args.skill:
        parser.error('deterministic reference requires an explicitly resolved --skill')
    if args.mode != 'deterministic' and not args.request:
        parser.error('model demo requires --request')
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.setdefault('ROS_DOMAIN_ID', '216')
    os.environ.setdefault('ROS_AUTOMATIC_DISCOVERY_RANGE', 'LOCALHOST')
    simulator = GazeboDemo(args.output / 'simulator')
    movement = inspection = observer = llm = None
    result = {'mode': args.mode, 'pass': False, 'live_model_requests': 0}
    def expired(signum, frame): raise TimeoutError('capability_demo_external_deadline')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 300)
    try:
        simulator.start()
        movement, inspection, observer = ArmTransport(), ArmReadinessTransport(), ArmTransport(read_only=True)
        invocation = registry().open({'state': movement, 'inspection': inspection})
        if args.mode == 'deterministic':
            invocation.execute(args.skill)
            answer = deterministic_report(invocation)
        elif args.mode == 'ollama':
            from rosa_backends.chat_ollama import ConfiguredChatOllama
            llm = ConfiguredChatOllama(model='qwen3.5:9b', base_url=args.ollama_url, streaming=False,
                reasoning=False, num_ctx=8192, num_predict=1024, temperature=0, seed=42,
                use_mmap=True, client_kwargs={'timeout': 180}, cache=False)
            agent = MacroROSA(llm, invocation, backend='ollama')
            answer = agent.invoke(args.request)
            result['inference'] = agent.inference_budget.snapshot()
            result['live_model_requests'] = agent.inference_budget.calls
        else:
            from rosa_auth.remembered import remembered_session
            from rosa_auth.responses import SiwcBackend
            from rosa_backends.chat_siwc import ChatSiwc
            status = {}
            with remembered_session(request_budget=8, status=status) as auth:
                transport = SiwcBackend(request_budget=8, token_provider=auth.access_token)
                llm = ChatSiwc(model='gpt-6.1-sol', backend=transport)
                try:
                    agent = MacroROSA(llm, invocation, backend='siwc')
                    answer = agent.invoke(args.request)
                    result['inference'] = agent.inference_budget.snapshot()
                    result['live_model_requests'] = agent.inference_budget.calls
                    transport.raise_if_unavailable()
                finally: llm.close()
            result['authorization'] = status
        result.update(answer=answer, snapshot=invocation.snapshot(),
            independent_joint_observation=observer.read('/ur5e', list(JOINTS)),
            accepted_report=bool(invocation.session.reports and invocation.session.reports[-1]['accepted']))
        result['pass'] = result['accepted_report']
    finally:
        for item in (movement, inspection, observer):
            if item: item.close()
        result['simulator_cleanup'] = simulator.close()
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'accepted_report': result['accepted_report'],
                      'live_model_requests': result['live_model_requests']}))


if __name__ == '__main__': main()
