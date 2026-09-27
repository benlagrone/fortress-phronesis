"""Read-only, bounded adapters. Credentials stay in the collector process."""
import asyncio,json,os,time,hashlib
from pathlib import Path
from urllib.parse import quote
import httpx
import websockets

def node(id,name,kind,**attrs):return dict(id=id,name=str(name)[:256],kind=kind,**attrs)
def edge(a,b,p):return dict(source=a,target=b,predicate=p)
async def pages(client,url,headers):
 result=[];offset=0
 for _ in range(100):
  r=await client.get(url,params={'offset':offset,'limit':200},headers=headers);r.raise_for_status();d=r.json()
  batch=d.get('data');total=d.get('totalCount')
  if not isinstance(batch,list) or not isinstance(total,int) or total<0:raise ValueError('invalid pagination')
  result.extend(batch)
  if len(result)>=total:return result
  if not batch:raise ValueError('incomplete pagination')
  offset+=len(batch)
 raise ValueError('page limit')
async def unifi(config):
 token=Path(config['token_file']).read_text().strip();base=config['url'].rstrip('/');headers={'X-API-Key':token}
 nodes=[];edges=[]
 async with httpx.AsyncClient(timeout=20,follow_redirects=False,verify=config.get('ca_file',True)) as c:
  for site in await pages(c,base+'/v1/sites',headers):
   sid='unifi:'+str(site['id']);nodes.append(node(sid,site.get('name','Site'),'site',state='observed'))
   for resource,kind in [('devices','device'),('clients','device')]:
    for item in await pages(c,base+'/v1/sites/'+quote(str(site['id']),safe='')+'/'+resource,headers):
     id=sid+':'+str(item['id'])
     attrs={k:item[k] for k in ['ipAddress','macAddress','model','type','state'] if k in item}
     nodes.append(node(id,item.get('name',item.get('ipAddress',item['id'])),kind,attributes=attrs,state='observed'))
     edges.append(edge(id,sid,'member_of'))
     if item.get('uplinkDeviceId'):edges.append(edge(id,sid+':'+str(item['uplinkDeviceId']),'attached_to'))
 return nodes,edges

async def homeassistant(config):
 token=Path(config['token_file']).read_text().strip();nodes=[];edges=[];prefix=config.get('id','homeassistant')
 async with websockets.connect(config['url'],open_timeout=15,max_size=4*1024*1024) as ws:
  hello=json.loads(await asyncio.wait_for(ws.recv(),15))
  if hello.get('type')!='auth_required':raise ValueError('HA handshake')
  await ws.send(json.dumps({'type':'auth','access_token':token}))
  auth=json.loads(await asyncio.wait_for(ws.recv(),15))
  if auth.get('type')!='auth_ok':raise PermissionError('HA auth')
  commands=[('config/area_registry/list','area'),('config/device_registry/list','ha_device'),('config/entity_registry/list','ha_entity')]
  for i,(command,kind) in enumerate(commands,1):
   await ws.send(json.dumps({'id':i,'type':command}));r=json.loads(await asyncio.wait_for(ws.recv(),20))
   if not r.get('success'):raise PermissionError('HA registry unavailable')
   for item in r['result']:
    key=item.get('id') or item.get('area_id') or item.get('entity_id');id=prefix+':'+kind+':'+key
    name=item.get('name_by_user') or item.get('name') or item.get('original_name') or key
    attrs={k:item[k] for k in ['manufacturer','model','platform','device_class'] if item.get(k)}
    nodes.append(node(id,name,kind,attributes=attrs,state='registered'))
    for field,targetkind,predicate in [('area_id','area','located_in'),('device_id','ha_device','provided_by'),('via_device_id','ha_device','integrated_via')]:
     if item.get(field):edges.append(edge(id,prefix+':'+targetkind+':'+item[field],predicate))
 return nodes,edges

