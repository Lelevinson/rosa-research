"""Download the required local model through an already-running Ollama server."""
import argparse
import json
from urllib.request import ProxyHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--model', default='qwen3.5:9b')
    args = parser.parse_args()
    request = Request(args.base_url.rstrip('/') + '/api/pull',
                      data=json.dumps({'model': args.model, 'stream': True}).encode(),
                      headers={'Content-Type': 'application/json'})
    previous = None
    succeeded = False
    with build_opener(ProxyHandler({})).open(request, timeout=600) as response:
        for line in response:
            event = json.loads(line)
            if event.get('error'):
                raise RuntimeError(event['error'])
            total, completed = event.get('total', 0), event.get('completed', 0)
            percent = int(completed / total * 100) if total else None
            marker = (event.get('status'), percent // 10 if percent is not None else None)
            if marker != previous:
                print(event.get('status', ''), f'{percent}%' if percent is not None else '', flush=True)
                previous = marker
            succeeded = event.get('status') == 'success'
    if not succeeded:
        raise RuntimeError('Download stream ended without success.')


if __name__ == '__main__':
    main()
