"""Behavioral checks for evidence boundaries; run with stdlib unittest."""
import copy
import unittest

from langchain_core.tools import tool
from pydantic import BaseModel

from discovery import Discovery, structural
from fixtures_development import bundle, temperature, renamed_argument, unrelated


class DiscoveryTests(unittest.TestCase):
    def test_documentation_keys_are_valid_argument_names(self):
        a = {"type": "object", "properties": {"description": {"type": "integer"}}}
        b = {"type": "object", "properties": {"title": {"type": "integer"}}}
        self.assertNotEqual(structural(a), structural(b))
        c = {"const": {"description": "x"}}
        d = {"const": {"description": "y"}}
        self.assertNotEqual(structural(c), structural(d))

    def test_opaque_text_in_wrappers_is_not_parsed_capability_evidence(self):
        for output in ({"raw": "load=17"}, {"echoes": ["load=17"]}):
            engine = Discovery()
            engine.refresh([bundle])
            self.assertFalse(engine.observe("bundle", {"item": 1}, output,
                                            snapshot="s1", successful=True))

    def populated(self, tools=(bundle, temperature), items=(0, 1, 4)):
        engine = Discovery()
        engine.refresh(list(tools))
        for item in items:
            for t in tools:
                args = {next(iter(t.args)): item}
                engine.observe(t.name, args, t.invoke(args), snapshot=f"s{item}", successful=True)
        return engine

    def test_support_is_scoped_and_fallback_keeps_original(self):
        engine = self.populated()
        pair = engine.pair("bundle", "temperature")
        self.assertTrue(pair["empirically_supported"])
        self.assertFalse(pair["replacement_allowed"])
        self.assertEqual(pair["semantic_equivalence"], "unestablished")
        calls = []
        result = engine.ordinary_call("temperature", {"item": 9},
                                      lambda name, args: calls.append((name, args)) or "original")
        self.assertEqual(result, "original")
        self.assertEqual(calls, [("temperature", {"item": 9})])

    def test_counterexample_revokes_support(self):
        engine = self.populated()
        engine.observe("bundle", {"item": 9}, {"temperature": 21.0}, snapshot="later", successful=True)
        engine.observe("temperature", {"item": 9}, {"temperature": 99.0}, snapshot="later", successful=True)
        self.assertEqual(engine.pair("bundle", "temperature")["fields"][0]["status"], "contradicted")

    def test_snapshots_arguments_and_schemas_must_match(self):
        engine = Discovery()
        engine.refresh([bundle, temperature, renamed_argument])
        for item in (0, 1, 4):
            engine.observe("bundle", {"item": item}, bundle.invoke({"item": item}), snapshot="a", successful=True)
            engine.observe("temperature", {"item": item}, temperature.invoke({"item": item}), snapshot="b", successful=True)
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])
        self.assertFalse(self.populated((bundle, renamed_argument)).pair("bundle", "renamed_argument")["arguments_compatible"])

    def test_constant_and_repeated_context_not_enough(self):
        engine = Discovery()
        engine.refresh([bundle, temperature])
        for snap in range(10):
            for name in ("bundle", "temperature"):
                engine.observe(name, {"item": 1}, {"temperature": 5.0}, snapshot=str(snap), successful=True)
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])
        for item in (2, 3, 4):
            for name in ("bundle", "temperature"):
                engine.observe(name, {"item": item}, {"temperature": 5.0}, snapshot=str(item), successful=True)
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])

    def test_invalid_and_error_outputs_cannot_preserve_support(self):
        for output, successful in [({"error": "failed"}, True), ({"success": True}, True),
                                   ("opaque text", True), ({"temperature": float("nan")}, True),
                                   ({"temperature": 5}, False), ({"temperature": (1, 2)}, True),
                                   ({"nested": {"error": "failed"}}, True)]:
            with self.subTest(output=output):
                engine = self.populated()
                self.assertFalse(engine.observe("bundle", {"item": 8}, output,
                                                snapshot="bad", successful=successful))
                self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])

    def test_missing_field_numeric_collision_and_conflict(self):
        engine = self.populated()
        engine.observe("bundle", {"item": 8}, {"pressure": 108.0}, snapshot="missing", successful=True)
        engine.observe("temperature", {"item": 8}, {"temperature": 19.0}, snapshot="missing", successful=True)
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])
        engine = self.populated()
        engine.observe("bundle", {"item": 8}, {"temperature": 19}, snapshot="type", successful=True)
        engine.observe("temperature", {"item": 8}, {"temperature": 19.0}, snapshot="type", successful=True)
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])
        engine = self.populated()
        self.assertFalse(engine.observe("bundle", {"item": 0}, {"temperature": 99.0}, snapshot="s0", successful=True))
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])

    def test_refresh_new_tools_revisions_removal_and_duplicates(self):
        engine = self.populated()
        engine.refresh([bundle, temperature, unrelated])
        self.assertTrue(engine.pair("bundle", "temperature")["empirically_supported"])
        self.assertFalse(engine.pair("bundle", "unrelated")["empirically_supported"])
        changed = temperature.model_copy(update={"description": "Changed tool"})
        engine.refresh([bundle, changed])
        self.assertFalse(engine.pair("bundle", "temperature")["empirically_supported"])
        self.assertIn("temperature", engine.revisions[-1]["invalidated"])
        engine.refresh([bundle])
        self.assertNotIn("temperature", engine.registry)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            engine.refresh([bundle, bundle])

    def test_observation_and_fallback_do_not_mutate_inputs(self):
        engine = self.populated()
        args, output = {"item": 11}, {"temperature": 25.0}
        before = copy.deepcopy((args, output))
        engine.observe("bundle", args, output, snapshot="s11", successful=True)
        output["temperature"] = 999.0
        args["item"] = 999
        stored = engine._observations[("bundle", "s11", '{"item":11}')]
        self.assertEqual(stored.arguments, before[0])
        original = {"item": 1}
        engine.ordinary_call("bundle", original, lambda name, kw: kw.update(item=9))
        self.assertEqual(original, {"item": 1})

    def test_metadata_and_declared_output_only_make_candidates(self):
        class Reading(BaseModel):
            temperature: float

        class Declared(type(temperature)):
            def get_output_schema(self, config=None):
                return Reading

        a = Declared(name="a", description="opaque one", args_schema=temperature.args_schema,
                     func=lambda item: {"temperature": item})
        b = Declared(name="b", description="distinct two", args_schema=temperature.args_schema,
                     func=lambda item: {"temperature": item + 1})
        engine = Discovery()
        engine.refresh([a, b])
        result = engine.pair("a", "b")
        self.assertTrue(result["candidate"])
        self.assertIn("declared_shared_paths", result["proposal_reasons"])
        self.assertFalse(result["empirically_supported"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
