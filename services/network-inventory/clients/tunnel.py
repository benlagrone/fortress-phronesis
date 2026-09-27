"""LAN-first, VPN-fallback, pinned-host SSH transport. Does not change VPN state."""
import subprocess,pathlib,time,json,urllib.request,signal,os
root=pathlib.Path.home()/'.config/fortress/dna';state=root/'connection.json';child=None

def write(mode,status):
 p=state.with_suffix('.tmp');p.write_text(json.dumps({'route':mode,'status':status,'checked_at':time.time(),'identity':'SSH pinned fortress-sextant.lan','location':'unknown'}));p.replace(state)
def stop(*args):
 if child:child.terminate()
 raise SystemExit
signal.signal(signal.SIGTERM,stop)
while True:
 connected=False
 for host,mode in [('192.168.0.36','LAN'),('100.121.75.0','VPN')]:
  write(mode,'connecting')
  args=['/usr/bin/ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=fortress-sextant.lan','-o','ConnectTimeout=4','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','-N','-L','127.0.0.1:18162:127.0.0.1:18160',host]
  child=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  while child.poll() is None:
   try:
    with urllib.request.urlopen('http://127.0.0.1:18162/healthz',timeout=3) as r:healthy=json.load(r).get('service')=='fortess-dna'
    write(mode,'connected' if healthy else 'identity_mismatch');connected=True
   except Exception:write(mode,'service_unreachable')
   time.sleep(5)
  child=None
  if connected:break
 write('none','VPN may be required; private service unreachable');time.sleep(5)
