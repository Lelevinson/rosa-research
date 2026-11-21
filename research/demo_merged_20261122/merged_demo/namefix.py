"""Answer name fix = his PUBLIC `namefix_rule.py` (name-rewrite v2, file unchanged) plus an answer_gate module.
answer_gate source: his file if env HIS_ANSWER_GATE points to it (its SHA-256 is recorded), else the labelled reconstruction `answer_gate_stub`."""
import hashlib
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent.parent
RULE_FILE = RESEARCH / 'studies' / 'name_fix_applied_20261117' / 'namefix_rule.py'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load():
    """Returns (rule module, answer_gate module, provenance dict). namefix_rule does `import answer_gate`, so the chosen module goes into sys.modules first."""
    his = os.environ.get('HIS_ANSWER_GATE')
    if his and Path(his).is_file():
        gate = _load('answer_gate', his)
        source = {'answer_gate_source': 'his_file', 'answer_gate_sha256': hashlib.sha256(Path(his).read_bytes()).hexdigest()}
    else:
        stub = HERE / 'answer_gate_stub.py'
        gate = _load('answer_gate', stub)
        source = {'answer_gate_source': 'RECONSTRUCTION from LEDGER_DEFINITION.md (not his file)',
                  'answer_gate_sha256': hashlib.sha256(stub.read_bytes()).hexdigest()}
    rule = _load('namefix_rule_demo', RULE_FILE)
    source['namefix_rule_sha256'] = hashlib.sha256(RULE_FILE.read_bytes()).hexdigest()
    return rule, gate, source


class NameFixer:
    def __init__(self):
        self.rule, self.gate, self.provenance = load()

    def apply(self, task_text, tool_outputs, answer):
        """Returns (rewritten answer, events, ledger size). The raw answer stays with the caller."""
        allowed = self.gate.allowed_names(task_text, tool_outputs)
        events = []
        rewritten = self.rule.rewrite_answer(answer, allowed, events)
        return rewritten, events, len(allowed)
