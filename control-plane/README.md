# Control Plane Container

Lightweight ops container to run deployment scripts against Contabo. No secrets baked in; mount the repo and SSH key at runtime.

## Build
```bash
docker build -t control-plane -f control-plane/Dockerfile .
```

## Run (interactive)
```bash
docker run -it --rm \
  -v "$PWD":/workspace \
  -v "$HOME/.ssh/id_rsa":/root/.ssh/id_rsa:ro \
  -v "$HOME/.ssh/known_hosts":/root/.ssh/known_hosts:ro \
  control-plane
```
Then inside:
```bash
cd /workspace
git pull
bash scripts/deploy-containers.sh   # or other ops scripts
```

## Notes
- Use an SSH key limited to the Contabo host.
- Container initiates outbound SSH only; no ports are exposed.
- Consider creating a non-root user if you prefer; adjust mounts accordingly.
