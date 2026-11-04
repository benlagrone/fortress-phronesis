"""Inert Markdown authoring, deterministic compilation, typed references."""
import hashlib
import json
import re
from pathlib import Path
import yaml
from yaml.tokens import AliasToken, AnchorToken, TagToken

KINDS = set('site network device host interface address vm runtime application service container ha_device ha_entity area integration mcp_service mcp_tool mcp_resource mcp_template mcp_prompt dataset endpoint project goal requirement capability repository release workflow workstream task worker policy decision schema term source'.split())
PREDICATES = {
 'hosted_on': ({'vm','runtime','service','application','container'}, {'host','vm','runtime'}),
 'runs_in': ({'container','service'}, {'runtime','vm','container'}),
 'implements': ({'service','application','repository'}, {'capability','requirement'}),
 'satisfies': ({'capability','task','release'}, {'requirement','goal'}),
 'exposes': ({'service','mcp_service','container','application'}, {'endpoint','capability','mcp_tool','mcp_resource','mcp_template','mcp_prompt'}),
 'built_from': ({'release','container','application'}, {'repository','release'}),
 'deployed_as': ({'service','application','release'}, {'container','service'}),
}
for name in 'attached_to uplink_to member_of provided_by integrated_via located_in depends_on connects_to replaced_by consumes owned_by validated_by governed_by derived_from'.split():
 PREDICATES[name] = (KINDS, KINDS)
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}$')
class InvalidOntology(ValueError): pass
class Loader(yaml.SafeLoader): pass
def mapping(loader, node, deep=False):
 result = {}
 for key,value in node.value:
  k=loader.construct_object(key,deep=deep)
  if not isinstance(k,str) or k in result: raise InvalidOntology('duplicate or non-string key')
  result[k]=loader.construct_object(value,deep=deep)
 return result
Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
def parse(text, path='definition.md'):
 if len(text.encode()) > 131072: raise InvalidOntology('file too large')
 parts=text.split('---',2)
 if len(parts)!=3 or parts[0].strip(): raise InvalidOntology('front matter required')
 try:
  tokens=list(yaml.scan(parts[1]))
  if len(tokens)>10000 or any(isinstance(t,(AliasToken,AnchorToken,TagToken)) for t in tokens): raise InvalidOntology('unsafe YAML')
  data=yaml.load(parts[1],Loader=Loader)
 except (yaml.YAMLError,RecursionError) as e: raise InvalidOntology('invalid YAML') from e
 required={'schema_version','id','kind','name','lifecycle','owner','authority_refs','access_class','relationships'}
 if not isinstance(data,dict) or not required<=data.keys(): raise InvalidOntology('missing fields')
 if data['schema_version']!=1 or not isinstance(data['id'],str) or not ID.fullmatch(data['id']): raise InvalidOntology('invalid version or identity')
 if data['kind'] not in KINDS or data['lifecycle'] not in {'proposed','active','deprecated','retired'}: raise InvalidOntology('invalid kind/lifecycle')
 if data['access_class'] not in {'fortress-private','restricted'}: raise InvalidOntology('unknown access classification')
 if not isinstance(data['name'],str) or len(data['name'])>256: raise InvalidOntology('invalid name')
 for key in ['authority_refs','relationships']:
  if not isinstance(data[key],list) or len(data[key])>500: raise InvalidOntology('invalid list')
 if not isinstance(data['owner'],str) or any(not isinstance(v,str) for v in data['authority_refs']): raise InvalidOntology('invalid references')
 for rel in data['relationships']:
  if not isinstance(rel,dict) or rel.get('predicate') not in PREDICATES or not isinstance(rel.get('target'),str): raise InvalidOntology('invalid relationship')
  if rel.get('evidence_kind')!='declared': raise InvalidOntology('authored facts must be declared')
 data.update(markdown=parts[2].strip(),path=path,content_hash=hashlib.sha256(text.encode()).hexdigest())
 return data

def compile_documents(documents, source_revision):
 if len(documents)>5000: raise InvalidOntology('too many definitions')
 entities={}
 for path,text in sorted(documents.items()):
  d=parse(text,path)
  if d['id'] in entities: raise InvalidOntology('duplicate identity')
  entities[d['id']]=d
 edges=[]; containment={}
 for id,d in entities.items():
  refs=[d['owner'],*d['authority_refs']]
  for ref in refs:
   if ref not in entities: raise InvalidOntology('unresolved owner/authority: '+ref)
  for r in d['relationships']:
   target=entities.get(r['target'])
   if not target: raise InvalidOntology('unresolved target: '+r['target'])
   src,dst=PREDICATES[r['predicate']]
   if d['kind'] not in src or target['kind'] not in dst: raise InvalidOntology('predicate type mismatch')
   edge={'source':id,'target':r['target'],'predicate':r['predicate'],'evidence_kind':'declared','definition_path':d['path']}
   edges.append(edge)
   if r['predicate'] in {'hosted_on','runs_in','member_of'}:containment.setdefault(id,[]).append(r['target'])
 def visit(n,active,seen):
  if n in active: raise InvalidOntology('containment cycle')
  if n in seen:return
  active.add(n)
  for v in containment.get(n,[]):visit(v,active,seen)
  active.remove(n);seen.add(n)
 seen=set()
 for n in containment:visit(n,set(),seen)
 digest=hashlib.sha256(json.dumps(entities,sort_keys=True).encode()).hexdigest()
 return {'revision':source_revision+':'+digest,'schema_version':1,'compiler_version':'1','entities':list(entities.values()),'edges':edges}

def compile_directory(root, revision):
 root=Path(root).resolve();documents={}
 for p in root.rglob('*.md'):
  if p.is_symlink() or not p.resolve().is_relative_to(root):raise InvalidOntology('symlink forbidden')
  text=p.read_text()
  if text.startswith('---'):documents[str(p.relative_to(root))]=text
 return compile_documents(documents,revision)
