from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry
from referencing.exceptions import NoSuchResource, Unresolvable


def _deny_remote_reference(uri):
    raise NoSuchResource(ref=uri)


def parameter_validator(tool):
    schema = tool.get('parameters', {})
    if not isinstance(schema, dict):
        raise ValueError('parameters must be a JSON Schema object')
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError('Invalid parameter schema: ' + exc.message) from exc
    return Draft202012Validator(schema, registry=Registry(retrieve=_deny_remote_reference))

SEVERITY_PENALTY={"critical":24,"high":14,"medium":7,"low":3}
RISK_LEVELS={"read-only":1,"reversible-write":2,"irreversible-write":3,"external-side-effect":4}

@dataclass(frozen=True)
class Finding:
    rule:str; severity:str; category:str; message:str; next_action:str
    def to_dict(self): return asdict(self)


def _f(rows,rule,severity,category,message,next_action): rows.append(Finding(rule,severity,category,message,next_action))


def classify_risk(tool:dict[str,Any])->str:
    explicit=str(tool.get('risk') or '').strip()
    if explicit in RISK_LEVELS: return explicit
    name=str(tool.get('name') or '').lower(); desc=str(tool.get('description') or '').lower(); text=name+' '+desc+' '+str(tool.get('side_effects') or '').lower()
    if any(x in text for x in ('delete','cancel','terminate','refund','charge','send payment')): return 'irreversible-write'
    if any(x in text for x in ('create','update','write','schedule','send','post','ticket')): return 'external-side-effect'
    return 'read-only'


def evaluate_tool(tool:dict[str,Any])->dict[str,Any]:
    parameter_validator(tool)
    findings=[]
    name=str(tool.get('name') or '')
    description=str(tool.get('description') or '')
    schema=tool.get('parameters') or {}
    properties=schema.get('properties') or {} if isinstance(schema,dict) else {}
    required=set(schema.get('required') or []) if isinstance(schema,dict) else set()
    risk=classify_risk(tool)
    confirmation=bool(tool.get('requires_confirmation',False))
    side_effects=str(tool.get('side_effects') or '').strip()
    examples=tool.get('examples') or []
    idempotent=tool.get('idempotent')
    permissions=tool.get('permissions') or []
    error_contract=tool.get('error_contract') or {}

    if not re.fullmatch(r'[a-z][a-z0-9_]{2,63}',name): _f(findings,'unstable-name','medium','schema','Tool name is not a stable snake_case identifier.','Use a concise action-oriented snake_case name, e.g. create_support_ticket.')
    if len(description.split())<10: _f(findings,'weak-description','high','schema','Tool description is too vague for reliable selection.','Explain when to use the tool, what it changes, important constraints, and expected outcome.')
    if not isinstance(schema,dict) or schema.get('type')!='object': _f(findings,'invalid-parameter-root','high','schema','Parameter schema should be a JSON Schema object.','Set parameters.type to object and define typed properties.')
    if not properties: _f(findings,'missing-parameters','medium','schema','No parameter properties are defined.','Define the minimum explicit parameters the tool needs.')
    for param,definition in properties.items():
        if not isinstance(definition,dict):
            _f(findings,'invalid-parameter-definition','high','schema',f"Parameter '{param}' is not a schema object.",'Use a JSON Schema definition with type and description.'); continue
        if not definition.get('type') and not definition.get('oneOf') and not definition.get('$ref'): _f(findings,'parameter-type-missing','medium','schema',f"Parameter '{param}' has no type.",'Declare a JSON Schema type or explicit oneOf/$ref.')
        if len(str(definition.get('description') or '').split())<5: _f(findings,'ambiguous-parameter','medium','schema',f"Parameter '{param}' lacks semantic detail.",'Describe format, constraints, source of truth, and how the value changes behavior.')
        if definition.get('type')=='string' and any(word in param.lower() for word in ('status','type','mode','action')) and not definition.get('enum'):
            _f(findings,'open-ended-control-string','medium','schema',f"Control parameter '{param}' is an unrestricted string.",'Use an enum when only a known set of values is valid.')
    unknown_required=required-set(properties)
    if unknown_required: _f(findings,'unknown-required-field','high','schema',f"Required fields are missing from properties: {sorted(unknown_required)}.",'Keep required and properties consistent.')
    if properties and not required: _f(findings,'missing-required-contract','low','schema','No required parameters are declared.','Mark inputs that must be present; keep truly optional inputs optional.')
    if risk in {'irreversible-write','external-side-effect'} and not confirmation: _f(findings,'confirmation-missing','critical','safety','A high-impact tool can execute without human confirmation.','Require confirmation and show an execution preview before changing external state.')
    if risk!='read-only' and not side_effects: _f(findings,'side-effects-undocumented','high','safety','External side effects are not documented.','State exactly which record/system changes and whether the change can be reversed.')
    if risk!='read-only' and idempotent is None: _f(findings,'idempotency-unspecified','medium','reliability','Idempotency behavior is unspecified.','Declare whether repeated calls are safe and how duplicate execution is detected.')
    if RISK_LEVELS[risk]>=2 and not permissions: _f(findings,'permissions-missing','high','permissions','A state-changing tool declares no permissions.','Require the narrowest explicit permission or role that authorizes execution.')
    if not examples: _f(findings,'missing-examples','low','usability','No valid tool-call example is provided.','Add at least one valid call and one recoverable invalid example.')
    if not error_contract: _f(findings,'error-contract-missing','high','reliability','The tool has no structured error contract.','Return stable error codes, a human-readable message, and a recoverable next action.')
    else:
        for key in ('code','message','next_action'):
            if key not in error_contract: _f(findings,'error-field-missing','medium','reliability',f"Error contract is missing '{key}'.",'Expose code, message, and next_action so the agent can recover intentionally.')

    penalties={k:0 for k in ('schema','safety','permissions','reliability','usability')}
    for f in findings: penalties[f.category]+=SEVERITY_PENALTY[f.severity]
    category_scores={k:max(0,100-min(100,v)) for k,v in penalties.items()}
    reliability=round(category_scores['reliability']*.35+category_scores['schema']*.3+category_scores['safety']*.2+category_scores['permissions']*.1+category_scores['usability']*.05)
    return {'tool':name or 'unnamed_tool','risk':risk,'risk_level':RISK_LEVELS[risk],'reliability_score':reliability,'confirmation_required':confirmation,'category_scores':category_scores,'findings':[x.to_dict() for x in sorted(findings,key=lambda x:-SEVERITY_PENALTY[x.severity])],'execution_policy':execution_policy(tool,risk),'preview':confirmation_preview(tool,risk)}


