import asyncio
from copy import deepcopy
import threading
import unittest
from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from rosa_reliability import ControlledStop, ExecutionSession, make_tools


class MemoryTransport:
    def __init__(self):
        self.values = {'/left': {'angle': 1}, '/right': {'angle': 9}}
        self.dispatches = []

    def read(self, node, names):
        self.dispatches.append(('read', node))
        return {k: self.values[node][k] for k in names}

    def write(self, node, values):
        self.dispatches.append(('write', node))
        self.values[node].update(values)
        return {'accepted': True}


class Capture(BaseCallbackHandler):
    def __init__(self):
        self.starts, self.ends, self.errors = [], [], []

    def on_tool_start(self, serialized, input_str, **kw):
        self.starts.append(kw['run_id'])

    def on_tool_end(self, output, **kw):
        self.ends.append(kw['run_id'])

    def on_tool_error(self, error, **kw):
        self.errors.append(kw['run_id'])


class ReliabilityTests(unittest.TestCase):
    def session(self, **kw):
        transport = MemoryTransport()
        session = ExecutionSession(transport, deepcopy(transport.values), **kw)
        return session, {t.name: t for t in make_tools(session)}

    def test_distinct_node_values_roundtrip_and_explicit_verification(self):
        s, tools = self.session()
        read = tools['read_state'].invoke({'nodes': ['/left', '/right']})
        self.assertEqual(read['observed_values'], s.targets)
        self.assertIn('fresh_verification_required', tools['submit_report'].invoke(
            {'status': 'SUCCESS', 'observed_values': read['observed_values']}))
        observed = tools['verify_outcome'].invoke({})
        report = tools['submit_report'].invoke({'status': 'SUCCESS', 'observed_values': observed['observed_values']})
        self.assertTrue(report['report_accepted'])
        self.assertEqual(s.validation_errors, 1)

    def test_schema_failure_recovers_without_native_dispatch_or_value_coercion(self):
        s, tools = self.session()
        bad = tools['write_state'].invoke({'node_name': '/left', 'values': {'angle': True}})
        self.assertIn('schema_validation', bad)
        self.assertFalse(s.transport.dispatches)
        self.assertIn('invalid_node_scope', tools['read_state'].invoke({'nodes': ['left']}))
        self.assertFalse(s.transport.dispatches)
        self.assertEqual(tools['read_state'].invoke({'nodes': ['/left']})['observed_values'], {'/left': {'angle': 1}})

    def test_read_write_and_automatic_check_share_predispatch_budget(self):
        s, tools = self.session(operation_limit=2, automatic_verification=True)
        tools['read_state'].invoke({'nodes': ['/left']})
        with self.assertRaisesRegex(ControlledStop, 'native_operation_budget'):
            tools['write_state'].invoke({'node_name': '/left', 'values': {'angle': 3}})
        self.assertEqual(s.transport.dispatches, [('read', '/left'), ('write', '/left')])
        self.assertIsNone(s.verification)
        with self.assertRaises(ControlledStop):
            tools['write_state'].invoke({'node_name': '/right', 'values': {'angle': 2}})
        self.assertEqual(len(s.transport.dispatches), 2)

    def test_freshness_and_swapped_node_reports_are_rejected(self):
        s, tools = self.session()
        observed = tools['verify_outcome'].invoke({})
        swapped = {'/left': {'angle': 9}, '/right': {'angle': 1}}
        self.assertIn('report_observation_mismatch', tools['submit_report'].invoke({'status': 'SUCCESS', 'observed_values': swapped}))
        tools['write_state'].invoke({'node_name': '/left', 'values': {'angle': 2}})
        self.assertIn('fresh_verification_required', tools['submit_report'].invoke({'status': 'SUCCESS', 'observed_values': observed['observed_values']}))
        tools['verify_outcome'].invoke({})
        self.assertIn('unsupported_success', tools['submit_report'].invoke({'status': 'SUCCESS', 'observed_values': s.verification['observed_values']}))
        self.assertFalse(any(r['accepted'] for r in s.reports))

    def test_controlled_stop_closes_real_langchain_callbacks_and_explicit_spans(self):
        provider, exporter = TracerProvider(), InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        s, tools = self.session(validation_limit=1, tracer=provider.get_tracer('test'))
        capture = Capture()
        t = tools['read_state']
        t.callbacks = [capture]
        t.invoke({'nodes': ['wrong']})
        with self.assertRaises(ControlledStop):
            t.invoke({'nodes': ['wrong']})
        self.assertEqual(set(capture.starts), set(capture.ends + capture.errors))
        spans = exporter.get_finished_spans()
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[-1].status.status_code.name, 'ERROR')
        self.assertTrue(all(e['status'] != 'STARTED' for e in s.events if e['type'] == 'tool'))
        provider.shutdown()

    def test_async_cancellation_waits_for_bounded_dispatch_and_terminal_callbacks(self):
        s, tools = self.session()
        entered, release = threading.Event(), threading.Event()
        original = s.transport.read
        def delayed(node, names):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('bounded_test_read')
            return original(node, names)
        s.transport.read = delayed
        capture = Capture()
        tools['read_state'].callbacks = [capture]
        async def run():
            task = asyncio.create_task(tools['read_state'].ainvoke({'nodes': ['/left']}))
            await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        asyncio.run(run())
        self.assertEqual(capture.starts, capture.ends)
        self.assertEqual(s.budget.events[0]['status'], 'RETURNED')

    def test_feedback_forms_preserve_identical_facts_and_retry_limits(self):
        import json
        plain, p = self.session()
        structured, q = self.session(structured_feedback=True)
        a = p['read_state'].invoke({'nodes': ['wrong']})
        b = json.loads(q['read_state'].invoke({'nodes': ['wrong']}))
        for k, v in b.items():
            self.assertIn(f'{k}={json.dumps(v, sort_keys=True)}', a)
        self.assertEqual(plain.validation_errors, structured.validation_errors)

    def test_missing_observation_is_unknown_and_trace_is_closed(self):
        s, tools = self.session()
        def fail(*args):
            raise TimeoutError('read_timeout')
        s.transport.read = fail
        capture = Capture()
        tools['read_state'].callbacks = [capture]
        result = tools['verify_outcome'].invoke({})
        self.assertIsNone(result['goal_reached'])
        self.assertIsNone(result['observed_values']['/left']['angle'])
        report = tools['submit_report'].invoke({'status': 'UNKNOWN', 'observed_values': result['observed_values']})
        self.assertTrue(report['report_accepted'])
        self.assertEqual(s.budget.events[-1]['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
