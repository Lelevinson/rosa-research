"""Load-only check: load one model into our own Ollama at a given num_ctx WITHOUT generating, report how much of it sits on the GPU, then unload.
LABEL: merged-method demo, lab setup, demonstration only, not evaluated, not for the paper.
Usage: python lab_load_check.py <model> <num_ctx> [endpoint]   (stdlib only)"""
import json
import sys
import time
import urllib.request

model, ctx = sys.argv[1], int(sys.argv[2])
base = sys.argv[3] if len(sys.argv) > 3 else 'http://127.0.0.1:11449'


def call(path, body=None, timeout=300):
    request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


started = time.time()
call('/api/generate', {'model': model, 'prompt': '', 'stream': False, 'keep_alive': '5m', 'options': {'num_ctx': ctx, 'use_mmap': True}})
seconds = round(time.time() - started, 1)
loaded = next((m for m in call('/api/ps')['models'] if m['name'] == model), None)
result = {'model': model, 'num_ctx': ctx, 'load_seconds': seconds, 'size_bytes': loaded and loaded['size'], 'size_vram_bytes': loaded and loaded['size_vram'],
          'fully_on_gpu': bool(loaded and loaded['size'] == loaded['size_vram']), 'gpu_fraction': loaded and round(loaded['size_vram'] / loaded['size'], 4),
          'context_length': loaded and loaded.get('context_length')}
call('/api/generate', {'model': model, 'prompt': '', 'stream': False, 'keep_alive': 0})
print(json.dumps(result))