def execution_policy(tool:dict[str,Any], risk:str|None=None)->dict[str,Any]:
    risk=risk or classify_risk(tool)
    requires_confirmation=bool(tool.get('requires_confirmation')) or risk in {'irreversible-write','external-side-effect'}
    return {'decision':'confirmation_required' if requires_confirmation else 'auto_allowed','risk':risk,'required_permissions':tool.get('permissions') or [],'idempotent':tool.get('idempotent'),'reason':'External or irreversible side effects require a human checkpoint.' if requires_confirmation else 'Read-only or explicitly low-risk action can be executed without a human checkpoint.'}


def confirmation_preview(tool:dict[str,Any],risk:str|None=None)->dict[str,Any]:
    risk=risk or classify_risk(tool)
    return {'action':tool.get('name') or 'unnamed_tool','risk':risk,'side_effects':tool.get('side_effects') or 'No side effects documented.','reversible':risk not in {'irreversible-write'},'requires_confirmation':bool(tool.get('requires_confirmation')) or risk in {'irreversible-write','external-side-effect'}}


def replay_call(tool:dict[str,Any],arguments:dict[str,Any],confirmed:bool=False,permissions:list[str]|None=None)->dict[str,Any]:
    validator = parameter_validator(tool)
    report=evaluate_tool(tool); policy=report['execution_policy']; permissions=set(permissions or [])
    missing=[p for p in policy['required_permissions'] if p not in permissions]
    trace=[{'stage':'schema_review','status':'pass' if report['category_scores']['schema']>=60 else 'warn'}]
    schema=tool.get('parameters') or {}; props=schema.get('properties') or {}; required=set(schema.get('required') or [])
    missing_args=[x for x in required if x not in arguments]
    unknown_args=[x for x in arguments if x not in props]
    try:
        errors = [{'path': '/'.join(str(p) for p in error.absolute_path), 'message': error.message}
                  for error in validator.iter_errors(arguments)]
    except Unresolvable as exc:
        errors = [{'path': '', 'message': 'Schema reference cannot be resolved locally; external fetching is disabled.'}]
    if missing_args or unknown_args or errors:
        trace.append({'stage':'argument_validation','status':'fail','missing':sorted(missing_args),'unknown':sorted(unknown_args),'errors':errors})
        return {'executed':False,'status':'validation_failed','trace':trace,'report':report}
    trace.append({'stage':'argument_validation','status':'pass'})
    if missing:
        trace.append({'stage':'permission_check','status':'fail','missing_permissions':missing})
        return {'executed':False,'status':'permission_denied','trace':trace,'report':report}
    trace.append({'stage':'permission_check','status':'pass'})
    if policy['decision']=='confirmation_required' and not confirmed:
        trace.append({'stage':'confirmation','status':'required'})
        return {'executed':False,'status':'confirmation_required','preview':report['preview'],'trace':trace,'report':report}
    trace.append({'stage':'confirmation','status':'pass' if policy['decision']=='confirmation_required' else 'not_required'})
    trace.append({'stage':'execution_simulator','status':'simulated_success'})
    return {'executed':True,'status':'simulated_success','result':{'ok':True,'tool':report['tool'],'arguments':arguments},'trace':trace,'report':report}
