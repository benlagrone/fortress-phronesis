"""Loopback-only Mac client. SSH supplies transport identity and encryption."""
import http.server,urllib.request,urllib.error,pathlib,json,os
ROOT=pathlib.Path.home()/'.config/fortress/dna'
class Proxy(http.server.BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args):pass
 def handle_request(self):
  if self.headers.get('Host') not in {'127.0.0.1:18161','localhost:18161'} or self.headers.get('Origin','http://127.0.0.1:18161') not in {'http://127.0.0.1:18161','http://localhost:18161'}:
   self.send_error(403);return
  if self.headers.get('Transfer-Encoding'):self.send_error(400);return
  try:length=int(self.headers.get('Content-Length','0'))
  except ValueError:self.send_error(400);return
  if length>131072 or length<0:self.send_error(413);return
  headers={'Authorization':'Bearer '+(ROOT/'access-token').read_text().strip(),'Content-Type':self.headers.get('Content-Type','application/json')}
  if self.headers.get('Origin'):headers['Origin']=self.headers['Origin']
  req=urllib.request.Request('http://127.0.0.1:18162'+self.path,data=self.rfile.read(length) if length else None,headers=headers,method=self.command)
  try:
   response=urllib.request.urlopen(req,timeout=30)
  except urllib.error.HTTPError as e:response=e
  except Exception:
   body=b'Fortess DNA is unreachable. Connect to the home LAN or VPN; the client cannot currently verify the Sextant route.'
   self.send_response(502);self.send_header('Content-Type','text/plain');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
  with response:
   self.send_response(response.status)
   for k,v in response.headers.items():
    if k.lower() not in {'connection','transfer-encoding','set-cookie'}:self.send_header(k,v)
   self.send_header('Connection','close');self.end_headers();self.close_connection=True
   try:
    if 'text/event-stream' in response.headers.get('Content-Type',''):
     while True:
      line=response.readline()
      if not line:break
      self.wfile.write(line);self.wfile.flush()
    else:
     while True:
      chunk=response.read(65536)
      if not chunk:break
      self.wfile.write(chunk)
   except (BrokenPipeError,ConnectionResetError):pass
 do_GET=handle_request;do_POST=handle_request;do_DELETE=handle_request
http.server.ThreadingHTTPServer(('127.0.0.1',18161),Proxy).serve_forever()
