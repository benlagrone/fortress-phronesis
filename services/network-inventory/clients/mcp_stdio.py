"""Shared Codex stdio bridge; private key stays in the native client."""
import sys,json,urllib.request
from pathlib import Path
key=(Path.home()/'.config/fortress/dna/access-token').read_text().strip()
for line in sys.stdin:
 try:
  message=json.loads(line)
  request=urllib.request.Request('http://127.0.0.1:18162/mcp',data=json.dumps(message).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=20) as response:result=json.load(response)
  if 'id' in message:print(json.dumps(result),flush=True)
 except Exception:
  if isinstance(locals().get('message'),dict) and 'id' in message:print(json.dumps({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32000,'message':'Fortess DNA unavailable; verify LAN/VPN and native client'}}),flush=True)
