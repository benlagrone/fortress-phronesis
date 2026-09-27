"""Sextant-only governed installer; touches only the DNA runtime and launch jobs."""
import os,pathlib,subprocess,json,secrets,hashlib,plistlib,socket,sys
r=pathlib.Path.home()/'Library/Application Support/Fortress/dna';release=pathlib.Path(sys.argv[1]);revision=sys.argv[2]
assert socket.gethostname().split('.')[0]=='fortress-sextant'
os.umask(0o077)
for name in ['config','collector','data','spool','definitions','logs','backups']:(r/name).mkdir(parents=True,exist_ok=True)
# Colima bind mounts run as the host UID; app uses the native host identity.
uid=os.getuid();gid=os.getgid()
tokenfile=r/'collector/access-token'
if not tokenfile.exists():tokenfile.write_text(secrets.token_urlsafe(48))
token=tokenfile.read_text().strip();(r/'config/auth.json').write_text(json.dumps({'identities':[{'name':'Fortress owner','role':'admin','sha256':hashlib.sha256(token.encode()).hexdigest()}]}))
for p in (r/'config').iterdir():os.chmod(p,0o600)
console='8C30669C4E6C000000000970E32A0000000009F489280000000068C35BD1:2025342498'
sources=[{'id':'docker','kind':'docker','host_id':'fortress.host.sextant','interval':5},{'id':'unifi','kind':'unifi','url':f'https://api.ui.com/v1/connector/consoles/{console}/proxy/network/integration','token_file':str(pathlib.Path.home()/'.config/fortress/secrets/unifi-api-key'),'interval':30}]
collector=r/'collector/config.json'
if collector.exists():
 existing=json.loads(collector.read_text());sources=existing['sources']
collector.write_text(json.dumps({'spool':str(r/'spool'),'sources':sources}))
app={'database':'/data/dna.sqlite','auth_file':'/config/auth.json','definitions_dir':'/definitions','static_dir':'/app/frontend/dist','secure_cookie':False,'route':'private authenticated loopback; HTTPS pending verification','origins':['http://127.0.0.1:18161','http://localhost:18161','http://127.0.0.1:18160','https://fortress-sextant.tail25f5c3.ts.net:8443'],'sources':[{'id':s['id'],'kind':'docker_spool' if s['kind']=='docker' else 'spool','path':'/spool/'+s['id']+'.json','interval':5} for s in sources]}
(r/'config/config.json').write_text(json.dumps(app))
# Real private definitions remain outside the public source repository.
def definition(id,kind,name,owner,relations=[]):
 import yaml
 d={'schema_version':1,'id':id,'kind':kind,'name':name,'lifecycle':'active','owner':owner,'authority_refs':[],'access_class':'fortress-private','relationships':relations}
 return '---\n'+yaml.safe_dump(d,sort_keys=False)+'---\n\n# '+name+'\n\nDeclared identity. Current observations are shown separately.\n'
python='/usr/local/bin/python3.12';venv=r/'collector/venv'
if not (venv/'bin/python').exists():subprocess.run([python,'-m','venv',str(venv)],check=True)
subprocess.run([str(venv/'bin/pip'),'install','--disable-pip-version-check','-q','-r',str(release/'services/network-inventory/requirements.lock')],check=True)
# Generate via installed YAML module in the private collector environment.
seed="""import pathlib,yaml,json,sys
root=pathlib.Path(sys.argv[1]);rev=sys.argv[2]
items=[('fortress.host.sextant','host','Sextant','fortress.host.sextant',[]),('fortress.project.dna','project','Fortess DNA','fortress.host.sextant',[]),('fortress.capability.network-inventory','capability','Network inventory and ontology','fortress.host.sextant',[{'predicate':'owned_by','target':'fortress.host.sextant','evidence_kind':'declared'}])]
for id,kind,name,owner,rels in items:
 p=root/(id+'.md')
 if not p.exists():p.write_text('---\\n'+yaml.safe_dump(dict(schema_version=1,id=id,kind=kind,name=name,lifecycle='active',owner=owner,authority_refs=[],access_class='fortress-private',relationships=rels),sort_keys=False)+'---\\n\\n# '+name+'\\n\\nDeclared identity; live observations remain separate.\\n')
(root/'REVISION').write_text(rev)
"""
subprocess.run([str(venv/'bin/python'),'-c',seed,str(r/'definitions'),revision],check=True)
image='fortess-dna:'+revision[:12];docker='/usr/local/bin/docker'
subprocess.run([docker,'build','-t',image,str(release/'services/network-inventory')],check=True)
imageid=subprocess.check_output([docker,'image','inspect','--format','{{.Id}}',image],text=True).strip()
# Container UID is deliberately the current native host UID to read only its own mounted files.
compose=(release/'docker-compose.network-inventory.yml').read_text().replace('user: "1000:1000"',f'user: "{uid}:{gid}"')
(r/'compose.yaml').write_text(compose)
env=dict(os.environ,DNA_ROOT=str(r),DNA_IMAGE=imageid)
subprocess.run([docker,'compose','-p','fortress-network-inventory','-f',str(r/'compose.yaml'),'up','-d'],env=env,check=True)
(r/'release.json').write_text(json.dumps({'commit':revision,'image_id':imageid,'release':str(release)}))
relay=r/'relay.sh';relay.write_text('''#!/bin/sh
set -eu
[ "$(hostname -s)" = "fortress-sextant" ]
exec /usr/bin/ssh -F "$HOME/.colima/_lima/colima/ssh.config" -o ControlMaster=no -o ControlPath=none -o ControlPersist=no -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 127.0.0.1:18160:127.0.0.1:18160 lima-colima
''');relay.chmod(0o700)
for name,args,extra in [('collector',[str(venv/'bin/python'),'-m','inventory.spool_runner',str(collector)],{'PYTHONPATH':str(release/'services/network-inventory')}),('relay',['/bin/sh',str(relay)],{})]:
 label='com.fortress.dna-'+name;path=pathlib.Path.home()/'Library/LaunchAgents'/f'{label}.plist'
 data={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':15,'EnvironmentVariables':extra,'StandardOutPath':str(r/'logs'/f'{name}.log'),'StandardErrorPath':str(r/'logs'/f'{name}.error.log')}
 path.write_bytes(plistlib.dumps(data));subprocess.run(['launchctl','bootout',f'gui/{uid}/{label}'],capture_output=True);subprocess.run(['launchctl','bootstrap',f'gui/{uid}',str(path)],check=True)
print(json.dumps({'commit':revision,'image_id':imageid,'runtime':str(r)}))
