"""H0 authority retention: repeated calls do not leak invocation files."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest
from agentic_praxis_grimoire import acquisition


def invoke(run, monkeypatch, attempt='attempt'):
    monkeypatch.setattr(acquisition, 'capture_catalog', lambda *a: ({'schema_version': 'apg.skill-catalog/v1'}, []))
    monkeypatch.setattr(acquisition.go_bridge, 'run', lambda argv, **kw: json.loads(Path(argv[-1]).read_text()))
    return acquisition.run_channel('skills', 'search', ['go', '--run-dir', str(run), '--run-id', 'run', '--binding-id', 'binding', '--attempt-id', attempt], {})


def test_repeated_authority_is_reused(tmp_path, monkeypatch):
    for _ in range(4):
        assert invoke(tmp_path, monkeypatch)['attempt_id'] == 'attempt'
    assert len(list(tmp_path.glob('acquisition-authority-*.json'))) == 1


def test_parallel_authorities_remain_distinct(tmp_path, monkeypatch):
    invoke(tmp_path, monkeypatch)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda n: invoke(tmp_path, monkeypatch, str(n)), range(12)))
    assert [r['attempt_id'] for r in results] == list(map(str, range(12)))


def test_retention_limit_preserves_old_authority(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, 'MAX_AUTHORITIES', 2)
    invoke(tmp_path, monkeypatch, 'one')
    invoke(tmp_path, monkeypatch, 'two')
    with pytest.raises(ValueError, match='authority retention limit'):
        invoke(tmp_path, monkeypatch, 'three')
    assert invoke(tmp_path, monkeypatch, 'one')['attempt_id'] == 'one'


def test_interrupted_publish_retains_bounded_pending(tmp_path, monkeypatch):
    original = acquisition.os.link
    monkeypatch.setattr(acquisition.os, 'link', lambda *a, **kw: (_ for _ in ()).throw(OSError('interrupted')))
    for _ in range(5):
        with pytest.raises(OSError, match='interrupted'):
            invoke(tmp_path, monkeypatch)
    assert len(list(tmp_path.iterdir())) == 2  # lock and one pending inode
    monkeypatch.setattr(acquisition.os, 'link', original)
    invoke(tmp_path, monkeypatch)
    assert not (tmp_path / '.acquisition-authority.pending').exists()


def test_interrupted_after_publish_preserves_immutable_bytes(tmp_path, monkeypatch):
    invoke(tmp_path, monkeypatch, 'one')
    path = next(tmp_path.glob('acquisition-authority-*.json'))
    before = path.read_bytes()
    acquisition.os.link(path, tmp_path / '.acquisition-authority.pending')
    invoke(tmp_path, monkeypatch, 'two')
    assert path.read_bytes() == before
    assert not (tmp_path / '.acquisition-authority.pending').exists()


def test_unsafe_authority_names_are_refused(tmp_path, monkeypatch):
    (tmp_path / '.acquisition-authority.pending').symlink_to(tmp_path / 'operator-config')
    with pytest.raises(OSError):
        invoke(tmp_path, monkeypatch)
    assert not (tmp_path / 'operator-config').exists()


def test_killed_writer_cannot_accumulate_pending(tmp_path):
    import os
    import signal
    import subprocess
    import sys
    import time
    script = '''
import os, sys, time
from pathlib import Path
from agentic_praxis_grimoire import acquisition
original = os.fsync
def pause(fd):
    original(fd)
    print('staged', flush=True)
    time.sleep(60)
acquisition.os.fsync = pause
acquisition.retain_authority(Path(sys.argv[1]), {'attempt_id': sys.argv[2]})
'''
    for n in range(3):
        child = subprocess.Popen([sys.executable, '-c', script, str(tmp_path), str(n)], stdout=subprocess.PIPE, text=True)
        try:
            assert child.stdout.readline().strip() == 'staged'
        finally:
            child.kill()
            child.wait(timeout=5)
            child.stdout.close()
    assert {p.name for p in tmp_path.iterdir()} == {'.acquisition-authority.lock', '.acquisition-authority.pending'}
    acquisition.retain_authority(tmp_path, {'attempt_id': 'recovered'})
    assert len(list(tmp_path.glob('acquisition-authority-*.json'))) == 1
