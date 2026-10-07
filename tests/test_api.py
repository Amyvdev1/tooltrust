from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_malformed_schema_returns_422():
    response=client.post('/api/evaluate',json={'parameters':{'type':'object','properties':[]}})
    assert response.status_code==422
def test_evaluate_endpoint():
    r=client.post('/api/evaluate',json={'name':'get_status','description':'Read the current order status without changing external records or state.','parameters':{'type':'object','properties':{}},'error_contract':{'code':'x','message':'x','next_action':'x'}})
    assert r.status_code==200 and 'reliability_score' in r.json()
