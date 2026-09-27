"""Native, read-only Docker inventory agent. Writes only sanitized atomic spool."""
import json,subprocess,time,os,argparse
from pathlib import Path

def docker(*args):
 result=subprocess.run([os.environ.get('DNA_DOCKER','/usr/local/bin/docker'),*args],capture_output=True,text=True,timeout=20,check=True)
 return result.stdout

def collect(host_id):
 info=json.loads(docker('info','--format','{{json .}}'));engine=host_id+':engine:'+info['ID'];vm=host_id+':vm:colima'
 nodes=[{'id':host_id,'name':'Phronesis' if host_id.endswith('phronesis') else 'Sextant','kind':'host','state':'observed'}, {'id':vm,'name':'Colima Linux VM','kind':'vm','state':'observed'}, {'id':engine,'name':info['Name'],'kind':'runtime','state':'running','attributes':{'architecture':info['Architecture'],'os':info['OperatingSystem']}}]
 edges=[{'source':vm,'target':host_id,'predicate':'hosted_on'},{'source':engine,'target':vm,'predicate':'hosted_on'}]
 if info['Name']!='colima':
  nodes=[n for n in nodes if n['id']!=vm];edges=[{'source':engine,'target':host_id,'predicate':'hosted_on'}]
 ids=docker('ps','-aq','--no-trunc').split();services=set()
 # Full inspect stays inside collector memory; never copy env, mounts, command or args.
 for start in range(0,len(ids),50):
  for c in json.loads(docker('inspect',*ids[start:start+50])):
   id=engine+':container:'+c['Id'];labels=c['Config'].get('Labels') or {};state=c['State'];ports=c['NetworkSettings'].get('Ports') or {}
   bindings=[]
   for port,entries in ports.items():
    for e in entries or []:bindings.append({'container_port':port,'host_ip':e['HostIp'],'host_port':e['HostPort'],'route':'loopback' if e['HostIp'] in ('127.0.0.1','::1') else 'requires_vantage_verification'})
   nodes.append({'id':id,'name':c['Name'].lstrip('/'),'kind':'container','state':state['Status'],'attributes':{'image':c['Config']['Image'],'image_id':c['Image'],'health':state.get('Health',{}).get('Status','unknown'),'ports':bindings}})
   edges.append({'source':id,'target':engine,'predicate':'runs_in'})
   project=labels.get('com.docker.compose.project');service=labels.get('com.docker.compose.service')
   if project and service:
    sid=engine+':compose:'+project+':'+service
    if sid not in services:nodes.append({'id':sid,'name':project+' / '+service,'kind':'service','state':'declared'});services.add(sid)
    edges.append({'source':id,'target':sid,'predicate':'member_of'})
 return {'created_at':time.time(),'nodes':nodes,'edges':edges}
def main():
 p=argparse.ArgumentParser();p.add_argument('--spool');p.add_argument('--once',action='store_true');p.add_argument('--host-id',default='fortress.host.sextant');args=p.parse_args();
 if args.once:print(json.dumps(collect(args.host_id)));return
 if not args.spool:p.error('--spool required unless --once')
 out=Path(args.spool);out.parent.mkdir(parents=True,exist_ok=True);os.umask(0o077)
 while True:
  try:
   payload=collect(args.host_id);temp=out.with_suffix('.tmp');temp.write_text(json.dumps(payload));temp.replace(out)
  except Exception:pass # Consumers independently detect stale spool; never print raw daemon payloads.
  time.sleep(5)
if __name__=='__main__':main()
