"""Provider-free native CLI regression for the source claude_only defaults."""
from pathlib import Path
import json
import os
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[3]
STAGES=['plan','plan_review','work','final_review','closeout']

@pytest.mark.parametrize('phase',['implementation_testing','architecture_docs','sysadmin'])
def test_claude_only_five_opus_high_with_gemini_and_luna(tmp_path,phase):
    home=tmp_path/'apgr';home.mkdir()
    (home/'config.toml').write_text('[dispatcher.bundle]\nrequired = true\n')
    env={k:v for k,v in os.environ.items() if not k.startswith(('APGR_','AGENT_CENTRAL_'))
         and k not in ('PYTHONPATH','PYTHONHOME')}
    env.update(APGR_HOME=str(home),PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([str(ROOT/'bin/apgr-dispatcher-bundle'),'project','--source-dir',
                    str(ROOT/'common/dispatcher'),'--apgr-home',str(home)],
                   cwd=ROOT,env=env,check=True,capture_output=True,timeout=30)
    request=tmp_path/'request.json'
    request.write_text(json.dumps({'schema':'agent-phase-request-v1','phase_type':phase,
                       'execution_mode':'claude_only','prompt':'Resolve only; do not execute providers.'}))
    result=subprocess.run([str(ROOT/'bin/agent-phase-resolve'),str(request),'--apgr-home',str(home),
                          '--lifecycle','standard','--finalization','checkpoint'],
                         cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=30)
    record=json.loads(result.stdout)
    assert record['execution_mode']=='claude_only'
    assert record['expected_stages']==STAGES
    for name in STAGES:
        row=record['stages'][name];i=row['intelligence'];c=row['worker_capability']
        assert (row['provider'],i['model'],i['effort'])==('claude','claude-opus-5-5','high')
        assert c['available'] is True and c['allowed'] is True
        assert set(c['allowed_worker_kinds'])=={'gemini','luna'}
        assert c['policy_selection']=='triple_pool_4x4x4' and c['borrowing'] is False
        assert c['limits']['max_gemini']==4 and c['limits']['max_luna']==4
        assert c['gemini_worker']['provider']=='antigravity'
        assert (c['luna_worker']['model'],c['luna_worker']['effort'],c['luna_worker']['transport'])==('gpt-6-luna','max','codex_external')
        assert row['process_read_only'] is (name in ('plan','plan_review','final_review'))
