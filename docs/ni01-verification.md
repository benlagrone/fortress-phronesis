# NI-01 offline verification and remaining acceptance

This completes only the reporting-and-acceptance-ledger implementation stage.
NI-01, all milestones and live acceptance remain incomplete (`not_run`).
The ledger in `evidence/ni01-coverage.json` covers every NI-01 requirement and
scenario. `offline_status=passed` means only the limited check described in its
evidence field passed, never that the full requirement passed.

## Repository contracts observed

Repository `AGENTS.md` requires the existing workspace deployment runway and
`docker compose -p fortress-phronesis -f docker-compose.pericope.yml ...`.
The protected network is `fortress-phronesis-net`; host ports remain MySQL 3307,
API 18000, frontend 13080 and Solomonic Clock 8086. Existing environment wiring,
profiles and dependencies are unchanged. The repository lock verifier passed
its 20 static checks. This does not verify external environment files, running
services, image digests or the authoritative workspace lock.

Shared capability routing remains client/browser -> app same-origin route ->
owning capability service -> provider adapters. Production voice remains owned
by `fortress-lan:voice-gateway`. This stage adds no service, route, deployment
path, image, listener or client registration.

The declared inventory capability owner is `fortress-sextant:network-inventory`.
Repository/project names and container names do not establish physical placement.
An owner string match is only agreement between supplied claims; trusted host,
VM, engine and enrolled endpoint identities still require independent evidence.
Missing identity stays unknown and a conflicting claim stays mismatch. No
external policy files or other projects were inspected in this isolated stage.
Before future runtime work, the owner must read the workspace policies and
Pericope lock named by repository `AGENTS.md`; these offline artifacts cannot
replace them.

## Offline utility interface

Import `scripts/fortress_bootstrap.py` and call `classify_route(home_lan, vpn_up)`,
`assess_owner(observed_owner, expected_owner)` or `report_bootstrap(evidence)`.
There is no probe, CLI collector, credential lookup, logging or control action.
`home_lan` and `vpn_up` accept booleans or None. Known home selects `lan`
regardless of VPN; known away with VPN selects `vpn`; known away without VPN
selects `unavailable`; unresolved inputs select `unknown`. These are supplied
route classifications, not physical-location detection or reachability proofs.

`report_bootstrap` accepts a mapping with `home_lan`, `vpn_up`, `observed_owner`,
`expected_owner`, `service_available` and `source_available`. Missing values
are unknown. Service/source booleans independently map True/False/None to
`available`/`unavailable`/`unknown`; other availability values remain unknown.
Only `owner_status`, `route`, `service_status`, `source_status`, and
`live_acceptance` are returned. The first two come from the production helpers.
`live_acceptance` is always `not_run`, even if supplied evidence claims success.
Identities, credentials, commands and all other fields are excluded.

Synthetic example:

```python
from scripts.fortress_bootstrap import report_bootstrap

report_bootstrap({
    'home_lan': False, 'vpn_up': True,
    'observed_owner': 'owner-b', 'expected_owner': 'owner-a',
    'service_available': False, 'source_available': None,
})
# {'owner_status': 'mismatch', 'route': 'vpn',
#  'service_status': 'unavailable', 'source_status': 'unknown',
#  'live_acceptance': 'not_run'}
```

A service failure does not imply source/device failure. A source failure does
not change the route or service status. The utility does not model freshness,
authentication errors, client disconnection, graph reconciliation or discovery.

## Executed offline validation

- `/usr/bin/python3 -B -m unittest discover -s tests -p 'test_fortress_bootstrap.py' -v`:
  20 tests passed. Includes the retained 12 tests now importing actual production
  code, the ninth route pair, 405 combinations (9 routes x 5 owner cases x 9
  service/source pairs), missing inputs, privacy canaries and helper delegation.
- Throwing mutations of `classify_route`, `assess_owner` and `report_bootstrap`
  in three disposable checkout-local copies each made that test suite exit 1
  with the corresponding mutant error. Originals were never mutated.
- Full repository discovery with `/usr/bin/python3 -B -m unittest discover -s tests -p 'test_*.py' -v`
  and a checkout-local `TMPDIR`: 28 tests ran, 26 passed and 2 failed in unchanged
  `test_author_acq.py`: `test_tracker_audit_allows_identical_ledgers` and
  `test_tracker_audit_warns_on_unknown_status_and_duplicate_name` expected
  `allowed` but received `blocked`. No unrelated fix was attempted.
