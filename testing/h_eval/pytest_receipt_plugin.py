"""Opt-in pytest hook receipt: collection and every setup/call/teardown outcome."""
import json
import os
from pathlib import Path

_nodes = []
_reports = []
_collection_errors = []
_internal_errors = []


def pytest_collection_finish(session):
    _nodes.extend(item.nodeid for item in session.items)


def pytest_collectreport(report):
    if report.failed:
        _collection_errors.append({'nodeid': report.nodeid, 'outcome': 'error'})


def pytest_runtest_logreport(report):
    _reports.append({'nodeid': report.nodeid, 'when': report.when,
                     'outcome': report.outcome, 'wasxfail': getattr(report, 'wasxfail', None),
                     'strict_xpass': str(report.longrepr).startswith('[XPASS(strict)]')})


def pytest_internalerror(excrepr, excinfo):
    _internal_errors.append({'outcome': 'error', 'kind': type(excinfo.value).__name__})


def pytest_sessionfinish(session, exitstatus):
    target = Path(os.environ['APG_PYTEST_RECEIPT'])
    with target.open('x', encoding='utf-8') as stream:
        json.dump({'schema': 'apg.pytest-events/v1', 'collected_nodeids': _nodes,
                   'reports': _reports, 'collection_errors': _collection_errors, 'internal_errors': _internal_errors,
                   'exit_code': int(exitstatus)}, stream, sort_keys=True)
