"""Locked Contabo release installer. Invoked only by the workspace deployment runner."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path("/root/workspace/fortress-phronesis/ops/lecrown-development")
PROPERTIES = ["platform-backend-1", "platform-frontend-1"]
ROUTES = {
    "app.lecrowndevelopment.com": (13084, 13095),
    "api.lecrowndevelopment.com": (18035, 18045),
}


def run(args, *, env=None, capture=False):
    return subprocess.run(args, env=env, check=True, text=True, stdout=subprocess.PIPE if capture else None).stdout


def properties_identity():
    return run(["docker", "inspect", "--format", "{{.Name}} {{.Id}} {{.Image}}", *PROPERTIES], capture=True)


def vhost(domain):
    matches = {path.resolve() for path in Path("/etc/nginx/sites-enabled").iterdir()
               if path.is_file() and re.search(r"server_name\s+[^;]*\b" + re.escape(domain) + r"\s*[; ]", path.read_text())}
    if len(matches) != 1:
        raise RuntimeError(f"Expected one nginx vhost file for {domain}")
    return matches.pop()


def private_write(path, text):
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(text, encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def new_vhost_text(domain, text):
    names = {name for group in re.findall(r"server_name\s+([^;]+);", text) for name in group.split()}
    if names != {domain}:
        raise RuntimeError(f"{domain} shares a vhost file with another hostname; cutover refused")
    old, new = ROUTES[domain]
    if f"http://127.0.0.1:{old}" not in text and f"http://127.0.0.1:{new}" not in text:
        raise RuntimeError(f"Unexpected upstream for {domain}; cutover refused")
    text = text.replace(f"http://127.0.0.1:{old}", f"http://127.0.0.1:{new}")
    if "proxy_read_timeout" not in text:
        text = text.replace(f"proxy_pass http://127.0.0.1:{new};", f"proxy_pass http://127.0.0.1:{new};\n        proxy_read_timeout 180s;")
    return text


def http_json(url, *, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def wait_health(url):
    for _ in range(45):
        try:
            if http_json(url).get("status") == "ok":
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError(f"Health check did not pass: {url}")


def compose(env, *args):
    return run(["docker", "compose", "-p", "lecrown-development", "-f", str(ROOT / "compose.yaml"), *args], env=env)


def snapshot_existing_database(backup):
    script = """
import os, pathlib, sqlite3, sys
source = pathlib.Path('/app/data/lecrown-development.db')
assert source.is_file(), 'Existing Development database is missing'
directory = source.parent / 'backups'
directory.mkdir(mode=0o700, exist_ok=True)
target = directory / (sys.argv[1] + '.db')
descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(descriptor)
with sqlite3.connect('file:' + str(source) + '?mode=ro', uri=True) as original:
    with sqlite3.connect(target) as snapshot:
        original.backup(snapshot)
        assert snapshot.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('Development database snapshot verified before release')
