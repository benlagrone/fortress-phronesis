import json,hashlib
import pytest
from fastapi.testclient import TestClient
from inventory.ontology import compile_documents,InvalidOntology
from inventory.store import Store
from inventory.app import create_app

def doc(id='a',kind='host',extra=''):
 return f'''---
schema_version: 1
id: {id}
kind: {kind}
name: Example
lifecycle: active
owner: {id}
authority_refs: []
access_class: fortress-private
relationships: []
{extra}---
Readable definition.
'''
def test_compile_and_identity():
 a=compile_documents({'host.md':doc()},'commit');b=compile_documents({'moved.md':doc()},'commit')
 assert a['entities'][0]['id']==b['entities'][0]['id']
@pytest.mark.parametrize('text',[doc(extra='name: Duplicate\n'),doc(extra='x: &a hi\ny: *a\n'),doc().replace('owner: a','owner: missing'),doc().replace('kind: host','kind: magic')])
def test_reject_unsafe(text):
 with pytest.raises(InvalidOntology):compile_documents({'x.md':text},'commit')
def test_no_delete_on_partial_and_recreation(tmp_path):
 s=Store(str(tmp_path/'db'));n={'id':'one','name':'same','kind':'container','state':'running'}
 s.ingest('docker','docker',[n],[]);s.ingest('docker','docker',[],[],complete=False)
 assert not s.snapshot()['nodes'][0]['removed']
 s.ingest('docker','docker',[dict(n,id='two')],[])
 assert {n['id']:n['removed'] for n in s.snapshot()['nodes']}=={'one':True,'two':False}
def test_activation_and_backup(tmp_path):
 s=Store(str(tmp_path/'db'));s.ingest('docker','docker',[{'id':'one','name':'same','kind':'container'}],[])
 b=compile_documents({'a.md':doc()},'v1');s.activate(b);s.backup(str(tmp_path/'backup'))
 restored=Store(str(tmp_path/'backup'));assert restored.snapshot()==s.snapshot() or restored.meta('definition_revision')==b['revision']
 assert any(n['id']=='one' for n in restored.snapshot()['nodes'])
def test_auth_and_mcp_readonly(tmp_path):
 auth=tmp_path/'auth.json';auth.write_text(json.dumps({'identities':[{'name':'viewer','role':'viewer','sha256':hashlib.sha256(b'test').hexdigest()}]}))
 cfg=tmp_path/'config.json';cfg.write_text(json.dumps({'database':str(tmp_path/'db'),'auth_file':str(auth),'sources':[],'secure_cookie':False}))
 app=create_app(cfg)
 with TestClient(app) as c:
  assert c.get('/api/graph').status_code==401
  headers={'Authorization':'Bearer test'}
  assert c.get('/api/graph',headers=headers).status_code==200
  assert c.get('/api/proposals',headers=headers).status_code==403
  r=c.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':1,'method':'tools/list'}).json()
  assert len(r['result']['tools'])==5
  assert c.post('/mcp',headers=headers,json={'id':2,'method':'resources/read'}).json()['error']['code']==-32601
  auth.write_text('{"identities":[]}');assert c.get('/api/graph',headers=headers).status_code==401
