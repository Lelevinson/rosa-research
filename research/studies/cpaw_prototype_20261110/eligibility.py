"""Inspect registry metadata without invoking tools or inferring semantics.

The optional trusted sidecar is supplied by the caller's separate permission and
registration system; tool metadata and model-authored claims are not authority.
"""
import json

def inspect_registry(registry, trusted=None):
    trusted=trusted or {}
    rows=[]
    for tool in registry:
        f=tool.func
        family=getattr(f,'__module__','unknown').rsplit('.',1)[-1]
        metadata=getattr(tool,'metadata',None) or {}
        auth=trusted.get(tool.name,{})
        typed=auth.get('outcome_contract')=='TRI_STATE_V1'
        read_only=auth.get('read_only') is True
        authorized=auth.get('authorized') is True
        argument_authorizer=callable(auth.get('authorize_arguments'))
        schema=tool.get_output_schema().model_json_schema()
        rows.append({'name':tool.name,'family':family,'class':type(tool).__name__,
                     'metadata':metadata,'output_schema':schema,
                     'informative_output_schema':bool(set(schema)-{'title','description'}),
                     'trusted_tri_state_registration':typed,
                     'trusted_read_only_authorization':read_only and authorized,
                     'trusted_argument_authorizer':argument_authorizer,
                     'eligible':typed and read_only and authorized and argument_authorizer})
    counts={}
    for family in sorted({r['family'] for r in rows}):
        selected=[r for r in rows if r['family']==family]
        counts[family]={'tools':len(selected),'eligible':sum(r['eligible'] for r in selected)}
    return {'description':'No invocations. Eligibility requires an independently supplied trusted sidecar; ROSATools provides none.',
            'count':len(rows),'eligible':sum(r['eligible'] for r in rows),
            'informative_output_schemas':sum(r['informative_output_schema'] for r in rows),
            'families':counts,'tools':rows}

def main():
    from rosa.tools import ROSATools
    print(json.dumps(inspect_registry(ROSATools(ros_version=2).get_tools()),indent=2,default=str))

if __name__=='__main__': main()
