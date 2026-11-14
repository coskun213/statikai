"""Capture real command output, timing, exit code and source fingerprints."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    root = args.root.resolve()
    target = root / 'audit_results' / 'logs'
    target.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    paths = list(root.glob('*.py')) + list((root/'statikai').glob('*.py'))
    sources = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    t0 = time.perf_counter()
    process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding='utf8', errors='replace')
    expired = []
    def stop():
        expired.append(True)
        process.kill()
    timer=threading.Timer(args.timeout,stop)
    timer.start()
    with (target / f'{args.name}.log').open('w',encoding='utf8') as handle:
        for line in process.stdout:
            handle.write(line);handle.flush()
            print(line,end='',flush=True)
    code=process.wait()
    timer.cancel()
    if expired: code=124
    report = dict(command=command, cwd=str(root), started_utc=started,
                  elapsed_seconds=round(time.perf_counter()-t0, 3),
                  exit_code=code, source_sha256=sources)
    (target / f'{args.name}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
