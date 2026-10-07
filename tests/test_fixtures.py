import json
from pathlib import Path
from app.core import evaluate_tool,replay_call
FIX=Path(__file__).parents[1]/"fixtures"

def load(name): return json.loads((FIX/name).read_text())

def test_safe_tool_beats_ambiguous_tool():
    assert evaluate_tool(load("safe-read-tool.json"))["reliability_score"] > evaluate_tool(load("ambiguous-tool.json"))["reliability_score"]

def test_risky_tool_requires_confirmation():
    tool=load("risky-write-tool.json")
    out=replay_call(tool,{"demo_id":"demo_42","reason":"Customer requested reschedule"},False,["demos:write"])
    assert out["status"] == "confirmation_required"