"""
    run(["docker", "exec", "lecrown-development-backend-1", "python", "-c", script, backup.name])


def validate_payload(payload):
    if not re.fullmatch(r"[a-f0-9]{40}", payload.get("source_sha", "")):
        raise ValueError("Expected a full Git source revision")
    required = {"SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD", "ESPOCRM_USERNAME", "ESPOCRM_PASSWORD"}
    if set(payload.get("runtime", {})) != required or not all(payload["runtime"].values()):
        raise ValueError("Missing or unexpected runtime settings")
    archive = base64.b64decode(payload["archive"], validate=True)
    if hashlib.sha256(archive).hexdigest() != payload["archive_sha256"]:
        raise ValueError("Source archive digest mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if ".." in parts or member.name.startswith("/") or member.issym() or member.islnk():
                raise ValueError("Unsafe source archive entry")
            if parts != ("platform",) and parts[:2] not in {("platform", "backend"), ("platform", "frontend")}:
                raise ValueError("Source archive exceeds the Development application scope")
    return archive


def rollback(backup, env):
    manifest = json.loads((backup / "manifest.json").read_text())
    for domain, target in manifest["vhosts"].items():
        shutil.copy2(backup / domain, target)
    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
    if manifest.get("previous_release"):
        previous = manifest["previous_release"]
        shutil.copy2(backup / "compose.yaml", ROOT / "compose.yaml")
        env["SOURCE_SHA"] = previous["source_sha"]
        compose(env, "up", "-d", "backend", "frontend", "collector")
        private_write(ROOT / "release.json", json.dumps(previous, indent=2))
    else:
        compose(env, "down")


def install(payload):
    archive = validate_payload(payload)
    if os.uname().machine != "x86_64":
        raise RuntimeError("This deployment is validated for linux/amd64 only")
    baseline = properties_identity()
    property_configs = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in Path("/etc/nginx/sites-enabled").glob("*lecrownproperties*") if path.is_file()}
    targets = {domain: vhost(domain) for domain in ROUTES}
    previous_release = json.loads((ROOT / "release.json").read_text()) if (ROOT / "release.json").exists() else None
    for domain, (old, new) in ROUTES.items():
        new_vhost_text(domain, targets[domain].read_text())
        if not previous_release:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", new))
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    for resource, name in [("volume", "lecrown_development_data"), ("network", "lecrown-development-net")]:
        inspected = subprocess.run(["docker", resource, "inspect", name], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if inspected.returncode == 0:
            labels = json.loads(inspected.stdout)[0].get("Labels") or {}
            if labels.get("com.docker.compose.project") != "lecrown-development":
                raise RuntimeError(f"Existing {resource} is not owned by this Development deployment")
    runtime_path = ROOT / "runtime.json"
    if runtime_path.exists():
        runtime = json.loads(runtime_path.read_text())
        for key, value in payload["runtime"].items():
            if key in runtime and runtime[key] != value:
                raise RuntimeError(f"Refusing to overwrite existing runtime setting: {key}")
            runtime.setdefault(key, value)
    else:
        runtime = payload["runtime"]
    env = {**os.environ, **runtime, "SOURCE_SHA": payload["source_sha"]}
    release = ROOT / "releases" / payload["source_sha"]
    release.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        tar.extractall(release, filter="data")
    for kind, context, dockerfile in [
        ("api", "platform/backend", "platform/backend/Dockerfile"),
        ("admin", "platform/frontend", "platform/frontend/admin/Dockerfile"),
    ]:
        image = f"lecrown-development-{kind}:sha-{payload['source_sha']}"
        run(["docker", "build", "--label", f"org.opencontainers.image.revision={payload['source_sha']}",
             "-t", image, "-f", str(release / dockerfile), str(release / context)])
        revision = run(["docker", "image", "inspect", "--format", '{{index .Config.Labels "org.opencontainers.image.revision"}}', image], capture=True).strip()
        if revision != payload["source_sha"]:
            raise RuntimeError("Image revision verification failed")
    backup = ROOT / "backups" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup.mkdir(parents=True, mode=0o700)
    if previous_release:
        snapshot_existing_database(backup)
    for domain, path in targets.items():
        shutil.copy2(path, backup / domain)
    if (ROOT / "compose.yaml").exists():
        shutil.copy2(ROOT / "compose.yaml", backup / "compose.yaml")
    private_write(backup / "manifest.json", json.dumps({"vhosts": {k: str(v) for k, v in targets.items()}, "previous_release": previous_release}, indent=2))
    private_write(runtime_path, json.dumps(runtime, indent=2))
    private_write(ROOT / "install_release.py", payload["installer"])
    private_write(ROOT / "compose.yaml", payload["compose"])
    try:
        compose(env, "config", "--quiet")
        compose(env, "up", "-d", "backend", "frontend")
        wait_health("http://127.0.0.1:18045/healthz")
        login = http_json("http://127.0.0.1:18045/auth/login", data={"username": runtime["ADMIN_USERNAME"], "password": runtime["ADMIN_PASSWORD"]})
        capabilities = http_json("http://127.0.0.1:18045/contracts/capabilities", token=login["access_token"])
        if not capabilities.get("candidate_inbox_enabled"):
            raise RuntimeError("Candidate inbox is not enabled in the new runtime")
        with urllib.request.urlopen("http://127.0.0.1:13095/container-healthz", timeout=20) as response:
            if response.status != 200:
                raise RuntimeError("Frontend health check failed")
        for domain, (old, new) in ROUTES.items():
            path = targets[domain]
            private_write(path, new_vhost_text(domain, path.read_text()))
        run(["nginx", "-t"])
        run(["systemctl", "reload", "nginx"])
        wait_health("https://api.lecrowndevelopment.com/healthz")
        wait_health("https://app.lecrowndevelopment.com/api/healthz")
        if properties_identity() != baseline:
            raise RuntimeError("Properties container identity changed during release")
        for path, digest in property_configs.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Properties nginx configuration changed during release")
        wait_health("https://backoffice.lecrownproperties.com/api/healthz")
        compose(env, "up", "-d", "collector")
        state = {"source_sha": payload["source_sha"], "archive_sha256": payload["archive_sha256"],
                 "released_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "backup": str(backup),
                 "properties_identity": baseline, "candidate_path": "/app/data/procurement-candidates.json"}
        private_write(ROOT / "release.json", json.dumps(state, indent=2))
        print(json.dumps({"deployed": True, "source_sha": payload["source_sha"], "properties_unchanged": True,
                          "backup": str(backup), "app": "https://app.lecrowndevelopment.com/"}), flush=True)
    except Exception:
        rollback(backup, env)
        raise


def main():
    payload = json.load(sys.stdin)
    if payload.get("action") == "rollback":
        backup = Path(payload["backup"]).resolve()
        if backup.parent != (ROOT / "backups").resolve():
            raise ValueError("Rollback backup must belong to this Development deployment")
        runtime = json.loads((ROOT / "runtime.json").read_text())
        current = json.loads((ROOT / "release.json").read_text())
        rollback(backup, {**os.environ, **runtime, "SOURCE_SHA": current["source_sha"]})
    else:
        install(payload)


if __name__ == "__main__":
    main()
