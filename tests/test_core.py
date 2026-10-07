from app.core import evaluate_tool,replay_call,classify_risk

def safe_tool(): return {'name':'cancel_demo','description':'Cancel one scheduled demo after validating the record and the explicit current user intent safely.','risk':'external-side-effect','requires_confirmation':True,'side_effects':'Changes demo status to cancelled.','idempotent':True,'permissions':['demos:write'],'parameters':{'type':'object','properties':{'demo_id':{'type':'string','description':'Stable identifier of the scheduled demo record.'}},'required':['demo_id']},'examples':[{'demo_id':'d1'}],'error_contract':{'code':'string','message':'string','next_action':'string'}}

def test_risky_tool_without_confirmation_fails():
    t=safe_tool();t['requires_confirmation']=False
    assert any(f['rule']=='confirmation-missing' for f in evaluate_tool(t)['findings'])

def test_safe_tool_scores_high(): assert evaluate_tool(safe_tool())['reliability_score']>=90

def test_replay_stops_for_confirmation():
    d=replay_call(safe_tool(),{'demo_id':'d1'},confirmed=False,permissions=['demos:write'])
    assert d['status']=='confirmation_required' and not d['executed']

def test_replay_requires_permission():
    d=replay_call(safe_tool(),{'demo_id':'d1'},confirmed=True,permissions=[])
    assert d['status']=='permission_denied'

def test_replay_executes_after_checks():
    d=replay_call(safe_tool(),{'demo_id':'d1'},confirmed=True,permissions=['demos:write'])
    assert d['executed'] is True

def test_heuristic_risk_classification(): assert classify_risk({'name':'delete_customer','description':'Delete customer record permanently'})=='irreversible-write'
