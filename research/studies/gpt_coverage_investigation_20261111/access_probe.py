"""Read account-visible catalog with existing plan OAuth; never prints credentials."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

from rosa_llm import Config, create_client, package_info
from rosa_llm.errors import LLMError
from rosa_llm.storage import CredentialStore

HERE=Path(__file__).resolve().parent
OUT=next(p for p in HERE.parents if p.name == 'research')/'_artifacts/gpt_coverage_investigation_20261111'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    config=replace(Config.load(),provider='openai',openai_model='',require_explicit_model=False,timeout=30)
    store=CredentialStore(config.credential_dir)
    # Read only selected booleans/permission scopes. No token/identity is serialized.
    record=store.read('credentials.json').get(config.profile,{})
    state=dict(has_access_token=bool(record.get('access_token')),
               has_refresh_token=bool(record.get('refresh_token')),
               needs_login=bool(record.get('needs_login')),
               access_token_unexpired=record.get('expires_at',0)>time.time()+30,
               scopes=record.get('scopes',[]))
    result=dict(configuration=config.to_dict(),package=package_info(),auth_state=state,
                inference_requests=0,api_key_used=False,models=[])
    started=time.perf_counter()
    try:
        with create_client(config) as client:
            models=client.models()
        result['models']=models
        result['status']='catalog_ok'
        result['luna_ids']=[m['id'] for m in models if 'luna' in (m['id']+' '+m['display_name']).lower()]
    except LLMError as error:
        result['status']='blocked'
        result['error']=error.to_dict()
    except Exception as error:
        result['status']='blocked'
        result['error']={'type':type(error).__name__,'message':'Catalog probe failed; no raw exception/credentials serialized.'}
    result['seconds']=time.perf_counter()-started
    (OUT/'access_probe.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
