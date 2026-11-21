"""Conversion tests. uv run python -m unittest discover -s research/studies/arg_type_retry_offline_20261119/tests"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import arg_type_retry as R  # noqa: E402

LIST_SCHEMA = {"type": "object", "properties": {"blacklist": {"type": "array", "items": {"type": "string"}}, "pattern": {"type": "string"}, "count": {"type": "integer"}, "flag": {"type": "boolean"},
                                                   "names": {"type": "array", "items": {"type": "string"}}, "ratio": {"type": "number"}}, "required": ["names"]}


def j(args, schema=LIST_SCHEMA, name="ros2_node_list"):
    return R.judge_call(name, args, schema)


class ConversionTests(unittest.TestCase):
    def test_valid_call_is_not_an_event(self):
        self.assertIsNone(j({"names": ["/a"], "blacklist": []}))

    def test_k3_empty_string_for_optional_array(self):
        v = j({"names": ["/a"], "blacklist": ""}); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"], {"names": ["/a"], "blacklist": []}); self.assertEqual(v["kinds"], ["K3"])
        self.assertTrue(j({"names": ["/a"], "blacklist": None})["fixable"])

    def test_k3_is_not_applied_to_a_required_array(self):
        v = j({"names": ""}); self.assertFalse(v["fixable"])

    def test_k1_json_string_to_array_and_object(self):
        v = j({"names": '["/a", "/b"]'}); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"]["names"], ["/a", "/b"]); self.assertEqual(v["kinds"], ["K1"])
        schema = {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}
        v = R.judge_call("t", {"request": '{"a": 1}'}, schema); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"], {"request": {"a": 1}})
        self.assertFalse(j({"names": "[not json"})["fixable"])
        self.assertFalse(j({"names": '{"a": 1}'})["fixable"])  # JSON of the wrong container type

    def test_k2_scalar_to_one_element_array(self):
        v = j({"names": "/a"}); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"]["names"], ["/a"]); self.assertEqual(v["kinds"], ["K2"])
        self.assertFalse(j({"names": 5})["fixable"])  # int is not accepted by the string items schema

    def test_k4_k5_k6_scalars(self):
        self.assertEqual(j({"names": ["/a"], "count": "12"})["converted"]["count"], 12)
        self.assertFalse(j({"names": ["/a"], "count": "012"})["fixable"]); self.assertFalse(j({"names": ["/a"], "count": "1.5"})["fixable"]); self.assertFalse(j({"names": ["/a"], "count": " 3"})["fixable"])
        self.assertEqual(j({"names": ["/a"], "ratio": "2.5"})["converted"]["ratio"], 2.5)
        self.assertEqual(j({"names": ["/a"], "flag": "True"})["converted"]["flag"], True); self.assertFalse(j({"names": ["/a"], "flag": "yes"})["fixable"])
        self.assertEqual(j({"names": ["/a"], "count": 3.0})["converted"]["count"], 3); self.assertFalse(j({"names": ["/a"], "count": 3.5})["fixable"])

    def test_exclusions_are_not_convertible(self):
        schema = {"type": "object", "properties": {"request": {"type": "string"}, "name": {"type": "string"}, "mode": {"type": "string", "enum": ["a", "b"]}}, "required": ["request"]}
        self.assertFalse(R.judge_call("t", {"request": {"x": 1}}, schema)["fixable"])      # object where string expected
        self.assertFalse(R.judge_call("t", {"request": 5}, schema)["fixable"])             # number where string expected
        self.assertFalse(R.judge_call("t", {}, schema)["fixable"])                         # missing required field
        self.assertFalse(R.judge_call("t", {"request": "x", "mode": "c"}, schema)["fixable"])  # enum
        self.assertFalse(R.judge_call("t", {"request": ["x"]}, schema)["fixable"])         # array where scalar expected

    def test_write_tools_are_never_fixable(self):
        v = R.judge_call("ros2_service_call", {"names": '["/a"]'}, LIST_SCHEMA); self.assertFalse(v["fixable"])

    def test_one_unfixable_problem_makes_the_call_unfixable(self):
        self.assertFalse(j({"names": '["/a"]', "count": "x"})["fixable"])

    def test_nested_items_are_converted(self):
        schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}}}, "required": ["items"]}
        v = R.judge_call("t", {"items": [{"n": "4"}, {"n": 5}]}, schema); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"]["items"], [{"n": 4}, {"n": 5}])

    def test_anyof_nullable_array_accepts_null_already(self):
        schema = {"type": "object", "properties": {"b": {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]}}}
        self.assertIsNone(R.judge_call("t", {"b": None}, schema))
        v = R.judge_call("t", {"b": ""}, schema); self.assertTrue(v["fixable"]); self.assertEqual(v["converted"], {"b": []})


if __name__ == "__main__":
    unittest.main()
