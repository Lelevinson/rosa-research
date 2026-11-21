import json, os, time, urllib.request, sys
URL=os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")+"/api/chat"
def chat(model, think, tools=False):
    body=dict(model=model, stream=False, messages=[{"role":"user","content":"A node list returned an empty result. What is 17*23, and what should I check next? Answer in two sentences."}],
              options=dict(temperature=0.7, num_predict=1500, num_ctx=8192, seed=1), keep_alive="5m")
    if think is not None: body["think"]=think
    if tools: body["tools"]=[{"type":"function","function":{"name":"ros2_node_list","description":"List nodes","parameters":{"type":"object","properties":{"pattern":{"type":"string"}}}}}]
    t=time.time()
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request(URL,json.dumps(body).encode(),{"Content-Type":"application/json"}),timeout=180))
    except urllib.error.HTTPError as e:
        return dict(think=think, error=e.read().decode()[:160])
    m=r["message"]
    return dict(think=think, tools=tools, has_thinking_field=bool(m.get("thinking")), thinking_chars=len(m.get("thinking") or ""), content_chars=len(m.get("content") or ""),
                eval_count=r.get("eval_count"), prompt_eval=r.get("prompt_eval_count"), secs=round(time.time()-t,1), tool_calls=len(m.get("tool_calls") or []), content_head=(m.get("content") or "")[:90].replace("\n"," "),
                think_in_content=("<think>" in (m.get("content") or "")))
model=sys.argv[1]
settings=[False,True]+(["low","medium","high"] if model.startswith("gpt-oss") else [])+[None]
for s in settings:
    print(json.dumps(chat(model,s)))
print(json.dumps(chat(model,True,tools=True)))
