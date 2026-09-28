"""Transactional evidence, revisions and bounded events. No raw source payloads."""
import sqlite3,json,time,hashlib,threading
from pathlib import Path

def stamp():return time.time()
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
class Store:
 def __init__(self,path):
  Path(path).parent.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(path,check_same_thread=False);self.db.row_factory=sqlite3.Row;self.lock=threading.RLock()
  self.db.executescript('''PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
  INSERT OR IGNORE INTO meta VALUES('revision','0');
  INSERT OR IGNORE INTO meta VALUES('definition_revision','none');
  CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,kind TEXT,status TEXT,checked REAL,success REAL,detail TEXT);
  CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,source TEXT,data TEXT,seen REAL,removed INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY,source TEXT,data TEXT);
  CREATE TABLE IF NOT EXISTS events(revision INTEGER PRIMARY KEY,created REAL,data TEXT);
  CREATE TABLE IF NOT EXISTS bundles(revision TEXT PRIMARY KEY,data TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,entity TEXT,data TEXT,state TEXT,created REAL);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,created REAL,action TEXT,data TEXT);
  ''');self.db.commit()
 def meta(self,key):return self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()[0]
 def bump(self,kind,source):
  rev=int(self.meta('revision'))+1
  self.db.execute('UPDATE meta SET value=? WHERE key="revision"',(str(rev),))
  self.db.execute('INSERT INTO events VALUES(?,?,?)',(rev,stamp(),encode({'kind':kind,'source':source,'definition_revision':self.meta('definition_revision')})))
  self.db.execute('DELETE FROM events WHERE revision<?',(rev-2000,));return rev
 def health(self,id,kind,status,detail=''):
  with self.lock,self.db:
   prev=self.db.execute('SELECT * FROM sources WHERE id=?',(id,)).fetchone()
   self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?)',(id,kind,status,stamp(),stamp() if status=='healthy' else prev['success'] if prev else None,detail[:160]))
   if not prev or prev['status']!=status:self.bump('source',id)
 def ingest(self,source,kind,nodes,edges,complete=True,absence='missing'):
  if not complete:
   self.health(source,kind,'partial','Incomplete snapshot; retained prior evidence');return
  if len(nodes)>20000 or len(edges)>40000:raise ValueError('snapshot bound')
  if len({n['id'] for n in nodes})!=len(nodes):raise ValueError('duplicate source IDs')
  now=stamp()
  with self.lock,self.db:
   previous={r['id']:r for r in self.db.execute('SELECT * FROM nodes WHERE source=?',(source,))}; changed=False
   for n in nodes:
    n=dict(n,source=source,evidence_kind=n.get('evidence_kind','observed'));raw=encode(n)
    old=previous.pop(n['id'],None)
    if not old or old['data']!=raw or old['removed']:changed=True
    self.db.execute('INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,0)',(n['id'],source,raw,now))
    if not old and source!='ontology':
     pid=hashlib.sha256((source+n['id']).encode()).hexdigest()
     self.db.execute('INSERT OR IGNORE INTO proposals VALUES(?,?,?,?,?)',(pid,n['id'],encode({'id':n['id'],'name':n['name'],'kind':n['kind'],'source':source,'base_revision':self.meta('definition_revision')}),'pending',now))
   for id,old in previous.items():
    if not old['removed']:
     n=json.loads(old['data']);n['state']=absence
     self.db.execute('UPDATE nodes SET removed=1,data=? WHERE id=?',(encode(n),id));changed=True
   oldedges={r['id']:r['data'] for r in self.db.execute('SELECT * FROM edges WHERE source=?',(source,))}
   newedges={hashlib.sha256((source+encode(e)).encode()).hexdigest():encode(dict(e,collector=source,evidence_kind=e.get('evidence_kind','observed'))) for e in edges}
   if oldedges!=newedges:
    self.db.execute('DELETE FROM edges WHERE source=?',(source,))
    self.db.executemany('INSERT INTO edges VALUES(?,?,?)',[(id,source,v) for id,v in newedges.items()]);changed=True
   prior=self.db.execute('SELECT status FROM sources WHERE id=?',(source,)).fetchone()
   self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?)',(source,kind,'healthy',now,now,''))
   if changed or not prior or prior[0]!='healthy':self.bump('snapshot',source)
 def activate(self,bundle):
  with self.lock,self.db:
   self.db.execute('INSERT OR REPLACE INTO bundles VALUES(?,?,?)',(bundle['revision'],encode(bundle),stamp()))
   # Definitions remain separate assertion records, even when IDs match observations.
   self.db.execute('UPDATE meta SET value=? WHERE key="definition_revision"',(bundle['revision'],))
   self.db.execute('INSERT INTO audit(created,action,data) VALUES(?,?,?)',(stamp(),'definition_activation',encode({'revision':bundle['revision']})))
   self.bump('definition_activation','ontology')
 def snapshot(self,restricted=False):
  with self.lock:
   self.db.execute('BEGIN')
   try:
    now=stamp();sources=[dict(r) for r in self.db.execute('SELECT * FROM sources ORDER BY id')]
    nodes=[]
    for r in self.db.execute('SELECT * FROM nodes ORDER BY id'):
     n=json.loads(r['data'])
     if n.get('access_class')=='restricted' and not restricted:continue
     n.update(last_seen=r['seen'],removed=bool(r['removed']),stale=now-r['seen']>180);nodes.append(n)
    edges=[json.loads(r['data']) for r in self.db.execute('SELECT data FROM edges')]
    revision=self.meta('definition_revision');row=self.db.execute('SELECT data FROM bundles WHERE revision=?',(revision,)).fetchone()
    definitions=[]
    if row:
     bundle=json.loads(row[0])
     for d in bundle['entities']:
      if d['access_class']=='restricted' and not restricted:continue
      definitions.append(d)
      nodes.append({'id':'definition:'+d['id'],'semantic_id':d['id'],'name':d['name'],'kind':d['kind'],'state':d['lifecycle'],'source':'ontology','evidence_kind':'declared','definition':d,'stale':False})
     edges.extend(dict(e,source='definition:'+e['source'],target='definition:'+e['target'],collector='ontology') for e in bundle['edges'])
    allowed={n['id'] for n in nodes};edges=[e for e in edges if e['source'] in allowed and e['target'] in allowed]
    return {'revision':int(self.meta('revision')),'definition_revision':revision,'nodes':nodes,'edges':edges,'definitions':definitions,'sources':sources,'generated_at':now}
   finally:self.db.commit()
 def events(self,after):
  with self.lock:return [dict(r) for r in self.db.execute('SELECT revision,created,data FROM events WHERE revision>? ORDER BY revision LIMIT 2001',(after,))]
 def proposals(self):
  with self.lock:return [dict(r,data=json.loads(r['data'])) for r in self.db.execute('SELECT * FROM proposals ORDER BY created DESC LIMIT 500')]
 def backup(self,path):
  with self.lock:
   target=sqlite3.connect(path);self.db.backup(target);target.close()
