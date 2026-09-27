"""Separate native collector owner. API receives only allowlisted snapshots."""
import asyncio,json,os,time,sys,subprocess
from pathlib import Path
from .collectors import unifi,homeassistant,mcp
from .agent import collect
async def main():
 os.umask(0o077);config=json.loads(Path(sys.argv[1]).read_text());root=Path(config['spool']);root.mkdir(parents=True,exist_ok=True)
 async def job(source):
  while True:
   try:
    if source['kind']=='docker':payload=await asyncio.to_thread(collect,source['host_id'])
    elif source['kind']=='ssh_docker':
     # Fixed enrolled host; requests never accept arbitrary SSH destinations or commands.
     if source['host']!='master-benjamin@192.168.0.126':raise ValueError('Host not enrolled')
     code=(Path(__file__).parent/'agent.py').read_text()
     command=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes',source['host'],'DNA_DOCKER=/usr/bin/docker python3 - --once --host-id fortress.host.phronesis']
     def remote():return subprocess.run(command,input=code,text=True,capture_output=True,timeout=35,check=True).stdout
     payload=json.loads(await asyncio.to_thread(remote))
    else:
     nodes,edges=await {'unifi':unifi,'homeassistant':homeassistant,'mcp':mcp}[source['kind']](source)
     payload={'created_at':time.time(),'nodes':nodes,'edges':edges}
    payload['status']='healthy'
   except Exception as e:payload={'created_at':time.time(),'status':'unavailable','detail':type(e).__name__}
   target=root/(source['id']+'.json');temp=target.with_suffix('.tmp');temp.write_text(json.dumps(payload));os.chmod(temp,0o644);temp.replace(target)
   await asyncio.sleep(max(5,source.get('interval',30)))
 await asyncio.gather(*(job(s) for s in config['sources']))
asyncio.run(main())
