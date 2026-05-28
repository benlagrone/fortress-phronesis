# Fortress LAN VibeVoice Handoff - 2026-05-28

## Symptom

PericopeAI Speak reaches the production API, but VibeVoice synthesis fails.

Browser/network response:

```json
{"detail":"VibeVoice service error: [Errno 111] Connection refused"}
```

Production API logs:

```text
[vibevoice_tts] {"event":"session_created","request_id":"codex-latency-smoke-20260528-001","chunk_count":3,...}
[vibevoice_tts] {"event":"session_chunk_synthesis_started","request_id":"codex-latency-smoke-20260528-001:chunk-1-of-3",...}
[vibevoice_tts] {"event":"job_create_started","request_id":"codex-latency-smoke-20260528-001:chunk-1-of-3",...}
[vibevoice_tts] {"event":"job_create_failed","error":"[Errno 111] Connection refused","upstream_elapsed_ms":49,...}
```

## Current Diagnosis

This is not a Pericope route or Contabo tunnel failure.

Confirmed from Contabo:

- `http://192.168.0.126:11434/api/tags` works for Ollama.
- `http://192.168.0.126:8133/control/api/voice` works for Fortress LAN control plane.
- `http://192.168.0.126:8011/healthz` refuses connection.

Confirmed from Fortress LAN control plane:

```json
{
  "configured": true,
  "base_url": "http://127.0.0.1:8011",
  "ok": false,
  "detail": "HTTPConnectionPool(host='127.0.0.1', port=8011): ... [Errno 111] Connection refused"
}
```

Attempting to start the VibeVoice container failed:

```text
Error response from daemon: failed to create task for container:
failed to fulfil mount request: open /run/nvidia-persistenced/socket: no such file or directory
```

Host GPU state:

```text
nvidia-smi:
Failed to initialize NVML: Driver/library version mismatch
NVML library version: 580.159

/proc/driver/nvidia/version:
NVIDIA UNIX Open Kernel Module ... 580.142

nvidia-persistenced.service:
inactive (dead) since Thu 2026-05-21
```

## Likely Root Cause

Fortress LAN NVIDIA user-space libraries and loaded kernel driver are mismatched. The GPU container runtime cannot start VibeVoice until the host NVIDIA stack is coherent again.

## Operator Recovery

Run on Fortress LAN as an operator with sudo:

```bash
ssh master-benjamin@100.100.97.30
nvidia-smi
cat /proc/driver/nvidia/version
systemctl status nvidia-persistenced --no-pager
```

If `nvidia-smi` still reports driver/library mismatch, complete the NVIDIA driver update and reboot the LAN host during an acceptable maintenance window.

After GPU runtime is healthy:

```bash
cd /home/master-benjamin/Projects/fortress-lan
VIBEVOICE_ENGINE=official docker compose --profile voice up -d --build vibevoice-api
curl -fsS http://127.0.0.1:8011/healthz
curl -fsS http://192.168.0.126:8011/healthz
```

Then from Contabo:

```bash
curl -fsS http://192.168.0.126:8011/healthz
curl -fsS http://192.168.0.126:8133/control/api/voice
```

## Pericope Fallback

PericopeAI now treats VibeVoice connection refusal as voice-service unavailable and falls back to browser speech synthesis, so the Speak button remains usable while Fortress LAN VibeVoice is offline.
