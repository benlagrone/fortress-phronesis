import asyncio,json,os,secrets,time,hashlib,hmac
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from .store import Store
from .ontology import compile_directory,InvalidOntology
from .collectors import collect_loop

def create_app(config_path=None):
 config_path=Path(config_path or os.environ.get('DNA_CONFIG','/config/config.json'))
 config=json.loads(config_path.read_text());store=Store(config['database']);sessions={}
 def auth_config():return json.loads(Path(config['auth_file']).read_text())
 def actor(request):
  cfg=auth_config();auth=request.headers.get('authorization','');token=auth[7:] if auth.startswith('Bearer ') else ''
  if not token:
   session=sessions.get(request.cookies.get('dna_session',''))
   if session and session['expires']>time.time():token=session['token']
  digest=hashlib.sha256(token.encode()).hexdigest()
  for identity in cfg['identities']:
   if token and not identity.get('revoked') and hmac.compare_digest(identity['sha256'],digest):return identity,digest
  raise HTTPException(401,'Sign in to Fortess DNA')
 @asynccontextmanager
 async def lifespan(app):
  task=asyncio.create_task(collect_loop(store,config))
  async def definitions():
   last=None
   while True:
    try:
     folder=config.get('definitions_dir')
     if folder:
      # Deployment provides an immutable reviewed bundle, never arbitrary Git fetch.
      marker=Path(folder)/'REVISION';revision=marker.read_text().strip()
      if revision!=last:
       bundle=compile_directory(folder,revision);store.activate(bundle);last=revision
       store.health('ontology','ontology','healthy')
    except Exception as e:store.health('ontology','ontology','invalid_candidate',type(e).__name__)
    await asyncio.sleep(10)
  ontology_task=asyncio.create_task(definitions())
  yield
  task.cancel();ontology_task.cancel()
  await asyncio.gather(task,ontology_task,return_exceptions=True)
 app=FastAPI(lifespan=lifespan);app.state.store=store
 @app.middleware('http')
 async def boundaries(request,call_next):
  if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0'))>131072:return JSONResponse({'detail':'request too large'},413)
  if request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('origin'):
   if request.headers['origin'].rstrip('/') not in config.get('origins',[]):return JSONResponse({'detail':'origin denied'},403)
  response=await call_next(request)
  response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"})
  return response
 @app.get('/healthz')
 def health():return {'service':'fortess-dna','status':'ok','version':'0.1.0'}
 @app.post('/api/session')
 async def login(request:Request):
  data=await request.json();token=data.get('token','')
  if not isinstance(token,str) or len(token)>256:raise HTTPException(401,'Invalid credential')
  digest=hashlib.sha256(token.encode()).hexdigest()
  found=next((i for i in auth_config()['identities'] if not i.get('revoked') and hmac.compare_digest(i['sha256'],digest)),None)
  if not found:raise HTTPException(401,'Invalid credential')
  if len(sessions)>100:sessions.clear()
  sid=secrets.token_urlsafe(32);sessions[sid]={'token':token,'expires':time.time()+28800}
  r=JSONResponse({'name':found['name'],'role':found['role']});r.set_cookie('dna_session',sid,httponly=True,secure=config.get('secure_cookie',True),samesite='strict',max_age=28800);return r
 @app.delete('/api/session')
 def logout(request:Request):
  sessions.pop(request.cookies.get('dna_session',''),None);r=JSONResponse({'ok':True});r.delete_cookie('dna_session');return r
 @app.get('/api/me')
 def me(request:Request):
  a,_=actor(request);return {'name':a['name'],'role':a['role'],'owner':'fortress-sextant:network-inventory','route':config.get('route','private'),'location':'unknown','authorization_epoch':hashlib.sha256(Path(config['auth_file']).read_bytes()).hexdigest()[:16]}
 def snapshot(request):
  a,_=actor(request);d=store.snapshot(a['role']=='admin');d['authorization_epoch']=hashlib.sha256(Path(config['auth_file']).read_bytes()).hexdigest()[:16];return d
 @app.get('/api/graph')
 def graph(request:Request,offset:int=0,limit:int=200,revision:int=-1,q:str='',kind:str=''):
  d=snapshot(request)
  if offset<0 or limit<1 or limit>500:raise HTTPException(400,'Invalid bounds')
  if revision!=-1 and revision!=d['revision']:raise HTTPException(409,'Snapshot changed; restart pagination')
  nodes=[n for n in d['nodes'] if (not q or q.lower() in (n['name']+' '+n['id']).lower()) and (not kind or n['kind']==kind)]
  d['total']=len(nodes);d['nodes']=nodes[offset:offset+limit];allowed={n['id'] for n in d['nodes']};d['edges']=[e for e in d['edges'] if e['source'] in allowed and e['target'] in allowed]
  d.pop('definitions');d['next_offset']=offset+limit if offset+limit<len(nodes) else None;return d
 @app.get('/api/node')
 def detail(request:Request,id:str):
  d=snapshot(request);n=next((n for n in d['nodes'] if n['id']==id),None)
  if not n:raise HTTPException(404,'Not found')
  return {'node':n,'relationships':[e for e in d['edges'] if id in (e['source'],e['target'])],'revision':d['revision']}
 @app.get('/api/events')
 async def events(request:Request):
  identity,identity_digest=actor(request);epoch=hashlib.sha256(Path(config['auth_file']).read_bytes()).hexdigest()
  async def stream():
   revision=-1
   while not await request.is_disconnected():
    try:
     _,digest=actor(request)
     if digest!=identity_digest or hashlib.sha256(Path(config['auth_file']).read_bytes()).hexdigest()!=epoch:raise HTTPException(401)
    except HTTPException:
     yield 'event: revoked\ndata: {}\n\n';return
    # Revision-only invalidations avoid leaking hidden object names or counts.
    current=int(store.meta('revision'))
    if current!=revision:
     yield 'event: revision\ndata: '+json.dumps({'revision':current})+'\n\n';revision=current
    else:yield ': heartbeat\n\n'
    await asyncio.sleep(2)
  return StreamingResponse(stream(),media_type='text/event-stream')
 @app.get('/api/proposals')
 def proposals(request:Request):
  a,_=actor(request)
  if a['role']!='admin':raise HTTPException(403,'Administrator required')
  return store.proposals()
 @app.post('/api/proposals/{id}/decision')
 async def decision(id:str,request:Request):
  a,_=actor(request)
  if a['role']!='admin':raise HTTPException(403)
  body=await request.json()
  if body.get('decision') not in {'accepted_for_authoring','rejected'}:raise HTTPException(400)
  with store.lock,store.db:
   row=store.db.execute('SELECT * FROM proposals WHERE id=?',(id,)).fetchone()
   if not row:raise HTTPException(404)
   if json.loads(row['data'])['base_revision']!=store.meta('definition_revision'):raise HTTPException(409,'Definition base changed; reconcile proposal')
   store.db.execute('UPDATE proposals SET state=? WHERE id=?',(body['decision'],id));store.db.execute('INSERT INTO audit(created,action,data) VALUES(?,?,?)',(time.time(),'proposal_decision',json.dumps({'id':id,'decision':body['decision'],'actor':a['name']})))
  return {'state':body['decision'],'activated':False}
 tools=[{'name':name,'description':description,'inputSchema':{'type':'object','properties':{'query':{'type':'string'},'id':{'type':'string'}},'additionalProperties':False}} for name,description in [('dna_search','Search authorized Fortress entities; returns bounded metadata with provenance.'),('dna_relationships','Get evidence-backed relationships for an entity.'),('dna_sources','Read source health and freshness.'),('dna_resolve_endpoint','Read observed endpoint metadata; never invent reachability.'),('dna_definitions','Read accepted ontology definitions and their revision.')]]
 @app.post('/mcp')
 async def mcp(request:Request):
  d=snapshot(request);payload=await request.json();method=payload.get('method');id=payload.get('id');result=None
  if method=='initialize':result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'fortess-dna','version':'0.1.0'}}
  elif method=='notifications/initialized':return JSONResponse({},202)
  elif method=='ping':result={}
  elif method=='tools/list':result={'tools':tools}
  elif method=='tools/call':
   p=payload.get('params',{});name=p.get('name');args=p.get('arguments',{});query=str(args.get('query','')).lower();target=args.get('id')
   if name=='dna_search':value=[n for n in d['nodes'] if query in (n['name']+' '+n['id']).lower()][:100]
   elif name=='dna_relationships':value=[e for e in d['edges'] if target in (e['source'],e['target'])][:200]
   elif name=='dna_sources':value=d['sources']
   elif name=='dna_definitions':value={'revision':d['definition_revision'],'definitions':[v for v in d['definitions'] if query in (v['name']+' '+v['id']).lower()][:100]}
   elif name=='dna_resolve_endpoint':value={'verified_route':False,'reason':'Route requires client-vantage verification','candidates':[n for n in d['nodes'] if n['id']==target and not n.get('removed') and not n.get('stale')]}
   else:return JSONResponse({'jsonrpc':'2.0','id':id,'error':{'code':-32601,'message':'Unknown tool'}})
   result={'content':[{'type':'text','text':json.dumps(value)}],'isError':False}
  else:return JSONResponse({'jsonrpc':'2.0','id':id,'error':{'code':-32601,'message':'Method not supported'}})
  return {'jsonrpc':'2.0','id':id,'result':result}
 static=Path(config.get('static_dir',Path(__file__).parent.parent/'frontend/dist'))
 if static.exists():
  app.mount('/assets',StaticFiles(directory=static/'assets'),name='assets')
  @app.get('/')
  def index():return FileResponse(static/'index.html')
 return app
