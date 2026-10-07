from pathlib import Path
from typing import Any
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .core import evaluate_tool,replay_call
BASE=Path(__file__).resolve().parent
app=FastAPI(title='ToolTrust',version='1.0.0',description='AI agent tool reliability and safety lab')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
class Replay(BaseModel):
    tool:dict[str,Any]; arguments:dict[str,Any]=Field(default_factory=dict); confirmed:bool=False; permissions:list[str]=Field(default_factory=list)
@app.get('/',include_in_schema=False)
def home(): return FileResponse(BASE/'static'/'index.html')
@app.get('/health')
def health(): return {'status':'ok','service':'tooltrust','version':'1.0.0'}
@app.post('/api/evaluate')
def evaluate(tool:dict[str,Any]): return evaluate_tool(tool)
@app.post('/api/replay')
def replay(payload:Replay): return replay_call(payload.tool,payload.arguments,payload.confirmed,payload.permissions)
