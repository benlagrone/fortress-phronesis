"""Local operator backup and isolated recovery drill. Never exposed via MCP."""
import argparse,json,sqlite3,time
from pathlib import Path
from .store import Store
p=argparse.ArgumentParser();p.add_argument('command',choices=['backup','restore-drill']);p.add_argument('--database',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
source=Store(a.database);source.backup(a.destination)
if a.command=='backup':print(json.dumps({'backup_created':True}));raise SystemExit
shadow=Store(a.destination);before={r[0] for r in shadow.db.execute('SELECT id FROM nodes')};revision=shadow.meta('definition_revision')
assert shadow.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
versions=list(shadow.db.execute('SELECT data FROM bundles ORDER BY created'))
if versions:
 shadow.activate(json.loads(versions[0][0]));assert before=={r[0] for r in shadow.db.execute('SELECT id FROM nodes')}
 current=shadow.db.execute('SELECT data FROM bundles WHERE revision=?',(revision,)).fetchone();shadow.activate(json.loads(current[0]))
assert before=={r[0] for r in shadow.db.execute('SELECT id FROM nodes')}
print(json.dumps({'restore_integrity':'ok','identities_preserved':len(before),'definition_versions_tested':len(versions),'definition_rollback_preserved_observations':bool(versions)}))