- `bash scripts/verify-pericope-deploy-lock.sh`: passed, static repository scope.
- `/usr/bin/python3 -B ../stage-check.py`: exit 0, including all 20 tests,
  operator report matrix, exact ledger IDs and dirty-worktree evidence check.
  The external checker is unchanged.
- `git diff --check` and whitespace checks on all four new artifacts: passed.

The system Python launcher emitted sandbox cache-write warnings; the test
interpreter ran and produced the results above. No live verification followed.
Private pinned inputs were read and their supplied SHA-256 pins verified;
private source documents and observed topology were not copied into deliverables.
The initial checkout contained untracked tests and worker inputs; these are
preserved. A narrow `.gitignore` exception exposes the bootstrap source for
review because the repository otherwise ignores `scripts/*`. No files are staged
or committed.

## Owner-performed live checks (all not_run)

Perform only with the necessary authority and a scheduled window for disruptive
checks. Retain dated sanitized evidence with client vantage, exact revision,
expected/actual result, source freshness, owner and remaining gaps privately.

1. **R24 baseline preservation:** record and preserve existing dirty worktrees
   explicitly before any action. Record each authorized worktree's branch,
   commit, status, untracked paths and dirty-file hashes privately. Do not
   auto-stash, clean, commit or overwrite existing edits. Compare after work.
2. **R01/R24 ownership and preflight:** verify trusted Sextant host identity,
   VM/engine identity and their binding. Establish no inventory runtime on
   physical Phronesis or Contabo. Inspect authoritative locks, registry, graph,
   listener occupancy and every approved bootstrap endpoint; record identity,
   route role, freshness and unresolved access gaps. Reconcile pinned images,
   authentication and smoke evidence without changing Pericope contracts.
3. **R16/R17/T17/T27 routes:** test actual home LAN with VPN off/on and away with
   VPN off/on. Verify approved hostname answers, TLS trust and enrolled identity
   from each allowed route. Test guest, WAN and unauthorized IPv6 denial, with
   no graph, metadata or credential exposure. Do not change DNS/VPN automatically.
4. **R17/T15/T18 failures:** independently exercise source auth failure, client
   disconnect and service failure. VPN-up/service-down must keep the VPN status;
   source-down/service-up must affect only the source. Verify first visit without
   cached assets has accurate native helper messaging, no mass offline/deletion,
   and correct recovery/reconciliation after gaps.
5. **R18/T19 discovery:** observe native advertisement and approved enrollment;
   test impostor and DNS-rebinding rejection before authentication. Verify
   network-change reconnect independent of the legacy resolver and graph database.
6. **R19/T20 shared access:** verify supported installed shared MCP configuration;
   run fresh tasks in two authorized non-Sysco projects. Record the same owner,
   tool availability and endpoint resolution with source, freshness and vantage.
7. **R20/T12/T21 privacy:** use synthetic hostile metadata and HA/Docker/MCP
   canaries end-to-end. Inspect storage, APIs, UI, SSE, cache and logs; prove
   exclusion of credentials, sensitive state, command arguments and resource
   contents. Verify escaping, no arbitrary fetch/process, and revocation clearing.
8. **R01/T24 cold start:** in an authorized harness/window start with physical
   Phronesis unavailable and WAN interrupted; show independent bootstrap,
   sources and graph startup while cloud-source gaps remain labeled.
9. **R24/R26/T26 governance:** exercise wrong-host, occupied-port and mismatched
   image/lock cases in an isolated verifier harness. Each must refuse before
   application; verify unrelated services and dirty worktrees stay unchanged.
10. **R26 control boundary:** instrument discovery to prove zero scanning, HA
    actuation, Docker writes, arbitrary SSH/URLs/commands, downstream MCP
    execution or automatic DNS/VPN changes. Synthetic offline filtering is not
    evidence of the future live system's complete control boundary.

## Unchanged program scope and dependencies

All 26 stories, R01-R38 and T01-T38 remain mandatory. This ledger is the NI-01
subset, not a replacement for the complete acceptance record. All unperformed
live network, ownership, identity, reconciliation and deployment gates are
`not_run`. Original predecessor relationships remain required, including NI-21
following NI-02; NI-22 following NI-21/NI-03/NI-04 and gating NI-05; NI-23
following NI-22/NI-11; NI-24 following NI-22/NI-12; NI-25 following
NI-24/NI-13/NI-14 and gating NI-15 and NI-18; NI-26 following NI-23/NI-25/NI-19
and gating NI-20. No PR or offline artifact satisfies predecessor completion.

Later source contracts, graph/ontology, access-scoped views, native clients,
reconciliation, recovery, restore/rollback and the 24-hour pilot remain required.
No live service, milestone, release or NI-01 completion is claimed here.
