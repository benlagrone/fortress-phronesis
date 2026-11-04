"""Workspace-owned deployment runner for the isolated LeCrown Development runtime."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
WORKSPACE = Path("/Users/benjaminlagrone/Documents/projects")
LOCK = WORKSPACE / "workspace-deployment/locks/lecrown-development.yaml"
SOURCE = WORKSPACE / "metroLecrown"


def git(*args, source=SOURCE):
    return subprocess.check_output(["git", "-C", str(source), *args])


def validate_source(source):
    source = source.resolve()
    if Path(git("rev-parse", "--show-toplevel", source=source).decode().strip()).resolve() != source:
        raise ValueError("Source must be a Git checkout root")
    remote = git("remote", "get-url", "origin", source=source).decode().strip()
    if remote not in {"https://github.com/benlagrone/lecrown-platform.git", "git@github.com:benlagrone/lecrown-platform.git"}:
        raise ValueError("Source checkout does not belong to the locked application repository")
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha")
    parser.add_argument("--source-root", type=Path, default=SOURCE, help="Clean checkout of the locked source repository")
    parser.add_argument("--app-env", type=Path)
    parser.add_argument("--crm-env", type=Path)
    parser.add_argument("--ssh-env", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", help="Exact Development backup directory from a release receipt")
    parser.add_argument("--verify", action="store_true", help="Read back the deployed release and worker health")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    if lock["compose_project"] != "lecrown-development" or lock["host_ports"] != {"api": "18045", "frontend": "13095"}:
        raise SystemExit("Deployment lock does not match this runner")
    subprocess.run(["python3", str(WORKSPACE / "workspace-deployment/checks/validate_locks.py"),
                    "--app", "lecrown-development"], check=True)
    source_sha = None
    if args.rollback and args.verify:
        parser.error("rollback and verify are mutually exclusive")
    if not args.rollback and not args.verify:
        source = validate_source(args.source_root)
        if not args.source_sha:
            parser.error("--source-sha is required for a release")
        source_sha = git("rev-parse", f"{args.source_sha}^{{commit}}", source=source).decode().strip()
        if git("diff", source_sha, "--", "platform/backend", "platform/frontend", source=source).strip():
            raise SystemExit("Application source differs from the selected commit")
        if git("ls-files", "--others", "--exclude-standard", "platform/backend", "platform/frontend", source=source).strip():
            raise SystemExit("Untracked application files must be reviewed before release")
    print(json.dumps({"action": "verify" if args.verify else "rollback" if args.rollback else "deploy", "apply": args.apply,
                      "source_sha": source_sha, "host": "89.117.151.145", "project": "lecrown-development",
                      "development_ports": {"frontend": 13095, "api": 18045}, "properties_ports_unchanged": [13084, 18035]}), flush=True)
    if not args.apply:
        return
    if not args.ssh_env:
        parser.error("--ssh-env is required for an authorized deployment connection")
    ssh_values = dotenv_values(args.ssh_env)
    password = ssh_values.get("SSH_PWD") or ssh_values.get("pwd")
    if not password:
        raise SystemExit("Deployment connection credential is missing")
    installer = (HERE / "install_release.py").read_text()
    if args.verify:
        payload = {"action": "verify"}
    elif args.rollback:
        payload = {"action": "rollback", "backup": args.rollback}
    else:
        if not args.app_env or not args.crm_env:
            parser.error("--app-env and --crm-env are required; whole files are never uploaded")
        app, crm = dotenv_values(args.app_env), dotenv_values(args.crm_env)
        runtime = {key: app.get(key) for key in ["SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD"]}
        runtime.update(ESPOCRM_USERNAME=crm.get("ESPOCRM_USERNAME") or crm.get("ESPOLOGIN"),
                       ESPOCRM_PASSWORD=crm.get("ESPOCRM_PASSWORD") or crm.get("ESPOPW"))
        if not all(runtime.values()):
            raise SystemExit("Required Development or CRM settings are missing")
        archive = git("archive", "--format=tar.gz", source_sha, "platform/backend", "platform/frontend", source=source)
        payload = {"action": "deploy", "source_sha": source_sha, "runtime": runtime, "installer": installer,
                   "compose": (HERE / "compose.yaml").read_text(), "archive": base64.b64encode(archive).decode(),
                   "archive_sha256": hashlib.sha256(archive).hexdigest()}
    with tempfile.TemporaryDirectory(prefix="lecrown-deploy-") as temporary:
        askpass = Path(temporary) / "askpass"
        askpass.write_text('#!/bin/sh\nprintf "%s" "$LECROWN_DEPLOY_PASSWORD"\n')
        askpass.chmod(0o700)
        env = {**os.environ, "DISPLAY": ":0", "SSH_ASKPASS_REQUIRE": "force", "SSH_ASKPASS": str(askpass), "LECROWN_DEPLOY_PASSWORD": password}
        command = "python3 -c " + shlex.quote(installer)
        subprocess.run(["ssh", "-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password",
                        "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=20",
                        "root@89.117.151.145", command], input=json.dumps(payload), text=True, env=env, check=True)


if __name__ == "__main__":
    main()