async def mcp(config):
 """HTTP MCP lists only. Never tools/call, resources/read or prompts/get."""
 headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
 if config.get('token_file'):headers['Authorization']='Bearer '+Path(config['token_file']).read_text().strip()
 sid=config['id'];nodes=[node(sid,config.get('name',sid),'mcp_service',state='registered')];edges=[]
 async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
  counter=0
  async def call(method,params=None,notify=False):
   nonlocal counter
   counter+=1;payload={'jsonrpc':'2.0','method':method,'params':params or {}}
   if not notify:payload['id']=counter
   response=await client.post(config['url'],headers=headers,json=payload);response.raise_for_status()
   if response.headers.get('mcp-session-id'):headers['Mcp-Session-Id']=response.headers['mcp-session-id']
   if notify:return {}
   if len(response.content)>2*1024*1024:raise ValueError('MCP response bound')
   if 'text/event-stream' in response.headers.get('content-type',''):
    payloads=[json.loads(l[5:].strip()) for l in response.text.splitlines() if l.startswith('data:')]
    d=next((v for v in payloads if v.get('id')==counter),{})
   else:d=response.json()
   if d.get('error'):raise ValueError('MCP list error')
   return d.get('result',{})
  init=await call('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'fortess-dna','version':'0.1.0'}})
  headers['MCP-Protocol-Version']=init.get('protocolVersion','2025-06-18');await call('notifications/initialized',notify=True)
  caps=init.get('capabilities',{})
  for category,method,key,kind in [('tools','tools/list','tools','mcp_tool'),('resources','resources/list','resources','mcp_resource'),('resources','resources/templates/list','resourceTemplates','mcp_template'),('prompts','prompts/list','prompts','mcp_prompt')]:
   if category not in caps:continue
   cursor=None;seen=set()
   for _ in range(100):
    result=await call(method,{'cursor':cursor} if cursor else {})
    for item in result.get(key,[]):
     name=item.get('name') or item.get('uri') or item.get('uriTemplate');id=sid+':'+kind+':'+hashlib.sha256(str(name).encode()).hexdigest()[:24]
     # No resource contents or credentials; descriptions are inert bounded text.
     attrs={k:item[k] for k in ['description','inputSchema','mimeType','uri','uriTemplate'] if k in item}
     if len(json.dumps(attrs))>32768:attrs={'description':'Metadata exceeds safe display bound'}
     nodes.append(node(id,name,kind,attributes=attrs,state='available'));edges.append(edge(sid,id,'exposes'))
    cursor=result.get('nextCursor')
    if not cursor:break
    if cursor in seen:raise ValueError('MCP repeated cursor')
    seen.add(cursor)
   else:raise ValueError('MCP page bound')
 return nodes,edges

async def collect_loop(store,config):
 async def job(source):
  kind=source['kind'];id=source['id'];interval=max(5,int(source.get('interval',30)))
  while True:
   try:
    if kind in {'docker_spool','spool'}:
     p=Path(source['path']);payload=json.loads(p.read_text())
     if time.time()-payload['created_at']>60:raise TimeoutError('stale agent')
     if payload.get('status') not in (None,'healthy'):
      store.health(id,kind,payload['status'],payload.get('detail','Source failed'));await asyncio.sleep(interval);continue
     nodes,edges=payload['nodes'],payload['edges']
    elif kind=='unifi':nodes,edges=await unifi(source)
    elif kind=='homeassistant':nodes,edges=await homeassistant(source)
    elif kind=='mcp':nodes,edges=await mcp(source)
    else:raise ValueError('unsupported adapter')
    store.ingest(id,kind,nodes,edges,absence='destroyed' if kind=='docker_spool' else 'missing')
   except asyncio.CancelledError:raise
   except Exception as exc:
    # Never retain exception strings: provider payloads can include credentials.
    status='unauthorized' if isinstance(exc,PermissionError) or isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in (401,403) else 'unavailable'
    store.health(id,kind,status,type(exc).__name__)
   await asyncio.sleep(interval)
 await asyncio.gather(*(job(s) for s in config.get('sources',[])))
