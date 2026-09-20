"""Source-owned passing outer test for a deliberately failing fixture consumer."""

HIDDEN_TEST = r'''
def test_failure_cleanup_and_isolation():
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import xml.etree.ElementTree as ET

    # A fresh child directory inherits candidate conftest and its public fixtures.
    # The child failure is an assertion, not an xfail/skip accepted as execution.
    with tempfile.TemporaryDirectory(prefix="apg_lifecycle_", dir=Path.cwd()) as raw:
        root = Path(raw)
        test = root / "test_consumer.py"
        report = root / "results.xml"
        state = root / "observed.json"
        test.write_text("import json\nfrom pathlib import Path\n"
            "STATE = Path(" + repr(str(state)) + ")\n"
            "def test_failure(output):\n"
            "    assert not output.exists()\n"
            "    output.write_text('failed')\n"
            "    STATE.write_text(json.dumps(str(output)))\n"
            "    assert False, 'source-owned deliberate failure'\n"
            "def test_after_failure(output):\n"
            "    assert not Path(json.loads(STATE.read_text())).exists()\n"
            "    assert not output.exists()\n"
            "    output.write_text('independent')\n"
            "    STATE.write_text(json.dumps(str(output)))\n")
        command = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=",
                   "-o", "python_files=*.py", "-o", "python_functions=test_*",
                   "--junitxml=" + str(report), str(test)]
        result = subprocess.run(command, capture_output=True, timeout=15)
        assert result.returncode == 1, 'deliberate failure must execute'
        assert report.stat().st_size < 1000000
        cases = ET.parse(report).getroot().findall('.//testcase')
        assert [case.get('name') for case in cases] == ['test_failure', 'test_after_failure']
        assert len(cases[0].findall('failure')) == 1
        assert 'source-owned deliberate failure' in cases[0].find('failure').get('message', '')
        assert not cases[0].findall('skipped') and not cases[0].findall('error')
        assert not any(cases[1].findall(tag) for tag in ('failure', 'error', 'skipped')), \
            'subsequent consumer must pass without skip or error'
        assert not Path(json.loads(state.read_text())).exists(), 'final consumer must clean up'
'''
