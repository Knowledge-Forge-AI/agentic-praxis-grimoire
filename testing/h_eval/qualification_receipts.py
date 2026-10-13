"""Exclusive attempt directories and exact candidate-bound command receipts."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import re
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def source_identity(root: Path = ROOT) -> dict:
    """Bind all tracked and nonignored new bytes without modifying any Git index."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    paths = sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')) - {b''})
    files = {}
    for raw in paths:
        name = os.fsdecode(raw)
        p = root / name
        if p.is_symlink():
            data, mode = os.fsencode(os.readlink(p)), '120000'
        elif p.is_file():
            data, mode = p.read_bytes(), '100755' if p.stat().st_mode & 0o111 else '100644'
        else:
            files[name] = {'deleted': True}
            continue
        files[name] = {'sha256': digest(data), 'bytes': len(data), 'mode': mode}
    return {'head_commit': git('rev-parse', 'HEAD').decode().strip(),
            'head_tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
            'candidate_identity_kind': 'sha256-canonical-path-mode-bytes-manifest-v1',
            'candidate_sha256': digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()),
            'files': files,
            'dirty_status': git('status', '--porcelain=v1', '-z').decode().split('\0')}


def new_attempt(parent: Path, suite: str) -> Path:
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', suite):
        raise ValueError('suite ID must be a simple path component')
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = parent / (suite + '-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex)
    path.mkdir(mode=0o700)
    return path


def run_command(argv, directory: Path, *, cwd: Path = ROOT, env=None) -> dict:
    before = source_identity(cwd)
    effective_env = dict(os.environ if env is None else env)
    resolved = shutil.which(argv[0], path=effective_env.get('PATH'))
    executable = Path(resolved).resolve() if resolved else None
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    tick = time.monotonic()
    with (directory / 'stdout').open('xb') as out, (directory / 'stderr').open('xb') as err:
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=err, check=False)
            exit_code = result.returncode
        except OSError as error:
            err.write((type(error).__name__ + ': command could not start\n').encode())
            exit_code = 127
    after = source_identity(cwd)
    value = {'schema': 'apg.qualification-command/v2', 'attempt_id': directory.name,
             'exact_argv': list(argv), 'cwd': str(cwd),
             'environment_digest': digest(json.dumps(effective_env, sort_keys=True, separators=(',', ':')).encode()),
             'executable': {'physical_path': str(executable) if executable else None,
                            'sha256': digest(executable.read_bytes()) if executable and executable.is_file() else None}, 'start_time': started,
             'end_time': dt.datetime.now(dt.timezone.utc).isoformat(),
             'duration_seconds': time.monotonic() - tick, 'exit_code': exit_code,
             'source_identity': before, 'source_unchanged': before == after,
             'end_candidate_sha256': after['candidate_sha256'],
             'artifacts': {name: {'path': name, 'sha256': digest((directory / name).read_bytes())}
                           for name in ('stdout', 'stderr')}}
    write_json(directory / 'command.json', value)
    return value


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--qualification-dir', type=Path, required=True)
    parser.add_argument('--suite', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('command required')
    attempt = new_attempt(args.qualification_dir.resolve() / 'command-receipts', args.suite)
    value = run_command(command, attempt)
    print(json.dumps({'attempt': str(attempt), 'exit_code': value['exit_code'], 'source_unchanged': value['source_unchanged']}))
    return value['exit_code'] if value['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
